"""The CUBRIDdb lanes reuse a cached driver wheel only on an exact key (#745).

The wheel links CCI statically, so its key is the runner OS/arch/image, the Python
ABI and the resolved source commit. A cache hit skips only the build; the wheel is
always installed and imported, and the live readiness probe still connects.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]

CACHE_ACTION = "actions/cache@55cc8345863c7cc4c66a329aec7e433d2d1c52a9"
KEY_PARTS = (
    "${{ runner.os }}",
    "${{ runner.arch }}",
    "${{ steps.cubriddb-src.outputs.image }}",
    "${{ steps.cubriddb-src.outputs.soabi }}",
    "${{ steps.cubriddb-src.outputs.commit }}",
)
EXPECTED = {
    ("ci.yml", "integration-tests"),
    ("integration-full.yml", "integration-full"),
    ("integration-full.yml", "make-integration"),
    ("integration-full.yml", "sqlalchemy-compliance"),
}
MISS = "steps.cubriddb-cache.outputs.cache-hit != 'true'"


def _jobs() -> list:
    found = []
    for wf in ("ci.yml", "integration-full.yml"):
        jobs = yaml.safe_load((ROOT / ".github/workflows" / wf).read_text())["jobs"]
        for name, job in jobs.items():
            steps = job.get("steps", [])
            if any(s.get("id") == "cubriddb-cache" for s in steps):
                found.append(pytest.param(wf, name, steps, id=f"{wf}:{name}"))
    return found


JOBS = _jobs()


def _step(steps: list, name: str) -> tuple[int, dict]:
    return next((i, s) for i, s in enumerate(steps) if s.get("name") == name)


def test_every_cubriddb_build_uses_the_cache() -> None:
    assert {(p.values[0], p.values[1]) for p in JOBS} == EXPECTED
    for wf in ("ci.yml", "integration-full.yml"):
        text = (ROOT / ".github/workflows" / wf).read_text()
        assert "uv pip install --system .\n" not in text, f"{wf}: uncached in-tree driver build"


@pytest.mark.parametrize(("wf", "name", "steps"), JOBS)
def test_cache_key_covers_abi_image_and_source_commit(wf: str, name: str, steps: list) -> None:
    _, src = _step(steps, "Fetch CUBRID Python driver source")
    for output in ("commit=$(git -C /tmp/cubrid-python rev-parse HEAD)", "SOABI", "ImageOS"):
        assert output in src["run"], f"{wf}:{name} must record {output}"
    _, cache = _step(steps, "Restore the CUBRID Python driver wheel")
    assert cache["uses"].split(" ")[0] == CACHE_ACTION
    assert cache["with"]["path"] == "/tmp/cubriddb-wheel"
    key = cache["with"]["key"]
    assert key.startswith("cubriddb-wheel-v")
    for part in KEY_PARTS:
        assert part in key, f"{wf}:{name} key misses {part}"
    assert "cubrid-version" not in key, "the server version must not split the wheel cache"


@pytest.mark.parametrize(("wf", "name", "steps"), JOBS)
def test_only_the_build_is_skipped_on_a_hit(wf: str, name: str, steps: list) -> None:
    for step_name in ("Install system dependencies", "Build the CUBRID Python driver wheel"):
        _, step = _step(steps, step_name)
        assert step["if"].endswith(MISS), f"{wf}:{name}: {step_name} must run only on a miss"
    i_install, install = _step(steps, "Install the CUBRID Python driver")
    assert MISS not in str(install.get("if", ""))
    assert "uv pip install --system /tmp/cubriddb-wheel/" in install["run"]
    assert "import CUBRIDdb, _cubrid" in install["run"]
    i_build, _ = _step(steps, "Build the CUBRID Python driver wheel")
    assert i_build < i_install


@pytest.mark.parametrize(
    ("wf", "name"),
    [
        ("ci.yml", "integration-tests"),
        ("integration-full.yml", "integration-full"),
        ("integration-full.yml", "sqlalchemy-compliance"),
    ],
)
def test_live_readiness_still_connects_through_cubriddb(wf: str, name: str) -> None:
    steps = yaml.safe_load((ROOT / ".github/workflows" / wf).read_text())["jobs"][name]["steps"]
    i_install, _ = _step(steps, "Install the CUBRID Python driver")
    i_ready, ready = _step(steps, "Wait for CUBRID to be ready")
    assert i_install < i_ready
    assert "CUBRIDdb.connect(" in ready["run"]


def test_all_jobs_share_one_key_and_one_build_recipe() -> None:
    # The wheels are interchangeable across jobs (same key namespace), so a recipe
    # edit in one copy without a matching key bump would silently reuse old wheels.
    keys, recipes = set(), set()
    for param in JOBS:
        steps = param.values[2]
        keys.add(_step(steps, "Restore the CUBRID Python driver wheel")[1]["with"]["key"])
        recipe = _step(steps, "Build the CUBRID Python driver wheel")[1]["run"]
        recipes.add("\n".join(line.strip() for line in recipe.splitlines() if line.strip()))
    assert len(keys) == 1, keys
    assert len(recipes) == 1, "the build recipes diverged; keep them identical"


def test_make_integration_guards_every_driver_step() -> None:
    steps = yaml.safe_load((ROOT / ".github/workflows/integration-full.yml").read_text())["jobs"][
        "make-integration"
    ]["steps"]
    for name in (
        "Fetch CUBRID Python driver source",
        "Restore the CUBRID Python driver wheel",
        "Install system dependencies",
        "Build the CUBRID Python driver wheel",
        "Install the CUBRID Python driver",
    ):
        assert "matrix.driver == 'cubriddb'" in _step(steps, name)[1]["if"], name
