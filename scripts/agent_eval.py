#!/usr/bin/env python3
"""Offline, deterministic grader for the opt-in agent evaluations in ``agent-evals/`` (#906).

An evaluation task (``agent-evals/tasks/<id>/task.json``) freezes a documented
historical fix: the base SHA before it, the problem, the files a correct change
may touch, the offline tests that prove the behavior, the documentation and
CHANGELOG decision, and which live CUBRID evidence the task does *not* have.

A candidate is three artifacts, never the agent's explanation alone:

* ``patch.diff``: the change, as ``git diff`` output against the base SHA;
* ``report.json``: what the agent says it ran and claims (see the README);
* ``results.json`` (optional): what ``scripts/agent_eval.py run`` observed when it
  applied the patch at the base SHA and ran the task's offline commands.

``grade`` scores the candidate against the task. Every criterion is ``pass``,
``fail`` or ``not_run``; a missing ``results.json`` makes the behavior criterion
``not_run``, so the verdict is at best ``incomplete``, never ``pass``. The output
is sorted JSON with no timestamps: the same artifacts always produce the same
bytes. ``check`` grades every recorded fixture under ``agent-evals/tasks`` and
compares it with its ``expected.json``. Nothing here calls a model, reads the
network or needs a database.

Usage::

    python scripts/agent_eval.py validate
    python scripts/agent_eval.py run --task ID --patch P --output J [--live]
    python scripts/agent_eval.py grade --task ID --patch P --report R [--results J]
    python scripts/agent_eval.py check

``run`` is the local dry run: it checks out the task's base SHA in a temporary
``git worktree``, applies the patch there and runs the task's offline commands
(and its live commands only with ``--live``), then removes the worktree. It needs
the base SHA in the local clone (``git fetch --unshallow`` in a shallow one).
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "agent-evals"
SCHEMA_VERSION = 1

# Evidence kinds an agent may report. Only the ``*_live`` kinds say anything about
# a real CUBRID server; compiled SQL, bound parameters and offline (recorded or
# mocked) reflection never do (#906: do not conflate compiled, bound and reflected).
EVIDENCE_KINDS = ("compiled", "bound", "reflected_offline", "executed_live", "reflected_live")
LIVE_KINDS = frozenset({"executed_live", "reflected_live"})
RESULTS = ("passed", "failed", "not run")

TASK_KEYS = {
    "schema_version",
    "id",
    "title",
    "issue",
    "fix_commit",
    "base_sha",
    "problem",
    "allowed_files",
    "required_tests",
    "non_goals",
    "validation",
    "docs",
    "changelog",
    "evidence",
    "expected",
}

# A statement that claims live verification. Matched case-insensitively in the
# report's statements and in lines the patch adds to Markdown files.
LIVE_CLAIM = re.compile(
    r"\b(?:verified|tested|confirmed|validated|works?|ran|passe[sd])\b[^.\n]{0,40}?"
    r"\b(?:on|against|with)\s+(?:a\s+)?(?:live\s+)?CUBRID\b"
    r"|\blive\s+(?:CUBRID\s+)?(?:tests?|run|integration)\s+(?:passe[sd]|succeeded)\b",
    re.IGNORECASE,
)
NOT_VERIFIED = re.compile(r"\bnot\s+(?:been\s+)?(?:verified|run|tested)\b", re.IGNORECASE)
# The supported CUBRIDdb C-extension driver must not be called deprecated; only
# the ``[cubrid]``/``[cubriddb]`` extras are (same rule as check_support_claims.py).
DEPRECATED_DRIVER = re.compile(
    r"\b(?:legacy|deprecated|obsolete) (?:CUBRIDdb(?: C-extension)?|C-extension) driver\b"
    r"|\bCUBRIDdb (?:driver|C-extension driver) is (?:deprecated|obsolete)\b",
    re.IGNORECASE,
)


class EvalError(Exception):
    """A malformed task or candidate artifact."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise EvalError(f"{path}: {exc}") from exc


