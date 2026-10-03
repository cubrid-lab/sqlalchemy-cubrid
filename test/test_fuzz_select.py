# test/test_fuzz_select.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Property-based fuzzing of SELECT compilation (stabilization Phase 1).

Hypothesis generates SELECT statements the hand-written suite never enumerated
and asserts dialect-level invariants that must hold for *every* compilable
statement:

* compilation raises only ``CompileError`` (a declared "unsupported" signal),
  never an unexpected exception (``AttributeError``, ``KeyError``, ``TypeError``,
  ``IndexError``, ``RecursionError``, ...);
* the number of positional placeholders in the SQL equals the number of bound
  parameters (a placeholder/param mismatch is the class of bug behind #421 and
  the ODKU multi-row failure #371).

These are offline (compile-only) checks and run in the normal PR suite. Live
execution fuzzing lives in the integration-marked tests.
"""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    and_,
    distinct,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.exc import CompileError

from sqlalchemy_cubrid.dialect import CubridDialect

# ---------------------------------------------------------------------------
# Fixture table with a spread of column types and identifier shapes.
# ---------------------------------------------------------------------------

_META = MetaData()
_T = Table(
    "fuzz_t",
    _META,
    Column("id", Integer, primary_key=True),
    Column("n", Numeric(10, 4)),
    Column("s", String(50)),
    Column("flag", Boolean),
    # A reserved word and a quoted-needing name exercise the identifier preparer.
    Column("value", Integer),
    Column("Mixed Case", Integer),
)
_COLUMNS = list(_T.c)

# Boundary values that have historically exposed dialect bugs.
_BOUNDARY_INTS = [
    0,
    1,
    -1,
    2**31,
    2**31 - 1,
    2**63 - 1,
    -(2**63),
]
_BOUNDARY_STRS = [
    "",
    "a",
    "O'Brien",
    "back\\slash",
    "percent%",
    "under_score",
    "\u00e9\u00e0\u4e2d\u6587",
    "select",
    "x" * 300,
]


def _compile(stmt: Any) -> Any:
    return stmt.compile(dialect=CubridDialect())


def _compile_literal(stmt: Any) -> Any:
    return stmt.compile(dialect=CubridDialect(), compile_kwargs={"literal_binds": True})


def _assert_param_count_matches(compiled: Any) -> None:
    """Positional placeholders must equal the number of bound parameters.

    Skipped for statements SQLAlchemy expands at execution time (``IN``
    POSTCOMPILE binds render one token that becomes N placeholders later), where
    the pre-execution ``?`` count legitimately differs from ``positiontup``.
    """
    sql = compiled.string
    if "POSTCOMPILE" in sql:
        return
    placeholder_count = sql.count("?")
    param_count = len(compiled.positiontup or [])
    assert placeholder_count == param_count, (
        f"placeholder/param mismatch: {placeholder_count} '?' vs "
        f"{param_count} params\nSQL: {sql}\nparams: {compiled.positiontup}"
    )


columns_strategy = st.lists(st.sampled_from(_COLUMNS), min_size=1, max_size=6)
int_values = st.sampled_from(_BOUNDARY_INTS)
str_values = st.sampled_from(_BOUNDARY_STRS)
scalar_values = st.one_of(int_values, str_values, st.none(), st.booleans())


@given(cols=columns_strategy, use_distinct=st.booleans())
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_fuzz_select_columns(cols: list[Any], use_distinct: bool) -> None:
    stmt = select(*cols)
    if use_distinct:
        stmt = stmt.distinct()
    try:
        compiled = _compile(stmt)
    except CompileError:
        return
    _assert_param_count_matches(compiled)


@given(
    col=st.sampled_from(_COLUMNS),
    value=scalar_values,
    op=st.sampled_from(["eq", "ne", "lt", "gt", "in_", "is_null"]),
)
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_fuzz_where_predicates(col: Any, value: Any, op: str) -> None:
    # SQLAlchemy itself (not the dialect) rejects ordering operators against
    # None/bool at construction time, so those generator combinations are
    # invalid input rather than a dialect bug — skip them.
    if op in ("lt", "gt") and (value is None or isinstance(value, bool)):
        return
    if op == "eq":
        pred = col == value
    elif op == "ne":
        pred = col != value
    elif op == "lt":
        pred = col < value
    elif op == "gt":
        pred = col > value
    elif op == "in_":
        pred = col.in_([value, value])
    else:
        pred = col.is_(None)
    stmt = select(_T.c.id).where(pred)
    try:
        compiled = _compile(stmt)
    except CompileError:
        return
    _assert_param_count_matches(compiled)


@given(
    values=st.lists(scalar_values, min_size=1, max_size=5),
    connective=st.sampled_from(["and", "or"]),
)
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_fuzz_boolean_connectives(values: list[Any], connective: str) -> None:
    preds = [_T.c.value == v for v in values]
    combined = and_(*preds) if connective == "and" else or_(*preds)
    stmt = select(_T.c.id).where(combined)
    try:
        compiled = _compile(stmt)
    except CompileError:
        return
    _assert_param_count_matches(compiled)


@given(
    limit=st.one_of(st.none(), int_values),
    offset=st.one_of(st.none(), int_values),
)
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_fuzz_limit_offset(limit: int | None, offset: int | None) -> None:
    stmt = select(_T.c.id)
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)
    try:
        compiled = _compile(stmt)
    except CompileError:
        return
    _assert_param_count_matches(compiled)


@given(
    order_cols=st.lists(st.sampled_from(_COLUMNS), max_size=4),
    group_cols=st.lists(st.sampled_from(_COLUMNS), max_size=4),
    descending=st.booleans(),
)
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_fuzz_order_group_by(
    order_cols: list[Any], group_cols: list[Any], descending: bool
) -> None:
    stmt = select(_T.c.id)
    for col in order_cols:
        stmt = stmt.order_by(col.desc() if descending else col.asc())
    if group_cols:
        stmt = select(*group_cols).group_by(*group_cols)
    try:
        compiled = _compile(stmt)
    except CompileError:
        return
    _assert_param_count_matches(compiled)


@given(
    inner_value=scalar_values,
    outer_value=scalar_values,
)
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_fuzz_subquery_and_bind(inner_value: Any, outer_value: Any) -> None:
    subq = select(_T.c.id).where(_T.c.value == inner_value).scalar_subquery()
    stmt = select(_T.c.id).where(or_(_T.c.id == subq, _T.c.value == outer_value))
    try:
        compiled = _compile(stmt)
    except CompileError:
        return
    _assert_param_count_matches(compiled)


@given(
    value=scalar_values,
    use_literal=st.booleans(),
    use_alias=st.booleans(),
)
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_fuzz_literal_alias_distinct(value: Any, use_literal: bool, use_alias: bool) -> None:
    tbl = _T.alias("a") if use_alias else _T
    rhs = literal(value) if use_literal else value
    stmt = select(distinct(tbl.c.value)).where(tbl.c.value == rhs)
    try:
        compiled = _compile(stmt)
    except CompileError:
        return
    _assert_param_count_matches(compiled)


@given(
    agg=st.sampled_from(["count", "sum", "max", "min", "avg"]),
    col=st.sampled_from(_COLUMNS),
    having_value=int_values,
)
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_fuzz_aggregate_having(agg: str, col: Any, having_value: int) -> None:
    aggregate = getattr(func, agg)(col)
    stmt = select(_T.c.value, aggregate).group_by(_T.c.value).having(aggregate > having_value)
    try:
        compiled = _compile(stmt)
    except CompileError:
        return
    _assert_param_count_matches(compiled)


def test_fuzz_select_smoke() -> None:
    """A deterministic sanity check so the module always has one non-fuzz test."""
    compiled = _compile(select(_T.c.id).where(_T.c.value == 1).limit(10).offset(5))
    _assert_param_count_matches(compiled)
    assert "LIMIT" in compiled.string


# ---------------------------------------------------------------------------
# Live-execution fuzzing: a compilable SELECT must also EXECUTE on real CUBRID.
# This is where compile-only invariants cannot reach — the pre-execution fuzz
# above proves the SQL is well-formed; this proves the server accepts it.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def live_engine() -> Any:
    import os

    url = os.environ.get("CUBRID_TEST_URL")
    if not url:
        pytest.skip("CUBRID_TEST_URL not set")
    from sqlalchemy import create_engine

    engine = create_engine(url)
    live_t = Table(
        "cookbook_fuzz_select",
        MetaData(),
        Column("id", Integer, primary_key=True, autoincrement=False),
        Column("n", Numeric(10, 4)),
        Column("s", String(50)),
        Column("flag", Boolean),
    )
    live_t.drop(engine, checkfirst=True)
    live_t.create(engine)
    from decimal import Decimal

    with engine.begin() as conn:
        conn.execute(
            live_t.insert(),
            [
                {"id": i, "n": Decimal(f"{i}.5"), "s": f"row{i}", "flag": bool(i % 2)}
                for i in range(1, 11)
            ],
        )
    yield engine, live_t
    live_t.drop(engine, checkfirst=True)
    engine.dispose()


@pytest.mark.integration
@given(
    limit=st.integers(min_value=0, max_value=20),
    offset=st.integers(min_value=0, max_value=20),
)
@settings(max_examples=60, deadline=None, suppress_health_check=list(HealthCheck))
def test_fuzz_limit_offset_live_cardinality(live_engine: Any, limit: int, offset: int) -> None:
    """#414-class invariant: LIMIT/OFFSET must return the exact expected rows."""
    engine, live_t = live_engine
    stmt = select(live_t.c.id).order_by(live_t.c.id).limit(limit).offset(offset)
    with engine.connect() as conn:
        ids = [row[0] for row in conn.execute(stmt)]
    all_ids = list(range(1, 11))
    expected = all_ids[offset : offset + limit]
    assert ids == expected, f"limit={limit} offset={offset}: {ids} != {expected}"


@pytest.mark.integration
@given(
    op=st.sampled_from(["eq", "ne", "lt", "gt", "in_"]),
    value=st.integers(min_value=-2, max_value=12),
)
@settings(max_examples=80, deadline=None, suppress_health_check=list(HealthCheck))
def test_fuzz_where_executes_live(live_engine: Any, op: str, value: int) -> None:
    """A compilable WHERE predicate must execute on live CUBRID without error."""
    engine, live_t = live_engine
    col = live_t.c.id
    if op == "eq":
        pred = col == value
    elif op == "ne":
        pred = col != value
    elif op == "lt":
        pred = col < value
    elif op == "gt":
        pred = col > value
    else:
        pred = col.in_([value, value + 1])
    stmt = select(live_t.c.id).where(pred)
    try:
        compiled = stmt.compile(dialect=engine.dialect)
    except CompileError:
        return
    with engine.connect() as conn:
        conn.execute(stmt).all()
    assert compiled is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
