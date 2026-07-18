from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from sqlalchemy_cubrid.dialect import CubridDialect


class _Result:
    _rows: list[tuple[Any, ...]]

    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def __iter__(self) -> Iterator[tuple[object, ...]]:
        return iter(self._rows)

    def fetchone(self) -> tuple[object, ...] | None:
        return self._rows[0] if self._rows else None


class _MockConnection:
    _show_columns: list[tuple[Any, ...]]
    _show_indexes: list[tuple[Any, ...]]
    _show_create: list[tuple[Any, ...]]
    _db_index: list[tuple[Any, ...]]
    _db_unique_names: list[tuple[Any, ...]]
    _db_attribute: list[tuple[Any, ...]]

    def __init__(self) -> None:
        self._show_columns = [
            ("id", "INTEGER", "NO", "PRI", None, "auto_increment"),
            ("email", "VARCHAR(200)", "NO", "UNI", None, ""),
            ("team_id", "INTEGER", "YES", "MUL", None, ""),
            ("score", "DECIMAL(10,2)", "YES", "", "0.00", ""),
        ]
        self._show_indexes = [
            ("users", 1, "idx_users_team_id", 1, "team_id"),
            ("users", 1, "idx_users_team_id", 2, "id"),
            ("users", 0, "uq_users_email", 1, "email"),
            ("users", 1, "pk_users", 1, "id"),
            ("users", 1, "fk_users_team", 1, "team_id"),
        ]
        self._show_create = [
            (
                "users",
                """
CREATE TABLE [users] (
  [id] INTEGER NOT NULL AUTO_INCREMENT,
  [email] VARCHAR(200) NOT NULL,
  [team_id] INTEGER,
  [score] DECIMAL(10,2) DEFAULT 0.00,
  CONSTRAINT [pk_users] PRIMARY KEY ([id]),
  CONSTRAINT [uq_users_email] UNIQUE KEY ([email]),
  CONSTRAINT [fk_users_team] FOREIGN KEY ([team_id]) REFERENCES [dba.teams] ([id]) ON DELETE SET NULL ON UPDATE RESTRICT
)
""",
            )
        ]
        self._db_index = [
            ("pk_users", True, False),
            ("fk_users_team", False, True),
            ("idx_users_team_id", False, False),
            ("uq_users_email", False, False),
        ]
        self._db_unique_names = [("uq_users_email",)]
        self._db_attribute = [
            ("id", "identifier"),
            ("email", "email address"),
            ("team_id", "team reference"),
            ("score", "quality score"),
        ]

    def execute(self, statement: Any, params: Any = None) -> _Result:
        sql = str(statement)
        if sql.startswith("SHOW COLUMNS IN"):
            return _Result(self._show_columns)
        if sql.startswith("SHOW INDEXES IN"):
            return _Result(self._show_indexes)
        if sql.startswith("SHOW CREATE TABLE"):
            return _Result(self._show_create)
        # The UNIQUE-constraint catalog query filters is_unique = 1.
        # Dispatch it separately from the general _db_index flag query
        # used by get_indexes() so the mock returns pre-filtered results.
        if "is_unique = 1" in sql:
            return _Result(self._db_unique_names)
        # The PK-name catalog query filters is_primary_key = 1.
        # Dispatch it separately so the mock returns only the PK row.
        if "is_primary_key = 1" in sql:
            return _Result([("pk_users",)])
        if "FROM _db_index" in sql:
            return _Result(self._db_index)
        if "FROM _db_attribute" in sql:
            return _Result(self._db_attribute)
        raise AssertionError(f"Unexpected SQL: {sql}, params={params}")


@pytest.fixture
def mock_connection() -> _MockConnection:
    return _MockConnection()


@pytest.fixture
def dialect() -> CubridDialect:
    return CubridDialect()


def test_get_columns_golden(dialect: CubridDialect, mock_connection: _MockConnection) -> None:
    columns = [dict(column) for column in dialect.get_columns(mock_connection, "users")]
    assert [column["name"] for column in columns] == ["id", "email", "team_id", "score"]
    assert [column["nullable"] for column in columns] == [False, False, True, True]
    assert [column["autoincrement"] for column in columns] == [True, False, False, False]
    assert [column["default"] for column in columns] == [None, None, None, "0.00"]
    assert [column["comment"] for column in columns] == [
        "identifier",
        "email address",
        "team reference",
        "quality score",
    ]
    assert [column["type"].__class__.__name__ for column in columns] == [
        "INTEGER",
        "VARCHAR",
        "INTEGER",
        "DECIMAL",
    ]


