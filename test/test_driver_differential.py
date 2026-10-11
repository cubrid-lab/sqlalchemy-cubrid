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
built still runs the pycubrid-only suite). The required CI comparison lane sets
``CUBRID_REQUIRE_DRIVER_DIFFERENTIAL=1``, which makes ``conftest.py`` fail the
session when no case in this module ran and passed (#486).
"""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy import (
    BigInteger,
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
from sqlalchemy.engine import make_url

from sqlalchemy_cubrid.dialect import CubridDialect

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


# ---------------------------------------------------------------------------
# DB-API contract areas that already behave correctly on the released drivers
# (#486, tracker #479). LOBs are handled separately in #485 (not touched here).
# IntegrityError classification (#480), results across commit/rollback (#481),
# cursor.description (#482) and collection round trips (#484) are at the end
# of this module.
# ---------------------------------------------------------------------------

_CJK = "中文한글日本語"
_UTF8 = "café ß \U0001f600"


def _scalar_table(name: str) -> Table:
    return Table(
        name,
        MetaData(),
        Column("id", Integer, primary_key=True, autoincrement=False),
        Column("big", BigInteger),
        Column("s", String(100)),
    )


_SCALAR_ROWS = [
    {"id": 1, "big": 2**40, "s": _CJK},
    {"id": 2, "big": -(2**31), "s": None},
    {"id": 3, "big": None, "s": _UTF8},
    {"id": 4, "big": 0, "s": ""},
]


def test_executemany_int_utf8_null_agrees(both_engines: Any) -> None:
    """Core executemany of int/BIGINT, CJK/4-byte UTF-8 and NULL agrees."""
    pyc, cext = both_engines

    def run(engine: Any) -> list[tuple[Any, ...]]:
        tbl = _scalar_table("drvdiff_em")
        tbl.drop(engine, checkfirst=True)
        tbl.create(engine)
        with engine.begin() as conn:
            conn.execute(tbl.insert(), _SCALAR_ROWS)
        with engine.connect() as conn:
            rows = [tuple(r) for r in conn.execute(select(tbl).order_by(tbl.c.id))]
        tbl.drop(engine, checkfirst=True)
        return rows

    expected = [(r["id"], r["big"], r["s"]) for r in _SCALAR_ROWS]
    assert run(pyc) == run(cext) == expected


def test_textual_executemany_agrees(both_engines: Any) -> None:
    """``text()`` executemany of int, CJK and interleaved NULL parameters agrees.

    CUBRIDdb 11.3.0.51 itself reuses the previous row's value for a ``None``
    parameter in ``executemany``; the ``cubrid://`` dialect runs executemany
    row by row to avoid that (#502), so NULL is compared here too.
    """
    pyc, cext = both_engines
    rows = [
        {"id": 1, "big": 2**40, "s": _CJK},
        {"id": 2, "big": None, "s": None},
        {"id": 3, "big": -(2**31), "s": _UTF8},
        {"id": 4, "big": None, "s": None},
        {"id": 5, "big": 0, "s": ""},
    ]

    def run(engine: Any) -> list[tuple[Any, ...]]:
        tbl = _scalar_table("drvdiff_tem")
        tbl.drop(engine, checkfirst=True)
        tbl.create(engine)
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO drvdiff_tem (id, big, s) VALUES (:id, :big, :s)"), rows)
        with engine.connect() as conn:
            result = [tuple(r) for r in conn.execute(select(tbl).order_by(tbl.c.id))]
        tbl.drop(engine, checkfirst=True)
        return result

    expected = [(r["id"], r["big"], r["s"]) for r in rows]
    assert run(pyc) == run(cext) == expected


def test_scalar_bind_agrees(both_engines: Any) -> None:
    """Scalar int, BIGINT, CJK string and NULL binds select the same rows."""
    pyc, cext = both_engines

    def run(engine: Any) -> list[Any]:
        tbl = _scalar_table("drvdiff_bind")
        tbl.drop(engine, checkfirst=True)
        tbl.create(engine)
        with engine.begin() as conn:
            conn.execute(tbl.insert(), _SCALAR_ROWS)
        with engine.connect() as conn:
            out = [
                conn.execute(text("SELECT s FROM drvdiff_bind WHERE id = :v"), {"v": 3}).all(),
                conn.execute(
                    text("SELECT id FROM drvdiff_bind WHERE big = :v"), {"v": 2**40}
                ).all(),
                conn.execute(text("SELECT id FROM drvdiff_bind WHERE s = :v"), {"v": _CJK}).all(),
                conn.execute(
                    text("SELECT COUNT(*) FROM drvdiff_bind WHERE :v IS NULL"), {"v": None}
                ).scalar(),
                conn.execute(select(tbl.c.id).where(tbl.c.big < -1)).all(),
            ]
        tbl.drop(engine, checkfirst=True)
        return out

    assert run(pyc) == run(cext) == [[(_UTF8,)], [(1,)], [(1,)], 4, [(2,)]]


def test_textual_column_names_agree(both_engines: Any) -> None:
    """Result keys of textual SQL (aliases, quoted, expressions) agree."""
    pyc, cext = both_engines
    sql = text(
        'SELECT id, id AS row_id, s AS "Mixed Case", big + 1 AS big_plus, 1 + 1, NULL '
        "FROM drvdiff_names ORDER BY id"
    )

    def run(engine: Any) -> list[str]:
        tbl = _scalar_table("drvdiff_names")
        tbl.drop(engine, checkfirst=True)
        tbl.create(engine)
        with engine.connect() as conn:
            keys = list(conn.execute(sql).keys())
        tbl.drop(engine, checkfirst=True)
        return keys

    expected = ["id", "row_id", "Mixed Case", "big_plus", "1+1", "null"]
    assert run(pyc) == run(cext) == expected


def test_commit_rollback_visibility_agrees(both_engines: Any) -> None:
    """Committed rows persist and rolled-back rows vanish on both drivers."""
    pyc, cext = both_engines

    def run(engine: Any) -> list[int]:
        tbl = _scalar_table("drvdiff_tx")
        tbl.drop(engine, checkfirst=True)
        tbl.create(engine)
        with engine.connect() as conn:
            conn.execute(tbl.insert().values(id=1))
            conn.commit()
            conn.execute(tbl.insert().values(id=2))
            conn.rollback()
        with engine.connect() as conn:
            ids = list(conn.execute(select(tbl.c.id).order_by(tbl.c.id)).scalars())
        tbl.drop(engine, checkfirst=True)
        return ids

    assert run(pyc) == run(cext) == [1]


# ---------------------------------------------------------------------------
# #481: results are never silently truncated across commit or rollback
# ---------------------------------------------------------------------------


def test_result_after_rollback_is_never_partial(both_engines: Any) -> None:
    """A result spanning several FETCHes is complete or raises after rollback.

    500 rows of 1000 bytes exceed pycubrid's 100-row FETCH batch and the
    broker's first response (~16 such rows). CUBRIDdb raises here; the fixed
    pycubrid raises ``InterfaceError``. Neither may return a partial result.
    """
    pyc, cext = both_engines
    rows = 500

    def run(engine: Any) -> str:
        tbl = Table(
            "drvdiff_rc",
            MetaData(),
            Column("id", Integer, primary_key=True, autoincrement=False),
            Column("payload", String(1000)),
        )
        tbl.drop(engine, checkfirst=True)
        tbl.create(engine)
        with engine.begin() as conn:
            conn.execute(tbl.insert(), [{"id": i, "payload": "x" * 1000} for i in range(rows)])
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1")).all()
                result = conn.execute(select(tbl.c.id, tbl.c.payload).order_by(tbl.c.id))
                if engine.dialect.driver == "pycubrid":
                    # The first response must not hold the whole result.
                    assert 0 < result.cursor._fetched_count < rows
                first = result.fetchone()
                # Checked before the rollback, so it holds even when the rest raises.
                assert first is not None and first.id == 0 and first.payload == "x" * 1000
                conn.rollback()
                try:
                    rest = result.fetchall()
                except sa.exc.DBAPIError:
                    return "raises"
        finally:
            tbl.drop(engine, checkfirst=True)
        # Everything returned, including the row fetchone() consumed, is an
        # in-order prefix with intact payloads.
        returned = [first, *rest]
        ids = [row.id for row in returned]
        assert ids == list(range(len(ids)))
        assert all(row.payload == "x" * 1000 for row in returned)
        return "complete" if len(ids) == rows else f"partial ({len(ids)} of {rows})"

    assert run(cext) == "raises"
    py_outcome = run(pyc)
    assert py_outcome in ("complete", "raises"), py_outcome


# ---------------------------------------------------------------------------
# #480: constraint violations surface as sqlalchemy.exc.IntegrityError
# ---------------------------------------------------------------------------

# Row 1 of drvdiff_ie exists and is referenced by row 1 of drvdiff_iec, so
# changing or truncating it violates the foreign key (#479,
# cubrid-lab/pycubrid#493). The TRUNCATE code depends on the server: CUBRID
# 11.2+ reports ER_TRUNCATE_PK_REFERRED (-1284), 10.2 and 11.0 report -924.
_CONSTRAINT_VIOLATIONS = {
    "not_null": ("INSERT INTO drvdiff_ie (id, parent_id, n) VALUES (2, NULL, NULL)", -631),
    "foreign_key": ("INSERT INTO drvdiff_ie (id, parent_id, n) VALUES (2, 999, 1)", -922),
    "unique_pk": ("INSERT INTO drvdiff_ie (id, parent_id, n) VALUES (1, NULL, 1)", -670),
    "restrict_delete": ("DELETE FROM drvdiff_ie WHERE id = 1", -924),
    "restrict_update": ("UPDATE drvdiff_ie SET id = 5 WHERE id = 1", -924),
    "restrict_truncate": ("TRUNCATE TABLE drvdiff_ie", -1284),
}
_PARENT_CHANGE_KINDS = {"restrict_delete", "restrict_update", "restrict_truncate"}


def _pycubrid_older_than(version: tuple[int, ...]) -> bool:
    import pycubrid

    installed = tuple(int(part) for part in pycubrid.__version__.split(".")[: len(version)])
    return installed < version


class _OldPycubridParentChangeClass(Exception):
    """Raised only for the known pycubrid < 1.9.0 class of a parent-change violation.

    pycubrid 1.8.x raises the base DatabaseError for -924/-1284
    (cubrid-lab/pycubrid#493). The xfail marker expects this exception alone, so
    any other failed assertion in the test still fails it.
    """


@pytest.mark.parametrize("kind", list(_CONSTRAINT_VIOLATIONS))
def test_constraint_violation_class_agrees(
    request: pytest.FixtureRequest, both_engines: Any, kind: str
) -> None:
    """Constraint violations raise IntegrityError on both drivers.

    The exception is CUBRIDdb on a -1284 TRUNCATE (CUBRID 11.2+): its error map
    predates that code, so it raises the base DatabaseError. Recorded here, not
    normalized by the dialect.
    """
    pyc, cext = both_engines
    sql, code = _CONSTRAINT_VIOLATIONS[kind]
    if kind in _PARENT_CHANGE_KINDS and _pycubrid_older_than((1, 9)):
        request.applymarker(
            pytest.mark.xfail(
                strict=True,
                raises=_OldPycubridParentChangeClass,
                reason="pycubrid < 1.9.0 raises DatabaseError for a referenced parent "
                "change (-924/-1284); IntegrityError since cubrid-lab/pycubrid#493",
            )
        )

    def run(engine: Any) -> tuple[str, Any]:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS drvdiff_iec"))
            conn.execute(text("DROP TABLE IF EXISTS drvdiff_ie"))
            conn.execute(
                text(
                    "CREATE TABLE drvdiff_ie (id INTEGER PRIMARY KEY, parent_id INTEGER, "
                    "n INTEGER NOT NULL, FOREIGN KEY (parent_id) REFERENCES drvdiff_ie(id))"
                )
            )
            conn.execute(
                text(
                    "CREATE TABLE drvdiff_iec (id INTEGER PRIMARY KEY, parent_id INTEGER, "
                    "FOREIGN KEY (parent_id) REFERENCES drvdiff_ie(id))"
                )
            )
            conn.execute(text("INSERT INTO drvdiff_ie (id, parent_id, n) VALUES (1, NULL, 1)"))
            conn.execute(text("INSERT INTO drvdiff_iec (id, parent_id) VALUES (1, 1)"))
        try:
            with engine.connect() as conn:
                raw = conn.connection.dbapi_connection
                with pytest.raises(sa.exc.DBAPIError) as excinfo:
                    conn.execute(text(sql))
                assert not excinfo.value.connection_invalidated
                conn.rollback()
                assert not conn.invalidated
                assert conn.connection.dbapi_connection is raw
                assert conn.execute(text("SELECT COUNT(*) FROM drvdiff_ie")).scalar() == 1
                assert conn.execute(text("SELECT COUNT(*) FROM drvdiff_iec")).scalar() == 1
        finally:
            with engine.begin() as conn:
                conn.execute(text("DROP TABLE IF EXISTS drvdiff_iec"))
                conn.execute(text("DROP TABLE IF EXISTS drvdiff_ie"))
        return type(excinfo.value).__name__, excinfo.value.orig

    c_class, c_orig = run(cext)
    if code == -1284 and cext.dialect.server_version_info[:2] < (11, 2):
        code = -924
    assert CubridDialect._extract_error_code(c_orig) == code
    if code == -1284:
        assert c_class == "DatabaseError"
        assert type(c_orig) is cext.dialect.loaded_dbapi.DatabaseError
    else:
        assert c_class == "IntegrityError"
        assert isinstance(c_orig, cext.dialect.loaded_dbapi.IntegrityError)
    py_class, py_orig = run(pyc)
    assert py_orig.code == code
    if (
        kind in _PARENT_CHANGE_KINDS
        and _pycubrid_older_than((1, 9))
        and py_class == "DatabaseError"
        and type(py_orig) is pyc.dialect.loaded_dbapi.DatabaseError
    ):
        raise _OldPycubridParentChangeClass(type(py_orig).__name__)
    assert py_class == "IntegrityError"
    assert isinstance(py_orig, pyc.dialect.loaded_dbapi.IntegrityError)


# ---------------------------------------------------------------------------
# #482: the cursor.description subset observable through SQLAlchemy
# ---------------------------------------------------------------------------


def test_scalar_description_agrees(both_engines: Any) -> None:
    """Textual-SQL names, scalar type codes and null_ok agree across drivers.

    Collection type codes intentionally differ (pycubrid SET/MULTISET/SEQUENCE
    16/17/18, CUBRIDdb CCI composite codes) and are covered per driver in
    test_integration.py.
    """
    pyc, cext = both_engines
    sql = text("SELECT id, nn, nl, bi, n, dt FROM drvdiff_desc")

    def run(engine: Any) -> list[tuple[Any, ...]]:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS drvdiff_desc"))
            conn.execute(
                text(
                    "CREATE TABLE drvdiff_desc (id INTEGER PRIMARY KEY, nn VARCHAR(20) NOT NULL, "
                    "nl VARCHAR(20), bi BIGINT, n NUMERIC(10,2), dt DATE)"
                )
            )
        try:
            with engine.connect() as conn:
                result = conn.execute(sql)
                desc = [(d[0], int(d[1]), bool(d[6])) for d in result.cursor.description]
                result.all()
        finally:
            with engine.begin() as conn:
                conn.execute(text("DROP TABLE IF EXISTS drvdiff_desc"))
        return desc

    expected = [
        ("id", 8, False),
        ("nn", 2, False),
        ("nl", 2, True),
        ("bi", 21, True),
        ("n", 7, True),
        ("dt", 13, True),
    ]
    assert run(cext) == expected
    py_desc = run(pyc)
    assert [d[:2] for d in py_desc] == [e[:2] for e in expected]
    assert [d[2] for d in py_desc] == [e[2] for e in expected]


# ---------------------------------------------------------------------------
# #484: SET/MULTISET/SEQUENCE round trips agree
# ---------------------------------------------------------------------------


def test_collection_roundtrip_agrees(both_engines: Any) -> None:
    """SET/MULTISET/SEQUENCE values agree once each driver's native shape is normalized.

    Binding a collection as a parameter is blocked on released pycubrid
    (``ProgrammingError``; the typed-collection parameters of
    cubrid-lab/pycubrid#567 are on pycubrid main only, see
    docs/DRIVER_COMPAT.md #11 and test_collection_roundtrip.py), so this case
    writes the collection literal directly in SQL, which both drivers accept
    identically. Reading differs by driver: CUBRIDdb always returns `str`
    elements regardless of the declared element type, while pycubrid (with
    ``?decode_collections=true``) returns the declared element type (`int`
    here); SET comes back as a `set` (CUBRIDdb) or `frozenset` (pycubrid).
    Both sides are normalized to `str` elements before comparing: SET as a
    set (order never matters there) and MULTISET via `sorted()` (unordered,
    docs/TYPES.md), both keeping duplicate counts; SEQUENCE compares the
    insertion order directly, which both drivers preserve. A NULL collection
    is unaffected by any of this and compares equal (`None`) on both drivers.
    """
    _, cext = both_engines
    # both_engines already proved pycubrid connects with the plain URL; add
    # decode_collections without disturbing any query options CUBRID_TEST_URL
    # already carries (update_query_dict, not string concatenation), and let a
    # connection failure here fail the test like any other, rather than skip
    # and silently drop this case from the required lane.
    pyc_url = make_url(_pycubrid_url()).update_query_dict({"decode_collections": "true"})
    pyc = create_engine(pyc_url)
    try:
        _run_collection_roundtrip(cext)
        _run_collection_roundtrip(pyc)
    finally:
        pyc.dispose()


def _run_collection_roundtrip(engine: Any) -> None:
    table = "drvdiff_coll"
    with engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        conn.execute(
            text(
                f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, s SET(INTEGER), "
                "ms MULTISET(INTEGER), sq SEQUENCE(INTEGER))"
            )
        )
        # Row 1 proves SET dedups and is unordered, MULTISET keeps duplicates,
        # and SEQUENCE keeps insertion order; row 2 proves NULL collections
        # round-trip as None.
        conn.execute(
            text(
                f"INSERT INTO {table} (id, s, ms, sq) VALUES (1, {{3,1,2,1}}, {{3,1,2,1}}, {{3,1,2,1}})"
            )
        )
        conn.execute(text(f"INSERT INTO {table} (id, s, ms, sq) VALUES (2, NULL, NULL, NULL)"))
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(f"SELECT s, ms, sq FROM {table} ORDER BY id")).all()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))

    (s, ms, sq), (s_null, ms_null, sq_null) = rows
    assert {str(v) for v in s} == {"1", "2", "3"}
    # MULTISET is unordered (docs/TYPES.md); compare duplicate counts via
    # sorted(), not the server's current iteration order, like
    # test_collection_roundtrip.py does.
    assert sorted(str(v) for v in ms) == ["1", "1", "2", "3"]
    assert [str(v) for v in sq] == ["3", "1", "2", "1"]
    assert (s_null, ms_null, sq_null) == (None, None, None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
