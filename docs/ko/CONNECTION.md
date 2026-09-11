# 연결과 드라이버 설정 (한국어)

> 🌐 [CONNECTION.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/CONNECTION.md)의 번역입니다. 영어 원문이 표준이며, 페이지 번역은 경고 수준의 동기화 규칙을 따릅니다.

이 가이드는 CUBRID Python 드라이버 설치, SQLAlchemy 연결 문자열 구성, 연결 수명 주기의 이해를 다룹니다.

---

## 목차

- [사전 준비](#사전-준비)
- [CUBRID Python 드라이버 설치](#cubrid-python-드라이버-설치)
- [연결 문자열 형식](#연결-문자열-형식)
- [엔트리 포인트](#엔트리-포인트)
- [방언의 URL 변환 방식](#방언의-url-변환-방식)
- [연결 옵션](#연결-옵션)
- [오토커밋 동작](#오토커밋-동작)
- [서버 버전 감지](#서버-버전-감지)
- [문제 해결](#문제-해결)

---

## 사전 준비

| 요구사항           | 버전            |
|--------------------|-----------------|
| Python             | 3.10+           |
| SQLAlchemy         | 2.0 – 2.1       |
| CUBRID 서버        | 10.2 – 11.4     |
| CUBRID Python 드라이버 | pycubrid (권장) 또는 CUBRID-Python (레거시) |

---

## CUBRID Python 드라이버 설치

### 권장: 순수 Python 드라이버 (pycubrid)

새 프로젝트에는 순수 Python [pycubrid](https://github.com/cubrid-lab/pycubrid) 드라이버를 사용하세요 — pip만으로 설치되고, C 빌드 도구 체인이 필요 없고, Python이 돌아가는 어디서든 동작합니다:

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

또는 따로 설치:

```bash
pip install sqlalchemy-cubrid pycubrid
```

그리고 `cubrid+pycubrid://` URL 스킴을 사용하세요:

```python
engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")
```

> **팁**: `pycubrid`는 순수 Python 구현입니다 — 네이티브 라이브러리 의존성 없이 Python이 돌아가는 어디서든 동작합니다. [GitHub의 pycubrid](https://github.com/cubrid-lab/pycubrid)를 참고하세요.

### 레거시: C 확장 드라이버 (CUBRID-Python)

레거시 [CUBRID-Python](https://github.com/CUBRID/cubrid-python) C 확장 드라이버는 `cubrid://` URL에 묶여 있습니다. `[cubriddb]` extra로 설치하고 `cubrid+cubriddb://` URL 스킴으로 명시적으로 선택하세요:

```bash
pip install "sqlalchemy-cubrid[cubriddb]"
```

또는 드라이버를 직접 설치:

```bash
pip install sqlalchemy-cubrid CUBRID-Python
```

> **참고**: `CUBRID-Python`은 C 확장 드라이버입니다. 일부 플랫폼에서는 CUBRID CCI 라이브러리가 필요할 수 있습니다. 플랫폼별 지침은 [CUBRID Python 드라이버 문서](https://www.cubrid.org/manual/en/11.0/api/python.html)를 참고하세요.

---

## 연결 문자열 형식

SQLAlchemy는 표준 URL 방식 연결 문자열을 사용합니다:

```
cubrid://user:password@host:port/database
```

### 예제

```python
from sqlalchemy import create_engine

# 기본 연결
engine = create_engine("cubrid://dba:password@localhost:33000/demodb")

# 비밀번호 없이 (CUBRID는 기본적으로 dba의 비밀번호 없는 접근을 허용)
engine = create_engine("cubrid://dba@localhost:33000/testdb")

# 명시적 드라이버 이름 (C 확장)
engine = create_engine("cubrid+cubrid://dba:password@localhost:33000/demodb")

# pycubrid 순수 Python 드라이버 사용
engine = create_engine("cubrid+pycubrid://dba:password@localhost:33000/demodb")
```

### URL 구성 요소

| 구성 요소  | 기본값        | 설명                                   |
|------------|---------------|----------------------------------------|
| `user`     | *(필수)*      | 데이터베이스 사용자 이름 (보통 `dba`)  |
| `password` | *(비어 있음)* | 데이터베이스 비밀번호                  |
| `host`     | `localhost`   | CUBRID 서버 호스트명 또는 IP           |
| `port`     | `33000`       | CUBRID 브로커 포트                     |
| `database` | *(필수)*      | 데이터베이스 이름                      |

---

## 엔트리 포인트

방언은 다음 SQLAlchemy 엔트리 포인트를 등록합니다:

| URL 스킴             | 드라이버    | 설명                                  |
|----------------------|-------------|----------------------------------------|
| `cubrid://`          | CUBRIDdb    | 기본 레거시 C 확장 드라이버           |
| `cubrid+cubrid://`   | CUBRIDdb    | 명시적 레거시 C 확장 드라이버         |
| `cubrid+cubriddb://` | CUBRIDdb    | 명시적 레거시 C 확장 드라이버         |
| `cubrid+pycubrid://` | pycubrid    | 순수 Python 드라이버 (C 빌드 불필요)  |
| `cubrid+aiopycubrid://` | pycubrid.aio | 비동기 순수 Python 드라이버        |

새 프로젝트는 `cubrid+pycubrid://`를 권장합니다 (순수 Python, 설치 가장 쉬움, 네이티브 빌드 단계 없음). `cubrid://` URL은 레거시 CUBRIDdb C 확장 드라이버에 묶입니다. 명시적으로 선택하려면 `[cubriddb]` 설치 extra와 함께 `cubrid+cubriddb://`를 사용하세요.

---

## 비동기 연결

비동기 애플리케이션에서는 `create_async_engine`과 함께 `cubrid+aiopycubrid://` URL 스킴을 사용하세요. `pycubrid>=1.3.2,<2.0`이 필요합니다.

```python
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

engine = create_async_engine("cubrid+aiopycubrid://dba@localhost:33000/testdb")

async with engine.connect() as conn:
    result = await conn.execute(text("SELECT 1"))
    print(result.scalar())
```

### PK 조회를 동반한 비동기 삽입

CUBRID에는 `RETURNING` 절이 없습니다. 비동기 ORM 삽입 후 auto-increment 기본 키를 얻으려면, 트랜잭션 블록 안에서 `await session.flush()`를 호출해 커밋 전에 객체의 PK를 채우세요:

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

engine = create_async_engine("cubrid+aiopycubrid://dba@localhost:33000/testdb")

async with AsyncSession(engine) as session:
    async with session.begin():
        user = User(name="Alice")
        session.add(user)
        await session.flush()  # 커밋 없이 user.id 채움
        print(f"Inserted id={user.id}")
```

PK가 필요한 Core 수준 삽입에서는 문장 후에 `SELECT LAST_INSERT_ID()`를 실행하세요 (README → 알려진 한계 참고).

## 방언의 URL 변환 방식

내부적으로 방언은 SQLAlchemy URL을 CUBRID 네이티브 연결 형식으로 변환합니다:

```
SQLAlchemy URL:  cubrid://dba:password@myhost:33000/mydb
                        ↓
CUBRID native:   CUBRID:myhost:33000:mydb:::
```

`create_connect_args()` 메서드가 CUBRID Python 드라이버의 `connect()` 함수에 위치 인자로 `(connect_url, username, password)`를 반환합니다.

### 변환 상세

```python
# CUBRIDdb (C 확장 드라이버):
connect_url = f"CUBRID:{host}:{port}:{database}:::"
args = (connect_url, username, password)
# → CUBRIDdb.connect("CUBRID:myhost:33000:mydb:::", "dba", "password")
```

CUBRID 연결 문자열 끝의 `:::`는 세 개의 빈 선택 파라미터입니다 (CUBRID가 향후 사용을 위해 예약).

### pycubrid 변환

pycubrid 방언은 키워드 인자를 직접 전달합니다:

```python
# pycubrid (순수 Python 드라이버):
kwargs = {"host": host, "port": port, "database": database, "user": user, "password": password}
# → pycubrid.connect(host="myhost", port=33000, database="mydb", user="dba", password="password")
```

---

## 연결 옵션

### 엔진 수준 옵션

```python
engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",

    # 모든 연결의 기본 격리 수준 설정
    isolation_level="REPEATABLE READ",

     # SQLAlchemy 2.0–2.1 커넥션 풀 설정
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,

    # SQL 로깅 활성화
    echo=True,
)
```

### 연결별 격리 수준

```python
with engine.connect().execution_options(
    isolation_level="SERIALIZABLE"
) as conn:
    # 이 연결은 SERIALIZABLE 격리 사용
    result = conn.execute(text("SELECT * FROM accounts"))
```

지원되는 모든 수준은 [격리 수준](ISOLATION_LEVELS.md)을 참고하세요.

### 백슬래시 이스케이프 (`no_backslash_escapes`)

CUBRID의 `no_backslash_escapes` 시스템 파라미터 기본값은 `yes`입니다. 즉 백슬래시는 문자열 리터럴에서 **리터럴 문자**입니다 (MySQL과 반대). 방언은 이 기본값에 맞습니다: `literal_binds=True`로 렌더링된 인라인 SQL 리터럴은 백슬래시를 그대로 보존하며 doubling하지 **않습니다**.

```python
# 기본: 백슬래시 보존 (서버에서 no_backslash_escapes=yes)
engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")
```

서버가 명시적으로 `no_backslash_escapes=no`로 설정된 경우(백슬래시가 이스케이프 문자로 동작), `no_backslash_escapes=False`를 전달해 방언이 인라인 리터럴 렌더링 시 백슬래시를 doubling하게 하세요:

```python
# 서버가 no_backslash_escapes=no로 구성됨
engine = create_engine(
    "cubrid+pycubrid://dba@localhost:33000/testdb",
    no_backslash_escapes=False,
)
```

이것은 연결 협상이 아니라 정적 방언 옵션입니다 — `literal_binds` 컴파일은 라이브 연결 없이 오프라인으로 실행될 수 있기 때문입니다. 인라인 리터럴 렌더링에만 영향을 미치며, 파라미터 바인딩 값은 이 설정과 무관하게 항상 드라이버가 올바르게 이스케이프합니다.

---

## 오토커밋 동작

### 드라이버 기본값과 방언 오버라이드

두 CUBRID Python 드라이버 모두 기본적으로 `autocommit=True`입니다. 방언은 SQLAlchemy가 트랜잭션을 올바르게 관리할 수 있도록 모든 새 연결에서 이를 오버라이드합니다. CUBRIDdb는 `conn.set_autocommit(False)`를, pycubrid는 속성 세터 `conn.autocommit = False`를 사용합니다.

### DDL 오토커밋 감지

CUBRID는 DDL 문을 암시적으로 커밋합니다. 방언은 DDL 패턴을 감지해 다음에 대해 오토커밋을 활성화합니다:

- `CREATE`, `ALTER`, `DROP`
- `GRANT`, `REVOKE`
- `TRUNCATE`
- `MERGE`

이것은 정규식 패턴을 사용하는 `CubridExecutionContext.should_autocommit_text()` 메서드가 처리합니다.

---

## 서버 버전 감지

방언은 초기화 시 서버 버전을 조회합니다:

```sql
SELECT VERSION()
```

결과(예: `11.2.0.0374`)는 내부 버전 검사를 위해 튜플 `(11, 2, 0, 374)`로 파싱됩니다.

---

## 문제 해결

### 흔한 연결 오류

#### `ImportError: No module named 'CUBRIDdb'`

CUBRID Python 드라이버가 설치되지 않았습니다:

```bash
pip install CUBRID-Python
```

#### 포트 33000에서 `Connection refused`

1. CUBRID 브로커 실행 확인:
   ```bash
   cubrid broker status
   ```

2. `cubrid_broker.conf`의 브로커 포트 확인 — 기본값은 `33000`.

3. Docker 사용 시:
   ```bash
   docker compose up -d
   docker compose logs cubrid
   ```

#### `Authentication failed`

CUBRID 기본 `dba` 사용자에게는 비밀번호가 없습니다. 설정했다면 연결 문자열과 일치하는지 확인하세요:

```python
# dba에 비밀번호가 없으면
engine = create_engine("cubrid://dba@localhost:33000/testdb")

# dba에 비밀번호가 있으면
engine = create_engine("cubrid://dba:mypassword@localhost:33000/testdb")
```

### Docker 퀵스타트

로컬 개발에는 제공되는 `docker-compose.yml`을 사용하세요:

```bash
# CUBRID 11.2 시작 (기본)
docker compose up -d

# 특정 버전 시작
CUBRID_VERSION=11.4 docker compose up -d

# 실행 확인
docker compose ps

# 연결
python -c "
from sqlalchemy import create_engine, text
engine = create_engine('cubrid://dba@localhost:33000/testdb')
with engine.connect() as conn:
    print(conn.execute(text('SELECT VERSION()')).scalar())
"
```

---

## 커넥션 풀 튜닝

SQLAlchemy는 기본적으로 커넥션 풀을 관리합니다. CUBRID가 풀과 상호작용하는 방식을 이해하는 것이 프로덕션 배포에 중요합니다.

### 핵심 풀 파라미터

```python
from sqlalchemy import create_engine

engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",

    # 풀 크기: 유지할 지속 연결 수
    pool_size=5,           # 기본: 5

    # 오버플로: pool_size를 넘어 허용되는 추가 연결
    max_overflow=10,       # 기본: 10

    # 타임아웃: 풀에서 연결을 얻기까지 대기 초
    pool_timeout=30,       # 기본: 30

    # 재활용: 연결이 교체되기까지의 초
    # CUBRID 브로커의 SESSION_TIMEOUT보다 낮게 설정
    pool_recycle=1800,     # 권장: 1800 (30분)

    # 사전 핑: 체크아웃 전 연결 생존 테스트
    pool_pre_ping=True,    # 프로덕션 권장: True
)
```

### `pool_pre_ping` (권장)

`pool_pre_ping=True`이면 SQLAlchemy는 연결을 애플리케이션에 넘기기 전에 `do_ping()`을 호출합니다. CUBRIDdb 방언은 CUBRID Python 드라이버의 네이티브 `connection.ping()` 메서드를 사용합니다. pycubrid 방언 둘 다 이제 pycubrid의 네이티브 `Connection.ping(False)` / `AsyncConnection.ping(False)` `CHECK_CAS` 경로를 사용해, 추가 `SELECT 1` 왕복 없이 끊어진 연결 오류를 방지합니다.

이것은 다음 상황에서 발생하는 "끊어진 연결" 오류를 방지합니다:

- CUBRID 브로커 재시작
- 네트워크 중단
- 브로커의 `SESSION_TIMEOUT` 만료

```python
# 프로덕션 권장 구성
engine = create_engine(
    "cubrid://dba@localhost:33000/mydb",
    pool_pre_ping=True,
    pool_recycle=1800,
)
```

### `pool_recycle`과 CUBRID 브로커 타임아웃

CUBRID 브로커에는 `SESSION_TIMEOUT` 설정이 있습니다 (버전에 따라 다르지만 보통 300초). 풀링된 연결이 이 타임아웃보다 오래 유휴 상태이면 브로커가 서버 측에서 닫습니다.

**항상 `pool_recycle`을 `SESSION_TIMEOUT`보다 낮게 설정**해 끊어진 연결을 피하세요:

```python
# CUBRID 브로커 SESSION_TIMEOUT이 300(5분)이면
engine = create_engine(
    "cubrid://dba@localhost:33000/mydb",
    pool_recycle=240,  # 브로커 타임아웃 전에 재활용
)
```

### 연결 해제 감지

방언은 드라이버 오류 메시지 문구 변경에 강건한 계층적 전략으로 연결 실패를 감지하는 `is_disconnect()`를 구현합니다:

1. **숫자 오류 코드 매칭 (주)** — `ER_COMMUNICATION`(-4, pycubrid), `CAS_ER_COMMUNICATION`(-21003/-21005), `ER_NET_CANT_CONNECT`(-10005), `ER_NET_SERVER_COMM_ERROR`(-10007) 등 안정적인 CUBRID/CCI 코드를 검사.
2. **명시적 `OSError` 원인 체인 (문구 무관)** — 예외의 명시적 `__cause__` 체인(`raise ... from`)에 `OSError`(예: 소켓 오류)이 있으면 메시지 문구와 무관하게 연결이 끊긴 것으로 간주. 무관한 진행 중 `OSError`가 살아있는 연결을 오탐 무효화하지 않도록 암시적 `__context__`는 의도적으로 무시.
3. **메시지 매칭 (폴백)** — 알려진 연결 해제 패턴("connection is closed", "broker is not available", "connection reset" 등)을 오류 메시지에서 검사. `OperationalError`가 없는 레거시 CUBRIDdb 드라이버와 코드도 `OSError` 원인도 없는 pycubrid의 클라이언트 측 문자열 전용 오류(예: "connection lost during receive")를 커버.

감지는 의도적으로 보수적입니다: 해제 코드도, `OSError` 원인도, 해제 메시지도 아닌 데이터베이스 오류(예: 잘못된 격리 수준 오류, 닫힌 커서 오용)는 연결 해제로 취급하지 **않아** 오탐 풀 무효화를 피합니다.

연결 해제가 감지되면 SQLAlchemy가 자동으로 연결을 무효화하고 풀에서 새 연결을 만듭니다.

### 오류 코드 매핑

CUBRID 드라이버 예외는 적절한 SQLAlchemy 예외 타입으로 매핑됩니다. 드라이버는 제한된 예외 계층을 노출합니다:

| CUBRID 드라이버 예외 | SA 예외 매핑 |
|---|---|
| `Error` (기본) | `DBAPIError` |
| `InterfaceError` | `InterfaceError` |
| `DatabaseError` | `DatabaseError` |
| `NotSupportedError` | `NotSupportedError` |

> **참고**: CUBRIDdb는 `OperationalError`, `ProgrammingError`, `InternalError`, `DataError`를 제공하지 않습니다. 모든 데이터베이스 수준 오류는 `DatabaseError`로 발생합니다.

### 풀 구성 권장사항

| 시나리오 | `pool_size` | `pool_recycle` | `pool_pre_ping` |
|---|---|---|---|
| 개발 | 2 | -1 (비활성) | False |
| 웹 애플리케이션 | 5–10 | 1800 | True |
| 고동시성 | 10–20 | 900 | True |
| 백그라운드 워커 | 2–5 | 600 | True |

### 단기 스크립트용 NullPool

스크립트나 일회성 작업에는 풀링을 완전히 끄세요:

```python
from sqlalchemy.pool import NullPool

engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",
    poolclass=NullPool,
)
```

---

## 연결 URL 파싱 흐름

```mermaid
flowchart TD
    input[SQLAlchemy URL string] --> parse[SQLAlchemy URL parser]
    parse --> check{Driver name}
    check -->|cubrid or cubrid+cubrid or cubrid+cubriddb| cext[Build CUBRID native DSN]
    check -->|cubrid+pycubrid| pykw[Build pycubrid kwargs]
    check -->|cubrid+aiopycubrid| aio[Build pycubrid.aio kwargs]
    cext --> connect1["CUBRIDdb.connect(url, user, password)"]
    pykw --> connect2["pycubrid.connect(host, port, database, user, password)"]
    aio --> connect3["pycubrid.aio.connect(...)"]
    connect1 --> session[Dialect on_connect sets autocommit=False]
    connect2 --> session
    connect3 --> session
```

!!! warning "올바른 방언 접두사 사용"
    `pycubrid://...`는 유효한 SQLAlchemy URL 스킴이 아닙니다.
    항상 `cubrid+pycubrid://...`를 사용하세요.

!!! warning "브로커 포트를 쿼리 문자열로 전달 금지"
    `...?port=33000`이 아니라 `...@host:33000/dbname`을 사용하세요.

!!! tip "프로덕션에서는 `pool_pre_ping=True` 권장"
    브로커 재시작이나 유휴 타임아웃 만료 후 끊어진 연결 실패를 방지합니다.

---

*참고: [격리 수준](ISOLATION_LEVELS.md) · [타입 매핑](TYPES.md) · [기능 지원](FEATURE_SUPPORT.md)*
