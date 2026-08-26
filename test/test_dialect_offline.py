from __future__ import annotations

import sys
import types
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import types as sqltypes
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.engine import url
from sqlalchemy.sql.elements import quoted_name

from sqlalchemy_cubrid.dialect import CubridDialect
from sqlalchemy_cubrid.dialect import _split_collection_members


class TestSplitCollectionMembers:
    def test_single_simple_member(self) -> None:
        assert _split_collection_members("INT") == ["INT"]

    def test_single_member_with_params(self) -> None:
        assert _split_collection_members("NUMERIC(10,2)") == ["NUMERIC(10,2)"]

    def test_multiple_members_with_params(self) -> None:
        assert _split_collection_members("NUMERIC(10,2),VARCHAR(50)") == [
            "NUMERIC(10,2)",
            "VARCHAR(50)",
        ]

    def test_nested_parentheses(self) -> None:
        assert _split_collection_members("SET(INT),VARCHAR(50)") == [
            "SET(INT)",
            "VARCHAR(50)",
        ]

    def test_empty_input(self) -> None:
        assert _split_collection_members("") == []
        assert _split_collection_members("   ") == []

    def test_unbalanced_close_paren_returns_whole(self) -> None:
        assert _split_collection_members("INT)") == ["INT)"]


def _invoke_reflection(dialect, method_name, connection, *args, **kwargs):
    method = getattr(dialect, method_name)
    if hasattr(method, "__wrapped__"):
        return method.__wrapped__(dialect, connection, *args, **kwargs)
    return method(connection, *args, **kwargs)


class TestDialectBasics:
    def test_init_with_and_without_isolation_level(self):
        default_dialect = CubridDialect()
        assert default_dialect.isolation_level is None

        custom_dialect = CubridDialect(isolation_level="SERIALIZABLE")
        assert custom_dialect.isolation_level == "SERIALIZABLE"

    def test_supports_twophase_commit_is_false(self):
        """CUBRID does not support two-phase commit."""
        dialect = CubridDialect()
        assert dialect.supports_twophase_commit is False

    def test_import_dbapi_success(self):
        fake_module = types.ModuleType("CUBRIDdb")
        with patch.dict(sys.modules, {"CUBRIDdb": fake_module}):
            imported = CubridDialect.import_dbapi()
        assert imported is fake_module

    def test_import_dbapi_import_error(self):
        import builtins

        real_import = builtins.__import__

        def _fake_import(name, *args, **kwargs):
            if name == "CUBRIDdb":
                raise ImportError("driver missing")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_fake_import):
            with pytest.raises(ImportError, match="Could not import CUBRIDdb"):
                CubridDialect.import_dbapi()

    def test_legacy_dbapi_method_calls_import_dbapi(self):
        fake_module = object()
        with patch.object(CubridDialect, "import_dbapi", return_value=fake_module) as mocked:
            assert CubridDialect.dbapi() is fake_module
        mocked.assert_called_once_with()

    def test_create_connect_args_full_url(self):
        dialect = CubridDialect()
        parsed = url.make_url("cubrid://dba:pw@dbhost:33001/demodb")

        args, kwargs = dialect.create_connect_args(parsed)

        assert args == ("CUBRID:dbhost:33001:demodb:::", "dba", "pw")
        assert kwargs == {}

    def test_create_connect_args_defaults(self):
        dialect = CubridDialect()
        parsed = url.make_url("cubrid://")

        args, kwargs = dialect.create_connect_args(parsed)

        assert args == ("CUBRID:localhost:33000::::", "", "")
        assert kwargs == {}

    def test_create_connect_args_none_url_raises(self):
        dialect = CubridDialect()
        none_url = cast(Any, None)
        with pytest.raises(ValueError, match="Unexpected database URL format"):
            dialect.create_connect_args(none_url)

    def test_on_connect_without_isolation_level(self):
        dialect = CubridDialect()
        dialect.set_isolation_level = MagicMock()

        dbapi_conn = MagicMock()
        hook = dialect.on_connect()
        hook(dbapi_conn)

        dbapi_conn.set_autocommit.assert_called_once_with(False)
        dialect.set_isolation_level.assert_not_called()

    def test_on_connect_with_isolation_level(self):
        dialect = CubridDialect(isolation_level="SERIALIZABLE")
        dialect.set_isolation_level = MagicMock()

        dbapi_conn = MagicMock()
        hook = dialect.on_connect()
        hook(dbapi_conn)

        dbapi_conn.set_autocommit.assert_called_once_with(False)
        dialect.set_isolation_level.assert_called_once_with(dbapi_conn, "SERIALIZABLE")

    def test_server_version_info_match_and_non_match(self):
        dialect = CubridDialect()

        connection = MagicMock()
        connection.execute.return_value.scalar.return_value = "11.2.9.0866"
        assert dialect._get_server_version_info(connection) == (11, 2, 9, 866)

        connection.execute.return_value.scalar.return_value = "not-a-version"
        assert dialect._get_server_version_info(connection) is None

    def test_get_default_schema_name(self):
        dialect = CubridDialect()
        connection = MagicMock()
        connection.execute.return_value.scalar.return_value = "dba"

        assert dialect._get_default_schema_name(connection) == "dba"

    def test_get_default_schema_name_null_returns_none(self):
        """SCHEMA() returning SQL NULL must yield None, not the string 'None'."""
        dialect = CubridDialect()
        connection = MagicMock()
        connection.execute.return_value.scalar.return_value = None

        assert dialect._get_default_schema_name(connection) is None

    def test_get_schema_names_empty_when_default_is_none(self):
        """With no default schema, get_schema_names() returns [] (not ['None'])."""
        dialect = CubridDialect()
        dialect.default_schema_name = None
        connection = MagicMock()

        assert dialect.get_schema_names(connection) == []

    def test_get_schema_names_returns_default(self):
        dialect = CubridDialect()
        dialect.default_schema_name = "dba"
        connection = MagicMock()

        assert dialect.get_schema_names(connection) == ["dba"]

    def test_initialize_delegates_to_default_dialect(self):
        dialect = CubridDialect()
        connection = MagicMock()

        with patch("sqlalchemy.engine.default.DefaultDialect.initialize") as init_super:
            dialect.initialize(connection)

        init_super.assert_called_once_with(connection)


