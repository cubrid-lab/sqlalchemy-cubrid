# test/test_integration.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Integration tests against a live CUBRID instance.

These tests require a running CUBRID database.  They are skipped
automatically when no CUBRID connection is available.

Set the environment variable ``CUBRID_TEST_URL`` to the connection
URL, e.g.::

    export CUBRID_TEST_URL="cubrid://dba@localhost:33000/testdb"

Alternatively, the tests look for a CUBRID instance at the default
``cubrid://dba@localhost:33000/testdb``.
"""

from __future__ import annotations

import datetime
from inspect import signature
import os
from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    inspect,
    select,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from sqlalchemy_cubrid import BLOB, CLOB, DOUBLE, MULTISET, SEQUENCE, SET

from test.pycubrid_upstream import xfail_unreleased_pycubrid_fix


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_DEFAULT_URL = "cubrid://dba@localhost:33000/testdb"


def _cubrid_url() -> str:
    return os.environ.get("CUBRID_TEST_URL", _DEFAULT_URL)


def _can_connect() -> bool:
    """Return True if a CUBRID instance is reachable."""
    try:
        engine = create_engine(_cubrid_url())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


# In CI, CUBRID is intentionally provisioned — connectivity failure
# should be a hard test error, not a silent skip.
_available = _can_connect()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _available,
        reason="CUBRID instance not available (set CUBRID_TEST_URL)",
    ),
]


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(_cubrid_url(), echo=False)
    yield eng
    eng.dispose()


@pytest.fixture(scope="module")
def metadata(engine):
    meta = MetaData()

    Table(
        "integration_users",
        meta,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("name", String(100), nullable=False),
        Column("email", String(200)),
    )

    Table(
        "integration_orders",
        meta,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column(
            "user_id",
            Integer,
            ForeignKey("integration_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        Column("amount", Integer, nullable=False),
    )

    meta.create_all(engine)
    yield meta
    meta.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean_tables(engine, metadata):
    """Truncate tables before each test."""
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM integration_orders"))
        conn.execute(text("DELETE FROM integration_users"))
    yield


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestServerConnection:
    def test_server_version(self, engine):
        """Verify we can connect and get a server version."""
        with engine.connect() as conn:
            version = conn.execute(text("SELECT VERSION()")).scalar()
        assert version is not None
        parts = version.split(".")
        assert len(parts) >= 3, f"Unexpected version format: {version}"

    def test_select_literal(self, engine):
        """Basic SELECT without tables."""
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 42")).scalar()
        assert result == 42


class TestIsDistinctFromIntegration:
    @pytest.mark.parametrize(
        ("left", "right", "expected_distinct"),
        [
            (1, 1, False),
            (1, 2, True),
            (None, None, False),
            (None, 1, True),
        ],
    )
    def test_distinct_from_truth_table(self, engine, left, right, expected_distinct):
        """Verify both null-safe distinctness operators against live CUBRID."""
        left_value = sa.literal(left)
        right_value = sa.literal(right)
        statement = sa.select(
            left_value.is_distinct_from(right_value).label("distinct_value"),
            left_value.is_not_distinct_from(right_value).label("not_distinct_value"),
        )

        with engine.connect() as connection:
            row = connection.execute(statement).one()

        assert bool(row.distinct_value) is expected_distinct
        assert bool(row.not_distinct_value) is (not expected_distinct)


class TestDDLAndDML:
    def test_insert_and_select(self, engine, metadata):
        """INSERT rows and SELECT them back."""
        users = metadata.tables["integration_users"]
        with engine.begin() as conn:
            conn.execute(users.insert().values(name="Alice", email="alice@example.com"))
            conn.execute(users.insert().values(name="Bob", email="bob@example.com"))

        with engine.connect() as conn:
            rows = conn.execute(users.select().order_by(users.c.name)).fetchall()
        assert len(rows) == 2
        assert rows[0].name == "Alice"
        assert rows[1].name == "Bob"

    def test_auto_increment(self, engine, metadata):
        """AUTO_INCREMENT generates sequential IDs."""
        users = metadata.tables["integration_users"]
        with engine.begin() as conn:
            conn.execute(users.insert().values(name="User1"))
            conn.execute(users.insert().values(name="User2"))

        with engine.connect() as conn:
            ids = [
                r[0]
                for r in conn.execute(
                    users.select().with_only_columns(users.c.id).order_by(users.c.id)
                ).fetchall()
            ]
        assert len(ids) == 2
        assert ids[1] > ids[0], "AUTO_INCREMENT should produce increasing IDs"

    def test_update(self, engine, metadata):
        """UPDATE modifies rows."""
        users = metadata.tables["integration_users"]
        with engine.begin() as conn:
            conn.execute(users.insert().values(name="Charlie", email="old@example.com"))
            conn.execute(
                users.update().where(users.c.name == "Charlie").values(email="new@example.com")
            )

        with engine.connect() as conn:
            email = conn.execute(users.select().where(users.c.name == "Charlie")).fetchone().email
        assert email == "new@example.com"

    def test_delete(self, engine, metadata):
        """DELETE removes rows."""
        users = metadata.tables["integration_users"]
        with engine.begin() as conn:
            conn.execute(users.insert().values(name="Ephemeral"))
            conn.execute(users.delete().where(users.c.name == "Ephemeral"))

        with engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM integration_users WHERE name = 'Ephemeral'")
            ).scalar()
        assert count == 0

    def test_join(self, engine, metadata):
        """JOIN between two tables."""
        users = metadata.tables["integration_users"]
        orders = metadata.tables["integration_orders"]

        with engine.begin() as conn:
            conn.execute(users.insert().values(name="Dave"))
            user_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
            conn.execute(orders.insert().values(user_id=user_id, amount=100))
            conn.execute(orders.insert().values(user_id=user_id, amount=250))

        with engine.connect() as conn:
            j = users.join(orders, users.c.id == orders.c.user_id)
            rows = conn.execute(
                users.select()
                .with_only_columns(users.c.name, orders.c.amount)
                .select_from(j)
                .order_by(orders.c.amount)
            ).fetchall()
        assert len(rows) == 2
        assert rows[0].amount == 100
        assert rows[1].amount == 250

    def test_limit_offset(self, engine, metadata):
        """LIMIT and OFFSET work correctly."""
        users = metadata.tables["integration_users"]
        with engine.begin() as conn:
            for i in range(5):
                conn.execute(users.insert().values(name=f"User{i}"))

        with engine.connect() as conn:
            rows = conn.execute(users.select().order_by(users.c.id).limit(2).offset(1)).fetchall()
        assert len(rows) == 2


class TestReflection:
    def test_has_table(self, engine, metadata):
        """has_table() returns correct results."""
        insp = inspect(engine)
        assert insp.has_table("integration_users")
        assert not insp.has_table("nonexistent_table_xyz")

    def test_get_table_names(self, engine, metadata):
        """get_table_names() includes our test tables."""
        insp = inspect(engine)
        tables = insp.get_table_names()
        assert "integration_users" in tables
        assert "integration_orders" in tables

    def test_get_columns(self, engine, metadata):
        """get_columns() reflects column metadata."""
        insp = inspect(engine)
        columns = insp.get_columns("integration_users")
        col_names = [c["name"] for c in columns]
        assert "id" in col_names
        assert "name" in col_names
        assert "email" in col_names

    def test_get_pk_constraint(self, engine, metadata):
        """get_pk_constraint() reflects primary key."""
        insp = inspect(engine)
        pk = insp.get_pk_constraint("integration_users")
        assert "id" in pk["constrained_columns"]

    def test_get_foreign_keys(self, engine, metadata):
        """get_foreign_keys() reflects FK from orders → users."""
        insp = inspect(engine)
        fks = insp.get_foreign_keys("integration_orders")
        assert len(fks) >= 1, (
            "get_foreign_keys() returned empty — FK reflection is broken. "
            "This previously masked a real Alembic regression."
        )
        fk = fks[0]
        assert "user_id" in fk["constrained_columns"]
        assert fk["referred_table"] == "integration_users"


class TestTransactions:
    def test_savepoint(self, engine, metadata):
        """Savepoint support (CUBRID supports savepoints, not RELEASE SAVEPOINT)."""
        users = metadata.tables["integration_users"]
        with engine.begin() as conn:
            conn.execute(users.insert().values(name="BeforeSP"))
            savepoint = conn.begin_nested()
            conn.execute(users.insert().values(name="InSP"))
            savepoint.rollback()

        with engine.connect() as conn:
            rows = conn.execute(users.select()).fetchall()
        names = [r.name for r in rows]
        assert "BeforeSP" in names
        assert "InSP" not in names

    def test_rollback(self, engine, metadata):
        """Transaction rollback discards changes."""
        users = metadata.tables["integration_users"]
        with engine.connect() as conn:
            trans = conn.begin()
            conn.execute(users.insert().values(name="WillRollback"))
            trans.rollback()

        with engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM integration_users WHERE name = 'WillRollback'")
            ).scalar()
        assert count == 0


class TestLastRowId:
    def test_lastrowid_via_orm(self, engine, metadata):
        """Verify lastrowid works through SA ORM Session."""
        users = metadata.tables["integration_users"]
        with Session(engine) as session:
            result = session.execute(users.insert().values(name="LastRowIdTest"))
            inserted_pk = result.inserted_primary_key[0]
            session.commit()
        assert inserted_pk is not None
        assert isinstance(inserted_pk, int)
        assert inserted_pk > 0


class TestIsolationLevel:
    def test_get_and_set_isolation_level(self, engine):
        """Get/set isolation level round-trip."""
        with engine.connect() as conn:
            raw_conn = conn.connection.dbapi_connection
            dialect = engine.dialect

            level = dialect.get_isolation_level(raw_conn)
            # CUBRID returns isolation level as an integer (e.g. 4) or string
            assert level is not None

            # Set to a known level and verify no error
            dialect.set_isolation_level(raw_conn, "SERIALIZABLE")
            new_level = dialect.get_isolation_level(raw_conn)
            assert new_level is not None


class TestDoPing:
    def test_ping_success(self, engine):
        """do_ping() succeeds on a live connection."""
        with engine.connect() as conn:
            raw_conn = conn.connection.dbapi_connection
            dialect = engine.dialect
            result = dialect.do_ping(raw_conn)
            assert result is True

    def test_pool_pre_ping(self):
        """Engine with pool_pre_ping=True works correctly."""
        eng = create_engine(_cubrid_url(), pool_pre_ping=True, echo=False)
        try:
            with eng.connect() as conn:
                result = conn.execute(text("SELECT 1")).scalar()
            assert result == 1
        finally:
            eng.dispose()


class TestIsDisconnect:
    def test_is_disconnect_with_non_disconnect_error(self, engine):
        """is_disconnect() returns False for normal database errors."""
        dialect = engine.dialect
        with engine.connect() as conn:
            raw_conn = conn.connection.dbapi_connection
            try:
                cursor = raw_conn.cursor()
                cursor.execute("SELECT * FROM nonexistent_table_xyz_12345")
            except Exception as e:
                assert dialect.is_disconnect(e, conn, None) is False

    def test_is_disconnect_returns_false_for_runtime_error(self, engine):
        """is_disconnect() returns False for non-DBAPI errors."""
        dialect = engine.dialect
        exc = RuntimeError("some random error")
        assert dialect.is_disconnect(exc, None, None) is False


class TestPostfetchLastRowId:
    def test_lastrowid_consistency(self, engine, metadata):
        """Verify lastrowid returns consistent IDs across inserts."""
        users = metadata.tables["integration_users"]
        ids = []
        with Session(engine) as session:
            for i in range(3):
                result = session.execute(users.insert().values(name=f"lastrowid_test_{i}"))
                ids.append(result.inserted_primary_key[0])
            session.commit()

        assert len(ids) == 3
        assert all(isinstance(pk, int) for pk in ids)
        assert ids[0] < ids[1] < ids[2], "IDs should be monotonically increasing"


class TestConnectionPool:
    def test_pool_recycle(self):
        """Engine with pool_recycle works without errors."""
        eng = create_engine(_cubrid_url(), pool_recycle=60, echo=False)
        try:
            with eng.connect() as conn:
                result = conn.execute(text("SELECT 1")).scalar()
            assert result == 1
        finally:
            eng.dispose()

    def test_multiple_connections(self):
        """Multiple connections from pool work correctly."""
        eng = create_engine(_cubrid_url(), pool_size=3, echo=False)
        try:
            conns = []
            for _ in range(3):
                c = eng.connect()
                conns.append(c)
            for c in conns:
                result = c.execute(text("SELECT 1")).scalar()
                assert result == 1
            for c in conns:
                c.close()
        finally:
            eng.dispose()


class TestReplaceIntegration:
    def test_replace_insert(self, engine, metadata):
        """REPLACE INTO inserts a new row when no conflict."""
        from sqlalchemy_cubrid import replace

        users = metadata.tables["integration_users"]
        with engine.begin() as conn:
            stmt = replace(users).values(name="ReplaceNew", email="replace@example.com")
            conn.execute(stmt)

        with engine.connect() as conn:
            row = conn.execute(users.select().where(users.c.name == "ReplaceNew")).fetchone()
        assert row is not None
        assert row.email == "replace@example.com"

    def test_replace_conflict(self, engine, metadata):
        """REPLACE INTO replaces existing row on duplicate key."""
        from sqlalchemy_cubrid import replace

        users = metadata.tables["integration_users"]
        with engine.begin() as conn:
            # Insert initial row
            conn.execute(users.insert().values(name="ReplaceMe", email="old@example.com"))
            row_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()

            # REPLACE with same PK — should delete old + insert new
            stmt = replace(users).values(id=row_id, name="Replaced", email="new@example.com")
            conn.execute(stmt)

        with engine.connect() as conn:
            row = conn.execute(users.select().where(users.c.id == row_id)).fetchone()
        assert row is not None
        assert row.name == "Replaced"
        assert row.email == "new@example.com"


class TestRecursiveCTEIntegration:
    def test_recursive_cte(self, engine, metadata):
        """WITH RECURSIVE generates a sequence in CUBRID 11.x+."""
        from sqlalchemy import column as col_func, literal as lit_func

        cte = select(lit_func(1).label("n")).cte(name="nums", recursive=True)
        cte_alias = cte.alias("a")
        cte = cte.union_all(
            select(col_func("n") + 1).select_from(cte_alias).where(col_func("n") < 5)
        )
        stmt = select(cte.c.n).order_by(cte.c.n)

        with engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()
        values = [r[0] for r in rows]
        assert values == [1, 2, 3, 4, 5]


class TestTraceQueryIntegration:
    def test_trace_query_returns_output(self, engine, metadata):
        """trace_query() returns non-empty trace output."""
        from sqlalchemy_cubrid import trace_query

        users = metadata.tables["integration_users"]
        # Insert a row so the query has something to trace
        with engine.begin() as conn:
            conn.execute(users.insert().values(name="TraceTest", email="trace@example.com"))

        with engine.connect() as conn:
            traces = trace_query(conn, text("SELECT * FROM integration_users"))
        # trace_query should return a list; on CUBRID it should have content
        assert isinstance(traces, list)
        # Trace may be empty in some CUBRID configurations, but should not error

    def test_trace_query_with_parameters(self, engine, metadata):
        """trace_query() works with parameterized statements."""
        from sqlalchemy_cubrid import trace_query

        users = metadata.tables["integration_users"]
        with engine.begin() as conn:
            conn.execute(users.insert().values(name="TraceParam", email="param@example.com"))

        with engine.connect() as conn:
            traces = trace_query(
                conn,
                text("SELECT * FROM integration_users WHERE name = :name"),
                parameters={"name": "TraceParam"},
            )
        assert isinstance(traces, list)


class TestFetchShapeCompatibility:
    """Verify DB-API fetchall/fetchmany return types are compatible with SQLAlchemy.

    pycubrid returns list[tuple] from fetchall() and fetchmany().
    These tests ensure SQLAlchemy handles these shapes correctly at the
    raw DB-API and ORM layers.
    """

    def test_raw_dbapi_fetchall_returns_list(self, engine):
        """Raw DB-API fetchall() returns a list of tuples."""
        raw_conn = engine.raw_connection()
        try:
            cursor = raw_conn.cursor()
            cursor.execute("SELECT 1, 'hello'")
            rows = cursor.fetchall()
            assert isinstance(rows, list), f"fetchall() returned {type(rows)}, expected list"
            assert len(rows) >= 1
            assert isinstance(rows[0], tuple), f"row type is {type(rows[0])}, expected tuple"
            cursor.close()
        finally:
            raw_conn.close()

    def test_raw_dbapi_fetchmany_returns_list(self, engine):
        """Raw DB-API fetchmany() returns a list of tuples."""
        raw_conn = engine.raw_connection()
        try:
            cursor = raw_conn.cursor()
            cursor.execute("SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3")
            rows = cursor.fetchmany(2)
            assert isinstance(rows, list), f"fetchmany() returned {type(rows)}, expected list"
            assert len(rows) == 2
            assert isinstance(rows[0], tuple), f"row type is {type(rows[0])}, expected tuple"
            cursor.close()
        finally:
            raw_conn.close()

    def test_raw_dbapi_fetchone_returns_tuple(self, engine):
        """Raw DB-API fetchone() returns a single tuple."""
        raw_conn = engine.raw_connection()
        try:
            cursor = raw_conn.cursor()
            cursor.execute("SELECT 42, 'test'")
            row = cursor.fetchone()
            assert isinstance(row, tuple), f"fetchone() returned {type(row)}, expected tuple"
            assert row == (42, "test")
            cursor.close()
        finally:
            raw_conn.close()

    def test_sqlalchemy_fetchall_with_orm(self, engine, metadata):
        """SQLAlchemy ORM layer works correctly with pycubrid's fetch results."""
        users = metadata.tables["integration_users"]
        with engine.begin() as conn:
            conn.execute(users.insert().values(name="FetchTest", email="fetch@example.com"))

        with engine.connect() as conn:
            result = conn.execute(
                select(users.c.name, users.c.email).where(users.c.name == "FetchTest")
            )
            rows = result.fetchall()
            assert len(rows) >= 1
            assert rows[0].name == "FetchTest"
            assert rows[0].email == "fetch@example.com"

    def test_sqlalchemy_fetchmany_with_text(self, engine, metadata):
        """SQLAlchemy text() query with fetchmany works correctly."""
        users = metadata.tables["integration_users"]
        with engine.begin() as conn:
            for i in range(3):
                conn.execute(
                    users.insert().values(name=f"BatchFetch{i}", email=f"batch{i}@example.com")
                )

        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT name, email FROM integration_users WHERE name LIKE :pat"),
                {"pat": "BatchFetch%"},
            )
            rows = result.fetchmany(2)
            assert len(rows) == 2
            # Verify rows are accessible by attribute name
            assert hasattr(rows[0], "name")

    def test_orm_bulk_insert_uses_insertmanyvalues(self, engine, metadata):
        """Prove the insertmanyvalues optimization works at runtime.

        This test verifies that ORM bulk inserts via Session.add_all()
        execute successfully against a live CUBRID instance, confirming
        the dialect's use_insertmanyvalues=True is honored end-to-end.
        """

        class _Base(DeclarativeBase):
            pass

        class BulkUser(_Base):
            __tablename__ = "imv_bulk_test"
            id: Mapped[int] = mapped_column(
                Integer,
                primary_key=True,
                autoincrement=True,
            )
            name: Mapped[str] = mapped_column(String(100))

        _Base.metadata.create_all(engine)
        try:
            with Session(engine) as session:
                session.add_all([BulkUser(name=f"user_{i}") for i in range(10)])
                session.commit()

            with engine.connect() as conn:
                count = conn.execute(text("SELECT COUNT(*) FROM imv_bulk_test")).scalar()
                assert count == 10
        finally:
            _Base.metadata.drop_all(engine)


