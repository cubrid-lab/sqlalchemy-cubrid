# scripts/report_test_results.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Write ``summary.json`` and a console summary from a pytest JUnit file (#1019).

``make test`` runs pytest with ``--junitxml`` and ``--cov-report=xml`` under
``test-results/test/`` and then calls this helper, which reads both files back and
writes ``summary.json``. The lane name and every path are arguments, so another lane
(for example a live-database one) can reuse it; coverage is optional.

Status:

* ``PASS``: pytest exited 0, nothing failed or errored, every expected file parsed
  and the coverage threshold (when given) is met.
* ``FAIL``: pytest exited non-zero, a test failed or errored, or coverage is below
  the threshold.
* ``INCOMPLETE``: pytest exited 0 but the JUnit file (or the coverage file, which is
  required whenever a threshold is given) is missing or unreadable, or holds no test case, 

With ``--require-executed`` (the live lane, #1020) a run in which no test passed,
failed, errored, xfailed or xpassed (every case skipped, as ``scripts/check_not_all_skipped.py``
judges a pytest log) is ``INCOMPLETE``, never ``PASS``; ``executed`` in ``summary.json``
says whether any test ran. ``--reason`` records why a run stopped early (a refused or
failed lifecycle) as a problem.

The exit status is 0 only for ``PASS``. A strict ``xpass`` is reported as a failure
by pytest and is counted as ``xpassed`` (not ``failed``); a non-strict ``xpass`` is a
plain pass in JUnit and counts as ``passed``.

Usage::

    python -m scripts.report_test_results --lane test --junit J.xml \
        --coverage C.xml --threshold 95 --pytest-exit 0 --output summary.json
    python -m scripts.report_test_results step-summary --summary summary.json \
        --title "Unit tests (Python 3.12)" >> "$GITHUB_STEP_SUMMARY"

``environment`` writes ``environment.json`` (Python, SQLAlchemy, driver and CUBRID
versions, platform, command; never credentials) next to a live lane's ``summary.json``.

``step-summary`` prints the one-line summary of a ``summary.json`` as Markdown for the
GitHub job summary (#1021). It always exits 0 and says so when the file is missing or
unreadable, so a publishing step never hides the failure of the test step before it.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import sys
from importlib import metadata
from pathlib import Path
from xml.etree.ElementTree import ParseError

from defusedxml import ElementTree

SCHEMA_VERSION = 1
COUNT_KEYS = ("selected", "passed", "failed", "errors", "skipped", "xfailed", "xpassed")
# Outcomes that prove a test body ran (the same meaning as check_not_all_skipped.py).
EXECUTED_KEYS = ("passed", "failed", "errors", "xfailed", "xpassed")
# Distribution names a driver is installed under; the first one found is reported.
DRIVER_DISTRIBUTIONS = {
    "pycubrid": ("pycubrid",),
    "cubriddb": ("CUBRID-Python", "cubrid-python", "CUBRIDdb"),
}


def parse_junit(path: Path) -> dict[str, int]:
    """Count the outcomes of the ``<testcase>`` records in a pytest JUnit file.

    pytest writes one record per failing phase, so a test whose call and teardown both
    fail has two records. ``selected`` counts each test once (by class name and name);
    every failure and error is still counted. A test with a failure or error is never
    also counted as passed, skipped or xfailed.
    """
    counts = dict.fromkeys(COUNT_KEYS, 0)
    clean: dict[tuple[str, str], str] = {}
    bad: set[tuple[str, str]] = set()
    root = ElementTree.parse(path).getroot()
    for case in root.iter("testcase"):
        key = (case.get("classname") or "", case.get("name") or "")
        clean.setdefault(key, "passed")
        if case.find("error") is not None:
            counts["errors"] += 1
            bad.add(key)
        elif (failure := case.find("failure")) is not None:
            if "XPASS(strict)" in (failure.get("message") or ""):
                counts["xpassed"] += 1
            else:
                counts["failed"] += 1
            bad.add(key)
        elif (skipped := case.find("skipped")) is not None:
            clean[key] = "xfailed" if skipped.get("type") == "pytest.xfail" else "skipped"
    counts["selected"] = len(clean)
    for key, outcome in clean.items():
        if key not in bad:
            counts[outcome] += 1
    return counts


def parse_coverage(path: Path) -> float:
    """Total line coverage, in percent, from a Cobertura ``coverage.xml``."""
    root = ElementTree.parse(path).getroot()
    return round(float(root.attrib["line-rate"]) * 100, 2)


def build_summary(
    *,
    lane: str,
    junit: Path,
    coverage: Path | None,
    threshold: float | None,
    pytest_exit: int,
    require_executed: bool = False,
    reason: str = "",
) -> dict[str, object]:
    """Read the result files and return the ``summary.json`` document."""
    problems: list[str] = [reason] if reason else []
    counts: dict[str, int] | None = None
    try:
        counts = parse_junit(junit)
    except (OSError, ParseError) as exc:
        problems.append(f"cannot read JUnit file {junit}: {exc}")
    percent: float | None = None
    if coverage is None and threshold is not None:
        problems.append("a coverage threshold was given without a coverage file")
    if coverage is not None:
        try:
            percent = parse_coverage(coverage)
        except (OSError, ParseError, KeyError, ValueError) as exc:
            problems.append(f"cannot read coverage file {coverage}: {exc}")
    threshold_met: bool | None = None
    if threshold is not None and percent is not None:
        threshold_met = percent >= threshold

    failing = pytest_exit != 0 or threshold_met is False
    if counts is not None and (counts["failed"] or counts["errors"] or counts["xpassed"]):
        failing = True
    executed = None if counts is None else any(counts[key] for key in EXECUTED_KEYS)
    if failing:
        status = "FAIL"
    elif problems or (counts is not None and counts["selected"] == 0):
        status = "INCOMPLETE"
        if not problems:
            problems.append("the JUnit file has no test cases")
    elif require_executed and not executed:
        status = "INCOMPLETE"
        problems.append("every selected test was skipped; the lane proved nothing")
    else:
        status = "PASS"
    return {
        "schema_version": SCHEMA_VERSION,
        "lane": lane,
        "status": status,
        "pytest_exit_code": pytest_exit,
        "executed": executed,
        "counts": counts,
        "coverage": {"percent": percent, "threshold": threshold, "threshold_met": threshold_met},
        "problems": problems,
    }


def format_line(summary: dict[str, object]) -> str:
    """The one-line console summary; always derived from *summary*."""
    counts = summary["counts"]
    coverage = summary["coverage"]
    assert isinstance(coverage, dict)
    parts = [f"{summary['lane']}: {summary['status']}"]
    if isinstance(counts, dict):
        parts.append(", ".join(f"{counts[key]} {key}" for key in COUNT_KEYS))
    if coverage["percent"] is not None:
        text = f"coverage {coverage['percent']:.2f}%"
        if coverage["threshold"] is not None:
            met = "met" if coverage["threshold_met"] else "NOT met"
            text += f" (threshold {coverage['threshold']:g}% {met})"
        parts.append(text)
    line = "; ".join(parts)
    problems = summary["problems"]
    if isinstance(problems, list) and problems:
        line += " [" + "; ".join(str(p) for p in problems) + "]"
    return line


def _version(*names: str) -> str | None:
    for name in names:
        try:
            return metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return None


# Credential assignments (NAME=value, quoted or not) and authenticated URLs.
_ASSIGNMENT = re.compile(
    r"""(\b\w*(?:PASSWORD|PASSWD|PWD|TOKEN|SECRET|CREDENTIAL|API_?KEY)\w*=)"""
    r"""("[^"]*"|'[^']*'|\S*)""",
    re.IGNORECASE,
)
_URL_PASSWORD = re.compile(r"(\b[A-Za-z][\w+.-]*://[^\s:/@]*:)[^\s@]*(@)")


def redact(text: str) -> str:
    """Mask credential assignments and URL passwords in *text* with ``***``."""
    text = _ASSIGNMENT.sub(r"\1***", text)
    return _URL_PASSWORD.sub(r"\1***\2", text)


def build_environment(
    *, lane: str, command: str, cubrid_version: str, driver: str
) -> dict[str, object]:
    """The ``environment.json`` document: fixed, non-secret facts only (#1020)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "lane": lane,
        "command": redact(command),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "sqlalchemy": _version("SQLAlchemy"),
        "sqlalchemy_cubrid": _version("sqlalchemy-cubrid"),
        "driver": {
            "name": driver,
            "version": _version(*DRIVER_DISTRIBUTIONS.get(driver, (driver,))),
        },
        "cubrid_version": cubrid_version,
    }


def environment_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="report_test_results environment")
    parser.add_argument("--lane", required=True)
    parser.add_argument("--command", required=True, help="the command that ran the lane")
    parser.add_argument("--cubrid-version", required=True)
    parser.add_argument("--driver", required=True, help="pycubrid or cubriddb")
    parser.add_argument("--output", required=True, type=Path, help="environment.json to write")
    args = parser.parse_args(argv)
    document = build_environment(
        lane=args.lane,
        command=args.command,
        cubrid_version=args.cubrid_version,
        driver=args.driver,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return 0


def step_summary(summary_path: Path, title: str) -> str:
    """Markdown for ``$GITHUB_STEP_SUMMARY``: a heading and the console line."""
    heading = f"### {title}\n\n"
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        line = format_line(summary)
    except (OSError, ValueError, KeyError, TypeError, AssertionError):
        return f"{heading}No readable `{summary_path}` was written (the run stopped early).\n"
    return f"{heading}`{line}`\n"


def step_summary_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="report_test_results step-summary")
    parser.add_argument("--summary", required=True, type=Path, help="summary.json to render")
    parser.add_argument("--title", default="Test results", help="heading, e.g. the matrix entry")
    args = parser.parse_args(argv)
    print(step_summary(args.summary, args.title), end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["step-summary"]:
        return step_summary_main(argv[1:])
    if argv[:1] == ["environment"]:
        return environment_main(argv[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", required=True, help="lane name recorded in summary.json")
    parser.add_argument("--junit", required=True, type=Path, help="pytest --junitxml file")
    parser.add_argument("--coverage", type=Path, default=None, help="Cobertura coverage.xml")
    parser.add_argument("--threshold", type=float, default=None, help="coverage floor in percent")
    parser.add_argument("--pytest-exit", required=True, type=int, help="pytest's exit status")
    parser.add_argument("--output", required=True, type=Path, help="summary.json to write")
    parser.add_argument(
        "--require-executed",
        action="store_true",
        help="INCOMPLETE unless at least one test ran (not only skipped)",
    )
    parser.add_argument("--reason", default="", help="why the run stopped early; a problem")
    args = parser.parse_args(argv)

    summary = build_summary(
        lane=args.lane,
        junit=args.junit,
        coverage=args.coverage,
        threshold=args.threshold,
        pytest_exit=args.pytest_exit,
        require_executed=args.require_executed,
        reason=args.reason,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{format_line(summary)} -> {args.output}")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
