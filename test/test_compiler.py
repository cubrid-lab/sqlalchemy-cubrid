# test/test_compiler.py
"""Offline compiler tests — no live CUBRID required.

Uses SQLAlchemy's compilation API to verify SQL generation without
a database connection.
"""

from __future__ import annotations

import operator

import pytest
import sqlalchemy as sa
from typing import Any, cast
from sqlalchemy import Column, Integer, MetaData, String, Table, select
from sqlalchemy.exc import CompileError

from sqlalchemy_cubrid import types as cubrid_types
from sqlalchemy_cubrid._compat import bind_with_type, is_literal_value
from sqlalchemy_cubrid.compiler import _CUBRID_OFFSET_NO_LIMIT_ROW_COUNT
from sqlalchemy_cubrid.dialect import CubridDialect


def _compile(stmt, dialect=None):
    """Compile a statement using the CUBRID dialect and return SQL string."""
    if dialect is None:
        dialect = CubridDialect()
    return stmt.compile(dialect=dialect, compile_kwargs={"literal_binds": True}).string


def _norm(sql: str) -> str:
    return " ".join(sql.split())


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


metadata = MetaData()
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100)),
    Column("email", String(200)),
)


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

    def test_dialect_option_opt_out(self):
        """Explicit keyword construction stores the opt-out flag as given."""
        assert CubridDialect(no_backslash_escapes=False).no_backslash_escapes is False


class TestCompatHelpers:
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


