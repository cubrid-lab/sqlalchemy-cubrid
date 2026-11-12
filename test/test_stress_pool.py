"""Connection pool concurrency stress tests against a live CUBRID instance.

Exercises QueuePool concurrent checkouts (threading + asyncio), pool
overflow under burst load, and pool_recycle, checkout timeout and checkin
reset behavior.

Skipped when ``CUBRID_TEST_URL`` is unset; an unreachable server errors
instead (the shared gate in ``test/conftest.py``, #593).
"""

from __future__ import annotations

import asyncio
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import Connection, create_engine, event, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import TimeoutError as SATimeoutError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import URL

from scripts.integration_urls import async_url


_DEFAULT_URL = "cubrid+pycubrid://dba@localhost:33000/testdb"


def _sync_url() -> str:
    return os.environ.get("CUBRID_TEST_URL", _DEFAULT_URL)


def _async_url() -> URL:
    return async_url(_sync_url(), os.environ.get("CUBRID_TEST_AURL"))


# The shared gate in test/conftest.py skips these tests when CUBRID_TEST_URL is
# unset and errors them when its server is unreachable (#593).
pytestmark = pytest.mark.integration


def _table() -> str:
    return f"sa_stress_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def shared_table():
    table = _table()
    engine = create_engine(_sync_url())
    with engine.begin() as conn:
        conn.execute(
            text(f"CREATE TABLE {table} (id INT AUTO_INCREMENT PRIMARY KEY, worker INT, n INT)")
        )
    engine.dispose()
    yield table
    cleanup = create_engine(_sync_url())
    with cleanup.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
    cleanup.dispose()


class TestQueuePoolConcurrency:
    def test_concurrent_checkouts_within_pool_size(self, shared_table: str) -> None:
        engine = create_engine(
            _sync_url(),
            poolclass=QueuePool,
            pool_size=8,
            max_overflow=0,
            pool_timeout=10,
        )
        try:
            n_workers = 8
            per_worker = 20
            errors: list[BaseException] = []
            lock = threading.Lock()

            def worker(idx: int) -> int:
                try:
                    with engine.begin() as conn:
                        for i in range(per_worker):
                            conn.execute(
                                text(f"INSERT INTO {shared_table} (worker, n) VALUES (:w, :n)"),
                                {"w": idx, "n": i},
                            )
                    with engine.connect() as conn:
                        return conn.execute(
                            text(f"SELECT COUNT(*) FROM {shared_table} WHERE worker = :w"),
                            {"w": idx},
                        ).scalar_one()
                except BaseException as exc:
                    with lock:
                        errors.append(exc)
                    return -1

            with ThreadPoolExecutor(max_workers=n_workers) as ex:
                results = list(ex.map(worker, range(n_workers)))

            assert not errors, f"worker errors: {errors!r}"
            assert all(r == per_worker for r in results), results
        finally:
            engine.dispose()

    def test_overflow_absorbs_burst_then_settles(self, shared_table: str) -> None:
        engine = create_engine(
            _sync_url(),
            poolclass=QueuePool,
            pool_size=4,
            max_overflow=12,
            pool_timeout=15,
        )
        try:
            n_workers = 16
            errors: list[BaseException] = []
            lock = threading.Lock()
            barrier = threading.Barrier(n_workers)

            def worker(idx: int) -> int:
                try:
                    barrier.wait(timeout=10)
                    with engine.begin() as conn:
                        conn.execute(
                            text(f"INSERT INTO {shared_table} (worker, n) VALUES (:w, 0)"),
                            {"w": idx},
                        )
                    return 1
                except BaseException as exc:
                    with lock:
                        errors.append(exc)
                    return -1

            with ThreadPoolExecutor(max_workers=n_workers) as ex:
                results = list(ex.map(worker, range(n_workers)))

            assert not errors, f"burst errors: {errors!r}"
            assert sum(results) == n_workers

            with engine.connect() as conn:
                total = conn.execute(text(f"SELECT COUNT(*) FROM {shared_table}")).scalar_one()
            assert total == n_workers

            assert engine.pool.checkedout() == 0
        finally:
            engine.dispose()

    def test_pool_timeout_raises_when_exhausted(self) -> None:
        engine = create_engine(
            _sync_url(),
            poolclass=QueuePool,
            pool_size=2,
            max_overflow=0,
            pool_timeout=1,
        )
        try:
            held = [engine.connect() for _ in range(2)]
            try:
                with pytest.raises(SATimeoutError):
                    engine.connect()
            finally:
                for c in held:
                    c.close()
        finally:
            engine.dispose()

    def test_pool_recycle_replaces_old_connection(self) -> None:
        engine = create_engine(
            _sync_url(),
            poolclass=QueuePool,
            pool_size=2,
            max_overflow=0,
            pool_recycle=1,
            pool_pre_ping=False,
        )
        try:
            with engine.connect() as conn:
                first_raw = conn.connection.dbapi_connection
                conn.execute(text("SELECT 1"))

            time.sleep(1.5)

            with engine.connect() as conn:
                second_raw = conn.connection.dbapi_connection
                conn.execute(text("SELECT 1"))

            assert first_raw is not second_raw
        finally:
            engine.dispose()


