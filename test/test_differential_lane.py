# test/test_differential_lane.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Offline checks for the required driver-differential lane (#486).

Runs ``test/test_driver_differential.py`` in a child pytest with no database
so every comparison skips: without ``CUBRID_REQUIRE_DRIVER_DIFFERENTIAL`` the
run must stay green (local offline runs), and with it the run must fail.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import report_driver_versions

_ROOT = Path(__file__).resolve().parent.parent
_FLAG = "CUBRID_REQUIRE_DRIVER_DIFFERENTIAL"


def _run_differential(require: bool) -> subprocess.CompletedProcess[str]:
    env = {
        k: v
        for k, v in os.environ.items()
        # CI=true would make conftest.py refuse the unconfigured integration run (#593).
        if k not in ("CI", "CUBRID_TEST_URL", _FLAG) and not k.startswith("COV_CORE_")
    }
    if require:
        env[_FLAG] = "1"
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "test/test_driver_differential.py",
            "-p",
            "no:cacheprovider",
        ],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_all_skipped_differential_passes_without_flag() -> None:
    proc = _run_differential(require=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert " skipped" in proc.stdout
    assert " passed" not in proc.stdout


def test_all_skipped_differential_fails_with_flag() -> None:
    proc = _run_differential(require=True)
    assert proc.returncode == pytest.ExitCode.TESTS_FAILED, proc.stdout + proc.stderr
    assert f"{_FLAG}=1 but no test_driver_differential.py case ran" in proc.stdout


def test_version_report_without_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    summary = tmp_path / "summary.md"
    monkeypatch.delenv("CUBRID_TEST_URL", raising=False)
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("CUBRIDDB_SOURCE_REF", "v0.0.0-test")

    assert report_driver_versions.main() == 0

    out = capsys.readouterr().out
    for label in ("Python:", "SQLAlchemy:", "pycubrid:", "CUBRIDdb (cubrid_python):"):
        assert label in out
    assert "CUBRIDdb source ref: v0.0.0-test" in out
    assert "CUBRID server via pycubrid: CUBRID_TEST_URL not set" in out
    assert "| CUBRID server via CUBRIDdb | `CUBRID_TEST_URL not set` |" in summary.read_text()
