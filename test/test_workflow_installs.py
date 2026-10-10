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

UV_ACTION = "astral-sh/setup-uv@c18668ad3cf93ea998bef934396af7bb5c839dc7"
UV_VERSION = "0.12.17"
# The release gate keeps setup-uv's event guard (`auto`); routine CI always caches.
WORKFLOWS = {"ci.yml": True, "integration-full.yml": "auto", "upstream-canary.yml": True}
EXPECTED_JOBS = {"ci.yml": 10, "integration-full.yml": 8, "upstream-canary.yml": 2}
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


def test_python_jobs_are_found() -> None:
    for wf, expected in EXPECTED_JOBS.items():
        assert sum(1 for p in PYTHON_JOBS if p.values[0] == wf) == expected, wf


@pytest.mark.parametrize(("wf", "name", "steps"), PYTHON_JOBS)
def test_job_sets_up_pinned_uv_after_python(wf: str, name: str, steps: list) -> None:
    uv = [s for s in steps if str(s.get("uses", "")).startswith("astral-sh/setup-uv@")]
    assert len(uv) == 1, f"{wf}:{name} needs exactly one setup-uv step"
    assert uv[0]["uses"] == UV_ACTION
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
