# test/test_check_not_all_skipped.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Offline tests for ``scripts/check_not_all_skipped.py`` (#486)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import check_not_all_skipped as mod


class TestEvaluate:
    def test_passed_only_is_ok(self) -> None:
        ok, message = mod.evaluate("============== 9 passed in 10.03s ==============")
        assert ok
        assert "9 test(s) actually ran" in message

    def test_passed_and_skipped_is_ok(self) -> None:
        ok, message = mod.evaluate("===== 5 passed, 3 skipped in 1.23s =====")
        assert ok
        assert "5 test(s) actually ran" in message

    def test_failed_and_passed_is_ok(self) -> None:
        ok, message = mod.evaluate("===== 1 failed, 2 passed in 1.00s =====")
        assert ok
        assert "3 test(s) actually ran" in message

    def test_xfailed_counts_as_real_execution(self) -> None:
        ok, _ = mod.evaluate("===== 2 xfailed in 1.00s =====")
        assert ok

    def test_all_skipped_is_not_ok(self) -> None:
        ok, message = mod.evaluate("============== 9 skipped in 0.20s ==============")
        assert not ok
        assert "skipped or deselected" in message

    def test_all_deselected_is_not_ok(self) -> None:
        ok, message = mod.evaluate("============== 9 deselected in 0.13s ==============")
        assert not ok
        assert "skipped or deselected" in message

    def test_no_tests_ran_is_not_ok(self) -> None:
        ok, message = mod.evaluate("============== no tests ran in 0.01s ==============")
        assert not ok
        assert "zero tests" in message

    def test_missing_summary_line_is_not_ok(self) -> None:
        ok, message = mod.evaluate("some unrelated log output\nwith no pytest summary at all\n")
        assert not ok
        assert "could not find" in message

    def test_summary_line_without_known_outcomes_is_not_ok(self) -> None:
        ok, message = mod.evaluate("============== interrupted ==============")
        assert not ok
        assert "could not parse outcome counts" in message

    def test_last_summary_line_wins_over_short_summary_header(self) -> None:
        log = (
            "=========================== short test summary info ============================\n"
            "FAILED test_foo.py::test_bar - AssertionError\n"
            "===== 1 failed, 2 passed in 1.00s =====\n"
        )
        ok, message = mod.evaluate(log)
        assert ok
        assert "3 test(s) actually ran" in message

    def test_errors_outcome_counts_as_real_execution(self) -> None:
        ok, _ = mod.evaluate("===== 2 errors in 1.00s =====")
        assert ok


class TestMain:
    def _write(self, tmp_path: Path, name: str, body: str) -> str:
        path = tmp_path / name
        path.write_text(body, encoding="utf-8")
        return str(path)

    def test_exit_zero_when_tests_ran(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        log = self._write(tmp_path, "run.log", "===== 9 passed in 1.00s =====")
        assert mod.main([log, "--label", "my lane"]) == 0
        out = capsys.readouterr().out
        assert "my lane" in out

    def test_exit_one_when_all_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        log = self._write(tmp_path, "run.log", "===== 9 skipped in 1.00s =====")
        assert mod.main([log]) == 1
        err = capsys.readouterr().err
        assert "::error::" in err
        assert "proved nothing" in err

    def test_allow_all_skipped_overrides_failure(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        log = self._write(tmp_path, "run.log", "===== 9 skipped in 1.00s =====")
        assert mod.main([log, "--allow-all-skipped", "driver not installed on purpose"]) == 0
        out = capsys.readouterr().out
        assert "allowed (driver not installed on purpose)" in out

    def test_combines_multiple_logfiles(self, tmp_path: Path) -> None:
        all_skipped = self._write(tmp_path, "a.log", "===== 9 skipped in 1.00s =====")
        all_passed = self._write(tmp_path, "b.log", "===== 2 passed in 1.00s =====")
        # Combined, the second file's real pass proves the overall step ran.
        assert mod.main([all_skipped, all_passed]) == 0

    def test_default_label_is_the_logfile_paths(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        log = self._write(tmp_path, "run.log", "===== 9 passed in 1.00s =====")
        assert mod.main([log]) == 0
        assert log in capsys.readouterr().out
