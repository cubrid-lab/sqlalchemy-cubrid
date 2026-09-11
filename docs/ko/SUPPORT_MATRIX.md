# 지원 매트릭스 (한국어)

> 🌐 [SUPPORT_MATRIX.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/SUPPORT_MATRIX.md)의 번역입니다. 영어 원문이 표준이며, 페이지 번역은 경고 수준의 동기화 규칙을 따릅니다.

sqlalchemy-cubrid 릴리스의 호환성과 기능 지원.

---

## 버전 호환성

### SQLAlchemy

| SQLAlchemy 버전 | 상태 | 비고 |
|---|---|---|
| 2.0.x | ✅ 지원 | 최소 요구 버전 |
| 2.1.x | ✅ 지원 | GA까지 최신 테스트 프리릴리스 |
| ≥ 2.2 | ❌ 미지원 | 코드가 SA 비공개 내부를 사용 (아래 참고) |
| < 2.0 | ❌ 미지원 | SA 1.x API 제거됨 |

**왜 `<2.3`인가?** 방언이 예고 없이 변경될 수 있는 비공개 SQLAlchemy API에 접근합니다:

| 비공개 API | 위치 | 용도 |
|---|---|---|
| `select._limit_clause` | `compiler.py:104` | LIMIT 절 컴파일 |
| `select._offset_clause` | `compiler.py:105` | OFFSET 절 컴파일 |
| `select._for_update_arg` | `compiler.py:93` | FOR UPDATE 절 |

리터럴 감지와 typed-bind 재생성은 이제 로컬 `_compat.py` 헬퍼를 거치므로, 직접적인 비공개 API 서피스는 이 세 속성으로 줄었습니다.

### Python

| Python 버전 | 상태 |
|---|---|
| 3.10 | ✅ 지원 |
| 3.11 | ✅ 지원 |
| 3.12 | ✅ 지원 |
| 3.13 | ✅ 지원 |
| 3.14 | ✅ 지원 |
| < 3.10 | ❌ 미지원 |

### CUBRID 서버

| CUBRID 버전 | 상태 | 비고 |
|---|---|---|
| 11.4 | ✅ 지원 | 최신 안정 버전 |
| 11.2 | ✅ 지원 | |
| 11.0 | ✅ 지원 | |
| 10.2 | ✅ 지원 | 최소 테스트 버전 |
| < 10.2 | ❌ 미지원 | |

### 드라이버

| 드라이버 | 설치 | URL 스킴 | 상태 |
|---|---|---|---|
| CUBRID-Python (CCI) | `pip install "sqlalchemy-cubrid[cubrid]"` 또는 `[cubriddb]` | `cubrid://` / `cubrid+cubriddb://` | ✅ 지원 (레거시 C 확장) |
| pycubrid (순수 Python) | `pip install "sqlalchemy-cubrid[pycubrid]"` | `cubrid+pycubrid://` | ✅ 지원 |
| pycubrid 비동기 | `pip install "sqlalchemy-cubrid[pycubrid]"` | `cubrid+aiopycubrid://` | ✅ 지원 |

---

## 기능 지원

### SQLAlchemy Core

| 기능 | 상태 | 비고 |
|---|---|---|
| `create_engine()` | ✅ | `cubrid://`, `cubrid+cubrid://`, `cubrid+cubriddb://`, `cubrid+pycubrid://` 스킴 |
| 비동기 엔진 | ✅ | `create_async_engine("cubrid+aiopycubrid://...")` |
| SQL 컴파일 | ✅ | SELECT, INSERT, UPDATE, DELETE, JOIN, 서브쿼리 |
| DDL 컴파일 | ✅ | CREATE TABLE, ALTER, DROP, AUTO_INCREMENT, COMMENT |
| 타입 시스템 | ✅ | 출하된 모든 CUBRID 타입 컴파일. 리플렉션 커버리지는 아래에 별도 표기 |
| 스키마 리플렉션 | ✅ | 테이블, 컬럼, PK, FK, 인덱스, 유니크 제약, 코멘트 |
| 트랜잭션 관리 | ✅ | 커밋, 롤백, 세이브포인트 (RELEASE SAVEPOINT 없음) |
| 커넥션 풀링 | ✅ | `pool_pre_ping`, 연결 해제 감지를 갖춘 SA 풀 |
| 문장 캐싱 | ✅ | `supports_statement_cache = True` |

### SQLAlchemy ORM

| 기능 | 상태 | 비고 |
|---|---|---|
| 선언형 모델 | ✅ | |
| 릴레이션십 | ✅ | |
| Session / Unit of Work | ✅ | |
| Query API | ✅ | |
| 하이브리드 속성 | ✅ | |

### Alembic

| 기능 | 상태 | 비고 |
|---|---|---|
| 자동 발견 | ✅ | `alembic.ddl` 엔트리 포인트 |
| 스키마 마이그레이션 | ✅ | CREATE, ALTER, DROP |
| Autogenerate | ✅ | 컬렉션 타입(SET, MULTISET, SEQUENCE) 포함 |
| 트랜잭션 DDL | ❌ | CUBRID는 DDL을 자동 커밋 |

### DML 확장

