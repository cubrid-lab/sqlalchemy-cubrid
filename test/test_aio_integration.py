from __future__ import annotations

import asyncio
import datetime
import json
import os
from decimal import Decimal
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import Any, Protocol, cast
from unittest.mock import patch

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy import Column, Integer, MetaData, String, Table, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from sqlalchemy_cubrid import DOUBLE, MULTISET, SEQUENCE, SET

from scripts.integration_urls import async_url

_DEFAULT_SYNC_URL = "cubrid://dba@localhost:33000/testdb"


class SupportsAutocommit(Protocol):
    autocommit: bool


class SupportsPing(Protocol):
    def ping(self, reconnect: bool = True) -> bool: ...


def _async_url() -> URL:
    sync = os.environ.get("CUBRID_TEST_URL", _DEFAULT_SYNC_URL)
    return async_url(sync, os.environ.get("CUBRID_TEST_AURL"))


# The shared gate in test/conftest.py skips these tests when CUBRID_TEST_URL is
# unset and errors them when its server is unreachable (#593).
pytestmark = [
    pytest.mark.integration,
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

    async def test_driver_connection_is_pycubrid_aio_connection(self, engine: AsyncEngine):
        pycubrid_aio = pytest.importorskip("pycubrid.aio")
        async with engine.connect() as conn:
            raw = await conn.get_raw_connection()
            driver_conn = cast(Any, raw.driver_connection)
            assert isinstance(driver_conn, pycubrid_aio.AsyncConnection)
            assert driver_conn is cast(Any, raw.dbapi_connection)._connection
            # Driver-level async APIs work on the returned object.
            assert await driver_conn.ping(False) is True
            cursor = driver_conn.cursor()
            try:
                await cursor.execute("SELECT 1")
                assert await cursor.fetchall() == [(1,)]
            finally:
                await cursor.close()

    async def test_pool_pre_ping_recovers_after_connection_drop(
        self,
        pre_ping_engine: AsyncEngine,
    ):
        async with pre_ping_engine.connect() as conn:
            raw = await conn.get_raw_connection()
            dropped_driver_connection = cast(object, raw.driver_connection)
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
                recovered_driver_connection = cast(object, raw.driver_connection)
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


# ---------------------------------------------------------------------------
# #485: SQLAlchemy-facing BLOB/CLOB value contract (async)
# ---------------------------------------------------------------------------
# Moved to the dedicated test/test_lob_value_contract.py (sync and async,
# Core and ORM, in one module) instead of growing this already very large
# file further.


# PEP 249 module-level names; kept in sync with the offline copy in
# test_aio_pycubrid_dialect.py. This live lane installs the released pycubrid,
# so the parity check runs against the real driver here (#500).
_PEP249_NAMES = (
    "apilevel",
    "threadsafety",
    "paramstyle",
    "Warning",
    "Error",
    "InterfaceError",
    "DatabaseError",
    "DataError",
    "OperationalError",
    "IntegrityError",
    "InternalError",
    "ProgrammingError",
    "NotSupportedError",
    "Date",
    "Time",
    "Timestamp",
    "DateFromTicks",
    "TimeFromTicks",
    "TimestampFromTicks",
    "Binary",
    "STRING",
    "BINARY",
    "NUMBER",
    "DATETIME",
    "ROWID",
)


@pytest.mark.parametrize("name", _PEP249_NAMES)
def test_adapter_exposes_every_pycubrid_pep249_name(engine: AsyncEngine, name: str):
    pycubrid = pytest.importorskip("pycubrid")
    if not hasattr(pycubrid, name):
        pytest.skip(f"pycubrid {pycubrid.__version__} does not define {name}")
    dbapi = cast(object, engine.dialect.dbapi)
    assert getattr(dbapi, name) is getattr(pycubrid, name)


# ---------------------------------------------------------------------------
# #481: results are never silently truncated across commit or rollback
# ---------------------------------------------------------------------------

# More rows than pycubrid's default FETCH batch (``fetch_size=100``), each wide
# enough that the broker's first response holds only ~16 of them.
_WIDE_ROWS = 500
_WIDE_PAYLOAD = "x" * 1000
_FETCHMANY_SIZE = 17


class TestAsyncResultCompletenessAcrossTransactionBoundary:
    """``AsyncConnection.execute()`` results across commit/rollback.

    SQLAlchemy's async DB-API adapter reads every row of a non-streaming result
    before ``execute()`` returns, so no FETCH happens after the boundary and the
    result stays complete. ``AsyncConnection.stream()`` is not available: the
    dialect does not support server-side cursors. The raw driver-cursor case
    below exercises the lazily fetching ``pycubrid.aio`` cursor directly.
    """

    @pytest_asyncio.fixture(autouse=True)
    async def wide_table(self, engine: AsyncEngine) -> AsyncIterator[Table]:
        table = Table(
            "aio_test_rc481",
            MetaData(),
            Column("id", Integer, primary_key=True, autoincrement=False),
            Column("payload", String(1000)),
        )
        async with engine.begin() as conn:
            await conn.run_sync(table.drop, checkfirst=True)
            await conn.run_sync(table.create)
            _ = await conn.execute(
                table.insert(), [{"id": i, "payload": _WIDE_PAYLOAD} for i in range(_WIDE_ROWS)]
            )
        yield table
        async with engine.begin() as conn:
            await conn.run_sync(table.drop, checkfirst=True)

    @pytest.mark.parametrize("method", ["fetchone", "fetchmany", "fetchall"])
    @pytest.mark.parametrize("boundary", ["commit", "rollback", "none"])
    async def test_unfinished_result_is_complete_or_raises(
        self, engine: AsyncEngine, wide_table: Table, boundary: str, method: str
    ):
        async with engine.connect() as conn:
            _ = (await conn.execute(text("SELECT 1"))).all()
            result = await conn.execute(
                select(wide_table.c.id, wide_table.c.payload).order_by(wide_table.c.id)
            )
            first = result.fetchone()
            assert first is not None
            if boundary == "commit":
                await conn.commit()
            elif boundary == "rollback":
                await conn.rollback()
            rest: list[sa.Row[tuple[int, str]]] = []
            try:
                if method == "fetchall":
                    rest = list(result.fetchall())
                elif method == "fetchmany":
                    while part := result.fetchmany(_FETCHMANY_SIZE):
                        rest.extend(part)
                else:
                    while (row := result.fetchone()) is not None:
                        rest.append(row)
            except sa.exc.DBAPIError:
                if boundary == "none":
                    raise
                return  # an explicit failure satisfies the contract
        ids = [first.id] + [row.id for row in rest]
        assert len(ids) == _WIDE_ROWS, f"silently truncated: {len(ids)} of {_WIDE_ROWS} rows"
        assert ids == list(range(_WIDE_ROWS))
        assert all(row.payload == _WIDE_PAYLOAD for row in rest)

    @pytest.mark.parametrize("boundary", ["commit", "rollback"])
    async def test_raw_driver_cursor_is_complete_or_raises(
        self,
        engine: AsyncEngine,
        wide_table: Table,
        boundary: str,
    ):
        """The aiopycubrid driver cursor itself, which fetches lazily.

        SQLAlchemy's buffering hides pycubrid#395 above, so this case drives the
        underlying ``pycubrid.aio`` connection directly: execute, fetch one row,
        end the transaction, then fetch the rest.
        """
        async with engine.connect() as conn:
            driver_conn = cast(Any, (await conn.get_raw_connection()).driver_connection)
            cursor = driver_conn.cursor()
            try:
                await cursor.execute("SELECT 1")
                assert await cursor.fetchall() == [(1,)]
                await cursor.execute("SELECT id, payload FROM aio_test_rc481 ORDER BY id")
                # The first response must not hold the whole result.
                assert 0 < cursor._fetched_count < _WIDE_ROWS
                first = await cursor.fetchone()
                # Checked before the boundary, so it holds even when the rest raises.
                assert first is not None and first[0] == 0 and first[1] == _WIDE_PAYLOAD
                if boundary == "commit":
                    await driver_conn.commit()
                else:
                    await driver_conn.rollback()
                pycubrid = pytest.importorskip("pycubrid")
                try:
                    rest: list[tuple[Any, ...]] | None = list(await cursor.fetchall())
                except pycubrid.Error:
                    rest = None  # an explicit failure satisfies the contract
                if rest is not None:
                    # Everything returned, including the row fetchone() consumed,
                    # is an in-order prefix with intact payloads.
                    returned = [first, *rest]
                    ids = [row[0] for row in returned]
                    assert ids == list(range(len(ids)))
                    assert all(row[1] == _WIDE_PAYLOAD for row in returned)
                if rest is not None:
                    assert len(ids) == _WIDE_ROWS, (
                        f"silently truncated: {len(ids)} of {_WIDE_ROWS} rows"
                    )
            finally:
                await cursor.close()


# ---------------------------------------------------------------------------
# #480: constraint violations surface as sqlalchemy.exc.IntegrityError
# ---------------------------------------------------------------------------


class _AsyncIntegrityBase(DeclarativeBase):
    pass


class _AsyncIntegrityParent(_AsyncIntegrityBase):
    __tablename__ = "aio_test_ie480_parent"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str | None] = mapped_column(String(20), nullable=False)


