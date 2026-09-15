from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import Protocol, cast
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import Column, Integer, MetaData, String, Table, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

_DEFAULT_SYNC_URL = "cubrid://dba@localhost:33000/testdb"


class SupportsAutocommit(Protocol):
    autocommit: bool


class SupportsPing(Protocol):
    def ping(self, reconnect: bool = True) -> bool: ...


def _async_url() -> str:
    sync = os.environ.get("CUBRID_TEST_URL", _DEFAULT_SYNC_URL)
    return sync.replace("cubrid://", "cubrid+aiopycubrid://", 1)


def _can_connect_async() -> bool:
    async def _probe() -> bool:
        engine = create_async_engine(_async_url())
        try:
            async with engine.connect() as conn:
                _ = await conn.execute(text("SELECT 1"))
            return True
        finally:
            await engine.dispose()

    try:
        return asyncio.run(_probe())
    except Exception:
        return False


# In CI, CUBRID is intentionally provisioned — connectivity failure
# should be a hard test error, not a silent skip.  Locally, developers
# without a running CUBRID instance get a skip.
_available = _can_connect_async()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _available,
        reason="CUBRID async instance not available (set CUBRID_TEST_URL)",
    ),
    pytest.mark.asyncio,
]


@pytest_asyncio.fixture(scope="function")
async def engine() -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(_async_url(), echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="function")
async def users_table(engine: AsyncEngine) -> AsyncIterator[Table]:
    meta = MetaData()
    users = Table(
        "aio_test_users",
        meta,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("name", String(100), nullable=False),
        Column("value", Integer),
    )

    async with engine.begin() as conn:
        _ = await conn.execute(text("DROP TABLE IF EXISTS aio_test_users"))
        await conn.run_sync(meta.create_all)

    yield users

    async with engine.begin() as conn:
        _ = await conn.execute(text("DROP TABLE IF EXISTS aio_test_users"))


@pytest_asyncio.fixture(scope="function")
async def seed_users(
    engine: AsyncEngine,
    users_table: Table,
) -> Callable[[Sequence[dict[str, int | str]]], Awaitable[Table]]:
    async def _seed(rows: Sequence[dict[str, int | str]]) -> Table:
        if rows:
            async with engine.begin() as conn:
                _ = await conn.execute(users_table.insert(), list(rows))
        return users_table

    return _seed


@pytest_asyncio.fixture(scope="function")
async def pre_ping_engine() -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(
        _async_url(),
        echo=False,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
    )
    yield eng
    await eng.dispose()


class TestAsyncCRUD:
    async def test_connect(self, engine: AsyncEngine):
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.fetchone() == (1,)

    async def test_insert_and_select(
        self,
        engine: AsyncEngine,
        seed_users: Callable[[Sequence[dict[str, int | str]]], Awaitable[Table]],
    ):
        users = await seed_users([{"name": "alice", "value": 10}, {"name": "bob", "value": 20}])

        async with engine.connect() as conn:
            result = await conn.execute(select(users.c.name).order_by(users.c.id))
            names = result.scalars().all()

        assert names == ["alice", "bob"]

    async def test_update(
        self,
        engine: AsyncEngine,
        seed_users: Callable[[Sequence[dict[str, int | str]]], Awaitable[Table]],
    ):
        users = await seed_users([{"name": "alice", "value": 10}])

        async with engine.begin() as conn:
            _ = await conn.execute(users.update().where(users.c.name == "alice").values(value=100))

        async with engine.connect() as conn:
            result = await conn.execute(select(users.c.value).where(users.c.name == "alice"))
            value = cast(object, result.scalar_one())

        assert isinstance(value, int)
        assert value == 100

    async def test_delete(
        self,
        engine: AsyncEngine,
        seed_users: Callable[[Sequence[dict[str, int | str]]], Awaitable[Table]],
    ):
        users = await seed_users([{"name": "bob", "value": 20}])

        async with engine.begin() as conn:
            _ = await conn.execute(users.delete().where(users.c.name == "bob"))

        async with engine.connect() as conn:
            result = await conn.execute(users.select().where(users.c.name == "bob"))

        assert result.fetchone() is None

    async def test_transaction_rollback(self, engine: AsyncEngine, users_table: Table):
        try:
            async with engine.begin() as conn:
                _ = await conn.execute(users_table.insert().values(name="will_rollback", value=999))
                raise RuntimeError("force rollback")
        except RuntimeError:
            pass

        async with engine.connect() as conn:
            result = await conn.execute(
                users_table.select().where(users_table.c.name == "will_rollback")
            )

        assert result.fetchone() is None

    async def test_concurrent_pool(self, engine: AsyncEngine):
        async def worker(i: int) -> int:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT :value"), {"value": i})
                value = cast(object, result.scalar_one())
                assert isinstance(value, int)
                return value

        results = await asyncio.gather(*(worker(i) for i in range(5)))
        assert sorted(results) == [0, 1, 2, 3, 4]

    async def test_bad_sql_raises(self, engine: AsyncEngine):
        with pytest.raises(Exception):
            async with engine.connect() as conn:
                _ = await conn.execute(text("SELECT * FROM nonexistent_xyz"))

    async def test_autocommit_toggle(self, engine: AsyncEngine):
        async with engine.connect() as conn:
            await conn.run_sync(
                lambda sync_conn: setattr(
                    cast(SupportsAutocommit, cast(object, sync_conn.connection.dbapi_connection)),
                    "autocommit",
                    True,
                )
            )
            await conn.run_sync(
                lambda sync_conn: setattr(
                    cast(SupportsAutocommit, cast(object, sync_conn.connection.dbapi_connection)),
                    "autocommit",
                    False,
                )
            )

    async def test_pool_pre_ping_recovers_after_connection_drop(
        self,
        pre_ping_engine: AsyncEngine,
    ):
        async with pre_ping_engine.connect() as conn:
            raw = await conn.get_raw_connection()
            dropped_driver_connection = cast(
                object,
                getattr(cast(object, raw.driver_connection), "_connection"),
            )
            close_streams = cast(
                Callable[[], Awaitable[None]],
                getattr(dropped_driver_connection, "_close_streams"),
            )

        await close_streams()

        dialect = pre_ping_engine.sync_engine.dialect
        ping_results: list[bool] = []

        def record_do_ping(dbapi_connection: object) -> bool:
            result = bool(cast(SupportsPing, dbapi_connection).ping(False))
            ping_results.append(result)
            return result

        with patch.object(dialect, "do_ping", side_effect=record_do_ping):
            async with pre_ping_engine.connect() as conn:
                raw = await conn.get_raw_connection()
                recovered_driver_connection = cast(
                    object,
                    getattr(cast(object, raw.driver_connection), "_connection"),
                )
                result = await conn.execute(text("SELECT 1"))
                assert result.scalar_one() == 1

            async with pre_ping_engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                assert result.scalar_one() == 1

        false_index = next(
            (index for index, value in enumerate(ping_results) if value is False),
            None,
        )
        assert false_index is not None, ping_results
        assert any(value is True for value in ping_results[false_index + 1 :]), ping_results
        assert recovered_driver_connection is not dropped_driver_connection

    async def test_insert_returns_lastrowid(self, engine: AsyncEngine, users_table: Table):
        # Keep the adapter surface minimal: async pycubrid already populates
        # cursor.lastrowid, and the dialect still has SQL fallback if a driver
        # helper is unavailable, so issue #208 does not need a new passthrough.
        async with engine.begin() as conn:
            result = await conn.execute(users_table.insert().values(name="carol", value=30))
            inserted_id = result.lastrowid
            inserted_primary_key = result.inserted_primary_key

        assert isinstance(inserted_id, int)
        assert inserted_id > 0
        assert inserted_primary_key == (inserted_id,)

        async with engine.connect() as conn:
            result = await conn.execute(
                select(users_table.c.name).where(users_table.c.id == inserted_id)
            )
            name = result.scalar_one_or_none()

        assert name == "carol"


