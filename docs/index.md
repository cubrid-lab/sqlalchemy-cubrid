# sqlalchemy-cubrid

SQLAlchemy 2.0–2.1 dialect for CUBRID, built for production-ready Core and ORM workloads.

> 한국어: [문서 홈](ko/index.md)

## Start here

New to CUBRID or to SQLAlchemy? Follow
[Your First SQLAlchemy Connection to CUBRID](QUICKSTART.md). It explains what
you need (CUBRID is a separate database server; installing the Python packages
does not install it), how to start a disposable local database with Docker, and
takes you to a first query and a first saved row on the recommended
`sqlalchemy-cubrid[pycubrid]` path.

## About this documentation

This site is the **development documentation**: it is rebuilt from the `main`
branch on every change, independently of package releases, so it can describe
changes that no published release contains yet. The version number in the
source (`__version__`) is not a release either: it can name a release
candidate, or a version that was abandoned and never published (1.11.1 is one).
<!-- docs-source-revision -->

- **Published releases** are listed on
  [GitHub Releases](https://github.com/cubrid-lab/sqlalchemy-cubrid/releases)
  and [PyPI](https://pypi.org/project/sqlalchemy-cubrid/#history); `pip install
  sqlalchemy-cubrid` installs the newest one. A release is listed in both as soon
  as it is uploaded, before the post-publication cookbook check runs. Only the
  publisher's `published and verified` result shows that this check passed too;
  reconciliation then marks the release PR `autorelease: tagged`.
- **Documentation of a published release** is the `docs/` folder at its tag:
  open the release on
  [GitHub Releases](https://github.com/cubrid-lab/sqlalchemy-cubrid/releases)
  and browse its tag's files, for example
  [`v1.11.0`](https://github.com/cubrid-lab/sqlalchemy-cubrid/tree/v1.11.0/docs).
- **Tested versions** are stated by each guide next to its commands, with the
  date and whether a published package or a source build was used. The
  [Quick Start](QUICKSTART.md) was run with published releases from PyPI.

## Key features

- Native SQLAlchemy 2.0–2.1 dialect support with statement caching
- CUBRID-specific DML support including `ON DUPLICATE KEY UPDATE`, `MERGE`, and `REPLACE INTO`
- Complete type system coverage and schema reflection support
- Built-in Alembic migration integration for CUBRID
- Driver choice: pure Python (`cubrid+pycubrid://`, recommended, sync and async) or the CUBRIDdb C extension (`cubrid://`)

## Quick install

Recommended, with the pure Python driver:

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

The dialect alone, for example to pair it with the CUBRIDdb C extension built
from source ([Driver Compatibility](DRIVER_COMPAT.md)):

```bash
pip install sqlalchemy-cubrid
```

## Minimal example

This uses the [quickstart's local lab](QUICKSTART.md#option-b-i-need-a-disposable-local-database)
(database `testdb`, user `dba` with no password); put your own values in the URL
for any other database.

```python
from sqlalchemy import create_engine, text

engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")
with engine.connect() as conn:
    print(conn.execute(text("SELECT 1 + 1")).scalar())  # 2
engine.dispose()
```

## Documentation sections

- [Start here: your first connection](QUICKSTART.md)
- [Connection Guide](CONNECTION.md)
- [User Guide](TYPES.md)
- [Reference](FEATURE_SUPPORT.md)

## Project links

- [GitHub](https://github.com/cubrid-lab/sqlalchemy-cubrid)
- [PyPI](https://pypi.org/project/sqlalchemy-cubrid/)
- [Changelog](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/CHANGELOG.md)
- [Contributing](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/CONTRIBUTING.md)

## Ecosystem

Part of the cubrid-lab Python ecosystem:

- pycubrid — Pure-Python DB-API 2.0 driver for CUBRID (sync + native asyncio)
- **sqlalchemy-cubrid** — SQLAlchemy 2.0–2.1 dialect + Alembic
- cubrid-cookbook-python — 68 runnable examples and application templates
- cubrid-mcp-server — MCP server — natural-language access for LLM clients
