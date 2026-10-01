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
from sqlalchemy.types import NullType

from sqlalchemy_cubrid.dialect import CubridDialect
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
EXPECTED_ENUM_VALUES = {
    "e_plain": ["x", "y", "z"],
    "e_punct": ["it's", "a, b", "c (d)"],
}


def _compiled(dialect: Any, columns: list[Any]) -> dict[str, str]:
    return {column["name"]: dialect.type_compiler.process(column["type"]) for column in columns}


def _reflect_rows(rows: list[tuple[Any, ...]], *catalog: list[Any]) -> list[Any]:
    """Run the real ``get_columns`` over ``SHOW COLUMNS`` *rows* followed by
    the *catalog* results, failing on any warning."""
    dialect = CubridDialect()
    connection = MagicMock()
    connection.execute.side_effect = [rows, *catalog, []]
    with warnings.catch_warnings():
        warnings.simplefilter("error", sa_exc.SAWarning)
        return [column["type"] for column in dialect.get_columns(connection, "t")]


def _reflect_catalog_type(
    raw: str,
    *,
    enum_rows: list[Any] | Exception | None = None,
    member_rows: list[Any] | None = None,
) -> Any:
    """Reflect one recorded SHOW COLUMNS type with explicit catalog replies."""
    dialect = CubridDialect()
    connection = MagicMock()

    def execute(statement: Any, params: Any = None) -> list[Any]:
        sql = str(statement)
        if sql.startswith("SHOW COLUMNS IN"):
            return [("c", raw, "YES", "", None, "")]
        if "_db_domain" in sql:
            if isinstance(enum_rows, Exception):
                raise enum_rows
            return enum_rows or []
        if "db_attr_setdomain_elm" in sql:
            return member_rows or []
        if "db_attribute" in sql:
            return []
        raise AssertionError(f"unexpected reflection query: {sql}")

    connection.execute.side_effect = execute
    return dialect.get_columns(connection, "t")[0]["type"]


# ---------------------------------------------------------------------------
# Offline: recorded server output through the real get_columns
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version", SUPPORTED_VERSIONS)
def test_recorded_column_types(version: str) -> None:
    dialect = CubridDialect()
    stub = _CatalogStub(_load(version)["tables"][TABLE], EXPECTED_ENUM_VALUES)
    with warnings.catch_warnings():
        warnings.simplefilter("error", sa_exc.SAWarning)
        columns = dialect.get_columns(stub, TABLE)
    assert _compiled(dialect, columns) == EXPECTED_TYPES
    enums = {c["name"]: list(c["type"].enums) for c in columns if c["name"].startswith("e_")}
    assert enums == EXPECTED_ENUM_VALUES


