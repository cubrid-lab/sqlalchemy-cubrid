# sqlalchemy-cubrid

**SQLAlchemy 2.0–2.1 dialect for the CUBRID database** — Python ORM, schema reflection, Alembic migrations, and type mapping for SQLAlchemy and CUBRID-specific types.

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

> **Status: Production/Stable** — `sqlalchemy-cubrid` is a maintained SQLAlchemy dialect for CUBRID supporting SQLAlchemy 2.0–2.1 and CUBRID 10.2–11.4.
> **Note:** Versions prior to 1.0.0 used inconsistent numbering (0.x, 2.x). The canonical version history starts at 1.0.0.

## Why sqlalchemy-cubrid?

CUBRID is a high-performance open-source relational database, widely adopted in
Korean public-sector and enterprise applications. Until now, there was no
actively maintained SQLAlchemy dialect that supports the modern 2.0–2.1 API.

**sqlalchemy-cubrid** bridges that gap:

- Full SQLAlchemy 2.0–2.1 dialect with **statement caching** and **PEP 561 typing**
- **Extensive offline test suite** with **high code coverage** ([CI badge above](https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/workflows/ci.yml)) — no database required to run them
- **Concurrency stress tests** — `QueuePool` sync threaded + asyncio.gather workloads validated against live CUBRID
- **SQLAlchemy 2.1-ready compat shim** — private API access wrapped in `_compat.py`; dependency pin now `>=2.0,<2.3` covering SA 2.0 and 2.1
- Tested against **4 CUBRID versions** (10.2, 11.0, 11.2, 11.4) across **Python 3.10 -- 3.14**
- CUBRID-specific DML constructs: `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`
- Alembic migration support out of the box
- **Three driver options** — pure Python (`cubrid+pycubrid://`, recommended), async pure Python (`cubrid+aiopycubrid://`), or the legacy C-extension (`cubrid://` / `cubrid+cubriddb://`)

## Support Status

- **Status**: Production/Stable [![PyPI version](https://img.shields.io/pypi/v/sqlalchemy-cubrid)](https://pypi.org/project/sqlalchemy-cubrid)
- Supported matrix: SQLAlchemy `>=2.0,<2.3`, CUBRID `10.2`, `11.0`, `11.2`, `11.4`, Python `3.10`–`3.14`
- Integration CI exercises Python 3.10 and 3.14 against all four CUBRID versions on every PR; intermediate versions (3.11–3.13) are supported and validated via the offline test suite
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

- Python 3.10+
- SQLAlchemy 2.0 – 2.1
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
pip install "sqlalchemy-cubrid[cubrid]"
```

> The `[cubrid]` extra installs the legacy [CUBRID-Python](https://github.com/CUBRID/cubrid-python)
> C-extension driver, which is the driver bound to the bare `cubrid://` URL. For new
> projects, prefer the pure-Python `[pycubrid]` driver (the `cubrid+pycubrid://` URL) —
> it installs with pip alone, needs no build tools, and is the recommended driver for
> this dialect. To select the legacy C-extension driver explicitly and unambiguously,
> use the `cubrid+cubriddb://` URL together with the `[cubriddb]` install extra.

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
- Three CUBRID MVCC isolation levels — `READ COMMITTED` (default), `REPEATABLE READ`, `SERIALIZABLE`
- Async support — `create_async_engine("cubrid+aiopycubrid://...")` via pycubrid.aio

## Known Limitations

- **No `RETURNING`** — `INSERT/UPDATE/DELETE ... RETURNING` not supported; for ORM use `await session.flush()` to populate `id` on the object (see [Async Quick Start](#async)), or for Core use `cursor.lastrowid` / `SELECT LAST_INSERT_ID()` after the statement
- **No sequences** — CUBRID uses `AUTO_INCREMENT` only
- **Single effective schema** — CUBRID exposes one schema per connection (the current user's schema); `get_schema_names()` reports that one schema and every reflection method honours `schema=` consistently (the default schema is reflected; any other schema yields no tables/views). Owner-qualified cross-schema reflection is not supported.
- **DDL auto-commits** — migrations are not transactional (`transactional_ddl = False`); use Alembic batch migrations and test rollback scenarios manually
- **SQLAlchemy 2.0–2.1 only** — pinned to `<2.3`; SA 2.1 pre-releases are forward-tested via shims and a `--pre` canary CI job ([details](docs/ARCHITECTURE.md))
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
| Alembic | >=1.7 |
| pycubrid (sync) | >=1.3.2,<2.0 |
| pycubrid (async) | >=1.3.2,<2.0 |

## FAQ

### How do I connect to CUBRID with SQLAlchemy?

```python
from sqlalchemy import create_engine
engine = create_engine("cubrid+pycubrid://dba:password@localhost:33000/demodb")
```

The recommended way is the pure-Python `pycubrid` driver, which installs with pip alone (no compilation): `create_engine("cubrid+pycubrid://dba:password@localhost:33000/demodb")`. The bare `cubrid://` URL uses the legacy `CUBRID-Python` C-extension driver (requires a C build toolchain); to select it explicitly and unambiguously use `cubrid+cubriddb://` with the `[cubriddb]` extra.

### Does sqlalchemy-cubrid support SQLAlchemy 2.0–2.1?

Yes. sqlalchemy-cubrid is built for SQLAlchemy 2.0–2.1 and supports the 2.0-style API including `Session.execute()`, typed `Mapped[]` columns, and statement caching.

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

`cubrid://` uses the C-extension driver (CUBRIDdb) which requires compilation. `cubrid+pycubrid://` uses the pure Python driver which installs with pip alone — no build tools needed. `cubrid+aiopycubrid://` uses the async variant of the pure Python driver for use with `create_async_engine` and `AsyncSession`.

> **Recommendation:** for new projects prefer `cubrid+pycubrid://` (pure Python, no build tools). Use `cubrid+cubriddb://` (with the `[cubriddb]` extra) when you specifically need the legacy CUBRIDdb C-extension driver.

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

## Disclaimer

> This project is part of [CUBRID Lab](https://github.com/cubrid-lab), an independent open-source initiative for CUBRID developer tooling, and is not affiliated with, sponsored by, or endorsed by CUBRID Corporation or the official CUBRID project.


## License

MIT -- see [LICENSE](LICENSE).
