# test/test_compiler.py
"""Offline compiler tests — no live CUBRID required.

Uses SQLAlchemy's compilation API to verify SQL generation without
a database connection. This module covers SELECT-side SQL (joins, CTEs,
window functions, LIMIT/OFFSET and FETCH, boolean and IS predicates,
literals and functions) and checks that span several statement kinds
(positional bind order, forwarded compile options). DML, DDL and type
compilation live in ``test_compiler_dml.py``, ``test_compiler_ddl.py`` and
``test_compiler_types.py``; shared helpers in ``_compiler_helpers.py``.
"""

from __future__ import annotations

import operator
import warnings

import pytest
import sqlalchemy as sa
from typing import Any, cast
from sqlalchemy import Column, Integer, MetaData, String, Table, select
from sqlalchemy.exc import CompileError

from sqlalchemy_cubrid import types as cubrid_types
from sqlalchemy_cubrid._compat import (
    bind_with_type,
    get_distinct,
    get_for_update_arg,
    get_limit_clause,
    get_offset_clause,
    is_literal_value,
)
from sqlalchemy_cubrid.compiler import _CUBRID_OFFSET_NO_LIMIT_ROW_COUNT
from sqlalchemy_cubrid.dialect import CubridDialect
from test._compiler_helpers import _compile, _norm, metadata, users


# Boolean expressions that need parentheses when used as operands or arguments.
_and = sa.and_(users.c.name == "a", users.c.id == 1)


_exists = sa.exists().where(users.c.name == "a")


class TestSelectCompilation:
    """Test SELECT statement compilation."""

    def test_simple_select(self):
        stmt = select(users)
        sql = _compile(stmt)
        assert "SELECT" in sql
        assert "users" in sql

    def test_select_distinct(self):
        stmt = select(users.c.name).distinct()
        sql = _compile(stmt)
        assert "DISTINCT" in sql

    def test_select_limit(self):
        stmt = select(users).limit(10)
        sql = _compile(stmt)
        assert "LIMIT" in sql
        assert "10" in sql

    def test_select_limit_exact_clause(self):
        stmt = select(users.c.id).limit(10)
        assert _norm(_compile(stmt)) == "SELECT users.id FROM users LIMIT 10"

    def test_select_offset(self):
        stmt = select(users).offset(5)
        sql = _compile(stmt)
        assert "LIMIT" in sql
        assert "5" in sql
        assert str(_CUBRID_OFFSET_NO_LIMIT_ROW_COUNT) in sql

    def test_select_offset_does_not_cap_at_varchar_length(self):
        # Regression for #414: offset-without-limit must not reuse the CUBRID
        # VARCHAR-length constant (2^30-1) as the row_count, which silently
        # caps result sets at ~1.07B rows. It must also stay below 2^63-1 so
        # CUBRID's internal offset+row_count addition does not overflow.
        stmt = select(users).offset(5)
        sql = _compile(stmt)
        assert "1073741823" not in sql
        assert _CUBRID_OFFSET_NO_LIMIT_ROW_COUNT == 4611686018427387904

    def test_select_limit_offset(self):
        stmt = select(users).limit(10).offset(5)
        sql = _compile(stmt)
        assert "LIMIT" in sql
        # CUBRID uses LIMIT offset, count
        assert "5" in sql
        assert "10" in sql

    def test_select_limit_offset_exact_clause(self):
        # CUBRID renders `LIMIT <offset>, <count>` (offset first). Exact match
        # guards the operand order and the comma-separated two-argument form.
        stmt = select(users.c.id).limit(10).offset(5)
        assert _norm(_compile(stmt)) == "SELECT users.id FROM users LIMIT 5, 10"

    def test_select_offset_only_exact_clause(self):
        # Offset without limit still emits the two-argument form, with the
        # sentinel row_count as the second operand.
        stmt = select(users.c.id).offset(7)
        assert _norm(_compile(stmt)) == (
            f"SELECT users.id FROM users LIMIT 7, {_CUBRID_OFFSET_NO_LIMIT_ROW_COUNT}"
        )

    def test_select_no_limit(self):
        stmt = select(users)
        sql = _compile(stmt)
        assert "LIMIT" not in sql

    def test_for_update_basic(self):
        """CUBRID supports FOR UPDATE; clause should be present."""
        stmt = select(users).with_for_update()
        sql = _compile(stmt)
        assert sql.strip().endswith("FOR UPDATE")

    def test_for_update_of_columns(self):
        """FOR UPDATE OF col1, col2 should render correctly."""
        stmt = select(users).with_for_update(of=[users.c.id, users.c.name])
        sql = _compile(stmt)
        assert "FOR UPDATE OF" in sql
        assert "users.id" in sql
        assert "users.name" in sql

    def test_for_update_nowait_raises(self):
        """CUBRID does not support NOWAIT; must raise CompileError."""
        stmt = select(users).with_for_update(nowait=True)
        with pytest.raises(CompileError, match="NOWAIT"):
            _compile(stmt)

    def test_for_update_skip_locked_raises(self):
        """CUBRID does not support SKIP LOCKED; must raise CompileError."""
        stmt = select(users).with_for_update(skip_locked=True)
        with pytest.raises(CompileError, match="SKIP LOCKED"):
            _compile(stmt)

    def test_for_update_read_raises(self):
        """CUBRID does not support FOR SHARE; must raise CompileError."""
        stmt = select(users).with_for_update(read=True)
        with pytest.raises(CompileError, match="FOR SHARE"):
            _compile(stmt)

    def test_for_update_key_share_raises(self):
        """CUBRID does not support FOR KEY SHARE; must raise CompileError."""
        stmt = select(users).with_for_update(key_share=True)
        with pytest.raises(CompileError, match="KEY SHARE"):
            _compile(stmt)


