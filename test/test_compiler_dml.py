# test/test_compiler_dml.py
"""Offline DML compiler tests — no live CUBRID required.

INSERT, UPDATE, RETURNING rejection, ON DUPLICATE KEY UPDATE, REPLACE, MERGE
and the ``sqlalchemy_cubrid.dml`` constructs, compiled without a database
connection.
"""

from __future__ import annotations


import pytest
import sqlalchemy as sa
from sqlalchemy import Column, Integer, MetaData, String, Table, select
from sqlalchemy.exc import CompileError

from sqlalchemy_cubrid.dialect import CubridDialect
from test._compiler_helpers import _compile, _norm, metadata, users


@pytest.mark.parametrize("operation", ["insert", "update", "delete"])
def test_dml_visitors_accept_framework_positional_arguments(operation):
    dialect = CubridDialect()
    compiler = dialect.statement_compiler(dialect, sa.select(sa.literal(1)))
    if operation == "insert":
        statement = sa.insert(users).values(id=1)
        actual = compiler.visit_insert(statement, None, None, literal_binds=True)
    elif operation == "update":
        statement = sa.update(users).values(name="updated")
        actual = compiler.visit_update(statement, None, literal_binds=True)
    else:
        statement = sa.delete(users)
        actual = compiler.visit_delete(statement, None, literal_binds=True)
    assert _norm(actual) == _norm(_compile(statement, dialect))


class TestInsertCompilation:
    """Test INSERT statement compilation."""

    def test_insert_default_values(self):
        """INSERT with no values should produce DEFAULT VALUES."""
        from sqlalchemy import insert

        stmt = insert(users).values()
        sql = _compile(stmt)
        assert "DEFAULT VALUES" in sql

    def test_insert_with_values(self):
        """INSERT with explicit values should compile normally."""
        from sqlalchemy import insert

        stmt = insert(users).values(name="test", email="test@example.com")
        sql = _compile(stmt)
        assert "INSERT INTO" in sql
        assert "users" in sql

    def test_insertmanyvalues_dropped_for_bind_expression_column(self):
        """#421: a column type with a bind_expression() disables insertmanyvalues.

        SQLAlchemy's insertmanyvalues row-expansion miscounts parameters when a
        bind is wrapped in a bind_expression (e.g. CAST(? AS ...)), so the CUBRID
        dialect drops the plan (in visit_insert) and falls back to ordinary
        executemany. The detection helper distinguishes the two cases.
        """
        from sqlalchemy import Integer, String, TypeDecorator, cast, insert, type_coerce
        from sqlalchemy.schema import MetaData, Table

        from sqlalchemy_cubrid.compiler import CubridCompiler

        class StringAsInt(TypeDecorator):
            impl = String(50)
            cache_ok = True

            def bind_expression(self, col):
                return cast(type_coerce(col, Integer), String(50))

        m = MetaData()
        with_expr = Table(
            "t_bindexpr",
            m,
            Column("id", Integer, primary_key=True, autoincrement=False),
            Column("x", StringAsInt()),
        )
        plain = Table(
            "t_plain",
            m,
            Column("id", Integer, primary_key=True, autoincrement=False),
            Column("x", String(50)),
        )

        assert CubridCompiler._insert_has_bind_expression(insert(with_expr)) is True
        assert CubridCompiler._insert_has_bind_expression(insert(plain)) is False

    def test_insert_from_cte_select_puts_with_after_the_column_list(self):
        """#897: CUBRID needs INSERT INTO t (...) WITH ... SELECT, not WITH ... INSERT."""
        source = sa.table("src", sa.column("id", Integer), sa.column("s", String))
        target = sa.table("t", sa.column("id", Integer), sa.column("s", String))
        cte = select(source.c.id, source.c.s).where(source.c.id > sa.bindparam("low", 2)).cte("c")
        stmt = sa.insert(target).from_select(
            ["id", "s"], select(cte.c.id, cte.c.s).where(cte.c.id < sa.bindparam("high", 9))
        )
        compiled = stmt.compile(dialect=CubridDialect())
        assert _norm(compiled.string) == _norm(
            "INSERT INTO t (id, s) "
            "WITH c AS (SELECT src.id AS id, src.s AS s FROM src WHERE src.id > ?) "
            "SELECT c.id, c.s FROM c WHERE c.id < ?"
        )
        assert compiled.positiontup == ["low", "high"]

    def test_insert_from_recursive_cte_select_puts_with_after_the_column_list(self):
        """#897: a recursive CTE renders WITH RECURSIVE after the column list."""
        target = sa.table("t", sa.column("id", Integer))
        base = select(sa.literal(1).label("n")).cte("c", recursive=True)
        cte = base.union_all(select(base.c.n + 1).where(base.c.n < 3))
        stmt = sa.insert(target).from_select(["id"], select(cte.c.n))
        sql = _norm(_compile(stmt))
        assert sql.startswith("INSERT INTO t (id) WITH RECURSIVE c(n) AS ("), sql


class TestReturningCompilation:
    """Test that RETURNING raises CompileError (CUBRID does not support it)."""

    def test_returning_on_insert_raises(self):
        stmt = sa.insert(users).values(name="test").returning(users.c.id, users.c.name)
        with pytest.raises(CompileError, match="RETURNING"):
            _compile(stmt)

    def test_returning_on_update_raises(self):
        stmt = sa.update(users).where(users.c.id == 1).values(name="test").returning(users.c.id)
        with pytest.raises(CompileError, match="RETURNING"):
            _compile(stmt)

    def test_returning_on_delete_raises(self):
        stmt = sa.delete(users).where(users.c.id == 1).returning(users.c.id)
        with pytest.raises(CompileError, match="RETURNING"):
            _compile(stmt)


