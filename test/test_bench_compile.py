"""Offline coverage for the compiler microbenchmark CLI."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "bench_compile",
    Path(__file__).resolve().parents[1] / "scripts/bench_compile.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize("iterations", ["0", "-1"])
def test_nonpositive_iterations_fail_with_usage_error(
    iterations: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        MODULE.main(["--iterations", iterations])

    assert excinfo.value.code == 2
    error = capsys.readouterr().err
    assert "usage:" in error
    assert "must be a positive integer" in error


def test_small_positive_iteration_count_generates_benchmark_table(
    capsys: pytest.CaptureFixture[str],
) -> None:
    MODULE.main(["--iterations", "1"])

    output = capsys.readouterr().out
    assert "Benchmarking CUBRID dialect compilation (1 iteration each)" in output
    assert "SELECT + LIMIT/OFFSET" in output
    assert "INSERT (simple)" in output
    assert "INSERT ON DUPLICATE KEY UPDATE" in output
    assert "SELECT FOR UPDATE" in output
    assert "Done. Compare results before/after optimization attempts." in output


def test_two_iterations_use_plural_label(
    capsys: pytest.CaptureFixture[str],
) -> None:
    MODULE.main(["--iterations", "2"])

    output = capsys.readouterr().out
    assert "Benchmarking CUBRID dialect compilation (2 iterations each)" in output