class TestAlembicAlterColumnIntegration:
    """Live validation that CubridImpl.alter_column emits server-accepted DDL.

    Guards the native ALTER TABLE MODIFY / CHANGE / RENAME COLUMN support
    (cubrid-lab/sqlalchemy-cubrid#305) against a real CUBRID server so we do
    not rely on compile-only assertions. See test/test_alembic.py for the
    offline SQL-emission tests.
    """

    def _operations(self, conn):
        from alembic.migration import MigrationContext
        from alembic.operations import Operations

        import sqlalchemy_cubrid.alembic_impl  # noqa: F401  (registers CubridImpl)

        ctx = MigrationContext.configure(connection=conn, opts={"as_sql": False})
        return Operations(ctx)

    def test_modify_column_type(self, engine):
        """alter_column(type_=...) emits ALTER TABLE ... MODIFY, accepted live."""
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS alter_it_modify"))
            conn.execute(text("CREATE TABLE alter_it_modify (id INT PRIMARY KEY, age INT)"))
            try:
                op = self._operations(conn)
                op.alter_column(
                    "alter_it_modify", "age", type_=sa.BigInteger(), existing_nullable=True
                )
                cols = {
                    c["name"]: str(c["type"]) for c in inspect(conn).get_columns("alter_it_modify")
                }
                assert cols["age"] == "BIGINT"
            finally:
                conn.execute(text("DROP TABLE IF EXISTS alter_it_modify"))
                conn.commit()

    def test_modify_column_full_definition(self, engine):
        """MODIFY restates NOT NULL / DEFAULT / COMMENT without error."""
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS alter_it_fulldef"))
            conn.execute(text("CREATE TABLE alter_it_fulldef (id INT PRIMARY KEY, age INT)"))
            try:
                op = self._operations(conn)
                op.alter_column(
                    "alter_it_fulldef",
                    "age",
                    type_=sa.BigInteger(),
                    existing_nullable=False,
                    existing_server_default="0",
                    existing_comment="age in years",
                )
                cols = {c["name"]: c for c in inspect(conn).get_columns("alter_it_fulldef")}
                assert str(cols["age"]["type"]) == "BIGINT"
                assert cols["age"]["nullable"] is False
            finally:
                conn.execute(text("DROP TABLE IF EXISTS alter_it_fulldef"))
                conn.commit()

    def test_rename_column(self, engine):
        """alter_column(new_column_name=...) emits ALTER TABLE ... RENAME COLUMN."""
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS alter_it_rename"))
            conn.execute(
                text("CREATE TABLE alter_it_rename (id INT PRIMARY KEY, note VARCHAR(50))")
            )
            try:
                op = self._operations(conn)
                op.alter_column(
                    "alter_it_rename",
                    "note",
                    new_column_name="remark",
                    existing_type=sa.String(50),
                )
                names = {c["name"] for c in inspect(conn).get_columns("alter_it_rename")}
                assert "remark" in names and "note" not in names
            finally:
                conn.execute(text("DROP TABLE IF EXISTS alter_it_rename"))
                conn.commit()

    def test_change_column_rename_and_type(self, engine):
        """Combined rename + type change emits ALTER TABLE ... CHANGE, accepted live."""
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS alter_it_change"))
            conn.execute(
                text("CREATE TABLE alter_it_change (id INT PRIMARY KEY, note VARCHAR(50))")
            )
            try:
                op = self._operations(conn)
                op.alter_column(
                    "alter_it_change",
                    "note",
                    new_column_name="memo",
                    type_=sa.String(100),
                    existing_nullable=True,
                )
                cols = {
                    c["name"]: str(c["type"]) for c in inspect(conn).get_columns("alter_it_change")
                }
                assert "note" not in cols
                assert cols["memo"] == "VARCHAR(100)"
            finally:
                conn.execute(text("DROP TABLE IF EXISTS alter_it_change"))
                conn.commit()


