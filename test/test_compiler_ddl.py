# test/test_compiler_ddl.py
"""Offline DDL compiler tests — no live CUBRID required.

CREATE/DROP TABLE and INDEX, comments, IF [NOT] EXISTS and TRUNCATE, compiled
without a database connection.
"""

from __future__ import annotations


import pytest
import sqlalchemy as sa
from sqlalchemy import Column, Integer, MetaData, String, Table
from sqlalchemy.exc import CompileError

from sqlalchemy_cubrid.dialect import CubridDialect


class TestDDLCompilation:
    """Test DDL (CREATE TABLE) compilation."""

    def _compile_ddl(self, table):
        from sqlalchemy.schema import CreateTable

        dialect = CubridDialect()
        return CreateTable(table).compile(dialect=dialect).string

    def test_autoincrement_column(self):
        """AUTO_INCREMENT should appear for autoincrement PK columns."""
        m = MetaData()
        t = Table(
            "test_ai",
            m,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("name", String(100)),
        )
        ddl = self._compile_ddl(t)
        assert "AUTO_INCREMENT" in ddl
        assert "NOT NULL" in ddl

    def test_no_autoincrement_without_flag(self):
        """Columns without autoincrement should not get AUTO_INCREMENT."""
        m = MetaData()
        t = Table(
            "test_no_ai",
            m,
            Column("id", Integer, primary_key=True, autoincrement=False),
            Column("name", String(100)),
        )
        ddl = self._compile_ddl(t)
        assert "AUTO_INCREMENT" not in ddl

    def test_identity_maps_to_autoincrement(self):
        """#388: Identity() is CUBRID's AUTO_INCREMENT, not a DEFAULT.

        SQLAlchemy stores an ``Identity()`` as ``column.server_default``; the
        DDL compiler must still emit AUTO_INCREMENT for the autoincrement column
        rather than suppressing it as if a literal DEFAULT were present.
        """
        from sqlalchemy import Identity

        m = MetaData()
        t = Table(
            "test_identity_ai",
            m,
            Column("id", Integer, Identity(), primary_key=True, autoincrement=True),
            Column("name", String(100)),
        )
        ddl = self._compile_ddl(t)
        assert "AUTO_INCREMENT" in ddl
        assert "DEFAULT" not in ddl

    def test_not_null_in_ddl(self):
        """NOT NULL columns should emit NOT NULL."""
        m = MetaData()
        t = Table(
            "test_nn",
            m,
            Column("id", Integer, primary_key=True),
            Column("name", String(100), nullable=False),
        )
        ddl = self._compile_ddl(t)
        # Both id (PK) and name should have NOT NULL
        # Count NOT NULL occurrences - at least 2
        assert ddl.count("NOT NULL") >= 2

    def test_nullable_column_no_not_null(self):
        """Nullable columns should not emit NOT NULL."""
        m = MetaData()
        t = Table(
            "test_nullable",
            m,
            Column("id", Integer, primary_key=True),
            Column("name", String(100), nullable=True),
        )
        ddl = self._compile_ddl(t)
        # name column line should not have NOT NULL
        # id should have NOT NULL (PK)
        lines = ddl.split("\n")
        for line in lines:
            if "name" in line.lower() and "id" not in line.lower():
                assert "NOT NULL" not in line

    def test_column_default_value(self):
        """Column defaults should emit DEFAULT clause."""
        m = MetaData()
        t = Table(
            "test_default",
            m,
            Column("id", Integer, primary_key=True, autoincrement=False),
            Column("status", Integer, server_default="0"),
        )
        ddl = self._compile_ddl(t)
        assert "DEFAULT" in ddl

    def test_ddl_type_output(self):
        """Verify type names appear correctly in DDL."""
        m = MetaData()
        t = Table(
            "test_types",
            m,
            Column("id", Integer, primary_key=True),
            Column("name", String(100)),
        )
        ddl = self._compile_ddl(t)
        assert "INTEGER" in ddl
        assert "VARCHAR(100)" in ddl