class TestIsolationLevelMethods:
    def test_get_isolation_level_string(self):
        dialect = CubridDialect()
        cursor = MagicMock()
        cursor.fetchone.return_value = ("SERIALIZABLE",)
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        level = dialect.get_isolation_level(dbapi_conn)

        assert level == "SERIALIZABLE"
        cursor.execute.assert_any_call("GET TRANSACTION ISOLATION LEVEL TO X")
        cursor.execute.assert_any_call("SELECT X")
        cursor.close.assert_called_once_with()

    def test_get_isolation_level_numeric(self):
        dialect = CubridDialect()
        cursor = MagicMock()
        cursor.fetchone.return_value = (6,)
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        level = dialect.get_isolation_level(dbapi_conn)
        assert level == "SERIALIZABLE"

    def test_get_isolation_level_unknown_numeric(self):
        dialect = CubridDialect()
        cursor = MagicMock()
        cursor.fetchone.return_value = (99,)
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        level = dialect.get_isolation_level(dbapi_conn)
        assert level == "99"

    def test_get_isolation_level_none_row_returns_default(self):
        dialect = CubridDialect()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        level = dialect.get_isolation_level(dbapi_conn)
        assert level == "READ COMMITTED"

    def test_get_isolation_level_values(self):
        dialect = CubridDialect()
        levels = dialect.get_isolation_level_values()

        assert len(levels) == 6
        assert "SERIALIZABLE" in levels
        assert "READ COMMITTED" in levels
        assert "REPEATABLE READ" in levels

    def test_set_isolation_level_all_mapped_levels(self):
        """set_isolation_level works for every valid string level."""
        dialect = CubridDialect()
        expected_map = {
            "SERIALIZABLE": 6,
            "REPEATABLE READ": 5,
            "READ COMMITTED": 4,
            "CURSOR STABILITY": 4,
        }
        for level_name, expected_num in expected_map.items():
            cursor = MagicMock()
            dbapi_conn = MagicMock(spec=[])
            dbapi_conn.cursor = MagicMock(return_value=cursor)

            dialect.set_isolation_level(dbapi_conn, level_name)

            cursor.execute.assert_any_call(f"SET TRANSACTION ISOLATION LEVEL {expected_num}")
            cursor.execute.assert_any_call("COMMIT")
            cursor.close.assert_called_once_with()

    def test_set_isolation_level_with_plain_dbapi_class(self):
        dialect = CubridDialect()
        cursor = MagicMock()

        class PlainDBAPIConnection:
            def cursor(self):
                return cursor

        plain_conn = PlainDBAPIConnection()
        dialect.set_isolation_level(plain_conn, "SERIALIZABLE")

        cursor.execute.assert_any_call("SET TRANSACTION ISOLATION LEVEL 6")
        cursor.execute.assert_any_call("COMMIT")
        cursor.close.assert_called_once_with()

    def test_set_isolation_level_invalid_raises(self):
        dialect = CubridDialect()
        cursor = MagicMock()
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        with pytest.raises(ValueError, match="Invalid isolation level"):
            dialect.set_isolation_level(dbapi_conn, "NONEXISTENT LEVEL")

    def test_set_isolation_level_obsolete_levels_rejected(self):
        """Legacy pre-MVCC levels (codes 1-3) are no longer accepted.

        CUBRID's MVCC engine (10.0+) supports only READ COMMITTED (4),
        REPEATABLE READ (5) and SERIALIZABLE (6); the server rejects
        SET TRANSACTION ISOLATION LEVEL 1|2|3, so the dialect must not
        offer names that resolve to those codes.
        """
        dialect = CubridDialect()
        obsolete = [
            "REPEATABLE READ SCHEMA, READ UNCOMMITTED INSTANCES",
            "READ COMMITTED SCHEMA, READ COMMITTED INSTANCES",
            "READ COMMITTED SCHEMA, READ UNCOMMITTED INSTANCES",
        ]
        for name in obsolete:
            dbapi_conn = MagicMock()
            dbapi_conn.cursor.return_value = MagicMock()
            with pytest.raises(ValueError, match="Invalid isolation level"):
                dialect.set_isolation_level(dbapi_conn, name)
        # And none of the surviving codes are the obsolete ones.
        assert set(dialect._ISOLATION_LEVEL_MAP.values()) == {4, 5, 6}
        assert set(dialect._ISOLATION_LEVEL_REVERSE) == {4, 5, 6}

    def test_reset_isolation_level(self):
        dialect = CubridDialect()
        cursor = MagicMock()
        # Use spec=[] to prevent MagicMock from auto-creating
        # a .connection attribute, which would cause set_isolation_level
        # to unwrap to a different mock object.
        dbapi_conn = MagicMock(spec=[])
        dbapi_conn.cursor = MagicMock(return_value=cursor)

        dialect.reset_isolation_level(dbapi_conn)
        cursor.execute.assert_any_call("SET TRANSACTION ISOLATION LEVEL 4")

    def test_isolation_level_set_get_roundtrip(self):
        """Every accepted input name round-trips to the same numeric code.

        Multiple aliases collapse onto one canonical name per code, so the
        invariant is semantic: MAP[name] == MAP[REVERSE[MAP[name]]].
        """
        dialect = CubridDialect()
        for name in dialect.get_isolation_level_values():
            code = dialect._ISOLATION_LEVEL_MAP[name.upper()]
            canonical = dialect._ISOLATION_LEVEL_REVERSE[code]
            # get_isolation_level() returns a value SA recognizes ...
            assert canonical in dialect.get_isolation_level_values()
            # ... and it maps back to the same underlying code.
            assert dialect._ISOLATION_LEVEL_MAP[canonical.upper()] == code

    def test_isolation_level_reverse_covers_all_codes(self):
        """Reverse map has one canonical name for every code in the forward map."""
        dialect = CubridDialect()
        forward_codes = set(dialect._ISOLATION_LEVEL_MAP.values())
        assert set(dialect._ISOLATION_LEVEL_REVERSE) == forward_codes
        # Short standard names are canonical for 4/5/6.
        assert dialect._ISOLATION_LEVEL_REVERSE[6] == "SERIALIZABLE"
        assert dialect._ISOLATION_LEVEL_REVERSE[5] == "REPEATABLE READ"
        assert dialect._ISOLATION_LEVEL_REVERSE[4] == "READ COMMITTED"