class TestBooleanSelectColumns:
    """EXISTS, NOT and AND/OR as a SELECT-list item are grouped (#966, #968, #970).

    CUBRID rejects ``SELECT EXISTS (SELECT 1)``, ``SELECT NOT (...)`` and
    ``SELECT a AND b`` but accepts each inside parentheses.
    """

    _where = users.c.name == "a"

    @pytest.mark.parametrize(
        ("column", "expected"),
        [
            (
                sa.exists().where(users.c.name == "a"),
                "SELECT (EXISTS (SELECT * FROM users WHERE users.name = 'a')) AS anon_1",
            ),
            (
                ~sa.exists().where(users.c.name == "a"),
                "SELECT (NOT (EXISTS (SELECT * FROM users WHERE users.name = 'a'))) AS anon_1",
            ),
            (
                sa.and_(users.c.name == "a", users.c.id == 1),
                "SELECT (users.name = 'a' AND users.id = 1) AS anon_1 FROM users",
            ),
            (
                sa.or_(users.c.name == "a", users.c.id == 1).label("x"),
                "SELECT (users.name = 'a' OR users.id = 1) AS x FROM users",
            ),
            (
                sa.and_(users.c.name == "a", sa.or_(users.c.id == 1, users.c.id == 2)),
                "SELECT (users.name = 'a' AND (users.id = 1 OR users.id = 2)) AS anon_1 FROM users",
            ),
        ],
        ids=["exists", "not-exists", "and", "or-labelled", "nested-or-once"],
    )
    def test_column_is_grouped(self, column, expected):
        assert _norm(_compile(select(column))).startswith(expected)

    def test_exists_select_and_subquery_columns_are_grouped(self):
        exists = sa.exists().where(self._where)
        assert _norm(_compile(exists.select())).startswith("SELECT (EXISTS (SELECT *")
        sql = _norm(_compile(select(select(exists.label("x")).subquery())))
        assert "FROM (SELECT (EXISTS (SELECT * FROM users WHERE users.name = 'a')) AS x" in sql

    def test_orm_query_exists_is_grouped(self):
        from sqlalchemy import orm

        class Base(orm.DeclarativeBase):
            pass

        class User(Base):
            __tablename__ = "orm_users"
            id = Column(Integer, primary_key=True)
            name = Column(String(10))

        session = orm.Session()
        query = session.query(session.query(User).filter(User.name == "a").exists())
        assert _norm(_compile(query.statement)).startswith(
            "SELECT (EXISTS (SELECT 1 FROM orm_users WHERE orm_users.name = 'a')) AS anon_1"
        )

    @pytest.mark.parametrize(
        ("stmt", "expected"),
        [
            (
                select(users.c.id).where(sa.exists().where(users.c.name == "a")),
                "WHERE EXISTS (SELECT * FROM users WHERE users.name = 'a')",
            ),
            (
                select(users.c.id).where(~sa.exists().where(users.c.name == "a")),
                "WHERE NOT (EXISTS (SELECT * FROM users WHERE users.name = 'a'))",
            ),
            (
                select(users.c.id).where(sa.and_(users.c.name == "a", users.c.id == 1)),
                "WHERE users.name = 'a' AND users.id = 1",
            ),
            (
                select(sa.case((sa.exists().where(users.c.name == "a"), 1), else_=0)),
                "SELECT CASE WHEN (EXISTS (SELECT * FROM users WHERE users.name = 'a')) THEN 1",
            ),
            (
                select(sa.case((sa.and_(users.c.name == "a", users.c.id == 1), 1), else_=0)),
                "SELECT CASE WHEN (users.name = 'a' AND users.id = 1) THEN 1",
            ),
        ],
        ids=["where-exists", "where-not-exists", "where-and", "case-exists", "case-and"],
    )
    def test_other_positions_are_unchanged(self, stmt, expected):
        assert expected in _norm(_compile(stmt))

    @pytest.mark.parametrize(
        ("column", "expected"),
        [
            (
                sa.type_coerce(sa.exists().where(users.c.name == "a"), sa.Boolean),
                "SELECT (EXISTS (SELECT * FROM users WHERE users.name = 'a')) AS anon_1",
            ),
            (
                sa.cast(sa.and_(users.c.name == "a", users.c.id == 1), Integer),
                "SELECT CAST((users.name = 'a' AND users.id = 1) AS INTEGER) AS anon_1",
            ),
            (
                sa.func.coalesce(sa.exists().where(users.c.name == "a"), False),
                "SELECT coalesce((EXISTS (SELECT * FROM users WHERE users.name = 'a')), 0)",
            ),
            (
                sa.func.coalesce(sa.or_(users.c.name == "a", users.c.id == 1), 0).label("x"),
                "SELECT coalesce((users.name = 'a' OR users.id = 1), 0) AS x",
            ),
            (
                sa.cast(sa.func.coalesce(~sa.exists().where(users.c.name == "a"), 0), Integer),
                "SELECT CAST(coalesce((NOT (EXISTS (SELECT * FROM users WHERE users.name = 'a')))"
                ", 0) AS INTEGER)",
            ),
        ],
        ids=["type-coerce-exists", "cast-and", "coalesce-exists", "coalesce-or", "cast-coalesce"],
    )
    def test_wrapped_column_is_grouped(self, column, expected):
        """A boolean column wrapped in a type coercion, CAST or function (#968)."""
        assert _norm(_compile(select(column))).startswith(expected)

    def test_type_decorator_column_expression_is_grouped(self):
        class Flag(sa.TypeDecorator):
            impl = Integer
            cache_ok = True

            def column_expression(self, col):
                return sa.func.coalesce(col, 0)

        sql = _norm(_compile(select(sa.type_coerce(_and, Flag()))))
        assert sql.startswith("SELECT coalesce((users.name = 'a' AND users.id = 1), 0) AS anon_1")

    @pytest.mark.parametrize(
        ("order_by", "expected"),
        [
            (_and, "ORDER BY (users.name = 'a' AND users.id = 1)"),
            (_exists, "ORDER BY (EXISTS (SELECT * FROM users WHERE users.name = 'a'))"),
            (~_exists, "ORDER BY (NOT (EXISTS (SELECT * FROM users WHERE users.name = 'a')))"),
            (
                _exists.desc().nulls_last(),
                "ORDER BY (EXISTS (SELECT * FROM users WHERE users.name = 'a')) DESC NULLS LAST",
            ),
            (
                sa.cast(_and, Integer),
                "ORDER BY CAST((users.name = 'a' AND users.id = 1) AS INTEGER)",
            ),
            (
                sa.cast(_and, Integer).label("k"),
                "ORDER BY CAST((users.name = 'a' AND users.id = 1) AS INTEGER)",
            ),
            (
                sa.func.coalesce(_exists, 0).label("k").desc(),
                "ORDER BY coalesce((EXISTS (SELECT * FROM users WHERE users.name = 'a')), 0) DESC",
            ),
        ],
        ids=[
            "and",
            "exists",
            "not-exists",
            "exists-desc-nulls-last",
            "cast-and",
            "unselected-label-cast",
            "unselected-label-function-desc",
        ],
    )
    def test_order_by_item_is_grouped(self, order_by, expected):
        sql = _norm(_compile(select(users.c.id).order_by(order_by, users.c.name)))
        assert sql.endswith(expected + ", users.name")

    @pytest.mark.parametrize(
        ("stmt", "expected"),
        [
            (
                select(users.c.id).where(sa.func.coalesce(_and, 0) == 1),
                "WHERE coalesce((users.name = 'a' AND users.id = 1), 0) = 1",
            ),
            (
                select(users.c.id).where(sa.cast(~_exists, Integer) == 1),
                "WHERE CAST((NOT (EXISTS (SELECT * FROM users WHERE users.name = 'a'))) AS INTEGER) = 1",
            ),
            (
                select(sa.func.count()).select_from(users).having(sa.cast(_and, Integer) == 1),
                "HAVING CAST((users.name = 'a' AND users.id = 1) AS INTEGER) = 1",
            ),
            (
                select(users.c.id).select_from(
                    users.join(users.alias("u"), sa.func.coalesce(_and, 0) == 1)
                ),
                "ON coalesce((users.name = 'a' AND users.id = 1), 0) = 1",
            ),
            (
                sa.update(users).values(id=sa.cast(_and, Integer)),
                "SET id=CAST((users.name = 'a' AND users.id = 1) AS INTEGER)",
            ),
            (
                select(sa.func.row_number().over(order_by=_exists)),
                "OVER (ORDER BY (EXISTS (SELECT * FROM users WHERE users.name = 'a')))",
            ),
            (
                select(sa.func.row_number().over(order_by=~(users.c.id == 1))),
                "OVER (ORDER BY users.id != 1)",
            ),
            (
                select(sa.func.row_number().over(order_by=(~_exists).desc())),
                "OVER (ORDER BY (NOT (EXISTS (SELECT * FROM users WHERE users.name = 'a'))) DESC)",
            ),
            (
                select(sa.func.row_number().over(partition_by=[_exists, users.c.id])),
                "OVER (PARTITION BY (EXISTS (SELECT * FROM users WHERE users.name = 'a')), users.id)",
            ),
            (
                select(sa.func.sum(users.c.id).over(order_by=sa.func.coalesce(_and, 0))),
                "OVER (ORDER BY coalesce((users.name = 'a' AND users.id = 1), 0))",
            ),
            (
                select(sa.func.percentile_cont(0.5).within_group(~_exists)),
                "WITHIN GROUP (ORDER BY (NOT (EXISTS (SELECT * FROM users WHERE users.name = 'a'))))",
            ),
            (
                select(sa.func.percentile_cont(0.5).within_group(_and)),
                "WITHIN GROUP (ORDER BY (users.name = 'a' AND users.id = 1))",
            ),
            (
                select(sa.func.row_number().over(order_by=[_and, users.c.id])),
                "OVER (ORDER BY (users.name = 'a' AND users.id = 1), users.id)",
            ),
            # CUBRID rejects a search condition as a GROUP BY item even in
            # parentheses; the function groups its argument wherever it appears.
            (
                select(sa.func.count()).select_from(users).group_by(sa.func.coalesce(_exists, 0)),
                "GROUP BY coalesce((EXISTS (SELECT * FROM users WHERE users.name = 'a')), 0)",
            ),
        ],
        ids=[
            "where-function",
            "where-cast-not-exists",
            "having-cast",
            "on-function",
            "update-set-cast",
            "window-order-by-exists",
            "window-order-by-negated-comparison",
            "window-order-by-not-desc",
            "window-partition-by-exists",
            "window-order-by-function",
            "within-group-not-exists",
            "within-group-and",
            "window-order-by-and-in-list",
            "group-by-function",
        ],
    )
    def test_grouped_outside_select_list(self, stmt, expected):
        """A CAST or function argument anywhere, and window BY items, are grouped (#970)."""
        assert expected in _norm(_compile(stmt))

    @pytest.mark.parametrize(
        ("stmt", "expected"),
        [
            (
                select(sa.func.count()).select_from(users).group_by(_and),
                "GROUP BY users.name = 'a' AND users.id = 1",
            ),
            (
                select(users.c.id).order_by(sa.case((_and, 1), else_=0)),
                "ORDER BY CASE WHEN (users.name = 'a' AND users.id = 1) THEN 1 ELSE 0 END",
            ),
            (
                select(sa.func.coalesce(users.c.name == "a", False)),
                "SELECT coalesce(users.name = 'a', 0)",
            ),
            # SQLAlchemy splits an and_() given as a window ORDER BY into items.
            (
                select(sa.func.row_number().over(order_by=_and)),
                "OVER (ORDER BY users.name = 'a', users.id = 1)",
            ),
            (
                select(sa.func.row_number().over(partition_by=users.c.name, order_by=users.c.id)),
                "OVER (PARTITION BY users.name ORDER BY users.id)",
            ),
        ],
        ids=[
            "group-by",
            "order-by-case",
            "comparison-argument",
            "window-order-by-and-split",
            "window-plain-items",
        ],
    )
    def test_wrapped_other_positions_are_unchanged(self, stmt, expected):
        """GROUP BY items, CASE conditions and non-boolean operands are not grouped."""
        assert expected in _norm(_compile(stmt))

    @pytest.mark.parametrize(
        ("case", "expected"),
        [
            (
                sa.case((users.c.id > 0, _and), else_=sa.literal(False)),
                "CASE WHEN (users.id > 0) THEN (users.name = 'a' AND users.id = 1) ELSE 0 END",
            ),
            (
                sa.case((users.c.id < 0, sa.literal(False)), else_=_and),
                "CASE WHEN (users.id < 0) THEN 0 ELSE (users.name = 'a' AND users.id = 1) END",
            ),
            (
                sa.case((users.c.id > 0, _exists), else_=sa.literal(False)),
                "CASE WHEN (users.id > 0) THEN (EXISTS (SELECT * FROM users "
                "WHERE users.name = 'a')) ELSE 0 END",
            ),
            (
                sa.case(
                    {1: sa.or_(users.c.name == "a", users.c.id == 2)},
                    value=users.c.id,
                    else_=~_exists,
                ),
                "CASE users.id WHEN 1 THEN (users.name = 'a' OR users.id = 2) "
                "ELSE (NOT (EXISTS (SELECT * FROM users WHERE users.name = 'a'))) END",
            ),
            (
                sa.case((_and, _and.self_group()), else_=users.c.name == "a"),
                "CASE WHEN (users.name = 'a' AND users.id = 1) THEN "
                "(users.name = 'a' AND users.id = 1) ELSE users.name = 'a' END",
            ),
            (
                sa.case(
                    (users.c.id > 0, sa.case((users.c.id > 1, _and), else_=sa.literal(False))),
                    else_=sa.literal(False),
                ),
                "CASE WHEN (users.id > 0) THEN CASE WHEN (users.id > 1) THEN "
                "(users.name = 'a' AND users.id = 1) ELSE 0 END ELSE 0 END",
            ),
            (
                sa.case(
                    (users.c.id > 0, sa.type_coerce(_and, sa.Boolean)), else_=sa.literal(False)
                ),
                "CASE WHEN (users.id > 0) THEN (users.name = 'a' AND users.id = 1) ELSE 0 END",
            ),
            (
                sa.case((users.c.id > 0, _exists.label("k")), else_=sa.literal(False)),
                "CASE WHEN (users.id > 0) THEN (EXISTS (SELECT * FROM users "
                "WHERE users.name = 'a')) ELSE 0 END",
            ),
            (
                sa.case((users.c.id > 0, users.c.id == 1), else_=sa.literal(False)),
                "CASE WHEN (users.id > 0) THEN users.id = 1 ELSE 0 END",
            ),
        ],
        ids=[
            "then-and",
            "else-and",
            "then-exists",
            "simple-case-or-and-not-exists",
            "already-grouped-and-comparison",
            "nested-case",
            "then-type-coerce-and",
            "then-label-exists",
            "then-comparison",
        ],
    )
    def test_case_value_is_grouped(self, case, expected):
        """A CASE THEN or ELSE value is grouped; WHEN conditions render as before (#982)."""
        assert f"SELECT {expected} AS anon_1" in _norm(_compile(select(case)))
        sql = _norm(_compile(select(users.c.id).where(case == sa.literal(True))))
        assert f"WHERE {expected} = 1" in sql

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (_and, "(users.name = 'a' AND users.id = 1)"),
            (sa.or_(users.c.name == "a", users.c.id == 2), "(users.name = 'a' OR users.id = 2)"),
            (_exists, "(EXISTS (SELECT * FROM users WHERE users.name = 'a'))"),
            (~_exists, "(NOT (EXISTS (SELECT * FROM users WHERE users.name = 'a')))"),
            (_and.self_group(), "(users.name = 'a' AND users.id = 1)"),
            (users.c.id == 1, "users.id = 1"),
        ],
        ids=["and", "or", "exists", "not-exists", "already-grouped-and", "comparison"],
    )
    def test_simple_case_value_is_grouped(self, value, expected):
        """A boolean simple-case value operand is grouped (#987)."""
        case = sa.case({True: 10}, value=value, else_=20)
        expected = f"CASE {expected} WHEN 1 THEN 10 ELSE 20 END"
        assert f"SELECT {expected} AS anon_1" in _norm(_compile(select(case)))
        sql = _norm(_compile(select(users.c.id).where(case == 10)))
        assert f"WHERE {expected} = 10" in sql

    class _BaseCaseCompiler(CubridDialect.statement_compiler):
        visit_case = sa.sql.compiler.SQLCompiler.visit_case

    class _BaseCaseDialect(CubridDialect):
        pass

    _BaseCaseDialect.statement_compiler = _BaseCaseCompiler

    @pytest.mark.parametrize(
        "value",
        [
            users.c.id,
            sa.bindparam("p", 1),
            sa.func.coalesce(users.c.id, 0),
            users.c.id == 1,
            sa.type_coerce(users.c.id, Integer),
        ],
        ids=["column", "bindparam", "function", "comparison", "type-coerce-column"],
    )
    def test_simple_case_plain_value_is_unchanged(self, value):
        """A non-boolean simple-case value renders as SQLAlchemy renders it (#987)."""
        stmt = select(users.c.id, sa.case({1: 10}, value=value, else_=20))
        assert _compile(stmt) == _compile(stmt, self._BaseCaseDialect())
        params = stmt.compile(dialect=CubridDialect())
        assert params.string == stmt.compile(dialect=self._BaseCaseDialect()).string

    def test_simple_case_value_reused_elsewhere(self):
        """The same object as a simple-case value and elsewhere is grouped only as the value."""
        case = sa.case({True: 10}, value=_and, else_=20)
        bare = "users.name = 'a' AND users.id = 1"
        sql = _norm(_compile(select(case, _and).where(_and)))
        assert sql == (
            f"SELECT CASE ({bare}) WHEN 1 THEN 10 ELSE 20 END AS anon_1, ({bare}) AS anon_2 "
            f"FROM users WHERE {bare}"
        )
        case = sa.case({True: _and}, value=_and, else_=sa.literal(False))
        sql = _norm(_compile(select(case).where(_and)))
        assert sql == (
            f"SELECT CASE ({bare}) WHEN 1 THEN ({bare}) ELSE 0 END AS anon_1 "
            f"FROM users WHERE {bare}"
        )

    def test_reused_expression_is_grouped_once_per_use(self):
        """The same object is grouped once where it is an item or an argument (#968, #970)."""
        exists = sa.exists().where(users.c.name == "a")
        bare = "EXISTS (SELECT * FROM users WHERE users.name = 'a')"
        window = sa.func.row_number().over(order_by=exists)
        sql = _norm(_compile(select(users.c.id).order_by(sa.func.coalesce(exists, 0), window)))
        assert sql.endswith(
            f"ORDER BY coalesce(({bare}), 0), row_number() OVER (ORDER BY ({bare}))"
        )
        sql = _norm(_compile(select(users.c.id).where(exists).order_by(exists, window)))
        assert f"WHERE {bare} ORDER BY ({bare}), row_number() OVER (ORDER BY ({bare}))" in sql
        sql = _norm(_compile(select(sa.func.max(exists).over(order_by=exists))))
        assert sql.startswith(f"SELECT max(({bare})) OVER (ORDER BY ({bare})) AS anon_1")
        cast_ = sa.cast(exists, Integer)
        sql = _norm(_compile(select(users.c.id).order_by(cast_, sa.func.max(cast_).over())))
        assert sql.endswith(
            f"ORDER BY CAST(({bare}) AS INTEGER), max(CAST(({bare}) AS INTEGER)) OVER ()"
        )


