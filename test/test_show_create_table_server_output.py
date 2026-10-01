# test/test_show_create_table_server_output.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Recorded supported-server output for FK / UNIQUE reflection (#611).

Foreign-key reflection has no catalog source: it parses ``SHOW CREATE TABLE``
text, so it depends on the clause grammar and order each server version
prints. ``test/test_show_create_table.py`` locks the parser with hand-written
DDL; this module pins what the supported servers actually print.

``test/fixtures/show_create_table/cubrid-<major>.<minor>.json`` holds, for each
supported version, the server build, the generating SQL (:data:`SETUP_SQL`) and,
per table, the ``SHOW CREATE TABLE`` row, the table's ``db_index`` flags and
its ``SHOW INDEXES`` rows. Since #631 they also hold the column sources of
``get_columns`` (``SHOW COLUMNS``, ``db_attribute`` and the collection member
types in ``db_attr_setdomain_elm``), with the native ``ENUM`` and collection
columns of ``sct_types``; ``test/test_reflection_enum_collection.py`` reflects
them. The files contain no credentials or host names.

* Offline, every recorded ``SHOW CREATE TABLE`` row goes through the real
  dialect parsers via the #590 adapter in ``test/test_show_create_table.py``
  (no copied parsing logic), and the recorded catalog rows through the real
  ``get_unique_constraints`` / ``get_indexes``; both must give
  :data:`EXPECTED_FOREIGN_KEYS` / :data:`EXPECTED_UNIQUE_CONSTRAINTS`.
* Live (``integration``), the same SQL runs on the server under test, and its
  normalized output must equal the recording for that version and its
  reflected constraints the expected ones; a format change fails with a diff.

Output assumptions these recordings support, on 10.2, 11.0, 11.2 and 11.4:

* Each constraint is printed as ``CONSTRAINT [name] ...`` with every
  identifier in brackets, punctuation (spaces, commas, parentheses) kept
  verbatim inside the brackets.
* A foreign key always prints both actions, ``ON DELETE`` first, then
  ``ON UPDATE``, and the default action is printed as ``RESTRICT``. Actions
  seen are ``CASCADE``, ``SET NULL``, ``NO ACTION`` and ``RESTRICT``; the
  servers reject ``ON UPDATE CASCADE`` and have no ``SET DEFAULT``.
* From 11.2 the referenced table is owner-qualified (``[dba.sct_parent]``);
  10.2 and 11.0 print it unqualified.
* ``UNIQUE`` constraints and ``CREATE UNIQUE INDEX`` indexes are printed alike
  as ``UNIQUE KEY`` and carry the same ``db_index`` flags, so each one is
  reflected both as a unique index and as a unique constraint whose
  ``duplicates_index`` names that index. ``DESC`` key parts print as
  ``[col] DESC``.

To record a version, run against a disposable database on that server::

    python -m test.test_show_create_table_server_output cubrid+pycubrid://dba@HOST:PORT/DB