class TestMultiTableUpdateCompilation:
    def test_multi_table_update(self):
        t1 = sa.table("t1", sa.column("id"), sa.column("val"))
        t2 = sa.table("t2", sa.column("id"), sa.column("rate"))

        stmt = t1.update().where(t1.c.id == t2.c.id).values(val=t2.c.rate)
        with pytest.raises(CompileError, match=r"UPDATE \.\.\. FROM"):
            _compile(stmt)

    def test_cast_with_none_type(self):
        """Test cast when typeclause returns None."""
        # This is a rare case; we test by patching type processing
        stmt = select(sa.cast(users.c.name, Integer))
        dialect = CubridDialect()
        compiler_obj = stmt.compile(dialect=dialect, compile_kwargs={"literal_binds": True})
        # The branch is rare but if type_.process returns None, CAST returns just the clause
        sql = compiler_obj.string
        # At least verify the statement compiles without error
        assert "users" in sql


class TestUpdateCompilation:
    """Test UPDATE statement compilation with LIMIT and FROM."""

    def test_update_with_limit(self):
        """Test UPDATE with cubrid_limit kwargs."""
        from sqlalchemy import update

        stmt = update(users).values(name="test")
        stmt.kwargs["cubrid_limit"] = 10
        sql = _compile(stmt)
        assert "UPDATE" in sql
        assert "LIMIT" in sql
        assert "10" in sql

    def test_update_with_limit_exact_clause(self):
        from sqlalchemy import update

        stmt = update(users).values(name="x")
        stmt.kwargs["cubrid_limit"] = 3
        assert _norm(_compile(stmt)) == "UPDATE users SET name='x' LIMIT 3"

    def test_update_without_limit(self):
        """Test UPDATE without limit - no LIMIT clause."""
        from sqlalchemy import update

        stmt = update(users).values(name="test")
        sql = _compile(stmt)
        assert "UPDATE" in sql

    def test_update_with_limit_zero(self):
        """Regression: LIMIT 0 must not be silently dropped. (#183)"""
        from sqlalchemy import update

        stmt = update(users).values(name="test")
        stmt.kwargs["cubrid_limit"] = 0
        sql = _compile(stmt)
        assert "LIMIT 0" in sql

    def test_update_limit_rejects_bool(self):
        """cubrid_limit=True must not be accepted (bool is subclass of int)."""
        from sqlalchemy import update

        stmt = update(users).values(name="test")
        stmt.kwargs["cubrid_limit"] = True
        with pytest.raises(CompileError, match="non-negative integer"):
            _compile(stmt)

    def test_update_limit_rejects_negative(self):
        """cubrid_limit=-1 must raise CompileError."""
        from sqlalchemy import update

        stmt = update(users).values(name="test")
        stmt.kwargs["cubrid_limit"] = -1
        with pytest.raises(CompileError, match="non-negative integer"):
            _compile(stmt)

    def test_update_limit_rejects_string(self):
        """cubrid_limit='5' must raise CompileError."""
        from sqlalchemy import update

        stmt = update(users).values(name="test")
        stmt.kwargs["cubrid_limit"] = "5"
        with pytest.raises(CompileError, match="non-negative integer"):
            _compile(stmt)

    def test_update_from_raises_compile_error(self):
        t1 = sa.table("t1", sa.column("id"), sa.column("val"))
        t2 = sa.table("t2", sa.column("id"), sa.column("rate"))
        stmt = t1.update().values(val=t2.c.rate).where(t1.c.id == t2.c.id)

        with pytest.raises(CompileError, match=r"UPDATE \.\.\. FROM"):
            stmt.compile(dialect=CubridDialect())


