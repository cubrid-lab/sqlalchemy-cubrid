# test/test_driver_differential.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Driver differential testing (stabilization Phase 5).

The dialect supports several drivers (``cubrid+pycubrid://``, the C-extension
``cubrid://``/``CUBRIDdb``, and async ``cubrid+aiopycubrid://``). The same
SQLAlchemy operation should return the same result on every driver. A divergence
is either a driver limitation (documented, not a dialect bug — e.g. #386's
CUBRIDdb NUMERIC truncation on some builds) or a real dialect bug.

This module runs the same Core operations on both the pycubrid and CUBRIDdb
drivers and asserts they agree. It is ``integration``-marked and additionally
skips if either driver cannot connect (so a machine without the C-extension
built still runs the pycubrid-only suite).
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
    create_engine,
    select,
    text,
)

pytestmark = pytest.mark.integration


def _base_url() -> str:
    url = os.environ.get("CUBRID_TEST_URL")
    if not url:
        pytest.skip("CUBRID_TEST_URL not set")
    return url


def _pycubrid_url() -> str:
    url = _base_url()
    # Normalize any cubrid[+driver]:// to the pycubrid driver.
    tail = url.split("://", 1)[1]
    return f"cubrid+pycubrid://{tail}"


def _c_driver_url() -> str:
    tail = _base_url().split("://", 1)[1]
    return f"cubrid://{tail}"


def _make_engine(url: str) -> Any:
    try:
        eng = create_engine(url)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return eng
    except Exception:  # driver unavailable / not built
        return None


@pytest.fixture(scope="module")
def both_engines() -> Any:
    pyc = _make_engine(_pycubrid_url())
    cext = _make_engine(_c_driver_url())
    if pyc is None or cext is None:
        pytest.skip("both pycubrid and CUBRIDdb drivers are required")
    yield pyc, cext
    pyc.dispose()
    cext.dispose()


def _table(name: str) -> Table:
    return Table(
        name,
        MetaData(),
        Column("id", Integer, primary_key=True, autoincrement=False),
        Column("n", Numeric(10, 4)),
        Column("s", String(50)),
        Column("flag", Boolean),
    )


_ROWS = [
    {"id": 1, "n": Decimal("15.7563"), "s": "alpha", "flag": True},
    {"id": 2, "n": Decimal("-40.0200"), "s": "O'Brien", "flag": False},
    {"id": 3, "n": Decimal("0.0000"), "s": "\u4e2d\u6587", "flag": True},
]


def _seed(engine: Any, tbl: Table) -> None:
    tbl.drop(engine, checkfirst=True)
    tbl.create(engine)
    with engine.begin() as conn:
        conn.execute(tbl.insert(), _ROWS)


def test_select_roundtrip_agrees(both_engines: Any) -> None:
    """SELECT of typed columns returns identical values on both drivers."""
    pyc, cext = both_engines
    t_py = _table("drvdiff_sel")
    t_c = _table("drvdiff_sel")
    _seed(pyc, t_py)

    def read(engine: Any, tbl: Table) -> list[tuple[Any, ...]]:
        with engine.connect() as conn:
            return sorted(
                (r.id, r.n, r.s, r.flag)
                for r in conn.execute(select(tbl.c.id, tbl.c.n, tbl.c.s, tbl.c.flag))
            )

    py_rows = read(pyc, t_py)
    c_rows = read(cext, t_c)
    t_py.drop(pyc, checkfirst=True)
    assert py_rows == c_rows, f"pycubrid {py_rows} != CUBRIDdb {c_rows}"


def test_update_delete_rowcount_agrees(both_engines: Any) -> None:
    """UPDATE/DELETE rowcount is the same on both drivers."""
    pyc, cext = both_engines

    def run(engine: Any) -> tuple[int, int]:
        tbl = _table("drvdiff_rc")
        _seed(engine, tbl)
        with engine.begin() as conn:
            upd = conn.execute(tbl.update().where(tbl.c.id > 1).values(s="x")).rowcount
            dele = conn.execute(tbl.delete().where(tbl.c.id == 1)).rowcount
        tbl.drop(engine, checkfirst=True)
        return upd, dele

    assert run(pyc) == run(cext)


def test_aggregate_agrees(both_engines: Any) -> None:
    """COUNT/SUM/MAX over the same data agree across drivers."""
    from sqlalchemy import func

    pyc, cext = both_engines

    def run(engine: Any) -> tuple[Any, ...]:
        tbl = _table("drvdiff_agg")
        _seed(engine, tbl)
        with engine.connect() as conn:
            row = conn.execute(select(func.count(tbl.c.id), func.max(tbl.c.id))).first()
        tbl.drop(engine, checkfirst=True)
        return tuple(row)

    assert run(pyc) == run(cext)


def test_null_handling_agrees(both_engines: Any) -> None:
    """NULL round-trips identically on both drivers."""
    pyc, cext = both_engines

    def run(engine: Any) -> list[Any]:
        tbl = _table("drvdiff_null")
        tbl.drop(engine, checkfirst=True)
        tbl.create(engine)
        with engine.begin() as conn:
            conn.execute(tbl.insert().values(id=1, n=None, s=None, flag=None))
        with engine.connect() as conn:
            row = conn.execute(select(tbl.c.n, tbl.c.s, tbl.c.flag)).first()
        tbl.drop(engine, checkfirst=True)
        return list(row)

    assert run(pyc) == run(cext) == [None, None, None]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