class _AsyncIntegrityChild(_AsyncIntegrityBase):
    __tablename__ = "aio_test_ie480_child"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    parent_id: Mapped[int] = mapped_column(sa.ForeignKey("aio_test_ie480_parent.id"))


# kind -> (mapped class, values violating the constraint, native CUBRID error
# code); parent 1 always exists.
_ASYNC_INTEGRITY_VIOLATIONS: dict[str, tuple[type[_AsyncIntegrityBase], dict[str, object], int]] = {
    "not_null": (_AsyncIntegrityParent, {"id": 2, "name": None}, -631),
    "foreign_key": (_AsyncIntegrityChild, {"id": 1, "parent_id": 999}, -922),
    "unique_pk": (_AsyncIntegrityParent, {"id": 1, "name": "duplicate"}, -670),  # control
}


def _assert_integrity_error(engine: AsyncEngine, exc: sa.exc.DBAPIError) -> None:
    assert isinstance(exc, sa.exc.IntegrityError), (
        f"expected sqlalchemy.exc.IntegrityError, got {type(exc).__name__} "
        f"wrapping {type(exc.orig).__module__}.{type(exc.orig).__name__}"
    )
    assert isinstance(exc.orig, engine.dialect.loaded_dbapi.IntegrityError)


def _integrity_counts(conn: sa.Connection) -> tuple[int, int]:
    parents, children = (
        conn.execute(select(sa.func.count()).select_from(model)).scalar_one()
        for model in (_AsyncIntegrityParent, _AsyncIntegrityChild)
    )
    return parents, children


