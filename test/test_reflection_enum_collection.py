# test/test_reflection_enum_collection.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Reflection of native ENUM and collection columns (#631).

What the supported servers print, from the ``sct_types`` table recorded by
``test/test_show_create_table_server_output.py`` on 10.2, 11.0, 11.2 and 11.4
(the output is identical on all four):

* ``SHOW COLUMNS`` prints an ENUM with its elements unescaped:
  ``ENUM('it's', 'a, b', 'c (d)')`` for ``ENUM('it''s', 'a, b', 'c (d)')``.
* It prints a collection as ``SET OF <type>[,<type>...]`` (``MULTISET OF``,
  ``SEQUENCE OF``; ``LIST`` is printed as ``SEQUENCE``), without the member
  lengths or precision and with the members in its own order
  (``SEQUENCE OF NCHAR VARYING,NUMERIC``, ``SMALLINT`` as ``SHORT``).
* A collection declared without a member type has no type at all (``None``).
* The public ``db_attr_setdomain_elm`` view lists every member type with its
  precision and scale, in declaration order (``STRING`` for ``VARCHAR``,
  ``VARBIT`` for ``BIT VARYING``, ``VARNCHAR`` for ``NCHAR VARYING``).

Offline, the recorded rows go through the real ``get_columns``; live, the
server under test reflects the same table, and ``metadata.reflect()`` followed
by ``create_all()`` on a fresh copy recreates the same DDL.
"""

from __future__ import annotations

import warnings
from typing import Any
from unittest.mock import MagicMock

import pytest
import sqlalchemy as sa
from sqlalchemy import exc as sa_exc

from sqlalchemy_cubrid.dialect import CubridDialect
from sqlalchemy_cubrid.types import MULTISET, SEQUENCE, SET
from test.test_show_create_table_server_output import (
    SETUP_SQL,
    SUPPORTED_VERSIONS,
    _CatalogStub,
    _load,
    _normalize_ddl,
)

TABLE = "sct_types"
(CREATE_SQL,) = [statement for statement in SETUP_SQL if f"CREATE TABLE {TABLE} " in statement]

#: ``sct_types`` columns and the DDL type each one reflects to.
EXPECTED_TYPES: dict[str, str] = {
    "id": "INTEGER",
    "e_plain": "ENUM('x', 'y', 'z')",
    "e_punct": "ENUM('it''s', 'a, b', 'c (d)')",
    "s_one": "SET(INTEGER)",
    "s_many": "SET(NUMERIC(10, 2),VARCHAR(20))",
    "s_of": "SET(CHAR(3))",
    "m_many": "MULTISET(INTEGER,DOUBLE)",
    "m_str": "MULTISET(VARCHAR(50))",
    "q_seq": "SEQUENCE(DATE,SMALLINT)",
    "q_list": "SEQUENCE(NUMERIC(15, 0),NCHAR VARYING(5))",
    "q_bits": "SEQUENCE(BIT(8),BIT VARYING(16))",
    "s_empty": "SET()",
    "m_empty": "MULTISET()",
    "q_empty": "SEQUENCE()",
}


def _compiled(dialect: Any, columns: list[Any]) -> dict[str, str]:
    return {column["name"]: dialect.type_compiler.process(column["type"]) for column in columns}


def _reflect_rows(rows: list[tuple[Any, ...]], *catalog: list[Any]) -> list[Any]:
    """Run the real ``get_columns`` over ``SHOW COLUMNS`` *rows* followed by
    the *catalog* results, failing on any warning."""
    dialect = CubridDialect()
    connection = MagicMock()
    connection.execute.side_effect = [rows, *catalog]
    with warnings.catch_warnings():
        warnings.simplefilter("error", sa_exc.SAWarning)
        return [column["type"] for column in dialect.get_columns(connection, "t")]


# ---------------------------------------------------------------------------
# Offline: recorded server output through the real get_columns
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version", SUPPORTED_VERSIONS)
def test_recorded_column_types(version: str) -> None:
    dialect = CubridDialect()
    stub = _CatalogStub(_load(version)["tables"][TABLE])
    with warnings.catch_warnings():
        warnings.simplefilter("error", sa_exc.SAWarning)
        columns = dialect.get_columns(stub, TABLE)
    assert _compiled(dialect, columns) == EXPECTED_TYPES
    enums = {c["name"]: list(c["type"].enums) for c in columns if c["name"].startswith("e_")}
    assert enums == {"e_plain": ["x", "y", "z"], "e_punct": ["it's", "a, b", "c (d)"]}


@pytest.mark.parametrize("version", SUPPORTED_VERSIONS)
def test_recorded_catalog_queries_only_when_needed(version: str) -> None:
    """The member-type and collection-kind lookups run once each."""
    stub = _CatalogStub(_load(version)["tables"][TABLE])
    CubridDialect().get_columns(stub, TABLE)
    assert sum("db_attr_setdomain_elm" in sql for sql in stub.statements) == 1
    assert sum("SELECT attr_name, data_type FROM" in sql for sql in stub.statements) == 1
    plain = _CatalogStub(_load(version)["tables"]["sct_parent"])
    CubridDialect().get_columns(plain, "sct_parent")
    assert not any("data_type" in sql for sql in plain.statements)


def test_enum_is_not_overwritten() -> None:
    """The ENUM built from the element list is the reflected type."""
    (coltype,) = _reflect_rows([("c", "ENUM('x', 'y')", "YES", "", None, "")], [])
    assert type(coltype).__name__ == "ENUM"
    assert list(coltype.enums) == ["x", "y"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("'it's', 'b'", ["it's", "b"]),
        ("'a, b', 'c (d)'", ["a, b", "c (d)"]),
        ("'it''s', 'b'", ["it's", "b"]),
        ("'x'", ["x"]),
        ("''", [""]),
        ("", []),
    ],
)
def test_parse_enum_elements_server_form(raw: str, expected: list[str]) -> None:
    from sqlalchemy_cubrid.dialect import _parse_enum_elements

    assert _parse_enum_elements(raw) == expected


@pytest.mark.parametrize(
    ("raw", "cls", "members"),
    [
        ("SET OF NUMERIC,VARCHAR", SET, ["NUMERIC", "VARCHAR(4096)"]),
        ("MULTISET OF DOUBLE,INTEGER", MULTISET, ["DOUBLE", "INTEGER"]),
        ("SEQUENCE OF DATE,SHORT", SEQUENCE, ["DATE", "SMALLINT"]),
        ("SEQUENCE OF BIT,BIT VARYING", SEQUENCE, ["BIT(1)", "BIT VARYING"]),
        ("SEQUENCE OF NCHAR VARYING,NUMERIC", SEQUENCE, ["NCHAR VARYING(4096)", "NUMERIC"]),
    ],
)
def test_collection_of_form_without_catalog_members(
    raw: str, cls: type, members: list[str]
) -> None:
    """Without catalog member rows the ``SHOW COLUMNS`` member names are used,
    split by the #626 member splitter (no parameters to strip)."""
    (coltype,) = _reflect_rows([("c", raw, "YES", "", None, "")], [], [])
    assert type(coltype) is cls
    dialect = CubridDialect()
    assert [dialect.type_compiler.process(m) for m in coltype._ddl_values] == members


def test_object_domain_member_keeps_its_class() -> None:
    """An object-domain member is printed by ``SHOW COLUMNS`` as ``OBJECT``
    and listed by ``db_attr_setdomain_elm`` as ``OBJECT`` with its
    ``domain_class_name`` (CUBRID 10.2 and 11.4: ``SET(t_ref)`` ->
    ``SET OF OBJECT`` / ``('a', 'OBJECT', 0, 0, 't_ref')``); the reflected
    member is the class name. An unknown catalog name without a class, and an
    unknown ``SHOW COLUMNS`` member, are kept as their bare names."""
    rows = [("c", "SEQUENCE OF INTEGER,OBJECT", "YES", "", None, "")]
    (from_catalog,) = _reflect_rows(
        rows, [("c", "OBJECT", 0, 0, "t_ref"), ("c", "INTEGER", 10, 0, None)], []
    )
    dialect = CubridDialect()
    assert dialect.type_compiler.process(from_catalog) == "SEQUENCE(t_ref,INTEGER)"
    (no_class,) = _reflect_rows(rows, [("c", "OBJECT", 0, 0, None)], [])
    assert no_class._ddl_values == ("OBJECT",)
    (from_show_columns,) = _reflect_rows([("c", "SET OF t_ref", "YES", "", None, "")], [], [])
    assert from_show_columns._ddl_values == ("t_ref",)


def test_collection_without_member_type_and_unknown_kind() -> None:
    """A ``None`` type that the catalog does not list as a collection warns
    and reflects as ``NullType`` instead of failing."""
    dialect = CubridDialect()
    connection = MagicMock()
    connection.execute.side_effect = [[("c", None, "YES", "", None, "")], [], []]
    with pytest.warns(sa_exc.SAWarning, match="Did not recognize type 'None' of column 'c'"):
        (column,) = dialect.get_columns(connection, "t")
    assert isinstance(column["type"], sa.types.NullType)


def test_reflected_collection_keeps_bind_processor() -> None:
    """The reflected type is the dialect collection class, so the #484 bind
    processor applies to it like to a declared one."""
    (coltype,) = _reflect_rows(
        [("c", "SEQUENCE OF DATE,SHORT", "YES", "", None, "")],
        [("c", "DATE", 10, 0, None), ("c", "SHORT", 5, 0, None)],
        [],
    )
    dialect = MagicMock(_cubrid_pycubrid_dbapi=True)
    process = coltype.bind_processor(dialect)
    assert process is not None
    with pytest.raises(TypeError, match="SEQUENCE is ordered"):
        process({1})


# ---------------------------------------------------------------------------
# Live: reflection and reflect() -> create_all() round trip
# ---------------------------------------------------------------------------


@pytest.fixture
def live_engine():  # noqa: ANN201
    import os

    engine = sa.create_engine(os.environ["CUBRID_TEST_URL"])
    yield engine
    engine.dispose()


@pytest.fixture
def types_table(live_engine: sa.Engine):  # noqa: ANN201
    with live_engine.begin() as connection:
        connection.exec_driver_sql(f"DROP TABLE IF EXISTS {TABLE}")
        connection.exec_driver_sql(CREATE_SQL)
    yield
    with live_engine.begin() as connection:
        connection.exec_driver_sql(f"DROP TABLE IF EXISTS {TABLE}")


def _table_state(connection: sa.Connection) -> tuple[str, list[Any], list[Any]]:
    ddl = connection.exec_driver_sql(f"SHOW CREATE TABLE {TABLE}").one()[1]
    show_columns = [tuple(row) for row in connection.exec_driver_sql(f"SHOW COLUMNS IN {TABLE}")]
    domains = connection.execute(
        sa.text(
            "SELECT attr_name, data_type, prec, scale, domain_class_name "
            "FROM db_attr_setdomain_elm WHERE class_name = :name"
        ),
        {"name": TABLE},
    ).all()
    return _normalize_ddl(ddl), show_columns, [tuple(row) for row in domains]


@pytest.mark.integration
@pytest.mark.usefixtures("types_table")
def test_live_column_types(live_engine: sa.Engine) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", sa_exc.SAWarning)
        columns = sa.inspect(live_engine).get_columns(TABLE)
    assert _compiled(live_engine.dialect, columns) == EXPECTED_TYPES


@pytest.mark.integration
@pytest.mark.usefixtures("types_table")
def test_live_reflect_then_create_all_recreates_ddl(live_engine: sa.Engine) -> None:
    with live_engine.connect() as connection:
        original = _table_state(connection)
    metadata = sa.MetaData()
    with warnings.catch_warnings():
        warnings.simplefilter("error", sa_exc.SAWarning)
        metadata.reflect(live_engine, only=[TABLE])
    with live_engine.begin() as connection:
        connection.exec_driver_sql(f"DROP TABLE {TABLE}")
    metadata.create_all(live_engine)
    with live_engine.connect() as connection:
        assert _table_state(connection) == original


@pytest.mark.integration
def test_live_object_domain_member_round_trip(live_engine: sa.Engine) -> None:
    """A collection of a class reflects with the class name and recreates the
    same DDL (11.x needs the referenced class to be ``DONT_REUSE_OID``)."""
    with live_engine.connect() as connection:
        version = connection.dialect.server_version_info or (0,)
    options = " DONT_REUSE_OID" if version >= (11, 0) else ""
    statements = (
        f"CREATE TABLE sct_obj_ref (id INT){options}",
        "CREATE TABLE sct_obj (a SET(sct_obj_ref), b SEQUENCE(sct_obj_ref, INT))",
    )

    def drop() -> None:
        with live_engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE IF EXISTS sct_obj")
            connection.exec_driver_sql("DROP TABLE IF EXISTS sct_obj_ref")

    drop()
    try:
        with live_engine.begin() as connection:
            for statement in statements:
                connection.exec_driver_sql(statement)
        with live_engine.connect() as connection:
            original = connection.exec_driver_sql("SHOW CREATE TABLE sct_obj").one()[1]
        columns = sa.inspect(live_engine).get_columns("sct_obj")
        assert _compiled(live_engine.dialect, columns) == {
            "a": "SET(sct_obj_ref)",
            "b": "SEQUENCE(sct_obj_ref,INTEGER)",
        }
        metadata = sa.MetaData()
        metadata.reflect(live_engine, only=["sct_obj"])
        with live_engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE sct_obj")
        metadata.create_all(live_engine)
        with live_engine.connect() as connection:
            recreated = connection.exec_driver_sql("SHOW CREATE TABLE sct_obj").one()[1]
        assert _normalize_ddl(recreated) == _normalize_ddl(original)
    finally:
        drop()