class TestExistenceChecks:
    def test_has_table_true_and_false(self):
        dialect = CubridDialect()
        connection = MagicMock()

        connection.execute.return_value.scalar.return_value = 1
        assert dialect.has_table(connection, "users") is True

        connection.execute.return_value.scalar.return_value = 0
        assert dialect.has_table(connection, "users") is False

    def test_has_table_recognizes_views(self):
        dialect = CubridDialect()
        connection = MagicMock()

        connection.execute.return_value.scalar.return_value = 1
        assert dialect.has_table(connection, "active_users") is True

    def test_has_index_true_false_and_exception(self):
        dialect = CubridDialect()
        connection = MagicMock()

        connection.execute.return_value.scalar.return_value = 2
        assert dialect.has_index(connection, "users", "ix_users_name") is True
        call_args = connection.execute.call_args
        bound_params = call_args[0][1]
        assert bound_params == {"table": "users", "name": "ix_users_name"}

        connection.execute.return_value.scalar.return_value = 0
        assert dialect.has_index(connection, "users", "ix_users_name") is False

        connection.execute.side_effect = RuntimeError("metadata unavailable")
        assert dialect.has_index(connection, "users", "ix_users_name") is False

    def test_has_index_filters_by_table(self):
        dialect = CubridDialect()
        connection = MagicMock()

        connection.execute.return_value.scalar.return_value = 0
        assert dialect.has_index(connection, "orders", "ix_name") is False
        call_args = connection.execute.call_args
        bound_params = call_args[0][1]
        assert bound_params["table"] == "orders"

    def test_has_sequence_always_false(self):
        dialect = CubridDialect()
        assert dialect.has_sequence(MagicMock(), "seq_users") is False


