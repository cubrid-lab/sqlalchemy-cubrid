from __future__ import annotations

import sys
import types
import warnings
from decimal import Decimal
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import types as sqltypes
from sqlalchemy.exc import (
    ArgumentError,
    NoSuchTableError,
    OperationalError,
    ProgrammingError,
    SAWarning,
)
from sqlalchemy.engine import url
from sqlalchemy.sql.elements import quoted_name

from sqlalchemy_cubrid.dialect import CubridDialect
from sqlalchemy_cubrid.dialect import _split_collection_members
from sqlalchemy_cubrid.types import TIMESTAMPTZ, TIMESTAMPLTZ, DATETIMETZ, DATETIMELTZ


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


def _class_type_result(class_type):
    """Result of the ``db_class`` class-type lookup (``None``: no such object)."""
    result = MagicMock()
    result.first.return_value = (class_type, "DBA") if class_type else None
    return result


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

    @pytest.mark.parametrize(
        ("given", "expected"),
        [
            ("SERIALIZABLE", "SERIALIZABLE"),
            ("serializable", "SERIALIZABLE"),
            ("repeatable_read", "REPEATABLE READ"),
            ("CURSOR STABILITY", "READ COMMITTED"),
            ("REPEATABLE READ SCHEMA, REPEATABLE READ INSTANCES", "REPEATABLE READ"),
            ("autocommit", "AUTOCOMMIT"),
            ("BOGUS", "BOGUS"),
        ],
    )
    def test_isolation_level_is_passed_to_default_dialect(self, given, expected):
        """SQLAlchemy owns the engine-level level; aliases become the canonical name (#501)."""
        dialect = CubridDialect(isolation_level=given)
        assert dialect._on_connect_isolation_level == expected
        assert dialect.isolation_level == expected
        assert dialect._builtin_onconnect() is not None

    def test_supports_twophase_commit_is_false(self):
        """CUBRID does not support two-phase commit."""
        dialect = CubridDialect()
        assert dialect.supports_twophase_commit is False

    def test_insert_returning_is_the_returning_switch(self):
        # Regression for #396: `insert_returning = False` is the SQLAlchemy 2.x
        # switch that disables implicit INSERT...RETURNING. The legacy 1.x
        # `implicit_returning` attribute is dead — 2.x's DefaultDialect does not
        # define it and the CRUD compiler no longer consults it.
        from sqlalchemy.engine.default import DefaultDialect

        assert CubridDialect.insert_returning is False
        assert CubridDialect.update_returning is False
        assert CubridDialect.delete_returning is False
        assert not hasattr(DefaultDialect, "implicit_returning")
        assert "implicit_returning" not in CubridDialect.__dict__

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

    @pytest.mark.parametrize("level", [6, b"SERIALIZABLE", 4.0])
    def test_non_string_isolation_level_raises_argument_error(self, level):
        with pytest.raises(ArgumentError, match="isolation_level must be a string"):
            CubridDialect(isolation_level=level)

    @pytest.mark.parametrize("level", ["AUTOCOMMIT", "SERIALIZABLE"])
    def test_connection_without_autocommit_property_fails_loudly(self, level):
        """A DBAPI connection lacking ``autocommit`` is a driver mismatch, not 'off'."""
        dialect = CubridDialect()
        dbapi_conn = MagicMock(spec=["cursor"])
        with pytest.raises(AttributeError, match="autocommit"):
            dialect.set_isolation_level(dbapi_conn, level)
        dbapi_conn.cursor.assert_not_called()

    def test_on_connect_leaves_isolation_level_to_sqlalchemy(self):
        """SQLAlchemy's built-in connect hook applies it, with ArgumentError validation (#501)."""
        dialect = CubridDialect(isolation_level="SERIALIZABLE")
        dialect.set_isolation_level = MagicMock()

        dbapi_conn = MagicMock()
        hook = dialect.on_connect()
        hook(dbapi_conn)

        dbapi_conn.set_autocommit.assert_called_once_with(False)
        dialect.set_isolation_level.assert_not_called()

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


def _fake_cubriddb(version: object) -> types.ModuleType:
    """A stand-in CUBRIDdb module whose ``_cubrid.__version__`` is *version*."""
    ext = types.ModuleType("_cubrid")
    if version is not None:
        ext.__version__ = version  # type: ignore[attr-defined]
    module = types.ModuleType("CUBRIDdb")
    module._cubrid = ext  # type: ignore[attr-defined]
    return module