async def _dbapi_connection(conn: Any) -> Any:
    return (await conn.get_raw_connection()).dbapi_connection


class TestAsyncIntegrityErrorContract:
    @pytest_asyncio.fixture(autouse=True)
    async def _integrity_tables(self, engine: AsyncEngine) -> AsyncIterator[None]:
        async with engine.begin() as conn:
            await conn.run_sync(_AsyncIntegrityBase.metadata.drop_all)
            await conn.run_sync(_AsyncIntegrityBase.metadata.create_all)
            _ = await conn.execute(sa.insert(_AsyncIntegrityParent), {"id": 1, "name": "parent"})
        yield
        async with engine.begin() as conn:
            await conn.run_sync(_AsyncIntegrityBase.metadata.drop_all)

    @pytest.mark.parametrize("kind", list(_ASYNC_INTEGRITY_VIOLATIONS))
    async def test_core_violation_raises_integrity_error(self, engine: AsyncEngine, kind: str):
        model, values, code = _ASYNC_INTEGRITY_VIOLATIONS[kind]
        async with engine.connect() as conn:
            raw = await _dbapi_connection(conn)
            with pytest.raises(sa.exc.DBAPIError) as excinfo:
                _ = await conn.execute(sa.insert(model), values)
            assert not excinfo.value.connection_invalidated
            await conn.rollback()
            # The same AsyncConnection, on the same DBAPI connection, runs new
            # statements after the rollback.
            assert not conn.invalidated
            assert await _dbapi_connection(conn) is raw
            assert await conn.run_sync(_integrity_counts) == (1, 0)
            _ = await conn.execute(sa.insert(_AsyncIntegrityChild), {"id": 10, "parent_id": 1})
            assert await conn.run_sync(_integrity_counts) == (1, 1)
            await conn.rollback()
        assert excinfo.value.orig.code == code  # pycubrid Error.code
        _assert_integrity_error(engine, excinfo.value)

    @pytest.mark.parametrize("kind", list(_ASYNC_INTEGRITY_VIOLATIONS))
    async def test_orm_flush_violation_raises_integrity_error(self, engine: AsyncEngine, kind: str):
        model, values, code = _ASYNC_INTEGRITY_VIOLATIONS[kind]
        # The AsyncSession is bound to one AsyncConnection, so after its rollback
        # it keeps using that connection and its DBAPI connection.
        async with engine.connect() as conn, AsyncSession(bind=conn) as session:
            raw = await _dbapi_connection(conn)
            session.add(model(**values))
            with pytest.raises(sa.exc.DBAPIError) as excinfo:
                await session.flush()
            assert not excinfo.value.connection_invalidated
            await session.rollback()
            assert not conn.invalidated
            assert await session.connection() is conn
            assert await _dbapi_connection(conn) is raw
            session.add(_AsyncIntegrityChild(id=10, parent_id=1))
            await session.flush()
            assert await conn.run_sync(_integrity_counts) == (1, 1)
            await session.rollback()
        assert excinfo.value.orig.code == code  # pycubrid Error.code
        _assert_integrity_error(engine, excinfo.value)