class TestWindowItemsMatchSQLAlchemy:
    """Window and WITHIN GROUP BY lists render one item at a time (#970).

    For items that need no grouping, the output must equal SQLAlchemy's own
    visit_clauselist, which renders those lists.
    """

    class _BaseListCompiler(CubridDialect.statement_compiler):
        visit_clauselist = sa.sql.compiler.SQLCompiler.visit_clauselist

    class _BaseListDialect(CubridDialect):
        pass

    _BaseListDialect.statement_compiler = _BaseListCompiler

    @staticmethod
    def _statements() -> list[Any]:
        name = users.c.name
        row_number = sa.func.row_number()
        return [
            select(row_number.over()),
            select(row_number.over(order_by=users.c.id)),
            select(row_number.over(partition_by=[name, users.c.id], order_by=users.c.id.desc())),
            select(row_number.over(order_by=[name.asc().nulls_last(), sa.text("id DESC")])),
            select(row_number.over(order_by=name == "a", rows=(None, 0))),
            select(row_number.over(order_by=sa.case((name == "a", 1), else_=0))),
            select(sa.func.sum(users.c.id).over(order_by=sa.func.coalesce(name, "x"))),
            select(sa.func.percentile_cont(0.5).within_group(users.c.id.desc())),
            select(users.c.id).where(sa.tuple_(users.c.id, name).in_([(1, "a")])),
        ]

    @pytest.mark.parametrize("index", range(9))
    def test_plain_items_match_base_clauselist(self, index):
        stmt = self._statements()[index]
        assert _compile(stmt) == _compile(stmt, self._BaseListDialect())


class TestOrderByClauseMatchesSQLAlchemy:
    """CubridCompiler.order_by_clause renders one item at a time (#968).

    For ORDER BY items that need no grouping, its output must equal
    SQLAlchemy's own order_by_clause, which it replaces.
    """

    class _BaseOrderByCompiler(CubridDialect.statement_compiler):
        order_by_clause = sa.sql.compiler.SQLCompiler.order_by_clause

    class _BaseOrderByDialect(CubridDialect):
        pass

    _BaseOrderByDialect.statement_compiler = _BaseOrderByCompiler

    @staticmethod
    def _statements() -> list[Any]:
        name = users.c.name
        upper = sa.func.upper(name).label("upper_name")
        sub = select(users.c.id).order_by(users.c.id.desc()).limit(2).subquery()
        return [
            select(users.c.id),
            select(users.c.id).order_by(users.c.id),
            select(users.c.id).order_by(users.c.id.desc(), name.asc().nulls_last()),
            select(upper).order_by(upper),
            select(users.c.id).order_by(upper.desc()),
            select(users.c.id).order_by(sa.text("id DESC"), sa.literal_column("2")),
            select(users.c.id).order_by(sa.func.coalesce(name, "x"), name == "a"),
            select(users.c.id).order_by(sa.case((name == "a", 1), else_=0)),
            select(users.c.id, name).order_by("name"),
            select(sub.c.id).order_by(sub.c.id),
            sa.union(select(users.c.id), select(users.c.id)).order_by("id"),
            select(users.c.id).order_by(users.c.id).limit(5).offset(10),
            select(users.c.id).order_by(None),
        ]

    @pytest.mark.parametrize("index", range(13))
    def test_plain_items_match_base_order_by_clause(self, index):
        stmt = self._statements()[index]
        assert _compile(stmt) == _compile(stmt, self._BaseOrderByDialect())

    def test_base_dialect_differs_only_where_grouping_applies(self):
        stmt = select(users.c.id).order_by(sa.and_(users.c.name == "a", users.c.id == 1))
        assert _norm(_compile(stmt)).endswith("ORDER BY (users.name = 'a' AND users.id = 1)")
        assert _norm(_compile(stmt, self._BaseOrderByDialect())).endswith(
            "ORDER BY users.name = 'a' AND users.id = 1"
        )


class TestWindowFunctionCompilation:
    """Test window function compilation."""

    def test_row_number(self):
        """ROW_NUMBER() OVER (ORDER BY ...) should compile."""
        stmt = select(
            users.c.name,
            sa.func.row_number().over(order_by=users.c.id).label("rn"),
        )
        sql = _compile(stmt)
        assert "row_number()" in sql.lower()
        assert "OVER" in sql
        assert "ORDER BY" in sql

    def test_rank_with_partition(self):
        """RANK() OVER (PARTITION BY ... ORDER BY ...) should compile."""
        stmt = select(
            users.c.name,
            sa.func.rank()
            .over(
                partition_by=users.c.email,
                order_by=users.c.id,
            )
            .label("rnk"),
        )
        sql = _compile(stmt)
        assert "rank()" in sql.lower()
        assert "PARTITION BY" in sql

    def test_dense_rank(self):
        """DENSE_RANK should compile via SA base compiler."""
        stmt = select(
            sa.func.dense_rank().over(order_by=users.c.id).label("dr"),
        )
        sql = _compile(stmt)
        assert "dense_rank()" in sql.lower()
        assert "OVER" in sql


