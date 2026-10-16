"""Offline tests of the agent-evals task format and grader (#906)."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from scripts import agent_eval as ae

TASK_ID = "json-bool-path-index"
FIXTURES = ae.EVALS / "tasks" / TASK_ID / "fixtures"


def _task() -> dict[str, Any]:
    return ae.load_task(TASK_ID)


def _fixture(name: str) -> tuple[str, Any, Any]:
    folder = FIXTURES / name
    results = folder / "results.json"
    return (
        (folder / "patch.diff").read_text(encoding="utf-8"),
        ae.load_json(folder / "report.json"),
        ae.load_json(results) if results.exists() else None,
    )


def _statuses(result: dict[str, Any]) -> dict[str, str]:
    return {name: c["status"] for name, c in result["criteria"].items()}


def test_every_recorded_fixture_grades_as_expected() -> None:
    assert ae.check() == []


def test_the_seed_task_cites_its_issue_fix_and_missing_live_evidence() -> None:
    task = _task()
    assert task["issue"] == "#914"
    assert task["fix_commit"].startswith("7744dd6")
    assert task["evidence"]["live"] == "absent"
    assert task["expected"]


def test_reference_fix_passes_every_criterion() -> None:
    result = ae.grade(_task(), *_fixture("reference"))
    assert result["verdict"] == "pass"
    assert set(_statuses(result).values()) == {"pass"}
    assert result["changed_files"] == sorted(result["changed_files"])


def test_grading_is_byte_for_byte_deterministic() -> None:
    first = ae.dump(ae.grade(_task(), *_fixture("reference")))
    second = ae.dump(ae.grade(_task(), *_fixture("reference")))
    assert first == second
    assert "time" not in first


def test_missing_results_is_incomplete_never_pass() -> None:
    patch, report, _ = _fixture("reference")
    result = ae.grade(_task(), patch, report, None)
    assert result["verdict"] == "incomplete"
    assert _statuses(result)["behavior"] == "not_run"


@pytest.mark.parametrize(
    ("fixture", "criterion"),
    [
        ("wrong_behavior", "behavior"),
        ("missing_regression_test", "regression_test"),
        ("scope_creep", "scope"),
        ("missing_docs", "docs"),
        ("false_live_claim", "claims"),
        ("deprecated_driver_claim", "claims"),
        ("unreported_live_check", "claims"),
        ("conflated_evidence", "evidence"),
        ("results_for_another_patch", "behavior"),
        ("no_fix_comment_only", "behavior"),
        ("mixed_disclaimer", "claims"),
        ("live_run_all_skipped", "evidence"),
        ("offline_command_labelled_live", "evidence"),
    ],
)
def test_each_deliberate_failure_fails_its_criterion(fixture: str, criterion: str) -> None:
    result = ae.grade(_task(), *_fixture(fixture))
    assert result["verdict"] == "fail"
    assert _statuses(result)[criterion] == "fail"


def test_live_claim_stands_only_with_a_recorded_live_run_for_the_same_patch() -> None:
    patch, report, results = _fixture("reference")
    report = copy.deepcopy(report)
    report["statements"] = ["The JSON path test passed against a live CUBRID server."]
    report["tests"][-1]["result"] = "passed"
    assert ae.grade(_task(), patch, report, results)["verdict"] == "fail"

    live = copy.deepcopy(results)
    live["commands"].append(
        {
            "command": _task()["validation"]["live"][0],
            "exit_code": 0,
            "kind": "live",
            "outcome": "passed",
        }
    )
    graded = ae.grade(_task(), patch, report, live)
    assert _statuses(graded)["claims"] == "pass"
    assert _statuses(graded)["evidence"] == "pass"

    live["patch_sha256"] = "0" * 64
    assert _statuses(ae.grade(_task(), patch, report, live))["claims"] == "fail"


def test_a_skipped_live_run_backs_no_claim() -> None:
    patch, report, results = _fixture("live_run_all_skipped")
    assert results["commands"][-1]["outcome"] == "skipped"
    statuses = _statuses(ae.grade(_task(), patch, report, results))
    assert statuses["claims"] == statuses["evidence"] == "fail"


def test_no_fix_is_caught_by_the_hidden_tests() -> None:
    _, _, results = _fixture("no_fix_comment_only")
    outcomes = {c["kind"]: c["outcome"] for c in results["commands"]}
    assert outcomes == {"offline": "passed", "hidden": "failed"}


@pytest.mark.parametrize(
    ("exit_code", "output", "outcome"),
    [
        (0, "....\n4 passed in 0.1s\n", "passed"),
        (0, "4 passed, 2 skipped in 0.1s", "passed"),
        (0, "sss\n3 skipped in 0.1s\n", "skipped"),
        (5, "no tests ran in 0.01s", "skipped"),
        (1, "1 failed, 3 passed in 0.1s", "failed"),
        (0, "", "skipped"),
        (2, "", "failed"),
    ],
)
def test_pytest_outcome(exit_code: int, output: str, outcome: str) -> None:
    assert ae.pytest_outcome(exit_code, output) == outcome


def test_each_clause_is_checked_on_its_own() -> None:
    assert ae._clauses("Verified against CUBRID 11.4. Live reflection was not verified.") == [
        "Verified against CUBRID 11.4",
        "Live reflection was not verified",
    ]
    assert ae._clauses("Tested on CUBRID 11.4, but Alembic was not run") == [
        "Tested on CUBRID 11.4",
        "but Alembic was not run",
    ]


def test_not_verified_wording_is_not_a_live_claim() -> None:
    assert not ae.LIVE_CLAIM.search("Bind rendering is covered offline.")
    text = "The live test was not run, so behavior on a live CUBRID server is not verified."
    assert ae.NOT_VERIFIED.search(text)
    assert ae.LIVE_CLAIM.search("Verified against a live CUBRID 11.4 server.")


def test_deprecated_driver_wording_is_rejected_but_deprecated_extras_are_not() -> None:
    assert ae.DEPRECATED_DRIVER.search("Use pycubrid instead of the legacy CUBRIDdb driver.")
    assert not ae.DEPRECATED_DRIVER.search("The [cubrid] extra is deprecated; CUBRIDdb remains.")


def _patch(path: str, *added: str, context: tuple[str, ...] = ()) -> str:
    lines = [f"diff --git a/{path} b/{path}", f"--- a/{path}", f"+++ b/{path}", "@@ -1 +1 @@"]
    lines += [f" {c}" for c in context] + [f"+{a}" for a in added]
    return "\n".join(lines) + "\n"


def test_patch_parser_keeps_added_lines_that_look_like_headers() -> None:
    files = ae.parse_patch(_patch("a.md", "++ not a header", "-- neither"))
    assert files == {"a.md": ["++ not a header", "-- neither"]}


def test_patch_parser_reads_spaces_renames_new_deleted_and_quoted_paths() -> None:
    patch = "\n".join(
        [
            "diff --git a/scratch notes.txt b/scratch notes.txt",
            "--- a/scratch notes.txt\t",
            "+++ b/scratch notes.txt\t",
            "@@ -1 +1,2 @@",
            "+spaced",
            "diff --git a/plain b/re named",
            "similarity index 100%",
            "rename from plain",
            "rename to re named",
            'diff --git "a/\\303\\251.txt" "b/\\303\\251.txt"',
            "new file mode 100644",
            "--- /dev/null",
            '+++ "b/\\303\\251.txt"',
            "@@ -0,0 +1 @@",
            "+accented",
            "diff --git a/gone.py b/gone.py",
            "deleted file mode 100644",
            "--- a/gone.py",
            "+++ /dev/null",
            "@@ -1 +0,0 @@",
            "-x",
            "diff --git a/img.png b/img.png",
            "Binary files a/img.png and b/img.png differ",
            "",
        ]
    )
    assert ae.parse_patch(patch) == {
        "scratch notes.txt": ["spaced"],
        "plain": [],
        "re named": [],
        "\u00e9.txt": ["accented"],
        "gone.py": [],
        "img.png": [],
    }


def test_a_rename_out_of_an_unallowed_file_is_scope_creep() -> None:
    patch, report, results = _fixture("reference")
    renamed = "\n".join(
        [
            "diff --git a/outside.txt b/docs/TYPES.md",
            "similarity index 100%",
            "rename from outside.txt",
            "rename to docs/TYPES.md",
            "",
        ]
    )
    result = ae.grade(_task(), patch + renamed, report, results)
    assert _statuses(result)["scope"] == "fail"
    assert "outside.txt" in result["criteria"]["scope"]["detail"]
    copied = renamed.replace("rename", "copy")
    assert "outside.txt" not in ae.parse_patch(copied)


def test_a_wrapped_markdown_claim_reads_as_one_paragraph() -> None:
    patch, report, results = _fixture("reference")
    task = _task()
    for added in (["Verified against CUBRID 11.4."], ["Verified against", "CUBRID 11.4."]):
        doc = _patch("docs/TYPES.md", *added)
        result = ae.grade(task, patch + doc, report, results)
        assert _statuses(result)["claims"] == "fail", added
    hunks = ae._hunks(_patch("a.md", "first", "", "second", context=("kept",)))
    assert ae._added_paragraphs(hunks) == ["first", "second"]
    split = ae._hunks(_patch("a.md", "Verified against") + _patch("b.md", "CUBRID 11.4."))
    assert ae._added_paragraphs(split) == ["Verified against", "CUBRID 11.4."]


@pytest.mark.parametrize(
    "patch",
    [
        "diff --git a/x b/y z\nBinary files differ\n",
        "diff --git a/x b/x\n--- x\n+++ x\n",
        'diff --git a/x b/x\n+++ "b/\\xff"\n',
    ],
)
def test_patch_parser_rejects_headers_it_cannot_read(patch: str) -> None:
    with pytest.raises(ae.EvalError):
        ae.parse_patch(patch)


def test_changelog_entry_must_sit_under_the_expected_section() -> None:
    task = _task()
    entry = "- **Bool path components are rejected (#914)**"
    good = ae._changelog(task, _patch("CHANGELOG.md", entry, context=("### Fixed", "")))
    assert good["status"] == "pass"
    wrong = ae._changelog(task, _patch("CHANGELOG.md", entry, context=("### Added", "")))
    assert wrong["status"] == "fail"
    assert ae._changelog(task, _patch("CHANGELOG.md", "- uncited"))["status"] == "fail"
    assert ae._changelog(task, _patch("CHANGELOG.md", entry))["status"] == "fail"

    none_expected = dict(task, changelog=None)
    assert ae._changelog(none_expected, "")["status"] == "pass"
    assert ae._changelog(none_expected, _patch("CHANGELOG.md", entry))["status"] == "fail"


def test_unknown_evidence_kind_is_rejected() -> None:
    patch, report, results = _fixture("reference")
    report = copy.deepcopy(report)
    report["tests"].append({"command": "x", "evidence": "smoke", "result": "passed"})
    assert _statuses(ae.grade(_task(), patch, report, results))["evidence"] == "fail"


@pytest.mark.parametrize(
    "report",
    [
        [],
        {"tests": "x"},
        {"tests": [], "statements": "x"},
        {"tests": [], "statements": [1]},
        {"tests": [None]},
        {"tests": [{"command": "x", "evidence": "compiled"}]},
    ],
)
def test_malformed_report_raises(report: Any) -> None:
    with pytest.raises(ae.EvalError):
        ae.grade(_task(), "", report, None)


@pytest.mark.parametrize(
    "change",
    [
        lambda r: [],
        lambda r: {**r, "commands": None},
        lambda r: {**r, "patch_sha256": None},
        lambda r: {**r, "applied": "yes"},
        lambda r: {**r, "commands": [None]},
        lambda r: {**r, "commands": [{**r["commands"][0], "outcome": "ok"}]},
        lambda r: {**r, "commands": [{**r["commands"][0], "kind": "smoke"}]},
        lambda r: {**r, "commands": [{**r["commands"][0], "exit_code": "0"}]},
    ],
)
def test_malformed_results_raise(change: Any) -> None:
    patch, report, results = _fixture("reference")
    with pytest.raises(ae.EvalError):
        ae.grade(_task(), patch, report, change(results))


def test_validate_task_reports_each_problem() -> None:
    assert ae.validate_task(_task()) == []
    assert ae.validate_task([]) == ["task: must be a JSON object"]
    broken = dict(_task(), base_sha="7a2512f", issue="914", extra=1)
    broken["evidence"] = {"live": "maybe", "required_kinds": ["smoke"]}
    broken["changelog"] = "Fixed"
    broken["validation"] = {"offline": "python -m pytest x", "live": [1]}
    broken["hidden_tests"] = ["../escape.py"]
    del broken["expected"]
    errors = " ".join(ae.validate_task(broken))
    for fragment in (
        "missing keys ['expected']",
        "unknown keys ['extra']",
        "base_sha must be a full",
        "issue must look like",
        "evidence.live",
        "evidence.required_kinds",
        "changelog must be null",
        "validation.offline must be a list of at least 1",
        "validation.live must be a list of at least 0",
        "hidden_tests must be a non-empty list",
    ):
        assert fragment in errors


def test_check_reports_a_fixture_that_grades_differently(tmp_path: Path) -> None:
    root = tmp_path / "agent-evals"
    task_dir = root / "tasks" / TASK_ID
    task_dir.mkdir(parents=True)
    (task_dir / "task.json").write_text(json.dumps(_task()), encoding="utf-8")
    hidden = task_dir / "hidden"
    hidden.mkdir()
    for name in _task()["hidden_tests"]:
        (hidden / name).write_bytes((ae.EVALS / "tasks" / TASK_ID / "hidden" / name).read_bytes())
    fixture = task_dir / "fixtures" / "flipped"
    fixture.mkdir(parents=True)
    for name in ("patch.diff", "report.json", "results.json"):
        (fixture / name).write_bytes((FIXTURES / "reference" / name).read_bytes())
    (fixture / "expected.json").write_text('{"criteria": {}, "verdict": "fail"}', "utf-8")
    problems = ae.check(root)
    assert len(problems) == 1
    assert problems[0].startswith(f"{TASK_ID}/flipped: graded")

    (hidden / _task()["hidden_tests"][0]).unlink()
    assert ae.check(root) == [f"{TASK_ID}: hidden test {_task()['hidden_tests'][0]} is missing"]
    assert ae.check(tmp_path / "empty") == [f"no tasks under {tmp_path / 'empty' / 'tasks'}"]


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    return done.stdout.decode().strip()


def test_run_applies_the_patch_at_the_base_sha_and_records_exit_codes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "value.txt").write_text("old\n", encoding="utf-8")
    (repo / "test_value.py").write_text(
        "def test_value():\n    assert open('value.txt').read() == 'new\\n'\n", encoding="utf-8"
    )
    _git(repo, "add", "value.txt", "test_value.py")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")
    check = "python -m pytest -q -p no:cacheprovider test_value.py"
    task = dict(_task(), base_sha=base, hidden_tests=[])
    task["validation"] = {"offline": [check], "live": ["python -c 'raise SystemExit(3)'"]}
    patch = "\n".join(
        ["diff --git a/value.txt b/value.txt", "--- a/value.txt", "+++ b/value.txt"]
        + ["@@ -1 +1 @@", "-old", "+new", ""]
    )

    result = ae.run(task, patch, repo=repo)
    assert result["applied"] is True
    assert result["patch_sha256"] == hashlib.sha256(patch.encode()).hexdigest()
    assert result["commands"] == [
        {"command": check, "exit_code": 0, "kind": "offline", "outcome": "passed"}
    ]
    assert ae.run(task, patch, live=True, repo=repo)["commands"][-1]["exit_code"] == 3
    assert ae.run(task, "not a patch\n", repo=repo)["applied"] is False
    assert "agent-eval-" not in _git(repo, "worktree", "list")


def test_cli_grade_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ref = FIXTURES / "reference"
    args = ["grade", "--task", TASK_ID, "--patch", str(ref / "patch.diff")]
    args += ["--report", str(ref / "report.json")]
    assert ae.main([*args, "--results", str(ref / "results.json")]) == 0
    assert json.loads(capsys.readouterr().out)["verdict"] == "pass"
    assert ae.main(args) == 1
    assert ae.main([*args[:-1], str(tmp_path / "missing.json")]) == 2
    assert ae.main(["validate"]) == 0
    assert ae.main(["check"]) == 0


def test_cli_runs_as_a_script() -> None:
    done = subprocess.run(
        [sys.executable, str(ae.ROOT / "scripts" / "agent_eval.py"), "validate"],
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stderr
