from __future__ import annotations

import asyncio
import json
import os
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

from sqlalchemy_cubrid import BLOB, CLOB

from scripts.integration_urls import async_url
from test.pycubrid_upstream import xfail_unreleased_pycubrid_fix

_DEFAULT_SYNC_URL = "cubrid://dba@localhost:33000/testdb"


class SupportsAutocommit(Protocol):
    autocommit: bool


class SupportsPing(Protocol):
    def ping(self, reconnect: bool = True) -> bool: ...


def _async_url() -> URL:
    sync = os.environ.get("CUBRID_TEST_URL", _DEFAULT_SYNC_URL)
    return async_url(sync, os.environ.get("CUBRID_TEST_AURL"))


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


# ---------------------------------------------------------------------------
# #485: SQLAlchemy-facing BLOB/CLOB value contract (async)
# ---------------------------------------------------------------------------

# Same payloads as test_integration.py; the large ones exceed the ~80 KB
# LOB_READ chunk documented by ``pycubrid.lob.Lob.read``.
_LOB_READ_CHUNK_BYTES = 80 * 1024
_LOB_SMALL_BYTES = b"\x00\x01\x7f\x80\xfe\xff binary"
_LOB_LARGE_BYTES = bytes(range(256)) * 1024
_LOB_SMALL_TEXT = "plain clob text"
_LOB_CJK_TEXT = "한국어 CLOB 日本語 中文 ✓ — ümlaut"
_LOB_LARGE_TEXT = (_LOB_CJK_TEXT + " / ") * 8000

_LOB_VALUE_TYPES: dict[str, type] = {
    "large_binary": bytes,
    "blob": bytes,
    "clob": str,
    "text": str,
}

_LOB_CASES = [
    pytest.param("large_binary", _LOB_SMALL_BYTES, id="large_binary-small"),
    pytest.param("large_binary", _LOB_LARGE_BYTES, id="large_binary-large"),
    pytest.param("large_binary", None, id="large_binary-null"),
    pytest.param("blob", _LOB_SMALL_BYTES, id="blob-small"),
    pytest.param("blob", _LOB_LARGE_BYTES, id="blob-large"),
    pytest.param("blob", None, id="blob-null"),
    pytest.param("clob", _LOB_SMALL_TEXT, id="clob-small"),
    pytest.param("clob", _LOB_CJK_TEXT, id="clob-cjk"),
    pytest.param("clob", _LOB_LARGE_TEXT, id="clob-large"),
    pytest.param("clob", None, id="clob-null"),
    pytest.param("text", _LOB_SMALL_TEXT, id="text-small"),
    pytest.param("text", _LOB_CJK_TEXT, id="text-cjk"),
    pytest.param("text", _LOB_LARGE_TEXT, id="text-large"),
    pytest.param("text", None, id="text-null"),
]


def _xfail_async_lob(request: pytest.FixtureRequest, kind: str, value: object) -> None:
    # Binding works since #500; only the non-NULL LOB *read* still returns the
    # driver's LOB-handle dict instead of bytes/str (pycubrid#441, #485).
    if kind in ("large_binary", "blob", "clob") and value is not None:
        request.applymarker(
            pytest.mark.xfail(
                strict=True,
                raises=(AssertionError, TypeError),
                reason=(
                    "released pycubrid fetches BLOB/CLOB columns as a raw LOB-handle dict "
                    "instead of bytes/str; official LOB fetch is cubrid-lab/pycubrid#441"
                ),
            )
        )


def _assert_lob_value(got: object, kind: str, expected: bytes | str | None) -> None:
    if expected is None:
        assert got is None
        return
    value_type = _LOB_VALUE_TYPES[kind]
    assert type(got) is value_type, f"expected {value_type.__name__}, got {type(got)!r}"
    assert got == expected


class _AsyncLobBase(DeclarativeBase):
    pass


# Binary and character LOB columns live in separate tables: an ORM INSERT binds
# every mapped column, so a LargeBinary column would break unrelated cases.
class _AsyncBinaryLobDocument(_AsyncLobBase):
    __tablename__ = "aio_test_lob485_binary"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    large_binary: Mapped[bytes | None] = mapped_column(sa.LargeBinary)
    blob: Mapped[bytes | None] = mapped_column(BLOB)


class _AsyncCharLobDocument(_AsyncLobBase):
    __tablename__ = "aio_test_lob485_char"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    clob: Mapped[str | None] = mapped_column(CLOB)
    text: Mapped[str | None] = mapped_column(sa.Text)


def _async_lob_model(kind: str) -> type[_AsyncLobBase]:
    if kind in ("large_binary", "blob"):
        return _AsyncBinaryLobDocument
    return _AsyncCharLobDocument


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