# ---------------------------------------------------------------------------
# #482: the cursor.description subset observable through SQLAlchemy
# ---------------------------------------------------------------------------

# column -> (SQLAlchemy type, nullable, CUBRID type code); same expectations as
# the sync pycubrid lane in test_integration.py.
_DESC_COLUMNS: dict[str, tuple[Any, bool, int]] = {
    "id": (Integer, False, 8),
    "nn": (String(20), False, 2),
    "nl": (String(20), True, 2),
    "bi": (sa.BigInteger, True, 21),
    "n": (sa.Numeric(10, 2), True, 7),
    "d": (DOUBLE, True, 12),
    "dt": (sa.Date, True, 13),
    "ts": (sa.TIMESTAMP, True, 15),
}
_DESC_ROW: dict[str, Any] = {
    "id": 1,
    "nn": "a",
    "nl": None,
    "bi": 2,
    "n": Decimal("3.50"),
    "d": 1.5,
    "dt": datetime.date(2020, 1, 2),
    "ts": datetime.datetime(2020, 1, 2, 3, 4, 5),
}
# column -> (collection type, pycubrid type code: SET 16, MULTISET 17, SEQUENCE 18).
_DESC_COLLECTIONS: dict[str, tuple[Any, int]] = {
    "s": (SET, 16),
    "ms": (MULTISET, 17),
    "sq": (SEQUENCE, 18),
}
# CUBRID collection literals cannot be bound as parameters portably (#484).
_DESC_COLLECTION_ROW = text(
    "INSERT INTO aio_test_cd482_coll (id, s, ms, sq) VALUES (1, {1,2}, {1,1}, {2,1})"
)
_DESC_TEXTUAL = text("SELECT id, nn AS alias, bi + 1 AS expr, 1 + 1 FROM aio_test_cd482")