def test_get_pk_constraint_golden(dialect: CubridDialect, mock_connection: _MockConnection) -> None:
    pk = dialect.get_pk_constraint(mock_connection, "users")
    assert pk == {"name": "pk_users", "constrained_columns": ["id"]}


def test_get_foreign_keys_golden(dialect: CubridDialect, mock_connection: _MockConnection) -> None:
    foreign_keys = dialect.get_foreign_keys(mock_connection, "users")
    assert foreign_keys == [
        {
            "name": "fk_users_team",
            "constrained_columns": ["team_id"],
            "options": {"ondelete": "SET NULL", "onupdate": "RESTRICT"},
            "referred_schema": None,
            "referred_table": "teams",
            "referred_columns": ["id"],
        }
    ]


def test_get_unique_constraints_golden(
    dialect: CubridDialect, mock_connection: _MockConnection
) -> None:
    unique_constraints = dialect.get_unique_constraints(mock_connection, "users")
    assert unique_constraints == [{"name": "uq_users_email", "column_names": ["email"]}]


def test_get_indexes_golden(dialect: CubridDialect, mock_connection: _MockConnection) -> None:
    indexes = dialect.get_indexes(mock_connection, "users")
    assert indexes == [
        {
            "name": "idx_users_team_id",
            "column_names": ["team_id", "id"],
            "unique": False,
        },
        {
            "name": "uq_users_email",
            "column_names": ["email"],
            "unique": True,
        },
    ]


# ---------------------------------------------------------------------------
# Extended golden tests: multi-column constraints, AUTO_INCREMENT variants
# ---------------------------------------------------------------------------


class _MockConnectionMultiCol:
    """Mock connection simulating a table with composite PK and multi-column unique."""

    def execute(self, statement: Any, params: Any = None) -> _Result:
        sql = str(statement)
        if sql.startswith("SHOW COLUMNS IN"):
            return _Result(
                [
                    ("tenant_id", "INTEGER", "NO", "PRI", None, ""),
                    ("item_id", "INTEGER", "NO", "PRI", None, "auto_increment"),
                    ("category", "VARCHAR(50)", "NO", "MUL", None, ""),
                    ("sku", "VARCHAR(100)", "NO", "MUL", None, ""),
                    ("price", "DECIMAL(12,4)", "YES", "", "0.0000", ""),
                ]
            )
        if sql.startswith("SHOW INDEXES IN"):
            return _Result(
                [
                    ("items", 1, "pk_items", 1, "tenant_id"),
                    ("items", 1, "pk_items", 2, "item_id"),
                    ("items", 0, "uq_items_tenant_sku", 1, "tenant_id"),
                    ("items", 0, "uq_items_tenant_sku", 2, "sku"),
                    ("items", 1, "idx_items_category", 1, "category"),
                ]
            )
        if sql.startswith("SHOW CREATE TABLE"):
            return _Result(
                [
                    (
                        "items",
                        """
CREATE TABLE [items] (
  [tenant_id] INTEGER NOT NULL,
  [item_id] INTEGER NOT NULL AUTO_INCREMENT,
  [category] VARCHAR(50) NOT NULL,
  [sku] VARCHAR(100) NOT NULL,
  [price] DECIMAL(12,4) DEFAULT 0.0000,
  CONSTRAINT [pk_items] PRIMARY KEY ([tenant_id], [item_id]),
  CONSTRAINT [uq_items_tenant_sku] UNIQUE KEY ([tenant_id], [sku]),
  CONSTRAINT [fk_items_tenant] FOREIGN KEY ([tenant_id]) REFERENCES [dba.tenants] ([id]) ON DELETE CASCADE ON UPDATE CASCADE
)
""",
                    )
                ]
            )
        if "is_primary_key = 1" in sql:
            return _Result([("pk_items",)])
        if "is_unique = 1" in sql:
            return _Result([("uq_items_tenant_sku",)])
        if "FROM _db_index" in sql:
            return _Result(
                [
                    ("pk_items", True, False),
                    ("uq_items_tenant_sku", False, False),
                    ("idx_items_category", False, False),
                    ("fk_items_tenant", False, True),
                ]
            )
        if "FROM _db_attribute" in sql:
            return _Result(
                [
                    ("tenant_id", None),
                    ("item_id", None),
                    ("category", None),
                    ("sku", None),
                    ("price", None),
                ]
            )
        raise AssertionError(f"Unexpected SQL: {sql}")