def validate_task(task: Any, where: str = "task") -> list[str]:
    """Return one message per problem in a task manifest."""
    if not isinstance(task, dict):
        return [f"{where}: must be a JSON object"]
    errors = []
    missing = sorted(TASK_KEYS - set(task))
    unknown = sorted(set(task) - TASK_KEYS)
    if missing:
        errors.append(f"{where}: missing keys {missing}")
    if unknown:
        errors.append(f"{where}: unknown keys {unknown}")
    if task.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{where}: schema_version must be {SCHEMA_VERSION}")
    for key in ("fix_commit", "base_sha"):
        if not re.fullmatch(r"[0-9a-f]{40}", str(task.get(key, ""))):
            errors.append(f"{where}: {key} must be a full 40-character commit SHA")
    if not re.fullmatch(r"#[0-9]+", str(task.get("issue", ""))):
        errors.append(f"{where}: issue must look like '#123'")
    for key in ("allowed_files", "required_tests", "non_goals"):
        value = task.get(key)
        if not isinstance(value, list) or not value or not all(isinstance(v, str) for v in value):
            errors.append(f"{where}: {key} must be a non-empty list of strings")
    validation = task.get("validation")
    if not isinstance(validation, dict) or not validation.get("offline"):
        errors.append(f"{where}: validation.offline must list at least one command")
    elif not isinstance(validation.get("live", []), list):
        errors.append(f"{where}: validation.live must be a list")
    docs = task.get("docs")
    if not isinstance(docs, list) or not all(isinstance(group, list) and group for group in docs):
        errors.append(f"{where}: docs must be a list of non-empty file-glob groups")
    changelog = task.get("changelog")
    if changelog is not None and not (
        isinstance(changelog, dict) and isinstance(changelog.get("section"), str)
    ):
        errors.append(f"{where}: changelog must be null or {{'section': ...}}")
    evidence = task.get("evidence")
    if not isinstance(evidence, dict):
        errors.append(f"{where}: evidence must be an object")
    else:
        if evidence.get("live") not in ("absent", "present"):
            errors.append(f"{where}: evidence.live must be 'absent' or 'present'")
        required = evidence.get("required_kinds", [])
        if not isinstance(required, list) or any(k not in EVIDENCE_KINDS for k in required):
            errors.append(f"{where}: evidence.required_kinds must use {list(EVIDENCE_KINDS)}")
    if not isinstance(task.get("expected"), str) or not task.get("expected"):
        errors.append(f"{where}: expected must describe the expected result")
    return errors


def parse_patch(text: str) -> dict[str, list[str]]:
    """Map each file the patch touches to the lines it adds (without the ``+``)."""
    return {
        path: [line for kind, line in lines if kind == "+"] for path, lines in _hunks(text).items()
    }


def _hunks(text: str) -> dict[str, list[tuple[str, str]]]:
    """Map each file to its added (``+``) and context (`` ``) lines, in diff order."""
    files: dict[str, list[tuple[str, str]]] = {}
    current: str | None = None
    header = False  # between ``diff --git`` and the file's first ``@@`` hunk
    for line in text.splitlines():
        match = re.match(r"diff --git a/(\S+) b/(\S+)$", line)
        if match:
            current, header = match.group(2), True
            files.setdefault(current, [])
            continue
        if current is None:
            continue
        if line.startswith("@@"):
            header = False
            files[current].append(("@", line))
        elif not header and line[:1] in ("+", " "):
            files[current].append((line[:1], line[1:]))
    return files


def _matches(path: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in globs)


def _criterion(status: str, detail: str) -> dict[str, str]:
    return {"status": status, "detail": detail}


def grade(task: dict[str, Any], patch: str, report: Any, results: Any | None) -> dict[str, Any]:
    """Score one candidate. Raises EvalError for a malformed report or results file."""
    if not isinstance(report, dict) or not isinstance(report.get("tests"), list):
        raise EvalError("report.json must be an object with a 'tests' list")
    if not isinstance(report.get("statements", []), list):
        raise EvalError("report.json 'statements' must be a list of strings")
    files = parse_patch(patch)
    changed = sorted(files)
    criteria: dict[str, dict[str, str]] = {}
    live_backed = _live_backing(results) and (
        results.get("patch_sha256") == hashlib.sha256(patch.encode("utf-8")).hexdigest()
    )

    # Behavior: the task's offline commands, run by ``run`` at the base SHA.
    if results is None:
        criteria["behavior"] = _criterion("not_run", "no results.json: offline tests not run")
    else:
        observed = {c.get("command"): c.get("exit_code") for c in results.get("commands", [])}
        wanted = task["validation"]["offline"]
        missing = [c for c in wanted if c not in observed]
        failed = [c for c in wanted if c in observed and observed[c] != 0]
        digest = hashlib.sha256(patch.encode("utf-8")).hexdigest()
        if (results.get("task"), results.get("base_sha"), results.get("patch_sha256")) != (
            task["id"],
            task["base_sha"],
            digest,
        ):
            criteria["behavior"] = _criterion(
                "fail", "results.json was recorded for another task, base SHA or patch"
            )
        elif not results.get("applied", False):
            criteria["behavior"] = _criterion("fail", "the patch did not apply at the base SHA")
        elif missing:
            criteria["behavior"] = _criterion("not_run", f"not run: {missing}")
        elif failed:
            criteria["behavior"] = _criterion("fail", f"failed: {failed}")
        else:
            criteria["behavior"] = _criterion("pass", "every offline validation command passed")

    tests = [path for path in changed if _matches(path, task["required_tests"])]
    criteria["regression_test"] = (
        _criterion("pass", f"tests changed: {tests}")
        if tests
        else _criterion("fail", f"no change to {task['required_tests']}")
    )

    extra = [path for path in changed if not _matches(path, task["allowed_files"])]
    criteria["scope"] = (
        _criterion("fail", f"outside the allowed files: {extra}")
        if extra
        else _criterion("pass", "every changed file is allowed")
    )

    unmet = [group for group in task["docs"] if not any(_matches(p, group) for p in changed)]
    criteria["docs"] = (
        _criterion("fail", f"no change to any of {unmet}")
        if unmet
        else _criterion("pass", "affected documentation updated")
    )

    criteria["changelog"] = _changelog(task, patch)
    criteria["claims"] = _claims(task, files, report, live_backed)
    criteria["evidence"] = _evidence(task, report, live_backed)

    statuses = {c["status"] for c in criteria.values()}
    verdict = "fail" if "fail" in statuses else "incomplete" if "not_run" in statuses else "pass"
    return {
        "schema_version": SCHEMA_VERSION,
        "task": task["id"],
        "changed_files": changed,
        "criteria": criteria,
        "verdict": verdict,
    }


