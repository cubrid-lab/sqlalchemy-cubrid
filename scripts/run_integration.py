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
3. ``docker compose -p <project> up -d`` with ``CUBRID_TEST_PORT`` exported, as the
   leader of its own process group, so a terminal Ctrl-C does not reach it.
4. The readiness wait (``--wait``) and the test command (``--test``), with
   ``CUBRID_TEST_URL`` pointing at the run-owned server through the driver.
5. ``docker compose -p <project> down -v`` in its own session, whatever happened.
6. With ``--results-dir`` (#1020), the result files described below.

Exit status: the first failing step's status (a step killed by signal N counts
as 128 + N). A cleanup failure is reported and fails an otherwise successful
run, but never hides an earlier failure.

Results (``--results-dir``, ``test-results/integration`` for ``make integration``): the
test command gets ``--junitxml=<dir>/junit.xml`` appended. Once the run owns the project
the directory's previous files are removed; after cleanup the runner writes
``environment.json`` and ``summary.json`` through ``scripts/report_test_results.py`` (the
reporter of ``make test``, loaded by path), so the summary carries the final exit status:
a cleanup failure is ``FAIL``, and a run that exits 0 without a JUnit file or with every
test skipped is ``INCOMPLETE``, never ``PASS``. A run refused or rejected before it owns
the project replaces any previous summary with a ``FAIL`` one that names the reason, so a
stale ``PASS`` never survives. After a failing run ``service.log`` holds the CUBRID
container log; saving it is best effort and never prevents ``down -v``. A reporting
problem is a warning and never changes the exit status. Run one ``make integration`` per
results directory at a time (the live suite already requires one run at a time).

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
import html
import importlib.util
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
import urllib.parse
from collections.abc import Sequence
from pathlib import Path
from types import FrameType, ModuleType

URL_SCHEMES = {"pycubrid": "cubrid+pycubrid", "cubriddb": "cubrid"}
PROJECT_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]*")
HANDLED_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
# Volumes of docker-compose.yml: images up to 11.3 keep databases in cubrid-data,
# the 11.4 image in cubrid-databases (#1000).
DATA_VOLUMES = ("cubrid-data", "cubrid-databases")
ROOT = Path(__file__).resolve().parent.parent
# Files a run writes into --results-dir besides the pytest JUnit file.
RESULT_FILES = ("junit.xml", "summary.json", "environment.json", "service.log")
LOG_TIMEOUT = 60.0
# Environment variables that may carry a database URL with a password.
URL_VARIABLES = ("CUBRID_TEST_URL", "CUBRID_TEST_AURL", "CUBRID_URL")


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


def _secrets() -> list[str]:
    """The configured secrets (CUBRID_PASSWORD, URL passwords) in every written form."""
    raw = [os.environ.get("CUBRID_PASSWORD", "")]
    for name in URL_VARIABLES:
        try:
            raw.append(urllib.parse.urlsplit(os.environ.get(name, "")).password or "")
        except ValueError:
            continue
    forms: set[str] = set()
    for secret in filter(None, raw):
        for form in (secret, urllib.parse.unquote(secret), urllib.parse.quote(secret, safe="")):
            forms.add(form)
            forms.add(html.escape(form))
            forms.add(html.escape(form, quote=False))
    return sorted(filter(None, forms), key=len, reverse=True)


def _sanitize_results(args: argparse.Namespace) -> None:
    """Replace the configured secrets in junit.xml and service.log with ``***``."""
    secrets = _secrets()
    if not args.results_dir or not secrets:
        return
    for name in ("junit.xml", "service.log"):
        path = ROOT / args.results_dir / name
        try:
            data = path.read_bytes()
            for secret in secrets:
                data = data.replace(secret.encode(), b"***")
            path.write_bytes(data)
        except FileNotFoundError:
            continue
        except OSError as exc:
            _err(f"WARNING: could not sanitize {path}: {exc}")
            path.unlink(missing_ok=True)


def _cubrid_version(project: str, env: dict[str, str]) -> str:
    """The CUBRID image tag Compose resolves (exported env, then .env, then the default)."""
    command = ["docker", "compose", "-p", project, "config", "--format", "json"]
    try:
        completed = subprocess.run(  # nosec B603 B607 - fixed docker compose argv
            command, env=env, stdout=subprocess.PIPE, text=True, timeout=LOG_TIMEOUT, check=False
        )
        image = json.loads(completed.stdout)["services"]["cubrid"]["image"]
        tag = image.rsplit("/", 1)[-1].partition(":")[2]
        if completed.returncode == 0 and tag:
            return tag
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        pass
    return os.environ.get("CUBRID_VERSION") or "unknown"