class TestAsyncLobValueContract:
    @pytest_asyncio.fixture(autouse=True)
    async def _lob_table(self, engine: AsyncEngine) -> AsyncIterator[None]:
        async with engine.begin() as conn:
            await conn.run_sync(_AsyncLobBase.metadata.drop_all)
            await conn.run_sync(_AsyncLobBase.metadata.create_all)
        yield
        async with engine.begin() as conn:
            await conn.run_sync(_AsyncLobBase.metadata.drop_all)

    def test_large_payloads_exceed_driver_lob_read_chunk(self):
        assert len(_LOB_LARGE_BYTES) > _LOB_READ_CHUNK_BYTES
        assert len(_LOB_LARGE_TEXT.encode("utf-8")) > _LOB_READ_CHUNK_BYTES

    @pytest.mark.parametrize(("kind", "value"), _LOB_CASES)
    async def test_core_roundtrip(
        self,
        request: pytest.FixtureRequest,
        engine: AsyncEngine,
        kind: str,
        value: bytes | str | None,
    ):
        _xfail_async_lob(request, kind, value)
        table = cast(Table, _async_lob_model(kind).__table__)
        async with engine.begin() as conn:
            _ = await conn.execute(table.insert(), {"id": 1, kind: value})
        async with engine.connect() as conn:
            result = await conn.execute(select(table.c[kind]).where(table.c.id == 1))
            got = result.scalar_one()
        _assert_lob_value(got, kind, value)

    @pytest.mark.parametrize(
        ("kind", "value"),
        [p for p in _LOB_CASES if p.values[0] in ("large_binary", "blob", "clob") and p.values[1]],
    )
    async def test_write_stores_full_value(
        self, engine: AsyncEngine, kind: str, value: bytes | str | None
    ):
        """Bound bytes/str reach the LOB intact; read back via server-side conversion."""
        table = cast(Table, _async_lob_model(kind).__table__)
        convert = sa.func.CLOB_TO_CHAR if kind == "clob" else sa.func.BLOB_TO_BIT
        async with engine.begin() as conn:
            _ = await conn.execute(table.insert(), {"id": 1, kind: value})
        async with engine.connect() as conn:
            result = await conn.execute(select(convert(table.c[kind])).where(table.c.id == 1))
            got = result.scalar_one()
        _assert_lob_value(got, kind, value)

    # #500: the async DB-API adapter lacked ``Binary``, so any LargeBinary/BLOB
    # bind (even ``None``, even an unset ORM column) raised AttributeError.
    @pytest.mark.parametrize("kind", ["large_binary", "blob"])
    @pytest.mark.parametrize("value", [None, _LOB_SMALL_BYTES], ids=["none", "bytes"])
    async def test_core_insert_binds_binary(
        self, engine: AsyncEngine, kind: str, value: bytes | None
    ):
        table = cast(Table, _AsyncBinaryLobDocument.__table__)
        async with engine.begin() as conn:
            _ = await conn.execute(sa.insert(table).values(id=1, **{kind: value}))
        async with engine.connect() as conn:
            result = await conn.execute(
                select(table.c[kind].is_(None), sa.func.BLOB_TO_BIT(table.c[kind])).where(
                    table.c.id == 1
                )
            )
            is_null, stored = result.one()
        assert bool(is_null) is (value is None)
        _assert_lob_value(stored, kind, value)

    async def test_orm_insert_with_unset_large_binary(self, engine: AsyncEngine):
        async with AsyncSession(engine) as session:
            session.add(_AsyncBinaryLobDocument(id=3))
            await session.commit()
        async with AsyncSession(engine) as session:
            doc = await session.get(_AsyncBinaryLobDocument, 3)
            assert doc is not None
            assert doc.large_binary is None
            assert doc.blob is None

    @pytest.mark.parametrize(("kind", "value"), _LOB_CASES)
    async def test_orm_roundtrip(
        self,
        request: pytest.FixtureRequest,
        engine: AsyncEngine,
        kind: str,
        value: bytes | str | None,
    ):
        _xfail_async_lob(request, kind, value)
        model = _async_lob_model(kind)
        async with AsyncSession(engine) as session, session.begin():
            session.add(model(id=1, **{kind: value}))
        async with AsyncSession(engine) as session:
            doc = await session.get(model, 1)
            assert doc is not None
            got = getattr(doc, kind)
        _assert_lob_value(got, kind, value)


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
        request: pytest.FixtureRequest,
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
            # ``_ConnectionFairy.driver_connection`` returns the SQLAlchemy adapter
            # here (the dialect does not override ``get_driver_connection()``),
            # so reach the ``pycubrid.aio`` connection through the adapter.
            adapter = (await conn.get_raw_connection()).dbapi_connection
            driver_conn = adapter.driver_connection
            cursor = driver_conn.cursor()
            try:
                await cursor.execute("SELECT 1")
                assert await cursor.fetchall() == [(1,)]
                await cursor.execute("SELECT id, payload FROM aio_test_rc481 ORDER BY id")
                # The first response must not hold the whole result.
                assert 0 < cursor._fetched_count < _WIDE_ROWS
                first = await cursor.fetchone()
                assert first is not None and first[0] == 0
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
                    # Whatever was returned is an in-order prefix with intact payloads.
                    ids = [first[0]] + [row[0] for row in rest]
                    assert ids == list(range(len(ids)))
                    assert all(row[1] == _WIDE_PAYLOAD for row in rest)
                # Only the completeness check is gated; an explicit error passes,
                # which is a strict XPASS on a build that already raises.
                xfail_unreleased_pycubrid_fix(
                    request, engine.dialect.driver, 395, raises=AssertionError
                )
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


def _xfail_async_integrity(request: pytest.FixtureRequest, driver: str, kind: str) -> None:
    # Released pycubrid raises NOT NULL (-631) and FK (-922) violations as a
    # generic DatabaseError; unique/PK (-670) is already an IntegrityError.
    if kind != "unique_pk":
        xfail_unreleased_pycubrid_fix(request, driver, 390, raises=AssertionError)


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
    async def test_core_violation_raises_integrity_error(
        self, request: pytest.FixtureRequest, engine: AsyncEngine, kind: str
    ):
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
        # Only the class check is gated; the checks above never are.
        _xfail_async_integrity(request, engine.dialect.driver, kind)
        _assert_integrity_error(engine, excinfo.value)

    @pytest.mark.parametrize("kind", list(_ASYNC_INTEGRITY_VIOLATIONS))
    async def test_orm_flush_violation_raises_integrity_error(
        self, request: pytest.FixtureRequest, engine: AsyncEngine, kind: str
    ):
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
        # Only the class check is gated; the checks above never are.
        _xfail_async_integrity(request, engine.dialect.driver, kind)
        _assert_integrity_error(engine, excinfo.value)