def _live_backing(results: Any | None) -> bool:
    """Whether the runner recorded a passing live command (only then may live claims stand)."""
    if not isinstance(results, dict):
        return False
    return any(
        c.get("kind") == "live" and c.get("exit_code") == 0 for c in results.get("commands", [])
    )


def _changelog(task: dict[str, Any], patch: str) -> dict[str, str]:
    expected = task["changelog"]
    lines = _hunks(patch).get("CHANGELOG.md", [])
    added = [text for kind, text in lines if kind == "+"]
    if expected is None:
        if added:
            return _criterion("fail", "the task needs no CHANGELOG entry, but one was added")
        return _criterion("pass", "no CHANGELOG entry, as the task expects")
    header = f"### {expected['section']}"
    issue = task["issue"]
    entry = next((i for i, (kind, text) in enumerate(lines) if kind == "+" and issue in text), None)
    if entry is None:
        return _criterion("fail", f"no CHANGELOG entry citing {issue}")
    # The nearest heading before the entry, added or kept as diff context, is its section.
    section = next(
        (text for kind, text in reversed(lines[:entry]) if kind != "@" and text.startswith("### ")),
        None,
    )
    if section is None:
        return _criterion("fail", f"cannot tell the entry's section; expected {header}")
    if section.strip() != header:
        return _criterion("fail", f"the CHANGELOG entry is under {section.strip()}, not {header}")
    return _criterion("pass", f"CHANGELOG entry under {header} cites {issue}")


def _claims(
    task: dict[str, Any], files: dict[str, list[str]], report: dict[str, Any], live_backed: bool
) -> dict[str, str]:
    statements = [s for s in report.get("statements", []) if isinstance(s, str)]
    doc_lines = [line for path, lines in files.items() if path.endswith(".md") for line in lines]
    problems = []
    for text in statements + doc_lines:
        if DEPRECATED_DRIVER.search(text):
            problems.append(f"calls the supported CUBRIDdb driver deprecated: {text.strip()!r}")
    if not live_backed:
        for text in statements + doc_lines:
            if LIVE_CLAIM.search(text) and not NOT_VERIFIED.search(text):
                problems.append(f"live claim without live evidence: {text.strip()!r}")
        for command in task["validation"].get("live", []):
            entry = next((t for t in report["tests"] if t.get("command") == command), None)
            if entry is None or entry.get("result") != "not run":
                problems.append(f"live check {command!r} is not reported as 'not run'")
        if task["validation"].get("live") and not any(NOT_VERIFIED.search(s) for s in statements):
            problems.append("the report does not say what was not verified")
    if problems:
        return _criterion("fail", "; ".join(sorted(set(problems))))
    return _criterion("pass", "claims match the recorded evidence")


def _evidence(task: dict[str, Any], report: dict[str, Any], live_backed: bool) -> dict[str, str]:
    problems = []
    kinds = set()
    for entry in report["tests"]:
        kind, result = entry.get("evidence"), entry.get("result")
        if kind not in EVIDENCE_KINDS or result not in RESULTS:
            problems.append(f"bad report entry {entry!r}")
            continue
        if result == "passed":
            kinds.add(kind)
            if kind in LIVE_KINDS and not live_backed:
                problems.append(f"{kind} reported as passed without a recorded live run")
    for kind in task["evidence"].get("required_kinds", []):
        if kind not in kinds:
            problems.append(f"no passed {kind} evidence")
    if problems:
        return _criterion("fail", "; ".join(problems))
    return _criterion("pass", f"evidence kinds: {sorted(kinds)}")