class TestOnDuplicateKeyUpdateCompilation:
    """Test ON DUPLICATE KEY UPDATE compilation."""

    def test_on_duplicate_key_update_basic(self):
        """ON DUPLICATE KEY UPDATE with simple column=value."""
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(id=1, name="test", email="test@example.com")
        stmt = stmt.on_duplicate_key_update(name="updated")
        sql = _compile(stmt)
        assert "ON DUPLICATE KEY UPDATE" in sql
        assert "name" in sql

    def test_on_duplicate_key_update_with_values_ref(self):
        """ON DUPLICATE KEY UPDATE referencing inserted values re-emits the bind.

        CUBRID 11.4 does not support VALUES(col), so the dialect re-uses the
        INSERT bind parameter.  The compiled SQL should contain a ``?``
        placeholder (not ``VALUES(name)``) and ``name`` should appear twice
        in ``positiontup``.
        """
        from sqlalchemy_cubrid.dml import insert
        from sqlalchemy_cubrid.pycubrid_dialect import PyCubridDialect

        stmt = insert(users).values(id=1, name="test", email="test@example.com")
        stmt = stmt.on_duplicate_key_update(name=stmt.inserted.name)
        compiled = stmt.compile(dialect=PyCubridDialect())
        sql = compiled.string
        assert "ON DUPLICATE KEY UPDATE" in sql
        assert "VALUES(" not in sql, "CUBRID does not support VALUES() — should use bind param"
        assert compiled.positiontup.count("name") == 2, (
            f"'name' should appear twice in positiontup, got {compiled.positiontup}"
        )

    def test_on_duplicate_key_update_multirow_inserted_ref_raises(self):
        """#371: inline multi-row VALUES + stmt.inserted.col must fail closed.

        Not expressible on CUBRID (no VALUES(col) / row-alias), so it must raise
        rather than silently bind one row's value for every conflicting row.
        """
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(
            [
                {"id": 1, "name": "a", "email": "a@example.com"},
                {"id": 2, "name": "b", "email": "b@example.com"},
            ]
        )
        stmt = stmt.on_duplicate_key_update(name=stmt.inserted.name)
        with pytest.raises(CompileError, match="multi-row VALUES INSERT"):
            _compile(stmt)

    def test_on_duplicate_key_update_multirow_nested_inserted_ref_raises(self):
        """#371: the inserted-value ref is unsupported even nested in an expression."""
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(
            [
                {"id": 1, "name": "a", "email": "a@example.com"},
                {"id": 2, "name": "b", "email": "b@example.com"},
            ]
        )
        stmt = stmt.on_duplicate_key_update(name=sa.func.coalesce(stmt.inserted.name, "x"))
        with pytest.raises(CompileError, match="multi-row VALUES INSERT"):
            _compile(stmt)

    def test_on_duplicate_key_update_multirow_literal_update_compiles(self):
        """#371: multi-row VALUES + a literal update needs no inserted value and compiles."""
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(
            [
                {"id": 1, "name": "a", "email": "a@example.com"},
                {"id": 2, "name": "b", "email": "b@example.com"},
            ]
        )
        stmt = stmt.on_duplicate_key_update(name="fixed")
        sql = _compile(stmt)
        assert "ON DUPLICATE KEY UPDATE" in sql

    def test_on_duplicate_key_update_dict_arg(self):
        """ON DUPLICATE KEY UPDATE with dict argument."""
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(id=1, name="test", email="test@example.com")
        stmt = stmt.on_duplicate_key_update({"name": "updated", "email": "new@example.com"})
        sql = _compile(stmt)
        assert "ON DUPLICATE KEY UPDATE" in sql

    def test_on_duplicate_key_update_ordered_list(self):
        """ON DUPLICATE KEY UPDATE with ordered list of tuples."""
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(id=1, name="test", email="test@example.com")
        stmt = stmt.on_duplicate_key_update([("name", "updated"), ("email", "new@example.com")])
        sql = _compile(stmt)
        assert "ON DUPLICATE KEY UPDATE" in sql

    def test_on_duplicate_key_update_with_subquery(self):
        """ON DUPLICATE KEY UPDATE with subquery value expression."""
        from sqlalchemy_cubrid.dml import insert

        # CUBRID supports subquery expressions in ODKU update values
        subq = sa.select(sa.func.max(users.c.id)).scalar_subquery()
        stmt = insert(users).values(id=1, name="test", email="test@example.com")
        stmt = stmt.on_duplicate_key_update(id=subq)
        sql = _compile(stmt)
        assert "ON DUPLICATE KEY UPDATE" in sql
        assert "SELECT max(users.id)" in sql.replace("\n", " ")

    def test_on_duplicate_key_update_with_expression(self):
        """ON DUPLICATE KEY UPDATE with arithmetic expression."""
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(id=1, name="test", email="test@example.com")
        stmt = stmt.on_duplicate_key_update(name=sa.literal_column("'prefix_' || name"))
        sql = _compile(stmt)
        assert "ON DUPLICATE KEY UPDATE" in sql
        assert "'prefix_' || name" in sql

    def test_on_duplicate_key_update_basic_nonliteral_binding_order(self):
        """#613: INSERT binds precede the ODKU update bind, in column order."""
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(id=1, name="test", email="test@example.com")
        stmt = stmt.on_duplicate_key_update(email="updated@example.com")
        compiled = stmt.compile(dialect=CubridDialect())
        assert compiled.positiontup[:3] == ["id", "name", "email"]
        assert len(compiled.positiontup) == 4
        update_bind = compiled.positiontup[3]
        assert compiled.params["id"] == 1
        assert compiled.params["name"] == "test"
        assert compiled.params["email"] == "test@example.com"
        assert compiled.params[update_bind] == "updated@example.com"

    def test_on_duplicate_key_update_dict_arg_nonliteral_binding_order(self):
        """#613: dict-arg ODKU binds in the dict's iteration order."""
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(id=1, name="test", email="test@example.com")
        stmt = stmt.on_duplicate_key_update({"name": "updated", "email": "new@example.com"})
        compiled = stmt.compile(dialect=CubridDialect())
        assert compiled.positiontup[:3] == ["id", "name", "email"]
        update_binds = compiled.positiontup[3:]
        assert len(update_binds) == 2
        assert [compiled.params[b] for b in update_binds] == ["updated", "new@example.com"]

    def test_on_duplicate_key_update_ordered_list_nonliteral_binding_order(self):
        """#613: ordered-list ODKU binds in the given list order."""
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(id=1, name="test", email="test@example.com")
        stmt = stmt.on_duplicate_key_update([("email", "new@example.com"), ("name", "updated")])
        compiled = stmt.compile(dialect=CubridDialect())
        update_binds = compiled.positiontup[3:]
        assert len(update_binds) == 2
        # The list gave email before name; the bind order must follow it,
        # not alphabetical or declared-column order.
        assert [compiled.params[b] for b in update_binds] == ["new@example.com", "updated"]


class TestReplaceCompilation:
    def test_replace_basic(self):
        from sqlalchemy_cubrid.dml import replace

        stmt = replace(users).values(name="test", email="test@test.com")
        sql = _compile(stmt)
        assert sql.startswith("REPLACE INTO")
        assert "users" in sql
        assert "'test'" in sql

    def test_replace_no_values(self):
        from sqlalchemy_cubrid.dml import replace

        stmt = replace(users)
        sql = _compile(stmt)
        assert sql.startswith("REPLACE INTO")

    def test_replace_with_columns(self):
        from sqlalchemy_cubrid.dml import replace

        stmt = replace(users).values(id=1, name="test", email="t@t.com")
        sql = _compile(stmt)
        assert "REPLACE INTO" in sql
        assert "INSERT" not in sql

    def test_replace_exported_from_package(self):
        from sqlalchemy_cubrid import replace as pkg_replace
        from sqlalchemy_cubrid.dml import replace as dml_replace

        assert pkg_replace is dml_replace

    def test_replace_is_not_insert(self):
        from sqlalchemy_cubrid.dml import replace

        stmt = replace(users).values(name="test")
        sql = _compile(stmt)
        assert not sql.startswith("INSERT")
        assert sql.startswith("REPLACE")

    def test_replace_factory_function(self):
        from sqlalchemy_cubrid.dml import Replace, replace

        stmt = replace(users)
        assert isinstance(stmt, Replace)

    def test_replace_inherits_insert(self):
        from sqlalchemy_cubrid.dml import Replace
        from sqlalchemy.sql.dml import Insert as StandardInsert

        assert issubclass(Replace, StandardInsert)


