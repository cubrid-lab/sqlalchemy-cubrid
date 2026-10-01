# Connection & Driver Setup

This guide covers how to install the CUBRID Python driver, configure SQLAlchemy connection strings, and understand the connection lifecycle.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installing the CUBRID Python Driver](#installing-the-cubrid-python-driver)
- [Connection String Format](#connection-string-format)
- [Entry Points](#entry-points)
- [How the Dialect Translates URLs](#how-the-dialect-translates-urls)
- [Connection Options](#connection-options)
- [Autocommit Behavior](#autocommit-behavior)
- [Server Version Detection](#server-version-detection)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Requirement        | Version         |
|--------------------|-----------------|
| Python             | 3.10+           |
| SQLAlchemy         | 2.0 – 2.1       |
| CUBRID Server      | 10.2 – 11.4     |
| CUBRID Python Driver | pycubrid (recommended) or CUBRIDdb built from cubrid-python v11.3.0.51+ (legacy) |

---

## Installing the CUBRID Python Driver

### Recommended: Pure Python Driver (pycubrid)

For new projects, use the pure-Python [pycubrid](https://github.com/cubrid-lab/pycubrid)
driver. It requires no CUBRID native libraries. Install the recommended extra:

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

This extra supports both sync and async pycubrid URLs and includes
SQLAlchemy's `asyncio` dependencies (`greenlet`). The driver itself is pure Python;
`greenlet` may require build tools when no compatible wheel is available.

Or install separately:

```bash
pip install sqlalchemy-cubrid pycubrid
```

Then use the `cubrid+pycubrid://` URL scheme:

```python
engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")
```

> **Tip**: The `pycubrid` driver itself is pure Python and requires no native libraries.
> The `[pycubrid]` extra also installs `greenlet`, which may need build tools.
> See [pycubrid on GitHub](https://github.com/cubrid-lab/pycubrid).

### Legacy: C-extension Driver (CUBRIDdb)

The legacy CUBRIDdb C-extension driver from
[cubrid-python](https://github.com/CUBRID/cubrid-python) is the driver bound to the bare
`cubrid://` URL; select it explicitly with the `cubrid+cubriddb://` URL scheme. The
supported way to install it is to build cubrid-python v11.3.0.51 or later from source,
see [Building CUBRIDdb from Source](DRIVER_COMPAT.md#building-cubriddb-from-source), and
then install the dialect on its own:

```bash
pip install sqlalchemy-cubrid
```

> **Warning**: do not install the driver from PyPI (`pip install CUBRID-Python`, or the
> deprecated `[cubrid]` / `[cubriddb]` extras). PyPI only has `CUBRID-Python` 9.3.x, which
> is untested with this dialect: it returns `BIGINT` as `str` and fails parts of the
> integration suite. A `cubrid://` engine emits a `SAWarning` at its first connection
> when the loaded CUBRIDdb is older than 11.3. See
> [PyPI `CUBRID-Python` 9.3.x is not supported](DRIVER_COMPAT.md#pypi-cubrid-python-93x-is-not-supported).
---

## Connection String Format

SQLAlchemy uses standard URL-style connection strings:

```
cubrid://user:password@host:port/database
```

### Examples

```python
from sqlalchemy import create_engine

# Basic connection
engine = create_engine("cubrid://dba:password@localhost:33000/demodb")

# Without password (CUBRID allows passwordless dba access by default)
engine = create_engine("cubrid://dba@localhost:33000/testdb")

# With explicit driver name (C-extension)
engine = create_engine("cubrid+cubrid://dba:password@localhost:33000/demodb")

# Using pycubrid pure Python driver
engine = create_engine("cubrid+pycubrid://dba:password@localhost:33000/demodb")
```

### URL Components

| Component  | Default     | Description                            |
|------------|-------------|----------------------------------------|
| `user`     | *(required)* | Database username (typically `dba`)   |
| `password` | *(empty)*   | Database password                      |
| `host`     | `localhost` | CUBRID server hostname or IP           |
| `port`     | `33000`     | CUBRID broker port                     |
| `database` | *(required)* | Database name                         |

### URL Query Options

`cubrid+pycubrid://` and `cubrid+aiopycubrid://` forward these URL query options to
`pycubrid.connect()` / `pycubrid.aio.connect()`, converted from the query string to
the type pycubrid expects:

```python
engine = create_engine(
    "cubrid+pycubrid://dba@localhost:33000/demodb?connect_timeout=5&read_timeout=30"
)
```

| Option | Value | Description |
|--------|-------|-------------|
| `connect_timeout` | positive number of seconds | Timeout for opening the broker connection |
| `read_timeout` | positive number of seconds | Socket read timeout after connecting |
| `fetch_size` | integer >= 1 | Server-side fetch batch size (pycubrid default `100`) |
| `charset` | codec name | Python codec, or CUBRID `utf8` / `euckr` / `iso88591`; set it to the database charset. Requires a pycubrid release newer than 1.8.0 ([cubrid-lab/pycubrid#510](https://github.com/cubrid-lab/pycubrid/pull/510)); with pycubrid 1.8.0, `create_engine()` raises `ArgumentError` naming the installed version |
| `ssl` | boolean | `true` enables TLS with pycubrid's default context (TLS 1.2+); pass an `ssl.SSLContext` through `connect_args` for anything else |
| `decode_collections` | boolean | Decode `SET` / `MULTISET` / `SEQUENCE` values into Python collections |
| `no_backslash_escapes` | boolean | pycubrid's own string-escape mode (auto-detected when omitted). This is not the `create_engine(no_backslash_escapes=...)` dialect option described [below](#backslash-escaping-no_backslash_escapes), which controls `literal_binds` rendering |
| `enable_timing` | boolean | pycubrid timing statistics |

Booleans accept `true`/`false`, `yes`/`no`, `on`/`off` and `1`/`0`. An invalid value,
a repeated option, `host` / `port` / `database` / `user` / `password` (set them in the
URL itself), `autocommit` (use `isolation_level="AUTOCOMMIT"`) and `json_deserializer`
(pass it through `connect_args`) raise `sqlalchemy.exc.ArgumentError` from
`create_engine()`. Any other key is ignored with pycubrid's
`UnknownConnectionOptionWarning`, which suggests the closest supported option;
`warnings.simplefilter("error", pycubrid.UnknownConnectionOptionWarning)` makes it an
error. `connect_args` values override URL query options.

The `cubrid://` / `cubrid+cubriddb://` (CUBRIDdb) dialect does not read the URL query
string: CUBRIDdb's `connect(url, user, password)` takes no keyword options, and any
query options are ignored.

---

## Entry Points

The dialect registers these SQLAlchemy entry points:

| URL Scheme           | Driver      | Description                          |
|----------------------|-------------|--------------------------------------|
| `cubrid://`          | CUBRIDdb    | Default legacy C-extension driver    |
| `cubrid+cubrid://`   | CUBRIDdb    | Explicit legacy C-extension driver   |
| `cubrid+cubriddb://` | CUBRIDdb    | Explicit legacy C-extension driver   |
| `cubrid+pycubrid://` | pycubrid    | Pure Python driver (no CUBRID native libraries) |
| `cubrid+aiopycubrid://` | pycubrid.aio | Async pure Python driver          |

For new projects prefer `cubrid+pycubrid://` (pure Python driver, no CUBRID native libraries). The `[pycubrid]` extra's `greenlet` dependency may need build tools when no compatible wheel is available. The bare `cubrid://` URL binds the legacy CUBRIDdb C-extension driver, built from cubrid-python v11.3.0.51 or later; to select it explicitly use `cubrid+cubriddb://`.
---

## Async Connection

For async applications, use the `cubrid+aiopycubrid://` URL scheme with `create_async_engine`. Requires `pycubrid>=1.8.0,<2.0`.

Install `sqlalchemy-cubrid[pycubrid]` to include the driver and SQLAlchemy's async
bridge. If installing the packages separately, also install `SQLAlchemy[asyncio]`.

```python
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

engine = create_async_engine("cubrid+aiopycubrid://dba@localhost:33000/testdb")

async with engine.connect() as conn:
    result = await conn.execute(text("SELECT 1"))
    print(result.scalar())
```

### Async insert with PK retrieval

CUBRID has no `RETURNING` clause. To obtain an auto-increment primary key after an
async ORM insert, call `await session.flush()` inside the transaction block to populate
the PK on the object before commit:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))

engine = create_async_engine("cubrid+aiopycubrid://dba@localhost:33000/testdb")

async with AsyncSession(engine) as session:
    async with session.begin():
        user = User(name="Alice")
        session.add(user)
        await session.flush()  # populates user.id without committing
        print(f"Inserted id={user.id}")
```

For Core-level inserts where you need the PK, run `SELECT LAST_INSERT_ID()` after the
statement (see README → Known Limitations).

## How the Dialect Translates URLs

Internally, the dialect converts SQLAlchemy URLs to the CUBRID native connection format:

```
SQLAlchemy URL:  cubrid://dba:password@myhost:33000/mydb
                        ↓
CUBRID native:   CUBRID:myhost:33000:mydb:::
```

The `create_connect_args()` method returns `(connect_url, username, password)` as positional arguments to the CUBRID Python driver's `connect()` function.

### Translation Details

```python
# CUBRIDdb (C-extension driver):
connect_url = f"CUBRID:{host}:{port}:{database}:::"
args = (connect_url, username, password)
# → CUBRIDdb.connect("CUBRID:myhost:33000:mydb:::", "dba", "password")
```

The trailing `:::` in the CUBRID connection string represents three empty optional parameters (reserved for future use by CUBRID).

### pycubrid Translation

The pycubrid dialect passes keyword arguments directly:

```python
# pycubrid (pure Python driver):
kwargs = {"host": host, "port": port, "database": database, "user": user, "password": password}
# → pycubrid.connect(host="myhost", port=33000, database="mydb", user="dba", password="password")
```

[URL query options](#url-query-options) are added to these keyword arguments.

---

## Connection Options

### Engine-Level Options

```python
engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",

    # Set default isolation level for all connections
    isolation_level="REPEATABLE READ",

     # SQLAlchemy 2.0–2.1 connection pool settings
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,

    # Enable SQL logging
    echo=True,
)
```

### Per-Connection Isolation Level

```python
with engine.connect().execution_options(
    isolation_level="SERIALIZABLE"
) as conn:
    # This connection uses SERIALIZABLE isolation
    result = conn.execute(text("SELECT * FROM accounts"))
```

See [Isolation Levels](ISOLATION_LEVELS.md) for all supported levels.

### Backslash Escaping (`no_backslash_escapes`)

CUBRID's `no_backslash_escapes` system parameter defaults to `yes`, meaning a
backslash is a **literal character** in string literals (the opposite of MySQL).
The dialect matches this default: inline SQL literals rendered with
`literal_binds=True` preserve backslashes as-is and do **not** double them.

```python
# Default: backslash preserved (no_backslash_escapes=yes on the server)
engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")
```

If your server is explicitly configured with `no_backslash_escapes=no` (backslash
acts as an escape character), pass `no_backslash_escapes=False` so the dialect
doubles backslashes when rendering inline literals:

```python
# Server configured with no_backslash_escapes=no
engine = create_engine(
    "cubrid+pycubrid://dba@localhost:33000/testdb",
    no_backslash_escapes=False,
)
```

This is a static dialect option (not connection-negotiated) because
`literal_binds` compilation may run offline with no live connection. It only
affects inline literal rendering; parameter-bound values are always escaped
correctly by the driver regardless of this setting.

---

## Autocommit Behavior

### Driver Default vs. Dialect Override

Both CUBRID Python drivers default to `autocommit=True`. The dialect overrides this on every new connection so that SQLAlchemy can manage transactions properly. CUBRIDdb uses `conn.set_autocommit(False)`; pycubrid uses the property setter `conn.autocommit = False`.

### No Statement-Text Autocommit

The dialect does not inspect SQL text to decide when to commit. SQLAlchemy 2.x
never consults the 1.x-era `should_autocommit_text()` hook, so DML and DDL
(including `INSERT`, `REPLACE`, `MERGE`, `CREATE`, and `DROP`) run inside the
connection's transaction and are committed only through the SQLAlchemy 2.x
Connection API: `conn.commit()`, an `engine.begin()` block, or a `Session`
commit. A connection closed without committing is rolled back.

---

## Server Version Detection

The dialect queries the server version on initialization:

```sql
SELECT VERSION()
```

The result (e.g., `11.2.0.0374`) is parsed into a tuple `(11, 2, 0, 374)` for internal version checks.

---

## Troubleshooting

### Common Connection Errors

#### `ImportError: No module named 'CUBRIDdb'`

The CUBRIDdb C-extension driver that the `cubrid://` URL uses is not installed. Switch
to the recommended pure-Python driver:

```bash
pip install "sqlalchemy-cubrid[pycubrid]"   # then use cubrid+pycubrid://
```

or build CUBRIDdb from cubrid-python v11.3.0.51 or later, see
[Building CUBRIDdb from Source](DRIVER_COMPAT.md#building-cubriddb-from-source). The
`CUBRID-Python` 9.3.x release on PyPI is untested with this dialect.

#### `Connection refused` on port 33000

1. Verify the CUBRID broker is running:
   ```bash
   cubrid broker status
   ```

2. Check the broker port in `cubrid_broker.conf` — default is `33000`.

3. If using Docker:
   ```bash
   docker compose up -d
   docker compose logs cubrid
   ```

#### `Authentication failed`

CUBRID's default `dba` user has no password. If you set one, ensure it matches your connection string:

```python
# If dba has no password
engine = create_engine("cubrid://dba@localhost:33000/testdb")

# If dba has a password
engine = create_engine("cubrid://dba:mypassword@localhost:33000/testdb")
```

### Docker Quick Start

For local development, use the provided `docker-compose.yml`:

```bash
# Start CUBRID 11.2 (default)
docker compose up -d

# Start a specific version
CUBRID_VERSION=11.4 docker compose up -d

# Verify it's running
docker compose ps

# Connect
python -c "
from sqlalchemy import create_engine, text
engine = create_engine('cubrid://dba@localhost:33000/testdb')
with engine.connect() as conn:
    print(conn.execute(text('SELECT VERSION()')).scalar())
"
```

---

## Connection Pool Tuning

SQLAlchemy manages a connection pool by default. Understanding how CUBRID interacts with the pool is important for production deployments.

### Key Pool Parameters

```python
from sqlalchemy import create_engine

engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",

    # Pool size: number of persistent connections to keep
    pool_size=5,           # Default: 5

    # Overflow: additional connections allowed beyond pool_size
    max_overflow=10,       # Default: 10

    # Timeout: seconds to wait for a connection from the pool
    pool_timeout=30,       # Default: 30

    # Recycle: seconds before a connection is replaced
    # Set this LOWER than CUBRID broker's SESSION_TIMEOUT
    pool_recycle=1800,     # Recommended: 1800 (30 minutes)

    # Pre-ping: test connection liveness before checkout
    pool_pre_ping=True,    # Recommended: True for production
)
```

### `pool_pre_ping` (Recommended)

When `pool_pre_ping=True`, SQLAlchemy calls `do_ping()` on each connection before handing it to your application. The CUBRIDdb dialect uses the native `connection.ping()` method from the CUBRID Python driver. Both pycubrid dialects now use the native `Connection.ping(False)` / `AsyncConnection.ping(False)` `CHECK_CAS` path from pycubrid, avoiding an extra `SELECT 1` round trip while still preventing stale-connection errors.

This prevents "stale connection" errors that occur when:
- The CUBRID broker restarts
- Network interruptions occur
- The broker's `SESSION_TIMEOUT` expires

```python
# Production-recommended configuration
engine = create_engine(
    "cubrid://dba@localhost:33000/mydb",
    pool_pre_ping=True,
    pool_recycle=1800,
)
```

### `pool_recycle` and CUBRID Broker Timeout

CUBRID's broker has a `SESSION_TIMEOUT` setting (default varies by version, typically 300 seconds). If a pooled connection sits idle longer than this timeout, the broker will close it server-side.

**Always set `pool_recycle` lower than `SESSION_TIMEOUT`** to avoid stale connections:

```python
# If CUBRID broker SESSION_TIMEOUT is 300 (5 minutes)
engine = create_engine(
    "cubrid://dba@localhost:33000/mydb",
    pool_recycle=240,  # Recycle before broker timeout
)
```

### Disconnect Detection

The dialect implements `is_disconnect()` which detects connection failures using a layered strategy that is resilient to driver error-message wording changes:

1. **Numeric error code matching (primary)** — checks the CCI and CAS codes that CUBRIDdb raises for a dead or unusable connection: `CCI_ER_COMMUNICATION` (-20004), `CAS_ER_COMMUNICATION` (-10003), `CCI_ER_CON_HANDLE` (-20002), `CCI_ER_CONNECT` (-20016) and `CAS_ER_NO_MORE_MEMORY` (-10002; the CAS closes the connection after sending it), plus the server codes for which the CUBRID broker resets the CAS because its session with `cub_server` is gone: `ER_TM_SERVER_DOWN_UNILATERALLY_ABORTED` (-111), `ER_NET_SERVER_CRASHED` (-199), `ER_OBJ_NO_CONNECT` (-224) and `ER_BO_CONNECT_FAILED` (-677). CUBRIDdb carries the code in `args[0]`; pycubrid carries it in `errno`, matched against these four server codes plus -1002, the legacy renumbering of `CAS_ER_NO_MORE_MEMORY` that pycubrid actually receives (CUBRID's CAS adds 9000 to CAS codes for drivers, like pycubrid, that don't advertise understanding its renewed error-code protocol). Codes are read only from these structured fields, never from message text: a message that starts with a number, such as a server error quoting application data (`-20004 rows rejected ...`), carries no code (#608). Other server codes are not disconnects: -4 is `ER_INTERRUPTED`, a query interrupted by `KILL QUERY`, and the connection stays usable. See [Troubleshooting — Errors After a cub_server Restart or Crash](TROUBLESHOOTING.md#errors-after-a-cub_server-restart-or-crash).
2. **Explicit `OSError` cause chain (wording-independent)** — if any `OSError` (e.g. a socket error) appears in the exception's explicit `__cause__` chain (a `raise ... from`), the connection is treated as dropped regardless of the message text. Implicit `__context__` is deliberately ignored so an unrelated in-flight `OSError` does not falsely invalidate a live connection.
3. **Message matching (fallback)** — checks error messages for known disconnect patterns (e.g., "connection is closed", "broker is not available", "connection reset") to cover the legacy CUBRIDdb driver and pycubrid's client-side string-only errors (e.g. "connection lost during receive", or "reconnecting failed" when pycubrid cannot replace a lost CAS session) that carry neither a code nor an `OSError` cause. Patterns are matched against the driver's own message (pycubrid's `args[0]`), not pycubrid's `str()`, which appends a description of `errno` such as `Communication error` for -4 (the server's `ER_INTERRUPTED`) and -671.

Detection is deliberately conservative: a database error with no disconnect code, no `OSError` cause, and a non-disconnect message (e.g. an invalid-isolation-level error or a closed-cursor misuse) is **not** treated as a disconnect, avoiding false-positive pool invalidation.

When a disconnect is detected, SQLAlchemy automatically invalidates the connection and creates a new one from the pool.

### Error Code Mapping

CUBRID driver exceptions are mapped to appropriate SQLAlchemy exception types. Both drivers expose the full PEP 249 exception hierarchy:

| CUBRID Driver Exception | SA Exception Mapping |
|---|---|
| `Error` (base) | `DBAPIError` |
| `InterfaceError` | `InterfaceError` |
| `DatabaseError` | `DatabaseError` |
| `DataError` | `DataError` |
| `OperationalError` | `OperationalError` |
| `IntegrityError` | `IntegrityError` |
| `InternalError` | `InternalError` |
| `ProgrammingError` | `ProgrammingError` |
| `NotSupportedError` | `NotSupportedError` |

> **Note**: CUBRIDdb 11.3.0.51 and pycubrid both provide every PEP 249 exception class above; SQLAlchemy wraps the class the driver raises. Which class a given server error gets depends on the driver, for example NOT NULL and foreign-key violations on released pycubrid. See [Driver Compatibility](DRIVER_COMPAT.md#exception-hierarchy).

### Pool Configuration Recommendations

| Scenario | `pool_size` | `pool_recycle` | `pool_pre_ping` |
|---|---|---|---|
| Development | 2 | -1 (disabled) | False |
| Web application | 5–10 | 1800 | True |
| High-concurrency | 10–20 | 900 | True |
| Background workers | 2–5 | 600 | True |

### NullPool for Short-Lived Scripts

For scripts or one-off tasks, disable pooling entirely:

```python
from sqlalchemy.pool import NullPool

engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",
    poolclass=NullPool,
)
```

---

## Connection URL Parsing Flow

```mermaid
flowchart TD
    input[SQLAlchemy URL string] --> parse[SQLAlchemy URL parser]
    parse --> check{Driver name}
    check -->|cubrid or cubrid+cubrid or cubrid+cubriddb| cext[Build CUBRID native DSN]
    check -->|cubrid+pycubrid| pykw[Build pycubrid kwargs]
    check -->|cubrid+aiopycubrid| aio[Build pycubrid.aio kwargs]
    cext --> connect1["CUBRIDdb.connect(url, user, password)"]
    pykw --> connect2["pycubrid.connect(host, port, database, user, password)"]
    aio --> connect3["pycubrid.aio.connect(...)"]
    connect1 --> session[Dialect on_connect sets autocommit=False]
    connect2 --> session
    connect3 --> session
```

!!! warning "Use the correct dialect prefix"
    `pycubrid://...` is not a valid SQLAlchemy URL scheme.
    Always use `cubrid+pycubrid://...`.

!!! warning "Do not pass broker port as query string"
    Use `...@host:33000/dbname`, not `...?port=33000`.

!!! tip "Prefer `pool_pre_ping=True` in production"
    This prevents stale connection failures after broker restarts or idle timeout expiration.

---

*See also: [Isolation Levels](ISOLATION_LEVELS.md) · [Type Mapping](TYPES.md) · [Feature Support](FEATURE_SUPPORT.md)*
