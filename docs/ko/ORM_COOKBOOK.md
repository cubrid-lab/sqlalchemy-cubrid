# ORM 쿡북 (한국어)

> 🌐 [ORM_COOKBOOK.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/ORM_COOKBOOK.md)의 번역입니다. 영어 원문이 표준이며, 페이지 번역은 경고 수준의 동기화 규칙을 따릅니다.

CUBRID를 위한 실용적인 SQLAlchemy 2.0 ORM 패턴. 이 가이드는 현대적 `DeclarativeBase` / `mapped_column` API를 사용해 테이블 정의, 릴레이션십, CRUD 연산, CUBRID 전용 DML 확장을 다룹니다.

연결 설정은 [CONNECTION.md](CONNECTION.md)를, 타입 매핑 상세는 [TYPES.md](TYPES.md)를, DML 확장 참조는 [DML_EXTENSIONS.md](DML_EXTENSIONS.md)를 참고하세요.

---

## 목차

- [빠른 설정](#빠른-설정)
- [테이블 정의](#테이블-정의)
- [기본 CRUD](#기본-crud)
- [릴레이션십](#릴레이션십)
- [ON DUPLICATE KEY UPDATE](#on-duplicate-key-update)
- [MERGE 문](#merge-문)
- [REPLACE INTO](#replace-into)
- [컬렉션 타입](#컬렉션-타입)
- [LOB 다루기](#lob-다루기)
- [이저 로딩](#이저-로딩)
- [하이브리드 속성](#하이브리드-속성)
- [CUBRID 전용 주의점](#cubrid-전용-주의점)

---

## 빠른 설정

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

engine = create_engine("cubrid://dba:password@localhost:33000/demodb")
```

---

## 테이블 정의

`DeclarativeBase`와 `mapped_column`을 사용하세요 (SQLAlchemy 2.0 스타일).

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
    # CUBRID에는 네이티브 BOOLEAN이 없음 — SMALLINT(0/1) 사용
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

### CUBRID 전용 타입을 사용한 테이블

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

## 기본 CRUD

### Create

```python
from sqlalchemy.orm import Session

with Session(engine) as session:
    user = User(name="Alice", email="alice@example.com")
    session.add(user)
    session.commit()

    # 자동 생성 ID 접근 (CUBRID는 AUTO_INCREMENT 사용)
    print(user.id)
```

### Read

```python
from sqlalchemy import select

with Session(engine) as session:
    # 단일 행
    stmt = select(User).where(User.email == "alice@example.com")
    user = session.scalars(stmt).one()

    # 필터링된 전체 행
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

## 릴레이션십

### 일대다

```python
with Session(engine) as session:
    user = User(name="Bob", email="bob@example.com")
    user.posts.append(Post(title="First Post", body="Hello world"))
    user.posts.append(Post(title="Second Post", body="More content"))
    session.add(user)
    session.commit()

    # 릴레이션십으로 조회
    stmt = select(User).where(User.name == "Bob")
    bob = session.scalars(stmt).one()
    for post in bob.posts:
        print(f"{post.title} by {post.author.name}")
```

### 다대다

```python
class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    posts: Mapped[list[Post]] = relationship(secondary="post_tags", back_populates="tags")


# 연관 테이블
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

> **참고**: CUBRID에는 `RETURNING` 절이 없습니다. SQLAlchemy는 INSERT 후 자동 생성 기본 키를 얻기 위해 `SELECT LAST_INSERT_ID()`를 사용합니다. 이것은 투명하게 동작합니다 — ORM이 방언의 `postfetch_lastrowid` 메커니즘으로 처리합니다.

---

## ON DUPLICATE KEY UPDATE

`sqlalchemy_cubrid.insert()`를 사용하세요 (SQLAlchemy 내장 `insert()`가 아니라).

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

### 삽입되는 값 참조

```python
stmt = insert(User).values(id=1, name="Alice", email="alice@example.com")
stmt = stmt.on_duplicate_key_update(
    name=stmt.inserted.name,  # 삽입되는 값을 사용
)
```

> **참고**: `stmt.inserted.<column>`가 CUBRID ODKU 절에서 `VALUES(column)`을 렌더링하는 지원되는 방식입니다.

---

## MERGE 문

완전한 `WHEN MATCHED` / `WHEN NOT MATCHED` 제어를 갖춘 upsert.

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

기본 키 충돌 시 기존 행을 삭제하고 삽입합니다. 주의해서 사용하세요 — 제자리 갱신하는 ODKU와 달리 삭제 후 재삽입입니다.

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

## 컬렉션 타입

CUBRID는 `SET`, `MULTISET`, `SEQUENCE` 컬렉션 타입을 제공합니다.

### 컬렉션 컬럼 정의

```python
from sqlalchemy import Column, Integer, MetaData, Table

from sqlalchemy_cubrid import MULTISET, SEQUENCE, SET

metadata = MetaData()

inventory = Table(
    "inventory",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("colors", SET("VARCHAR")),          # 순서 없음, 유일한 원소
    Column("sizes", MULTISET("VARCHAR")),      # 순서 없음, 중복 허용
    Column("history", SEQUENCE("VARCHAR")),    # 순서 있음, 중복 허용
)
```

### DDL 출력

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

## LOB 다루기

### CLOB (Character Large Object)

```python
from sqlalchemy_cubrid import CLOB


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(CLOB)  # 대용량 텍스트 내용
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

## 이저 로딩

`joinedload`와 `selectinload`로 N+1 쿼리를 피하세요.

```python
from sqlalchemy.orm import joinedload, selectinload

with Session(engine) as session:
    # 조인 로드 — JOIN을 사용한 단일 쿼리
    stmt = select(User).options(joinedload(User.posts)).where(User.id == 1)
    user = session.scalars(stmt).unique().one()

    # Select-in 로드 — IN 절을 사용한 별도 SELECT (컬렉션에 더 좋음)
    stmt = select(User).options(selectinload(User.posts))
    users = session.scalars(stmt).unique().all()

    # 중첩 이저 로딩
    stmt = (
        select(User)
        .options(selectinload(User.posts).selectinload(Post.tags))
        .where(User.is_active == 1)
    )
    users = session.scalars(stmt).unique().all()
```

---

## 하이브리드 속성

Python과 SQL 양쪽에서 동작하는 계산 속성.

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
    # Python에서 동작
    product = session.get(Product, 1)
    print(product.price_with_tax)  # Python에서 계산

    # SQL 쿼리에서 동작
    stmt = select(Product).where(Product.price_with_tax > 100)
    expensive = session.scalars(stmt).all()
```

---

## CUBRID 전용 주의점

### 1. RETURNING 절 없음

CUBRID는 `INSERT ... RETURNING`이나 `UPDATE ... RETURNING`을 지원하지 않습니다.
ORM이 자동 생성 키를 `SELECT LAST_INSERT_ID()`로 자동 조회합니다.

**영향**: `insert().returning()`을 사용한 대량 삽입은 불가능합니다. 표준 `session.add_all()`이나 returning 없는 `insert().values([...])`를 사용하세요.

### 2. 네이티브 BOOLEAN 없음

CUBRID는 `Boolean`을 `SMALLINT`(0/1)로 매핑합니다. 쿼리에서 정수 값을 사용하세요:

```python
# 올바름
stmt = select(User).where(User.is_active == 1)

# 역시 동작 — SQLAlchemy가 변환 처리
stmt = select(User).where(User.is_active == True)  # noqa: E712
```

### 3. JSON 타입 (CUBRID ≥ 10.2)

CUBRID 10.2+는 네이티브 JSON 컬럼 타입을 지원합니다. sqlalchemy-cubrid v1.2.0부터 JSON이 완전히 매핑됩니다:

```python
from sqlalchemy_cubrid import JSON


class Config(Base):
    __tablename__ = "configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    data = mapped_column(JSON)  # 네이티브 JSON 컬럼

# 경로 접근은 JSON_EXTRACT로 컴파일:
session.query(Config).filter(Config.data["key"] == "value")
```

> **CUBRID < 10.2 회피:** JSON을 `STRING`/`VARCHAR`로 저장하고 Python에서 직렬화/역직렬화하세요. [문제 해결](TROUBLESHOOTING.md#json-타입-사용)을 참고하세요.

### 4. ARRAY 대신 컬렉션 타입

CUBRID는 SQL `ARRAY` 대신 `SET`, `MULTISET`, `SEQUENCE`를 사용합니다:

| 타입 | 순서 | 중복 | 사용 사례 |
|---|:---:|:---:|---|
| `SET` | ✗ | ✗ | 유일한 태그, 카테고리 |
| `MULTISET` | ✗ | ✓ | 개수, 반복 값 |
| `SEQUENCE` | ✓ | ✓ | 순서 있는 목록, 이력 |

### 5. DDL 자동 커밋

CUBRID는 모든 DDL 문(`CREATE TABLE`, `ALTER TABLE` 등)을 암시적으로 커밋합니다.
즉 `Base.metadata.create_all(engine)`은 즉시 커밋되며 — 롤백할 수 없습니다. Alembic 연동은 그에 맞게 `transactional_ddl = False`를 설정합니다.

### 6. 임시 테이블 없음

CUBRID는 `CREATE TEMPORARY TABLE`을 지원하지 않습니다. 임시 저장이 필요하면 정리 전략을 갖춘 일반 테이블을 사용하세요.

### 7. 식별자 대소문자 폴딩

CUBRID는 식별자를 (SQL 표준의 대문자와 달리) **소문자**로 폴딩합니다. 인용된 식별자는 대소문자를 보존하지만 거의 필요하지 않습니다.

---

## 추가 실용 레시피

### 유니크 이메일로 멱등성 있는 사용자 upsert

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

### 명시적 flush 창을 사용한 대량 생성

```python
BATCH = 500

with Session(engine) as session:
    for i in range(0, len(payload_rows), BATCH):
        chunk = payload_rows[i : i + BATCH]
        session.add_all(User(name=row["name"], email=row["email"]) for row in chunk)
        session.flush()  # 메모리 상한 유지
    session.commit()
```

### 잔액 이체를 위한 비관적 잠금

```python
from sqlalchemy import select

with Session(engine) as session:
    account = session.scalars(
        select(Account).where(Account.id == 10).with_for_update()
    ).one()
    account.balance -= 100
    session.commit()
```

!!! warning "`RETURNING` 기반 ORM 패턴 피하기"
    CUBRID는 `RETURNING`을 지원하지 않습니다. `flush()` + 매핑된 아이덴티티 값을 선호하세요.

!!! warning "upsert에는 CUBRID 확장 API 사용"
    ODKU 동작에는 SQLAlchemy 일반 `insert()` 대신 `sqlalchemy_cubrid.insert()`를 사용하세요.

!!! tip "큰 컬렉션에는 `selectinload` 선호"
    `joinedload`는 일대다 조인에서 행을 크게 증폭시킬 수 있습니다.

---

*참고: MySQL, PostgreSQL, SQLite와의 완전한 비교는 [기능 지원 매트릭스](FEATURE_SUPPORT.md)를 보세요.*