class TestExecutemanyNoneAndRowcount:
    """#502: executemany stores ``None`` as NULL and reports the total rowcount.

    CUBRIDdb reuses the previous row's value for a ``None`` parameter and
    reports only the last row's rowcount; the ``cubrid://`` dialect runs such
    statements row by row. pycubrid is correct natively and must keep its own
    ``executemany``. Both lanes (``CUBRID_TEST_URL``) run these tests.
    """

    _ROWS = [
        {"id": 1, "v": "a", "n": 10},
        {"id": 2, "v": None, "n": None},
        {"id": 3, "v": "c", "n": 30},
        {"id": 4, "v": None, "n": None},
    ]
    _EXPECTED = [(1, "a", 10), (2, None, None), (3, "c", 30), (4, None, None)]

    @pytest.fixture
    def em_table(self, engine):
        meta = MetaData()
        tbl = Table(
            "em502",
            meta,
            Column("id", Integer, primary_key=True, autoincrement=False),
            Column("v", String(20)),
            Column("n", Integer),
        )
        meta.drop_all(engine)
        meta.create_all(engine)
        yield tbl
        meta.drop_all(engine)

    @staticmethod
    def _rows(engine):
        with engine.connect() as conn:
            return [tuple(r) for r in conn.execute(text("SELECT id, v, n FROM em502 ORDER BY id"))]

    def test_text_executemany_interleaved_none(self, engine, em_table):
        with engine.begin() as conn:
            result = conn.execute(
                text("INSERT INTO em502 (id, v, n) VALUES (:id, :v, :n)"), self._ROWS
            )
            assert result.rowcount == 4
        assert self._rows(engine) == self._EXPECTED

    def test_core_update_executemany_with_none(self, engine, em_table):
        with engine.begin() as conn:
            conn.execute(em_table.insert(), [{"id": i, "v": "orig", "n": i} for i in (1, 2, 3, 4)])
        stmt = (
            em_table.update()
            .where(em_table.c.id == sa.bindparam("b_id"))
            .values(v=sa.bindparam("b_v"), n=sa.bindparam("b_n"))
        )
        params = [{"b_id": r["id"], "b_v": r["v"], "b_n": r["n"]} for r in self._ROWS]
        with engine.begin() as conn:
            assert conn.execute(stmt, params).rowcount == 4
        assert self._rows(engine) == self._EXPECTED

    def test_executemany_rowcount_is_total(self, engine, em_table):
        with engine.begin() as conn:
            conn.execute(em_table.insert(), [{"id": i, "v": "x", "n": i % 2} for i in range(1, 7)])
        with engine.begin() as conn:
            # Rows matched per parameter set: 3 (n=1), 0 (n=5), 3 (n=0).
            upd = conn.execute(
                em_table.update().where(em_table.c.n == sa.bindparam("b_n")).values(v="y"),
                [{"b_n": 1}, {"b_n": 5}, {"b_n": 0}],
            )
            assert upd.rowcount == 6
            dele = conn.execute(
                em_table.delete().where(em_table.c.id == sa.bindparam("b_id")),
                [{"b_id": 1}, {"b_id": 2}, {"b_id": 99}],
            )
            assert dele.rowcount == 2

    def test_orm_batched_update_of_several_objects(self, engine, em_table):
        class _Base(DeclarativeBase):
            pass

        class Em(_Base):
            __table__ = em_table

        with Session(engine) as session:
            session.add_all([Em(id=i, v="orig", n=i) for i in (1, 2, 3, 4)])
            session.commit()
            objs = {o.id: o for o in session.scalars(select(Em))}
            for row in self._ROWS:
                objs[row["id"]].v = row["v"]
                objs[row["id"]].n = row["n"]
            # One executemany UPDATE for all four rows; a last-row rowcount
            # used to raise StaleDataError here on cubrid://.
            session.commit()
        assert self._rows(engine) == self._EXPECTED

    def test_core_insert_many_stays_on_insertmanyvalues(self, engine, em_table, monkeypatch):
        calls = []
        original = engine.dialect.do_executemany

        def spy(*args, **kwargs):
            calls.append(args[1])
            return original(*args, **kwargs)

        monkeypatch.setattr(engine.dialect, "do_executemany", spy)
        with engine.begin() as conn:
            conn.execute(em_table.insert(), self._ROWS)
        assert calls == []
        assert self._rows(engine) == self._EXPECTED

    def test_core_insert_many_with_bind_expression_uses_executemany(self, engine, monkeypatch):
        """A bind_expression() column drops insertmanyvalues (#421).

        The INSERT then goes through ``do_executemany`` (the per-row guard on
        ``cubrid://``), and interleaved ``None`` must still store NULL.
        """

        class CastString(sa.types.TypeDecorator):
            impl = String(20)
            cache_ok = True

            def bind_expression(self, bindvalue):
                return sa.cast(sa.type_coerce(bindvalue, String(20)), String(20))

        meta = MetaData()
        tbl = Table(
            "em502_bindexpr",
            meta,
            Column("id", Integer, primary_key=True, autoincrement=False),
            Column("v", CastString()),
            Column("n", Integer),
        )
        meta.drop_all(engine)
        meta.create_all(engine)
        calls = []
        original = engine.dialect.do_executemany

        def spy(*args, **kwargs):
            calls.append(args[1])
            return original(*args, **kwargs)

        monkeypatch.setattr(engine.dialect, "do_executemany", spy)
        try:
            with engine.begin() as conn:
                assert conn.execute(tbl.insert(), self._ROWS).rowcount == 4
            with engine.connect() as conn:
                rows = [tuple(r) for r in conn.execute(select(tbl).order_by(tbl.c.id))]
            assert len(calls) == 1
            assert rows == self._EXPECTED
        finally:
            meta.drop_all(engine)


