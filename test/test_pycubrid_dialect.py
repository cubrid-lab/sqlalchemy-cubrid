from __future__ import annotations

import sys
import types
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.engine import url

from sqlalchemy_cubrid.pycubrid_dialect import PyCubridDialect, PyCubridExecutionContext


class TestPyCubridDialectBasics:
    def test_driver_name(self):
        dialect = PyCubridDialect()
        assert dialect.driver == "pycubrid"
        assert dialect.name == "cubrid"

    def test_supports_statement_cache(self):
        dialect = PyCubridDialect()
        assert dialect.supports_statement_cache is True

    def test_insertmanyvalues_flags(self):
        dialect = PyCubridDialect()
        assert dialect.use_insertmanyvalues is True
        assert dialect.use_insertmanyvalues_wo_returning is True

    def test_default_paramstyle(self):
        dialect = PyCubridDialect()
        assert dialect.default_paramstyle == "qmark"

    def test_execution_context_class(self):
        dialect = PyCubridDialect()
        assert dialect.execution_ctx_cls is PyCubridExecutionContext

    def test_inherits_cubrid_dialect_properties(self):
        dialect = PyCubridDialect()
        assert dialect.supports_native_boolean is False
        assert dialect.supports_sequences is False
        assert dialect.max_identifier_length == 254
        assert dialect.insert_returning is False
        assert dialect.postfetch_lastrowid is True

    def test_init_with_and_without_isolation_level(self):
        default_dialect = PyCubridDialect()
        assert default_dialect.isolation_level is None

        custom_dialect = PyCubridDialect(isolation_level="SERIALIZABLE")
        assert custom_dialect.isolation_level == "SERIALIZABLE"

    def test_import_dbapi_success(self):
        fake_module = types.ModuleType("pycubrid")
        with patch.dict(sys.modules, {"pycubrid": fake_module}):
            imported = PyCubridDialect.import_dbapi()
        assert imported is fake_module

    def test_import_dbapi_import_error(self):
        with patch(
            "sqlalchemy_cubrid.pycubrid_dialect.import_module",
            side_effect=ImportError("pycubrid not installed"),
        ):
            with pytest.raises(ImportError, match="pycubrid not installed"):
                PyCubridDialect.import_dbapi()


class TestPyCubridConnectArgs:
    def test_create_connect_args_full_url(self):
        dialect = PyCubridDialect()
        parsed = url.make_url("cubrid+pycubrid://dba:pw@dbhost:33001/demodb")

        args, kwargs = dialect.create_connect_args(parsed)

        assert args == ()
        assert kwargs == {
            "host": "dbhost",
            "port": 33001,
            "database": "demodb",
            "user": "dba",
            "password": "pw",
        }

    def test_create_connect_args_defaults(self):
        dialect = PyCubridDialect()
        parsed = url.make_url("cubrid+pycubrid://")

        args, kwargs = dialect.create_connect_args(parsed)

        assert args == ()
        assert kwargs == {
            "host": "localhost",
            "port": 33000,
            "database": "",
            "user": "dba",
            "password": "",
        }

    def test_create_connect_args_partial_url(self):
        dialect = PyCubridDialect()
        parsed = url.make_url("cubrid+pycubrid://myuser@myhost/mydb")

        args, kwargs = dialect.create_connect_args(parsed)

        assert kwargs["host"] == "myhost"
        assert kwargs["database"] == "mydb"
        assert kwargs["user"] == "myuser"
        assert kwargs["password"] == ""
        assert kwargs["port"] == 33000

    def test_create_connect_args_none_url_raises(self):
        dialect = PyCubridDialect()
        none_url = cast(Any, None)
        with pytest.raises(ValueError, match="Unexpected database URL format"):
            dialect.create_connect_args(none_url)


class TestPyCubridOnConnect:
    def test_on_connect_without_isolation_level(self):
        dialect = PyCubridDialect()
        dialect.set_isolation_level = MagicMock()

        dbapi_conn = MagicMock()
        hook = dialect.on_connect()
        assert hook is not None
        hook(dbapi_conn)

        # pycubrid uses property setter, not set_autocommit()
        assert dbapi_conn.autocommit is False
        dialect.set_isolation_level.assert_not_called()

    def test_on_connect_with_isolation_level(self):
        dialect = PyCubridDialect(isolation_level="SERIALIZABLE")
        dialect.set_isolation_level = MagicMock()

        dbapi_conn = MagicMock()
        hook = dialect.on_connect()
        assert hook is not None
        hook(dbapi_conn)

        assert dbapi_conn.autocommit is False
        dialect.set_isolation_level.assert_called_once_with(dbapi_conn, "SERIALIZABLE")


