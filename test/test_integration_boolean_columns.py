"""EXISTS and AND/OR as SELECT-list and ORDER BY items run on a live CUBRID.

CUBRID rejects ``SELECT EXISTS (...)`` and ``SELECT a AND b``; the dialect
groups such a column (#966), also inside a type coercion, CAST or function
argument and as an ORDER BY item (#968). Sync, including the ORM
``query(...).exists()`` idiom, and async. CUBRID rejects a search condition as
a GROUP BY item even in parentheses; grouping by the column's label works.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy import Column, Integer, MetaData, String, Table, orm
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from scripts.integration_urls import async_url

pytestmark = pytest.mark.integration

_DEFAULT_SYNC_URL = "cubrid://dba@localhost:33000/testdb"
_metadata = MetaData()
_items = Table(
    f"bool_cols_{uuid.uuid4().hex[:8]}",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(10)),
)


class _Base(orm.DeclarativeBase):
    pass


class _Item(_Base):
    __table__ = _items


def _sync_url() -> str:
    return os.environ.get("CUBRID_TEST_URL", _DEFAULT_SYNC_URL)


@pytest.fixture(scope="module")
def engine() -> Iterator[sa.Engine]:
    eng = sa.create_engine(_sync_url())
    _metadata.create_all(eng)
    with eng.begin() as conn:
        conn.execute(_items.insert(), [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}])
    try:
        yield eng
    finally:
        _metadata.drop_all(eng)
        eng.dispose()


def _columns() -> list[tuple[str, sa.ColumnElement[bool], bool]]:
    found = sa.exists().where(_items.c.name == "a")
    missing = sa.exists().where(_items.c.name == "z")
    return [
        ("exists", found, True),
        ("missing", missing, False),
        ("not-exists", ~missing, True),
        ("and", sa.and_(_items.c.name == "a", _items.c.id == 1), True),
        ("or", sa.or_(_items.c.name == "z", _items.c.id == 2), False),
    ]


@pytest.mark.parametrize(
    ("label", "column", "expected"), _columns(), ids=[c[0] for c in _columns()]
)
def test_boolean_column(engine: sa.Engine, label: str, column, expected: bool) -> None:
    stmt = sa.select(column.label(label))
    if label in ("and", "or"):
        stmt = stmt.select_from(_items).where(_items.c.id == 1)
    with engine.connect() as conn:
        assert bool(conn.execute(stmt).scalar_one()) is expected


def test_orm_query_exists(engine: sa.Engine) -> None:
    with orm.Session(engine) as session:
        assert session.query(session.query(_Item).filter(_Item.name == "a").exists()).scalar()
        assert not session.scalar(sa.select(sa.select(_Item).where(_Item.name == "z").exists()))


class _Flag(sa.TypeDecorator[int]):
    impl = Integer
    cache_ok = True

    def column_expression(self, col):
        return sa.func.coalesce(col, 0)


def _wrapped() -> list[tuple[str, sa.ColumnElement[object], int]]:
    found = sa.exists().where(_items.c.name == "a")
    first = sa.and_(_items.c.name == "a", _items.c.id == 1)
    return [
        ("type-coerce-exists", sa.type_coerce(found, sa.Boolean), 1),
        ("cast-and", sa.cast(first, Integer), 1),
        ("cast-exists", sa.cast(found, Integer), 1),
        ("coalesce-exists", sa.func.coalesce(found, False), 1),
        ("coalesce-and", sa.func.coalesce(first, 0), 1),
        ("if-and", sa.func.if_(first, 1, 0), 1),
        ("type-decorator", sa.type_coerce(first, _Flag()), 1),
    ]


@pytest.mark.parametrize(
    ("label", "column", "expected"), _wrapped(), ids=[c[0] for c in _wrapped()]
)
def test_wrapped_boolean_column(engine: sa.Engine, label: str, column, expected: int) -> None:
    stmt = sa.select(column.label(label)).select_from(_items).where(_items.c.id == 1)
    with engine.connect() as conn:
        assert int(conn.execute(stmt).scalar_one()) == expected


def test_boolean_order_by(engine: sa.Engine) -> None:
    other = _items.alias("other")
    later = sa.exists().where(other.c.id > _items.c.id)
    first = sa.and_(_items.c.name == "a", _items.c.id == 1)
    with engine.connect() as conn:
        for order_by, ids in (
            (first, [2, 1]),
            (sa.or_(_items.c.name == "b", _items.c.id == 9).desc(), [2, 1]),
            (later, [2, 1]),
            (~later, [1, 2]),
            (sa.cast(first, Integer).label("unselected"), [2, 1]),
        ):
            stmt = sa.select(_items.c.id).order_by(order_by, _items.c.id)
            assert conn.execute(stmt).scalars().all() == ids


def test_boolean_group_by_label(engine: sa.Engine) -> None:
    first = sa.and_(_items.c.name == "a", _items.c.id == 1).label("first")
    stmt = sa.select(first, sa.func.count()).group_by("first").order_by("first")
    with engine.connect() as conn:
        assert [(bool(k), n) for k, n in conn.execute(stmt)] == [(False, 1), (True, 1)]
    with pytest.raises(sa.exc.ProgrammingError):
        with engine.connect() as conn:
            conn.execute(sa.select(sa.func.count()).select_from(_items).group_by(first.element))


@pytest_asyncio.fixture
async def aengine(engine: sa.Engine) -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(async_url(_sync_url(), os.environ.get("CUBRID_TEST_AURL")))
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest.mark.asyncio
async def test_async_exists_column(aengine: AsyncEngine) -> None:
    async with aengine.connect() as conn:
        stmt = sa.select(sa.exists().where(_items.c.name == "a"))
        assert bool((await conn.execute(stmt)).scalar_one()) is True
        stmt = sa.select(sa.cast(sa.exists().where(_items.c.name == "z"), Integer))
        assert (await conn.execute(stmt)).scalar_one() == 0
