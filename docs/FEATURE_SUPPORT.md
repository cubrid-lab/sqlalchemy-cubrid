# Feature Support Comparison

A comprehensive comparison of **sqlalchemy-cubrid** capabilities against the mature SQLAlchemy dialects for MySQL, PostgreSQL, and SQLite.

Use this document to understand what the CUBRID dialect supports, what it doesn't, and how it compares to other database backends when choosing a dialect for your project.

---

## Table of Contents

- [Legend](#legend)
- [Summary](#summary)
- [DML — Data Manipulation Language](#dml--data-manipulation-language)
- [DDL — Data Definition Language](#ddl--data-definition-language)
- [Query Features](#query-features)
- [Type System](#type-system)
- [Schema Reflection](#schema-reflection)
- [Transactions & Connections](#transactions--connections)
- [Dialect Engine Features](#dialect-engine-features)
- [CUBRID-Specific Features](#cubrid-specific-features)
- [CUBRID-Specific DML Constructs](#cubrid-specific-dml-constructs)
- [Index Hints](#index-hints)
- [Known Limitations & Roadmap](#known-limitations--roadmap)

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Fully supported |
| ⚠️ | Partial or emulated support |
| ❌ | Not supported |

---

## Summary

High-level overview by feature category.

| Category | CUBRID | MySQL | PostgreSQL | SQLite |
|----------|--------|-------|------------|--------|
| DML | ✅ | ✅ | ✅ | ⚠️ |
| DDL | ✅ | ✅ | ✅ | ⚠️ |
| Query features | ✅ | ✅ | ✅ | ✅ |
| Type system | ⚠️ | ✅ | ✅ | ⚠️ |
| Schema reflection | ✅ | ✅ | ✅ | ⚠️ |
| Transactions | ✅ | ✅ | ✅ | ⚠️ |
| Engine features | ⚠️ | ✅ | ✅ | ⚠️ |

---

## DML — Data Manipulation Language

| Feature | CUBRID | MySQL | PostgreSQL | SQLite |
|---------|--------|-------|------------|--------|
| INSERT … RETURNING | ❌ | ❌ | ✅ | ✅ |
| UPDATE … RETURNING | ❌ | ❌ | ✅ | ✅ |
| DELETE … RETURNING | ❌ | ❌ | ✅ | ✅ |
| INSERT … DEFAULT VALUES | ✅ | ❌ | ✅ | ✅ |
| Empty INSERT | ✅ | ⚠️ | ✅ | ✅ |
| Multi-row INSERT | ✅ | ✅ | ✅ | ✅ |
| INSERT FROM SELECT | ✅ | ✅ | ✅ | ✅ |
| ON DUPLICATE KEY UPDATE | ✅ | ✅ | ❌ | ❌ |
| MERGE statement | ✅ | ❌ | ❌ | ❌ |
| REPLACE INTO | ✅ | ✅ | ❌ | ✅ |
| FOR UPDATE (row locking) | ✅ | ✅ | ✅ | ❌ |
| UPDATE with LIMIT | ✅ | ✅ | ❌ | ❌ |
| TRUNCATE TABLE | ✅ | ✅ | ✅ | ❌ |
| IS DISTINCT FROM | ❌ | ❌ | ✅ | ❌ |
| Postfetch LASTROWID | ✅ | ✅ | ❌ | ✅ |

### Notes

- **RETURNING**: CUBRID has no `RETURNING` clause. Auto-generated keys cannot be fetched in the same round-trip as the INSERT, so the dialect relies on `postfetch_lastrowid = True` instead (`get_last_insert_id()` / SQL fallback for the C driver; `cursor.lastrowid` for pycubrid).
- **DEFAULT VALUES**: CUBRID supports `INSERT INTO t DEFAULT VALUES`. The dialect sets `supports_default_values = True`.
- **ON DUPLICATE KEY UPDATE**: CUBRID supports `INSERT … ON DUPLICATE KEY UPDATE` with `VALUES()` references (identical to MySQL pre-8.0 syntax). Use `sqlalchemy_cubrid.insert(table).on_duplicate_key_update(col=value)`. See [CUBRID-Specific DML Constructs](#cubrid-specific-dml-constructs) for usage examples.
- **MERGE**: CUBRID supports the full SQL MERGE statement. Use `sqlalchemy_cubrid.dml.merge(target)` with `.using()`, `.on()`, `.when_matched_then_update()`, and `.when_not_matched_then_insert()`. See [CUBRID-Specific DML Constructs](#cubrid-specific-dml-constructs).
- **FOR UPDATE**: CUBRID supports `SELECT … FOR UPDATE [OF col1, col2]`. NOWAIT and SKIP LOCKED are not supported.
- **UPDATE with LIMIT**: CUBRID and MySQL both support `UPDATE … LIMIT n`. PostgreSQL and SQLite do not.
- **Multi-table UPDATE**: SQLAlchemy's multi-table UPDATE pattern compiles to `UPDATE t1, t2 SET ... WHERE ...`, which matches the MySQL-style syntax accepted by CUBRID. The dialect intentionally keeps `update_from_clause()` disabled because no extra `FROM` clause is required.
- **TRUNCATE**: CUBRID supports `TRUNCATE TABLE`. The dialect includes `TRUNCATE` in autocommit detection.
- **IS DISTINCT FROM**: Not a CUBRID SQL operator. SQLAlchemy may emulate it with `CASE` expressions on dialects that lack native support.

---

## DDL — Data Definition Language

| Feature | CUBRID | MySQL | PostgreSQL | SQLite |
|---------|--------|-------|------------|--------|
| ALTER TABLE | ✅ | ✅ | ✅ | ⚠️ |
| Table comments | ✅ | ✅ | ✅ | ❌ |
| Column comments | ✅ | ✅ | ✅ | ❌ |
| CREATE … IF NOT EXISTS | ✅ | ✅ | ✅ | ✅ |
| DROP … IF EXISTS | ✅ | ✅ | ✅ | ✅ |
| Temporary tables | ❌ | ✅ | ✅ | ✅ |
| Multiple schemas | ❌ | ✅ | ✅ | ⚠️ |

### Notes

- **ALTER TABLE**: CUBRID supports standard `ALTER TABLE` for adding/dropping columns and constraints. SQLite has limited ALTER support (add column only; no drop/rename column before 3.35).
- **Comments**: CUBRID supports inline `COMMENT` syntax for both tables (e.g., `CREATE TABLE t (...) COMMENT = 'text'`) and columns (e.g., `col TYPE COMMENT 'text'`). The dialect implements `SetTableComment`, `DropTableComment`, and `SetColumnComment` DDL constructs. Comment reflection is supported via `get_table_comment()` and column comments in `get_columns()`.
- **IF NOT EXISTS / IF EXISTS**: CUBRID supports `CREATE TABLE IF NOT EXISTS` and `DROP TABLE IF EXISTS`. The base SA compiler handles these natively.
- **Temporary tables**: CUBRID does not support `CREATE TEMPORARY TABLE` or session-scoped tables.
- **Multiple schemas**: CUBRID operates in a single-schema model. MySQL uses databases as schemas. SQLite can attach databases but does not have true schema support.

---

## Query Features

| Feature | CUBRID | MySQL | PostgreSQL | SQLite |
|---------|--------|-------|------------|--------|
| Common Table Expressions (WITH) | ✅ | ✅ | ✅ | ✅ |
| Recursive CTEs (WITH RECURSIVE) | ✅ | ✅ | ✅ | ✅ |
| CTEs on DML | ❌ | ❌ | ✅ | ❌ |
| Window functions | ✅ | ✅ | ✅ | ✅ |
| NULLS FIRST / NULLS LAST | ✅ | ❌ | ✅ | ✅ |
| GROUP_CONCAT | ✅ | ✅ | ❌ | ✅ |
| INTERSECT | ✅ | ✅ | ✅ | ✅ |
| EXCEPT | ✅ | ✅ | ✅ | ✅ |
| DISTINCT | ✅ | ✅ | ✅ | ✅ |
| LIMIT / OFFSET | ✅ | ✅ | ✅ | ✅ |
| Lateral joins | ❌ | ❌ | ✅ | ❌ |
| Full-text search (MATCH … AGAINST) | ❌ | ✅ | ✅ | ✅ |
| Query trace / EXPLAIN | ⚠️ | ✅ | ✅ | ✅ |
### Notes

- **CTEs**: CUBRID 11.0+ supports `WITH` clauses for read queries. Writable CTEs (`WITH … INSERT/UPDATE/DELETE`) are not supported.
- **Recursive CTEs**: CUBRID 11.x+ supports `WITH RECURSIVE` for recursive queries. SQLAlchemy's base compiler generates correct syntax — no dialect-specific compilation needed.
- **Window functions**: CUBRID supports `ROW_NUMBER()`, `RANK()`, `DENSE_RANK()`, and other window functions with `OVER(PARTITION BY … ORDER BY …)`. The SA base compiler handles these natively.
- **NULLS FIRST / NULLS LAST**: CUBRID supports `ORDER BY col ASC NULLS FIRST` and `ORDER BY col DESC NULLS LAST`. The SA base compiler handles these natively.
- **GROUP_CONCAT**: CUBRID supports `GROUP_CONCAT([DISTINCT] expr [ORDER BY …] [SEPARATOR '…'])`. Use `sa.func.group_concat(column)`.
- **LIMIT / OFFSET**: CUBRID uses MySQL-style `LIMIT [offset,] count` syntax. When only an offset is given, the dialect emits `LIMIT offset, 1073741823` (max int) as a workaround.
- **Join variants**: INNER JOIN and LEFT OUTER JOIN compile normally. FULL OUTER JOIN and `LATERAL` are rejected during compilation because CUBRID does not support them.
- **Lateral joins**: CUBRID does not support `LATERAL` subqueries. The `LATERAL` keyword causes a syntax error.
- **Full-text search**: CUBRID does not support `MATCH … AGAINST` syntax or full-text indexes.
- **Query trace**: CUBRID uses `SET TRACE ON` / `SHOW TRACE` instead of standard `EXPLAIN`. The dialect provides `trace_query()` as a utility function — see [CUBRID-Specific DML Constructs](#cubrid-specific-dml-constructs).

---

## Type System

### Standard SQL Types

| Type | CUBRID | MySQL | PostgreSQL | SQLite |
|------|--------|-------|------------|--------|
| SMALLINT | ✅ | ✅ | ✅ | ✅ |
| INTEGER | ✅ | ✅ | ✅ | ✅ |
| BIGINT | ✅ | ✅ | ✅ | ✅ |
| NUMERIC / DECIMAL | ✅ | ✅ | ✅ | ✅ |
| FLOAT | ✅ | ✅ | ✅ | ✅ |
| DOUBLE / REAL | ✅ | ✅ | ✅ | ✅ |
| BOOLEAN | ⚠️ | ⚠️ | ✅ | ⚠️ |
| DATE | ✅ | ✅ | ✅ | ✅ |
| TIME | ✅ | ✅ | ✅ | ✅ |
| DATETIME | ✅ | ✅ | ✅ | ✅ |
| TIMESTAMP | ✅ | ✅ | ✅ | ✅ |
| CHAR | ✅ | ✅ | ✅ | ✅ |
| VARCHAR | ✅ | ✅ | ✅ | ✅ |
| NCHAR / NVARCHAR | ✅ | ⚠️ | ❌ | ❌ |
| TEXT | ✅ | ✅ | ✅ | ✅ |
| BLOB | ✅ | ✅ | ✅ | ✅ |
| CLOB | ✅ | ✅ | ✅ | ✅ |
| BIT / BIT VARYING | ✅ | ✅ | ✅ | ❌ |

### Extended Types

| Type | CUBRID | MySQL | PostgreSQL | SQLite |
|------|--------|-------|------------|--------|
| ENUM | ❌ | ✅ | ✅ | ❌ |
| JSON | ✅ | ✅ | ✅ | ⚠️ |
| ARRAY | ❌ | ❌ | ✅ | ❌ |
| UUID | ❌ | ❌ | ✅ | ❌ |
| INTERVAL | ❌ | ❌ | ✅ | ❌ |
| HSTORE | ❌ | ❌ | ✅ | ❌ |

### Notes

- **BOOLEAN**: CUBRID maps `BOOLEAN` to `SMALLINT`. MySQL maps it to `TINYINT(1)`. SQLite stores booleans as integers. Only PostgreSQL has a native `BOOLEAN` type.
- **NCHAR / NVARCHAR**: CUBRID has first-class national character types. MySQL handles national characters via column charset. PostgreSQL and SQLite have no separate national character types.
- **JSON**: CUBRID 10.2+ has native JSON support (RFC 7159) with 25+ JSON functions. The dialect supports `JSON` type, `col["key"]` path expressions via `JSON_EXTRACT`, and typed access (`as_string()`, `as_integer()`, `as_float()`). MySQL (5.7+) and PostgreSQL also have native JSON support. SQLite has JSON functions but no dedicated column type.
- **ARRAY**: CUBRID uses collection types (`SET`, `MULTISET`, `SEQUENCE`) which serve a similar purpose but are not SQL-standard arrays. PostgreSQL has native `ARRAY[]` support.
- **CLOB**: CUBRID and MySQL have explicit `CLOB` types. PostgreSQL uses `TEXT` (unlimited length). SQLite stores all text as `TEXT`.

---

## Schema Reflection

| Feature | CUBRID | MySQL | PostgreSQL | SQLite |
|---------|--------|-------|------------|--------|
| Table names | ✅ | ✅ | ✅ | ✅ |
| Column information | ✅ | ✅ | ✅ | ✅ |
| Primary keys | ✅ | ✅ | ✅ | ✅ |
| Foreign keys | ✅ | ✅ | ✅ | ✅ |
| Indexes | ✅ | ✅ | ✅ | ✅ |
| Unique constraints | ✅ | ✅ | ✅ | ✅ |
| Check constraints | ❌ | ✅ | ✅ | ❌ |
| Table comments | ✅ | ✅ | ✅ | ❌ |
| Column comments | ✅ | ✅ | ✅ | ❌ |
| View names | ✅ | ✅ | ✅ | ✅ |
| View definitions | ✅ | ✅ | ✅ | ✅ |
| Schema names | ❌ | ✅ | ✅ | ❌ |
| Sequences | ❌ | ❌ | ✅ | ❌ |
| `has_table` | ✅ | ✅ | ✅ | ✅ |
| `has_index` | ✅ | ❌ | ✅ | ✅ |
| `has_sequence` | ❌ | ❌ | ✅ | ❌ |

### Notes

- **Check constraints**: CUBRID parses CHECK constraint syntax but does not enforce it at runtime. To avoid reflecting misleading metadata, the dialect intentionally returns an empty list from `get_check_constraints()`.
- **Table comments**: Reflected via `get_table_comment()` querying the `db_class.comment` system catalog column.
- **Column comments**: Reflected via `get_columns()` querying the `_db_attribute.comment` system catalog column. Returned in the `"comment"` key of each column dict.
- **has_index**: The CUBRID dialect implements `has_index()` by querying `_db_index`. The MySQL SA dialect does not provide a dedicated `has_index()` method.
- **Reflection source**: Reflection is split across multiple sources: `SHOW COLUMNS IN` + `_db_attribute` for columns/comments, `SHOW COLUMNS IN` + optional `db_constraint` lookup for PK names, `SHOW CREATE TABLE` parsing for foreign keys and unique constraints, `SHOW INDEXES IN` + `_db_index` for indexes, `SHOW CREATE VIEW` for view definitions, and `db_class` for table/view names and table comments.

---

## Transactions & Connections

| Feature | CUBRID | MySQL | PostgreSQL | SQLite |
|---------|--------|-------|------------|--------|
| Isolation level management | ✅ | ✅ | ✅ | ✅ |
| Savepoints | ✅ | ✅ | ✅ | ✅ |
| Two-phase commit | ❌ | ✅ | ✅ | ❌ |
| Server-side cursors | ❌ | ✅ | ✅ | ❌ |
| Autocommit detection | ✅ | ✅ | ✅ | ✅ |
| Connection-level encoding | ❌ | ✅ | ✅ | ❌ |

### CUBRID Isolation Levels

CUBRID supports six isolation levels — more than the SQL standard's four:

| Level | Description |
|-------|-------------|
| `SERIALIZABLE` | Full serialization |
| `REPEATABLE READ CLASS, REPEATABLE READ INSTANCES` | Repeatable read for both schema and data |
| `REPEATABLE READ CLASS, READ COMMITTED INSTANCES` | Repeatable read for schema, read committed for data |
| `REPEATABLE READ CLASS, READ UNCOMMITTED INSTANCES` | Repeatable read for schema, read uncommitted for data |
| `READ COMMITTED CLASS, READ COMMITTED INSTANCES` | Read committed for both |
| `READ COMMITTED CLASS, READ UNCOMMITTED INSTANCES` | Read committed for schema, read uncommitted for data |

### Notes

- **Two-phase commit**: CUBRID does not support distributed transactions via `XA`.
- **Server-side cursors**: The CUBRID Python driver does not expose server-side cursor functionality.
- **Autocommit detection**: The CUBRID execution context uses a regex pattern matching `SET`, `ALTER`, `CREATE`, `DROP`, `GRANT`, `REVOKE`, and `TRUNCATE` statements to determine when to enable autocommit.
- **Savepoints**: CUBRID supports `SAVEPOINT` and `ROLLBACK TO SAVEPOINT`. `RELEASE SAVEPOINT` is not supported — the dialect implements `do_release_savepoint()` as a no-op.

---

## Dialect Engine Features

| Feature | CUBRID | MySQL | PostgreSQL | SQLite |
|---------|--------|-------|------------|--------|
| Statement caching | ✅ | ✅ | ✅ | ✅ |
| Native enum | ❌ | ✅ | ✅ | ❌ |
| Native boolean | ❌ | ❌ | ✅ | ❌ |
| Native decimal | ✅ | ✅ | ✅ | ❌ |
| Sequences | ❌ | ❌ | ✅ | ❌ |
| ON UPDATE CASCADE | ✅ | ✅ | ✅ | ✅ |
| ON DELETE CASCADE | ✅ | ✅ | ✅ | ✅ |
| Self-referential FKs | ✅ | ✅ | ✅ | ✅ |
| Independent connections | ✅ | ✅ | ✅ | ✅ |
| Unicode DDL | ✅ | ✅ | ✅ | ✅ |
| Name normalization | ✅ | ❌ | ✅ | ❌ |

### Notes

- **Statement caching**: `supports_statement_cache = True`. The dialect is fully compatible with SQLAlchemy 2.0's compiled cache.
- **Name normalization**: CUBRID folds unquoted identifiers to lowercase. The dialect normalizes identifiers to match Python-side expectations (`requires_name_normalize = True`).
- **Max identifier length**: CUBRID allows identifiers up to 254 characters — significantly longer than MySQL (64) or PostgreSQL (63).

---

## CUBRID-Specific Features

These types and capabilities are unique to the CUBRID dialect and have no direct equivalent in MySQL, PostgreSQL, or SQLite.

| Feature | Description |
|---------|-------------|
| `MONETARY` type | Fixed-point currency type with locale-aware formatting |
| `STRING` type | Alias for `VARCHAR(1,073,741,823)` — maximum-length variable string |
| `OBJECT` type | OID reference type pointing to another row by object identifier |
| `SET` collection | Unordered collection of unique elements |
| `MULTISET` collection | Unordered collection that allows duplicates |
| `SEQUENCE` collection | Ordered collection that allows duplicates |
| 6 isolation levels | Separate class-level and instance-level isolation granularity |
| 254-char identifiers | Longer than MySQL (64) and PostgreSQL (63) |

### Collection Types

CUBRID's collection types (`SET`, `MULTISET`, `SEQUENCE`) are typed containers that hold elements of a specified data type. They are declared in DDL as:

```
SET(INTEGER)
MULTISET(VARCHAR)
SEQUENCE(DOUBLE)
```

These are fully supported by the dialect's type compiler and can be used in `Column` definitions.

---

## CUBRID-Specific DML Constructs

The dialect provides custom SQLAlchemy constructs for CUBRID-specific DML features that go beyond the standard SA API.

### ON DUPLICATE KEY UPDATE

CUBRID supports `INSERT … ON DUPLICATE KEY UPDATE` with `VALUES()` references (identical to MySQL pre-8.0 syntax).

```python
from sqlalchemy_cubrid import insert

stmt = insert(users).values(id=1, name="alice", email="alice@example.com")
stmt = stmt.on_duplicate_key_update(name="updated_alice")
# INSERT INTO users (id, name, email) VALUES (1, 'alice', 'alice@example.com')
# ON DUPLICATE KEY UPDATE name = 'updated_alice'

# Reference the inserted value:
stmt = insert(users).values(id=1, name="alice", email="alice@example.com")
stmt = stmt.on_duplicate_key_update(name=stmt.inserted.name)
# ON DUPLICATE KEY UPDATE name = VALUES(name)
```

**Accepted argument forms:**
- Keyword arguments: `stmt.on_duplicate_key_update(name="value")`
- Dictionary: `stmt.on_duplicate_key_update({"name": "value"})`
- List of tuples (ordered): `stmt.on_duplicate_key_update([("name", "value"), ("email", "value")])`

### MERGE Statement

CUBRID supports the SQL `MERGE` statement for conditional INSERT/UPDATE in a single operation.

```python
from sqlalchemy_cubrid.dml import merge

stmt = (
    merge(target_table)
    .using(source_table)
    .on(target_table.c.id == source_table.c.id)
    .when_matched_then_update(
        {"name": source_table.c.name, "email": source_table.c.email},
        where=source_table.c.name.is_not(None),       # optional WHERE
        delete_where=target_table.c.active == False,   # optional DELETE WHERE
    )
    .when_not_matched_then_insert(
        {
            "id": source_table.c.id,
            "name": source_table.c.name,
            "email": source_table.c.email,
        },
        where=source_table.c.name.is_not(None),  # optional WHERE
    )
)
```

**Generated SQL:**
```sql
MERGE INTO target_table
USING source_table
ON (target_table.id = source_table.id)
WHEN MATCHED THEN UPDATE SET name = source_table.name, email = source_table.email
  WHERE source_table.name IS NOT NULL
  DELETE WHERE target_table.active = 0
WHEN NOT MATCHED THEN INSERT (id, name, email)
  VALUES (source_table.id, source_table.name, source_table.email)
  WHERE source_table.name IS NOT NULL
```

**Builder methods:**
- `merge(target)` — factory function, sets target table
- `.using(source)` — source table or subquery
- `.on(condition)` — join condition
- `.when_matched_then_update(values, where=None, delete_where=None)` — UPDATE clause
- `.when_matched_then_delete(where=None)` — adds DELETE WHERE to an existing WHEN MATCHED clause
- `.when_not_matched_then_insert(values, where=None)` — INSERT clause

At least one of `when_matched_then_update` or `when_not_matched_then_insert` must be specified.

### GROUP_CONCAT

CUBRID supports `GROUP_CONCAT` as an aggregate function:

```python
import sqlalchemy as sa

stmt = sa.select(sa.func.group_concat(users.c.name))
# SELECT GROUP_CONCAT(users.name) FROM users
```

### REPLACE INTO

CUBRID supports `REPLACE INTO` which inserts a new row, or deletes the conflicting row and inserts the new one if a duplicate key is found.

```python
from sqlalchemy_cubrid import replace

stmt = replace(users).values(id=1, name="alice", email="alice@example.com")
# REPLACE INTO users (id, name, email) VALUES (1, 'alice', 'alice@example.com')
```

The `replace()` construct behaves like `insert()` but generates `REPLACE INTO` instead of `INSERT INTO`.

### Query Trace

CUBRID uses `SET TRACE ON` / `SHOW TRACE` instead of standard `EXPLAIN`. The dialect provides a `trace_query()` utility:

```python
from sqlalchemy_cubrid import trace_query

with engine.connect() as conn:
    traces = trace_query(conn, text("SELECT * FROM users WHERE id = 1"))
    for line in traces:
        print(line)
```

`trace_query()` handles the full lifecycle: enables tracing, executes your statement, collects trace output, and disables tracing — all within a safe `try/finally` block.
---

## Index Hints

CUBRID supports index hints in SELECT queries. These can be used via SQLAlchemy's built-in hint mechanisms — no custom dialect constructs are needed.

### USING INDEX

```python
# Using Select.with_hint()
stmt = (
    sa.select(users)
    .with_hint(users, "USING INDEX idx_users_name", dialect_name="cubrid")
)

# Using Select.suffix_with()
stmt = sa.select(users).suffix_with("USING INDEX idx_users_name")
```

### USE INDEX / FORCE INDEX / IGNORE INDEX

```python
stmt = (
    sa.select(users)
    .with_hint(users, "USE INDEX (idx_users_name)", dialect_name="cubrid")
)

stmt = (
    sa.select(users)
    .with_hint(users, "FORCE INDEX (idx_users_email)", dialect_name="cubrid")
)

stmt = (
    sa.select(users)
    .with_hint(users, "IGNORE INDEX (idx_users_old)", dialect_name="cubrid")
)
```

> **Note**: When using `with_hint(dialect_name="cubrid")`, the hint is only emitted when compiling against the CUBRID dialect. Other dialects will ignore it, making your code safely portable.

---

## Known Limitations & Roadmap

Features not currently supported that may be added in future releases, depending on CUBRID database evolution and community contributions.

| Feature | Status | Reason |
|---------|--------|--------|
| RETURNING clause | ❌ | CUBRID does not support `INSERT/UPDATE/DELETE … RETURNING` |
| JSON type | ✅ | Native JSON support (CUBRID 10.2+) with path expressions via `JSON_EXTRACT` |
| Temporary tables | ❌ | CUBRID does not support `CREATE TEMPORARY TABLE` |
| Multiple schemas | ❌ | CUBRID operates in a single-schema model |
| IS DISTINCT FROM | ❌ | Not a CUBRID SQL operator |
| Check constraint reflection | ❌ | CUBRID parses but ignores CHECK constraints |
| Sequences | ❌ | CUBRID uses `AUTO_INCREMENT` instead |
| Lateral joins | ❌ | `LATERAL` keyword causes syntax error in CUBRID |
| Full-text search | ❌ | No `MATCH … AGAINST` syntax or full-text indexes |
| Standard EXPLAIN | ❌ | CUBRID uses `SET TRACE ON` / `SHOW TRACE` instead (supported via `trace_query()`) |
| Alembic migrations | ✅ | Supported via `CubridImpl` entry-point (`pip install sqlalchemy-cubrid[alembic]`) |

---

*Last updated: April 2026 · sqlalchemy-cubrid v1.4.0 Beta · SQLAlchemy 2.0–2.1*
