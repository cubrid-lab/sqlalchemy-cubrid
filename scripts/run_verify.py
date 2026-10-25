"""Run ``make verify``'s phases and always write its summary (#1018, #1020).

The ``verify`` Make recipe is a single ``exec`` of this script, so a signal that make
forwards to its recipe reaches it directly. It runs ``make check``, ``make test`` and
``make integration`` one after another and stops at the first failing phase; the phases after it are recorded as not run. The phases are not Make
prerequisites, so even ``make -j`` never starts a later phase early.

The phases stay in the caller's process group, so a terminal keeps them in the foreground
and a Ctrl-C reaches them as it would without this runner. On SIGINT, SIGTERM or SIGHUP the
first signal is also forwarded to the running phase's make, which passes it on to its
recipe (``make integration`` execs ``scripts/run_integration.py``, which then cleans up its
Compose project once, however many signals it gets). The runner waits for that phase to finish,
starts no further phase, writes the summary and exits 128 + the signal number. Later
signals are only recorded. A signal already ignored when the run starts stays ignored.

Afterwards, whatever happened, ``scripts/report_test_results.py aggregate`` writes
``<results-dir>/summary.json`` with the lanes' JUnit files and the live
``environment.json``. The exit status is that of the first failing phase, or 1 when every
phase exited 0 but the summary is not ``PASS``.
"""

from __future__ import annotations

import argparse
import importlib.util
import signal
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from types import FrameType, ModuleType

ROOT = Path(__file__).resolve().parent.parent
PHASES = ("check", "test", "integration")
HANDLED_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)


class _State:
    # The first handled signal; it decides the exit status.
    received: signal.Signals | None = None
    # The running phase's make, which a signal is forwarded to.
    active: subprocess.Popen[bytes] | None = None


def _on_signal(signum: int, frame: FrameType | None) -> None:
    if _State.received is not None:
        return
    _State.received = signal.Signals(signum)
    print(f"Received {_State.received.name}; stopping make verify", file=sys.stderr, flush=True)
    if _State.active is not None and _State.active.poll() is None:
        _State.active.send_signal(signum)


def _run_phase(make: str, phase: str) -> int:
    """Run ``make <phase>``; return a shell-style status (128 + N when killed by N)."""
    try:
        process = subprocess.Popen(  # nosec B603 - argv from the Makefile, no shell
            [make, "--no-print-directory", phase]
        )
    except OSError as exc:
        print(f"{make}: {exc.strerror or exc}", file=sys.stderr, flush=True)
        return 127 if isinstance(exc, FileNotFoundError) else 126
    _State.active = process
    try:
        # A signal that arrived while the phase was starting is forwarded now.
        if _State.received is not None:
            process.send_signal(_State.received)
        returncode = process.wait()
    finally:
        _State.active = None
    return 128 - returncode if returncode < 0 else returncode


def _reporter() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "run_verify_reporter", ROOT / "scripts" / "report_test_results.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n", 1)[0])
    parser.add_argument("--make", required=True, help="the make program to run each phase")
    parser.add_argument("--results-dir", required=True, type=Path, help="verify results")
    parser.add_argument("--test-results", required=True, type=Path, help="make test results")
    parser.add_argument(
        "--integration-results", required=True, type=Path, help="make integration results"
    )
    args = parser.parse_args(argv)

    for signum in HANDLED_SIGNALS:
        if signal.getsignal(signum) is not signal.SIG_IGN:
            signal.signal(signum, _on_signal)

    status = 0
    exits: dict[str, int | None] = dict.fromkeys(PHASES)
    for phase in PHASES:
        if status or _State.received is not None:
            break
        exits[phase] = status = _run_phase(args.make, phase)
    if _State.received is not None:
        status = 128 + _State.received

    lanes = {"test": args.test_results, "integration": args.integration_results}
    command = ["aggregate", "--output", str(args.results_dir / "summary.json")]
    for phase in PHASES:
        code = exits[phase]
        value = "not-run" if code is None else str(code)
        if phase in lanes:
            value += f":{lanes[phase] / 'summary.json'}"
            # Only a lane that ran this time contributes its JUnit file.
            if code is not None:
                command += ["--copy-junit", f"{phase}={lanes[phase] / 'junit.xml'}"]
        command += ["--phase", f"{phase}={value}"]
    if exits["integration"] is not None:
        command += ["--environment", str(args.integration_results / "environment.json")]
    try:
        summary_status = int(_reporter().main(command))
    except Exception as exc:  # noqa: BLE001 - reporting must never hide the phase status
        print(f"ERROR: could not write the verify summary: {exc}", file=sys.stderr, flush=True)
        summary_status = 1
    return status or summary_status


if __name__ == "__main__":
    raise SystemExit(main())
