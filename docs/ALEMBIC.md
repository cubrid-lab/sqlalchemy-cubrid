# Alembic Migration Support

Guide for using [Alembic](https://alembic.sqlalchemy.org/) database migrations with the CUBRID dialect.

---

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Running Migrations](#running-migrations)
- [CUBRID-Specific Behavior](#cubrid-specific-behavior)
- [Limitations & Workarounds](#limitations--workarounds)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

---

## Installation

Install sqlalchemy-cubrid with the `alembic` extra:

```bash
pip install sqlalchemy-cubrid[alembic]
```

This pulls in Alembic ≥ 1.7.2 as a dependency. The CUBRID Alembic implementation
(`CubridImpl`) is registered automatically when the CUBRID dialect loads —
no manual configuration is needed.

> **Note**: If you install Alembic separately (`pip install alembic`), the
> CUBRID implementation is still registered as long as `sqlalchemy-cubrid`
> is installed in the same environment.

---

## Configuration

### Initialize Alembic

```bash
alembic init alembic
```

This creates an `alembic/` directory and an `alembic.ini` configuration file.

### Set the Database URL

Edit `alembic.ini`:

```ini
[alembic]
sqlalchemy.url = cubrid://dba:password@localhost:33000/demodb
```

Or set it dynamically in `alembic/env.py`:

```python
from sqlalchemy import create_engine

def run_migrations_online():
    connectable = create_engine("cubrid://dba:password@localhost:33000/demodb")

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()
```

### env.py Setup

The `CubridImpl` class is registered as soon as any CUBRID URL loads the
dialect, so `env.py` never needs a CUBRID import. Which template to start from
depends on the driver:

- **Synchronous URLs** (`cubrid://`, `cubrid+cubriddb://`,
  `cubrid+pycubrid://`): the standard `env.py` from `alembic init` works
  without modification.
- **Async URL** (`cubrid+aiopycubrid://`): use Alembic's async template,
  `alembic init -t async <dir>`. Its generated `env.py` also works without
  modification. The standard template's online path calls the synchronous
  `engine_from_config()`, which cannot drive the async driver and fails with
  `sqlalchemy.exc.MissingGreenlet`; offline `--sql` mode works with either
  template. Verified on CUBRID 11.4 with Alembic 1.7.2 and 1.20.0:
  `upgrade head` / `downgrade base` through an unmodified async-template
  `env.py` (covered by `test/test_alembic_registration.py`).

A minimal `env.py` for online migrations:

```python
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

# Import your models' metadata
from myapp.models import Base

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
```

---

## Running Migrations

### Create a Migration

```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "add users table"

# Create an empty migration
alembic revision -m "custom migration"
```

### Apply Migrations

```bash
# Upgrade to the latest version
alembic upgrade head

# Upgrade to a specific revision
alembic upgrade abc123

# Downgrade one step
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history --verbose
```

---

## CUBRID-Specific Behavior

### Transactional DDL

CUBRID DDL is transactional. With client autocommit off — the dialect turns it
off on every connection — `CREATE TABLE`, `ALTER TABLE`, `DROP TABLE`,
`TRUNCATE`, `CREATE INDEX` (including `WITH ONLINE [PARALLEL n]`),
`CREATE VIEW`, `CREATE SERIAL` and `RENAME TABLE` run inside the current
transaction: `ROLLBACK` undoes them, and they never commit DML issued earlier in
the same transaction (see the
[CUBRID manual](https://www.cubrid.org/manual/en/11.4/sql/transaction.html),
where `ROLLBACK WORK` undoes an `ALTER TABLE … DROP`). The only auto-commit
behavior in CUBRID is client autocommit (`CCI_DEFAULT_AUTOCOMMIT`, or csql's
default auto-commit mode), which commits after every statement, DDL or DML.

`CubridImpl` therefore sets `transactional_ddl = True`, which tells Alembic:

- **The whole `alembic upgrade` runs in one transaction** by default. If any
  revision fails, every revision in that run is rolled back, including the
  `alembic_version` update, so the database stays at its starting revision.
- With `transaction_per_migration=True` in `context.configure()`, each
  revision runs and commits in its own transaction instead: revisions that
  finished stay applied, and the failing revision is rolled back as a whole.
- `context.is_transactional_ddl()` returns `True`.

**Schema locks.** Uncommitted DDL keeps its schema lock on the table until the
transaction ends, so other sessions that touch the table wait (as `SCH_S_LOCK`
waits) for the whole transaction; CUBRID's default `lock_timeout` is unlimited,
so they wait indefinitely rather than time out. For long migrations, or
migrations on large tables, set `transaction_per_migration=True` so each revision commits and
releases its locks as soon as it finishes:

```python
# env.py
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    transaction_per_migration=True,
)
```

Alembic's `autocommit_block()` is not a way to commit part of an upgrade early on
CUBRID: it switches the connection to the `AUTOCOMMIT` isolation level, which the
dialect does not accept before #501, and it gives up the upgrade's atomicity.
Use `transaction_per_migration=True` to commit between revisions instead.

**Offline (`--sql`) scripts.** CUBRID has no `BEGIN` statement (csql rejects it
with `Syntax error: unexpected 'BEGIN'`); a transaction starts implicitly. The
CUBRID implementation therefore emits no `BEGIN;` and ends each transaction with
`COMMIT;` (one per upgrade, or one per revision with
`transaction_per_migration=True`). Run the script with both
`--no-auto-commit` and `--no-single-line`:

```bash
csql -u dba demodb --no-auto-commit --no-single-line -i upgrade.sql
```

`--no-auto-commit` makes those `COMMIT;` lines the only commit points; in csql's
default auto-commit mode every statement commits on its own. `--no-single-line`
makes csql stop at the first failing statement and exit with status 1, so the
open transaction is rolled back: nothing from the whole upgrade (or, with
`transaction_per_migration=True`, from the failing revision) is kept. In csql's
default single-line mode, csql reports the error, **continues with the next
statements, runs the trailing `COMMIT;` and exits 0**, so a failed script can
leave partial schema and a bumped `alembic_version`.

!!! note "Changed in 1.8.0"
    Earlier releases set `transactional_ddl = False`. Alembic still wrapped each
    revision in its own transaction in online mode, so each revision was already
    atomic, but a failed `upgrade` kept the revisions before it. Now the whole
    upgrade is atomic by default; set `transaction_per_migration=True` to keep the
    previous per-revision behavior.

### Auto-Registration

Alembic picks its migration implementation from a registry keyed by
`dialect.name`; a `DefaultImpl` subclass adds itself to that registry when its
module is imported (`CubridImpl.__dialect__ = "cubrid"`). Alembic does not load
dialect implementations from package entry points.

`sqlalchemy_cubrid/dialect.py` therefore imports `sqlalchemy_cubrid.alembic_impl`
when Alembic is installed (and skips it silently when it is not). Every CUBRID
URL — `cubrid://`, `cubrid+cubriddb://`, `cubrid+pycubrid://` and
`cubrid+aiopycubrid://` — loads that module and has `dialect.name == "cubrid"`,
so building the engine (or, in offline `--sql` mode, the dialect from the URL)
registers `CubridImpl` before Alembic looks it up. No imports or configuration
are required in `env.py` or your migration files.

Because of this, loading the CUBRID dialect imports Alembic whenever Alembic is
installed, even in applications that never run a migration. That import takes
roughly 0.1 s, and Alembic 1.18 and later log seven `INFO` lines from the
`alembic.runtime.plugins` logger while importing (`setup plugin
alembic.autogenerate.schemas`, ..., `setup plugin
alembic.ext.checkconstraint_byname`). They are Alembic's own messages and appear
on the first CUBRID engine or dialect only when the application routes `INFO`
records to a handler, for example with `logging.basicConfig(level=logging.INFO)`.
The dialect leaves the `alembic` logger alone, since its level is the
application's choice. To hide the lines, raise that logger's level in the
application's logging setup:

```python
import logging

logging.getLogger("alembic").setLevel(logging.WARNING)
```

Alembic offers no supported way to defer the registration until a migration
runs: `DefaultImpl.get_by_dialect()` is a plain lookup in the registry, and the
`alembic.plugins` entry points (Alembic 1.18+) load on every `import alembic`
and do not exist on the older supported versions.

If Alembic is installed but fails to import (for example Alembic 1.7.0/1.7.1,
which raise `NameError` on SQLAlchemy 2.x), the dialect still loads and emits a
single `RuntimeWarning` saying the Alembic integration is disabled, with the
original exception. If a warning filter turns that warning into an error
(`-W error`), the message is logged through the `sqlalchemy_cubrid.dialect`
logger instead, so the dialect still loads. Upgrading to
`alembic>=1.7.2,<2.0` fixes it.

Versions before this fix declared an `alembic.ddl` entry point that Alembic
never read, so a default `env.py` failed with `KeyError: 'cubrid'` unless it
imported `sqlalchemy_cubrid.alembic_impl` explicitly. That import is harmless
and can stay.

### Implementation Details

```python
class CubridImpl(DefaultImpl):
    __dialect__ = "cubrid"
    transactional_ddl = True

    def emit_begin(self):
        # CUBRID has no BEGIN statement; offline scripts only emit COMMIT;
        pass
```

The implementation inherits all standard Alembic operations from `DefaultImpl`:
- `add_column`, `drop_column`
- `add_constraint`, `drop_constraint`
- `create_table`, `drop_table`
- `create_index`, `drop_index`
- `alter_column` (type change, rename, nullable, default — all native)
- `bulk_insert`

---

## Limitations & Workarounds

Creating a UNIQUE index through Alembic requires a live connection so the dialect
can inspect CUBRID's FK auto-indexes and detect collisions. Without a connection,
the guard raises `CompileError` with a live-connection requirement; it does not
silently skip validation. Non-unique index generation is unaffected.

### ✅ ALTER COLUMN TYPE (native)

CUBRID supports changing a column's data type in place via `MODIFY`:

```sql
-- This works:
ALTER TABLE users MODIFY COLUMN name BIGINT;
```

**In Alembic**, `alter_column(type_=...)` emits native
`ALTER TABLE ... MODIFY <col> <definition>`. Because CUBRID's `MODIFY`
restates the *entire* column definition, the dialect reconstructs the full
definition (`NOT NULL` / `DEFAULT` / `AUTO_INCREMENT` / `COMMENT`) from the
`existing_*` metadata Alembic supplies, so existing attributes are not
silently dropped:

```python
def upgrade():
    op.alter_column("users", "name", type_=sa.BigInteger())
```

!!! warning "Lossy conversions may be rejected"
    Incompatible or truncating conversions may be rejected by the server
    depending on the `alter_table_change_type_strict` system parameter (when
    `yes`, incompatible/truncating conversions raise an error; when `no`,
    CUBRID may silently truncate). For genuinely lossy or unsupported
    conversions, fall back to `batch_alter_table` (table recreate):

    ```python
    def upgrade():
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column("name", type_=sa.BigInteger())
    ```

### ✅ RENAME COLUMN (native)

CUBRID supports renaming columns via `RENAME COLUMN`:

```sql
-- This works:
ALTER TABLE users RENAME COLUMN old_name TO new_name;
```

**In Alembic**, `alter_column(new_column_name=...)` emits native
`ALTER TABLE ... RENAME COLUMN old TO new`. When a rename is combined with a
type change, the dialect emits `ALTER TABLE ... CHANGE old new <definition>`
in a single statement:

```python
def upgrade():
    op.alter_column("users", "old_name", new_column_name="new_name")
```

### ⚠️ Long migrations hold schema locks

DDL is transactional (see [Transactional DDL](#transactional-ddl)), so a failed
upgrade rolls back cleanly. The cost is that each DDL statement keeps its schema
lock until the transaction commits. Be aware:

- By default the whole upgrade is one transaction, so every table it touches
  stays locked until the last revision finishes
- Use `transaction_per_migration=True` for long migrations or large tables
- Test migrations against a staging database before production
- Maintain database backups before running migrations

### `alter_column()` behavior

The CUBRID Alembic implementation maps `alter_column()` to native CUBRID DDL:

- `type_=` changes → `MODIFY` (or `CHANGE` when combined with a rename)
- `new_column_name=` renames → `RENAME COLUMN` (or `CHANGE` with a type change)
- `nullable=` / `server_default=` / comment changes routed through `DefaultImpl`

Type changes reconstruct the full column definition from `existing_*` metadata
so that attributes such as `NOT NULL` / `DEFAULT` / `COMMENT` are preserved.

> **Important — hand-written type-changing migrations must pass `existing_*`.**
> Because CUBRID's `MODIFY` / `CHANGE` restate the *entire* column definition,
> the dialect can only preserve an attribute it is told about. Alembic
> autogenerate populates `existing_type`, `existing_nullable`,
> `existing_server_default`, and `existing_comment` from the reflected column,
> but a manual `op.alter_column(..., type_=...)` does **not**. When editing a
> migration by hand, pass `existing_nullable=`, `existing_server_default=`,
> `existing_comment=`, and `existing_autoincrement=` for any attribute that must
> survive the type change — otherwise it will be dropped. To *intentionally*
> remove an attribute (e.g. a default), pass it explicitly (`server_default=None`),
> which overrides the `existing_*` value.

### Summary

| Operation | Supported | Workaround |
|---|:---:|---|
| `create_table` | ✅ | — |
| `drop_table` | ✅ | — |
| `add_column` | ✅ | — |
| `drop_column` | ✅ | — |
| `alter_column` (nullable) | ✅ | — |
| `alter_column` (default) | ✅ | — |
| `alter_column` (type) | ✅ | `batch_alter_table` for lossy conversions |
| `alter_column` (rename) | ✅ | — |
| `create_index` | ✅ | `if_not_exists=True` raises `CompileError` (CUBRID has no `CREATE INDEX IF NOT EXISTS`); check `inspect(conn).has_index()` first instead |
| `drop_index` | ✅ | Emits `DROP INDEX <name> ON <table>`, so `table_name` is required (`CompileError` without it); `if_exists=True` raises `CompileError` (CUBRID has no `DROP INDEX IF EXISTS`) |
| `add_constraint` | ✅ | — |
| `drop_constraint` | ✅ | — |
| `bulk_insert` | ✅ | — |
| Transactional DDL | ✅ | `transaction_per_migration=True` for long or large-table migrations |

---

## Examples

### Create a Table

```python
"""create users table

Revision ID: 001
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(200), unique=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_users_email", "users", ["email"])


def downgrade():
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
```

### Add a Column

```python
def upgrade():
    op.add_column("users", sa.Column("is_active", sa.SmallInteger(), server_default="1"))


def downgrade():
    op.drop_column("users", "is_active")
```

### Change Column Type (via batch)

```python
def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("name", type_=sa.String(500))


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("name", type_=sa.String(100))
```

### Rename Column (via batch)

```python
def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("name", new_column_name="full_name")


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("full_name", new_column_name="name")
```

---

## Troubleshooting

### "No implementation found for dialect 'cubrid'"

**Cause**: `sqlalchemy-cubrid` is not installed, or not installed with the
`alembic` extra.

**Fix**:

```bash
pip install sqlalchemy-cubrid[alembic]
```

### `INFO` log lines `setup plugin alembic...` when using the dialect

Alembic 1.18+ logs these while it is imported, and the CUBRID dialect imports
Alembic when it is installed. Set `logging.getLogger("alembic").setLevel(logging.WARNING)`
in the application; see [Auto-Registration](#auto-registration).

### "Alembic is required for migration support"

**Cause**: The `alembic_impl` module was imported directly without Alembic
installed.

**Fix**:

```bash
pip install "alembic>=1.7.2,<2.0"
```

### Migration partially applied

**Cause**: CUBRID DDL is transactional, so a failed online upgrade does not leave
a half-applied revision: the failing transaction is rolled back. By default that
is the whole upgrade; with `transaction_per_migration=True` it is the failing
revision, and the revisions before it stay committed and recorded in
`alembic_version`. Partial state can still come from:

- client autocommit, which commits every statement: driver-level autocommit, csql's default auto-commit mode, or `isolation_level="AUTOCOMMIT"` where the dialect accepts it (#501);
- an offline (`--sql`) script run without `csql --no-auto-commit --no-single-line`
  (csql's default single-line mode continues past a failing statement and still
  runs the trailing `COMMIT;`);
- a revision that calls `COMMIT` itself (for example through `op.execute`).

**Fix**:
1. Manually inspect the database state
2. Either complete the remaining operations manually, or reverse the
   completed ones
3. Stamp the revision to the correct state: `alembic stamp <revision>`

### `alter_column` type change rejected by the server

**Cause**: A lossy or incompatible type conversion when the
`alter_table_change_type_strict` system parameter is `yes`.

**Fix**: For genuinely lossy/unsupported conversions, use `batch_alter_table` — see [ALTER COLUMN TYPE (native)](#-alter-column-type-native).

### `alembic revision --autogenerate` fails with a reflection error

**Cause**: Foreign keys are read from `SHOW CREATE TABLE`. Since #589 a failure
there (a dropped connection, an authorization error, a driver error) raises
instead of being reported as "this table has no foreign keys", which made
autogenerate propose `add_fk` for foreign keys that already exist.

**Fix**: Fix the underlying error and run autogenerate again; set
`pool_pre_ping=True` on the engine if the connection went stale. A `NoSuchTableError`
for a table of another owner is expected since CUBRID 11.2, where an unqualified name
resolves in the current user's schema; run autogenerate as the table owner.

---

## Migration Safety Checklist

!!! note "DDL is transactional"
    CUBRID rolls back DDL with the transaction; only client autocommit commits it early.
    By default a failed `alembic upgrade` leaves no partial schema and no version bump.
    Uncommitted DDL holds schema locks, so use `transaction_per_migration=True` for
    long or large-table migrations.

!!! warning "Lossy type changes may be rejected by the server"
    `alter_column(type_=...)` and `alter_column(new_column_name=...)` emit native
    CUBRID DDL (`MODIFY` / `RENAME COLUMN` / `CHANGE`). Only genuinely lossy or
    incompatible type conversions are rejected (governed by
    `alter_table_change_type_strict`); for those, use `op.batch_alter_table()`
    with tested downgrade steps.

!!! tip "Always test upgrade + downgrade on staging"
    Validate full forward and backward migration chains before production rollout.

!!! tip "Create backups for destructive operations"
    Back up data before `drop_column`, `drop_table`, or multi-step restructuring migrations.

### Pre-Migration Checklist

Before running migrations in production:

- [ ] **Plan lock duration** — DDL holds schema locks until commit, and by default the whole upgrade is one transaction. Use `transaction_per_migration=True` for long or large-table migrations.
- [ ] **No client autocommit** — don't run migrations with client autocommit on (driver-level autocommit, csql's default auto-commit mode, or `isolation_level="AUTOCOMMIT"` where the dialect accepts it (#501)), and run offline scripts with `csql --no-auto-commit --no-single-line`, so a failure rolls back cleanly.
- [ ] **Backup database** — `cubrid backupdb demodb` before destructive operations
- [ ] **Test upgrade + downgrade cycle** — run `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` on staging
- [ ] **Verify state after each step** — query `db_class` system table to confirm schema matches expectations
- [ ] **Maintenance window** — schedule high-impact migrations during low-traffic periods
- [ ] **Rollback script ready** — for each `upgrade()`, have a tested manual rollback SQL if `downgrade()` is insufficient

### Recommended Pre-Deploy Sequence

1. `cubrid backupdb demodb` — create a full backup
2. `alembic upgrade head` on a staging copy
3. Run smoke tests and critical queries against staging
4. `alembic downgrade -1` and `alembic upgrade head` to verify reversibility
5. Deploy during a maintenance window for high-impact schema changes
6. Monitor `alembic current` post-deploy to confirm expected revision

### Advisory CI Safety Check

Add the following script to list revisions with several DDL operations. This is advisory
(warning-only) and does not block CI. Such revisions still roll back as a whole on failure,
but they hold schema locks longer. The script counts calls to Alembic DDL operations, including
constraint creation (`create_unique_constraint`, `create_foreign_key`, `create_check_constraint`,
`create_primary_key`), in each `upgrade()` and `downgrade()` separately; bare references such as
`op.drop_table` without a call are not counted. It is a heuristic, not a control-flow analysis:

```python
#!/usr/bin/env python3
"""Check Alembic revisions for multiple DDL operations (advisory).

CUBRID DDL is transactional, so a failing revision is rolled back as a
whole. Every DDL statement holds a schema lock on its table until the
transaction commits, though, so this lists revisions with several DDL
calls: they keep tables locked longer and are candidates for running with
``transaction_per_migration=True`` or for splitting.

Only calls such as ``op.create_table(...)`` or ``batch_op.add_column(...)``
count; a bare reference like ``op.drop_table`` is not a DDL operation. This is
a heuristic AST scan, not control-flow analysis: a call in a loop or branch
counts once, as written, and DDL issued from helpers defined outside
``upgrade()``/``downgrade()`` is not seen.

Usage:
    python scripts/alembic_safety_check.py alembic/versions/
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

DDL_CALLS = {
    "create_table", "drop_table", "add_column", "drop_column",
    "create_index", "drop_index", "alter_column",
    "add_constraint", "drop_constraint",
    "create_unique_constraint", "create_foreign_key",
    "create_check_constraint", "create_primary_key",
}


def check_revision(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    warnings = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name not in ("upgrade", "downgrade"):
            continue
        ddl_count = sum(
            1 for node in ast.walk(func)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in DDL_CALLS
        )
        if ddl_count > 1:
            warnings.append(
                f"{path.name}:{func.name}() has {ddl_count} DDL operations "
                "(schema locks are held until the transaction commits)"
            )
    return warnings


def main() -> None:
    versions_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("alembic/versions")
    if not versions_dir.is_dir():
        print(f"Directory not found: {versions_dir}")
        sys.exit(1)

    all_warnings = []
    for py_file in sorted(versions_dir.glob("*.py")):
        all_warnings.extend(check_revision(py_file))

    if all_warnings:
        print("⚠️  Alembic safety warnings (advisory):")
        for w in all_warnings:
            print(f"  • {w}")
        print(f"\nTotal: {len(all_warnings)} warning(s)")
        print(
            "Tip: these revisions roll back whole on failure but hold schema locks "
            "until commit; use transaction_per_migration=True for long or "
            "large-table migrations."
        )
    else:
        print("✓ No revision has more than one DDL call per function.")


if __name__ == "__main__":
    main()
```

Example CI integration (`.github/workflows/ci.yml`):

```yaml
- name: Alembic safety check (advisory)
  run: python scripts/alembic_safety_check.py alembic/versions/ || true
```

### Rollback Script Template

For critical migrations, create a companion rollback SQL file:

```sql
-- rollback_001_add_users_table.sql
-- Manual rollback for revision abc123 (add users table)
-- Use if alembic downgrade fails or is insufficient.

DROP TABLE IF EXISTS users;

-- Verify: SELECT class_name FROM db_class WHERE class_name = 'users';
-- Expected: no rows
```

Store rollback scripts in `alembic/rollbacks/` alongside your versions directory.

---

*See also: [Connection Guide](CONNECTION.md) · [Type Mapping](TYPES.md) · [Feature Support](FEATURE_SUPPORT.md)*