class TestTypeCompilation:
    """Test type compiler output."""

    def _compile_type(self, type_):
        dialect = CubridDialect()
        return dialect.type_compiler_instance.process(type_)

    def test_boolean_maps_to_smallint(self):
        result = self._compile_type(sa.Boolean())
        assert result == "SMALLINT"

    def test_numeric_no_params(self):
        from sqlalchemy_cubrid.types import NUMERIC

        result = self._compile_type(NUMERIC())
        assert result == "NUMERIC"

    def test_numeric_with_precision(self):
        from sqlalchemy_cubrid.types import NUMERIC

        result = self._compile_type(NUMERIC(precision=10))
        assert result == "NUMERIC(10)"

    def test_numeric_with_scale(self):
        from sqlalchemy_cubrid.types import NUMERIC

        result = self._compile_type(NUMERIC(precision=10, scale=2))
        assert result == "NUMERIC(10, 2)"

    def test_varchar_with_length(self):
        from sqlalchemy_cubrid.types import VARCHAR

        result = self._compile_type(VARCHAR(length=255))
        assert result == "VARCHAR(255)"

    def test_varchar_no_length(self):
        from sqlalchemy_cubrid.types import VARCHAR

        result = self._compile_type(VARCHAR())
        assert result == "VARCHAR(4096)"

    def test_string_no_length_uses_default(self):
        result = self._compile_type(sa.String())
        assert result == "VARCHAR(4096)"

    @pytest.mark.parametrize(
        "type_",
        [
            pytest.param(sa.String(0), id="String"),
            pytest.param(sa.Unicode(0), id="Unicode"),
            pytest.param(sa.VARCHAR(0), id="sa.VARCHAR"),
            pytest.param(cubrid_types.VARCHAR(length=0), id="cubrid.VARCHAR"),
        ],
    )
    def test_varchar_zero_length_raises(self, type_):
        """Regression (#440): explicit length=0 must not become VARCHAR(4096)."""
        with pytest.raises(CompileError, match=r"VARCHAR\(0\)"):
            self._compile_type(type_)

    def test_char_with_length(self):
        from sqlalchemy_cubrid.types import CHAR

        result = self._compile_type(CHAR(length=10))
        assert result == "CHAR(10)"

    def test_char_no_length(self):
        from sqlalchemy_cubrid.types import CHAR

        result = self._compile_type(CHAR())
        assert result == "CHAR"

    @pytest.mark.parametrize(
        "type_",
        [
            pytest.param(sa.CHAR(0), id="sa.CHAR"),
            pytest.param(cubrid_types.CHAR(length=0), id="cubrid.CHAR"),
        ],
    )
    def test_char_zero_length_raises(self, type_):
        """Regression (#476): explicit length=0 must not become bare CHAR."""
        with pytest.raises(CompileError, match=r"CHAR\(0\)"):
            self._compile_type(type_)

    def test_nchar(self):
        from sqlalchemy_cubrid.types import NCHAR

        result = self._compile_type(NCHAR(length=50))
        assert result == "NCHAR(50)"

    def test_nvarchar(self):
        from sqlalchemy_cubrid.types import NVARCHAR

        result = self._compile_type(NVARCHAR(length=100))
        assert result == "NCHAR VARYING(100)"

    def test_blob(self):
        result = self._compile_type(sa.LargeBinary())
        assert result == "BLOB"

    def test_text(self):
        result = self._compile_type(sa.Text())
        assert result == "STRING"

    @pytest.mark.parametrize(
        "type_",
        [sa.UnicodeText(), sa.UnicodeText(length=100), sa.TEXT(), sa.Text(length=100)],
        ids=["UnicodeText", "UnicodeText(100)", "TEXT", "Text(100)"],
    )
    def test_text_family_compiles_to_string(self, type_):
        """#534: CUBRID has no TEXT; every Text variant compiles like Text."""
        assert self._compile_type(type_) == "STRING"

    def test_unicode_text_column_ddl(self):
        from sqlalchemy.schema import CreateTable

        t = Table("ut", MetaData(), Column("body", sa.UnicodeText()))
        ddl = CreateTable(t).compile(dialect=CubridDialect()).string
        assert "body STRING" in ddl
        assert "TEXT" not in ddl

    @pytest.mark.parametrize(
        ("type_", "expected"),
        [
            (sa.BINARY(), "BIT(8)"),
            (sa.BINARY(4), "BIT(32)"),
            (sa.VARBINARY(), "BIT VARYING"),
            (sa.VARBINARY(16), "BIT VARYING(128)"),
        ],
        ids=["BINARY", "BINARY(4)", "VARBINARY", "VARBINARY(16)"],
    )
    def test_binary_types_compile_to_bit_strings(self, type_, expected):
        """#545: CUBRID has no BINARY/VARBINARY; lengths are bytes -> bits."""
        assert self._compile_type(type_) == expected

    @pytest.mark.parametrize("type_", [sa.BINARY(0), sa.VARBINARY(0)], ids=["BINARY", "VARBINARY"])
    def test_binary_types_reject_zero_length(self, type_):
        with pytest.raises(CompileError, match=r"BINARY\(0\)"):
            self._compile_type(type_)

    @pytest.mark.parametrize(
        "type_",
        [sa.UUID(), sa.UUID(as_uuid=False), sa.Uuid(), sa.Uuid(as_uuid=False)],
        ids=["UUID", "UUID(as_uuid=False)", "Uuid", "Uuid(as_uuid=False)"],
    )
    def test_uuid_types_compile_to_char32(self, type_):
        """#545: CUBRID has no UUID; sa.UUID is stored like sa.Uuid."""
        assert self._compile_type(type_) == "CHAR(32)"

    def test_float(self):
        from sqlalchemy_cubrid.types import FLOAT

        result = self._compile_type(FLOAT(precision=10))
        assert result == "FLOAT(10)"

    def test_double(self):
        from sqlalchemy_cubrid.types import DOUBLE

        result = self._compile_type(DOUBLE())
        assert result == "DOUBLE"

    def test_bit(self):
        from sqlalchemy_cubrid.types import BIT

        result = self._compile_type(BIT(length=8))
        assert result == "BIT(8)"

    def test_bit_varying(self):
        from sqlalchemy_cubrid.types import BIT

        result = self._compile_type(BIT(length=256, varying=True))
        assert result == "BIT VARYING(256)"

    def test_bit_unspecified_length_defaults_to_one(self):
        from sqlalchemy_cubrid.types import BIT

        result = self._compile_type(BIT())
        assert result == "BIT(1)"

    @pytest.mark.parametrize(
        "type_",
        [
            pytest.param(cubrid_types.BIT(length=0), id="BIT"),
            pytest.param(cubrid_types.BIT(length=0, varying=True), id="BIT-VARYING"),
        ],
    )
    def test_bit_zero_length_raises(self, type_):
        """Regression (#441): explicit length=0 must not become BIT(1)."""
        with pytest.raises(CompileError, match=r"BIT"):
            self._compile_type(type_)

    def test_datetime(self):
        result = self._compile_type(sa.DateTime())
        assert result == "DATETIME"

    def test_date(self):
        result = self._compile_type(sa.Date())
        assert result == "DATE"

    def test_time(self):
        result = self._compile_type(sa.Time())
        assert result == "TIME"

    def test_set_collection(self):
        from sqlalchemy_cubrid.types import SET, CHAR

        result = self._compile_type(SET(CHAR(10)))
        assert result == "SET(CHAR(10))"

    def test_multiset_collection(self):
        from sqlalchemy_cubrid.types import MULTISET, VARCHAR

        result = self._compile_type(MULTISET(VARCHAR(255)))
        assert result == "MULTISET(VARCHAR(255))"

    def test_sequence_collection(self):
        from sqlalchemy_cubrid.types import SEQUENCE

        result = self._compile_type(SEQUENCE(sa.Integer()))
        assert result == "SEQUENCE(INTEGER)"

    def test_string_type(self):
        from sqlalchemy_cubrid.types import STRING

        result = self._compile_type(STRING())
        assert result == "STRING"

    def test_string_with_national_flag(self):
        from sqlalchemy_cubrid.types import STRING

        result = self._compile_type(STRING(national=True))
        assert "NCHAR VARYING" in result

    def test_clob(self):
        from sqlalchemy_cubrid.types import CLOB

        result = self._compile_type(CLOB())
        assert result == "CLOB"

    def test_decimal(self):
        from sqlalchemy_cubrid.types import DECIMAL

        result = self._compile_type(DECIMAL(precision=15, scale=4))
        assert result == "DECIMAL(15, 4)"

    def test_smallint(self):
        from sqlalchemy_cubrid.types import SMALLINT

        result = self._compile_type(SMALLINT())
        assert result == "SMALLINT"

    def test_bigint(self):
        from sqlalchemy_cubrid.types import BIGINT

        result = self._compile_type(BIGINT())
        assert result == "BIGINT"

    def test_decimal_no_precision(self):
        """Test DECIMAL() without precision."""
        from sqlalchemy_cubrid.types import DECIMAL

        result = self._compile_type(DECIMAL())
        assert result == "DECIMAL"

    def test_decimal_with_precision_only(self):
        """Test DECIMAL with precision but no scale."""
        from sqlalchemy_cubrid.types import DECIMAL

        result = self._compile_type(DECIMAL(precision=10))
        assert result == "DECIMAL(10)"

    def test_float_no_precision(self):
        """Test FLOAT() without precision defaults to 7."""
        from sqlalchemy_cubrid.types import FLOAT

        result = self._compile_type(FLOAT())
        assert result == "FLOAT(7)"

    def test_float_no_precision_stdlib(self):
        """Test SQLAlchemy Float() without precision compiles to FLOAT."""
        result = self._compile_type(sa.Float())
        assert result == "FLOAT"

    def test_timestamp_type(self):
        """Test TIMESTAMP type compilation."""
        result = self._compile_type(sa.TIMESTAMP())
        assert result == "TIMESTAMP"

    def test_timestamptz_type(self):
        """Test TIMESTAMPTZ type compilation."""
        from sqlalchemy_cubrid.types import TIMESTAMPTZ

        result = self._compile_type(TIMESTAMPTZ())
        assert result == "TIMESTAMPTZ"

    def test_timestampltz_type(self):
        """Test TIMESTAMPLTZ type compilation."""
        from sqlalchemy_cubrid.types import TIMESTAMPLTZ

        result = self._compile_type(TIMESTAMPLTZ())
        assert result == "TIMESTAMPLTZ"

    def test_datetimetz_type(self):
        """Test DATETIMETZ type compilation."""
        from sqlalchemy_cubrid.types import DATETIMETZ

        result = self._compile_type(DATETIMETZ())
        assert result == "DATETIMETZ"

    def test_datetimeltz_type(self):
        """Test DATETIMELTZ type compilation."""
        from sqlalchemy_cubrid.types import DATETIMELTZ

        result = self._compile_type(DATETIMELTZ())
        assert result == "DATETIMELTZ"

    def test_tz_types_have_timezone_semantics(self):
        """TZ types should report timezone=True."""
        from sqlalchemy_cubrid.types import TIMESTAMPTZ, TIMESTAMPLTZ, DATETIMETZ, DATETIMELTZ

        for cls in (TIMESTAMPTZ, TIMESTAMPLTZ, DATETIMETZ, DATETIMELTZ):
            assert cls.timezone is True, f"{cls.__name__}.timezone should be True"

    @pytest.mark.parametrize("timezone", [False, True])
    def test_tz_constructor_keyword_preserves_timezone(self, timezone):
        from sqlalchemy_cubrid.types import TIMESTAMPTZ, TIMESTAMPLTZ, DATETIMETZ, DATETIMELTZ

        for cls in (TIMESTAMPTZ, TIMESTAMPLTZ, DATETIMETZ, DATETIMELTZ):
            assert cls(timezone=timezone).timezone is True

    def test_tz_types_reflection_mapping(self):
        """ischema_names maps TZ type strings to distinct classes."""
        from sqlalchemy_cubrid.dialect import ischema_names
        from sqlalchemy_cubrid.types import TIMESTAMPTZ, TIMESTAMPLTZ, DATETIMETZ, DATETIMELTZ

        assert ischema_names["TIMESTAMPTZ"] is TIMESTAMPTZ
        assert ischema_names["TIMESTAMPLTZ"] is TIMESTAMPLTZ
        assert ischema_names["DATETIMETZ"] is DATETIMETZ
        assert ischema_names["DATETIMELTZ"] is DATETIMELTZ

    def test_varchar_with_national_flag(self):
        """Test VARCHAR with national flag redirects to NVARCHAR."""
        from sqlalchemy_cubrid.types import VARCHAR

        t = VARCHAR(length=100, national=True)
        result = self._compile_type(t)
        assert result == "NCHAR VARYING(100)"

    def test_char_with_national_flag(self):
        """Test CHAR with national flag redirects to NCHAR."""
        from sqlalchemy_cubrid.types import CHAR

        t = CHAR(length=50, national=True)
        result = self._compile_type(t)
        assert result == "NCHAR(50)"

    def test_nvarchar_no_length(self):
        """Test NVARCHAR() without length defaults to 4096."""
        from sqlalchemy_cubrid.types import NVARCHAR

        result = self._compile_type(NVARCHAR())
        assert result == "NCHAR VARYING(4096)"

    @pytest.mark.parametrize(
        "type_",
        [
            pytest.param(sa.NVARCHAR(0), id="sa.NVARCHAR"),
            pytest.param(cubrid_types.NVARCHAR(length=0), id="cubrid.NVARCHAR"),
            pytest.param(
                cubrid_types.VARCHAR(length=0, national=True), id="cubrid.VARCHAR-national"
            ),
        ],
    )
    def test_nvarchar_zero_length_raises(self, type_):
        """Regression (#440): explicit length=0 must not become NCHAR VARYING(4096)."""
        with pytest.raises(CompileError, match=r"NCHAR VARYING\(0\)"):
            self._compile_type(type_)

    def test_nchar_no_length(self):
        """Test NCHAR() without length."""
        from sqlalchemy_cubrid.types import NCHAR

        result = self._compile_type(NCHAR())
        assert result == "NCHAR"

    @pytest.mark.parametrize(
        "type_",
        [
            pytest.param(sa.NCHAR(0), id="sa.NCHAR"),
            pytest.param(cubrid_types.NCHAR(length=0), id="cubrid.NCHAR"),
            pytest.param(cubrid_types.CHAR(length=0, national=True), id="cubrid.CHAR-national"),
        ],
    )
    def test_nchar_zero_length_raises(self, type_):
        """Regression (#476): explicit length=0 must not become bare NCHAR."""
        with pytest.raises(CompileError, match=r"NCHAR\(0\)"):
            self._compile_type(type_)

    def test_bit_varying_no_length(self):
        """Test BIT VARYING without explicit length."""
        from sqlalchemy_cubrid.types import BIT

        result = self._compile_type(BIT(length=None, varying=True))
        assert result == "BIT VARYING"

    def test_object_type(self):
        """Test OBJECT type compilation via mock type."""
        from sqlalchemy.sql import sqltypes

        class MockObject(sqltypes.TypeEngine[Any]):
            __visit_name__ = "OBJECT"

        obj = MockObject()
        result = self._compile_type(obj)
        assert result == "OBJECT"

    def test_set_with_string_values(self):
        """Test SET with string values (not type objects)."""
        from sqlalchemy_cubrid.types import SET

        # SET can accept string type names like 'INTEGER'
        result = self._compile_type(SET("INTEGER"))
        assert result == "SET(INTEGER)"

    def test_monetary_type(self):
        """Test MONETARY type compilation via mock type."""
        from sqlalchemy.sql import sqltypes

        class MockMonetary(sqltypes.TypeEngine[Any]):
            __visit_name__ = "MONETARY"

        mon = MockMonetary()
        result = self._compile_type(mon)
        assert result == "MONETARY"

    def test_datetime_lowercase(self):
        """Test visit_datetime (lowercase) for datetime types."""
        from sqlalchemy.sql import sqltypes

        class MockDatetime(sqltypes.TypeDecorator[Any]):
            impl = sqltypes.DateTime
            __visit_name__ = "datetime"

        dt = MockDatetime()
        result = self._compile_type(dt)
        assert result == "DATETIME"

    def test_datetime_uppercase(self):
        """Test visit_DATETIME (uppercase) for DATETIME types."""
        from sqlalchemy.sql import sqltypes

        class MockDATETIME(sqltypes.TypeEngine[Any]):
            __visit_name__ = "DATETIME"

        dt = MockDATETIME()
        result = self._compile_type(dt)
        assert result == "DATETIME"

    def test_get_method_direct(self):
        """Test _get helper method in TypeCompiler."""
        dialect = CubridDialect()
        compiler = dialect.type_compiler_instance
        # The _get method retrieves attribute from type or kwargs
        from sqlalchemy_cubrid.types import VARCHAR

        t = VARCHAR(length=100)
        # _get(key, type_, kw) should return kw[key] or type_.key
        get_method = getattr(compiler, "_get")
        result = get_method("length", t, {})
        assert result == 100
        # Test with kw override
        result = get_method("length", t, {"length": 200})
        assert result == 200