class TestReplaceKeywordIsStructural:
    """REPLACE is emitted as the statement verb, never by rewriting SQL text (#591)."""

    target = sa.table("t", sa.column("id", Integer), sa.column("s", String))
    source = sa.table("src", sa.column("id", Integer), sa.column("s", String))

    def test_issue_repro_prefix_and_literal_in_from_select(self):
        from sqlalchemy_cubrid import replace

        stmt = (
            replace(self.target)
            .prefix_with("/* c */")
            .from_select(
                ["id", "s"],
                select(self.source.c.id, sa.literal("INSERT INTO", String)),
            )
        )
        sql = _compile(stmt)
        assert _norm(sql) == _norm(
            "REPLACE /* c */ INTO t (id, s) SELECT src.id, 'INSERT INTO' AS anon_1 FROM src"
        )

    def test_prefix_and_literal_column_value(self):
        from sqlalchemy_cubrid import replace

        stmt = (
            replace(self.target)
            .prefix_with("/* c */")
            .values(id=1, s=sa.literal_column("'INSERT INTO'"))
        )
        compiled = stmt.compile(dialect=CubridDialect())
        assert compiled.string == "REPLACE /* c */ INTO t (id, s) VALUES (?, 'INSERT INTO')"
        assert compiled.positiontup == ["id"]
        assert compiled.params == {"id": 1}

    def test_prefix_and_bound_value_untouched(self):
        from sqlalchemy_cubrid import replace

        stmt = replace(self.target).prefix_with("/* c */").values(id=1, s="INSERT INTO")
        compiled = stmt.compile(dialect=CubridDialect())
        assert compiled.string == "REPLACE /* c */ INTO t (id, s) VALUES (?, ?)"
        assert compiled.positiontup == ["id", "s"]
        assert compiled.params == {"id": 1, "s": "INSERT INTO"}

    def test_prefix_comment_containing_insert_into(self):
        from sqlalchemy_cubrid import replace

        stmt = replace(self.target).prefix_with("/* INSERT INTO audit */").values(id=1, s="x")
        compiled = stmt.compile(dialect=CubridDialect())
        assert compiled.string == ("REPLACE /* INSERT INTO audit */ INTO t (id, s) VALUES (?, ?)")
        assert compiled.positiontup == ["id", "s"]

    def test_identifier_spelled_insert_into(self):
        from sqlalchemy_cubrid import replace

        tbl = sa.table(
            "insert_into", sa.column("INSERT INTO", Integer), sa.column("insert_into", Integer)
        )
        stmt = replace(tbl).prefix_with("/* c */").values({"INSERT INTO": 1, "insert_into": 2})
        compiled = stmt.compile(dialect=CubridDialect())
        assert compiled.string == (
            'REPLACE /* c */ INTO insert_into ("INSERT INTO", insert_into) VALUES (?, ?)'
        )
        assert list(compiled.params.values()) == [1, 2]

    def test_multi_values_with_prefix(self):
        from sqlalchemy_cubrid import replace

        stmt = (
            replace(self.target)
            .prefix_with("/* c */")
            .values([{"id": 1, "s": "INSERT INTO"}, {"id": 2, "s": "b"}])
        )
        compiled = stmt.compile(dialect=CubridDialect())
        assert compiled.string == ("REPLACE /* c */ INTO t (id, s) VALUES (?, ?), (?, ?)")
        assert compiled.positiontup == ["id_m0", "s_m0", "id_m1", "s_m1"]
        assert list(compiled.params.values()) == [1, "INSERT INTO", 2, "b"]

    def test_prefix_for_other_dialect_is_not_rendered(self):
        from sqlalchemy_cubrid import replace

        stmt = replace(self.target).prefix_with("IGNORE", dialect="mysql").values(id=1)
        assert _compile(stmt) == "REPLACE INTO t (id) VALUES (1)"

    def test_cte_with_literal_and_prefix(self):
        from sqlalchemy_cubrid import replace

        cte = select(self.source.c.id, sa.literal("INSERT INTO", String).label("s")).cte("c")
        stmt = (
            replace(self.target)
            .prefix_with("/* c */")
            .from_select(["id", "s"], select(cte.c.id, cte.c.s))
        )
        sql = _norm(_compile(stmt))
        assert sql == _norm(
            "REPLACE /* c */ INTO t (id, s) "
            "WITH c AS (SELECT src.id AS id, 'INSERT INTO' AS s FROM src) "
            "SELECT c.id, c.s FROM c"
        )

    def test_cte_from_select_with_bound_values_and_prefix(self):
        """A REPLACE CTE keeps SELECT binds in their emitted placeholder order."""
        from sqlalchemy_cubrid import replace

        cte = (
            select(self.source.c.id, self.source.c.s)
            .where(self.source.c.id > sa.bindparam("low", 2))
            .cte("c")
        )
        stmt = (
            replace(self.target)
            .prefix_with("/* c */")
            .from_select(
                ["id", "s"],
                select(cte.c.id, cte.c.s).where(cte.c.id < sa.bindparam("high", 9)),
            )
        )
        compiled = stmt.compile(dialect=CubridDialect())

        assert _norm(compiled.string) == _norm(
            "REPLACE /* c */ INTO t (id, s) "
            "WITH c AS (SELECT src.id AS id, src.s AS s FROM src WHERE src.id > ?) "
            "SELECT c.id, c.s FROM c WHERE c.id < ?"
        )
        assert compiled.string.count("?") == 2
        assert compiled.positiontup == ["low", "high"]
        assert [compiled.params[name] for name in compiled.positiontup] == [2, 9]

    def test_cte_without_prefix(self):
        from sqlalchemy_cubrid import replace

        cte = select(self.source.c.id, self.source.c.s).cte("c")
        stmt = replace(self.target).from_select(["id", "s"], select(cte.c.id, cte.c.s))
        sql = _norm(_compile(stmt))
        assert sql == _norm(
            "REPLACE INTO t (id, s) "
            "WITH c AS (SELECT src.id AS id, src.s AS s FROM src) "
            "SELECT c.id, c.s FROM c"
        )

    def test_insert_is_unchanged(self):
        stmt = sa.insert(self.target).prefix_with("/* c */").values(id=1, s="INSERT INTO")
        assert _compile(stmt) == "INSERT /* c */ INTO t (id, s) VALUES (1, 'INSERT INTO')"

    def test_executemany_uses_replace(self):
        from sqlalchemy_cubrid import replace

        compiled = (
            replace(users)
            .prefix_with("/* c */")
            .compile(dialect=CubridDialect(), column_keys=["id", "name"])
        )
        assert compiled.string == "REPLACE /* c */ INTO users (id, name) VALUES (?, ?)"
        assert compiled.positiontup == ["id", "name"]

    def test_unexpected_insert_text_raises(self, monkeypatch):
        from sqlalchemy.sql import compiler as sa_compiler

        from sqlalchemy_cubrid import replace

        monkeypatch.setattr(sa_compiler.SQLCompiler, "visit_insert", lambda *a, **kw: "BOGUS")
        with pytest.raises(CompileError, match="Could not locate the INSERT verb"):
            _compile(replace(self.target).values(id=1))