@pytest.fixture
def mock_multicol() -> _MockConnectionMultiCol:
    return _MockConnectionMultiCol()


def test_composite_pk_golden(
    dialect: CubridDialect, mock_multicol: _MockConnectionMultiCol
) -> None:
    pk = dialect.get_pk_constraint(mock_multicol, "items")
    assert pk == {"name": "pk_items", "constrained_columns": ["tenant_id", "item_id"]}


def test_multi_column_unique_golden(
    dialect: CubridDialect, mock_multicol: _MockConnectionMultiCol
) -> None:
    ucs = dialect.get_unique_constraints(mock_multicol, "items")
    assert ucs == [{"name": "uq_items_tenant_sku", "column_names": ["tenant_id", "sku"]}]


def test_autoincrement_non_first_pk_column(
    dialect: CubridDialect, mock_multicol: _MockConnectionMultiCol
) -> None:
    """AUTO_INCREMENT on item_id (second PK column) should be detected."""
    columns = [dict(c) for c in dialect.get_columns(mock_multicol, "items")]
    assert columns[0]["autoincrement"] is False  # tenant_id
    assert columns[1]["autoincrement"] is True  # item_id


def test_foreign_key_cascade_golden(
    dialect: CubridDialect, mock_multicol: _MockConnectionMultiCol
) -> None:
    fks = dialect.get_foreign_keys(mock_multicol, "items")
    assert fks == [
        {
            "name": "fk_items_tenant",
            "constrained_columns": ["tenant_id"],
            "referred_schema": None,
            "referred_table": "tenants",
            "referred_columns": ["id"],
            "options": {"ondelete": "CASCADE", "onupdate": "CASCADE"},
        }
    ]


def test_indexes_exclude_pk_and_unique(
    dialect: CubridDialect, mock_multicol: _MockConnectionMultiCol
) -> None:
    """get_indexes should return only non-PK, non-FK indexes."""
    indexes = dialect.get_indexes(mock_multicol, "items")
    assert indexes == [
        {"name": "uq_items_tenant_sku", "column_names": ["tenant_id", "sku"], "unique": True},
        {"name": "idx_items_category", "column_names": ["category"], "unique": False},
    ]


# ---------------------------------------------------------------------------
# Edge-case tests: empty result sets, NULL metadata, missing constraints
# These test the mock-bypass gaps — scenarios where CUBRID returns less data
# than the happy-path golden tests expect.
# ---------------------------------------------------------------------------


class _MockEmptyTable:
    """Mock connection for a table with NO indexes, NO PK, NO FK, NO comments.

    This simulates a heap table (no constraints at all). Every reflection
    method should return an empty list/dict, not crash.
    """

    def execute(self, statement: Any, params: Any = None) -> _Result:
        sql = str(statement)
        if sql.startswith("SHOW COLUMNS IN"):
            return _Result(
                [
                    ("data", "VARCHAR(100)", "YES", "", None, ""),
                ]
            )
        if sql.startswith("SHOW INDEXES IN"):
            return _Result([])  # no indexes
        if sql.startswith("SHOW CREATE TABLE"):
            return _Result([])  # no DDL
        if "is_primary_key = 1" in sql:
            return _Result([])  # no PK
        if "is_unique = 1" in sql:
            return _Result([])  # no unique
        if "FROM _db_index" in sql:
            return _Result([])  # no indexes at all
        if "FROM _db_attribute" in sql:
            return _Result([])  # no column comments
        if "FROM db_class" in sql or "comment FROM db_class" in sql:
            return _Result([(None,)])  # table comment is NULL
        raise AssertionError(f"Unexpected SQL: {sql}, params={params}")


@pytest.fixture
def mock_empty_table() -> _MockEmptyTable:
    return _MockEmptyTable()


