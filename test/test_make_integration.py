"""Exercise Docker ownership and failure propagation without starting Docker."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.fixture
def integration_runner(tmp_path: Path):
    make = shutil.which("make")
    if make is None:
        pytest.skip("make is required for Makefile regression tests")
    shutil.copyfile(Path(__file__).resolve().parents[1] / "Makefile", tmp_path / "Makefile")
    log = tmp_path / "commands.log"
    stub = (
        f"#!{sys.executable}\n"
        + """\
import os
from pathlib import Path
import sys

name = Path(sys.argv[0]).name
with open(os.environ["COMMAND_LOG"], "a", encoding="utf-8") as stream:
    stream.write(" ".join([name, *sys.argv[1:]]) + "\\n")
if name == "docker":
    phase = "UP" if sys.argv[2] == "up" else "DOWN"
elif name == "sleep":
    phase = "WAIT"
else:
    phase = "TEST"
sys.exit(int(os.environ.get(phase + "_STATUS", "0")))
"""
    )
    for name in ("docker", "sleep", "pytest-stub"):
        command = tmp_path / name
        command.write_text(stub, encoding="utf-8")
        command.chmod(0o755)

    def run(target: str = "integration", *, dry_run: bool = False, **statuses: int):
        env = os.environ.copy()
        # Do not inherit outer make jobserver or command-line variable overrides.
        for key in ("MAKEFLAGS", "MFLAGS", "MAKEOVERRIDES"):
            env.pop(key, None)
        env.update(
            PATH=str(tmp_path) + os.pathsep + env.get("PATH", ""),
            COMMAND_LOG=str(log),
            CUBRID_TEST_URL="cubrid://dba@localhost:33000/external",
            **{
                phase + "_STATUS": str(statuses.get(phase.lower(), 0))
                for phase in ("UP", "DOWN", "WAIT", "TEST")
            },
        )
        result = subprocess.run(
            [
                make,
                "--no-print-directory",
                *(["-n"] if dry_run else []),
                target,
                "PYTEST=pytest-stub",
            ],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return result, log.read_text(encoding="utf-8").splitlines() if log.exists() else []

    return run


@pytest.mark.parametrize("test_status", [0, 7])
@pytest.mark.parametrize("cleanup_status", [0, 9])
def test_integration_always_cleans_up(integration_runner, test_status, cleanup_status):
    result, commands = integration_runner(test=test_status, down=cleanup_status)
    assert commands == [
        "docker compose up -d",
        "sleep 10",
        "pytest-stub test/ -m integration -v",
        "docker compose down -v",
    ]
    assert (result.returncode == 0) == (test_status == cleanup_status == 0)
    if test_status:
        # GNU make itself exits 2; its diagnostic retains the recipe's test exit.
        assert "Error 7" in result.stderr
    if cleanup_status:
        assert "Docker cleanup failed" in result.stderr


@pytest.mark.parametrize("phase", ["up", "wait"])
def test_integration_cleans_up_after_setup_failure(integration_runner, phase):
    result, commands = integration_runner(**{phase: 6})
    assert result.returncode != 0
    assert commands[0] == "docker compose up -d"
    assert commands[-1] == "docker compose down -v"
    assert not any(command.startswith("pytest-stub") for command in commands)


@pytest.mark.parametrize("test_status", [0, 7])
def test_integration_local_never_manages_docker(integration_runner, test_status):
    result, commands = integration_runner("integration-local", test=test_status)
    assert commands == ["pytest-stub test/ -m integration -v"]
    assert (result.returncode == 0) == (test_status == 0)


def test_integration_dry_run_does_not_execute_commands(integration_runner):
    result, commands = integration_runner(dry_run=True)
    assert result.returncode == 0
    assert commands == []
