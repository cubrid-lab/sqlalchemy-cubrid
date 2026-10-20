"""GROUP_CONCAT forms run on a live CUBRID (#990, #984).

CUBRID's ``GROUP_CONCAT([DISTINCT] expr [ORDER BY ...] [SEPARATOR '...'])``
rejects its modifiers inside an extra pair of parentheses (-493), so the
dialect renders only the argument-list parentheses. A boolean argument keeps
the grouping every function argument gets (#970), once. Groups without an
ORDER BY are compared as sorted lists because their order is unspecified.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
import sqlalchemy as sa
from sqlalchemy import Column, Integer, MetaData, String, Table

pytestmark = pytest.mark.integration

_DEFAULT_SYNC_URL = "cubrid://dba@localhost:33000/testdb"
_metadata = MetaData()
_rows = Table(
    f"group_concat_{uuid.uuid4().hex[:8]}",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("g", Integer),
    Column("a", Integer),
    Column("b", Integer),
    Column("s", String(10)),
)


def _sync_url() -> str:
    return os.environ.get("CUBRID_TEST_URL", _DEFAULT_SYNC_URL)


@pytest.fixture(scope="module")
def engine() -> Iterator[sa.Engine]:
    eng = sa.create_engine(_sync_url())
    _metadata.create_all(eng)
    with eng.begin() as conn:
        conn.execute(
            _rows.insert(),
            [
                {"id": 1, "g": 1, "a": 1, "b": 2, "s": "x"},
                {"id": 2, "g": 1, "a": 1, "b": 0, "s": "y"},
                {"id": 3, "g": 1, "a": None, "b": 2, "s": None},
                {"id": 4, "g": 2, "a": 1, "b": None, "s": "x"},
                {"id": 5, "g": 2, "a": 0, "b": 0, "s": "x"},
                {"id": 6, "g": 2, "a": None, "b": None, "s": "z"},
                {"id": 7, "g": 3, "a": None, "b": None, "s": None},
            ],
        )
    try:
        yield eng
    finally:
        _metadata.drop_all(eng)
        eng.dispose()


def _by_group(engine: sa.Engine, concat: sa.ColumnElement[str]) -> dict[int, str | None]:
    stmt = sa.select(_rows.c.g, concat).group_by(_rows.c.g).order_by(_rows.c.g)
    with engine.connect() as conn:
        return {g: value for g, value in conn.execute(stmt)}


def _sorted(values: dict[int, str | None]) -> dict[int, list[str] | None]:
    return {g: None if v is None else sorted(v.split(",")) for g, v in values.items()}


def test_group_concat_column(engine: sa.Engine) -> None:
    result = _by_group(engine, sa.func.group_concat(_rows.c.s))
    assert _sorted(result) == {1: ["x", "y"], 2: ["x", "x", "z"], 3: None}


def test_group_concat_distinct(engine: sa.Engine) -> None:
    result = _by_group(engine, sa.func.group_concat(_rows.c.s.distinct()))
    assert _sorted(result) == {1: ["x", "y"], 2: ["x", "z"], 3: None}


def test_group_concat_order_by_separator(engine: sa.Engine) -> None:
    modifiers = sa.literal_column("s ORDER BY s DESC SEPARATOR ';'")
    result = _by_group(engine, sa.func.group_concat(modifiers))
    assert result == {1: "y;x", 2: "z;x;x", 3: None}


def test_group_concat_distinct_order_by_separator(engine: sa.Engine) -> None:
    modifiers = sa.literal_column("DISTINCT s ORDER BY s DESC SEPARATOR ';'")
    result = _by_group(engine, sa.func.group_concat(modifiers))
    assert result == {1: "y;x", 2: "z;x", 3: None}


@pytest.mark.parametrize(
    ("argument", "expected"),
    [
        (sa.and_(_rows.c.a == 1, _rows.c.b == 2), {1: ["0", "1"], 2: ["0"], 3: None}),
        (sa.or_(_rows.c.a == 1, _rows.c.b == 2), {1: ["1", "1", "1"], 2: ["0", "1"], 3: None}),
        (
            sa.exists().where(_rows.c.s == "z"),
            {1: ["1", "1", "1"], 2: ["1", "1", "1"], 3: ["1"]},
        ),
        (
            ~sa.exists().where(_rows.c.s == "z"),
            {1: ["0", "0", "0"], 2: ["0", "0", "0"], 3: ["0"]},
        ),
    ],
    ids=["and", "or", "exists", "not-exists"],
)
def test_group_concat_boolean_argument(engine: sa.Engine, argument, expected) -> None:
    concat = sa.func.group_concat(argument)
    assert _sorted(_by_group(engine, concat)) == expected
    stmt = sa.select(_rows.c.g).group_by(_rows.c.g).having(concat.is_not(None)).order_by(_rows.c.g)
    with engine.connect() as conn:
        groups = conn.execute(stmt).scalars().all()
    assert groups == [g for g, value in expected.items() if value is not None]


_aggregate_order_by = pytest.mark.skipif(
    not hasattr(sa.sql.functions.FunctionElement, "aggregate_order_by"),
    reason="aggregate_order_by() is SQLAlchemy 2.1+",
)
_both = sa.and_(_rows.c.a == 1, _rows.c.b == 2)


@_aggregate_order_by
@pytest.mark.parametrize(
    ("concat", "expected"),
    [
        (
            lambda: sa.func.group_concat(_rows.c.s).aggregate_order_by(_rows.c.s.desc()),
            {1: "y,x", 2: "z,x,x", 3: None},
        ),
        (
            lambda: sa.func.group_concat(_rows.c.s.distinct()).aggregate_order_by(_rows.c.s.desc()),
            {1: "y,x", 2: "z,x", 3: None},
        ),
        (
            lambda: sa.func.group_concat(_rows.c.b).aggregate_order_by(_rows.c.b),
            {1: "0,2,2", 2: "0", 3: None},
        ),
        (
            lambda: sa.func.group_concat(_both).aggregate_order_by(_both),
            {1: "0,1", 2: "0", 3: None},
        ),
    ],
    ids=["desc", "distinct", "integer", "boolean"],
)
def test_group_concat_aggregate_order_by(engine: sa.Engine, concat, expected) -> None:
    assert _by_group(engine, concat()) == expected
    stmt = sa.select(_rows.c.g).group_by(_rows.c.g).having(concat() == expected[1])
    with engine.connect() as conn:
        assert conn.execute(stmt).scalars().all() == [1]