_desc_metadata = MetaData()
_desc_table = Table(
    "aio_test_cd482",
    _desc_metadata,
    *(
        Column(name, type_, primary_key=name == "id", autoincrement=False, nullable=nullable)
        for name, (type_, nullable, _) in _DESC_COLUMNS.items()
    ),
)
_desc_collections = Table(
    "aio_test_cd482_coll",
    _desc_metadata,
    Column("id", Integer, primary_key=True, autoincrement=False),
    *(Column(name, kind(Integer())) for name, (kind, _) in _DESC_COLLECTIONS.items()),
)


def _description(result: sa.CursorResult[Any]) -> list[tuple[Any, ...]]:
    assert result.cursor is not None and result.cursor.description is not None
    return [tuple(d) for d in result.cursor.description]


class TestAsyncCursorDescriptionContract:
    @pytest_asyncio.fixture(autouse=True)
    async def _description_tables(self, engine: AsyncEngine) -> AsyncIterator[None]:
        async with engine.begin() as conn:
            await conn.run_sync(_desc_metadata.drop_all)
            await conn.run_sync(_desc_metadata.create_all)
            _ = await conn.execute(_desc_table.insert(), _DESC_ROW)
            _ = await conn.execute(_DESC_COLLECTION_ROW)
        yield
        async with engine.begin() as conn:
            await conn.run_sync(_desc_metadata.drop_all)

    async def test_textual_sql_column_names(self, engine: AsyncEngine):
        async with engine.connect() as conn:
            result = await conn.execute(_DESC_TEXTUAL)
            names = [d[0] for d in _description(result)]
            keys = list(result.keys())
            row = result.one()
        assert names == keys == ["id", "alias", "expr", "1+1"]
        assert row._mapping["alias"] == "a" and row.expr == 3

    async def test_core_select_keys_match_description(self, engine: AsyncEngine):
        async with engine.connect() as conn:
            reflected = await conn.run_sync(
                lambda sync_conn: Table("aio_test_cd482", MetaData(), autoload_with=sync_conn)
            )
            result = await conn.execute(select(reflected))
            names = [d[0] for d in _description(result)]
            assert list(result.keys()) == names == list(_DESC_COLUMNS)

    async def test_scalar_type_codes(self, engine: AsyncEngine):
        async with engine.connect() as conn:
            result = await conn.execute(select(_desc_table))
            codes = {d[0]: d[1] for d in _description(result)}
        assert codes == {name: spec[2] for name, spec in _DESC_COLUMNS.items()}

    async def test_null_ok(self, engine: AsyncEngine):
        async with engine.connect() as conn:
            result = await conn.execute(select(_desc_table))
            null_ok = {d[0]: bool(d[6]) for d in _description(result)}
        assert null_ok == {name: spec[1] for name, spec in _DESC_COLUMNS.items()}

    async def test_reflected_nullability_uses_catalog(self, engine: AsyncEngine):
        """Reflection reads nullability from the catalog, not cursor.description."""
        async with engine.connect() as conn:
            columns = await conn.run_sync(
                lambda sync_conn: sa.inspect(sync_conn).get_columns("aio_test_cd482")
            )
        nullable = {c["name"]: c["nullable"] for c in columns}
        assert nullable == {name: spec[1] for name, spec in _DESC_COLUMNS.items()}

    async def test_collection_type_codes(self):
        # A dedicated engine keeps any broken connection out of the shared pool:
        # pycubrid < 1.8.0 misreads the collection column header.
        engine = create_async_engine(_async_url())
        try:
            async with engine.connect() as conn:
                result = await conn.execute(
                    select(*(_desc_collections.c[name] for name in _DESC_COLLECTIONS))
                )
                codes = {d[0]: d[1] for d in _description(result)}
                assert len(result.all()) == 1
            assert codes == {name: spec[1] for name, spec in _DESC_COLLECTIONS.items()}
        finally:
            await engine.dispose()

    async def test_sync_and_async_descriptions_agree(self, engine: AsyncEngine):
        """Names, type codes and null_ok match the sync pycubrid dialect."""
        async with engine.connect() as conn:
            result = await conn.execute(select(_desc_table))
            async_desc = [(d[0], d[1], bool(d[6])) for d in _description(result)]
        sync_engine = sa.create_engine(_async_url().set(drivername="cubrid+pycubrid"))
        try:
            with sync_engine.connect() as sync_conn:
                sync_result = sync_conn.execute(select(_desc_table))
                sync_desc = [(d[0], d[1], bool(d[6])) for d in _description(sync_result)]
                sync_result.all()
        finally:
            sync_engine.dispose()
        assert async_desc == sync_desc