class TestPyCubridDoPing:
    def test_do_ping_propagates_true(self):
        dialect = PyCubridDialect()
        dbapi_conn = MagicMock()
        dbapi_conn.ping.return_value = True

        result = dialect.do_ping(dbapi_conn)

        assert result is True
        dbapi_conn.ping.assert_called_once_with(False)

    def test_do_ping_propagates_false(self):
        dialect = PyCubridDialect()
        dbapi_conn = MagicMock()
        dbapi_conn.ping.return_value = False

        result = dialect.do_ping(dbapi_conn)

        assert result is False
        dbapi_conn.ping.assert_called_once_with(False)


class TestPyCubridExecutionContext:
    def test_get_lastrowid_from_cursor(self):
        ctx = PyCubridExecutionContext.__new__(PyCubridExecutionContext)
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 42
        ctx.cursor = mock_cursor
        ctx._dbapi_connection = MagicMock()

        assert ctx.get_lastrowid() == 42
        ctx._dbapi_connection.cursor.assert_not_called()

    def test_get_lastrowid_none(self):
        ctx = PyCubridExecutionContext.__new__(PyCubridExecutionContext)
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = None
        ctx.cursor = mock_cursor
        ctx._dbapi_connection = MagicMock()

        assert ctx.get_lastrowid() is None
        ctx._dbapi_connection.cursor.assert_not_called()

    def test_get_lastrowid_fallback_on_attribute_error(self):
        ctx = PyCubridExecutionContext.__new__(PyCubridExecutionContext)
        # Cursor without lastrowid attribute
        ctx.cursor = cast(Any, object())

        mock_server_cursor = MagicMock()
        mock_server_cursor.fetchone.return_value = ("99",)
        ctx._dbapi_connection = MagicMock()
        ctx._dbapi_connection.cursor.return_value = mock_server_cursor

        result = ctx.get_lastrowid()

        assert result == 99
        mock_server_cursor.execute.assert_called_once_with("SELECT LAST_INSERT_ID()")
        mock_server_cursor.close.assert_called_once()

    def test_get_lastrowid_fallback_returns_none_when_no_rows(self):
        ctx = PyCubridExecutionContext.__new__(PyCubridExecutionContext)
        ctx.cursor = cast(Any, object())

        mock_server_cursor = MagicMock()
        mock_server_cursor.fetchone.return_value = None
        ctx._dbapi_connection = MagicMock()
        ctx._dbapi_connection.cursor.return_value = mock_server_cursor

        result = ctx.get_lastrowid()

        assert result is None
        mock_server_cursor.close.assert_called_once()


class TestPyCubridEntryPointRegistration:
    def test_dialect_module_attribute(self):
        from sqlalchemy_cubrid import pycubrid_dialect

        assert pycubrid_dialect.dialect is PyCubridDialect

    def test_create_engine_url_format(self):
        """Verify the dialect parses cubrid+pycubrid:// URLs correctly."""
        parsed = url.make_url("cubrid+pycubrid://dba:secret@myserver:33000/testdb")
        assert parsed.drivername == "cubrid+pycubrid"
        assert parsed.host == "myserver"
        assert parsed.port == 33000
        assert parsed.database == "testdb"
        assert parsed.username == "dba"
        assert parsed.password == "secret"


