from __future__ import annotations

import asyncio
from typing import Any

import pytest


@pytest.fixture
def bdb() -> Any:
    # The script imports pycubrid at module level; the repo/offline lanes do
    # not install the pycubrid extra, so the module is skipped there.
    pytest.importorskip("pycubrid")
    from scripts import bench_dialect_baseline

    return bench_dialect_baseline


def test_summary_returns_expected_statistics(bdb: Any) -> None:
    values = [10.0, 20.0, 30.0]

    result = bdb.summary(values)

    assert result["median"] == 20.0
    assert result["min"] == 10.0
    assert result["max"] == 30.0
    assert result["q1"] == 15.0
    assert result["q3"] == 25.0
    assert result["trials"] == values


def test_summary_handles_single_value(bdb: Any) -> None:
    values = [42.0]

    result = bdb.summary(values)

    assert result["median"] == 42.0
    assert result["min"] == 42.0
    assert result["max"] == 42.0
    assert result["q1"] == 42.0
    assert result["q3"] == 42.0
    assert result["trials"] == values


def test_us_converts_median_nanoseconds_to_microseconds(bdb: Any) -> None:
    assert bdb.us([1000, 2000, 3000]) == 2.0


@pytest.mark.parametrize(
    ("items", "trial", "expected"),
    [
        (["A", "B", "C"], 0, ["A", "B", "C"]),
        (["A", "B", "C"], 1, ["B", "C", "A"]),
        (["A", "B", "C"], 4, ["B", "C", "A"]),
    ],
)
def test_rotate_moves_items_by_trial(
    bdb: Any,
    items: list[str],
    trial: int,
    expected: list[str],
) -> None:
    original = items.copy()

    result = bdb.rotate(items, trial)

    assert result == expected
    assert items == original


# --- #1402: the baseline only creates and drops a table it owns ---------------------------


def _sqlite_engine(tmp_path: Any, with_sentinel: bool) -> Any:
    from sqlalchemy import create_engine, text

    engine = create_engine(f"sqlite:///{tmp_path / 'baseline.db'}")
    if with_sentinel:
        with engine.begin() as conn:
            conn.execute(
                text("CREATE TABLE bench_dialect_baseline (id INTEGER PRIMARY KEY, note TEXT)")
            )
            conn.execute(
                text("INSERT INTO bench_dialect_baseline (id, note) VALUES (1, 'sentinel')")
            )
    return engine


def _rows(engine: Any) -> list[Any]:
    from sqlalchemy import text

    with engine.connect() as conn:
        return conn.execute(text("SELECT id, note FROM bench_dialect_baseline")).all()


class _FakeAsyncConn:
    """Runs AsyncConnection.run_sync callbacks on a real sync SQLite connection."""

    def __init__(self, sync_conn: Any) -> None:
        self._sync_conn = sync_conn

    async def run_sync(self, fn: Any, *args: Any) -> Any:
        return fn(self._sync_conn, *args)


class _FakeAsyncEngine:
    """Minimal AsyncEngine stand in: connect() and begin() over a sync engine."""

    def __init__(self, engine: Any) -> None:
        self._engine = engine

    def connect(self) -> Any:
        return self._context(self._engine.connect())

    def begin(self) -> Any:
        return self._context(self._engine.begin())

    @staticmethod
    def _context(sync_cm: Any) -> Any:
        class _Ctx:
            async def __aenter__(self) -> _FakeAsyncConn:
                return _FakeAsyncConn(sync_cm.__enter__())

            async def __aexit__(self, *exc: Any) -> bool:
                return bool(sync_cm.__exit__(*exc))

        return _Ctx()


def test_claim_table_refuses_an_existing_table(bdb: Any, tmp_path: Any) -> None:
    engine = _sqlite_engine(tmp_path, with_sentinel=True)
    with pytest.raises(SystemExit, match="already exists"):
        bdb.claim_table(engine)
    assert _rows(engine) == [(1, "sentinel")]
    engine.dispose()


