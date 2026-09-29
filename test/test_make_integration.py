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
import signal
import subprocess
import sys
import time

import pytest

PROJECT = "sa-it-stub"
UP = f"docker compose -p {PROJECT} up -d"
DOWN = f"docker compose -p {PROJECT} down -v"
WAIT = "sleep 10"
TEST = "pytest-stub test/ -m integration -v"


@pytest.fixture(params=["sh", "bash"])
def integration_runner(request, tmp_path: Path):
    make = shutil.which("make")
    if make is None:
        pytest.skip("make is required for Makefile regression tests")
    # make runs recipes with /bin/sh (dash on Debian/Ubuntu, bash on macOS);
    # also run every case under bash explicitly.
    shell_override: list[str] = []
    if request.param == "bash":
        bash = shutil.which("bash")
        if bash is None:
            pytest.skip("bash is not installed")
        shell_override = [f"SHELL={bash}"]
    shutil.copyfile(Path(__file__).resolve().parents[1] / "Makefile", tmp_path / "Makefile")
    log = tmp_path / "commands.log"
    stub = (
        f"#!{sys.executable}\n"
        + """\
import os
from pathlib import Path
import signal
import sys
import time

name = Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ["COMMAND_LOG"], "a", encoding="utf-8") as stream:
    stream.write(" ".join([name, *args]) + "\\n")
existing = set(filter(None, os.environ.get("EXISTING", "").split(",")))
if name == "docker":
    if args[0] == "compose":
        phase = "UP" if "up" in args else "DOWN"
    else:
        # Read-only ownership probes: docker ps / volume ls / network ls with a
        # project label filter, and an unfiltered volume listing for the name.
        kind = {"ps": "container", "volume": "volume", "network": "network"}[args[0]]
        if kind == "volume" and "--filter" not in args:
            kind = "named-volume"
            for volume in filter(None, os.environ.get("OTHER_VOLUMES", "").split(",")):
                print(volume)
            if kind in existing:
                print(os.environ["PROJECT"] + "_cubrid-data")
        elif kind in existing:
            print("pre-existing-" + kind)
        if os.environ.get("FAILING_PROBE") == kind:
            sys.exit(5)
        phase = "PROBE"
elif name == "sleep":
    phase = "WAIT"
else:
    phase = "TEST"
    with open(os.environ["COMMAND_LOG"], "a", encoding="utf-8") as stream:
        stream.write("CUBRID_TEST_URL=" + os.environ.get("CUBRID_TEST_URL", "") + "\\n")
        if os.environ.get("READ_STDIN"):
            stream.write("stdin=" + sys.stdin.read().strip() + "\\n")
if phase == os.environ.get("IGNORE_TERM_PHASE"):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
if phase == "UP" and os.environ.get("UP_GRANDCHILD"):
    # Like a Compose CLI plugin process started by `docker compose`.
    import subprocess

    # UP_GRANDCHILD=slow: finish its work for a second after SIGTERM, then log;
    # UP_GRANDCHILD=ignore: ignore SIGTERM entirely.
    helper_code = {
        "slow": (
            "import os, signal, sys, time\\n"
            "def stop(*_):\\n"
            "    time.sleep(1)\\n"
            "    with open(os.environ['COMMAND_LOG'], 'a', encoding='utf-8') as stream:\\n"
            "        stream.write('UP helper finished\\\\n')\\n"
            "    sys.exit(0)\\n"
            "signal.signal(signal.SIGTERM, stop)\\n"
        ),
        "ignore": "import signal; signal.signal(signal.SIGTERM, signal.SIG_IGN)\\n",
    }.get(os.environ["UP_GRANDCHILD"], "")
    # The helper announces its pid only once its signal handling is in place.
    helper_code += (
        "import os, time\\n"
        "marker = os.environ['COMMAND_LOG'] + '.grandchild'\\n"
        "with open(marker + '.tmp', 'w', encoding='utf-8') as stream:\\n"
        "    stream.write(str(os.getpid()))\\n"
        "os.replace(marker + '.tmp', marker)\\n"
        "time.sleep(30)\\n"
    )
    subprocess.Popen([sys.executable, "-c", helper_code])
    marker = Path(os.environ["COMMAND_LOG"] + ".grandchild")
    while not marker.exists():
        time.sleep(0.01)
if phase == "DOWN":
    # Like Go programs such as docker compose, handle termination signals even
    # if the parent shell ignores them, so only process isolation protects cleanup.
    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, signal.SIG_DFL)
if phase in os.environ.get("BLOCK_PHASES", "").split(","):
    # Tell the test which shell runs the recipe (our parent) and which process
    # to check afterwards, then block until signalled or BLOCK_SECONDS pass.
    ready = Path(os.environ["COMMAND_LOG"] + "." + phase + ".ready")
    ready.write_text(f"{os.getppid()} {os.getpid()}", encoding="utf-8")
    time.sleep(float(os.environ.get(phase + "_BLOCK_SECONDS", "30")))
    with open(os.environ["COMMAND_LOG"], "a", encoding="utf-8") as stream:
        stream.write(phase + " finished\\n")
sys.exit(int(os.environ.get(phase + "_STATUS", "0")))
"""
    )
    for name in ("docker", "sleep", "pytest-stub"):
        command = tmp_path / name
        command.write_text(stub, encoding="utf-8")
        command.chmod(0o755)

    def command_and_env(
        target: str = "integration",
        *,
        dry_run: bool = False,
        project: str | None = PROJECT,
        existing: str = "",
        make_vars: tuple[str, ...] = (),
        extra_env: dict[str, str] | None = None,
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
            PROJECT=project or "",
            **{
                phase + "_STATUS": str(statuses.get(phase.lower(), 0))
                for phase in ("PROBE", "UP", "DOWN", "WAIT", "TEST")
            },
        )
        env.update(extra_env or {})
        return [
            make,
            "--no-print-directory",
            *(["-n"] if dry_run else []),
            target,
            "PYTEST=pytest-stub",
            *([f"INTEGRATION_PROJECT={project}"] if project else []),
            *make_vars,
            *shell_override,
        ], env

    def commands() -> list[str]:
        return log.read_text(encoding="utf-8").splitlines() if log.exists() else []

    def run(*args, stdin_text: str | None = None, **kwargs):
        command, env = command_and_env(*args, **kwargs)
        result = subprocess.run(
            command,
            cwd=tmp_path,
            env=env,
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return result, commands()

    def wait_ready(phase: str, process: subprocess.Popen[str]) -> tuple[int, int]:
        ready = Path(f"{log}.{phase}.ready")
        deadline = time.monotonic() + 10
        while not ready.exists() or not ready.read_text(encoding="utf-8"):
            if process.poll() is not None or time.monotonic() > deadline:
                process.kill()
                out, err = process.communicate()
                pytest.fail(f"stub never blocked at {phase}: {out}\n{err}")
            time.sleep(0.02)
        shell_pid, stub_pid = map(int, ready.read_text(encoding="utf-8").split())
        return shell_pid, stub_pid

    def start(*block_phases: str, extra_env: dict[str, str] | None = None, **kwargs):
        """Start make in its own process group; stubs block at ``block_phases``."""
        env_overrides = {"BLOCK_PHASES": ",".join(block_phases), **(extra_env or {})}
        command, env = command_and_env(extra_env=env_overrides, **kwargs)
        process = subprocess.Popen(
            command,
            cwd=tmp_path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        shell_pid, stub_pid = wait_ready(block_phases[0], process)
        return process, shell_pid, stub_pid

    run.start = start  # type: ignore[attr-defined]
    run.commands = commands  # type: ignore[attr-defined]
    run.wait_ready = wait_ready  # type: ignore[attr-defined]
    run.log = log  # type: ignore[attr-defined]
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
        "docker volume ls -q",
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


@pytest.mark.parametrize("probe", ["container", "volume", "network", "named-volume"])
def test_integration_fails_closed_when_ownership_probe_fails(integration_runner, probe):
    # A Docker error (e.g. the daemon is unreachable) is not evidence of absence.
    result, commands = integration_runner(extra_env={"FAILING_PROBE": probe})
    assert result.returncode != 0
    assert "Error 5" in result.stderr
    assert "Ownership check of Compose project" in result.stderr
    assert "nothing was started" in result.stderr
    assert "Refusing to run" not in result.stderr
    assert _lifecycle(commands) == []


def test_integration_named_volume_probe_matches_exact_name(integration_runner):
    # Only `<project>_cubrid-data` itself counts, not other volumes sharing part of it.
    others = f"{PROJECT}_cubrid-data-old,x{PROJECT}_cubrid-data,{PROJECT}-2_cubrid-data"
    result, commands = integration_runner(extra_env={"OTHER_VOLUMES": others})
    assert result.returncode == 0, result.stderr
    assert UP in commands
    result, commands = integration_runner(
        existing="named-volume", extra_env={"OTHER_VOLUMES": others}
    )
    assert result.returncode != 0
    assert "Refusing to run" in result.stderr


@pytest.mark.parametrize("project", ["Upper", "-dash", "_under", "dot.ted", "sp ace", "semi;colon"])
def test_integration_rejects_invalid_project_name(integration_runner, project):
    # Validated before any Docker command, including the read-only probes.
    result, commands = integration_runner(project=project)
    assert result.returncode != 0
    assert "Error 2" in result.stderr
    assert "INTEGRATION_PROJECT must match ^[a-z0-9][a-z0-9_-]*$" in result.stderr
    assert commands == []


def test_integration_accepts_valid_fixed_project_name(integration_runner):
    result, commands = integration_runner(project="0sa_it-x")
    assert result.returncode == 0, result.stderr
    assert "docker compose -p 0sa_it-x down -v" in commands


def test_integration_pytest_keeps_terminal_stdin(integration_runner):
    # Background jobs of a non-interactive shell otherwise read /dev/null, which
    # would break `pytest --pdb`.
    result, commands = integration_runner(
        stdin_text="from-terminal\n", extra_env={"READ_STDIN": "1"}
    )
    assert result.returncode == 0, result.stderr
    assert "stdin=from-terminal" in commands


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


def _finish(process: subprocess.Popen[str]) -> tuple[int, str]:
    try:
        _, stderr = process.communicate(timeout=15)
    except subprocess.TimeoutExpired:  # pragma: no cover - diagnostic path
        os.killpg(process.pid, signal.SIGKILL)
        _, stderr = process.communicate()
        pytest.fail(f"make did not exit after the signal: {stderr}")
    return process.returncode, stderr


def _alive(pid: int) -> bool:
    # An orphaned process may stay a zombie briefly until init reaps it.
    deadline = time.monotonic() + 5
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        if time.monotonic() > deadline:
            return True
        time.sleep(0.05)


SIGNALS = [
    pytest.param(signal.SIGINT, "SIGINT", id="INT"),
    pytest.param(signal.SIGTERM, "SIGTERM", id="TERM"),
    pytest.param(signal.SIGHUP, "SIGHUP", id="HUP"),
]


@pytest.mark.parametrize("phase", ["UP", "WAIT", "TEST"])
@pytest.mark.parametrize(("signum", "signame"), SIGNALS)
def test_integration_cleans_up_once_on_signal(integration_runner, phase, signum, signame):
    # A blocked `up -d` is given INTEGRATION_STOP_GRACE seconds to finish first.
    process, shell_pid, stub_pid = integration_runner.start(
        phase, make_vars=("INTEGRATION_STOP_GRACE=1",)
    )
    os.kill(shell_pid, signum)
    returncode, stderr = _finish(process)
    assert returncode != 0
    # make reports the recipe shell's signal-style exit status 128 + N.
    assert f"Error {128 + signum}" in stderr, stderr
    assert f"Received {signame}; cleaning up" in stderr
    lifecycle = _lifecycle(integration_runner.commands())
    assert lifecycle.count(DOWN) == 1
    assert lifecycle[-1] == DOWN
    # The blocked command was stopped before cleanup, not left running.
    assert not _alive(stub_pid)


@pytest.mark.parametrize(("signum", "signame"), SIGNALS)
def test_integration_cleans_up_once_when_process_group_is_signalled(
    integration_runner, signum, signame
):
    # Ctrl-C and a closed terminal signal the whole foreground process group:
    # make, the recipe shell and the running command all receive it.
    process, _, stub_pid = integration_runner.start("TEST")
    os.killpg(process.pid, signum)
    returncode, _ = _finish(process)
    assert returncode != 0
    assert _lifecycle(integration_runner.commands()).count(DOWN) == 1
    assert not _alive(stub_pid)


def test_integration_cleans_up_once_when_make_is_terminated(integration_runner):
    # `timeout make integration` and `kill <make pid>` signal only make, which
    # forwards SIGTERM to the recipe shell.
    process, _, stub_pid = integration_runner.start("TEST")
    os.kill(process.pid, signal.SIGTERM)
    returncode, _ = _finish(process)
    assert returncode != 0
    assert _lifecycle(integration_runner.commands()).count(DOWN) == 1
    assert not _alive(stub_pid)


@pytest.mark.parametrize("down_status", [0, 9])
def test_integration_signal_during_cleanup_does_not_repeat_it(integration_runner, down_status):
    process, shell_pid, _ = integration_runner.start(
        "TEST", "DOWN", extra_env={"DOWN_BLOCK_SECONDS": "1"}, down=down_status
    )
    os.kill(shell_pid, signal.SIGTERM)
    integration_runner.wait_ready("DOWN", process)
    # A second Ctrl-C or kill while `down -v` runs neither restarts nor aborts it.
    os.kill(shell_pid, signal.SIGINT)
    os.kill(shell_pid, signal.SIGTERM)
    returncode, stderr = _finish(process)
    assert returncode != 0
    # The first signal's status wins over the cleanup failure and later signals.
    assert "Error 143" in stderr, stderr
    assert "Received SIGINT" not in stderr
    assert _lifecycle(integration_runner.commands()).count(DOWN) == 1


@pytest.mark.parametrize(("signum", "signame"), SIGNALS)
def test_integration_group_signal_during_cleanup_does_not_abort_it(
    integration_runner, signum, signame
):
    # GNU timeout, Ctrl-C and a closed terminal signal the whole process group.
    # `docker compose down -v` must not receive that signal halfway through.
    process, _, _ = integration_runner.start("TEST", "DOWN", extra_env={"DOWN_BLOCK_SECONDS": "1"})
    os.killpg(process.pid, signal.SIGTERM)
    integration_runner.wait_ready("DOWN", process)
    os.killpg(process.pid, signum)
    returncode, stderr = _finish(process)
    assert returncode != 0
    commands = integration_runner.commands()
    assert _lifecycle(commands).count(DOWN) == 1
    assert "DOWN finished" in commands, stderr
    assert "Docker cleanup of Compose project" not in stderr


@pytest.mark.parametrize(("signum", "signame"), SIGNALS)
def test_integration_signal_during_startup_stops_its_process_group(
    integration_runner, signum, signame
):
    # `docker compose up -d` runs as its own process-group leader, so stopping
    # it (after the grace period) also stops helpers it started, such as the
    # Compose CLI plugin process.
    process, shell_pid, stub_pid = integration_runner.start(
        "UP", extra_env={"UP_GRANDCHILD": "1"}, make_vars=("INTEGRATION_STOP_GRACE=1",)
    )
    helper_pid = int(Path(f"{integration_runner.log}.grandchild").read_text(encoding="utf-8"))
    os.kill(shell_pid, signum)
    returncode, stderr = _finish(process)
    assert f"Error {128 + signum}" in stderr, stderr
    lifecycle = _lifecycle(integration_runner.commands())
    assert lifecycle == [UP, DOWN]
    assert not _alive(stub_pid)
    assert not _alive(helper_pid)


def test_integration_kills_step_that_ignores_sigterm(integration_runner):
    # A step that ignores SIGTERM is killed after INTEGRATION_STOP_GRACE seconds,
    # so cleanup cannot hang on it.
    process, shell_pid, stub_pid = integration_runner.start(
        "TEST",
        extra_env={"IGNORE_TERM_PHASE": "TEST"},
        make_vars=("INTEGRATION_STOP_GRACE=1",),
    )
    started = time.monotonic()
    os.kill(shell_pid, signal.SIGTERM)
    returncode, stderr = _finish(process)
    assert time.monotonic() - started < 10
    assert "Error 143" in stderr, stderr
    assert _lifecycle(integration_runner.commands()).count(DOWN) == 1
    assert not _alive(stub_pid)


@pytest.mark.parametrize("helper", ["slow", "ignore"])
def test_integration_waits_for_startup_helpers_before_cleanup(integration_runner, helper):
    # The Compose plugin can outlive the `docker` CLI after SIGTERM and keep
    # creating resources; `down -v` must not run until the whole startup process
    # group is gone, or those late resources would be left behind.
    process, shell_pid, stub_pid = integration_runner.start(
        "UP",
        extra_env={"UP_GRANDCHILD": helper},
        make_vars=("INTEGRATION_STOP_GRACE=1",),
    )
    helper_pid = int(Path(f"{integration_runner.log}.grandchild").read_text(encoding="utf-8"))
    os.kill(shell_pid, signal.SIGTERM)
    returncode, stderr = _finish(process)
    assert "Error 143" in stderr, stderr
    commands = integration_runner.commands()
    assert not _alive(helper_pid)
    if helper == "slow":
        assert commands.index("UP helper finished") < commands.index(DOWN)
    assert _lifecycle(commands)[-1] == DOWN


@pytest.mark.parametrize(("signum", "signame"), SIGNALS)
def test_integration_lets_startup_finish_before_cleanup(integration_runner, signum, signame):
    # The Docker daemon completes a container create even after the client is
    # killed, so interrupting `up -d` could leave a container (and a re-created,
    # unlabeled volume) behind after `down -v`. On a signal, `up -d` is left to
    # finish within INTEGRATION_STOP_GRACE seconds, and only then cleaned up.
    process, shell_pid, stub_pid = integration_runner.start(
        "UP", extra_env={"UP_BLOCK_SECONDS": "1"}, make_vars=("INTEGRATION_STOP_GRACE=10",)
    )
    started = time.monotonic()
    os.kill(shell_pid, signum)
    returncode, stderr = _finish(process)
    assert time.monotonic() - started < 8
    assert f"Error {128 + signum}" in stderr, stderr
    assert "Letting docker compose up finish" in stderr
    commands = integration_runner.commands()
    # `up -d` ran to completion (it was not sent SIGTERM), then cleanup ran once.
    assert commands.index("UP finished") < commands.index(DOWN)
    assert _lifecycle(commands).count(DOWN) == 1
    assert WAIT not in commands
    assert not _alive(stub_pid)
