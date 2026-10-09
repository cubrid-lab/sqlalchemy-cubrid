# PRD: sqlalchemy-cubrid — SQLAlchemy 2.0–2.1용 CUBRID 방언 (한국어)

> 🌐 [PRD.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/PRD.md)의 번역입니다. 영어 원문이 표준이며, CI가 영어 원문과의 구조 일치를 검사합니다.

## 1. 개요

**프로젝트**: sqlalchemy-cubrid
**현재 버전**: 1.8.0
**상태**: Production/Stable (활발히 유지보수 중; 비동기 + JSON 제공 완료)
**저장소**: [github.com/cubrid-lab/sqlalchemy-cubrid](https://github.com/cubrid-lab/sqlalchemy-cubrid)
**라이선스**: MIT

### 1.1 문제 정의 (원래 상태)

원래의 `sqlalchemy-cubrid` 프로젝트는 방치되어 동작하지 않는 상태였습니다:
- SQLAlchemy < 1.4를 대상으로 함 (현재는 2.0+)
- 폐기된 API 사용 (`basestring`, `inspect.getargspec`, `super(ClassName, self)`)
- 컴파일러, 타입 시스템, 리플렉션 메서드에 치명적인 버그 존재
- CI 파이프라인과 테스트가 없고, 최신 환경에 설치할 수 없었음

### 1.2 구축한 것

SQLAlchemy 2.0–2.1용 현대적 CUBRID 방언을 제공하는, 처음부터 다시 작성한 완전한 재구현입니다:

- 문장 캐싱을 갖춘 **완전한 SQLAlchemy 2.0–2.1 방언**
- **완전한 SQL 기능 커버리지** — CUBRID가 지원하는 모든 것이 활성화됨
- **포괄적인 타입 시스템** — CUBRID 전용 컬렉션과 JSON을 포함한 20개 이상의 타입
- **스키마 리플렉션** — 테이블, 뷰, 컬럼, PK, FK, 인덱스, 유니크 제약조건, 코멘트
- **DML 확장** — ON DUPLICATE KEY UPDATE, MERGE, GROUP_CONCAT, TRUNCATE
- **DDL 지원** — COMMENT, IF NOT EXISTS / IF EXISTS, AUTO_INCREMENT
- `CubridImpl`을 통한 **Alembic 마이그레이션 지원**, 방언이 로드될 때 등록됨
- **광범위한 오프라인 및 통합 테스트 스위트** — CI가 오프라인 스위트에 최소 95% 라인 커버리지 게이트를 강제합니다 (`--cov-fail-under=95`). 현재 테스트 수는 CI job 출력을 참고하세요
- **CI/CD** — Python 3.10–3.14 × CUBRID 10.2–11.4 매트릭스
- 방언을 다루는 `docs/`의 **영어 문서 파일 17개**

### 1.3 성공 기준 — 상태

| 기준 | 목표 | 달성 |
|---|---|---|
| Python 3.10+에 설치 가능 | ✅ | ✅ `pip install sqlalchemy-cubrid` |
| SQLAlchemy 2.0 – 2.1 호환 | ✅ | ✅ 완전한 API 준수 |
| 오프라인 테스트 (라이브 DB 없음) | ✅ | ✅ 광범위한 스위트, 커버리지 ≥ 95% CI 강제 |
| 모든 방언 메서드 구현 | ✅ | ✅ 리플렉션, 컴파일, 타입 |
| 버전 매트릭스를 갖춘 CI/CD | ✅ | ✅ Py 3.10–3.14 × CUBRID 10.2–11.4 |
| PyPI에 게시 가능 | ✅ | ✅ 태그 시 릴리스 워크플로 |
| Alembic 지원 | ✅ | ✅ CubridImpl 자동 등록 + autogenerate |
| ≥ 95% 코드 커버리지 | ✅ | ✅ `--cov-fail-under=95`로 CI 강제 |
| 포괄적인 문서 | ✅ | ✅ 영어 문서 파일 17개 + README |

---

## 2. 기술 아키텍처

### 2.1 모듈 구조

```mermaid
graph TD
    root["sqlalchemy_cubrid/ (Python 패키지 모듈 + py.typed 마커)"]
    init["__init__.py - 공개 API: 타입, insert(), merge(), replace(), trace_query(), __version__ 내보내기"]
    compat["_compat.py - SQLAlchemy 비공개 API 호환 헬퍼"]
    base["base.py - CubridExecutionContext, CubridIdentifierPreparer"]
    compiler["compiler.py - CubridSQLCompiler, CubridDDLCompiler, CubridTypeCompiler"]
    dialect["dialect.py - CubridDialect 리플렉션, 연결, 격리 수준"]
    pycubrid["pycubrid_dialect.py - PyCubridDialect 순수 Python 드라이버 변형"]
    aio["aio_pycubrid_dialect.py - PyCubridAsyncDialect 비동기 드라이버 변형"]
    dml["dml.py - ON DUPLICATE KEY UPDATE (Insert), MERGE 문"]
    trace["trace.py - 쿼리 추적 헬퍼"]
    types["types.py - CUBRID 타입 시스템: 숫자, 문자열, LOB, 컬렉션"]
    req["requirements.py - SA 2.0 테스트 요구사항 플래그"]
    alembic["alembic_impl.py - Alembic 마이그레이션용 CubridImpl"]
    typed["py.typed - PEP 561 마커"]

    root --> init
    root --> compat
    root --> base
    root --> compiler
    root --> dialect
    root --> pycubrid
    root --> aio
    root --> dml
    root --> trace
    root --> types
    root --> req
    root --> alembic
    root --> typed
```

### 2.2 의존성 매트릭스

| 패키지 | 버전 | 용도 |
|---|---|---|
| SQLAlchemy | ≥ 2.0, < 2.3 | 핵심 ORM/엔진 프레임워크 |
| Python | ≥ 3.10 | 런타임 |
| CUBRID-Python | any | DBAPI 드라이버 (선택적 extra) |
| Alembic | ≥ 1.7.2 | 마이그레이션 지원 (선택적 extra) |
| pytest | ≥ 7.0 | 테스트 (개발용) |
| ruff | ≥ 0.4 | 린트 + 포맷 (개발용) |

### 2.3 엔트리 포인트

```toml
[project.entry-points."sqlalchemy.dialects"]
cubrid = "sqlalchemy_cubrid.dialect:CubridDialect"
"cubrid.cubrid" = "sqlalchemy_cubrid.dialect:CubridDialect"
"cubrid.pycubrid" = "sqlalchemy_cubrid.pycubrid_dialect:PyCubridDialect"
"cubrid.aiopycubrid" = "sqlalchemy_cubrid.aio_pycubrid_dialect:PyCubridAsyncDialect"

```

---

## 3. 구현된 기능

### 3.1 타입 시스템 (`types.py` — 349줄)

#### 표준 SQL 타입

| SQLAlchemy 타입 | CUBRID SQL 타입 | 참고 |
|---|---|---|
| `Integer` | `INTEGER` | 32비트 부호 있는 정수 |
| `SmallInteger` | `SMALLINT` | 16비트 부호 있는 정수 |
| `BigInteger` | `BIGINT` | 64비트 부호 있는 정수 |
| `Float` | `FLOAT` | 7자리 정밀도 |
| `Double`, `REAL` | `DOUBLE` | 15자리 정밀도 |
| `Numeric(p, s)` | `NUMERIC(p, s)` | 정확한 숫자, 최대 38자리 |
| `String(n)` | `VARCHAR(n)` | 가변 길이 |
| `Text` | `STRING` | VARCHAR(1,073,741,823) |
| `Unicode(n)` | `VARCHAR(n)` | 데이터베이스 문자셋 |
| `UnicodeText` | `STRING` | `Text`와 동일 (CUBRID에는 `TEXT`가 없음) |
| `LargeBinary` | `BLOB` | Binary Large Object |
| `Boolean` | `SMALLINT` | 0/1로 에뮬레이트 |
| `Date` / `Time` / `DateTime` / `TIMESTAMP` | 네이티브 | 직접 매핑 |

#### CUBRID 전용 타입

| 타입 | 설명 |
|---|---|
| `STRING` | `VARCHAR(1,073,741,823)` — 최대 길이 가변 문자열 |
| `BIT(n)` / `BIT VARYING(n)` | 고정/가변 길이 비트 문자열 |
| `CLOB` | Character Large Object |
| `MONETARY` | 고정 소수점 통화 타입 |
| `OBJECT` | OID 참조 타입 |
| `SET(type)` | 고유한 요소의 순서 없는 컬렉션 |
| `MULTISET(type)` | 중복을 허용하는 순서 없는 컬렉션 |
| `SEQUENCE(type)` | 중복을 허용하는 순서 있는 컬렉션 |

### 3.2 SQL 컴파일러 (`compiler.py` — 507줄)

#### SQLCompiler

| 메서드 | 출력 |
|---|---|
| `visit_cast` | `CAST(expr AS type)` |
| `visit_sysdate_func` | `SYSDATE` |
| `visit_utc_timestamp_func` | `UTC_TIME()` |
| `visit_group_concat_func` | `GROUP_CONCAT(...)` |
| `render_literal_value` | 백슬래시 이스케이프 |
| `get_select_precolumns` | `DISTINCT` 처리 |
| `visit_join` | `INNER JOIN` / `LEFT OUTER JOIN` |
| `limit_clause` | `LIMIT offset, count` (MySQL 스타일) |
| `for_update_clause` | `FOR UPDATE [OF col, ...]` |
| `update_limit_clause` | UPDATE의 `LIMIT n` |

#### DDLCompiler

| 메서드 | 출력 |
|---|---|
| `get_column_specification` | `AUTO_INCREMENT`, `COMMENT`를 포함한 컬럼 DDL |
| `visit_set_table_comment` | `ALTER TABLE t COMMENT = 'text'` |
| `visit_drop_table_comment` | `ALTER TABLE t COMMENT = ''` |
| `visit_set_column_comment` | `ALTER TABLE t MODIFY col ... COMMENT 'text'` |

#### TypeCompiler

모든 CUBRID 타입이 DDL 문자열로 컴파일됩니다: `SMALLINT`, `INTEGER`, `BIGINT`, `NUMERIC(p,s)`,
`DECIMAL(p,s)`, `FLOAT(p)`, `REAL(p)`, `DOUBLE`, `DOUBLE PRECISION`, `CHAR(n)`, `VARCHAR(n)`,
`NCHAR(n)`, `NVARCHAR(n)`, `STRING`, `BIT(n)`, `BIT VARYING(n)`, `BLOB`, `CLOB`,
`SET(type)`, `MULTISET(type)`, `SEQUENCE(type)`, `MONETARY`, `OBJECT`, `BOOLEAN` → `SMALLINT`.

### 3.3 방언 (`dialect.py` — 605줄)

#### 방언 설정

```python
class CubridDialect(default.DefaultDialect):
    name = "cubrid"
    supports_statement_cache = True
    supports_native_boolean = False       # SMALLINT로 에뮬레이트
    supports_native_enum = True            # 네이티브 ENUM('a','b') DDL
    supports_native_decimal = True
    supports_sequences = False            # AUTO_INCREMENT 사용
    supports_default_values = True        # INSERT ... DEFAULT VALUES
    supports_empty_insert = True
    supports_multivalues_insert = True
    supports_comments = True              # 테이블 + 컬럼 코멘트
    supports_is_distinct_from = True      # NULL-안전 <=>로 에뮬레이트
    insert_returning = False              # RETURNING 절 없음
    update_returning = False
    delete_returning = False
    postfetch_lastrowid = True
    requires_name_normalize = False       # CUBRID가 이미 소문자로 폴딩
    max_identifier_length = 254
    default_paramstyle = "qmark"
```

> **비동기 방언**: `PyCubridAsyncDialect`는 `is_async = True`로 pycubrid 방언을 서브클래싱하고 `AsyncAdapt_pycubrid_dbapi`를 통해 `pycubrid.aio`를 감쌉니다. `create_async_engine("cubrid+aiopycubrid://...")`와 함께 사용할 수 있도록 `cubrid.aiopycubrid` 엔트리 포인트로 등록됩니다.

#### 리플렉션 메서드 (모두 구현됨)

| 메서드 | 소스 |
|---|---|
| `get_table_names()` | `db_class` (`class_type = 'CLASS'`, 시스템 테이블 제외) |
| `get_view_names()` | `db_class` (`class_type = 'VCLASS'`) |
| `get_view_definition()` | `SHOW CREATE VIEW` |
| `get_columns()` | `SHOW COLUMNS IN` + `db_attribute.comment` |
| `get_pk_constraint()` | `db_index` + `db_index_key` (PK 행을 찾지 못하면 `SHOW COLUMNS IN`으로 폴백) |
| `get_foreign_keys()` | `SHOW CREATE TABLE` 파싱 |
| `get_indexes()` | `SHOW INDEXES IN` + `db_index` 플래그 |
| `get_unique_constraints()` | `db_index` + `SHOW INDEXES IN` (`db_index`에 해당 테이블의 인덱스가 하나도 없거나, 11.2+에서 이름이 유니크 인덱스가 없는 다른 소유자의 클래스로 해석될 때에만 `SHOW CREATE TABLE` 파싱으로 폴백합니다. 유니크 인덱스가 있으면 `SHOW INDEXES IN`이 먼저 `NoSuchTableError`를 발생시킵니다) |
| `get_table_comment()` | `db_class.comment` |
| `get_check_constraints()` | `[]` 반환 (CUBRID는 CHECK를 무시) |
| `get_schema_names()` | `[]` 반환 (스키마 객체 없음) |
| `has_table()` | `db_class`에 대한 파라미터화된 쿼리 |
| `has_index()` | `db_index`에 대한 쿼리 |
| `has_sequence()` | 항상 `False` 반환 |

#### 연결과 격리

- **URL 변환**: `cubrid://user:pass@host:port/db` → `CUBRID:host:port:db:::`
- **3가지 MVCC 격리 수준** — `READ COMMITTED` (기본값), `REPEATABLE READ`, `SERIALIZABLE`
- **SQL 텍스트 기반 오토커밋 없음**: DML과 DDL은 SQLAlchemy 2.x Connection API(`commit()`, `begin()`, `Session`)를 통해서만 커밋됩니다
- **세이브포인트**: 지원됩니다. `RELEASE SAVEPOINT`는 no-op입니다

### 3.4 DML 확장 (`dml.py` — 267줄)

#### ON DUPLICATE KEY UPDATE

```python
from sqlalchemy_cubrid import insert

stmt = insert(users).values(id=1, name="alice")
stmt = stmt.on_duplicate_key_update(name="updated_alice")
# 또는 삽입된 값을 참조:
stmt = stmt.on_duplicate_key_update(name=stmt.inserted.name)
```

#### MERGE 문

```python
from sqlalchemy_cubrid.dml import merge

stmt = (
    merge(target)
    .using(source)
    .on(target.c.id == source.c.id)
    .when_matched_then_update({"name": source.c.name})
    .when_not_matched_then_insert({"id": source.c.id, "name": source.c.name})
)
```

### 3.5 Alembic 지원 (`alembic_impl.py` — 141줄)

- `transactional_ddl = True`를 갖는 `CubridImpl(DefaultImpl)` (CUBRID DDL은 트랜잭션으로 처리됨). CUBRID에는 `BEGIN` 문이 없으므로 `emit_begin()`은 no-op이며, 따라서 오프라인 스크립트는 `COMMIT;`만 냅니다
- 방언 모듈이 로드될 때 Alembic에 등록됨
- Autogenerate: 마이그레이션 스크립트에서 SET/MULTISET/SEQUENCE를 렌더링하기 위한 `render_type()`
- Autogenerate: 컬렉션 타입의 의미적 비교를 위한 `compare_type()`
- 네이티브 `alter_column`: 타입 변경(`MODIFY`), 이름 변경(`RENAME COLUMN`), 결합(`CHANGE`). `batch_alter_table`은 손실이 있는 변환에만 사용 (`alter_table_change_type_strict`)
---

## 4. 테스트 커버리지

### 4.1 테스트 매트릭스

오프라인 스위트는 `test/test_compiler.py`, `test_types.py`,
`test_requirements.py`, `test_dialect_offline.py`, `test_base.py`,
`test_alembic*.py`, `test_dialects.py`, `test_trace.py`와
리플렉션, 컬렉션, Alembic 플러그인 등록, 드라이버 계약, 저장소 도구를 다루는
그 밖의 많은 모듈에 걸쳐 있습니다. 파일별 및 전체 테스트 수는 거의 모든 PR마다
바뀌므로, 여기에 고정된 스냅숏을 두는 대신 `pytest test/ -m "not integration and
not repo" --collect-only`를 실행하거나 `offline-tests` CI job 출력에서
현재 수치를 확인하세요. CI는 최소 95% 라인 커버리지 게이트를
강제합니다 (`--cov-fail-under=95`).

### 4.2 도달 불가능한 라인

`compiler.py`와 `dml.py`의 몇몇 라인은 SQLAlchemy의 공개 API로는 발동될 수 없는
방어적 폴백입니다 (빈 `for_update_clause`/`limit_clause` 반환, DDL 타입 컴파일 폴백,
타입 정규화의 `else` 분기). 정확한 라인 번호는 모듈이 바뀜에 따라 달라지므로,
`pytest test/ -m "not integration and not repo" --cov=sqlalchemy_cubrid
--cov-report=term-missing`(또는 `make test`)을 실행하고 `Missing` 컬럼에서
현재 목록을 확인하세요.

### 4.3 CI 매트릭스

| 워크플로 | Python 버전 | CUBRID 버전 | 소스 |
|---|---|---|---|
| PR/push 오프라인 테스트 | PR: 3.12, push·주간·수동 실행: 3.11과 3.14 (전체 스위트, 95% 커버리지) | 해당 없음 (오프라인) | `.github/workflows/ci.yml` |
| PR/push 통합 테스트 | 축소 매트릭스: 3.14 (11.4와 함께), 3.11 (10.2와 함께) | 11.4, 10.2 — 2개 조합만, 교차 곱이 아님 | `.github/workflows/ci.yml` |
| 야간 / 릴리스 게이트 / 수동 전체 통합 매트릭스 | 3.10, 3.11, 3.12, 3.13, 3.14 | 10.2, 11.0, 11.2, 11.4 | `.github/workflows/integration-full.yml` |

---

## 5. 알려진 한계

(방언이 아니라) CUBRID 자체가 부과하는 한계:

| 기능 | 상태 | 이유 |
|---|---|---|
| `RETURNING` 절 | ❌ | CUBRID에는 `INSERT/UPDATE/DELETE ... RETURNING`이 없음 |
| 네이티브 `BOOLEAN` | ⚠️ | `SMALLINT`(0/1)로 에뮬레이트 |
| `JSON` 타입 | ✅ | 네이티브 JSON 타입/함수는 CUBRID 10.2+에서 지원되며 방언이 매핑함 |
| `ARRAY` 타입 | ❌ | `SET` / `MULTISET` / `SEQUENCE` 컬렉션을 사용 |
| 시퀀스 | ❌ | CUBRID는 `AUTO_INCREMENT`를 사용 |
| 다중 스키마 | ❌ | 단일 스키마 모델 |
| 임시 테이블 | ❌ | CUBRID에는 `CREATE TEMPORARY TABLE`이 없음 |
| `IS DISTINCT FROM` | ❌ | CUBRID SQL 연산자가 아님 |
| `RELEASE SAVEPOINT` | ❌ | 방언이 no-op으로 구현 |
| CHECK 제약조건 리플렉션 | ❌ | CUBRID는 CHECK를 파싱하지만 무시함 |
| 비동기 DBAPI 지원 | ✅ | pycubrid.aio 비동기 드라이버를 통해 (`cubrid+aiopycubrid://`) |
| 2단계 커밋 (XA) | ❌ | CUBRID에는 분산 트랜잭션 지원이 없음 |
| 서버 측 커서 | ❌ | CUBRID Python 드라이버의 한계 |
| Alembic ALTER COLUMN TYPE | ✅ | 네이티브 `MODIFY`. 손실이 있는 변환에는 `batch_alter_table` |
| Alembic RENAME COLUMN | ✅ | 네이티브 `RENAME COLUMN` (타입 변경과 결합되면 `CHANGE`) |
| FOR UPDATE NOWAIT / SKIP LOCKED | ❌ | CUBRID가 지원하지 않음 |

---

## 6. 문서

| 문서 | 줄 수 | 내용 |
|---|---|---|
| [`README.md`](../../README.md) | 80 | 간결한 랜딩 페이지 |
| [`docs/CONNECTION.md`](CONNECTION.md) | 258 | 연결 문자열, URL 형식, 드라이버 설정 |
| [`docs/TYPES.md`](TYPES.md) | 313 | 전체 타입 매핑, CUBRID 전용 타입 |
| [`docs/ISOLATION_LEVELS.md`](ISOLATION_LEVELS.md) | 206 | CUBRID의 세 가지 MVCC 격리 수준 |
| [`docs/DML_EXTENSIONS.md`](DML_EXTENSIONS.md) | 361 | ON DUPLICATE KEY UPDATE, MERGE, GROUP_CONCAT |
| [`docs/ALEMBIC.md`](ALEMBIC.md) | 376 | Alembic 마이그레이션 가이드, 한계 |
| [`docs/FEATURE_SUPPORT.md`](FEATURE_SUPPORT.md) | 442 | MySQL/PG/SQLite와의 기능 비교 |
| [`docs/DEVELOPMENT.md`](DEVELOPMENT.md) | 383 | 개발 환경 설정, 테스트, Docker, CI/CD |
| [`CHANGELOG.md`](../../CHANGELOG.md) | 119 | 릴리스 이력 (Keep a Changelog) |
| [`CONTRIBUTING.md`](../../CONTRIBUTING.md) | 225 | 기여 가이드라인 |

---

## 7. 릴리스 이력

| v0.1.0 | 2026-03-12 | 완전한 재작성 — SA 2.0, 모든 리플렉션, 컴파일러, 타입, CI/CD |
| v0.2.0 | 2026-03-12 | SQL 기능 확장 — FOR UPDATE, 윈도우 함수, MERGE, ODKU, COMMENT, DDL 확장 |
| v0.3.0 | 2026-03-12 | Alembic 지원, 엣지 케이스 테스트, 99% 커버리지 |
| v0.3.1 | 2026-03-12 | 정리 — 레거시 파일 제거, 샘플 현대화, 커뮤니티 파일 |
| v0.3.2 | 2026-03-12 | 문서 재구성 — 새 가이드 파일 6개, README 재작성 |
| v0.4.0 | 2026-03-12 | 드라이버 및 호환성 강화 — 오류 코드, do_ping, 커넥션 풀 튜닝 |
| v0.5.0 | 2026-03-12 | 쿼리 기능 확장 — REPLACE INTO, 재귀 CTE, ODKU 서브쿼리, trace |
| v0.6.0 | 2026-03-12 | 타입 시스템 확장, Alembic autogenerate, SA 2.1 대비, ORM 쿡북 |

---

## 8. 로드맵

### v0.4.0 — 드라이버 및 호환성 강화

**목표**: 실사용 편의성과 CUBRID 드라이버 호환성을 개선합니다.

| 항목 | 설명 | 우선순위 |
| 항목 | 설명 | 우선순위 | 상태 |
|---|---|---|---|
| CUBRID-Python 드라이버 감사 | 최신 CUBRID-Python 릴리스에 대해 테스트하고 버전 호환성 매트릭스를 문서화 | 높음 | ✅ 완료 |
| 커넥션 풀 튜닝 | CUBRID에서의 SA 커넥션 풀 동작(pool_size, pool_recycle, pool_pre_ping)을 테스트하고 문서화 | 높음 | ✅ 완료 |
| `postfetch_lastrowid` 검증 | CUBRID 버전 전반에서 `get_last_insert_id()` 동작을 확인하고, 일관되지 않으면 수정 | 높음 | ✅ 완료 |
| 오류 코드 매핑 | 올바른 예외 처리를 위해 CUBRID 오류 코드를 SA 예외(`IntegrityError`, `OperationalError` 등)로 매핑 | 중간 | ✅ 완료 |
| CUBRID 12.x 지원 | CUBRID 12가 릴리스되면 테스트하고 CI 매트릭스에 추가 | 중간 | ⏳ 차단됨 (미릴리스) |
| Python 3.14 지원 | 사용 가능해지면 Python 3.14를 CI 매트릭스에 추가 | 낮음 | ✅ 완료 |

### v0.5.0 — 쿼리 기능 확장

**목표**: CUBRID의 역량 안에서 SQL 기능 커버리지를 극대화합니다.

| 항목 | 설명 | 우선순위 | 상태 |
|---|---|---|---|
| `REPLACE` 문 | CUBRID는 `REPLACE INTO`를 지원 — 커스텀 DML construct로 추가 | 중간 | ✅ 완료 |
| 서브쿼리를 사용하는 `INSERT ... ON DUPLICATE KEY UPDATE` | ODKU 절에서 서브쿼리 값 지원 | 중간 | ✅ 완료 |
| Lateral 조인 | CUBRID의 lateral 조인 지원을 조사하고, 가능하면 활성화 | 낮음 | ❌ 미지원 |
| 재귀 CTE | CUBRID 11.x+에서 재귀 `WITH RECURSIVE` 지원 테스트 | 낮음 | ✅ 완료 |
| 전문 검색 | CUBRID에는 전문 인덱스가 있음 — 가능하다면 커스텀 construct로 노출 | 낮음 | ❌ 미지원 |
| `EXPLAIN` 출력 | 쿼리 계획 검사를 위한 `EXPLAIN` 접두사 지원 추가 | 낮음 | ✅ 완료 (trace_query) |

### v0.6.0 — SQLAlchemy 2.1+ 및 비동기

**목표**: 완전한 SQLAlchemy 2.1 정합과 현대적 비동기 지원.

| 항목 | 설명 | 우선순위 | 상태 |
|---|---|---|---|
| SQLAlchemy 2.1 호환성 | SA 2.1의 호환성을 깨는 변경을 추적하고 그에 맞춰 방언을 갱신 | 높음 | ⏳ SA 2.1 미릴리스 |
| SQLAlchemy 2.2+ 향후 버전 호환 | 향후 SA 릴리스에 대해 테스트하고 조정 | 높음 | ⏳ 미릴리스 |
| 비동기 DBAPI 지원 | CUBRID Python 드라이버가 비동기 지원을 추가하면 `create_async_engine` 호환성 구현 | 중간 | ✅ 완료 |
| 타입 어노테이션 개선 | `insert()`, `merge()` 반환 타입에 대한 완전한 `overload` 시그니처 추가 | 중간 | ✅ 완료 |
| `RETURNING` 에뮬레이션 | 단일 행 반환을 위한 TRIGGER 기반 또는 `LAST_INSERT_ID` 우회 방법 조사 | 낮음 | ⏳ 시작 전 |

### 장기 — 커뮤니티와 생태계

**목표**: 활발한 커뮤니티를 갖춘 지속 가능한 오픈소스 프로젝트.

| 항목 | 설명 | 우선순위 | 상태 |
|---|---|---|---|
| PyPI 게시 | 레지스트리에서 `pip install`할 수 있도록 PyPI에 게시 | 높음 | ✅ 완료 |
| 문서 사이트 | GitHub Pages 또는 Read the Docs로 문서 배포 | 중간 | ⏳ 시작 전 |
| Alembic autogenerate 튜닝 | CUBRID 전용 타입(SET, MULTISET, SEQUENCE)에 대한 autogenerate 개선 | 중간 | ✅ 완료 |
| SQLAlchemy 테스트 스위트 통과율 | SA의 표준 방언 테스트 스위트에 대한 통과율을 추적하고 높임 | 중간 | ⏳ 시작 전 |
| CUBRID ORM 쿡북 | 실용 예제: CUBRID에서의 관계, eager loading, 하이브리드 프로퍼티 | 낮음 | ✅ 완료 |
| 성능 벤치마크 | 일반적인 연산에서 원시 CUBRID-Python 대비 방언 오버헤드를 벤치마크 | 낮음 | ⏳ 시작 전 |
| 커뮤니티 기여자 | 이슈 템플릿, good-first-issue 레이블, 기여자 문서 | 낮음 | ✅ 완료 (이슈 템플릿) |

### 로드맵 우선순위

```mermaid
graph LR
    v130["v0.4.0"] --> v130a["드라이버 호환성 강화"]
    v130 --> v130b["오류 코드 매핑 + 커넥션 풀링"]

    v140["v0.5.0"] --> v140a["REPLACE 문"]
    v140 --> v140b["재귀 CTE, 전문 검색"]

    v200["v0.6.0"] --> v200a["SQLAlchemy 2.1+ 완전 호환"]
    v200 --> v200b["비동기 지원 (드라이버가 지원할 때)"]

    longterm["장기"] --> longa["PyPI, 문서 사이트, 커뮤니티 성장"]
    longterm --> longb["SA 테스트 스위트 통과율, 벤치마크"]
```

---

## 9. 아키텍처 결정

### 9.1 왜 단일 패키지인가 (별도 저장소가 아니라)

Alembic 지원, 타입, DML 확장은 모두 `sqlalchemy_cubrid/` 안에 있습니다 — 하나의 패키지입니다.
이는 모든 성숙한 SA 방언(MySQL, PostgreSQL, SQLite)의 패턴을 따릅니다.
저장소를 분리하면 이 정도 규모의 방언에는 아무 이점 없이 버전 관리 복잡성만 생깁니다.

### 9.2 왜 기본적으로 오프라인 테스트인가

CUBRID는 실행 중인 서버 인스턴스가 필요합니다. 대부분의 방언 로직(SQL 컴파일,
타입 매핑, 리플렉션 파싱)은 결정적이며 데이터베이스 없이 테스트할 수 있습니다.
오프라인 스위트(기본 `pytest test/ -m "not integration and not repo"` 선택)는 데이터베이스 없이 실행되어, 빠른 CI와 기여자 온보딩을 가능하게 합니다.

### 9.3 왜 95% 커버리지 임계값인가

SA 방언의 버그는 미묘합니다 — 잘못된 SQL 생성, 누락된 이스케이프, 깨진 리플렉션.
높은 커버리지는 회귀가 사용자에게 도달하기 전에 잡아냅니다. 커버되지 않은 라인이 있다면
도달 불가능한 방어적 폴백이어야 하며, 현재 수치는 커버리지 리포트에서 확인하세요.

### 9.4 Alembic의 네이티브 ALTER 컬럼 지원

CUBRID는 `ALTER TABLE ... MODIFY`, `CHANGE`, `RENAME COLUMN`(MySQL 호환 구문)을
네이티브로 지원하므로, 방언은 컬럼 타입 변경과 이름 변경에 대해 예외를 발생시키는 대신
네이티브 DDL을 냅니다. 타입 변환은 `alter_table_change_type_strict` 시스템 파라미터에
따라 결정됩니다. 손실이 있거나 호환되지 않는 변환의 경우, 데이터 마이그레이션을
완전히 제어해야 할 때 사용자는 여전히 Alembic의 `batch_alter_table`
테이블 재생성 전략으로 폴백할 수 있습니다.

---

*마지막 업데이트: 2026년 9월 · sqlalchemy-cubrid v1.8.0*

---

## 10. 예제 우선 설계 철학

### 왜 예제 우선인가

CUBRID의 생태계는 PostgreSQL이나 MySQL에 비해 작습니다. 생태계가 작은
프로젝트일수록 진입 장벽을 최소화해야 합니다 — 사용자는 문서를 읽은 지 30초 안에
동작하는 코드를 복사해 붙여넣을 수 있어야 합니다.

> 생태계가 아직 작기 때문에, 이 프로젝트는 도입 장벽을 낮추기 위해 풍부한 예제와
> 쿡북 스타일의 문서를 제공합니다.

### Hello World

```bash
pip install sqlalchemy-cubrid
```

```python
from sqlalchemy import create_engine, text

engine = create_engine("cubrid://dba:password@localhost:33000/demodb")

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.scalar())  # 1
```

이 코드는 SQLAlchemy를 통해 CUBRID 데이터베이스에 연결하고, 쿼리를 실행한 뒤
결과를 출력합니다. ORM 설정은 필요 없습니다 — 설치하고 연결하기만 하면 됩니다.

### Hello World — ORM

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

### AI 에이전트 발견 가능성

오늘날의 개발자는 Claude Code, OpenCode, Cursor, GitHub Copilot, Devin 등의
AI 코딩 어시스턴트에 점점 더 의존합니다. 이러한 에이전트는 README 파일, PRD,
문서, 예제 코드를 읽고 어떤 라이브러리를 추천할지 결정합니다.

**문서에 예제가 많을수록 = AI가 추천할 확률이 높아집니다.**

동작하는 코드를 PRD, README, 문서에 직접 포함함으로써, AI 에이전트가
sqlalchemy-cubrid를 정확하게 발견하고, 학습하고, 추천할 수 있도록 합니다.

### 쿡북 통합

[cubrid-cookbook](https://github.com/cubrid-lab/cubrid-cookbook-python) 저장소는
sqlalchemy-cubrid용 실행 가능한 예제를 제공합니다:

| 예제 | 설명 |
|---|---|
| `python/sqlalchemy/01_connect.py` | Core 엔진 연결 |
| `python/sqlalchemy/02_orm.py` | ORM 모델과 CRUD |
| `python/sqlalchemy/03_dml.py` | DML 확장 (ODKU, MERGE, REPLACE) |
| `python/sqlalchemy/04_relationships.py` | ORM 관계 |
| `python/sqlalchemy/05_reflection.py` | 스키마 리플렉션 |
| `python/sqlalchemy/06_alembic.py` | Alembic 마이그레이션 |

프레임워크 통합 예제:

| 예제 | 프레임워크 | 설명 |
|---|---|---|
| `python/fastapi/` | FastAPI | 자동 문서를 갖춘 REST API |
| `python/django/` | Django | SQLAlchemy 브리지를 통한 Django 프로젝트 |
| `python/flask/` | Flask | Flask + Flask-SQLAlchemy |
| `python/pandas/` | Pandas | 데이터 분석 파이프라인 |
| `python/streamlit/` | Streamlit | 인터랙티브 데이터 대시보드 |
| `python/celery/` | Celery | 비동기 작업 큐 |

### 성공한 프로젝트에서 얻은 영감

예제가 풍부한 문서 덕분에 성공한 측면이 있는 프로젝트들:

| 프로젝트 | 그들이 한 일 |
|---|---|
| **FastAPI** | 모든 엔드포인트를 실행 가능한 예제로 문서화. 가장 빠르게 성장하는 Python 웹 프레임워크가 됨 |
| **LangChain** | 쿡북 우선 접근이 AI 분야에서 폭발적인 도입을 이끎 |
| **SQLAlchemy** | 광범위한 ORM 쿡북과 튜토리얼. 15년 넘게 사실상의 표준 Python ORM |
| **Pandas** | "10 Minutes to pandas"와 쿡북이 데이터 과학의 진입 장벽을 낮춤 |

sqlalchemy-cubrid는 같은 철학을 따릅니다: **예제는 보조 자료가 아니라 주된 문서입니다.**