class TestNullsOrderCompilation:
    """Test NULLS FIRST / NULLS LAST in ORDER BY."""

    def test_nulls_first(self):
        stmt = select(users).order_by(users.c.name.asc().nulls_first())
        sql = _compile(stmt)
        assert "NULLS FIRST" in sql

    def test_nulls_last(self):
        stmt = select(users).order_by(users.c.name.desc().nulls_last())
        sql = _compile(stmt)
        assert "NULLS LAST" in sql


class TestJoinCompilation:
    orders = Table(
        "orders",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer),
        Column("total", Integer),
    )

    def test_inner_join(self):
        stmt = select(users).join(self.orders, users.c.id == self.orders.c.user_id)
        sql = _compile(stmt)
        assert "INNER JOIN" in sql
        assert "ON" in sql

    def test_left_outer_join(self):
        stmt = select(users).outerjoin(self.orders, users.c.id == self.orders.c.user_id)
        sql = _compile(stmt)
        assert "LEFT OUTER JOIN" in sql
        assert "ON" in sql

    def test_full_outer_join_raises(self):
        stmt = select(users).select_from(
            users.join(self.orders, users.c.id == self.orders.c.user_id, full=True)
        )
        with pytest.raises(CompileError, match="FULL OUTER JOIN"):
            _compile(stmt)

    def test_lateral_raises(self):
        subq = (
            select(self.orders.c.user_id)
            .where(self.orders.c.user_id == users.c.id)
            .lateral("order_lateral")
        )
        stmt = select(users.c.id).select_from(users.join(subq, sa.true()))
        with pytest.raises(CompileError, match="LATERAL"):
            _compile(stmt)


class TestCastCompilation:
    def test_cast_integer(self):
        stmt = select(sa.cast(users.c.name, Integer))
        sql = _compile(stmt)
        assert "CAST" in sql
        assert "AS" in sql
        # Must have space before AS
        assert "AS " in sql

    def test_cast_string(self):
        stmt = select(sa.cast(users.c.id, String(50)))
        sql = _compile(stmt)
        assert "CAST" in sql
        assert "AS" in sql


class TestLiteralValueCompilation:
    """Test render_literal_value method."""

    def test_render_literal_with_backslash_default(self):
        """Default CUBRID (no_backslash_escapes=yes): backslash is literal, NOT doubled."""
        stmt = select(sa.literal("path\\to\\file"))
        sql = _compile(stmt)
        # Backslashes must be preserved as-is; doubling would corrupt data.
        assert "path\\to\\file" in sql
        assert "\\\\" not in sql

    def test_render_literal_with_backslash_escape_mode(self):
        """Legacy escape mode (no_backslash_escapes=no): backslashes are doubled."""
        dialect = CubridDialect(no_backslash_escapes=False)
        stmt = select(sa.literal("path\\to\\file"))
        sql = _compile(stmt, dialect=dialect)
        assert "\\\\" in sql

    def test_render_literal_backslash_preserves_quote_escaping(self):
        """Single-quote escaping must still work alongside literal backslashes."""
        stmt = select(sa.literal("C:\\it's"))
        sql = _compile(stmt)
        # Backslash stays single; quote is escaped by SQLAlchemy's base handling.
        assert "C:\\it" in sql
        assert "\\\\" not in sql

    def test_dialect_default_option_value(self):
        """Default dialect option matches CUBRID's default (no doubling)."""
        assert CubridDialect().no_backslash_escapes is True

    @pytest.mark.parametrize(
        ("no_backslash_escapes", "expected"),
        [
            (True, "users.name = '\\'' OR 1=1 -- '"),
            (False, "users.name = '\\\\'' OR 1=1 -- '"),
        ],
    )
    def test_quote_after_backslash_stays_inside_the_literal(self, no_backslash_escapes, expected):
        """#863: ``\\' OR 1=1 --`` renders as one literal in each server mode."""
        dialect = CubridDialect(no_backslash_escapes=no_backslash_escapes)
        stmt = select(users.c.id).where(users.c.name == "\\' OR 1=1 -- ")
        sql = stmt.compile(dialect=dialect, compile_kwargs={"literal_binds": True}).string
        assert expected in sql

    def test_dialect_option_opt_out(self):
        """Explicit keyword construction stores the opt-out flag as given."""
        assert CubridDialect(no_backslash_escapes=False).no_backslash_escapes is False


class TestCompatHelpers:
    @pytest.mark.parametrize(
        ("getter", "attribute", "fallback"),
        [
            (get_for_update_arg, "_for_update_arg", None),
            (get_limit_clause, "_limit_clause", None),
            (get_offset_clause, "_offset_clause", None),
            (get_distinct, "_distinct", False),
        ],
    )
    def test_select_attribute_accessors(self, getter, attribute, fallback):
        statement = select(users.c.id).limit(10).offset(5).distinct().with_for_update()

        assert getter(statement) is getattr(statement, attribute)
        assert getter(object()) is fallback

    def test_is_literal_value(self):
        assert is_literal_value(1) is True
        assert is_literal_value("value") is True
        assert is_literal_value(users.c.name) is False
        assert is_literal_value(sa.literal("value")) is False

    def test_bind_with_type(self):
        element = sa.bindparam("name", "value")
        typed_element = bind_with_type(element, users.c.name.type)

        assert typed_element is not element
        assert typed_element.key == element.key
        assert typed_element.value == element.value
        assert typed_element.unique == element.unique
        assert isinstance(typed_element.type, users.c.name.type.__class__)

    def test_bind_with_type_fallback_when_clone_missing(self):
        """Verify graceful degradation if SA removes _clone() in a future release."""
        from unittest.mock import PropertyMock, patch

        element = sa.bindparam("name", "value", unique=True)
        # Simulate _clone being unavailable (hypothetical SA 2.2+ rename)
        with patch.object(type(element), "_clone", new_callable=PropertyMock) as mock_clone:
            mock_clone.side_effect = AttributeError("_clone removed")
            typed_element = bind_with_type(element, users.c.name.type)

        assert typed_element is not element
        assert typed_element.value == "value"
        assert typed_element.unique is True
        assert isinstance(typed_element.type, users.c.name.type.__class__)


class TestFunctionCompilation:
    """Test function compilation (SYSDATE, UTC_TIMESTAMP)."""

    def test_sysdate_func(self):
        """Test SYSDATE function compilation."""
        stmt = select(sa.func.sysdate())
        sql = _compile(stmt)
        assert "SYSDATE" in sql

    def test_utc_timestamp_func(self):
        """Test UTC_TIMESTAMP function compilation."""
        stmt = select(sa.func.utc_timestamp())
        sql = _compile(stmt)
        assert "UTC_TIMESTAMP()" in sql

    def test_cast_string_to_integer(self):
        """Test casting string column to integer."""
        stmt = select(sa.cast(users.c.name, Integer))
        sql = _compile(stmt)
        assert "CAST" in sql
        assert "INTEGER" in sql


class TestGroupConcatCompilation:
    """Test GROUP_CONCAT function compilation."""

    def test_group_concat_basic(self):
        """GROUP_CONCAT() should compile via visit_group_concat_func."""
        stmt = select(sa.func.group_concat(users.c.name))
        sql = _compile(stmt)
        assert "GROUP_CONCAT" in sql
        assert "users.name" in sql

    def test_group_concat_basic_exact(self):
        stmt = select(sa.func.group_concat(users.c.name))
        assert _norm(_compile(stmt)) == (
            "SELECT GROUP_CONCAT(users.name) AS group_concat_1 FROM users"
        )

    @pytest.mark.parametrize(
        ("arguments", "expected"),
        [
            ((users.c.name,), "GROUP_CONCAT(users.name)"),
            ((users.c.name.distinct(),), "GROUP_CONCAT(DISTINCT users.name)"),
            (
                (sa.literal_column("users.name ORDER BY users.name DESC SEPARATOR ';'"),),
                "GROUP_CONCAT(users.name ORDER BY users.name DESC SEPARATOR ';')",
            ),
            (
                (sa.literal_column("DISTINCT users.name ORDER BY users.name SEPARATOR '|'"),),
                "GROUP_CONCAT(DISTINCT users.name ORDER BY users.name SEPARATOR '|')",
            ),
            ((users.c.id == 1,), "GROUP_CONCAT(users.id = 1)"),
            ((users.c.id + 1,), "GROUP_CONCAT(users.id + 1)"),
            ((_and,), "GROUP_CONCAT((users.name = 'a' AND users.id = 1))"),
            (
                (sa.or_(users.c.name == "a", users.c.id == 2),),
                "GROUP_CONCAT((users.name = 'a' OR users.id = 2))",
            ),
            ((_exists,), "GROUP_CONCAT((EXISTS (SELECT * FROM users WHERE users.name = 'a')))"),
            (
                (~_exists,),
                "GROUP_CONCAT((NOT (EXISTS (SELECT * FROM users WHERE users.name = 'a'))))",
            ),
            (
                (sa.func.coalesce(_and, 0),),
                "GROUP_CONCAT(coalesce((users.name = 'a' AND users.id = 1), 0))",
            ),
            (
                (users.c.name, sa.literal_column("SEPARATOR ','")),
                "GROUP_CONCAT(users.name, SEPARATOR ',')",
            ),
            ((), "GROUP_CONCAT()"),
        ],
        ids=[
            "column",
            "distinct",
            "order-by-separator",
            "distinct-order-by-separator",
            "comparison",
            "expression",
            "and",
            "or",
            "exists",
            "not-exists",
            "nested-function",
            "separator-argument",
            "no-argument",
        ],
    )
    def test_group_concat_argument_list_parentheses_only(self, arguments, expected):
        """GROUP_CONCAT renders only the argument-list parentheses (#990).

        A boolean argument keeps the grouping every function argument gets (#970),
        once (#984), as in ``coalesce((a AND b), 0)``.
        """
        concat = sa.func.group_concat(*arguments)
        assert f"SELECT {expected} AS group_concat_1" in _norm(_compile(select(concat)))
        if arguments:
            sql = _norm(_compile(select(users.c.id).group_by(users.c.id).having(concat != "")))
            assert f"HAVING {expected} != ''" in sql


