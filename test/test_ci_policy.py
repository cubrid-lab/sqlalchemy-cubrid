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


def test_pr_smoke_is_separate_from_main_coverage_and_single_linux_lane() -> None:
    jobs = workflow("ci.yml")["jobs"]
    offline = jobs["offline-tests"]
    matrix = offline["strategy"]["matrix"]
    assert matrix["python-version"] == ["3.12"]
    assert matrix.get("os", [offline["runs-on"]]) == ["ubuntu-latest"]
    steps = offline["steps"]
    smoke = next(s for s in steps if s.get("name") == "Run representative PR smoke tests")
    coverage = next(s for s in steps if s.get("name") == "Run offline tests with coverage")
    assert smoke["if"] == "github.event_name == 'pull_request'"
    assert coverage["if"] == "github.event_name != 'pull_request'"
    assert "--cov-fail-under=95" in coverage["run"]
    assert "--cov" not in smoke["run"]
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


def test_pr_smoke_paths_exist() -> None:
    import shlex

    steps = workflow("ci.yml")["jobs"]["offline-tests"]["steps"]
    smoke = next(s for s in steps if s.get("name") == "Run representative PR smoke tests")
    paths = [word for word in shlex.split(smoke["run"]) if word.endswith(".py")]
    assert paths
    assert all((ROOT / path).is_file() for path in paths)


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
