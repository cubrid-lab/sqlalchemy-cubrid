"""Exercise Docker ownership and failure propagation without starting Docker.

``make integration`` runs ``scripts/run_integration.py`` (#1009). Every command
that runner starts (``docker``, the readiness wait and the pytest command) is a
logging stub on ``PATH``, so no container, volume or network is ever created or
removed. The tests drive the real Makefile target, so they cover the recipe's
variable pass-through as well as the runner.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import time

import pytest
import yaml

PROJECT = "sa-it-stub"
UP = f"docker compose -p {PROJECT} up -d"
DOWN = f"docker compose -p {PROJECT} down -v"
WAIT = "wait-stub"
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
    root = Path(__file__).resolve().parents[1]
    shutil.copyfile(root / "Makefile", tmp_path / "Makefile")
    (tmp_path / "scripts").mkdir()
    for script in ("run_integration.py", "report_test_results.py"):
        shutil.copyfile(root / "scripts" / script, tmp_path / "scripts" / script)
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
        phase = (
            "UP" if "up" in args else "LOGS" if "logs" in args
            else "CONFIG" if "config" in args else "DOWN"
        )
        if phase == "LOGS":
            print("cubrid service log line " + os.environ.get("LOG_SECRET", ""))
        if phase == "CONFIG":
            # Like Compose: exported variable, then .env in the project directory, then 11.2.
            tag = os.environ.get("CUBRID_VERSION", "")
            dotenv = Path(".env")
            if not tag and dotenv.exists():
                for line in dotenv.read_text(encoding="utf-8").splitlines():
                    if line.startswith("CUBRID_VERSION="):
                        tag = line.split("=", 1)[1]
            print('{"services": {"cubrid": {"image": "cubrid/cubrid:' + (tag or "11.2") + '"}}}')
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
elif name == "wait-stub":
    phase = "WAIT"
else:
    phase = "TEST"
    cases = os.environ.get("JUNIT_CASES", "pass")
    for arg in args:
        if arg.startswith("--junitxml=") and cases != "none":
            body = {
                "fail": '<testcase classname="t" name="f"><failure message="'
                + os.environ.get("JUNIT_MESSAGE", "")
                + '">t</failure></testcase>',
                "pass": '<testcase classname="t" name="a"/>',
                "skip": '<testcase classname="t" name="s"><skipped type="pytest.skip" message="x"/></testcase>',
            }[cases]
            Path(arg.split("=", 1)[1]).write_text(
                '<?xml version="1.0"?><testsuites><testsuite name="pytest">'
                + body
                + "</testsuite></testsuites>",
                encoding="utf-8",
            )
    with open(os.environ["COMMAND_LOG"], "a", encoding="utf-8") as stream:
        stream.write("CUBRID_TEST_URL=" + os.environ.get("CUBRID_TEST_URL", "") + "\\n")
        if os.environ.get("READ_STDIN"):
            stream.write("stdin=" + sys.stdin.read().strip() + "\\n")
if phase == "UP" and os.environ.get("LOG_UP_PORT"):
    # The host port Compose interpolates into docker-compose.yml.
    with open(os.environ["COMMAND_LOG"], "a", encoding="utf-8") as stream:
        stream.write("up CUBRID_TEST_PORT=" + os.environ.get("CUBRID_TEST_PORT", "") + "\\n")
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
    for name in ("docker", "wait-stub", "pytest-stub"):
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
        for key in (
            "MAKEFLAGS",
            "MFLAGS",
            "MAKEOVERRIDES",
            "CUBRID_PORT",
            "CUBRID_TEST_PORT",
            "INTEGRATION_PROJECT",
            "INTEGRATION_DRIVER",
        ):
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
            "WAIT_FOR_CUBRID=wait-stub",
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

    def start(
        *block_phases: str,
        extra_env: dict[str, str] | None = None,
        ignore_sigint: bool = False,
        **kwargs,
    ):
        """Start make in its own process group; stubs block at ``block_phases``.

        ``ignore_sigint`` starts make with SIGINT ignored, as a background job of
        a non-interactive shell is.
        """
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
            preexec_fn=(lambda: signal.signal(signal.SIGINT, signal.SIG_IGN))
            if ignore_sigint
            else None,
        )
        shell_pid, stub_pid = wait_ready(block_phases[0], process)
        return process, shell_pid, stub_pid

    run.start = start  # type: ignore[attr-defined]
    run.commands = commands  # type: ignore[attr-defined]
    run.wait_ready = wait_ready  # type: ignore[attr-defined]
    run.log = log  # type: ignore[attr-defined]
    return run


def _lifecycle(commands: list[str]) -> list[str]:
    """Drop the probes and the service-log read; keep the lifecycle commands.

    The ``--junitxml`` argument the runner appends to the test command is dropped too.
    """
    return [
        re.sub(r" --junitxml=\S+$", "", command)
        for command in commands
        if not command.startswith(("docker ps", "docker volume", "docker network"))
        and " logs " not in command
        and " config " not in command
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
        "CUBRID_TEST_URL=cubrid+pycubrid://dba@localhost:33000/testdb",
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


def test_integration_refuses_a_pre_existing_11_4_database_volume(integration_runner):
    # The 11.4 database volume is the project's too (#1000): a kept one must survive.
    others = f"{PROJECT}_cubrid-databases-old,x{PROJECT}_cubrid-databases"
    result, commands = integration_runner(extra_env={"OTHER_VOLUMES": others})
    assert result.returncode == 0, result.stderr
    assert UP in commands
    result, commands = integration_runner(
        extra_env={"OTHER_VOLUMES": f"{others},{PROJECT}_cubrid-databases"}
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


@pytest.mark.parametrize("source", ["make", "env"])
def test_integration_honours_port_override(integration_runner, source):
    result, commands = integration_runner(
        make_vars=("CUBRID_TEST_PORT=33999",) if source == "make" else (),
        extra_env={
            "LOG_UP_PORT": "1",
            **({"CUBRID_TEST_PORT": "33999"} if source == "env" else {}),
        },
    )
    assert result.returncode == 0, result.stderr
    assert "up CUBRID_TEST_PORT=33999" in commands
    assert "CUBRID_TEST_URL=cubrid+pycubrid://dba@localhost:33999/testdb" in commands
    assert "deprecated" not in result.stderr


@pytest.mark.parametrize("source", ["make", "env"])
def test_integration_honours_the_deprecated_port_variable(integration_runner, source):
    # CUBRID_PORT, the name before #1008, still selects the port, with a warning.
    result, commands = integration_runner(
        make_vars=("CUBRID_PORT=33998",) if source == "make" else (),
        extra_env={"LOG_UP_PORT": "1", **({"CUBRID_PORT": "33998"} if source == "env" else {})},
    )
    assert result.returncode == 0, result.stderr
    assert "up CUBRID_TEST_PORT=33998" in commands
    assert "CUBRID_TEST_URL=cubrid+pycubrid://dba@localhost:33998/testdb" in commands
    assert "CUBRID_PORT is deprecated; use CUBRID_TEST_PORT" in result.stderr


def test_integration_prefers_cubrid_test_port_over_the_deprecated_name(integration_runner):
    result, commands = integration_runner(
        make_vars=("CUBRID_TEST_PORT=33999",),
        extra_env={"LOG_UP_PORT": "1", "CUBRID_PORT": "33998"},
    )
    assert result.returncode == 0, result.stderr
    assert "up CUBRID_TEST_PORT=33999" in commands
    assert "CUBRID_TEST_URL=cubrid+pycubrid://dba@localhost:33999/testdb" in commands
    assert "deprecated" not in result.stderr


@pytest.mark.parametrize(
    ("driver", "url"),
    [
        ("pycubrid", "cubrid+pycubrid://dba@localhost:33000/testdb"),
        ("cubriddb", "cubrid://dba@localhost:33000/testdb"),
    ],
)
def test_integration_driver_selects_test_url(integration_runner, driver, url):
    # pycubrid (the recommended driver) is the default; cubriddb runs the same
    # suite through the CUBRIDdb C extension (#575).
    result, commands = integration_runner(make_vars=(f"INTEGRATION_DRIVER={driver}",))
    assert result.returncode == 0, result.stderr
    assert f"CUBRID_TEST_URL={url}" in commands
    assert f"(driver: {driver})" in result.stdout


@pytest.mark.parametrize("driver", ["", "CUBRIDdb", "cubrid", "pycubrid ", "x;y"])
def test_integration_rejects_unknown_driver(integration_runner, driver):
    # Validated before any Docker command, including the read-only probes.
    result, commands = integration_runner(make_vars=(f"INTEGRATION_DRIVER={driver}",))
    assert result.returncode != 0
    assert "Error 2" in result.stderr
    assert "INTEGRATION_DRIVER must be pycubrid or cubriddb" in result.stderr
    assert commands == []


@pytest.mark.parametrize("test_status", [0, 7])
def test_integration_local_never_manages_docker(integration_runner, test_status):
    result, commands = integration_runner("integration-local", test=test_status)
    assert commands == [TEST, "CUBRID_TEST_URL=cubrid://dba@localhost:33000/external"]
    assert (result.returncode == 0) == (test_status == 0)


def test_integration_dry_run_does_not_execute_commands(integration_runner):
    result, commands = integration_runner(dry_run=True)
    assert result.returncode == 0
    assert commands == []


def test_integration_waits_for_readiness_instead_of_a_fixed_sleep():
    # #575: a fixed 10 s sleep let the suite start before a fresh container's
    # database and broker were up. Check the real default command (make -n runs
    # nothing).
    make = shutil.which("make")
    if make is None:
        pytest.skip("make is required for Makefile regression tests")
    env = os.environ.copy()
    for key in ("MAKEFLAGS", "MFLAGS", "MAKEOVERRIDES", "INTEGRATION_READY_TIMEOUT"):
        env.pop(key, None)
    result = subprocess.run(
        [make, "--no-print-directory", "-n", "integration", "INTEGRATION_READY_TIMEOUT=42"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "python3 -m scripts.wait_for_cubrid --timeout 42" in result.stdout
    assert "sleep 10" not in result.stdout


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


def test_integration_cleans_up_when_a_step_cannot_start(integration_runner):
    # Like `set -e` on a shell's "command not found", the run fails with 127 and
    # still removes what it started.
    result, commands = integration_runner(make_vars=("WAIT_FOR_CUBRID=/nonexistent/wait",))
    assert "Error 127" in result.stderr
    assert _lifecycle(commands) == [UP, DOWN]


def test_integration_recipe_runs_the_runner_as_its_only_process(integration_runner):
    # The recipe execs scripts/run_integration.py, so no shell sits between make
    # and the runner: make's forwarded SIGTERM reaches the process that cleans up.
    process, runner_pid, _ = integration_runner.start("TEST", extra_env={"TEST_BLOCK_SECONDS": "1"})
    args = subprocess.run(
        ["ps", "-o", "ppid=,args=", "-p", str(runner_pid)],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.split()
    returncode, stderr = _finish(process)
    assert returncode == 0, stderr
    assert args, "runner exited before ps could inspect it"
    assert int(args[0]) == process.pid
    assert "scripts/run_integration.py" in args


def test_integration_keeps_a_signal_ignored_at_entry_ignored(integration_runner):
    # Like a shell trap, the runner cannot handle a signal that was already
    # ignored when make started; the run continues and cleans up normally.
    process, runner_pid, _ = integration_runner.start(
        "TEST", extra_env={"TEST_BLOCK_SECONDS": "1"}, ignore_sigint=True
    )
    os.kill(runner_pid, signal.SIGINT)
    returncode, stderr = _finish(process)
    assert returncode == 0, stderr
    assert "Received SIGINT" not in stderr
    commands = integration_runner.commands()
    assert "TEST finished" in commands
    assert _lifecycle(commands).count(DOWN) == 1


def test_integration_kills_a_startup_group_that_ignores_sigterm(integration_runner):
    # After the grace period, a `docker compose up -d` group that ignores SIGTERM
    # gets SIGKILL another grace period later, so cleanup cannot hang on it.
    process, runner_pid, stub_pid = integration_runner.start(
        "UP",
        extra_env={"IGNORE_TERM_PHASE": "UP"},
        make_vars=("INTEGRATION_STOP_GRACE=1",),
    )
    started = time.monotonic()
    os.kill(runner_pid, signal.SIGTERM)
    returncode, stderr = _finish(process)
    assert time.monotonic() - started < 10
    assert "Error 143" in stderr, stderr
    assert _lifecycle(integration_runner.commands()) == [UP, DOWN]
    assert not _alive(stub_pid)


def test_compose_registers_the_database_for_a_stable_host() -> None:
    """The image records CUBRID_DB_HOST (else the container ID) on the volume (#997)."""
    root = Path(__file__).resolve().parents[1]
    compose = yaml.safe_load((root / "docker-compose.yml").read_text())
    environment = compose["services"]["cubrid"]["environment"]
    assert environment["CUBRID_DB"] == "testdb"
    assert environment["CUBRID_DB_HOST"] == "localhost"


def test_compose_service_contract() -> None:
    """One service, ``cubrid``, with ``testdb``, a SQL health check and no fixed name (#1008)."""
    root = Path(__file__).resolve().parents[1]
    compose = yaml.safe_load((root / "docker-compose.yml").read_text())
    assert list(compose["services"]) == ["cubrid"]
    service = compose["services"]["cubrid"]
    assert service["image"] == "cubrid/cubrid:${CUBRID_VERSION:-11.2}"
    assert service["environment"]["CUBRID_DB"] == "testdb"
    assert service["healthcheck"]["test"] == [
        "CMD",
        "csql",
        "-u",
        "dba",
        "testdb",
        "-c",
        "SELECT 1",
    ]
    # Run-owned make integration projects must not collide on a container name.
    assert "container_name" not in service


def test_compose_publishes_the_broker_on_loopback_only() -> None:
    """``CUBRID_TEST_PORT`` (deprecated fallback ``CUBRID_PORT``) on 127.0.0.1 (#1008)."""
    root = Path(__file__).resolve().parents[1]
    compose = yaml.safe_load((root / "docker-compose.yml").read_text())
    assert compose["services"]["cubrid"]["ports"] == [
        "127.0.0.1:${CUBRID_TEST_PORT:-${CUBRID_PORT:-33000}}:33000"
    ]


def test_compose_keeps_every_image_database_directory_in_a_named_volume() -> None:
    """Images up to 11.3 keep databases in /var/lib/cubrid, 11.4 elsewhere (#1000)."""
    root = Path(__file__).resolve().parents[1]
    compose = yaml.safe_load((root / "docker-compose.yml").read_text())
    mounts = dict(volume.split(":", 1)[::-1] for volume in compose["services"]["cubrid"]["volumes"])
    assert mounts == {
        "/var/lib/cubrid": "cubrid-data",
        "/home/cubrid/CUBRID/databases": "cubrid-databases",
    }
    assert set(compose["volumes"]) == {"cubrid-data", "cubrid-databases"}


def test_fix_db_host_rewrites_only_the_testdb_host(tmp_path: Path) -> None:
    """Run the target's in-container script against a local databases.txt (#997)."""
    make = shutil.which("make")
    if make is None:
        pytest.skip("make is required for Makefile regression tests")
    databases = tmp_path / "databases"
    databases.mkdir()
    listing = databases / "databases.txt"
    listing.write_text(
        "#db-name\tvol-path\t\tdb-host\t\tlog-path\t\tlob-base-path\n"
        "testdb\t\t/var/lib/cubrid/testdb\tee2bfa1105f9\t/var/lib/cubrid/testdb\t"
        "file:/var/lib/cubrid/testdb/lob\n"
        "otherdb\t/var/lib/cubrid/otherdb\tee2bfa1105f9\t/var/lib/cubrid/otherdb\t"
        "file:/var/lib/cubrid/otherdb/lob\n"
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "docker.log"
    docker = bin_dir / "docker"
    # Log the call, then run the `sh -c` script locally as `docker compose exec` would.
    docker.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$*" >> "$REVIEW_LOG"\n'
        'while [ "$#" -gt 0 ] && [ "$1" != "-c" ]; do shift; done\n'
        'exec sh -c "$2"\n'
    )
    docker.chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    env["REVIEW_LOG"] = str(log)
    env["CUBRID_DATABASES"] = str(databases)
    env["TMPDIR"] = str(tmp_path)
    makefile = Path(__file__).resolve().parents[1] / "Makefile"
    listing.chmod(0o640)
    os.utime(listing, (1_000_000_000, 1_000_000_000))
    inode = listing.stat().st_ino

    def fix() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [make, "-f", str(makefile), "docker-fix-db-host"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
        )

    result = fix()

    assert result.returncode == 0, result.stderr
    # Rewritten in place, so the owner and mode the server relies on are kept.
    assert listing.stat().st_ino == inode
    assert stat.S_IMODE(listing.stat().st_mode) == 0o640
    backup = databases / "databases.txt.before-fix-db-host"
    # cp -p: the backup keeps the original's mode and timestamp.
    assert stat.S_IMODE(backup.stat().st_mode) == 0o640
    assert backup.stat().st_mtime == 1_000_000_000
    assert log.read_text().startswith("compose exec -T -u root cubrid sh -c ")
    original = (databases / "databases.txt.before-fix-db-host").read_text()
    assert original.splitlines()[1].split()[2] == "ee2bfa1105f9"
    lines = listing.read_text().splitlines()
    assert lines[0] == "#db-name\tvol-path\t\tdb-host\t\tlog-path\t\tlob-base-path"
    assert lines[1].split() == [
        "testdb",
        "/var/lib/cubrid/testdb",
        "localhost",
        "/var/lib/cubrid/testdb",
        "file:/var/lib/cubrid/testdb/lob",
    ]
    assert lines[2].split()[2] == "ee2bfa1105f9"
    assert "localhost" in result.stdout
    assert sorted(path.name for path in tmp_path.iterdir()) == ["bin", "databases", "docker.log"]
    assert sorted(path.name for path in databases.iterdir()) == [
        "databases.txt",
        "databases.txt.before-fix-db-host",
    ]
    # A second run keeps the first backup, the only record of the stale host.
    assert fix().returncode == 0
    assert backup.read_text() == original


# --- Result files (#1020) ----------------------------------------------------

RESULTS = Path("test-results") / "integration"


def _results(tmp_path: Path) -> Path:
    return tmp_path / RESULTS


def _summary(tmp_path: Path) -> dict:
    import json

    return json.loads((_results(tmp_path) / "summary.json").read_text(encoding="utf-8"))


def test_integration_writes_results_and_a_matching_console_line(integration_runner, tmp_path):
    result, _ = integration_runner()
    assert result.returncode == 0, result.stderr
    summary = _summary(tmp_path)
    assert summary["status"] == "PASS"
    assert summary["lane"] == "integration"
    assert summary["executed"] is True
    assert summary["counts"]["passed"] == 1
    assert (_results(tmp_path) / "junit.xml").is_file()
    assert not (_results(tmp_path) / "service.log").exists()
    # The last console line is derived from summary.json.
    last = result.stdout.strip().splitlines()[-1]
    assert last.startswith("integration: PASS; 1 selected, 1 passed")
    assert last.endswith(str(_results(tmp_path) / "summary.json"))
    import json

    environment = json.loads((_results(tmp_path) / "environment.json").read_text("utf-8"))
    assert environment["lane"] == "integration"
    assert environment["command"] == "make integration INTEGRATION_DRIVER=pycubrid"
    assert environment["cubrid_version"] == "11.2"
    assert environment["driver"]["name"] == "pycubrid"
    for key in ("python", "platform", "sqlalchemy"):
        assert environment[key]


def test_integration_results_never_contain_a_credential(integration_runner, tmp_path):
    secret = "topsecret-1020"
    result, _ = integration_runner(
        test=7,
        extra_env={
            "CUBRID_PASSWORD": secret,
            "CUBRID_TEST_URL": f"cubrid+pycubrid://dba:{secret}@localhost:33000/external",
            "CUBRID_TEST_AURL": f"cubrid+pycubrid://dba:{secret}@localhost:33000/external",
        },
    )
    assert result.returncode != 0
    files = [path for path in _results(tmp_path).rglob("*") if path.is_file()]
    assert {path.name for path in files} >= {"summary.json", "environment.json", "junit.xml"}
    for path in files:
        assert secret not in path.read_text(encoding="utf-8"), path


def test_integration_failing_tests_are_fail_and_save_the_service_log(integration_runner, tmp_path):
    result, commands = integration_runner(test=7)
    assert result.returncode != 0
    summary = _summary(tmp_path)
    assert summary["status"] == "FAIL"
    assert summary["pytest_exit_code"] == 7
    assert "cubrid service log line" in (_results(tmp_path) / "service.log").read_text("utf-8")
    assert commands[-1] == DOWN


def test_integration_service_log_failure_never_skips_cleanup(integration_runner, tmp_path):
    result, commands = integration_runner(test=7, extra_env={"LOGS_STATUS": "5"})
    assert result.returncode != 0
    assert commands.count(DOWN) == 1
    assert _summary(tmp_path)["status"] == "FAIL"


def test_integration_cleanup_failure_is_fail_even_when_tests_passed(integration_runner, tmp_path):
    result, _ = integration_runner(down=9)
    assert result.returncode != 0
    summary = _summary(tmp_path)
    assert summary["status"] == "FAIL"
    assert summary["pytest_exit_code"] == 9
    assert "docker cleanup failed" in summary["problems"]


def test_integration_setup_failure_is_fail_without_junit(integration_runner, tmp_path):
    result, _ = integration_runner(wait=6)
    assert result.returncode != 0
    assert _summary(tmp_path)["status"] == "FAIL"
    assert not (_results(tmp_path) / "junit.xml").exists()


@pytest.mark.parametrize("cases", ["skip", "none"])
def test_integration_a_lane_that_proved_nothing_is_incomplete(integration_runner, tmp_path, cases):
    # Exit 0 from pytest, but every test skipped or no JUnit file: never PASS.
    result, _ = integration_runner(extra_env={"JUNIT_CASES": cases})
    assert result.returncode != 0
    assert _summary(tmp_path)["status"] == "INCOMPLETE"
    assert _summary(tmp_path)["executed"] is (False if cases == "skip" else None)


def test_integration_clears_a_previous_pass_once_it_owns_the_project(integration_runner, tmp_path):
    results = _results(tmp_path)
    results.mkdir(parents=True)
    for name in ("summary.json", "junit.xml", "service.log", "environment.json"):
        (results / name).write_text("previous run", encoding="utf-8")
    result, _ = integration_runner(extra_env={"JUNIT_CASES": "none"})
    assert result.returncode != 0
    assert (results / "summary.json").read_text("utf-8") != "previous run"
    assert not (results / "service.log").exists()
    assert not (results / "junit.xml").exists()


@pytest.mark.parametrize("existing", ["container", "named-volume"])
def test_integration_refusal_replaces_a_previous_pass(integration_runner, tmp_path, existing):
    results = _results(tmp_path)
    results.mkdir(parents=True)
    (results / "summary.json").write_text('{"status": "PASS"}', encoding="utf-8")
    (results / "junit.xml").write_text("stale", encoding="utf-8")
    result, commands = integration_runner(existing=existing)
    assert result.returncode != 0
    assert not any(command.startswith("docker compose") for command in commands)
    summary = _summary(tmp_path)
    assert summary["status"] == "FAIL"
    assert any("refused to run" in problem for problem in summary["problems"])
    assert not (results / "junit.xml").exists()


def test_integration_failed_ownership_probe_replaces_a_previous_pass(integration_runner, tmp_path):
    results = _results(tmp_path)
    results.mkdir(parents=True)
    (results / "summary.json").write_text('{"status": "PASS"}', encoding="utf-8")
    result, _ = integration_runner(extra_env={"FAILING_PROBE": "volume"})
    assert "failed (status 5)" in result.stderr
    assert result.returncode != 0
    assert _summary(tmp_path)["status"] == "FAIL"


@pytest.mark.parametrize(
    ("make_vars", "reason"),
    [
        (("INTEGRATION_DRIVER=oracle",), "INTEGRATION_DRIVER"),
        (("INTEGRATION_PROJECT=Bad",), "PROJECT"),
    ],
)
def test_integration_rejected_arguments_leave_a_fail_summary(
    integration_runner, tmp_path, make_vars, reason
):
    results = _results(tmp_path)
    results.mkdir(parents=True)
    (results / "summary.json").write_text('{"status": "PASS"}', encoding="utf-8")
    result, commands = integration_runner(make_vars=make_vars)
    assert result.returncode != 0
    assert commands == []
    summary = _summary(tmp_path)
    assert summary["status"] == "FAIL"
    assert any(reason in problem for problem in summary["problems"])


def test_integration_local_writes_no_results(integration_runner, tmp_path):
    result, _ = integration_runner("integration-local")
    assert result.returncode == 0, result.stderr
    assert not _results(tmp_path).exists()


def test_integration_redacts_secrets_from_junit_and_service_log(integration_runner, tmp_path):
    secret = "p@ss/w&rd<1>"
    quoted = "p%40ss%2Fw%26rd%3C1%3E"
    escaped = "p@ss/w&amp;rd&lt;1&gt;"
    result, _ = integration_runner(
        test=7,
        extra_env={
            "CUBRID_PASSWORD": secret,
            "CUBRID_URL": f"cubrid+pycubrid://dba:{quoted}@localhost:33000/x",
            "JUNIT_CASES": "fail",
            "JUNIT_MESSAGE": f"login {escaped} failed with {quoted} and {secret}",
            "LOG_SECRET": f"{secret} {quoted}",
        },
    )
    assert result.returncode != 0
    texts = [path.read_text("utf-8") for path in _results(tmp_path).iterdir()]
    assert any("login ***" in text for text in texts)
    assert any("cubrid service log line" in text for text in texts)
    for text in texts:
        for form in (secret, quoted, escaped, "w&rd"):
            assert form not in text


def test_integration_records_the_version_compose_resolves(integration_runner, tmp_path):
    import json

    (tmp_path / ".env").write_text("CUBRID_VERSION=10.2\n", encoding="utf-8")
    result, _ = integration_runner()
    assert result.returncode == 0, result.stderr
    environment = json.loads((_results(tmp_path) / "environment.json").read_text("utf-8"))
    assert environment["cubrid_version"] == "10.2"
    # An exported variable wins over .env, as in Compose.
    result, _ = integration_runner(extra_env={"CUBRID_VERSION": "11.4"})
    environment = json.loads((_results(tmp_path) / "environment.json").read_text("utf-8"))
    assert environment["cubrid_version"] == "11.4"


def test_integration_collects_the_service_log_after_a_cleanup_only_failure(
    integration_runner, tmp_path
):
    result, commands = integration_runner(down=9)
    assert result.returncode != 0
    assert any(" logs " in command for command in commands)
    assert "cubrid service log line" in (_results(tmp_path) / "service.log").read_text("utf-8")
    assert _summary(tmp_path)["status"] == "FAIL"
