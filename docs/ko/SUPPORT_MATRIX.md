# 지원 매트릭스 (한국어)

> 🌐 [SUPPORT_MATRIX.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/SUPPORT_MATRIX.md)의 번역입니다. 영어 원문이 표준이며, CI가 영어 원문과의 구조 일치를 검사합니다.

sqlalchemy-cubrid 릴리스의 호환성과 기능 지원.

---

## 버전 호환성

### SQLAlchemy

| SQLAlchemy 버전 | 상태 | 비고 |
|---|---|---|
| 2.0.x | ✅ 지원 | 최소 요구 버전 |
| 2.1.x | ✅ 지원 | GA 정식 릴리스이며 CI에서 2.1.1 테스트됨 |
| ≥ 2.2 | ❌ 미지원 | 2.2가 출시되어 전체 매트릭스를 통과할 때까지 `<2.2` 상한으로 제외됨; 코드가 SA 비공개 내부를 사용 (아래 참고) |
| < 2.0 | ❌ 미지원 | SA 1.x API 제거됨 |

**왜 `<2.2`인가?** 방언이 예고 없이 변경될 수 있는 비공개 SQLAlchemy API에 접근합니다:

| 비공개 API | 위치 | 용도 |
|---|---|---|
| `select._limit_clause` | `compiler.py:104` | LIMIT 절 컴파일 |
| `select._offset_clause` | `compiler.py:105` | OFFSET 절 컴파일 |
| `select._for_update_arg` | `compiler.py:93` | FOR UPDATE 절 |

리터럴 감지와 typed-bind 재생성은 이제 로컬 `_compat.py` 헬퍼를 거치므로, 직접적인 비공개 API 서피스는 이 세 속성으로 줄었습니다.

### Python

| Python 버전 | 상태 |
|---|---|
| 3.11 | ✅ 지원 |
| 3.12 | ✅ 지원 |
| 3.13 | ✅ 지원 |
| 3.14 | ✅ 지원 |
| 3.15 | ✅ 지원 (표준 GIL 빌드, 아래 참고 사항 참고) |
| 3.10 | ❌ 1.10.0부터 미지원 (1.9.x까지 지원) |
| < 3.10 | ❌ 미지원 |