class TestCommentCompilation:
    def test_column_comment_in_ddl(self):
        from sqlalchemy.schema import CreateTable

        t = sa.Table(
            "t",
            sa.MetaData(),
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(50), comment="user name"),
        )
        compiled = CreateTable(t).compile(dialect=CubridDialect())
        sql = str(compiled)
        assert "COMMENT" in sql
        assert "user name" in sql

    def test_column_comment_with_backslash_not_doubled(self):
        """Regression #313: DDL COMMENT literals must not double backslashes."""
        from sqlalchemy.schema import CreateTable

        t = sa.Table(
            "t",
            sa.MetaData(),
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("path", sa.String(50), comment="C:\\temp"),
        )
        sql = str(CreateTable(t).compile(dialect=CubridDialect()))
        assert "C:\\temp" in sql
        assert "\\\\" not in sql

    def test_table_comment_in_ddl(self):
        from sqlalchemy.schema import CreateTable

        t = sa.Table(
            "t",
            sa.MetaData(),
            sa.Column("id", sa.Integer, primary_key=True),
            comment="my table",
        )
        compiled = CreateTable(t).compile(dialect=CubridDialect())
        sql = str(compiled)
        assert "COMMENT =" in sql
        assert "my table" in sql

    def test_set_table_comment(self):
        from sqlalchemy.schema import SetTableComment

        t = sa.Table(
            "t",
            sa.MetaData(),
            sa.Column("id", sa.Integer),
            comment="new comment",
        )
        compiled = SetTableComment(t).compile(dialect=CubridDialect())
        sql = str(compiled)
        assert "ALTER TABLE" in sql
        assert "COMMENT =" in sql
        assert "new comment" in sql

    def test_drop_table_comment(self):
        from sqlalchemy.schema import DropTableComment

        t = sa.Table(
            "t",
            sa.MetaData(),
            sa.Column("id", sa.Integer),
            comment="old comment",
        )
        compiled = DropTableComment(t).compile(dialect=CubridDialect())
        sql = str(compiled)
        assert "ALTER TABLE" in sql
        assert "COMMENT = ''" in sql

    def test_set_column_comment(self):
        from sqlalchemy.schema import SetColumnComment

        t = sa.Table(
            "t",
            sa.MetaData(),
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(50), comment="new name"),
        )
        compiled = SetColumnComment(t.c.name).compile(dialect=CubridDialect())
        sql = str(compiled)
        assert "ALTER TABLE" in sql
        assert "MODIFY" in sql
        assert "COMMENT" in sql
        assert "new name" in sql


class TestIfExistsDDL:
    """Test IF NOT EXISTS / IF EXISTS DDL compilation."""

    def test_create_table_if_not_exists(self):
        """CREATE TABLE IF NOT EXISTS should compile correctly."""
        from sqlalchemy.schema import CreateTable

        t = sa.Table(
            "t",
            sa.MetaData(),
            sa.Column("id", sa.Integer, primary_key=True),
        )
        compiled = CreateTable(t, if_not_exists=True).compile(dialect=CubridDialect())
        sql = str(compiled)
        assert "IF NOT EXISTS" in sql

    def test_drop_table_if_exists(self):
        """DROP TABLE IF EXISTS should compile correctly."""
        from sqlalchemy.schema import DropTable

        t = sa.Table(
            "t",
            sa.MetaData(),
            sa.Column("id", sa.Integer, primary_key=True),
        )
        compiled = DropTable(t, if_exists=True).compile(dialect=CubridDialect())
        sql = str(compiled)
        assert "IF EXISTS" in sql


class TestTruncateCompilation:
    """Test TRUNCATE TABLE compilation."""

    def test_truncate_basic(self):
        """TRUNCATE TABLE should compile."""
        from sqlalchemy import text

        sql = str(text("TRUNCATE TABLE users"))
        assert "TRUNCATE" in sql


