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

This pulls in Alembic ≥ 1.7 as a dependency. The CUBRID Alembic implementation
(`CubridImpl`) is registered automatically via the `alembic.ddl` entry point —
no manual configuration is needed.

> **Note**: If you install Alembic separately (`pip install alembic`), it will
> still auto-discover the CUBRID implementation as long as `sqlalchemy-cubrid`
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

The standard Alembic `env.py` works without modification. The `CubridImpl`
class is auto-discovered when the connection URL uses the `cubrid://` scheme.

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

### DDL Auto-Commit

CUBRID implicitly commits every DDL statement. The `CubridImpl` sets
`transactional_ddl = False`, which tells Alembic:

- **No transaction wrapping** around DDL statements
- Each `CREATE TABLE`, `ALTER TABLE`, `DROP TABLE` commits immediately
- A failed migration may leave the database in a partially-migrated state

**Implication**: If a migration with multiple DDL operations fails halfway
through, you cannot simply roll back — the earlier operations have already
been committed. Write migrations with small, atomic steps.

### Auto-Discovery

The dialect registers `CubridImpl` via the `alembic.ddl` entry point in
`pyproject.toml`:

```toml
[project.entry-points."alembic.ddl"]
cubrid = "sqlalchemy_cubrid.alembic_impl:CubridImpl"
```

When Alembic detects a `cubrid://` connection URL, it automatically loads
`CubridImpl`. No imports or configuration are required in your migration files.

### Implementation Details

```python
class CubridImpl(DefaultImpl):
    __dialect__ = "cubrid"
    transactional_ddl = False
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

### ⚠️ DDL Auto-Commit

As noted above, DDL is auto-committed. Be aware:

- Keep migrations small (one logical change per migration)
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
so that attributes such as `NOT NULL` / `DEFAULT` / `COMMENT` are preserved.

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
| `create_index` | ✅ | — |
| `drop_index` | ✅ | — |
| `add_constraint` | ✅ | — |
| `drop_constraint` | ✅ | — |
| `bulk_insert` | ✅ | — |
| Transactional DDL | ❌ | Small atomic migrations |

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

### "Alembic is required for migration support"

**Cause**: The `alembic_impl` module was imported directly without Alembic
installed.

**Fix**:

```bash
pip install "alembic>=1.7,<2.0"
```

### Migration partially applied

**Cause**: A migration with multiple DDL statements failed partway through.
Because CUBRID auto-commits DDL, some statements already took effect.

**Fix**:
1. Manually inspect the database state
2. Either complete the remaining operations manually, or reverse the
   completed ones
3. Stamp the revision to the correct state: `alembic stamp <revision>`

### `alter_column` type change rejected by the server

**Cause**: A lossy or incompatible type conversion when the
`alter_table_change_type_strict` system parameter is `yes`.

**Fix**: For genuinely lossy/unsupported conversions, use `batch_alter_table` — see [ALTER COLUMN TYPE (native)](#-alter-column-type-native).

---

## Migration Safety Checklist

!!! warning "DDL is not transactional"
    CUBRID auto-commits DDL. A failed migration can leave partial schema changes applied.
    Prefer small revisions with one logical schema change each.

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

- [ ] **One DDL operation per revision** — since each DDL auto-commits, a failure mid-revision leaves partial state. Split multi-DDL revisions.
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

Add the following script to catch multi-DDL revisions early. This is advisory (warning-only)
and does not block CI:

```python
#!/usr/bin/env python3
"""Check Alembic revisions for multiple DDL operations (advisory).

Warns when a single revision contains multiple DDL calls, which is risky
with CUBRID's non-transactional DDL.

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
}


def check_revision(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    warnings = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name not in ("upgrade", "downgrade"):
            continue
        ddl_count = sum(
            1 for node in ast.walk(func)
            if isinstance(node, ast.Attribute) and node.attr in DDL_CALLS
        )
        if ddl_count > 1:
            warnings.append(
                f"{path.name}:{func.name}() has {ddl_count} DDL operations "
                f"(recommended: 1 per revision for CUBRID)"
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
        print("Tip: Split multi-DDL revisions to avoid partial migration state.")
    else:
        print("✓ All revisions have single DDL operations per function.")


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