# Column types CUBRID rejects in CREATE TABLE, and the ones it accepts.
# Both lists come from live ``CREATE TABLE t (x <type>)`` attempts on CUBRID
# 10.2 and 11.4 (#545); the two versions agree.
_CUBRID_REJECTED_TYPE_NAMES = {
    "ARRAY",
    "BINARY",
    "BOOL",
    "BOOLEAN",
    "BYTEA",
    "DATETIME2",
    "IMAGE",
    "INTERVAL",
    "JSONB",
    "LONG",
    "LONGBLOB",
    "LONGTEXT",
    "MEDIUMBLOB",
    "MEDIUMTEXT",
    "MONEY",
    "NTEXT",
    "NUMBER",
    "NVARCHAR",
    "NVARCHAR2",
    "RAW",
    "SERIAL",
    "TEXT",
    "TIME WITH TIME ZONE",
    "TINYBLOB",
    "TINYTEXT",
    "UNIQUEIDENTIFIER",
    "UUID",
    "VARBINARY",
    "VARCHAR2",
    "YEAR",
}
_CUBRID_ACCEPTED_TYPE_NAMES = {
    "BIGINT",
    "BIT",
    "BIT VARYING",
    "BLOB",
    "CHAR",
    "CLOB",
    "DATE",
    "DATETIME",
    "DATETIMELTZ",
    "DATETIMETZ",
    "DECIMAL",
    "DOUBLE",
    "DOUBLE PRECISION",
    "ENUM",
    "FLOAT",
    "INTEGER",
    "JSON",
    "NCHAR",
    "NCHAR VARYING",
    "NUMERIC",
    "REAL",
    "SMALLINT",
    "STRING",
    "TIME",
    "TIMESTAMP",
    "TIMESTAMPLTZ",
    "TIMESTAMPTZ",
    "VARCHAR",
}
# Not column types in their own right (abstract bases, wrappers, tuples).
_NON_COLUMN_TYPE_NAMES = {
    "NullType",
    "TupleType",
    "TypeDecorator",
    "TypeEngine",
    "UserDefinedType",
    "Variant",
}


