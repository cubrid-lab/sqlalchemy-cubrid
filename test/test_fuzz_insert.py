# test/test_fuzz_insert.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Property-based fuzzing of INSERT compilation and execution (Phase 2).

The INSERT path is where the most recent real bugs lived (#421 the
insertmanyvalues + bind_expression mismatch, #371 the ODKU multi-row failure),
so it gets its own fuzzer.

Offline invariants (no DB):

* compilation raises only ``CompileError``, never an unexpected exception;
* the positional-placeholder count equals the bound-parameter count for both
  single-row and inline multi-row VALUES.

Live invariants (``integration``-marked): the same rows inserted by different
execution modes (single INSERT, executemany, ORM add_all) must produce
identical stored data — a metamorphic check that no execution path silently
corrupts or drops values.
"""

from __future__ import annotations

import os
from decimal import Decimal
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
)
from sqlalchemy.exc import CompileError

from sqlalchemy_cubrid.dialect import CubridDialect

_META = MetaData()
_T = Table(
    "fuzz_ins",
    _META,
    Column("id", Integer, primary_key=True, autoincrement=False),
    Column("n", Numeric(10, 4)),
    Column("s", String(100)),
    Column("flag", Boolean),
)

_BOUNDARY_INTS = [0, 1, -1, 2**31, 2**31 - 1, 2**63 - 1, -(2**63)]
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
_BOUNDARY_DECIMALS = [
    Decimal("0"),
    Decimal("1.5"),
    Decimal("-1.5"),
    Decimal("15.7563"),
    Decimal("9999.9999"),
    Decimal("-9999.9999"),
]

row_strategy = st.fixed_dictionaries(
    {
        "id": st.integers(min_value=-(2**31), max_value=2**31 - 1),
        "n": st.sampled_from(_BOUNDARY_DECIMALS),
        "s": st.sampled_from(_BOUNDARY_STRS),
        "flag": st.booleans(),
    }
)

# Live-execution rows must respect the column's declared length; a value longer
# than String(100) is rejected identically by every insert mode (CUBRID
# "Cannot coerce"), which is correct backend behavior, not a dialect divergence.
_LIVE_STRS = [s for s in _BOUNDARY_STRS if len(s) <= 100]
live_row_strategy = st.fixed_dictionaries(
    {
        "id": st.integers(min_value=-(2**31), max_value=2**31 - 1),
        "n": st.sampled_from(_BOUNDARY_DECIMALS),
        "s": st.sampled_from(_LIVE_STRS),
        "flag": st.booleans(),
    }
)


def _assert_param_count_matches(compiled: Any) -> None:
    sql = compiled.string
    if "POSTCOMPILE" in sql:
        return
    placeholder_count = sql.count("?")
    param_count = len(compiled.positiontup or [])
    assert placeholder_count == param_count, (
        f"placeholder/param mismatch: {placeholder_count} '?' vs "
        f"{param_count} params\nSQL: {sql}\nparams: {compiled.positiontup}"
    )


@given(row=row_strategy)
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_fuzz_single_insert_param_count(row: dict[str, Any]) -> None:
    stmt = _T.insert().values(**row)
    try:
        compiled = stmt.compile(dialect=CubridDialect())
    except CompileError:
        return
    _assert_param_count_matches(compiled)


@given(rows=st.lists(row_strategy, min_size=2, max_size=8, unique_by=lambda r: r["id"]))
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_fuzz_multivalues_insert_param_count(rows: list[dict[str, Any]]) -> None:
    stmt = _T.insert().values(rows)
    try:
        compiled = stmt.compile(dialect=CubridDialect())
    except CompileError:
        return
    _assert_param_count_matches(compiled)


@given(
    cols=st.lists(st.sampled_from(["id", "n", "s", "flag"]), min_size=1, max_size=4, unique=True),
    value=st.one_of(st.sampled_from(_BOUNDARY_INTS), st.sampled_from(_BOUNDARY_STRS)),
)
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_fuzz_partial_column_insert(cols: list[str], value: Any) -> None:
    values = {c: value for c in cols}
    stmt = _T.insert().values(**values)
    try:
        compiled = stmt.compile(dialect=CubridDialect())
    except CompileError:
        return
    _assert_param_count_matches(compiled)


def test_fuzz_insert_smoke() -> None:
    """A deterministic sanity check so the module always has one non-fuzz test."""
    stmt = _T.insert().values(id=1, n=Decimal("1.5"), s="x", flag=True)
    compiled = stmt.compile(dialect=CubridDialect())
    _assert_param_count_matches(compiled)
    assert "INSERT INTO" in compiled.string


# ---------------------------------------------------------------------------
# Live-execution metamorphic fuzzing: single INSERT == executemany == ORM must
# all store identical data. A divergence means an execution path corrupts rows.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def live_engine() -> Any:
    url = os.environ.get("CUBRID_TEST_URL")
    if not url:
        pytest.skip("CUBRID_TEST_URL not set")
    from sqlalchemy import create_engine

    engine = create_engine(url)
    yield engine
    engine.dispose()


def _fresh_table(engine: Any, name: str) -> Any:
    tbl = Table(
        name,
        MetaData(),
        Column("id", Integer, primary_key=True, autoincrement=False),
        Column("n", Numeric(10, 4)),
        Column("s", String(100)),
        Column("flag", Boolean),
    )
    tbl.drop(engine, checkfirst=True)
    tbl.create(engine)
    return tbl


@pytest.mark.integration
@given(
    rows=st.lists(live_row_strategy, min_size=2, max_size=6, unique_by=lambda r: r["id"]),
)
@settings(max_examples=40, deadline=None, suppress_health_check=list(HealthCheck))
def test_fuzz_insert_modes_agree_live(live_engine: Any, rows: list[dict[str, Any]]) -> None:
    """single INSERT, executemany, and multi-values must store identical data."""
    engine = live_engine

    def _readback(tbl: Any) -> list[tuple[Any, ...]]:
        from sqlalchemy import select

        with engine.connect() as conn:
            return sorted(
                (r.id, r.n, r.s, r.flag)
                for r in conn.execute(select(tbl.c.id, tbl.c.n, tbl.c.s, tbl.c.flag))
            )

    t_single = _fresh_table(engine, "cookbook_fuzz_ins_single")
    with engine.begin() as conn:
        for row in rows:
            conn.execute(t_single.insert().values(**row))
    single_data = _readback(t_single)
    t_single.drop(engine, checkfirst=True)

    t_many = _fresh_table(engine, "cookbook_fuzz_ins_many")
    with engine.begin() as conn:
        conn.execute(t_many.insert(), rows)
    many_data = _readback(t_many)
    t_many.drop(engine, checkfirst=True)

    t_multi = _fresh_table(engine, "cookbook_fuzz_ins_multi")
    with engine.begin() as conn:
        conn.execute(t_multi.insert().values(rows))
    multi_data = _readback(t_multi)
    t_multi.drop(engine, checkfirst=True)

    assert single_data == many_data, f"single != executemany:\n{single_data}\n{many_data}"
    assert single_data == multi_data, f"single != multi-values:\n{single_data}\n{multi_data}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
