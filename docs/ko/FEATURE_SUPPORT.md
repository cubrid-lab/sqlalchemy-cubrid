# 기능 지원 비교 (한국어)

> 🌐 [FEATURE_SUPPORT.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/FEATURE_SUPPORT.md)의 번역입니다. 영어 원문이 표준이며, 페이지 번역은 경고 수준의 동기화 규칙을 따릅니다.

**sqlalchemy-cubrid**의 역량을 MySQL, PostgreSQL, SQLite의 성숙한 SQLAlchemy 방언과 종합 비교합니다.

이 문서를 사용해 CUBRID 방언이 무엇을 지원하고 지원하지 않는지, 프로젝트의 방언 선택 시 다른 데이터베이스 백엔드와 어떻게 비교되는지 이해하세요.

---

## 목차

- [범례](#범례)
- [요약](#요약)
- [DML — 데이터 조작 언어](#dml--데이터-조작-언어)
- [DDL — 데이터 정의 언어](#ddl--데이터-정의-언어)
- [쿼리 기능](#쿼리-기능)
- [타입 시스템](#타입-시스템)
- [스키마 리플렉션](#스키마-리플렉션)
- [트랜잭션과 연결](#트랜잭션과-연결)
- [방언 엔진 기능](#방언-엔진-기능)
- [CUBRID 전용 기능](#cubrid-전용-기능)
- [CUBRID 전용 DML 구성](#cubrid-전용-dml-구성)
- [인덱스 힌트](#인덱스-힌트)
- [알려진 한계와 로드맵](#알려진-한계와-로드맵)

---

## 범례

| 기호 | 의미 |
|--------|---------|
| ✅ | 완전 지원 |
| ⚠️ | 부분 또는 에뮬레이트 지원 |
| ❌ | 미지원 |

---

## 요약

기능 범주별 상위 개요.

| 범주 | CUBRID | MySQL | PostgreSQL | SQLite |
|----------|--------|-------|------------|--------|
| DML | ✅ | ✅ | ✅ | ⚠️ |
| DDL | ✅ | ✅ | ✅ | ⚠️ |
| 쿼리 기능 | ✅ | ✅ | ✅ | ✅ |
| 타입 시스템 | ⚠️ | ✅ | ✅ | ⚠️ |
| 스키마 리플렉션 | ✅ | ✅ | ✅ | ⚠️ |
| 트랜잭션 | ✅ | ✅ | ✅ | ⚠️ |
| 엔진 기능 | ⚠️ | ✅ | ✅ | ⚠️ |

---

## DML — 데이터 조작 언어

| 기능 | CUBRID | MySQL | PostgreSQL | SQLite |
|---------|--------|-------|------------|--------|
| INSERT … RETURNING | ❌ | ❌ | ✅ | ✅ |
| UPDATE … RETURNING | ❌ | ❌ | ✅ | ✅ |
| DELETE … RETURNING | ❌ | ❌ | ✅ | ✅ |
| INSERT … DEFAULT VALUES | ✅ | ❌ | ✅ | ✅ |
| 빈 INSERT | ✅ | ⚠️ | ✅ | ✅ |
| 다중 행 INSERT | ✅ | ✅ | ✅ | ✅ |
| INSERT FROM SELECT | ✅ | ✅ | ✅ | ✅ |
| ON DUPLICATE KEY UPDATE | ✅ | ✅ | ❌ | ❌ |
| MERGE 문 | ✅ | ❌ | ❌ | ❌ |
| REPLACE INTO | ✅ | ✅ | ❌ | ✅ |
| FOR UPDATE (행 잠금) | ✅ | ✅ | ✅ | ❌ |
| LIMIT를 가진 UPDATE | ✅ | ✅ | ❌ | ❌ |
| TRUNCATE TABLE | ✅ | ✅ | ✅ | ❌ |
| IS DISTINCT FROM | ❌ | ❌ | ✅ | ❌ |
| Postfetch LASTROWID | ✅ | ✅ | ❌ | ✅ |

### 참고

- **RETURNING**: CUBRID에는 `RETURNING` 절이 없습니다. 자동 생성 키를 INSERT와 같은 왕복에서 가져올 수 없어, 방언은 대신 `postfetch_lastrowid = True`에 의존합니다 (C 드라이버는 `get_last_insert_id()` / SQL 폴백, pycubrid는 `cursor.lastrowid`).
- **DEFAULT VALUES**: CUBRID는 `INSERT INTO t DEFAULT VALUES`를 지원합니다. 방언은 `supports_default_values = True`를 설정합니다.
- **ON DUPLICATE KEY UPDATE**: CUBRID는 `VALUES()` 참조를 갖춘 `INSERT … ON DUPLICATE KEY UPDATE`를 지원합니다 (MySQL 8.0 이전 구문과 동일). `sqlalchemy_cubrid.insert(table).on_duplicate_key_update(col=value)`를 사용하세요. 사용 예는 [CUBRID 전용 DML 구성](#cubrid-전용-dml-구성) 참고.
- **MERGE**: CUBRID는 완전한 SQL MERGE 문을 지원합니다. `.using()`, `.on()`, `.when_matched_then_update()`, `.when_not_matched_then_insert()`와 함께 `sqlalchemy_cubrid.dml.merge(target)`을 사용하세요. [CUBRID 전용 DML 구성](#cubrid-전용-dml-구성) 참고.
- **FOR UPDATE**: CUBRID는 `SELECT … FOR UPDATE [OF col1, col2]`를 지원합니다. NOWAIT와 SKIP LOCKED는 미지원.
- **LIMIT를 가진 UPDATE**: CUBRID와 MySQL 모두 `UPDATE … LIMIT n`을 지원합니다. PostgreSQL과 SQLite는 미지원.
- **다중 테이블 UPDATE**: SQLAlchemy의 다중 테이블 UPDATE 패턴은 `UPDATE t1, t2 SET ... WHERE ...`로 컴파일되며, CUBRID가 받는 MySQL 스타일 구문과 일치합니다. 방언은 추가 `FROM` 절이 필요 없기 때문에 의도적으로 `update_from_clause()`를 비활성화합니다.
- **TRUNCATE**: CUBRID는 `TRUNCATE TABLE`을 지원합니다. 방언은 오토커밋 감지에 `TRUNCATE`를 포함합니다.
- **IS DISTINCT FROM**: CUBRID SQL 연산자가 아닙니다. SQLAlchemy는 네이티브 지원이 없는 방언에서 `CASE` 표현식으로 에뮬레이트할 수 있습니다.

---

## DDL — 데이터 정의 언어

| 기능 | CUBRID | MySQL | PostgreSQL | SQLite |
|---------|--------|-------|------------|--------|
| ALTER TABLE | ✅ | ✅ | ✅ | ⚠️ |
| 테이블 코멘트 | ✅ | ✅ | ✅ | ❌ |
| 컬럼 코멘트 | ✅ | ✅ | ✅ | ❌ |
| CREATE … IF NOT EXISTS | ✅ | ✅ | ✅ | ✅ |
| DROP … IF EXISTS | ✅ | ✅ | ✅ | ✅ |
| 임시 테이블 | ❌ | ✅ | ✅ | ✅ |
| 다중 스키마 | ❌ | ✅ | ✅ | ⚠️ |

### 참고

- **ALTER TABLE**: CUBRID는 컬럼과 제약조건 추가/삭제를 위한 표준 `ALTER TABLE`을 지원합니다. SQLite는 ALTER 지원이 제한적입니다 (컬럼 추가만, 3.35 이전에는 drop/rename 불가).
- **코멘트**: CUBRID는 테이블(예: `CREATE TABLE t (...) COMMENT = 'text'`)과 컬럼(예: `col TYPE COMMENT 'text'`) 모두 인라인 `COMMENT` 구문을 지원합니다. 방언은 `SetTableComment`, `DropTableComment`, `SetColumnComment` DDL 구성을 구현합니다. 코멘트 리플렉션은 `get_table_comment()`와 `get_columns()`의 컬럼 코멘트로 지원됩니다.
- **IF NOT EXISTS / IF EXISTS**: CUBRID는 `CREATE TABLE IF NOT EXISTS`와 `DROP TABLE IF EXISTS`를 지원합니다. 기본 SA 컴파일러가 이를 네이티브로 처리합니다.
- **임시 테이블**: CUBRID는 `CREATE TEMPORARY TABLE`이나 세션 범위 테이블을 지원하지 않습니다.
- **다중 스키마**: CUBRID는 단일 스키마 모델로 동작합니다. MySQL은 데이터베이스를 스키마로 사용합니다. SQLite는 데이터베이스를 attach할 수 있지만 진정한 스키마 지원은 없습니다.

---

## 쿼리 기능

| 기능 | CUBRID | MySQL | PostgreSQL | SQLite |
|---------|--------|-------|------------|--------|
| 공통 테이블 표현식 (WITH) | ✅ | ✅ | ✅ | ✅ |
| 재귀 CTE (WITH RECURSIVE) | ✅ | ✅ | ✅ | ✅ |
| DML 상의 CTE | ❌ | ❌ | ✅ | ❌ |
| 윈도우 함수 | ✅ | ✅ | ✅ | ✅ |
| NULLS FIRST / NULLS LAST | ✅ | ❌ | ✅ | ✅ |
| GROUP_CONCAT | ✅ | ✅ | ❌ | ✅ |
| INTERSECT | ✅ | ✅ | ✅ | ✅ |
| EXCEPT | ✅ | ✅ | ✅ | ✅ |
| DISTINCT | ✅ | ✅ | ✅ | ✅ |
| LIMIT / OFFSET | ✅ | ✅ | ✅ | ✅ |
| Lateral 조인 | ❌ | ❌ | ✅ | ❌ |
| 전문 검색 (MATCH … AGAINST) | ❌ | ✅ | ✅ | ✅ |
| 쿼리 추적 / EXPLAIN | ⚠️ | ✅ | ✅ | ✅ |

### 참고

- **CTE**: CUBRID 11.0+는 읽기 쿼리를 위한 `WITH` 절을 지원합니다. 쓰기 가능 CTE(`WITH … INSERT/UPDATE/DELETE`)는 미지원.
- **재귀 CTE**: CUBRID 11.x+는 재귀 쿼리를 위한 `WITH RECURSIVE`를 지원합니다. SQLAlchemy 기본 컴파일러가 올바른 구문을 생성합니다 — 방언별 컴파일이 필요 없습니다.
- **윈도우 함수**: CUBRID는 `OVER(PARTITION BY … ORDER BY …)`와 함께 `ROW_NUMBER()`, `RANK()`, `DENSE_RANK()` 등의 윈도우 함수를 지원합니다. SA 기본 컴파일러가 이를 네이티브로 처리합니다.
- **NULLS FIRST / NULLS LAST**: CUBRID는 `ORDER BY col ASC NULLS FIRST`와 `ORDER BY col DESC NULLS LAST`를 지원합니다. SA 기본 컴파일러가 네이티브로 처리합니다.
- **GROUP_CONCAT**: CUBRID는 `GROUP_CONCAT([DISTINCT] expr [ORDER BY …] [SEPARATOR '…'])`를 지원합니다. `sa.func.group_concat(column)`을 사용하세요.
- **LIMIT / OFFSET**: CUBRID는 MySQL 스타일 `LIMIT [offset,] count` 구문을 사용합니다. 오프셋만 주어지면 방언은 회피로 `LIMIT offset, 1073741823`(최대 int)을 냅니다.
- **조인 변형**: INNER JOIN과 LEFT OUTER JOIN은 정상 컴파일됩니다. FULL OUTER JOIN과 `LATERAL`은 CUBRID가 지원하지 않아 컴파일 중 거부됩니다.
- **Lateral 조인**: CUBRID는 `LATERAL` 서브쿼리를 지원하지 않습니다. `LATERAL` 키워드는 구문 오류를 일으킵니다.
- **전문 검색**: CUBRID는 `MATCH … AGAINST` 구문이나 전문 인덱스를 지원하지 않습니다.
- **쿼리 추적**: CUBRID는 표준 `EXPLAIN` 대신 `SET TRACE ON` / `SHOW TRACE`를 사용합니다. 방언은 유틸리티 함수로 `trace_query()`를 제공합니다 — [CUBRID 전용 DML 구성](#cubrid-전용-dml-구성) 참고.

---

## 타입 시스템

### 표준 SQL 타입

| 타입 | CUBRID | MySQL | PostgreSQL | SQLite |
|------|--------|-------|------------|--------|
| SMALLINT | ✅ | ✅ | ✅ | ✅ |
| INTEGER | ✅ | ✅ | ✅ | ✅ |
| BIGINT | ✅ | ✅ | ✅ | ✅ |
| NUMERIC / DECIMAL | ✅ | ✅ | ✅ | ✅ |
| FLOAT | ✅ | ✅ | ✅ | ✅ |
| DOUBLE / REAL | ✅ | ✅ | ✅ | ✅ |
| BOOLEAN | ⚠️ | ⚠️ | ✅ | ⚠️ |
| DATE | ✅ | ✅ | ✅ | ✅ |
| TIME | ✅ | ✅ | ✅ | ✅ |
| DATETIME | ✅ | ✅ | ✅ | ✅ |
| TIMESTAMP | ✅ | ✅ | ✅ | ✅ |
| CHAR | ✅ | ✅ | ✅ | ✅ |
| VARCHAR | ✅ | ✅ | ✅ | ✅ |
| NCHAR / NVARCHAR | ✅ | ⚠️ | ❌ | ❌ |
| TEXT | ✅ | ✅ | ✅ | ✅ |
| BLOB | ✅ | ✅ | ✅ | ✅ |
| CLOB | ✅ | ✅ | ✅ | ✅ |
| BIT / BIT VARYING | ✅ | ✅ | ✅ | ❌ |

### 확장 타입

| 타입 | CUBRID | MySQL | PostgreSQL | SQLite |
|------|--------|-------|------------|--------|
| ENUM | ❌ | ✅ | ✅ | ❌ |
| JSON | ✅ | ✅ | ✅ | ⚠️ |
| ARRAY | ❌ | ❌ | ✅ | ❌ |
| UUID | ❌ | ❌ | ✅ | ❌ |
| INTERVAL | ❌ | ❌ | ✅ | ❌ |
| HSTORE | ❌ | ❌ | ✅ | ❌ |

### 참고

- **BOOLEAN**: CUBRID는 `BOOLEAN`을 `SMALLINT`로 매핑합니다. MySQL은 `TINYINT(1)`로 매핑합니다. SQLite는 불리언을 정수로 저장합니다. PostgreSQL만 네이티브 `BOOLEAN` 타입을 가집니다.
- **NCHAR / NVARCHAR**: CUBRID는 일급 국가 문자 타입을 가집니다. MySQL은 컬럼 문자셋으로 국가 문자를 처리합니다. PostgreSQL과 SQLite에는 별도의 국가 문자 타입이 없습니다.
- **JSON**: CUBRID 10.2+는 25개 이상의 JSON 함수를 가진 네이티브 JSON 지원(RFC 7159)이 있습니다. 방언은 `JSON` 타입, `JSON_EXTRACT`를 통한 `col["key"]` 경로 표현식, 타입별 접근(`as_string()`, `as_integer()`, `as_float()`)을 지원합니다. MySQL(5.7+)과 PostgreSQL도 네이티브 JSON 지원이 있습니다. SQLite는 JSON 함수는 있지만 전용 컬럼 타입은 없습니다.
- **ARRAY**: CUBRID는 유사 목적을 수행하지만 SQL 표준 배열은 아닌 컬렉션 타입(`SET`, `MULTISET`, `SEQUENCE`)을 사용합니다. PostgreSQL은 네이티브 `ARRAY[]` 지원이 있습니다.
- **CLOB**: CUBRID와 MySQL은 명시적 `CLOB` 타입이 있습니다. PostgreSQL은 `TEXT`(무제한 길이)를 사용합니다. SQLite는 모든 텍스트를 `TEXT`로 저장합니다.

---

## 스키마 리플렉션

| 기능 | CUBRID | MySQL | PostgreSQL | SQLite |
|---------|--------|-------|------------|--------|
| 테이블 이름 | ✅ | ✅ | ✅ | ✅ |
| 컬럼 정보 | ✅ | ✅ | ✅ | ✅ |
| 기본 키 | ✅ | ✅ | ✅ | ✅ |
| 외래 키 | ✅ | ✅ | ✅ | ✅ |
| 인덱스 | ✅ | ✅ | ✅ | ✅ |
| 유니크 제약 | ✅ | ✅ | ✅ | ✅ |
| CHECK 제약 | ❌ | ✅ | ✅ | ❌ |
| 테이블 코멘트 | ✅ | ✅ | ✅ | ❌ |
| 컬럼 코멘트 | ✅ | ✅ | ✅ | ❌ |
| 뷰 이름 | ✅ | ✅ | ✅ | ✅ |
| 뷰 정의 | ✅ | ✅ | ✅ | ✅ |
| 스키마 이름 | ❌ | ✅ | ✅ | ❌ |
| 시퀀스 | ❌ | ❌ | ✅ | ❌ |
| `has_table` | ✅ | ✅ | ✅ | ✅ |
| `has_index` | ✅ | ❌ | ✅ | ✅ |
| `has_sequence` | ❌ | ❌ | ✅ | ❌ |

### 참고

- **CHECK 제약**: CUBRID는 CHECK 제약 구문을 파싱하지만 런타임에 강제하지 않습니다. 오해를 일으키는 메타데이터의 리플렉션을 피하기 위해 방언은 의도적으로 `get_check_constraints()`에서 빈 리스트를 반환합니다.
- **테이블 코멘트**: `db_class.comment` 시스템 카탈로그 컬럼을 조회하는 `get_table_comment()`로 리플렉트됩니다.
- **컬럼 코멘트**: `_db_attribute.comment` 시스템 카탈로그 컬럼을 조회하는 `get_columns()`로 리플렉트됩니다. 각 컬럼 dict의 `"comment"` 키로 반환됩니다.
- **has_index**: CUBRID 방언은 `_db_index`를 조회해 `has_index()`를 구현합니다. MySQL SA 방언은 전용 `has_index()` 메서드를 제공하지 않습니다.
- **리플렉션 소스**: 리플렉션은 여러 소스에 분산되어 있습니다: 컬럼/코멘트는 `SHOW COLUMNS IN` + `_db_attribute`, PK 이름은 `SHOW COLUMNS IN` + 선택적 `db_constraint` 조회, 외래 키와 유니크 제약은 `SHOW CREATE TABLE` 파싱, 인덱스는 `SHOW INDEXES IN` + `_db_index`, 뷰 정의는 `SHOW CREATE VIEW`, 테이블/뷰 이름과 테이블 코멘트는 `db_class`.

---

## 트랜잭션과 연결

| 기능 | CUBRID | MySQL | PostgreSQL | SQLite |
|---------|--------|-------|------------|--------|
| 격리 수준 관리 | ✅ | ✅ | ✅ | ✅ |
| 세이브포인트 | ✅ | ✅ | ✅ | ✅ |
| 2단계 커밋 | ❌ | ✅ | ✅ | ❌ |
| 서버 측 커서 | ❌ | ✅ | ✅ | ❌ |
| 오토커밋 감지 | ✅ | ✅ | ✅ | ✅ |
| 연결 수준 인코딩 | ❌ | ✅ | ✅ | ❌ |

### CUBRID 격리 수준

CUBRID의 MVCC 엔진(10.0+)은 세 가지 격리 수준을 지원합니다:

| 수준 | 설명 |
|-------|-------------|
| `SERIALIZABLE` (6) | 완전 직렬화 |
| `REPEATABLE READ` (5) | 트랜잭션 내 반복 가능한 읽기 |
| `READ COMMITTED` (4, 기본) | 읽기는 커밋된 데이터만 봄. 반복 불가능 리드 가능 |

### 참고

- **2단계 커밋**: CUBRID는 `XA`를 통한 분산 트랜잭션을 지원하지 않습니다.
- **서버 측 커서**: CUBRID Python 드라이버는 서버 측 커서 기능을 노출하지 않습니다.
- **오토커밋 감지**: CUBRID 실행 컨텍스트는 `SET`, `ALTER`, `CREATE`, `DROP`, `GRANT`, `REVOKE`, `TRUNCATE` 문에 매칭하는 정규식 패턴을 사용해 오토커밋 활성화 시점을 결정합니다.
- **세이브포인트**: CUBRID는 `SAVEPOINT`와 `ROLLBACK TO SAVEPOINT`를 지원합니다. `RELEASE SAVEPOINT`는 미지원 — 방언은 `do_release_savepoint()`를 no-op로 구현합니다.

---

## 방언 엔진 기능

| 기능 | CUBRID | MySQL | PostgreSQL | SQLite |
|---------|--------|-------|------------|--------|
| 문장 캐싱 | ✅ | ✅ | ✅ | ✅ |
| 네이티브 enum | ❌ | ✅ | ✅ | ❌ |
| 네이티브 불리언 | ❌ | ❌ | ✅ | ❌ |
| 네이티브 decimal | ✅ | ✅ | ✅ | ❌ |
| 시퀀스 | ❌ | ❌ | ✅ | ❌ |
| ON UPDATE CASCADE | ✅ | ✅ | ✅ | ✅ |
| ON DELETE CASCADE | ✅ | ✅ | ✅ | ✅ |
| 자기 참조 FK | ✅ | ✅ | ✅ | ✅ |
| 독립 연결 | ✅ | ✅ | ✅ | ✅ |
| 유니코드 DDL | ✅ | ✅ | ✅ | ✅ |
| 이름 정규화 | ✅ | ❌ | ✅ | ❌ |

### 참고

- **문장 캐싱**: `supports_statement_cache = True`. 방언은 SQLAlchemy 2.0의 컴파일 캐시와 완전 호환됩니다.
- **이름 정규화**: CUBRID는 인용되지 않은 식별자를 소문자로 폴딩합니다. 방언은 Python 측 기대에 맞게 식별자를 정규화합니다 (`requires_name_normalize = True`).
- **최대 식별자 길이**: CUBRID는 254자까지 식별자를 허용합니다 — MySQL(64)이나 PostgreSQL(63)보다 상당히 깁니다.

---

## CUBRID 전용 기능

이 타입과 역량은 CUBRID 방언에 고유하며 MySQL, PostgreSQL, SQLite에 직접 대응물이 없습니다.

| 기능 | 설명 |
|---------|-------------|
| `MONETARY` 타입 | 로케일 인식 형식의 고정소수점 통화 타입 |
| `STRING` 타입 | `VARCHAR(1,073,741,823)`의 별칭 — 최대 길이 가변 문자열 |
| `OBJECT` 타입 | 객체 식별자로 다른 행을 가리키는 OID 참조 타입 |
| `SET` 컬렉션 | 유일한 원소의 순서 없는 컬렉션 |
| `MULTISET` 컬렉션 | 중복을 허용하는 순서 없는 컬렉션 |
| `SEQUENCE` 컬렉션 | 중복을 허용하는 순서 있는 컬렉션 |
| 3가지 MVCC 격리 수준 | `READ COMMITTED`(기본), `REPEATABLE READ`, `SERIALIZABLE` |
| 254자 식별자 | MySQL(64)과 PostgreSQL(63)보다 김 |

### 컬렉션 타입

CUBRID의 컬렉션 타입(`SET`, `MULTISET`, `SEQUENCE`)은 지정된 데이터 타입의 원소를 담는 타입 컨테이너입니다. DDL에서 다음과 같이 선언됩니다:

```
SET(INTEGER)
MULTISET(VARCHAR)
SEQUENCE(DOUBLE)
```

이것들은 방언의 타입 컴파일러가 완전히 지원하며 `Column` 정의에서 사용할 수 있습니다.

---

## CUBRID 전용 DML 구성

방언은 표준 SA API를 넘어서는 CUBRID 전용 DML 기능을 위한 커스텀 SQLAlchemy 구성을 제공합니다.

### ON DUPLICATE KEY UPDATE

CUBRID는 `VALUES()` 참조를 갖춘 `INSERT … ON DUPLICATE KEY UPDATE`를 지원합니다 (MySQL 8.0 이전 구문과 동일).

```python
from sqlalchemy_cubrid import insert

stmt = insert(users).values(id=1, name="alice", email="alice@example.com")
stmt = stmt.on_duplicate_key_update(name="updated_alice")
# INSERT INTO users (id, name, email) VALUES (1, 'alice', 'alice@example.com')
# ON DUPLICATE KEY UPDATE name = 'updated_alice'

# 삽입되는 값 참조:
stmt = insert(users).values(id=1, name="alice", email="alice@example.com")
stmt = stmt.on_duplicate_key_update(name=stmt.inserted.name)
# ON DUPLICATE KEY UPDATE name = VALUES(name)
```

**허용되는 인자 형태:**
- 키워드 인자: `stmt.on_duplicate_key_update(name="value")`
- 딕셔너리: `stmt.on_duplicate_key_update({"name": "value"})`
- 튜플 리스트 (순서 있음): `stmt.on_duplicate_key_update([("name", "value"), ("email", "value")])`

### MERGE 문

CUBRID는 단일 연산으로 조건부 INSERT/UPDATE를 수행하는 SQL `MERGE` 문을 지원합니다.

```python
from sqlalchemy_cubrid.dml import merge

stmt = (
    merge(target_table)
    .using(source_table)
    .on(target_table.c.id == source_table.c.id)
    .when_matched_then_update(
        {"name": source_table.c.name, "email": source_table.c.email},
        where=source_table.c.name.is_not(None),       # 선택적 WHERE
        delete_where=target_table.c.active == False,   # 선택적 DELETE WHERE
    )
    .when_not_matched_then_insert(
        {
            "id": source_table.c.id,
            "name": source_table.c.name,
            "email": source_table.c.email,
        },
        where=source_table.c.name.is_not(None),  # 선택적 WHERE
    )
)
```

**생성 SQL:**
```sql
MERGE INTO target_table
USING source_table
ON (target_table.id = source_table.id)
WHEN MATCHED THEN UPDATE SET name = source_table.name, email = source_table.email
  WHERE source_table.name IS NOT NULL
  DELETE WHERE target_table.active = 0
WHEN NOT MATCHED THEN INSERT (id, name, email)
  VALUES (source_table.id, source_table.name, source_table.email)
  WHERE source_table.name IS NOT NULL
```

**빌더 메서드:**
- `merge(target)` — 팩토리 함수, 대상 테이블 설정
- `.using(source)` — 소스 테이블 또는 서브쿼리
- `.on(condition)` — 조인 조건
- `.when_matched_then_update(values, where=None, delete_where=None)` — UPDATE 절
- `.when_matched_then_delete(where=None)` — 기존 WHEN MATCHED 절에 DELETE WHERE 추가
- `.when_not_matched_then_insert(values, where=None)` — INSERT 절

`when_matched_then_update` 또는 `when_not_matched_then_insert` 중 최소 하나는 지정해야 합니다.

### GROUP_CONCAT

CUBRID는 집계 함수로 `GROUP_CONCAT`을 지원합니다:

```python
import sqlalchemy as sa

stmt = sa.select(sa.func.group_concat(users.c.name))
# SELECT GROUP_CONCAT(users.name) FROM users
```

### REPLACE INTO

CUBRID는 새 행을 삽입하거나, 중복 키가 발견되면 충돌하는 행을 삭제하고 새 행을 삽입하는 `REPLACE INTO`를 지원합니다.

```python
from sqlalchemy_cubrid import replace

stmt = replace(users).values(id=1, name="alice", email="alice@example.com")
# REPLACE INTO users (id, name, email) VALUES (1, 'alice', 'alice@example.com')
```

`replace()` 구성은 `insert()`처럼 동작하지만 `INSERT INTO` 대신 `REPLACE INTO`를 생성합니다.

### 쿼리 추적

CUBRID는 표준 `EXPLAIN` 대신 `SET TRACE ON` / `SHOW TRACE`를 사용합니다. 방언은 `trace_query()` 유틸리티를 제공합니다:

```python
from sqlalchemy_cubrid import trace_query

with engine.connect() as conn:
    traces = trace_query(conn, text("SELECT * FROM users WHERE id = 1"))
    for line in traces:
        print(line)
```

`trace_query()`는 전체 수명 주기를 처리합니다: 추적 활성화, 문장 실행, 추적 출력 수집, 추적 비활성화 — 전부 안전한 `try/finally` 블록 안에서.

---

## 인덱스 힌트

CUBRID는 SELECT 쿼리에서 인덱스 힌트를 지원합니다. SQLAlchemy 내장 힌트 메커니즘을 통해 사용할 수 있습니다 — 커스텀 방언 구성이 필요 없습니다.

### USING INDEX

```python
# Select.with_hint() 사용
stmt = (
    sa.select(users)
    .with_hint(users, "USING INDEX idx_users_name", dialect_name="cubrid")
)

# Select.suffix_with() 사용
stmt = sa.select(users).suffix_with("USING INDEX idx_users_name")
```

### USE INDEX / FORCE INDEX / IGNORE INDEX

```python
stmt = (
    sa.select(users)
    .with_hint(users, "USE INDEX (idx_users_name)", dialect_name="cubrid")
)

stmt = (
    sa.select(users)
    .with_hint(users, "FORCE INDEX (idx_users_email)", dialect_name="cubrid")
)

stmt = (
    sa.select(users)
    .with_hint(users, "IGNORE INDEX (idx_users_old)", dialect_name="cubrid")
)
```

> **참고**: `with_hint(dialect_name="cubrid")`를 사용하면 힌트는 CUBRID 방언으로 컴파일할 때만 출력됩니다. 다른 방언은 이를 무시하므로 코드가 안전하게 이식 가능합니다.

---

## 알려진 한계와 로드맵

현재 지원되지 않지만 CUBRID 데이터베이스 발전과 커뮤니티 기여에 따라 향후 릴리스에 추가될 수 있는 기능들.

| 기능 | 상태 | 이유 |
|---------|--------|--------|
| RETURNING 절 | ❌ | CUBRID는 `INSERT/UPDATE/DELETE … RETURNING` 미지원 |
| JSON 타입 | ✅ | `JSON_EXTRACT`를 통한 경로 표현식을 갖춘 네이티브 JSON 지원 (CUBRID 10.2+) |
| 임시 테이블 | ❌ | CUBRID는 `CREATE TEMPORARY TABLE` 미지원 |
| 다중 스키마 | ❌ | CUBRID는 단일 스키마 모델로 동작 |
| IS DISTINCT FROM | ❌ | CUBRID SQL 연산자가 아님 |
| CHECK 제약 리플렉션 | ❌ | CUBRID는 CHECK 제약을 파싱하지만 무시 |
| 시퀀스 | ❌ | CUBRID는 대신 `AUTO_INCREMENT` 사용 |
| Lateral 조인 | ❌ | `LATERAL` 키워드가 CUBRID에서 구문 오류 발생 |
| 전문 검색 | ❌ | `MATCH … AGAINST` 구문이나 전문 인덱스 없음 |
| 표준 EXPLAIN | ❌ | CUBRID는 대신 `SET TRACE ON` / `SHOW TRACE` 사용 (`trace_query()`로 지원) |
| Alembic 마이그레이션 | ✅ | `CubridImpl` 엔트리 포인트로 지원 (`pip install sqlalchemy-cubrid[alembic]`) |

---

*최종 갱신: 2026년 4월 · sqlalchemy-cubrid v1.4.0 Beta · SQLAlchemy 2.0–2.1*
