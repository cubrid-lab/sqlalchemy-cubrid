# ORM Cookbook

Practical SQLAlchemy 2.0 ORM patterns for CUBRID. This guide covers table definitions,
relationships, CRUD operations, and CUBRID-specific DML extensions using the modern
`DeclarativeBase` / `mapped_column` API.

For connection setup, see [CONNECTION.md](CONNECTION.md).
For type mapping details, see [TYPES.md](TYPES.md).
For DML extensions reference, see [DML_EXTENSIONS.md](DML_EXTENSIONS.md).

---

## Table of Contents

- [Quick Setup](#quick-setup)
- [Table Definitions](#table-definitions)
- [Basic CRUD](#basic-crud)
- [Relationships](#relationships)
- [ON DUPLICATE KEY UPDATE](#on-duplicate-key-update)
- [MERGE Statement](#merge-statement)
- [REPLACE INTO](#replace-into)
- [Collection Types](#collection-types)
- [Working with LOBs](#working-with-lobs)
- [Eager Loading](#eager-loading)
- [Hybrid Properties](#hybrid-properties)
- [CUBRID-Specific Gotchas](#cubrid-specific-gotchas)

---

## Quick Setup

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

engine = create_engine("cubrid://dba:password@localhost:33000/demodb")
```

---

## Table Definitions

Use `DeclarativeBase` and `mapped_column` (SQLAlchemy 2.0 style).

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from sqlalchemy_cubrid import CLOB, MONETARY, SET, SMALLINT, STRING


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    bio: Mapped[str | None] = mapped_column(CLOB, default=None)
    # CUBRID has no native BOOLEAN — use SMALLINT (0/1)
    is_active: Mapped[int] = mapped_column(SMALLINT, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.sysdate())

    posts: Mapped[list[Post]] = relationship(back_populates="author")


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(STRING)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    author: Mapped[User] = relationship(back_populates="posts")
    tags: Mapped[list[Tag]] = relationship(secondary="post_tags", back_populates="posts")
```

### Table with CUBRID-Specific Types

```python
from sqlalchemy import Column, Integer, MetaData, Table

from sqlalchemy_cubrid import BIT, BLOB, MONETARY, MULTISET, OBJECT, SEQUENCE, SET

metadata = MetaData()

products = Table(
    "products",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("price", MONETARY),
    Column("colors", SET("red", "green", "blue")),
    Column("sizes", MULTISET("S", "M", "L", "XL")),
    Column("image", BLOB),
    Column("flags", BIT(8)),
)
```

---

## Basic CRUD

### Create

```python
from sqlalchemy.orm import Session

with Session(engine) as session:
    user = User(name="Alice", email="alice@example.com")
    session.add(user)
    session.commit()

    # Access auto-generated ID (CUBRID uses AUTO_INCREMENT)
    print(user.id)
```

### Read

```python
from sqlalchemy import select

with Session(engine) as session:
    # Single row
    stmt = select(User).where(User.email == "alice@example.com")
    user = session.scalars(stmt).one()

    # All rows with filtering
    stmt = select(User).where(User.is_active == 1).order_by(User.name)
    users = session.scalars(stmt).all()
```

### Update

```python
with Session(engine) as session:
    user = session.get(User, 1)
    user.name = "Alice Updated"
    session.commit()
```

### Delete

```python
with Session(engine) as session:
    user = session.get(User, 1)
    session.delete(user)
    session.commit()
```

---

## Relationships

### One-to-Many

```python
with Session(engine) as session:
    user = User(name="Bob", email="bob@example.com")
    user.posts.append(Post(title="First Post", body="Hello world"))
    user.posts.append(Post(title="Second Post", body="More content"))
    session.add(user)
    session.commit()

    # Query with relationship
    stmt = select(User).where(User.name == "Bob")
    bob = session.scalars(stmt).one()
    for post in bob.posts:
        print(f"{post.title} by {post.author.name}")
```

### Many-to-Many

```python
class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    posts: Mapped[list[Post]] = relationship(secondary="post_tags", back_populates="tags")


# Association table
post_tags = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", ForeignKey("posts.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)
```

```python
with Session(engine) as session:
    tag = Tag(name="python")
    post = session.get(Post, 1)
    post.tags.append(tag)
    session.commit()
```

> **Note**: CUBRID has no `RETURNING` clause. SQLAlchemy uses `SELECT LAST_INSERT_ID()`
> to retrieve auto-generated primary keys after INSERT. This works transparently —
> the ORM handles it via the dialect's `postfetch_lastrowid` mechanism.

---

## ON DUPLICATE KEY UPDATE

Use `sqlalchemy_cubrid.insert()` (not SQLAlchemy's built-in `insert()`).

```python
from sqlalchemy_cubrid import insert

with Session(engine) as session:
    stmt = insert(User).values(
        id=1,
        name="Alice",
        email="alice@example.com",
    ).on_duplicate_key_update(
        name="Alice Updated",
        email="alice-new@example.com",
    )
    session.execute(stmt)
    session.commit()
```

### Referencing Inserted Values

```python
stmt = insert(User).values(id=1, name="Alice", email="alice@example.com")
stmt = stmt.on_duplicate_key_update(
    name=stmt.inserted.name,  # Use the value being inserted
)
```

> **Note**: `stmt.inserted.<column>` re-emits the INSERT bind parameter in the ON DUPLICATE KEY UPDATE clause.

---

## MERGE Statement

Upsert with full `WHEN MATCHED` / `WHEN NOT MATCHED` control.

```python
from sqlalchemy import select
from sqlalchemy_cubrid import merge

with Session(engine) as session:
    source = select(User).where(User.is_active == 1).subquery()

    stmt = (
        merge(Post.__table__)
        .using(source)
        .on(Post.__table__.c.author_id == source.c.id)
        .when_matched_then_update({"title": source.c.name})
        .when_not_matched_then_insert({
            "title": source.c.name,
            "body": "Auto-created",
            "author_id": source.c.id,
        })
    )
    session.execute(stmt)
    session.commit()
```

---

## REPLACE INTO

Deletes existing row if primary key conflicts, then inserts. Use with caution —
it deletes and re-inserts (unlike ODKU which updates in place).

```python
from sqlalchemy_cubrid import replace

with Session(engine) as session:
    stmt = replace(User.__table__).values(
        id=1,
        name="Alice Replaced",
        email="alice@example.com",
    )
    session.execute(stmt)
    session.commit()
```

---

## Collection Types

CUBRID provides `SET`, `MULTISET`, and `SEQUENCE` collection types.

### Defining Collection Columns

```python
from sqlalchemy import Column, Integer, MetaData, Table

from sqlalchemy_cubrid import MULTISET, SEQUENCE, SET

metadata = MetaData()

inventory = Table(
    "inventory",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("colors", SET("VARCHAR")),          # Unordered, unique elements
    Column("sizes", MULTISET("VARCHAR")),      # Unordered, duplicates allowed
    Column("history", SEQUENCE("VARCHAR")),    # Ordered, duplicates allowed
)
```

### DDL Output

```sql
CREATE TABLE inventory (
    id INTEGER AUTO_INCREMENT NOT NULL,
    colors SET(VARCHAR),
    sizes MULTISET(VARCHAR),
    history SEQUENCE(VARCHAR),
    PRIMARY KEY (id)
)
```

---

## Working with LOBs

### CLOB (Character Large Object)

```python
from sqlalchemy_cubrid import CLOB


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(CLOB)  # Large text content
```

### BLOB (Binary Large Object)

```python
from sqlalchemy_cubrid import BLOB


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255))
    data: Mapped[bytes] = mapped_column(BLOB)
```

```python
with Session(engine) as session:
    with open("photo.jpg", "rb") as f:
        attachment = Attachment(filename="photo.jpg", data=f.read())
    session.add(attachment)
    session.commit()
```

---

## Eager Loading

Avoid N+1 queries with `joinedload` and `selectinload`.

```python
from sqlalchemy.orm import joinedload, selectinload

with Session(engine) as session:
    # Joined load — single query with JOIN
    stmt = select(User).options(joinedload(User.posts)).where(User.id == 1)
    user = session.scalars(stmt).unique().one()

    # Select-in load — separate SELECT with IN clause (better for collections)
    stmt = select(User).options(selectinload(User.posts))
    users = session.scalars(stmt).unique().all()

    # Nested eager loading
    stmt = (
        select(User)
        .options(selectinload(User.posts).selectinload(Post.tags))
        .where(User.is_active == 1)
    )
    users = session.scalars(stmt).unique().all()
```

---

## Hybrid Properties

Computed properties that work both in Python and SQL.

```python
from sqlalchemy.ext.hybrid import hybrid_property


class Product(Base):
    __tablename__ = "products_v2"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    price: Mapped[float] = mapped_column()
    tax_rate: Mapped[float] = mapped_column(default=0.1)

    @hybrid_property
    def price_with_tax(self) -> float:
        return self.price * (1 + self.tax_rate)

    @price_with_tax.inplace.expression
    @classmethod
    def _price_with_tax_expression(cls):
        return cls.price * (1 + cls.tax_rate)
```

```python
with Session(engine) as session:
    # Works in Python
    product = session.get(Product, 1)
    print(product.price_with_tax)  # Computed in Python

    # Works in SQL queries
    stmt = select(Product).where(Product.price_with_tax > 100)
    expensive = session.scalars(stmt).all()
```

---

## CUBRID-Specific Gotchas

### 1. No RETURNING Clause

CUBRID does not support `INSERT ... RETURNING` or `UPDATE ... RETURNING`.
The ORM retrieves auto-generated keys via `SELECT LAST_INSERT_ID()` automatically.

**Impact**: Bulk inserts with `insert().returning()` are not available. Use standard
`session.add_all()` or `insert().values([...])` without returning.

### 2. No Native BOOLEAN

CUBRID maps `Boolean` to `SMALLINT` (0/1). Use integer values in queries:

```python
# Correct
stmt = select(User).where(User.is_active == 1)

# Also works — SQLAlchemy handles the conversion
stmt = select(User).where(User.is_active == True)  # noqa: E712
```

### 3. JSON Type (CUBRID ≥ 10.2)

CUBRID 10.2+ supports a native JSON column type. Since sqlalchemy-cubrid v1.2.0,
JSON is fully mapped:

```python
from sqlalchemy_cubrid import JSON


class Config(Base):
    __tablename__ = "configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    data = mapped_column(JSON)  # Native JSON column

# Path access compiles to JSON_EXTRACT:
session.query(Config).filter(Config.data["key"] == "value")
```

> **CUBRID < 10.2 workaround:** Store JSON as `STRING`/`VARCHAR` and
> serialize/deserialize in Python. See [Troubleshooting](../docs/TROUBLESHOOTING.md#json-type-usage).

### 4. Collection Types Instead of ARRAY

CUBRID uses `SET`, `MULTISET`, and `SEQUENCE` instead of SQL `ARRAY`:

| Type | Ordered | Duplicates | Use Case |
|---|:---:|:---:|---|
| `SET` | ✗ | ✗ | Unique tags, categories |
| `MULTISET` | ✗ | ✓ | Counts, repeated values |
| `SEQUENCE` | ✓ | ✓ | Ordered lists, history |

### 5. DDL Auto-Commits

CUBRID implicitly commits all DDL statements (`CREATE TABLE`, `ALTER TABLE`, etc.).
This means `Base.metadata.create_all(engine)` commits immediately — it cannot be
rolled back. The Alembic integration sets `transactional_ddl = False` accordingly.

### 6. No Temporary Tables

CUBRID does not support `CREATE TEMPORARY TABLE`. Use regular tables with
a cleanup strategy if you need temporary storage.

### 7. Identifier Case Folding

CUBRID folds identifiers to **lowercase** (unlike the SQL standard which uses
uppercase). Quoted identifiers preserve case but are rarely needed.

---

## Additional Practical Recipes

### Idempotent user upsert with unique email

```python
from sqlalchemy import func
from sqlalchemy_cubrid import insert

with Session(engine) as session:
    stmt = insert(User.__table__).values(id=1, name="Alice", email="alice@example.com")
    stmt = stmt.on_duplicate_key_update(
        name=stmt.inserted.name,
        updated_at=func.current_datetime(),
    )
    session.execute(stmt)
    session.commit()
```

### Bulk create with explicit flush windows

```python
BATCH = 500

with Session(engine) as session:
    for i in range(0, len(payload_rows), BATCH):
        chunk = payload_rows[i : i + BATCH]
        session.add_all(User(name=row["name"], email=row["email"]) for row in chunk)
        session.flush()  # keep memory bounded
    session.commit()
```

### Pessimistic lock for balance transfer

```python
from sqlalchemy import select

with Session(engine) as session:
    account = session.scalars(
        select(Account).where(Account.id == 10).with_for_update()
    ).one()
    account.balance -= 100
    session.commit()
```

!!! warning "Avoid `RETURNING`-based ORM patterns"
    CUBRID does not support `RETURNING`. Prefer `flush()` + mapped identity values.

!!! warning "Use CUBRID extension APIs for upsert"
    For ODKU behavior, use `sqlalchemy_cubrid.insert()` rather than SQLAlchemy's generic `insert()`.

!!! tip "Prefer `selectinload` for large collections"
    `joinedload` can multiply rows significantly on one-to-many joins.

---

*See also: [Feature Support Matrix](FEATURE_SUPPORT.md) for a complete comparison
with MySQL, PostgreSQL, and SQLite.*
