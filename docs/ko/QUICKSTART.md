# 빠른 시작 (한국어)

> 🌐 [QUICKSTART.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/QUICKSTART.md)의 번역입니다. 영어 원문이 표준이며, 페이지 번역은 경고 수준의 동기화 규칙을 따릅니다.

몇 분 안에 동작하는 SQLAlchemy + CUBRID 애플리케이션을 만듭니다.

---

## 사전 준비

시작하기 전에 다음이 준비되어 있는지 확인하세요:

- CUBRID 서버 (실행 중이고 도달 가능)
- Python 3.10+
- 지원되는 드라이버 구성 중 하나:
  - CUBRID-Python(C 확장)을 통한 `cubrid://`
  - pycubrid를 통한 `cubrid+pycubrid://`
  - pycubrid.aio를 통한 `cubrid+aiopycubrid://`

```bash
pip install sqlalchemy-cubrid
# 또는: pip install "sqlalchemy-cubrid[pycubrid]"
```

---

## 방언 설치

```bash
pip install sqlalchemy-cubrid
```

---

## 연결 URL 형식

지원되는 URL 형식 중 하나를 사용하세요:

```text
cubrid://user:password@host:port/database
cubrid+pycubrid://user:password@host:port/database
cubrid+aiopycubrid://user:password@host:port/database
```

예:

```python
from sqlalchemy import create_engine

engine = create_engine("cubrid://dba@localhost:33000/testdb")
```

---

## 방언 스택

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

## SQLAlchemy Core 예제

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

# 테이블 생성
metadata.create_all(engine)

# 행 삽입
with engine.begin() as conn:
    conn.execute(insert(users).values(name="Alice"))

# 행 조회
with engine.connect() as conn:
    rows = conn.execute(select(users.c.id, users.c.name).order_by(users.c.id)).all()
    print(rows)
```

---

## SQLAlchemy ORM 예제

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

## 흔한 주의점

!!! warning "RETURNING 미지원"
    CUBRID는 `INSERT ... RETURNING`이나 `UPDATE ... RETURNING`을 지원하지 않습니다.
    SQLAlchemy는 방언 고유 메커니즘으로 기본 키 조회를 처리합니다.

!!! warning "네이티브 BOOLEAN 타입 없음"
    불리언 값은 `SMALLINT`(`1`/`0`)로 저장됩니다.
    SQLAlchemy `Boolean`을 평소처럼 사용하세요. 변환은 방언이 처리합니다.

!!! tip "기본 사용자와 포트로 시작"
    흔한 개발 기본값:
    - 사용자: `dba`
    - 포트: `33000`

---

## 다음 단계

- [연결 가이드](CONNECTION.md)
- [ORM 쿡북](ORM_COOKBOOK.md)
- [타입 매핑](TYPES.md)
