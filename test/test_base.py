from __future__ import annotations

import types
from unittest.mock import MagicMock

import pytest

from sqlalchemy_cubrid.base import (
    AUTOCOMMIT_REGEXP,
    RESERVED_WORDS,
    CubridExecutionContext,
    CubridIdentifierPreparer,
)
from sqlalchemy_cubrid.dialect import CubridDialect


class TestAutocommitRegexp:
    @pytest.mark.parametrize(
        "statement",
        [
            "UPDATE users SET name='x'",
            "insert into users values (1)",
            "  CrEaTe TABLE t (id int)",
            "DELETE FROM users",
            "drop table users",
            "ALTER TABLE users ADD COLUMN email VARCHAR(100)",
            "MERGE INTO users u USING src s ON (u.id = s.id)",
            "TRUNCATE TABLE users",
        ],
    )
    def test_matches_writes(self, statement):
        assert AUTOCOMMIT_REGEXP.match(statement)

    @pytest.mark.parametrize(
        "statement",
        [
            "SELECT * FROM users",
            " show tables",
            "WITH cte AS (SELECT 1) SELECT * FROM cte",
        ],
    )
    def test_does_not_match_reads(self, statement):
        assert AUTOCOMMIT_REGEXP.match(statement) is None


class TestReservedWords:
    def test_reserved_words_type_and_contents(self):
        assert isinstance(RESERVED_WORDS, frozenset)
        assert "select" in RESERVED_WORDS
        assert "insert" in RESERVED_WORDS
        assert "table" in RESERVED_WORDS
        assert "merge" not in RESERVED_WORDS


class TestIdentifierPreparer:
    def test_constructor_defaults(self):
        preparer = CubridIdentifierPreparer(CubridDialect())

        assert preparer.initial_quote == '"'
        assert preparer.final_quote == '"'
        assert preparer.escape_quote == '"'
        assert preparer.omit_schema is False


class TestExecutionContext:
    def test_should_autocommit_text(self):
        context = object.__new__(CubridExecutionContext)

        assert context.should_autocommit_text("DELETE FROM users")
        assert context.should_autocommit_text("SELECT 1") is None

    def test_get_lastrowid_uses_raw_connection_method(self):
        context = object.__new__(CubridExecutionContext)

        raw_conn = types.SimpleNamespace(get_last_insert_id=lambda: 987)
        setattr(
            context,
            "root_connection",
            types.SimpleNamespace(connection=types.SimpleNamespace(dbapi_connection=raw_conn)),
        )

        context.create_server_side_cursor = MagicMock()

        assert context.get_lastrowid() == 987
        context.create_server_side_cursor.assert_not_called()

    def test_get_lastrowid_falls_back_when_method_missing(self):
        context = object.__new__(CubridExecutionContext)

        raw_conn = object()
        setattr(
            context,
            "root_connection",
            types.SimpleNamespace(connection=types.SimpleNamespace(dbapi_connection=raw_conn)),
        )

        cursor = MagicMock()
        cursor.fetchone.return_value = (42,)
        context.create_server_side_cursor = MagicMock(return_value=cursor)

        assert context.get_lastrowid() == 42
        cursor.execute.assert_called_once_with("SELECT LAST_INSERT_ID()")
        cursor.close.assert_called_once_with()

    def test_get_lastrowid_falls_back_when_raw_conn_access_raises(self):
        context = object.__new__(CubridExecutionContext)

        class BrokenRootConnection:
            @property
            def connection(self):
                raise RuntimeError("cannot reach raw connection")

        setattr(context, "root_connection", BrokenRootConnection())

        cursor = MagicMock()
        cursor.fetchone.return_value = (101,)
        context.create_server_side_cursor = MagicMock(return_value=cursor)

        assert context.get_lastrowid() == 101
        cursor.execute.assert_called_once_with("SELECT LAST_INSERT_ID()")
        cursor.close.assert_called_once_with()

    def test_get_lastrowid_returns_none_when_fallback_has_no_row(self):
        context = object.__new__(CubridExecutionContext)

        setattr(
            context,
            "root_connection",
            types.SimpleNamespace(connection=types.SimpleNamespace(dbapi_connection=object())),
        )

        cursor = MagicMock()
        cursor.fetchone.return_value = None
        context.create_server_side_cursor = MagicMock(return_value=cursor)

        assert context.get_lastrowid() is None
        cursor.execute.assert_called_once_with("SELECT LAST_INSERT_ID()")
        cursor.close.assert_called_once_with()
