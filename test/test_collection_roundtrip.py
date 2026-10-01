"""Live SET / MULTISET / SEQUENCE round trips through SQLAlchemy (#484).

The pycubrid dialects bind a ``list``/``tuple``/``set``/``frozenset`` value of a
collection column as a ``pycubrid.types.Set``/``Multiset``/``Sequence`` typed
collection parameter (cubrid-lab/pycubrid#567), and read collections back with
``decode_collections=true`` as ``frozenset`` (``SET``) or ``list``
(``MULTISET``/``SEQUENCE``).

The typed parameters are on pycubrid main but not in a release yet: the released
pycubrid (1.8.0, the ``[pycubrid]`` floor) rejects collection parameters, so
every case that binds a collection is a strict xfail there and the upstream
canary (pycubrid@main, ``CUBRID_REQUIRE_TYPED_COLLECTIONS=1``) runs them for
real. A ``NULL`` collection binds on every pycubrid release and is never xfailed.

The sync tests use the driver ``CUBRID_TEST_URL`` selects. On CUBRIDdb
(``cubrid://``) the pycubrid cases are skipped and ``TestCubriddbCollectionBinds``
records what CUBRIDdb does with the same values (docs/DRIVER_COMPAT.md).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, select
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from scripts.integration_urls import async_url
from sqlalchemy_cubrid import MULTISET, SEQUENCE, SET

# The shared gate in test/conftest.py skips these tests when CUBRID_TEST_URL is
# unset and errors them when its server is unreachable (#593).
pytestmark = pytest.mark.integration

_DEFAULT_URL = "cubrid://dba@localhost:33000/testdb"


def _typed_collections_available() -> bool:
    try:
        import pycubrid.types as pycubrid_types
    except ImportError:
        return False
    return all(hasattr(pycubrid_types, name) for name in ("Set", "Multiset", "Sequence"))


_TYPED_COLLECTIONS = _typed_collections_available()
_NO_TYPED_COLLECTIONS_REASON = (
    "the installed pycubrid has no pycubrid.types.Set/Multiset/Sequence (released "
    "pycubrid 1.8.0 rejects collection parameters); typed collection parameters "
    "are on pycubrid main, cubrid-lab/pycubrid#567"
)


#: Set in the lane that installs pycubrid main (upstream-canary.yml): there a
#: missing feature must fail the run instead of turning every case into an xfail.
_REQUIRE_ENV = "CUBRID_REQUIRE_TYPED_COLLECTIONS"


def _xfail_without_typed_collections(request: pytest.FixtureRequest) -> None:
    if not _TYPED_COLLECTIONS:
        if os.environ.get(_REQUIRE_ENV) == "1":
            pytest.fail(f"{_REQUIRE_ENV}=1 but {_NO_TYPED_COLLECTIONS_REASON}", pytrace=False)
        request.applymarker(
            pytest.mark.xfail(
                strict=True, raises=sa.exc.ProgrammingError, reason=_NO_TYPED_COLLECTIONS_REASON
            )
        )


def _decoding(url: URL) -> URL:
    """*url* with pycubrid's collection decoding turned on."""
    return url.update_query_dict({"decode_collections": "true"})


def _sync_url() -> URL:
    return make_url(os.environ.get("CUBRID_TEST_URL", _DEFAULT_URL))


def _async_url() -> URL:
    sync = os.environ.get("CUBRID_TEST_URL", _DEFAULT_URL)
    return _decoding(async_url(sync, os.environ.get("CUBRID_TEST_AURL")))


_metadata = MetaData()
_core = Table(
    "coll_rt_core",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=False),
    Column("s", SET(Integer())),
    Column("ms", MULTISET(String(20))),
    Column("sq", SEQUENCE(Integer())),
    Column("txt", SEQUENCE(String(20))),
)


class _Base(DeclarativeBase):
    pass