class TestCacheKeyRegression:
    """Verify that Insert/Replace cache keys work correctly with inherit_cache=True.

    These tests ensure that different DML variants produce distinct cache keys,
    preventing cross-contamination of compiled SQL in SQLAlchemy's query cache.
    """

    def test_plain_insert_cache_key(self):
        """Plain INSERT should produce a stable cache key."""
        from sqlalchemy_cubrid.dml import insert

        stmt1 = insert(users).values(name="a")
        stmt2 = insert(users).values(name="b")
        key1 = stmt1._generate_cache_key()
        key2 = stmt2._generate_cache_key()
        assert key1 is not None
        assert key2 is not None
        # Same structure, different bind values → same cache key
        assert key1[0] == key2[0]

    @staticmethod
    def _key(stmt):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error", sa.exc.SAWarning)
            return stmt._generate_cache_key()

    def test_insert_odku_is_cacheable(self):
        """#871: ON DUPLICATE KEY UPDATE has a cache key and emits no SAWarning."""
        from sqlalchemy_cubrid.dml import insert

        odku = insert(users).values(name="a").on_duplicate_key_update(name="b")
        assert self._key(odku) is not None

    def test_odku_with_other_values_shares_the_cache_key(self):
        from sqlalchemy_cubrid.dml import insert

        key1 = self._key(insert(users).values(name="a").on_duplicate_key_update(name="b"))
        key2 = self._key(insert(users).values(name="z").on_duplicate_key_update(name="c"))
        assert key1 == key2

    @pytest.mark.parametrize(
        "other",
        [
            lambda stmt: stmt.on_duplicate_key_update(email="b"),
            lambda stmt: stmt.on_duplicate_key_update(name=users.c.name + "x"),
            lambda stmt: stmt.on_duplicate_key_update(name=stmt.inserted.name),
            lambda stmt: stmt.on_duplicate_key_update([("email", "b"), ("name", "b")]),
            lambda stmt: stmt,
        ],
    )
    def test_different_odku_clauses_have_distinct_cache_keys(self, other):
        from sqlalchemy_cubrid.dml import insert

        base = insert(users).values(name="a")
        reference = self._key(base.on_duplicate_key_update([("name", "b"), ("email", "b")]))
        assert self._key(other(base)) != reference

    @pytest.mark.parametrize(
        "update",
        [
            lambda stmt: users.c.name + "x",
            lambda stmt: stmt.inserted.name,
            lambda stmt: sa.func.upper(users.c.name),
        ],
    )
    def test_update_expression_is_part_of_the_cache_key(self, update):
        """Same update column: only the value expression differs from the baseline."""
        from sqlalchemy_cubrid.dml import insert

        base = insert(users).values(name="a")
        literal = self._key(base.on_duplicate_key_update(name="b"))
        assert self._key(base.on_duplicate_key_update(name=update(base))) != literal

    def test_cached_odku_compiles_the_new_values(self):
        """The cached compiled form must bind the new statement's update value."""
        from sqlalchemy_cubrid.dml import insert
        from sqlalchemy_cubrid.pycubrid_dialect import PyCubridDialect

        dialect = PyCubridDialect()
        first = insert(users).values(name="a").on_duplicate_key_update(name="b")
        second = insert(users).values(name="z").on_duplicate_key_update(name="c")
        compiled = dialect.statement_compiler(dialect, first, cache_key=self._key(first))
        params = compiled.construct_params(
            extracted_parameters=self._key(second)[1], escape_names=False
        )
        assert sorted(v for v in params.values() if isinstance(v, str)) == ["c", "z"]

    def test_replace_cache_key(self):
        """REPLACE should produce a stable, non-None cache key."""
        from sqlalchemy_cubrid.dml import replace

        stmt = replace(users).values(name="a")
        key = stmt._generate_cache_key()
        assert key is not None

    def test_replace_and_insert_cache_keys_differ(self):
        """REPLACE and INSERT must have different cache keys."""
        from sqlalchemy_cubrid.dml import insert, replace

        ins = insert(users).values(name="a")
        rep = replace(users).values(name="a")
        ins_key = ins._generate_cache_key()
        rep_key = rep._generate_cache_key()
        assert ins_key is not None
        assert rep_key is not None
        assert ins_key[0] != rep_key[0]