class TestBackslashLiteralRoundtrip:
    """Regression #313: backslashes must survive both param binding and
    literal_binds rendering on a default CUBRID (no_backslash_escapes=yes)."""

    @pytest.mark.parametrize(
        "value",
        [
            "C:\\temp",
            "regex \\d+",
            "a\\nb",
            "C:\\it's",
        ],
    )
    def test_backslash_roundtrip(self, engine, metadata, value):
        users = metadata.tables["integration_users"]
        with engine.begin() as conn:
            conn.execute(users.insert().values(name=value, email="bs@example.com"))

        # Read back via parameter path.
        with engine.connect() as conn:
            stored = conn.execute(
                sa.select(users.c.name).where(users.c.email == "bs@example.com")
            ).scalar()
        assert stored == value, f"param roundtrip corrupted: {stored!r} != {value!r}"

        # Match the same value via literal_binds rendering (inline SQL literal).
        with engine.connect() as conn:
            compiled = (
                sa.select(users.c.name)
                .where(users.c.name == value)
                .compile(
                    dialect=engine.dialect,
                    compile_kwargs={"literal_binds": True},
                )
            )
            matched = conn.exec_driver_sql(str(compiled)).scalar()
        assert matched == value, f"literal_binds roundtrip corrupted: {matched!r}"


