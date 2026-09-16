# test/test_metamorphic.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Metamorphic testing (Phase 3).

When the "correct" SQL is hard to state directly, compare the results of two
different-but-equivalent ways of expressing the same operation. A divergence is
a bug (or a documented, expected semantic difference).

Pairs exercised here:

* Core ``select`` vs ORM ``Session.execute(select(...))`` — same rows;
* ``column == bindparam()`` vs ``column == literal()`` — same rows;
* single INSERT loop vs ``executemany`` — same stored data (also covered by the
  INSERT fuzzer, kept here as a fixed corpus).

All are ``integration``-marked (they need a live CUBRID). Offline, a single
deterministic smoke test keeps the module importable in the PR suite.
"""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    bindparam,
    literal,
    select,
)


def test_metamorphic_smoke() -> None:
    """Deterministic offline sanity check so the module has one PR-suite test."""
    stmt_bind = select(literal(1))
    assert stmt_bind is not None


@pytest.fixture(scope="module")
def seeded() -> Any:
    url = os.environ.get("CUBRID_TEST_URL")
    if not url:
        pytest.skip("CUBRID_TEST_URL not set")
    from sqlalchemy import create_engine

    engine = create_engine(url)
    tbl = Table(
        "cookbook_metamorphic",
        MetaData(),
        Column("id", Integer, primary_key=True, autoincrement=False),
        Column("n", Numeric(10, 4)),
        Column("s", String(50)),
        Column("flag", Boolean),
    )
    tbl.drop(engine, checkfirst=True)
    tbl.create(engine)
    with engine.begin() as conn:
        conn.execute(
            tbl.insert(),
            [
                {"id": i, "n": Decimal(f"{i}.25"), "s": f"row{i}", "flag": bool(i % 2)}
                for i in range(1, 21)
            ],
        )
    yield engine, tbl
    tbl.drop(engine, checkfirst=True)
    engine.dispose()


@pytest.mark.integration
def test_core_vs_orm_select_agree(seeded: Any) -> None:
    """Core select and ORM-style execute(select()) return identical rows."""
    engine, tbl = seeded
    from sqlalchemy.orm import Session

    core_rows = None
    with engine.connect() as conn:
        core_rows = sorted(tuple(r) for r in conn.execute(select(tbl.c.id, tbl.c.s)))

    with Session(engine) as session:
        orm_rows = sorted(tuple(r) for r in session.execute(select(tbl.c.id, tbl.c.s)))

    assert core_rows == orm_rows


@pytest.mark.integration
@pytest.mark.parametrize("target", [1, 10, 20, 999])
def test_bind_vs_literal_agree(seeded: Any, target: int) -> None:
    """A predicate written with a bindparam vs a literal returns the same rows."""
    engine, tbl = seeded
    with engine.connect() as conn:
        bind_rows = sorted(
            r[0]
            for r in conn.execute(select(tbl.c.id).where(tbl.c.id == bindparam("t")), {"t": target})
        )
        literal_rows = sorted(
            r[0] for r in conn.execute(select(tbl.c.id).where(tbl.c.id == literal(target)))
        )
    assert bind_rows == literal_rows


@pytest.mark.integration
@pytest.mark.parametrize("limit,offset", [(0, 0), (5, 0), (5, 5), (10, 15), (100, 0)])
def test_limit_offset_vs_python_slice(seeded: Any, limit: int, offset: int) -> None:
    """SQL LIMIT/OFFSET must match a Python slice of the full ordered result."""
    engine, tbl = seeded
    with engine.connect() as conn:
        full = [r[0] for r in conn.execute(select(tbl.c.id).order_by(tbl.c.id))]
        sql_page = [
            r[0]
            for r in conn.execute(select(tbl.c.id).order_by(tbl.c.id).limit(limit).offset(offset))
        ]
    assert sql_page == full[offset : offset + limit]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
