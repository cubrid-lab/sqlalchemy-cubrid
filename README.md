# sqlalchemy-cubrid

**SQLAlchemy 2.0–2.1 dialect for the CUBRID database** — Python ORM, schema reflection, Alembic migrations, and type mapping for SQLAlchemy and CUBRID-specific types.

[🇰🇷 한국어](docs/README.ko.md) · [🇺🇸 English](README.md) · [🇨🇳 中文](docs/README.zh.md) · [🇮🇳 हिन्दी](docs/README.hi.md) · [🇩🇪 Deutsch](docs/README.de.md) · [🇷🇺 Русский](docs/README.ru.md)

<!-- BADGES:START -->
[![PyPI version](https://img.shields.io/pypi/v/sqlalchemy-cubrid)](https://pypi.org/project/sqlalchemy-cubrid)
[![python version](https://img.shields.io/pypi/pyversions/sqlalchemy-cubrid)](https://www.python.org)
[![ci workflow](https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/workflows/ci.yml/badge.svg)](https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/workflows/ci.yml)
[![integration-full workflow](https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/workflows/integration-full.yml/badge.svg)](https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/workflows/integration-full.yml)
[![license](https://img.shields.io/github/license/cubrid-lab/sqlalchemy-cubrid)](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/cubrid-lab/sqlalchemy-cubrid)](https://github.com/cubrid-lab/sqlalchemy-cubrid)
[![docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://cubrid-lab.github.io/sqlalchemy-cubrid/)
<!-- BADGES:END -->

---

> **Status: Production/Stable** — `sqlalchemy-cubrid` is a maintained SQLAlchemy dialect for CUBRID supporting SQLAlchemy 2.0–2.1 and CUBRID 10.2–11.4.
> **Note:** Versions prior to 1.0.0 used inconsistent numbering (0.x, 2.x). The canonical version history starts at 1.0.0.

## Why sqlalchemy-cubrid?

CUBRID is a high-performance open-source relational database, widely adopted in
Korean public-sector and enterprise applications. Until now, there was no
actively maintained SQLAlchemy dialect that supports the modern 2.0–2.1 API.

**sqlalchemy-cubrid** bridges that gap:

- Full SQLAlchemy 2.0–2.1 dialect with **statement caching** and **PEP 561 typing**
- **Extensive offline test suite** — no database required to run it; CI enforces a minimum 95% line-coverage gate (`--cov-fail-under=95` in the `offline-tests` job, [CI badge above](https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/workflows/ci.yml))
- **Concurrency stress tests** — `QueuePool` sync threaded + asyncio.gather workloads validated against live CUBRID
- **SQLAlchemy 2.1-ready compat shim** — private API access wrapped in `_compat.py`; dependency pin now `>=2.0,<2.3` covering SA 2.0 and 2.1
- Tested against **4 CUBRID versions** (10.2, 11.0, 11.2, 11.4) across **Python 3.10 -- 3.14**
- CUBRID-specific DML constructs: `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`
- Alembic migration support out of the box
- **Three driver options** — pure Python (`cubrid+pycubrid://`, recommended), async pure Python (`cubrid+aiopycubrid://`), or the legacy C-extension (`cubrid://` / `cubrid+cubriddb://`)

## Support Status

- **Status**: Production/Stable [![PyPI version](https://img.shields.io/pypi/v/sqlalchemy-cubrid)](https://pypi.org/project/sqlalchemy-cubrid)
- Supported matrix: SQLAlchemy `>=2.0,<2.3`, CUBRID `10.2`, `11.0`, `11.2`, `11.4`, Python `3.10`–`3.14`
- Ordinary PRs run one Ubuntu/Python 3.12 offline smoke lane; high-risk changes add newest live integration. Main/changed-weekly runs use oldest/newest endpoints. The full supported integration matrix remains manual and release-gated. See [CI execution policy](docs/CI_POLICY.md).
- SQLAlchemy 2.1 pre-releases are exercised by a non-gating `--pre` canary CI job
- See [Known Limitations](#known-limitations) for behavior boundaries and unsupported features

## Architecture

```mermaid
flowchart TD
    app["Application"] --> sa["SQLAlchemy Core/ORM"]
    sa --> dialect["CubridDialect"]
    dialect --> pycubrid["pycubrid driver"]
    dialect --> cext["CUBRIDdb driver"]
    dialect --> aio["pycubrid.aio async driver"]
    pycubrid --> server["CUBRID Server"]
    cext --> server
    aio --> server
```

```mermaid
flowchart TD
    expr["SQL Expression"] --> compiler["CubridSQLCompiler"] --> sql["SQL String"]
```

## Requirements

**Python 3.10 support retirement:** Python 3.10 reached upstream end of life on
2026-10-01 ([PEP 619](https://peps.python.org/pep-0619/#310-lifespan)).
The current 1.8.x line and the upcoming 1.9.x advance-notice release retain Python
3.10 support. The following minor release (planned 1.10.0) will require Python
3.11 or newer, after the 1.9.0 notice has shipped. Upgrade your interpreter,
recreate your virtual environment and validate your application before upgrading
to that release. This notice does not change the current installation requirement
or add a runtime warning.

- Python 3.10+
- SQLAlchemy 2.0 – 2.1
- [pycubrid](https://github.com/cubrid-lab/pycubrid) (pure Python, recommended) **or** the legacy CUBRIDdb C extension built from [cubrid-python](https://github.com/CUBRID/cubrid-python) v11.3.0.51 or later

## Installation

```bash
pip install sqlalchemy-cubrid
```

With the pure Python driver (sync and async):

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

The `[pycubrid]` extra supports both `cubrid+pycubrid://` and
`cubrid+aiopycubrid://`. It includes SQLAlchemy's `asyncio` extra (`greenlet`);
`greenlet` may need build tools if a compatible wheel is unavailable.

With Alembic support:

```bash
pip install "sqlalchemy-cubrid[alembic]"
```

With the legacy CUBRIDdb C-extension driver (the bare `cubrid://` URL), build
CUBRIDdb from [cubrid-python](https://github.com/CUBRID/cubrid-python) v11.3.0.51 or
later; see [Driver Compatibility](docs/DRIVER_COMPAT.md#building-cubriddb-from-source).

> **The `[cubrid]` and `[cubriddb]` extras are deprecated.** They install the
> `CUBRID-Python` package from PyPI, whose newest release is 9.3.x (2015). That release is
> untested with this dialect: it returns `BIGINT` as `str` and fails parts of the
> integration suite. The dialect warns (`SAWarning`) at the first connection when it
> finds a CUBRIDdb older than 11.3. For new projects, use the recommended pure-Python
> `[pycubrid]` driver (the `cubrid+pycubrid://` URL). To select the legacy C-extension
> driver explicitly, use the `cubrid+cubriddb://` URL.

<img src="docs/demo.gif" alt="sqlalchemy-cubrid in action" width="100%"/>

## Quick Start

### Core (Connection-Level)

```python
from sqlalchemy import create_engine, text

engine = create_engine("cubrid+pycubrid://dba:password@localhost:33000/demodb")

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.scalar())
```

### ORM (Session-Level)

```python
from sqlalchemy import create_engine, String
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(200), unique=True)


engine = create_engine("cubrid+pycubrid://dba:password@localhost:33000/demodb")
Base.metadata.create_all(engine)

with Session(engine) as session:
    user = User(name="Alice", email="alice@example.com")
    session.add(user)
    session.commit()
```

### Async

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

engine = create_async_engine("cubrid+aiopycubrid://dba:password@localhost:33000/demodb")

async with AsyncSession(engine) as session:
    result = await session.execute(text("SELECT 1"))
    print(result.scalar())
```

#### Async insert with PK retrieval

CUBRID has no `RETURNING` clause. For ORM inserts, call `await session.flush()`
inside the transaction block to populate the auto-increment PK on the object before commit:

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

engine = create_async_engine("cubrid+aiopycubrid://dba:password@localhost:33000/demodb")

async with AsyncSession(engine) as session:
    async with session.begin():
        user = User(name="Alice")
        session.add(user)
        await session.flush()  # populates user.id without committing
        print(f"Inserted id={user.id}")
```

For raw Core inserts where you need the auto-increment PK, run `SELECT LAST_INSERT_ID()`
after the statement (see [Known Limitations](#known-limitations)).

## Features

- Type mapping for SQLAlchemy standard and CUBRID-specific types — numeric, string, date/time, bit, LOB, collection, and JSON types
- SQL compilation -- SELECT, JOIN, CAST, LIMIT/OFFSET, subqueries, CTEs, window functions
- DML extensions -- `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`, `FOR UPDATE`, `TRUNCATE`
- DDL support -- `COMMENT`, `IF NOT EXISTS` / `IF EXISTS`, `AUTO_INCREMENT`
- Schema reflection -- tables, views, columns, PKs, FKs, indexes, unique constraints, comments
- Alembic migrations via `CubridImpl` (registered automatically when the dialect loads)
- Three CUBRID MVCC isolation levels — `READ COMMITTED` (default), `REPEATABLE READ`, `SERIALIZABLE`
- Async support — `create_async_engine("cubrid+aiopycubrid://...")` via pycubrid.aio

## Known Limitations

- **No `RETURNING`** — `INSERT/UPDATE/DELETE ... RETURNING` not supported; for ORM use `await session.flush()` to populate `id` on the object (see [Async Quick Start](#async)), or for Core use `cursor.lastrowid` / `SELECT LAST_INSERT_ID()` after the statement
- **No sequences** — CUBRID uses `AUTO_INCREMENT` only
- **Single effective schema** — CUBRID exposes one schema per connection (the current user's schema); `get_schema_names()` reports that one schema and every reflection method honours `schema=` consistently (the default schema is reflected; any other schema yields no tables/views). Owner-qualified cross-schema reflection is not supported.
- **Uncommitted DDL holds schema locks** — CUBRID DDL is transactional (`ROLLBACK` undoes it; only client autocommit, which the dialect turns off, commits it early), so by default a whole Alembic upgrade is one transaction (`transactional_ddl = True`) and keeps the tables it touches locked until it commits; use `transaction_per_migration=True` for long or large-table migrations
- **SQLAlchemy 2.0–2.1 only** — pinned to `<2.3`; SA 2.1 pre-releases are forward-tested via shims and a `--pre` canary CI job ([details](docs/ARCHITECTURE.md))
- **Async requires pycubrid >= 1.8.0,<2.0** — the `cubrid+aiopycubrid://` driver needs the async-capable pycubrid package line currently supported by this project
- **CARDINALITY() broken** — `func.cardinality()` raises `CompileError` with workaround guidance; the CUBRID server has a [known bug](https://github.com/cubrid-lab/.github/issues/3)
- **Reserved words auto-quoted** — Column names matching CUBRID reserved words (`day`, `count`, `value`, etc.) are automatically double-quoted in DDL; see [reserved word list](https://github.com/cubrid-lab/.github/issues/5)
- **Timezone type reflection** — CUBRID's `TIMESTAMPTZ`, `TIMESTAMPLTZ`, `DATETIMETZ` and `DATETIMELTZ` reflect as distinct SQLAlchemy types (`sqlalchemy_cubrid.TIMESTAMPTZ`/`TIMESTAMPLTZ`/`DATETIMETZ`/`DATETIMELTZ`, each with `timezone=True`) rather than collapsing into plain `TIMESTAMP`/`DATETIME` (#181, #442); see [Type Mapping](docs/TYPES.md#type-reflection-ischema_names-only)

## Documentation

| Guide | Description |
|---|---|
| [Connection](docs/CONNECTION.md) | Connection strings, URL format, driver setup, pool tuning |
| [Type Mapping](docs/TYPES.md) | Full type mapping, CUBRID-specific types, collection types |
| [DML Extensions](docs/DML_EXTENSIONS.md) | ON DUPLICATE KEY UPDATE, MERGE, REPLACE INTO, query trace |
| [Isolation Levels](docs/ISOLATION_LEVELS.md) | The three CUBRID MVCC isolation levels, configuration |
| [Alembic Migrations](docs/ALEMBIC.md) | Setup, configuration, limitations, batch workarounds |
| [Feature Support](docs/FEATURE_SUPPORT.md) | Comparison with MySQL, PostgreSQL, SQLite |
| [ORM Cookbook](docs/ORM_COOKBOOK.md) | Practical ORM examples, relationships, queries |
| [Development](docs/DEVELOPMENT.md) | Dev setup, testing, Docker, coverage, CI/CD |
| [Driver Compatibility](docs/DRIVER_COMPAT.md) | CUBRID-Python driver versions and known issues |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues, error solutions, debugging techniques |
| [Async Connection](docs/CONNECTION.md#async-connection) | Async engine setup with `cubrid+aiopycubrid://` |

## Compatibility Matrix

| Component | Supported versions |
|---|---|
| Python | 3.10, 3.11, 3.12, 3.13, 3.14 |
| CUBRID | 10.2, 11.0, 11.2, 11.4 |
| SQLAlchemy | 2.0–2.1 |
| Alembic | >=1.7.2 |
| pycubrid (sync) | >=1.8.0,<2.0 |
| pycubrid (async) | >=1.8.0,<2.0 |

## FAQ

### How do I connect to CUBRID with SQLAlchemy?

```python
from sqlalchemy import create_engine
engine = create_engine("cubrid+pycubrid://dba:password@localhost:33000/demodb")
```

The recommended way is the pure-Python `pycubrid` driver: `create_engine("cubrid+pycubrid://dba:password@localhost:33000/demodb")`. The driver requires no CUBRID native libraries. The `[pycubrid]` extra also installs `greenlet` for SQLAlchemy's async bridge; it may require build tools when no compatible wheel is available. The bare `cubrid://` URL uses the legacy CUBRIDdb C-extension driver, which must be built from cubrid-python v11.3.0.51 or later (the PyPI `CUBRID-Python` 9.3.x release that the deprecated `[cubriddb]` extra installs is untested); to select it explicitly and unambiguously use `cubrid+cubriddb://`.

### Does sqlalchemy-cubrid support SQLAlchemy 2.0–2.1?

Yes. sqlalchemy-cubrid is built for SQLAlchemy 2.0–2.1 and supports the 2.0-style API including `Session.execute()`, typed `Mapped[]` columns, and statement caching.

### Does sqlalchemy-cubrid support Alembic migrations?

Yes. Install with `pip install "sqlalchemy-cubrid[alembic]"`. The CUBRID migration implementation registers itself when the dialect loads, so the default `env.py` works unchanged with synchronous URLs; for `cubrid+aiopycubrid://`, use Alembic's async template (`alembic init -t async`). CUBRID DDL is transactional, so by default a failed `alembic upgrade` is rolled back whole, version bump included; set `transaction_per_migration=True` to commit after each revision for long or large-table migrations.

### What Python versions are supported?

Python 3.10, 3.11, 3.12, 3.13, and 3.14.

### Does CUBRID support RETURNING clauses?

No. CUBRID does not support `INSERT ... RETURNING` or `UPDATE ... RETURNING`. Use `cursor.lastrowid` or `SELECT LAST_INSERT_ID()` instead.

### How do I use ON DUPLICATE KEY UPDATE with CUBRID?

```python
from sqlalchemy_cubrid import insert
stmt = insert(users).values(name="Alice").on_duplicate_key_update(name="Alice Updated")
```

### What's the difference between `cubrid://` and `cubrid+pycubrid://`?

`cubrid://` uses the C-extension driver (CUBRIDdb) which requires compilation. `cubrid+pycubrid://` uses the pure Python driver, which requires no CUBRID native libraries. The `[pycubrid]` extra includes `greenlet`, whose installation may require build tools when no compatible wheel is available. `cubrid+aiopycubrid://` uses the async variant of the pure Python driver for use with `create_async_engine` and `AsyncSession`.

> **Recommendation:** for new projects prefer `cubrid+pycubrid://` (pure Python driver, no CUBRID native libraries). The `[pycubrid]` extra's `greenlet` dependency may need build tools. Use `cubrid+cubriddb://` with CUBRIDdb built from cubrid-python v11.3.0.51 or later when you specifically need the legacy C-extension driver.

### Does sqlalchemy-cubrid support async?

Yes. Use `create_async_engine("cubrid+aiopycubrid://...")` with the pycubrid async driver. Requires `pycubrid>=1.8.0,<2.0`. Both pycubrid dialects use native `Connection.ping(False)` / `AsyncConnection.ping(False)` for `pool_pre_ping`, and all Core and ORM features work with `AsyncSession`.


## Related Projects

- [pycubrid](https://github.com/cubrid-lab/pycubrid) — Pure Python DB-API 2.0 driver for CUBRID
- [cubrid-cookbook-python](https://github.com/cubrid-lab/cubrid-cookbook-python) — Production-ready Python examples for CUBRID

## Roadmap

See [`ROADMAP.md`](ROADMAP.md) for this project's direction and next milestones.

For the ecosystem-wide view, see the [CUBRID Labs Ecosystem Roadmap](https://github.com/cubrid-lab/.github/blob/main/ROADMAP.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines and [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for development setup.

### First contribution

New to CUBRID? Pick the repository that matches what you want to work on:

- Documentation and runnable examples: [cubrid-cookbook-python](https://github.com/cubrid-lab/cubrid-cookbook-python)
- Pure-Python driver fixes: [pycubrid](https://github.com/cubrid-lab/pycubrid)
- SQLAlchemy dialect fixes: [sqlalchemy-cubrid](https://github.com/cubrid-lab/sqlalchemy-cubrid)

Most first issues can be developed and tested with the offline checks in CONTRIBUTING.md — no Docker or CUBRID server needed. Live CUBRID verification can be completed by CI and maintainers.

Browse open [`good first issue`](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22+no%3Aassignee) tasks.

## Security

Report vulnerabilities via email -- see [SECURITY.md](SECURITY.md). Do not open public issues for security concerns.

## Disclaimer

> This project is part of [CUBRID Lab](https://github.com/cubrid-lab), an independent open-source initiative for CUBRID developer tooling, and is not affiliated with, sponsored by, or endorsed by CUBRID Corporation or the official CUBRID project.


## License

MIT -- see [LICENSE](LICENSE).
