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

> 긴 "SCHEMA, … INSTANCES" 표기 두 개와 `CURSOR STABILITY`는 여전히 유효한 수준(4/5)으로 해석되기 때문에 하위 호환 별칭으로 유지됩니다. 제거된 수준 1–3으로 해석되던 레거시 이름은 **더 이상 받지 않으며** `ValueError`를 발생시킵니다.

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

### 연결 반환 시 리셋

연결이 풀로 반환되면 방언은 다음 체크아웃을 위한 깨끗한 상태를 보장하기 위해 격리를 수준 4(`READ COMMITTED`)로 리셋합니다.

---

## 모범 사례

1. **특별한 이유가 없으면 기본값(수준 4)을 사용하세요.**
   대부분의 웹 애플리케이션은 `READ COMMITTED`로 올바르게 동작합니다.

2. **`SERIALIZABLE`은 아껴 쓰세요.** 가장 강력한 보장을 제공하지만 부하 하에서 심각한 잠금 경합을 일으킬 수 있습니다.

3. **애플리케이션 전체 기본은 엔진 수준에서 설정**하고, 필요할 때만 연결별로 오버라이드하세요.

4. **DDL 자동 커밋을 인지하세요.** CUBRID는 격리 수준과 무관하게 DDL 문을 자동 커밋합니다. `CREATE TABLE`, `ALTER TABLE` 등은 모든 트랜잭션에 즉시 보입니다.

---

!!! warning "격리 수준 변경에는 COMMIT 필요"
    CUBRID는 커밋 경계와 함께 `SET TRANSACTION ISOLATION LEVEL`을 적용합니다.
    런타임에 수준을 전환할 때 트랜잭션 범위를 그에 맞게 계획하세요.

!!! tip "기본 수준 4는 균형 잡힌 기준선"
    `READ COMMITTED`(수준 4)로 시작하고, 정확성이 중요한 경로에만 수준 5나 6으로 이동하세요.

---

*참고: [연결 설정](CONNECTION.md) · [기능 지원](FEATURE_SUPPORT.md)*
