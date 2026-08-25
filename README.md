# sqlalchemy-cubrid

**SQLAlchemy 2.0–2.2 dialect for the CUBRID database** — Python ORM, schema reflection, Alembic migrations, and type mapping for SQLAlchemy and CUBRID-specific types.

[🇰🇷 한국어](docs/README.ko.md) · [🇺🇸 English](README.md) · [🇨🇳 中文](docs/README.zh.md) · [🇮🇳 हिन्दी](docs/README.hi.md) · [🇩🇪 Deutsch](docs/README.de.md) · [🇷🇺 Русский](docs/README.ru.md)

<!-- BADGES:START -->
[![PyPI version](https://img.shields.io/pypi/v/sqlalchemy-cubrid)](https://pypi.org/project/sqlalchemy-cubrid)
[![python version](https://img.shields.io/pypi/pyversions/sqlalchemy-cubrid)](https://www.python.org)
[![ci workflow](https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/workflows/ci.yml/badge.svg)](https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/workflows/ci.yml)
[![integration-full workflow](https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/workflows/integration-full.yml/badge.svg)](https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/workflows/integration-full.yml)
[![coverage](https://codecov.io/gh/cubrid-lab/sqlalchemy-cubrid/branch/main/graph/badge.svg)](https://codecov.io/gh/cubrid-lab/sqlalchemy-cubrid)
[![license](https://img.shields.io/github/license/cubrid-lab/sqlalchemy-cubrid)](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/cubrid-lab/sqlalchemy-cubrid)](https://github.com/cubrid-lab/sqlalchemy-cubrid)
[![docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://cubrid-lab.github.io/sqlalchemy-cubrid/)
<!-- BADGES:END -->

---

> **Status: Production/Stable** — `sqlalchemy-cubrid` is a maintained SQLAlchemy dialect for CUBRID supporting SQLAlchemy 2.0–2.2 and CUBRID 10.2–11.4.
> **Note:** Versions prior to 1.0.0 used inconsistent numbering (0.x, 2.x). The canonical version history starts at 1.0.0.

## Why sqlalchemy-cubrid?

CUBRID is a high-performance open-source relational database, widely adopted in
Korean public-sector and enterprise applications. Until now, there was no
actively maintained SQLAlchemy dialect that supports the modern 2.0–2.2 API.

**sqlalchemy-cubrid** bridges that gap:

- Full SQLAlchemy 2.0–2.2 dialect with **statement caching** and **PEP 561 typing**
- **Extensive offline test suite** with **high code coverage** ([CI badge above](https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/workflows/ci.yml)) — no database required to run them
- **Concurrency stress tests** — `QueuePool` sync threaded + asyncio.gather workloads validated against live CUBRID
- **SQLAlchemy 2.2-ready compat shim** — private API access wrapped in `_compat.py`; dependency pin now `>=2.0,<2.3` covering SA 2.0, 2.1, and the upcoming 2.2 release line
- Tested against **4 CUBRID versions** (10.2, 11.0, 11.2, 11.4) across **Python 3.10 -- 3.14**
- CUBRID-specific DML constructs: `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`
- Alembic migration support out of the box
- **Three driver options** — pure Python (`cubrid://` or `cubrid+pycubrid://`), async pure Python (`cubrid+aiopycubrid://`), or the legacy C-extension (`cubrid+cubriddb://`)

## Support Status

- **Status**: Production/Stable [![PyPI version](https://img.shields.io/pypi/v/sqlalchemy-cubrid)](https://pypi.org/project/sqlalchemy-cubrid)
- Supported matrix: SQLAlchemy `>=2.0,<2.3`, CUBRID `10.2`, `11.0`, `11.2`, `11.4`, Python `3.10`–`3.14`
- Integration CI exercises Python 3.10 and 3.14 against all four CUBRID versions on every PR; intermediate versions (3.11–3.13) are supported and validated via the offline test suite
- SQLAlchemy `2.2` remains canary-only until explicitly added to the supported matrix
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

- Python 3.10+
- SQLAlchemy 2.0 – 2.2
- [CUBRID-Python](https://github.com/CUBRID/cubrid-python) (C-extension) **or** [pycubrid](https://github.com/cubrid-lab/pycubrid) (pure Python)

## Installation

```bash
pip install sqlalchemy-cubrid
```

With the pure Python driver (no C build needed):

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

With Alembic support:

```bash
pip install "sqlalchemy-cubrid[alembic]"
```

With the legacy CUBRID-Python C-extension driver (requires a C build toolchain):

```bash
pip install "sqlalchemy-cubrid[cubriddb]"
```

> The `[cubrid]` extra installs the pure-Python [pycubrid](https://github.com/cubrid-lab/pycubrid)
> driver (the same as `[pycubrid]`), matching the bare `cubrid://` URL default. It
> installs with pip alone and needs no build tools.
>
> **Default driver (changed in 2.0):** the bare `cubrid://` URL now binds the
> pure-Python `pycubrid` driver. In 1.x it bound the legacy CUBRIDdb C-extension
> and emitted a `DeprecationWarning`; that warning is gone in 2.0 because the flip
> is complete. To keep the legacy CUBRIDdb C-extension driver, install the
> `[cubriddb]` extra and use the `cubrid+cubriddb://` URL.

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
- Alembic migrations via `CubridImpl` (auto-discovered entry point)
- All 6 CUBRID isolation levels (dual-granularity: class-level + instance-level)
- Async support — `create_async_engine("cubrid+aiopycubrid://...")` via pycubrid.aio

## Known Limitations

- **No `RETURNING`** — `INSERT/UPDATE/DELETE ... RETURNING` not supported; for ORM use `await session.flush()` to populate `id` on the object (see [Async Quick Start](#async)), or for Core use `cursor.lastrowid` / `SELECT LAST_INSERT_ID()` after the statement
- **No sequences** — CUBRID uses `AUTO_INCREMENT` only
- **Single effective schema** — CUBRID exposes one schema per connection (the current user's schema); `get_schema_names()` reports that one schema and every reflection method honours `schema=` consistently (the default schema is reflected; any other schema yields no tables/views). Owner-qualified cross-schema reflection is not supported.
- **DDL auto-commits** — migrations are not transactional (`transactional_ddl = False`); use Alembic batch migrations and test rollback scenarios manually
- **SQLAlchemy 2.0–2.2 only** — pinned to `<2.3`; SA 2.2 is forward-supported via shims and a `--pre` canary CI job ([details](docs/ARCHITECTURE.md))
- **Async requires pycubrid >= 1.3.2,<2.0** — the `cubrid+aiopycubrid://` driver needs the async-capable pycubrid package line currently supported by this project
- **CARDINALITY() broken** — `func.cardinality()` raises `CompileError` with workaround guidance; the CUBRID server has a [known bug](https://github.com/cubrid-lab/.github/issues/3)
- **Reserved words auto-quoted** — Column names matching CUBRID reserved words (`day`, `count`, `value`, etc.) are automatically double-quoted in DDL; see [reserved word list](https://github.com/cubrid-lab/.github/issues/5)
- **Timezone type fidelity** — CUBRID `TIMESTAMPTZ` is reflected as `TIMESTAMP`; timezone offset is preserved in the stored value but the dialect does not distinguish `TZ` vs `LTZ` semantics at the SQLAlchemy type level. In practice this means `datetime` objects round-trip correctly but explicit TZ/LTZ type introspection is not available

## Documentation

| Guide | Description |
|---|---|
| [Connection](docs/CONNECTION.md) | Connection strings, URL format, driver setup, pool tuning |
| [Type Mapping](docs/TYPES.md) | Full type mapping, CUBRID-specific types, collection types |
| [DML Extensions](docs/DML_EXTENSIONS.md) | ON DUPLICATE KEY UPDATE, MERGE, REPLACE INTO, query trace |
| [Isolation Levels](docs/ISOLATION_LEVELS.md) | All 6 CUBRID isolation levels, configuration |
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
| SQLAlchemy | 2.0–2.2 |
| Alembic | >=1.7 |
| pycubrid (sync) | >=1.3.2,<2.0 |
| pycubrid (async) | >=1.3.2,<2.0 |

## FAQ

### How do I connect to CUBRID with SQLAlchemy?

```python
from sqlalchemy import create_engine
engine = create_engine("cubrid+pycubrid://dba:password@localhost:33000/demodb")
```

The bare `cubrid://` URL uses the pure-Python `pycubrid` driver (installs with pip, no compilation): `create_engine("cubrid://dba:password@localhost:33000/demodb")`. This is the default since sqlalchemy-cubrid 2.0 (in 1.x the bare URL used the legacy CUBRIDdb C-extension and warned). To keep the legacy CUBRIDdb C-extension driver explicitly, use `cubrid+cubriddb://` with the `[cubriddb]` extra.

### Does sqlalchemy-cubrid support SQLAlchemy 2.0–2.2?

Yes. sqlalchemy-cubrid is built for SQLAlchemy 2.0–2.2 and supports the 2.0-style API including `Session.execute()`, typed `Mapped[]` columns, and statement caching.

### Does sqlalchemy-cubrid support Alembic migrations?

Yes. Install with `pip install "sqlalchemy-cubrid[alembic]"`. The dialect auto-registers via entry point. Note that CUBRID auto-commits DDL, so migrations are not transactional.

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

Since 2.0, `cubrid://` and `cubrid+pycubrid://` both use the pure-Python `pycubrid` driver, which installs with pip alone — no build tools needed. `cubrid+aiopycubrid://` uses the async variant of the pure Python driver for use with `create_async_engine` and `AsyncSession`. For the legacy C-extension driver (CUBRIDdb), use `cubrid+cubriddb://` (with the `[cubriddb]` extra), which requires compilation.

> **Note (2.0 change):** the bare `cubrid://` default driver changed from CUBRIDdb to `pycubrid` in sqlalchemy-cubrid 2.0 (1.x emitted a `DeprecationWarning`). To keep the legacy CUBRIDdb driver, use `cubrid+cubriddb://` with the `[cubriddb]` extra.

### Does sqlalchemy-cubrid support async?

Yes. Use `create_async_engine("cubrid+aiopycubrid://...")` with the pycubrid async driver. Requires `pycubrid>=1.3.2,<2.0`. Both pycubrid dialects use native `Connection.ping(False)` / `AsyncConnection.ping(False)` for `pool_pre_ping`, and all Core and ORM features work with `AsyncSession`.


## Related Projects

- [pycubrid](https://github.com/cubrid-lab/pycubrid) — Pure Python DB-API 2.0 driver for CUBRID
- [cubrid-cookbook-python](https://github.com/cubrid-lab/cubrid-cookbook-python) — Production-ready Python examples for CUBRID

## Roadmap

See [`ROADMAP.md`](ROADMAP.md) for this project's direction and next milestones.

For the ecosystem-wide view, see the [CUBRID Labs Ecosystem Roadmap](https://github.com/cubrid-lab/.github/blob/main/ROADMAP.md) and [Project Board](https://github.com/orgs/cubrid-lab/projects/2).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines and [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for development setup.

## Security

Report vulnerabilities via email -- see [SECURITY.md](SECURITY.md). Do not open public issues for security concerns.

## License

MIT -- see [LICENSE](LICENSE).