class _Tagged(_Base):
    __tablename__ = "coll_rt_orm"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    tags: Mapped[Any] = mapped_column(SET(String(20)), nullable=True)
    scores: Mapped[Any] = mapped_column(MULTISET(Integer()), nullable=True)
    history: Mapped[Any] = mapped_column(SEQUENCE(Integer()), nullable=True)


# id -> (bound row values, values read back). MULTISET order is not kept by the
# server, so MULTISET results are compared sorted (see _normalized).
_ROWS: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {
    "set-unique": (
        {"s": [3, 1, 1, 3]},
        {"s": frozenset({1, 3})},
    ),
    "python-set": (
        {"s": {5, 4}, "ms": frozenset({"x"})},
        {"s": frozenset({4, 5}), "ms": ["x"]},
    ),
    "multiset-duplicates": (
        {"ms": ["b", "a", "b", "a", "a"]},
        {"ms": ["a", "a", "a", "b", "b"]},
    ),
    "sequence-order": (
        {"sq": [3, 1, 2, 1], "txt": ("z", "a", "z")},
        {"sq": [3, 1, 2, 1], "txt": ["z", "a", "z"]},
    ),
    "unicode": (
        {"txt": ["한글", "é", "a'b"], "ms": ["한글", "한글"]},
        {"txt": ["한글", "é", "a'b"], "ms": ["한글", "한글"]},
    ),
    "empty": (
        {"s": set(), "ms": [], "sq": (), "txt": []},
        {"s": frozenset(), "ms": [], "sq": [], "txt": []},
    ),
    "null-elements": (
        {"sq": [None, 2, None]},
        {"sq": [None, 2, None]},
    ),
}
_COLUMNS = ("s", "ms", "sq", "txt")


def _expected(read: dict[str, Any]) -> dict[str, Any]:
    return {name: read.get(name) for name in _COLUMNS}


def _normalized(row: Any) -> dict[str, Any]:
    values = {name: getattr(row, name) for name in _COLUMNS}
    if isinstance(values["ms"], list):
        values["ms"] = sorted(values["ms"])
    return values


def _insert_params(row_id: int, bound: dict[str, Any]) -> dict[str, Any]:
    return {"id": row_id, **{name: bound.get(name) for name in _COLUMNS}}


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    url = _sync_url()
    if url.get_driver_name() != "pycubrid":
        pytest.skip(
            "pycubrid typed collection binding; CUBRIDdb is covered by TestCubriddbCollectionBinds"
        )
    eng = create_engine(_decoding(url))
    yield eng
    eng.dispose()


@pytest.fixture
def core_table(engine: Engine) -> Iterator[Table]:
    _metadata.drop_all(engine)
    _metadata.create_all(engine)
    yield _core
    _metadata.drop_all(engine)


@pytest.fixture
def orm_table(engine: Engine) -> Iterator[None]:
    _Base.metadata.drop_all(engine)
    _Base.metadata.create_all(engine)
    yield
    _Base.metadata.drop_all(engine)