class TestReflectionMethods:
    def test_get_columns_covers_all_type_branches(self):
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        rows = [
            ("char_col", "CHAR(3)", "YES", "", None, ""),
            ("varchar_col", "VARCHAR(100)", "YES", "", "v", ""),
            ("nchar_col", "NCHAR(10)", "NO", "", None, None),
            ("num_col", "NUMERIC(10,2)", "YES", "", "0", ""),
            ("dec_col", "DECIMAL", "NO", "", None, ""),
            ("int_col", "INTEGER", "NO", "", None, "auto_increment"),
            ("unknown_col", "MYSTERY", "YES", "", None, ""),
        ]
        comment_rows = [
            ("char_col", "char comment"),
            ("int_col", "int comment"),
            ("unknown_col", None),
        ]
        connection.execute.side_effect = [rows, comment_rows]

        with patch("sqlalchemy.util.warn") as warn:
            columns = _invoke_reflection(dialect, "get_columns", connection, "sample_table")

        assert len(columns) == 7

        assert columns[0]["type"].__class__.__name__ == "CHAR"
        assert columns[0]["type"].length == 3

        assert columns[1]["type"].__class__.__name__ == "VARCHAR"
        assert columns[1]["type"].length == 100
        assert columns[1]["default"] == "v"

        assert columns[2]["type"].__class__.__name__ == "NCHAR"
        assert columns[2]["type"].length == 10
        assert columns[2]["nullable"] is False

        assert columns[3]["type"].__class__.__name__ == "NUMERIC"
        assert columns[3]["type"].precision == 10
        assert columns[3]["type"].scale == 2

        assert columns[4]["type"].__class__.__name__ == "DECIMAL"

        assert columns[5]["type"].__class__.__name__ == "INTEGER"
        assert columns[5]["autoincrement"] is True
        assert columns[5]["comment"] == "int comment"

        assert columns[6]["type"] is sqltypes.NULLTYPE
        assert columns[6]["comment"] is None
        warn.assert_called_once()

    def test_get_columns_preserves_timezone_for_tz_types(self):
        """Regression: TIMESTAMPTZ/DATETIMETZ reflection must set timezone=True. (#181)"""
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        rows = [
            ("ts_col", "TIMESTAMP", "YES", "", None, ""),
            ("tstz_col", "TIMESTAMPTZ", "YES", "", None, ""),
            ("tsltz_col", "TIMESTAMPLTZ", "YES", "", None, ""),
            ("dt_col", "DATETIME", "YES", "", None, ""),
            ("dttz_col", "DATETIMETZ", "YES", "", None, ""),
            ("dtltz_col", "DATETIMELTZ", "YES", "", None, ""),
        ]
        comment_rows = []
        connection.execute.side_effect = [rows, comment_rows]

        columns = _invoke_reflection(dialect, "get_columns", connection, "tz_table")

        assert len(columns) == 6
        # Plain types: no timezone
        assert getattr(columns[0]["type"], "timezone", False) is False
        assert getattr(columns[3]["type"], "timezone", False) is False
        # TZ/LTZ types: timezone=True
        assert columns[1]["type"].timezone is True  # TIMESTAMPTZ
        assert columns[2]["type"].timezone is True  # TIMESTAMPLTZ
        assert columns[4]["type"].timezone is True  # DATETIMETZ
        assert columns[5]["type"].timezone is True  # DATETIMELTZ

    def test_get_columns_char_varying_and_nchar_varying_reflection(self):
        """Regression: CHAR VARYING/NCHAR VARYING reflection maps to VARCHAR/NVARCHAR with correct lengths. (#201)"""
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        rows = [
            ("char_var_col", "CHAR VARYING(50)", "YES", "", None, ""),
            ("nchar_var_col", "NCHAR VARYING(20)", "NO", "", None, ""),
        ]
        comment_rows = []
        connection.execute.side_effect = [rows, comment_rows]

        columns = _invoke_reflection(dialect, "get_columns", connection, "char_varying_table")

        assert len(columns) == 2

        assert columns[0]["type"].__class__.__name__ == "VARCHAR"
        assert columns[0]["type"].length == 50
        assert columns[0]["nullable"] is True

        assert columns[1]["type"].__class__.__name__ == "NVARCHAR"
        assert columns[1]["type"].length == 20
        assert columns[1]["nullable"] is False

    def test_get_columns_collection_with_precision_scale_member(self):
        """Regression: SET(NUMERIC(10,2)) must not split on the inner comma. (#204)"""
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        rows = [
            ("set_col", "SET(NUMERIC(10,2),VARCHAR(50))", "YES", "", None, ""),
        ]
        comment_rows: list[Any] = []
        connection.execute.side_effect = [rows, comment_rows]

        columns = _invoke_reflection(dialect, "get_columns", connection, "coll_table")

        assert len(columns) == 1
        col_type = columns[0]["type"]
        assert col_type.__class__.__name__ == "SET"
        members = col_type._ddl_values
        assert len(members) == 2
        assert members[0].__class__.__name__ == "NUMERIC"
        assert members[0].precision == 10
        assert members[0].scale == 2
        assert members[1].__class__.__name__ == "VARCHAR"
        assert members[1].length == 50

    def test_get_pk_constraint_with_primary_key_and_constraint_name(self):
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        show_columns_rows = [
            ("id", "INTEGER", "NO", "PRI", None, "auto_increment"),
            ("name", "VARCHAR(50)", "YES", "", None, ""),
        ]
        constraint_result = MagicMock()
        constraint_result.fetchone.return_value = ("pk_users",)
        connection.execute.side_effect = [show_columns_rows, constraint_result]

        pk = _invoke_reflection(dialect, "get_pk_constraint", connection, "users")

        assert pk == {"name": "pk_users", "constrained_columns": ["id"]}

    def test_get_foreign_keys_success_and_exception(self):
        dialect = CubridDialect()
        # ``main`` is this connection's effective schema; passing it must not
        # trip the non-default-schema guard (#291) while we verify FK parsing.
        dialect.default_schema_name = "main"

        ddl = (
            "CREATE TABLE [orders] (\n"
            "  [id] INTEGER NOT NULL,\n"
            "  CONSTRAINT [pk_orders] PRIMARY KEY ([id]),\n"
            "  CONSTRAINT [fk_order_user] FOREIGN KEY ([user_id], [tenant_id]) "
            "REFERENCES [dba.users] ([id], [tenant_id]) "
            "ON DELETE RESTRICT ON UPDATE RESTRICT,\n"
            "  CONSTRAINT [fk_order_legacy] FOREIGN KEY ([legacy_id]) "
            "REFERENCES [legacy] ([id])\n"
            ")"
        )

        success_conn = MagicMock()
        success_conn.info_cache = {}
        success_conn.dialect_options = {}
        success_result = MagicMock()
        success_result.fetchone.return_value = ("orders", ddl)
        success_conn.execute.return_value = success_result

        fks = _invoke_reflection(
            dialect,
            "get_foreign_keys",
            success_conn,
            "orders",
            schema="main",
        )

        assert len(fks) == 2
        first = next(item for item in fks if item["name"] == "fk_order_user")
        assert first["constrained_columns"] == ["user_id", "tenant_id"]
        # Owner prefix (``dba.``) must be stripped from the referenced table.
        assert first["referred_table"] == "users"
        assert first["referred_columns"] == ["id", "tenant_id"]
        assert first["referred_schema"] == "main"

        second = next(item for item in fks if item["name"] == "fk_order_legacy")
        assert second["referred_table"] == "legacy"
        assert second["referred_columns"] == ["id"]

        failed_conn = MagicMock()
        failed_conn.info_cache = {}
        failed_conn.dialect_options = {}
        failed_conn.execute.side_effect = RuntimeError("fk lookup failed")

        assert _invoke_reflection(dialect, "get_foreign_keys", failed_conn, "orders") == []

    def test_get_table_names(self):
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        connection.execute.return_value = [("users",), ("orders",)]

        assert _invoke_reflection(dialect, "get_table_names", connection, schema="main") == []
        assert _invoke_reflection(dialect, "get_table_names", connection, schema=None) == [
            "users",
            "orders",
        ]

    def test_get_view_names(self):
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        connection.execute.return_value = [("active_users",), ("recent_orders",)]

        views = _invoke_reflection(dialect, "get_view_names", connection)
        assert views == ["active_users", "recent_orders"]

    def test_get_view_names_rejects_non_default_schema(self):
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        connection.execute.return_value = [("active_users",)]
        # default_schema_name is None on an uninitialized dialect, so any
        # explicit schema is non-default and must yield [] -- previously this
        # method ignored schema= and returned ALL views (issue #280).
        assert _invoke_reflection(dialect, "get_view_names", connection, schema="main") == []

    def test_schema_reflection_is_consistent_single_schema(self):
        """All list/existence methods honour schema= uniformly (issue #280)."""
        dialect = CubridDialect()
        dialect.default_schema_name = "dba"

        # get_schema_names now agrees with the default schema instead of [].
        conn = MagicMock()
        conn.info_cache = {}
        conn.dialect_options = {}
        assert dialect.get_schema_names(conn) == ["dba"]

        # The default schema is honoured across list methods ...
        tbl_conn = MagicMock()
        tbl_conn.info_cache = {}
        tbl_conn.dialect_options = {}
        tbl_conn.execute.return_value = [("users",)]
        assert _invoke_reflection(dialect, "get_table_names", tbl_conn, schema="dba") == ["users"]

        view_conn = MagicMock()
        view_conn.info_cache = {}
        view_conn.dialect_options = {}
        view_conn.execute.return_value = [("v_users",)]
        assert _invoke_reflection(dialect, "get_view_names", view_conn, schema="dba") == ["v_users"]

        # ... and a non-default schema is uniformly rejected: tables AND views
        # both return [] (no more "0 tables + all views" divergence).
        assert _invoke_reflection(dialect, "get_table_names", tbl_conn, schema="other") == []
        assert _invoke_reflection(dialect, "get_view_names", view_conn, schema="other") == []

        # Existence checks reject non-default schemas without touching the DB.
        has_conn = MagicMock()
        has_conn.info_cache = {}
        has_conn.dialect_options = {}
        assert dialect.has_table(has_conn, "users", schema="other") is False
        assert dialect.has_index(has_conn, "users", "idx", schema="other") is False
        has_conn.execute.assert_not_called()

    def test_get_view_definition_with_and_without_row(self):
        dialect = CubridDialect()

        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        result = MagicMock()
        result.fetchone.return_value = ("view_name", "SELECT * FROM users")
        connection.execute.return_value = result
        assert (
            _invoke_reflection(dialect, "get_view_definition", connection, "user_view")
            == "SELECT * FROM users"
        )

        empty_result = MagicMock()
        empty_result.fetchone.return_value = None
        connection.execute.return_value = empty_result
        assert _invoke_reflection(dialect, "get_view_definition", connection, "user_view") == ""

    def test_get_indexes_with_primary_key_and_exception_paths(self):
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        # Single batch query returns (index_name, is_primary_key, is_foreign_key)
        # tuples for every index on the table.  PK and FK auto-indexes are
        # filtered from the SHOW INDEXES output.
        flag_rows = [
            ("uq_name", 0, 0),
            ("pk_users", 1, 0),
            ("idx_email", 0, 0),
        ]

        show_indexes_rows = [
            (None, 0, "uq_name", None, "first_name"),
            (None, 0, "uq_name", None, "last_name"),
            (None, 0, "pk_users", None, "id"),
            (None, 1, "idx_email", None, "email"),
        ]

        connection.execute.side_effect = [
            flag_rows,  # batch _db_index query
            show_indexes_rows,  # SHOW INDEXES
        ]

        indexes = _invoke_reflection(dialect, "get_indexes", connection, "users")

        assert indexes == [
            {"name": "uq_name", "column_names": ["first_name", "last_name"], "unique": True},
            {"name": "idx_email", "column_names": ["email"], "unique": False},
        ]

    def test_get_indexes_batch_pk_query_failure(self):
        """When the batch catalog query fails, all indexes are returned."""
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        show_indexes_rows = [
            (None, 0, "uq_name", None, "first_name"),
            (None, 0, "pk_users", None, "id"),
        ]

        connection.execute.side_effect = [
            RuntimeError("catalog unavailable"),  # batch flag query fails
            show_indexes_rows,  # SHOW INDEXES
        ]

        indexes = _invoke_reflection(dialect, "get_indexes", connection, "users")

        # Both indexes returned since PK/FK detection failed gracefully.
        assert len(indexes) == 2
        assert indexes[0]["name"] == "uq_name"
        assert indexes[1]["name"] == "pk_users"

    def test_get_indexes_excludes_fk_auto_indexes(self):
        """FK auto-indexes (``_db_index.is_foreign_key`` true) are filtered.

        See cubrid-lab/sqlalchemy-cubrid#120 — otherwise Alembic
        autogenerate emits spurious drop_index/create_index diffs.
        """
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        flag_rows = [
            ("fk_orders_user", 0, 1),
            ("fk_orders_product", 0, 1),
            ("idx_orders_status", 0, 0),
        ]

        connection.execute.side_effect = [
            flag_rows,
            [
                (None, 1, "fk_orders_user", None, "user_id"),
                (None, 1, "fk_orders_product", None, "product_id"),
                (None, 1, "idx_orders_status", None, "status"),
            ],
        ]

        indexes = _invoke_reflection(dialect, "get_indexes", connection, "orders")

        assert indexes == [
            {"name": "idx_orders_status", "column_names": ["status"], "unique": False},
        ]

    def test_get_unique_constraints_success_and_exception(self):
        dialect = CubridDialect()

        ddl = (
            "CREATE TABLE [users] (\n"
            "  [id] INTEGER NOT NULL,\n"
            "  CONSTRAINT [pk_users] PRIMARY KEY ([id]),\n"
            "  CONSTRAINT [uq_users_email] UNIQUE KEY ([email], [tenant_id]),\n"
            "  CONSTRAINT [uq_users_name] UNIQUE KEY ([name])\n"
            ")"
        )

        success_conn = MagicMock()
        success_conn.info_cache = {}
        success_conn.dialect_options = {}
        success_result = MagicMock()
        success_result.fetchone.return_value = ("users", ddl)
        success_conn.execute.return_value = success_result

        unique_constraints = _invoke_reflection(
            dialect,
            "get_unique_constraints",
            success_conn,
            "users",
        )

        assert unique_constraints == [
            {"name": "uq_users_email", "column_names": ["email", "tenant_id"]},
            {"name": "uq_users_name", "column_names": ["name"]},
        ]

        failed_conn = MagicMock()
        failed_conn.info_cache = {}
        failed_conn.dialect_options = {}
        failed_conn.execute.side_effect = RuntimeError("uc lookup failed")

        assert _invoke_reflection(dialect, "get_unique_constraints", failed_conn, "users") == []

    def test_get_unique_constraints_from_catalog_success(self):
        """Primary path: _db_index catalog query returns unique index names,
        SHOW INDEXES resolves column names."""
        dialect = CubridDialect()

        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        # First execute: _db_index returns unique index names (excluding PK/FK)
        # Second execute: SHOW INDEXES returns column details
        unique_name_rows = [
            ("uq_users_email",),
            ("uq_users_name",),
        ]
        show_indexes_rows = [
            (None, 0, "uq_users_email", 1, "email"),
            (None, 0, "uq_users_email", 2, "tenant_id"),
            (None, 0, "uq_users_name", 1, "name"),
            (None, 1, "pk_users", 1, "id"),  # PK — should be excluded
        ]
        connection.execute.side_effect = [unique_name_rows, show_indexes_rows]

        uqs = _invoke_reflection(dialect, "get_unique_constraints", connection, "users")

        assert uqs == [
            {"name": "uq_users_email", "column_names": ["email", "tenant_id"]},
            {"name": "uq_users_name", "column_names": ["name"]},
        ]

    def test_get_unique_constraints_catalog_empty_falls_back_to_ddl(self):
        """When _db_index returns no unique indexes, fall back to DDL regex."""
        dialect = CubridDialect()

        ddl = (
            "CREATE TABLE [users] (\n"
            "  [id] INTEGER NOT NULL,\n"
            "  CONSTRAINT [uq_users_email] UNIQUE KEY ([email])\n"
            ")"
        )

        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        # First execute: _db_index returns empty list (no unique indexes found)
        # Second execute: SHOW CREATE TABLE for DDL fallback
        ddl_result = MagicMock()
        ddl_result.fetchone.return_value = ("users", ddl)
        connection.execute.side_effect = [[], ddl_result]

        uqs = _invoke_reflection(dialect, "get_unique_constraints", connection, "users")

        assert uqs == [{"name": "uq_users_email", "column_names": ["email"]}]

    def test_get_unique_constraints_catalog_exception_falls_back_to_ddl(self):
        """When _db_index query raises an exception, fall back to DDL regex."""
        dialect = CubridDialect()

        ddl = (
            "CREATE TABLE [users] (\n"
            "  [id] INTEGER NOT NULL,\n"
            "  CONSTRAINT [uq_users_email] UNIQUE KEY ([email])\n"
            ")"
        )

        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        # First execute: _db_index raises an exception
        # Second execute: SHOW CREATE TABLE for DDL fallback
        ddl_result = MagicMock()
        ddl_result.fetchone.return_value = ("users", ddl)
        connection.execute.side_effect = [RuntimeError("catalog unavailable"), ddl_result]

        uqs = _invoke_reflection(dialect, "get_unique_constraints", connection, "users")

        assert uqs == [{"name": "uq_users_email", "column_names": ["email"]}]

    def test_get_pk_constraint_name_from_index(self):
        """PK constraint name is fetched from _db_index (not the phantom db_constraint)."""
        dialect = CubridDialect()

        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        show_columns_rows = [
            ("id", "INTEGER", "NO", "PRI", None, "auto_increment"),
        ]
        index_result = MagicMock()
        index_result.fetchone.return_value = ("pk_users",)
        connection.execute.side_effect = [show_columns_rows, index_result]

        pk = _invoke_reflection(dialect, "get_pk_constraint", connection, "users")

        assert pk == {"name": "pk_users", "constrained_columns": ["id"]}

    def test_get_pk_constraint_name_query_failure_returns_none(self):
        """When _db_index query fails, PK name should be None but columns still returned."""
        dialect = CubridDialect()

        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        show_columns_rows = [
            ("id", "INTEGER", "NO", "PRI", None, "auto_increment"),
        ]
        connection.execute.side_effect = [show_columns_rows, RuntimeError("index query failed")]

        pk = _invoke_reflection(dialect, "get_pk_constraint", connection, "users")

        assert pk == {"name": None, "constrained_columns": ["id"]}

    def test_get_check_constraints_get_table_comment_and_schema_names(self):
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        table_comment_result = MagicMock()
        table_comment_result.fetchone.return_value = ("users table comment",)
        connection.execute.return_value = table_comment_result

        checks = _invoke_reflection(dialect, "get_check_constraints", connection, "users")
        comment = _invoke_reflection(dialect, "get_table_comment", connection, "users")

        assert checks == []
        assert comment == {"text": "users table comment"}
        assert dialect.get_schema_names(connection) == []


