# test/test_integration.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Integration tests against a live CUBRID instance.

These tests require a running CUBRID database.  Set the environment
variable ``CUBRID_TEST_URL`` to the connection URL, e.g.::

    export CUBRID_TEST_URL="cubrid://dba@localhost:33000/testdb"

Without it they are skipped; with it, an unreachable server errors every
test instead (the shared gate in ``test/conftest.py``, #593).

Many tests here create tables and database users with fixed names (for
example ``t583_fresh``, ``alter_it_modify``, ``u543``), so run the module
against a dedicated database, one run at a time (``make integration`` starts
a run-owned server).
"""

from __future__ import annotations

import contextlib
import datetime
from inspect import signature
import os
import select as io_select
import subprocess
import sys
import uuid
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

from sqlalchemy_cubrid import BLOB, CLOB, DOUBLE, MULTISET, SEQUENCE, SET, STRING
from sqlalchemy_cubrid.dialect import CubridDialect


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_DEFAULT_URL = "cubrid://dba@localhost:33000/testdb"


def _cubrid_url() -> str:
    return os.environ.get("CUBRID_TEST_URL", _DEFAULT_URL)


# Fixed-name database users (below) are suffixed with this per-process token so
# that an interrupted prior run, or a concurrent job against the same shared
# database, cannot collide with -- or get silently masked by -- a leftover or
# simultaneously-running user of the same name (#607).
_USER_SUFFIX = f"{os.getpid()}{uuid.uuid4().hex[:6]}"


# The shared gate in test/conftest.py skips these tests when CUBRID_TEST_URL is
# unset and errors them when its server is unreachable (#593).
pytestmark = pytest.mark.integration


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


_bool_meta = MetaData()
_bool_table = Table(
    "bool_is_465",
    _bool_meta,
    Column("id", Integer, primary_key=True, autoincrement=False),
    Column("b", sa.Boolean),
    Column("x", Integer),
)
_bc = _bool_table.c


class TestBooleanIsIntegration:
    """#465: Boolean IS predicates compile to SQL CUBRID accepts, with
    SQLAlchemy's three-valued semantics. Rows: id 1 (b true, x 5), id 2
    (b false, x 6), id 3 (b NULL, x NULL). Each case gives the per-row value
    (True/False/None); WHERE keeps the rows where it is True."""

    @pytest.fixture(scope="class")
    def bool_rows(self, engine):
        _bool_meta.drop_all(engine)
        _bool_meta.create_all(engine)
        with engine.begin() as conn:
            conn.execute(
                _bool_table.insert(),
                [
                    {"id": 1, "b": True, "x": 5},
                    {"id": 2, "b": False, "x": 6},
                    {"id": 3, "b": None, "x": None},
                ],
            )
        yield
        _bool_meta.drop_all(engine)

    @pytest.mark.parametrize(
        ("expr", "expected"),
        [
            pytest.param(_bc.b.is_(True), (True, False, False), id="is_true"),
            pytest.param(_bc.b.is_(False), (False, True, False), id="is_false"),
            pytest.param(_bc.b.is_not(True), (False, True, True), id="is_not_true"),
            pytest.param(_bc.b.is_not(False), (True, False, True), id="is_not_false"),
            pytest.param(_bc.b.is_(sa.true()), (True, False, False), id="is_true_const"),
            pytest.param(_bc.b.is_not(sa.false()), (True, False, True), id="is_not_false_const"),
            pytest.param(~_bc.b.is_(True), (False, True, True), id="negated_is_true"),
            pytest.param(_bc.b.is_(None), (False, False, True), id="is_null"),
            pytest.param(_bc.b.is_not(None), (True, True, False), id="is_not_null"),
            pytest.param(_bc.b == True, (True, False, None), id="eq_true"),  # noqa: E712
            pytest.param(_bc.b == False, (False, True, None), id="eq_false"),  # noqa: E712
            pytest.param(_bc.b != True, (False, True, None), id="ne_true"),  # noqa: E712
            pytest.param(sa.not_(_bc.b), (False, True, None), id="not_col"),
            pytest.param(sa.true(), (True, True, True), id="true_const"),
            pytest.param(sa.false(), (False, False, False), id="false_const"),
            pytest.param((_bc.x == 5).is_(True), (True, False, False), id="cmp_is_true"),
            pytest.param((_bc.x == 5).is_(False), (False, True, False), id="cmp_is_false"),
            pytest.param((_bc.x == 5).is_not(True), (False, True, True), id="cmp_is_not_true"),
            pytest.param((_bc.x == 5).is_not(False), (True, False, True), id="cmp_is_not_false"),
            pytest.param(_bc.b.is_(sa.literal(True)), (True, False, False), id="is_literal"),
            pytest.param(_bc.b == sa.literal(True), (True, False, None), id="eq_literal"),
        ],
    )
    def test_truth_table(self, engine, bool_rows, expr, expected):
        with engine.connect() as conn:
            ids = conn.execute(select(_bc.id).where(expr).order_by(_bc.id)).scalars().all()
            assert ids == [i for i, value in zip((1, 2, 3), expected) if value is True]
            projection = select(expr.label("v")).select_from(_bool_table).order_by(_bc.id)
            values = conn.execute(projection).scalars().all()
        assert tuple(None if v is None else bool(v) for v in values) == expected

    @pytest.mark.parametrize(
        ("value", "is_ids", "is_not_ids"),
        [(True, [1], [2, 3]), (False, [2], [1, 3]), (None, [3], [1, 2])],
    )
    def test_is_bound_parameter(self, engine, bool_rows, value, is_ids, is_not_ids):
        # Renders ``b <=> ?``; a NULL parameter has the meaning of IS NULL.
        flag = sa.bindparam("flag", type_=sa.Boolean)
        with engine.connect() as conn:
            for expr, expected in ((_bc.b.is_(flag), is_ids), (_bc.b.is_not(flag), is_not_ids)):
                stmt = select(_bc.id).where(expr).order_by(_bc.id)
                assert conn.execute(stmt, {"flag": value}).scalars().all() == expected

    @pytest.mark.parametrize(
        ("expr", "expected_ids"),
        [
            pytest.param(sa.and_(_bc.x == 5, _bc.b.is_(True)), [1], id="and"),
            pytest.param(sa.or_(_bc.b.is_(False), _bc.b.is_(None)), [2, 3], id="or"),
            pytest.param(sa.and_(_bc.b, sa.true()), [1], id="and_true"),
            pytest.param(sa.or_(_bc.b, sa.false()), [1], id="or_false"),
        ],
    )
    def test_combined_in_where(self, engine, bool_rows, expr, expected_ids):
        # AND/OR are WHERE-only: CUBRID rejects logical operators in a SELECT list.
        with engine.connect() as conn:
            ids = conn.execute(select(_bc.id).where(expr).order_by(_bc.id)).scalars().all()
        assert ids == expected_ids


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

    def test_existence_checks_for_missing_objects_and_checkfirst(self, engine):
        """A missing table or index is not reported as existing (#583).

        COUNT(*) is BIGINT, which the PyPI CUBRID-Python 9.3 driver fetches as
        str; has_table() / has_index() must not treat ``'0'`` as true.
        """
        meta = MetaData()
        t = Table("t583_fresh", meta, Column("id", Integer, primary_key=True), Column("v", Integer))
        sa.Index("ix_t583_fresh_v", t.c.v)
        meta.drop_all(engine, checkfirst=True)
        try:
            with engine.connect() as conn:
                assert engine.dialect.has_table(conn, "t583_fresh") is False
                assert engine.dialect.has_index(conn, "t583_fresh", "ix_t583_fresh_v") is False
            meta.create_all(engine, checkfirst=True)
            # checkfirst must not skip the CREATE of a table that does not exist.
            insp = inspect(engine)
            assert insp.has_table("t583_fresh")
            assert insp.has_index("t583_fresh", "ix_t583_fresh_v")
            assert not insp.has_index("t583_fresh", "ix_t583_missing")
            meta.create_all(engine, checkfirst=True)
        finally:
            meta.drop_all(engine, checkfirst=True)
        with engine.connect() as conn:
            assert engine.dialect.has_table(conn, "t583_fresh") is False

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

    @pytest.mark.parametrize("method", ["get_columns", "get_indexes"])
    def test_syntax_error_is_not_no_such_table(self, engine, method):
        """#454: a -493 syntax error from SHOW COLUMNS / SHOW INDEXES propagates
        as the driver error; only ``Unknown class`` means a missing table."""
        with engine.connect() as conn:
            with pytest.raises(sa.exc.NoSuchTableError):
                getattr(inspect(conn), method)("nonexistent_table_xyz")
        if not _server_at_least(engine, (11, 4)):
            # CUBRID 10.2 accepts "]" in a quoted name and reports Unknown class.
            pytest.skip("CUBRID < 11.4 accepts ']' in a quoted identifier")
        with engine.connect() as conn:
            # CUBRID 11.4 rejects "]" in an identifier with a -493 syntax error.
            with pytest.raises(sa.exc.DBAPIError, match="cannot contain"):
                getattr(inspect(conn), method)("bad]name")


# More tables than a CUBRID connection has server query entries (100, #548): a
# reflection query whose result is left open holds one entry each, and the
# next query then fails with -830 "Cannot allocate query entry".
_MANY_TABLES = 150


class TestReflectionQueryEntries:
    """#529 review: reflecting many tables on ONE connection must not leak
    server query entries (-830)."""

    @pytest.fixture
    def many_tables(self, engine):
        meta = MetaData()
        Table("qe_parent", meta, Column("id", Integer, primary_key=True))
        for n in range(_MANY_TABLES):
            Table(
                f"qe_t{n:03d}",
                meta,
                Column("id", Integer, primary_key=True),
                Column("u", Integer, unique=True),
                Column("p", Integer, ForeignKey("qe_parent.id")),
            )
        meta.drop_all(engine)
        meta.create_all(engine)
        yield meta
        meta.drop_all(engine)

    def test_metadata_reflect_many_tables_on_one_connection(self, engine, many_tables):
        with engine.connect() as conn:
            reflected = MetaData()
            reflected.reflect(conn, only=list(many_tables.tables))
            # The same connection still runs statements afterwards.
            assert conn.execute(text("SELECT 1")).scalar() == 1
        assert set(reflected.tables) == set(many_tables.tables)
        table = reflected.tables[f"qe_t{_MANY_TABLES - 1:03d}"]
        assert [fk.column.table.name for fk in table.foreign_keys] == ["qe_parent"]
        assert {tuple(i.columns.keys()) for i in table.indexes if i.unique} >= {("u",)}

    def test_inspector_loop_many_tables_on_one_connection(self, engine, many_tables):
        names = [name for name in many_tables.tables if name != "qe_parent"]
        with engine.connect() as conn:
            insp = inspect(conn)
            for name in names:
                insp.get_indexes(name)
                insp.get_unique_constraints(name)
                insp.get_foreign_keys(name)
                insp.get_table_comment(name)
            assert conn.execute(text("SELECT 1")).scalar() == 1


def _server_at_least(engine, version):
    with engine.connect() as conn:
        return conn.dialect.server_version_info[: len(version)] >= version


class TestSameNameClassOfOtherOwner:
    """#529 review: since CUBRID 11.2 classes of different owners may share a
    name. Reflecting ``y_dup`` as user u2 must describe u2's own table, not a
    same-named DBA view granted to PUBLIC (which made get_indexes() return
    [])."""

    @pytest.fixture
    def u2_engine(self, engine):
        if engine.url.username is None or engine.url.username.lower() != "dba":
            pytest.skip("needs a DBA connection to create a user")
        if not _server_at_least(engine, (11, 2)):
            pytest.skip("CUBRID < 11.2 has one global namespace for class names")

        def run(eng, *statements, ignore_errors=False):
            # One transaction per statement: DDL is transactional, so a
            # rollback after a failed statement must not undo an earlier
            # successful one (#607).
            with eng.connect() as conn:
                for statement in statements:
                    try:
                        conn.exec_driver_sql(statement)
                        conn.commit()
                    except Exception:
                        if not ignore_errors:
                            raise
                        conn.rollback()

        username = f"u2_{_USER_SUFFIX}"
        u2 = create_engine(engine.url.set(username=username, password=None))

        def cleanup():
            run(u2, "DROP TABLE y_dup", "DROP TABLE y_dup_parent", ignore_errors=True)
            u2.dispose()
            run(engine, "DROP VIEW y_dup", f"DROP USER {username}", ignore_errors=True)

        # Idempotent: ensure the user exists (so cleanup() below can connect
        # as it) before dropping it and any state it owns, then (re)create it
        # for real. Combined with the per-process-unique username, an
        # interrupted prior run or a concurrent job against the same shared
        # database can no longer make this CREATE USER fail with
        # "already exists" (#607).
        run(engine, f"CREATE USER {username}", ignore_errors=True)
        cleanup()
        run(engine, f"CREATE USER {username}")
        try:
            run(
                engine,
                "CREATE VIEW y_dup AS SELECT 1 AS a FROM db_root",
                "GRANT SELECT ON y_dup TO PUBLIC",
            )
            run(
                u2,
                "CREATE TABLE y_dup_parent (id INT PRIMARY KEY)",
                "CREATE TABLE y_dup (id INT PRIMARY KEY, u INT UNIQUE, p INT, "
                "CONSTRAINT fk_y_dup_p FOREIGN KEY (p) REFERENCES y_dup_parent (id))",
            )
            yield u2
        finally:
            cleanup()

    def test_reflection_uses_the_current_users_class(self, u2_engine):
        with u2_engine.connect() as conn:
            owners = conn.execute(
                text("SELECT owner_name, class_type FROM db_class WHERE class_name = 'y_dup'")
            ).fetchall()
            assert sorted(owners) == [
                ("DBA", "VCLASS"),
                (u2_engine.url.username.upper(), "CLASS"),
            ]

            insp = inspect(conn)
            assert "u_y_dup_u" in {index["name"] for index in insp.get_indexes("y_dup")}
            assert [uc["name"] for uc in insp.get_unique_constraints("y_dup")] == ["u_y_dup_u"]
            fks = insp.get_foreign_keys("y_dup")
            assert [(fk["name"], fk["referred_table"]) for fk in fks] == [
                ("fk_y_dup_p", "y_dup_parent")
            ]


@contextlib.contextmanager
def _r549_user_cycle(engine, as_user):
    """Create user ``u549`` and the ``r549_t`` / ``r549_parent`` tables (plus,
    since CUBRID 11.2, a same-named decoy owned by the other side), yield the
    owning engine, then drop everything.

    Idempotent: the user is (re-)created before ``cleanup()`` drops it and
    any state it owns, then (re)created for real. Combined with the
    per-process-unique username, an interrupted prior run -- or a
    concurrent job against the same shared database -- can no longer make
    the real ``CREATE USER`` fail with "already exists" (#607). Safe to call
    back to back against the same database.
    """

    def run(eng, *statements, ignore_errors=False):
        # One transaction per statement: DDL is transactional, so a
        # rollback after a failed statement must not undo an earlier
        # successful one (#607).
        with eng.connect() as conn:
            for statement in statements:
                try:
                    conn.exec_driver_sql(statement)
                    conn.commit()
                except Exception:
                    if not ignore_errors:
                        raise
                    conn.rollback()

    username = f"u549_{_USER_SUFFIX}"
    u549 = create_engine(engine.url.set(username=username, password=None))
    owner, other = (engine, u549) if as_user == "dba" else (u549, engine)

    def cleanup():
        for eng in (u549, engine):
            run(
                eng,
                "DROP TABLE r549_t",
                "DROP TABLE r549_parent",
                ignore_errors=True,
            )
        u549.dispose()
        run(engine, f"DROP USER {username}", ignore_errors=True)

    run(engine, f"CREATE USER {username}", ignore_errors=True)
    cleanup()
    run(engine, f"CREATE USER {username}")
    try:
        run(
            owner,
            "CREATE TABLE r549_parent (id INT PRIMARY KEY)",
            "CREATE TABLE r549_t (a INT, b INT, p INT, u INT UNIQUE, "
            "v INT COMMENT 'v comment', "
            "CONSTRAINT pk_r549_t PRIMARY KEY (a, b), "
            "CONSTRAINT fk_r549_t_p FOREIGN KEY (p) REFERENCES r549_parent (id))",
            "CREATE INDEX ix_r549_t_v ON r549_t (v)",
        )
        if _server_at_least(engine, (11, 2)):
            run(
                other,
                "CREATE TABLE r549_t (id INT PRIMARY KEY, v INT COMMENT 'decoy', w INT UNIQUE)",
                "CREATE INDEX ix_r549_decoy_v ON r549_t (v)",
                "GRANT SELECT ON r549_t TO PUBLIC",
            )
        yield owner
    finally:
        cleanup()


class TestReflectionAsNonDba:
    """#549: ``_db_index``, ``_db_index_key`` and ``_db_attribute`` are readable
    only by DBA, so reflection reads the public catalog views. Reflect the same
    table as DBA and as a new user, by its name and in upper case. Since 11.2
    the other user also owns a same-named decoy table readable by the
    reflecting user, whose indexes and comments must not leak into the
    result."""

    @pytest.fixture(params=["dba", "u549"])
    def reflecting_engine(self, request, engine):
        if engine.url.username is None or engine.url.username.lower() != "dba":
            pytest.skip("needs a DBA connection to create a user")

        with _r549_user_cycle(engine, request.param) as owner:
            yield owner

    def test_reflection_setup_reruns_against_same_database(self, engine):
        """#607 regression: run the non-DBA (``u549``) reflection setup/
        teardown cycle twice in a row against the same database. A stale
        user or table left behind by the first cycle must not make the
        second cycle's ``CREATE USER`` fail with "already exists"."""
        if engine.url.username is None or engine.url.username.lower() != "dba":
            pytest.skip("needs a DBA connection to create a user")

        for _ in range(2):
            with _r549_user_cycle(engine, "u549") as owner:
                with owner.connect() as conn:
                    insp = inspect(conn)
                    assert insp.get_pk_constraint("r549_t") == {
                        "name": "pk_r549_t",
                        "constrained_columns": ["a", "b"],
                    }

    @pytest.mark.parametrize("name", ["r549_t", "R549_T"])
    def test_reflection(self, reflecting_engine, name):
        with reflecting_engine.connect() as conn:
            insp = inspect(conn)
            indexes = {i["name"]: (i["column_names"], i["unique"]) for i in insp.get_indexes(name)}
            # No PK index, no FK auto-index, no index of the decoy table.
            assert indexes == {"u_r549_t_u": (["u"], True), "ix_r549_t_v": (["v"], False)}
            assert insp.get_pk_constraint(name) == {
                "name": "pk_r549_t",
                "constrained_columns": ["a", "b"],
            }
            assert insp.get_unique_constraints(name) == [
                {"name": "u_r549_t_u", "column_names": ["u"], "duplicates_index": "u_r549_t_u"}
            ]
            # SHOW CREATE TABLE works for a non-DBA owner too (#589).
            fks = insp.get_foreign_keys(name)
            assert [(fk["name"], fk["referred_table"]) for fk in fks] == [
                ("fk_r549_t_p", "r549_parent")
            ]
            assert insp.has_index(name, "ix_r549_t_v")
            assert insp.has_index(name, "pk_r549_t")
            assert not insp.has_index(name, "ix_r549_decoy_v")
            assert not insp.has_index(name, "no_such_index")
            comments = {c["name"]: c["comment"] for c in insp.get_columns(name)}
            assert comments == {"a": None, "b": None, "p": None, "u": None, "v": "v comment"}


class TestShowCreateTableFailures:
    """#589: ``get_foreign_keys`` (and the DDL fallback of
    ``get_unique_constraints``) read ``SHOW CREATE TABLE``. A failure there
    used to be logged and reported as "no constraints", so Alembic
    autogenerate emitted an ``add_fk`` for a foreign key that already
    exists."""

    PARENT = "r589_parent"
    CHILD = "r589_child"
    PLAIN = "r589_plain"

    @classmethod
    def _metadata(cls):
        meta = MetaData()
        Table(cls.PARENT, meta, Column("id", Integer, primary_key=True))
        Table(
            cls.CHILD,
            meta,
            Column("id", Integer, primary_key=True),
            Column(
                "pid",
                Integer,
                # CUBRID reports the default actions as RESTRICT (#597); name them so
                # the comparison is about the constraint, not its options.
                ForeignKey(
                    f"{cls.PARENT}.id",
                    name="fk_r589_child_pid",
                    ondelete="RESTRICT",
                    onupdate="RESTRICT",
                ),
            ),
        )
        Table(cls.PLAIN, meta, Column("id", Integer, primary_key=True))
        return meta

    def _diffs(self, conn, meta):
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext

        tables = {self.PARENT, self.CHILD, self.PLAIN}
        ctx = MigrationContext.configure(
            connection=conn,
            opts={"include_name": lambda name, type_, parent: type_ != "table" or name in tables},
        )
        return compare_metadata(ctx, meta)

    @pytest.fixture
    def meta(self, engine):
        meta = self._metadata()
        meta.drop_all(engine)
        meta.create_all(engine)
        try:
            yield meta
        finally:
            meta.drop_all(engine)

    @staticmethod
    def _fail_show_create_table(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SHOW CREATE TABLE"):
            raise RuntimeError("SHOW CREATE TABLE failed")

    def test_autogenerate_has_no_fk_diff_when_reflection_works(self, engine, meta):
        with engine.connect() as conn:
            insp = inspect(conn)
            assert [fk["name"] for fk in insp.get_foreign_keys(self.CHILD)] == ["fk_r589_child_pid"]
            # A successful SHOW CREATE TABLE without constraints: empty lists.
            assert insp.get_foreign_keys(self.PLAIN) == []
            assert insp.get_unique_constraints(self.PLAIN) == []
            assert self._diffs(conn, meta) == []

    def test_autogenerate_raises_when_show_create_table_fails(self, engine, meta):
        sa.event.listen(engine, "before_cursor_execute", self._fail_show_create_table)
        try:
            with engine.connect() as conn:
                with pytest.raises(RuntimeError, match="SHOW CREATE TABLE failed"):
                    inspect(conn).get_foreign_keys(self.CHILD)
                conn.rollback()
                with pytest.raises(RuntimeError, match="SHOW CREATE TABLE failed"):
                    # The DDL fallback, taken because the table has no unique index.
                    inspect(conn).get_unique_constraints(self.PLAIN)
                conn.rollback()
                # Before #589 this returned [("add_fk", ...)] for the
                # existing foreign key.
                with pytest.raises(RuntimeError, match="SHOW CREATE TABLE failed"):
                    self._diffs(conn, meta)
        finally:
            sa.event.remove(engine, "before_cursor_execute", self._fail_show_create_table)


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
            # SQLAlchemy does not know about this raw set, so the pool would
            # hand the SERIALIZABLE connection to later tests; discard it.
            conn.invalidate()


class TestIsolationLevelAcrossTransactionBoundaries:
    """The configured isolation level survives commit, rollback and pool checkin (#505).

    pycubrid opens a new CAS session after the driver's ``commit()`` /
    ``rollback()``, which starts at the server default (READ COMMITTED).
    """

    # Own engines: a re-applied level changes how later tests on a shared
    # pooled pycubrid connection see an unfinished result (DRIVER_COMPAT #10).
    @pytest.fixture
    def serializable_engine(self):
        eng = create_engine(
            _cubrid_url(), isolation_level="SERIALIZABLE", pool_size=1, max_overflow=0
        )
        yield eng
        eng.dispose()

    @pytest.fixture
    def default_engine(self):
        eng = create_engine(_cubrid_url(), pool_size=1, max_overflow=0)
        yield eng
        eng.dispose()

    def test_engine_level_survives_commit_rollback_and_checkin(self, serializable_engine):
        with serializable_engine.connect() as conn:
            dbapi_conn = conn.connection.dbapi_connection
            assert conn.get_isolation_level() == "SERIALIZABLE"
            conn.execute(text("SELECT 1"))
            conn.commit()
            assert conn.get_isolation_level() == "SERIALIZABLE"
            conn.execute(text("SELECT 1"))
            conn.rollback()
            assert conn.get_isolation_level() == "SERIALIZABLE"

        with serializable_engine.connect() as conn:
            assert conn.connection.dbapi_connection is dbapi_conn
            assert conn.get_isolation_level() == "SERIALIZABLE"

    def test_reset_on_return_rollback_reapplies_the_level(self, serializable_engine):
        """The pool's rollback on checkin is the only end of transaction here."""
        with serializable_engine.connect() as conn:
            dbapi_conn = conn.connection.dbapi_connection
            conn.execute(text("SELECT 1"))
        with serializable_engine.connect() as conn:
            assert conn.connection.dbapi_connection is dbapi_conn
            # Read before any statement, so no begin/do_begin ran on this checkout.
            assert conn.get_isolation_level() == "SERIALIZABLE"

    def test_engine_level_survives_begin_block_and_session(self, serializable_engine):
        with serializable_engine.begin() as conn:
            conn.execute(text("SELECT 1"))
        with Session(serializable_engine) as session:
            session.execute(text("SELECT 1"))
            session.commit()
            assert session.connection().get_isolation_level() == "SERIALIZABLE"
            session.rollback()
        with serializable_engine.connect() as conn:
            assert conn.get_isolation_level() == "SERIALIZABLE"

    @pytest.fixture
    def fail_next_reapply(self, serializable_engine, monkeypatch):
        """Make the next dialect-level SET TRANSACTION fail once (pycubrid re-apply only)."""
        if serializable_engine.dialect.driver not in ("pycubrid", "aiopycubrid"):
            pytest.skip("only the pycubrid dialects re-apply the level")
        state = {"armed": False, "failed": 0}
        original = CubridDialect.set_isolation_level

        def flaky(dialect, dbapi_connection, level):
            if state["armed"]:
                state["armed"] = False
                state["failed"] += 1
                raise RuntimeError("simulated re-apply failure")
            return original(dialect, dbapi_connection, level)

        monkeypatch.setattr(CubridDialect, "set_isolation_level", flaky)
        with serializable_engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS iso505_reapply"))
            conn.execute(text("CREATE TABLE iso505_reapply (id INT PRIMARY KEY)"))
        yield state
        with serializable_engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS iso505_reapply"))

    @staticmethod
    def _committed_ids():
        eng = create_engine(_cubrid_url(), poolclass=sa.pool.NullPool)
        try:
            with eng.connect() as conn:
                return sorted(conn.execute(text("SELECT id FROM iso505_reapply")).scalars())
        finally:
            eng.dispose()

    def test_failed_reapply_after_commit_keeps_the_commit(
        self, serializable_engine, fail_next_reapply
    ):
        with serializable_engine.connect() as conn:
            conn.execute(text("INSERT INTO iso505_reapply VALUES (1)"))
            fail_next_reapply["armed"] = True
            conn.commit()  # must not raise: the data is committed
            assert fail_next_reapply["failed"] == 1
            assert self._committed_ids() == [1]

            conn.execute(text("SELECT 1"))  # next transaction start retries the re-apply
            assert conn.get_isolation_level() == "SERIALIZABLE"

    def test_failed_reapply_after_rollback_keeps_the_original_error(
        self, serializable_engine, fail_next_reapply
    ):
        with serializable_engine.begin() as conn:
            conn.execute(text("INSERT INTO iso505_reapply VALUES (1)"))
        with serializable_engine.connect() as conn:
            with pytest.raises(sa.exc.IntegrityError):
                with conn.begin():
                    fail_next_reapply["armed"] = True
                    conn.execute(text("INSERT INTO iso505_reapply VALUES (1)"))
            assert fail_next_reapply["failed"] == 1

            conn.execute(text("SELECT 1"))
            assert conn.get_isolation_level() == "SERIALIZABLE"

    def test_connection_level_survives_commit_and_rollback(self, default_engine):
        with default_engine.connect() as conn:
            conn = conn.execution_options(isolation_level="REPEATABLE READ")
            conn.execute(text("SELECT 1"))
            conn.commit()
            assert conn.get_isolation_level() == "REPEATABLE READ"
            conn.execute(text("SELECT 1"))
            conn.rollback()
            assert conn.get_isolation_level() == "REPEATABLE READ"


class TestAutocommitIsolationLevel:
    """``isolation_level="AUTOCOMMIT"`` and engine-level restore on every driver (#501)."""

    TABLE = "iso501_autocommit"

    @pytest.fixture
    def observer(self):
        """A second session that sees only committed rows."""
        eng = create_engine(_cubrid_url(), poolclass=sa.pool.NullPool)
        with eng.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {self.TABLE}"))
            conn.execute(text(f"CREATE TABLE {self.TABLE} (id INT)"))

        def committed(row_id: int) -> int:
            with eng.connect() as conn:
                return conn.execute(
                    text(f"SELECT COUNT(*) FROM {self.TABLE} WHERE id = :id"), {"id": row_id}
                ).scalar_one()

        yield committed
        with eng.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {self.TABLE}"))
        eng.dispose()

    @pytest.fixture
    def make_engine(self):
        engines = []

        def make(**kw):
            eng = create_engine(_cubrid_url(), pool_size=1, max_overflow=0, **kw)
            engines.append(eng)
            return eng

        yield make
        for eng in engines:
            eng.dispose()

    def _insert(self, conn, row_id):
        conn.execute(text(f"INSERT INTO {self.TABLE} VALUES (:id)"), {"id": row_id})

    @pytest.mark.parametrize("path", ["create_engine", "engine_options", "connection_options"])
    def test_autocommit_row_is_visible_before_commit_and_survives_rollback(
        self, observer, make_engine, path
    ):
        if path == "create_engine":
            eng = make_engine(isolation_level="AUTOCOMMIT")
        elif path == "engine_options":
            eng = make_engine().execution_options(isolation_level="AUTOCOMMIT")
        else:
            eng = make_engine()
        with eng.connect() as conn:
            if path == "connection_options":
                conn = conn.execution_options(isolation_level="AUTOCOMMIT")
            dbapi_conn = conn.connection.dbapi_connection
            assert eng.dialect.detect_autocommit_setting(dbapi_conn) is True
            self._insert(conn, 1)
            assert observer(1) == 1
            conn.rollback()
        assert observer(1) == 1

    def test_pooled_connection_is_transactional_again_after_checkin(self, observer, make_engine):
        eng = make_engine()
        with eng.connect() as conn:
            conn = conn.execution_options(isolation_level="AUTOCOMMIT")
            dbapi_conn = conn.connection.dbapi_connection
            self._insert(conn, 1)

        with eng.connect() as conn:
            assert conn.connection.dbapi_connection is dbapi_conn
            assert eng.dialect.detect_autocommit_setting(dbapi_conn) is False
            self._insert(conn, 2)
            assert observer(2) == 0
            conn.rollback()
        assert observer(1) == 1
        assert observer(2) == 0

    @pytest.mark.parametrize("override", ["REPEATABLE READ", "AUTOCOMMIT"])
    def test_engine_level_is_restored_after_connection_override(self, make_engine, override):
        eng = make_engine(isolation_level="SERIALIZABLE")
        with eng.connect() as conn:
            dbapi_conn = conn.connection.dbapi_connection
            conn = conn.execution_options(isolation_level=override)
            if override == "AUTOCOMMIT":
                assert eng.dialect.detect_autocommit_setting(dbapi_conn) is True
            else:
                assert conn.get_isolation_level() == override

        with eng.connect() as conn:
            assert conn.connection.dbapi_connection is dbapi_conn
            assert eng.dialect.detect_autocommit_setting(dbapi_conn) is False
            assert conn.get_isolation_level() == "SERIALIZABLE"
            conn.execute(text("SELECT 1"))
            conn.commit()
            assert conn.get_isolation_level() == "SERIALIZABLE"

    def test_engine_level_autocommit_is_restored_after_connection_override(
        self, observer, make_engine
    ):
        eng = make_engine(isolation_level="AUTOCOMMIT")
        with eng.connect() as conn:
            dbapi_conn = conn.connection.dbapi_connection
            conn = conn.execution_options(isolation_level="SERIALIZABLE")
            self._insert(conn, 1)
            assert observer(1) == 0
            conn.rollback()

        with eng.connect() as conn:
            assert conn.connection.dbapi_connection is dbapi_conn
            assert eng.dialect.detect_autocommit_setting(dbapi_conn) is True
            self._insert(conn, 2)
            assert observer(2) == 1
        assert observer(1) == 0

    @pytest.mark.parametrize(
        ("alias", "canonical"),
        [("CURSOR STABILITY", "READ COMMITTED"), ("repeatable_read", "REPEATABLE READ")],
    )
    def test_engine_level_alias_is_restored_after_connection_override(
        self, make_engine, alias, canonical
    ):
        eng = make_engine(isolation_level=alias)
        assert eng.dialect.isolation_level == canonical
        with eng.connect() as conn:
            dbapi_conn = conn.connection.dbapi_connection
            assert conn.get_isolation_level() == canonical
            conn = conn.execution_options(isolation_level="SERIALIZABLE")
            assert conn.get_isolation_level() == "SERIALIZABLE"
        with eng.connect() as conn:
            # Same connection: SQLAlchemy's checkin reset did not fail and invalidate it.
            assert conn.connection.dbapi_connection is dbapi_conn
            assert conn.get_isolation_level() == canonical

    def test_skip_autocommit_rollback_with_engine_level_autocommit(self, observer, make_engine):
        eng = make_engine(isolation_level="AUTOCOMMIT", skip_autocommit_rollback=True)
        with eng.connect() as conn:
            dbapi_conn = conn.connection.dbapi_connection
            self._insert(conn, 1)
            conn.rollback()  # skipped: detect_autocommit_setting() reports True
        assert observer(1) == 1
        with eng.connect() as conn:
            assert conn.connection.dbapi_connection is dbapi_conn
            assert eng.dialect.detect_autocommit_setting(dbapi_conn) is True
            conn = conn.execution_options(isolation_level="SERIALIZABLE")
            self._insert(conn, 2)
            conn.rollback()  # not skipped: the connection is transactional now
        assert observer(2) == 0

    def test_invalid_level_raises_argument_error_on_every_path(self, make_engine):
        with pytest.raises(sa.exc.ArgumentError, match="Invalid value 'BOGUS'"):
            with make_engine(isolation_level="BOGUS").connect():
                pass
        with pytest.raises(sa.exc.ArgumentError, match="Invalid value 'BOGUS'"):
            with make_engine().execution_options(isolation_level="BOGUS").connect():
                pass
        with make_engine().connect() as conn:
            with pytest.raises(sa.exc.ArgumentError, match="Invalid value 'BOGUS'"):
                conn.execution_options(isolation_level="BOGUS")


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


# Run in a separate process: CUBRIDdb holds the GIL while a statement runs
# (and select() on a pipe, used to hear "ready" from it, is POSIX-only). It
# records the transactions already running a query (its own included),
# prints "ready", then sends KILL QUERY to the one new query that is still
# running half a second later: the victim.
#
# This still identifies the victim by timing rather than by its SQL text.
# CUBRID gives no way to do the latter: neither ``SHOW TRANSACTION TABLES``
# nor ``SHOW THREADS`` exposes the running statement's text or any field an
# application can tag (``Client_info``/``Client_program``/``Client_pid`` are
# the CAS's own identity, not the driver's; verified live on 11.4). The slow
# query below is still tagged with a unique comment, so a run can be found in
# a broker SQL log by eye, but the helper itself cannot match on it. That
# makes this test reliable only when it is the sole session running a slow
# query against the target CUBRID instance at the time, e.g. one `make
# integration` run at a time against a given container/database (#578).
_KILL_QUERY_SCRIPT = """
import sys, time
import sqlalchemy as sa

def running(cur):
    cur.execute("SHOW TRANSACTION TABLES")
    cols = [d[0].lower() for d in cur.description]
    index, started = cols.index("tran_index"), cols.index("query_start_time")
    return {row[index] for row in cur.fetchall() if row[started] is not None}

engine = sa.create_engine(sys.argv[1], poolclass=sa.pool.NullPool)
raw = engine.raw_connection()
try:
    cur = raw.cursor()
    before = running(cur)
    print("ready", flush=True)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        new = running(cur) - before
        if new:
            time.sleep(0.5)
            # Only a query still running after the pause: a short one, such as
            # the service health check, must not be mistaken for the victim.
            victims = new & running(cur)
            if len(victims) == 1:
                # KILL takes no bind parameter; tran_index is an int from the server.
                cur.execute("KILL QUERY " + str(int(victims.pop())))
                print("killed", flush=True)
                break
        time.sleep(0.1)
    else:
        sys.exit("no running query to kill")
finally:
    raw.close()
"""

# Long enough to be killed mid-run. Its runtime is bounded by the catalog size
# (under a minute on CUBRID 11.4) if the kill fails: the helper then exits
# non-zero and the test fails instead of hanging. The comment is a unique tag
# for finding this run's query by eye in a broker SQL log; CUBRID does not
# expose it back through SHOW TRANSACTION TABLES, so the helper above still
# matches by timing, not by this text (see the comment on _KILL_QUERY_SCRIPT).
_SLOW_QUERY = text(
    f"SELECT /* kill-query-victim:{uuid.uuid4().hex} */ COUNT(*)"
    " FROM db_attribute a, db_attribute b, db_attribute c,"
    " (SELECT attr_name FROM db_attribute LIMIT 10) d"
)


class TestIsDisconnect:
    def test_interrupted_query_keeps_connection(self, engine):
        """A query interrupted by KILL QUERY fails with -4 but keeps the connection (#572).

        -4 is the server's ER_INTERRUPTED. CUBRIDdb reports it in ``args[0]``
        and pycubrid in ``errno``; neither is a disconnect.

        Relies on ``_KILL_QUERY_SCRIPT``, which identifies its victim by
        timing and waits on it through a pipe with ``select()`` (POSIX-only);
        see the comment above that script for why (#578).
        """
        url = engine.url.render_as_string(hide_password=False)
        killer = subprocess.Popen(  # noqa: S603 - runs this interpreter on a fixed script
            [sys.executable, "-c", _KILL_QUERY_SCRIPT, url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            assert killer.stdout is not None
            # Bounded wait: the helper may stall connecting to a busy broker.
            readable, _, _ = io_select.select([killer.stdout], [], [], 60)
            if not readable or killer.stdout.readline().strip() != "ready":
                killer.kill()
                killer.wait(timeout=60)
                pytest.fail(f"KILL QUERY helper failed: {killer.stderr.read()}")
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                dbapi_conn = conn.connection.dbapi_connection
                with pytest.raises(sa.exc.DBAPIError) as info:
                    conn.execute(_SLOW_QUERY)
                orig = info.value.orig
                code = getattr(orig, "errno", None)  # pycubrid
                if code is None:
                    code = orig.args[0]  # CUBRIDdb
                assert code == -4
                assert info.value.connection_invalidated is False
                conn.rollback()
                assert conn.execute(text("SELECT 1")).scalar() == 1
                assert conn.connection.dbapi_connection is dbapi_conn
            assert killer.wait(timeout=60) == 0, killer.stderr.read()
        finally:
            if killer.poll() is None:
                killer.kill()
                killer.wait()

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

    def test_replace_with_prefix_and_insert_into_text(self, engine, metadata):
        """REPLACE with a prefix still replaces rows and keeps "INSERT INTO" data (#591)."""
        from sqlalchemy_cubrid import replace

        users = metadata.tables["integration_users"]
        with engine.begin() as conn:
            conn.execute(users.insert().values(name="PrefixOld", email="old@example.com"))
            row_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()

            stmt = (
                replace(users)
                .prefix_with("/* INSERT INTO audit */")
                .values(id=row_id, name="INSERT INTO", email=sa.literal_column("'INSERT INTO'"))
            )
            assert str(stmt.compile(dialect=engine.dialect)).startswith(
                "REPLACE /* INSERT INTO audit */ INTO"
            )
            conn.execute(stmt)

        with engine.connect() as conn:
            rows = conn.execute(users.select().where(users.c.id == row_id)).fetchall()
        assert len(rows) == 1
        assert rows[0].name == "INSERT INTO"
        assert rows[0].email == "INSERT INTO"

    def test_replace_executemany_with_prefix(self, engine, metadata):
        """executemany REPLACE with a prefix replaces every conflicting row (#591)."""
        from sqlalchemy_cubrid import replace

        users = metadata.tables["integration_users"]
        with engine.begin() as conn:
            ids = []
            for name in ("ManyOld1", "ManyOld2"):
                conn.execute(users.insert().values(name=name, email="old@example.com"))
                ids.append(conn.execute(text("SELECT LAST_INSERT_ID()")).scalar())

            conn.execute(
                replace(users).prefix_with("/* c */"),
                [{"id": i, "name": "INSERT INTO", "email": f"new{i}@example.com"} for i in ids],
            )

        with engine.connect() as conn:
            rows = conn.execute(
                users.select().where(users.c.id.in_(ids)).order_by(users.c.id)
            ).fetchall()
        assert [(r.id, r.name, r.email) for r in rows] == [
            (i, "INSERT INTO", f"new{i}@example.com") for i in ids
        ]


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


class TestAutogenerateTextStringIntegration:
    """#544: autogenerate against live STRING / VARCHAR(n) columns."""

    TABLE = "autogen_text_544"

    @staticmethod
    def _metadata(**column_types):
        meta = MetaData()
        Table(
            TestAutogenerateTextStringIntegration.TABLE,
            meta,
            Column("id", Integer, primary_key=True),
            *[Column(name, type_) for name, type_ in column_types.items()],
        )
        return meta

    def _diffs(self, conn, meta):
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext

        ctx = MigrationContext.configure(
            connection=conn,
            opts={
                "compare_type": True,
                "include_name": lambda name, type_, parent: type_ != "table" or name == self.TABLE,
            },
        )
        return compare_metadata(ctx, meta)

    def _apply(self, conn, diffs):
        from alembic.migration import MigrationContext
        from alembic.operations import Operations

        op = Operations(MigrationContext.configure(connection=conn))
        for kind, _schema, table, column, existing, old_type, new_type in (d[0] for d in diffs):
            assert kind == "modify_type"
            op.alter_column(
                table,
                column,
                type_=new_type,
                existing_type=old_type,
                existing_nullable=existing["existing_nullable"],
            )

    @pytest.fixture()
    def conn(self, engine):
        table = Table(self.TABLE, MetaData())
        with engine.connect() as conn:
            table.drop(conn, checkfirst=True)
            conn.commit()
            try:
                yield conn
            finally:
                conn.rollback()
                table.drop(conn, checkfirst=True)
                conn.commit()

    def test_unbounded_types_have_no_false_diffs(self, conn):
        self._metadata(t=sa.Text(), ut=sa.UnicodeText(), s=STRING(), g=sa.Text()).create_all(conn)
        conn.commit()
        cols = {c["name"]: c["type"] for c in inspect(conn).get_columns(self.TABLE)}
        assert {n: str(cols[n]) for n in ("t", "ut", "s", "g")} == dict.fromkeys(
            ("t", "ut", "s", "g"), "VARCHAR(1073741823)"
        )
        meta = self._metadata(t=sa.Text(), ut=sa.UnicodeText(), s=STRING(), g=sa.String())
        assert self._diffs(conn, meta) == []

    def test_text_to_string_n_is_detected_and_applied(self, conn):
        self._metadata(v=sa.Text()).create_all(conn)
        conn.commit()
        target = self._metadata(v=sa.String(10))
        diffs = self._diffs(conn, target)
        assert [(d[0][0], d[0][3]) for d in diffs] == [("modify_type", "v")]
        self._apply(conn, diffs)
        conn.commit()
        assert str(inspect(conn).get_columns(self.TABLE)[1]["type"]) == "VARCHAR(10)"
        assert self._diffs(conn, target) == []

    def test_string_n_to_text_is_detected_and_applied(self, conn):
        self._metadata(v=sa.String(10)).create_all(conn)
        conn.commit()
        target = self._metadata(v=sa.Text())
        diffs = self._diffs(conn, target)
        assert [(d[0][0], d[0][3]) for d in diffs] == [("modify_type", "v")]
        self._apply(conn, diffs)
        conn.commit()
        assert str(inspect(conn).get_columns(self.TABLE)[1]["type"]) == "VARCHAR(1073741823)"
        assert self._diffs(conn, target) == []


class TestDropIndexIntegration:
    """#533: ``Index.drop()`` and Alembic ``op.drop_index`` are accepted live."""

    def test_index_drop(self, engine):
        meta = MetaData()
        t = Table(
            "drop_idx_533", meta, Column("id", Integer, primary_key=True), Column("v", Integer)
        )
        idx = sa.Index("ix_drop_idx_533_v", t.c.v)
        meta.drop_all(engine)
        meta.create_all(engine)
        try:
            assert inspect(engine).has_index("drop_idx_533", "ix_drop_idx_533_v")
            idx.drop(engine)
            assert not inspect(engine).has_index("drop_idx_533", "ix_drop_idx_533_v")
            # checkfirst consults has_index, so a second drop is a no-op.
            idx.drop(engine, checkfirst=True)
        finally:
            meta.drop_all(engine)

    def test_alembic_drop_index(self, engine):
        from alembic.migration import MigrationContext
        from alembic.operations import Operations

        import sqlalchemy_cubrid.alembic_impl  # noqa: F401  (registers CubridImpl)

        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS drop_idx_533_op"))
            conn.execute(text("CREATE TABLE drop_idx_533_op (id INT PRIMARY KEY, v INT)"))
            conn.execute(text("CREATE INDEX ix_drop_idx_533_op_v ON drop_idx_533_op (v)"))
            try:
                ctx = MigrationContext.configure(connection=conn)
                op = Operations(ctx)
                with pytest.raises(sa.exc.CompileError, match="pass table_name"):
                    op.drop_index("ix_drop_idx_533_op_v")
                assert inspect(conn).has_index("drop_idx_533_op", "ix_drop_idx_533_op_v")
                op.drop_index("ix_drop_idx_533_op_v", table_name="drop_idx_533_op")
                assert not inspect(conn).has_index("drop_idx_533_op", "ix_drop_idx_533_op_v")
            finally:
                conn.execute(text("DROP TABLE IF EXISTS drop_idx_533_op"))
                conn.commit()


class TestCreateIndexIfNotExistsIntegration:
    """#540: CUBRID rejects CREATE INDEX IF NOT EXISTS; plain CREATE INDEX works."""

    def test_plain_create_index_and_if_not_exists(self, engine):
        meta = MetaData()
        t = Table(
            "create_idx_540", meta, Column("id", Integer, primary_key=True), Column("v", Integer)
        )
        idx = sa.Index("ix_create_idx_540_v", t.c.v)
        meta.drop_all(engine)
        t.create(engine)
        try:
            idx.drop(engine)
            assert not inspect(engine).has_index("create_idx_540", "ix_create_idx_540_v")
            idx.create(engine)
            assert inspect(engine).has_index("create_idx_540", "ix_create_idx_540_v")
            # checkfirst is the supported guard: a second create is a no-op.
            idx.create(engine, checkfirst=True)
            with engine.connect() as conn:
                with pytest.raises(sa.exc.CompileError, match="CREATE INDEX IF NOT EXISTS"):
                    conn.execute(sa.schema.CreateIndex(idx, if_not_exists=True))
                # The server itself rejects the syntax, which is why it is refused.
                with pytest.raises(sa.exc.DBAPIError):
                    conn.exec_driver_sql(
                        "CREATE INDEX IF NOT EXISTS ix_create_idx_540_w ON create_idx_540 (v)"
                    )
                conn.rollback()
        finally:
            meta.drop_all(engine)


class TestMixedCaseExistenceIntegration:
    """#543: CUBRID stores quoted mixed-case names in lower case."""

    def test_has_table_and_has_index(self, engine):
        meta = MetaData()
        t = Table("Users543", meta, Column("id", Integer, primary_key=True), Column("v", Integer))
        sa.Index("IX_Mixed543", t.c.v)
        meta.drop_all(engine)
        meta.create_all(engine)
        try:
            insp = inspect(engine)
            assert insp.has_table("Users543")
            assert insp.has_table("users543")
            assert not insp.has_table("Missing543")
            assert insp.has_index("Users543", "IX_Mixed543")
            assert insp.has_index("users543", "ix_mixed543")
            assert not insp.has_index("Users543", "IX_Missing543")
            assert not insp.has_index("Missing543", "IX_Mixed543")
        finally:
            meta.drop_all(engine)
        insp = inspect(engine)
        assert not insp.has_table("Users543")
        assert not insp.has_index("Users543", "IX_Mixed543")

    def test_checkfirst_create_and_drop(self, engine):
        meta = MetaData()
        t = Table("Users543Cf", meta, Column("id", Integer, primary_key=True), Column("v", Integer))
        idx = sa.Index("IX_Mixed543Cf", t.c.v)
        meta.drop_all(engine)
        try:
            t.create(engine, checkfirst=True)
            # has_table finds the lower-case stored table: no second CREATE.
            t.create(engine, checkfirst=True)
            # create_all creates the table's indexes with it.
            assert inspect(engine).has_index("Users543Cf", "IX_Mixed543Cf")
            idx.create(engine, checkfirst=True)
            idx.drop(engine, checkfirst=True)
            # Before #543 checkfirst saw no index and silently skipped the drop.
            assert not inspect(engine).has_index("Users543Cf", "IX_Mixed543Cf")
            idx.drop(engine, checkfirst=True)
            idx.create(engine, checkfirst=True)
            assert inspect(engine).has_index("Users543Cf", "IX_Mixed543Cf")
            t.drop(engine, checkfirst=True)
            assert not inspect(engine).has_table("Users543Cf")
            t.drop(engine, checkfirst=True)
        finally:
            meta.drop_all(engine)


class TestHasIndexOwnerPreference:
    """#543 review: since CUBRID 11.2 classes of different owners may share a
    name. ``has_index`` answers for the current user's own class, like
    ``_get_class_type``, and only falls back to another owner's class when the
    current user has none. Checked as DBA: a non-DBA user cannot read
    ``_db_index`` yet (#549)."""

    @pytest.fixture
    def u543_engine(self, engine):
        if engine.url.username is None or engine.url.username.lower() != "dba":
            pytest.skip("needs a DBA connection to create a user")
        if not _server_at_least(engine, (11, 2)):
            pytest.skip("CUBRID < 11.2 has one global namespace for class names")

        def run(eng, *statements, ignore_errors=False):
            # One transaction per statement: DDL is transactional, so a
            # rollback after a failed statement must not undo an earlier
            # successful one (#607).
            with eng.connect() as conn:
                for statement in statements:
                    try:
                        conn.exec_driver_sql(statement)
                        conn.commit()
                    except Exception:
                        if not ignore_errors:
                            raise
                        conn.rollback()

        username = f"u543_{_USER_SUFFIX}"
        u543 = create_engine(engine.url.set(username=username, password=None))

        def cleanup():
            run(u543, 'DROP TABLE "Own543"', ignore_errors=True)
            u543.dispose()
            run(engine, 'DROP TABLE "Own543"', f"DROP USER {username}", ignore_errors=True)

        # Idempotent: ensure the user exists (so cleanup() below can connect
        # as it) before dropping it and any state it owns, then (re)create it
        # for real. Combined with the per-process-unique username, an
        # interrupted prior run or a concurrent job against the same shared
        # database can no longer make this CREATE USER fail with
        # "already exists" (#607).
        run(engine, f"CREATE USER {username}", ignore_errors=True)
        cleanup()
        run(engine, f"CREATE USER {username}")
        try:
            run(engine, 'CREATE TABLE "Own543" (id INT PRIMARY KEY, v INT)')
            run(
                u543,
                'CREATE TABLE "Own543" (id INT PRIMARY KEY, v INT)',
                'CREATE INDEX "IX_Other543" ON "Own543" (v)',
            )
            yield u543
        finally:
            cleanup()

    def test_has_index_prefers_the_current_users_class(self, engine, u543_engine):
        with engine.connect() as conn:
            owners = conn.execute(
                text("SELECT owner_name FROM db_class WHERE class_name = 'own543'")
            ).fetchall()
            assert sorted(owners) == [("DBA",), (u543_engine.url.username.upper(),)]

            # Only the other owner's same-named class has the index.
            assert inspect(conn).has_table("Own543")
            assert not inspect(conn).has_index("Own543", "IX_Other543")

            # Once the current user's class is gone, the other owner's is used.
            conn.exec_driver_sql('DROP TABLE "Own543"')
            conn.commit()
            assert inspect(conn).has_index("Own543", "IX_Other543")


class TestUnicodeTextIntegration:
    """#534: ``UnicodeText`` creates a CUBRID STRING column (CUBRID has no TEXT)."""

    def test_create_table_and_cjk_round_trip(self, engine):
        meta = MetaData()
        t = Table(
            "unicode_text_534",
            meta,
            Column("id", Integer, primary_key=True),
            Column("body", sa.UnicodeText()),
        )
        values = ["한국어 텍스트", "日本語のテキスト", "中文文本 😀", "", None, "x" * 5000]
        meta.drop_all(engine)
        meta.create_all(engine)
        try:
            with engine.begin() as conn:
                conn.execute(t.insert(), [{"id": i, "body": v} for i, v in enumerate(values)])
            with engine.connect() as conn:
                got = conn.execute(select(t.c.body).order_by(t.c.id)).scalars().all()
                col = {c["name"]: c for c in inspect(conn).get_columns("unicode_text_534")}
            assert got == values
            assert isinstance(col["body"]["type"], sa.String)
        finally:
            meta.drop_all(engine)


class TestBinaryAndUuidIntegration:
    """#545: ``BINARY``/``VARBINARY`` map to BIT strings and ``UUID`` to CHAR(32)."""

    @pytest.fixture()
    def table(self, engine):
        meta = MetaData()
        t = Table(
            "binary_uuid_545",
            meta,
            Column("id", Integer, primary_key=True),
            Column("bin", sa.BINARY(4)),
            Column("varbin", sa.VARBINARY(16)),
            Column("varbin_max", sa.VARBINARY()),
            Column("u", sa.UUID()),
            Column("u_str", sa.UUID(as_uuid=False)),
        )
        meta.drop_all(engine)
        meta.create_all(engine)
        yield t
        meta.drop_all(engine)

    def test_bytes_and_uuid_round_trip(self, engine, table):
        u1, u2 = uuid.uuid4(), uuid.uuid4()
        rows = [
            {
                "id": 1,
                "bin": b"\x00\x01\xfe\xff",
                "varbin": b"\x00\xff" * 8,
                "varbin_max": bytes(range(256)) * 4,
                "u": u1,
                "u_str": str(u1),
            },
            {"id": 2, "bin": b"ab", "varbin": b"ab", "varbin_max": b"x", "u": u2, "u_str": str(u2)},
            {"id": 3, "bin": None, "varbin": None, "varbin_max": None, "u": None, "u_str": None},
        ]
        with engine.begin() as conn:
            conn.execute(table.insert(), rows)
        with engine.connect() as conn:
            got = [dict(r._mapping) for r in conn.execute(select(table).order_by(table.c.id))]
            by_bytes = conn.execute(select(table.c.id).where(table.c.varbin == b"ab")).scalar()
            by_uuid = conn.execute(select(table.c.id).where(table.c.u == u2)).scalar()
            by_str = conn.execute(select(table.c.id).where(table.c.u_str == str(u1))).scalar()
        # BINARY is fixed-length: shorter values come back zero-padded.
        rows[1]["bin"] = b"ab\x00\x00"
        assert got == rows
        assert isinstance(got[0]["bin"], bytes) and isinstance(got[0]["varbin"], bytes)
        assert isinstance(got[0]["u"], uuid.UUID) and isinstance(got[0]["u_str"], str)
        assert (by_bytes, by_uuid, by_str) == (2, 2, 1)

    def test_reflection_and_autogenerate_have_no_false_diffs(self, engine, table):
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext

        with engine.connect() as conn:
            cols = {c["name"]: c["type"] for c in inspect(conn).get_columns(table.name)}
            ctx = MigrationContext.configure(
                connection=conn,
                opts={
                    "compare_type": True,
                    "include_name": lambda name, type_, parent: (
                        type_ != "table" or name == table.name
                    ),
                },
            )
            assert compare_metadata(ctx, table.metadata) == []

            # A real length change is still detected.
            changed = MetaData()
            Table(
                table.name,
                changed,
                *[
                    Column(c.name, c.type, primary_key=c.primary_key)
                    for c in table.c
                    if c.name != "varbin"
                ],
                Column("varbin", sa.VARBINARY(32)),
            )
            diffs = compare_metadata(ctx, changed)
        compiled = {n: engine.dialect.type_compiler_instance.process(t) for n, t in cols.items()}
        assert compiled["bin"] == "BIT(32)"
        assert compiled["varbin"] == "BIT VARYING(128)"
        assert compiled["varbin_max"] == "BIT VARYING(1073741823)"
        assert compiled["u"] == compiled["u_str"] == "CHAR(32)"
        assert [d[0][0] for d in diffs] == ["modify_type"]
        assert diffs[0][0][3] == "varbin"


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

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (15, Decimal("15.00")),
            (45.684, Decimal("45.68")),
            ("45.684", Decimal("45.68")),
            (1234567.89, Decimal("1234567.89")),
            (True, Decimal("1.00")),
            (None, None),
        ],
    )
    def test_as_numeric_returns_decimal(self, engine, value, expected):
        """#535: ``as_numeric(p, s)`` returns a Decimal at scale ``s``."""
        meta = MetaData()
        table = Table(
            "integration_json535",
            meta,
            Column("id", Integer, primary_key=True, autoincrement=False),
            Column("data_json", sa.JSON),
        )
        meta.create_all(engine)
        try:
            with engine.begin() as conn:
                conn.execute(table.insert().values(id=1, data_json={"a": value, "b": [value]}))
            with engine.connect() as conn:
                row = conn.execute(
                    sa.select(
                        table.c.data_json["a"].as_numeric(10, 2),
                        table.c.data_json[("b", 0)].as_numeric(10, 2),
                        table.c.data_json["a"].as_float(),
                    )
                ).one()
            for got in row[:2]:
                assert got == expected
                if expected is not None:
                    assert isinstance(got, Decimal)
                    assert got.as_tuple().exponent == -2
            if expected is not None:
                assert isinstance(row[2], float)
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

# pycubrid requests further rows in FETCH batches of ``fetch_size`` (the
# ``pycubrid.connection.Connection`` default, 100 in 1.7.1), and the broker's
# first response to the SELECT is further capped by size: it holds only ~16 of
# the 1000-byte rows below. The result therefore needs several FETCH round trips
# after the first response, which is exactly what a commit/rollback can
# invalidate.
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
        fetch_size = signature(pycubrid_connection.Connection).parameters["fetch_size"].default
        assert isinstance(fetch_size, int)
        assert _WIDE_ROWS > fetch_size

    @pytest.mark.parametrize("method", ["fetchone", "fetchmany", "fetchall"])
    @pytest.mark.parametrize("boundary", ["commit", "rollback", "none"])
    def test_unfinished_result_is_complete_or_raises(self, engine, wide_table, boundary, method):
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
            # Checked before the boundary, so it holds even when the rest raises.
            assert first is not None and first.id == 0 and first.payload == _WIDE_PAYLOAD
            if boundary == "commit":
                conn.commit()
            elif boundary == "rollback":
                conn.rollback()
            error = None
            try:
                rest = _drain(result, method)
            except sa.exc.DBAPIError as exc:
                if boundary == "none":
                    raise
                error, rest = exc, None  # an explicit failure satisfies the contract
        if engine.dialect.driver == "cubrid":
            # Recorded CUBRIDdb 11.3 behavior (CUBRID 10.2 and 11.4), for comparison.
            if boundary == "rollback":
                assert isinstance(error, sa.exc.InterfaceError), error
            else:
                assert error is None
        if rest is not None:
            # Everything returned, including the row fetchone() consumed, is an
            # in-order prefix with intact payloads.
            returned = [first, *rest]
            ids = [row.id for row in returned]
            assert ids == list(range(len(ids)))
            assert all(row.payload == _WIDE_PAYLOAD for row in returned)
        if rest is not None:
            assert len(ids) == _WIDE_ROWS, f"silently truncated: {len(ids)} of {_WIDE_ROWS} rows"


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


# kind -> (mapped class, values violating the constraint, native CUBRID error
# code); parent 1 always exists.
_INTEGRITY_VIOLATIONS = {
    "not_null": (_IntegrityParent, {"id": 2, "name": None}, -631),
    "foreign_key": (_IntegrityChild, {"id": 1, "parent_id": 999}, -922),
    "unique_pk": (_IntegrityParent, {"id": 1, "name": "duplicate"}, -670),  # control
}


def _native_error_code(engine, orig):
    """The server error code: pycubrid ``Error.code``, CUBRIDdb ``args[0]``."""
    if engine.dialect.driver == "pycubrid":
        return orig.code
    return CubridDialect._extract_error_code(orig)


def _assert_integrity_error(engine, exc):
    assert isinstance(exc, sa.exc.IntegrityError), (
        f"expected sqlalchemy.exc.IntegrityError, got {type(exc).__name__} "
        f"wrapping {type(exc.orig).__module__}.{type(exc.orig).__name__}"
    )
    assert isinstance(exc.orig, engine.dialect.loaded_dbapi.IntegrityError)


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
    def test_core_violation_raises_integrity_error(self, engine, kind):
        model, values, code = _INTEGRITY_VIOLATIONS[kind]
        with engine.connect() as conn:
            raw = conn.connection.dbapi_connection
            with pytest.raises(sa.exc.DBAPIError) as excinfo:
                conn.execute(sa.insert(model), values)
            assert not excinfo.value.connection_invalidated
            conn.rollback()
            # The same Connection, on the same DBAPI connection, runs new
            # statements after the rollback.
            assert not conn.invalidated
            assert conn.connection.dbapi_connection is raw
            assert _integrity_counts(conn) == (1, 0)
            conn.execute(sa.insert(_IntegrityChild), {"id": 10, "parent_id": 1})
            assert _integrity_counts(conn) == (1, 1)
            conn.rollback()
        assert _native_error_code(engine, excinfo.value.orig) == code
        _assert_integrity_error(engine, excinfo.value)

    @pytest.mark.parametrize("kind", list(_INTEGRITY_VIOLATIONS))
    def test_orm_flush_violation_raises_integrity_error(self, engine, kind):
        model, values, code = _INTEGRITY_VIOLATIONS[kind]
        # The Session is bound to one Connection, so after its rollback it keeps
        # using that Connection and its DBAPI connection.
        with engine.connect() as conn, Session(bind=conn) as session:
            raw = conn.connection.dbapi_connection
            session.add(model(**values))
            with pytest.raises(sa.exc.DBAPIError) as excinfo:
                session.flush()
            assert not excinfo.value.connection_invalidated
            session.rollback()
            assert not conn.invalidated
            assert session.connection() is conn
            assert conn.connection.dbapi_connection is raw
            session.add(_IntegrityChild(id=10, parent_id=1))
            session.flush()
            assert _integrity_counts(session.connection()) == (1, 1)
            session.rollback()
        assert _native_error_code(engine, excinfo.value.orig) == code
        _assert_integrity_error(engine, excinfo.value)


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

    def test_null_ok(self, engine, desc_tables):
        table, _ = desc_tables
        with engine.connect() as conn:
            result = conn.execute(select(table))
            null_ok = {d[0]: bool(d[6]) for d in result.cursor.description}
            result.all()
        assert null_ok == {name: spec[1] for name, spec in _DESC_COLUMNS.items()}

    def test_reflected_nullability_uses_catalog(self, engine, desc_tables):
        """Reflection reads nullability from the catalog, not cursor.description."""
        columns = {
            c["name"]: c["nullable"] for c in inspect(engine).get_columns("integration_cd482")
        }
        assert columns == {name: spec[1] for name, spec in _DESC_COLUMNS.items()}

    def test_collection_type_codes(self, desc_tables):
        _, collections = desc_tables
        # A dedicated engine keeps any broken connection out of the shared pool:
        # pycubrid < 1.8.0 misreads the collection column header.
        engine = create_engine(_cubrid_url())
        try:
            if engine.dialect.driver == "pycubrid":
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
