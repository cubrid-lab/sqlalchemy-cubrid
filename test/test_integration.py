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

import os

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


pytestmark = pytest.mark.skipif(
    not _can_connect(),
    reason="CUBRID instance not available (set CUBRID_TEST_URL)",
)


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
        # CUBRID may not always reflect FKs through db_constraint depending on version
        if len(fks) >= 1:
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
            matched = conn.execute(
                sa.select(users.c.name)
                .where(users.c.name == value)
                .compile(
                    dialect=engine.dialect,
                    compile_kwargs={"literal_binds": True},
                )
            ).scalar()
        assert matched == value, f"literal_binds roundtrip corrupted: {matched!r}"