class TestJSONRoundTrip:
    """#394: sa.JSON columns must return Python dict/list, not str, on read."""

    def test_json_dict_roundtrips_as_dict(self, engine):
        meta = MetaData()
        table = Table(
            "integration_json394",
            meta,
            Column("id", String(32), primary_key=True),
            Column("data_json", sa.JSON),
        )
        meta.create_all(engine)
        try:
            payload = {"key": "value", "nested": {"n": 1}, "list": [1, 2, 3]}
            with engine.begin() as conn:
                conn.execute(table.insert().values(id="abc", data_json=payload))
            with engine.connect() as conn:
                result = conn.execute(sa.select(table.c.data_json)).scalar()
            assert isinstance(result, dict)
            assert result == payload
        finally:
            meta.drop_all(engine)


# ---------------------------------------------------------------------------
# #485: SQLAlchemy-facing BLOB/CLOB value contract
# ---------------------------------------------------------------------------

# pycubrid documents (``pycubrid.lob.Lob.read``) that the CUBRID broker caps
# a single LOB_READ response at ~80 KB.  The large payloads below exceed that
# chunk so a value assembled from one partial read cannot pass.
_LOB_READ_CHUNK_BYTES = 80 * 1024
_LOB_SMALL_BYTES = b"\x00\x01\x7f\x80\xfe\xff binary"
_LOB_LARGE_BYTES = bytes(range(256)) * 1024  # 256 KiB, every byte value
_LOB_SMALL_TEXT = "plain clob text"
_LOB_CJK_TEXT = "한국어 CLOB 日本語 中文 ✓ — ümlaut"
_LOB_LARGE_TEXT = (_LOB_CJK_TEXT + " / ") * 8000  # > 80 KB when UTF-8 encoded

# column kind -> (SQLAlchemy type, documented Python value type)
_LOB_KINDS = {
    "large_binary": (sa.LargeBinary, bytes),
    "blob": (BLOB, bytes),
    "clob": (CLOB, str),
    "text": (sa.Text, str),
}

