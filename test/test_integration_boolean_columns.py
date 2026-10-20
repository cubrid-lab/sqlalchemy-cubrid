"""EXISTS and AND/OR as SELECT-list and ORDER BY items run on a live CUBRID.

CUBRID rejects ``SELECT EXISTS (...)`` and ``SELECT a AND b``; the dialect
groups such a column (#966), also inside a type coercion, CAST or function
argument and as an ORDER BY item (#968), and as a CAST or function argument
anywhere in a statement, an ORDER BY / PARTITION BY item of a window or
WITHIN GROUP (#970), and a CASE THEN or ELSE value (#982). Sync, including the
ORM ``query(...).exists()`` idiom, and async. CUBRID rejects a search condition
as a GROUP BY item even in parentheses; grouping by the column's label works.
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


def test_boolean_operand_outside_select_list(engine: sa.Engine) -> None:
    other = _items.alias("other")
    later = sa.exists().where(other.c.id > _items.c.id)
    first = sa.and_(_items.c.name == "a", _items.c.id == 1)
    same_b = sa.and_(other.c.id == _items.c.id, other.c.name == "b")
    last = sa.and_(sa.func.max(_items.c.name) == "b", sa.func.max(_items.c.id) > 1)
    with engine.connect() as conn:
        for stmt, ids in (
            (sa.select(_items.c.id).where(sa.func.coalesce(first, 0) == 1), [1]),
            (sa.select(_items.c.id).where(sa.cast(~later, Integer) == 1), [2]),
            (
                sa.select(_items.c.id).group_by(_items.c.id).having(sa.cast(last, Integer) == 1),
                [2],
            ),
            (
                sa.select(_items.c.id).select_from(
                    _items.join(other, sa.func.coalesce(same_b, 0) == 1)
                ),
                [2],
            ),
        ):
            assert conn.execute(stmt.order_by(_items.c.id)).scalars().all() == ids


def test_boolean_operand_in_update(engine: sa.Engine) -> None:
    first = sa.and_(_items.c.name == "a", _items.c.id == 1)
    flag = sa.cast(sa.cast(first, Integer), String(10))
    with engine.connect() as conn:
        with conn.begin() as trans:
            conn.execute(_items.update().values(name=flag).where(_items.c.id == 1))
            stmt = sa.select(_items.c.name).where(_items.c.id == 1)
            assert conn.execute(stmt).scalar_one() == "1"
            trans.rollback()


def test_boolean_window_items(engine: sa.Engine) -> None:
    other = _items.alias("other")
    later = sa.exists().where(other.c.id > _items.c.id)
    first = sa.and_(_items.c.name == "a", _items.c.id == 1)
    row_number = sa.func.row_number
    with engine.connect() as conn:
        for window, rows in (
            (row_number().over(order_by=later), [(1, 2), (2, 1)]),
            (row_number().over(order_by=(~later).desc()), [(1, 2), (2, 1)]),
            (row_number().over(partition_by=later, order_by=_items.c.id), [(1, 1), (2, 1)]),
            (sa.func.sum(_items.c.id).over(order_by=sa.func.coalesce(first, 0)), [(1, 3), (2, 2)]),
        ):
            stmt = sa.select(_items.c.id, window).order_by(_items.c.id)
            assert [tuple(map(int, row)) for row in conn.execute(stmt)] == rows
        for fraction, expected in ((0.0, False), (1.0, True)):
            within = sa.func.percentile_disc(fraction).within_group(later)
            stmt = sa.select(within).select_from(_items)
            assert bool(conn.execute(stmt).scalar_one()) is expected


def test_boolean_case_values(engine: sa.Engine) -> None:
    found = sa.exists().where(_items.c.name == "a")
    missing = sa.exists().where(_items.c.name == "z")
    first = sa.and_(_items.c.name == "a", _items.c.id == 1)
    false = sa.literal(False)
    with engine.connect() as conn:
        for case, rows in (
            (sa.case((_items.c.id > 0, first), else_=false), [(1, 1), (2, 0)]),
            (sa.case((_items.c.id < 0, false), else_=first), [(1, 1), (2, 0)]),
            (sa.case((_items.c.id > 0, found), else_=false), [(1, 1), (2, 1)]),
            (sa.case({1: first}, value=_items.c.id, else_=~missing), [(1, 1), (2, 1)]),
            (sa.case((first, sa.or_(_items.c.id == 2, missing)), else_=~found), [(1, 0), (2, 0)]),
        ):
            stmt = sa.select(_items.c.id, case).order_by(_items.c.id)
            assert [tuple(map(int, row)) for row in conn.execute(stmt)] == rows
        case = sa.case((_items.c.id > 1, first), else_=found)
        stmt = sa.select(_items.c.id).where(case == sa.literal(True)).order_by(_items.c.id)
        assert conn.execute(stmt).scalars().all() == [1]


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
        first = sa.and_(_items.c.name == "a", _items.c.id == 1)
        stmt = sa.select(_items.c.id).where(sa.func.coalesce(first, 0) == 1)
        assert (await conn.execute(stmt)).scalars().all() == [1]
