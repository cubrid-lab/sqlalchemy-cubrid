# Isolation Levels

Since CUBRID 10.0 (the MVCC engine), CUBRID supports **three** transaction isolation levels: `READ COMMITTED`, `REPEATABLE READ`, and `SERIALIZABLE`. This document explains each level, how to configure them, and how they compare to other databases.

> **Historical note.** Releases prior to CUBRID 10.0 exposed six numeric levels (1–6) that split isolation into separate *schema* (class-level) and *instance* (data-level) dimensions. The MVCC engine introduced in 10.0 removed the four legacy granular levels; the server now accepts **only** numeric codes `4` (READ COMMITTED), `5` (REPEATABLE READ), and `6` (SERIALIZABLE). Attempting `SET TRANSACTION ISOLATION LEVEL 1|2|3` on a modern server fails with:
>
> ```
> Isolation level value in MVCC must be 'read committed', 'repeatable read' or 'serializable'
> ```
>
> Accordingly, this dialect only accepts names that resolve to levels 4, 5, and 6.

---

## Table of Contents

- [Overview](#overview)
- [Isolation Level Details](#isolation-level-details)
- [Configuration](#configuration)
  - [Engine-Level (Default for All Connections)](#engine-level-default-for-all-connections)
  - [Connection-Level (Per Connection)](#connection-level-per-connection)
  - [Execution Options (Per Statement Block)](#execution-options-per-statement-block)
  - [AUTOCOMMIT](#autocommit)
- [Accepted Level Names](#accepted-level-names)
- [Comparison with SQL Standard](#comparison-with-sql-standard)
- [How the Dialect Manages Isolation](#how-the-dialect-manages-isolation)
- [Best Practices](#best-practices)

---

## Overview

| Level | Numeric | Name (Short)                  |
|-------|---------|-------------------------------|
| 6     | 6       | `SERIALIZABLE`                |
| 5     | 5       | `REPEATABLE READ`             |
| 4     | 4       | `READ COMMITTED` *(default)*  |

The CUBRID server default is **level 4** (`READ COMMITTED`).

---

## Isolation Level Details

### Level 6 — SERIALIZABLE

The strictest isolation level. Transactions are fully serialized: no dirty reads, no non-repeatable reads, no phantom reads.

**Use when**: Absolute consistency is required (e.g., financial transactions, audit logs).

**Trade-off**: Highest lock contention, lowest concurrency.

### Level 5 — REPEATABLE READ

Reads are repeatable within a transaction. No phantom reads on indexed columns.

**Use when**: You need consistent reads within a transaction but can tolerate slightly lower throughput than serializable.

### Level 4 — READ COMMITTED *(Default)*

Reads see only committed values but may see different results on re-read (non-repeatable reads possible).

**Use when**: General-purpose OLTP workloads. The best balance of consistency and performance for most applications.

---

## Configuration

### Engine-Level (Default for All Connections)

Set the default isolation level when creating the engine:

```python
from sqlalchemy import create_engine

engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",
    isolation_level="REPEATABLE READ",
)
```

### Connection-Level (Per Connection)

Set isolation level on a specific connection:

```python
from sqlalchemy import text

with engine.connect().execution_options(
    isolation_level="SERIALIZABLE"
) as conn:
    result = conn.execute(text("SELECT * FROM accounts WHERE id = :id"), {"id": 1})
    # This connection uses SERIALIZABLE isolation
```

### Execution Options (Per Statement Block)

```python
with engine.begin() as conn:
    # Switch isolation for this block
    conn = conn.execution_options(isolation_level="SERIALIZABLE")
    conn.execute(text("UPDATE accounts SET balance = balance - 100 WHERE id = 1"))
    conn.execute(text("UPDATE accounts SET balance = balance + 100 WHERE id = 2"))
    # Commits at end of block
```

### AUTOCOMMIT

`AUTOCOMMIT` turns on the driver's autocommit mode, so each statement commits
as soon as it runs. It works on `cubrid://` (CUBRIDdb), `cubrid+pycubrid://`
and `cubrid+aiopycubrid://`, at every level SQLAlchemy offers:

```python
# Every connection from this engine
engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb", isolation_level="AUTOCOMMIT")

# An engine copy that shares the pool
autocommit_engine = engine.execution_options(isolation_level="AUTOCOMMIT")

# One connection
with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
    conn.execute(text("INSERT INTO logs (msg) VALUES ('event')"))
    # Already visible to other sessions; conn.rollback() cannot undo it
```

`AUTOCOMMIT` is a driver mode, not a server isolation level: the server level
stays what it was, and `conn.get_isolation_level()` still reports it. Setting
any other level turns driver autocommit off again, and a pooled connection
returns to transactional mode when it is checked in (see
[Reset on Connection Return](#reset-on-connection-return)). Use
`engine.dialect.detect_autocommit_setting(dbapi_connection)` to check the mode
of a DBAPI connection.

---

## Accepted Level Names

The dialect accepts multiple name forms for convenience. All names resolve to one
of the three MVCC levels; names are **case-insensitive**.

| Name                                                   | Maps To Level |
|--------------------------------------------------------|---------------|
| `SERIALIZABLE`                                         | 6             |
| `REPEATABLE READ`                                      | 5             |
| `REPEATABLE READ SCHEMA, REPEATABLE READ INSTANCES`    | 5             |
| `READ COMMITTED`                                       | 4             |
| `REPEATABLE READ SCHEMA, READ COMMITTED INSTANCES`     | 4             |
| `CURSOR STABILITY`                                     | 4             |
| `AUTOCOMMIT`                                           | driver autocommit, no server level |

> The two long "SCHEMA, … INSTANCES" spellings and `CURSOR STABILITY` are retained
> as backward-compatible aliases because they resolve to still-valid levels (4/5).
> An engine-level alias is stored under its canonical name (for example
> `isolation_level="CURSOR STABILITY"` becomes `READ COMMITTED`).
> The legacy names that resolved to the removed levels 1–3 are **no longer
> accepted**. An unknown name raises `sqlalchemy.exc.ArgumentError` from
> `create_engine(isolation_level=...)` (on first connect) and from
> `execution_options(isolation_level=...)`; calling
> `dialect.set_isolation_level()` directly raises `ValueError`.

---

## Comparison with SQL Standard

| SQL Standard Level    | CUBRID Equivalent   | Level |
|-----------------------|---------------------|-------|
| `READ UNCOMMITTED`    | *(not supported)*   | —     |
| `READ COMMITTED`      | Level 4 *(default)* | 4     |
| `REPEATABLE READ`     | Level 5             | 5     |
| `SERIALIZABLE`        | Level 6             | 6     |

CUBRID's MVCC engine does not offer a `READ UNCOMMITTED` (dirty-read) level;
the lowest available level is `READ COMMITTED`.

---

## How the Dialect Manages Isolation

### Setting Isolation Level

The dialect uses the `SET TRANSACTION ISOLATION LEVEL` SQL command with CUBRID's numeric level:

```sql
SET TRANSACTION ISOLATION LEVEL 5
COMMIT
```

The `COMMIT` after setting isolation level is required by CUBRID to apply the change.

### Reading Current Level

The dialect reads the current isolation level using CUBRID's proprietary syntax:

```sql
GET TRANSACTION ISOLATION LEVEL TO X
SELECT X
```

The returned numeric value is mapped back to a descriptive string.

> **Note — canonical names on read-back.** `get_isolation_level()` returns the
> **canonical** name for a level, which may differ from the alias you passed to
> `set_isolation_level()`. CUBRID accepts several aliases that map to the same
> numeric level (see [Accepted Level Names](#accepted-level-names)) — for
> example both `"REPEATABLE READ"` and `"REPEATABLE READ SCHEMA, REPEATABLE READ
> INSTANCES"` map to level 5 — but reading the level resolves the numeric code
> back through a single canonical entry. A `set` → `get` round-trip therefore
> returns the canonical name (e.g. `"REPEATABLE READ"`), not necessarily the
> exact string you supplied.

### Kept Across Commit and Rollback on pycubrid

pycubrid opens a new CAS session after the driver's `commit()` / `rollback()`,
and that session starts at the server default level (see
[Driver Compatibility, Known Issue 10](DRIVER_COMPAT.md#10-pycubrid-starts-a-new-session-after-commit--rollback-dialect-re-applies-the-isolation-level)).
`cubrid+pycubrid://` and `cubrid+aiopycubrid://` therefore re-apply the level
they last set on a connection after every commit and rollback, so an engine- or
connection-level `isolation_level` stays in effect. `cubrid://` (CUBRIDdb) keeps
the session and needs no re-apply.

### Reset on Connection Return

When a connection whose level was changed with `execution_options()` is
returned to the pool, SQLAlchemy restores the engine-level `isolation_level`
(including `AUTOCOMMIT`). Without an engine-level setting it restores the level
the first connection reported, which is the server default (normally
`READ COMMITTED`). Earlier releases always reset to `READ COMMITTED`, which
dropped an engine-level setting after a per-connection override.

---

## Best Practices

1. **Use the default (level 4)** unless you have a specific reason to change it.
   Most web applications work correctly with `READ COMMITTED`.

2. **Use `SERIALIZABLE` sparingly.** It provides the strongest guarantees but can cause significant lock contention under load.

3. **Set isolation at the engine level** for application-wide defaults, and override per-connection only when needed.

4. **DDL is transactional.** At every isolation level, CUBRID runs DDL inside the current transaction: `ROLLBACK` undoes `CREATE TABLE`, `ALTER TABLE` and the like, and DDL never commits earlier DML. Uncommitted DDL holds a schema lock on its table, so other transactions that use the table wait until it commits or rolls back. Only client autocommit (driver-level autocommit, or `isolation_level="AUTOCOMMIT"` where the dialect accepts it, #501) commits DDL immediately.

---

!!! warning "Isolation level changes require COMMIT"
    CUBRID applies `SET TRANSACTION ISOLATION LEVEL` with a commit boundary.
    Plan transaction scopes accordingly when switching levels at runtime.

!!! tip "Default level 4 is a balanced baseline"
    Start with `READ COMMITTED` (level 4), then move to level 5 or 6 only for correctness-critical paths.

---

*See also: [Connection Setup](CONNECTION.md) · [Feature Support](FEATURE_SUPPORT.md)*