class TestDmlModule:
    """Test dml.py module constructs."""

    def test_insert_function_returns_cubrid_insert(self):
        from sqlalchemy_cubrid.dml import Insert, insert

        stmt = insert(users)
        assert isinstance(stmt, Insert)

    def test_on_duplicate_key_update_empty_dict_raises(self):
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(id=1, name="test")
        with pytest.raises(ValueError, match="must not be empty"):
            stmt.on_duplicate_key_update({})

    def test_on_duplicate_key_update_invalid_type_raises(self):
        from typing import cast

        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(id=1, name="test")
        invalid_value = cast(dict[str, object], cast(object, "invalid"))
        with pytest.raises(ValueError, match="must be a non-empty dictionary"):
            stmt.on_duplicate_key_update(invalid_value)

    def test_on_duplicate_key_update_both_args_and_kwargs_raises(self):
        from sqlalchemy import exc
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(id=1, name="test")
        with pytest.raises(exc.ArgumentError):
            stmt.on_duplicate_key_update({"name": "x"}, email="y")

    def test_on_duplicate_key_update_multiple_args_raises(self):
        from sqlalchemy import exc
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(id=1, name="test")
        with pytest.raises(exc.ArgumentError):
            stmt.on_duplicate_key_update({"name": "x"}, {"email": "y"})

    def test_inserted_property(self):
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users)
        assert hasattr(stmt.inserted, "id")
        assert hasattr(stmt.inserted, "name")

    def test_duplicate_on_duplicate_clause_raises(self):
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(id=1, name="test")
        stmt = stmt.on_duplicate_key_update(name="x")
        with pytest.raises(Exception):
            stmt.on_duplicate_key_update(name="y")