class TestAsyncIsolationLevelAcrossTransactionBoundaries:
    """The configured isolation level survives commit, rollback and pool checkin (#505)."""

    async def test_engine_level_survives_commit_rollback_and_checkin(self):
        eng = create_async_engine(
            _async_url(), isolation_level="SERIALIZABLE", pool_size=1, max_overflow=0
        )
        try:
            async with eng.connect() as conn:
                dbapi_conn = (await conn.get_raw_connection()).dbapi_connection
                assert await conn.get_isolation_level() == "SERIALIZABLE"
                _ = await conn.execute(text("SELECT 1"))
                await conn.commit()
                assert await conn.get_isolation_level() == "SERIALIZABLE"
                _ = await conn.execute(text("SELECT 1"))
                await conn.rollback()
                assert await conn.get_isolation_level() == "SERIALIZABLE"

            async with eng.connect() as conn:
                assert (await conn.get_raw_connection()).dbapi_connection is dbapi_conn
                assert await conn.get_isolation_level() == "SERIALIZABLE"
        finally:
            await eng.dispose()

    async def test_connection_level_survives_commit_and_rollback(self, engine: AsyncEngine):
        async with engine.connect() as conn:
            conn = await conn.execution_options(isolation_level="REPEATABLE READ")
            _ = await conn.execute(text("SELECT 1"))
            await conn.commit()
            assert await conn.get_isolation_level() == "REPEATABLE READ"
            _ = await conn.execute(text("SELECT 1"))
            await conn.rollback()
            assert await conn.get_isolation_level() == "REPEATABLE READ"