**Python 3.10 지원 종료:** Python 3.10은 2026-10-01에 공식 지원이
종료됐습니다([PEP 619](https://peps.python.org/pep-0619/#310-lifespan)).
1.8.x와 1.9.x는 Python 3.10을 지원하며, 1.9.0에 사전 안내가 포함됐습니다.
1.10.0부터 패키지는 Python 3.11 이상을 요구하므로(`requires-python =
">=3.11"`), Python 3.10의 `pip`은 계속 1.9.x를 설치합니다. 수정은 최신 릴리스
라인에만 제공되므로 1.9.x의 추가 릴리스는 없습니다. 업그레이드하기 전에
Python을 업그레이드하고 가상 환경을 새로 만든 뒤 애플리케이션을 검증하세요.

**Python 3.15:** 표준 GIL을 쓰는 CPython
[3.15.0](https://www.python.org/downloads/release/python-3150/) 정식 릴리스를
지원합니다. free-threaded 빌드는 지원하지 않습니다. 전체 호환성 매트릭스는 수동
실행과 모든 릴리스에서 Python 3.15를 지원되는 모든 CUBRID 버전과 함께 실행하며,
3.15는 최신 오프라인 엔드포인트입니다. 수동 `python-canary.yml` 레인은 계속 3.15에서
wheel/sdist의 새 환경 설치를 확인합니다. 지원 범위:

- **pycubrid (`cubrid+pycubrid://`, `cubrid+aiopycubrid://`):** pycubrid는 1.10.0
  다음 릴리스부터 Python 3.15를 선언합니다
  ([cubrid-lab/pycubrid#831](https://github.com/cubrid-lab/pycubrid/pull/831)).
  `[pycubrid]` 하한은 `pycubrid>=1.8.0,<2.0` 그대로입니다. pycubrid 1.10.0은 3.15에서
  동기·비동기 통합 스위트를 통과하지만 3.15를 선언하지 않습니다. Python 3.15는
  `ksc5601` 코덱 별칭을 CP949로 매핑하므로, 3.15에서 pycubrid 1.10.0 이하는
  `?charset=ksc5601`을 거부합니다. `?charset=euckr`을 쓰거나, `ksc5601`을 직접
  EUC-KR로 매핑하는 3.15 선언 pycubrid 릴리스를 쓰세요.
- **CUBRIDdb (`cubrid://`):** 공식 `cubrid-python` v11.3.0.51 소스는 `ubuntu-latest`의
  CI 빌드 절차로 3.15용으로 빌드되며, 전체 매트릭스는 3.15에서 해당 레인을 실행합니다.
  GCC 14에서는 Python 3.14와 3.15 모두에서 기본 빌드가 실패합니다(비교한 두 버전이며 3.11–3.13은 시험하지 않음). GCC 14가
  `-Wincompatible-pointer-types`와 `-Wint-conversion`을 오류로 만들기 때문입니다.
  이 프로젝트는 CI에 경고 완화 플래그를 추가하지 않습니다. [드라이버 호환성](DRIVER_COMPAT.md)을
  참고하세요.
- **3.15에서 실행하지 않는 검사:** SQLAlchemy 컴플라이언스 레인은 Python 3.14/CUBRID
  11.4와 Python 3.11/CUBRID 10.2에 그대로 둡니다.
- **가비지 컬렉션된 연결:** SQLAlchemy 2.1에서는 참조 순환 안에서 잃어버린 풀 연결(트랜잭션이
  아직 열린 연결 등)이 3.15에서 종료되지도 풀로 반환되지도 않습니다. 이는 모든 방언에 영향을
  주는 SQLAlchemy 2.1/CPython 3.15 상호작용이며, 해당 통합 테스트는 그 환경에서 예상된
  실패(xfail)로 처리됩니다. [연결 가이드](CONNECTION.md#비동기-연결)를 참고하세요.
- **환경:** pycubrid를 통한 Decimal 하위 클래스 파라미터에는 C `_decimal` 모듈이
  필요합니다. `libmpdec` 없이 빌드한 Python에는 이 모듈이 없으며, 이때 pycubrid는
  이런 파라미터에 `ProgrammingError`를 발생시킵니다. 일반 `Decimal` 값은 영향이 없습니다.
  CI가 쓰는 `actions/setup-python` 3.15.0 빌드, `python:3.15-rc` Docker 이미지,
  `libmpdec-dev` 없는 소스 빌드에서 이 모듈이 없음을 확인했으므로, CI의 3.15 셀에서는
  Decimal 하위 클래스 왕복 테스트를 건너뜁니다. 3.15를 지원 목록에
  올린 시점에 Docker Hub에는 정식 `python:3.15` 이미지가 없었으며, CI는
  `actions/setup-python`을 사용합니다.

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
| CUBRIDdb (CCI) | cubrid-python v11.3.0.51+에서 빌드 ([방법](DRIVER_COMPAT.md#소스에서-cubriddb-빌드)). `[cubrid]` / `[cubriddb]` extra는 폐기 예정이며 테스트되지 않은 PyPI 9.3.x를 설치 | `cubrid://` / `cubrid+cubriddb://` | ✅ 지원되는 C 확장 드라이버 (v11.3.0.51+만) |
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
| `executemany` (`text()`, UPDATE, DELETE) | ✅ | 모든 드라이버에서 `None`은 NULL로 바인딩되고 `rowcount`는 모든 파라미터 세트의 합계입니다(`supports_sane_multi_rowcount = True`). `cubrid://`에서는 CUBRIDdb 버그를 피하기 위해 방언이 각 파라미터 세트를 별도의 `execute()`로 실행합니다. 이 때문에 행마다 문장 준비가 한 번 더 필요하며, 1000행 UPDATE 기준 드라이버 자체 `executemany`보다 약 2.9배 느립니다. pycubrid는 한 번만 준비하는 `executemany`를 그대로 사용합니다. insertmanyvalues를 사용하는 여러 행의 Core `insert()`는 영향이 없습니다. 타입이 `bind_expression()`을 정의하는 컬럼이 있는 테이블에 대한 INSERT는 executemany로 대체되므로(#421) `cubrid://`에서 행 단위 가드를 사용합니다. [드라이버 호환성, 알려진 문제 7](DRIVER_COMPAT.md#알려진-문제) 참고 |

### SQLAlchemy ORM

| 기능 | 상태 | 비고 |
|---|---|---|
| 선언형 모델 | ✅ | |
| 릴레이션십 | ✅ | |
| Session / Unit of Work | ✅ | |
| 일괄 UPDATE / DELETE 행 수 검사 | ✅ | 모든 드라이버에서 일괄 flush가 일치한 행 수를 검사합니다. `cubrid://`에서는 행 단위 `executemany` 가드에 의존합니다. [드라이버 호환성, 알려진 문제 7](DRIVER_COMPAT.md#알려진-문제) 참고 |
| Query API | ✅ | |
| 하이브리드 속성 | ✅ | |

### Alembic

| 기능 | 상태 | 비고 |
|---|---|---|
| 자동 등록 | ✅ | 방언 로드 시 등록 (`env.py` 임포트 불필요) |
| 스키마 마이그레이션 | ✅ | CREATE, ALTER, DROP |
| Autogenerate | ✅ | 컬렉션 타입(SET, MULTISET, SEQUENCE) 포함. CUBRID 전용 멤버 타입은 `cubrid_types.MONETARY()`, `cubrid_types.BIT(...)` 등으로 렌더링됩니다 |
| 트랜잭션 DDL | ✅ | DDL은 트랜잭션과 함께 롤백됨. 기본적으로 업그레이드 전체가 원자적 (리비전별 커밋은 `transaction_per_migration=True`) |

### DML 확장

| 기능 | 상태 | 비고 |
|---|---|---|
| `ON DUPLICATE KEY UPDATE` | ✅ | `sqlalchemy_cubrid.insert()`를 통해 |
| `MERGE` 문 | ✅ | `sqlalchemy_cubrid.merge()`를 통해 |
| `REPLACE INTO` | ✅ | `sqlalchemy_cubrid.replace()`를 통해 |
| `GROUP_CONCAT` | ✅ | |
| `TRUNCATE TABLE` | ✅ | 둘러싼 트랜잭션과 함께 커밋 |
| `FOR UPDATE` | ✅ | `OF` 절 포함 |
| 재귀 CTE | ✅ | `WITH RECURSIVE` (CUBRID 10.2, 11.0, 11.2, 11.4에서 확인) |
| 윈도우 함수 | ✅ | ROW_NUMBER, RANK, LAG, LEAD 등 |
| 인덱스 힌트 | ✅ | SA `with_hint()` / `suffix_with()`를 통해 |

### 알려진 한계

| 기능 | 상태 | 비고 |
|---|---|---|
| JSON 타입 | ✅ | v1.2.0부터, CUBRID ≥ 10.2 필요 |
| 네이티브 Enum | ✅ | 네이티브 `ENUM('a', 'b', ...)` — 10.2–11.4에서 검증 (#343) |
| Interval 타입 | ❌ | CUBRID 미지원 |
| RETURNING 절 | ❌ | `INSERT/UPDATE/DELETE ... RETURNING` 미지원 |
| BOOLEAN | ⚠️ | SMALLINT(0/1)로 매핑 — 네이티브 불리언 없음. CUBRID의 `IS`는 `NULL`/`TRUE`/`FALSE`만 받으므로 `col.is_(True)` / `is_not(False)` 등은 null-safe `<=>`로 에뮬레이트합니다(`col <=> 1`, `(col <=> 1) = 0`) (#465). `IS [NOT] NULL`, `col == True`, `not_(col)`은 그대로 컴파일됩니다. CUBRID는 SELECT 목록의 `AND`/`OR`/`NOT`을 거부하므로 `WHERE`에서 사용하거나 `case()`로 감싸세요. [불리언 조건식](TYPES.md#불리언-조건식) 참고 |
| 시퀀스 | ❌ | CUBRID는 AUTO_INCREMENT만 사용 |
| CHECK 제약 리플렉션 | ❌ | `get_check_constraints()`가 빈 리스트 반환 |
| 멀티 스키마 | ❌ | CUBRID는 단일 스키마 모델 |
| RELEASE SAVEPOINT | ❌ | no-op (CUBRID 미지원) |
| Lateral 조인 | ❌ | CUBRID에 LATERAL 서브쿼리 지원 없음 |
| 전문 검색 | ❌ | MATCH … AGAINST 구문 없음 |
| 비동기 DBAPI | ✅ | pycubrid.aio 비동기 드라이버 경유(`cubrid+aiopycubrid://`), pycubrid >= 1.8.0,<2.0 필요 |

---

## 타입 매핑

선언/컴파일 타입과 리플렉트 타입은 동일하지 않습니다. `REAL`, `MONETARY`, `OBJECT`는 올바르게 컴파일되고 모델에 선언할 수 있지만 `dialect.ischema_names`에 없어서 리플렉션이 자동으로 매핑하지 않습니다.
리플렉션 열은 스키마 메타데이터 매핑을, Python 타입 열은 의도한 값 형태를 설명합니다. 어느 열도 모든 드라이버가 그 값을 변형 없이 바인딩하고 반환한다는 보장은 아닙니다. BLOB/CLOB 로케이터, 빈 BIT 값, CUBRIDdb DECIMAL 절삭, 컬렉션 바인딩 차이는 [타입 매핑](TYPES.md)과 [드라이버 호환성](DRIVER_COMPAT.md)을 참고하세요.

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
| TIMESTAMPTZ | `TIMESTAMPTZ` (`timezone=True`) | `datetime.datetime` | ✅ `TIMESTAMP`로 합쳐지지 않는 별도 리플렉트 타입 |
| TIMESTAMPLTZ | `TIMESTAMPLTZ` (`timezone=True`) | `datetime.datetime` | ✅ `TIMESTAMP`로 합쳐지지 않는 별도 리플렉트 타입 |
| DATETIMETZ | `DATETIMETZ` (`timezone=True`) | `datetime.datetime` | ✅ `DATETIME`으로 합쳐지지 않는 별도 리플렉트 타입 |
| DATETIMELTZ | `DATETIMELTZ` (`timezone=True`) | `datetime.datetime` | ✅ `DATETIME`으로 합쳐지지 않는 별도 리플렉트 타입 |
| BIT(n) / BIT VARYING(n) | `BIT(n)` / `BIT(n, varying=True)` | `bytes` | ✅ 길이와 `VARYING` 유지 |
| BIT(n\*8) | `sa.BINARY(n)` (`BINARY()` → `BIT(8)`) | `bytes` | ✅ `BIT(n*8)`로 리플렉트 |
| BIT VARYING(n\*8) | `sa.VARBINARY(n)` (`VARBINARY()` → `BIT VARYING`) | `bytes` | ✅ `BIT VARYING(n*8)`로 리플렉트 |
| CHAR(32) | `sa.Uuid` / `sa.UUID` | `uuid.UUID`, `as_uuid=False`이면 `str` | ✅ `CHAR(32)`로 리플렉트 |
| BLOB | `sa.LargeBinary` | `bytes` (문서상). NULL이 아닌 값 조회는 현재 드라이버 LOB 로케이터를 반환합니다. [드라이버 호환성, 알려진 문제 6](DRIVER_COMPAT.md#알려진-문제) 참고 | ✅ |
| CLOB | `CLOB` | `str` (문서상). NULL이 아닌 값 조회는 현재 드라이버 LOB 로케이터를 반환합니다. [드라이버 호환성, 알려진 문제 6](DRIVER_COMPAT.md#알려진-문제) 참고 | ✅ |
| SET | `SET` | 컬렉션 | ✅ |
| MULTISET | `MULTISET` | 컬렉션 | ✅ |
| SEQUENCE | `SEQUENCE` | 컬렉션 | ✅ |
| OBJECT | `OBJECT` | OID 참조 | ❌ 선언/컴파일 전용 |

CUBRID에는 `BINARY`, `VARBINARY`, `UUID` 타입이 없습니다. `sa.BINARY(n)` / `sa.VARBINARY(n)`은 비트 단위 길이의 비트 문자열(`BIT(n*8)` / `BIT VARYING(n*8)`)로 컴파일되며, `BINARY`는 더 짧은 값을 `\x00`으로 채웁니다. 빈 `b""`는 보존되지 않고 `None`(pycubrid의 `BINARY(n)`은 0 바이트)으로 조회됩니다. `sa.Uuid`와 `sa.UUID`는 `CHAR(32)`에 32자 16진 문자열로 저장됩니다. 리플렉트된 BIT 컬럼은 길이를 유지하므로 Alembic autogenerate가 이 컬럼들에 대해 잘못된 타입 변경을 보고하지 않습니다. [표준 SQL 타입](TYPES.md#표준-sql-타입) 참고.

---

## CI 매트릭스

| 검증 | 일상 실행 | 전체 호환성 |
| --- | --- | --- |
| 오프라인 | 95% 커버리지의 전체 스위트: PR은 Ubuntu/Python 3.12, main·변경이 있는 주간 실행·수동 실행은 Python 3.11과 3.15 | 로컬 전체 테스트는 그대로 사용 가능 |
| 라이브 통합 | 고위험 PR은 Python 3.14/CUBRID 11.4. main/변경이 있는 주간 실행은 Python 3.11/CUBRID 10.2도 실행 | 수동 실행과 모든 릴리스에서 Python 3.11–3.15 × CUBRID 10.2/11.0/11.2/11.4 |

[CI 실행 정책](CI_POLICY.md)을 참고하세요. 이 정책은 각 실행이 무엇을 테스트할지를
고를 뿐, 위에 나열한 지원 버전을 정의하지 않습니다. 대표 PR 검사는 지원되는 모든
조합에 대한 증거가 아닙니다.

### SQLAlchemy 컴플라이언스 레인

공식 SQLAlchemy 컴플라이언스 스위트는 두 드라이버 모두에서 병합을 차단합니다. 각 레인은 `test/known_failures.txt`에 검토된 자체 알려진 실패 기준선을 가집니다. [개발 가이드](DEVELOPMENT.md#sqlalchemy-컴플라이언스-레인)를 참고하세요.

| 레인 | 드라이버 | SQLAlchemy | CUBRID (PR CI) | 알려진 실패 (11.4 / 10.2) |
|---|---|---|---|---|
| `cubrid@sa2.0` | CUBRIDdb (cubrid-python v11.3.0.51) | 2.0.53 | 11.4 | 68 / 61 |
| `pycubrid@sa2.0` | pycubrid 1.8.0 (선언된 하한) | 2.0.53 | 10.2 | 54 (10.2에서만 게이트) |
| `pycubrid@sa2.1` | pycubrid 1.8.0 (선언된 하한) | 2.1.1 | 11.4 | 58 / 51 |

권장 드라이버는 pycubrid입니다. 컴플라이언스 레인은 사용자가 설치할 수 있는 가장 오래된 릴리스를 검증하도록 `pycubrid>=1.8.0,<2.0`의 선언된 하한을 일부러 고정합니다. 통합 레인은 최신 pycubrid 릴리스를 설치하며, 1.8.0 이후 바뀐 동작은 별도의 회귀 테스트가 있고 1.8.0에서는 strict xfail입니다(#479).

알려진 실패 대부분은 두 드라이버에 공통입니다. CUBRID 백엔드 규칙(식별자 소문자 변환, `[ ]` 식별자 구분자, 윈도 프레임 절 미지원, 행 단위 외래 키 검사, 단정밀도 `FLOAT`)과 `test/known_failures.txt`에 기록된 미해결 방언 리플렉션/DDL 버그입니다. NUMERIC 절단과 정수 나눗셈 항목은 CUBRIDdb 레인에만 있습니다.

## 테스트 커버리지

오프라인 및 통합 테스트 개수는 PR마다 늘어나므로, 여기에 고정된 스냅샷 대신
`offline-tests` / `integration-tests` CI 작업 출력에서 현재 수치를 확인하세요.

| 지표 | 값 |
|---|---|
| 커버리지 하한 | 95% (CI 강제, `offline-tests` 작업의 `--cov-fail-under=95`) |

---

*참고: [연결 가이드](CONNECTION.md) · [타입 시스템](TYPES.md) · [기능 지원](FEATURE_SUPPORT.md) · [드라이버 호환성](DRIVER_COMPAT.md) · [변경 이력](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/CHANGELOG.md)*