class TestCubriddbVersionGuard:
    """Warn at first connect when CUBRIDdb is older than the tested 11.3 line (#585)."""

    @pytest.mark.parametrize(
        "version",
        [
            b"9.3.0.0001",  # PyPI CUBRID-Python 9.3.0.1
            b"9.3.0.0002",  # PyPI CUBRID-Python 9.3.0.2
            "8.4.3.0004",
            b"11.2.0.0100",
            "10.2.0.0001",
        ],
    )
    def test_older_driver_warns(self, version: object) -> None:
        dialect = CubridDialect()
        dialect.dbapi = _fake_cubriddb(version)
        raw = version.decode() if isinstance(version, bytes) else version

        with pytest.warns(SAWarning, match=r"CUBRIDdb .* is older than the CUBRIDdb 11\.3") as rec:
            dialect._warn_if_untested_cubriddb()

        message = str(rec[0].message)
        assert raw in message
        assert "cubrid+pycubrid://" in message
        assert "v11.3.0.51" in message

    @pytest.mark.parametrize(
        "version", [b"11.3.0.0001", "11.3.0.0051", b"11.4.0.0001", "12.0.0.0001"]
    )
    def test_tested_or_newer_driver_does_not_warn(self, version: object) -> None:
        dialect = CubridDialect()
        dialect.dbapi = _fake_cubriddb(version)

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            dialect._warn_if_untested_cubriddb()

    @pytest.mark.parametrize("version", [None, b"unknown", "", 11])
    def test_unknown_version_does_not_warn(self, version: object) -> None:
        dialect = CubridDialect()
        dialect.dbapi = _fake_cubriddb(version)

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            dialect._warn_if_untested_cubriddb()

    def test_module_without_extension_does_not_warn(self) -> None:
        dialect = CubridDialect()
        dialect.dbapi = types.ModuleType("CUBRIDdb")  # type: ignore[assignment]

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            dialect._warn_if_untested_cubriddb()

    def test_pycubrid_dialect_skips_check(self) -> None:
        from sqlalchemy_cubrid.pycubrid_dialect import PyCubridDialect

        dialect = PyCubridDialect()
        dialect.dbapi = _fake_cubriddb(b"9.3.0.0001")

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            dialect._warn_if_untested_cubriddb()

    def test_initialize_runs_the_check(self) -> None:
        dialect = CubridDialect()
        dialect.dbapi = _fake_cubriddb(b"9.3.0.0001")

        with patch("sqlalchemy.engine.default.DefaultDialect.initialize"):
            with pytest.warns(SAWarning, match="CUBRIDdb 9.3.0.0001 is older"):
                dialect.initialize(MagicMock())


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

        assert len(levels) == 7
        assert "AUTOCOMMIT" in levels
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
            dbapi_conn = MagicMock(spec=["cursor", "autocommit"])
            dbapi_conn.autocommit = False
            dbapi_conn.cursor = MagicMock(return_value=cursor)

            dialect.set_isolation_level(dbapi_conn, level_name)

            cursor.execute.assert_any_call(f"SET TRANSACTION ISOLATION LEVEL {expected_num}")
            cursor.execute.assert_any_call("COMMIT")
            cursor.close.assert_called_once_with()

    def test_set_isolation_level_with_plain_dbapi_class(self):
        dialect = CubridDialect()
        cursor = MagicMock()

        class PlainDBAPIConnection:
            autocommit = False

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

    def test_reset_isolation_level_is_sqlalchemys(self):
        """No override: checkin restores the engine level, not always READ COMMITTED (#501)."""
        assert "reset_isolation_level" not in vars(CubridDialect)
        dialect = CubridDialect(isolation_level="SERIALIZABLE")
        dialect.default_isolation_level = "SERIALIZABLE"
        cursor = MagicMock()
        dbapi_conn = MagicMock(spec=["cursor", "autocommit"])
        dbapi_conn.autocommit = False
        dbapi_conn.cursor.return_value = cursor

        dialect.reset_isolation_level(dbapi_conn)

        cursor.execute.assert_any_call("SET TRANSACTION ISOLATION LEVEL 6")

    def test_set_autocommit_enables_driver_autocommit_without_sql(self):
        dialect = CubridDialect()
        dbapi_conn = MagicMock(spec=["cursor", "autocommit"])
        dbapi_conn.autocommit = False

        dialect.set_isolation_level(dbapi_conn, "AUTOCOMMIT")

        assert dbapi_conn.autocommit is True
        dbapi_conn.cursor.assert_not_called()

    def test_other_level_turns_driver_autocommit_off_first(self):
        dialect = CubridDialect()
        events: list[str] = []

        class Conn:
            _autocommit = True

            @property
            def autocommit(self):
                return self._autocommit

            @autocommit.setter
            def autocommit(self, value):
                events.append(f"autocommit={value}")
                self._autocommit = value

            def cursor(self):
                cursor = MagicMock()
                cursor.execute.side_effect = events.append
                return cursor

        conn = Conn()
        dialect.set_isolation_level(conn, "SERIALIZABLE")

        assert events == ["autocommit=False", "SET TRANSACTION ISOLATION LEVEL 6", "COMMIT"]

    def test_driver_autocommit_is_not_toggled_when_already_set(self):
        """Toggling costs round trips (and a reconnect on pycubrid); skip no-ops."""
        dialect = CubridDialect()
        writes: list[bool] = []

        class Conn:
            autocommit = property(lambda self: self._value, lambda self, v: writes.append(v))

            def __init__(self, value):
                self._value = value

            def cursor(self):
                return MagicMock()

        dialect.set_isolation_level(Conn(False), "READ COMMITTED")
        dialect.set_isolation_level(Conn(True), "AUTOCOMMIT")

        assert writes == []

    @pytest.mark.parametrize("value", [True, False])
    def test_detect_autocommit_setting(self, value):
        dialect = CubridDialect()
        dbapi_conn = MagicMock(spec=["autocommit"])
        dbapi_conn.autocommit = value
        assert dialect.detect_autocommit_setting(dbapi_conn) is value

    @pytest.mark.parametrize("level", ["BOGUS", "READ UNCOMMITTED", ""])
    def test_invalid_level_raises_argument_error_through_sqlalchemy(self, level):
        """Engine-, connection- and execution-option levels are validated by SQLAlchemy (#501)."""
        dialect = CubridDialect()
        dbapi_conn = MagicMock()
        with pytest.raises(ArgumentError, match="Invalid value"):
            dialect._assert_and_set_isolation_level(dbapi_conn, level)
        dbapi_conn.cursor.assert_not_called()

    def test_isolation_level_set_get_roundtrip(self):
        """Every accepted input name round-trips to the same numeric code.

        Multiple aliases collapse onto one canonical name per code, so the
        invariant is semantic: MAP[name] == MAP[REVERSE[MAP[name]]].
        """
        dialect = CubridDialect()
        for name in dialect.get_isolation_level_values():
            if name == "AUTOCOMMIT":  # driver mode, not a server level
                continue
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

    @pytest.mark.parametrize(
        ("count", "expected"),
        [
            (0, False),
            (1, True),
            ("0", False),
            ("1", True),
            ("2", True),
            (Decimal("0"), False),
            (Decimal("1"), True),
            (None, False),
        ],
    )
    def test_has_table_and_has_index_coerce_count_type(self, count, expected):
        """PyPI CUBRID-Python 9.3 fetches the BIGINT COUNT(*) as str (#583)."""
        dialect = CubridDialect()
        connection = MagicMock()
        connection.execute.return_value.scalar.return_value = count

        assert dialect.has_table(connection, "users") is expected
        assert dialect.has_index(connection, "users", "ix_users_name") is expected

    def test_has_table_honors_inspector_info_cache(self):
        """Inspector.has_table() is cached until clear_cache() (SA HasTableTest)."""
        dialect = CubridDialect()
        connection = MagicMock()
        info_cache: dict = {}

        connection.execute.return_value.scalar.return_value = 0
        assert dialect.has_table(connection, "t", info_cache=info_cache) is False
        connection.execute.return_value.scalar.return_value = 1
        assert dialect.has_table(connection, "t", info_cache=info_cache) is False
        assert connection.execute.call_count == 1
        assert dialect.has_table(connection, "t", info_cache={}) is True

    def test_has_table_recognizes_views(self):
        dialect = CubridDialect()
        connection = MagicMock()

        connection.execute.return_value.scalar.return_value = 1
        assert dialect.has_table(connection, "active_users") is True

    def test_has_table_matches_lower_case_stored_name(self):
        """CUBRID stores quoted mixed-case names in lower case (#543)."""
        dialect = CubridDialect()
        connection = MagicMock()

        connection.execute.return_value.scalar.return_value = 1
        assert dialect.has_table(connection, "Users543") is True
        sql = str(connection.execute.call_args[0][0])
        assert "class_name IN (:name, LOWER(:name))" in sql
        assert connection.execute.call_args[0][1] == {"name": "Users543"}

    def test_has_index_true_false_and_error_propagates(self):
        dialect = CubridDialect()
        connection = MagicMock()

        connection.execute.return_value.scalar.return_value = 2
        assert dialect.has_index(connection, "users", "ix_users_name") is True
        call_args = connection.execute.call_args
        assert "FROM db_index" in str(call_args[0][0])
        bound_params = call_args[0][1]
        assert bound_params == {"table": "users", "name": "ix_users_name"}

        # No matching db_index row: a missing index or table.
        connection.execute.return_value.scalar.return_value = 0
        assert dialect.has_index(connection, "users", "ix_users_name") is False

        # A failing catalog query propagates instead of being cached as False (#444).
        connection.execute.side_effect = RuntimeError("metadata unavailable")
        with pytest.raises(RuntimeError, match="metadata unavailable"):
            dialect.has_index(connection, "users", "ix_users_name")

    def test_has_index_filters_by_table(self):
        dialect = CubridDialect()
        connection = MagicMock()

        connection.execute.return_value.scalar.return_value = 0
        assert dialect.has_index(connection, "orders", "ix_name") is False
        call_args = connection.execute.call_args
        bound_params = call_args[0][1]
        assert bound_params["table"] == "orders"

    def test_has_index_matches_lower_case_names_and_prefers_own_class(self):
        """Mixed-case names match their stored lower-case form (#543); since
        11.2 the index must belong to the owner the db_class lookup prefers."""
        dialect = CubridDialect()
        dialect.server_version_info = (11, 4, 6, 1963)
        connection = MagicMock()
        count = MagicMock()
        count.scalar.return_value = 1
        connection.execute.side_effect = [_class_type_result("CLASS"), count]

        assert dialect.has_index(connection, "Users543", "IX_Mixed543") is True
        lookup_sql = str(connection.execute.call_args_list[0][0][0])
        assert "owner_name = CURRENT_USER THEN 0" in lookup_sql
        sql, params = connection.execute.call_args_list[1][0]
        assert "class_name IN (:table, LOWER(:table))" in str(sql)
        assert "index_name IN (:name, LOWER(:name))" in str(sql)
        assert "owner_name = :owner" in str(sql)
        assert params == {"table": "Users543", "name": "IX_Mixed543", "owner": "DBA"}

    def test_has_index_is_cached_per_info_cache(self):
        """An Inspector answers has_index from its cache until clear_cache() (#533)."""
        dialect = CubridDialect()
        connection = MagicMock()
        info_cache: dict = {}

        connection.execute.return_value.scalar.return_value = 0
        assert dialect.has_index(connection, "t", "ix", info_cache=info_cache) is False
        connection.execute.return_value.scalar.return_value = 1
        assert dialect.has_index(connection, "t", "ix", info_cache=info_cache) is False
        assert connection.execute.call_count == 1
        info_cache.clear()
        assert dialect.has_index(connection, "t", "ix", info_cache=info_cache) is True
        # Without an info_cache (e.g. Index.drop(checkfirst=True)) nothing is cached.
        assert dialect.has_index(connection, "t", "ix") is True
        assert connection.execute.call_count == 3

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

    def test_get_columns_bit_keeps_length_and_varying(self):
        """#545: BIT(n) / BIT VARYING(n) reflect with their length, so they compile back unchanged."""
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        rows = [
            ("bit_col", "BIT(32)", "YES", "", None, ""),
            ("varbit_col", "BIT VARYING(128)", "YES", "", None, ""),
            ("varbit_max_col", "BIT VARYING(1073741823)", "YES", "", None, ""),
            ("bare_col", "BIT VARYING", "YES", "", None, ""),
        ]
        connection.execute.side_effect = [rows, []]

        columns = _invoke_reflection(dialect, "get_columns", connection, "bit_table")

        compiled = [dialect.type_compiler_instance.process(c["type"]) for c in columns]
        assert compiled == [
            "BIT(32)",
            "BIT VARYING(128)",
            "BIT VARYING(1073741823)",
            "BIT VARYING",
        ]

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

        # db_index_key catalog rows: (key_attr_name, index_name), ordered.
        catalog_rows = [("id", "pk_users")]
        connection.execute.side_effect = [catalog_rows]

        pk = _invoke_reflection(dialect, "get_pk_constraint", connection, "users")

        assert pk == {"name": "pk_users", "constrained_columns": ["id"]}

    def test_get_pk_constraint_composite_key_keeps_all_columns(self):
        """#426: a composite PK must reflect every column in key order."""
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        catalog_rows = [("a", "pk_t_a_b"), ("b", "pk_t_a_b")]
        connection.execute.side_effect = [catalog_rows]

        pk = _invoke_reflection(dialect, "get_pk_constraint", connection, "t")

        assert pk == {"name": "pk_t_a_b", "constrained_columns": ["a", "b"]}

    def test_get_pk_constraint_falls_back_to_show_columns(self):
        """If the catalog has no PK row, fall back to SHOW COLUMNS (single PK)."""
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        show_columns_rows = [
            ("id", "INTEGER", "NO", "PRI", None, "auto_increment"),
            ("name", "VARCHAR(50)", "YES", "", None, ""),
        ]
        connection.execute.side_effect = [[], show_columns_rows]

        pk = _invoke_reflection(dialect, "get_pk_constraint", connection, "users")

        assert pk == {"name": None, "constrained_columns": ["id"]}

    def test_unknown_class_error_detection(self):
        """#387, #454: only CUBRID's ``Unknown class`` message marks a missing table.

        pycubrid before 1.8.0 reports every native -493 (including plain syntax
        errors) with SQLSTATE 42S02 and a ``Table not found`` description, so neither the
        code, the SQLSTATE nor that description identifies a missing table.
        """
        from sqlalchemy import exc

        from sqlalchemy_cubrid.dialect import _is_unknown_class_error

        class _PycubridError(Exception):
            # Shape of pycubrid < 1.8.0's ProgrammingError for any native -493.
            errno = -493
            sqlstate = "42S02"

        syntax = _PycubridError(
            "Syntax: Syntax error: unexpected 'SELEC' (errno=-493, "
            "sqlstate='42S02', description='Table not found')"
        )
        missing = _PycubridError(
            'Syntax: Unknown class "dba.missing". show columns from [missing] '
            "(errno=-493, sqlstate='42S02', description='Table not found')"
        )

        # Native -493, SQLSTATE 42S02 or "Table not found" alone: not missing.
        assert _is_unknown_class_error(syntax) is False
        assert _is_unknown_class_error(exc.ProgrammingError("SELEC 1", {}, syntax)) is False
        assert _is_unknown_class_error(Exception(-493, "Syntax error: unexpected 'SELEC'")) is False
        assert _is_unknown_class_error(Exception("Table not found")) is False
        assert _is_unknown_class_error(Exception("some other error")) is False
        # The SQLAlchemy wrapper's text (the SQL statement) is not inspected.
        assert (
            _is_unknown_class_error(
                exc.ProgrammingError(
                    "SHOW COLUMNS IN [Unknown class]",
                    {},
                    Exception(-494, "Authorization failure"),
                )
            )
            is False
        )

        # The server's "Unknown class" message, in pycubrid and CUBRIDdb shapes.
        assert _is_unknown_class_error(missing) is True
        assert _is_unknown_class_error(exc.ProgrammingError("SHOW", {}, missing)) is True
        assert _is_unknown_class_error(Exception(-493, 'Unknown class "dba.x".')) is True
        assert _is_unknown_class_error(Exception('Unknown class "dba.x"')) is True

    @pytest.mark.parametrize("method", ["get_columns", "get_indexes"])
    def test_syntax_error_is_not_no_such_table(self, method):
        """#454: a pycubrid -493 / 42S02 syntax error from SHOW COLUMNS or SHOW
        INDEXES propagates unchanged instead of becoming NoSuchTableError."""
        from sqlalchemy import exc

        class _PycubridError(Exception):
            errno = -493
            sqlstate = "42S02"

        orig = _PycubridError(
            "Syntax: unterminated identifier (errno=-493, sqlstate='42S02', "
            "description='Table not found')"
        )
        failure = exc.ProgrammingError("SHOW ...", {}, orig)

        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        if method == "get_columns":
            connection.execute.side_effect = failure
        else:
            # db_class lookup, the index-flag catalog query, then SHOW INDEXES.
            connection.execute.side_effect = [_class_type_result("CLASS"), [], failure]

        with pytest.raises(exc.ProgrammingError) as exc_info:
            _invoke_reflection(dialect, method, connection, "t")
        assert exc_info.value is failure

    def test_get_columns_missing_table_raises_no_such_table(self):
        """#387: get_columns on a missing table raises NoSuchTableError."""
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        connection.execute.side_effect = Exception('Unknown class "dba.missing"')

        with pytest.raises(NoSuchTableError):
            _invoke_reflection(dialect, "get_columns", connection, "missing")

    def test_get_columns_other_error_propagates(self):
        """#387: a non-not-found error from SHOW COLUMNS is not swallowed."""
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        connection.execute.side_effect = RuntimeError("connection reset")

        with pytest.raises(RuntimeError):
            _invoke_reflection(dialect, "get_columns", connection, "t")

    def test_get_indexes_missing_table_raises_no_such_table(self):
        """#387: get_indexes on a missing table raises NoSuchTableError."""
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        # db_class lookup (no such object), the batch index-flag catalog
        # query, then SHOW INDEXES.
        connection.execute.side_effect = [
            _class_type_result(None),
            [],
            Exception('Syntax: Unknown class "dba.missing".'),
        ]

        with pytest.raises(NoSuchTableError):
            _invoke_reflection(dialect, "get_indexes", connection, "missing")

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
        success_result.first.return_value = ("orders", ddl)
        success_conn.execute.side_effect = [_class_type_result("CLASS"), success_result]

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

        # SHOW CREATE TABLE lists fk_order_user first; the result is sorted
        # by constraint name (#531).
        assert [fk["name"] for fk in fks] == ["fk_order_legacy", "fk_order_user"]

        failed_conn = MagicMock()
        failed_conn.info_cache = {}
        failed_conn.dialect_options = {}
        # Any SHOW CREATE TABLE failure other than a missing table propagates
        # instead of reporting "no foreign keys" (#589).
        failed_conn.execute.side_effect = [
            _class_type_result("CLASS"),
            RuntimeError("fk lookup failed"),
        ]

        with pytest.raises(RuntimeError, match="fk lookup failed"):
            _invoke_reflection(dialect, "get_foreign_keys", failed_conn, "orders")

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
        statement = connection.execute.call_args[0][0]
        assert "is_system_class = 'NO' ORDER BY class_name" in str(statement)

    def test_get_view_names(self):
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        connection.execute.return_value = [("active_users",), ("recent_orders",)]

        views = _invoke_reflection(dialect, "get_view_names", connection)
        assert views == ["active_users", "recent_orders"]
        statement = connection.execute.call_args[0][0]
        assert "is_system_class = 'NO' ORDER BY class_name" in str(statement)

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
        result.first.return_value = ("view_name", "SELECT * FROM users")
        connection.execute.return_value = result
        assert (
            _invoke_reflection(dialect, "get_view_definition", connection, "user_view")
            == "SELECT * FROM users"
        )

        # SHOW CREATE VIEW on a table returns no row: not a view (#530).
        empty_result = MagicMock()
        empty_result.first.return_value = None
        connection.execute.return_value = empty_result
        with pytest.raises(NoSuchTableError):
            _invoke_reflection(dialect, "get_view_definition", connection, "users")

    def test_get_indexes_with_primary_key_and_exception_paths(self):
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        # Single batch query returns (index_name, is_primary_key, is_foreign_key)
        # tuples for every index on the table.  PK and FK auto-indexes are
        # filtered from the SHOW INDEXES output.
        flag_rows = [
            ("uq_name", "NO", "NO"),
            ("pk_users", "YES", "NO"),
            ("idx_email", "NO", "NO"),
        ]

        show_indexes_rows = [
            (None, 0, "uq_name", None, "first_name"),
            (None, 0, "uq_name", None, "last_name"),
            (None, 0, "pk_users", None, "id"),
            (None, 1, "idx_email", None, "email"),
        ]

        connection.execute.side_effect = [
            _class_type_result("CLASS"),  # db_class lookup
            flag_rows,  # batch db_index query
            show_indexes_rows,  # SHOW INDEXES
        ]

        indexes = _invoke_reflection(dialect, "get_indexes", connection, "users")

        assert indexes == [
            {"name": "uq_name", "column_names": ["first_name", "last_name"], "unique": True},
            {"name": "idx_email", "column_names": ["email"], "unique": False},
        ]

    def test_get_indexes_batch_pk_query_failure(self):
        """#549: a failing batch catalog query raises instead of reporting the
        PK and FK auto-indexes as ordinary indexes."""
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        connection.execute.side_effect = [
            _class_type_result("CLASS"),  # db_class lookup
            RuntimeError("catalog unavailable"),  # batch flag query fails
        ]

        with pytest.raises(RuntimeError, match="catalog unavailable"):
            _invoke_reflection(dialect, "get_indexes", connection, "users")
        assert connection.execute.call_count == 2

    def test_get_indexes_excludes_fk_auto_indexes(self):
        """FK auto-indexes (``db_index.is_foreign_key = 'YES'``) are filtered.

        See cubrid-lab/sqlalchemy-cubrid#120 — otherwise Alembic
        autogenerate emits spurious drop_index/create_index diffs.
        """
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        flag_rows = [
            ("fk_orders_user", "NO", "YES"),
            ("fk_orders_product", "NO", "YES"),
            ("idx_orders_status", "NO", "NO"),
        ]

        connection.execute.side_effect = [
            _class_type_result("CLASS"),
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

    def test_get_indexes_on_view_returns_empty(self):
        """#529: a view has no indexes of its own; SHOW INDEXES IN <view>
        would list the base table's indexes, so it is not run."""
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        connection.execute.side_effect = [_class_type_result("VCLASS")]

        assert _invoke_reflection(dialect, "get_indexes", connection, "users_v") == []
        assert connection.execute.call_count == 1

    def test_class_type_lookup_closes_result_prefers_own_class_and_is_cached(self):
        """#529 review: the db_class lookup must close its result (an open one
        holds a server query entry until -830), prefer the current user's
        class over a same-named class of another owner, and run once per
        name per Inspector."""
        dialect = CubridDialect()
        connection = MagicMock()
        result = _class_type_result("CLASS")
        connection.execute.return_value = result
        info_cache: dict = {}

        assert dialect._get_class_type(connection, "Users", info_cache=info_cache) == "CLASS"
        assert dialect._get_class_type(connection, "Users", info_cache=info_cache) == "CLASS"

        assert connection.execute.call_count == 1
        result.first.assert_called_once_with()
        result.fetchone.assert_not_called()
        statement, params = connection.execute.call_args.args
        sql = str(statement)
        assert "class_name IN (:name, LOWER(:name))" in sql
        assert "ORDER BY CASE WHEN owner_name = CURRENT_USER THEN 0" in sql
        assert "WHEN is_system_class = 'YES' THEN 1 ELSE 2 END" in sql
        assert params == {"name": "Users"}

    @pytest.mark.parametrize(
        ("version", "owner_filtered"),
        [
            (None, False),
            ((10, 2, 18, 9024), False),
            ((11, 0, 16, 419), False),
            ((11, 2, 9, 866), True),
        ],
    )
    def test_catalog_views_filter_owner_since_11_2(self, version, owner_filtered):
        """#549: reflection reads the public catalog views (``_db_index`` and
        friends are DBA-only). Since 11.2 they list same-named classes of other
        owners, so the rows are limited to the owner ``_get_class_info``
        prefers; before 11.2 the views have no ``owner_name`` column."""
        dialect = CubridDialect()
        dialect.server_version_info = version
        connection = MagicMock()
        info_cache: dict = {}

        def execute(statement, params=None):
            sql = str(statement)
            if "FROM db_class" in sql:
                return _class_type_result("CLASS")
            result = MagicMock()
            result.__iter__.return_value = iter([])
            result.scalar.return_value = 1
            return result

        connection.execute.side_effect = execute
        dialect.get_pk_constraint(connection, "t", info_cache=info_cache)
        dialect.get_unique_constraints(connection, "t", info_cache=info_cache)
        dialect.has_index(connection, "t", "ix", info_cache=info_cache)
        dialect.get_columns(connection, "t", info_cache=info_cache)
        dialect.get_indexes(connection, "t", info_cache=info_cache)

        catalog_calls = [
            (str(call.args[0]), call.args[1])
            for call in connection.execute.call_args_list
            if " db_index" in str(call.args[0]) or "db_attribute" in str(call.args[0])
        ]
        assert len(catalog_calls) == 5
        for sql, params in catalog_calls:
            assert "_db_" not in sql
            # Matched as given or lower-cased, like the db_class lookup.
            assert "class_name IN (:table, LOWER(:table))" in sql
            assert params["table"] == "t"
            assert ("owner_name = :owner" in sql) is owner_filtered
            assert (params.get("owner") == "DBA") is owner_filtered
        pk_sql = catalog_calls[0][0]
        assert "FROM db_index i, db_index_key k" in pk_sql
        if owner_filtered:
            assert "AND i.owner_name = :owner AND k.owner_name = :owner" in pk_sql
        # The db_class lookup runs at most once per name per Inspector.
        class_lookups = [
            call for call in connection.execute.call_args_list if "db_class" in str(call.args[0])
        ]
        assert len(class_lookups) == 1

    def test_catalog_class_filter_missing_class_has_no_owner_filter(self):
        dialect = CubridDialect()
        dialect.server_version_info = (11, 4, 6, 1963)
        connection = MagicMock()
        connection.execute.return_value = _class_type_result(None)

        assert dialect._catalog_class_filter(connection, "Missing", info_cache={}) == (
            "class_name IN (:table, LOWER(:table))",
            {"table": "Missing"},
        )

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
        success_result.first.return_value = ("users", ddl)
        # class-type lookup, empty unique-index catalog, SHOW CREATE TABLE
        success_conn.execute.side_effect = [_class_type_result("CLASS"), [], success_result]

        unique_constraints = _invoke_reflection(
            dialect,
            "get_unique_constraints",
            success_conn,
            "users",
        )

        assert unique_constraints == [
            {
                "name": "uq_users_email",
                "column_names": ["email", "tenant_id"],
                "duplicates_index": "uq_users_email",
            },
            {
                "name": "uq_users_name",
                "column_names": ["name"],
                "duplicates_index": "uq_users_name",
            },
        ]

        failed_conn = MagicMock()
        failed_conn.info_cache = {}
        failed_conn.dialect_options = {}
        failed_conn.execute.side_effect = [
            _class_type_result("CLASS"),
            RuntimeError("catalog unavailable"),
        ]

        # A failing catalog query raises (#549).
        with pytest.raises(RuntimeError, match="catalog unavailable"):
            _invoke_reflection(dialect, "get_unique_constraints", failed_conn, "users")

    def test_get_unique_constraints_from_catalog_success(self):
        """Primary path: db_index catalog query returns unique index names,
        SHOW INDEXES resolves column names."""
        dialect = CubridDialect()

        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        # First execute: db_index returns unique index names (excluding PK/FK)
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
        connection.execute.side_effect = [
            _class_type_result("CLASS"),
            unique_name_rows,
            show_indexes_rows,
        ]

        uqs = _invoke_reflection(dialect, "get_unique_constraints", connection, "users")

        assert uqs == [
            {
                "name": "uq_users_email",
                "column_names": ["email", "tenant_id"],
                "duplicates_index": "uq_users_email",
            },
            {
                "name": "uq_users_name",
                "column_names": ["name"],
                "duplicates_index": "uq_users_name",
            },
        ]

    def test_get_unique_constraints_catalog_empty_falls_back_to_ddl(self):
        """When db_index returns no unique indexes, fall back to DDL regex."""
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

        # First execute: db_index returns empty list (no unique indexes found)
        # Second execute: SHOW CREATE TABLE for DDL fallback
        ddl_result = MagicMock()
        ddl_result.first.return_value = ("users", ddl)
        connection.execute.side_effect = [_class_type_result("CLASS"), [], ddl_result]

        uqs = _invoke_reflection(dialect, "get_unique_constraints", connection, "users")

        assert uqs == [
            {
                "name": "uq_users_email",
                "column_names": ["email"],
                "duplicates_index": "uq_users_email",
            }
        ]

    def test_get_unique_constraints_catalog_missing_table_raises(self):
        """SHOW INDEXES failing with ``Unknown class`` after the catalog found
        unique indexes (e.g. another owner's class) raises NoSuchTableError."""
        dialect = CubridDialect()

        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        connection.execute.side_effect = [
            _class_type_result("CLASS"),
            [("uq_users_email",)],
            Exception('Unknown class "dba.users"'),
        ]

        with pytest.raises(NoSuchTableError):
            _invoke_reflection(dialect, "get_unique_constraints", connection, "users")

        other_error = MagicMock()
        other_error.info_cache = {}
        other_error.dialect_options = {}
        other_error.execute.side_effect = [
            _class_type_result("CLASS"),
            [("uq_users_email",)],
            RuntimeError("connection reset"),
        ]
        with pytest.raises(RuntimeError, match="connection reset"):
            _invoke_reflection(dialect, "get_unique_constraints", other_error, "users")

    def test_get_pk_constraint_name_from_index(self):
        """PK columns and name come from the db_index_key catalog (#426)."""
        dialect = CubridDialect()

        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        catalog_rows = [("id", "pk_users")]
        connection.execute.side_effect = [catalog_rows]

        pk = _invoke_reflection(dialect, "get_pk_constraint", connection, "users")

        assert pk == {"name": "pk_users", "constrained_columns": ["id"]}

    def test_get_pk_constraint_catalog_failure_raises(self):
        """#549: a failing catalog query raises; falling back to SHOW COLUMNS
        would lose the PK name and every composite column after the first."""
        dialect = CubridDialect()

        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        connection.execute.side_effect = [RuntimeError("index query failed")]

        with pytest.raises(RuntimeError, match="index query failed"):
            _invoke_reflection(dialect, "get_pk_constraint", connection, "users")

    def test_get_check_constraints_get_table_comment_and_schema_names(self):
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        table_comment_result = MagicMock()
        table_comment_result.first.return_value = ("users table comment",)
        connection.execute.return_value = table_comment_result

        checks = _invoke_reflection(dialect, "get_check_constraints", connection, "users")
        comment = _invoke_reflection(dialect, "get_table_comment", connection, "users")

        assert checks == []
        assert comment == {"text": "users table comment"}
        assert dialect.get_schema_names(connection) == []


class TestMissingObjectReflection:
    """#530: reflecting a table or view that does not exist raises
    NoSuchTableError, and a view skips the table-only SHOW CREATE TABLE."""

    @staticmethod
    def _connection(*side_effect):
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        connection.execute.side_effect = list(side_effect)
        return connection

    @staticmethod
    def _unknown_class(name="missing"):
        return Exception(f'Syntax: Unknown class "dba.{name}".')

    @staticmethod
    def _syntax_error():
        """A generic -493 error that is not a missing object.

        pycubrid reports syntax errors with the same native code and SQLSTATE
        (42S02) as a missing class (#454), so only the message tells them
        apart.
        """
        from sqlalchemy import exc

        orig = Exception("Syntax: syntax error, unexpected 'SELEC'")
        orig.errno = -493  # type: ignore[attr-defined]
        orig.sqlstate = "42S02"  # type: ignore[attr-defined]
        return exc.ProgrammingError("SHOW ...", {}, orig)

    @pytest.mark.parametrize("method_name", ["get_foreign_keys", "get_unique_constraints"])
    def test_missing_table_raises_before_show_create_table(self, method_name):
        connection = self._connection(_class_type_result(None))
        with pytest.raises(NoSuchTableError):
            _invoke_reflection(CubridDialect(), method_name, connection, "missing")
        assert connection.execute.call_count == 1

    @pytest.mark.parametrize("method_name", ["get_foreign_keys", "get_unique_constraints"])
    def test_view_returns_empty_without_show_create_table(self, method_name, caplog):
        connection = self._connection(_class_type_result("VCLASS"))
        with caplog.at_level("WARNING", logger="sqlalchemy_cubrid.dialect"):
            assert _invoke_reflection(CubridDialect(), method_name, connection, "v") == []
        assert connection.execute.call_count == 1
        assert not caplog.records

    def test_foreign_keys_ddl_missing_table_raises(self):
        """A table dropped between the lookup and SHOW CREATE TABLE."""
        connection = self._connection(_class_type_result("CLASS"), self._unknown_class())
        with pytest.raises(NoSuchTableError):
            _invoke_reflection(CubridDialect(), "get_foreign_keys", connection, "missing")

    def test_unique_constraints_ddl_fallback_does_not_swallow_missing_table(self):
        connection = self._connection(_class_type_result("CLASS"), [], self._unknown_class())
        with pytest.raises(NoSuchTableError):
            _invoke_reflection(CubridDialect(), "get_unique_constraints", connection, "missing")

    @pytest.mark.parametrize("method_name", ["get_foreign_keys", "get_unique_constraints"])
    def test_ddl_fallback_syntax_error_is_not_a_missing_table(self, method_name):
        from sqlalchemy.exc import ProgrammingError

        side_effect = [_class_type_result("CLASS")]
        if method_name == "get_unique_constraints":
            side_effect.append([])  # empty unique-index catalog
        connection = self._connection(*side_effect, self._syntax_error())
        with pytest.raises(ProgrammingError) as excinfo:
            _invoke_reflection(CubridDialect(), method_name, connection, "t")
        assert not isinstance(excinfo.value, NoSuchTableError)

    def test_table_comment_missing_table_raises(self):
        result = MagicMock()
        result.first.return_value = None
        connection = self._connection(result)
        with pytest.raises(NoSuchTableError):
            _invoke_reflection(CubridDialect(), "get_table_comment", connection, "missing")

    def test_table_comment_prefers_own_class_and_closes_result(self):
        result = MagicMock()
        result.first.return_value = (None,)
        connection = self._connection(result)
        assert _invoke_reflection(CubridDialect(), "get_table_comment", connection, "T") == {
            "text": None
        }
        result.first.assert_called_once_with()
        sql = str(connection.execute.call_args.args[0])
        assert "class_name IN (:name, LOWER(:name))" in sql
        assert "ORDER BY CASE WHEN owner_name = CURRENT_USER THEN 0" in sql

    def test_pk_constraint_missing_table_raises(self):
        # Empty PK catalog, then SHOW COLUMNS fails with "Unknown class".
        connection = self._connection([], self._unknown_class())
        with pytest.raises(NoSuchTableError):
            _invoke_reflection(CubridDialect(), "get_pk_constraint", connection, "missing")

    def test_pk_constraint_syntax_error_propagates(self):
        from sqlalchemy.exc import ProgrammingError

        connection = self._connection([], self._syntax_error())
        with pytest.raises(ProgrammingError):
            _invoke_reflection(CubridDialect(), "get_pk_constraint", connection, "t")

    def test_view_definition_missing_view_raises(self):
        connection = self._connection(self._unknown_class("missing_v"))
        with pytest.raises(NoSuchTableError):
            _invoke_reflection(CubridDialect(), "get_view_definition", connection, "missing_v")

    def test_view_definition_syntax_error_propagates(self):
        from sqlalchemy.exc import ProgrammingError

        connection = self._connection(self._syntax_error())
        with pytest.raises(ProgrammingError):
            _invoke_reflection(CubridDialect(), "get_view_definition", connection, "v")


class _DriverError(Exception):
    pass


_SHOW_CREATE_TABLE_ERRORS = [
    OperationalError(
        "SHOW CREATE TABLE",
        {},
        _DriverError("Cannot communicate with the broker"),
        connection_invalidated=True,
    ),
    ProgrammingError(
        "SHOW CREATE TABLE", {}, _DriverError("Syntax: select is not authorized on t.")
    ),
    ProgrammingError(
        "SHOW CREATE TABLE", {}, _DriverError("Semantic: SELECT is not authorized on dba.t.")
    ),
    RuntimeError("boom"),
]
_SHOW_CREATE_TABLE_ERROR_IDS = ["disconnect", "not-authorized-493", "not-authorized-494", "runtime"]


class TestShowCreateTableErrorsPropagate:
    """#589: ``get_foreign_keys`` and ``get_unique_constraints`` read
    ``SHOW CREATE TABLE``. A failure there must not be reported as "no
    constraints", which Alembic autogenerate would turn into spurious
    ``add_fk`` / ``add_constraint`` operations."""

    METHODS = ["get_foreign_keys", "get_unique_constraints"]

    @staticmethod
    def _connection(method_name, show_create_table):
        side_effect = [_class_type_result("CLASS")]
        if method_name == "get_unique_constraints":
            side_effect.append([])  # empty unique-index catalog: DDL fallback
        side_effect.append(show_create_table)
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        connection.execute.side_effect = side_effect
        return connection

    @pytest.mark.parametrize("method_name", METHODS)
    @pytest.mark.parametrize("error", _SHOW_CREATE_TABLE_ERRORS, ids=_SHOW_CREATE_TABLE_ERROR_IDS)
    def test_show_create_table_failure_propagates(self, method_name, error, caplog):
        connection = self._connection(method_name, error)
        with caplog.at_level("WARNING", logger="sqlalchemy_cubrid.dialect"):
            with pytest.raises(type(error)) as excinfo:
                _invoke_reflection(CubridDialect(), method_name, connection, "t")
        assert excinfo.value is error
        assert not isinstance(excinfo.value, NoSuchTableError)
        assert not caplog.records

    def test_disconnect_keeps_connection_invalidated(self):
        error = _SHOW_CREATE_TABLE_ERRORS[0]
        connection = self._connection("get_foreign_keys", error)
        with pytest.raises(type(error)) as excinfo:
            _invoke_reflection(CubridDialect(), "get_foreign_keys", connection, "t")
        assert excinfo.value.connection_invalidated

    @pytest.mark.parametrize("method_name", METHODS)
    def test_no_show_create_table_row_raises_no_such_table(self, method_name):
        """The class lookup found the table but SHOW CREATE TABLE returned no
        row (e.g. it was dropped in between): the table is gone, not
        constraint-free."""
        result = MagicMock()
        result.first.return_value = None
        connection = self._connection(method_name, result)
        with pytest.raises(NoSuchTableError, match="t"):
            _invoke_reflection(CubridDialect(), method_name, connection, "t")

    @pytest.mark.parametrize("method_name", METHODS)
    def test_successful_query_without_constraints_returns_empty(self, method_name):
        result = MagicMock()
        result.first.return_value = (
            "t",
            "CREATE TABLE [t] ([id] INTEGER NOT NULL, CONSTRAINT [pk_t_id] PRIMARY KEY ([id]))",
        )
        connection = self._connection(method_name, result)
        assert _invoke_reflection(CubridDialect(), method_name, connection, "t") == []


class TestDoReleaseSavepoint:
    def test_do_release_savepoint_is_noop(self):
        """CUBRID does not support RELEASE SAVEPOINT; method should be a no-op."""
        dialect = CubridDialect()
        connection = MagicMock()
        # Should not raise, should not call anything on connection
        result = dialect.do_release_savepoint(connection, "sp_test")
        assert result is None
        connection.execute.assert_not_called()


class _RowcountCursor:
    """Fake DB-API cursor whose ``execute`` reports a scripted rowcount."""

    def __init__(self, rowcounts: list[int]) -> None:
        self._rowcounts = iter(rowcounts)
        self.executed: list[tuple[str, Any]] = []
        self.executemany_calls: list[tuple[str, Any]] = []
        self.rowcount = -1

    def execute(self, statement: str, params: Any) -> None:
        self.executed.append((statement, params))
        self.rowcount = next(self._rowcounts)

    def executemany(self, statement: str, params: Any) -> None:
        self.executemany_calls.append((statement, params))


class TestDoExecutemany:
    """CUBRIDdb executemany guard (#502) and its pycubrid opt-out."""

    _ROWS = [(1, "a"), (2, None), (3, "c")]

    def test_cubriddb_executes_each_row_and_sums_rowcount(self) -> None:
        cursor = _RowcountCursor([1, 0, 2])
        CubridDialect().do_executemany(cursor, "UPDATE t SET v = ? WHERE id = ?", self._ROWS)
        assert cursor.executed == [("UPDATE t SET v = ? WHERE id = ?", row) for row in self._ROWS]
        assert cursor.executemany_calls == []
        assert cursor.rowcount == 3

    def test_cubriddb_unknown_row_rowcount_makes_total_unknown(self) -> None:
        cursor = _RowcountCursor([1, -1, 2])
        CubridDialect().do_executemany(cursor, "UPDATE t SET v = ?", self._ROWS)
        assert len(cursor.executed) == 3
        assert cursor.rowcount == -1

    @pytest.mark.parametrize(
        "dialect_path",
        [
            "sqlalchemy_cubrid.pycubrid_dialect:PyCubridDialect",
            "sqlalchemy_cubrid.aio_pycubrid_dialect:PyCubridAsyncDialect",
        ],
    )
    def test_pycubrid_dialects_keep_driver_executemany(self, dialect_path: str) -> None:
        import importlib

        module_name, class_name = dialect_path.split(":")
        dialect_cls = getattr(importlib.import_module(module_name), class_name)
        cursor = _RowcountCursor([])
        dialect_cls().do_executemany(cursor, "INSERT INTO t VALUES (?, ?)", self._ROWS)
        assert cursor.executemany_calls == [("INSERT INTO t VALUES (?, ?)", self._ROWS)]
        assert cursor.executed == []
        assert dialect_cls.supports_sane_multi_rowcount is True

    def test_cubriddb_supports_sane_multi_rowcount(self) -> None:
        assert CubridDialect.supports_sane_multi_rowcount is True


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
            "connection lost during receive",  # pycubrid sync clean-EOF (#322)
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

    # CUBRIDdb client-side codes for a dead or unusable connection (#572, #578).
    _CUBRIDDB_DISCONNECT = [
        (-10002, "ERROR: CAS, -10002, No more memory"),
        (-10003, "ERROR: CAS, -10003, Cannot receive data from client"),
        (-20002, "ERROR: CCI, -20002, Invalid connection handle"),
        (-20004, "ERROR: CCI, -20004, Cannot communicate with server"),
        (-20016, "ERROR: CCI, -20016, Cannot connect to CUBRID CAS"),
    ]

    # Codes the old table listed that are not disconnects (#572).
    _NOT_DISCONNECT = [
        -4,  # ER_INTERRUPTED: an interrupted query (e.g. KILL QUERY)
        -10005,  # CAS_ER_TRAN_TYPE
        -10007,  # CAS_ER_NUM_BIND
        -21003,  # CUBRID JDBC's ER_COMMUNICATION; no Python driver raises it
        -21005,  # CUBRID JDBC's ER_TYPE_CONVERSION
    ]

    @pytest.mark.parametrize(("error_code", "message"), _CUBRIDDB_DISCONNECT)
    def test_disconnect_by_error_code(self, dialect_with_dbapi, error_code, message):
        """CUBRIDdb ``(code, message)`` errors with a disconnect code disconnect."""
        dialect, dbapi = dialect_with_dbapi
        exc = dbapi.InterfaceError(error_code, message)
        assert dialect.is_disconnect(exc, None, None) is True
        # Wording-independent: the code alone decides.
        assert dialect.is_disconnect(dbapi.DatabaseError(error_code), None, None) is True

    @pytest.mark.parametrize("error_code", _NOT_DISCONNECT)
    def test_removed_codes_are_not_disconnect_cubriddb(self, dialect_with_dbapi, error_code):
        """CUBRIDdb errors carrying a code the old table wrongly listed do not disconnect."""
        dialect, dbapi = dialect_with_dbapi
        exc = dbapi.DatabaseError(error_code, f"ERROR: DBMS, {error_code}, opaque message")
        assert dialect.is_disconnect(exc, None, None) is False
        assert dialect.is_disconnect(dbapi.DatabaseError(error_code), None, None) is False

    def test_interrupted_query_is_not_disconnect_cubriddb(self, dialect_with_dbapi):
        """CUBRIDdb's error for a query interrupted by KILL QUERY keeps the connection."""
        dialect, dbapi = dialect_with_dbapi
        exc = dbapi.DatabaseError(
            -4, "ERROR: DBMS, -4, Has been interrupted.[CAS INFO-127.0.0.1:33000,1,44]."
        )
        assert dialect.is_disconnect(exc, None, None) is False

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
        """is_disconnect() extracts numeric code from string like '-20004 msg'."""
        dialect, dbapi = dialect_with_dbapi
        assert dialect.is_disconnect(dbapi.DatabaseError("-20004 opaque"), None, None) is True
        assert dialect.is_disconnect(dbapi.DatabaseError("-4 opaque"), None, None) is False

    def test_disconnect_with_empty_args(self, dialect_with_dbapi):
        """is_disconnect() handles exception with no args gracefully."""
        dialect, dbapi = dialect_with_dbapi
        exc = dbapi.DatabaseError()
        assert dialect.is_disconnect(exc, None, None) is False

    # ----- pycubrid full hierarchy (includes OperationalError) -----

    @pytest.fixture()
    def pycubrid_dialect(self):
        """Dialect with a pycubrid-style dbapi (full PEP 249 hierarchy)."""
        dialect = CubridDialect()
        dbapi = MagicMock()

        class Error(Exception):
            pass

        class InterfaceError(Error):
            pass

        class DatabaseError(Error):
            pass

        class OperationalError(DatabaseError):
            pass

        dbapi.Error = Error
        dbapi.InterfaceError = InterfaceError
        dbapi.DatabaseError = DatabaseError
        dbapi.OperationalError = OperationalError

        dialect.dbapi = dbapi
        return dialect, dbapi

    def test_interrupted_query_is_not_disconnect_pycubrid(self, pycubrid_dialect):
        """pycubrid's errno -4 is the server's ER_INTERRUPTED, not a lost connection (#572)."""
        dialect, dbapi = pycubrid_dialect
        exc = dbapi.OperationalError("Has been interrupted.")
        exc.code = exc.errno = -4
        assert dialect.is_disconnect(exc, None, None) is False

    def test_operational_error_without_code_or_cause_is_not_disconnect(self, pycubrid_dialect):
        """OperationalError with a non-disconnect message is not a disconnect."""
        dialect, dbapi = pycubrid_dialect
        exc = dbapi.OperationalError("invalid isolation level")
        assert dialect.is_disconnect(exc, None, None) is False

    def test_disconnect_via_oserror_cause(self, pycubrid_dialect):
        """is_disconnect() detects an OSError in the cause chain (wording-free)."""
        dialect, dbapi = pycubrid_dialect
        try:
            try:
                raise OSError("socket error 104")
            except OSError as os_exc:
                raise dbapi.OperationalError("transport failure xyz") from os_exc
        except dbapi.OperationalError as exc:
            assert dialect.is_disconnect(exc, None, None) is True

    def test_implicit_oserror_context_is_not_disconnect(self, pycubrid_dialect):
        """Implicit __context__ (unrelated in-flight OSError) must NOT disconnect.

        An OSError merely being handled when an unrelated DBAPI error is
        raised links via __context__, not __cause__. Treating that as a
        disconnect would falsely invalidate a live pooled connection, so
        only the explicit ``raise ... from`` cause chain is followed.
        """
        dialect, dbapi = pycubrid_dialect
        try:
            try:
                raise ConnectionResetError("reset")
            except ConnectionResetError:
                raise dbapi.OperationalError("opaque driver message")
        except dbapi.OperationalError as exc:
            assert dialect.is_disconnect(exc, None, None) is False

    def test_non_oserror_cause_falls_back_to_message(self, pycubrid_dialect):
        """A non-OSError cause does not trigger; message fallback still applies."""
        dialect, dbapi = pycubrid_dialect
        try:
            try:
                raise ValueError("parse error")
            except ValueError as val_exc:
                raise dbapi.OperationalError("lost connection") from val_exc
        except dbapi.OperationalError as exc:
            assert dialect.is_disconnect(exc, None, None) is True

    def test_interface_error_misuse_is_not_disconnect(self, pycubrid_dialect):
        """Non-fatal InterfaceError misuse must not invalidate the pool."""
        dialect, dbapi = pycubrid_dialect
        exc = dbapi.InterfaceError("Cursor is closed")
        assert dialect.is_disconnect(exc, None, None) is False

    # ----- cub_server crash / stop: broker CAS-reset codes (#565) -----

    _SERVER_SESSION_LOST = [
        -111,  # ER_TM_SERVER_DOWN_UNILATERALLY_ABORTED
        -199,  # ER_NET_SERVER_CRASHED
        -224,  # ER_OBJ_NO_CONNECT
        -677,  # ER_BO_CONNECT_FAILED
    ]

    @pytest.mark.parametrize("error_code", _SERVER_SESSION_LOST)
    def test_server_session_lost_code_cubriddb(self, dialect_with_dbapi, error_code):
        """CUBRIDdb ``(code, message)`` errors for a lost server session disconnect."""
        dialect, dbapi = dialect_with_dbapi
        # Wording-independent: the code alone decides.
        exc = dbapi.DatabaseError(error_code, "opaque server message")
        assert dialect.is_disconnect(exc, None, None) is True

    @staticmethod
    def _pycubrid_error(dbapi, message: str, errno: int | None):
        """Mimic pycubrid: ``args`` hold only the message, the code is in ``errno``."""
        exc = dbapi.DatabaseError(message)
        exc.errno = errno
        return exc

    @pytest.mark.parametrize("error_code", _SERVER_SESSION_LOST)
    def test_server_session_lost_code_pycubrid(self, pycubrid_dialect, error_code):
        """pycubrid errors carrying a lost-server-session ``errno`` disconnect."""
        dialect, dbapi = pycubrid_dialect
        exc = self._pycubrid_error(dbapi, "opaque server message", error_code)
        assert dialect.is_disconnect(exc, None, None) is True

    # CAS codes (cas_error.h) as pycubrid actually receives them: legacy-
    # renumbered by CAS_CONV_ERROR_TO_OLD (+9000), since pycubrid never
    # advertises understanding the renewed error-code protocol (#578).
    _PYCUBRID_LEGACY_CAS = [
        -1002,  # legacy CAS_ER_NO_MORE_MEMORY (-10002 + 9000)
    ]

    @pytest.mark.parametrize("error_code", _PYCUBRID_LEGACY_CAS)
    def test_pycubrid_legacy_cas_code_is_disconnect(self, pycubrid_dialect, error_code):
        """pycubrid errors carrying a legacy-renumbered CAS disconnect code disconnect (#578)."""
        dialect, dbapi = pycubrid_dialect
        exc = self._pycubrid_error(dbapi, "opaque server message", error_code)
        assert dialect.is_disconnect(exc, None, None) is True

    @pytest.mark.parametrize(
        "errno",
        [
            *_NOT_DISCONNECT,
            -493,  # ER_PT_SYNTAX
            -671,  # ER_CSS_RECV_OR_SEND: evaluated and not added (#564)
            None,
        ],
    )
    def test_other_pycubrid_errno_is_not_disconnect(self, pycubrid_dialect, errno):
        """Only the server-session codes are matched against pycubrid ``errno``."""
        dialect, dbapi = pycubrid_dialect
        exc = self._pycubrid_error(dbapi, "opaque server message", errno)
        assert dialect.is_disconnect(exc, None, None) is False

    def test_decorated_str_does_not_decide_message_match(self, pycubrid_dialect):
        """Only the driver's own message is matched, not a decorated ``str()``.

        pycubrid's ``str()`` appends a description looked up from ``errno``
        (``Communication error`` for -4 and -671).
        """
        dialect, dbapi = pycubrid_dialect

        class DecoratedError(dbapi.OperationalError):
            def __str__(self) -> str:
                return f"{self.args[0]} (errno=-4, description='Communication error')"

        assert dialect.is_disconnect(DecoratedError("opaque"), None, None) is False
        assert dialect.is_disconnect(DecoratedError("connection is closed"), None, None) is True

    @pytest.mark.parametrize(
        ("errno", "expected"),
        [
            *((code, False) for code in _NOT_DISCONNECT),
            (-671, False),
            (-493, False),
            *((code, True) for code in _SERVER_SESSION_LOST),
        ],
    )
    @pytest.mark.parametrize("variant", ["sync", "async"])
    def test_real_pycubrid_errors(self, variant, errno, expected):
        """Real pycubrid exceptions through both pycubrid dialects."""
        pycubrid = pytest.importorskip("pycubrid")
        if variant == "sync":
            from sqlalchemy_cubrid.pycubrid_dialect import PyCubridDialect as dialect_cls
        else:
            from sqlalchemy_cubrid.aio_pycubrid_dialect import (
                PyCubridAsyncDialect as dialect_cls,
            )
        dialect = dialect_cls()
        dialect.dbapi = dialect_cls.import_dbapi()
        exc = pycubrid.OperationalError("opaque server message", code=errno, errno=errno)
        assert dialect.is_disconnect(exc, None, None) is expected

    def test_pycubrid_failed_reconnect_is_disconnect(self, pycubrid_dialect):
        """pycubrid's failed CHECK_CAS reconnect leaves the connection closed."""
        dialect, dbapi = pycubrid_dialect
        exc = dbapi.OperationalError(
            "CAS did not answer CHECK_CAS out of transaction and reconnecting failed"
        )
        assert dialect.is_disconnect(exc, None, None) is True


class TestExtractErrorCode:
    """Tests for CubridDialect._extract_error_code()."""

    def test_integer_arg(self):
        """Extracts integer error code from args[0]."""
        exc = Exception(-20004)
        assert CubridDialect._extract_error_code(exc) == -20004

    def test_string_with_embedded_code(self):
        """Extracts error code from string like '-20004 message'."""
        exc = Exception("-20004 Cannot communicate")
        assert CubridDialect._extract_error_code(exc) == -20004

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
        ctx._dbapi_connection = MagicMock()
        ctx._dbapi_connection.cursor.return_value = cursor

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
        ctx._dbapi_connection = MagicMock()
        ctx._dbapi_connection.cursor.return_value = cursor

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
        ctx._dbapi_connection = MagicMock()
        ctx._dbapi_connection.cursor.return_value = cursor

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

    def test_timezone_aware_types_instance_attribute(self):
        assert TIMESTAMPTZ().timezone is True
        assert TIMESTAMPLTZ().timezone is True
        assert DATETIMETZ().timezone is True
        assert DATETIMELTZ().timezone is True