class TestAsyncJSON:
    @pytest_asyncio.fixture(autouse=True)
    async def _json_table(self, engine: AsyncEngine) -> AsyncIterator[None]:
        async with engine.begin() as conn:
            _ = await conn.execute(text("DROP TABLE IF EXISTS aio_test_json"))
            _ = await conn.execute(
                text("CREATE TABLE aio_test_json (id INT AUTO_INCREMENT PRIMARY KEY, payload JSON)")
            )
        yield
        async with engine.begin() as conn:
            _ = await conn.execute(text("DROP TABLE IF EXISTS aio_test_json"))

    async def _insert_json(self, engine: AsyncEngine, value: object) -> None:
        async with engine.begin() as conn:
            _ = await conn.execute(
                text("INSERT INTO aio_test_json (payload) VALUES (:p)"),
                {"p": json.dumps(value) if value is not None else None},
            )

    async def _last_json(self, engine: AsyncEngine) -> object | None:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT payload FROM aio_test_json ORDER BY id DESC LIMIT 1")
            )
            raw = result.scalar()
            return json.loads(raw) if isinstance(raw, str) else raw

    async def test_dict_roundtrip(self, engine: AsyncEngine):
        value = {"key": "value", "n": 42}
        await self._insert_json(engine, value)
        assert await self._last_json(engine) == value

    async def test_list_roundtrip(self, engine: AsyncEngine):
        value = [1, "two", 3.0, None]
        await self._insert_json(engine, value)
        assert await self._last_json(engine) == value

    async def test_nested_roundtrip(self, engine: AsyncEngine):
        value = {"a": {"b": [1, {"c": True}]}}
        await self._insert_json(engine, value)
        assert await self._last_json(engine) == value

    async def test_null_json(self, engine: AsyncEngine):
        async with engine.begin() as conn:
            _ = await conn.execute(text("INSERT INTO aio_test_json (payload) VALUES (NULL)"))
        assert await self._last_json(engine) is None

    async def test_empty_object(self, engine: AsyncEngine):
        await self._insert_json(engine, {})
        assert await self._last_json(engine) == {}

    async def test_empty_array(self, engine: AsyncEngine):
        await self._insert_json(engine, [])
        assert await self._last_json(engine) == []

    async def test_json_extract(self, engine: AsyncEngine):
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT JSON_EXTRACT('{\"a\": 1}', '$.a')"))
            assert result.scalar() is not None

    async def test_orm_json_type(self, engine: AsyncEngine):
        from sqlalchemy_cubrid.types import JSON as CubridJSON

        meta = MetaData()
        table = Table(
            "aio_test_json_orm",
            meta,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("data", CubridJSON),
        )
        async with engine.begin() as conn:
            _ = await conn.execute(text("DROP TABLE IF EXISTS aio_test_json_orm"))
            await conn.run_sync(meta.create_all)

        test_data = {"items": [1, 2, 3]}
        async with engine.begin() as conn:
            _ = await conn.execute(table.insert().values(data=test_data))

        async with engine.connect() as conn:
            result = await conn.execute(select(table.c.data))
            value = cast(object | None, result.scalar_one_or_none())
            assert value is not None
            if isinstance(value, str):
                value = cast(object, json.loads(value))
            assert value == test_data

        async with engine.begin() as conn:
            _ = await conn.execute(text("DROP TABLE IF EXISTS aio_test_json_orm"))