# A CUBRID session variable lives in the server session behind one connection.
# Setting it on one checkout and reading it on the next tells whether the pool
# handed back the same server session or opened a new one, without relying on
# Python object identity.
_SET_MARKER = text("SET @sa_pool_session = 1151")
_GET_MARKER = text("SELECT @sa_pool_session")


def _session_marker(conn: Connection) -> int | None:
    """Return the marker of this connection's server session, or None in a new session.

    A session variable has no fixed column type, and the PyPI CUBRIDdb 9.3
    driver returns such values as ``str`` (docs/DRIVER_COMPAT.md), so the
    marker is converted to ``int`` before the tests compare it (#1143).
    """
    try:
        value = conn.execute(_GET_MARKER).scalar()
    except DBAPIError as exc:
        # -1070: "Session variable '@sa_pool_session' not defined."
        if "-1070" not in str(exc.orig):
            raise
        return None
    return None if value is None else int(value)


class TestQueuePoolLifecycle:
    """Pool recycle, checkout timeout and checkin reset on a live server (#1151).

    These checks need no timing upper bound: a recycled connection is detected
    by its server session, and the timeout test only bounds how long the
    failing checkout may take.
    """

    @pytest.mark.parametrize(
        ("recycle", "replaced"), [(1, True), (3600, False)], ids=["older", "younger"]
    )
    def test_pool_recycle_replaces_only_connections_older_than_the_limit(
        self, recycle: int, replaced: bool
    ) -> None:
        engine = create_engine(
            _sync_url(),
            poolclass=QueuePool,
            pool_size=1,
            max_overflow=0,
            pool_recycle=recycle,
            pool_pre_ping=False,
        )
        connects: list[object] = []
        closes: list[object] = []
        event.listen(engine, "connect", lambda dbapi_conn, _record: connects.append(dbapi_conn))
        event.listen(engine, "close", lambda dbapi_conn, _record: closes.append(dbapi_conn))
        try:
            with engine.connect() as conn:
                conn.execute(_SET_MARKER)
                first = conn.connection.dbapi_connection
                conn.commit()

            # Longer than the 1 s limit; far below the 3600 s one.
            time.sleep(1.5)

            with engine.connect() as conn:
                marker = _session_marker(conn)
                second = conn.connection.dbapi_connection
            if replaced:
                assert marker is None, "the recycled checkout kept the old server session"
                assert second is not first
                assert connects == [first, second]
                assert closes == [first], "the expired connection was not closed"
            else:
                assert marker == 1151, "a connection younger than pool_recycle was replaced"
                assert second is first
                assert connects == [first]
                assert closes == []
            assert engine.pool.checkedout() == 0
        finally:
            engine.dispose()

    def test_checkout_times_out_when_pool_and_overflow_are_saturated(self) -> None:
        engine = create_engine(
            _sync_url(),
            poolclass=QueuePool,
            pool_size=2,
            max_overflow=1,
            pool_timeout=1,
        )
        held = []
        try:
            held = [engine.connect() for _ in range(3)]
            for conn in held:
                assert conn.execute(text("SELECT 1")).scalar() == 1
            assert engine.pool.checkedout() == 3
            assert engine.pool.overflow() == 1

            started = time.monotonic()
            with pytest.raises(SATimeoutError):
                engine.connect()
            waited = time.monotonic() - started
            # The checkout waits for pool_timeout, then fails; generous upper bound.
            assert 0.9 <= waited < 10, waited
            assert engine.pool.checkedout() == 3

            # Returning one connection lets the next checkout through.
            held.pop().close()
            with engine.connect() as conn:
                assert conn.execute(text("SELECT 1")).scalar() == 1
        finally:
            for conn in held:
                conn.close()
            assert engine.pool.checkedout() == 0
            engine.dispose()

    def test_checkin_rolls_back_and_keeps_the_session(self, shared_table: str) -> None:
        """Uncommitted work is rolled back on return; the pooled session stays usable.

        The same server session would see its own uncommitted row, so a count of
        zero on the next checkout of that session proves the rollback.
        """
        engine = create_engine(
            _sync_url(), poolclass=QueuePool, pool_size=1, max_overflow=0, pool_timeout=5
        )
        insert = text(f"INSERT INTO {shared_table} (worker, n) VALUES (1, 0)")
        count = text(f"SELECT COUNT(*) FROM {shared_table}")
        try:
            # Closed with the INSERT neither committed nor rolled back.
            with engine.connect() as conn:
                conn.execute(_SET_MARKER)
                conn.execute(insert)
                assert conn.execute(count).scalar_one() == 1

            # Explicit rollback, then return.
            with engine.connect() as conn:
                assert _session_marker(conn) == 1151
                assert conn.execute(count).scalar_one() == 0
                conn.execute(insert)
                conn.rollback()
                assert not conn.in_transaction()

            with engine.begin() as conn:
                assert _session_marker(conn) == 1151
                assert conn.execute(count).scalar_one() == 0
                conn.execute(insert)

            with engine.connect() as conn:
                assert conn.execute(count).scalar_one() == 1
            assert engine.pool.checkedout() == 0
            assert engine.pool.checkedin() == 1
        finally:
            engine.dispose()