class TestCoreRoundTrip:
    @pytest.mark.parametrize("case", list(_ROWS))
    def test_execute(
        self, request: pytest.FixtureRequest, engine: Engine, core_table: Table, case: str
    ) -> None:
        _xfail_without_typed_collections(request)
        bound, read = _ROWS[case]
        with engine.begin() as conn:
            conn.execute(core_table.insert(), _insert_params(1, bound))
        with engine.connect() as conn:
            row = conn.execute(select(core_table)).one()
        assert _normalized(row) == _expected(read)

    def test_null_collections(self, engine: Engine, core_table: Table) -> None:
        # Binds no collection, so this passes on released pycubrid too.
        with engine.begin() as conn:
            conn.execute(core_table.insert(), _insert_params(1, {}))
        with engine.connect() as conn:
            row = conn.execute(select(core_table)).one()
        assert _normalized(row) == dict.fromkeys(_COLUMNS)

    def test_executemany(
        self, request: pytest.FixtureRequest, engine: Engine, core_table: Table
    ) -> None:
        _xfail_without_typed_collections(request)
        params = [_insert_params(i, bound) for i, (bound, _) in enumerate(_ROWS.values())]
        params.append(_insert_params(len(params), {}))
        with engine.begin() as conn:
            conn.execute(core_table.insert(), params)
        with engine.connect() as conn:
            rows = conn.execute(select(core_table).order_by(core_table.c.id)).all()
        expected = [_expected(read) for _, read in _ROWS.values()] + [dict.fromkeys(_COLUMNS)]
        assert [_normalized(row) for row in rows] == expected

    def test_where_predicates(
        self, request: pytest.FixtureRequest, engine: Engine, core_table: Table
    ) -> None:
        _xfail_without_typed_collections(request)
        with engine.begin() as conn:
            conn.execute(
                core_table.insert(),
                [
                    _insert_params(1, {"s": [1, 2], "sq": [3, 1, 2]}),
                    _insert_params(2, {"s": [7], "sq": [1, 2, 3]}),
                ],
            )
        with engine.connect() as conn:
            # SEQUENCE equality is order-sensitive.
            by_sequence = conn.execute(
                select(core_table.c.id).where(core_table.c.sq == [3, 1, 2])
            ).all()
            # The bound value takes the column's type, so it is a SET literal too.
            subset = conn.execute(
                select(core_table.c.id).where(core_table.c.s.op("SUBSETEQ")([1, 2, 5]))
            ).all()
        assert by_sequence == [(1,)]
        assert subset == [(1,)]

    def test_update(
        self, request: pytest.FixtureRequest, engine: Engine, core_table: Table
    ) -> None:
        _xfail_without_typed_collections(request)
        with engine.begin() as conn:
            conn.execute(core_table.insert(), _insert_params(1, {"sq": [1, 2]}))
            conn.execute(core_table.update().values(sq=[2, 2, 1], ms=["q", "q"]))
        with engine.connect() as conn:
            row = conn.execute(select(core_table.c.sq, core_table.c.ms)).one()
        assert (row.sq, row.ms) == ([2, 2, 1], ["q", "q"])


class TestOrmRoundTrip:
    def test_add_update_and_clear(
        self, request: pytest.FixtureRequest, engine: Engine, orm_table: None
    ) -> None:
        _xfail_without_typed_collections(request)
        with Session(engine) as session:
            session.add_all(
                [
                    _Tagged(id=1, tags={"b", "a"}, scores=[2, 2, 1], history=[5, 3, 5]),
                    _Tagged(id=2, tags=set(), scores=[], history=[]),
                    _Tagged(id=3),
                ]
            )
            session.commit()

        with Session(engine) as session:
            rows = session.scalars(select(_Tagged).order_by(_Tagged.id)).all()
            got = [(t.tags, sorted(t.scores or []), t.history) for t in rows]
            assert got == [
                (frozenset({"a", "b"}), [1, 2, 2], [5, 3, 5]),
                (frozenset(), [], []),
                (None, [], None),
            ]
            assert rows[2].scores is None
            # Collection values are replaced, not mutated in place: SQLAlchemy
            # does not track in-place changes to a list or set attribute.
            rows[0].history = [*rows[0].history, 1]
            rows[1].tags = None
            session.commit()

        with Session(engine) as session:
            first = session.get(_Tagged, 1)
            second = session.get(_Tagged, 2)
            assert first is not None and second is not None
            assert first.history == [5, 3, 5, 1]
            assert second.tags is None