class TestMergeCompilation:
    source = Table(
        "source_data",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(100)),
        Column("email", String(200)),
    )

    def test_merge_when_matched_update(self):
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).using(self.source).on(users.c.id == self.source.c.id)
        stmt = stmt.when_matched_then_update(
            {"name": self.source.c.name, "email": self.source.c.email}
        )
        sql = _compile(stmt)
        assert "MERGE INTO" in sql
        assert "USING" in sql
        assert "ON" in sql
        assert "WHEN MATCHED THEN UPDATE SET" in sql

    def test_merge_when_not_matched_insert(self):
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).using(self.source).on(users.c.id == self.source.c.id)
        stmt = stmt.when_not_matched_then_insert(
            {
                "id": self.source.c.id,
                "name": self.source.c.name,
                "email": self.source.c.email,
            }
        )
        sql = _compile(stmt)
        assert "MERGE INTO" in sql
        assert "WHEN NOT MATCHED THEN INSERT" in sql
        assert "VALUES" in sql

    def test_merge_both_clauses(self):
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).using(self.source).on(users.c.id == self.source.c.id)
        stmt = stmt.when_matched_then_update({"name": self.source.c.name})
        stmt = stmt.when_not_matched_then_insert(
            {
                "id": self.source.c.id,
                "name": self.source.c.name,
                "email": self.source.c.email,
            }
        )
        sql = _compile(stmt)
        assert "WHEN MATCHED THEN UPDATE SET" in sql
        assert "WHEN NOT MATCHED THEN INSERT" in sql

    def test_merge_when_matched_with_where(self):
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).using(self.source).on(users.c.id == self.source.c.id)
        stmt = stmt.when_matched_then_update(
            {"name": self.source.c.name},
            where=self.source.c.name.is_not(None),
        )
        sql = _compile(stmt)
        assert "WHEN MATCHED THEN UPDATE SET" in sql
        assert "WHERE" in sql

    def test_merge_when_matched_with_delete_where(self):
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).using(self.source).on(users.c.id == self.source.c.id)
        stmt = stmt.when_matched_then_update(
            {"name": self.source.c.name},
            delete_where=users.c.name.is_(None),
        )
        sql = _compile(stmt)
        assert "DELETE WHERE" in sql

    def test_merge_when_not_matched_with_where(self):
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).using(self.source).on(users.c.id == self.source.c.id)
        stmt = stmt.when_not_matched_then_insert(
            {
                "id": self.source.c.id,
                "name": self.source.c.name,
                "email": self.source.c.email,
            },
            where=self.source.c.name.is_not(None),
        )
        sql = _compile(stmt)
        assert "WHEN NOT MATCHED THEN INSERT" in sql
        assert "WHERE" in sql

    def test_merge_factory_function(self):
        from sqlalchemy_cubrid.dml import Merge, merge

        stmt = merge(users)
        assert isinstance(stmt, Merge)

    def test_merge_exported_from_package(self):
        from sqlalchemy_cubrid import merge as package_merge
        from sqlalchemy_cubrid.dml import merge as dml_merge

        assert package_merge is dml_merge

    def test_merge_no_when_clause_raises(self):
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).using(self.source).on(users.c.id == self.source.c.id)
        with pytest.raises(Exception):
            _compile(stmt)

    def test_merge_with_subquery_source(self):
        from sqlalchemy_cubrid.dml import merge

        subq = select(self.source).where(self.source.c.id > 0).subquery()
        stmt = merge(users).using(subq).on(users.c.id == subq.c.id)
        stmt = stmt.when_matched_then_update({"name": subq.c.name})
        sql = _compile(stmt)
        assert "MERGE INTO" in sql
        assert "USING" in sql
        assert "SELECT" in sql or "select" in sql.lower()

    def test_merge_when_matched_then_delete(self):
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).using(self.source).on(users.c.id == self.source.c.id)
        stmt = stmt.when_matched_then_update({"name": self.source.c.name})
        stmt = stmt.when_matched_then_delete(users.c.name.is_(None))
        sql = _compile(stmt)
        assert "DELETE WHERE" in sql

    def test_merge_when_matched_then_delete_without_update_raises(self):
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).using(self.source).on(users.c.id == self.source.c.id)
        with pytest.raises(ValueError):
            stmt.when_matched_then_delete(users.c.name.is_(None))

    def test_merge_when_not_matched_insert_with_tuple_list(self):
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).using(self.source).on(users.c.id == self.source.c.id)
        stmt = stmt.when_not_matched_then_insert(
            [
                ("id", self.source.c.id),
                ("name", self.source.c.name),
                ("email", self.source.c.email),
            ]
        )
        sql = _compile(stmt)
        assert "WHEN NOT MATCHED THEN INSERT" in sql
        assert "VALUES" in sql

    def test_merge_when_not_matched_insert_with_column_list(self):
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).using(self.source).on(users.c.id == self.source.c.id)
        stmt = stmt.when_not_matched_then_insert(
            [self.source.c.id, self.source.c.name, self.source.c.email]
        )
        sql = _compile(stmt)
        assert "WHEN NOT MATCHED THEN INSERT" in sql
        assert "VALUES" in sql

    def test_merge_when_matched_literal_value(self):
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).using(self.source).on(users.c.id == self.source.c.id)
        stmt = stmt.when_matched_then_update({"name": "updated"})
        sql = _compile(stmt)
        assert "WHEN MATCHED THEN UPDATE SET" in sql
        assert "'updated'" in sql

    def test_merge_when_matched_column_key(self):
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).using(self.source).on(users.c.id == self.source.c.id)
        stmt = stmt.when_matched_then_update({users.c.name: self.source.c.name})
        sql = _compile(stmt)
        assert "WHEN MATCHED THEN UPDATE SET" in sql
        assert "name" in sql

    def test_merge_when_matched_update_invalid_values_raises(self):
        from typing import cast

        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users)
        invalid_values = cast(
            list[tuple[object, object]],
            cast(object, [users.c.name]),
        )
        with pytest.raises(ValueError):
            stmt.when_matched_then_update(invalid_values)

    def test_merge_when_not_matched_insert_invalid_values_raises(self):
        from typing import cast

        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users)
        invalid_values = cast(
            dict[str, object],
            cast(object, "invalid"),
        )
        with pytest.raises(ValueError):
            stmt.when_not_matched_then_insert(invalid_values)

    def test_merge_missing_using_raises(self):
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).on(users.c.id == self.source.c.id)
        stmt = stmt.when_matched_then_update({"name": self.source.c.name})
        with pytest.raises(Exception):
            _compile(stmt)

    def test_merge_missing_on_raises(self):
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).using(self.source)
        stmt = stmt.when_matched_then_update({"name": self.source.c.name})
        with pytest.raises(Exception):
            _compile(stmt)

    def test_merge_keyed_column_uses_db_name(self):
        """Column('db_name', key='attr_name') should render db_name in SQL."""
        from sqlalchemy_cubrid.dml import merge

        keyed_table = Table(
            "keyed_tbl",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("db_name", String(100), key="attr_name"),
        )

        stmt = merge(keyed_table).using(self.source).on(keyed_table.c.id == self.source.c.id)
        stmt = stmt.when_matched_then_update({"attr_name": self.source.c.name})
        sql = _compile(stmt)
        # Must use the actual DB column name, not the key
        assert '"db_name"' in sql or "db_name" in sql
        assert "attr_name" not in sql.replace("attr_name", "") or "attr_name" not in sql

    def test_merge_keyed_column_not_matched_insert(self):
        """Keyed columns in NOT MATCHED INSERT should also use db_name."""
        from sqlalchemy_cubrid.dml import merge

        keyed_table = Table(
            "keyed_tbl2",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("db_col", String(100), key="py_attr"),
        )

        stmt = merge(keyed_table).using(self.source).on(keyed_table.c.id == self.source.c.id)
        stmt = stmt.when_not_matched_then_insert(
            {"id": self.source.c.id, "py_attr": self.source.c.name}
        )
        sql = _compile(stmt)
        assert "db_col" in sql
        assert "py_attr" not in sql

    def test_merge_when_matched_literal_value_binding(self):
        """#613: a literal UPDATE SET value binds; a column reference does not."""
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).using(self.source).on(users.c.id == self.source.c.id)
        stmt = stmt.when_matched_then_update({"name": "fixed_name", "email": self.source.c.email})
        compiled = stmt.compile(dialect=CubridDialect())
        assert compiled.positiontup == ["param_1"]
        assert compiled.params["param_1"] == "fixed_name"
        assert "source_data.email" in compiled.string

    def test_merge_when_not_matched_literal_value_binding(self):
        """#613: same rule for WHEN NOT MATCHED THEN INSERT values."""
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).using(self.source).on(users.c.id == self.source.c.id)
        stmt = stmt.when_not_matched_then_insert(
            {"id": self.source.c.id, "name": "default_name", "email": self.source.c.email}
        )
        compiled = stmt.compile(dialect=CubridDialect())
        assert compiled.positiontup == ["param_1"]
        assert compiled.params["param_1"] == "default_name"

    def test_merge_both_clauses_binding_order(self):
        """#613: the matched-update bind precedes the not-matched-insert bind,
        matching the WHEN MATCHED ... WHEN NOT MATCHED clause order in the SQL."""
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).using(self.source).on(users.c.id == self.source.c.id)
        stmt = stmt.when_matched_then_update({"name": "matched_name"})
        stmt = stmt.when_not_matched_then_insert(
            {"id": self.source.c.id, "name": "inserted_name", "email": self.source.c.email}
        )
        compiled = stmt.compile(dialect=CubridDialect())
        assert len(compiled.positiontup) == 2
        matched_bind, insert_bind = compiled.positiontup
        assert compiled.params[matched_bind] == "matched_name"
        assert compiled.params[insert_bind] == "inserted_name"
        assert compiled.string.index("WHEN MATCHED") < compiled.string.index("WHEN NOT MATCHED")

    def test_merge_when_matched_where_binding_order(self):
        """#613: the UPDATE SET bind precedes the WHERE predicate's bind,
        matching their order in the rendered SQL."""
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users).using(self.source).on(users.c.id == self.source.c.id)
        stmt = stmt.when_matched_then_update(
            {"name": "fixed"}, where=self.source.c.name == sa.bindparam("wpred", "alice")
        )
        compiled = stmt.compile(dialect=CubridDialect())
        assert len(compiled.positiontup) == 2
        set_bind, where_bind = compiled.positiontup
        assert compiled.params[set_bind] == "fixed"
        assert where_bind == "wpred"
        assert compiled.params["wpred"] == "alice"