class TestDoReleaseSavepoint:
    def test_do_release_savepoint_is_noop(self):
        """CUBRID does not support RELEASE SAVEPOINT; method should be a no-op."""
        dialect = CubridDialect()
        connection = MagicMock()
        # Should not raise, should not call anything on connection
        result = dialect.do_release_savepoint(connection, "sp_test")
        assert result is None
        connection.execute.assert_not_called()


class TestIsDisconnect:
    """Tests for CubridDialect.is_disconnect() error detection."""

    @pytest.fixture()
    def dialect_with_dbapi(self):
        """Create a dialect with a mock dbapi module."""
        dialect = CubridDialect()

        # Build a mock dbapi module with CUBRIDdb's actual exception hierarchy:
        # Error (base) -> InterfaceError, DatabaseError, NotSupportedError
        dbapi = MagicMock()

        class Error(Exception):
            pass

        class InterfaceError(Error):
            pass

        class DatabaseError(Error):
            pass

        class NotSupportedError(Error):
            pass

        dbapi.Error = Error
        dbapi.InterfaceError = InterfaceError
        dbapi.DatabaseError = DatabaseError
        dbapi.NotSupportedError = NotSupportedError

        dialect.dbapi = dbapi
        return dialect, dbapi

    @pytest.mark.parametrize(
        "message",
        [
            "connection is closed",
            "Closed connection detected",
            "Lost connection to server",
            "server has gone away",
            "Connection Reset by peer",
            "Broken Pipe in socket",
            "Cannot communicate with the broker",
            "Received invalid packet from server",
            "Broker is not available right now",
            "Communication error during query",
            "Connection timed out after 30s",
            "Connection refused on port 33000",
            "connection was killed by admin",
            "Failed to connect to host",
        ],
    )
    def test_disconnect_message_patterns(self, dialect_with_dbapi, message):
        """is_disconnect() returns True for known disconnect messages."""
        dialect, dbapi = dialect_with_dbapi
        exc = dbapi.DatabaseError(message)
        assert dialect.is_disconnect(exc, None, None) is True

    @pytest.mark.parametrize(
        "message",
        [
            "syntax error in SQL",
            "unique constraint violation",
            "table not found",
            "permission denied",
            "division by zero",
        ],
    )
    def test_non_disconnect_messages(self, dialect_with_dbapi, message):
        """is_disconnect() returns False for non-disconnect errors."""
        dialect, dbapi = dialect_with_dbapi
        exc = dbapi.DatabaseError(message)
        assert dialect.is_disconnect(exc, None, None) is False

    @pytest.mark.parametrize(
        "error_code",
        [
            -21003,  # CAS_ER_COMMUNICATION
            -21005,  # CAS_ER_COMMUNICATION (alternate)
            -10005,  # ER_NET_CANT_CONNECT
            -10007,  # ER_NET_SERVER_COMM_ERROR
        ],
    )
    def test_disconnect_by_error_code(self, dialect_with_dbapi, error_code):
        """is_disconnect() returns True for known disconnect error codes."""
        dialect, dbapi = dialect_with_dbapi
        exc = dbapi.DatabaseError(error_code)
        assert dialect.is_disconnect(exc, None, None) is True

    def test_disconnect_with_interface_error(self, dialect_with_dbapi):
        """is_disconnect() works with InterfaceError subclass."""
        dialect, dbapi = dialect_with_dbapi
        exc = dbapi.InterfaceError("connection is closed")
        assert dialect.is_disconnect(exc, None, None) is True

    def test_non_dbapi_error_returns_false(self, dialect_with_dbapi):
        """is_disconnect() returns False for non-DBAPI exceptions."""
        dialect, _ = dialect_with_dbapi
        exc = RuntimeError("connection is closed")
        assert dialect.is_disconnect(exc, None, None) is False

    def test_disconnect_error_code_in_string_arg(self, dialect_with_dbapi):
        """is_disconnect() extracts numeric code from string like '-21003 msg'."""
        dialect, dbapi = dialect_with_dbapi
        exc = dbapi.DatabaseError("-21003 Cannot communicate with the broker")
        assert dialect.is_disconnect(exc, None, None) is True

    def test_disconnect_with_empty_args(self, dialect_with_dbapi):
        """is_disconnect() handles exception with no args gracefully."""
        dialect, dbapi = dialect_with_dbapi
        exc = dbapi.DatabaseError()
        assert dialect.is_disconnect(exc, None, None) is False


