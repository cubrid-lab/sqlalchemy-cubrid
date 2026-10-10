"""Exercise aggregate gates for selected, skipped and cancelled validation."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.name
pytestmark = pytest.mark.repo


def workflow(name: str) -> dict:
    return yaml.safe_load((ROOT / ".github/workflows" / name).read_text())


def gate() -> dict:
    return workflow("ci.yml")["jobs"]["matrix-result"]


def run_gate(selected: set[str], results: dict[str, str]) -> subprocess.CompletedProcess:
    step = gate()["steps"][0]
    env = dict(os.environ)
    for job in gate()["needs"]:
        key = job.upper().replace("-", "_")
        env[f"R_{key}"] = results.get(job, "success" if job in selected else "skipped")
        env[f"E_{key}"] = "true" if job in selected else "false"
    return subprocess.run(
        ["bash", "-eo", "pipefail", "-c", step["run"]],
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )


@pytest.mark.parametrize("result", ["failure", "cancelled", "skipped"])
@pytest.mark.parametrize("job", gate()["needs"])
def test_every_selected_job_must_succeed(job: str, result: str) -> None:
    completed = run_gate(set(gate()["needs"]), {job: result})
    assert completed.returncode != 0
    assert result in completed.stdout


def test_docs_only_intentional_skips_pass() -> None:
    completed = run_gate({"detect-changes", "lint", "doc-lint"}, {})
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.parametrize("result", ["failure", "cancelled"])
def test_even_unselected_job_failure_is_not_hidden(result: str) -> None:
    completed = run_gate({"detect-changes", "lint"}, {"integration-tests": result})
    assert completed.returncode != 0


def test_ordinary_code_smoke_without_live_jobs_passes() -> None:
    selected = {"detect-changes", "lint", "offline-tests", "typecheck"}
    if REPO == "pycubrid":
        selected.add("compat-check")
    assert run_gate(selected, {}).returncode == 0


def test_full_release_call_is_preserved_without_automatic_schedule() -> None:
    full = workflow("integration-full.yml")
    events = full.get("on", full.get(True))
    assert set(events) == {"workflow_dispatch", "workflow_call"}
    assert events["workflow_call"]["inputs"]["sha"]["required"] is True
    matrix = full["jobs"]["integration-full"]["strategy"]["matrix"]
    assert matrix["python-version"] == ["3.11", "3.12", "3.13", "3.14"]
    assert len(matrix["cubrid-version"]) == 4


def test_oldest_cells_use_python_311_and_keep_the_sqlalchemy_20_line() -> None:
    ci = workflow("ci.yml")["jobs"]
    alembic = next(s for s in ci["alembic-compat"]["steps"] if "setup-python" in s.get("uses", ""))
    assert alembic["with"]["python-version"] == "3.11"
    cells = ci["integration-tests"]["strategy"]["matrix"]
    assert (
        '{"python-version":"3.11","cubrid-version":"10.2",'
        '"pycubrid-compliance-sqlalchemy":"2.0.53"}' in cells
    )
    assert '"3.10"' not in cells
    # Python 3.11 resolves SQLAlchemy 2.1 by itself; the oldest cell and the
    # oldest full-matrix row must pin the minimum supported 2.0 line.
    pins = {
        "ci.yml": (
            ci["integration-tests"],
            "matrix.python-version == '3.11' && matrix.cubrid-version == '10.2'",
        ),
        "integration-full.yml": (
            workflow("integration-full.yml")["jobs"]["integration-full"],
            "matrix.python-version == '3.11'",
        ),
    }
    for name, (job, condition) in pins.items():
        names = [s.get("name", "") for s in job["steps"]]
        pin = next(s for s in job["steps"] if s.get("name", "").startswith("Pin the minimum"))
        assert pin["if"] == condition, name
        install, *log = pin["run"].strip().splitlines()
        assert install == 'uv pip install --system "sqlalchemy[asyncio]>=2.0,<2.1"', name
        assert log == ["uv pip freeze --system | grep -i '^sqlalchemy=='"], name
        assert names.index(pin["name"]) == names.index("Install project") + 1, name


OFFLINE_MATRIX = re.compile(
    r"^\$\{\{ fromJSON\(github\.event_name == 'pull_request' && '(?P<pr>\[.*?\])'"
    r" \|\| '(?P<other>\[.*?\])'\) \}\}$"
)


def offline_cells(event: str) -> list[str]:
    """Render the offline-tests matrix expression for one ``github.event_name``."""
    expression = workflow("ci.yml")["jobs"]["offline-tests"]["strategy"]["matrix"]
    match = OFFLINE_MATRIX.fullmatch(expression["python-version"])
    assert match, expression
    return json.loads(match["pr" if event == "pull_request" else "other"])


def test_ci_triggers_route_through_offline_cell_selection() -> None:
    ci = workflow("ci.yml")
    events = ci.get("on", ci.get(True))
    assert set(events) == {"pull_request", "push", "schedule", "workflow_dispatch"}
    assert events["push"]["branches"] == ["main"]


@pytest.mark.parametrize(
    ("event", "cells"),
    [
        # Ordinary and high-risk PRs keep one representative interpreter (#742).
        ("pull_request", ["3.12"]),
        # Main pushes, the weekly schedule and manual dispatches run the oldest
        # and newest supported Python (#734).
        ("push", ["3.11", "3.14"]),
        ("schedule", ["3.11", "3.14"]),
        ("workflow_dispatch", ["3.11", "3.14"]),
    ],
)
def test_offline_cells_are_selected_by_event(event: str, cells: list[str]) -> None:
    assert offline_cells(event) == cells


def test_offline_endpoints_match_the_supported_python_range() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert project["requires-python"] == ">=3.11"
    supported = sorted(
        (
            c.rsplit(" :: ", 1)[1]
            for c in project["classifiers"]
            if re.fullmatch(r"Programming Language :: Python :: 3\.\d+", c)
        ),
        key=lambda v: tuple(map(int, v.split("."))),
    )
    assert offline_cells("push") == [supported[0], supported[-1]] == ["3.11", "3.14"]
    full = workflow("integration-full.yml")["jobs"]["integration-full"]["strategy"]["matrix"]
    assert full["python-version"] == supported


def test_full_offline_suite_runs_on_every_event_in_linux_lanes() -> None:
    jobs = workflow("ci.yml")["jobs"]
    offline = jobs["offline-tests"]
    assert offline["if"] == "needs.detect-changes.outputs.code == 'true'"
    assert offline["strategy"]["fail-fast"] is False
    assert offline["runs-on"] == "ubuntu-latest"
    assert offline["timeout-minutes"] == 15
    assert set(offline["strategy"]["matrix"]) == {"python-version"}
    steps = offline["steps"]
    names = [s.get("name") for s in steps]
    assert "Run representative PR smoke tests" not in names
    # No step may run only on (or skip on) pull requests, whatever its name.
    assert not [s.get("name") for s in steps if "pull_request" in str(s.get("if", ""))]
    setups = [
        s for s in steps if "setup-python" in s.get("uses", "") or "setup-uv" in s.get("uses", "")
    ]
    assert len(setups) == 2
    assert all(s["with"]["python-version"] == "${{ matrix.python-version }}" for s in setups)
    coverage = next(s for s in steps if s.get("name") == "Run offline tests with coverage")
    upload = next(s for s in steps if s.get("name") == "Upload coverage")
    # PRs run the same full selection and coverage floor as pushes (#742).
    # No event filter on either step; the upload may only widen to always().
    assert "if" not in coverage and upload.get("if", "always()") == "always()"
    assert "test/" in coverage["run"].split()
    assert '-m "not integration and not repo"' in coverage["run"]
    assert "--cov-fail-under=95" in coverage["run"]
    # One artifact per interpreter so the endpoint cells do not collide (#734).
    assert upload["with"]["name"] == "coverage-report-py${{ matrix.python-version }}"
    # The dotfile must actually upload, and a missing file must fail the job.
    assert upload["with"]["path"] == ".coverage"
    assert upload["with"]["include-hidden-files"] is True
    assert upload["with"]["if-no-files-found"] == "error"
    assert "outputs.live" in jobs["integration-tests"]["if"]
    assert "pull_request" in jobs["integration-tests"]["strategy"]["matrix"]


@pytest.mark.parametrize("result", ["failure", "cancelled", "skipped"])
def test_offline_endpoint_cell_outcome_fails_the_gate(result: str) -> None:
    # With fail-fast off, a failed or cancelled endpoint cell makes the
    # offline-tests job result non-success; a skip while code is selected is
    # unexpected. Each must turn the required gate red.
    selected = {"detect-changes", "lint", "typecheck", "offline-tests"}
    completed = run_gate(selected, {"offline-tests": result})
    assert completed.returncode != 0
    assert f"offline-tests expected success, got {result}" in completed.stdout


def test_offline_gate_expectation_follows_code_selection() -> None:
    env = gate()["steps"][0]["env"]
    assert env["R_OFFLINE_TESTS"] == "${{ needs.offline-tests.result }}"
    assert env["E_OFFLINE_TESTS"] == "${{ needs.detect-changes.outputs.code }}"
    assert gate()["if"] == "always()"


def test_sensitive_execution_paths_select_live_validation() -> None:
    filters = yaml.safe_load(
        workflow("ci.yml")["jobs"]["detect-changes"]["steps"][-1]["with"]["filters"]
    )
    paths = (
        [
            "pycubrid/_cursor_common.py",
            "pycubrid/lob.py",
            "pycubrid/constants.py",
            "pycubrid/types.py",
        ]
        if REPO == "pycubrid"
        else [
            "sqlalchemy_cubrid/aio_pycubrid_dialect.py",
            "sqlalchemy_cubrid/pycubrid_dialect.py",
            "sqlalchemy_cubrid/_compat.py",
            "sqlalchemy_cubrid/dml.py",
        ]
    )
    assert set(paths) <= set(filters["risk"])
    assert filters["code"][0].startswith("!{")
    if REPO == "pycubrid":
        assert "tests/helpers/tls_*.py" in filters["tls"]
        assert "tests/fixtures/tls/**" in filters["tls"]


def test_ci_event_groups_do_not_cancel_each_other() -> None:
    group = workflow("ci.yml")["concurrency"]["group"]

    def render(event: str, ref: str) -> str:
        result = group.replace("${{ github.event_name }}", event).replace("${{ github.ref }}", ref)
        assert "${{" not in result
        return result

    main_groups = {
        render(event, "refs/heads/main") for event in ("push", "schedule", "workflow_dispatch")
    }
    assert len(main_groups) == 3
    # New commits retain the same event/ref group and still replace the old PR run.
    assert "github.sha" not in group
    assert "github.run_id" not in group
    assert render("pull_request", "refs/pull/659/merge") != render(
        "pull_request", "refs/pull/660/merge"
    )
    assert workflow("ci.yml")["concurrency"]["cancel-in-progress"] is True


def test_documentation_generator_includes_policy_and_preserves_index(tmp_path: Path) -> None:
    import shutil
    import sys

    docs = tmp_path / "docs"
    scripts = tmp_path / "scripts"
    docs.mkdir()
    scripts.mkdir()
    shutil.copyfile(ROOT / "scripts/generate_llms_full.py", scripts / "generate_llms_full.py")
    policy = "# CI policy regression fixture\n\nEvent-isolated representative validation.\n"
    (docs / "CI_POLICY.md").write_text(policy)
    index = (ROOT / "docs/llms.txt").read_bytes()
    (docs / "llms.txt").write_bytes(index)
    subprocess.run(
        [sys.executable, str(scripts / "generate_llms_full.py")],
        check=True,
        capture_output=True,
        timeout=10,
    )
    assert policy.strip() in (docs / "llms-full.txt").read_text()
    assert (tmp_path / "llms.txt").read_bytes() == index
    assert (
        b"[CI execution policy](https://cubrid-lab.github.io/sqlalchemy-cubrid/CI_POLICY/)" in index
    )


LIVE_JOBS = ("make-integration", "integration-tests")


@pytest.mark.parametrize("name", LIVE_JOBS)
def test_live_lanes_start_without_waiting_for_static_and_offline_jobs(name: str) -> None:
    # #744: live lanes run in parallel with lint/typecheck/offline-tests.
    assert workflow("ci.yml")["jobs"][name]["needs"] == ["detect-changes"], name


def test_gate_still_requires_static_and_offline_jobs() -> None:
    needs = set(gate()["needs"])
    assert {"lint", "typecheck", "offline-tests", *LIVE_JOBS} <= needs


# Jobs that report but never gate; everything else in ci.yml must feed the gate.
CI_ADVISORY_JOBS = {"sqlalchemy-21-canary"}
WEEKLY_OR_DISPATCH = "github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'"


def gate_key(job: str) -> str:
    return job.upper().replace("-", "_")


def test_gate_needs_every_gating_job() -> None:
    # A gating job missing from `needs` would never be checked (#737).
    jobs = workflow("ci.yml")["jobs"]
    assert set(gate()["needs"]) == set(jobs) - {"matrix-result"} - CI_ADVISORY_JOBS
    advisory = {name for name, job in jobs.items() if job.get("continue-on-error")}
    assert advisory == CI_ADVISORY_JOBS


@pytest.mark.parametrize("job", gate()["needs"])
def test_gate_checks_every_needed_job(job: str) -> None:
    step = gate()["steps"][0]
    key = gate_key(job)
    assert step["env"][f"R_{key}"] == "${{ needs.%s.result }}" % job
    assert f"E_{key}" in step["env"]
    assert re.search(rf'^\s*check {re.escape(job)} "\$R_{key}" "\$E_{key}"$', step["run"], re.M)


@pytest.mark.parametrize("job", gate()["needs"])
def test_missing_result_of_a_selected_job_fails_the_gate(job: str) -> None:
    # An empty result is what a job that never reported looks like.
    completed = run_gate(set(gate()["needs"]), {job: ""})
    assert completed.returncode != 0


def test_live_smoke_is_folded_into_make_integration() -> None:
    # #737: live-smoke ran test_integration.py and test_regression.py with
    # Python 3.12, CUBRID 11.4 and cubrid+pycubrid://; make-integration runs every
    # integration-marked test with the same interpreter, server and driver.
    jobs = workflow("ci.yml")["jobs"]
    assert "live-smoke" not in jobs
    make = jobs["make-integration"]
    assert make["if"] == "needs.detect-changes.outputs.extended == 'true'"
    setups = [s for s in make["steps"] if "setup-python" in s.get("uses", "")]
    assert [s["with"]["python-version"] for s in setups] == ["3.12"]
    install = next(s for s in make["steps"] if s.get("name") == "Install project")
    assert 'uv pip install --system -e ".[dev,pycubrid]"' in install["run"]
    run = next(s for s in make["steps"] if s.get("name") == "Run make integration")
    assert "make integration INTEGRATION_DRIVER=pycubrid " in run["run"]
    assert run["env"]["CUBRID_VERSION"] == "11.4"
    guard = [
        s
        for s in make["steps"]
        if "python -m scripts.check_not_all_skipped make-integration.log" in s.get("run", "")
    ]
    assert len(guard) == 1
    assert "run $(PYTEST) $(TESTS)/ -m integration -v" in (ROOT / "Makefile").read_text()
    for name in ("test_integration.py", "test_regression.py"):
        text = (ROOT / "test" / name).read_text()
        assert re.search(r"^pytestmark = pytest\.mark\.integration$", text, re.M), name
    # The former lane installed Alembic; the dev extra still does.
    dev = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert any(d.startswith("alembic") for d in dev["optional-dependencies"]["dev"])


def test_sqlalchemy_prerelease_canary_is_weekly_and_advisory() -> None:
    job = workflow("ci.yml")["jobs"]["sqlalchemy-21-canary"]
    # Upstream drift does not depend on this repository's diff (#737).
    assert job["if"] == WEEKLY_OR_DISPATCH
    assert "needs" not in job
    assert job["continue-on-error"] is True
    assert "sqlalchemy-21-canary" not in gate()["needs"]


def test_oldest_cell_cubriddb_compliance_is_weekly_and_gating_lanes_are_not() -> None:
    steps = {s.get("name"): s for s in workflow("ci.yml")["jobs"]["integration-tests"]["steps"]}
    advisory = steps["Run SQLAlchemy dialect compliance suite (non-gating, other cells)"]
    assert advisory["continue-on-error"] is True
    assert f"&& ({WEEKLY_OR_DISPATCH})" in advisory["if"]
    for name in (
        "Run SQLAlchemy dialect compliance suite (gating, CUBRIDdb)",
        "Run SQLAlchemy dialect compliance suite (gating, released pycubrid)",
    ):
        assert "event_name" not in str(steps[name].get("if", "")), name
        assert "continue-on-error" not in steps[name], name


def test_weekly_ci_and_upstream_canary_do_not_share_a_weekday() -> None:
    def weekdays(name: str) -> set[str]:
        doc = workflow(name)
        return {entry["cron"].split()[4] for entry in doc.get("on", doc.get(True))["schedule"]}

    assert weekdays("ci.yml") == {"1"}
    assert weekdays("upstream-canary.yml") == {"4"}


def test_release_runs_the_offline_endpoint_cells_itself() -> None:
    # #737: the release does not rely on the main push run for the #734 cells.
    full = workflow("integration-full.yml")["jobs"]
    job = full["offline-endpoints"]
    assert "if" not in job
    assert job["strategy"]["fail-fast"] is False
    assert job["strategy"]["matrix"] == {"python-version": offline_cells("push")}
    ci_steps = workflow("ci.yml")["jobs"]["offline-tests"]["steps"]

    def run_of(steps: list, name: str) -> str:
        return next(s for s in steps if s.get("name") == name)["run"]

    for name in ("Install dependencies", "Run offline tests with coverage"):
        assert run_of(job["steps"], name) == run_of(ci_steps, name), name
    release_gate = full["full-matrix-result"]
    assert "offline-endpoints" in release_gate["needs"]
    assert "needs.offline-endpoints.result" in release_gate["steps"][0]["run"]


# --- #786: documentation site build on pull requests ------------------------


def detect() -> dict:
    return workflow("ci.yml")["jobs"]["detect-changes"]


def test_support_claim_check_runs_for_docs_or_tooling_changes() -> None:
    lint = workflow("ci.yml")["jobs"]["lint"]
    assert lint["needs"] == "detect-changes"
    steps = [
        step
        for step in lint["steps"]
        if step.get("run") == "python scripts/check_support_claims.py"
    ]
    assert len(steps) == 1
    assert steps[0]["if"] == (
        "${{ needs.detect-changes.outputs.docs == 'true' || "
        "needs.detect-changes.outputs.tooling == 'true' }}"
    )


def test_docs_build_job_mirrors_docs_workflow_and_stays_build_only() -> None:
    job = workflow("ci.yml")["jobs"]["docs-build"]
    assert job["needs"] == "detect-changes"
    assert job["if"] == "needs.detect-changes.outputs.site == 'true'"
    assert job["timeout-minutes"] == 10
    assert "permissions" not in job, "inherits the read-only workflow permissions"
    assert workflow("ci.yml")["permissions"] == {"contents": "read", "pull-requests": "read"}
    assert "environment" not in job
    steps = job["steps"]
    checkout = next(s for s in steps if s["uses"].startswith("actions/checkout@"))
    assert checkout["with"]["persist-credentials"] is False
    for step in steps:
        if "uses" in step:
            assert len(step["uses"].split("@", 1)[1].split()[0]) == 40, step["uses"]
            assert "pages" not in step["uses"], "PRs never upload or deploy a Pages artifact"
    runs = [s["run"] for s in steps if "run" in s]
    assert runs[0].splitlines()[0] == (
        "uv pip install --system -r .github/docs-requirements/requirements.txt"
    )
    # Same build commands, in the same order, as docs.yml's build job.
    docs_runs = [s["run"] for s in workflow("docs.yml")["jobs"]["build"]["steps"] if "run" in s]
    assert (
        runs[1:]
        == docs_runs[1:]
        == ["python scripts/generate_llms_full.py", "mkdocs build --strict"]
    )
    assert docs_runs[0] == "pip install -r .github/docs-requirements/requirements.txt"


def test_docs_site_selection_covers_every_site_input() -> None:
    step = next(s for s in detect()["steps"] if s.get("id") == "filter")
    filters = yaml.safe_load(step["with"]["filters"])
    assert set(filters["site"]) == {
        "docs/**",  # content, nav assets and translations
        "mkdocs.yml",
        "scripts/generate_llms_full.py",
        ".github/docs-requirements/**",
        ".github/workflows/docs.yml",
        ".github/workflows/ci.yml",
    }


def test_docs_site_output_is_forced_only_for_manual_dispatch() -> None:
    out = detect()["outputs"]["site"]
    assert "github.event_name == 'workflow_dispatch' ||" in out
    assert "steps.filter.outputs.site == 'true'" in out


def test_gate_expects_docs_build_exactly_when_the_site_is_selected() -> None:
    step = gate()["steps"][0]
    assert step["env"]["E_DOCS_BUILD"] == "${{ needs.detect-changes.outputs.site }}"
    assert "docs-build" in gate()["needs"]
    base = {"detect-changes", "lint", "doc-lint", "docs-build"}
    assert run_gate(base, {}).returncode == 0
    for result in ("failure", "cancelled", "skipped"):
        completed = run_gate(base, {"docs-build": result})
        assert completed.returncode != 0
        assert f"docs-build expected success, got {result}" in completed.stdout
    # Not selected: a skipped build passes, a failed one still blocks.
    assert run_gate(base - {"docs-build"}, {}).returncode == 0
    assert run_gate(base - {"docs-build"}, {"docs-build": "failure"}).returncode != 0