class TestAsyncAutocommitIsolationLevel:
    """``isolation_level="AUTOCOMMIT"`` and engine-level restore on aiopycubrid (#501)."""

    TABLE = "aio_iso501_autocommit"

    @pytest_asyncio.fixture
    async def observer(self) -> AsyncIterator[Callable[[int], Awaitable[int]]]:
        """A second session that sees only committed rows."""
        eng = create_async_engine(_async_url(), poolclass=sa.pool.NullPool)
        async with eng.begin() as conn:
            _ = await conn.execute(text(f"DROP TABLE IF EXISTS {self.TABLE}"))
            _ = await conn.execute(text(f"CREATE TABLE {self.TABLE} (id INT)"))

        async def committed(row_id: int) -> int:
            async with eng.connect() as conn:
                result = await conn.execute(
                    text(f"SELECT COUNT(*) FROM {self.TABLE} WHERE id = :id"), {"id": row_id}
                )
                return int(result.scalar_one())

        yield committed
        async with eng.begin() as conn:
            _ = await conn.execute(text(f"DROP TABLE IF EXISTS {self.TABLE}"))
        await eng.dispose()

    @pytest_asyncio.fixture
    async def make_engine(self) -> AsyncIterator[Callable[..., AsyncEngine]]:
        engines: list[AsyncEngine] = []

        def make(**kw: Any) -> AsyncEngine:
            eng = create_async_engine(_async_url(), pool_size=1, max_overflow=0, **kw)
            engines.append(eng)
            return eng

        yield make
        for eng in engines:
            await eng.dispose()

    async def _insert(self, conn: Any, row_id: int) -> None:
        _ = await conn.execute(text(f"INSERT INTO {self.TABLE} VALUES (:id)"), {"id": row_id})

    @pytest.mark.parametrize("path", ["create_engine", "engine_options", "connection_options"])
    async def test_autocommit_row_is_visible_before_commit_and_survives_rollback(
        self,
        observer: Callable[[int], Awaitable[int]],
        make_engine: Callable[..., AsyncEngine],
        path: str,
    ):
        if path == "create_engine":
            eng = make_engine(isolation_level="AUTOCOMMIT")
        elif path == "engine_options":
            eng = make_engine().execution_options(isolation_level="AUTOCOMMIT")
        else:
            eng = make_engine()
        async with eng.connect() as conn:
            if path == "connection_options":
                conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
            dbapi_conn = (await conn.get_raw_connection()).dbapi_connection
            assert eng.dialect.detect_autocommit_setting(dbapi_conn) is True
            await self._insert(conn, 1)
            assert await observer(1) == 1
            await conn.rollback()
        assert await observer(1) == 1

    async def test_pooled_connection_is_transactional_again_after_checkin(
        self,
        observer: Callable[[int], Awaitable[int]],
        make_engine: Callable[..., AsyncEngine],
    ):
        eng = make_engine()
        async with eng.connect() as conn:
            conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
            dbapi_conn = (await conn.get_raw_connection()).dbapi_connection
            await self._insert(conn, 1)

        async with eng.connect() as conn:
            assert (await conn.get_raw_connection()).dbapi_connection is dbapi_conn
            assert eng.dialect.detect_autocommit_setting(dbapi_conn) is False
            await self._insert(conn, 2)
            assert await observer(2) == 0
            await conn.rollback()
        assert await observer(1) == 1
        assert await observer(2) == 0

    @pytest.mark.parametrize("override", ["REPEATABLE READ", "AUTOCOMMIT"])
    async def test_engine_level_is_restored_after_connection_override(
        self, make_engine: Callable[..., AsyncEngine], override: str
    ):
        eng = make_engine(isolation_level="SERIALIZABLE")
        async with eng.connect() as conn:
            dbapi_conn = (await conn.get_raw_connection()).dbapi_connection
            conn = await conn.execution_options(isolation_level=override)
            if override == "AUTOCOMMIT":
                assert eng.dialect.detect_autocommit_setting(dbapi_conn) is True
            else:
                assert await conn.get_isolation_level() == override

        async with eng.connect() as conn:
            assert (await conn.get_raw_connection()).dbapi_connection is dbapi_conn
            assert eng.dialect.detect_autocommit_setting(dbapi_conn) is False
            assert await conn.get_isolation_level() == "SERIALIZABLE"
            _ = await conn.execute(text("SELECT 1"))
            await conn.commit()
            assert await conn.get_isolation_level() == "SERIALIZABLE"

    async def test_engine_level_autocommit_is_restored_after_connection_override(
        self,
        observer: Callable[[int], Awaitable[int]],
        make_engine: Callable[..., AsyncEngine],
    ):
        eng = make_engine(isolation_level="AUTOCOMMIT")
        async with eng.connect() as conn:
            dbapi_conn = (await conn.get_raw_connection()).dbapi_connection
            conn = await conn.execution_options(isolation_level="SERIALIZABLE")
            await self._insert(conn, 1)
            assert await observer(1) == 0
            await conn.rollback()

        async with eng.connect() as conn:
            assert (await conn.get_raw_connection()).dbapi_connection is dbapi_conn
            assert eng.dialect.detect_autocommit_setting(dbapi_conn) is True
            await self._insert(conn, 2)
            assert await observer(2) == 1
        assert await observer(1) == 0

    async def test_invalid_level_raises_argument_error_on_every_path(
        self, make_engine: Callable[..., AsyncEngine]
    ):
        with pytest.raises(sa.exc.ArgumentError, match="Invalid value 'BOGUS'"):
            async with make_engine(isolation_level="BOGUS").connect():
                pass
        with pytest.raises(sa.exc.ArgumentError, match="Invalid value 'BOGUS'"):
            async with make_engine().execution_options(isolation_level="BOGUS").connect():
                pass
        async with make_engine().connect() as conn:
            with pytest.raises(sa.exc.ArgumentError, match="Invalid value 'BOGUS'"):
                _ = await conn.execution_options(isolation_level="BOGUS")


