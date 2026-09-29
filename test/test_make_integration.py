"""Exercise Docker ownership and failure propagation without starting Docker.

Every command the ``integration`` recipe runs (``docker``, ``sleep`` and the
pytest command) is a logging stub on ``PATH``, so no container, volume or
network is ever created or removed.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

PROJECT = "sa-it-stub"
UP = f"docker compose -p {PROJECT} up -d"
DOWN = f"docker compose -p {PROJECT} down -v"
WAIT = "sleep 10"
TEST = "pytest-stub test/ -m integration -v"


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
args = sys.argv[1:]
with open(os.environ["COMMAND_LOG"], "a", encoding="utf-8") as stream:
    stream.write(" ".join([name, *args]) + "\\n")
existing = set(filter(None, os.environ.get("EXISTING", "").split(",")))
if name == "docker":
    if args[0] == "compose":
        phase = "UP" if "up" in args else "DOWN"
    elif args[0] == "volume" and args[1] == "inspect":
        sys.exit(0 if "named-volume" in existing else 1)
    else:
        # Ownership probes: docker ps / volume ls / network ls with a label filter.
        kind = {"ps": "container", "volume": "volume", "network": "network"}[args[0]]
        if kind in existing:
            print("pre-existing-" + kind)
        phase = "PROBE"
elif name == "sleep":
    phase = "WAIT"
else:
    phase = "TEST"
    with open(os.environ["COMMAND_LOG"], "a", encoding="utf-8") as stream:
        stream.write("CUBRID_TEST_URL=" + os.environ.get("CUBRID_TEST_URL", "") + "\\n")
sys.exit(int(os.environ.get(phase + "_STATUS", "0")))
"""
    )
    for name in ("docker", "sleep", "pytest-stub"):
        command = tmp_path / name
        command.write_text(stub, encoding="utf-8")
        command.chmod(0o755)

    def run(
        target: str = "integration",
        *,
        dry_run: bool = False,
        project: str | None = PROJECT,
        existing: str = "",
        make_vars: tuple[str, ...] = (),
        **statuses: int,
    ):
        env = os.environ.copy()
        # Do not inherit outer make jobserver or command-line variable overrides.
        for key in ("MAKEFLAGS", "MFLAGS", "MAKEOVERRIDES", "CUBRID_PORT", "INTEGRATION_PROJECT"):
            env.pop(key, None)
        env.update(
            PATH=str(tmp_path) + os.pathsep + env.get("PATH", ""),
            COMMAND_LOG=str(log),
            CUBRID_TEST_URL="cubrid://dba@localhost:33000/external",
            EXISTING=existing,
            **{
                phase + "_STATUS": str(statuses.get(phase.lower(), 0))
                for phase in ("PROBE", "UP", "DOWN", "WAIT", "TEST")
            },
        )
        result = subprocess.run(
            [
                make,
                "--no-print-directory",
                *(["-n"] if dry_run else []),
                target,
                "PYTEST=pytest-stub",
                *([f"INTEGRATION_PROJECT={project}"] if project else []),
                *make_vars,
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


def _lifecycle(commands: list[str]) -> list[str]:
    """Drop the read-only ownership probes and keep the lifecycle commands."""
    return [
        command
        for command in commands
        if not command.startswith(("docker ps", "docker volume", "docker network"))
    ]


def test_integration_probes_ownership_before_starting(integration_runner):
    result, commands = integration_runner()
    assert result.returncode == 0, result.stderr
    label = f"label=com.docker.compose.project={PROJECT}"
    assert commands[:4] == [
        f"docker ps -aq --filter {label}",
        f"docker volume ls -q --filter {label}",
        f"docker network ls -q --filter {label}",
        f"docker volume inspect {PROJECT}_cubrid-data",
    ]
    assert commands.index(UP) > 3


@pytest.mark.parametrize("test_status", [0, 7])
@pytest.mark.parametrize("cleanup_status", [0, 9])
def test_integration_always_cleans_up(integration_runner, test_status, cleanup_status):
    result, commands = integration_runner(test=test_status, down=cleanup_status)
    assert _lifecycle(commands) == [
        UP,
        WAIT,
        TEST,
        "CUBRID_TEST_URL=cubrid://dba@localhost:33000/testdb",
        DOWN,
    ]
    assert (result.returncode == 0) == (test_status == cleanup_status == 0)
    if test_status:
        # GNU make itself exits 2; its diagnostic retains the recipe's test exit.
        assert "Error 7" in result.stderr
    if cleanup_status:
        assert "Docker cleanup of Compose project" in result.stderr
        if not test_status:
            assert "Error 9" in result.stderr


@pytest.mark.parametrize("phase", ["up", "wait"])
@pytest.mark.parametrize("cleanup_status", [0, 9])
def test_integration_cleans_up_after_setup_failure(integration_runner, phase, cleanup_status):
    result, commands = integration_runner(**{phase: 6}, down=cleanup_status)
    assert result.returncode != 0
    # The startup failure, not the cleanup failure, is what make reports.
    assert "Error 6" in result.stderr
    lifecycle = _lifecycle(commands)
    assert lifecycle[0] == UP
    assert lifecycle[-1] == DOWN
    assert lifecycle.count(DOWN) == 1
    assert not any(command.startswith("pytest-stub") for command in commands)


@pytest.mark.parametrize("existing", ["container", "volume", "network", "named-volume"])
@pytest.mark.parametrize("up_status", [0, 6])
def test_integration_refuses_pre_existing_project(integration_runner, existing, up_status):
    # A same-project stack or volume that this run did not create must survive,
    # even when startup would have failed: nothing is started and nothing removed.
    result, commands = integration_runner(existing=existing, up=up_status)
    assert result.returncode != 0
    assert "Refusing to run" in result.stderr
    assert _lifecycle(commands) == []
    assert not any(command.startswith("docker compose") for command in commands)


def test_integration_fails_closed_when_ownership_probe_fails(integration_runner):
    result, commands = integration_runner(probe=5)
    assert result.returncode != 0
    assert _lifecycle(commands) == []


def test_integration_uses_fresh_project_per_run(integration_runner):
    first, commands = integration_runner(project=None)
    assert first.returncode == 0, first.stderr
    ups = [c for c in commands if c.startswith("docker compose") and c.endswith("up -d")]
    downs = [c for c in commands if c.startswith("docker compose") and c.endswith("down -v")]
    assert len(ups) == len(downs) == 1
    match = re.fullmatch(r"docker compose -p (sqlalchemy-cubrid-it-\d{14}-\d+) up -d", ups[0])
    assert match, ups
    assert downs[0] == f"docker compose -p {match.group(1)} down -v"
    # The default project of a manual `docker compose up` / `make docker-up` is never used.
    assert not any(
        c.startswith("docker compose up") or c == "docker compose down -v" for c in commands
    )


def test_integration_honours_port_override(integration_runner):
    result, commands = integration_runner(make_vars=("CUBRID_PORT=33999",))
    assert result.returncode == 0, result.stderr
    assert "CUBRID_TEST_URL=cubrid://dba@localhost:33999/testdb" in commands


@pytest.mark.parametrize("test_status", [0, 7])
def test_integration_local_never_manages_docker(integration_runner, test_status):
    result, commands = integration_runner("integration-local", test=test_status)
    assert commands == [TEST, "CUBRID_TEST_URL=cubrid://dba@localhost:33000/external"]
    assert (result.returncode == 0) == (test_status == 0)


def test_integration_dry_run_does_not_execute_commands(integration_runner):
    result, commands = integration_runner(dry_run=True)
    assert result.returncode == 0
    assert commands == []