class TestExtractErrorCode:
    """Tests for CubridDialect._extract_error_code()."""

    def test_integer_arg(self):
        """Extracts integer error code from args[0]."""
        exc = Exception(-21003)
        assert CubridDialect._extract_error_code(exc) == -21003

    def test_string_with_embedded_code(self):
        """Extracts error code from string like '-21003 message'."""
        exc = Exception("-21003 Cannot communicate")
        assert CubridDialect._extract_error_code(exc) == -21003

    def test_string_without_code(self):
        """Returns None for string without leading number."""
        exc = Exception("some error message")
        assert CubridDialect._extract_error_code(exc) is None

    def test_empty_args(self):
        """Returns None for exception with no args."""
        exc = Exception()
        assert CubridDialect._extract_error_code(exc) is None

    def test_empty_string_arg(self):
        """Returns None for exception with empty string arg."""
        exc = Exception("")
        assert CubridDialect._extract_error_code(exc) is None

    def test_non_numeric_string_code(self):
        """Returns None when first token is not numeric."""
        exc = Exception("ERROR: connection lost")
        assert CubridDialect._extract_error_code(exc) is None

    def test_positive_integer(self):
        """Handles positive integer error codes."""
        exc = Exception(1234)
        assert CubridDialect._extract_error_code(exc) == 1234


