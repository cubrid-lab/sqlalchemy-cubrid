# test/test_report_test_results.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Offline tests for ``scripts/report_test_results.py`` (#1019)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from scripts import report_test_results as mod

JUNIT_HEAD = '<?xml version="1.0"?><testsuites><testsuite name="pytest">'
JUNIT_TAIL = "</testsuite></testsuites>"

PASSING = '<testcase classname="t" name="a"/><testcase classname="t" name="b"/>'
SKIPPED = '<testcase classname="t" name="s"><skipped type="pytest.skip" message="x"/></testcase>'
XFAILED = '<testcase classname="t" name="x"><skipped type="pytest.xfail" message="r"/></testcase>'
XPASSED = (
    '<testcase classname="t" name="xp"><failure message="[XPASS(strict)] r">t</failure></testcase>'
)
FAILED = '<testcase classname="t" name="f"><failure message="assert 0">t</failure></testcase>'
ERRORED = '<testcase classname="t" name="e"><error message="boom">t</error></testcase>'


def _junit(tmp_path: Path, *cases: str) -> Path:
    path = tmp_path / "junit.xml"
    path.write_text(JUNIT_HEAD + "".join(cases) + JUNIT_TAIL, encoding="utf-8")
    return path


def _coverage(tmp_path: Path, rate: float) -> Path:
    path = tmp_path / "coverage.xml"
    path.write_text(f'<?xml version="1.0"?><coverage line-rate="{rate}"/>', encoding="utf-8")
    return path


def _summary(tmp_path: Path, junit: Path | None, coverage: Path | None, exit_code: int = 0):
    return mod.build_summary(
        lane="test",
        junit=junit or tmp_path / "missing-junit.xml",
        coverage=coverage,
        threshold=95,
        pytest_exit=exit_code,
    )


def test_parse_junit_counts_every_outcome(tmp_path):
    path = _junit(tmp_path, PASSING, SKIPPED, XFAILED, XPASSED, FAILED, ERRORED)
    assert mod.parse_junit(path) == {
        "selected": 7,
        "passed": 2,
        "failed": 1,
        "errors": 1,
        "skipped": 1,
        "xfailed": 1,
        "xpassed": 1,
    }


def test_pass_with_skips(tmp_path):
    summary = _summary(tmp_path, _junit(tmp_path, PASSING, SKIPPED), _coverage(tmp_path, 0.9712))
    assert summary["status"] == "PASS"
    assert summary["schema_version"] == 1
    assert summary["counts"]["skipped"] == 1
    assert summary["coverage"] == {"percent": 97.12, "threshold": 95, "threshold_met": True}
    assert summary["problems"] == []


@pytest.mark.parametrize("bad", [FAILED, ERRORED, XPASSED])
def test_failing_tests_are_fail_even_if_pytest_exit_is_zero(tmp_path, bad):
    summary = _summary(tmp_path, _junit(tmp_path, PASSING, bad), _coverage(tmp_path, 0.99))
    assert summary["status"] == "FAIL"


def test_nonzero_pytest_exit_is_fail(tmp_path):
    summary = _summary(tmp_path, _junit(tmp_path, PASSING), _coverage(tmp_path, 0.99), 1)
    assert summary["status"] == "FAIL"


def test_nonzero_pytest_exit_without_files_is_fail(tmp_path):
    summary = _summary(tmp_path, None, None, 2)
    assert summary["status"] == "FAIL"
    assert summary["counts"] is None
    assert summary["problems"]


def test_coverage_below_threshold_is_fail(tmp_path):
    summary = _summary(tmp_path, _junit(tmp_path, PASSING), _coverage(tmp_path, 0.9499))
    assert summary["status"] == "FAIL"
    assert summary["coverage"]["threshold_met"] is False


def test_missing_junit_is_incomplete(tmp_path):
    summary = _summary(tmp_path, None, _coverage(tmp_path, 0.99))
    assert summary["status"] == "INCOMPLETE"
    assert "JUnit" in summary["problems"][0]


