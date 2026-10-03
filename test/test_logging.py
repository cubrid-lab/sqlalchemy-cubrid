"""Tests for logging output in sqlalchemy-cubrid dialect modules."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from sqlalchemy_cubrid.pycubrid_dialect import PyCubridDialect


class TestPyCubridDialectLogging:
    """Verify PyCubridDialect emits expected log messages."""

    def test_import_dbapi_logs_version(self, caplog: pytest.LogCaptureFixture) -> None:
        """import_dbapi() should log the loaded pycubrid version."""
        fake_module = MagicMock()
        fake_module.__version__ = "1.2.0"

        with patch.dict("sys.modules", {"pycubrid": fake_module}):
            with caplog.at_level(logging.DEBUG, logger="sqlalchemy_cubrid.pycubrid_dialect"):
                result = PyCubridDialect.import_dbapi()

        assert any("pycubrid" in m and "1.2.0" in m for m in caplog.messages)
        assert result is fake_module

    def test_create_connect_args_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        """create_connect_args() should log connection target."""
        dialect = PyCubridDialect()
        url = MagicMock()
        url.translate_connect_args.return_value = {
            "host": "myhost",
            "port": 33000,
            "database": "mydb",
            "user": "dba",
            "password": "secret",
        }

        with caplog.at_level(logging.DEBUG, logger="sqlalchemy_cubrid.pycubrid_dialect"):
            dialect.create_connect_args(url)

        log_text = "\n".join(caplog.messages)
        assert "myhost" in log_text
        assert "33000" in log_text or "mydb" in log_text
        assert "secret" not in log_text

    def test_on_connect_logs_autocommit(self, caplog: pytest.LogCaptureFixture) -> None:
        """on_connect() should log the autocommit setting (SQLAlchemy applies isolation_level)."""
        dialect = PyCubridDialect()

        fn = dialect.on_connect()
        assert fn is not None

        mock_conn = MagicMock()
        with caplog.at_level(logging.DEBUG, logger="sqlalchemy_cubrid.pycubrid_dialect"):
            fn(mock_conn)

        assert any("autocommit=False" in m for m in caplog.messages)


class TestCubridDialectLogging:
    """Verify CubridDialect emits expected log messages."""

    def test_dialect_has_module_logger(self) -> None:
        """CubridDialect module should have a logger configured."""
        import sqlalchemy_cubrid.dialect as dialect_mod

        assert hasattr(dialect_mod, "log")
        assert dialect_mod.log.name == "sqlalchemy_cubrid.dialect"


class TestLoggingDoesNotLeakCredentials:
    """Ensure credentials never appear in dialect log output."""

    def test_create_connect_args_no_password_in_logs(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Password must never appear in log messages."""
        dialect = PyCubridDialect()
        url = MagicMock()
        url.translate_connect_args.return_value = {
            "host": "localhost",
            "port": 33000,
            "database": "testdb",
            "user": "admin",
            "password": "my_secret_pass_xyz",
        }

        with caplog.at_level(logging.DEBUG, logger="sqlalchemy_cubrid.pycubrid_dialect"):
            dialect.create_connect_args(url)

        full_log = "\n".join(caplog.messages)
        assert "my_secret_pass_xyz" not in full_log
