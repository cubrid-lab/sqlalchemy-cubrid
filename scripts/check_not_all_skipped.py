"""Fail a CI step whose pytest run proved nothing (#486).

A lane that silently skips every test it was meant to run (a stale ``skipif``,
a driver that stopped connecting, a copy-pasted file list that no longer
matches reality) still exits ``0``: pytest treats "zero collected" and
"collected N, all skipped" the same as success. That hides a misconfigured
lane behind a green check.

This script reads the captured stdout/stderr of one or more pytest
invocations (each run through ``tee`` so the summary line survives a failing
earlier command under ``set -o pipefail``) and fails unless at least one of
them shows real execution: zero tests collected, or every collected test
ended up skipped / deselected with none passed, failed, errored or xpassed,
counts as that invocation proving nothing. ``xfailed`` counts as real
execution (the test body ran). Each file is judged on its own final summary
line, independent of the others, so a step that chains several pytest
invocations only needs one of them to actually run something.

A lane that is deliberately all-skip in a given cell (document why) passes
``--allow-all-skipped "<reason>"``; the script then reports the reason and
exits 0 instead of failing on that cell.

Usage::

    set -o pipefail
    python -m pytest test/test_integration.py -v --tb=short | tee run.log
    python -m scripts.check_not_all_skipped run.log --label "integration tests"
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

#: pytest's final summary line, e.g. "===== 9 passed, 1 skipped in 1.23s ====="
#: or "===== no tests ran in 0.01s =====". Matched per line, last match wins.
_SUMMARY_LINE = re.compile(r"^=+\s*(?P<body>.+?)\s*=+\s*$")
_NO_TESTS_RAN = re.compile(r"\bno tests ran\b")
#: "error" also matches the "error" prefix of "errors", so that alternative
#: would never be reached; the dict key is "error" either way.
_COUNT = re.compile(
    r"(?P<count>\d+) (?P<outcome>passed|failed|error|skipped|deselected|xfailed|xpassed)"
)

#: Outcomes that prove the lane actually exercised code, not just skipped past it.
_MEANINGFUL_OUTCOMES = frozenset({"passed", "failed", "error", "xpassed", "xfailed"})


def _last_summary_body(log_text: str) -> str | None:
    """The body of the last pytest summary line in *log_text*, or None."""
    body = None
    for line in log_text.splitlines():
        match = _SUMMARY_LINE.match(line.strip())
        if match:
            body = match["body"]
    return body


def evaluate(log_text: str) -> tuple[bool, str]:
    """Return ``(ok, message)`` for one pytest invocation's captured *log_text*.

    ``ok`` is False when no summary line was found, zero tests were
    collected, or every collected test was skipped/deselected.
    """
    body = _last_summary_body(log_text)
    if body is None:
        return False, "could not find a pytest summary line in the output"
    if _NO_TESTS_RAN.search(body):
        return False, f"pytest ran zero tests ({body})"
    counts: dict[str, int] = {}
    for match in _COUNT.finditer(body):
        counts[match["outcome"]] = counts.get(match["outcome"], 0) + int(match["count"])
    if not counts:
        return False, f"could not parse outcome counts from the pytest summary ({body})"
    meaningful = sum(count for outcome, count in counts.items() if outcome in _MEANINGFUL_OUTCOMES)
    if meaningful == 0:
        return False, f"every collected test was skipped or deselected ({body})"
    return True, f"{meaningful} test(s) actually ran ({body})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logfiles", nargs="+", type=Path, help="captured pytest stdout/stderr")
    parser.add_argument("--label", default=None, help="name of the lane/step, for the message")
    parser.add_argument(
        "--allow-all-skipped",
        metavar="REASON",
        default=None,
        help="do not fail when every test was skipped; print REASON instead",
    )
    args = parser.parse_args(argv)

    label = args.label or ", ".join(str(p) for p in args.logfiles)
    # Each file is judged on its own last summary line, then combined with "any
    # file proved real execution" — a step that chains several pytest
    # invocations is fine as long as one of them actually ran something,
    # independent of the files' order.
    results = [
        evaluate(path.read_text(encoding="utf-8", errors="replace")) for path in args.logfiles
    ]
    detail = "; ".join(message for _, message in results)
    if any(ok for ok, _ in results):
        print(f"{label}: {detail}")
        return 0
    if args.allow_all_skipped:
        print(f"{label}: {detail}; allowed ({args.allow_all_skipped})")
        return 0
    print(f"::error::{label}: {detail}; the lane proved nothing", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
