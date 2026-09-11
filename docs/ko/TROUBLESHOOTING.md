# 문제 해결 가이드 (한국어)

> 🌐 [TROUBLESHOOTING.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/TROUBLESHOOTING.md)의 번역입니다. 영어 원문이 표준이며, 페이지 번역은 경고 수준의 동기화 규칙을 따릅니다.

sqlalchemy-cubrid의 흔한 문제에 대한 종합 해결책 — 연결 설정, SQL 컴파일, 타입 매핑, 스키마 리플렉션, Alembic 마이그레이션, ORM 패턴, 성능 튜닝.

---

## 목차

- [설치 문제](#설치-문제)
  - [ImportError: No module named 'CUBRIDdb'](#importerror-no-module-named-cubriddb)
  - [ImportError: No module named 'pycubrid'](#importerror-no-module-named-pycubrid)
  - [C 확장 빌드 실패](#c-확장-빌드-실패)
- [연결 문제](#연결-문제)
  - [포트 33000 연결 거부](#포트-33000-연결-거부)
  - [인증 실패](#인증-실패)
  - [끊어진 연결 / 연결 해제](#끊어진-연결--연결-해제)
  - [커넥션 풀 고갈](#커넥션-풀-고갈)
  - [잘못된 URL 형식](#잘못된-url-형식)
- [SQL 컴파일 문제](#sql-컴파일-문제)
  - [미지원 RETURNING 절](#미지원-returning-절)
  - [불리언 컬럼 동작](#불리언-컬럼-동작)
  - [LIMIT / OFFSET 구문](#limit--offset-구문)
  - [CAST 타입 제한](#cast-타입-제한)
  - [예약어 충돌](#예약어-충돌)
  - [JSON 타입 사용](#json-타입-사용)
- [타입 매핑 문제](#타입-매핑-문제)
  - [불리언이 SMALLINT로 매핑](#불리언이-smallint로-매핑)
  - [Text가 STRING으로 매핑](#text가-string으로-매핑)
  - [ARRAY 타입 없음](#array-타입-없음)
  - [LOB 컬럼 동작](#lob-컬럼-동작)
  - [컬렉션 타입 (SET, MULTISET, SEQUENCE)](#컬렉션-타입-set-multiset-sequence)
  - [Decimal 정밀도](#decimal-정밀도)
- [스키마 리플렉션 문제](#스키마-리플렉션-문제)
  - [리플렉션 중 테이블을 찾을 수 없음](#리플렉션-중-테이블을-찾을-수-없음)
  - [테이블 이름의 대소문자 구분](#테이블-이름의-대소문자-구분)
  - [뷰 리플렉션](#뷰-리플렉션)
  - [스키마 지원 없음](#스키마-지원-없음)
- [ORM 문제](#orm-문제)
  - [autoincrement와 lastrowid](#autoincrement와-lastrowid)
  - [시퀀스 없음 — AUTO_INCREMENT 사용](#시퀀스-없음--auto_increment-사용)
  - [릴레이션십 캐스케이드 동작](#릴레이션십-캐스케이드-동작)
  - [대량 삽입 성능](#대량-삽입-성능)
- [DML 확장 문제](#dml-확장-문제)
  - [ON DUPLICATE KEY UPDATE 동작 안 함](#on-duplicate-key-update-동작-안-함)
  - [MERGE 문 오류](#merge-문-오류)
  - [REPLACE INTO 동작](#replace-into-동작)
- [Alembic 마이그레이션 문제](#alembic-마이그레이션-문제)
  - [방언 'cubrid'에 대한 구현을 찾을 수 없음](#방언-cubrid에-대한-구현을-찾을-수-없음)
  - [ALTER COLUMN TYPE 거부됨 (손실 변환)](#alter-column-type-거부됨-손실-변환)
  - [RENAME COLUMN](#rename-column)
  - [부분 마이그레이션 (DDL 자동 커밋)](#부분-마이그레이션-ddl-자동-커밋)
  - [Autogenerate가 변경을 감지하지 못함](#autogenerate가-변경을-감지하지-못함)
- [격리 수준 문제](#격리-수준-문제)
  - [격리 수준 설정](#격리-수준-설정)
  - [DDL이 현재 트랜잭션 커밋](#ddl이-현재-트랜잭션-커밋)
- [트랜잭션 문제](#트랜잭션-문제)
  - [데이터가 저장되지 않음](#데이터가-저장되지-않음)
  - [오토커밋 충돌](#오토커밋-충돌)
  - [세이브포인트 한계](#세이브포인트-한계)
- [성능 문제](#성능-문제)
  - [느린 스키마 리플렉션](#느린-스키마-리플렉션)
  - [연결 오버헤드](#연결-오버헤드)
  - [문장 캐싱](#문장-캐싱)
- [Docker 문제](#docker-문제)
  - [컨테이너는 시작되는데 연결 안 됨](#컨테이너는-시작되는데-연결-안-됨)
  - [데이터베이스가 생성되지 않음](#데이터베이스가-생성되지-않음)
  - [버전별 동작](#버전별-동작)
- [디버깅 기법](#디버깅-기법)

---

## 설치 문제

### ImportError: No module named 'CUBRIDdb'

**증상:**

```
ImportError: No module named 'CUBRIDdb'
```

**원인:** CUBRID C 확장 Python 드라이버가 설치되지 않음.

**해결 — 옵션 A: C 확장 드라이버 설치:**

```bash
pip install CUBRID-Python
```

> **참고:** CUBRID CCI 라이브러리와 C 컴파일러가 필요합니다. 플랫폼별 지침은 [CUBRID Python 드라이버 문서](https://www.cubrid.org/manual/en/11.0/api/python.html)를 참고하세요.

**해결 — 옵션 B: 순수 Python 드라이버 사용 (권장):**

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

그리고 연결 URL을 변경하세요:

```python
# 이전 (C 확장)
engine = create_engine("cubrid://dba@localhost:33000/testdb")

# 이후 (순수 Python — C 빌드 불필요)
engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")
```

---

### ImportError: No module named 'pycubrid'

**증상:**

```
ImportError: No module named 'pycubrid'
```

**해결:**

```bash
pip install pycubrid
# 또는 둘 다 함께 설치
pip install "sqlalchemy-cubrid[pycubrid]"
```

---

### C 확장 빌드 실패

**증상:** `pip install CUBRID-Python`이 컴파일 오류로 실패.

**흔한 원인:**
- C 컴파일러 누락 (`gcc` / `cl.exe`)
- CUBRID CCI 헤더 누락
- 호환되지 않는 플랫폼

**해결:** 대신 pycubrid를 사용하세요 — 순수 Python이라 빌드 도구가 필요 없습니다:

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

---

## 연결 문제

### 포트 33000 연결 거부

**증상:**

```
OperationalError: (CUBRIDdb.DatabaseError) Connection refused
```

**해결:**

1. **CUBRID 브로커 실행 확인:**

   ```bash
   cubrid broker status
   cubrid service status
   ```

2. **Docker 컨테이너 미준비:**

   ```bash
   docker compose up -d
   sleep 10  # 전체 초기화 대기
   docker compose ps  # "running" 상태 확인
   ```

3. **잘못된 포트:** 실제 브로커 포트는 `cubrid_broker.conf`에서 확인.

4. **방화벽:** 포트 33000이 차단되지 않았는지 확인.

---

### 인증 실패

**증상:**

```
OperationalError: Authentication failed
```

**해결:** CUBRID 기본 `dba` 사용자에게는 **비밀번호가 없습니다**:

```python
# 올바름 — 비밀번호 없음
engine = create_engine("cubrid://dba@localhost:33000/testdb")

# 올바름 — 비밀번호 설정 시
engine = create_engine("cubrid://dba:mypassword@localhost:33000/testdb")
```

---

### 끊어진 연결 / 연결 해제

**증상:**

```
OperationalError: Connection is closed
OperationalError: broker is not available
```

**원인:** CUBRID 브로커에는 `SESSION_TIMEOUT`(기본 ~300초)이 있습니다. 유휴 풀링 연결이 서버 측에서 만료됩니다.

**해결:** 풀 설정 구성:

```python
engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",
    pool_pre_ping=True,  # 체크아웃 전 네이티브 드라이버 핑
    pool_recycle=240,     # SESSION_TIMEOUT(300초) 전에 재활용
)
```

`cubrid+pycubrid://`와 `cubrid+aiopycubrid://`의 경우 `pool_pre_ping=True`는 이제 `SELECT 1`을 발행하는 대신 pycubrid의 네이티브 `CHECK_CAS` 핑을 사용합니다.

자세한 권장사항은 [연결 가이드 — 풀 튜닝](CONNECTION.md#커넥션-풀-튜닝)을 참고하세요.

---

### 커넥션 풀 고갈

**증상:**

```
TimeoutError: QueuePool limit of size 5 overflow 10 reached
```

**원인:**
- 연결이 풀로 반환되지 않음 (`close()`나 컨텍스트 매니저 누락)
- 애플리케이션 동시성에 비해 풀이 너무 작음

**해결:**

```python
engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
)

# 연결 반환을 위해 항상 컨텍스트 매니저 사용
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
```

---

### 잘못된 URL 형식

**증상:**

```
ArgumentError: Could not parse rfc1738 URL
NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:pycubrid
```

**올바른 URL 형식:**

```python
# C 확장 드라이버 (CUBRIDdb)
engine = create_engine("cubrid://dba@localhost:33000/testdb")
engine = create_engine("cubrid+cubrid://dba@localhost:33000/testdb")

# 순수 Python 드라이버 (pycubrid)
engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")
```

**흔한 실수:**

```python
# 잘못됨 — 'pycubrid://'은 유효한 스킴이 아님
engine = create_engine("pycubrid://dba@localhost:33000/testdb")

# 잘못됨 — 포트는 쿼리 파라미터가 아니라 URL에 있어야 함
engine = create_engine("cubrid://dba@localhost/testdb?port=33000")
```

---

## SQL 컴파일 문제

### 미지원 RETURNING 절

**증상:**

```
CompileError: RETURNING is not supported by this dialect
```

**원인:** CUBRID는 `INSERT ... RETURNING`이나 `UPDATE ... RETURNING`을 지원하지 않습니다.

**해결:** 방언이 드라이버 연결의 `get_last_insert_id()`로 자동 처리합니다. `SELECT LAST_INSERT_ID()`를 사용할 수도 있습니다:

```python
from sqlalchemy import insert, select, text

# 삽입 후 생성된 ID 얻기
with engine.begin() as conn:
    result = conn.execute(
        insert(users).values(name="Alice", email="alice@example.com")
    )
    new_id = result.inserted_primary_key[0]
    print(f"New user ID: {new_id}")

# 또는 LAST_INSERT_ID() 사용
with engine.begin() as conn:
    conn.execute(text("INSERT INTO users (name) VALUES ('Alice')"))
    last_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
```

**ORM 패턴:**

```python
with Session(engine) as session:
    user = User(name="Alice", email="alice@example.com")
    session.add(user)
    session.flush()  # INSERT 전송, user.id 채움
    print(user.id)   # flush 후 사용 가능
    session.commit()
```

---

### 불리언 컬럼 동작

**증상:** 불리언 컬럼이 `True`/`False` 대신 `0`과 `1`을 저장/반환.

**원인:** CUBRID에는 네이티브 `BOOLEAN` 타입이 없습니다. 방언은 `Boolean`을 `SMALLINT`로 매핑합니다.

**해결:** 예상된 동작입니다. SQLAlchemy가 Python `bool`과 `SMALLINT(0/1)` 사이를 자동 변환합니다:

```python
from sqlalchemy import Boolean
from sqlalchemy.orm import mapped_column, Mapped

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # SMALLINT로 저장: True→1, False→0
    # 자동으로 bool로 조회됨
```

**raw SQL에서:**

```python
# 삽입
conn.execute(text("INSERT INTO users (is_active) VALUES (:val)"), {"val": 1})

# 조회 — 0/1과 비교
conn.execute(text("SELECT * FROM users WHERE is_active = 1"))
```

---

### LIMIT / OFFSET 구문

**증상:** 페이지네이션에서 예기치 않은 쿼리 동작.

**CUBRID는 표준 `LIMIT n OFFSET m` 구문을 지원합니다.** 방언이 자동 생성합니다:

```python
# SQLAlchemy가 올바른 CUBRID LIMIT/OFFSET 생성
stmt = select(users).limit(10).offset(20)
# → SELECT ... FROM users LIMIT 10 OFFSET 20
```

**참고:** CUBRID는 MySQL의 `LIMIT offset, count` 쉼표 구문을 지원하지 않습니다. 방언은 항상 `LIMIT n OFFSET m`을 사용합니다.

---

### CAST 타입 제한

**증상:**

```
ProgrammingError: CAST to this type is not supported
```

**원인:** CUBRID의 `CAST()`는 제한된 대상 타입 집합을 지원합니다.

**지원되는 CAST 대상:**

| 대상 타입 | 예 |
|---|---|
| `CHAR(n)` | `CAST(col AS CHAR(10))` |
| `VARCHAR(n)` | `CAST(col AS VARCHAR(100))` |
| `NCHAR(n)` | `CAST(col AS NCHAR(10))` |
| `INTEGER` | `CAST(col AS INTEGER)` |
| `BIGINT` | `CAST(col AS BIGINT)` |
| `FLOAT` | `CAST(col AS FLOAT)` |
| `DOUBLE` | `CAST(col AS DOUBLE)` |
| `NUMERIC(p,s)` | `CAST(col AS NUMERIC(10,2))` |
| `DATE` | `CAST(col AS DATE)` |
| `TIME` | `CAST(col AS TIME)` |
| `DATETIME` | `CAST(col AS DATETIME)` |
| `TIMESTAMP` | `CAST(col AS TIMESTAMP)` |

**미지원:** `CAST(... AS BOOLEAN)`, `CAST(... AS BLOB)`, `CAST(... AS SET)`.

---

### 예약어 충돌

**증상:**

```
ProgrammingError: Syntax error near 'value'
```

**원인:** CUBRID에는 컬럼/테이블 이름과 충돌할 수 있는 많은 예약어가 있습니다.

**흔한 CUBRID 예약어:**

| 예약어 | 안전한 대안 |
|---|---|
| `value` | `val`, `item_value` |
| `count` | `cnt`, `item_count` |
| `data` | `file_data`, `raw_data` |
| `level` | `user_level` |
| `action` | `user_action` |
| `status` | `item_status` |
| `type` | `item_type` |

**해결 — 방언이 식별자를 자동 인용하지만**, raw SQL에 `text()`를 쓴다면 수동으로 인용하세요:

```python
# ORM과 Core 구성에는 자동 인용이 동작
class Config(Base):
    __tablename__ = "config"
    value: Mapped[str] = mapped_column("val", String(100))  # 컬럼 이름 변경

# raw SQL에는 큰따옴표 사용
conn.execute(text('SELECT "value" FROM config'))
```

`CubridIdentifierPreparer`가 예약어 인용을 자동 처리합니다. 전체 예약어 목록은 `base.py`에 유지됩니다.

---

### JSON 타입 사용

**상태:** JSON은 sqlalchemy-cubrid v1.2.0부터 지원되며 CUBRID ≥ 10.2가 필요합니다.

**기본 사용:**

```python
from sqlalchemy import Column, MetaData, Table, select
from sqlalchemy_cubrid import JSON

metadata = MetaData()

config = Table(
    "config",
    metadata,
    Column("data", JSON),
)
```

**경로 접근:** `col["key"]`는 CUBRID에서 `JSON_EXTRACT(...)`로 컴파일됩니다.

```python
stmt = select(config.c.data["theme"])
```

**이 오류가 보이면:**

```
CompileError: JSON is not supported by this dialect
```

`sqlalchemy-cubrid>=1.2.0`으로 업그레이드하세요.

**CUBRID < 10.2 회피:** JSON을 `VARCHAR`나 `STRING`으로 저장하고 Python에서 직렬화/역직렬화하세요:

```python
import json
from sqlalchemy import String, TypeDecorator

class JSONType(TypeDecorator):
    """Store JSON as VARCHAR in CUBRID."""
    impl = String(4096)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None

class Config(Base):
    __tablename__ = "config"
    id: Mapped[int] = mapped_column(primary_key=True)
    settings: Mapped[dict] = mapped_column(JSONType)
```

---

## 타입 매핑 문제

### 불리언이 SMALLINT로 매핑

위의 [불리언 컬럼 동작](#불리언-컬럼-동작)을 참고하세요.

---

### Text가 STRING으로 매핑

**동작:** SQLAlchemy의 `Text` 타입은 CUBRID의 `STRING` 타입으로 매핑되며, `VARCHAR(1,073,741,823)`과 동등합니다 — 매우 큰 가변 길이 문자열.

```python
from sqlalchemy import Text

class Article(Base):
    __tablename__ = "articles"
    content: Mapped[str] = mapped_column(Text)
    # DDL에서 → STRING (VARCHAR(1073741823)과 동등)
```

이것은 올바른 동작입니다. CUBRID의 `STRING` 타입은 MySQL/PostgreSQL의 `TEXT`와 같은 목적을 수행합니다.

---

### ARRAY 타입 없음

**원인:** CUBRID에는 표준 `ARRAY` 타입이 없습니다. 대신 **컬렉션 타입**을 제공합니다: `SET`, `MULTISET`, `SEQUENCE`.

```python
from sqlalchemy_cubrid import SET, MULTISET, SEQUENCE

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    tags: Mapped[str] = mapped_column(SET(String(50)))        # 유일, 순서 없음
    categories: Mapped[str] = mapped_column(MULTISET(String(50)))  # 중복 허용
    colors: Mapped[str] = mapped_column(SEQUENCE(String(50)))      # 순서 있음
```

**SQL 대응물:**

```sql
CREATE TABLE products (
    id INTEGER AUTO_INCREMENT PRIMARY KEY,
    tags SET(VARCHAR(50)),
    categories MULTISET(VARCHAR(50)),
    colors SEQUENCE(VARCHAR(50))
);
```

---

### LOB 컬럼 동작

**CLOB**(Character Large Object)과 **BLOB**(Binary Large Object) 타입이 지원됩니다:

```python
from sqlalchemy import LargeBinary, Text

class Document(Base):
    __tablename__ = "documents"
    content: Mapped[str] = mapped_column(Text)       # STRING 사용 (CLOB 유사)
    binary_data: Mapped[bytes] = mapped_column(LargeBinary)  # BLOB 사용
```

**참고:** LOB 동작은 드라이버에 따라 다릅니다:
- **CUBRIDdb** (C 확장): LOB 컬럼이 raw 바이트나 LOB 핸들을 반환할 수 있음
- **pycubrid** (순수 Python): LOB 컬럼이 메타데이터 딕셔너리 반환 (`lob_type`, `lob_length`, `file_locator`, `packed_lob_handle`)

간단한 사용 사례에는 문자열/바이트를 직접 삽입하면 LOB 컬럼에 저장됩니다.

---

### 컬렉션 타입 (SET, MULTISET, SEQUENCE)

**리플렉션:** 컬렉션 컬럼이 있는 테이블을 리플렉트하면 방언이 적절한 SQLAlchemy 타입으로 되돌려 매핑합니다:

```python
from sqlalchemy import inspect

inspector = inspect(engine)
columns = inspector.get_columns("products")
for col in columns:
    print(f"{col['name']}: {col['type']}")
    # tags: SET(VARCHAR(50))
    # categories: MULTISET(VARCHAR(50))
```

**컬렉션 데이터 삽입:** raw SQL에서 CUBRID의 컬렉션 리터럴 구문을 사용하세요:

```sql
INSERT INTO products (tags) VALUES ({'red', 'blue', 'green'});
```

---

### Decimal 정밀도

**증상:** Decimal 값이 정밀도를 잃음.

**해결:** 정확한 십진 연산을 위해 `NUMERIC(precision, scale)`을 사용하세요:

```python
from sqlalchemy_cubrid import NUMERIC

class Product(Base):
    __tablename__ = "products"
    price: Mapped[Decimal] = mapped_column(NUMERIC(10, 2))
    # 소수점 이하 2자리로 정확히 10자리 저장
```

CUBRID는 최대 38자리 정밀도를 지원합니다.

---

## 스키마 리플렉션 문제

### 리플렉션 중 테이블을 찾을 수 없음

**증상:**

```
NoSuchTableError: table_name
```

**원인:**

1. **테이블이 존재하지 않음** — CUBRID에서 직접 확인
2. **대소문자 구분** — CUBRID는 식별자를 (SQL 표준이 대문자로 폴딩하는 것과 달리) **소문자**로 폴딩합니다:

   ```python
   # CUBRID는 테이블 이름을 소문자로 저장
   inspector = inspect(engine)
   tables = inspector.get_table_names()
   print(tables)  # ['users', 'products'] — 전부 소문자
   ```

3. **잘못된 데이터베이스** — 연결 URL이 올바른 데이터베이스를 가리키는지 확인

---

### 테이블 이름의 대소문자 구분

**CUBRID는 인용되지 않은 식별자를 소문자로 폴딩합니다.** 이것은 PostgreSQL(소문자)과 Oracle(대문자)과 다릅니다.

```python
# 전부 같은 테이블을 가리킴
conn.execute(text("CREATE TABLE MyTable (id INT)"))  # 'mytable'로 저장
conn.execute(text("SELECT * FROM MYTABLE"))          # 'mytable' 발견
conn.execute(text("SELECT * FROM mytable"))          # 'mytable' 발견

# 대소문자를 보존하려면 큰따옴표 사용
conn.execute(text('CREATE TABLE "MyTable" (id INT)'))  # 'MyTable'로 저장
conn.execute(text('SELECT * FROM "MyTable"'))          # 반드시 인용 필요
```

방언의 `CubridIdentifierPreparer`가 `requires_name_normalize = True`와 `initial_quote = '"'` 설정으로 이것을 자동 처리합니다.

---

### 뷰 리플렉션

**지원됩니다.** `inspector.get_view_names()`를 사용하세요:

```python
inspector = inspect(engine)
views = inspector.get_view_names()
print(views)  # ['my_view', 'active_users_view']
```

---

### 스키마 지원 없음

**CUBRID는 단일 스키마 모델을 사용합니다.** PostgreSQL과 달리 데이터베이스 내에 여러 스키마 개념이 없습니다.

```python
# 잘못됨 — CUBRID는 schema 파라미터 미지원
inspector.get_table_names(schema="public")

# 올바름 — schema 생략
inspector.get_table_names()
```

코드가 여러 데이터베이스(PostgreSQL + CUBRID)에서 동작해야 한다면 조건문으로 처리하세요:

```python
schema = None if dialect_name == "cubrid" else "public"
tables = inspector.get_table_names(schema=schema)
```

---

## ORM 문제

### autoincrement와 lastrowid

**CUBRID는 자동 생성 기본 키에 (시퀀스가 아니라) `AUTO_INCREMENT`를 사용합니다**:

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
```

**삽입 후 ID는 `flush()`로 사용 가능합니다:**

```python
with Session(engine) as session:
    user = User(name="Alice")
    session.add(user)
    session.flush()
    print(user.id)  # 자동 생성 ID
    session.commit()
```

방언은 `CubridExecutionContext`에 `get_lastrowid()`를 구현하며, `raw_conn.get_last_insert_id()`를 호출합니다 (드라이버 메서드를 사용할 수 없으면 SQL의 `SELECT LAST_INSERT_ID()`로 폴백).

---

### 시퀀스 없음 — AUTO_INCREMENT 사용

**증상:**

```
CompileError: sequences are not supported by this dialect
```

**원인:** CUBRID는 SQL 시퀀스를 지원하지 않습니다. 대신 `AUTO_INCREMENT` 컬럼을 사용하세요:

```python
# 잘못됨 — 시퀀스 미지원
from sqlalchemy import Sequence
id = Column(Integer, Sequence("user_id_seq"), primary_key=True)

# 올바름 — autoincrement 사용
id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
```

---

### 릴레이션십 캐스케이드 동작

**외래 키 캐스케이드는 CUBRID에서 정상 동작합니다**:

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    posts: Mapped[list["Post"]] = relationship(back_populates="author", cascade="all, delete-orphan")

class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    author: Mapped["User"] = relationship(back_populates="posts")
```

---

### 대량 삽입 성능

**많은 행을 삽입하려면**, dict 리스트와 함께 `insert().values()`를 사용하세요:

```python
from sqlalchemy import insert

with engine.begin() as conn:
    conn.execute(
        insert(users),
        [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
            {"name": "Charlie", "email": "charlie@example.com"},
        ],
    )
```

매우 큰 데이터셋에는 `executemany()`로 배치 삽입하거나 `executemany_batch()`(pycubrid 전용)를 사용하세요.

---

## DML 확장 문제

### ON DUPLICATE KEY UPDATE 동작 안 함

**증상:** `on_duplicate_key_update()`가 `AttributeError` 발생.

**원인:** 방언의 커스텀 `insert()` 대신 SQLAlchemy 내장 `insert()`를 사용 중:

```python
# 잘못됨 — 표준 SQLAlchemy insert에는 on_duplicate_key_update 없음
from sqlalchemy import insert
stmt = insert(users).values(name="Alice")
stmt = stmt.on_duplicate_key_update(name="Alice Updated")  # AttributeError!

# 올바름 — 방언의 insert 사용
from sqlalchemy_cubrid import insert
stmt = insert(users).values(name="Alice")
stmt = stmt.on_duplicate_key_update(name="Alice Updated")
```

**중복 감지가 동작하려면 테이블에 UNIQUE 또는 PRIMARY KEY 제약이 있어야 합니다.**

---

### MERGE 문 오류

**증상:** `MERGE` 문 컴파일 실패.

**체크리스트:**

1. **올바른 모듈에서 임포트:**

   ```python
   from sqlalchemy_cubrid.dml import merge
   ```

2. **필수 절이 모두 있어야 함:**

   ```python
   stmt = (
       merge(target)
       .using(source)                        # 필수
       .on(target.c.id == source.c.id)       # 필수
       .when_matched_then_update(...)        # WHEN 절 최소 하나
       .when_not_matched_then_insert(...)
   )
   ```

3. **`when_matched_then_delete()`는 선행 `when_matched_then_update()` 필요:**

   ```python
   # 잘못됨 — 갱신 없는 삭제
   merge(t).using(s).on(condition).when_matched_then_delete()

   # 올바름 — 갱신 후 삭제
   merge(t).using(s).on(condition).when_matched_then_update({...}).when_matched_then_delete(where=...)
   ```

---

### REPLACE INTO 동작

**`REPLACE INTO`는 기존 행을 삭제하고 새 행을 삽입합니다** (제자리 갱신하는 `ON DUPLICATE KEY UPDATE`와 달리):

```python
from sqlalchemy_cubrid import replace

# 이것은 충돌하는 키의 기존 행을 삭제하고,
# 새 행을 삽입함
stmt = replace(users).values(id=1, name="Alice", email="alice@new.com")
```

**경고:** 테이블이 `AUTO_INCREMENT`를 사용하면 `REPLACE INTO`는 행에 **새 auto-increment ID**를 부여합니다. 기존 행의 ID를 보존하려면 대신 `ON DUPLICATE KEY UPDATE`를 사용하세요.

---

## Alembic 마이그레이션 문제

### 방언 'cubrid'에 대한 구현을 찾을 수 없음

**증상:**

```
CommandError: No implementation found for dialect 'cubrid'
```

**해결:** `alembic` extra와 함께 설치:

```bash
pip install "sqlalchemy-cubrid[alembic]"
```

`CubridImpl` 클래스는 `alembic.ddl` 엔트리 포인트로 자동 발견됩니다. 수동 구성이 필요 없습니다.

---

### ALTER COLUMN TYPE 거부됨 (손실 변환)

**증상:**

```
Error: cannot coerce value ... (incompatible type change)
```

**CUBRID는 네이티브 `ALTER TABLE ... MODIFY`로 컬럼 데이터 타입 변경을 지원하며**, 방언이 자동으로 냅니다. 변경은 손실/호환 불가이고 `alter_table_change_type_strict` 시스템 파라미터가 `yes`일 때만 거부됩니다 (`no`이면 CUBRID가 조용히 절단할 수 있음).

**정상 사용 (네이티브 `MODIFY` 출력):**

```python
def upgrade():
    op.alter_column("users", "name", type_=sa.String(500))
```

**진짜 손실 변환에 대한 회피 — `batch_alter_table` 사용 (테이블 재생성):**

```python
def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("name", type_=sa.String(500))

def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("name", type_=sa.String(100))
```

`batch_alter_table`은 새 테이블 생성, 데이터 복사, 원본 삭제, 이름 변경을 수행합니다.

---

### RENAME COLUMN

**CUBRID는 `ALTER TABLE ... RENAME COLUMN`을 지원합니다.** 방언이 네이티브로 출력하며, `alter_column(new_column_name=...)`은 더 이상 예외를 발생시키지 않습니다. 이름 변경 + 타입 변경 결합은 단일 `CHANGE` 문으로 출력됩니다.

**정상 사용 (네이티브 `RENAME COLUMN` 출력):**

```python
def upgrade():
    op.alter_column("users", "old_name", new_column_name="new_name")
```

---

### 부분 마이그레이션 (DDL 자동 커밋)

**증상:** 마이그레이션이 중간에 실패해 데이터베이스가 불일치 상태로 남음.

**원인:** CUBRID는 모든 DDL 문(`CREATE`, `ALTER`, `DROP`)을 자동 커밋합니다. `CubridImpl`은 `transactional_ddl = False`를 설정하므로 Alembic이 DDL 연산을 롤백할 수 없습니다.

**예방:**

1. 마이그레이션을 작게 유지 — 마이그레이션당 하나의 논리적 변경
2. 먼저 스테이징 데이터베이스에서 마이그레이션 테스트
3. 마이그레이션 실행 전 데이터베이스 백업

**복구:**

```bash
# 현재 상태 확인
alembic current

# 데이터베이스를 수동 수정한 뒤 올바른 리비전으로 스탬프
alembic stamp <revision_id>
```

---

### Autogenerate가 변경을 감지하지 못함

**가능한 원인:**

1. **모델이 임포트되지 않음** — Alembic autogenerate는 `env.py` 실행 시 임포트된 모델만 봄:

   ```python
   # env.py에서 — 모든 모델 임포트
   from myapp.models import Base
   target_metadata = Base.metadata
   ```

2. **다른 스키마로 테이블이 이미 존재** — CUBRID 리플렉션이 모델 정의와 완벽히 일치하지 않을 수 있음 (예: `VARCHAR(4096)` vs `String()`)

3. **컬렉션 타입** — `SET`, `MULTISET`, `SEQUENCE` 타입의 변경은 autogenerate가 감지하지 못할 수 있음

---

## 격리 수준 문제

### 격리 수준 설정

**CUBRID의 MVCC 엔진(10.0+)은 세 가지 격리 수준을 지원합니다:**

```python
# 엔진 수준 (모든 연결에 적용)
engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",
    isolation_level="REPEATABLE READ",
)

# 연결 수준
with engine.connect().execution_options(
    isolation_level="SERIALIZABLE"
) as conn:
    result = conn.execute(text("SELECT * FROM accounts"))
```

**사용 가능한 수준:**

| SQLAlchemy 이름 | CUBRID 숫자 수준 |
|---|---|
| `"SERIALIZABLE"` | 6 |
| `"REPEATABLE READ"` | 5 |
| `"READ COMMITTED"` *(기본)* | 4 |

레거시 pre-MVCC 수준(`READ UNCOMMITTED`와 숫자 코드 1–3으로 해석되던 세분화된 class/instance 조합)은 CUBRID 10.0에서 제거되었으며 더 이상 받지 않습니다. 전달하면 `ValueError`가 발생합니다. [격리 수준](ISOLATION_LEVELS.md)을 참고하세요.

---

### DDL이 현재 트랜잭션 커밋

**모든 DDL 문은 CUBRID에서 자동 커밋됩니다.** 즉:

```python
with engine.begin() as conn:
    conn.execute(text("INSERT INTO users (name) VALUES ('Alice')"))
    conn.execute(text("CREATE TABLE temp (id INT)"))  # 모든 것을 자동 커밋!
    # 위의 INSERT는 이제 커밋됨. 아래에서 오류가 나도 롤백 안 됨
    conn.execute(text("INSERT INTO users (name) VALUES ('Bob')"))
```

**모범 사례:** 같은 트랜잭션에서 DML과 DDL을 절대 혼용하지 마세요.

---

## 트랜잭션 문제

### 데이터가 저장되지 않음

**증상:** 오류 없이 삽입됐는데 재연결 후 사라짐.

**원인:** `commit()` 누락 또는 트랜잭션 컨텍스트 미사용.

**해결:**

```python
# 옵션 1: 명시적 커밋
with engine.connect() as conn:
    conn.execute(text("INSERT INTO users (name) VALUES ('Alice')"))
    conn.commit()

# 옵션 2: begin()은 성공 시 자동 커밋
with engine.begin() as conn:
    conn.execute(text("INSERT INTO users (name) VALUES ('Alice')"))
    # 성공적 종료 시 자동 커밋

# 옵션 3: ORM 세션
with Session(engine) as session:
    session.add(User(name="Alice"))
    session.commit()
```

---

### 오토커밋 충돌

**증상:** 문장이 예기치 않게 커밋됨.

**배경:** 두 CUBRID 드라이버 모두 기본적으로 `autocommit=True`이지만, 방언이 SQLAlchemy가 트랜잭션을 관리할 수 있도록 모든 새 연결에서 `autocommit=False`로 설정합니다.

**진짜 오토커밋이 필요하면** (각 문장이 즉시 커밋):

```python
with engine.connect().execution_options(
    isolation_level="AUTOCOMMIT"
) as conn:
    conn.execute(text("INSERT INTO logs (msg) VALUES ('event')"))
    # 즉시 커밋됨
```

---

### 세이브포인트 한계

**CUBRID는 `SAVEPOINT`와 `ROLLBACK TO SAVEPOINT`를 지원하지만**, `RELEASE SAVEPOINT`는 지원하지 **않습니다**. 방언은 `do_release_savepoint()`를 no-op로 구현합니다.

```python
with engine.begin() as conn:
    conn.execute(text("INSERT INTO users (name) VALUES ('Alice')"))
    savepoint = conn.begin_nested()
    try:
        conn.execute(text("INSERT INTO users (name) VALUES ('duplicate')"))
        savepoint.commit()
    except Exception:
        savepoint.rollback()
    # Alice의 삽입은 여전히 대기 중
    conn.commit()
```

---

## 성능 문제

### 느린 스키마 리플렉션

**증상:** `inspector.get_table_names()`나 `metadata.reflect()`가 느림.

**원인:** 스키마 리플렉션은 시스템 카탈로그를 조회하며, 테이블이 많으면 느릴 수 있습니다.

**해결:** 필요한 테이블만 리플렉트하세요:

```python
# 느림 — 전체 테이블 리플렉트
metadata.reflect(bind=engine)

# 빠름 — 특정 테이블만 리플렉트
metadata.reflect(bind=engine, only=["users", "products", "orders"])
```

---

### 연결 오버헤드

**각 연결은 다단계 CAS 핸드셰이크를 수행합니다.** 커넥션 풀링을 사용하세요:

```python
# 기본 풀 (웹 앱 권장)
engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",
    pool_size=5,
    pool_pre_ping=True,
)

# 스크립트용 NullPool (풀링 없음)
from sqlalchemy.pool import NullPool
engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",
    poolclass=NullPool,
)
```

---

### 문장 캐싱

**방언은 SQLAlchemy의 문장 캐싱을 지원합니다** (`supports_statement_cache = True`). SQLAlchemy 2.0에서 기본 활성화되며 반복 쿼리의 컴파일 오버헤드를 크게 줄입니다.

구성이 필요 없습니다 — 자동으로 동작합니다.

---

## Docker 문제

### 컨테이너는 시작되는데 연결 안 됨

**해결:**

```bash
# 1. 컨테이너가 실제로 실행 중인지 확인
docker compose ps

# 2. 브로커 초기화 대기 (~10초 소요)
docker compose up -d && sleep 10

# 3. 연결 테스트
python3 -c "
from sqlalchemy import create_engine, text
engine = create_engine('cubrid+pycubrid://dba@localhost:33000/testdb')
with engine.connect() as conn:
    print(conn.execute(text('SELECT 1')).scalar())
"
```

---

### 데이터베이스가 생성되지 않음

**Docker 이미지는 `CUBRID_DB`에 지정된 데이터베이스만 생성합니다:**

```yaml
services:
  cubrid:
    image: cubrid/cubrid:11.2
    environment:
      CUBRID_DB: testdb  # 이 데이터베이스만 생성됨
    ports:
      - "33000:33000"
```

연결 URL이 다른 데이터베이스 이름을 사용하면 실패합니다. `CUBRID_DB`를 연결 URL과 일치시키세요.

---

### 버전별 동작

**CUBRID 버전을 명시적으로 지정하세요:**

```bash
# 기본 (11.2)
docker compose up -d

# 특정 버전
CUBRID_VERSION=11.4 docker compose up -d
CUBRID_VERSION=10.2 docker compose up -d
```

**알려진 버전 차이:**

| 기능 | CUBRID 10.2 | CUBRID 11.0+ |
|---|---|---|
| `UPDATE`의 `LIMIT` | ❌ | ✅ |
| `CTE` (WITH 절) | ❌ | ✅ |
| `MERGE` | ✅ | ✅ |
| 인덱스 코멘트 | ❌ | ✅ |

---

## 디버깅 기법

## 문제 해결 의사결정 흐름

```mermaid
flowchart TD
    start[Issue observed] --> kind{Primary symptom}
    kind -->|Import / Module error| install[Check driver install]
    kind -->|Connection failure| conn[Validate URL, host, port, credentials]
    kind -->|SQL compile/runtime error| sql[Inspect generated SQL and unsupported feature]
    kind -->|Migration failure| mig[Check Alembic limitations and DDL auto-commit]
    kind -->|Performance issue| perf[Check pool settings, indexes, statement patterns]

    install --> i1{CUBRIDdb or pycubrid?}
    i1 -->|CUBRIDdb| i2[Install CUBRID-Python and CCI dependencies]
    i1 -->|pycubrid| i3[Install pycubrid and use cubrid+pycubrid URL]

    conn --> c1{Broker reachable?}
    c1 -->|No| c2[Start broker / docker service and verify port 33000]
    c1 -->|Yes| c3[Enable pool_pre_ping and review SESSION_TIMEOUT]

    sql --> s1{Using unsupported feature?}
    s1 -->|RETURNING / ARRAY| s2[Refactor using supported CUBRID patterns]
    s1 -->|No| s3[Enable SQLAlchemy echo and inspect raw SQL]

    mig --> m1[Split migration into atomic DDL steps]
    perf --> p1[Profile query plan, batch size, lock scope]
```

!!! tip "재현 가능성으로 시작"
    실패 사례를 엔진 하나, 테이블 하나, 쿼리 하나인 최소 스크립트로 축소하세요.
    문제가 드라이버인지, 방언인지, 애플리케이션 로직인지 빠르게 식별할 수 있습니다.

!!! warning "컴파일 오류와 런타임 오류 구분"
    - 컴파일 오류는 SQL이 전송되기 전에 발생.
    - 런타임 오류는 CUBRID나 드라이버에서 발생.
    - 디버깅 경로가 다릅니다.

!!! tip "이슈 리포트에 환경 상세 포함"
    방언 버전, SQLAlchemy 버전, 드라이버(`CUBRIDdb` 또는 `pycubrid`),
    CUBRID 서버 버전, 사용한 정확한 연결 URL 형식을 포함하세요.

### SQL 로깅 활성화

```python
# 방법 1: echo=True
engine = create_engine("cubrid://dba@localhost:33000/testdb", echo=True)

# 방법 2: Python 로깅
import logging
logging.basicConfig()
logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)
```

출력에는 SQL 문, 파라미터, 실행 시간이 포함됩니다.

### 방언 버전 확인

```python
import sqlalchemy_cubrid
print(sqlalchemy_cubrid.__version__)  # 예: "1.4.0"

from sqlalchemy import create_engine
engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")
print(engine.dialect.name)            # "cubrid"
print(engine.dialect.server_version_info)  # (11, 2, 0, 378)
```

### 컴파일된 SQL 검사

```python
from sqlalchemy.dialects import registry

# 실행 없이 CUBRID용 문장 컴파일
from sqlalchemy_cubrid.dialect import CubridDialect

stmt = select(users).where(users.c.name == "Alice")
compiled = stmt.compile(dialect=CubridDialect())
print(str(compiled))
print(compiled.params)
```

### 연결 테스트 스크립트

```python
#!/usr/bin/env python3
"""Quick sqlalchemy-cubrid connection test."""
import sys
from sqlalchemy import create_engine, text, inspect

url = "cubrid+pycubrid://dba@localhost:33000/testdb"
try:
    engine = create_engine(url)
    with engine.connect() as conn:
        version = conn.execute(text("SELECT VERSION()")).scalar()
        print(f"✅ Connected to CUBRID {version}")

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✅ Found {len(tables)} tables: {tables[:5]}{'...' if len(tables) > 5 else ''}")

    print("✅ All checks passed")
except Exception as e:
    print(f"❌ Failed: {e}")
    sys.exit(1)
```

---

*참고: [연결 가이드](CONNECTION.md) · [타입 매핑](TYPES.md) · [DML 확장](DML_EXTENSIONS.md) · [Alembic](ALEMBIC.md) · [기능 지원](FEATURE_SUPPORT.md)*
