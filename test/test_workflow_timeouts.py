"""Every executing workflow job carries an explicit, bounded timeout (#741).

GitHub's default job limit is 360 minutes, so a hung container, socket, driver
build or install would hold a runner for six hours. Jobs that call a reusable
workflow cannot set ``timeout-minutes``; repo-local callees are checked through
their own executing jobs, and externally owned callees are an explicit allowlist.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"

MAX_TIMEOUT_MINUTES = 180
GATE_MAX_TIMEOUT_MINUTES = 10

# Documented exceptions above MAX_TIMEOUT_MINUTES (docs/CI_POLICY.md); none today.
JOB_MAX_OVERRIDES: dict[tuple[str, str], int] = {}

# Reusable workflows owned outside this repository. Their timeouts are set (or
# tracked) in the owning repository, not here. Keep entries exact.
EXTERNAL_REUSABLE_CALLERS = {
    ("ci.yml", "doc-lint"): "cubrid-lab/.github/.github/workflows/doc-lint.yml",
    ("codeql.yml", "analyze"): "cubrid-lab/.github/.github/workflows/codeql.yml",
    ("integration-full.yml", "fuzz-bug-hunt"): (
        "cubrid-lab/.github/.github/workflows/live-smoke.yml"
    ),
    ("publish-pypi.yml", "verify-cookbook"): (
        "cubrid-lab/cubrid-cookbook-python/.github/workflows/smoke-test.yml"
    ),
}

GATES = {("ci.yml", "matrix-result"), ("integration-full.yml", "full-matrix-result")}


def _jobs() -> list[tuple[str, str, dict]]:
    found = []
    for path in sorted([*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")]):
        for name, job in yaml.safe_load(path.read_text())["jobs"].items():
            found.append((path.name, name, job))
    return found


EXECUTING = [(wf, name, job) for wf, name, job in _jobs() if "uses" not in job]
CALLERS = [(wf, name, job) for wf, name, job in _jobs() if "uses" in job]


def _params(jobs: list[tuple[str, str, dict]]) -> list:
    return [pytest.param(wf, name, job, id=f"{wf}:{name}") for wf, name, job in jobs]


def test_every_job_is_either_executing_or_a_reusable_caller() -> None:
    for wf, name, job in EXECUTING:
        assert "runs-on" in job, f"{wf}:{name} has neither runs-on nor uses"


@pytest.mark.parametrize(("wf", "name", "job"), _params(EXECUTING))
def test_executing_job_has_bounded_integer_timeout(wf: str, name: str, job: dict) -> None:
    timeout = job.get("timeout-minutes")
    assert isinstance(timeout, int) and not isinstance(timeout, bool), (
        f"{wf}:{name} must set an integer timeout-minutes (default would be 360)"
    )
    limit = JOB_MAX_OVERRIDES.get((wf, name), MAX_TIMEOUT_MINUTES)
    assert 1 <= timeout <= limit, f"{wf}:{name} timeout {timeout} out of range"


@pytest.mark.parametrize(("wf", "name", "job"), _params(CALLERS))
def test_reusable_caller_is_local_or_allowlisted(wf: str, name: str, job: dict) -> None:
    target = job["uses"]
    if target.startswith("./.github/workflows/"):
        callee = ROOT / target.removeprefix("./")
        assert callee.is_file(), f"{wf}:{name} calls missing {target}"
        for callee_name, callee_job in yaml.safe_load(callee.read_text())["jobs"].items():
            if "uses" not in callee_job:
                assert isinstance(callee_job.get("timeout-minutes"), int), (
                    f"{callee.name}:{callee_name} (called from {wf}:{name}) needs a timeout"
                )
        return
    expected = EXTERNAL_REUSABLE_CALLERS.get((wf, name))
    assert expected is not None, f"{wf}:{name} calls external {target}; add it to the allowlist"
    assert target.split("@", 1)[0] == expected


def test_allowlist_and_overrides_have_no_stale_entries() -> None:
    callers = {(wf, name) for wf, name, _ in CALLERS}
    assert set(EXTERNAL_REUSABLE_CALLERS) <= callers
    for wf, name, job in CALLERS:
        if (wf, name) in EXTERNAL_REUSABLE_CALLERS:
            assert not job["uses"].startswith("./"), f"{wf}:{name} is local; drop it from the list"
    assert set(JOB_MAX_OVERRIDES) <= {(wf, name) for wf, name, _ in EXECUTING}


@pytest.mark.parametrize(("wf", "name"), sorted(GATES))
def test_aggregate_gates_have_short_timeouts(wf: str, name: str) -> None:
    job = yaml.safe_load((WORKFLOWS / wf).read_text())["jobs"][name]
    timeout = job.get("timeout-minutes")
    assert isinstance(timeout, int) and 1 <= timeout <= GATE_MAX_TIMEOUT_MINUTES
    # A timed-out dependency reports a non-success result; the gate must still run.
    assert str(job.get("if", "")).strip() in {"always()", "${{ always() }}"}


def run_release_gate(results: dict[str, str]) -> subprocess.CompletedProcess:
    # test/test_ci_policy.py covers matrix-result; this covers the release gate.
    if shutil.which("bash") is None:
        pytest.skip("GitHub workflow shell requires bash")
    job = yaml.safe_load((WORKFLOWS / "integration-full.yml").read_text())["jobs"][
        "full-matrix-result"
    ]
    script = "\n".join(step["run"] for step in job["steps"] if "run" in step)
    for need in job["needs"]:
        script = script.replace("${{ needs.%s.result }}" % need, results.get(need, "success"))
    assert "${{" not in script, "gate references an unexpected expression"
    return subprocess.run(
        ["bash", "-eo", "pipefail", "-c", script],
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )


def test_release_gate_passes_when_every_dependency_succeeds() -> None:
    completed = run_release_gate({})
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Full compatibility matrix passed." in completed.stdout


RELEASE_GATE_NEEDS = yaml.safe_load((WORKFLOWS / "integration-full.yml").read_text())["jobs"][
    "full-matrix-result"
]["needs"]


def test_release_gate_requires_the_offline_endpoint_cells() -> None:
    # #737: the release runs the Python 3.11/3.14 offline cells itself.
    assert set(RELEASE_GATE_NEEDS) == {"integration-full", "make-integration", "offline-endpoints"}


@pytest.mark.parametrize("result", ["failure", "cancelled", "skipped", ""])
@pytest.mark.parametrize("failed", RELEASE_GATE_NEEDS)
def test_release_gate_fails_on_any_non_success_dependency(failed: str, result: str) -> None:
    completed = run_release_gate({failed: result})
    assert completed.returncode != 0
    assert result in completed.stdout
