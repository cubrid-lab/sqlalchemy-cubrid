"""Live SQLAlchemy-facing BLOB/CLOB value contract (#485), independent of any
pycubrid LOB-handle API.

pycubrid is adding official LOB-handle binding/fetch operations and stateful
LOB semantics (cubrid-lab/pycubrid#441, #442). SQLAlchemy users interact with
BLOB/CLOB through ``LargeBinary``/``BLOB``/``Text``/``CLOB`` *values*, never
driver handles, and that value contract must stay verified independently of
whatever pycubrid exposes at the cursor/handle level.

Binding a value into a BLOB/CLOB column already round-trips correctly on
every released driver (writes are verified below with ``BLOB_TO_BIT``/
``CLOB_TO_CHAR`` server-side conversion, which reads back exactly what was
written). What does **not** round-trip yet is a plain ``SELECT`` read: every
currently released pycubrid (and CUBRIDdb) hands back a driver-specific LOB
locator instead of the documented Python value for a non-``NULL`` BLOB/CLOB
column, so those read cases are strict xfails here, tied to the pycubrid
feature that would fix them (cubrid-lab/pycubrid#441) rather than to a pinned
driver/version string: if a future pycubrid release (or CUBRIDdb update)
starts returning the real value, the ``strict=True`` xfail flips to an XPASS
and fails the suite, which is the signal to delete the xfail. ``NULL`` and
``Text``/``STRING`` values are unaffected by the locator and are asserted
directly on every driver.

As of pycubrid 1.8.0 (the supported floor) and pycubrid main, ordinary-cursor
BLOB/CLOB fetch behaves identically: the low-level ``pycubrid.lob.Lob``
handle class pycubrid now ships is not wired into ordinary ``execute()``/
fetch at all (cubrid-lab/pycubrid#441/#442 are still open upstream), so there
is currently nothing to gate behind a pycubrid-main-only code path. The
module docstring and ``docs/DRIVER_COMPAT.md`` are the place to record it if
that changes.

This is a dedicated module rather than more additions to the already very
large ``test/test_integration.py``/``test/test_aio_integration.py`` (moved
from there, where PR #490 first added them); the sync tests select their
driver from ``CUBRID_TEST_URL``, and the async tests derive the async route
from it (``scripts.integration_urls.async_url``), covering Core and ORM, sync
and async, on CUBRIDdb and pycubrid, in one place.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import cast

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, select
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from scripts.integration_urls import async_url
from sqlalchemy_cubrid import BLOB, CLOB

# The shared gate in test/conftest.py skips these tests when CUBRID_TEST_URL is
# unset and errors them when its server is unreachable (#593).
pytestmark = pytest.mark.integration

_DEFAULT_URL = "cubrid://dba@localhost:33000/testdb"

# pycubrid documents (``pycubrid.lob.Lob.read``) that the CUBRID broker caps a
# single LOB_READ response at ~80 KB. The large payloads below exceed that
# chunk so a value assembled from one partial read cannot pass.
_LOB_READ_CHUNK_BYTES = 80 * 1024
_LOB_SMALL_BYTES = b"\x00\x01\x7f\x80\xfe\xff binary"
_LOB_LARGE_BYTES = bytes(range(256)) * 1024  # 256 KiB, every byte value
_LOB_SMALL_TEXT = "plain clob text"
_LOB_CJK_TEXT = "한국어 CLOB 日本語 中文 ✓ — ümlaut"
_LOB_LARGE_TEXT = (_LOB_CJK_TEXT + " / ") * 8000  # > 80 KB when UTF-8 encoded

# column kind -> (SQLAlchemy type, documented Python value type)
_LOB_KINDS = {
    "large_binary": (sa.LargeBinary, bytes),
    "blob": (BLOB, bytes),
    "clob": (CLOB, str),
    "text": (sa.Text, str),
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

# Released drivers hand back a LOB locator instead of the value for BLOB/CLOB
# columns. NULL and ``Text`` (CUBRID ``STRING``) values are unaffected. Keyed
# by DB-API driver name (``engine.dialect.driver``), not pinned to a version:
# the reason names the upstream feature that would resolve it, and
# ``strict=True`` below turns a fix into a loud XPASS failure instead of a
# silent pass-through.
_PYCUBRID_LOCATOR_REASON = (
    "released pycubrid (and pycubrid main) fetches BLOB/CLOB columns as a raw "
    "LOB-handle dict/locator (sync: lob_type/lob_length/file_locator; async: the "
    "file_locator string) instead of bytes/str; official LOB fetch is "
    "cubrid-lab/pycubrid#441"
)
_LOB_LOCATOR_XFAIL = {
    "pycubrid": _PYCUBRID_LOCATOR_REASON,
    "aiopycubrid": _PYCUBRID_LOCATOR_REASON,
    "cubrid": (
        "CUBRIDdb fetches BLOB/CLOB columns as the server file-locator string "
        "('file:...') instead of bytes/str (#485)"
    ),
}


def _xfail_lob_locator(
    request: pytest.FixtureRequest, driver: str, kind: str, value: object
) -> None:
    reason = _LOB_LOCATOR_XFAIL.get(driver)
    if reason is not None and kind != "text" and value is not None:
        request.applymarker(
            pytest.mark.xfail(strict=True, raises=(AssertionError, TypeError), reason=reason)
        )


def _assert_lob_value(got: object, kind: str, expected: object) -> None:
    if expected is None:
        assert got is None
        return
    value_type = _LOB_KINDS[kind][1]
    assert type(got) is value_type, f"expected {value_type.__name__}, got {type(got)!r}"
    assert len(got) == len(expected)
    assert got == expected


def _sync_url() -> URL:
    return make_url(os.environ.get("CUBRID_TEST_URL", _DEFAULT_URL))


def _async_url() -> URL:
    sync = os.environ.get("CUBRID_TEST_URL", _DEFAULT_URL)
    return async_url(sync, os.environ.get("CUBRID_TEST_AURL"))


class TestLobPayloadSizes:
    def test_large_payloads_exceed_driver_lob_read_chunk(self) -> None:
        assert len(_LOB_LARGE_BYTES) > _LOB_READ_CHUNK_BYTES
        assert len(_LOB_LARGE_TEXT.encode("utf-8")) > _LOB_READ_CHUNK_BYTES


# ---------------------------------------------------------------------------
# Sync Core / ORM
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    eng = create_engine(_sync_url(), echo=False)
    yield eng
    eng.dispose()


class TestLobValueContractCore:
    @pytest.fixture(scope="class")
    def lob_table(self, engine: Engine) -> Iterator[Table]:
        meta = MetaData()
        table = Table(
            "lob_value_contract_core",
            meta,
            Column("id", Integer, primary_key=True, autoincrement=False),
            *(Column(kind, type_) for kind, (type_, _) in _LOB_KINDS.items()),
        )
        meta.drop_all(engine)
        meta.create_all(engine)
        yield table
        meta.drop_all(engine)

    @pytest.mark.parametrize(("kind", "value"), _LOB_CASES)
    def test_roundtrip(
        self,
        request: pytest.FixtureRequest,
        engine: Engine,
        lob_table: Table,
        kind: str,
        value: object,
    ) -> None:
        _xfail_lob_locator(request, engine.dialect.driver, kind, value)
        with engine.begin() as conn:
            conn.execute(lob_table.delete())
            conn.execute(lob_table.insert(), {"id": 1, kind: value})
        with engine.connect() as conn:
            got = conn.execute(select(lob_table.c[kind]).where(lob_table.c.id == 1)).scalar_one()
        _assert_lob_value(got, kind, value)

    @pytest.mark.parametrize(
        ("kind", "value"),
        [p for p in _LOB_CASES if p.values[0] in ("large_binary", "blob", "clob") and p.values[1]],
    )
    def test_write_stores_full_value(
        self, engine: Engine, lob_table: Table, kind: str, value: object
    ) -> None:
        """Bound bytes/str reach the LOB intact; read back via server-side conversion."""
        column = lob_table.c[kind]
        convert = sa.func.CLOB_TO_CHAR if kind == "clob" else sa.func.BLOB_TO_BIT
        with engine.begin() as conn:
            conn.execute(lob_table.delete())
            conn.execute(lob_table.insert(), {"id": 1, kind: value})
        with engine.connect() as conn:
            got = conn.execute(select(convert(column)).where(lob_table.c.id == 1)).scalar_one()
        _assert_lob_value(got, kind, value)


class _LobBase(DeclarativeBase):
    pass


class _LobDocument(_LobBase):
    __tablename__ = "lob_value_contract_orm"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    large_binary: Mapped[bytes | None] = mapped_column(sa.LargeBinary)
    blob: Mapped[bytes | None] = mapped_column(BLOB)
    clob: Mapped[str | None] = mapped_column(CLOB)
    text: Mapped[str | None] = mapped_column(sa.Text)


class TestLobValueContractORM:
    @pytest.fixture(scope="class")
    def lob_orm_table(self, engine: Engine) -> Iterator[None]:
        _LobBase.metadata.drop_all(engine)
        _LobBase.metadata.create_all(engine)
        yield
        _LobBase.metadata.drop_all(engine)

    @pytest.mark.parametrize(("kind", "value"), _LOB_CASES)
    def test_roundtrip(
        self,
        request: pytest.FixtureRequest,
        engine: Engine,
        lob_orm_table: None,
        kind: str,
        value: object,
    ) -> None:
        _xfail_lob_locator(request, engine.dialect.driver, kind, value)
        with Session(engine) as session, session.begin():
            session.query(_LobDocument).delete()
            session.add(_LobDocument(id=1, **{kind: value}))
        with Session(engine) as session:
            doc = session.get(_LobDocument, 1)
            assert doc is not None
            got = getattr(doc, kind)
        _assert_lob_value(got, kind, value)

    def test_insert_with_unset_columns(self, engine: Engine, lob_orm_table: None) -> None:
        # #500: the async DB-API adapter lacked ``Binary``, so any LargeBinary/BLOB
        # bind (even an unset ORM column, which still binds ``None``) raised
        # AttributeError. Kept here (sync and async) as a direct regression test
        # for an *unset* mapped attribute, which is a distinct bind path from the
        # explicit ``None`` already covered by ``test_roundtrip``.
        with Session(engine) as session, session.begin():
            session.query(_LobDocument).delete()
            session.add(_LobDocument(id=2))
        with Session(engine) as session:
            doc = session.get(_LobDocument, 2)
            assert doc is not None
            assert doc.large_binary is None
            assert doc.blob is None
            assert doc.clob is None
            assert doc.text is None


# ---------------------------------------------------------------------------
# Async Core / ORM
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def async_engine() -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(_async_url())
    async with eng.begin() as conn:
        await conn.run_sync(_LobBase.metadata.drop_all)
        await conn.run_sync(_LobBase.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(_LobBase.metadata.drop_all)
    await eng.dispose()


def _async_driver(engine: AsyncEngine) -> str:
    return engine.sync_engine.dialect.driver


@pytest.mark.asyncio
class TestAsyncLobValueContract:
    @pytest.mark.parametrize(("kind", "value"), _LOB_CASES)
    async def test_core_roundtrip(
        self,
        request: pytest.FixtureRequest,
        async_engine: AsyncEngine,
        kind: str,
        value: object,
    ) -> None:
        _xfail_lob_locator(request, _async_driver(async_engine), kind, value)
        table = cast(Table, _LobDocument.__table__)
        async with async_engine.begin() as conn:
            await conn.execute(table.insert(), {"id": 1, kind: value})
        async with async_engine.connect() as conn:
            result = await conn.execute(select(table.c[kind]).where(table.c.id == 1))
            got = result.scalar_one()
        _assert_lob_value(got, kind, value)

    @pytest.mark.parametrize(
        ("kind", "value"),
        [p for p in _LOB_CASES if p.values[0] in ("large_binary", "blob", "clob") and p.values[1]],
    )
    async def test_write_stores_full_value(
        self, async_engine: AsyncEngine, kind: str, value: object
    ) -> None:
        table = cast(Table, _LobDocument.__table__)
        convert = sa.func.CLOB_TO_CHAR if kind == "clob" else sa.func.BLOB_TO_BIT
        async with async_engine.begin() as conn:
            await conn.execute(table.insert(), {"id": 1, kind: value})
        async with async_engine.connect() as conn:
            result = await conn.execute(select(convert(table.c[kind])).where(table.c.id == 1))
            got = result.scalar_one()
        _assert_lob_value(got, kind, value)

    @pytest.mark.parametrize(("kind", "value"), _LOB_CASES)
    async def test_orm_roundtrip(
        self,
        request: pytest.FixtureRequest,
        async_engine: AsyncEngine,
        kind: str,
        value: object,
    ) -> None:
        _xfail_lob_locator(request, _async_driver(async_engine), kind, value)
        async with AsyncSession(async_engine) as session, session.begin():
            session.add(_LobDocument(id=1, **{kind: value}))
        async with AsyncSession(async_engine) as session:
            doc = await session.get(_LobDocument, 1)
            assert doc is not None
            got = getattr(doc, kind)
        _assert_lob_value(got, kind, value)

    async def test_orm_insert_with_unset_columns(self, async_engine: AsyncEngine) -> None:
        async with AsyncSession(async_engine) as session, session.begin():
            session.add(_LobDocument(id=2))
        async with AsyncSession(async_engine) as session:
            doc = await session.get(_LobDocument, 2)
            assert doc is not None
            assert doc.large_binary is None
            assert doc.blob is None
            assert doc.clob is None
            assert doc.text is None