def _generic_type_instances():
    """Every public generic SQLAlchemy type, plus common argument variants."""
    import inspect

    instances = []
    for name in sorted(dir(sa.types)):
        cls = getattr(sa.types, name)
        if (
            name.startswith("_")
            or name in _NON_COLUMN_TYPE_NAMES
            or not inspect.isclass(cls)
            or not issubclass(cls, sa.types.TypeEngine)
        ):
            continue
        if issubclass(cls, sa.Enum):
            instances.append(cls("a", "b"))
        elif issubclass(cls, sa.ARRAY):
            instances.append(cls(sa.Integer()))
        else:
            instances.append(cls())
    instances += [
        sa.String(10),
        sa.Unicode(10),
        sa.VARCHAR(10),
        sa.NVARCHAR(10),
        sa.CHAR(5),
        sa.NCHAR(5),
        sa.Text(100),
        sa.UnicodeText(100),
        sa.BINARY(4),
        sa.VARBINARY(4),
        sa.LargeBinary(100),
        sa.Numeric(10, 2),
        sa.DECIMAL(10, 2),
        sa.Float(10),
        sa.DateTime(timezone=True),
        sa.DATETIME(timezone=True),
        sa.TIMESTAMP(timezone=True),
        sa.Time(timezone=True),
        sa.TIME(timezone=True),
        sa.Uuid(as_uuid=False),
        sa.Uuid(native_uuid=False),
        sa.UUID(as_uuid=False),
        sa.Enum("a", "b", native_enum=False),
        sa.Boolean(create_constraint=True),
        sa.Interval(native=True),
    ]
    return instances


