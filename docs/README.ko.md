# sqlalchemy-cubrid

**CUBRID 데이터베이스를 위한 SQLAlchemy 2.0–2.2 방언** — SQLAlchemy 및 CUBRID 전용 타입을 위한 Python ORM, 스키마 리플렉션, Alembic 마이그레이션, 타입 매핑을 제공합니다.

[🇰🇷 한국어](README.ko.md) · [🇺🇸 English](../README.md) · [🇨🇳 中文](README.zh.md) · [🇮🇳 हिन्दी](README.hi.md) · [🇩🇪 Deutsch](README.de.md) · [🇷🇺 Русский](README.ru.md)

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

> **상태: Production/Stable** — CUBRID 10.2–11.4 및 SQLAlchemy 2.0–2.2을 지원하는 유지보수 다이얼렉트입니다. 모든 PR에 대해 라이브 DB 통합 CI가 실행됩니다.

## 왜 sqlalchemy-cubrid인가?

CUBRID는 고성능 오픈소스 관계형 데이터베이스로, 한국 공공기관 및 기업 환경에서
널리 사용되고 있습니다. 지금까지 최신 2.0–2.2 API를 지원하는 SQLAlchemy 방언은
활발히 유지보수되지 않았습니다.

**sqlalchemy-cubrid**는 이 공백을 메웁니다:

- **statement caching**과 **PEP 561 타입 지원**을 갖춘 완전한 SQLAlchemy 2.0–2.2 방언
- **오프라인 테스트 619개**, **약 98.26% 코드 커버리지** — 데이터베이스 없이도 실행 가능
- **동시성 스트레스 테스트** — `QueuePool` 기반 동기 스레드 + `asyncio.gather` 워크로드를 실 CUBRID에서 검증
- **SQLAlchemy 2.2 대응 compat shim** — private API 접근을 `_compat.py`로 감쌌지만, 완전한 2.2 검증 전까지는 `<2.3`로 고정
- **Python 3.10 -- 3.14** 전반에서 **4개 CUBRID 버전**(10.2, 11.0, 11.2, 11.4) 테스트 완료
- CUBRID 전용 DML 구문: `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`
- Alembic 마이그레이션 기본 지원
- **세 가지 드라이버 옵션** — C 확장(`cubrid://`), 순수 Python(`cubrid+pycubrid://`), 비동기 순수 Python(`cubrid+aiopycubrid://`)

## 아키텍처

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

## 요구 사항

