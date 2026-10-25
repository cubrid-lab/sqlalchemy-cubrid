"""Makefile target semantics (#1009).

``make test`` is the complete offline suite, ``make check`` the complete non-test
quality gate, ``make verify`` those two and then the live ``make integration`` lane
(#1018), and only ``make format``
modifies files. ``make docker-down`` keeps the local test data and only
``make docker-clean`` deletes it (#1008). Most checks use ``make -n`` (print, do not run); the ``doctor`` and
``check-all`` checks run the targets with every tool replaced by ``true`` or
``false``, so nothing is installed, linted or modified.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")
TOOLS = ("PYTEST", "RUFF", "MYPY", "BANDIT", "PRE_COMMIT")


def _make(*args: str) -> subprocess.CompletedProcess[str]:
    make = shutil.which("make")
    if make is None:
        pytest.skip("make is required for Makefile regression tests")
    env = os.environ.copy()
    # Do not inherit outer make state or tool overrides.
    for key in (
        "MAKEFLAGS",
        "MFLAGS",
        "MAKEOVERRIDES",
        "PYTHON",
        "CUBRID_PORT",
        "CUBRID_TEST_PORT",
        *TOOLS,
    ):
        env.pop(key, None)
    return subprocess.run(
        [make, "--no-print-directory", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _dry_run(*targets: str) -> list[str]:
    result = _make("-n", *targets)
    assert result.returncode == 0, result.stderr
    return result.stdout.splitlines()


def _prerequisites(target: str) -> list[str]:
    match = re.search(rf"^{re.escape(target)}:([^#\n]*)", MAKEFILE, re.M)
    assert match, f"target {target!r} not found in Makefile"
    return match.group(1).split()


def test_tool_variables_are_overridable_and_use_the_interpreter():
    assert re.search(r"^PYTHON \?= python3$", MAKEFILE, re.M)
    for name, module in zip(TOOLS, ("pytest", "ruff", "mypy", "bandit", "pre_commit"), strict=True):
        assert re.search(rf"^{name} \?= \$\(PYTHON\) -m {module}$", MAKEFILE, re.M), name
    # No tool is looked up on PATH or bound with a plain `=`.
    assert not re.search(r"^(PYTHON|PYTEST|RUFF|MYPY|BANDIT|PRE_COMMIT) = ", MAKEFILE, re.M)


def test_integration_helpers_moved_out_of_the_makefile():
    for name in ("RUN_DETACHED", "RUN_IN_NEW_GROUP", "SIGNAL_AFTER", "WAIT_GROUP"):
        assert name not in MAKEFILE
    recipe = re.search(r"^integration:.*\n((?:\t.*\n)+)", MAKEFILE, re.M)
    assert recipe
    # One command (continuation lines included): the runner, exec'd by the shell.
    assert recipe.group(1).startswith("\t@exec $(PYTHON) scripts/run_integration.py ")
    assert recipe.group(1).count("\n") == recipe.group(1).count("\\\n") + 1
    for option in ("driver", "port", "project", "ready-timeout", "stop-grace", "wait", "test"):
        assert f"--{option}=" in recipe.group(1)


@pytest.mark.parametrize("target", ["lint", "format-check"])
def test_lint_and_format_check_never_modify_files(target):
    lines = _dry_run(target, "LINT_PATHS=x.py")
    assert lines[0] == "python3 scripts/check_tool_versions.py"
    expected = {
        "lint": "python3 -m ruff check x.py",
        "format-check": "python3 -m ruff format --check x.py",
    }
    assert lines[1:] == [expected[target]]


def test_format_is_the_mutating_target_and_checks_tool_versions():
    assert _dry_run("format", "LINT_PATHS=x.py") == [
        "python3 scripts/check_tool_versions.py",
        "python3 -m ruff check --fix x.py",
        "python3 -m ruff format x.py",
    ]


def test_check_is_the_complete_non_test_quality_gate():
    assert _prerequisites("check") == [
        "lint",
        "format-check",
        "typecheck",
        "security",
        "check-docs-reason",
    ]
    lines = _dry_run("check")
    assert not any("pytest" in line or "docker" in line for line in lines)


def test_verify_runs_check_then_test_then_the_live_lane():
    # Sub-makes, not prerequisites, so `make -j` cannot start a later phase early.
    assert _prerequisites("verify") == []
    # Pin the driver so an exported INTEGRATION_DRIVER=cubriddb cannot change the default.
    lines = _dry_run("verify", "INTEGRATION_DRIVER=pycubrid")
    offline = next(i for i, line in enumerate(lines) if '-m "not integration"' in line)
    live = next(i for i, line in enumerate(lines) if "scripts/run_integration.py" in line)
    static = max(i for i, line in enumerate(lines) if "bandit" in line or " -m ruff " in line)
    assert static < offline < live
    assert '--driver="pycubrid"' in "\n".join(lines[live:])


def test_test_stays_offline():
    lines = _dry_run("test")
    assert not any("docker" in line or "run_integration" in line for line in lines)


@pytest.mark.parametrize("jobs", [[], ["-j3"]], ids=["serial", "parallel"])
def test_verify_never_starts_the_live_lane_after_failing_offline_tests(tmp_path, jobs):
    log = tmp_path / "python.log"
    stub = tmp_path / "python"
    # Logs every call; the offline pytest run fails, everything else succeeds.
    stub.write_text(
        f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{log}"\n'
        'case " $* " in *" -m pytest "*"not integration"*) exit 1 ;; esac\nexit 0\n'
    )
    stub.chmod(0o755)
    # Keep the real recipes' result directories inside tmp_path.
    results = [f"TEST_RESULTS={tmp_path}/test", f"INTEGRATION_RESULTS={tmp_path}/integration"]
    result = _make(*jobs, "verify", f"PYTHON={stub}", *results)
    assert result.returncode != 0
    calls = log.read_text().splitlines()
    assert any("-m pytest" in call for call in calls)
    assert not any("scripts/run_integration.py" in call for call in calls)


@pytest.mark.parametrize("target", ["clean", "clean-all"])
def test_clean_never_removes_docker_or_cubrid_data(target):
    lines = _dry_run(target)
    assert lines
    assert not any("docker" in line or "cubrid" in line.lower() for line in lines)


def test_docker_down_keeps_the_test_data_volumes():
    assert _dry_run("docker-down") == ["docker compose down"]


def test_docker_clean_is_the_only_target_that_deletes_test_data_volumes():
    assert _dry_run("docker-clean") == ["docker compose down -v"]
    documented = re.findall(r"^([a-zA-Z_-]+):.*?## ", MAKEFILE, re.M)
    deleting = [target for target in documented if "down -v" in "\n".join(_dry_run(target))]
    # make integration removes only its own run-owned project, in the runner.
    assert deleting == ["docker-clean"]


@pytest.mark.parametrize(
    ("args", "port"),
    [
        # No port given: Compose resolves it (.env, then its 33000 default).
        ((), None),
        (("CUBRID_TEST_PORT=33300",), "33300"),
        # The deprecated pre-#1008 name, used only when CUBRID_TEST_PORT is unset.
        (("CUBRID_PORT=33301",), "33301"),
        (("CUBRID_PORT=33301", "CUBRID_TEST_PORT=33300"), "33300"),
    ],
)
def test_docker_up_passes_the_broker_port_to_compose(args, port):
    result = _make("-n", "docker-up", *args)
    assert result.returncode == 0, result.stderr
    prefix = "" if port is None else f'CUBRID_TEST_PORT="{port}" '
    assert result.stdout.splitlines()[0] == f"{prefix}docker compose up -d"
    deprecated = "CUBRID_PORT is deprecated; use CUBRID_TEST_PORT" in result.stderr
    assert deprecated == (args == ("CUBRID_PORT=33301",))


def test_docker_up_leaves_an_env_file_port_to_compose():
    # A port set only in Compose's .env must not be overridden by the Make default.
    result = _make("-n", "docker-up")
    assert result.returncode == 0, result.stderr
    assert "CUBRID_TEST_PORT=" not in result.stdout.splitlines()[0]
    compose = (ROOT / "docker-compose.yml").read_text()
    assert "${CUBRID_TEST_PORT:-${CUBRID_PORT:-33000}}" in compose


@pytest.mark.parametrize("target", ["docker-down", "docker-clean", "check", "test", "help"])
def test_deprecated_port_warning_is_limited_to_targets_that_use_the_port(target):
    # Other CUBRID tools export CUBRID_PORT as a client setting; it must not make
    # every target warn (#1008).
    result = _make("-n", target, "CUBRID_PORT=33301")
    assert result.returncode == 0, result.stderr
    assert "deprecated" not in result.stderr


def test_check_all_is_a_deprecated_alias_of_check():
    assert _prerequisites("check-all") == ["check"]
    stubs = [f"{name}=true" for name in ("PYTHON", *TOOLS)]
    result = _make("check-all", *stubs)
    assert result.returncode == 0, result.stderr
    assert "'make check-all' is deprecated" in result.stderr
    assert "deprecated" not in result.stdout


def test_doctor_passes_when_every_tool_answers():
    result = _make("doctor", *(f"{name}=true" for name in ("PYTHON", *TOOLS)))
    assert result.returncode == 0, result.stderr
    assert "All checks passed!" in result.stdout


@pytest.mark.parametrize("broken", ["PYTHON", *TOOLS])
def test_doctor_fails_closed_for_a_missing_or_invalid_tool(broken):
    stubs = [f"{name}={'false' if name == broken else 'true'}" for name in ("PYTHON", *TOOLS)]
    result = _make("doctor", *stubs)
    assert result.returncode != 0
    assert "All checks passed!" not in result.stdout + result.stderr
    assert "ERROR: required tooling is missing or invalid" in result.stderr


def test_doctor_fails_for_a_tool_that_is_not_installed():
    result = _make("doctor", "RUFF=/nonexistent/ruff")
    assert result.returncode != 0
    assert "All checks passed!" not in result.stdout + result.stderr


def test_help_groups_targets_by_purpose():
    result = _make("help")
    assert result.returncode == 0, result.stderr
    text = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    sections = re.findall(r"^(\S.*)$", text, re.M)
    assert sections == [
        "Setup",
        "Quality (static checks; only format modifies files)",
        "Tests (offline; no Docker, no database)",
        "Integration (Docker)",
        "Maintenance",
    ]
    documented = re.findall(r"^([a-zA-Z_-]+):.*?## ", MAKEFILE, re.M)
    listed = re.findall(r"^  (\S+)\s", text, re.M)
    assert listed == documented


def test_ci_calls_only_canonical_targets():
    # Deprecated aliases are kept for contributors, never for CI (#1009).
    targets = set(re.findall(r"^([a-zA-Z_-]+):", MAKEFILE, re.M))
    deprecated = {"check-all", "test-offline"}
    calls = []
    for workflow in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        for job in yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"].values():
            for step in job.get("steps", []):
                calls += re.findall(
                    r"(?:^\s*|[;&|]\s*)make ([a-z][a-z-]*)", step.get("run", ""), re.M
                )
    assert calls
    assert set(calls) <= targets - deprecated


def test_test_writes_junit_coverage_and_summary_under_test_results():
    # #1019: one pytest run keeps its selection and the 95% floor and reports to
    # test-results/test/, then the helper writes summary.json and sets the status.
    text = "\n".join(_dry_run("test"))
    assert '-m "not integration"' in text
    assert "--cov-fail-under=95" in text
    assert '--junitxml="test-results/test/junit.xml"' in text
    assert '--cov-report=xml:"test-results/test/coverage.xml"' in text
    assert "-m scripts.report_test_results" in text
    assert '--output "test-results/test/summary.json"' in text
    assert text.count("-m pytest") == 1


def test_test_results_are_gitignored_and_removed_by_clean():
    assert "test-results/" in (ROOT / ".gitignore").read_text().splitlines()
    assert "test-results/" in " ".join(_dry_run("clean"))


def test_test_keeps_pytest_failure_status_and_records_fail(tmp_path):
    # Stub pytest as a failing command that writes no files: the recipe must still
    # report (INCOMPLETE data -> FAIL because pytest failed) and exit non-zero.
    result = _make("test", "PYTEST=false", f"TEST_RESULTS={tmp_path / 'r'}")
    assert result.returncode != 0
    summary = json.loads((tmp_path / "r" / "summary.json").read_text())
    assert summary["status"] == "FAIL"
    assert summary["pytest_exit_code"] == 1
    assert "test: FAIL" in result.stdout


def test_test_quotes_every_results_path_in_the_recipe():
    text = "\n".join(_dry_run("test", "TEST_RESULTS=a b"))
    assert 'rm -rf -- "a b"' in text
    assert '--junitxml="a b/junit.xml"' in text
    assert '--output "a b/summary.json"' in text


@pytest.mark.parametrize("bad", ["", ".", "./", "..", "/"])
def test_test_refuses_a_results_dir_that_could_delete_more_than_its_own(bad):
    result = _make("test", f"TEST_RESULTS={bad}", "PYTEST=false")
    assert result.returncode != 0
    assert "refusing to use TEST_RESULTS" in result.stderr
    assert (ROOT / "Makefile").exists()
    assert (ROOT / "test").is_dir()


def test_test_results_dir_with_spaces_deletes_only_itself(tmp_path):
    sibling = tmp_path / "my"
    sibling.mkdir()
    (sibling / "keep.txt").write_text("x")
    target = tmp_path / "my results"
    result = _make("test", "PYTEST=false", f"TEST_RESULTS={target}")
    assert result.returncode != 0
    assert (sibling / "keep.txt").exists()
    assert json.loads((target / "summary.json").read_text())["status"] == "FAIL"