_HAS_AGGREGATE_ORDER_BY = hasattr(sa.sql.functions.FunctionElement, "aggregate_order_by")


@pytest.mark.skipif(not _HAS_AGGREGATE_ORDER_BY, reason="aggregate_order_by() is SQLAlchemy 2.1+")
class TestAggregateOrderByCompilation:
    """SQLAlchemy 2.1 aggregate_order_by() keeps its ORDER BY (#991).

    CUBRID takes an ORDER BY only inside GROUP_CONCAT's argument list; every
    other function raises instead of losing the ORDER BY.
    """

    @pytest.mark.parametrize(
        ("concat", "expected"),
        [
            (
                lambda: sa.func.group_concat(users.c.name).aggregate_order_by(users.c.name.desc()),
                "GROUP_CONCAT(users.name ORDER BY users.name DESC)",
            ),
            (
                lambda: sa.func.group_concat(users.c.name.distinct()).aggregate_order_by(
                    users.c.name
                ),
                "GROUP_CONCAT(DISTINCT users.name ORDER BY users.name)",
            ),
            (
                lambda: sa.aggregate_order_by(
                    sa.func.group_concat(users.c.name), users.c.name.asc().nulls_last()
                ),
                "GROUP_CONCAT(users.name ORDER BY users.name ASC NULLS LAST)",
            ),
            (
                lambda: sa.func.group_concat(_and).aggregate_order_by(_and.desc()),
                "GROUP_CONCAT((users.name = 'a' AND users.id = 1) "
                "ORDER BY (users.name = 'a' AND users.id = 1) DESC)",
            ),
            (
                lambda: sa.func.group_concat(_exists).aggregate_order_by(_exists),
                "GROUP_CONCAT((EXISTS (SELECT * FROM users WHERE users.name = 'a')) "
                "ORDER BY (EXISTS (SELECT * FROM users WHERE users.name = 'a')))",
            ),
            (
                lambda: sa.func.group_concat(~_exists).aggregate_order_by(users.c.id),
                "GROUP_CONCAT((NOT (EXISTS (SELECT * FROM users WHERE users.name = 'a'))) "
                "ORDER BY users.id)",
            ),
            (
                lambda: sa.func.GROUP_CONCAT(users.c.name).aggregate_order_by(users.c.name),
                "GROUP_CONCAT(users.name ORDER BY users.name)",
            ),
            (
                lambda: sa.func.group_concat(users.c.name).aggregate_order_by(
                    sa.literal_column("1").desc()
                ),
                "GROUP_CONCAT(users.name ORDER BY 1 DESC)",
            ),
        ],
        ids=[
            "column-desc",
            "distinct",
            "nulls-last",
            "and",
            "exists",
            "not-exists",
            "upper-case-name",
            "position",
        ],
    )
    def test_group_concat_order_by(self, concat, expected):
        assert _norm(_compile(select(concat()))).startswith(f"SELECT {expected} AS ")
        stmt = select(users.c.id).group_by(users.c.id).having(concat() != "")
        assert f"HAVING {expected} != ''" in _norm(_compile(stmt))

    @pytest.mark.parametrize(
        "function",
        [
            lambda: sa.func.foo(users.c.name),
            lambda: sa.func.json_arrayagg(users.c.name),
            lambda: sa.func.count(users.c.name),
            lambda: sa.func.aggregate_strings(users.c.name, ","),
        ],
        ids=["generic", "json_arrayagg", "count", "aggregate_strings"],
    )
    def test_other_functions_raise(self, function):
        stmt = select(function().aggregate_order_by(users.c.name))
        with pytest.raises(CompileError, match="only for GROUP_CONCAT"):
            _compile(stmt)

    def test_filtered_group_concat_names_filter(self):
        concat = sa.func.group_concat(users.c.name).filter(users.c.id > 1)
        with pytest.raises(CompileError, match="does not support FILTER with aggregate_order_by"):
            _compile(select(sa.aggregate_order_by(concat, users.c.name)))

    def test_filtered_other_function_raises(self):
        concat = sa.func.count(users.c.name).filter(users.c.id > 1)
        with pytest.raises(CompileError, match="does not support FILTER with aggregate_order_by"):
            _compile(select(sa.aggregate_order_by(concat, users.c.name)))


class TestRecursiveCTECompilation:
    """Test recursive CTE (WITH RECURSIVE) compilation."""

    def test_recursive_cte_basic(self):
        """WITH RECURSIVE should compile correctly."""
        cte = sa.select(sa.literal(1).label("n")).cte(name="counter", recursive=True)
        cte_alias = cte.alias()
        cte = cte.union_all(sa.select((cte_alias.c.n + 1).label("n")).where(cte_alias.c.n < 5))
        stmt = sa.select(cte)
        sql = _compile(stmt)
        assert "WITH RECURSIVE" in sql
        assert "counter" in sql

    def test_non_recursive_cte(self):
        """Non-recursive WITH should compile without RECURSIVE keyword."""
        cte = sa.select(users.c.id, users.c.name).where(users.c.id > 0).cte(name="active_users")
        stmt = sa.select(cte)
        sql = _compile(stmt)
        assert "WITH " in sql
        assert "RECURSIVE" not in sql
        assert "active_users" in sql

    def test_cte_with_join(self):
        """CTE used in a JOIN should compile correctly."""
        cte = sa.select(users.c.id, users.c.name).cte(name="user_cte")
        stmt = sa.select(users.c.email, cte.c.name).select_from(
            users.join(cte, users.c.id == cte.c.id)
        )
        sql = _compile(stmt)
        assert "WITH " in sql
        assert "user_cte" in sql
        assert "JOIN" in sql