- Python 3.10+
- SQLAlchemy 2.0 – 2.2
- [CUBRID-Python](https://github.com/CUBRID/cubrid-python) (C 확장) **또는** [pycubrid](https://github.com/cubrid-lab/pycubrid) (순수 Python)

## 설치

```bash
pip install sqlalchemy-cubrid
```

순수 Python 드라이버 사용 시(C 빌드 불필요):

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

Alembic 지원 포함:

```bash
pip install "sqlalchemy-cubrid[alembic]"
```

## 빠른 시작

### Core (연결 수준)

```python
from sqlalchemy import create_engine, text

engine = create_engine("cubrid://dba:password@localhost:33000/demodb")

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.scalar())
```

### ORM (세션 수준)

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


engine = create_engine("cubrid://dba:password@localhost:33000/demodb")
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

## 주요 기능

- SQLAlchemy 표준 타입과 CUBRID 전용 타입을 위한 타입 매핑 — 숫자, 문자열, 날짜/시간, 비트, LOB, 컬렉션, JSON 타입
- SQL 컴파일 -- SELECT, JOIN, CAST, LIMIT/OFFSET, 서브쿼리, CTE, 윈도우 함수
- DML 확장 -- `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`, `FOR UPDATE`, `TRUNCATE`
- DDL 지원 -- `COMMENT`, `IF NOT EXISTS` / `IF EXISTS`, `AUTO_INCREMENT`
- 스키마 리플렉션 -- 테이블, 뷰, 컬럼, PK, FK, 인덱스, 유니크 제약 조건, 코멘트
- `CubridImpl`을 통한 Alembic 마이그레이션 (자동 탐색 엔트리 포인트)
- CUBRID의 세 가지 MVCC 격리 수준 — `READ COMMITTED`(기본값), `REPEATABLE READ`, `SERIALIZABLE`
- Async 지원 — pycubrid.aio 기반 `create_async_engine("cubrid+aiopycubrid://...")`

## 알려진 제한 사항

- **`RETURNING` 미지원** — `INSERT/UPDATE/DELETE ... RETURNING`은 지원되지 않으며, 대신 `cursor.lastrowid` 또는 `LAST_INSERT_ID()`를 사용해야 합니다
- **시퀀스 없음** — CUBRID는 `AUTO_INCREMENT`만 사용합니다
- **멀티 스키마 미지원** — 데이터베이스당 단일 스키마 모델입니다
- **DDL 자동 커밋** — 마이그레이션은 트랜잭션 처리되지 않습니다(`transactional_ddl = False`)
- **SQLAlchemy 2.0–2.2만 지원** — 내부 API 의존성 때문에 `<2.3`로 고정되어 있습니다([자세한 내용](ARCHITECTURE.md))
- **Async는 pycubrid >= 1.2.0,<2.0 필요** — `cubrid+aiopycubrid://` 드라이버는 현재 이 프로젝트가 지원하는 async 가능 pycubrid 패키지 라인이 필요합니다

## 문서

| 가이드 | 설명 |
|---|---|
| [연결](CONNECTION.md) | 연결 문자열, URL 형식, 드라이버 설정, 풀 튜닝 |
| [타입 매핑](TYPES.md) | 전체 타입 매핑, CUBRID 전용 타입, 컬렉션 타입 |
| [DML 확장](DML_EXTENSIONS.md) | ON DUPLICATE KEY UPDATE, MERGE, REPLACE INTO, 쿼리 추적 |
| [격리 수준](ISOLATION_LEVELS.md) | CUBRID의 세 가지 MVCC 격리 수준, 설정 |
| [Alembic 마이그레이션](ALEMBIC.md) | 설정, 구성, 제한 사항, 배치 우회 방법 |
| [기능 지원](FEATURE_SUPPORT.md) | MySQL, PostgreSQL, SQLite와의 비교 |
| [ORM 활용 가이드](ORM_COOKBOOK.md) | 실용적인 ORM 예제, 관계, 쿼리 |
| [개발 가이드](DEVELOPMENT.md) | 개발 환경 설정, 테스트, Docker, 커버리지, CI/CD |
| [드라이버 호환성](DRIVER_COMPAT.md) | CUBRID-Python 드라이버 버전 및 알려진 이슈 |
| [문제 해결](TROUBLESHOOTING.md) | 일반적인 문제, 오류 해결, 디버깅 기법 |
| [비동기 연결](CONNECTION.md#async-connection) | `cubrid+aiopycubrid://`를 사용하는 async 엔진 설정 |

## 호환성 매트릭스

| 구성 요소 | 지원 버전 |
|---|---|
| Python | 3.10, 3.11, 3.12, 3.13, 3.14 |
| CUBRID | 10.2, 11.0, 11.2, 11.4 |
| SQLAlchemy | 2.0–2.2 |
| Alembic | >=1.7 |
| pycubrid (sync) | >=1.2.0,<2.0 |
| pycubrid (async) | >=1.2.0,<2.0 |

## FAQ

### SQLAlchemy로 CUBRID에 어떻게 연결하나요?

```python
from sqlalchemy import create_engine
engine = create_engine("cubrid://dba:password@localhost:33000/demodb")
```

순수 Python 드라이버(C 빌드 불필요)를 쓰려면: `create_engine("cubrid+pycubrid://dba@localhost:33000/demodb")`

### sqlalchemy-cubrid는 SQLAlchemy 2.0–2.2을 지원하나요?

예. sqlalchemy-cubrid는 SQLAlchemy 2.0–2.2용으로 만들어졌으며, `Session.execute()`, 타입이 지정된 `Mapped[]` 컬럼, statement caching을 포함한 2.0 스타일 API를 지원합니다.

### sqlalchemy-cubrid는 Alembic 마이그레이션을 지원하나요?

예. `pip install "sqlalchemy-cubrid[alembic]"`로 설치하세요. 방언은 entry point를 통해 자동 등록됩니다. 단, CUBRID는 DDL을 자동 커밋하므로 마이그레이션은 트랜잭션 처리되지 않습니다.

### 어떤 Python 버전을 지원하나요?

Python 3.10, 3.11, 3.12, 3.13, 3.14를 지원합니다.

### CUBRID는 RETURNING 절을 지원하나요?

아니요. CUBRID는 `INSERT ... RETURNING` 또는 `UPDATE ... RETURNING`을 지원하지 않습니다. 대신 `cursor.lastrowid` 또는 `SELECT LAST_INSERT_ID()`를 사용하세요.

### CUBRID에서 ON DUPLICATE KEY UPDATE는 어떻게 사용하나요?

```python
from sqlalchemy_cubrid import insert
stmt = insert(users).values(name="Alice").on_duplicate_key_update(name="Alice Updated")
```

### `cubrid://`와 `cubrid+pycubrid://`의 차이는 무엇인가요?

`cubrid://`는 컴파일이 필요한 C 확장 드라이버(CUBRIDdb)를 사용합니다. `cubrid+pycubrid://`는 pip만으로 설치되는 순수 Python 드라이버를 사용하므로 빌드 도구가 필요 없습니다. `cubrid+aiopycubrid://`는 `create_async_engine` 및 `AsyncSession`과 함께 사용하는 순수 Python 드라이버의 비동기 변형입니다.

### sqlalchemy-cubrid는 async를 지원하나요?

예. pycubrid async 드라이버와 함께 `create_async_engine("cubrid+aiopycubrid://...")`를 사용하세요. `pycubrid>=1.3.2,<2.0`이 필요합니다. 두 pycubrid 방언 모두 `pool_pre_ping`에서 네이티브 `Connection.ping(False)` / `AsyncConnection.ping(False)`를 사용하며, Core와 ORM 기능 모두 `AsyncSession`에서 동작합니다.


## 관련 프로젝트

- [pycubrid](https://github.com/cubrid-lab/pycubrid) — CUBRID용 순수 Python DB-API 2.0 드라이버
- [cubrid-cookbook-python](https://github.com/cubrid-lab/cubrid-cookbook-python) — CUBRID를 위한 프로덕션용 Python 예제

## 로드맵

이 프로젝트의 방향과 다음 마일스톤은 [`ROADMAP.md`](../ROADMAP.md)를 참고하세요.

생태계 전체 관점은 [CUBRID Labs Ecosystem Roadmap](https://github.com/cubrid-lab/.github/blob/main/ROADMAP.md)과 [프로젝트 보드](https://github.com/orgs/cubrid-lab/projects/2)를 참고하세요.

## 기여하기

가이드라인은 [CONTRIBUTING.md](../CONTRIBUTING.md), 개발 환경 설정은 [docs/DEVELOPMENT.md](DEVELOPMENT.md)를 참고하세요.

## 보안

취약점은 이메일로 제보해 주세요 -- 자세한 내용은 [SECURITY.md](../SECURITY.md)를 참고하세요. 보안 관련 사항은 공개 이슈로 등록하지 마세요.

## 라이선스

MIT -- [LICENSE](../LICENSE) 참조.
