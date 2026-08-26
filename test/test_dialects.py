# test/test_dialects.py
"""Offline dialect tests — no live CUBRID required."""

from __future__ import annotations

from sqlalchemy import Column, Integer, MetaData, String, Table, insert
from sqlalchemy.engine import url

from sqlalchemy_cubrid.dialect import CubridDialect


class TestConnectionString:
    """Verify create_connect_args produces valid CUBRID connection strings."""

    def test_basic_url(self):
        dialect = CubridDialect()
        u = url.make_url("cubrid://dba:1234@127.0.0.1:33000/demodb")
        args, kwargs = dialect.create_connect_args(u)

        assert args[0] == "CUBRID:127.0.0.1:33000:demodb:::"
        assert args[1] == "dba"
        assert args[2] == "1234"
        assert kwargs == {}

    def test_url_default_port(self):
        dialect = CubridDialect()
        u = url.make_url("cubrid://dba:secret@myhost/testdb")
        args, _ = dialect.create_connect_args(u)

        assert "myhost" in args[0]
        assert "testdb" in args[0]
        assert args[1] == "dba"
        assert args[2] == "secret"

    def test_url_no_password(self):
        dialect = CubridDialect()
        u = url.make_url("cubrid://dba@localhost:33000/demodb")
        args, _ = dialect.create_connect_args(u)

        assert args[0] == "CUBRID:localhost:33000:demodb:::"
        assert args[1] == "dba"


class TestDialectProperties:
    """Verify dialect flags are set correctly."""

    def test_name(self):
        assert CubridDialect.name == "cubrid"

    def test_paramstyle(self):
        assert CubridDialect.default_paramstyle == "qmark"

    def test_no_returning(self):
        assert CubridDialect.insert_returning is False
        assert CubridDialect.update_returning is False
        assert CubridDialect.delete_returning is False

    def test_no_native_boolean(self):
        assert CubridDialect.supports_native_boolean is False

    def test_supports_statement_cache(self):
        assert CubridDialect.supports_statement_cache is True

    def test_no_sequences(self):
        assert CubridDialect.supports_sequences is False

    def test_identifier_length(self):
        assert CubridDialect.max_identifier_length == 254

    def test_supports_default_values(self):
        assert CubridDialect.supports_default_values is True

    def test_multivalues_insert(self):
        assert CubridDialect.supports_multivalues_insert is True

    def test_insertmanyvalues_enabled(self):
        assert CubridDialect.use_insertmanyvalues is True
        assert CubridDialect.use_insertmanyvalues_wo_returning is True

    def test_insertmanyvalues_generates_batched_insert(self):
        table = Table(
            "imv_test",
            MetaData(),
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("name", String(50), nullable=False),
        )

        stmt = insert(table).values(
            [
                {"name": "alpha"},
                {"name": "beta"},
                {"name": "gamma"},
                {"name": "delta"},
                {"name": "epsilon"},
            ]
        )

        compiled = stmt.compile(dialect=CubridDialect())
        sql_text = str(compiled)

        assert sql_text.startswith("INSERT INTO imv_test")
        assert sql_text.count("(?)") == 5
        assert "), (" in sql_text

    def test_isolation_level_values(self):
        dialect = CubridDialect()
        levels = dialect.get_isolation_level_values()
        assert "SERIALIZABLE" in levels
        assert len(levels) == 6