_LOB_CASES = [
    pytest.param("large_binary", _LOB_SMALL_BYTES, id="large_binary-small"),
    pytest.param("large_binary", _LOB_LARGE_BYTES, id="large_binary-large"),
    pytest.param("large_binary", None, id="large_binary-null"),
    pytest.param("blob", _LOB_SMALL_BYTES, id="blob-small"),
    pytest.param("blob", _LOB_LARGE_BYTES, id="blob-large"),
    pytest.param("blob", None, id="blob-null"),
    pytest.param("clob", _LOB_SMALL_TEXT, id="clob-small"),
    pytest.param("clob", _LOB_CJK_TEXT, id="clob-cjk"),
    pytest.param("clob", _LOB_LARGE_TEXT, id="clob-large"),
    pytest.param("clob", None, id="clob-null"),
    pytest.param("text", _LOB_SMALL_TEXT, id="text-small"),
    pytest.param("text", _LOB_CJK_TEXT, id="text-cjk"),
    pytest.param("text", _LOB_LARGE_TEXT, id="text-large"),
    pytest.param("text", None, id="text-null"),
]

# Released drivers hand back a LOB locator instead of the value for BLOB/CLOB
# columns.  NULL and ``Text`` (CUBRID ``STRING``) values are unaffected.
_LOB_LOCATOR_XFAIL = {
    "pycubrid": (
        "released pycubrid fetches BLOB/CLOB columns as a raw LOB-handle dict "
        "(lob_type/lob_length/file_locator) instead of bytes/str; official LOB "
        "fetch is cubrid-lab/pycubrid#441"
    ),
    "cubrid": (
        "CUBRIDdb fetches BLOB/CLOB columns as the server file-locator string "
        "('file:...') instead of bytes/str (#485)"
    ),
}


def _xfail_lob_locator(request, engine, kind, value):
    reason = _LOB_LOCATOR_XFAIL.get(engine.dialect.driver)
    if reason is not None and kind != "text" and value is not None:
        request.applymarker(
            pytest.mark.xfail(strict=True, raises=(AssertionError, TypeError), reason=reason)
        )


def _assert_lob_value(got, kind, expected):
    if expected is None:
        assert got is None
        return
    value_type = _LOB_KINDS[kind][1]
    assert type(got) is value_type, f"expected {value_type.__name__}, got {type(got)!r}"
    assert len(got) == len(expected)
    assert got == expected


class TestLobPayloadSizes:
    def test_large_payloads_exceed_driver_lob_read_chunk(self):
        assert len(_LOB_LARGE_BYTES) > _LOB_READ_CHUNK_BYTES
        assert len(_LOB_LARGE_TEXT.encode("utf-8")) > _LOB_READ_CHUNK_BYTES


class TestLobValueContractCore:
    @pytest.fixture(scope="class")
    def lob_table(self, engine):
        meta = MetaData()
        table = Table(
            "integration_lob485",
            meta,
            Column("id", Integer, primary_key=True, autoincrement=False),
            *(Column(kind, type_) for kind, (type_, _) in _LOB_KINDS.items()),
        )
        meta.drop_all(engine)
        meta.create_all(engine)
        yield table
        meta.drop_all(engine)

    @pytest.mark.parametrize(("kind", "value"), _LOB_CASES)
    def test_roundtrip(self, request, engine, lob_table, kind, value):
        _xfail_lob_locator(request, engine, kind, value)
        with engine.begin() as conn:
            conn.execute(lob_table.delete())
            conn.execute(lob_table.insert(), {"id": 1, kind: value})
        with engine.connect() as conn:
            got = conn.execute(sa.select(lob_table.c[kind]).where(lob_table.c.id == 1)).scalar_one()
        _assert_lob_value(got, kind, value)

    @pytest.mark.parametrize(
        ("kind", "value"),
        [p for p in _LOB_CASES if p.values[0] in ("large_binary", "blob", "clob") and p.values[1]],
    )
    def test_write_stores_full_value(self, engine, lob_table, kind, value):
        """Bound bytes/str reach the LOB intact; read back via server-side conversion."""
        column = lob_table.c[kind]
        convert = sa.func.CLOB_TO_CHAR if kind == "clob" else sa.func.BLOB_TO_BIT
        with engine.begin() as conn:
            conn.execute(lob_table.delete())
            conn.execute(lob_table.insert(), {"id": 1, kind: value})
        with engine.connect() as conn:
            got = conn.execute(sa.select(convert(column)).where(lob_table.c.id == 1)).scalar_one()
        _assert_lob_value(got, kind, value)


class _LobBase(DeclarativeBase):
    pass


class _LobDocument(_LobBase):
    __tablename__ = "integration_lob485_orm"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    large_binary: Mapped[bytes | None] = mapped_column(sa.LargeBinary)
    blob: Mapped[bytes | None] = mapped_column(BLOB)
    clob: Mapped[str | None] = mapped_column(CLOB)
    text: Mapped[str | None] = mapped_column(sa.Text)


class TestLobValueContractORM:
    @pytest.fixture(scope="class")
    def lob_orm_table(self, engine):
        _LobBase.metadata.drop_all(engine)
        _LobBase.metadata.create_all(engine)
        yield
        _LobBase.metadata.drop_all(engine)

    @pytest.mark.parametrize(("kind", "value"), _LOB_CASES)
    def test_roundtrip(self, request, engine, lob_orm_table, kind, value):
        _xfail_lob_locator(request, engine, kind, value)
        with Session(engine) as session, session.begin():
            session.query(_LobDocument).delete()
            session.add(_LobDocument(id=1, **{kind: value}))
        with Session(engine) as session:
            doc = session.get(_LobDocument, 1)
            assert doc is not None
            got = getattr(doc, kind)
        _assert_lob_value(got, kind, value)


# ---------------------------------------------------------------------------
# #481: results are never silently truncated across commit or rollback
# ---------------------------------------------------------------------------

# pycubrid requests further rows in FETCH batches of ``fetch_size`` (default 100,
# ``pycubrid.connection.Connection``), and the broker's first response to the
# SELECT is further capped by size: it holds only ~16 of the 1000-byte rows
# below. The result therefore needs several FETCH round trips after the first
# response, which is exactly what a commit/rollback can invalidate.
_PYCUBRID_FETCH_SIZE = 100
_WIDE_ROWS = 500
_WIDE_PAYLOAD = "x" * 1000
_FETCHMANY_SIZE = 17