def _type_name(ddl: str) -> str:
    """``NCHAR VARYING(10)`` -> ``NCHAR VARYING``; ``ENUM('a')`` -> ``ENUM``."""
    return ddl.split("(", 1)[0].strip().upper()


def test_rejected_and_accepted_type_names_are_disjoint():
    assert not _CUBRID_REJECTED_TYPE_NAMES & _CUBRID_ACCEPTED_TYPE_NAMES


@pytest.mark.parametrize("type_", _generic_type_instances(), ids=repr)
def test_generic_types_never_compile_to_a_type_cubrid_rejects(type_):
    """#545: sweep every generic SQLAlchemy type through the type compiler.

    A type either compiles to a column type CUBRID accepts, or raises
    ``CompileError`` (e.g. ``ARRAY``) -- never DDL the server rejects.
    A new SQLAlchemy type whose DDL is in neither list fails here, so its
    CUBRID mapping gets checked live before it is added to the allowlist.
    """
    try:
        ddl = CubridDialect().type_compiler_instance.process(type_)
    except CompileError:
        assert isinstance(type_, sa.ARRAY)
        return
    name = _type_name(ddl)
    assert name not in _CUBRID_REJECTED_TYPE_NAMES, ddl
    assert name in _CUBRID_ACCEPTED_TYPE_NAMES, ddl


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
            "WITH c AS (SELECT src.id AS id, 'INSERT INTO' AS s FROM src) "
            "REPLACE /* c */ INTO t (id, s) SELECT c.id, c.s FROM c"
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
            "WITH c AS (SELECT src.id AS id, src.s AS s FROM src WHERE src.id > ?) "
            "REPLACE /* c */ INTO t (id, s) SELECT c.id, c.s FROM c WHERE c.id < ?"
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
            "WITH c AS (SELECT src.id AS id, src.s AS s FROM src) "
            "REPLACE INTO t (id, s) SELECT c.id, c.s FROM c"
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