class TestDoPing:
    """Tests for CubridDialect.do_ping()."""

    def test_ping_success(self):
        """do_ping() returns True when ping() succeeds."""
        dialect = CubridDialect()
        dbapi_conn = MagicMock()
        dbapi_conn.ping.return_value = None

        result = dialect.do_ping(dbapi_conn)

        assert result is True
        dbapi_conn.ping.assert_called_once()

    def test_ping_returns_false_on_exception(self):
        """do_ping() returns False on failure instead of propagating."""
        dialect = CubridDialect()
        dbapi_conn = MagicMock()
        dbapi_conn.ping.side_effect = RuntimeError("connection lost")

        result = dialect.do_ping(dbapi_conn)
        assert result is False


class TestPostfetchLastRowId:
    """Tests for postfetch_lastrowid flag and get_lastrowid behavior."""

    def test_postfetch_lastrowid_is_true(self):
        """CubridDialect sets postfetch_lastrowid = True."""
        dialect = CubridDialect()
        assert dialect.postfetch_lastrowid is True

    def test_get_lastrowid_via_driver_method(self):
        """get_lastrowid() uses raw connection's get_last_insert_id()."""
        from sqlalchemy_cubrid.base import CubridExecutionContext

        ctx = CubridExecutionContext.__new__(CubridExecutionContext)
        raw_conn = MagicMock()
        raw_conn.get_last_insert_id.return_value = 42

        connection = MagicMock()
        connection.connection.dbapi_connection = raw_conn
        ctx.root_connection = connection

        assert ctx.get_lastrowid() == 42
        raw_conn.get_last_insert_id.assert_called_once()

    def test_get_lastrowid_fallback_to_sql(self):
        """get_lastrowid() falls back to SELECT LAST_INSERT_ID()."""
        from sqlalchemy_cubrid.base import CubridExecutionContext

        ctx = CubridExecutionContext.__new__(CubridExecutionContext)

        # Make the driver method unavailable
        raw_conn = MagicMock(spec=[])
        connection = MagicMock()
        connection.connection.dbapi_connection = raw_conn
        ctx.root_connection = connection

        cursor = MagicMock()
        cursor.fetchone.return_value = (99,)
        ctx.create_server_side_cursor = MagicMock(return_value=cursor)

        assert ctx.get_lastrowid() == 99
        cursor.execute.assert_called_once_with("SELECT LAST_INSERT_ID()")
        cursor.close.assert_called_once()

    def test_get_lastrowid_returns_none_when_no_result(self):
        """get_lastrowid() returns None if SELECT LAST_INSERT_ID() returns nothing."""
        from sqlalchemy_cubrid.base import CubridExecutionContext

        ctx = CubridExecutionContext.__new__(CubridExecutionContext)

        raw_conn = MagicMock(spec=[])
        connection = MagicMock()
        connection.connection.dbapi_connection = raw_conn
        ctx.root_connection = connection

        cursor = MagicMock()
        cursor.fetchone.return_value = None
        ctx.create_server_side_cursor = MagicMock(return_value=cursor)

        assert ctx.get_lastrowid() is None

    def test_get_lastrowid_exception_in_driver_method(self):
        """get_lastrowid() falls back if get_last_insert_id() raises."""
        from sqlalchemy_cubrid.base import CubridExecutionContext

        ctx = CubridExecutionContext.__new__(CubridExecutionContext)

        raw_conn = MagicMock()
        raw_conn.get_last_insert_id.side_effect = RuntimeError("driver error")
        connection = MagicMock()
        connection.connection.dbapi_connection = raw_conn
        ctx.root_connection = connection

        cursor = MagicMock()
        cursor.fetchone.return_value = (77,)
        ctx.create_server_side_cursor = MagicMock(return_value=cursor)

        assert ctx.get_lastrowid() == 77


