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

> The two long "SCHEMA, … INSTANCES" spellings and `CURSOR STABILITY` are retained
> as backward-compatible aliases because they resolve to still-valid levels (4/5).
> The legacy names that resolved to the removed levels 1–3 are **no longer
> accepted** and raise `ValueError`.

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

### Reset on Connection Return

When a connection is returned to the pool, the dialect resets isolation to level 4 (`READ COMMITTED`) to ensure a clean state for the next checkout.

---

## Best Practices

1. **Use the default (level 4)** unless you have a specific reason to change it.
   Most web applications work correctly with `READ COMMITTED`.

2. **Use `SERIALIZABLE` sparingly.** It provides the strongest guarantees but can cause significant lock contention under load.

3. **Set isolation at the engine level** for application-wide defaults, and override per-connection only when needed.

4. **Be aware of DDL auto-commit.** CUBRID auto-commits DDL statements regardless of isolation level. This means `CREATE TABLE`, `ALTER TABLE`, etc. are immediately visible to all transactions.

---

!!! warning "Isolation level changes require COMMIT"
    CUBRID applies `SET TRANSACTION ISOLATION LEVEL` with a commit boundary.
    Plan transaction scopes accordingly when switching levels at runtime.

!!! tip "Default level 4 is a balanced baseline"
    Start with `READ COMMITTED` (level 4), then move to level 5 or 6 only for correctness-critical paths.

---

*See also: [Connection Setup](CONNECTION.md) · [Feature Support](FEATURE_SUPPORT.md)*