class TestCoverageEdgeCases:
    """Tests for compiler.py uncovered edge-case branches."""

    def test_visit_cast_none_type(self):
        """compiler.py line 36: visit_cast when type_ processes to None."""
        # Directly test the visit_cast method via the compiler
        dialect = CubridDialect()
        stmt = select(sa.cast(users.c.name, Integer))
        compiler_obj = stmt.compile(dialect=dialect, compile_kwargs={"literal_binds": True})
        # Create a mock cast element where typeclause processes to None
        from unittest.mock import MagicMock

        mock_cast = MagicMock()
        mock_clause = MagicMock()
        mock_self_group = MagicMock()
        mock_cast.typeclause = MagicMock()
        mock_cast.clause = mock_clause
        mock_clause.self_group.return_value = mock_self_group
        # Make process return None for typeclause, "col" for clause
        original_process = compiler_obj.process

        def patched_process(element, **kw):
            if element is mock_cast.typeclause:
                return cast(str, cast(object, None))
            if element is mock_self_group:
                return "users.name"
            return original_process(element, **kw)

        object.__setattr__(compiler_obj, "process", patched_process)
        result = compiler_obj.visit_cast(mock_cast)
        assert result == "users.name"

    def test_for_update_arg_none(self):
        """compiler.py line 72: for_update_clause when _for_update_arg is None."""
        # A plain SELECT without .with_for_update() should return empty string
        stmt = select(users)
        sql = _compile(stmt)
        assert "FOR UPDATE" not in sql

    def test_limit_clause_both_none(self):
        """compiler.py line 86: limit_clause when both limit and offset are None."""
        stmt = select(users)
        sql = _compile(stmt)
        assert "LIMIT" not in sql

    def test_update_from_clause_raises_compile_error(self):
        from sqlalchemy import update

        # Multi-table update — triggers update_from_clause
        orders = Table(
            "orders",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("user_id", Integer),
            extend_existing=True,
        )
        stmt = update(users).values(name="test").where(users.c.id == orders.c.user_id)
        with pytest.raises(CompileError, match=r"UPDATE \.\.\. FROM"):
            _compile(stmt)

    def test_on_duplicate_key_update_table_none(self):
        """compiler.py line 124: visit_on_duplicate_key_update when table is None."""
        from unittest.mock import patch, MagicMock, PropertyMock
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(id=1, name="test")
        stmt = stmt.on_duplicate_key_update(name="updated")
        dialect = CubridDialect()
        compiler_obj = stmt.compile(dialect=dialect, compile_kwargs={"literal_binds": True})
        on_dup = stmt._post_values_clause
        # Patch current_executable to return an object without .table
        with patch.object(
            type(compiler_obj), "current_executable", new_callable=PropertyMock
        ) as mock_prop:
            mock_exec = MagicMock(spec=[])
            mock_prop.return_value = mock_exec
            visit_on_duplicate_key_update = getattr(compiler_obj, "visit_on_duplicate_key_update")
            result = visit_on_duplicate_key_update(on_dup)
        assert result == "ON DUPLICATE KEY UPDATE"

    def test_on_duplicate_key_update_isnull_bind_param(self):
        """compiler.py line 158: BindParameter with _isnull type in replace function."""
        from sqlalchemy_cubrid.dml import insert
        from sqlalchemy.sql.elements import BindParameter
        from sqlalchemy.sql import sqltypes

        stmt = insert(users).values(id=1, name="test", email="test@example.com")
        # Create a bind param with null type
        null_bind = BindParameter(None, "new_value", type_=sqltypes.NULLTYPE)
        stmt = stmt.on_duplicate_key_update(name=null_bind)
        sql = _compile(stmt)
        assert "ON DUPLICATE KEY UPDATE" in sql

    def test_on_duplicate_key_update_else_returns_none(self):
        """compiler.py line 167: replace function else branch returning None."""
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(id=1, name="test", email="test@example.com")
        # Use a column expression that is NOT a BindParameter and NOT from inserted_alias
        stmt = stmt.on_duplicate_key_update(name=users.c.name + " suffix")
        sql = _compile(stmt)
        assert "ON DUPLICATE KEY UPDATE" in sql

    def test_on_duplicate_key_update_non_matching_column_raises(self):
        """compiler.py: non-matching columns should raise CompileError."""
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(id=1, name="test", email="test@example.com")
        stmt = stmt.on_duplicate_key_update(nonexistent_column="value")
        with pytest.raises(CompileError, match="no effective columns"):
            _compile(stmt)

    def test_merge_missing_target_raises(self):
        """compiler.py line 202: MERGE with _target = None."""
        from sqlalchemy_cubrid.dml import Merge

        stmt = Merge.__new__(Merge)
        object.__setattr__(stmt, "_target", None)
        object.__setattr__(stmt, "_using_source", users)
        object.__setattr__(stmt, "_on_condition", users.c.id == users.c.id)
        object.__setattr__(stmt, "_when_matched", {"values": {"name": "test"}})
        object.__setattr__(stmt, "_when_not_matched", None)
        with pytest.raises(Exception, match="requires a target table"):
            _compile(stmt)

    def test_merge_resolve_target_column_string_not_in_target_raises(self):
        """compiler.py: unknown string key in MERGE WHEN MATCHED must raise CompileError."""
        from sqlalchemy_cubrid.dml import merge

        source = Table(
            "src",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String(100)),
            extend_existing=True,
        )
        stmt = merge(users).using(source).on(users.c.id == source.c.id)
        stmt = stmt.when_matched_then_update({"nonexistent_col": "value"})
        with pytest.raises(CompileError, match="not found in target table"):
            _compile(stmt)

    def test_merge_resolve_target_column_with_name_attr(self):
        """compiler.py line 221: _resolve_target_column with object that has name attr."""
        from sqlalchemy_cubrid.dml import merge

        source = Table(
            "src2",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String(100)),
            extend_existing=True,
        )
        stmt = merge(users).using(source).on(users.c.id == source.c.id)
        # Use an actual Column object as key — it has .name attr but isn't a plain string
        stmt = stmt.when_matched_then_update({users.c.name: source.c.name})
        sql = _compile(stmt)
        assert "WHEN MATCHED THEN UPDATE SET" in sql

    def test_merge_render_column_name_fallback(self):
        """compiler.py line 228: _render_column_name when column_key has no name attr."""
        from sqlalchemy_cubrid.dml import merge

        source = Table(
            "src3",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String(100)),
            extend_existing=True,
        )
        stmt = merge(users).using(source).on(users.c.id == source.c.id)
        stmt = stmt.when_matched_then_update({users.c.name: source.c.name})
        # Inject a processable element with no .name attr: sa.text()
        text_element = sa.text("custom_col")
        assert stmt._when_matched is not None
        stmt._when_matched["values"][text_element] = source.c.name
        sql = _compile(stmt)
        assert "WHEN MATCHED THEN UPDATE SET" in sql

    def test_merge_resolve_target_column_validates_column_against_target(self):
        """compiler.py line 227-229: _resolve_target_column validates Column objects against target_columns. (#202)"""
        from sqlalchemy_cubrid.dml import merge

        source = Table(
            "src7",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String(100)),
            extend_existing=True,
        )

        # Test 1: Column object that IS in target_columns returns the target column
        stmt = merge(users).using(source).on(users.c.id == source.c.id)
        stmt = stmt.when_matched_then_update({users.c.name: source.c.name})
        sql = _compile(stmt)
        assert "WHEN MATCHED THEN UPDATE SET" in sql

        # Test 2: Column object not in target table raises CompileError
        non_target_col = Column("external_col", String(50))
        stmt2 = merge(users).using(source).on(users.c.id == source.c.id)
        stmt2._when_matched = {
            "values": {non_target_col: source.c.name}  # Column not in users table
        }
        stmt2._when_not_matched = None
        from sqlalchemy import exc

        with pytest.raises(exc.CompileError, match="not found in target table"):
            _compile(stmt2)

    def test_merge_empty_matched_values_raises(self):
        """compiler.py line 248: MERGE WHEN MATCHED with empty values."""
        from sqlalchemy_cubrid.dml import merge

        source = Table(
            "src4",
            metadata,
            Column("id", Integer, primary_key=True),
            extend_existing=True,
        )
        stmt = merge(users).using(source).on(users.c.id == source.c.id)
        stmt._when_matched = {"values": {}}  # empty values
        stmt._when_not_matched = None
        with pytest.raises(Exception, match="requires at least one UPDATE value"):
            _compile(stmt)

    def test_merge_empty_not_matched_columns_raises(self):
        """compiler.py line 276: MERGE WHEN NOT MATCHED with empty columns."""
        from sqlalchemy_cubrid.dml import merge

        source = Table(
            "src5",
            metadata,
            Column("id", Integer, primary_key=True),
            extend_existing=True,
        )
        stmt = merge(users).using(source).on(users.c.id == source.c.id)
        stmt._when_matched = None
        stmt._when_not_matched = {"columns": [], "values": []}
        with pytest.raises(Exception, match="requires INSERT columns and values"):
            _compile(stmt)

    def test_merge_mismatched_not_matched_columns_values_raises(self):
        """compiler.py line 280: MERGE WHEN NOT MATCHED with mismatched columns/values."""
        from sqlalchemy_cubrid.dml import merge

        source = Table(
            "src6",
            metadata,
            Column("id", Integer, primary_key=True),
            extend_existing=True,
        )
        stmt = merge(users).using(source).on(users.c.id == source.c.id)
        stmt._when_matched = None
        stmt._when_not_matched = {
            "columns": ["id", "name"],
            "values": [source.c.id],  # mismatched count
        }
        with pytest.raises(Exception, match="columns and values must match"):
            _compile(stmt)


class TestDialectReflectionExceptionPaths:
    """Tests for dialect.py reflection exception paths."""

    def test_get_columns_comment_query_exception(self):
        """A failing comment query raises (#549)."""
        from unittest.mock import MagicMock

        dialect = CubridDialect()
        conn = MagicMock()

        # First call: SHOW COLUMNS succeeds with one row
        columns_result = MagicMock()
        columns_result.__iter__ = MagicMock(
            return_value=iter(
                [
                    ("id", "INTEGER", "NO", "PRI", None, "AUTO_INCREMENT"),
                ]
            )
        )

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return columns_result
            else:
                raise Exception("comment query failed")

        conn.execute = MagicMock(side_effect=side_effect)

        # A failing comment query raises instead of silently dropping every
        # column comment (#549).
        with pytest.raises(Exception, match="comment query failed"):
            dialect.get_columns(conn, "test_table", None)

    def test_get_pk_constraint_exception(self):
        """A failing catalog query raises; no silent SHOW COLUMNS fallback (#549)."""
        from unittest.mock import MagicMock

        dialect = CubridDialect()
        conn = MagicMock()

        # SHOW COLUMNS fallback returns the single PRI column.
        columns_result = MagicMock()
        columns_result.__iter__ = MagicMock(
            return_value=iter(
                [
                    ("id", "INTEGER", "NO", "PRI", None, "AUTO_INCREMENT"),
                ]
            )
        )

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call is the db_index_key catalog query — make it fail.
                raise Exception("catalog query failed")
            return columns_result

        conn.execute = MagicMock(side_effect=side_effect)

        # Falling back would lose the PK name and trailing composite columns.
        with pytest.raises(Exception, match="catalog query failed"):
            dialect.get_pk_constraint(conn, "test_table", None)
        assert call_count[0] == 1


class TestIsDistinctFromCompilation:
    """CUBRID emulates IS [NOT] DISTINCT FROM with null-safe ``<=>``."""

    def test_is_distinct_from(self):
        sql = _compile(select(users.c.name).where(users.c.name.is_distinct_from("Alice")))
        assert "(users.name" in sql
        assert ") = 0" in sql
        assert "<=>" in sql
        assert "'Alice'" in sql

    def test_isnot_distinct_from(self):
        sql = _compile(select(users.c.name).where(users.c.name.is_not_distinct_from("Alice")))
        assert "users.name <=> 'Alice'" in sql

    def test_is_distinct_from_in_projection(self):
        expr = users.c.name.is_distinct_from(users.c.email).label("is_distinct")
        sql = _compile(select(expr))
        assert "(users.name <=> users.email) = 0 AS is_distinct" in sql

    def test_null_safe_on_both_sides(self):
        sql = _compile(select(users.c.id).where(users.c.name.is_distinct_from(users.c.email)))
        assert "(users.name <=> users.email) = 0" in sql


_flags = Table(
    "flags",
    MetaData(),
    Column("id", Integer, primary_key=True),
    Column("b", sa.Boolean),
    Column("x", Integer),
)


