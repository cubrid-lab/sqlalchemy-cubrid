"""CI, full-matrix and canary jobs install dependencies with a pinned uv (#743).

uv only replaces the installer; resolution follows the same pyproject constraints.
Plain ``pip`` stays where it is the point: the packaging smoke venvs prove the built
wheel and sdist install with the end-user tool, and the external live-smoke reusable
workflow receives its own install command.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]

WORKFLOW_DIR = ROOT / ".github" / "workflows"
UV_ACTION_PREFIX = "astral-sh/setup-uv@"
FULL_SHA = re.compile(r"[0-9a-f]{40}")
UV_VERSION = "0.12.17"
# The release gate keeps setup-uv's event guard (`auto`); routine CI always caches.
WORKFLOWS = {"ci.yml": True, "integration-full.yml": "auto", "upstream-canary.yml": True}
EXPECTED_JOBS = {"ci.yml": 11, "integration-full.yml": 8, "upstream-canary.yml": 2}
# Jobs that set up Python but install nothing (stdlib-only scripts).
NO_INSTALL = {("integration-full.yml", "version-differential")}
PIP_INSTALL = re.compile(r"\bpip3?\s+install\b")
PIP_SMOKE_ALLOWED = re.compile(r"^/tmp/test-(wheel|wheel-pycubrid|sdist)/bin/pip install ")


def _python_jobs() -> list:
    params = []
    for wf in WORKFLOWS:
        jobs = yaml.safe_load((ROOT / ".github/workflows" / wf).read_text())["jobs"]
        for name, job in jobs.items():
            steps = job.get("steps", [])
            if (wf, name) in NO_INSTALL:
                continue
            if any("actions/setup-python@" in str(s.get("uses", "")) for s in steps):
                params.append(pytest.param(wf, name, steps, id=f"{wf}:{name}"))
    return params


PYTHON_JOBS = _python_jobs()


def _setup_uv_refs() -> set[str]:
    """Read actual workflow actions, including an invalid empty `setup-uv@` ref."""
    refs: set[str] = set()
    for path in WORKFLOW_DIR.glob("*.yml"):
        workflow = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for job in workflow.get("jobs", {}).values():
            for step in job.get("steps", []):
                uses = str(step.get("uses", ""))
                if uses.startswith(UV_ACTION_PREFIX):
                    refs.add(uses[len(UV_ACTION_PREFIX) :])
    return refs


def _setup_uv_pin_error(refs: set[str]) -> str | None:
    """Require all workflow setup-uv steps to share a valid full commit SHA."""
    if len(refs) != 1:
        return f"setup-uv must use one ref, found {sorted(refs)}"
    value = next(iter(refs))
    if not FULL_SHA.fullmatch(value):
        return f"setup-uv must use a full lowercase 40-character SHA, found {value!r}"
    return None


def test_all_workflows_share_a_full_setup_uv_sha() -> None:
    assert _setup_uv_pin_error(_setup_uv_refs()) is None


@pytest.mark.parametrize("sha", ["a" * 40, "0123456789abcdef0123456789abcdef01234567"])
def test_dependabot_can_change_the_sha_without_a_test_edit(sha: str) -> None:
    assert _setup_uv_pin_error({sha}) is None


@pytest.mark.parametrize(
    "refs",
    [
        {"a" * 40, "b" * 40},
        {"a" * 40, ""},
        {""},
        {"v10.3.3"},
        {"main"},
        {"a" * 39},
        {"a" * 41},
        {"A" * 40},
        set(),
    ],
)
def test_bad_setup_uv_refs_are_rejected(refs: set[str]) -> None:
    assert _setup_uv_pin_error(refs) is not None


def test_python_jobs_are_found() -> None:
    for wf, expected in EXPECTED_JOBS.items():
        assert sum(1 for p in PYTHON_JOBS if p.values[0] == wf) == expected, wf


@pytest.mark.parametrize(("wf", "name", "steps"), PYTHON_JOBS)
def test_job_sets_up_pinned_uv_after_python(wf: str, name: str, steps: list) -> None:
    uv = [s for s in steps if str(s.get("uses", "")).startswith(UV_ACTION_PREFIX)]
    assert len(uv) == 1, f"{wf}:{name} needs exactly one setup-uv step"
    assert uv[0]["with"]["version"] == UV_VERSION
    assert uv[0]["with"]["enable-cache"] == WORKFLOWS[wf]
    assert uv[0]["with"]["cache-dependency-glob"] == "pyproject.toml"
    # One cache per job. setup-uv follows setup-python and both share one
    # python-version spec, so UV_PYTHON resolves to setup-python's interpreter and
    # the cache key carries the minor version, not the patch that drifts by runner.
    assert uv[0]["with"]["cache-suffix"] == "${{ github.job }}"
    python = next(s for s in steps if "actions/setup-python@" in str(s.get("uses", "")))
    assert steps.index(python) < steps.index(uv[0]), f"{wf}:{name} set up Python first"
    assert uv[0]["with"]["python-version"] == python["with"]["python-version"]
    first_uv_use = next(i for i, s in enumerate(steps) if "uv pip" in s.get("run", ""))
    assert steps.index(uv[0]) < first_uv_use, f"{wf}:{name} calls uv before setup-uv"


@pytest.mark.parametrize(("wf", "name", "steps"), PYTHON_JOBS)
def test_job_installs_with_uv_and_logs_versions(wf: str, name: str, steps: list) -> None:
    lines = [line.strip() for s in steps if "run" in s for line in s["run"].splitlines()]
    assert any(line.startswith("uv pip install --system ") for line in lines), name
    assert "uv pip freeze --system" in lines, f"{wf}:{name} must log resolved versions"
    for line in lines:
        if PIP_INSTALL.search(line) and not line.startswith("uv pip "):
            assert PIP_SMOKE_ALLOWED.match(line), f"{wf}:{name} still uses pip: {line}"
    uv_lines = [line for line in lines if line.startswith("uv pip ")]
    assert not any(re.search(r"--pre\b(?!release)", line) for line in uv_lines), (
        "uv spells pre-release opt-in as --prerelease=..."
    )
    # pip's --upgrade touches only named packages; uv's upgrades their dependencies too.
    assert not any(re.search(r"--upgrade\b(?!-package)", line) for line in uv_lines), (
        "use --upgrade-package <name> to keep pip's upgrade scope"
    )


@pytest.mark.parametrize(("wf", "name"), sorted(NO_INSTALL))
def test_no_install_jobs_stay_install_free(wf: str, name: str) -> None:
    steps = yaml.safe_load((ROOT / ".github/workflows" / wf).read_text())["jobs"][name]["steps"]
    assert not any("setup-uv" in str(s.get("uses", "")) for s in steps)
    assert not any(PIP_INSTALL.search(s.get("run", "")) for s in steps)
