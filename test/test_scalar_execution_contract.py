"""Live SQLAlchemy scalar binding contract, verified through the ordinary
PEP 249 ``execute()``/``executemany()`` DB-API path rather than assuming
native prepared execution (#483).

pycubrid#439 added an additive, opt-in sync prepared/typed scalar-binding
cursor under ``pycubrid.compat.native`` (INT32, UTF-8 ``CHAR`` and SQL
``NULL`` only), released in pycubrid 1.8.0 (the supported floor). Ordinary
sync and async DB-API execution is unaffected and stays on the existing FC41
path: neither ``sqlalchemy_cubrid.pycubrid_dialect`` nor
``sqlalchemy_cubrid.aio_pycubrid_dialect`` import or call
``pycubrid.compat`` anywhere, so SQLAlchemy cannot transparently gain typed
FC3 binding merely because the driver now has it, and the dialect does not
call pycubrid's lower-level compat APIs to manufacture that claim. The
preferred outcome stays "no dialect implementation change" (per #483); these
tests document that the existing ordinary scalar contract is correct and
that the compatibility surface genuinely has no effect, rather than adding
prepared-specific acceptance tests for an integration that is not designed
or released.

This is a dedicated module (the #484/#485 pattern,
``test/test_collection_roundtrip.py`` / ``test/test_lob_value_contract.py``)
rather than more additions to ``test/test_integration.py`` /
``test/test_aio_integration.py``. Cases: integer, UTF-8/CJK string, ``NULL``,
repeated execution of the same compiled statement, ordinary
``executemany()``, Core inserts/updates, ORM flush, a failed bind followed by
connection reuse, and sync/async, verified on CUBRID 10.2 and 11.4 with
pycubrid 1.8.0, pycubrid main and CUBRIDdb. None of this is blocked or
xfailed: ordinary scalar execution already works correctly on every driver
tested.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any, cast

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, select
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from scripts.integration_urls import async_url

# The shared gate in test/conftest.py skips these tests when CUBRID_TEST_URL is
# unset and errors them when its server is unreachable (#593).
pytestmark = pytest.mark.integration

_DEFAULT_URL = "cubrid://dba@localhost:33000/testdb"
_CJK_TEXT = "한국어 스칼라 日本語 中文 ✓ — ümlaut"

# column kind -> (SQLAlchemy type, documented Python value type)
_SCALAR_KINDS: dict[str, tuple[sa.types.TypeEngine[Any], type]] = {
    "n": (Integer(), int),
    "s": (String(200), str),
}

_SCALAR_CASES = [
    pytest.param("n", 1, id="int-positive"),
    pytest.param("n", -7, id="int-negative"),
    pytest.param("n", 0, id="int-zero"),
    pytest.param("n", None, id="int-null"),
    pytest.param("s", "plain ascii", id="string-ascii"),
    pytest.param("s", _CJK_TEXT, id="string-cjk"),
    pytest.param("s", "", id="string-empty"),
    pytest.param("s", None, id="string-null"),
]


def _assert_scalar_value(got: object, kind: str, expected: object) -> None:
    if expected is None:
        assert got is None
        return
    value_type = _SCALAR_KINDS[kind][1]
    assert type(got) is value_type, f"expected {value_type.__name__}, got {type(got)!r}"
    assert got == expected


def _sync_url() -> URL:
    return make_url(os.environ.get("CUBRID_TEST_URL", _DEFAULT_URL))


def _async_url() -> URL:
    sync = os.environ.get("CUBRID_TEST_URL", _DEFAULT_URL)
    return async_url(sync, os.environ.get("CUBRID_TEST_AURL"))


class TestDialectDoesNotReferenceCompatNative:
    """Offline: the dialect source never imports/calls ``pycubrid.compat`` (#483).

    Ordinary sync/async DB-API execution must stay on FC41 regardless of what
    the installed pycubrid additionally offers under ``compat.native`` /
    ``compat.cubriddb``; scanning the source keeps that claim true rather than
    letting it silently rot if a later change wires in a "faster" prepared
    path without a documented, released SQLAlchemy/DB-API integration design.
    """

    def test_dialect_source_has_no_compat_reference(self) -> None:
        import sqlalchemy_cubrid

        package_dir = Path(sqlalchemy_cubrid.__file__).resolve().parent
        # Scoped to pycubrid's compatibility namespace, not the project's own
        # unrelated ``sqlalchemy_cubrid._compat`` shim module.
        needles = (
            "pycubrid.compat",
            "from pycubrid import compat",
            "compat.native",
            "compat.cubriddb",
        )
        offenders = {
            path.name: hit
            for path in sorted(package_dir.glob("*.py"))
            for hit in needles
            if hit in path.read_text(encoding="utf-8")
        }
        assert not offenders, f"dialect source references pycubrid.compat: {offenders}"


class TestCompatNativeNotInvoked:
    """Live: ordinary engine use never touches ``pycubrid.compat.native`` (#483)."""

    def test_ordinary_use_never_calls_compat_native_connect(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        url = _sync_url()
        if url.get_driver_name() != "pycubrid":
            pytest.skip("pycubrid.compat.native is a pycubrid-only surface")
        pycubrid_compat_native = pytest.importorskip("pycubrid.compat.native")

        def _fail_if_called(*args: object, **kwargs: object) -> None:
            raise AssertionError(
                "pycubrid.compat.native.connect() must never be called by the dialect"
            )

        monkeypatch.setattr(pycubrid_compat_native, "connect", _fail_if_called)

        engine = create_engine(url)
        try:
            with engine.begin() as conn:
                conn.execute(sa.text("SELECT 1"))
                meta = MetaData()
                table = Table(
                    "scalar_contract_compat_probe",
                    meta,
                    Column("id", Integer, primary_key=True, autoincrement=False),
                    Column("n", Integer),
                )
                meta.drop_all(conn)
                meta.create_all(conn)
                conn.execute(table.insert(), {"id": 1, "n": 42})
                got = conn.execute(select(table.c.n).where(table.c.id == 1)).scalar_one()
                assert got == 42
                meta.drop_all(conn)
        finally:
            engine.dispose()


# ---------------------------------------------------------------------------
# Sync Core / ORM
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    eng = create_engine(_sync_url(), echo=False)
    yield eng
    eng.dispose()


class TestScalarValueContractCore:
    @pytest.fixture(scope="class")
    def scalar_table(self, engine: Engine) -> Iterator[Table]:
        meta = MetaData()
        table = Table(
            "scalar_contract_core",
            meta,
            Column("id", Integer, primary_key=True, autoincrement=False),
            *(Column(kind, type_) for kind, (type_, _) in _SCALAR_KINDS.items()),
        )
        meta.drop_all(engine)
        meta.create_all(engine)
        yield table
        meta.drop_all(engine)

    @pytest.mark.parametrize(("kind", "value"), _SCALAR_CASES)
    def test_roundtrip(self, engine: Engine, scalar_table: Table, kind: str, value: object) -> None:
        with engine.begin() as conn:
            conn.execute(scalar_table.delete())
            conn.execute(scalar_table.insert(), {"id": 1, kind: value})
        with engine.connect() as conn:
            got = conn.execute(
                select(scalar_table.c[kind]).where(scalar_table.c.id == 1)
            ).scalar_one()
        _assert_scalar_value(got, kind, value)

    def test_update(self, engine: Engine, scalar_table: Table) -> None:
        with engine.begin() as conn:
            conn.execute(scalar_table.delete())
            conn.execute(scalar_table.insert(), {"id": 1, "n": 1, "s": "before"})
            conn.execute(
                scalar_table.update().where(scalar_table.c.id == 1).values(n=2, s=_CJK_TEXT)
            )
        with engine.connect() as conn:
            row = conn.execute(select(scalar_table.c.n, scalar_table.c.s)).one()
        assert (row.n, row.s) == (2, _CJK_TEXT)

    def test_repeated_execution_binds_fresh_values(
        self, engine: Engine, scalar_table: Table
    ) -> None:
        """The same compiled ``insert()`` construct, executed repeatedly, binds
        each call's own parameters rather than any cached/stale value."""
        insert_stmt = scalar_table.insert()
        rows = [{"id": i, "n": i * 3, "s": f"row-{i}-{_CJK_TEXT}"} for i in range(1, 26)]
        with engine.begin() as conn:
            conn.execute(scalar_table.delete())
            for row in rows:
                conn.execute(insert_stmt, row)
        with engine.connect() as conn:
            got = conn.execute(select(scalar_table).order_by(scalar_table.c.id)).all()
        assert [(r.id, r.n, r.s) for r in got] == [(r["id"], r["n"], r["s"]) for r in rows]


def _spy_executemany(dialect: object, monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Record the number of parameter sets of every ``do_executemany`` call."""
    calls: list[int] = []
    original = dialect.do_executemany  # type: ignore[attr-defined]

    def spy(
        cursor: object, statement: object, parameters: object, context: object = None
    ) -> object:
        calls.append(len(parameters))  # type: ignore[arg-type]
        return original(cursor, statement, parameters, context)

    monkeypatch.setattr(dialect, "do_executemany", spy)
    return calls


class TestScalarExecutemany:
    def test_ordinary_executemany(self, monkeypatch: pytest.MonkeyPatch) -> None:
        eng = create_engine(_sync_url(), use_insertmanyvalues=False)
        meta = MetaData()
        table = Table(
            "scalar_contract_executemany",
            meta,
            Column("id", Integer, primary_key=True, autoincrement=False),
            Column("n", Integer),
            Column("s", String(200)),
        )
        try:
            meta.drop_all(eng)
            meta.create_all(eng)
            calls = _spy_executemany(eng.dialect, monkeypatch)
            rows: list[dict[str, Any]] = [
                {"id": 1, "n": 1, "s": "a"},
                {"id": 2, "n": None, "s": _CJK_TEXT},
                {"id": 3, "n": -5, "s": None},
            ]
            with eng.begin() as conn:
                conn.execute(table.insert(), rows)
            with eng.connect() as conn:
                got = conn.execute(select(table).order_by(table.c.id)).all()
        finally:
            meta.drop_all(eng)
            eng.dispose()
        assert calls == [len(rows)]
        assert [(r.id, r.n, r.s) for r in got] == [(r["id"], r["n"], r["s"]) for r in rows]


class _ScalarBase(DeclarativeBase):
    pass


class _ScalarRow(_ScalarBase):
    __tablename__ = "scalar_contract_orm"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    n: Mapped[int | None] = mapped_column(Integer)
    s: Mapped[str | None] = mapped_column(String(200))


class TestScalarORMFlush:
    @pytest.fixture(scope="class")
    def scalar_orm_table(self, engine: Engine) -> Iterator[None]:
        _ScalarBase.metadata.drop_all(engine)
        _ScalarBase.metadata.create_all(engine)
        yield
        _ScalarBase.metadata.drop_all(engine)

    def test_flush_inserts_and_updates(self, engine: Engine, scalar_orm_table: None) -> None:
        with Session(engine) as session, session.begin():
            session.query(_ScalarRow).delete()
            session.add_all(
                [
                    _ScalarRow(id=1, n=10, s="first"),
                    _ScalarRow(id=2, n=None, s=_CJK_TEXT),
                    _ScalarRow(id=3, n=-1, s=None),
                ]
            )
        with Session(engine) as session:
            rows = session.scalars(select(_ScalarRow).order_by(_ScalarRow.id)).all()
            assert [(r.id, r.n, r.s) for r in rows] == [
                (1, 10, "first"),
                (2, None, _CJK_TEXT),
                (3, -1, None),
            ]
            rows[0].n = 99
            rows[0].s = "updated"
            session.commit()
        with Session(engine) as session:
            row = session.get(_ScalarRow, 1)
            assert row is not None
            assert (row.n, row.s) == (99, "updated")


class _NotNullBase(DeclarativeBase):
    pass


class _NotNullRow(_NotNullBase):
    __tablename__ = "scalar_contract_notnull"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    n: Mapped[int] = mapped_column(Integer, nullable=False)


class TestFailedBindThenConnectionReuse:
    """A failed scalar bind (NOT NULL violation) does not strand the
    connection/session: the same DBAPI connection runs new statements
    afterward (overlaps #480's broader IntegrityError contract; kept here,
    scoped to a plain scalar bind, for #483's acceptance checklist)."""

    @pytest.fixture(scope="class", autouse=True)
    def notnull_table(self, engine: Engine) -> Iterator[None]:
        _NotNullBase.metadata.drop_all(engine)
        _NotNullBase.metadata.create_all(engine)
        yield
        _NotNullBase.metadata.drop_all(engine)

    def test_core(self, engine: Engine) -> None:
        with engine.connect() as conn:
            raw = conn.connection.dbapi_connection
            with pytest.raises(sa.exc.DBAPIError):
                conn.execute(sa.insert(cast(Table, _NotNullRow.__table__)), {"id": 1, "n": None})
            conn.rollback()
            assert not conn.invalidated
            assert conn.connection.dbapi_connection is raw
            conn.execute(sa.insert(cast(Table, _NotNullRow.__table__)), {"id": 1, "n": 7})
            conn.commit()
            got = conn.execute(select(cast(Table, _NotNullRow.__table__).c.n)).scalar_one()
        assert got == 7

    def test_orm_flush(self, engine: Engine) -> None:
        with engine.connect() as conn, Session(bind=conn) as session:
            raw = conn.connection.dbapi_connection
            session.add(_NotNullRow(id=2, n=None))
            with pytest.raises(sa.exc.DBAPIError):
                session.flush()
            session.rollback()
            assert not conn.invalidated
            assert conn.connection.dbapi_connection is raw
            session.add(_NotNullRow(id=2, n=11))
            session.flush()
            session.commit()
            got = session.scalars(select(_NotNullRow.n).where(_NotNullRow.id == 2)).one()
        assert got == 11


# ---------------------------------------------------------------------------
# Async Core / ORM
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def async_engine() -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(_async_url())
    yield eng
    await eng.dispose()


@pytest.mark.asyncio
class TestAsyncScalarValueContract:
    @pytest_asyncio.fixture(autouse=True)
    async def _scalar_table(self, async_engine: AsyncEngine) -> AsyncIterator[None]:
        meta = MetaData()
        table = Table(
            "scalar_contract_async",
            meta,
            Column("id", Integer, primary_key=True, autoincrement=False),
            *(Column(kind, type_) for kind, (type_, _) in _SCALAR_KINDS.items()),
        )
        self._table = table
        async with async_engine.begin() as conn:
            await conn.run_sync(meta.drop_all)
            await conn.run_sync(meta.create_all)
        yield
        async with async_engine.begin() as conn:
            await conn.run_sync(meta.drop_all)

    @pytest.mark.parametrize(("kind", "value"), _SCALAR_CASES)
    async def test_roundtrip(self, async_engine: AsyncEngine, kind: str, value: object) -> None:
        table = self._table
        async with async_engine.begin() as conn:
            await conn.execute(table.delete())
            await conn.execute(table.insert(), {"id": 1, kind: value})
        async with async_engine.connect() as conn:
            result = await conn.execute(select(table.c[kind]).where(table.c.id == 1))
            got = result.scalar_one()
        _assert_scalar_value(got, kind, value)

    async def test_executemany(
        self, async_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # insertmanyvalues (the default) sends one multi-row INSERT via
        # do_execute(), not do_executemany(); force it off to exercise the
        # ordinary DB-API executemany() path itself.
        table = self._table
        eng = create_async_engine(_async_url(), use_insertmanyvalues=False)
        calls = _spy_executemany(eng.sync_engine.dialect, monkeypatch)
        rows: list[dict[str, Any]] = [
            {"id": 1, "n": 1, "s": "a"},
            {"id": 2, "n": None, "s": _CJK_TEXT},
            {"id": 3, "n": -5, "s": None},
        ]
        try:
            async with eng.begin() as conn:
                await conn.execute(table.delete())
                await conn.execute(table.insert(), rows)
            async with eng.connect() as conn:
                result = await conn.execute(select(table).order_by(table.c.id))
                got = result.all()
        finally:
            await eng.dispose()
        assert calls == [len(rows)]
        assert [(r.id, r.n, r.s) for r in got] == [(r["id"], r["n"], r["s"]) for r in rows]


class _AsyncScalarBase(DeclarativeBase):
    pass


class _AsyncScalarRow(_AsyncScalarBase):
    __tablename__ = "scalar_contract_async_orm"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    n: Mapped[int | None] = mapped_column(Integer)
    s: Mapped[str | None] = mapped_column(String(200))


@pytest.mark.asyncio
class TestAsyncScalarORMFlush:
    @pytest_asyncio.fixture(autouse=True)
    async def _orm_table(self, async_engine: AsyncEngine) -> AsyncIterator[None]:
        async with async_engine.begin() as conn:
            await conn.run_sync(_AsyncScalarBase.metadata.drop_all)
            await conn.run_sync(_AsyncScalarBase.metadata.create_all)
        yield
        async with async_engine.begin() as conn:
            await conn.run_sync(_AsyncScalarBase.metadata.drop_all)

    async def test_flush_inserts_and_updates(self, async_engine: AsyncEngine) -> None:
        async with AsyncSession(async_engine) as session, session.begin():
            session.add_all(
                [
                    _AsyncScalarRow(id=1, n=10, s="first"),
                    _AsyncScalarRow(id=2, n=None, s=_CJK_TEXT),
                ]
            )
        async with AsyncSession(async_engine) as session:
            rows = (
                await session.scalars(select(_AsyncScalarRow).order_by(_AsyncScalarRow.id))
            ).all()
            assert [(r.id, r.n, r.s) for r in rows] == [(1, 10, "first"), (2, None, _CJK_TEXT)]
            rows[0].n = 99
            await session.commit()
        async with AsyncSession(async_engine) as session:
            row = await session.get(_AsyncScalarRow, 1)
            assert row is not None
            assert row.n == 99


class _AsyncNotNullBase(DeclarativeBase):
    pass


class _AsyncNotNullRow(_AsyncNotNullBase):
    __tablename__ = "scalar_contract_async_notnull"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    n: Mapped[int] = mapped_column(Integer, nullable=False)


@pytest.mark.asyncio
class TestAsyncFailedBindThenConnectionReuse:
    @pytest_asyncio.fixture(autouse=True)
    async def _notnull_table(self, async_engine: AsyncEngine) -> AsyncIterator[None]:
        async with async_engine.begin() as conn:
            await conn.run_sync(_AsyncNotNullBase.metadata.drop_all)
            await conn.run_sync(_AsyncNotNullBase.metadata.create_all)
        yield
        async with async_engine.begin() as conn:
            await conn.run_sync(_AsyncNotNullBase.metadata.drop_all)

    async def test_core(self, async_engine: AsyncEngine) -> None:
        async with async_engine.connect() as conn:
            raw = (await conn.get_raw_connection()).dbapi_connection
            with pytest.raises(sa.exc.DBAPIError):
                await conn.execute(
                    sa.insert(cast(Table, _AsyncNotNullRow.__table__)), {"id": 1, "n": None}
                )
            await conn.rollback()
            assert not conn.invalidated
            assert (await conn.get_raw_connection()).dbapi_connection is raw
            await conn.execute(
                sa.insert(cast(Table, _AsyncNotNullRow.__table__)), {"id": 1, "n": 7}
            )
            await conn.commit()
            result = await conn.execute(select(cast(Table, _AsyncNotNullRow.__table__).c.n))
            got = result.scalar_one()
        assert got == 7
