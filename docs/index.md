# sqlalchemy-cubrid

SQLAlchemy 2.0–2.1 dialect for CUBRID, built for production-ready Core and ORM workloads.

## Key features

- Native SQLAlchemy 2.0–2.1 dialect support with statement caching
- CUBRID-specific DML support including `ON DUPLICATE KEY UPDATE`, `MERGE`, and `REPLACE INTO`
- Complete type system coverage and schema reflection support
- Built-in Alembic migration integration for CUBRID
- Dual driver support: C-extension (`cubrid://`) and pure Python (`cubrid+pycubrid://`)

## Quick install

```bash
pip install sqlalchemy-cubrid
```

Pure Python driver option:

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

## Minimal example

```python
from sqlalchemy import create_engine, text
engine = create_engine("cubrid://dba:password@localhost:33000/demodb")
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    row = result.fetchone()
    print(row[0])
```

## Documentation sections

- [Getting Started](CONNECTION.md)
- [User Guide](TYPES.md)
- [Reference](FEATURE_SUPPORT.md)

## Project links

- [GitHub](https://github.com/cubrid-lab/sqlalchemy-cubrid)
- [PyPI](https://pypi.org/project/sqlalchemy-cubrid/)
- [Changelog](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/CHANGELOG.md)
- [Contributing](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/CONTRIBUTING.md)