class TestBooleanIsCompilation:
    """CUBRID's ``IS`` only takes ``[NOT] NULL`` / ``[NOT] TRUE/FALSE`` (and
    since 11.2 ``IS TRUE`` needs a logical operand), so ``IS 1`` / ``IS NOT 0``
    from SQLAlchemy's non-native Boolean is rendered with null-safe ``<=>``."""

    @pytest.mark.parametrize(
        ("expr", "expected"),
        [
            (_flags.c.b.is_(True), "flags.b <=> 1"),
            (_flags.c.b.is_(False), "flags.b <=> 0"),
            (_flags.c.b.is_not(True), "(flags.b <=> 1) = 0"),
            (_flags.c.b.is_not(False), "(flags.b <=> 0) = 0"),
            (_flags.c.b.is_(sa.true()), "flags.b <=> 1"),
            (_flags.c.b.is_not(sa.false()), "(flags.b <=> 0) = 0"),
            (~_flags.c.b.is_(True), "(flags.b <=> 1) = 0"),
            ((_flags.c.x == 5).is_(True), "(flags.x = 5) <=> 1"),
            ((_flags.c.x == 5).is_not(False), "((flags.x = 5) <=> 0) = 0"),
            (_flags.c.b.is_(sa.literal(True)), "flags.b <=> 1"),
            (
                sa.and_(_flags.c.x == 5, _flags.c.b.is_(True)),
                "flags.x = 5 AND flags.b <=> 1",
            ),
        ],
    )
    def test_is_with_a_value_uses_null_safe_equality(self, expr, expected):
        where = _compile(select(_flags.c.id).where(expr))
        assert where.endswith("WHERE " + expected)
        assert " IS 1" not in where and " IS 0" not in where
        assert " IS NOT 1" not in where and " IS NOT 0" not in where

    @pytest.mark.parametrize(
        ("expr", "expected"),
        [
            (_flags.c.b.is_(True), "flags.b <=> 1 AS v"),
            (_flags.c.b.is_not(True), "(flags.b <=> 1) = 0 AS v"),
        ],
    )
    def test_is_with_a_value_in_projection(self, expr, expected):
        # ``NOT (a <=> b)`` and ``x IS NOT TRUE`` are rejected in a SELECT list.
        assert expected in _compile(select(expr.label("v")))

    @pytest.mark.parametrize(
        ("expr", "expected"),
        [
            (_flags.c.b.is_(None), "flags.b IS NULL"),
            (_flags.c.b.is_not(None), "flags.b IS NOT NULL"),
            # SQLAlchemy's ``== None`` / ``!= None`` operator path, which builds
            # IS [NOT] NULL; operator.eq/ne avoid a Python None comparison.
            (operator.eq(_flags.c.b, None), "flags.b IS NULL"),
            (operator.ne(_flags.c.b, None), "flags.b IS NOT NULL"),
            (_flags.c.b.is_(sa.null()), "flags.b IS NULL"),
        ],
    )
    def test_is_null_keeps_its_syntax(self, expr, expected):
        assert _compile(select(_flags.c.id).where(expr)).endswith("WHERE " + expected)

    @pytest.mark.parametrize(
        ("expr", "expected"),
        [
            (sa.null().is_(_flags.c.b), "NULL <=> flags.b"),
            (_flags.c.b.is_(sa.literal(None, sa.Boolean)), "flags.b <=> NULL"),
            (_flags.c.b.is_(_flags.c.x), "flags.b <=> flags.x"),
            (_flags.c.b.is_not(_flags.c.x), "(flags.b <=> flags.x) = 0"),
            (_flags.c.b.is_(True) == False, "(flags.b <=> 1) = 0"),  # noqa: E712
            (
                sa.case((_flags.c.b.is_(True), 1), else_=0) == 1,
                "CASE WHEN (flags.b <=> 1) THEN 1 ELSE 0 END = 1",
            ),
        ],
    )
    def test_is_grouping_and_other_operands(self, expr, expected):
        # ``<=> NULL`` has the meaning of ``IS NULL``.
        assert _compile(select(_flags.c.id).where(expr)).endswith("WHERE " + expected)

    def test_is_in_order_by(self):
        stmt = select(_flags.c.id).order_by(_flags.c.b.is_(True).desc(), _flags.c.b.is_not(False))
        assert _compile(stmt).endswith("ORDER BY flags.b <=> 1 DESC, (flags.b <=> 0) = 0")

    def test_is_with_a_bound_parameter(self):
        stmt = select(_flags.c.id).where(_flags.c.b.is_(sa.bindparam("flag", type_=sa.Boolean)))
        compiled = stmt.compile(dialect=CubridDialect())
        assert str(compiled).endswith("WHERE flags.b <=> ?")

    @pytest.mark.parametrize(
        ("expr", "expected"),
        [
            (_flags.c.b == True, "flags.b = 1"),  # noqa: E712
            (_flags.c.b == False, "flags.b = 0"),  # noqa: E712
            (_flags.c.b, "flags.b = 1"),
            (sa.not_(_flags.c.b), "flags.b = 0"),
            (sa.true(), "1 = 1"),
            (sa.and_(_flags.c.b, sa.true()), "flags.b = 1"),
            (sa.or_(_flags.c.b, sa.false()), "flags.b = 1"),
            (_flags.c.b.is_distinct_from(True), "(flags.b <=> 1) = 0"),
        ],
    )
    def test_other_boolean_forms_unchanged(self, expr, expected):
        assert _compile(select(_flags.c.id).where(expr)).endswith("WHERE " + expected)


class TestNumericBindCast386:
    """#386: scaled numeric binds are cast so CUBRID keeps their scale; a
    FROM-less SELECT with WHERE gets a synthetic FROM db_root."""

    def test_scaled_numeric_bind_renders_cast(self):
        from decimal import Decimal

        t = Table("nb1", MetaData(), Column("x", sa.Numeric(8, 4)))
        stmt = select(sa.type_coerce(t.c.x + Decimal("37.12"), sa.Numeric(8, 4)))
        sql = stmt.compile(dialect=CubridDialect()).string
        assert "CAST(? AS NUMERIC(8, 4))" in sql or "CAST(:" in sql

    def test_unconstrained_numeric_bind_not_cast(self):
        from decimal import Decimal

        t = Table("nb2", MetaData(), Column("y", sa.Numeric()))
        stmt = select(sa.type_coerce(t.c.y + Decimal("1.5"), sa.Numeric()))
        sql = stmt.compile(dialect=CubridDialect()).string
        assert "CAST(" not in sql

    def test_fromless_select_with_where_gets_default_from(self):
        stmt = select(sa.literal(1)).where(sa.bindparam("a", 1) == sa.bindparam("b", 1))
        sql = stmt.compile(dialect=CubridDialect()).string
        assert "FROM db_root" in sql


class TestPositionalBindOrderAcrossConstructs:
    """#613: assert the emitted ``?`` placeholder order and the ordered values
    (``[compiled.params[name] for name in compiled.positiontup]``) for
    constructs not already covered by ``TestReplaceKeywordIsStructural`` --
    CTEs, correlated subqueries, INSERT ... SELECT, multi-row VALUES and
    LIMIT/OFFSET -- plus a metamorphic invariant: reordering selected columns
    must not change the bind order of WHERE predicates.

    Deliberately does not assert ``len(params) == len(positiontup)``: a
    repeated name (ODKU's VALUES() re-use, REPLACE's multi-row ``_mN``
    suffixes) makes ``params`` the smaller, deduplicated mapping while
    ``positiontup`` lists every placeholder occurrence.
    """

    def _ordered_values(self, compiled):
        return [compiled.params[name] for name in compiled.positiontup]

    def test_cte_binding_order(self):
        """A bind inside the CTE body precedes a bind in the outer query."""
        cte = select(users.c.id, users.c.name).where(users.c.name == sa.bindparam("n1", "alice"))
        cte = cte.cte("c")
        stmt = select(cte.c.id).where(cte.c.id > sa.bindparam("minid", 10))
        compiled = stmt.compile(dialect=CubridDialect())
        assert compiled.positiontup == ["n1", "minid"]
        assert self._ordered_values(compiled) == ["alice", 10]
        assert compiled.string.count("?") == 2

    def test_recursive_cte_binding_order(self):
        """Anchor bind precedes the recursive term's increment and limit binds."""
        anchor = select(sa.bindparam("start", 1).label("n"))
        cte = anchor.cte(name="counter", recursive=True)
        cte_alias = cte.alias()
        cte = cte.union_all(
            select((cte_alias.c.n + sa.bindparam("step", 1)).label("n")).where(
                cte_alias.c.n < sa.bindparam("stop", 5)
            )
        )
        stmt = select(cte)
        compiled = stmt.compile(dialect=CubridDialect())
        assert compiled.positiontup == ["start", "step", "stop"]
        assert self._ordered_values(compiled) == [1, 1, 5]

    def test_correlated_subquery_binding_order(self):
        """A bind inside a scalar subquery precedes a bind in the outer WHERE."""
        subq = (
            select(sa.func.max(users.c.id))
            .where(users.c.name == sa.bindparam("n2", "bob"))
            .scalar_subquery()
        )
        stmt = (
            select(users.c.id)
            .where(users.c.id == subq)
            .where(users.c.email == sa.bindparam("e2", "x@y"))
        )
        compiled = stmt.compile(dialect=CubridDialect())
        assert compiled.positiontup == ["n2", "e2"]
        assert self._ordered_values(compiled) == ["bob", "x@y"]

    def test_insert_select_binding_order(self):
        """INSERT ... SELECT binds only the binds inside the SELECT, in order."""
        src = Table("src_613", metadata, Column("id", Integer), Column("name", String(50)))
        stmt = sa.insert(users).from_select(
            ["id", "name"],
            select(src.c.id, src.c.name).where(src.c.name == sa.bindparam("srcname", "c")),
        )
        compiled = stmt.compile(dialect=CubridDialect())
        assert compiled.positiontup == ["srcname"]
        assert self._ordered_values(compiled) == ["c"]
        assert "VALUES" not in compiled.string

    def test_multirow_insert_binding_order(self):
        """Plain multi-row INSERT VALUES binds row-major, left to right (#613).

        Mirrors ``TestReplaceKeywordIsStructural.test_multi_values_with_prefix``
        for ordinary ``INSERT`` (REPLACE already covers this combination).
        """
        stmt = sa.insert(users).values([{"id": 1, "name": "a"}, {"id": 2, "name": "b"}])
        compiled = stmt.compile(dialect=CubridDialect())
        assert compiled.string == "INSERT INTO users (id, name) VALUES (?, ?), (?, ?)"
        assert compiled.positiontup == ["id_m0", "name_m0", "id_m1", "name_m1"]
        assert self._ordered_values(compiled) == [1, "a", 2, "b"]

    def test_limit_offset_binding_order(self):
        """CUBRID's ``LIMIT <offset>, <count>`` binds offset before count.

        Regression guard: the dialect's ``limit_clause`` processes the offset
        clause before the limit clause (matching the rendered operand order);
        swapping that order would silently bind the row count where the
        offset belongs (and vice versa) without changing the SQL text shape.
        """
        stmt = select(users.c.id).where(users.c.name == sa.bindparam("n3", "z")).limit(5).offset(2)
        compiled = stmt.compile(dialect=CubridDialect())
        assert _norm(compiled.string).endswith("LIMIT ?, ?")
        assert compiled.positiontup[0] == "n3"
        offset_name, count_name = compiled.positiontup[1], compiled.positiontup[2]
        assert compiled.params[offset_name] == 2
        assert compiled.params[count_name] == 5

    def test_postcompile_expansion_binding_order(self):
        """#613: an expanding ``IN`` bind renders one ``?`` per element, in
        list order, and the following bind still comes after all of them.

        Unexpanded (``render_postcompile=False``, the default -- what a
        ``CompileState``-cached statement looks like before execution), the
        bind stays a single ``__[POSTCOMPILE_names]`` placeholder in
        ``positiontup``, with its whole list as the one value; the real
        per-element names and values only appear once
        ``render_postcompile=True`` processes it (what the DBAPI driver
        actually receives at execution time).
        """
        stmt = select(users.c.id).where(
            users.c.name.in_(sa.bindparam("names", value=["a", "b", "c"], expanding=True))
        )
        stmt = stmt.where(users.c.email == sa.bindparam("e", "z@example.com"))

        unexpanded = stmt.compile(dialect=CubridDialect())
        assert "__[POSTCOMPILE_names]" in unexpanded.string
        assert unexpanded.positiontup == ["names", "e"]
        assert unexpanded.params["names"] == ["a", "b", "c"]

        expanded = stmt.compile(
            dialect=CubridDialect(), compile_kwargs={"render_postcompile": True}
        )
        assert _norm(expanded.string) == _norm(
            "SELECT users.id FROM users WHERE users.name IN (?, ?, ?) AND users.email = ?"
        )
        assert expanded.positiontup == ["names_1", "names_2", "names_3", "e"]
        assert self._ordered_values(expanded) == ["a", "b", "c", "z@example.com"]

    def test_postcompile_expansion_after_a_preceding_bind(self):
        """#613: a bind before an expanding ``IN`` keeps its position; the
        expanded elements are inserted in place, not appended at the end."""
        stmt = select(users.c.id).where(users.c.email == sa.bindparam("e", "z@example.com"))
        stmt = stmt.where(users.c.name.in_(sa.bindparam("names", value=["a", "b"], expanding=True)))

        expanded = stmt.compile(
            dialect=CubridDialect(), compile_kwargs={"render_postcompile": True}
        )
        assert expanded.positiontup == ["e", "names_1", "names_2"]
        assert self._ordered_values(expanded) == ["z@example.com", "a", "b"]

    def test_metamorphic_select_column_order_does_not_reorder_where_binds(self):
        """Reordering the SELECT list leaves WHERE bind order unchanged."""
        stmt_a = (
            select(users.c.id, users.c.name)
            .where(users.c.email == sa.bindparam("e", "x"))
            .where(users.c.id > sa.bindparam("minid", 1))
        )
        stmt_b = (
            select(users.c.name, users.c.id)
            .where(users.c.email == sa.bindparam("e", "x"))
            .where(users.c.id > sa.bindparam("minid", 1))
        )
        c_a = stmt_a.compile(dialect=CubridDialect())
        c_b = stmt_b.compile(dialect=CubridDialect())
        assert c_a.positiontup == c_b.positiontup == ["e", "minid"]
        assert self._ordered_values(c_a) == self._ordered_values(c_b) == ["x", 1]