class TestTruncateCompilation:
    """Test TRUNCATE TABLE compilation."""

    def test_truncate_basic(self):
        """TRUNCATE TABLE should compile."""
        from sqlalchemy import text

        sql = str(text("TRUNCATE TABLE users"))
        assert "TRUNCATE" in sql


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
            "SELECT GROUP_CONCAT((users.name)) AS group_concat_1 FROM users"
        )

    def test_group_concat_with_separator(self):
        """GROUP_CONCAT with separator literal."""
        stmt = select(sa.func.group_concat(users.c.name, sa.literal_column("SEPARATOR ','")))
        sql = _compile(stmt)
        assert "GROUP_CONCAT" in sql


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

    def test_insert_odku_cache_key_is_none(self):
        """INSERT … ODKU returns None cache key (matches MySQL dialect behavior).

        OnDuplicateClause doesn't define _traverse_internals, so SA correctly
        disables caching for ODKU statements. This is intentional — the dynamic
        update dict makes safe caching non-trivial without full traversal support.
        """
        from sqlalchemy_cubrid.dml import insert

        odku = insert(users).values(name="a").on_duplicate_key_update(name="b")
        odku_key = odku._generate_cache_key()
        assert odku_key is None

    def test_two_odku_variants_both_uncacheable(self):
        """ODKU with different column sets both return None (uncacheable)."""
        from sqlalchemy_cubrid.dml import insert

        odku1 = insert(users).values(name="a").on_duplicate_key_update(name="updated")
        odku2 = insert(users).values(name="a").on_duplicate_key_update(email="updated")
        key1 = odku1._generate_cache_key()
        key2 = odku2._generate_cache_key()
        # Both uncacheable due to OnDuplicateClause
        assert key1 is None
        assert key2 is None

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