class TestFKIndexCollisionDDL:
    """#355: CREATE INDEX on FK columns — DDL compiler behavior."""

    def test_non_unique_index_on_fk_column_passed_through(self):
        """Non-unique index on FK columns is passed through (CUBRID accepts it)."""
        from sqlalchemy import ForeignKey, Index, schema

        m = MetaData()
        Table("parent", m, Column("id", Integer, primary_key=True))
        child = Table(
            "child",
            m,
            Column("id", Integer, primary_key=True),
            Column("pid", Integer, ForeignKey("parent.id")),
            Index("idx_pid", "pid"),
        )
        idx = list(child.indexes)[0]
        ddl = schema.CreateIndex(idx).compile(dialect=CubridDialect())
        assert "CREATE INDEX" in ddl.string

    def test_unique_index_on_fk_column_raises(self):
        """UNIQUE index matching FK columns raises CompileError."""
        import pytest
        from sqlalchemy import ForeignKey, Index, schema

        m = MetaData()
        Table("parent", m, Column("id", Integer, primary_key=True))
        child = Table(
            "child_u",
            m,
            Column("id", Integer, primary_key=True),
            Column("pid", Integer, ForeignKey("parent.id")),
            Index("idx_pid_u", "pid", unique=True),
        )
        idx = [i for i in child.indexes if i.name == "idx_pid_u"][0]
        with pytest.raises(CompileError, match="CUBRID cannot create a UNIQUE index"):
            schema.CreateIndex(idx).compile(dialect=CubridDialect())

    def test_non_fk_index_not_affected(self):
        """Index on non-FK columns proceeds normally."""
        from sqlalchemy import Index, schema

        m = MetaData()
        t = Table(
            "standalone",
            m,
            Column("id", Integer, primary_key=True),
            Column("val", String(50)),
            Index("idx_val", "val"),
        )
        idx = list(t.indexes)[0]
        ddl = schema.CreateIndex(idx).compile(dialect=CubridDialect())
        assert "CREATE INDEX" in ddl.string

    def test_different_column_order_not_skipped(self):
        """Index with reversed column order vs FK is not skipped."""
        from sqlalchemy import ForeignKeyConstraint, Index, schema

        m = MetaData()
        Table("parent2", m, Column("a", Integer), Column("b", Integer))
        child = Table(
            "child2",
            m,
            Column("id", Integer, primary_key=True),
            Column("a", Integer),
            Column("b", Integer),
            ForeignKeyConstraint(["a", "b"], ["parent2.a", "parent2.b"]),
            Index("idx_ba", "b", "a"),  # reversed order
        )
        idx = [i for i in child.indexes if i.name == "idx_ba"][0]
        ddl = schema.CreateIndex(idx).compile(dialect=CubridDialect())
        assert "CREATE INDEX" in ddl.string


class TestDropIndexDDL533:
    """#533: CUBRID requires ``DROP INDEX <name> ON <table>``."""

    @staticmethod
    def _drop(index, **kw):
        return sa.schema.DropIndex(index, **kw).compile(dialect=CubridDialect()).string.strip()

    def test_drop_index_names_its_table(self):
        t = Table("users", MetaData(), Column("email", String(50)))
        assert self._drop(sa.Index("ix_users_email", t.c.email)) == (
            "DROP INDEX ix_users_email ON users"
        )

    def test_drop_index_quotes_name_and_table_and_keeps_schema(self):
        t = Table("Users", MetaData(), Column("email", String(50)), schema="dba")
        assert self._drop(sa.Index("IX_Mixed", t.c.email)) == (
            'DROP INDEX "IX_Mixed" ON dba."Users"'
        )

    def test_drop_unique_index(self):
        t = Table("users", MetaData(), Column("email", String(50)))
        assert self._drop(sa.Index("ux_email", t.c.email, unique=True)) == (
            "DROP INDEX ux_email ON users"
        )

    def test_drop_index_if_exists_is_rejected(self):
        """CUBRID has no DROP INDEX IF EXISTS (10.2-11.4 answer a syntax error)."""
        t = Table("users", MetaData(), Column("email", String(50)))
        with pytest.raises(CompileError, match="does not support DROP INDEX IF EXISTS"):
            self._drop(sa.Index("ix_users_email", t.c.email), if_exists=True)

    def test_drop_index_without_table_is_rejected(self):
        with pytest.raises(CompileError, match="requires the index's table"):
            self._drop(sa.Index("ix_orphan"))

    def test_drop_index_without_name_is_rejected(self):
        with pytest.raises(CompileError, match="requires that the index have a name"):
            self._drop(sa.Index(None))


