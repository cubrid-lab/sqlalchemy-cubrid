"""Connection pool concurrency stress tests against a live CUBRID instance.

Exercises QueuePool concurrent checkouts (threading + asyncio), pool
overflow under burst load, and pool_recycle behavior.

Skipped automatically when no CUBRID instance is available.
"""

from __future__ import annotations

import asyncio
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import TimeoutError as SATimeoutError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import QueuePool


_DEFAULT_URL = "cubrid+pycubrid://dba@localhost:33000/testdb"
_DEFAULT_AURL = "cubrid+aiopycubrid://dba@localhost:33000/testdb"


def _sync_url() -> str:
    return os.environ.get("CUBRID_TEST_URL", _DEFAULT_URL)


def _async_url() -> str:
    return os.environ.get("CUBRID_TEST_AURL", _DEFAULT_AURL)


def _can_connect() -> bool:
    try:
        engine = create_engine(_sync_url())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _can_connect(),
        reason="CUBRID instance not available (set CUBRID_TEST_URL)",
    ),
]


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

            results = await asyncio.gather(*(worker(i) for i in range(n)))
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

            results = await asyncio.gather(*(worker(i) for i in range(n)))
            assert sum(results) == n

            async with engine.connect() as conn:
                result = await conn.execute(text(f"SELECT COUNT(*) FROM {shared_table}"))
                total = result.scalar_one()
            assert total == n
        finally:
            await engine.dispose()
