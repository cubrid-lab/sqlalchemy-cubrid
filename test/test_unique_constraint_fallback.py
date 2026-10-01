# test/test_unique_constraint_fallback.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""When ``get_unique_constraints`` falls back to ``SHOW CREATE TABLE`` (#610).

The ``db_index`` catalog lists a table's indexes exactly when ``db_class``
lists the table, for its owner and for a user granted ``SELECT`` on it (checked
as DBA and as a non-DBA user on CUBRID 10.2, 11.0, 11.2 and 11.4). So once the
catalog shows any index of the table (its primary key, a foreign-key index,
an ordinary index) and none of them is a unique one, the table has no unique
constraint and parsing ``SHOW CREATE TABLE`` cannot find one: the request is
skipped. The fallback is kept when the catalog lists no index of the table at
all, which it cannot tell apart from a catalog that does not show them.

The stub below answers the catalog queries from per-index flags the way the
server does, so the tests describe the requests and results, not the SQL text.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import NoSuchTableError

from sqlalchemy_cubrid.dialect import CubridDialect

FK = ("fk_t_parent", "NO", "NO", "YES")
PLAIN_INDEX = ("ix_t_v", "NO", "NO", "NO")
UNIQUE = ("uq_t_code", "YES", "NO", "NO")
# CUBRID reports a primary key as unique too.
PK = ("pk_t_id", "YES", "YES", "NO")


class _Rows(list[Any]):
    def first(self) -> Any:
        return self[0] if self else None


class _Connection:
    """Answers the reflection queries for one table from index flags
    ``(index_name, is_unique, is_primary_key, is_foreign_key)``."""

    def __init__(
        self,
        indexes: tuple[tuple[str, str, str, str], ...],
        *,
        class_type: str | None = "CLASS",
        ddl: str = "CREATE TABLE [t] ([id] INTEGER)",
        show_indexes: tuple[tuple[Any, ...], ...] = (),
        fail_catalog: bool = False,
    ) -> None:
        self.indexes = indexes
        self.class_type = class_type
        self.ddl = ddl
        self.show_indexes = show_indexes
        self.fail_catalog = fail_catalog
        self.statements: list[str] = []

    def execute(self, statement: Any, params: Any = None) -> _Rows:
        sql = " ".join(str(statement).split())
        self.statements.append(sql)
        if "FROM db_class" in sql:
            return _Rows([] if self.class_type is None else [(self.class_type, "DBA")])
        if "FROM db_index" in sql:
            if self.fail_catalog:
                raise RuntimeError("db_index query failed")
            if "is_unique = 'YES'" in sql:
                # A query that filters unique, non-PK, non-FK indexes itself.
                return _Rows(
                    [(name,) for name, *flags in self.indexes if flags == ["YES", "NO", "NO"]]
                )
            return _Rows([index for index in self.indexes])
        if sql.startswith("SHOW INDEXES IN"):
            return _Rows(self.show_indexes)
        if sql.startswith("SHOW CREATE TABLE"):
            return _Rows([("t", self.ddl)])
        raise AssertionError(f"Unexpected SQL: {sql!r}")

    def count(self, prefix: str) -> int:
        return sum(1 for sql in self.statements if sql.startswith(prefix))


@pytest.fixture
def dialect() -> CubridDialect:
    return CubridDialect()


@pytest.mark.parametrize(
    "indexes",
    [(PK,), (FK,), (PLAIN_INDEX,), (PK, FK, PLAIN_INDEX)],
    ids=["pk", "fk_index", "plain_index", "pk_fk_plain"],
)
def test_verified_empty_catalog_skips_show_create_table(
    dialect: CubridDialect, indexes: tuple[tuple[str, str, str, str], ...]
) -> None:
    connection = _Connection(
        indexes,
        # Would be wrongly reported if the DDL were still parsed.
        ddl="CREATE TABLE [t] ([id] INTEGER, CONSTRAINT [stale] UNIQUE KEY ([id]))",
    )
    assert dialect.get_unique_constraints(connection, "t") == []
    assert connection.count("SHOW CREATE TABLE") == 0
    assert connection.count("SHOW INDEXES") == 0
    # db_class lookup + one catalog query.
    assert len(connection.statements) == 2


def test_table_without_any_index_keeps_ddl_fallback(dialect: CubridDialect) -> None:
    connection = _Connection(
        (),
        ddl="CREATE TABLE [t] ([code] INTEGER, CONSTRAINT [uq_t_code] UNIQUE KEY ([code]))",
    )
    assert dialect.get_unique_constraints(connection, "t") == [
        {"name": "uq_t_code", "column_names": ["code"], "duplicates_index": "uq_t_code"}
    ]
    assert connection.count("SHOW CREATE TABLE") == 1


def test_table_without_any_index_and_no_unique_in_ddl(dialect: CubridDialect) -> None:
    connection = _Connection(())
    assert dialect.get_unique_constraints(connection, "t") == []
    assert connection.count("SHOW CREATE TABLE") == 1