class TestCompileOptionsForwarded862:
    """``literal_binds`` and other compile options reach every nested element."""

    def test_cast_operand_renders_literal(self):
        stmt = select(sa.cast(users.c.name + "x", String(10)))
        assert "CAST(users.name || 'x' AS VARCHAR(10))" in _compile(stmt)

    def test_on_duplicate_key_update_values_render_literals(self):
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(id=1, name="a", email="e")
        stmt = stmt.on_duplicate_key_update(name="b", id=users.c.id + 1)
        sql = _compile(stmt)
        assert "?" not in sql
        assert "name = 'b'" in sql
        assert "id = (users.id + 1)" in sql

    def test_on_duplicate_key_update_keeps_binds_without_literal_binds(self):
        from sqlalchemy_cubrid.dml import insert

        stmt = insert(users).values(id=1, name="a", email="e")
        stmt = stmt.on_duplicate_key_update(name="b")
        assert "name = ?" in str(stmt.compile(dialect=CubridDialect()))

    def test_server_default_cast_renders_literal(self):
        t = Table(
            "t862_default",
            MetaData(),
            Column("id", Integer, primary_key=True),
            Column("s", String(10), server_default=sa.cast(sa.literal(5), String(10))),
        )
        ddl = str(sa.schema.CreateTable(t).compile(dialect=CubridDialect()))
        assert "DEFAULT CAST(5 AS VARCHAR(10))" in ddl

    def test_functional_index_cast_renders_literal(self):
        t = Table("t862_index", MetaData(), Column("a", Integer))
        index = sa.Index("ix_t862", sa.cast(t.c.a + 1, String(10)))
        index._set_parent(t)
        ddl = str(sa.schema.CreateIndex(index).compile(dialect=CubridDialect()))
        assert "CAST(a + 1 AS VARCHAR(10))" in ddl

    def test_collection_member_receives_type_compiler_options(self, monkeypatch):
        from sqlalchemy_cubrid.compiler import CubridTypeCompiler

        seen: list[dict[str, Any]] = []
        original = CubridTypeCompiler.visit_VARCHAR

        def spy(self: Any, type_: Any, **kw: Any) -> str:
            seen.append(kw)
            return original(self, type_, **kw)

        monkeypatch.setattr(CubridTypeCompiler, "visit_VARCHAR", spy)
        marker = object()
        rendered = CubridDialect().type_compiler_instance.process(
            cubrid_types.SET(sa.VARCHAR(10)), type_expression=marker
        )
        assert rendered == "SET(VARCHAR(10))"
        assert seen and seen[-1].get("type_expression") is marker


class TestFetchAsLimit867:
    """CUBRID has no FETCH FIRST ... ROWS ONLY; fetch() uses LIMIT."""

    def test_fetch(self):
        sql = _compile(select(users.c.id).order_by(users.c.id).fetch(2))
        assert _norm(sql).endswith("ORDER BY users.id LIMIT 2")
        assert "FETCH" not in sql

    def test_offset_fetch(self):
        sql = _compile(select(users.c.id).offset(1).fetch(2))
        assert _norm(sql).endswith("LIMIT 1, 2")
        assert "OFFSET" not in sql

    def test_fetch_binds_without_literal_binds(self):
        compiled = select(users.c.id).offset(3).fetch(4).compile(dialect=CubridDialect())
        assert _norm(compiled.string).endswith("LIMIT ?, ?")
        assert sorted(compiled.params.values()) == [3, 4]

    def test_fetch_in_subquery(self):
        inner = select(users.c.id).fetch(1).scalar_subquery()
        sql = _compile(select(users.c.name).where(users.c.id == inner))
        assert "LIMIT 1)" in _norm(sql)

    @pytest.mark.parametrize(
        ("option", "message"), [("percent", "PERCENT"), ("with_ties", "WITH TIES")]
    )
    def test_fetch_options_raise(self, option, message):
        stmt = select(users.c.id).order_by(users.c.id).fetch(2, **{option: True})
        with pytest.raises(CompileError, match=message):
            _compile(stmt)

    def test_fetch_clause_with_explicit_clause_and_offset_only(self):
        compiler = CubridDialect().statement_compiler(CubridDialect(), None)
        offset_only = select(users.c.id).offset(5)
        assert compiler.fetch_clause(offset_only, fetch_clause=None) == (
            " \n LIMIT %s, %s" % ("?", _CUBRID_OFFSET_NO_LIMIT_ROW_COUNT)
        )
        assert compiler.fetch_clause(select(users.c.id)) == ""
        assert compiler.fetch_clause(select(users.c.id), fetch_clause=sa.literal(3)) == (
            " \n LIMIT ?"
        )


class TestDialectSmallCorrectness870:
    @staticmethod
    def _lint(stmt):
        from sqlalchemy.sql import compiler as sa_compiler

        dialect = CubridDialect()
        return dialect.statement_compiler(
            dialect, stmt, linting=sa_compiler.COLLECT_CARTESIAN_PRODUCTS | sa_compiler.WARN_LINTING
        )

    def test_join_is_not_reported_as_a_cartesian_product(self):
        a = Table("a870", MetaData(), Column("id", Integer))
        b = Table("b870", MetaData(), Column("a_id", Integer))
        stmt = select(a.c.id).select_from(a.join(b, a.c.id == b.c.a_id))
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            self._lint(stmt)

    def test_unjoined_from_item_is_still_reported(self):
        a = Table("a870", MetaData(), Column("id", Integer))
        b = Table("b870", MetaData(), Column("a_id", Integer))
        c = Table("c870", MetaData(), Column("x", Integer))
        stmt = select(a.c.id, c.c.x).select_from(a.join(b, a.c.id == b.c.a_id))
        with pytest.warns(sa.exc.SAWarning, match="cartesian product"):
            self._lint(stmt)

    @pytest.mark.parametrize(
        ("collection", "expected"),
        [
            (cubrid_types.SET(Integer), "SET(INTEGER)"),
            (cubrid_types.MULTISET(Integer, String), "MULTISET(INTEGER,VARCHAR(4096))"),
            (cubrid_types.SEQUENCE(cubrid_types.MONETARY), "SEQUENCE(MONETARY)"),
        ],
    )
    def test_collection_member_type_class(self, collection, expected):
        assert CubridDialect().type_compiler_instance.process(collection) == expected

    def test_dead_code_is_removed(self):
        from sqlalchemy_cubrid.compiler import CubridTypeCompiler

        assert not hasattr(CubridTypeCompiler, "_get")

    def test_ignored_type_arguments_are_deprecated(self):
        with pytest.warns(DeprecationWarning, match="'display_width' argument of SMALLINT") as w1:
            small = cubrid_types.SMALLINT(display_width=5)
        with pytest.warns(DeprecationWarning, match="'values' argument of VARCHAR") as w2:
            varchar = cubrid_types.VARCHAR(10, values=["a"])
        with pytest.warns(DeprecationWarning, match="'values' argument of STRING") as w3:
            cubrid_types.STRING(values=["a"])
        # Each warning points at this caller, not at a constructor in types.py.
        assert {w[0].filename for w in (w1, w2, w3)} == {__file__}
        assert all("future 1.x MINOR release" in str(w[0].message) for w in (w1, w2, w3))
        assert not hasattr(small, "display_width")
        assert not hasattr(varchar, "values")
        assert repr(small) == "SMALLINT()"
        assert repr(varchar) == "VARCHAR(length=10)"
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            cubrid_types.BIGINT()
            cubrid_types.CHAR(3)