def test_malformed_junit_is_incomplete(tmp_path):
    path = tmp_path / "junit.xml"
    path.write_text("<testsuite", encoding="utf-8")
    assert _summary(tmp_path, path, _coverage(tmp_path, 0.99))["status"] == "INCOMPLETE"


def test_missing_coverage_is_incomplete(tmp_path):
    summary = _summary(tmp_path, _junit(tmp_path, PASSING), tmp_path / "nope.xml")
    assert summary["status"] == "INCOMPLETE"
    assert summary["coverage"]["percent"] is None
    assert "coverage" in summary["problems"][0]


def test_zero_test_cases_is_incomplete(tmp_path):
    summary = _summary(tmp_path, _junit(tmp_path), _coverage(tmp_path, 0.99))
    assert summary["status"] == "INCOMPLETE"


def test_coverage_is_optional_for_other_lanes(tmp_path):
    summary = mod.build_summary(
        lane="live",
        junit=_junit(tmp_path, PASSING),
        coverage=None,
        threshold=None,
        pytest_exit=0,
    )
    assert summary["status"] == "PASS"
    assert summary["coverage"] == {"percent": None, "threshold": None, "threshold_met": None}
    assert "coverage" not in mod.format_line(summary)


def test_main_writes_summary_and_prints_a_matching_line(tmp_path, capsys):
    out = tmp_path / "out" / "summary.json"
    code = mod.main(
        [
            "--lane", "test",
            "--junit", str(_junit(tmp_path, PASSING, SKIPPED, XFAILED)),
            "--coverage", str(_coverage(tmp_path, 0.96)),
            "--threshold", "95",
            "--pytest-exit", "0",
            "--output", str(out),
        ]
    )  # fmt: skip
    assert code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    line = capsys.readouterr().out
    assert data["status"] == "PASS"
    assert line.startswith(
        "test: PASS; 4 selected, 2 passed, 0 failed, 0 errors, 1 skipped, 1 xfailed"
    )
    assert "coverage 96.00% (threshold 95% met)" in line
    assert str(out) in line


def test_main_exits_nonzero_and_records_fail(tmp_path, capsys):
    out = tmp_path / "summary.json"
    code = mod.main(
        [
            "--lane", "test",
            "--junit", str(_junit(tmp_path, PASSING, FAILED)),
            "--coverage", str(_coverage(tmp_path, 0.99)),
            "--threshold", "95",
            "--pytest-exit", "1",
            "--output", str(out),
        ]
    )  # fmt: skip
    assert code == 1
    assert json.loads(out.read_text(encoding="utf-8"))["status"] == "FAIL"
    assert "test: FAIL" in capsys.readouterr().out


def test_call_and_teardown_failures_of_one_test_are_selected_once(tmp_path):
    # pytest writes one <testcase> per failing phase for the same test.
    call = '<testcase classname="t" name="both"><failure message="assert 0">t</failure></testcase>'
    teardown = '<testcase classname="t" name="both"><error message="teardown">t</error></testcase>'
    counts = mod.parse_junit(_junit(tmp_path, PASSING, call, teardown))
    assert counts["selected"] == 3
    assert counts["passed"] == 2
    assert (counts["failed"], counts["errors"]) == (1, 1)


def test_teardown_error_after_a_pass_is_not_also_a_pass(tmp_path):
    ok = '<testcase classname="t" name="x"/>'
    teardown = '<testcase classname="t" name="x"><error message="teardown">t</error></testcase>'
    counts = mod.parse_junit(_junit(tmp_path, ok, teardown))
    assert counts == {
        "selected": 1,
        "passed": 0,
        "failed": 0,
        "errors": 1,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
    }


def test_threshold_without_coverage_is_incomplete(tmp_path, capsys):
    summary = mod.build_summary(
        lane="test",
        junit=_junit(tmp_path, PASSING),
        coverage=None,
        threshold=95,
        pytest_exit=0,
    )
    assert summary["status"] == "INCOMPLETE"
    assert "without a coverage file" in summary["problems"][0]
    code = mod.main(
        ["--lane", "test", "--junit", str(tmp_path / "junit.xml"), "--threshold", "95"]
        + ["--pytest-exit", "0", "--output", str(tmp_path / "s.json")]
    )
    assert code == 1
    assert "INCOMPLETE" in capsys.readouterr().out


