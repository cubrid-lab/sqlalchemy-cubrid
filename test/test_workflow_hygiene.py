"""Pinned docs tools, scan concurrency and the pycubrid floor stay enforced (#761, #762, #764)."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"
DOCS_REQUIREMENTS = ".github/docs-requirements/requirements.txt"
DOCS_TOOLS = {"mkdocs", "mkdocs-material", "pymdown-extensions"}
PIN = re.compile(r"^(?P<name>[A-Za-z0-9_.-]+)==(?P<version>\d+(?:\.\d+)*)$")


def _workflow(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text())


def _runs(workflow: dict) -> list[str]:
    return [
        step["run"]
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if "run" in step
    ]


def test_docs_requirements_pin_every_docs_tool_exactly() -> None:
    lines = [
        line.strip()
        for line in (ROOT / DOCS_REQUIREMENTS).read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    pins = {m["name"]: m["version"] for m in map(PIN.match, lines) if m}
    assert len(pins) == len(lines), f"every line must be an exact == pin: {lines}"
    assert set(pins) == DOCS_TOOLS


def test_every_docs_build_installs_from_the_pinned_file() -> None:
    builds = [
        (path.name, job)
        for path in WORKFLOWS.glob("*.yml")
        for job in yaml.safe_load(path.read_text())["jobs"].values()
        if any("mkdocs build" in step.get("run", "") for step in job.get("steps", []))
    ]
    assert {name for name, _ in builds} == {"docs.yml", "ci.yml"}
    for name, job in builds:
        installs = [
            line.strip()
            for step in job["steps"]
            for line in step.get("run", "").splitlines()
            if "pip install" in line
        ]
        # ci.yml's PR build (#786) installs with uv like every other ci.yml job.
        installer = "uv pip install --system" if name == "ci.yml" else "pip install"
        assert installs == [f"{installer} -r {DOCS_REQUIREMENTS}"], name


def test_dependabot_updates_the_docs_requirements() -> None:
    config = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text())
    directories = [u["directory"] for u in config["updates"] if u["package-ecosystem"] == "pip"]
    assert "/.github/docs-requirements" in directories


def test_scan_workflows_cancel_superseded_pull_requests_only() -> None:
    for name in ("codeql.yml", "security.yml"):
        concurrency = _workflow(name)["concurrency"]
        assert concurrency["group"] == (
            "${{ github.workflow }}-${{ github.event_name == 'pull_request' && github.ref || github.run_id }}"
        ), name
        assert concurrency["cancel-in-progress"] == (
            "${{ github.event_name == 'pull_request' }}"
        ), f"{name} must never cancel main or scheduled runs"


def test_compliance_lane_pins_the_declared_pycubrid_floor() -> None:
    extras = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"][
        "optional-dependencies"
    ]
    floors = [m[1] for r in extras["pycubrid"] if (m := re.match(r"pycubrid>=([\d.]+),", r))]
    assert len(floors) == 1, extras["pycubrid"]
    pins = re.findall(r'"pycubrid==([\d.]+)"', (WORKFLOWS / "ci.yml").read_text())
    assert pins == floors, (
        f"ci.yml pins pycubrid {pins} but pyproject declares floor {floors}; "
        "change both together (#764)"
    )
