# Isolation Levels

CUBRID provides six isolation levels — more than the SQL standard's four. This document explains each level, how to configure them, and how they compare to other databases.

---

## Table of Contents

- [Overview](#overview)
- [Isolation Level Details](#isolation-level-details)
- [Configuration](#configuration)
  - [Engine-Level (Default for All Connections)](#engine-level-default-for-all-connections)
  - [Connection-Level (Per Connection)](#connection-level-per-connection)
  - [Execution Options (Per Statement Block)](#execution-options-per-statement-block)
- [CUBRID's Dual-Granularity Model](#cubrids-dual-granularity-model)
- [Accepted Level Names](#accepted-level-names)
- [Comparison with SQL Standard](#comparison-with-sql-standard)
- [How the Dialect Manages Isolation](#how-the-dialect-manages-isolation)
- [Best Practices](#best-practices)

---

## Overview

| Level | Numeric | Name (Short)                   | Name (Full)                                                   |
|-------|---------|-------------------------------|---------------------------------------------------------------|
| 6     | 6       | `SERIALIZABLE`                | Serializable                                                  |
| 5     | 5       | `REPEATABLE READ`             | Repeatable Read Schema, Repeatable Read Instances              |
| 4     | 4       | `READ COMMITTED` *(default)*  | Repeatable Read Schema, Read Committed Instances               |
| 3     | 3       | —                             | Repeatable Read Schema, Read Uncommitted Instances             |
| 2     | 2       | —                             | Read Committed Schema, Read Committed Instances                |
| 1     | 1       | —                             | Read Committed Schema, Read Uncommitted Instances              |

The CUBRID server default is **level 4** (`READ COMMITTED`).

---

## Isolation Level Details

### Level 6 — SERIALIZABLE

The strictest isolation level. Transactions are fully serialized: no dirty reads, no non-repeatable reads, no phantom reads.

**Use when**: Absolute consistency is required (e.g., financial transactions, audit logs).

**Trade-off**: Highest lock contention, lowest concurrency.

### Level 5 — REPEATABLE READ

Both schema (class-level) and data (instance-level) reads are repeatable within a transaction. No phantom reads on indexed columns.

**Use when**: You need consistent reads within a transaction but can tolerate slightly lower throughput than serializable.

### Level 4 — READ COMMITTED *(Default)*

Schema reads are repeatable; data reads see only committed values but may see different results on re-read (non-repeatable reads possible).

**Use when**: General-purpose OLTP workloads. The best balance of consistency and performance for most applications.

### Level 3 — REPEATABLE READ Schema, READ UNCOMMITTED Instances

Schema reads are repeatable, but data reads may see uncommitted changes from other transactions (dirty reads possible).

**Use when**: Read-heavy analytics where absolute accuracy is not critical and you want to avoid data-level read locks.

### Level 2 — READ COMMITTED Schema, READ COMMITTED Instances

Both schema and data reads see only committed values, but neither is repeatable. Schema changes from committed transactions are visible immediately.

**Use when**: Applications that don't modify schema during normal operation and can tolerate non-repeatable reads.

### Level 1 — READ COMMITTED Schema, READ UNCOMMITTED Instances

Schema reads see only committed values. Data reads may see uncommitted changes (dirty reads).

**Use when**: Maximum read performance in controlled environments where dirty reads are acceptable. Not recommended for production applications.

---

## Configuration

### Engine-Level (Default for All Connections)

Set the default isolation level when creating the engine:

```python
from sqlalchemy import create_engine

# Use short name
engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",
    isolation_level="REPEATABLE READ",
)

# Use full CUBRID name
engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",
    isolation_level="REPEATABLE READ SCHEMA, REPEATABLE READ INSTANCES",
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

## CUBRID's Dual-Granularity Model

Unlike most databases, CUBRID separates isolation into two dimensions:

- **Class-level** (schema operations): Controls visibility of DDL changes (table creation, column alterations)
- **Instance-level** (data operations): Controls visibility of DML changes (inserts, updates, deletes)

This is why CUBRID has 6 levels instead of the standard 4. The combinations are:

| Class (Schema)     | Instance (Data)     | Level |
|--------------------|---------------------|-------|
| Serializable       | Serializable        | 6     |
| Repeatable Read    | Repeatable Read     | 5     |
| Repeatable Read    | Read Committed      | 4     |
| Repeatable Read    | Read Uncommitted    | 3     |
| Read Committed     | Read Committed      | 2     |
| Read Committed     | Read Uncommitted    | 1     |

In practice, most applications use levels 4 (default), 5, or 6.

---

## Accepted Level Names

The dialect accepts multiple name forms for convenience:

| Short Name                                             | Maps To Level |
|--------------------------------------------------------|---------------|
| `SERIALIZABLE`                                         | 6             |
| `REPEATABLE READ`                                      | 5             |
| `REPEATABLE READ SCHEMA, REPEATABLE READ INSTANCES`    | 5             |
| `READ COMMITTED`                                       | 4             |
| `REPEATABLE READ SCHEMA, READ COMMITTED INSTANCES`     | 4             |
| `CURSOR STABILITY`                                     | 4             |
| `REPEATABLE READ SCHEMA, READ UNCOMMITTED INSTANCES`   | 3             |
| `READ COMMITTED SCHEMA, READ COMMITTED INSTANCES`      | 2             |
| `READ COMMITTED SCHEMA, READ UNCOMMITTED INSTANCES`    | 1             |

Names are **case-insensitive**.

---

## Comparison with SQL Standard

| SQL Standard Level    | CUBRID Equivalent   | Level |
|-----------------------|---------------------|-------|
| `READ UNCOMMITTED`    | Level 1 *(closest)* | 1     |
| `READ COMMITTED`      | Level 4 *(default)* | 4     |
| `REPEATABLE READ`     | Level 5             | 5     |
| `SERIALIZABLE`        | Level 6             | 6     |

Levels 2 and 3 are CUBRID-specific and have no direct SQL standard equivalent.

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

3. **Avoid levels 1 and 3 in production.** Dirty reads (read uncommitted instances) can lead to inconsistent application behavior.

4. **Set isolation at the engine level** for application-wide defaults, and override per-connection only when needed.

5. **Be aware of DDL auto-commit.** CUBRID auto-commits DDL statements regardless of isolation level. This means `CREATE TABLE`, `ALTER TABLE`, etc. are immediately visible to all transactions.

---

## Isolation Behavior Diagram

```mermaid
flowchart LR
    l1[Level 1\nRC Schema + RU Instances] --> l2[Level 2\nRC Schema + RC Instances]
    l2 --> l3[Level 3\nRR Schema + RU Instances]
    l3 --> l4[Level 4\nRR Schema + RC Instances\nDefault]
    l4 --> l5[Level 5\nRR Schema + RR Instances]
    l5 --> l6[Level 6\nSerializable]

    dirty[Dirty read risk] -. highest .-> l1
    dirty -. reduced .-> l3
    dirty -. blocked .-> l2
    dirty -. blocked .-> l4
    dirty -. blocked .-> l5
    dirty -. blocked .-> l6
```

!!! warning "Isolation level changes require COMMIT"
    CUBRID applies `SET TRANSACTION ISOLATION LEVEL` with a commit boundary.
    Plan transaction scopes accordingly when switching levels at runtime.

!!! tip "Default level 4 is a balanced baseline"
    Start with `READ COMMITTED` (level 4), then move to level 5 or 6 only for correctness-critical paths.

---

*See also: [Connection Setup](CONNECTION.md) · [Feature Support](FEATURE_SUPPORT.md)*