def test_claim_table_does_not_reuse_a_table_created_after_the_check(
    bdb: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _sqlite_engine(tmp_path, with_sentinel=True)

    class _StaleInspector:
        def has_table(self, _name: str) -> bool:
            return False

    monkeypatch.setattr(bdb, "inspect", lambda _conn: _StaleInspector())
    with pytest.raises(Exception, match="already exists"):
        bdb.claim_table(engine)
    assert _rows(engine) == [(1, "sentinel")]
    engine.dispose()


def test_claim_and_drop_touch_only_the_owned_table(bdb: Any, tmp_path: Any) -> None:
    from sqlalchemy import inspect

    engine = _sqlite_engine(tmp_path, with_sentinel=False)
    bdb.claim_table(engine)
    assert inspect(engine).has_table(bdb.TABLE)
    bdb.drop_owned_table(engine, keep_original_error=False)
    assert not inspect(engine).has_table(bdb.TABLE)
    engine.dispose()


def test_drop_error_is_a_warning_when_the_run_already_failed(
    bdb: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    engine = _sqlite_engine(tmp_path, with_sentinel=False)

    def broken_drop(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("drop failed")

    monkeypatch.setattr(bdb.Base.metadata, "drop_all", broken_drop)
    bdb.drop_owned_table(engine, keep_original_error=True)
    assert "could not drop 'bench_dialect_baseline': drop failed" in capsys.readouterr().err
    with pytest.raises(OSError, match="drop failed"):
        bdb.drop_owned_table(engine, keep_original_error=False)
    engine.dispose()


def test_async_claim_table_refuses_an_existing_table(bdb: Any, tmp_path: Any) -> None:
    engine = _sqlite_engine(tmp_path, with_sentinel=True)
    with pytest.raises(SystemExit, match="already exists"):
        asyncio.run(bdb.async_claim_table(_FakeAsyncEngine(engine)))
    assert _rows(engine) == [(1, "sentinel")]
    engine.dispose()


def test_async_claim_and_drop_touch_only_the_owned_table(bdb: Any, tmp_path: Any) -> None:
    from sqlalchemy import inspect

    engine = _sqlite_engine(tmp_path, with_sentinel=False)
    fake = _FakeAsyncEngine(engine)
    asyncio.run(bdb.async_claim_table(fake))
    assert inspect(engine).has_table(bdb.TABLE)
    asyncio.run(bdb.async_drop_owned_table(fake, keep_original_error=False))
    assert not inspect(engine).has_table(bdb.TABLE)
    engine.dispose()


# --- #1402: run_sync and run_async end to end, on SQLite with the CUBRID pieces faked ------------


def _patch_common(bdb: Any, monkeypatch: pytest.MonkeyPatch, fail_at: str | None) -> type:
    class _Raw:
        closed = False

        def close(self) -> None:
            _Raw.closed = True

        def commit(self) -> None:
            pass

    def reset(*_args: Any, **_kwargs: Any) -> None:
        if fail_at == "reset":
            raise RuntimeError("workload failed")

    async def async_reset(*_args: Any, **_kwargs: Any) -> None:
        reset()

    async def async_value(*_args: Any, **_kwargs: Any) -> int:
        return 1

    monkeypatch.setattr(bdb, "check", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(bdb, "environment", lambda *_args: {"env": "fake"})
    monkeypatch.setattr(bdb, "reset", reset)
    monkeypatch.setattr(bdb, "async_reset", async_reset)
    for name in ("bench_select_pk", "bench_fetch_all", "bench_reflect", "bench_batch"):
        monkeypatch.setattr(bdb, name, lambda *_args, **_kwargs: 1)
    for name in ("async_select_pk", "async_fetch_all", "async_batch"):
        monkeypatch.setattr(bdb, name, async_value)
    if fail_at == "startup":

        def broken_connector(_engine: Any) -> Any:
            def connect() -> Any:
                raise ConnectionError("raw connect failed")

            return connect

        async def broken_aio_connect(**_kwargs: Any) -> Any:
            raise ConnectionError("raw connect failed")

        monkeypatch.setattr(bdb, "raw_connector", broken_connector)
        monkeypatch.setattr(bdb.pycubrid.aio, "connect", broken_aio_connect)
    else:

        async def aio_connect(**_kwargs: Any) -> Any:
            raw = _Raw()

            class _AsyncRaw:
                async def close(self) -> None:
                    raw.close()

                async def commit(self) -> None:
                    pass

            return _AsyncRaw()

        monkeypatch.setattr(bdb, "raw_connector", lambda _engine: _Raw)
        monkeypatch.setattr(bdb.pycubrid.aio, "connect", aio_connect)
    monkeypatch.setattr(bdb, "raw_kwargs", lambda _engine: {})
    return _Raw


def _sqlite_url(tmp_path: Any) -> str:
    return f"sqlite:///{tmp_path / 'baseline.db'}"


def _versioned_engine(url: str) -> Any:
    from sqlalchemy import create_engine, event

    engine = create_engine(url)
    event.listen(
        engine, "connect", lambda conn, _rec: conn.create_function("version", 0, lambda: "fake")
    )
    return engine


class _FullFakeAsyncEngine(_FakeAsyncEngine):
    """Adds what run_async reads from an AsyncEngine: execute, dialect, pool and dispose."""

    def __init__(self, engine: Any) -> None:
        super().__init__(engine)
        self.dialect = engine.dialect
        self.pool = engine.pool

    async def dispose(self) -> None:
        self._engine.dispose()


async def _fake_execute(self: _FakeAsyncConn, statement: Any, *args: Any) -> Any:
    return self._sync_conn.execute(statement, *args)


def _baseline_args() -> Any:
    import argparse

    return argparse.Namespace(
        dsn="unused",
        concurrency=[],
        trials=1,
        rows=1,
        iterations=1,
        fetch_rounds=1,
        reflect_rounds=1,
        batch=1,
        batch_rounds=1,
    )


def _run(bdb: Any, route: str, url: str, monkeypatch: pytest.MonkeyPatch) -> Any:
    if route == "sync":
        monkeypatch.setattr(bdb, "create_engine", lambda *_args, **_kwargs: _versioned_engine(url))
        return bdb.run_sync(_baseline_args())
    monkeypatch.setattr(_FakeAsyncConn, "execute", _fake_execute, raising=False)
    monkeypatch.setattr(
        bdb,
        "create_async_engine",
        lambda *_args, **_kwargs: _FullFakeAsyncEngine(_versioned_engine(url)),
    )
    return asyncio.run(bdb.run_async(_baseline_args()))


@pytest.mark.parametrize("route", ["sync", "async"])
def test_run_leaves_an_existing_table_untouched(
    bdb: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    engine = _sqlite_engine(tmp_path, with_sentinel=True)
    _patch_common(bdb, monkeypatch, fail_at=None)
    with pytest.raises(SystemExit, match="already exists"):
        _run(bdb, route, _sqlite_url(tmp_path), monkeypatch)
    assert _rows(engine) == [(1, "sentinel")]
    engine.dispose()


@pytest.mark.parametrize("route", ["sync", "async"])
def test_run_drops_only_its_own_table_on_success(
    bdb: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    from sqlalchemy import inspect

    raw = _patch_common(bdb, monkeypatch, fail_at=None)
    report = _run(bdb, route, _sqlite_url(tmp_path), monkeypatch)
    assert report["environment"] == {"env": "fake"}
    assert len(report["trials"]) == 1
    assert raw.closed
    engine = _sqlite_engine(tmp_path, with_sentinel=False)
    assert not inspect(engine).has_table(bdb.TABLE)
    engine.dispose()


@pytest.mark.parametrize("route", ["sync", "async"])
@pytest.mark.parametrize("fail_at", ["startup", "reset"])
def test_run_drops_its_table_and_keeps_the_error_when_it_fails(
    bdb: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch, route: str, fail_at: str
) -> None:
    from sqlalchemy import inspect

    _patch_common(bdb, monkeypatch, fail_at=fail_at)
    expected = ConnectionError if fail_at == "startup" else RuntimeError
    with pytest.raises(expected):
        _run(bdb, route, _sqlite_url(tmp_path), monkeypatch)
    engine = _sqlite_engine(tmp_path, with_sentinel=False)
    assert not inspect(engine).has_table(bdb.TABLE)
    engine.dispose()
