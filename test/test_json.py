# test/test_json.py
from __future__ import annotations


import pytest
import sqlalchemy as sa
from sqlalchemy import Column, Integer, MetaData, String, Table, func, select

from sqlalchemy_cubrid.dialect import CubridDialect
from sqlalchemy_cubrid.types import JSON, JSONIndexType, JSONPathType


def _compile(stmt, dialect=None):
    if dialect is None:
        dialect = CubridDialect()
    return stmt.compile(dialect=dialect, compile_kwargs={"literal_binds": True}).string


metadata = MetaData()
json_table = Table(
    "json_test",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("data", JSON),
    Column("name", String(100)),
)


class TestJSONType:
    def test_visit_name(self):
        assert JSON.__visit_name__ == "JSON"

    def test_is_subclass_of_sa_json(self):
        from sqlalchemy.sql import sqltypes

        assert issubclass(JSON, sqltypes.JSON)

    def test_instantiation(self):
        t = JSON()
        assert t is not None

    def test_none_as_null_parameter(self):
        t = JSON(none_as_null=True)
        assert t.none_as_null is True


class TestJSONDDLCompilation:
    def test_json_column_ddl(self):
        dialect = CubridDialect()
        compiled = dialect.type_compiler_instance.process(JSON())
        assert compiled == "JSON"

    def test_generic_sa_json_compiles_to_json(self):
        tbl = Table(
            "ddl_test",
            MetaData(),
            Column("id", Integer, primary_key=True),
            Column("payload", sa.JSON),
        )
        dialect = CubridDialect()
        create_ddl = sa.schema.CreateTable(tbl).compile(dialect=dialect).string
        assert "JSON" in create_ddl

    def test_cubrid_json_compiles_to_json(self):
        tbl = Table(
            "ddl_test2",
            MetaData(),
            Column("id", Integer, primary_key=True),
            Column("payload", JSON),
        )
        dialect = CubridDialect()
        create_ddl = sa.schema.CreateTable(tbl).compile(dialect=dialect).string
        assert "JSON" in create_ddl


class TestJSONIndexType:
    def test_format_integer_index(self):
        idx = JSONIndexType()
        assert idx._format_value(0) == "$[0]"
        assert idx._format_value(3) == "$[3]"

    def test_format_string_key(self):
        idx = JSONIndexType()
        assert idx._format_value("name") == '$."name"'
        assert idx._format_value("address") == '$."address"'


class TestJSONPathType:
    def test_format_simple_path(self):
        pth = JSONPathType()
        assert pth._format_value(("a",)) == '$."a"'

    def test_format_nested_path(self):
        pth = JSONPathType()
        assert pth._format_value(("a", "b", "c")) == '$."a"."b"."c"'

    def test_format_mixed_path(self):
        pth = JSONPathType()
        assert pth._format_value(("a", 1, "b")) == '$."a"[1]."b"'

    def test_format_array_only_path(self):
        pth = JSONPathType()
        assert pth._format_value((0, 1, 2)) == "$[0][1][2]"


class TestJSONPathExpressionCompilation:
    def test_json_getitem_string_key(self):
        stmt = select(json_table.c.data["name"])
        sql = _compile(stmt)
        assert "JSON_EXTRACT" in sql

    def test_json_getitem_integer_index(self):
        stmt = select(json_table.c.data[0])
        sql = _compile(stmt)
        assert "JSON_EXTRACT" in sql

    def test_json_path_getitem(self):
        stmt = select(json_table.c.data[("a", "b")])
        sql = _compile(stmt)
        assert "JSON_EXTRACT" in sql

    def test_json_getitem_in_where(self):
        stmt = select(json_table).where(json_table.c.data["status"].as_string() == "active")
        sql = _compile(stmt)
        assert "JSON_EXTRACT" in sql
        assert "JSON_UNQUOTE" in sql

    def test_json_getitem_as_integer(self):
        stmt = select(json_table).where(json_table.c.data["count"].as_integer() > 5)
        sql = _compile(stmt)
        assert "JSON_EXTRACT" in sql
        assert "CAST" in sql
        assert "INTEGER" in sql

    def test_json_getitem_as_float(self):
        stmt = select(json_table).where(json_table.c.data["score"].as_float() > 3.5)
        sql = _compile(stmt)
        assert "JSON_EXTRACT" in sql
        assert "CAST" in sql
        assert "DOUBLE" in sql

    def test_json_null_handling_for_string(self):
        stmt = select(json_table.c.data["name"].as_string())
        sql = _compile(stmt)
        assert "WHEN 'null' THEN NULL" in sql

    def test_json_getitem_as_boolean(self):
        stmt = select(json_table).where(
            json_table.c.data["active"].as_boolean() == True  # noqa: E712
        )
        sql = _compile(stmt)
        assert "WHEN 'true' THEN 1" in sql
        assert "WHEN 'false' THEN 0" in sql


class TestJSONKeyEscaping:
    def test_key_with_embedded_quote(self):
        idx = JSONIndexType()
        assert idx._format_value('a"b') == '$."a""b"'

    def test_key_with_dot(self):
        idx = JSONIndexType()
        assert idx._format_value("a.b") == '$."a.b"'

    def test_key_with_space(self):
        idx = JSONIndexType()
        assert idx._format_value("a b") == '$."a b"'

    def test_empty_string_key(self):
        idx = JSONIndexType()
        assert idx._format_value("") == '$.""'

    def test_path_with_embedded_quote(self):
        pth = JSONPathType()
        assert pth._format_value(('a"b', "c")) == '$."a""b"."c"'


