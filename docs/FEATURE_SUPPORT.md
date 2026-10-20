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
| IS DISTINCT FROM | ✅ | ❌ | ✅ | ❌ |
| Postfetch LASTROWID | ✅ | ✅ | ❌ | ✅ |

### Notes

- **RETURNING**: CUBRID has no `RETURNING` clause. Auto-generated keys cannot be fetched in the same round-trip as the INSERT, so the dialect relies on `postfetch_lastrowid = True` instead (`get_last_insert_id()` / SQL fallback for the C driver; `cursor.lastrowid` for pycubrid).
- **DEFAULT VALUES**: CUBRID supports `INSERT INTO t DEFAULT VALUES`. The dialect sets `supports_default_values = True`.
- **ON DUPLICATE KEY UPDATE**: CUBRID supports `INSERT … ON DUPLICATE KEY UPDATE`. The dialect handles `stmt.inserted` references by re-emitting INSERT bind parameters (CUBRID does not support the `VALUES()` function). Use `sqlalchemy_cubrid.insert(table).on_duplicate_key_update(col=value)`. See [CUBRID-Specific DML Constructs](#cubrid-specific-dml-constructs) for usage examples.
- **MERGE**: CUBRID supports the full SQL MERGE statement. Use `sqlalchemy_cubrid.dml.merge(target)` with `.using()`, `.on()`, `.when_matched_then_update()`, and `.when_not_matched_then_insert()`. See [CUBRID-Specific DML Constructs](#cubrid-specific-dml-constructs).
- **FOR UPDATE**: CUBRID supports `SELECT … FOR UPDATE [OF col1, col2]`. NOWAIT and SKIP LOCKED are not supported.
- **UPDATE with LIMIT**: CUBRID and MySQL both support `UPDATE … LIMIT n`. PostgreSQL and SQLite do not.
- **Multi-table UPDATE**: SQLAlchemy's multi-table UPDATE pattern compiles to `UPDATE t1, t2 SET ... WHERE ...`, which matches the MySQL-style syntax accepted by CUBRID. The dialect intentionally keeps `update_from_clause()` disabled because no extra `FROM` clause is required.
- **TRUNCATE**: CUBRID supports `TRUNCATE TABLE`. Like other statements, it runs inside the connection's transaction and takes effect only when committed (see [No Statement-Text Autocommit](CONNECTION.md#no-statement-text-autocommit)).
- **IS DISTINCT FROM**: CUBRID lacks the SQL-standard syntax but supports the null-safe equal `<=>`. The dialect emulates `a IS DISTINCT FROM b` as `(a <=> b) = 0` and `a IS NOT DISTINCT FROM b` as `a <=> b`, preserving NULL-safe semantics in predicates and SELECT projections (#344, #377). `IS`/`IS NOT` against a value, e.g. Boolean `col.is_(True)`, is rendered the same way (`col <=> 1`, `(col <=> 1) = 0`), because CUBRID's `IS` accepts only `NULL`, `TRUE` and `FALSE` (#465); see [Boolean predicates](TYPES.md#boolean-predicates).

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
- **IF NOT EXISTS / IF EXISTS**: CUBRID supports `CREATE TABLE IF NOT EXISTS` and `DROP TABLE IF EXISTS`. The base SA compiler handles these natively. CUBRID has no `CREATE INDEX IF NOT EXISTS` or `DROP INDEX IF EXISTS`, so `CreateIndex(..., if_not_exists=True)` and `DropIndex(..., if_exists=True)` raise `CompileError` (#540, #533); use `checkfirst=True` or `inspect(conn).has_index()` instead.
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

- **CTEs**: CUBRID supports `WITH` clauses for read queries; `TestIsolatedCTE849` in `test/test_integration.py` checks them live on CUBRID 10.2, 11.0, 11.2 and 11.4 (#849): non-recursive and recursive `SELECT`, bound parameters inside the CTE, `values()` via a CTE, and `UPDATE` / `DELETE ... WHERE col = (SELECT ... FROM cte)` return the expected rows. A data-modifying statement inside a CTE body (a PostgreSQL-style writable CTE, `WITH x AS (INSERT … RETURNING …)`) is not supported; an `UPDATE` or `DELETE` can still read a CTE through a subquery, as above. `UPDATE ... FROM cte` and `DELETE ... FROM cte` raise, because CUBRID has no multi-table `UPDATE` / `DELETE`. `insert().from_select(..., select(cte))` and `replace().from_select(..., select(cte))`, including a recursive CTE, render the `WITH` clause after the column list (`INSERT INTO t (...) WITH ... SELECT`), the only order CUBRID accepts; `WITH ... INSERT` is a syntax error (-493) on CUBRID 10.2 and 11.4 (#897). SQLAlchemy's own `CTETest` nodes stay baselined in `test/known_failures.txt`, because their fixture cleanup fails on CUBRID's per-row foreign-key check, not because of these queries.
- **Recursive CTEs**: CUBRID supports `WITH RECURSIVE` for recursive queries, verified live on 10.2, 11.0, 11.2 and 11.4 (#849). SQLAlchemy's base compiler generates correct syntax — no dialect-specific compilation needed.
- **Window functions**: CUBRID supports `ROW_NUMBER()`, `RANK()`, `DENSE_RANK()`, and other window functions with `OVER(PARTITION BY … ORDER BY …)`. The SA base compiler handles these natively.
- **NULLS FIRST / NULLS LAST**: CUBRID supports `ORDER BY col ASC NULLS FIRST` and `ORDER BY col DESC NULLS LAST`. The SA base compiler handles these natively.
- **GROUP_CONCAT**: CUBRID supports `GROUP_CONCAT([DISTINCT] expr [ORDER BY …] [SEPARATOR '…'])`. Use `sa.func.group_concat(column)`, `sa.func.group_concat(column.distinct())`, or a `literal_column()` argument for `ORDER BY` / `SEPARATOR`; see [GROUP_CONCAT](#group_concat).
- **LIMIT / OFFSET**: CUBRID uses MySQL-style `LIMIT [offset,] count` syntax. When only an offset is given, the dialect emits `LIMIT offset, 4611686018427387904` (2^62) as the "all remaining rows" sentinel — effectively unbounded, and small enough that CUBRID's internal `offset + count` addition never overflows the signed BIGINT range. CUBRID has no `FETCH FIRST n ROWS ONLY`, so `Select.fetch(n)` also renders as `LIMIT n` (`LIMIT offset, n` with `.offset()`, #867); `fetch(..., percent=True)` and `fetch(..., with_ties=True)` have no `LIMIT` equivalent and raise `CompileError`.
- **Boolean SELECT-list items**: CUBRID rejects a bare `EXISTS (...)`, `NOT (...)` or `a AND b` / `a OR b` as a SELECT-list item (`SELECT EXISTS (SELECT 1)` is a syntax error) but accepts it inside parentheses. The dialect groups such a column, so `select(exists().where(...))`, `select(~exists()...)`, `select(and_(...))` and the ORM `session.query(q.exists()).scalar()` work (#966). CUBRID also rejects these expressions as a bare CAST or function argument and as an ORDER BY item, so the dialect groups them there too (also inside `type_coerce()`, labels and sort modifiers). `select(type_coerce(exists(), Boolean))`, `select(cast(and_(...), Integer))`, `select(func.coalesce(exists(), False))`, a Boolean `TypeDecorator` whose `column_expression()` wraps the column, `order_by(and_(...))` and `order_by(exists())` work (#968). A CAST or function groups such an argument wherever it appears, not only in the SELECT list, for example in `WHERE`, `HAVING`, `ON` or `UPDATE ... SET`, so `where(func.coalesce(and_(...), 0) == 1)` and `where(cast(and_(...), Integer) == 1)` work. An `EXISTS (...)` or `NOT (...)` item of a window or `WITHIN GROUP` `ORDER BY` or `PARTITION BY` is grouped too, so `over(order_by=exists())`, `over(partition_by=exists())` and `within_group(~exists())` work. A single `and_()` or `or_()` passed as a window `order_by` or `partition_by` is split by SQLAlchemy itself into separate items, on every dialect (for `or_()` that changes the meaning), so pass it inside a list, `over(order_by=[and_(...)])`, or call `.self_group()`; inside a list and in `WITHIN GROUP` it is grouped (#970). A `CASE` `THEN` or `ELSE` value is grouped too, in a searched and a simple (`value=`) `case()`, so `case((x > 0, and_(...)), else_=literal(False))` and `case((x > 0, exists()), else_=literal(False))` work (#982). A boolean simple-case value operand is grouped too, so `case({True: 10}, value=and_(...), else_=20)` and `case({True: 10}, value=exists(), else_=20)` work (#987). CUBRID can reject a `CASE` whose results are boolean and that has no `ELSE` or only `ELSE NULL`, for example one with a single `WHEN` ("semantic error", -495), with or without the grouping; this is a server limitation, so pass a non-NULL `else_=`, for example `else_=literal(False)`. CUBRID 11.4 also ignores any `CASE` used as a window `ORDER BY` or `PARTITION BY` item: it is evaluated as a constant, without an error, so the window is numbered as if the item were absent. Do not use a `CASE` there. A `CASE` with a boolean value as a `GROUP BY` item fails ("search condition is not allowed as group by spec", -493); group by its label instead. The same expressions as a bare `WHERE`, `HAVING` or `ON` condition, a `GROUP BY` item, a `CASE` `WHEN` condition or any other operand render as before. **Not supported:** a boolean expression as a `GROUP BY` item. CUBRID rejects any search condition there, even inside parentheses ("search condition is not allowed as group by spec", -493), so `group_by(a | b)` and `group_by(exists())` fail. Label the expression in the SELECT list and group by the label instead, for example `select(and_(...).label("k"), func.count()).group_by("k")`. The same applies to a CAST or function in `GROUP BY`: `group_by(func.coalesce(exists(), 0))` fails, with or without the grouping. Verified on CUBRID 11.4; not verified on 10.2, 11.0 or 11.2.
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
| BLOB | ⚠️ | ✅ | ✅ | ✅ |
| CLOB | ⚠️ | ✅ | ✅ | ✅ |
| BIT / BIT VARYING | ✅ | ✅ | ✅ | ❌ |

### Extended Types

| Type | CUBRID | MySQL | PostgreSQL | SQLite |
|------|--------|-------|------------|--------|
| ENUM | ✅ | ✅ | ✅ | ❌ |
| JSON | ✅ | ✅ | ✅ | ⚠️ |
| ARRAY | ❌ | ❌ | ✅ | ❌ |
| UUID | ❌ | ❌ | ✅ | ❌ |
| INTERVAL | ❌ | ❌ | ✅ | ❌ |
| HSTORE | ❌ | ❌ | ✅ | ❌ |

### Notes

- **BOOLEAN**: CUBRID maps `BOOLEAN` to `SMALLINT`. MySQL maps it to `TINYINT(1)`. SQLite stores booleans as integers. Only PostgreSQL has a native `BOOLEAN` type.
- **NCHAR / NVARCHAR**: CUBRID has first-class national character types. MySQL handles national characters via column charset. PostgreSQL and SQLite have no separate national character types.
- **JSON**: CUBRID 10.2+ has native JSON support (RFC 7159) with 25+ JSON functions. The dialect supports `JSON` type, `col["key"]` path expressions via `JSON_EXTRACT`, and typed access (`as_string()`, `as_integer()`, `as_float()`, and `as_numeric(p, s)`, which casts to `NUMERIC(p,s)` and returns `Decimal`). `as_numeric()` accepts JSON numbers, plain-decimal numeric strings (`"15.5"`) and JSON `true`/`false` (`1.00`/`0.00`). A string in exponent notation (`"1e3"`) raises CUBRID error -181, and a value outside `NUMERIC(p,s)` raises -427; use `as_float()` for those. A non-numeric string (`"abc"`) raises -181 with both `as_numeric()` and `as_float()`, so validate or filter such values first. MySQL (5.7+) and PostgreSQL also have native JSON support. SQLite has JSON functions but no dedicated column type.
- **ARRAY**: CUBRID uses collection types (`SET`, `MULTISET`, `SEQUENCE`) which serve a similar purpose but are not SQL-standard arrays. PostgreSQL has native `ARRAY[]` support.
- **CLOB**: CUBRID and MySQL have explicit `CLOB` types. PostgreSQL uses `TEXT` (unlimited length). SQLite stores all text as `TEXT`.
- **BLOB / CLOB on CUBRID (⚠️)**: The types are implemented: `BLOB`, `CLOB` and `LargeBinary` compile to CUBRID `BLOB` / `CLOB` DDL and reflect back, binding `bytes` / `str` stores the full value, and `NULL` round-trips as `None`. What is partial is the value returned by an ordinary Core or ORM `SELECT`: a non-NULL `BLOB` / `CLOB` column comes back as the driver's LOB locator, not as `bytes` / `str`, on `cubrid://`, `cubrid+pycubrid://` and `cubrid+aiopycubrid://` (and for `LargeBinary` / `BLOB` SQLAlchemy's result processor then raises `TypeError`). This is a driver fetch limitation, not a CUBRID storage limit; `test/test_lob_value_contract.py` keeps those reads as strict xfails. To read content, convert on the server (`CLOB_TO_CHAR(col)`, `BLOB_TO_BIT(col)`) or store large text in `Text` (CUBRID `STRING`). See [Driver Compatibility, Known Issue 6](DRIVER_COMPAT.md#6-blob--clob-reads-return-a-lob-locator) and [Types](TYPES.md).

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
- **Column comments**: Reflected via `get_columns()` querying the `db_attribute.comment` catalog view column. Returned in the `"comment"` key of each column dict.
- **has_index**: The CUBRID dialect implements `has_index()` by querying `db_index`. The MySQL SA dialect does not provide a dedicated `has_index()` method. CUBRID stores identifiers in lower case, even quoted ones, so `has_table()` and `has_index()` also match a mixed-case name against its lower-case stored form (#543); `Index.drop(checkfirst=True)` therefore works for `Index("IX_Mixed", Table("Users", ...))`.
- **Index shapes**: `get_indexes()` reports a function-based key (`CREATE INDEX ... (LOWER(a))`) in `expressions` with `None` in `column_names`, a `DESC` key in `column_sorting`, a filtered index (`... WHERE c > 3`) as `dialect_options["cubrid_where"]` and a key prefix (`a(5)`) as `dialect_options["cubrid_length"]` (#869), from the `SHOW INDEXES` `Func`, `Collation` and `Sub_part` columns and `db_index.filter_expression`. CUBRID prints the expression and the filter with the column qualified by its table (`lower([dba.t].[a])`, `[dba.t].c>3`); the qualifier is dropped, so they reflect as `lower([a])` and `c>3`, and a reflected table re-creates the same indexes. The same options create them: `Index("ix", t.c.c, cubrid_where=t.c.c > 3)` emits `CREATE INDEX ix ON t (c) WHERE c > 3`, and `Index("ix", t.c.a, cubrid_length={"a": 5})` (or `cubrid_length=5` for every column key) emits `CREATE INDEX ix ON t (a(5))`. CUBRID rejects a `UNIQUE` filtered index, so `unique=True` with `cubrid_where` raises `CompileError`, as does a prefix length on an expression key. Alembic autogenerate compares these indexes by their normalized keys, sort order, filter and prefix lengths (string literals are compared as written), so an unchanged one is not proposed again on any supported Alembic; replacing one whose sort order, filter or prefix length changed needs Alembic 1.12 or later, the first release that calls the dialect's index comparison.
- **Unique constraints and unique indexes**: CUBRID implements a `UNIQUE` constraint as a unique index and cannot tell it apart from `CREATE UNIQUE INDEX`, so, as with MySQL, each one is reported by both `get_indexes()` and `get_unique_constraints()`, and the unique-constraint entry carries `duplicates_index` naming the index. `Table` reflection (and Alembic autogenerate) uses that key to keep only the unique index. `get_indexes()` returns an empty list for a view.
- **Missing tables and views**: `get_columns()`, `get_pk_constraint()`, `get_foreign_keys()`, `get_indexes()`, `get_unique_constraints()`, `get_table_comment()` and `get_view_definition()` raise `NoSuchTableError` for an object that does not exist, so the `get_multi_*()` variants leave it out; `get_view_definition()` also raises it for a table. For a view, `get_foreign_keys()` and `get_unique_constraints()` return an empty list without running `SHOW CREATE TABLE`.
- **Reflection source**: Reflection is split across multiple sources: `SHOW COLUMNS IN` + `db_attribute` for columns/comments, `db_index` + `db_index_key` for the primary key (name and every column in key order), `SHOW CREATE TABLE` parsing for foreign keys, `db_index` + `SHOW INDEXES IN` for unique constraints (with `SHOW CREATE TABLE` parsing as the fallback only when `db_index` lists no index of the table at all or, since CUBRID 11.2, when the name resolves to another owner's class that shows no unique index (if it shows one, `SHOW INDEXES IN` raises `NoSuchTableError` first; the fallback raises it too); any other table with a primary key, a foreign key or another index but no unique one is answered from the catalog, #610), `SHOW INDEXES IN` + `db_index` for indexes, `SHOW CREATE VIEW` for view definitions, and `db_class` for table/view names and table comments.
- **Foreign-key DDL grammar**: `get_foreign_keys()` relies on the `SHOW CREATE TABLE` output of the supported servers (10.2, 11.0, 11.2 and 11.4), recorded in `test/fixtures/show_create_table/` and checked against the live server by `test/test_show_create_table_server_output.py` (#611): every identifier is printed in brackets with spaces, commas and parentheses kept verbatim; each foreign key prints both actions, `ON DELETE` before `ON UPDATE`, with the default printed as `RESTRICT`; the actions are `CASCADE`, `SET NULL`, `NO ACTION` and `RESTRICT` (the servers reject `ON UPDATE CASCADE` and have no `SET DEFAULT`); the referenced table is owner-qualified (`[dba.parent]`) from 11.2 and unqualified on 10.2 and 11.0, and the owner is dropped from `referred_table`. A `UNIQUE` constraint and a `CREATE UNIQUE INDEX` index both print as `UNIQUE KEY`.
- **Table and view listings**: `get_table_names()`, `get_view_names()` and `has_table()` read `db_class`. Since CUBRID 11.2 that view lists the classes of every owner the user may read, while an unqualified name resolves only in the current user's schema, so these methods are limited to `owner_name = CURRENT_USER` (#864): another owner's table of the same name no longer makes `create_all()` skip the current user's table, `MetaData.reflect()` no longer aborts with `NoSuchTableError` on it, and two owners' same-named tables are listed once. A `schema=` argument other than the default schema still returns no names, as for every reflection method. CUBRID 10.2 and 11.0 class names are global, so their listings are unchanged.
- **Reflected server defaults**: `get_columns()` reports each default as SQL that `CreateTable` and Alembic can emit again (#865). A numeric column's numeric default is kept as `SHOW COLUMNS` prints it (`5`, `-3`, `1.50`). Any other default, including a string column's `'5'` (which `SHOW COLUMNS` also prints as `5`), is read from `SHOW CREATE TABLE`, which `get_columns()` then runs once for the table: `SHOW COLUMNS` prints a string default without its quotes, so `'it''s'`, `''` and the string `'NULL'` used to reflect as `it''s`, an empty string and `NULL`, a date as `01/02/2020`, and both `'CURRENT_USER'` and `USER` as `CURRENT_USER`. They now reflect as `'it''s'`, `''`, `'NULL'`, `date '01/02/2020'`, `'CURRENT_USER'` and `CURRENT_USER`; functions such as `SYS_DATETIME` or `TO_CHAR(SYS_DATETIME, 'YYYY')`, charset-prefixed literals (`_utf8'q'`, `N'n'`) and bit strings (`X'a0'`) keep the server's spelling. A column without a default still reflects `None`. Views do not run `SHOW CREATE TABLE`; if its output cannot be parsed, the `SHOW COLUMNS` text is kept.
- **Reflection as a non-DBA user**: Reflection reads only the catalog views every user can read (`db_class`, `db_index`, `db_index_key`, `db_attribute`), never the DBA-only `_db_index`, `_db_index_key` or `_db_attribute` catalog tables, so a non-DBA user gets the same indexes, primary key, unique constraints, `has_index()` answer and column comments as DBA. The table name matches as given or folded to lower case, as in `SHOW COLUMNS IN <name>`. Since CUBRID 11.2 these views also list same-named classes of other owners, so the rows are limited to the owner of the reflected class (the current user's own class first, as for `db_class`). A failing catalog query raises instead of silently falling back to incomplete metadata.
- **`SHOW CREATE TABLE` failures**: `get_foreign_keys()` (and the `SHOW CREATE TABLE` fallback of `get_unique_constraints()`) returns an empty list only when `SHOW CREATE TABLE` succeeds and the DDL has no such constraint. `Unknown class`, or no row for a table that the catalog listed, raises `NoSuchTableError`; any other failure (a disconnect, an authorization error, a driver error) propagates instead of being logged and reported as "no constraints", which made Alembic autogenerate emit `add_fk` for foreign keys that already exist (#589). CUBRID lists in `db_class` only the tables a user holds `SELECT` on, and `SHOW CREATE TABLE` on such a table does not fail with an authorization error (checked as a non-DBA user on CUBRID 10.2 and 11.4), so no failure is tolerated for non-DBA users either. Since CUBRID 11.2 an unqualified name resolves in the current user's schema, so another owner's table, even one granted to the current user, raises `NoSuchTableError` from `get_columns()` as well as here; `get_unique_constraints()` therefore keeps reading `SHOW CREATE TABLE` for such a table when the catalog lists its indexes but no unique one; when the catalog lists a unique index of it, `SHOW INDEXES IN` raises `NoSuchTableError` before the DDL is read. For a table of the current user (any visible table before 11.2) whose catalog lists indexes but no unique one, `get_unique_constraints()` returns `[]` without running `SHOW CREATE TABLE` (#610). When the catalog lists a unique index that `SHOW INDEXES` does not return key columns for, `get_unique_constraints()` raises `InvalidRequestError` naming the unresolved and the resolved indexes, instead of reporting an incomplete set that Alembic would read as missing constraints (#848).

---

## Transactions & Connections

| Feature | CUBRID | MySQL | PostgreSQL | SQLite |
|---------|--------|-------|------------|--------|
| Isolation level management | ✅ | ✅ | ✅ | ✅ |
| Savepoints | ✅ | ✅ | ✅ | ✅ |
| Two-phase commit | ❌ | ✅ | ✅ | ❌ |
| Server-side cursors | ❌ | ✅ | ✅ | ❌ |
| Autocommit detection from SQL text | ❌ | ❌ | ❌ | ❌ |
| Connection-level encoding | ❌ | ✅ | ✅ | ❌ |

### CUBRID Isolation Levels

CUBRID's MVCC engine (10.0+) supports three isolation levels:

| Level | Description |
|-------|-------------|
| `SERIALIZABLE` (6) | Full serialization |
| `REPEATABLE READ` (5) | Repeatable read within a transaction |
| `READ COMMITTED` (4, default) | Reads see only committed data; non-repeatable reads possible |

SQLAlchemy's `AUTOCOMMIT` level is also accepted on every driver; it switches the driver to autocommit mode. See [Isolation Levels](ISOLATION_LEVELS.md#autocommit).

### Notes

- **Two-phase commit**: CUBRID does not support distributed transactions via `XA`.
- **Server-side cursors**: The CUBRID Python driver does not expose server-side cursor functionality.
- **Autocommit detection from SQL text**: SQLAlchemy 2.x does not inspect statement text to decide when to commit, for any dialect. DML and DDL are committed only through `conn.commit()`, an `engine.begin()` block, or a `Session` commit. See [No Statement-Text Autocommit](CONNECTION.md#no-statement-text-autocommit).
- **Savepoints**: CUBRID supports `SAVEPOINT` and `ROLLBACK TO SAVEPOINT`. `RELEASE SAVEPOINT` is not supported — the dialect implements `do_release_savepoint()` as a no-op.

---

## Dialect Engine Features

| Feature | CUBRID | MySQL | PostgreSQL | SQLite |
|---------|--------|-------|------------|--------|
| Statement caching | ✅ | ✅ | ✅ | ✅ |
| Native enum | ✅ | ✅ | ✅ | ❌ |
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
- **Name normalization**: CUBRID folds unquoted identifiers to lowercase, which already matches SQLAlchemy's lowercase convention for case-insensitive names. The dialect therefore sets `requires_name_normalize = False` and does not apply SQLAlchemy's upper-case name normalization.
- **Max identifier length**: CUBRID allows identifiers up to 254 characters — significantly longer than MySQL (64) or PostgreSQL (63).
- **Result metadata (`cursor.description`)**: the dialect passes the driver's `cursor.description` through unchanged (`CursorResult.cursor.description`) and normalizes none of it. Verified live on CUBRID 10.2 and 11.4 for sync and async pycubrid and CUBRIDdb (#482): `Result.keys()` equals the description names, including `text()` aliases and expressions (`1 + 1` is named `1+1`); scalar type codes are the CUBRID codes on every driver (for example `VARCHAR` 2, `NUMERIC` 7, `INTEGER` 8, `DOUBLE` 12, `DATE` 13, `TIMESTAMP` 15, `BIGINT` 21); sync and async pycubrid report the same values. Driver differences: collection columns are `SET` 16 / `MULTISET` 17 / `SEQUENCE` 18 on pycubrid but CCI composite codes on CUBRIDdb (the kind in bits `0x60` plus the element type, so `SET(INTEGER)` is 40); `null_ok` is a `bool` on pycubrid and `0`/`1` on CUBRIDdb. Released pycubrid 1.7.1 reports `null_ok` inverted (cubrid-lab/pycubrid#431) and collection columns with their element type code (cubrid-lab/pycubrid#430); both are fixed in pycubrid 1.8.0, which the contract tests require. SQLAlchemy itself does not consume `null_ok`, and reflection (`Inspector.get_columns()`) reads nullability from the catalog, so it is unaffected.

---

## CUBRID-Specific Features

These types and capabilities are unique to the CUBRID dialect and have no direct equivalent in MySQL, PostgreSQL, or SQLite.

| Feature | Description |
|---------|-------------|
| `MONETARY` type | Currency-aware server type; declared/compiled but not auto-reflected |
| `STRING` type | Alias for `VARCHAR(1,073,741,823)` — maximum-length variable string |
| `OBJECT` type | OID reference type pointing to another row by object identifier |
| `SET` collection | Unordered collection of unique elements |
| `MULTISET` collection | Unordered collection that allows duplicates |
| `SEQUENCE` collection | Ordered collection that allows duplicates |
| 3 MVCC isolation levels | `READ COMMITTED` (default), `REPEATABLE READ`, `SERIALIZABLE` |
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

CUBRID supports `INSERT … ON DUPLICATE KEY UPDATE`. The dialect handles `stmt.inserted` references by re-emitting INSERT bind parameters (CUBRID does not support the `VALUES()` function).

```python
from sqlalchemy_cubrid import insert

stmt = insert(users).values(id=1, name="alice", email="alice@example.com")
stmt = stmt.on_duplicate_key_update(name="updated_alice")
# INSERT INTO users (id, name, email) VALUES (1, 'alice', 'alice@example.com')
# ON DUPLICATE KEY UPDATE name = 'updated_alice'

# Reference the inserted value:
stmt = insert(users).values(id=1, name="alice", email="alice@example.com")
stmt = stmt.on_duplicate_key_update(name=stmt.inserted.name)
# ON DUPLICATE KEY UPDATE name = ?
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

stmt = sa.select(sa.func.group_concat(users.c.name.distinct()))
# SELECT GROUP_CONCAT(DISTINCT users.name) FROM users

# SQLAlchemy 2.1: ORDER BY with aggregate_order_by()
stmt = sa.select(sa.func.group_concat(users.c.name).aggregate_order_by(users.c.name.desc()))
# SELECT GROUP_CONCAT(users.name ORDER BY users.name DESC) FROM users

# SEPARATOR (and ORDER BY on SQLAlchemy 2.0) has no SQLAlchemy construct; write it as text
stmt = sa.select(
    sa.func.group_concat(sa.literal_column("name ORDER BY name DESC SEPARATOR ';'"))
).select_from(users)
# SELECT GROUP_CONCAT(name ORDER BY name DESC SEPARATOR ';') FROM users

stmt = sa.select(sa.func.group_concat(sa.and_(users.c.id > 1, users.c.name != "")))
# SELECT GROUP_CONCAT((users.id > ? AND users.name != ?)) FROM users
```

NULL values are skipped, and a group with only NULLs returns `NULL`. Without `ORDER BY`
the order of the concatenated values is unspecified. A boolean `EXISTS`, `NOT`, `AND` or
`OR` argument, or `aggregate_order_by()` item, is grouped like any function argument.
CUBRID takes one `ORDER BY` item, and it must be the `GROUP_CONCAT` argument itself or a
position such as `literal_column("1")`; another expression fails on the server (-494).
Verified on CUBRID 11.4; not verified on 10.2, 11.0 or 11.2. Not supported:

- `sa.func.group_concat(column, sa.literal_column("SEPARATOR ','"))` renders
  `GROUP_CONCAT(users.name, SEPARATOR ',')`, which CUBRID rejects (-493). Put `SEPARATOR`
  in the same `literal_column()` text as the expression.
- More than one argument: CUBRID takes a single expression ("invalid use of group_concat").
- More than one `aggregate_order_by()` item (-493), or `aggregate_order_by()` with a
  `literal_column()` argument that contains `SEPARATOR` (the `ORDER BY` would follow it,
  -493). Write the whole `ORDER BY ... SEPARATOR` text instead.
- `aggregate_order_by()` on any function other than `GROUP_CONCAT`, including
  `func.aggregate_strings()`: no other CUBRID aggregate takes an `ORDER BY`, so it raises
  `CompileError` instead of dropping the `ORDER BY`.
- `aggregate_order_by()` on a `.filter(...)`ed function, `GROUP_CONCAT` included: CUBRID has no
  `FILTER (WHERE ...)` clause, so it raises `CompileError`.

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

| Check constraint reflection | ❌ | CUBRID parses but ignores CHECK constraints |
| Sequences | ❌ | CUBRID uses `AUTO_INCREMENT` instead |
| Lateral joins | ❌ | `LATERAL` keyword causes syntax error in CUBRID |
| Full-text search | ❌ | No `MATCH … AGAINST` syntax or full-text indexes |
| Standard EXPLAIN | ❌ | CUBRID uses `SET TRACE ON` / `SHOW TRACE` instead (supported via `trace_query()`) |
| Alembic migrations | ✅ | Supported via `CubridImpl`, registered when the dialect loads (`pip install sqlalchemy-cubrid[alembic]`) |

---

*Last updated: September 2026 · sqlalchemy-cubrid v1.8.0 · SQLAlchemy 2.0–2.1*