def _write_summary(tmp_path, pytest_exit=0, junit_cases=(PASSING,)):
    out = tmp_path / "summary.json"
    mod.main(
        [
            "--lane", "offline",
            "--junit", str(_junit(tmp_path, *junit_cases)),
            "--coverage", str(_coverage(tmp_path, 0.96)),
            "--threshold", "95",
            "--pytest-exit", str(pytest_exit),
            "--output", str(out),
        ]
    )  # fmt: skip
    return out


def test_step_summary_renders_the_console_line_as_markdown(tmp_path, capsys):
    out = _write_summary(tmp_path)
    capsys.readouterr()
    code = mod.main(["step-summary", "--summary", str(out), "--title", "Unit tests (Python 3.12)"])
    assert code == 0
    text = capsys.readouterr().out
    summary = json.loads(out.read_text(encoding="utf-8"))
    assert text == f"### Unit tests (Python 3.12)\n\n`{mod.format_line(summary)}`\n"
    assert "offline: PASS" in text


def test_step_summary_shows_a_failing_lane_and_still_exits_zero(tmp_path, capsys):
    out = _write_summary(tmp_path, pytest_exit=1, junit_cases=(PASSING, FAILED))
    capsys.readouterr()
    assert mod.main(["step-summary", "--summary", str(out)]) == 0
    text = capsys.readouterr().out
    assert text.startswith("### Test results\n\n`offline: FAIL;")


@pytest.mark.parametrize("content", [None, "not json", "[]", '{"lane": "x"}'])
def test_step_summary_reports_a_missing_or_unreadable_summary(tmp_path, capsys, content):
    path = tmp_path / "summary.json"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    assert mod.main(["step-summary", "--summary", str(path), "--title", "T"]) == 0
    text = capsys.readouterr().out
    assert text == f"### T\n\nNo readable `{path}` was written (the run stopped early).\n"


def test_require_executed_makes_an_all_skipped_run_incomplete(tmp_path):
    kwargs = {"lane": "integration", "coverage": None, "threshold": None, "pytest_exit": 0}
    skipped = mod.build_summary(junit=_junit(tmp_path, SKIPPED), require_executed=True, **kwargs)
    assert skipped["status"] == "INCOMPLETE"
    assert skipped["executed"] is False
    ran = mod.build_summary(
        junit=_junit(tmp_path, SKIPPED, XFAILED), require_executed=True, **kwargs
    )
    assert ran["status"] == "PASS"
    assert ran["executed"] is True
    # Without the flag, an all-skipped run keeps its previous meaning.
    assert mod.build_summary(junit=_junit(tmp_path, SKIPPED), **kwargs)["status"] == "PASS"


def test_reason_is_recorded_and_stops_a_pass(tmp_path):
    summary = mod.build_summary(
        lane="integration",
        junit=_junit(tmp_path, PASSING),
        coverage=None,
        threshold=None,
        pytest_exit=0,
        reason="why",
    )
    assert summary["status"] == "INCOMPLETE"
    assert summary["problems"] == ["why"]