class TestAsyncPoolConcurrency:
    @pytest.mark.asyncio
    async def test_async_gather_within_pool_size(self, shared_table: str) -> None:
        engine = create_async_engine(
            _async_url(),
            pool_size=8,
            max_overflow=0,
            pool_timeout=10,
        )
        try:
            n = 8
            per_task = 15

            async def worker(idx: int) -> int:
                async with engine.begin() as conn:
                    for i in range(per_task):
                        await conn.execute(
                            text(f"INSERT INTO {shared_table} (worker, n) VALUES (:w, :n)"),
                            {"w": idx, "n": i},
                        )
                async with engine.connect() as conn:
                    result = await conn.execute(
                        text(f"SELECT COUNT(*) FROM {shared_table} WHERE worker = :w"),
                        {"w": idx},
                    )
                    return result.scalar_one()

            async with asyncio.TaskGroup() as tg:
                tasks = [tg.create_task(worker(i)) for i in range(n)]
            results = [task.result() for task in tasks]
            assert all(r == per_task for r in results), results
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_async_overflow_burst(self, shared_table: str) -> None:
        engine = create_async_engine(
            _async_url(),
            pool_size=4,
            max_overflow=12,
            pool_timeout=15,
        )
        try:
            n = 16

            async def worker(idx: int) -> int:
                async with engine.begin() as conn:
                    await conn.execute(
                        text(f"INSERT INTO {shared_table} (worker, n) VALUES (:w, 0)"),
                        {"w": idx},
                    )
                return 1

            async with asyncio.TaskGroup() as tg:
                tasks = [tg.create_task(worker(i)) for i in range(n)]
            results = [task.result() for task in tasks]
            assert sum(results) == n

            async with engine.connect() as conn:
                result = await conn.execute(text(f"SELECT COUNT(*) FROM {shared_table}"))
                total = result.scalar_one()
            assert total == n
        finally:
            await engine.dispose()