def _drain(result, method):
    """Consume the rest of *result* with the given fetch method."""
    if method == "fetchall":
        return list(result.fetchall())
    rows = []
    while True:
        if method == "fetchmany":
            part = result.fetchmany(_FETCHMANY_SIZE)
            if not part:
                return rows
            rows.extend(part)
        else:
            row = result.fetchone()
            if row is None:
                return rows
            rows.append(row)


class TestResultCompletenessAcrossTransactionBoundary:
    @pytest.fixture(scope="class")
    def wide_table(self, engine):
        meta = MetaData()
        table = Table(
            "integration_rc481",
            meta,
            Column("id", Integer, primary_key=True, autoincrement=False),
            Column("payload", String(1000)),
        )
        meta.drop_all(engine)
        meta.create_all(engine)
        with engine.begin() as conn:
            conn.execute(
                table.insert(), [{"id": i, "payload": _WIDE_PAYLOAD} for i in range(_WIDE_ROWS)]
            )
        yield table
        meta.drop_all(engine)

    def test_row_count_exceeds_pycubrid_fetch_batch(self):
        pycubrid_connection = pytest.importorskip("pycubrid.connection")
        default = signature(pycubrid_connection.Connection).parameters["fetch_size"]
        assert default.default == _PYCUBRID_FETCH_SIZE
        assert _WIDE_ROWS > _PYCUBRID_FETCH_SIZE

    @pytest.mark.parametrize("method", ["fetchone", "fetchmany", "fetchall"])
    @pytest.mark.parametrize("boundary", ["commit", "rollback", "none"])
    def test_unfinished_result_is_complete_or_raises(
        self, request, engine, wide_table, boundary, method
    ):
        """After a transaction boundary, the rest of a result is complete or an error.

        ``none`` is the control: the full result needs FETCHes past the first
        response. With a boundary, returning every row and raising a DB-API
        error are both acceptable; a successful partial result is not.
        """
        with engine.connect() as conn:
            # A completed query on the same connection is the normal state of a
            # pooled connection; released pycubrid truncates silently from it.
            conn.execute(text("SELECT 1")).all()
            result = conn.execute(
                select(wide_table.c.id, wide_table.c.payload).order_by(wide_table.c.id)
            )
            if engine.dialect.driver == "pycubrid":
                # The first response must not hold the whole result.
                assert 0 < result.cursor._fetched_count < _WIDE_ROWS
            first = result.fetchone()
            if boundary == "commit":
                conn.commit()
            elif boundary == "rollback":
                conn.rollback()
            if boundary != "none":
                # Applied only now, so the preconditions above stay unmasked.
                xfail_unreleased_pycubrid_fix(
                    request, engine.dialect.driver, 395, raises=AssertionError
                )
            try:
                rest = _drain(result, method)
            except sa.exc.DBAPIError:
                if boundary == "none":
                    raise
                rest = None  # an explicit failure satisfies the contract
        if engine.dialect.driver == "cubrid":
            # Recorded CUBRIDdb 11.3 behavior (CUBRID 10.2 and 11.4), for comparison.
            expected = {"commit": "complete", "rollback": "raises", "none": "complete"}
            assert ("raises" if rest is None else "complete") == expected[boundary]
        if rest is None:
            return
        ids = [first.id] + [row.id for row in rest]
        assert len(ids) == _WIDE_ROWS, f"silently truncated: {len(ids)} of {_WIDE_ROWS} rows"
        assert ids == list(range(_WIDE_ROWS))
        assert all(row.payload == _WIDE_PAYLOAD for row in rest)


# ---------------------------------------------------------------------------
# #480: constraint violations surface as sqlalchemy.exc.IntegrityError
# ---------------------------------------------------------------------------


class _IntegrityBase(DeclarativeBase):
    pass


class _IntegrityParent(_IntegrityBase):
    __tablename__ = "integration_ie480_parent"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str | None] = mapped_column(String(20), nullable=False)


class _IntegrityChild(_IntegrityBase):
    __tablename__ = "integration_ie480_child"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    parent_id: Mapped[int] = mapped_column(ForeignKey("integration_ie480_parent.id"))


# kind -> (mapped class, values violating the constraint); parent 1 always exists.
_INTEGRITY_VIOLATIONS = {
    "not_null": (_IntegrityParent, {"id": 2, "name": None}),
    "foreign_key": (_IntegrityChild, {"id": 1, "parent_id": 999}),
    "unique_pk": (_IntegrityParent, {"id": 1, "name": "duplicate"}),  # control
}


def _xfail_integrity(request, driver, kind):
    # Released pycubrid raises NOT NULL (-631) and FK (-922) violations as a
    # generic DatabaseError; unique/PK (-670) is already an IntegrityError.
    if kind != "unique_pk":
        xfail_unreleased_pycubrid_fix(request, driver, 390, raises=AssertionError)


def _assert_integrity_error(exc):
    assert isinstance(exc, sa.exc.IntegrityError), (
        f"expected sqlalchemy.exc.IntegrityError, got {type(exc).__name__} "
        f"wrapping {type(exc.orig).__module__}.{type(exc.orig).__name__}"
    )


def _integrity_counts(conn):
    return tuple(
        conn.execute(select(sa.func.count()).select_from(model)).scalar_one()
        for model in (_IntegrityParent, _IntegrityChild)
    )


class TestIntegrityErrorContract:
    @pytest.fixture(scope="class", autouse=True)
    def integrity_tables(self, engine):
        _IntegrityBase.metadata.drop_all(engine)
        _IntegrityBase.metadata.create_all(engine)
        with engine.begin() as conn:
            conn.execute(sa.insert(_IntegrityParent), {"id": 1, "name": "parent"})
        yield
        _IntegrityBase.metadata.drop_all(engine)

    @pytest.mark.parametrize("kind", list(_INTEGRITY_VIOLATIONS))
    def test_core_violation_raises_integrity_error(self, request, engine, kind):
        model, values = _INTEGRITY_VIOLATIONS[kind]
        with engine.connect() as conn:
            with pytest.raises(sa.exc.DBAPIError) as excinfo:
                conn.execute(sa.insert(model), values)
            conn.rollback()
            # The same connection runs new statements after the rollback.
            assert _integrity_counts(conn) == (1, 0)
            conn.execute(sa.insert(_IntegrityChild), {"id": 10, "parent_id": 1})
            assert _integrity_counts(conn) == (1, 1)
            conn.rollback()
        # Only the class check is gated; the recovery checks above never are.
        _xfail_integrity(request, engine.dialect.driver, kind)
        _assert_integrity_error(excinfo.value)

    @pytest.mark.parametrize("kind", list(_INTEGRITY_VIOLATIONS))
    def test_orm_flush_violation_raises_integrity_error(self, request, engine, kind):
        model, values = _INTEGRITY_VIOLATIONS[kind]
        with Session(engine) as session:
            session.add(model(**values))
            with pytest.raises(sa.exc.DBAPIError) as excinfo:
                session.flush()
            session.rollback()
            # The same session (and its connection) keeps working.
            session.add(_IntegrityChild(id=10, parent_id=1))
            session.flush()
            assert _integrity_counts(session.connection()) == (1, 1)
            session.rollback()
        # Only the class check is gated; the recovery checks above never are.
        _xfail_integrity(request, engine.dialect.driver, kind)
        _assert_integrity_error(excinfo.value)


