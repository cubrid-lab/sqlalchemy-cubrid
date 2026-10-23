"""Run ``make integration`` in a fresh, run-owned Docker Compose project (#1009).

The ``integration`` Make recipe is a single call to this script, which owns the
lifecycle the recipe used to spell out in shell (#575, #593, #1000):

1. Validate ``--driver`` (``pycubrid`` or ``cubriddb``) and ``--project``
   (``^[a-z0-9][a-z0-9_-]*$``; default ``sqlalchemy-cubrid-it-<timestamp>-<pid>``).
   An invalid value exits 2 before any Docker command.
2. Check that the project owns nothing yet: no container, volume or network with
   its Compose label and no volume named exactly ``<project>_cubrid-data`` or
   ``<project>_cubrid-databases``. Anything found exits 1 ("Refusing to run");
   a failing probe exits with its status. Nothing is started or removed then.
3. ``docker compose -p <project> up -d`` with ``CUBRID_PORT`` exported, as the
   leader of its own process group, so a terminal Ctrl-C does not reach it.
4. The readiness wait (``--wait``) and the test command (``--test``), with
   ``CUBRID_TEST_URL`` pointing at the run-owned server through the driver.
5. ``docker compose -p <project> down -v`` in its own session, whatever happened.

Exit status: the first failing step's status (a step killed by signal N counts
as 128 + N). A cleanup failure is reported and fails an otherwise successful
run, but never hides an earlier failure.

On SIGINT, SIGTERM or SIGHUP the run stops the running step and cleans up once,
then exits 128 + the signal number. A ``docker compose up -d`` in progress is
first given ``--stop-grace`` seconds to finish (the daemon completes a container
create even after the client is killed), then its process group gets SIGTERM,
and cleanup waits until the whole group, including the Compose plugin process,
is gone. Any other step gets SIGTERM at once and SIGKILL after ``--stop-grace``
seconds. Later signals are ignored until cleanup has finished. A signal already
ignored when the run starts stays ignored, as it would for a shell trap.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from collections.abc import Sequence
from types import FrameType

URL_SCHEMES = {"pycubrid": "cubrid+pycubrid", "cubriddb": "cubrid"}
PROJECT_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]*")
HANDLED_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
# Volumes of docker-compose.yml: images up to 11.3 keep databases in cubrid-data,
# the 11.4 image in cubrid-databases (#1000).
DATA_VOLUMES = ("cubrid-data", "cubrid-databases")


class Interrupted(Exception):
    """Raised from the signal handler to unwind out of a waiting step."""


class _State:
    # The first handled signal; it decides the exit status.
    received: signal.Signals | None = None
    # True only while waiting for a step, so the handler never raises elsewhere.
    armed = False
    announced = False


def _on_signal(signum: int, frame: FrameType | None) -> None:
    if _State.received is None:
        _State.received = signal.Signals(signum)
    if _State.armed:
        _State.armed = False
        raise Interrupted


def _announce() -> None:
    """Report the first handled signal once, before anything is stopped."""
    if _State.received is not None and not _State.announced:
        _State.announced = True
        _err(f"Received {_State.received.name}; cleaning up")


def _shell_status(returncode: int) -> int:
    """Report a step killed by signal N as a shell would: 128 + N."""
    return 128 - returncode if returncode < 0 else returncode


def _err(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _start_failed(command: Sequence[str], exc: OSError) -> int:
    """Report a command that could not start; return the status a shell would."""
    _err(f"{command[0]}: {exc.strerror or exc}")
    return 127 if isinstance(exc, FileNotFoundError) else 126


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:  # pragma: no cover - a reused id we cannot signal
        return True
    return True


def _signal_group(pgid: int, signum: int) -> None:
    try:
        os.killpg(pgid, signum)
    except (ProcessLookupError, PermissionError):
        pass


def _wait_group(pgid: int, grace: float) -> None:
    """Wait until no process is left in ``pgid``; SIGKILL it after ``grace`` seconds.

    The Compose plugin can outlive the ``docker`` CLI that started it, so cleanup
    must not start before the whole group is gone.
    """
    deadline = time.monotonic() + grace
    while _group_alive(pgid) and time.monotonic() < deadline:
        time.sleep(0.1)
    if _group_alive(pgid):
        _signal_group(pgid, signal.SIGKILL)
    while _group_alive(pgid) and time.monotonic() < deadline + 5:
        time.sleep(0.1)


def _stop_startup(process: subprocess.Popen[bytes], grace: float) -> None:
    """Let ``docker compose up -d`` finish, then stop its whole process group."""
    _err(
        f"Letting docker compose up finish (up to {grace:g}s) so that cleanup sees "
        "everything it created"
    )
    try:
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        _signal_group(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            _signal_group(process.pid, signal.SIGKILL)
            process.wait()
    _wait_group(process.pid, grace)


def _stop_step(process: subprocess.Popen[bytes], grace: float) -> None:
    """SIGTERM a running step at once and SIGKILL it after ``grace`` seconds."""
    if process.poll() is None:
        try:
            process.terminate()
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def _run_step(
    command: Sequence[str], env: dict[str, str], grace: float, *, startup: bool = False
) -> int:
    """Run one lifecycle step; on a handled signal, stop it and raise ``Interrupted``.

    ``startup`` runs the command as the leader of a new process group. Other steps
    stay in the caller's process group, so a terminal Ctrl-C also reaches them.
    """
    if _State.received is not None:
        _announce()
        raise Interrupted
    try:
        process = subprocess.Popen(  # nosec B603 - argv from the Makefile, no shell
            list(command), env=env, process_group=0 if startup else None
        )
    except OSError as exc:
        return _start_failed(command, exc)
    try:
        _State.armed = True
        # A signal that arrived while the step was being started is only recorded.
        if _State.received is not None:
            _State.armed = False
            raise Interrupted
        status = process.wait()
    except Interrupted:
        _announce()
        if startup:
            _stop_startup(process, grace)
        else:
            _stop_step(process, grace)
        raise
    finally:
        _State.armed = False
    return _shell_status(status)


def _probe(command: Sequence[str], project: str) -> list[str]:
    try:
        completed = subprocess.run(  # nosec B603 B607 - fixed docker argv
            list(command), stdout=subprocess.PIPE, text=True, check=False
        )
        status = _shell_status(completed.returncode)
    except OSError as exc:
        status = _start_failed(command, exc)
    if status:
        _err(
            f"Ownership check of Compose project '{project}' failed (status {status}); "
            "nothing was started."
        )
        raise SystemExit(status)
    return [line for line in completed.stdout.splitlines() if line]


def _owns_nothing(project: str) -> bool:
    """Return True when Compose project ``project`` has no resources yet.

    A failing probe (e.g. an unreachable daemon) is not evidence of absence: it
    exits with the probe's status before anything is started.
    """
    label = f"label=com.docker.compose.project={project}"
    found = _probe(["docker", "ps", "-aq", "--filter", label], project)
    found += _probe(["docker", "volume", "ls", "-q", "--filter", label], project)
    found += _probe(["docker", "network", "ls", "-q", "--filter", label], project)
    # An unlabeled volume with the project's exact data-volume name counts too.
    names = {f"{project}_{volume}" for volume in DATA_VOLUMES}
    found += [name for name in _probe(["docker", "volume", "ls", "-q"], project) if name in names]
    return not found


def _cleanup(project: str, env: dict[str, str]) -> int:
    """Run ``down -v`` in its own session, so no group signal can abort it."""
    command = ["docker", "compose", "-p", project, "down", "-v"]
    try:
        returncode = subprocess.call(  # nosec B603 B607 - fixed docker compose argv
            command, env=env, start_new_session=True
        )
        status = _shell_status(returncode)
    except OSError as exc:
        status = _start_failed(command, exc)
    if status:
        _err(f"Docker cleanup of Compose project '{project}' failed (status {status})")
    return status


def _lifecycle(args: argparse.Namespace, project: str, env: dict[str, str]) -> int:
    status = _run_step(
        ["docker", "compose", "-p", project, "up", "-d"], env, args.stop_grace, startup=True
    )
    if status:
        return status
    test_env = {
        **env,
        "CUBRID_TEST_URL": f"{URL_SCHEMES[args.driver]}://dba@localhost:{args.port}/testdb",
    }
    print(f"Waiting for CUBRID to be ready (up to {args.ready_timeout}s)...", flush=True)
    for command in (args.wait, args.test):
        status = _run_step(shlex.split(command), test_env, args.stop_grace)
        if status:
            return status
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n", 1)[0])
    parser.add_argument("--driver", required=True, help="pycubrid or cubriddb")
    parser.add_argument("--port", required=True, help="host port of the run-owned CUBRID")
    parser.add_argument("--project", default="", help="fixed Compose project name")
    parser.add_argument("--ready-timeout", default="180", help="seconds, for the message")
    parser.add_argument("--stop-grace", type=float, default=10.0, help="seconds")
    parser.add_argument("--wait", required=True, help="readiness command")
    parser.add_argument("--test", required=True, help="test command")
    args = parser.parse_args(argv)

    if args.driver not in URL_SCHEMES:
        _err(
            f"INTEGRATION_DRIVER must be pycubrid or cubriddb (got '{args.driver}'); "
            "nothing was started."
        )
        return 2
    project = args.project
    if project and not PROJECT_PATTERN.fullmatch(project):
        _err(
            f"INTEGRATION_PROJECT must match ^[a-z0-9][a-z0-9_-]*$ (got '{project}'); "
            "nothing was started."
        )
        return 2
    project = project or f"sqlalchemy-cubrid-it-{time.strftime('%Y%m%d%H%M%S')}-{os.getpid()}"

    if not _owns_nothing(project):
        _err(
            f"Refusing to run: Compose project '{project}' already has containers, volumes or networks."
        )
        _err(
            "make integration only starts and removes a project it creates; nothing was started or removed."
        )
        return 1

    env = {**os.environ, "CUBRID_PORT": args.port}
    # Cleanup is registered only now, after the ownership check passed.
    for signum in HANDLED_SIGNALS:
        if signal.getsignal(signum) is not signal.SIG_IGN:
            signal.signal(signum, _on_signal)
    print(
        f"Using run-owned Compose project '{project}' on host port {args.port} "
        f"(driver: {args.driver})",
        flush=True,
    )
    status = 1
    try:
        status = _lifecycle(args, project, env)
    except Interrupted:
        status = 0
    finally:
        # Also after an unexpected error, which then propagates (exit status 1).
        if _State.received is not None:
            _announce()
            status = 128 + _State.received
        # Cleanup runs once: further signals are ignored until it has finished.
        for signum in HANDLED_SIGNALS:
            signal.signal(signum, signal.SIG_IGN)
        cleanup_status = _cleanup(project, env)
    return status or cleanup_status


if __name__ == "__main__":
    raise SystemExit(main())
