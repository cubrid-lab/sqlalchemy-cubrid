# Quick Start

Get a working SQLAlchemy + CUBRID application running in minutes.

---

## Prerequisites

Before you start, make sure the following are available:

- CUBRID server (running and reachable)
- Python 3.10+
- One supported driver configuration:
  - `cubrid://` via CUBRID-Python (C-extension)
  - `cubrid+pycubrid://` via pycubrid
  - `cubrid+aiopycubrid://` via pycubrid.aio

```bash
pip install sqlalchemy-cubrid
# or: pip install "sqlalchemy-cubrid[pycubrid]"
```

---

## Install the Dialect

```bash
pip install sqlalchemy-cubrid
```

---

## Connection URL Format

Use one of the supported URL formats:

```text
cubrid://user:password@host:port/database
cubrid+pycubrid://user:password@host:port/database
cubrid+aiopycubrid://user:password@host:port/database
```

Example:

```python
from sqlalchemy import create_engine

engine = create_engine("cubrid://dba@localhost:33000/testdb")
```

---

## Dialect Stack

```mermaid
flowchart TD
    app[Application Code] --> sa[SQLAlchemy 2.0–2.1]
    sa --> dialect[sqlalchemy-cubrid]
    dialect --> cext[CUBRIDdb]
    dialect --> pure[pycubrid]
    dialect --> aio[pycubrid.aio]
    cext --> db[(CUBRID Server)]
    pure --> db
    aio --> db
```

---

## SQLAlchemy Core Example

```python
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    insert,
    select,
)

engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb", echo=True)
metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(100), nullable=False),
)

# Create table
metadata.create_all(engine)

# Insert row
with engine.begin() as conn:
    conn.execute(insert(users).values(name="Alice"))

# Select rows
with engine.connect() as conn:
    rows = conn.execute(select(users.c.id, users.c.name).order_by(users.c.id)).all()
    print(rows)
```

---

## SQLAlchemy ORM Example

```python
from __future__ import annotations

from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users_orm"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb", echo=True)
Base.metadata.create_all(engine)

with Session(engine) as session:
    # Create
    session.add(User(name="Bob"))
    session.commit()

    # Read
    bob = session.scalars(select(User).where(User.name == "Bob")).one()

    # Update
    bob.name = "Bob Updated"
    session.commit()

    # Delete
    session.delete(bob)
    session.commit()
```

---

## Common Gotchas

!!! warning "No RETURNING support"
    CUBRID does not support `INSERT ... RETURNING` or `UPDATE ... RETURNING`.
    SQLAlchemy handles primary key retrieval via dialect-specific mechanisms.

!!! warning "No native BOOLEAN type"
    Boolean values are stored as `SMALLINT` (`1`/`0`).
    Use SQLAlchemy `Boolean` normally; conversion is handled by the dialect.

!!! tip "Start with default user and port"
    The common development defaults are:
    - user: `dba`
    - port: `33000`

---

## Next Steps

- [Connection Guide](CONNECTION.md)
- [ORM Cookbook](ORM_COOKBOOK.md)
- [Type Mapping](TYPES.md)