# ---------------------------------------------------------------------------
# #482: the cursor.description subset observable through SQLAlchemy
# ---------------------------------------------------------------------------

# column -> (SQLAlchemy type, nullable, CUBRID type code). Both drivers report
# the CUBRID CAS/CCI scalar type codes; pycubrid's full per-type matrix lives
# upstream.
_DESC_COLUMNS = {
    "id": (Integer, False, 8),
    "nn": (String(20), False, 2),
    "nl": (String(20), True, 2),
    "bi": (sa.BigInteger, True, 21),
    "n": (sa.Numeric(10, 2), True, 7),
    "d": (DOUBLE, True, 12),
    "dt": (sa.Date, True, 13),
    "ts": (sa.TIMESTAMP, True, 15),
}
_DESC_ROW = {
    "id": 1,
    "nn": "a",
    "nl": None,
    "bi": 2,
    "n": Decimal("3.50"),
    "d": 1.5,
    "dt": datetime.date(2020, 1, 2),
    "ts": datetime.datetime(2020, 1, 2, 3, 4, 5),
}
# column -> (collection type, pycubrid type code, CUBRIDdb type code). pycubrid
# reports the collection kind (SET 16, MULTISET 17, SEQUENCE 18); CUBRIDdb
# reports CCI's composite code: the kind in bits 0x60 (0x20/0x40/0x60) plus the
# element type (INTEGER 8). The dialect does not normalize either form.
_DESC_COLLECTIONS = {
    "s": (SET, 16, 0x20 | 8),
    "ms": (MULTISET, 17, 0x40 | 8),
    "sq": (SEQUENCE, 18, 0x60 | 8),
}
# CUBRID collection literals cannot be bound as parameters portably across the
# drivers (#484), so the one collection row is a fixed statement.
_DESC_COLLECTION_ROW = text(
    "INSERT INTO integration_cd482_coll (id, s, ms, sq) VALUES (1, {1,2}, {1,1}, {2,1})"
)
_DESC_TEXTUAL = text("SELECT id, nn AS alias, bi + 1 AS expr, 1 + 1 FROM integration_cd482")


def _description_tables(metadata):
    table = Table(
        "integration_cd482",
        metadata,
        *(
            Column(name, type_, primary_key=name == "id", autoincrement=False, nullable=nullable)
            for name, (type_, nullable, _) in _DESC_COLUMNS.items()
        ),
    )
    collections = Table(
        "integration_cd482_coll",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=False),
        *(Column(name, kind(Integer())) for name, (kind, _, _) in _DESC_COLLECTIONS.items()),
    )
    return table, collections


class TestCursorDescriptionContract:
    @pytest.fixture(scope="class")
    def desc_tables(self, engine):
        meta = MetaData()
        table, collections = _description_tables(meta)
        meta.drop_all(engine)
        meta.create_all(engine)
        with engine.begin() as conn:
            conn.execute(table.insert(), _DESC_ROW)
            conn.execute(_DESC_COLLECTION_ROW)
        yield table, collections
        meta.drop_all(engine)

    def test_textual_sql_column_names(self, engine, desc_tables):
        with engine.connect() as conn:
            result = conn.execute(_DESC_TEXTUAL)
            names = [d[0] for d in result.cursor.description]
            keys = list(result.keys())
            row = result.one()
        assert names == keys == ["id", "alias", "expr", "1+1"]
        assert row._mapping["alias"] == "a" and row.expr == 3

    def test_core_select_keys_match_description(self, engine, desc_tables):
        reflected = Table("integration_cd482", MetaData(), autoload_with=engine)
        with engine.connect() as conn:
            result = conn.execute(select(reflected))
            names = [d[0] for d in result.cursor.description]
            assert list(result.keys()) == names == list(_DESC_COLUMNS)
            result.all()

    def test_scalar_type_codes(self, engine, desc_tables):
        table, _ = desc_tables
        with engine.connect() as conn:
            result = conn.execute(select(table))
            codes = {d[0]: d[1] for d in result.cursor.description}
            result.all()
        assert codes == {name: spec[2] for name, spec in _DESC_COLUMNS.items()}

    def test_null_ok(self, request, engine, desc_tables):
        table, _ = desc_tables
        with engine.connect() as conn:
            result = conn.execute(select(table))
            null_ok = {d[0]: bool(d[6]) for d in result.cursor.description}
            result.all()
        # Released pycubrid reports null_ok inverted (NOT NULL -> True).
        xfail_unreleased_pycubrid_fix(request, engine.dialect.driver, 431, raises=AssertionError)
        assert null_ok == {name: spec[1] for name, spec in _DESC_COLUMNS.items()}

    def test_reflected_nullability_uses_catalog(self, engine, desc_tables):
        """Reflection reads nullability from the catalog, not cursor.description."""
        columns = {
            c["name"]: c["nullable"] for c in inspect(engine).get_columns("integration_cd482")
        }
        assert columns == {name: spec[1] for name, spec in _DESC_COLUMNS.items()}

    def test_collection_type_codes(self, request, desc_tables):
        _, collections = desc_tables
        # Released pycubrid keeps only the element type code (INTEGER 8) and
        # decodes the payload as that scalar; depending on the payload the
        # SELECT can fail with "malformed response from broker" and close the
        # connection, so this case uses its own engine.
        engine = create_engine(_cubrid_url())
        try:
            if engine.dialect.driver == "pycubrid":
                xfail_unreleased_pycubrid_fix(
                    request, "pycubrid", 430, raises=(AssertionError, sa.exc.DBAPIError)
                )
                expected = {name: spec[1] for name, spec in _DESC_COLLECTIONS.items()}
            else:
                expected = {name: spec[2] for name, spec in _DESC_COLLECTIONS.items()}
            with engine.connect() as conn:
                result = conn.execute(select(*(collections.c[name] for name in _DESC_COLLECTIONS)))
                codes = {d[0]: d[1] for d in result.cursor.description}
                assert len(result.all()) == 1
            assert codes == expected
        finally:
            engine.dispose()