def run(task: dict[str, Any], patch: str, live: bool = False, repo: Path = ROOT) -> dict[str, Any]:
    """Apply the patch at the base SHA in a throwaway worktree and run the task's commands."""
    commands = [(c, "offline") for c in task["validation"]["offline"]]
    if live:
        commands += [(c, "live") for c in task["validation"].get("live", [])]
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task": task["id"],
        "base_sha": task["base_sha"],
        "patch_sha256": hashlib.sha256(patch.encode("utf-8")).hexdigest(),
        "applied": False,
        "commands": [],
    }
    with tempfile.TemporaryDirectory(prefix="agent-eval-") as tmp:
        worktree = Path(tmp) / "worktree"
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "worktree",
                "add",
                "--detach",
                str(worktree),
                task["base_sha"],
            ],
            check=True,
            capture_output=True,
        )
        try:
            patch_file = Path(tmp) / "candidate.diff"
            patch_file.write_text(patch, encoding="utf-8")
            applied = subprocess.run(
                ["git", "-C", str(worktree), "apply", "--whitespace=nowarn", str(patch_file)],
                capture_output=True,
            )
            result["applied"] = applied.returncode == 0
            if result["applied"]:
                for command, kind in commands:
                    argv = shlex.split(command)
                    if argv[:1] == ["python"]:  # the interpreter running this script
                        argv[0] = sys.executable
                    done = subprocess.run(argv, cwd=worktree, capture_output=True)
                    result["commands"].append(
                        {"command": command, "kind": kind, "exit_code": done.returncode}
                    )
        finally:
            subprocess.run(
                ["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
                capture_output=True,
            )
    return result


def load_task(task_id: str, root: Path = EVALS) -> dict[str, Any]:
    path = root / "tasks" / task_id / "task.json"
    task = load_json(path)
    errors = validate_task(task, str(path.relative_to(root.parent)))
    if errors:
        raise EvalError("; ".join(errors))
    return task


def dump(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def check(root: Path = EVALS) -> list[str]:
    """Validate every task and re-grade every fixture against its expected verdict."""
    problems = []
    tasks = sorted(p.parent for p in (root / "tasks").glob("*/task.json"))
    if not tasks:
        return [f"no tasks under {root / 'tasks'}"]
    for task_dir in tasks:
        try:
            task = load_task(task_dir.name, root)
        except EvalError as exc:
            problems.append(str(exc))
            continue
        if task["id"] != task_dir.name:
            problems.append(f"{task_dir.name}: id is {task['id']!r}")
        fixtures = sorted(p for p in (task_dir / "fixtures").glob("*") if p.is_dir())
        if not fixtures:
            problems.append(f"{task_dir.name}: no fixtures")
        for fixture in fixtures:
            results = fixture / "results.json"
            try:
                got = grade(
                    task,
                    (fixture / "patch.diff").read_text(encoding="utf-8"),
                    load_json(fixture / "report.json"),
                    load_json(results) if results.exists() else None,
                )
            except (EvalError, OSError) as exc:
                problems.append(f"{task_dir.name}/{fixture.name}: {exc}")
                continue
            expected = load_json(fixture / "expected.json")
            if got["verdict"] != expected["verdict"] or any(
                got["criteria"].get(name, {}).get("status") != status
                for name, status in expected["criteria"].items()
            ):
                problems.append(f"{task_dir.name}/{fixture.name}: graded {dump(got)}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="validate every task manifest")
    sub.add_parser("check", help="re-grade every recorded fixture")
    r = sub.add_parser("run", help="dry run: apply a patch at the base SHA and run the tests")
    r.add_argument("--task", required=True)
    r.add_argument("--patch", required=True, type=Path)
    r.add_argument("--output", required=True, type=Path)
    r.add_argument("--live", action="store_true", help="also run the live commands")
    g = sub.add_parser("grade", help="grade one candidate")
    g.add_argument("--task", required=True)
    g.add_argument("--patch", required=True, type=Path)
    g.add_argument("--report", required=True, type=Path)
    g.add_argument("--results", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            for task_dir in sorted(p.parent for p in (EVALS / "tasks").glob("*/task.json")):
                load_task(task_dir.name)
            print("agent-evals: every task manifest is valid")
            return 0
        if args.command == "check":
            problems = check()
            for problem in problems:
                print(problem, file=sys.stderr)
            if problems:
                return 1
            print("agent-evals: every fixture grades as expected")
            return 0
        task = load_task(args.task)
        if args.command == "run":
            observed = run(task, args.patch.read_text(encoding="utf-8"), live=args.live)
            args.output.write_text(dump(observed), encoding="utf-8")
            print(f"agent-eval: wrote {args.output}")
            return 0
        result = grade(
            task,
            args.patch.read_text(encoding="utf-8"),
            load_json(args.report),
            load_json(args.results) if args.results else None,
        )
    except (EvalError, OSError, subprocess.CalledProcessError) as exc:
        print(f"agent-eval: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(dump(result))
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
