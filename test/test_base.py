from __future__ import annotations

import asyncio
import types
import warnings
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa
from sqlalchemy.engine.default import DefaultExecutionContext
from sqlalchemy.ext.asyncio import create_async_engine

import sqlalchemy_cubrid.base as cubrid_base
from sqlalchemy_cubrid.aio_pycubrid_dialect import PyCubridAsyncDialect
from sqlalchemy_cubrid.base import (
    RESERVED_WORDS,
    CubridExecutionContext,
    CubridIdentifierPreparer,
)
from sqlalchemy_cubrid.dialect import CubridDialect
from sqlalchemy_cubrid.pycubrid_dialect import PyCubridDialect, PyCubridExecutionContext

_DIALECT_CLASSES = (CubridDialect, PyCubridDialect, PyCubridAsyncDialect)


def _fake_dbapi() -> types.SimpleNamespace:
    raw_conn = MagicMock(name="dbapi_connection")
    return types.SimpleNamespace(
        paramstyle="qmark",
        Error=type("Error", (Exception,), {}),
        connect=MagicMock(return_value=raw_conn),
    )


class TestLegacySA1HooksRemoved:
    # Regression for #462: SQLAlchemy 2.x never calls the 1.x-era
    # ``should_autocommit_text()`` execution-context hook (so the
    # ``AUTOCOMMIT_REGEXP`` it consulted was dead too), and
    # ``create_engine()`` resolves the DBAPI through ``import_dbapi()`` when a
    # dialect class defines it, so the legacy ``dbapi()`` classmethod was
    # unreachable. Transactions are driven by the SA 2.x Connection API.

    def test_autocommit_text_hook_and_regexp_are_gone(self):
        assert not hasattr(DefaultExecutionContext, "should_autocommit_text")
        assert not hasattr(CubridExecutionContext, "should_autocommit_text")
        assert not hasattr(PyCubridExecutionContext, "should_autocommit_text")
        assert not hasattr(cubrid_base, "AUTOCOMMIT_REGEXP")

    @pytest.mark.parametrize("dialect_cls", _DIALECT_CLASSES)
    def test_legacy_dbapi_classmethod_is_gone(self, dialect_cls):
        assert "import_dbapi" in dialect_cls.__dict__
        assert not any("dbapi" in klass.__dict__ for klass in dialect_cls.__mro__)

    @pytest.mark.parametrize(
        ("dialect_cls", "url"),
        [
            (CubridDialect, "cubrid://dba@localhost:33000/testdb"),
            (PyCubridDialect, "cubrid+pycubrid://dba@localhost:33000/testdb"),
        ],
    )
    def test_create_engine_uses_import_dbapi_without_deprecation(self, dialect_cls, url):
        fake = _fake_dbapi()
        with patch.object(dialect_cls, "import_dbapi", classmethod(lambda cls: fake)):
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                engine = sa.create_engine(url)
        assert engine.dialect.dbapi is fake

    def test_create_async_engine_uses_import_dbapi_without_deprecation(self):
        fake = _fake_dbapi()
        with patch.object(PyCubridAsyncDialect, "import_dbapi", classmethod(lambda cls: fake)):
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                engine = create_async_engine("cubrid+aiopycubrid://dba@localhost:33000/testdb")
        assert engine.sync_engine.dialect.dbapi is fake
        asyncio.run(engine.dispose())

    def _engine(self):
        fake = _fake_dbapi()
        engine = sa.create_engine(
            "cubrid+pycubrid://dba@localhost:33000/testdb", module=fake, poolclass=sa.pool.NullPool
        )
        engine.dialect.initialize = lambda connection: None  # type: ignore[method-assign]
        return engine, fake.connect.return_value

    @pytest.mark.parametrize(
        "statement",
        ["DELETE FROM t", "REPLACE INTO t VALUES (1)", "CREATE TABLE t (id INT)"],
    )
    def test_dml_ddl_text_is_not_autocommitted(self, statement):
        engine, raw_conn = self._engine()
        with engine.connect() as conn:
            conn.execute(sa.text(statement))
        raw_conn.commit.assert_not_called()
        raw_conn.rollback.assert_called()

    def test_explicit_commit_and_begin_commit(self):
        engine, raw_conn = self._engine()
        with engine.connect() as conn:
            conn.execute(sa.text("REPLACE INTO t VALUES (1)"))
            conn.commit()
        assert raw_conn.commit.call_count == 1

        with engine.begin() as conn:
            conn.execute(sa.text("DELETE FROM t"))
        assert raw_conn.commit.call_count == 2