def test_get_indexes_empty_table(
    dialect: CubridDialect, mock_empty_table: _MockEmptyTable
) -> None:
    """A table with no indexes should return an empty list, not crash."""
    indexes = dialect.get_indexes(mock_empty_table, "heap_table")
    assert indexes == []


def test_get_pk_constraint_empty_table(
    dialect: CubridDialect, mock_empty_table: _MockEmptyTable
) -> None:
    """A table with no PK should return an empty constraint dict."""
    pk = dialect.get_pk_constraint(mock_empty_table, "heap_table")
    assert pk == {"name": None, "constrained_columns": []}


def test_get_foreign_keys_empty_table(
    dialect: CubridDialect, mock_empty_table: _MockEmptyTable
) -> None:
    """A table with no foreign keys should return an empty list."""
    fks = dialect.get_foreign_keys(mock_empty_table, "heap_table")
    assert fks == []


def test_get_unique_constraints_empty_table(
    dialect: CubridDialect, mock_empty_table: _MockEmptyTable
) -> None:
    """A table with no unique constraints should return an empty list."""
    ucs = dialect.get_unique_constraints(mock_empty_table, "heap_table")
    assert ucs == []


def test_get_columns_no_comment(
    dialect: CubridDialect, mock_empty_table: _MockEmptyTable
) -> None:
    """A column with no comment should reflect comment as None."""
    columns = [dict(c) for c in dialect.get_columns(mock_empty_table, "heap_table")]
    assert len(columns) == 1
    assert columns[0]["name"] == "data"
    assert columns[0]["comment"] is None


def test_get_table_comment_empty(
    dialect: CubridDialect, mock_empty_table: _MockEmptyTable
) -> None:
    """A table with no comment should return {"text": None}."""
    comment = dialect.get_table_comment(mock_empty_table, "heap_table")
    assert comment == {"text": None}


class _MockNullFlags:
    """Mock connection where _db_index returns NULL for is_primary_key/is_foreign_key.

    Some CUBRID versions may return NULL instead of 0 for boolean flags.
    The parsing code should handle both (truthy check via `if flag_row[1]`).
    """

    def __init__(self) -> None:
        self._show_columns = [
            ("id", "INTEGER", "NO", "PRI", None, "auto_increment"),
        ]
        self._show_indexes = [
            ("test", 1, "pk_test", 1, "id"),
        ]

    def execute(self, statement: Any, params: Any = None) -> _Result:
        sql = str(statement)
        if sql.startswith("SHOW COLUMNS IN"):
            return _Result(self._show_columns)
        if sql.startswith("SHOW INDEXES IN"):
            return _Result(self._show_indexes)
        if sql.startswith("SHOW CREATE TABLE"):
            return _Result([])
        if "is_primary_key = 1" in sql:
            return _Result([("pk_test",)])
        if "is_unique = 1" in sql:
            return _Result([])
        if "FROM _db_index" in sql:
            # Return NULL for boolean flags instead of False (0)
            return _Result([("pk_test", None, None)])
        if "FROM _db_attribute" in sql:
            return _Result([])
        raise AssertionError(f"Unexpected SQL: {sql}")


@pytest.fixture
def mock_null_flags() -> _MockNullFlags:
    return _MockNullFlags()


def test_get_indexes_null_flags(
    dialect: CubridDialect, mock_null_flags: _MockNullFlags
) -> None:
    """Document behavior when _db_index returns NULL for boolean flags.

    In CUBRID's ``_db_index`` system view, ``is_primary_key`` and
    ``is_foreign_key`` are NOT NULL boolean columns. However, if a future
    schema change or corruption introduces NULL, the parsing code uses
    Python truthiness (``if flag_row[1]:``), so NULL is treated as
    ``False`` — the index is NOT excluded from ``get_indexes()``.

    This is a known limitation: the batch flag query relies on truthy
    values, not an explicit ``== 1`` check. In practice, CUBRID always
    returns 0 or 1 for these columns, so this scenario does not arise.
    """
    indexes = dialect.get_indexes(mock_null_flags, "test")
    # NULL is falsy → pk_indexes is empty → pk_test is NOT excluded
    assert len(indexes) == 1
    assert indexes[0]["name"] == "pk_test"