class TestFuncJSONExtract:
    def test_func_json_extract(self):
        stmt = select(func.JSON_EXTRACT(json_table.c.data, "$.name"))
        sql = _compile(stmt)
        assert "JSON_EXTRACT" in sql
        assert "$.name" in sql

    def test_func_json_contains(self):
        stmt = select(json_table).where(
            func.JSON_CONTAINS(json_table.c.data, '"value"', "$.key") == 1
        )
        sql = _compile(stmt)
        assert "JSON_CONTAINS" in sql

    def test_func_json_object(self):
        stmt = select(func.JSON_OBJECT("key", "value"))
        sql = _compile(stmt)
        assert "JSON_OBJECT" in sql

    def test_func_json_array(self):
        stmt = select(func.JSON_ARRAY(1, 2, 3))
        sql = _compile(stmt)
        assert "JSON_ARRAY" in sql


class TestColspecs:
    def test_generic_json_maps_to_cubrid_json(self):
        from sqlalchemy_cubrid.dialect import colspecs
        from sqlalchemy.sql import sqltypes

        assert sqltypes.JSON in colspecs
        assert colspecs[sqltypes.JSON] is JSON

    def test_json_index_type_mapped(self):
        from sqlalchemy_cubrid.dialect import colspecs
        from sqlalchemy.sql import sqltypes

        assert sqltypes.JSON.JSONIndexType in colspecs
        assert colspecs[sqltypes.JSON.JSONIndexType] is JSONIndexType

    def test_json_path_type_mapped(self):
        from sqlalchemy_cubrid.dialect import colspecs
        from sqlalchemy.sql import sqltypes

        assert sqltypes.JSON.JSONPathType in colspecs
        assert colspecs[sqltypes.JSON.JSONPathType] is JSONPathType


class TestIschemaNames:
    def test_json_in_ischema_names(self):
        from sqlalchemy_cubrid.dialect import ischema_names

        assert "JSON" in ischema_names
        assert ischema_names["JSON"] is JSON


class TestJSONExport:
    def test_json_in_init_all(self):
        import sqlalchemy_cubrid

        assert "JSON" in sqlalchemy_cubrid.__all__
        assert "JSONIndexType" in sqlalchemy_cubrid.__all__
        assert "JSONPathType" in sqlalchemy_cubrid.__all__

    def test_json_importable(self):
        from sqlalchemy_cubrid import JSON as ImportedJSON

        assert ImportedJSON is JSON

    def test_json_index_type_importable(self):
        from sqlalchemy_cubrid import JSONIndexType as ImportedJIT

        assert ImportedJIT is JSONIndexType

    def test_json_path_type_importable(self):
        from sqlalchemy_cubrid import JSONPathType as ImportedJPT

        assert ImportedJPT is JSONPathType


class TestFormatTypeMixinProcessors:
    def _dialect(self):
        from sqlalchemy_cubrid.dialect import CubridDialect

        return CubridDialect()

    def test_format_value_not_implemented(self):
        from sqlalchemy_cubrid.types import _FormatTypeMixin

        with pytest.raises(NotImplementedError):
            _FormatTypeMixin()._format_value("anything")

    def test_index_bind_processor_int(self):
        proc = JSONIndexType().bind_processor(self._dialect())
        assert proc is not None
        assert proc(0) == "$[0]"

    def test_index_bind_processor_string_escapes(self):
        proc = JSONIndexType().bind_processor(self._dialect())
        assert proc('a"b') == '$."a""b"'

    def test_index_literal_processor_int(self):
        proc = JSONIndexType().literal_processor(self._dialect())
        assert proc is not None
        result = proc(2)
        assert "$[2]" in result

    def test_index_literal_processor_string(self):
        proc = JSONIndexType().literal_processor(self._dialect())
        result = proc("name")
        assert '$."name"' in result

    def test_path_bind_processor(self):
        proc = JSONPathType().bind_processor(self._dialect())
        assert proc is not None
        assert proc(("a", 1, "b")) == '$."a"[1]."b"'

    def test_path_literal_processor(self):
        proc = JSONPathType().literal_processor(self._dialect())
        result = proc(("x", 0))
        assert '$."x"[0]' in result

    def test_index_bind_processor_no_super(self, monkeypatch):
        """Cover the branch where string_bind_processor returns None."""
        idx = JSONIndexType()
        monkeypatch.setattr(idx, "string_bind_processor", lambda dialect: None)
        proc = idx.bind_processor(self._dialect())
        assert proc("k") == '$."k"'

    def test_index_literal_processor_no_super(self, monkeypatch):
        """Cover the branch where string_literal_processor returns None."""
        idx = JSONIndexType()
        monkeypatch.setattr(idx, "string_literal_processor", lambda dialect: None)
        proc = idx.literal_processor(self._dialect())
        assert proc("k") == '$."k"'

    def test_index_literal_processor_backslash_not_doubled(self):
        """Regression #313: JSON path literals must not double backslashes."""
        proc = JSONIndexType().literal_processor(self._dialect())
        assert proc is not None
        result = proc("a\\b")
        assert "\\\\" not in result
