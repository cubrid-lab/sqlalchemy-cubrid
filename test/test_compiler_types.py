# test/test_compiler_types.py
"""Offline type compiler tests — no live CUBRID required.

Column type rendering through the CUBRID type compiler, the generic types
CUBRID rejects in CREATE TABLE, and native ENUM DDL.
"""

from __future__ import annotations

import re

import pytest
import sqlalchemy as sa
from typing import Any
from sqlalchemy import Column, Integer, MetaData, Table, select
from sqlalchemy.exc import CompileError

from sqlalchemy_cubrid import types as cubrid_types
from sqlalchemy_cubrid.dialect import CubridDialect
from test._compiler_helpers import _compile


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

    @pytest.mark.parametrize(
        ("type_", "expected"),
        [
            pytest.param(sa.String(-1), "VARCHAR(-1)", id="String"),
            pytest.param(sa.Unicode(-1), "VARCHAR(-1)", id="Unicode"),
            pytest.param(sa.VARCHAR(-1), "VARCHAR(-1)", id="sa.VARCHAR"),
            pytest.param(cubrid_types.VARCHAR(length=-1), "VARCHAR(-1)", id="cubrid.VARCHAR"),
            pytest.param(sa.CHAR(-1), "CHAR(-1)", id="sa.CHAR"),
            pytest.param(cubrid_types.CHAR(length=-1), "CHAR(-1)", id="cubrid.CHAR"),
            pytest.param(cubrid_types.NVARCHAR(length=-1), "NCHAR VARYING(-1)", id="NVARCHAR"),
            pytest.param(cubrid_types.NCHAR(length=-1), "NCHAR(-1)", id="NCHAR"),
            pytest.param(cubrid_types.BIT(length=-1), "BIT(-1)", id="BIT"),
            pytest.param(
                cubrid_types.BIT(length=-1, varying=True),
                "BIT VARYING(-1)",
                id="BIT-VARYING",
            ),
            pytest.param(sa.BINARY(-1), "BINARY(-1)", id="BINARY"),
            pytest.param(sa.VARBINARY(-1), "VARBINARY(-1)", id="VARBINARY"),
        ],
    )
    def test_character_and_bit_types_reject_negative_length(self, type_, expected):
        """Regression (#491): negative lengths fail locally instead of reaching CUBRID."""
        with pytest.raises(CompileError, match=rf"{re.escape(expected)}"):
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

    @pytest.mark.parametrize(
        ("no_backslash_escapes", "expected"),
        [(True, "ENUM('a\\''b', 'c')"), (False, "ENUM('a\\\\''b', 'c')")],
    )
    def test_enum_label_backslash_follows_server_mode(self, no_backslash_escapes, expected):
        """#863: ENUM labels escape a backslash as other string literals do."""
        t = Table("t_enum5", MetaData(), Column("e", sa.Enum("a\\'b", "c")))
        dialect = CubridDialect(no_backslash_escapes=no_backslash_escapes)
        sql = _compile(sa.schema.CreateTable(t), dialect=dialect)
        assert expected in sql

    def test_enum_select_param(self):
        t = Table("t_enum4", MetaData(), Column("e", sa.Enum("a", "b")))
        sql = _compile(select(t.c.e).where(t.c.e == "a"))
        assert "t_enum4.e" in sql


class TestEnumTypeDetection:
    """ENUM type detection stays separate from exact catalog label reading."""

    def test_regex_matches_show_columns_form(self):
        from sqlalchemy_cubrid.dialect import _RE_ENUM

        m = _RE_ENUM.match("ENUM('a', 'b', 'c')")
        assert m is not None
        assert m.group(1) == "'a', 'b', 'c'"
        assert _RE_ENUM.match("VARCHAR(10)") is None