def _report(
    args: argparse.Namespace, status: int, reason: str = "", cubrid_version: str = ""
) -> int:
    """Write environment.json and summary.json; return 0 unless the summary is not PASS.

    A reporting failure only warns and returns 0, so it never changes the exit status.
    """
    if not args.results_dir:
        return 0
    results = ROOT / args.results_dir
    try:
        spec = importlib.util.spec_from_file_location(
            "run_integration_reporter", ROOT / "scripts" / "report_test_results.py"
        )
        assert spec is not None and spec.loader is not None
        reporter: ModuleType = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reporter)
        reporter.main(
            [
                "environment",
                "--lane", "integration",
                "--command", args.command,
                "--cubrid-version", cubrid_version or os.environ.get("CUBRID_VERSION") or "unknown",
                "--driver", args.driver if args.driver in URL_SCHEMES else "unknown",
                "--output", str(results / "environment.json"),
            ]
        )  # fmt: skip
        summarize = [
            "--lane", "integration",
            "--junit", str(results / "junit.xml"),
            "--pytest-exit", str(status),
            "--output", str(results / "summary.json"),
            "--require-executed",
        ]  # fmt: skip
        if reason:
            summarize += ["--reason", reason]
        return int(reporter.main(summarize))
    except Exception as exc:  # noqa: BLE001 - reporting must never change the status
        _err(f"WARNING: could not write the result summary: {exc}")
        return 0


def _clear_results(args: argparse.Namespace) -> None:
    """Remove a previous run's files, so a stale PASS cannot outlive this run."""
    if not args.results_dir:
        return
    results = ROOT / args.results_dir
    try:
        results.mkdir(parents=True, exist_ok=True)
        for name in RESULT_FILES:
            (results / name).unlink(missing_ok=True)
    except OSError as exc:
        _err(f"WARNING: could not prepare {results}: {exc}")


def _save_service_log(args: argparse.Namespace, project: str, env: dict[str, str]) -> None:
    """Save the CUBRID container log next to the results; best effort."""
    if not args.results_dir:
        return
    try:
        with (ROOT / args.results_dir / "service.log").open("wb") as log:
            subprocess.run(  # nosec B603 B607 - fixed docker compose argv
                ["docker", "compose", "-p", project, "logs", "--no-color", "cubrid"],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=LOG_TIMEOUT,
                check=False,
                start_new_session=True,
            )
    except (OSError, subprocess.SubprocessError) as exc:
        _err(f"WARNING: could not save the service log: {exc}")


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
    test = shlex.split(args.test)
    if args.results_dir:
        test.append(f"--junitxml={ROOT / args.results_dir / 'junit.xml'}")
    for command in (shlex.split(args.wait), test):
        status = _run_step(command, test_env, args.stop_grace)
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
    parser.add_argument("--results-dir", default="", help="write junit.xml, summary.json, ... here")
    parser.add_argument(
        "--command", default="make integration", help="recorded in environment.json"
    )
    args = parser.parse_args(argv)

    if args.driver not in URL_SCHEMES:
        _err(
            f"INTEGRATION_DRIVER must be pycubrid or cubriddb (got '{args.driver}'); "
            "nothing was started."
        )
        _clear_results(args)
        _report(args, 2, "invalid INTEGRATION_DRIVER; nothing was started")
        return 2
    project = args.project
    if project and not PROJECT_PATTERN.fullmatch(project):
        _err(
            f"INTEGRATION_PROJECT must match ^[a-z0-9][a-z0-9_-]*$ (got '{project}'); "
            "nothing was started."
        )
        _clear_results(args)
        _report(args, 2, "invalid INTEGRATION_PROJECT; nothing was started")
        return 2
    project = project or f"sqlalchemy-cubrid-it-{time.strftime('%Y%m%d%H%M%S')}-{os.getpid()}"

    try:
        owns_nothing = _owns_nothing(project)
    except SystemExit as exc:  # a failed read-only ownership probe
        _clear_results(args)
        _report(args, int(exc.code or 1), "ownership check failed; nothing was started")
        raise
    if not owns_nothing:
        _err(
            f"Refusing to run: Compose project '{project}' already has containers, volumes or networks."
        )
        _err(
            "make integration only starts and removes a project it creates; nothing was started or removed."
        )
        _clear_results(args)
        _report(args, 1, f"project '{project}' already has resources; refused to run")
        return 1

    _clear_results(args)
    env = {**os.environ, "CUBRID_TEST_PORT": args.port}
    cubrid_version = _cubrid_version(project, env)
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
        cleanup_status = 0
        try:
            if status:
                _save_service_log(args, project, env)
        finally:
            # The log is best effort; teardown is guaranteed.
            cleanup_status = _cleanup(project, env)
        if cleanup_status and not status:
            # Tests passed but teardown failed: collect from whatever remains.
            _save_service_log(args, project, env)
        _sanitize_results(args)
        # Last, so the summary carries the final status, cleanup included.
        reason = "docker cleanup failed" if cleanup_status and not status else ""
        summary_status = _report(args, status or cleanup_status, reason, cubrid_version)
    # A zero exit with a summary that is not PASS (INCOMPLETE) still fails the run.
    return status or cleanup_status or summary_status


if __name__ == "__main__":
    raise SystemExit(main())