def test_unique_index_uses_catalog_and_filters_pk_and_fk(dialect: CubridDialect) -> None:
    connection = _Connection(
        (PK, FK, UNIQUE),
        show_indexes=(
            ("t", 0, "pk_t_id", 1, "id"),
            ("t", 1, "fk_t_parent", 1, "parent_id"),
            ("t", 0, "uq_t_code", 1, "code"),
            ("t", 0, "uq_t_code", 2, "region"),
        ),
    )
    assert dialect.get_unique_constraints(connection, "t") == [
        {"name": "uq_t_code", "column_names": ["code", "region"], "duplicates_index": "uq_t_code"}
    ]
    assert connection.count("SHOW CREATE TABLE") == 0
    assert connection.count("SHOW INDEXES") == 1
    assert len(connection.statements) == 3


def test_catalog_failure_propagates(dialect: CubridDialect) -> None:
    connection = _Connection((PK,), fail_catalog=True)
    with pytest.raises(RuntimeError, match="db_index query failed"):
        dialect.get_unique_constraints(connection, "t")
    assert connection.count("SHOW CREATE TABLE") == 0


def test_view_runs_only_the_class_lookup(dialect: CubridDialect) -> None:
    connection = _Connection((), class_type="VCLASS")
    assert dialect.get_unique_constraints(connection, "t") == []
    assert len(connection.statements) == 1


def test_missing_table_raises(dialect: CubridDialect) -> None:
    connection = _Connection((), class_type=None)
    with pytest.raises(NoSuchTableError):
        dialect.get_unique_constraints(connection, "t")
    assert len(connection.statements) == 1


# ---------------------------------------------------------------------------
# Live: requests issued by get_unique_constraints on the server under test
# ---------------------------------------------------------------------------

_LIVE_SETUP = (
    "CREATE TABLE ucf_pk (id INT PRIMARY KEY, v INT)",
    "CREATE TABLE ucf_fk (id INT PRIMARY KEY, pid INT,"
    " CONSTRAINT fk_ucf_fk_pid FOREIGN KEY (pid) REFERENCES ucf_pk (id))",
    "CREATE TABLE ucf_noidx (v INT)",
    "CREATE TABLE ucf_uq (id INT PRIMARY KEY, code INT, CONSTRAINT uq_ucf_code UNIQUE (code))",
    "CREATE TABLE ucf_uidx (id INT PRIMARY KEY, code INT)",
    "CREATE UNIQUE INDEX ux_ucf_code ON ucf_uidx (code)",
    "CREATE VIEW ucf_v AS SELECT id FROM ucf_pk",
)
_LIVE_DROP = ("DROP VIEW IF EXISTS ucf_v",) + tuple(
    f"DROP TABLE IF EXISTS {table}"
    for table in ("ucf_fk", "ucf_uidx", "ucf_uq", "ucf_noidx", "ucf_pk")
)


@pytest.fixture
def live_engine():  # noqa: ANN201
    engine = sa.create_engine(os.environ["CUBRID_TEST_URL"])
    with engine.begin() as connection:
        for statement in _LIVE_DROP + _LIVE_SETUP:
            connection.exec_driver_sql(statement)
    yield engine
    with engine.begin() as connection:
        for statement in _LIVE_DROP:
            connection.exec_driver_sql(statement)
    engine.dispose()


@pytest.mark.integration
@pytest.mark.parametrize(
    ("table", "expected", "requests"),
    [
        # A table whose catalog lists an index (PK / FK) but no unique one:
        # db_class + db_index only (was 3 with SHOW CREATE TABLE).
        ("ucf_pk", [], 2),
        ("ucf_fk", [], 2),
        # No index at all: the SHOW CREATE TABLE fallback is kept.
        ("ucf_noidx", [], 3),
        # Unique constraint / unique index: db_class + db_index + SHOW INDEXES.
        ("ucf_uq", [{"name": "uq_ucf_code", "column_names": ["code"]}], 3),
        ("ucf_uidx", [{"name": "ux_ucf_code", "column_names": ["code"]}], 3),
        ("ucf_v", [], 1),
    ],
)
def test_live_requests(live_engine: Any, table: str, expected: list[Any], requests: int) -> None:
    statements: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001, ANN202
        statements.append(statement)

    with live_engine.connect() as connection:
        sa.event.listen(connection, "before_cursor_execute", record)
        result = sa.inspect(connection).get_unique_constraints(table)
    for constraint in expected:
        constraint["duplicates_index"] = constraint["name"]
    assert result == expected
    assert len(statements) == requests, statements
    assert any(s.startswith("SHOW CREATE TABLE") for s in statements) is (table == "ucf_noidx")


@pytest.mark.integration
def test_live_missing_table(live_engine: Any) -> None:
    with live_engine.connect() as connection:
        with pytest.raises(NoSuchTableError):
            sa.inspect(connection).get_unique_constraints("ucf_missing")
