# Troubleshooting Guide

Comprehensive solutions for common sqlalchemy-cubrid issues — connection setup, SQL compilation, type mapping, schema reflection, Alembic migrations, ORM patterns, and performance tuning.

---

## Table of Contents

- [Installation Issues](#installation-issues)
  - [ImportError: No module named 'CUBRIDdb'](#importerror-no-module-named-cubriddb)
  - [ImportError: No module named 'pycubrid'](#importerror-no-module-named-pycubrid)
  - [C Extension Build Failure](#c-extension-build-failure)
- [Connection Issues](#connection-issues)
  - [Connection Refused on Port 33000](#connection-refused-on-port-33000)
  - [Authentication Failed](#authentication-failed)
  - [Stale Connections / Disconnections](#stale-connections--disconnections)
  - [Connection Pool Exhaustion](#connection-pool-exhaustion)
  - [Wrong URL Format](#wrong-url-format)
- [SQL Compilation Issues](#sql-compilation-issues)
  - [Unsupported RETURNING Clause](#unsupported-returning-clause)
  - [Boolean Column Behavior](#boolean-column-behavior)
  - [LIMIT / OFFSET Syntax](#limit--offset-syntax)
  - [CAST Type Limitations](#cast-type-limitations)
  - [Reserved Word Conflicts](#reserved-word-conflicts)
  - [JSON Type Usage](#json-type-usage)
- [Type Mapping Issues](#type-mapping-issues)
  - [Boolean Mapped to SMALLINT](#boolean-mapped-to-smallint)
  - [Text Mapped to STRING](#text-mapped-to-string)
  - [Missing ARRAY Type](#missing-array-type)
  - [LOB Column Behavior](#lob-column-behavior)
  - [Collection Types (SET, MULTISET, SEQUENCE)](#collection-types-set-multiset-sequence)
  - [Decimal Precision](#decimal-precision)
- [Schema Reflection Issues](#schema-reflection-issues)
  - [Table Not Found During Reflection](#table-not-found-during-reflection)
  - [Case Sensitivity in Table Names](#case-sensitivity-in-table-names)
  - [View Reflection](#view-reflection)
  - [Missing Schema Support](#missing-schema-support)
- [ORM Issues](#orm-issues)
  - [autoincrement and lastrowid](#autoincrement-and-lastrowid)
  - [No Sequences — Use AUTO_INCREMENT](#no-sequences--use-auto_increment)
  - [Relationship Cascade Behavior](#relationship-cascade-behavior)
  - [Bulk Insert Performance](#bulk-insert-performance)
- [DML Extension Issues](#dml-extension-issues)
  - [ON DUPLICATE KEY UPDATE Not Working](#on-duplicate-key-update-not-working)
  - [MERGE Statement Errors](#merge-statement-errors)
  - [REPLACE INTO Behavior](#replace-into-behavior)
- [Alembic Migration Issues](#alembic-migration-issues)
  - [No Implementation Found for Dialect 'cubrid'](#no-implementation-found-for-dialect-cubrid)
  - [ALTER COLUMN TYPE Rejected (lossy conversion)](#alter-column-type-rejected-lossy-conversion)
  - [RENAME COLUMN](#rename-column)
  - [Partial Migration (DDL Auto-Commit)](#partial-migration-ddl-auto-commit)
  - [Autogenerate Not Detecting Changes](#autogenerate-not-detecting-changes)
- [Isolation Level Issues](#isolation-level-issues)
  - [Setting Isolation Levels](#setting-isolation-levels)
  - [DDL Commits Current Transaction](#ddl-commits-current-transaction)
- [Transaction Issues](#transaction-issues)
  - [Data Not Persisted](#data-not-persisted)
  - [Autocommit Conflicts](#autocommit-conflicts)
  - [Savepoint Limitations](#savepoint-limitations)
- [Performance Issues](#performance-issues)
  - [Slow Schema Reflection](#slow-schema-reflection)
  - [Connection Overhead](#connection-overhead)
  - [Statement Caching](#statement-caching)
- [Docker Issues](#docker-issues)
  - [Container Starts but Cannot Connect](#container-starts-but-cannot-connect)
  - [Database Not Created](#database-not-created)
  - [Version-Specific Behavior](#version-specific-behavior)
- [Debugging Techniques](#debugging-techniques)

---

## Installation Issues

### ImportError: No module named 'CUBRIDdb'

**Symptom:**

```
ImportError: No module named 'CUBRIDdb'
```

**Cause:** The CUBRID C-extension Python driver is not installed.

**Fix — Option A: Install the C-extension driver:**

```bash
pip install CUBRID-Python
```

> **Note:** This requires the CUBRID CCI library and a C compiler. See the [CUBRID Python driver docs](https://www.cubrid.org/manual/en/11.0/api/python.html) for platform-specific instructions.

**Fix — Option B: Use the pure Python driver instead (recommended):**

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

Then change your connection URL:

```python
# Before (C-extension)
engine = create_engine("cubrid://dba@localhost:33000/testdb")

# After (pure Python — no C build needed)
engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")
```

---

### ImportError: No module named 'pycubrid'

**Symptom:**

```
ImportError: No module named 'pycubrid'
```

**Fix:**

```bash
pip install pycubrid
# Or install both together
pip install "sqlalchemy-cubrid[pycubrid]"
```

---

### C Extension Build Failure

**Symptom:** `pip install CUBRID-Python` fails with compilation errors.

**Common causes:**
- Missing C compiler (`gcc` / `cl.exe`)
- Missing CUBRID CCI headers
- Incompatible platform

**Fix:** Use pycubrid instead — it's pure Python and requires no build tools:

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

---

## Connection Issues

### Connection Refused on Port 33000

**Symptom:**

```
OperationalError: (CUBRIDdb.DatabaseError) Connection refused
```

**Fixes:**

1. **Check the CUBRID broker is running:**

   ```bash
   cubrid broker status
   cubrid service status
   ```

2. **Docker container not ready:**

   ```bash
   docker compose up -d
   sleep 10  # Wait for full initialization
   docker compose ps  # Verify "running" status
   ```

3. **Wrong port:** Check `cubrid_broker.conf` for the actual broker port.

4. **Firewall:** Ensure port 33000 is not blocked.

---

### Authentication Failed

**Symptom:**

```
OperationalError: Authentication failed
```

**Fix:** CUBRID's default `dba` user has **no password**:

```python
# Correct — no password
engine = create_engine("cubrid://dba@localhost:33000/testdb")

# Correct — with password (if set)
engine = create_engine("cubrid://dba:mypassword@localhost:33000/testdb")
```

---

### Stale Connections / Disconnections

**Symptom:**

```
OperationalError: Connection is closed
OperationalError: broker is not available
```

**Cause:** The CUBRID broker has a `SESSION_TIMEOUT` (default ~300 seconds). Idle pooled connections expire server-side.

**Fix:** Configure pool settings:

```python
engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",
    pool_pre_ping=True,  # Native driver ping before checkout
    pool_recycle=240,     # Recycle before SESSION_TIMEOUT (300s)
)
```

For `cubrid+pycubrid://` and `cubrid+aiopycubrid://`, `pool_pre_ping=True` now uses pycubrid's native `CHECK_CAS` ping instead of issuing `SELECT 1`.

See [Connection Guide — Pool Tuning](CONNECTION.md#connection-pool-tuning) for detailed recommendations.

---

### Connection Pool Exhaustion

**Symptom:**

```
TimeoutError: QueuePool limit of size 5 overflow 10 reached
```

**Causes:**
- Connections not being returned to the pool (missing `close()` or context manager)
- Pool too small for application concurrency

**Fix:**

```python
engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
)

# Always use context managers to return connections
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
```

---

### Wrong URL Format

**Symptom:**

```
ArgumentError: Could not parse rfc1738 URL
NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:pycubrid
```

**Correct URL formats:**

```python
# C-extension driver (CUBRIDdb)
engine = create_engine("cubrid://dba@localhost:33000/testdb")
engine = create_engine("cubrid+cubrid://dba@localhost:33000/testdb")

# Pure Python driver (pycubrid)
engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")
```

**Common mistakes:**

```python
# WRONG — 'pycubrid://' is not a valid scheme
engine = create_engine("pycubrid://dba@localhost:33000/testdb")

# WRONG — port should be in the URL, not as a query parameter
engine = create_engine("cubrid://dba@localhost/testdb?port=33000")
```

---

## SQL Compilation Issues

### Unsupported RETURNING Clause

**Symptom:**

```
CompileError: RETURNING is not supported by this dialect
```

**Cause:** CUBRID does not support `INSERT ... RETURNING` or `UPDATE ... RETURNING`.

**Fix:** The dialect handles this automatically via `get_last_insert_id()` on the driver connection. You can also use `SELECT LAST_INSERT_ID()`:

```python
from sqlalchemy import insert, select, text

# Insert and get the generated ID
with engine.begin() as conn:
    result = conn.execute(
        insert(users).values(name="Alice", email="alice@example.com")
    )
    new_id = result.inserted_primary_key[0]
    print(f"New user ID: {new_id}")

# Or use LAST_INSERT_ID()
with engine.begin() as conn:
    conn.execute(text("INSERT INTO users (name) VALUES ('Alice')"))
    last_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
```

**ORM pattern:**

```python
with Session(engine) as session:
    user = User(name="Alice", email="alice@example.com")
    session.add(user)
    session.flush()  # Sends INSERT, populates user.id
    print(user.id)   # Available after flush
    session.commit()
```

---

### Boolean Column Behavior

**Symptom:** Boolean columns store/return `0` and `1` instead of `True`/`False`.

**Cause:** CUBRID has no native `BOOLEAN` type. The dialect maps `Boolean` to `SMALLINT`.

**Fix:** This is expected. SQLAlchemy automatically converts between Python `bool` and `SMALLINT(0/1)`:

```python
from sqlalchemy import Boolean
from sqlalchemy.orm import mapped_column, Mapped

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Stored as SMALLINT: True→1, False→0
    # Retrieved as bool automatically
```

**In raw SQL:**

```python
# Insert
conn.execute(text("INSERT INTO users (is_active) VALUES (:val)"), {"val": 1})

# Query — compare against 0/1
conn.execute(text("SELECT * FROM users WHERE is_active = 1"))
```

---

### LIMIT / OFFSET Syntax

**Symptom:** Unexpected query behavior with pagination.

**CUBRID supports standard `LIMIT n OFFSET m` syntax.** The dialect generates this automatically:

```python
# SQLAlchemy generates correct CUBRID LIMIT/OFFSET
stmt = select(users).limit(10).offset(20)
# → SELECT ... FROM users LIMIT 10 OFFSET 20
```

**Note:** CUBRID does not support MySQL's `LIMIT offset, count` comma syntax. The dialect always uses `LIMIT n OFFSET m`.

---

### CAST Type Limitations

**Symptom:**

```
ProgrammingError: CAST to this type is not supported
```

**Cause:** CUBRID's `CAST()` supports a limited set of target types.

**Supported CAST targets:**

| Target Type | Example |
|---|---|
| `CHAR(n)` | `CAST(col AS CHAR(10))` |
| `VARCHAR(n)` | `CAST(col AS VARCHAR(100))` |
| `NCHAR(n)` | `CAST(col AS NCHAR(10))` |
| `INTEGER` | `CAST(col AS INTEGER)` |
| `BIGINT` | `CAST(col AS BIGINT)` |
| `FLOAT` | `CAST(col AS FLOAT)` |
| `DOUBLE` | `CAST(col AS DOUBLE)` |
| `NUMERIC(p,s)` | `CAST(col AS NUMERIC(10,2))` |
| `DATE` | `CAST(col AS DATE)` |
| `TIME` | `CAST(col AS TIME)` |
| `DATETIME` | `CAST(col AS DATETIME)` |
| `TIMESTAMP` | `CAST(col AS TIMESTAMP)` |

**Unsupported:** `CAST(... AS BOOLEAN)`, `CAST(... AS BLOB)`, `CAST(... AS SET)`.

---

### Reserved Word Conflicts

**Symptom:**

```
ProgrammingError: Syntax error near 'value'
```

**Cause:** CUBRID has many reserved words that may conflict with column or table names.

**Common CUBRID reserved words:**

| Reserved Word | Safe Alternative |
|---|---|
| `value` | `val`, `item_value` |
| `count` | `cnt`, `item_count` |
| `data` | `file_data`, `raw_data` |
| `level` | `user_level` |
| `action` | `user_action` |
| `status` | `item_status` |
| `type` | `item_type` |

**Fix — The dialect auto-quotes identifiers**, but if you're using `text()` for raw SQL, quote manually:

```python
# Auto-quoting works for ORM and Core constructs
class Config(Base):
    __tablename__ = "config"
    value: Mapped[str] = mapped_column("val", String(100))  # Rename the column

# For raw SQL, use double quotes
conn.execute(text('SELECT "value" FROM config'))
```

The `CubridIdentifierPreparer` handles quoting automatically for reserved words. The full reserved word list is maintained in `base.py`.

---

### JSON Type Usage

**Status:** JSON is supported in sqlalchemy-cubrid since v1.2.0 and requires CUBRID ≥ 10.2.

**Basic usage:**

```python
from sqlalchemy import Column, MetaData, Table, select
from sqlalchemy_cubrid import JSON

metadata = MetaData()

config = Table(
    "config",
    metadata,
    Column("data", JSON),
)
```

**Path access:** `col["key"]` compiles to `JSON_EXTRACT(...)` on CUBRID.

```python
stmt = select(config.c.data["theme"])
```

**If you see this error:**

```
CompileError: JSON is not supported by this dialect
```

upgrade to `sqlalchemy-cubrid>=1.2.0`.

**Workaround for CUBRID < 10.2:** Store JSON as `VARCHAR` or `STRING` and serialize/deserialize in Python:

```python
import json
from sqlalchemy import String, TypeDecorator

class JSONType(TypeDecorator):
    """Store JSON as VARCHAR in CUBRID."""
    impl = String(4096)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None

class Config(Base):
    __tablename__ = "config"
    id: Mapped[int] = mapped_column(primary_key=True)
    settings: Mapped[dict] = mapped_column(JSONType)
```

---

## Type Mapping Issues

### Boolean Mapped to SMALLINT

See [Boolean Column Behavior](#boolean-column-behavior) above.

---

### Text Mapped to STRING

**Behavior:** SQLAlchemy's `Text` type maps to CUBRID's `STRING` type, which is equivalent to `VARCHAR(1,073,741,823)` — a very large variable-length string.

```python
from sqlalchemy import Text

class Article(Base):
    __tablename__ = "articles"
    content: Mapped[str] = mapped_column(Text)
    # → STRING in DDL (equivalent to VARCHAR(1073741823))
```

This is correct behavior. CUBRID's `STRING` type serves the same purpose as `TEXT` in MySQL/PostgreSQL.

---

### Missing ARRAY Type

**Cause:** CUBRID does not have a standard `ARRAY` type. Instead, it offers **collection types**: `SET`, `MULTISET`, and `SEQUENCE`.

```python
from sqlalchemy_cubrid import SET, MULTISET, SEQUENCE

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    tags: Mapped[str] = mapped_column(SET(String(50)))        # Unique, unordered
    categories: Mapped[str] = mapped_column(MULTISET(String(50)))  # Allows duplicates
    colors: Mapped[str] = mapped_column(SEQUENCE(String(50)))      # Ordered
```

**SQL equivalents:**

```sql
CREATE TABLE products (
    id INTEGER AUTO_INCREMENT PRIMARY KEY,
    tags SET(VARCHAR(50)),
    categories MULTISET(VARCHAR(50)),
    colors SEQUENCE(VARCHAR(50))
);
```

---

### LOB Column Behavior

**CLOB** (Character Large Object) and **BLOB** (Binary Large Object) types are supported:

```python
from sqlalchemy import LargeBinary, Text

class Document(Base):
    __tablename__ = "documents"
    content: Mapped[str] = mapped_column(Text)       # Uses STRING (CLOB-like)
    binary_data: Mapped[bytes] = mapped_column(LargeBinary)  # Uses BLOB
```

**Note:** LOB behavior depends on the driver:
- **CUBRIDdb** (C-extension): LOB columns may return raw bytes or LOB handles
- **pycubrid** (pure Python): LOB columns return a dictionary with metadata (`lob_type`, `lob_length`, `file_locator`, `packed_lob_handle`)

For simple use cases, insert strings/bytes directly and they will be stored in the LOB column.

---

### Collection Types (SET, MULTISET, SEQUENCE)

**Reflection:** When reflecting tables with collection columns, the dialect maps them back to the appropriate SQLAlchemy type:

```python
from sqlalchemy import inspect

inspector = inspect(engine)
columns = inspector.get_columns("products")
for col in columns:
    print(f"{col['name']}: {col['type']}")
    # tags: SET(VARCHAR(50))
    # categories: MULTISET(VARCHAR(50))
```

**Inserting collection data:** Use CUBRID's collection literal syntax in raw SQL:

```sql
INSERT INTO products (tags) VALUES ({'red', 'blue', 'green'});
```

---

### Decimal Precision

**Symptom:** Decimal values lose precision.

**Fix:** Use `NUMERIC(precision, scale)` for exact decimal arithmetic:

```python
from sqlalchemy_cubrid import NUMERIC

class Product(Base):
    __tablename__ = "products"
    price: Mapped[Decimal] = mapped_column(NUMERIC(10, 2))
    # Stores exactly 10 digits with 2 decimal places
```

CUBRID supports precision up to 38 digits.

---

## Schema Reflection Issues

### Table Not Found During Reflection

**Symptom:**

```
NoSuchTableError: table_name
```

**Causes:**

1. **Table doesn't exist** — verify in CUBRID directly
2. **Case sensitivity** — CUBRID folds identifiers to **lowercase** (unlike SQL standard which folds to uppercase):

   ```python
   # CUBRID stores table names in lowercase
   inspector = inspect(engine)
   tables = inspector.get_table_names()
   print(tables)  # ['users', 'products'] — all lowercase
   ```

3. **Wrong database** — ensure your connection URL points to the correct database

---

### Case Sensitivity in Table Names

**CUBRID folds unquoted identifiers to lowercase.** This differs from PostgreSQL (lowercase) and Oracle (uppercase).

```python
# These all refer to the same table
conn.execute(text("CREATE TABLE MyTable (id INT)"))  # Stored as 'mytable'
conn.execute(text("SELECT * FROM MYTABLE"))          # Finds 'mytable'
conn.execute(text("SELECT * FROM mytable"))          # Finds 'mytable'

# To preserve case, use double quotes
conn.execute(text('CREATE TABLE "MyTable" (id INT)'))  # Stored as 'MyTable'
conn.execute(text('SELECT * FROM "MyTable"'))          # Must use quotes
```

The dialect's `CubridIdentifierPreparer` handles this automatically by setting `requires_name_normalize = True` and `initial_quote = '"'`.

---

### View Reflection

**Supported.** Use `inspector.get_view_names()`:

```python
inspector = inspect(engine)
views = inspector.get_view_names()
print(views)  # ['my_view', 'active_users_view']
```

---

### Missing Schema Support

**CUBRID uses a single-schema model.** Unlike PostgreSQL, there is no concept of multiple schemas within a database.

```python
# WRONG — CUBRID doesn't support schema parameter
inspector.get_table_names(schema="public")

# CORRECT — omit schema
inspector.get_table_names()
```

If your code needs to work across databases (PostgreSQL + CUBRID), handle this with a conditional:

```python
schema = None if dialect_name == "cubrid" else "public"
tables = inspector.get_table_names(schema=schema)
```

---

## ORM Issues

### autoincrement and lastrowid

**CUBRID uses `AUTO_INCREMENT`** (not sequences) for auto-generated primary keys:

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
```

**After insert, the ID is available via `flush()`:**

```python
with Session(engine) as session:
    user = User(name="Alice")
    session.add(user)
    session.flush()
    print(user.id)  # Auto-generated ID
    session.commit()
```

The dialect implements `get_lastrowid()` in `CubridExecutionContext` which calls `raw_conn.get_last_insert_id()` (falling back to `SELECT LAST_INSERT_ID()` via SQL if the driver method is unavailable).

---

### No Sequences — Use AUTO_INCREMENT

**Symptom:**

```
CompileError: sequences are not supported by this dialect
```

**Cause:** CUBRID does not support SQL sequences. Use `AUTO_INCREMENT` columns instead:

```python
# WRONG — sequences not supported
from sqlalchemy import Sequence
id = Column(Integer, Sequence("user_id_seq"), primary_key=True)

# CORRECT — use autoincrement
id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
```

---

### Relationship Cascade Behavior

**Foreign key cascades work normally** in CUBRID:

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    posts: Mapped[list["Post"]] = relationship(back_populates="author", cascade="all, delete-orphan")

class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    author: Mapped["User"] = relationship(back_populates="posts")
```

---

### Bulk Insert Performance

**For inserting many rows**, use `insert().values()` with a list of dicts:

```python
from sqlalchemy import insert

with engine.begin() as conn:
    conn.execute(
        insert(users),
        [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
            {"name": "Charlie", "email": "charlie@example.com"},
        ],
    )
```

For very large datasets, batch inserts with `executemany()` or use `executemany_batch()` (pycubrid-specific).

---

## DML Extension Issues

### ON DUPLICATE KEY UPDATE Not Working

**Symptom:** `on_duplicate_key_update()` raises `AttributeError`.

**Cause:** You're using SQLAlchemy's built-in `insert()` instead of the dialect's custom `insert()`:

```python
# WRONG — standard SQLAlchemy insert has no on_duplicate_key_update
from sqlalchemy import insert
stmt = insert(users).values(name="Alice")
stmt = stmt.on_duplicate_key_update(name="Alice Updated")  # AttributeError!

# CORRECT — use the dialect's insert
from sqlalchemy_cubrid import insert
stmt = insert(users).values(name="Alice")
stmt = stmt.on_duplicate_key_update(name="Alice Updated")
```

**The table must have a UNIQUE or PRIMARY KEY constraint** for the duplicate detection to work.

---

### MERGE Statement Errors

**Symptom:** `MERGE` statement compilation fails.

**Checklist:**

1. **Import from the correct module:**

   ```python
   from sqlalchemy_cubrid.dml import merge
   ```

2. **All required clauses must be present:**

   ```python
   stmt = (
       merge(target)
       .using(source)                        # Required
       .on(target.c.id == source.c.id)       # Required
       .when_matched_then_update(...)        # At least one WHEN clause
       .when_not_matched_then_insert(...)
   )
   ```

3. **`when_matched_then_delete()` requires a prior `when_matched_then_update()`:**

   ```python
   # WRONG — delete without update
   merge(t).using(s).on(condition).when_matched_then_delete()

   # CORRECT — delete after update
   merge(t).using(s).on(condition).when_matched_then_update({...}).when_matched_then_delete(where=...)
   ```

---

### REPLACE INTO Behavior

**`REPLACE INTO` deletes the existing row and inserts a new one** (unlike `ON DUPLICATE KEY UPDATE` which updates in place):

```python
from sqlalchemy_cubrid import replace

# This DELETES the existing row with the conflicting key,
# then INSERTs the new row
stmt = replace(users).values(id=1, name="Alice", email="alice@new.com")
```

**Warning:** `REPLACE INTO` causes the row to get a **new auto-increment ID** if the table uses `AUTO_INCREMENT`. If you want to preserve the existing row's ID, use `ON DUPLICATE KEY UPDATE` instead.

---

## Alembic Migration Issues

### No Implementation Found for Dialect 'cubrid'

**Symptom:**

```
CommandError: No implementation found for dialect 'cubrid'
```

**Fix:** Install with the `alembic` extra:

```bash
pip install "sqlalchemy-cubrid[alembic]"
```

The `CubridImpl` class is auto-discovered via the `alembic.ddl` entry point. No manual configuration needed.

---

### ALTER COLUMN TYPE Rejected (lossy conversion)

**Symptom:**

```
Error: cannot coerce value ... (incompatible type change)
```

**CUBRID supports changing a column's data type** via native
`ALTER TABLE ... MODIFY`, which the dialect emits automatically. A change is
only rejected when it is lossy/incompatible and the
`alter_table_change_type_strict` system parameter is `yes` (when `no`, CUBRID
may silently truncate).

**Normal usage (emits native `MODIFY`):**

```python
def upgrade():
    op.alter_column("users", "name", type_=sa.String(500))
```

**Workaround for genuinely lossy conversions — use `batch_alter_table` (table recreate):**

```python
def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("name", type_=sa.String(500))

def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("name", type_=sa.String(100))
```

`batch_alter_table` creates a new table, copies data, drops the original, and renames.

---

### RENAME COLUMN

**CUBRID supports `ALTER TABLE ... RENAME COLUMN`.** The dialect emits it
natively; `alter_column(new_column_name=...)` no longer raises. A combined
rename + type change is emitted as a single `CHANGE` statement.

**Normal usage (emits native `RENAME COLUMN`):**

```python
def upgrade():
    op.alter_column("users", "old_name", new_column_name="new_name")
```

---

### Partial Migration (DDL Auto-Commit)

**Symptom:** A migration fails partway through, leaving the database in an inconsistent state.

**Cause:** CUBRID auto-commits every DDL statement (`CREATE`, `ALTER`, `DROP`). The `CubridImpl` sets `transactional_ddl = False`, meaning Alembic cannot roll back DDL operations.

**Prevention:**

1. Keep migrations small — one logical change per migration
2. Test migrations against a staging database first
3. Back up the database before running migrations

**Recovery:**

```bash
# Check current state
alembic current

# Manually fix the database, then stamp to correct revision
alembic stamp <revision_id>
```

---

### Autogenerate Not Detecting Changes

**Possible causes:**

1. **Models not imported** — Alembic's autogenerate only sees models that are imported when `env.py` runs:

   ```python
   # In env.py — import all models
   from myapp.models import Base
   target_metadata = Base.metadata
   ```

2. **Table already exists with different schema** — CUBRID reflection may not perfectly match your model definition (e.g., `VARCHAR(4096)` vs `String()`)

3. **Collection types** — changes to `SET`, `MULTISET`, `SEQUENCE` types may not be detected by autogenerate

---

## Isolation Level Issues

### Setting Isolation Levels

**CUBRID supports 6 isolation levels** (dual-granularity: class-level + instance-level):

```python
# Engine-level (applies to all connections)
engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",
    isolation_level="REPEATABLE READ",
)

# Connection-level
with engine.connect().execution_options(
    isolation_level="SERIALIZABLE"
) as conn:
    result = conn.execute(text("SELECT * FROM accounts"))
```

**Available levels:**

| SQLAlchemy Name | CUBRID Level |
|---|---|
| `"SERIALIZABLE"` | `TRAN_SERIALIZABLE` |
| `"REPEATABLE READ"` | `TRAN_REP_CLASS_REP_INSTANCE` |
| `"READ COMMITTED"` | `TRAN_REP_CLASS_COMMIT_INSTANCE` |
| `"READ UNCOMMITTED"` | `TRAN_REP_CLASS_UNCOMMIT_INSTANCE` |
| `"CUBRID READ COMMITTED"` | `TRAN_COMMIT_CLASS_COMMIT_INSTANCE` |
| `"CUBRID READ UNCOMMITTED"` | `TRAN_COMMIT_CLASS_UNCOMMIT_INSTANCE` |

---

### DDL Commits Current Transaction

**All DDL statements auto-commit in CUBRID.** This means:

```python
with engine.begin() as conn:
    conn.execute(text("INSERT INTO users (name) VALUES ('Alice')"))
    conn.execute(text("CREATE TABLE temp (id INT)"))  # AUTO-COMMITS everything!
    # The INSERT above is now committed, even if an error occurs below
    conn.execute(text("INSERT INTO users (name) VALUES ('Bob')"))
```

**Best practice:** Never mix DML and DDL in the same transaction.

---

## Transaction Issues

### Data Not Persisted

**Symptom:** Data is inserted without errors but disappears after reconnecting.

**Cause:** Missing `commit()` or not using a transaction context.

**Fix:**

```python
# Option 1: Explicit commit
with engine.connect() as conn:
    conn.execute(text("INSERT INTO users (name) VALUES ('Alice')"))
    conn.commit()

# Option 2: begin() auto-commits on success
with engine.begin() as conn:
    conn.execute(text("INSERT INTO users (name) VALUES ('Alice')"))
    # Auto-commits on successful exit

# Option 3: ORM session
with Session(engine) as session:
    session.add(User(name="Alice"))
    session.commit()
```

---

### Autocommit Conflicts

**Symptom:** Statements commit unexpectedly.

**Background:** Both CUBRID drivers default to `autocommit=True`, but the dialect sets `autocommit=False` on each new connection so SQLAlchemy can manage transactions.

**If you need true autocommit** (each statement commits immediately):

```python
with engine.connect().execution_options(
    isolation_level="AUTOCOMMIT"
) as conn:
    conn.execute(text("INSERT INTO logs (msg) VALUES ('event')"))
    # Committed immediately
```

---

### Savepoint Limitations

**CUBRID supports `SAVEPOINT` and `ROLLBACK TO SAVEPOINT`**, but does **not** support `RELEASE SAVEPOINT`. The dialect implements `do_release_savepoint()` as a no-op.

```python
with engine.begin() as conn:
    conn.execute(text("INSERT INTO users (name) VALUES ('Alice')"))
    savepoint = conn.begin_nested()
    try:
        conn.execute(text("INSERT INTO users (name) VALUES ('duplicate')"))
        savepoint.commit()
    except Exception:
        savepoint.rollback()
    # Alice's insert is still pending
    conn.commit()
```

---

## Performance Issues

### Slow Schema Reflection

**Symptom:** `inspector.get_table_names()` or `metadata.reflect()` is slow.

**Cause:** Schema reflection queries system catalogs, which can be slow with many tables.

**Fix:** Reflect only the tables you need:

```python
# SLOW — reflects ALL tables
metadata.reflect(bind=engine)

# FAST — reflect specific tables
metadata.reflect(bind=engine, only=["users", "products", "orders"])
```

---

### Connection Overhead

**Each connection performs a multi-step CAS handshake.** Use connection pooling:

```python
# Default pool (recommended for web apps)
engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",
    pool_size=5,
    pool_pre_ping=True,
)

# NullPool for scripts (no pooling)
from sqlalchemy.pool import NullPool
engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",
    poolclass=NullPool,
)
```

---

### Statement Caching

**The dialect supports SQLAlchemy's statement caching** (`supports_statement_cache = True`). This is enabled by default in SQLAlchemy 2.0 and significantly reduces compilation overhead for repeated queries.

No configuration needed — it works automatically.

---

## Docker Issues

### Container Starts but Cannot Connect

**Fix:**

```bash
# 1. Check container is actually running
docker compose ps

# 2. Wait for broker initialization (takes ~10 seconds)
docker compose up -d && sleep 10

# 3. Test connection
python3 -c "
from sqlalchemy import create_engine, text
engine = create_engine('cubrid+pycubrid://dba@localhost:33000/testdb')
with engine.connect() as conn:
    print(conn.execute(text('SELECT 1')).scalar())
"
```

---

### Database Not Created

**The Docker image only creates the database specified in `CUBRID_DB`:**

```yaml
services:
  cubrid:
    image: cubrid/cubrid:11.2
    environment:
      CUBRID_DB: testdb  # Only this database is created
    ports:
      - "33000:33000"
```

If your connection URL uses a different database name, it will fail. Match `CUBRID_DB` with your connection URL.

---

### Version-Specific Behavior

**Specify the CUBRID version explicitly:**

```bash
# Default (11.2)
docker compose up -d

# Specific version
CUBRID_VERSION=11.4 docker compose up -d
CUBRID_VERSION=10.2 docker compose up -d
```

**Known version differences:**

| Feature | CUBRID 10.2 | CUBRID 11.0+ |
|---|---|---|
| `LIMIT` in `UPDATE` | ❌ | ✅ |
| `CTE` (WITH clause) | ❌ | ✅ |
| `MERGE` | ✅ | ✅ |
| Index comments | ❌ | ✅ |

---

## Debugging Techniques

## Troubleshooting Decision Flow

```mermaid
flowchart TD
    start[Issue observed] --> kind{Primary symptom}
    kind -->|Import / Module error| install[Check driver install]
    kind -->|Connection failure| conn[Validate URL, host, port, credentials]
    kind -->|SQL compile/runtime error| sql[Inspect generated SQL and unsupported feature]
    kind -->|Migration failure| mig[Check Alembic limitations and DDL auto-commit]
    kind -->|Performance issue| perf[Check pool settings, indexes, statement patterns]

    install --> i1{CUBRIDdb or pycubrid?}
    i1 -->|CUBRIDdb| i2[Install CUBRID-Python and CCI dependencies]
    i1 -->|pycubrid| i3[Install pycubrid and use cubrid+pycubrid URL]

    conn --> c1{Broker reachable?}
    c1 -->|No| c2[Start broker / docker service and verify port 33000]
    c1 -->|Yes| c3[Enable pool_pre_ping and review SESSION_TIMEOUT]

    sql --> s1{Using unsupported feature?}
    s1 -->|RETURNING / ARRAY| s2[Refactor using supported CUBRID patterns]
    s1 -->|No| s3[Enable SQLAlchemy echo and inspect raw SQL]

    mig --> m1[Split migration into atomic DDL steps]
    perf --> p1[Profile query plan, batch size, lock scope]
```

!!! tip "Start with reproducibility"
    Reduce the failing case to a minimal script with one engine, one table, and one query.
    This quickly identifies whether the issue is driver, dialect, or application logic.

!!! warning "Distinguish compilation errors from runtime errors"
    - Compilation errors happen before SQL is sent.
    - Runtime errors come from CUBRID or the driver.
    They need different debugging paths.

!!! tip "Capture environment details in issue reports"
    Include dialect version, SQLAlchemy version, driver (`CUBRIDdb` or `pycubrid`),
    CUBRID server version, and the exact connection URL format used.

### Enable SQL Logging

```python
# Method 1: echo=True
engine = create_engine("cubrid://dba@localhost:33000/testdb", echo=True)

# Method 2: Python logging
import logging
logging.basicConfig()
logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)
```

Output includes SQL statements, parameters, and execution times.

### Check Dialect Version

```python
import sqlalchemy_cubrid
print(sqlalchemy_cubrid.__version__)  # e.g., "1.4.0"

from sqlalchemy import create_engine
engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")
print(engine.dialect.name)            # "cubrid"
print(engine.dialect.server_version_info)  # (11, 2, 0, 378)
```

### Inspect Compiled SQL

```python
from sqlalchemy.dialects import registry

# Compile a statement for CUBRID without executing
from sqlalchemy_cubrid.dialect import CubridDialect

stmt = select(users).where(users.c.name == "Alice")
compiled = stmt.compile(dialect=CubridDialect())
print(str(compiled))
print(compiled.params)
```

### Test Connection Script

```python
#!/usr/bin/env python3
"""Quick sqlalchemy-cubrid connection test."""
import sys
from sqlalchemy import create_engine, text, inspect

url = "cubrid+pycubrid://dba@localhost:33000/testdb"
try:
    engine = create_engine(url)
    with engine.connect() as conn:
        version = conn.execute(text("SELECT VERSION()")).scalar()
        print(f"✅ Connected to CUBRID {version}")

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✅ Found {len(tables)} tables: {tables[:5]}{'...' if len(tables) > 5 else ''}")

    print("✅ All checks passed")
except Exception as e:
    print(f"❌ Failed: {e}")
    sys.exit(1)
```

---

*See also: [Connection Guide](CONNECTION.md) · [Type Mapping](TYPES.md) · [DML Extensions](DML_EXTENSIONS.md) · [Alembic](ALEMBIC.md) · [Feature Support](FEATURE_SUPPORT.md)*
