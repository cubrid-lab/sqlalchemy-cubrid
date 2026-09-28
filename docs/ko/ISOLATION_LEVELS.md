# 격리 수준 (한국어)

> 🌐 [ISOLATION_LEVELS.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/ISOLATION_LEVELS.md)의 번역입니다. 영어 원문이 표준이며, 페이지 번역은 경고 수준의 동기화 규칙을 따릅니다.

CUBRID 10.0(MVCC 엔진)부터 CUBRID는 **세 가지** 트랜잭션 격리 수준을 지원합니다: `READ COMMITTED`, `REPEATABLE READ`, `SERIALIZABLE`. 이 문서는 각 수준, 구성 방법, 다른 데이터베이스와의 비교를 설명합니다.

> **역사적 참고.** CUBRID 10.0 이전 릴리스는 격리를 *스키마*(클래스 수준)와 *인스턴스*(데이터 수준) 차원으로 분리한 6개 숫자 수준(1–6)을 노출했습니다. 10.0에 도입된 MVCC 엔진은 레거시 세분화 수준 4개를 제거했습니다. 서버는 이제 숫자 코드 `4`(READ COMMITTED), `5`(REPEATABLE READ), `6`(SERIALIZABLE)만 받습니다. 현대 서버에서 `SET TRANSACTION ISOLATION LEVEL 1|2|3`을 시도하면 다음과 함께 실패합니다:
>
> ```
> Isolation level value in MVCC must be 'read committed', 'repeatable read' or 'serializable'
> ```
>
> 따라서 이 방언은 수준 4, 5, 6으로 해석되는 이름만 받습니다.

---

## 목차