"""

from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest
import sqlalchemy as sa

from sqlalchemy_cubrid.dialect import CubridDialect
from test.test_show_create_table import parse_foreign_keys, parse_unique_constraints

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "show_create_table"

#: Supported versions (docs/SUPPORT_MATRIX.md); each must have a recording.
SUPPORTED_VERSIONS = ("10.2", "11.0", "11.2", "11.4")

#: The SQL every recording was generated with, in order.
SETUP_SQL: tuple[str, ...] = (
    "CREATE TABLE sct_parent ("
    " id INT NOT NULL, tenant_id INT NOT NULL, code VARCHAR(10),"
    " CONSTRAINT pk_sct_parent PRIMARY KEY (id, tenant_id),"
    " CONSTRAINT uq_sct_parent_code UNIQUE (code))",
    "CREATE UNIQUE INDEX ux_sct_parent_tenant_code ON sct_parent (tenant_id, code DESC)",
    'CREATE TABLE "sct ref, (x)" ('
    ' id INT PRIMARY KEY, "odd col, (y)" INT,'
    ' CONSTRAINT "uq sct odd, (name)" UNIQUE ("odd col, (y)"))',
    "CREATE TABLE sct_child ("
    ' id INT PRIMARY KEY, parent_id INT, tenant_id INT, p2 INT, p3 INT, "odd, col (x)" INT,'
    " self_id INT,"
    " CONSTRAINT fk_sct_child_default FOREIGN KEY (parent_id, tenant_id)"
    " REFERENCES sct_parent (id, tenant_id),"
    " CONSTRAINT fk_sct_child_cascade FOREIGN KEY (p2, tenant_id)"
    " REFERENCES sct_parent (id, tenant_id) ON DELETE CASCADE ON UPDATE RESTRICT,"
    " CONSTRAINT fk_sct_child_set_null FOREIGN KEY (p3, tenant_id)"
    " REFERENCES sct_parent (id, tenant_id) ON DELETE SET NULL ON UPDATE SET NULL,"
    ' CONSTRAINT "fk sct odd, (name)" FOREIGN KEY ("odd, col (x)")'
    ' REFERENCES "sct ref, (x)" (id) ON DELETE NO ACTION ON UPDATE NO ACTION,'
    " CONSTRAINT fk_sct_child_self FOREIGN KEY (self_id)"
    " REFERENCES sct_child (id) ON DELETE RESTRICT)",
    # Column types whose SHOW COLUMNS form get_columns parses (#631): native
    # ENUM and every collection spelling, with and without member types.
    "CREATE TABLE sct_types ("
    " id INT PRIMARY KEY, e_plain ENUM('x', 'y', 'z'), e_punct ENUM('it''s', 'a, b', 'c (d)'),"
    " s_one SET(INT), s_many SET(NUMERIC(10,2), VARCHAR(20)), s_of SET OF CHAR(3),"
    " m_many MULTISET(INT, DOUBLE), m_str MULTISET(VARCHAR(50)),"
    " q_seq SEQUENCE(DATE, SMALLINT), q_list LIST(NUMERIC, NCHAR VARYING(5)),"
    " q_bits SEQUENCE(BIT(8), BIT VARYING(16)),"
    " s_empty SET, m_empty MULTISET, q_empty LIST)",
)

#: Tables created by :data:`SETUP_SQL`, in drop order.
TABLES = ("sct_types", "sct_child", "sct ref, (x)", "sct_parent")


def _fk(
    name: str,
    columns: list[str],
    table: str,
    referred: list[str],
    ondelete: str = "RESTRICT",
    onupdate: str = "RESTRICT",
) -> dict[str, Any]:
    return {
        "name": name,
        "constrained_columns": columns,
        "options": {"ondelete": ondelete, "onupdate": onupdate},
        "referred_schema": None,
        "referred_table": table,
        "referred_columns": referred,
    }


#: Reflected foreign keys per table, sorted by name (#531). A key declared
#: without actions reflects as RESTRICT / RESTRICT, as the server prints it.
EXPECTED_FOREIGN_KEYS: dict[str, list[dict[str, Any]]] = {
    "sct_types": [],
    "sct_parent": [],
    "sct ref, (x)": [],
    "sct_child": [
        _fk(
            "fk sct odd, (name)",
            ["odd, col (x)"],
            "sct ref, (x)",
            ["id"],
            ondelete="NO ACTION",
            onupdate="NO ACTION",
        ),
        _fk(
            "fk_sct_child_cascade",
            ["p2", "tenant_id"],
            "sct_parent",
            ["id", "tenant_id"],
            ondelete="CASCADE",
        ),
        _fk("fk_sct_child_default", ["parent_id", "tenant_id"], "sct_parent", ["id", "tenant_id"]),
        _fk("fk_sct_child_self", ["self_id"], "sct_child", ["id"]),
        _fk(
            "fk_sct_child_set_null",
            ["p3", "tenant_id"],
            "sct_parent",
            ["id", "tenant_id"],
            ondelete="SET NULL",
            onupdate="SET NULL",
        ),
    ],
}

#: Reflected unique constraints per table, sorted by name. The constraint and
#: the ``CREATE UNIQUE INDEX`` index reflect alike; each duplicates its index.
EXPECTED_UNIQUE_CONSTRAINTS: dict[str, list[dict[str, Any]]] = {
    "sct_parent": [
        {"name": "uq_sct_parent_code", "column_names": ["code"]},
        {"name": "ux_sct_parent_tenant_code", "column_names": ["tenant_id", "code"]},
    ],
    "sct ref, (x)": [{"name": "uq sct odd, (name)", "column_names": ["odd col, (y)"]}],
    "sct_child": [],
    "sct_types": [],
}
for _constraints in EXPECTED_UNIQUE_CONSTRAINTS.values():
    for _constraint in _constraints:
        _constraint["duplicates_index"] = _constraint["name"]


def _by_name(items: list[Any]) -> list[dict[str, Any]]:
    return sorted((dict(item) for item in items), key=lambda item: item["name"])


# ---------------------------------------------------------------------------
# Capture (shared by the live test and the recording entry point)
# ---------------------------------------------------------------------------


def _quote(connection: sa.Connection, name: str) -> str:
    return connection.dialect.identifier_preparer.quote_identifier(name)


def _drop_tables(connection: sa.Connection) -> None:
    for table in TABLES:
        connection.exec_driver_sql(f"DROP TABLE IF EXISTS {_quote(connection, table)}")


def _capture(connection: sa.Connection) -> dict[str, dict[str, list[Any]]]:
    """Return, per table, its ``SHOW CREATE TABLE`` row, ``db_index`` flags
    (sorted by index name), ``SHOW INDEXES`` key columns (Table, Non_unique,
    Key_name, Seq_in_index, Column_name, Collation; sorted), and the column
    sources of ``get_columns`` (#631): the ``SHOW COLUMNS`` rows, the
    ``db_attribute`` name / type / comment (by ``def_order``) and the
    ``db_attr_setdomain_elm`` collection member types (in server order)."""
    captured: dict[str, dict[str, list[Any]]] = {}
    for table in TABLES:
        quoted = _quote(connection, table)
        show_create = connection.exec_driver_sql(f"SHOW CREATE TABLE {quoted}").one()
        db_index = connection.execute(
            sa.text(
                "SELECT index_name, is_unique, is_primary_key, is_foreign_key "
                "FROM db_index WHERE class_name = :name ORDER BY index_name"
            ),
            {"name": table},
        ).all()
        show_indexes = connection.exec_driver_sql(f"SHOW INDEXES IN {quoted}").all()
        show_columns = connection.exec_driver_sql(f"SHOW COLUMNS IN {quoted}").all()
        db_attribute = connection.execute(
            sa.text(
                "SELECT attr_name, data_type, comment FROM db_attribute "
                "WHERE class_name = :name ORDER BY def_order"
            ),
            {"name": table},
        ).all()
        set_domains = connection.execute(
            sa.text(
                "SELECT attr_name, data_type, prec, scale FROM db_attr_setdomain_elm "
                "WHERE class_name = :name"
            ),
            {"name": table},
        ).all()
        captured[table] = {
            "show_create_table": [str(value) for value in show_create],
            "db_index": [list(row) for row in db_index],
            "show_indexes": sorted([list(row[:6]) for row in show_indexes], key=repr),
            "show_columns": [list(row[:6]) for row in show_columns],
            "db_attribute": [list(row) for row in db_attribute],
            "set_domains": [list(row) for row in set_domains],
        }
    return captured


def _server_version(connection: sa.Connection) -> str:
    return str(connection.exec_driver_sql("SELECT version()").scalar())


def _fixture_path(version: str) -> Path:
    return FIXTURE_DIR / f"cubrid-{'.'.join(version.split('.')[:2])}.json"


def _load(version: str) -> dict[str, Any]:
    return json.loads(_fixture_path(version).read_text(encoding="utf-8"))


def _normalize_ddl(ddl: str) -> str:
    """Collapse whitespace runs and drop the table options after the closing
    parenthesis (``REUSE_OID, COLLATE ...`` depend on the database, not on the
    constraint grammar)."""
    ddl = re.sub(r"\s+", " ", ddl).strip()
    return ddl[: ddl.rindex(")") + 1]


def _record(url: str) -> Path:
    """Run :data:`SETUP_SQL` on *url*, write the recording for its version and
    drop the tables again."""
    engine = sa.create_engine(url)
    try:
        with engine.begin() as connection:
            _drop_tables(connection)
            for statement in SETUP_SQL:
                connection.exec_driver_sql(statement)
        try:
            with engine.connect() as connection:
                version = _server_version(connection)
                tables = _capture(connection)
        finally:
            with engine.begin() as connection:
                _drop_tables(connection)
    finally:
        engine.dispose()
    path = _fixture_path(version)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "cubrid_version": version,
        "captured_with": "python -m test.test_show_create_table_server_output <url>",
        "setup_sql": list(SETUP_SQL),
        "tables": tables,
    }
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Offline: recorded output through the real dialect
# ---------------------------------------------------------------------------


class _Rows(list[Any]):
    def first(self) -> Any:
        return self[0] if self else None


class _CatalogStub:
    """Serves one recorded table to ``get_unique_constraints`` / ``get_indexes``.

    Answers the ``db_class`` lookup and the two ``db_index`` projections
    used by unique-constraint and index reflection from the recorded flags,
    plus ``SHOW INDEXES`` / ``SHOW CREATE TABLE``. Any other statement fails.
    """

    def __init__(self, recorded: dict[str, list[Any]]) -> None:
        self._recorded = recorded
        self.statements: list[str] = []

    def execute(self, statement: Any, params: Any = None) -> _Rows:
        sql = " ".join(str(statement).split())
        self.statements.append(sql)
        flags = self._recorded["db_index"]
        if "FROM db_class" in sql:
            rows: list[Any] = [("CLASS", "DBA")]
        elif sql.startswith(
            "SELECT index_name, is_unique, is_primary_key, is_foreign_key FROM db_index WHERE "
        ):
            rows = [tuple(f) for f in flags]
        elif sql.startswith(
            "SELECT index_name, is_primary_key, is_foreign_key FROM db_index WHERE "
        ):
            rows = [(f[0], f[2], f[3]) for f in flags]
        elif sql.startswith("SHOW INDEXES IN"):
            rows = [tuple(row) for row in self._recorded["show_indexes"]]
        elif sql.startswith("SHOW CREATE TABLE"):
            rows = [tuple(self._recorded["show_create_table"])]
        elif sql.startswith("SHOW COLUMNS IN"):
            rows = [tuple(row) for row in self._recorded["show_columns"]]
        elif sql.startswith("SELECT attr_name, comment FROM db_attribute WHERE "):
            rows = [(row[0], row[2]) for row in self._recorded["db_attribute"]]
        elif sql.startswith("SELECT attr_name, data_type FROM db_attribute WHERE "):
            rows = [
                (row[0], row[1])
                for row in self._recorded["db_attribute"]
                if row[1] in ("SET", "MULTISET", "SEQUENCE")
            ]
        elif sql.startswith("SELECT attr_name, data_type, prec, scale FROM db_attr_setdomain_elm "):
            rows = [tuple(row) for row in self._recorded["set_domains"]]
        else:
            raise AssertionError(f"Unexpected SQL: {sql!r}")
        return _Rows(rows)


def _recordings() -> list[tuple[str, str]]:
    return [(version, table) for version in SUPPORTED_VERSIONS for table in TABLES]


@pytest.fixture
def dialect() -> CubridDialect:
    return CubridDialect()


@pytest.mark.parametrize("version", SUPPORTED_VERSIONS)
def test_recording_metadata(version: str) -> None:
    recording = _load(version)
    assert recording["cubrid_version"].startswith(version + ".")
    assert recording["setup_sql"] == list(SETUP_SQL)
    assert sorted(recording["tables"]) == sorted(TABLES)
    text = _fixture_path(version).read_text(encoding="utf-8")
    assert "password" not in text.lower() and "://" not in text


@pytest.mark.parametrize(("version", "table"), _recordings())
def test_recorded_foreign_keys(dialect: CubridDialect, version: str, table: str) -> None:
    ddl = _load(version)["tables"][table]["show_create_table"][1]
    assert parse_foreign_keys(dialect, ddl) == EXPECTED_FOREIGN_KEYS[table]


@pytest.mark.parametrize(("version", "table"), _recordings())
def test_recorded_unique_constraints_from_ddl(
    dialect: CubridDialect, version: str, table: str
) -> None:
    ddl = _load(version)["tables"][table]["show_create_table"][1]
    assert _by_name(parse_unique_constraints(dialect, ddl)) == EXPECTED_UNIQUE_CONSTRAINTS[table]


@pytest.mark.parametrize(("version", "table"), _recordings())
def test_recorded_catalog_matches_ddl(dialect: CubridDialect, version: str, table: str) -> None:
    """The catalog path gives the DDL path's unique constraints, and each one
    is also reflected as a unique index of the same name and columns."""
    recorded = _load(version)["tables"][table]
    uniques = dialect.get_unique_constraints(_CatalogStub(recorded), table)
    assert _by_name(uniques) == EXPECTED_UNIQUE_CONSTRAINTS[table]
    unique_indexes = [
        {"name": index["name"], "column_names": index["column_names"]}
        for index in _by_name(dialect.get_indexes(_CatalogStub(recorded), table))
        if index["unique"]
    ]
    assert unique_indexes == [
        {"name": uc["name"], "column_names": uc["column_names"]}
        for uc in EXPECTED_UNIQUE_CONSTRAINTS[table]
    ]


@pytest.mark.parametrize("version", SUPPORTED_VERSIONS)
def test_recorded_referenced_table_qualification(version: str) -> None:
    ddl = _load(version)["tables"]["sct_child"]["show_create_table"][1]
    qualified = tuple(int(part) for part in version.split(".")) >= (11, 2)
    assert ("REFERENCES [dba.sct_parent]" in ddl) is qualified
    assert ("REFERENCES [sct_parent]" in ddl) is not qualified


# ---------------------------------------------------------------------------
# Live: the server under test still prints the recorded output
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def live_engine():  # noqa: ANN201
    import os

    engine = sa.create_engine(os.environ["CUBRID_TEST_URL"])
    yield engine
    engine.dispose()


@pytest.fixture
def live_tables(live_engine: sa.Engine):  # noqa: ANN201
    with live_engine.begin() as connection:
        _drop_tables(connection)
        for statement in SETUP_SQL:
            connection.exec_driver_sql(statement)
    yield
    with live_engine.begin() as connection:
        _drop_tables(connection)


@pytest.mark.integration
@pytest.mark.usefixtures("live_tables")
def test_live_output_matches_recording(live_engine: sa.Engine) -> None:
    with live_engine.connect() as connection:
        version = _server_version(connection)
        actual = _capture(connection)
    if not _fixture_path(version).exists():
        pytest.fail(
            f"no recorded SHOW CREATE TABLE output for CUBRID {version} "
            f"({_fixture_path(version).name}); record it with "
            "`python -m test.test_show_create_table_server_output <url>`"
        )
    recorded = _load(version)["tables"]
    for table in TABLES:
        expected_ddl = _normalize_ddl(recorded[table]["show_create_table"][1])
        actual_ddl = _normalize_ddl(actual[table]["show_create_table"][1])
        if actual_ddl != expected_ddl:
            diff = "\n".join(
                difflib.unified_diff(
                    expected_ddl.replace(", ", ",\n").splitlines(),
                    actual_ddl.replace(", ", ",\n").splitlines(),
                    "recorded",
                    f"CUBRID {version}",
                    lineterm="",
                )
            )
            pytest.fail(f"SHOW CREATE TABLE {table!r} output drifted:\n{diff}")
        for key in ("db_index", "show_indexes", "show_columns", "db_attribute", "set_domains"):
            assert actual[table][key] == recorded[table][key], f"{key} of {table!r} drifted"


@pytest.mark.integration
@pytest.mark.usefixtures("live_tables")
def test_live_reflection_matches_contract(live_engine: sa.Engine) -> None:
    inspector = sa.inspect(live_engine)
    for table in TABLES:
        assert inspector.get_foreign_keys(table) == EXPECTED_FOREIGN_KEYS[table]
        assert (
            _by_name(inspector.get_unique_constraints(table))
            == (EXPECTED_UNIQUE_CONSTRAINTS[table])
        )


if __name__ == "__main__":  # pragma: no cover - recording entry point
    if len(sys.argv) != 2:
        sys.exit("usage: python -m test.test_show_create_table_server_output <cubrid-url>")
    print(_record(sys.argv[1]))
