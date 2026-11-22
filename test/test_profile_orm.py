"""Offline coverage for the ORM profiler's dialect hotspot selection (#1041)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

SPEC = importlib.util.spec_from_file_location(
    "profile_orm",
    Path(__file__).resolve().parents[1] / "scripts" / "profile_orm.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
# The module defines ORM classes with `Mapped[...]` annotations, which SQLAlchemy
# resolves through ``sys.modules[cls.__module__]``; register it before executing.
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class _FakeStats:
    """Stand-in for ``pstats.Stats``: ``_top_dialect_hotspots`` only reads ``.stats``."""

    def __init__(self, stats: dict[tuple[str, int, str], tuple[Any, ...]]) -> None:
        self.stats = stats


def _entry(
    primitive_calls: int,
    total_calls: int,
    self_time: float,
    cumulative_time: float,
) -> tuple[Any, ...]:
    """One ``pstats`` value: (primitive calls, total calls, self, cumulative, callers)."""
    return (primitive_calls, total_calls, self_time, cumulative_time, {})


def test_only_dialect_modules_are_kept_and_labeled_with_line_and_function() -> None:
    compiler = MODULE.DIALECT_MODULES["compiler.py"]
    dialect = MODULE.DIALECT_MODULES["dialect.py"]
    stats = _FakeStats(
        {
            (compiler, 10, "visit_select"): _entry(3, 4, 0.01, 0.5),
            (dialect, 20, "do_execute"): _entry(1, 1, 0.2, 0.5),
            (
                "/venv/lib/python3.12/site-packages/sqlalchemy/engine/base.py",
                9,
                "execute",
            ): _entry(1, 1, 0.9, 9.0),
            (
                "/venv/lib/python3.12/site-packages/pycubrid/connection.py",
                5,
                "cursor",
            ): _entry(1, 1, 1.0, 2.0),
            ("<built-in>", 0, "method 'connect'"): _entry(1, 1, 1.0, 1.0),
            ("<string>", 1, "<module>"): _entry(1, 1, 1.0, 1.0),
        }
    )

    hotspots = MODULE._top_dialect_hotspots(stats)

    # Same cumulative time, so the larger self time wins.
    assert [hotspot.function for hotspot in hotspots] == [
        "dialect.py:20:do_execute",
        "compiler.py:10:visit_select",
    ]
    assert hotspots[0].cumulative_time_s == 0.5
    assert hotspots[0].self_time_s == 0.2
    assert hotspots[0].calls == 1
    assert hotspots[0].primitive_calls == 1
    # total calls is the second tuple item, primitive calls the first.
    assert hotspots[1].calls == 4
    assert hotspots[1].primitive_calls == 3


def test_empty_stats_table_yields_no_hotspots() -> None:
    assert MODULE._top_dialect_hotspots(_FakeStats({})) == []


def test_results_are_ordered_by_cumulative_time_and_capped_at_max_results() -> None:
    compiler = MODULE.DIALECT_MODULES["compiler.py"]
    stats = _FakeStats(
        {(compiler, index, f"f{index}"): _entry(1, 1, 0.0, float(index)) for index in range(7)}
    )

    hotspots = MODULE._top_dialect_hotspots(stats)

    assert MODULE.MAX_RESULTS == 5
    assert [hotspot.function for hotspot in hotspots] == [
        "compiler.py:6:f6",
        "compiler.py:5:f5",
        "compiler.py:4:f4",
        "compiler.py:3:f3",
        "compiler.py:2:f2",
    ]


@pytest.mark.parametrize("pseudo_file", ["<string>", "<built-in>", "<frozen importlib._bootstrap>"])
def test_normalized_path_returns_pseudo_file_names_unchanged(pseudo_file: str) -> None:
    assert MODULE._normalized_path(pseudo_file) == pseudo_file


# --- #1401: the profiler only creates, clears and drops a table it owns -----------------

from sqlalchemy import create_engine as _create_engine  # noqa: E402
from sqlalchemy import inspect as _inspect  # noqa: E402
from sqlalchemy import text as _text  # noqa: E402


def _run_main(monkeypatch: pytest.MonkeyPatch, dsn: str, output: Path) -> None:
    argv = [
        "profile_orm.py",
        "--dsn",
        dsn,
        "--crud-loops",
        "1",
        "--bulk-count",
        "2",
        "--bulk-rounds",
        "1",
        "--select-rounds",
        "1",
        "--select-seed-count",
        "2",
        "--compile-loops",
        "1",
        "--output",
        str(output),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    MODULE.main()


def _table_names(dsn: str) -> list[str]:
    engine = _create_engine(dsn)
    try:
        return _inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_existing_bench_users_table_is_left_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dsn = f"sqlite:///{tmp_path / 'user.db'}"
    engine = _create_engine(dsn)
    with engine.begin() as connection:
        connection.execute(_text("CREATE TABLE bench_users (id INTEGER PRIMARY KEY, name TEXT)"))
        connection.execute(_text("INSERT INTO bench_users (id, name) VALUES (1, 'sentinel')"))
    engine.dispose()

    with pytest.raises(SystemExit, match="already exists"):
        _run_main(monkeypatch, dsn, tmp_path / "report.json")

    engine = _create_engine(dsn)
    with engine.connect() as connection:
        rows = connection.execute(_text("SELECT id, name FROM bench_users")).all()
    engine.dispose()
    assert rows == [(1, "sentinel")]
    assert not (tmp_path / "report.json").exists()


def test_fresh_run_creates_and_drops_only_its_own_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dsn = f"sqlite:///{tmp_path / 'scratch.db'}"
    # The compile workload renders CUBRID's ON DUPLICATE KEY UPDATE, which SQLite cannot compile.
    monkeypatch.setattr(MODULE, "_run_compile_workload", lambda *_args: None)
    _run_main(monkeypatch, dsn, tmp_path / "report.json")

    assert "bench_users" not in _table_names(dsn)
    assert (tmp_path / "report.json").exists()


def test_failed_workload_drops_owned_table_and_keeps_the_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dsn = f"sqlite:///{tmp_path / 'scratch.db'}"

    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("workload failed")

    monkeypatch.setattr(MODULE, "_run_bulk_insert", boom)
    with pytest.raises(RuntimeError, match="workload failed"):
        _run_main(monkeypatch, dsn, tmp_path / "report.json")

    assert "bench_users" not in _table_names(dsn)


def test_cleanup_error_does_not_hide_the_workload_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dsn = f"sqlite:///{tmp_path / 'scratch.db'}"

    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("workload failed")

    def broken_drop(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("drop failed")

    monkeypatch.setattr(MODULE, "_run_bulk_insert", boom)
    monkeypatch.setattr(MODULE.Base.metadata, "drop_all", broken_drop)
    with pytest.raises(RuntimeError, match="workload failed"):
        _run_main(monkeypatch, dsn, tmp_path / "report.json")

    assert "could not drop 'bench_users': drop failed" in capsys.readouterr().err


def test_table_created_after_the_check_is_not_reused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dsn = f"sqlite:///{tmp_path / 'race.db'}"
    engine = _create_engine(dsn)
    with engine.begin() as connection:
        connection.execute(_text("CREATE TABLE bench_users (id INTEGER PRIMARY KEY, name TEXT)"))
        connection.execute(_text("INSERT INTO bench_users (id, name) VALUES (1, 'sentinel')"))
    engine.dispose()

    class _StaleInspector:
        """Simulates another process creating the table right after the existence check."""

        def has_table(self, _name: str) -> bool:
            return False

    monkeypatch.setattr(MODULE, "inspect", lambda _engine: _StaleInspector())
    with pytest.raises(Exception, match="already exists"):
        _run_main(monkeypatch, dsn, tmp_path / "report.json")

    engine = _create_engine(dsn)
    with engine.connect() as connection:
        rows = connection.execute(_text("SELECT id, name FROM bench_users")).all()
    engine.dispose()
    assert rows == [(1, "sentinel")]