def test_enum_catalog_query_binds_owner_and_attribute_on_11_4(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dialect = CubridDialect()
    dialect.server_version_info = (11, 4, 6)
    stub = _CatalogStub(_load("11.4")["tables"][TABLE], EXPECTED_ENUM_VALUES)
    original_execute = stub.execute
    calls: list[tuple[str, Any]] = []

    def record_execute(statement: Any, params: Any = None) -> Any:
        calls.append((str(statement), params))
        return original_execute(statement, params)

    monkeypatch.setattr(stub, "execute", record_execute)
    dialect.get_columns(stub, TABLE)
    enum_calls = [(sql, params) for sql, params in calls if "FROM _db_class c" in sql]
    assert len(enum_calls) == 2
    assert {params["attr_name"] for _, params in enum_calls} == set(EXPECTED_ENUM_VALUES)
    assert all("c.unique_name = :class_name" in sql for sql, _ in enum_calls)
    assert all(params["class_name"] == "dba.sct_types" for _, params in enum_calls)


@pytest.mark.parametrize("version", SUPPORTED_VERSIONS)
def test_recorded_catalog_queries_only_when_needed(version: str) -> None:
    """The member-type and collection-kind lookups run once each."""
    stub = _CatalogStub(_load(version)["tables"][TABLE], EXPECTED_ENUM_VALUES)
    CubridDialect().get_columns(stub, TABLE)
    assert sum("db_attr_setdomain_elm" in sql for sql in stub.statements) == 1
    assert sum("SELECT attr_name, data_type FROM" in sql for sql in stub.statements) == 1
    plain = _CatalogStub(_load(version)["tables"]["sct_parent"])
    CubridDialect().get_columns(plain, "sct_parent")
    assert not any("data_type" in sql for sql in plain.statements)


def test_enum_is_not_overwritten() -> None:
    """The ENUM built from the element list is the reflected type."""
    (coltype,) = _reflect_rows(
        [("c", "ENUM('x', 'y')", "YES", "", None, "")],
        [("c", "x", 1), ("c", "y", 2)],
    )
    assert type(coltype).__name__ == "ENUM"
    assert list(coltype.enums) == ["x", "y"]


@pytest.mark.parametrize(
    ("catalog_rows", "expected"),
    [
        ([("c", "a', 'b", 1), ("c", "other", 2)], ["a', 'b", "other"]),
        ([("c", "a", 1), ("c", "b", 2), ("c", "other", 3)], ["a", "b", "other"]),
    ],
)
def test_ambiguous_enum_output_uses_exact_catalog_values(
    catalog_rows: list[Any], expected: list[str]
) -> None:
    """Two legal definitions print the same SHOW text; only catalog rows distinguish them."""
    coltype = _reflect_catalog_type("ENUM('a', 'b', 'other')", enum_rows=catalog_rows)
    assert list(coltype.enums) == expected


@pytest.mark.parametrize("cubriddb_shape", [False, True])
@pytest.mark.parametrize("catalog", ["_db_class", "_db_attribute", "_db_domain"])
def test_enum_catalog_permission_denial_fails_closed(cubriddb_shape: bool, catalog: str) -> None:
    class CatalogPermissionError(RuntimeError):
        errno = -494

    denied = (
        RuntimeError(-494, f"SELECT is not authorized on {catalog}")
        if cubriddb_shape
        else CatalogPermissionError(f"SELECT is not authorized on {catalog} (-494)")
    )
    with pytest.warns(sa_exc.SAWarning, match="ENUM"):
        coltype = _reflect_catalog_type("ENUM('a', 'b')", enum_rows=denied)
    assert isinstance(coltype, NullType)


def test_unrelated_enum_catalog_failure_propagates() -> None:
    with pytest.raises(RuntimeError, match="catalog unavailable"):
        _reflect_catalog_type("ENUM('a', 'b')", enum_rows=RuntimeError("catalog unavailable"))


def test_unrelated_semantic_494_propagates() -> None:
    class CatalogSemanticError(RuntimeError):
        errno = -494

    with pytest.raises(CatalogSemanticError, match="Unknown class"):
        _reflect_catalog_type(
            "ENUM('a', 'b')", enum_rows=CatalogSemanticError("Unknown class (-494)")
        )


@pytest.mark.parametrize(
    "raw",
    [
        "SET OF NUMERIC,VARCHAR",
        "MULTISET OF DOUBLE,INTEGER",
        "SEQUENCE OF DATE,SHORT",
        "SEQUENCE OF BIT,BIT VARYING",
        "SEQUENCE OF NCHAR VARYING,NUMERIC",
    ],
)
def test_collection_of_form_without_catalog_members_fails_closed(raw: str) -> None:
    """SHOW COLUMNS omits modifiers; absent member-domain rows are not enough."""
    with pytest.warns(sa_exc.SAWarning, match="collection"):
        coltype = _reflect_catalog_type(raw)
    assert isinstance(coltype, NullType)


def test_object_domain_member_keeps_its_class() -> None:
    """An object-domain member is printed by ``SHOW COLUMNS`` as ``OBJECT``
    and listed by ``db_attr_setdomain_elm`` as ``OBJECT`` with its
    ``domain_class_name`` (CUBRID 10.2 and 11.4: ``SET(t_ref)`` ->
    ``SET OF OBJECT`` / ``('a', 'OBJECT', 0, 0, 't_ref')``); the reflected
    member is the class name. A missing target class or missing catalog rows
    must fail closed instead of compiling a different object domain."""
    rows = [("c", "SEQUENCE OF INTEGER,OBJECT", "YES", "", None, "")]
    (from_catalog,) = _reflect_rows(
        rows, [("c", "OBJECT", 0, 0, "t_ref"), ("c", "INTEGER", 10, 0, None)], []
    )
    dialect = CubridDialect()
    assert dialect.type_compiler.process(from_catalog) == "SEQUENCE(t_ref,INTEGER)"
    with pytest.raises(ValueError, match="no domain class"):
        _reflect_rows(rows, [("c", "OBJECT", 0, 0, None)], [])
    with pytest.warns(sa_exc.SAWarning, match="collection"):
        from_show_columns = _reflect_catalog_type("SET OF t_ref")
    assert isinstance(from_show_columns, NullType)


@pytest.mark.parametrize(
    "member_rows",
    [
        [],
        [("c", "NUMERIC", 10, 2, None)],
        [("c", "NUMERIC", 10, 2, None), ("c", "NUMERIC", 8, 0, None)],
    ],
)
def test_incomplete_or_inconsistent_typed_catalog_fails_closed(member_rows: list[Any]) -> None:
    """SHOW COLUMNS erased member modifiers, so missing rows cannot be guessed."""
    with pytest.warns(sa_exc.SAWarning, match="collection"):
        coltype = _reflect_catalog_type("SET OF NUMERIC,VARCHAR", member_rows=member_rows)
    assert isinstance(coltype, NullType)


def test_object_member_preserves_target_class() -> None:
    coltype = _reflect_catalog_type(
        "SET OF OBJECT",
        member_rows=[("c", "OBJECT", 0, 0, "target_ref")],
    )
    compiled = CubridDialect().type_compiler.process(coltype)
    assert "target_ref" in compiled
    assert compiled != "SET(OBJECT)"


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


def test_enum_member_of_collection_fails_closed() -> None:
    """``SET(ENUM('x','y'))`` is printed as ``SET OF ENUM`` and listed by the
    view as ``('s', 'ENUM', 0, 0, NULL)`` on 10.2 and 11.4: the values are not
    there, and ``SET(ENUM())`` is not valid DDL."""
    with pytest.warns(sa_exc.SAWarning, match="collection"):
        coltype = _reflect_catalog_type("SET OF ENUM", member_rows=[("c", "ENUM", 0, 0, None)])
    assert isinstance(coltype, NullType)


@pytest.mark.parametrize(
    ("domain_owner", "table_owner", "expected"),
    [
        ("RA", "RB", "ra.tref2"),
        ("RB", "RB", "tref2"),
        ("Rb", "RB", "tref2"),
        (None, "RB", "tref2"),
        ("RA", None, "tref2"),
    ],
)
def test_object_member_of_another_owner_is_qualified(
    domain_owner: str | None, table_owner: str | None, expected: str
) -> None:
    """``rb.tx (o SET(ra.tref2))`` must not reflect as ``SET(tref2)``, which
    ``create_all()`` would resolve in ``rb``'s schema."""
    member = CubridDialect()._collection_member_type(
        "OBJECT", 0, 0, "tref2", domain_owner, table_owner
    )
    assert member == expected


def test_member_owner_is_read_on_11_2() -> None:
    """From 11.2 the member query also selects ``domain_owner_name`` and the
    table owner comes from the class lookup."""
    dialect = CubridDialect()
    dialect.server_version_info = (11, 4, 0)
    statements: list[str] = []

    def execute(statement: Any, params: Any = None) -> Any:
        sql = " ".join(str(statement).split())
        statements.append(sql)
        if sql.startswith("SHOW COLUMNS IN"):
            return [("o", "SET OF OBJECT", "YES", "", None, "")]
        if "FROM db_class" in sql:
            result = MagicMock()
            result.first.return_value = ("CLASS", "RB")
            return result
        if "db_attr_setdomain_elm" in sql:
            return [("o", "OBJECT", 0, 0, "tref2", "RA")]
        return []

    connection = MagicMock()
    connection.execute.side_effect = execute
    with warnings.catch_warnings():
        warnings.simplefilter("error", sa_exc.SAWarning)
        (column,) = dialect.get_columns(connection, "tx")
    assert dialect.type_compiler.process(column["type"]) == "SET(ra.tref2)"
    assert any("domain_owner_name" in sql for sql in statements)


# ---------------------------------------------------------------------------
# Live: non-DBA users, other owners and ENUM members
# ---------------------------------------------------------------------------

LIVE_USER = "u631"


def _run(engine: sa.Engine, *statements: str, ignore_errors: bool = False) -> None:
    for statement in statements:
        try:
            with engine.begin() as connection:
                connection.exec_driver_sql(statement)
        except sa_exc.DBAPIError:
            if not ignore_errors:
                raise


def _live_version(engine: sa.Engine) -> tuple[int, ...]:
    with engine.connect() as connection:
        return tuple(connection.dialect.server_version_info or (0,))


@pytest.fixture
def user_engine(live_engine: sa.Engine):  # noqa: ANN201
    """A non-DBA user ``u631``, created for the test and dropped with its tables."""
    user = sa.create_engine(live_engine.url.set(username=LIVE_USER, password=None))
    tables = ("sct_enum_u", "sct_obj_uref")

    def cleanup() -> None:
        with live_engine.connect() as connection:
            exists = connection.execute(
                sa.text("SELECT COUNT(*) FROM db_user WHERE name = :name"),
                {"name": LIVE_USER.upper()},
            ).scalar()
        if exists:
            _run(user, *(f"DROP TABLE IF EXISTS {t}" for t in tables), ignore_errors=True)
            user.dispose()
            _run(live_engine, f"DROP USER {LIVE_USER}")

    cleanup()
    _run(live_engine, f"CREATE USER {LIVE_USER}")
    try:
        yield user
    finally:
        user.dispose()
        cleanup()


@pytest.mark.integration
def test_live_enum_as_non_dba_user_fails_closed(user_engine: sa.Engine) -> None:
    """A non-DBA user is denied ``_db_*`` (-494): every ENUM column warns and
    reflects as NullType, and the transaction stays usable."""
    _run(
        user_engine,
        "CREATE TABLE sct_enum_u (id INT, e_plain ENUM('x', 'y'), e_sep ENUM('a'', ''b', 'other'))",
    )
    with user_engine.begin() as connection:
        with pytest.warns(sa_exc.SAWarning, match="Could not safely reflect ENUM"):
            columns = sa.inspect(connection).get_columns("sct_enum_u")
        assert connection.exec_driver_sql("SELECT COUNT(*) FROM sct_enum_u").scalar() == 0
    types = {column["name"]: column["type"] for column in columns}
    assert isinstance(types["e_plain"], NullType)
    assert isinstance(types["e_sep"], NullType)
    assert not isinstance(types["id"], NullType)


@pytest.mark.integration
def test_live_enum_member_of_collection_fails_closed(live_engine: sa.Engine) -> None:
    _run(
        live_engine,
        "DROP TABLE IF EXISTS sct_set_enum",
        "CREATE TABLE sct_set_enum (s SET(ENUM('x', 'y')))",
    )
    try:
        with pytest.warns(sa_exc.SAWarning, match="collection type of column 's'"):
            (column,) = sa.inspect(live_engine).get_columns("sct_set_enum")
        assert isinstance(column["type"], NullType)
    finally:
        _run(live_engine, "DROP TABLE IF EXISTS sct_set_enum")


@pytest.mark.integration
def test_live_object_member_of_another_owner_round_trip(
    live_engine: sa.Engine, user_engine: sa.Engine
) -> None:
    """From 11.2 a member class of another owner reflects as ``owner.class``,
    so ``create_all()`` recreates the column instead of failing."""
    if _live_version(live_engine) < (11, 2):
        pytest.skip("class names are global before CUBRID 11.2")
    _run(user_engine, "CREATE TABLE sct_obj_uref (id INT) DONT_REUSE_OID")
    _run(live_engine, "DROP TABLE IF EXISTS sct_obj_x")
    try:
        _run(live_engine, f"CREATE TABLE sct_obj_x (o SET({LIVE_USER}.sct_obj_uref), p INT)")
        with live_engine.connect() as connection:
            original = connection.exec_driver_sql("SHOW CREATE TABLE sct_obj_x").one()[1]
        with warnings.catch_warnings():
            warnings.simplefilter("error", sa_exc.SAWarning)
            columns = sa.inspect(live_engine).get_columns("sct_obj_x")
            metadata = sa.MetaData()
            metadata.reflect(live_engine, only=["sct_obj_x"])
        assert _compiled(live_engine.dialect, columns) == {
            "o": f"SET({LIVE_USER}.sct_obj_uref)",
            "p": "INTEGER",
        }
        _run(live_engine, "DROP TABLE sct_obj_x")
        metadata.create_all(live_engine)
        with live_engine.connect() as connection:
            recreated = connection.exec_driver_sql("SHOW CREATE TABLE sct_obj_x").one()[1]
        assert _normalize_ddl(recreated) == _normalize_ddl(original)
    finally:
        _run(live_engine, "DROP TABLE IF EXISTS sct_obj_x")