class TestCubriddbCollectionBinds:
    """What CUBRIDdb does with the same plain values (no dialect processing).

    CUBRIDdb binds a ``list``/``tuple``/``set`` itself, always as a CUBRID SET
    host variable, so a MULTISET loses its duplicates and a SEQUENCE its order
    (CUBRIDdb 11.3.0.51, CUBRID 10.2 and 11.4). The dialect does not change
    this; docs/DRIVER_COMPAT.md documents it.
    """

    @pytest.fixture
    def cubriddb_table(self) -> Iterator[tuple[Engine, Table]]:
        url = _sync_url()
        if url.get_driver_name() != "cubrid":
            pytest.skip("CUBRIDdb behavior; runs when CUBRID_TEST_URL selects cubrid://")
        eng = create_engine(url)
        _metadata.drop_all(eng)
        _metadata.create_all(eng)
        yield eng, _core
        _metadata.drop_all(eng)
        eng.dispose()

    def test_plain_values_bind_as_set(self, cubriddb_table: tuple[Engine, Table]) -> None:
        eng, table = cubriddb_table
        with eng.begin() as conn:
            conn.execute(
                table.insert(),
                _insert_params(1, {"s": [3, 1, 1], "ms": ["b", "a", "b"], "sq": [3, 1, 2, 1]}),
            )
            conn.execute(table.insert(), _insert_params(2, {"s": [], "ms": [], "sq": []}))
        with eng.connect() as conn:
            rows = conn.execute(select(table).order_by(table.c.id)).all()
        # Elements come back as strings, SET as a mutable set.
        assert (rows[0].s, rows[0].ms, rows[0].sq) == ({"1", "3"}, ["a", "b"], ["1", "2", "3"])
        assert (rows[1].s, rows[1].ms, rows[1].sq) == (set(), [], [])


@pytest_asyncio.fixture
async def async_engine() -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(_async_url())
    async with eng.begin() as conn:
        await conn.run_sync(_metadata.drop_all)
        await conn.run_sync(_metadata.create_all)
        await conn.run_sync(_Base.metadata.drop_all)
        await conn.run_sync(_Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(_metadata.drop_all)
        await conn.run_sync(_Base.metadata.drop_all)
    await eng.dispose()


@pytest.mark.asyncio
class TestAsyncRoundTrip:
    async def test_core_executemany(
        self, request: pytest.FixtureRequest, async_engine: AsyncEngine
    ) -> None:
        _xfail_without_typed_collections(request)
        params = [_insert_params(i, bound) for i, (bound, _) in enumerate(_ROWS.values())]
        params.append(_insert_params(len(params), {}))
        async with async_engine.begin() as conn:
            await conn.execute(_core.insert(), params[0])
            await conn.execute(_core.insert(), params[1:])
        async with async_engine.connect() as conn:
            rows = (await conn.execute(select(_core).order_by(_core.c.id))).all()
        expected = [_expected(read) for _, read in _ROWS.values()] + [dict.fromkeys(_COLUMNS)]
        assert [_normalized(row) for row in rows] == expected

    async def test_core_null_collections(self, async_engine: AsyncEngine) -> None:
        async with async_engine.begin() as conn:
            await conn.execute(_core.insert(), _insert_params(1, {}))
        async with async_engine.connect() as conn:
            row = (await conn.execute(select(_core))).one()
        assert _normalized(row) == dict.fromkeys(_COLUMNS)

    async def test_orm(self, request: pytest.FixtureRequest, async_engine: AsyncEngine) -> None:
        _xfail_without_typed_collections(request)
        async with AsyncSession(async_engine) as session:
            session.add_all(
                [
                    _Tagged(id=1, tags=["a", "a"], scores=(4, 4), history=[2, 1, 2]),
                    _Tagged(id=2, tags=frozenset(), scores=[], history=()),
                ]
            )
            await session.commit()
        async with AsyncSession(async_engine) as session:
            rows = (await session.scalars(select(_Tagged).order_by(_Tagged.id))).all()
            assert [(t.tags, t.scores, t.history) for t in rows] == [
                (frozenset({"a"}), [4, 4], [2, 1, 2]),
                (frozenset(), [], []),
            ]