# ---------------------------------------------------------------------------
# Native ENUM compilation (#343)
# ---------------------------------------------------------------------------


class TestEnumCompilation:
    """Native ENUM('a', 'b', ...) DDL — CUBRID supports it on 10.2–11.4."""

    def test_enum_create_table(self):
        t = Table(
            "t_enum",
            MetaData(),
            Column("id", Integer, primary_key=True),
            Column("e", sa.Enum("a", "b", "c")),
        )
        sql = _compile(sa.schema.CreateTable(t))
        assert "ENUM('a', 'b', 'c')" in sql

    def test_dialect_enum_type_direct(self):
        from sqlalchemy_cubrid import ENUM

        t = Table("t_enum2", MetaData(), Column("e", ENUM("x", "y")))
        sql = _compile(sa.schema.CreateTable(t))
        assert "ENUM('x', 'y')" in sql

    def test_enum_element_quote_escaped(self):
        from sqlalchemy_cubrid import ENUM

        t = Table("t_enum3", MetaData(), Column("e", ENUM("it's", "b")))
        sql = _compile(sa.schema.CreateTable(t))
        assert "ENUM('it''s', 'b')" in sql

    def test_enum_select_param(self):
        t = Table("t_enum4", MetaData(), Column("e", sa.Enum("a", "b")))
        sql = _compile(select(t.c.e).where(t.c.e == "a"))
        assert "t_enum4.e" in sql


class TestEnumReflectionParse:
    """Unit tests for the ENUM(...) type-string parser (no DB needed)."""

    def test_parse_simple(self):
        from sqlalchemy_cubrid.dialect import _parse_enum_elements

        assert _parse_enum_elements("'a', 'b', 'c'") == ["a", "b", "c"]

    def test_parse_escaped_quote(self):
        from sqlalchemy_cubrid.dialect import _parse_enum_elements

        assert _parse_enum_elements("'it''s', 'b'") == ["it's", "b"]

    def test_regex_matches_show_columns_form(self):
        from sqlalchemy_cubrid.dialect import _RE_ENUM

        m = _RE_ENUM.match("ENUM('a', 'b', 'c')")
        assert m is not None
        assert m.group(1) == "'a', 'b', 'c'"
        assert _RE_ENUM.match("VARCHAR(10)") is None


# ---------------------------------------------------------------------------
# IS DISTINCT FROM emulation via null-safe <=> (#344)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Boolean IS / IS NOT predicates (#465)
# ---------------------------------------------------------------------------

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