class TestReservedWords:
    def test_reserved_words_type_and_contents(self):
        assert isinstance(RESERVED_WORDS, frozenset)
        assert "select" in RESERVED_WORDS
        assert "insert" in RESERVED_WORDS
        assert "table" in RESERVED_WORDS
        assert "merge" not in RESERVED_WORDS

    @pytest.mark.parametrize("word", ["key", "value"])
    def test_key_value_are_reserved(self, word):
        assert word in RESERVED_WORDS

    @pytest.mark.parametrize("word", ["key", "value"])
    def test_reserved_column_is_quoted_in_select(self, word):
        import sqlalchemy as sa

        metadata = sa.MetaData()
        table = sa.Table(
            "weather_model_parameter",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(word, sa.String(50)),
        )
        compiled = str(sa.select(table.c[word]).compile(dialect=CubridDialect()))
        assert f'"{word}"' in compiled


class TestIdentifierPreparer:
    def test_constructor_defaults(self):
        preparer = CubridIdentifierPreparer(CubridDialect())

        assert preparer.initial_quote == '"'
        assert preparer.final_quote == '"'
        assert preparer.escape_quote == '"'
        assert preparer.omit_schema is False


class TestExecutionContext:
    def test_get_lastrowid_uses_raw_connection_method(self):
        context = object.__new__(CubridExecutionContext)

        raw_conn = types.SimpleNamespace(get_last_insert_id=lambda: 987)
        setattr(
            context,
            "root_connection",
            types.SimpleNamespace(connection=types.SimpleNamespace(dbapi_connection=raw_conn)),
        )

        context._dbapi_connection = MagicMock()

        assert context.get_lastrowid() == 987
        context._dbapi_connection.cursor.assert_not_called()

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
        context._dbapi_connection = types.SimpleNamespace(cursor=lambda: cursor)

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
        context._dbapi_connection = types.SimpleNamespace(cursor=lambda: cursor)

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
        context._dbapi_connection = types.SimpleNamespace(cursor=lambda: cursor)

        assert context.get_lastrowid() is None
        cursor.execute.assert_called_once_with("SELECT LAST_INSERT_ID()")
        cursor.close.assert_called_once_with()

    @pytest.mark.parametrize("context_cls", [CubridExecutionContext, PyCubridExecutionContext])
    @pytest.mark.parametrize("failure", ["execute", "fetchone", "conversion"])
    def test_get_lastrowid_fallback_closes_cursor_on_error(self, context_cls, failure):
        context = context_cls()
        context.root_connection = types.SimpleNamespace(
            connection=types.SimpleNamespace(dbapi_connection=object())
        )
        context.cursor = object()
        cursor = MagicMock()
        context._dbapi_connection = types.SimpleNamespace(cursor=lambda: cursor)
        if failure == "conversion":
            cursor.fetchone.return_value = ("invalid-id",)
            error = ValueError
        else:
            getattr(cursor, failure).side_effect = RuntimeError("fallback failed")
            error = RuntimeError

        with pytest.raises(
            error, match="invalid-id" if failure == "conversion" else "fallback failed"
        ):
            context.get_lastrowid()

        cursor.execute.assert_called_once_with("SELECT LAST_INSERT_ID()")
        cursor.close.assert_called_once_with()

    @pytest.mark.parametrize("value", [None, "987"])
    def test_get_lastrowid_preserves_native_result(self, value):
        context = CubridExecutionContext()
        context.root_connection = types.SimpleNamespace(
            connection=types.SimpleNamespace(
                dbapi_connection=types.SimpleNamespace(get_last_insert_id=lambda: value)
            )
        )
        context._dbapi_connection = MagicMock()

        assert context.get_lastrowid() == (None if value is None else 987)
        context._dbapi_connection.cursor.assert_not_called()

    def test_get_lastrowid_falls_back_when_driver_method_raises(self):
        context = CubridExecutionContext()
        raw_conn = MagicMock()
        raw_conn.get_last_insert_id.side_effect = RuntimeError("driver failed")
        context.root_connection = types.SimpleNamespace(
            connection=types.SimpleNamespace(dbapi_connection=raw_conn)
        )
        cursor = MagicMock()
        cursor.fetchone.return_value = ("42",)
        context._dbapi_connection = types.SimpleNamespace(cursor=lambda: cursor)

        assert context.get_lastrowid() == 42
        cursor.execute.assert_called_once_with("SELECT LAST_INSERT_ID()")
        cursor.close.assert_called_once_with()