def test_environment_records_versions_and_no_credential(tmp_path, monkeypatch):
    monkeypatch.setenv("CUBRID_PASSWORD", "topsecret")
    monkeypatch.setenv("CUBRID_TEST_URL", "cubrid+pycubrid://dba:topsecret@localhost/testdb")
    output = tmp_path / "out" / "environment.json"
    code = mod.main(
        [
            "environment",
            "--lane", "integration",
            "--command", "make integration",
            "--cubrid-version", "11.2",
            "--driver", "pycubrid",
            "--output", str(output),
        ]
    )  # fmt: skip
    assert code == 0
    text = output.read_text(encoding="utf-8")
    assert "topsecret" not in text
    document = json.loads(text)
    assert document["cubrid_version"] == "11.2"
    assert document["driver"]["name"] == "pycubrid"
    assert document["sqlalchemy"]
    assert document["python"] and document["platform"]


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("CUBRID_PASSWORD=topsecret make integration", "CUBRID_PASSWORD=*** make integration"),
        ("make integration API_TOKEN='a b' X=1", "make integration API_TOKEN=*** X=1"),
        ('DB_SECRET="s s" make x', "DB_SECRET=*** make x"),
        (
            "make it CUBRID_TEST_URL=cubrid+pycubrid://dba:p%40ss@localhost/db",
            "make it CUBRID_TEST_URL=cubrid+pycubrid://dba:***@localhost/db",
        ),
        (
            "make integration INTEGRATION_DRIVER=pycubrid",
            "make integration INTEGRATION_DRIVER=pycubrid",
        ),
    ],
)
def test_environment_redacts_credentials_in_the_command(tmp_path, command, expected):
    output = tmp_path / "environment.json"
    mod.main(
        ["environment", "--lane", "l", "--command", command, "--cubrid-version", "11.2",
         "--driver", "pycubrid", "--output", str(output)]
    )  # fmt: skip
    assert json.loads(output.read_text("utf-8"))["command"] == expected


def _lane(tmp_path: Path, name: str, status: str) -> Path:
    path = tmp_path / name / "summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"lane": name, "status": status}), encoding="utf-8")
    return path


def _statuses(summary):
    return {phase["name"]: phase["status"] for phase in summary["phases"]}


def test_aggregate_passes_only_when_every_phase_passed(tmp_path):
    summary = mod.build_aggregate(
        [
            ("check", 0, None),
            ("test", 0, _lane(tmp_path, "test", "PASS")),
            ("integration", 0, _lane(tmp_path, "integration", "PASS")),
        ]
    )
    assert summary["status"] == "PASS"
    assert summary["problems"] == []
    assert [phase["name"] for phase in summary["phases"]] == ["check", "test", "integration"]


@pytest.mark.parametrize(
    ("live", "expected", "phase"),
    [
        # The lane's own verdict wins over a zero exit status.
        ((0, "INCOMPLETE"), "INCOMPLETE", "INCOMPLETE"),
        ((0, "FAIL"), "FAIL", "FAIL"),
        # A non-zero exit status is a failure even next to a stale PASS summary.
        ((1, "PASS"), "FAIL", "FAIL"),
    ],
)
def test_aggregate_takes_the_worst_lane_verdict(tmp_path, live, expected, phase):
    exit_code, status = live
    summary = mod.build_aggregate(
        [("test", 0, _lane(tmp_path, "test", "PASS")),
         ("integration", exit_code, _lane(tmp_path, "integration", status))]
    )  # fmt: skip
    assert summary["status"] == expected
    assert _statuses(summary)["integration"] == phase


def test_aggregate_never_passes_a_phase_that_did_not_run(tmp_path):
    summary = mod.build_aggregate(
        [("check", 0, None), ("test", 0, _lane(tmp_path, "test", "PASS")),
         ("integration", None, tmp_path / "integration" / "summary.json")]
    )  # fmt: skip
    assert summary["status"] == "INCOMPLETE"
    assert _statuses(summary)["integration"] == "NOT_RUN"
    assert "integration did not run" in summary["problems"]


@pytest.mark.parametrize(
    "content",
    [None, "not json", '{"status": "GREEN"}', '{"status": []}', '{"status": {}}', "[]"],
)
def test_aggregate_treats_a_missing_or_unreadable_lane_summary_as_incomplete(tmp_path, content):
    path = tmp_path / "integration" / "summary.json"
    if content is not None:
        path.parent.mkdir(parents=True)
        path.write_text(content, encoding="utf-8")
    summary = mod.build_aggregate([("integration", 0, path)])
    assert summary["status"] == "INCOMPLETE"
    assert summary["problems"]


