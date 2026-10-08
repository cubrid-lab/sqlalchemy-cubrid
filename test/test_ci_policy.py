"""Exercise aggregate gates for selected, skipped and cancelled validation."""

from __future__ import annotations

import os
import subprocess
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


def test_full_offline_suite_runs_on_every_event_in_one_linux_lane() -> None:
    jobs = workflow("ci.yml")["jobs"]
    offline = jobs["offline-tests"]
    matrix = offline["strategy"]["matrix"]
    assert matrix["python-version"] == ["3.12"]
    assert matrix.get("os", [offline["runs-on"]]) == ["ubuntu-latest"]
    steps = offline["steps"]
    names = [s.get("name") for s in steps]
    assert "Run representative PR smoke tests" not in names
    # No step may run only on (or skip on) pull requests, whatever its name.
    assert not [s.get("name") for s in steps if "pull_request" in str(s.get("if", ""))]
    coverage = next(s for s in steps if s.get("name") == "Run offline tests with coverage")
    upload = next(s for s in steps if s.get("name") == "Upload coverage")
    # PRs run the same full selection and coverage floor as pushes (#742).
    assert "if" not in coverage and "if" not in upload
    assert "test/" in coverage["run"].split()
    assert '-m "not integration and not repo"' in coverage["run"]
    assert "--cov-fail-under=95" in coverage["run"]
    # The dotfile must actually upload, and a missing file must fail the job.
    assert upload["with"]["path"] == ".coverage"
    assert upload["with"]["include-hidden-files"] is True
    assert upload["with"]["if-no-files-found"] == "error"
    assert "outputs.live" in jobs["integration-tests"]["if"]
    assert "pull_request" in jobs["integration-tests"]["strategy"]["matrix"]


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


LIVE_JOBS = ("live-smoke", "make-integration", "integration-tests")


@pytest.mark.parametrize("name", LIVE_JOBS)
def test_live_lanes_start_without_waiting_for_static_and_offline_jobs(name: str) -> None:
    # #744: live lanes run in parallel with lint/typecheck/offline-tests.
    assert workflow("ci.yml")["jobs"][name]["needs"] == ["detect-changes"], name


def test_gate_still_requires_static_and_offline_jobs() -> None:
    needs = set(gate()["needs"])
    assert {"lint", "typecheck", "offline-tests", *LIVE_JOBS} <= needs