class TestAsyncCancellationAndDeadline:
    """A cancelled or timed-out query retires the session; the pool recovers (#479 gap 4).

    When the caller cancels an outstanding request, pycubrid retires the session
    and raises ``asyncio.CancelledError`` (kept through pycubrid#554/pycubrid#556 in
    1.9.0 and pycubrid#687/pycubrid#744 in 1.10.0), so ``asyncio.wait_for()`` surfaces the built-in
    ``TimeoutError``. pycubrid's own ``read_timeout`` deadline raises
    ``OperationalError``, which the dialect classifies as a disconnect (#624).
    Either way SQLAlchemy must invalidate the connection instead of returning the
    broken session to the pool, and the next checkout must get a working
    connection without leaking a pool slot. Both tests pass on the 1.8.0 floor
    as well, so they carry no version gate.
    """

    _SELECT_ONE = text("SELECT 1")
    _SLOW_QUERY = text("SELECT SLEEP(5)")

    @staticmethod
    def _make_engine(**query: str) -> tuple[AsyncEngine, list[BaseException | None]]:
        url = _async_url().update_query_dict(query) if query else _async_url()
        # One slot and no overflow: a leaked or never-returned connection would
        # make the next checkout wait for pool_timeout and fail.
        eng = create_async_engine(url, pool_size=1, max_overflow=0, pool_timeout=5)
        invalidated: list[BaseException | None] = []
        sa.event.listen(
            eng.sync_engine.pool,
            "invalidate",
            lambda _dbapi_conn, _record, exc: invalidated.append(exc),
        )
        return eng, invalidated

    @classmethod
    async def _assert_fresh_checkout(cls, eng: AsyncEngine, broken: object) -> None:
        pool = eng.sync_engine.pool
        assert pool.checkedout() == 0, pool.status()
        async with eng.connect() as conn:
            assert (await conn.execute(cls._SELECT_ONE)).scalar() == 1
            assert (await conn.get_raw_connection()).driver_connection is not broken
            assert pool.checkedout() == 1, pool.status()
        assert pool.checkedout() == 0, pool.status()
        assert pool.checkedin() == 1, pool.status()

    async def test_wait_for_timeout_discards_the_connection(self):
        eng, invalidated = self._make_engine()
        try:
            async with eng.connect() as conn:
                assert (await conn.execute(self._SELECT_ONE)).scalar() == 1
                broken = (await conn.get_raw_connection()).driver_connection
                started = asyncio.get_running_loop().time()
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(conn.execute(self._SLOW_QUERY), timeout=0.2)
                # The deadline fired; the query did not run to completion.
                assert asyncio.get_running_loop().time() - started < 3
                assert conn.invalidated is True
            assert len(invalidated) == 1, invalidated
            await self._assert_fresh_checkout(eng, broken)
        finally:
            await eng.dispose()

    async def test_driver_read_timeout_is_a_disconnect(self):
        pycubrid = pytest.importorskip("pycubrid")
        eng, invalidated = self._make_engine(read_timeout="0.5")
        try:
            async with eng.connect() as conn:
                assert (await conn.execute(self._SELECT_ONE)).scalar() == 1
                broken = (await conn.get_raw_connection()).driver_connection
                started = asyncio.get_running_loop().time()
                with pytest.raises(sa.exc.OperationalError, match="read timeout") as excinfo:
                    _ = await conn.execute(self._SLOW_QUERY)
                assert asyncio.get_running_loop().time() - started < 3
                assert excinfo.value.connection_invalidated is True
                assert isinstance(excinfo.value.orig, pycubrid.OperationalError)
                assert conn.invalidated is True
            assert invalidated == [excinfo.value.orig]
            await self._assert_fresh_checkout(eng, broken)
        finally:
            await eng.dispose()
