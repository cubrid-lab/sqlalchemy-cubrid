"""Regression tests for reported issues — live CUBRID execution.

Each test reproduces a specific issue and verifies the fix against a real
CUBRID server.  These tests remain permanently as compatibility contracts.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    select,
    text,
)
from sqlalchemy.orm import Session

_DEFAULT_URL = "cubrid://dba@localhost:33000/testdb"


def _cubrid_url() -> str:
    return os.environ.get("CUBRID_TEST_URL", _DEFAULT_URL)


def _can_connect() -> bool:
    try:
        engine = create_engine(_cubrid_url())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


_in_ci = os.environ.get("CI", "").lower() in ("true", "1")
_available = _can_connect()
if _in_ci and not _available:
    pytest.fail(
        "CUBRID instance is NOT reachable but CI=true — "
        "regression tests must not be silently skipped in CI.",
        pytrace=False,
    )

pytestmark = pytest.mark.skipif(
    not _available,
    reason="CUBRID instance not available (set CUBRID_TEST_URL)",
)


@pytest.fixture()
def engine():
    eng = create_engine(_cubrid_url())
    yield eng
    eng.dispose()


@pytest.fixture()
def metadata(engine):
    meta = MetaData()
    yield meta
    meta.drop_all(engine)


class TestIssue356ODKUValues:
    """#356: ON DUPLICATE KEY UPDATE must not render VALUES(col).

    CUBRID 11.4 does not support the VALUES() function in ODKU clauses.
    The dialect must emit a bind parameter instead.
    """

    def test_upsert_with_inserted_ref(self, engine, metadata):
        from sqlalchemy_cubrid.dml import insert

        t = Table(
            "test_356",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("val", String(50)),
        )
        metadata.create_all(engine)

        with Session(engine) as s:
            s.execute(t.insert().values(id=1, val="original"))
            s.commit()

        with Session(engine) as s:
            stmt = insert(t).values(id=1, val="updated")
            stmt = stmt.on_duplicate_key_update(val=stmt.inserted.val)
            s.execute(stmt)
            s.commit()

        with Session(engine) as s:
            row = s.execute(select(t).where(t.c.id == 1)).one()
            assert row.val == "updated"

    def test_upsert_with_literal_value(self, engine, metadata):
        from sqlalchemy_cubrid.dml import insert

        t = Table(
            "test_356_lit",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("val", String(50)),
        )
        metadata.create_all(engine)

        with Session(engine) as s:
            s.execute(t.insert().values(id=1, val="original"))
            s.commit()

        with Session(engine) as s:
            stmt = insert(t).values(id=1, val="updated")
            stmt = stmt.on_duplicate_key_update(val="updated")
            s.execute(stmt)
            s.commit()

        with Session(engine) as s:
            row = s.execute(select(t).where(t.c.id == 1)).one()
            assert row.val == "updated"


class TestIssue371ODKUMultiRow:
    """#371: ODKU with multi-row INSERT."""

    def test_multi_row_with_literal_odku(self, engine, metadata):
        """Multi-row INSERT + literal ODKU value works."""
        from sqlalchemy_cubrid.dml import insert

        t = Table(
            "test_371_lit",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("val", String(50)),
        )
        metadata.create_all(engine)

        with Session(engine) as s:
            s.execute(t.insert().values(id=1, val="original"))
            s.commit()

        with Session(engine) as s:
            stmt = insert(t).values([{"id": 1, "val": "A"}, {"id": 2, "val": "B"}])
            stmt = stmt.on_duplicate_key_update(val="overwritten")
            s.execute(stmt)
            s.commit()

        with Session(engine) as s:
            rows = {r.id: r.val for r in s.execute(select(t).order_by(t.c.id)).all()}
            assert rows[1] == "overwritten"
            assert rows[2] == "B"

    def test_multi_row_with_inserted_ref_raises(self, engine, metadata):
        """Multi-row INSERT + stmt.inserted raises CompileError."""
        from sqlalchemy.exc import CompileError
        from sqlalchemy_cubrid.dml import insert

        t = Table(
            "test_371_ref",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("val", String(50)),
        )
        metadata.create_all(engine)

        stmt = insert(t).values([{"id": 1, "val": "A"}])
        stmt = stmt.on_duplicate_key_update(val=stmt.inserted.val)
        with pytest.raises(CompileError, match="single-row INSERT"):
            with Session(engine) as s:
                s.execute(stmt)


class TestIssue355FKIndexCollision:
    """#355: CREATE INDEX on FK columns must not collide with auto-index.

    CUBRID auto-creates an index for FK columns. Explicit CREATE INDEX
    on the same column set fails with errno=-272.
    """

    def test_fk_with_non_unique_index(self, engine, metadata):
        """Non-unique index on FK columns: CUBRID accepts this natively."""
        Table("test_355_parent", metadata, Column("id", Integer, primary_key=True))
        Table(
            "test_355_child",
            metadata,
            Column("id", Integer, primary_key=True),
            Column(
                "pid",
                Integer,
                ForeignKey("test_355_parent.id"),
                nullable=False,
            ),
            Index("idx_355_pid", "pid"),
        )
        # CUBRID allows non-unique index alongside FK auto-index
        metadata.create_all(engine)

    def test_fk_with_unique_explicit_index_raises(self, engine, metadata):
        """UNIQUE index on FK columns raises CompileError (#366).

        CUBRID cannot add a UNIQUE index after FK auto-index creation.
        The dialect raises CompileError with guidance to use column-level
        unique=True instead.
        """
        from sqlalchemy.exc import CompileError

        Table(
            "test_355_parent_u",
            metadata,
            Column("id", Integer, primary_key=True),
        )
        Table(
            "test_355_child_u",
            metadata,
            Column("id", Integer, primary_key=True),
            Column(
                "pid",
                Integer,
                ForeignKey("test_355_parent_u.id"),
                nullable=False,
            ),
            Index("idx_355_pid_u", "pid", unique=True),
        )
        with pytest.raises(CompileError, match="CUBRID cannot create a UNIQUE index"):
            metadata.create_all(engine)