| 기능 | 상태 | 비고 |
|---|---|---|
| `ON DUPLICATE KEY UPDATE` | ✅ | `sqlalchemy_cubrid.insert()`를 통해 |
| `MERGE` 문 | ✅ | `sqlalchemy_cubrid.merge()`를 통해 |
| `REPLACE INTO` | ✅ | `sqlalchemy_cubrid.replace()`를 통해 |
| `GROUP_CONCAT` | ✅ | |
| `TRUNCATE TABLE` | ✅ | 오토커밋 감지 |
| `FOR UPDATE` | ✅ | `OF` 절 포함 |
| 재귀 CTE | ✅ | `WITH RECURSIVE` (CUBRID 11.x+) |
| 윈도우 함수 | ✅ | ROW_NUMBER, RANK, LAG, LEAD 등 |
| 인덱스 힌트 | ✅ | SA `with_hint()` / `suffix_with()`를 통해 |

### 알려진 한계

| 기능 | 상태 | 비고 |
|---|---|---|
| JSON 타입 | ✅ | v1.2.0부터, CUBRID ≥ 10.2 필요 |
| 네이티브 Enum | ❌ | CUBRID에 ENUM 없음 — VARCHAR + CHECK 제약 사용 |
| Interval 타입 | ❌ | CUBRID 미지원 |
| RETURNING 절 | ❌ | `INSERT/UPDATE/DELETE ... RETURNING` 미지원 |
| BOOLEAN | ⚠️ | SMALLINT(0/1)로 매핑 — 네이티브 불리언 없음 |
| 시퀀스 | ❌ | CUBRID는 AUTO_INCREMENT만 사용 |
| CHECK 제약 리플렉션 | ❌ | `get_check_constraints()`가 빈 리스트 반환 |
| 멀티 스키마 | ❌ | CUBRID는 단일 스키마 모델 |
| RELEASE SAVEPOINT | ❌ | no-op (CUBRID 미지원) |
| Lateral 조인 | ❌ | CUBRID에 LATERAL 서브쿼리 지원 없음 |
| 전문 검색 | ❌ | MATCH … AGAINST 구문 없음 |
| 비동기 DBAPI | ✅ | pycubrid.aio 비동기 드라이버 경유(`cubrid+aiopycubrid://`), pycubrid >= 1.2.0,<2.0 필요 |

---

## 타입 매핑

선언/컴파일 타입과 리플렉트 타입은 동일하지 않습니다. `REAL`, `MONETARY`, `OBJECT`는 올바르게 컴파일되고 모델에 선언할 수 있지만 `dialect.ischema_names`에 없어서 리플렉션이 자동으로 매핑하지 않습니다.

| CUBRID 타입 | SQLAlchemy 타입 | Python 타입 | 리플렉션 |
|---|---|---|---|
| INTEGER | `sa.Integer` | `int` | ✅ |
| BIGINT | `sa.BigInteger` | `int` | ✅ |
| SMALLINT | `sa.SmallInteger` | `int` | ✅ |
| FLOAT | `sa.Float` | `float` | ✅ |
| REAL | `REAL` | `float` | ❌ 선언/컴파일 전용 |
| DOUBLE | `sa.Float` | `float` | ✅ |
| NUMERIC / DECIMAL | `sa.Numeric` | `decimal.Decimal` | ✅ |
| MONETARY | `MONETARY` | `float` | ❌ 선언/컴파일 전용 |
| CHAR | `sa.CHAR` | `str` | ✅ |
| VARCHAR | `sa.String` | `str` | ✅ |
| NCHAR | `NCHAR` | `str` | ✅ |
| NVARCHAR | `NVARCHAR` | `str` | ✅ |
| STRING | `STRING` | `str` | ✅ |
| DATE | `sa.Date` | `datetime.date` | ✅ |
| TIME | `sa.Time` | `datetime.time` | ✅ |
| DATETIME | `sa.DateTime` | `datetime.datetime` | ✅ |
| TIMESTAMP | `sa.TIMESTAMP` | `datetime.datetime` | ✅ |
| BIT | `BIT` | `bytes` | ✅ |
| BLOB | `sa.LargeBinary` | `bytes` | ✅ |
| CLOB | `CLOB` | `str` | ✅ |
| SET | `SET` | 컬렉션 | ✅ |
| MULTISET | `MULTISET` | 컬렉션 | ✅ |
| SEQUENCE | `SEQUENCE` | 컬렉션 | ✅ |
| OBJECT | `OBJECT` | OID 참조 | ❌ 선언/컴파일 전용 |

---

## CI 매트릭스

| 차원 | PR / push | 나이틀리 + 태그 + dispatch |
|---|---|---|
| 오프라인 테스트 | Python 3.10, 3.11, 3.12, 3.13, 3.14 | 동일 |
| 통합 테스트 | Python {3.10, 3.14} × CUBRID {10.2, 11.0, 11.2, 11.4} = 8잡 | Python {3.10, 3.11, 3.12, 3.13, 3.14} × CUBRID {10.2, 11.0, 11.2, 11.4} = 20잡 |

5 × 4 전체 통합 매트릭스는 `.github/workflows/integration-full.yml`이 나이틀리 일정, 태그 릴리스, `workflow_dispatch` 요청 시 실행합니다.

## 테스트 커버리지

| 지표 | 값 |
|---|---|
| 오프라인 테스트 | 619 |
| 통합 테스트 | 동기 35 + 비동기 16 |
| 라인 커버리지 | 오프라인 ~98.26% |
| 커버리지 하한 | 95% (CI 강제) |

---

*참고: [연결 가이드](CONNECTION.md) · [타입 시스템](TYPES.md) · [기능 지원](FEATURE_SUPPORT.md) · [드라이버 호환성](DRIVER_COMPAT.md) · [변경 이력](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/CHANGELOG.md)*