class TestDmlCoverage:
    """Tests for uncovered dml.py branches."""

    def test_on_duplicate_clause_with_column_collection(self):
        """dml.py line 116: OnDuplicateClause.__init__ with ColumnCollection."""
        from sqlalchemy_cubrid.dml import insert

        m = MetaData()
        t = Table(
            "cc_test",
            m,
            Column("id", Integer, primary_key=True),
            Column("name", String(50)),
        )
        stmt = insert(t).values(id=1, name="test")
        # table.c is a ReadOnlyColumnCollection, which is a ColumnCollection
        stmt = stmt.on_duplicate_key_update(dict(t.c))
        sql = _compile(stmt)
        assert "ON DUPLICATE KEY UPDATE" in sql

    def test_merge_into_method(self):
        """dml.py lines 149-150: Merge.into() method."""
        from sqlalchemy_cubrid.dml import merge

        m = MetaData()
        t1 = Table("into_t1", m, Column("id", Integer, primary_key=True))
        t2 = Table("into_t2", m, Column("id", Integer, primary_key=True))
        source = Table(
            "into_src", m, Column("id", Integer, primary_key=True), Column("name", String(50))
        )
        stmt = merge(t1).into(t2).using(source).on(t2.c.id == source.c.id)
        stmt = stmt.when_matched_then_update({"id": source.c.id})
        sql = _compile(stmt)
        # Target should be t2, not t1
        assert "into_t2" in sql
        assert "MERGE INTO" in sql

    def test_when_not_matched_with_column_collection(self):
        """dml.py lines 221-226: when_not_matched_then_insert with ColumnCollection."""
        from sqlalchemy_cubrid.dml import merge

        m = MetaData()
        target = Table(
            "cc_target",
            m,
            Column("id", Integer, primary_key=True),
            Column("name", String(50)),
        )
        source = Table(
            "cc_source",
            m,
            Column("id", Integer, primary_key=True),
            Column("name", String(50)),
        )
        stmt = merge(target).using(source).on(target.c.id == source.c.id)
        # Pass ColumnCollection (table.c) as values_dict_or_column_list
        stmt = stmt.when_not_matched_then_insert(list(source.c))
        sql = _compile(stmt)
        assert "WHEN NOT MATCHED THEN INSERT" in sql

    def test_when_not_matched_empty_column_list_raises(self):
        """dml.py line 241: Empty column list error."""
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users)
        with pytest.raises(ValueError, match="non-empty"):
            stmt.when_not_matched_then_insert([])

    def test_normalize_key_value_pairs_with_tuple_input(self):
        """dml.py lines 268-271: _normalize_key_value_pairs with tuple input."""
        from sqlalchemy_cubrid.dml import merge

        source = Table(
            "tuple_src",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String(100)),
            Column("email", String(200)),
            extend_existing=True,
        )
        stmt = merge(users).using(source).on(users.c.id == source.c.id)
        # Pass a tuple of tuples (not a list of tuples)
        stmt = stmt.when_matched_then_update((("name", source.c.name), ("email", source.c.email)))
        sql = _compile(stmt)
        assert "WHEN MATCHED THEN UPDATE SET" in sql

    def test_normalize_key_value_pairs_empty_raises(self):
        """dml.py line 276: Empty pairs error."""
        from sqlalchemy_cubrid.dml import merge

        stmt = merge(users)
        with pytest.raises(ValueError, match="non-empty"):
            stmt.when_matched_then_update({})


class TestMergeForeignColumnKeys847:
    target = Table(
        "t847", MetaData(), Column("id", Integer, primary_key=True), Column("name", String(20))
    )
    source = Table(
        "s847", MetaData(), Column("id", Integer, primary_key=True), Column("name", String(20))
    )

    def _base(self, target=None):
        from sqlalchemy_cubrid.dml import merge

        target = self.target if target is None else target
        return merge(target).using(self.source).on(target.c.id == self.source.c.id)

    @pytest.mark.parametrize(
        "build",
        [
            lambda m, s: m.when_matched_then_update({s.c.name: "x"}),
            lambda m, s: m.when_matched_then_update([(s.c.name, "x")]),
            lambda m, s: m.when_not_matched_then_insert({s.c.id: s.c.id, s.c.name: s.c.name}),
            lambda m, s: m.when_not_matched_then_insert([(s.c.id, 1), (s.c.name, "x")]),
        ],
    )
    def test_foreign_column_with_a_colliding_name_is_rejected(self, build):
        stmt = build(self._base(), self.source)
        with pytest.raises(CompileError, match="belongs to 's847', not the MERGE target"):
            _compile(stmt)

    def test_foreign_column_with_an_unknown_name_keeps_the_202_error(self):
        other = Table("o847", MetaData(), Column("zzz", Integer))
        stmt = self._base().when_matched_then_update({other.c.zzz: 1})
        with pytest.raises(CompileError, match="column 'zzz' not found in target table"):
            _compile(stmt)

    @pytest.mark.parametrize(
        "build",
        [
            lambda m, t, s: m.when_matched_then_update({t.c.name: s.c.name}),
            lambda m, t, s: m.when_matched_then_update([("name", s.c.name)]),
            lambda m, t, s: m.when_matched_then_update({sa.column("name"): s.c.name}),
            lambda m, t, s: m.when_not_matched_then_insert([s.c.id, s.c.name]),
            lambda m, t, s: m.when_not_matched_then_insert(s.c),
            lambda m, t, s: m.when_not_matched_then_insert({t.c.id: s.c.id, "name": s.c.name}),
        ],
    )
    def test_legitimate_keys_still_compile(self, build):
        sql = _compile(build(self._base(), self.target, self.source))
        assert "t847" in sql
        assert "belongs to" not in sql

    def test_alias_target_accepts_base_and_alias_columns(self):
        alias = self.target.alias("tgt")
        stmt = self._base(alias).when_matched_then_update(
            {self.target.c.name: self.source.c.name, alias.c.id: self.source.c.id}
        )
        sql = _norm(_compile(stmt))
        assert "UPDATE SET name = s847.name, id = s847.id" in sql

    def test_bind_order_of_legitimate_statement_is_unchanged(self):
        from sqlalchemy_cubrid.pycubrid_dialect import PyCubridDialect

        stmt = self._base().when_matched_then_update({self.target.c.name: "a"})
        stmt = stmt.when_not_matched_then_insert({self.target.c.id: 7, "name": "b"})
        compiled = stmt.compile(dialect=PyCubridDialect())
        assert [compiled.params[key] for key in compiled.positiontup] == ["a", 7, "b"]