- [개요](#개요)
- [격리 수준 상세](#격리-수준-상세)
- [구성](#구성)
  - [엔진 수준 (모든 연결의 기본)](#엔진-수준-모든-연결의-기본)
  - [연결 수준 (연결별)](#연결-수준-연결별)
  - [실행 옵션 (문장 블록별)](#실행-옵션-문장-블록별)
  - [AUTOCOMMIT](#autocommit)
- [허용되는 수준 이름](#허용되는-수준-이름)
- [SQL 표준과 비교](#sql-표준과-비교)
- [방언의 격리 관리 방식](#방언의-격리-관리-방식)
- [모범 사례](#모범-사례)

---

## 개요

| 수준 | 숫자 | 이름 (약칭)                    |
|-------|---------|-------------------------------|
| 6     | 6       | `SERIALIZABLE`                |
| 5     | 5       | `REPEATABLE READ`             |
| 4     | 4       | `READ COMMITTED` *(기본)*     |

CUBRID 서버 기본값은 **수준 4**(`READ COMMITTED`)입니다.

---

## 격리 수준 상세

### 수준 6 — SERIALIZABLE

가장 엄격한 격리 수준. 트랜잭션이 완전히 직렬화됩니다: 더티 리드 없음, 반복 불가능 리드 없음, 팬텀 리드 없음.

**사용 시기**: 절대적 일관성이 필요할 때 (예: 금융 거래, 감사 로그).

**트레이드오프**: 잠금 경합 최고, 동시성 최저.

### 수준 5 — REPEATABLE READ

트랜잭션 내에서 읽기가 반복 가능합니다. 인덱스된 컬럼에서 팬텀 리드가 없습니다.

**사용 시기**: 트랜잭션 내 일관된 읽기가 필요하지만 serializable보다 약간 낮은 처리량을 감당할 수 있을 때.

### 수준 4 — READ COMMITTED *(기본)*

읽기는 커밋된 값만 보지만 재읽기 시 다른 결과를 볼 수 있습니다 (반복 불가능 리드 가능).

**사용 시기**: 범용 OLTP 워크로드. 대부분의 애플리케이션에 일관성과 성능의 최고 균형.

---

## 구성

### 엔진 수준 (모든 연결의 기본)

엔진 생성 시 기본 격리 수준 설정:

```python
from sqlalchemy import create_engine

engine = create_engine(
    "cubrid://dba@localhost:33000/testdb",
    isolation_level="REPEATABLE READ",
)
```

### 연결 수준 (연결별)

특정 연결에 격리 수준 설정:

```python
from sqlalchemy import text

with engine.connect().execution_options(
    isolation_level="SERIALIZABLE"
) as conn:
    result = conn.execute(text("SELECT * FROM accounts WHERE id = :id"), {"id": 1})
    # 이 연결은 SERIALIZABLE 격리 사용
```

### 실행 옵션 (문장 블록별)

```python
with engine.begin() as conn:
    # 이 블록의 격리 전환
    conn = conn.execution_options(isolation_level="SERIALIZABLE")
    conn.execute(text("UPDATE accounts SET balance = balance - 100 WHERE id = 1"))
    conn.execute(text("UPDATE accounts SET balance = balance + 100 WHERE id = 2"))
    # 블록 끝에서 커밋
```

### AUTOCOMMIT

`AUTOCOMMIT`은 드라이버의 오토커밋 모드를 켜서 각 문장이 실행 즉시 커밋되게 합니다. `cubrid://`(CUBRIDdb), `cubrid+pycubrid://`, `cubrid+aiopycubrid://`에서 SQLAlchemy가 제공하는 모든 수준으로 사용할 수 있습니다:

```python
# 이 엔진의 모든 연결
engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb", isolation_level="AUTOCOMMIT")

# 풀을 공유하는 엔진 사본
autocommit_engine = engine.execution_options(isolation_level="AUTOCOMMIT")

# 하나의 연결
with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
    conn.execute(text("INSERT INTO logs (msg) VALUES ('event')"))
    # 다른 세션에 이미 보이며, conn.rollback()으로 되돌릴 수 없음
```

`AUTOCOMMIT`은 서버 격리 수준이 아니라 드라이버 모드입니다. `cubrid://`(CUBRIDdb)에서는 서버 수준이 그대로이며 `conn.get_isolation_level()`도 그 수준을 보고합니다. pycubrid 1.8.0은 오토커밋 모드에서도 세션을 유지하므로 `cubrid+pycubrid://`와 `cubrid+aiopycubrid://`에서도 마찬가지입니다([드라이버 호환성, 알려진 문제 10](DRIVER_COMPAT.md#10-pycubrid는-cas-재시작-후-세션을-교체-방언이-격리-수준을-다시-적용) 참고). 다른 수준을 설정하면 드라이버 오토커밋이 다시 꺼지고, 풀링된 연결은 반환될 때 트랜잭션 모드로 돌아갑니다([연결 반환 시 리셋](#연결-반환-시-리셋) 참고). DBAPI 연결의 모드는 `engine.dialect.detect_autocommit_setting(dbapi_connection)`으로 확인할 수 있습니다.

---

## 허용되는 수준 이름

방언은 편의를 위해 여러 이름 형태를 받습니다. 모든 이름은 세 MVCC 수준 중 하나로 해석되며, 이름은 **대소문자를 구분하지 않습니다**.

| 이름                                                    | 매핑되는 수준 |
|--------------------------------------------------------|---------------|
| `SERIALIZABLE`                                          | 6             |
| `REPEATABLE READ`                                       | 5             |
| `REPEATABLE READ SCHEMA, REPEATABLE READ INSTANCES`     | 5             |
| `READ COMMITTED`                                        | 4             |
| `REPEATABLE READ SCHEMA, READ COMMITTED INSTANCES`      | 4             |
| `CURSOR STABILITY`                                      | 4             |
| `AUTOCOMMIT`                                            | 드라이버 오토커밋, 서버 수준 없음 |

> 긴 "SCHEMA, … INSTANCES" 표기 두 개와 `CURSOR STABILITY`는 여전히 유효한 수준(4/5)으로 해석되기 때문에 하위 호환 별칭으로 유지됩니다. 엔진 수준 별칭은 정규 이름으로 저장됩니다(예: `isolation_level="CURSOR STABILITY"`는 `READ COMMITTED`가 됨). 제거된 수준 1–3으로 해석되던 레거시 이름은 **더 이상 받지 않습니다**. 알 수 없는 이름은 `create_engine(isolation_level=...)`(첫 연결 시)과 `execution_options(isolation_level=...)`에서 `sqlalchemy.exc.ArgumentError`를 발생시키며, `dialect.set_isolation_level()`을 직접 호출하면 `ValueError`를 발생시킵니다.

---

## SQL 표준과 비교

| SQL 표준 수준          | CUBRID 대응          | 수준 |
|-----------------------|---------------------|-------|
| `READ UNCOMMITTED`    | *(미지원)*          | —     |
| `READ COMMITTED`      | 수준 4 *(기본)*     | 4     |
| `REPEATABLE READ`     | 수준 5              | 5     |
| `SERIALIZABLE`        | 수준 6              | 6     |

CUBRID의 MVCC 엔진은 `READ UNCOMMITTED`(더티 리드) 수준을 제공하지 않습니다. 사용 가능한 최저 수준은 `READ COMMITTED`입니다.

---

## 방언의 격리 관리 방식

### 격리 수준 설정

방언은 CUBRID의 숫자 수준과 함께 `SET TRANSACTION ISOLATION LEVEL` SQL 명령을 사용합니다:

```sql
SET TRANSACTION ISOLATION LEVEL 5
COMMIT
```

격리 수준 설정 후의 `COMMIT`은 변경 적용을 위해 CUBRID가 요구합니다.

### 현재 수준 읽기

방언은 CUBRID의 독자 구문으로 현재 격리 수준을 읽습니다:

```sql
GET TRANSACTION ISOLATION LEVEL TO X
SELECT X
```

반환된 숫자 값은 설명 문자열로 다시 매핑됩니다.

> **참고 — 읽기 시 정규 이름.** `get_isolation_level()`은 수준의 **정규(canonical)** 이름을 반환하며, 이는 `set_isolation_level()`에 전달한 별칭과 다를 수 있습니다. CUBRID는 같은 숫자 수준으로 매핑되는 여러 별칭을 받습니다([허용되는 수준 이름](#허용되는-수준-이름) 참고) — 예컨대 `"REPEATABLE READ"`와 `"REPEATABLE READ SCHEMA, REPEATABLE READ INSTANCES"` 둘 다 수준 5로 매핑 — 하지만 수준 읽기는 숫자 코드를 단일 정규 항목으로 되돌려 해석합니다. 따라서 `set` → `get` 왕복은 (전달한 정확한 문자열이 아니라) 정규 이름(예: `"REPEATABLE READ"`)을 반환합니다.

### pycubrid에서 commit과 rollback 후에도 유지

pycubrid 1.8.0은 `commit()` / `rollback()` 이후에도 CAS 세션과 격리 수준을 유지하며, CAS 자체가 재시작된 경우에만 서버 기본 수준으로 새 세션을 엽니다([드라이버 호환성, 알려진 문제 10](DRIVER_COMPAT.md#10-pycubrid는-cas-재시작-후-세션을-교체-방언이-격리-수준을-다시-적용) 참고). 따라서 `cubrid+pycubrid://`와 `cubrid+aiopycubrid://`는 연결에 마지막으로 설정한 수준을 commit과 rollback마다 다시 적용하여, 트랜잭션 끝에서 CAS가 교체되어도 엔진 수준 또는 연결 수준 `isolation_level`이 유지되도록 합니다. `cubrid://`(CUBRIDdb)는 세션을 유지하므로 다시 적용할 필요가 없습니다.

### 연결 반환 시 리셋

`execution_options()`로 수준을 바꾼 연결이 풀로 반환되면 SQLAlchemy가 엔진 수준 `isolation_level`(`AUTOCOMMIT` 포함)을 복원합니다. 엔진 수준 설정이 없으면 첫 연결이 보고한 수준, 즉 서버 기본값(보통 `READ COMMITTED`)을 복원합니다. 이전 릴리스는 항상 `READ COMMITTED`로 리셋했기 때문에 연결별 재정의 후 엔진 수준 설정이 사라졌습니다.

---

## 모범 사례

1. **특별한 이유가 없으면 기본값(수준 4)을 사용하세요.**
   대부분의 웹 애플리케이션은 `READ COMMITTED`로 올바르게 동작합니다.

2. **`SERIALIZABLE`은 아껴 쓰세요.** 가장 강력한 보장을 제공하지만 부하 하에서 심각한 잠금 경합을 일으킬 수 있습니다.

3. **애플리케이션 전체 기본은 엔진 수준에서 설정**하고, 필요할 때만 연결별로 오버라이드하세요.

4. **DDL은 트랜잭션으로 처리됩니다.** 모든 격리 수준에서 CUBRID는 DDL을 현재 트랜잭션 안에서 실행합니다. `ROLLBACK`은 `CREATE TABLE`, `ALTER TABLE` 등을 되돌리고, DDL은 앞선 DML을 커밋하지 않습니다. 커밋되지 않은 DDL은 테이블의 스키마 잠금을 유지하므로, 그 테이블을 사용하는 다른 트랜잭션은 커밋이나 롤백까지 기다립니다. DDL을 즉시 커밋하는 것은 클라이언트 자동 커밋(드라이버 수준 자동 커밋, 또는 방언이 지원하는 경우(#501) `isolation_level="AUTOCOMMIT"`)뿐입니다.

---

!!! warning "격리 수준 변경에는 COMMIT 필요"
    CUBRID는 커밋 경계와 함께 `SET TRANSACTION ISOLATION LEVEL`을 적용합니다.
    런타임에 수준을 전환할 때 트랜잭션 범위를 그에 맞게 계획하세요.

!!! tip "기본 수준 4는 균형 잡힌 기준선"
    `READ COMMITTED`(수준 4)로 시작하고, 정확성이 중요한 경로에만 수준 5나 6으로 이동하세요.

---

*참고: [연결 설정](CONNECTION.md) · [기능 지원](FEATURE_SUPPORT.md)*