def test_aggregate_main_writes_the_summary_junit_and_environment(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("CUBRID_PASSWORD", "topsecret")
    lanes = tmp_path / "lanes"
    test_summary = _lane(lanes, "test", "PASS")
    live_summary = _lane(lanes, "integration", "PASS")
    # A failing offline test can print a configured credential into its JUnit report.
    (lanes / "test" / "junit.xml").write_text(
        "<testsuites>topsecret</testsuites>", encoding="utf-8"
    )
    (lanes / "integration" / "junit.xml").write_text("<testsuites/>", encoding="utf-8")
    (lanes / "integration" / "environment.json").write_text('{"lane": "x"}', encoding="utf-8")
    output = tmp_path / "verify" / "summary.json"
    code = mod.main(
        [
            "aggregate", "--output", str(output),
            "--phase", "check=0",
            "--phase", f"test=0:{test_summary}",
            "--phase", f"integration=0:{live_summary}",
            "--copy-junit", f"test={lanes / 'test' / 'junit.xml'}",
            "--copy-junit", f"integration={lanes / 'integration' / 'junit.xml'}",
            "--copy-junit", f"missing={lanes / 'missing.xml'}",
            "--environment", str(lanes / "integration" / "environment.json"),
        ]
    )  # fmt: skip
    assert code == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    verify = output.parent
    assert sorted(p.name for p in (verify / "junit").iterdir()) == ["integration.xml", "test.xml"]
    assert (verify / "environment.json").read_text(encoding="utf-8") == '{"lane": "x"}'
    # No credential from the environment reaches any verify result file.
    for path in verify.rglob("*"):
        if path.is_file():
            assert "topsecret" not in path.read_text(encoding="utf-8")
    line = capsys.readouterr().out
    assert line.startswith("verify: PASS; check PASS, test PASS, integration PASS -> ")


def test_aggregate_main_exits_nonzero_unless_pass(tmp_path, capsys):
    output = tmp_path / "summary.json"
    assert mod.main(["aggregate", "--output", str(output), "--phase", "check=2"]) == 1
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "FAIL"
    assert "verify: FAIL; check FAIL" in capsys.readouterr().out


def test_aggregate_rejects_a_malformed_phase(tmp_path):
    with pytest.raises(SystemExit):
        mod.main(["aggregate", "--output", str(tmp_path / "s.json"), "--phase", "check=ok"])


def test_step_summary_renders_the_verify_summary(tmp_path, capsys):
    output = tmp_path / "summary.json"
    mod.main(["aggregate", "--output", str(output), "--phase", "check=0",
              "--phase", "integration=not-run"])  # fmt: skip
    capsys.readouterr()
    assert mod.main(["step-summary", "--summary", str(output), "--title", "Verify"]) == 0
    text = capsys.readouterr().out
    assert text.startswith("### Verify\n\n`verify: INCOMPLETE; check PASS, integration NOT_RUN")


def test_aggregate_records_a_result_file_it_cannot_copy(tmp_path, capsys):
    lane = _lane(tmp_path, "integration", "PASS")
    unreadable = tmp_path / "integration" / "junit.xml"
    unreadable.mkdir()  # exists, but reading it fails
    output = tmp_path / "verify" / "summary.json"
    code = mod.main(
        ["aggregate", "--output", str(output), "--phase", f"integration=0:{lane}",
         "--copy-junit", f"integration={unreadable}"]
    )  # fmt: skip
    assert code == 1
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["status"] == "INCOMPLETE"
    assert _statuses(summary) == {"integration": "PASS"}
    assert any("could not copy" in problem for problem in summary["problems"])
    assert not (output.parent / "junit" / "integration.xml").exists()


def test_configured_secrets_match_the_live_runner(monkeypatch):
    from scripts import run_integration

    monkeypatch.setenv("CUBRID_PASSWORD", "p&ss")
    monkeypatch.setenv("CUBRID_TEST_URL", "cubrid+pycubrid://dba:w%40rd@localhost/testdb")
    monkeypatch.delenv("CUBRID_TEST_AURL", raising=False)
    monkeypatch.delenv("CUBRID_URL", raising=False)
    assert mod.configured_secrets(os.environ) == run_integration._secrets()