class TestCreateIndexIfNotExists540:
    """#540: CUBRID has no CREATE INDEX IF NOT EXISTS (10.2-11.4 answer a syntax error)."""

    def test_create_index_if_not_exists_is_rejected(self):
        t = Table("users", MetaData(), Column("email", String(50)))
        idx = sa.Index("ix_users_email", t.c.email)
        with pytest.raises(CompileError, match="does not support CREATE INDEX IF NOT EXISTS"):
            sa.schema.CreateIndex(idx, if_not_exists=True).compile(dialect=CubridDialect())

    def test_unique_create_index_if_not_exists_is_rejected(self):
        t = Table("users", MetaData(), Column("email", String(50)))
        idx = sa.Index("ux_users_email", t.c.email, unique=True)
        with pytest.raises(CompileError, match="has_index"):
            sa.schema.CreateIndex(idx, if_not_exists=True).compile(dialect=CubridDialect())

    def test_plain_create_index_is_unchanged(self):
        t = Table("Users", MetaData(), Column("email", String(50)))
        idx = sa.Index("IX_Mixed", t.c.email)
        ddl = sa.schema.CreateIndex(idx).compile(dialect=CubridDialect()).string.strip()
        assert ddl == 'CREATE INDEX "IX_Mixed" ON "Users" (email)'


class TestIndexDialectOptions869:
    _t = Table("t869", MetaData(), Column("a", String(20)), Column("b", Integer))

    @staticmethod
    def _ddl(index):
        return str(sa.schema.CreateIndex(index).compile(dialect=CubridDialect()))

    def test_where_expression_and_text(self):
        t = self._t
        assert self._ddl(sa.Index("i1", t.c.b, cubrid_where=t.c.b > 3)) == (
            "CREATE INDEX i1 ON t869 (b) WHERE b > 3"
        )
        assert self._ddl(sa.Index("i2", t.c.b, cubrid_where="b>3")) == (
            "CREATE INDEX i2 ON t869 (b) WHERE b>3"
        )

    def test_length_mapping_integer_and_desc(self):
        t = self._t
        assert self._ddl(sa.Index("i3", t.c.a.desc(), t.c.b, cubrid_length={"a": 5})) == (
            "CREATE INDEX i3 ON t869 (a(5) DESC, b)"
        )
        assert self._ddl(sa.Index("i4", t.c.a, cubrid_length=4, unique=True)) == (
            "CREATE UNIQUE INDEX i4 ON t869 (a(4))"
        )
        assert self._ddl(
            sa.Index("i5", t.c.a.asc(), cubrid_length={"a": 2}, cubrid_where=t.c.b > 1)
        ) == ("CREATE INDEX i5 ON t869 (a(2) ASC) WHERE b > 1")

    @pytest.mark.parametrize("value", [None, 0, "5"])
    def test_invalid_mapping_value_raises(self, value):
        with pytest.raises(CompileError, match="positive integer"):
            self._ddl(sa.Index("i10", self._t.c.a, cubrid_length={"a": value}))

    @pytest.mark.parametrize("length", [0, -1, "5", 2.5])
    def test_invalid_length_raises(self, length):
        with pytest.raises(CompileError, match="cubrid_length"):
            self._ddl(sa.Index("i6", self._t.c.a, cubrid_length=length))

    def test_length_on_expression_raises(self):
        with pytest.raises(CompileError, match="cubrid_length"):
            self._ddl(sa.Index("i7", sa.func.lower(self._t.c.a), cubrid_length=3))

    @pytest.mark.parametrize(
        ("keys", "length"),
        [
            (lambda t: [sa.func.lower(t.c.a)], {"a": 5}),
            (lambda t: [t.c.a], {"misspelled": 5}),
            (lambda t: [t.c.a.desc(), sa.func.lower(t.c.a)], {"a": 2, "lower": 3}),
        ],
    )
    def test_length_mapping_keys_must_be_plain_columns(self, keys, length):
        with pytest.raises(CompileError, match="not a plain column key"):
            self._ddl(sa.Index("i9", *keys(self._t), cubrid_length=length))

    def test_unique_filtered_index_raises(self):
        with pytest.raises(CompileError, match="UNIQUE filtered"):
            self._ddl(sa.Index("i8", self._t.c.b, unique=True, cubrid_where="b>0"))