class TestDisconnectMessages:
    """Ensure _disconnect_messages tuple is properly defined."""

    def test_disconnect_messages_is_tuple(self):
        assert isinstance(CubridDialect._disconnect_messages, tuple)

    def test_disconnect_messages_all_lowercase(self):
        """All patterns must be lowercase for case-insensitive matching."""
        for msg in CubridDialect._disconnect_messages:
            assert msg == msg.lower(), f"Pattern not lowercase: {msg!r}"

    def test_disconnect_messages_not_empty(self):
        assert len(CubridDialect._disconnect_messages) > 0


class TestSchemaGuard:
    """Schema-argument handling is consistent across reflection methods.

    CUBRID exposes a single effective schema per connection.  Object-detail
    methods must raise :class:`NoSuchTableError` for a non-default schema;
    list/existence methods must return empty/false; ``schema=None`` and the
    default schema are always accepted.
    """

    DETAIL_METHODS = [
        "get_columns",
        "get_pk_constraint",
        "get_foreign_keys",
        "get_indexes",
        "get_unique_constraints",
        "get_table_comment",
    ]

    def _dialect(self) -> CubridDialect:
        dialect = CubridDialect()
        dialect.default_schema_name = "dba"
        return dialect

    @pytest.mark.parametrize("method_name", DETAIL_METHODS)
    def test_detail_methods_raise_for_non_default_schema(self, method_name: str) -> None:
        dialect = self._dialect()
        connection = MagicMock()
        method = getattr(dialect, method_name)
        with pytest.raises(NoSuchTableError):
            method(connection, "t", schema="other")
        connection.execute.assert_not_called()

    def test_get_view_definition_raises_for_non_default_schema(self) -> None:
        dialect = self._dialect()
        connection = MagicMock()
        with pytest.raises(NoSuchTableError):
            dialect.get_view_definition(connection, "v", schema="other")
        connection.execute.assert_not_called()

    def test_list_methods_return_empty_for_non_default_schema(self) -> None:
        dialect = self._dialect()
        connection = MagicMock()
        assert dialect.get_table_names(connection, schema="other") == []
        assert dialect.get_view_names(connection, schema="other") == []
        connection.execute.assert_not_called()

    def test_existence_methods_return_false_for_non_default_schema(self) -> None:
        dialect = self._dialect()
        connection = MagicMock()
        assert dialect.has_table(connection, "t", schema="other") is False
        assert dialect.has_index(connection, "t", "ix", schema="other") is False
        connection.execute.assert_not_called()

    def test_schema_is_default(self) -> None:
        dialect = self._dialect()
        assert dialect._schema_is_default(None) is True
        assert dialect._schema_is_default("dba") is True
        assert dialect._schema_is_default("other") is False

    def test_raise_if_non_default_schema_allows_default(self) -> None:
        dialect = self._dialect()
        dialect._raise_if_non_default_schema(None, "t")
        dialect._raise_if_non_default_schema("dba", "t")

    def test_raise_if_non_default_schema_raises_qualified(self) -> None:
        dialect = self._dialect()
        with pytest.raises(NoSuchTableError):
            dialect._raise_if_non_default_schema("other", "t")


class TestSchemaNameNormalization:
    """``_schema_is_default`` compares schema names case-insensitively (#292).

    CUBRID reports catalog names uppercased while SQLAlchemy works in lower
    case, so the guard must normalize both sides.  Explicitly-quoted names
    (``quoted_name`` with ``quote=True``) remain case-sensitive.
    """

    def _dialect(self, default_schema: str | quoted_name | None) -> CubridDialect:
        dialect = CubridDialect()
        dialect.default_schema_name = default_schema  # type: ignore[assignment]
        return dialect

    def test_lowercase_schema_matches_uppercase_default(self) -> None:
        dialect = self._dialect("DBA")
        assert dialect._schema_is_default("dba") is True

    def test_uppercase_schema_matches_lowercase_default(self) -> None:
        dialect = self._dialect("dba")
        assert dialect._schema_is_default("DBA") is True

    def test_exact_match_still_accepted(self) -> None:
        dialect = self._dialect("dba")
        assert dialect._schema_is_default("dba") is True

    def test_none_schema_always_accepted(self) -> None:
        dialect = self._dialect("dba")
        assert dialect._schema_is_default(None) is True

    def test_non_matching_schema_rejected(self) -> None:
        dialect = self._dialect("dba")
        assert dialect._schema_is_default("other") is False

    def test_none_default_rejects_non_none_schema(self) -> None:
        dialect = self._dialect(None)
        assert dialect._schema_is_default("dba") is False
        assert dialect._schema_is_default(None) is True

    def test_explicitly_quoted_schema_is_case_sensitive(self) -> None:
        dialect = self._dialect("dba")
        quoted = quoted_name("DBA", quote=True)
        assert dialect._schema_is_default(quoted) is False

    def test_explicitly_quoted_default_is_case_sensitive(self) -> None:
        dialect = self._dialect(quoted_name("dba", quote=True))
        assert dialect._schema_is_default("DBA") is False

    def test_explicitly_quoted_exact_match_accepted(self) -> None:
        dialect = self._dialect("dba")
        quoted = quoted_name("dba", quote=True)
        assert dialect._schema_is_default(quoted) is True