class TestPyCubridIsolationLevels:
    """Verify that PyCubridDialect inherits isolation level handling."""

    def test_isolation_level_values(self):
        dialect = PyCubridDialect()
        values = dialect.get_isolation_level_values()
        assert "SERIALIZABLE" in values
        assert "READ COMMITTED" in values

    def test_set_isolation_level(self):
        dialect = PyCubridDialect()
        dbapi_conn = MagicMock()
        cursor = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        dialect.set_isolation_level(dbapi_conn, "SERIALIZABLE")

        cursor.execute.assert_any_call("SET TRANSACTION ISOLATION LEVEL 6")
        cursor.execute.assert_any_call("COMMIT")
        cursor.close.assert_called_once()

    def test_set_isolation_level_invalid_raises(self):
        dialect = PyCubridDialect()
        dbapi_conn = MagicMock()

        with pytest.raises(ValueError, match="Invalid isolation level"):
            dialect.set_isolation_level(dbapi_conn, "INVALID_LEVEL")

    def test_get_isolation_level_numeric(self):
        dialect = PyCubridDialect()
        cursor = MagicMock()
        cursor.fetchone.return_value = (6,)
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        level = dialect.get_isolation_level(dbapi_conn)
        assert level == "SERIALIZABLE"

    def test_reset_isolation_level(self):
        dialect = PyCubridDialect()
        dbapi_conn = MagicMock()
        cursor = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        dialect.reset_isolation_level(dbapi_conn)

        cursor.execute.assert_any_call("SET TRANSACTION ISOLATION LEVEL 4")


class TestPyCubridIsolationLevelReapply:
    """pycubrid drops the isolation level at commit/rollback; the dialect re-applies it (#505)."""

    @staticmethod
    def _dbapi_conn() -> MagicMock:
        conn = MagicMock(spec=["cursor", "commit", "rollback"])
        conn.cursor.return_value = MagicMock()
        return conn

    @pytest.mark.parametrize("method", ["do_commit", "do_rollback"])
    def test_end_of_transaction_without_level_does_not_reapply(self, method):
        dialect = PyCubridDialect()
        dbapi_conn = self._dbapi_conn()

        getattr(dialect, method)(dbapi_conn)

        getattr(dbapi_conn, method.removeprefix("do_")).assert_called_once_with()
        dbapi_conn.cursor.assert_not_called()

    @pytest.mark.parametrize("method", ["do_commit", "do_rollback"])
    def test_end_of_transaction_reapplies_last_level(self, method):
        dialect = PyCubridDialect()
        dbapi_conn = self._dbapi_conn()
        dialect.set_isolation_level(dbapi_conn, "SERIALIZABLE")
        dialect.set_isolation_level(dbapi_conn, "REPEATABLE READ")
        cursor = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        # SQLAlchemy passes a pool proxy here, not the raw DBAPI connection.
        proxy = types.SimpleNamespace(
            dbapi_connection=dbapi_conn, commit=dbapi_conn.commit, rollback=dbapi_conn.rollback
        )
        getattr(dialect, method)(proxy)

        getattr(dbapi_conn, method.removeprefix("do_")).assert_called_once_with()
        assert [c.args for c in cursor.execute.call_args_list] == [
            ("SET TRANSACTION ISOLATION LEVEL 5",),
            ("COMMIT",),
        ]

    def test_reapply_runs_after_the_driver_call(self):
        dialect = PyCubridDialect()
        dbapi_conn = self._dbapi_conn()
        dialect.set_isolation_level(dbapi_conn, "SERIALIZABLE")
        calls: list[str] = []
        dbapi_conn.commit.side_effect = lambda: calls.append("commit")
        dbapi_conn.cursor.side_effect = lambda: calls.append("cursor") or MagicMock()

        dialect.do_commit(dbapi_conn)

        assert calls == ["commit", "cursor"]

    def test_levels_are_tracked_per_connection(self):
        dialect = PyCubridDialect()
        first, second = self._dbapi_conn(), self._dbapi_conn()
        dialect.set_isolation_level(first, "SERIALIZABLE")

        dialect.do_commit(second)

        second.cursor.assert_not_called()

    def test_invalid_level_is_not_tracked(self):
        dialect = PyCubridDialect()
        dbapi_conn = self._dbapi_conn()
        with pytest.raises(ValueError, match="Invalid isolation level"):
            dialect.set_isolation_level(dbapi_conn, "INVALID_LEVEL")

        dialect.do_rollback(dbapi_conn)

        dbapi_conn.cursor.assert_not_called()


class TestPyCubridDoReleaseAndMiscMethods:
    def test_do_release_savepoint_is_noop(self):
        dialect = PyCubridDialect()
        conn = MagicMock()
        # Should not raise
        dialect.do_release_savepoint(conn, "sp1")

    def test_has_sequence_always_false(self):
        dialect = PyCubridDialect()
        conn = MagicMock()
        assert dialect.has_sequence(conn, "myseq") is False
