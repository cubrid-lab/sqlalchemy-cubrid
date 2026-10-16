# SQLAlchemy로 CUBRID에 처음 연결하기

> 🌐 [QUICKSTART.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/QUICKSTART.md)의 번역입니다. 영어 원문이 표준이며, CI가 영어 원문과의 구조 일치를 검사합니다.

SQLAlchemy로 CUBRID를 사용할 때는 네 가지 구성 요소가 함께 동작합니다.

- **SQLAlchemy**는 여러분이 코드를 작성하는 Python 라이브러리입니다.
- **sqlalchemy-cubrid**는 *방언(dialect)*으로, SQLAlchemy에 CUBRID의 SQL 방식을 알려 줍니다.
- **pycubrid**는 *드라이버*로, SQL을 네트워크를 통해 데이터베이스로 전달합니다.
- **CUBRID 서버**는 데이터베이스 자체로, 어딘가에서 이미 실행 중이어야 하는 별도의 프로그램입니다.

Python 패키지를 설치해도 CUBRID가 설치되거나 데이터베이스가 만들어지지는 않습니다.
이 과정은 권장 경로인 `sqlalchemy-cubrid[pycubrid]` 패키지와 동기 `cubrid+pycubrid://` URL로,
빈 폴더에서 시작해 첫 쿼리와 첫 저장 행까지 안내합니다. 각 강의에는 목표가 하나 있고, 눈으로 확인할
수 있는 결과로 끝납니다.

1. [CUBRID와 Python 준비](LESSON_PREPARE.md): 접속할 수 있는 데이터베이스와, 방언과 드라이버가
   설치된 가상 환경.
2. [첫 쿼리 실행](LESSON_FIRST_QUERY.md): `SELECT 1 + 1`이 `2`를 출력합니다.
3. 이 페이지의 [행을 저장하고 다시 읽기](#3단계-행을-저장하고-다시-읽기)와 [정리](#정리).

다른 드라이버, ORM, 비동기 코드와 Alembic은 [그다음](#다음-단계)에 다룹니다.

---

## 3단계: 행을 저장하고 다시 읽기

이 단계에는 [2강](LESSON_FIRST_QUERY.md)에서 동작한 URL이 필요합니다. 같은 URL로 `first_saved_row.py`를
만드세요.

```python
from sqlalchemy import create_engine, text

URL = "cubrid+pycubrid://dba@localhost:33000/testdb"
engine = create_engine(URL)

# 1. Create a table that belongs to this tutorial. The comment marks it, so the
#    cleanup script only ever drops this tutorial's own table.
with engine.begin() as conn:  # begin() commits when the block ends without an error
    conn.execute(
        text(
            "CREATE TABLE sqlalchemy_quickstart_notes (id INT PRIMARY KEY, note VARCHAR(100))"
            " COMMENT = 'created by the sqlalchemy-cubrid quickstart'"
        )
    )

# 2. Insert one row. :id and :note are filled from the dictionary that follows.
with engine.begin() as conn:
    conn.execute(
        text("INSERT INTO sqlalchemy_quickstart_notes (id, note) VALUES (:id, :note)"),
        {"id": 1, "note": "my first saved row"},
    )

# 3. Insert a second row, then undo it with rollback.
with engine.connect() as conn:
    conn.execute(
        text("INSERT INTO sqlalchemy_quickstart_notes (id, note) VALUES (:id, :note)"),
        {"id": 2, "note": "this row is rolled back"},
    )
    conn.rollback()  # discard everything since the transaction began

engine.dispose()

# 4. Read the table through a brand-new engine, so through a different connection.
check = create_engine(URL)
with check.connect() as conn:
    rows = conn.execute(text("SELECT id, note FROM sqlalchemy_quickstart_notes ORDER BY id")).all()
    print("Rows seen by a new connection:", rows)
check.dispose()
```

**트랜잭션**은 변경 사항을 묶어 함께 영구 반영되게 합니다. `engine.begin()`을 쓰면 블록이
끝날 때 커밋하고, 오류가 발생하면 롤백합니다. `rollback()`은 트랜잭션이 시작된 이후의 모든
변경을 버립니다. `:id`와 `:note`는 바인딩 파라미터입니다. 값을 SQL 텍스트에 직접 붙여 넣지
말고 항상 이렇게 전달하세요. 파일을 실행하세요.

```bash
python first_saved_row.py
```

롤백한 행은 사라지고, 별도의 연결은 저장된 행을 봅니다.

```text
Rows seen by a new connection: [(1, 'my first saved row')]
```

파일을 두 번째로 실행하거나 중단된 뒤 다시 실행하면 첫 문장에서
`Class dba.sqlalchemy_quickstart_notes already exists`로 멈춥니다(소유자 이름, 여기서는
`dba`는 여러분의 사용자입니다). 이전 실행의 테이블이 아직 남아 있으니 아래 정리를 실행한 뒤
`first_saved_row.py`를 다시 실행하세요.

### 정리

`cleanup_quickstart.py`는 튜토리얼 테이블을 지우는데, 여러분의 사용자가 소유한 그 이름의
테이블에 튜토리얼 주석이 있을 때만 지웁니다. 여러분이 직접 만든 같은 이름의 테이블이나 다른
사용자의 테이블은 그대로 둡니다.

```python
from sqlalchemy import create_engine, text

MARK = "created by the sqlalchemy-cubrid quickstart"
engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")

with engine.begin() as conn:
    comment = conn.execute(
        text(
            "SELECT comment FROM db_class"
            " WHERE class_name = :name AND owner_name = CURRENT_USER"
        ),
        {"name": "sqlalchemy_quickstart_notes"},
    ).first()
    if comment is None:
        print("Nothing to clean up: sqlalchemy_quickstart_notes does not exist.")
    elif comment[0] != MARK:
        print("Not dropped: sqlalchemy_quickstart_notes was not created by this quickstart.")
    else:
        conn.execute(text("DROP TABLE sqlalchemy_quickstart_notes"))
        print("Dropped sqlalchemy_quickstart_notes.")

engine.dispose()
```

```bash
python cleanup_quickstart.py
```

`Dropped sqlalchemy_quickstart_notes.`를 출력하거나, 지울 것이 없으면
`Nothing to clean up: sqlalchemy_quickstart_notes does not exist.`를 출력합니다. Docker
실습 환경을 사용했다면 `docker rm -f -v sqlalchemy-cubrid-quickstart`로 실습 환경 전체도
지울 수 있습니다.

---

## 첫 연결이 실패하면

다음은 SQLAlchemy 2.1.4, sqlalchemy-cubrid 1.11.0, pycubrid 1.13.0으로 CUBRID 11.4 실습
환경에서 각 실수에 대해 출력된 메시지(트레이스백의 마지막 줄)입니다. SQLAlchemy는 드라이버
오류를 감싸며, 드라이버 오류는 괄호 안에 표시됩니다.

| 메시지 | 의미 | 확인할 것 |
|---|---|---|
| `ModuleNotFoundError: No module named 'pycubrid'` | 이 Python에 드라이버가 설치되지 않았습니다. | [1강](LESSON_PREPARE.md#가상-환경에-sqlalchemy-cubrid-설치)처럼 `[pycubrid]` extra로 설치하고, 가상 환경을 활성화한 뒤 시스템 `python3`이 아닌 `python`을 실행하세요. |
| `NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:cubrid.pycubird` | URL이 존재하지 않는 방언이나 드라이버를 가리킵니다(여기서는 오타). | URL이 정확히 `cubrid+pycubrid://`로 시작하는지 확인하세요. |
| `OperationalError: (pycubrid.exceptions.OperationalError) failed to connect to CUBRID broker` | 그 호스트와 포트에서 아무것도 응답하지 않았습니다. | 서버가 실행 중인지(실습 환경이면 `docker ps`에 `sqlalchemy-cubrid-quickstart`가 보이는지), URL의 호스트와 포트가 맞는지, 방화벽이 포트를 막지 않는지 확인하세요. |
| `DatabaseError: (pycubrid.exceptions.DatabaseError) Failed to connect to database server, 'nosuchdb', ...` | 브로커는 응답했지만 그 이름으로 실행 중인 데이터베이스가 없습니다. | URL 끝의 데이터베이스 이름을 확인하고, 그 데이터베이스가 시작되어 있는지 관리자에게 물어보세요. |
| `OperationalError: (pycubrid.exceptions.OperationalError) User "nobody" is invalid. ...` | 그 데이터베이스에 해당 사용자가 없습니다. | URL의 사용자 이름을 확인하세요. |
| `OperationalError: (pycubrid.exceptions.OperationalError) Incorrect or missing password. ...` | 사용자는 있지만 비밀번호가 틀렸습니다. | URL의 비밀번호(`user:password@...`)를 확인하세요. |

포트를 생략하면(`cubrid+pycubrid://dba@localhost/testdb`) 기본값 `33000`을 사용합니다.
문제를 우회하지 말고 값을 고치세요. 운영 `dba` 계정으로 바꾸거나 오류를 없애려고 TLS 인증서
검사를 끄지 마세요. `@`, `:`, `/`가 포함된 비밀번호는 URL에서 퍼센트 인코딩해야 합니다.
SQLAlchemy의
[특수 문자 이스케이프](https://docs.sqlalchemy.org/en/20/core/engines.html#escaping-special-characters-such-as-signs-in-passwords)를
참고하세요. 더 많은 사례는 [문제 해결](TROUBLESHOOTING.md)에 있습니다.

---

## 다음 단계

여러분은 SQL 문과 테이블을 직접 다루는 SQLAlchemy **Core**로 SQL을 실행했습니다. **ORM**은
대신 Python 클래스를 테이블에 매핑하므로 객체로 작업합니다. ORM도 같은 엔진과 연결 개념
위에서 동작합니다.

- [README 사용법](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/README.ko.md#빠른-시작): 짧은 Core, ORM, 비동기 예제.
- [ORM 쿡북](ORM_COOKBOOK.md): 모델, 관계, 일반적인 ORM 패턴.
- [연결 가이드](CONNECTION.md): 모든 URL 형식, 연결 옵션, 비동기 `cubrid+aiopycubrid://` 드라이버.
- [드라이버 호환성](DRIVER_COMPAT.md): 소스에서 빌드하는 지원 CUBRIDdb C 확장 드라이버와 드라이버 간 차이.
- [Alembic 마이그레이션](ALEMBIC.md), [타입 매핑](TYPES.md), [기능 지원](FEATURE_SUPPORT.md)(`RETURNING` 절 미지원 같은 CUBRID의 제약 포함).

---

## 시작하기 전에

[1강: CUBRID와 Python 준비](LESSON_PREPARE.md)로 옮겨졌습니다.

### 방법 A: 이미 CUBRID 데이터베이스가 있습니다

[1강의 방법 A](LESSON_PREPARE.md#방법-a-이미-cubrid-데이터베이스가-있습니다)로 옮겨졌습니다.

### 방법 B: 버려도 되는 로컬 데이터베이스가 필요합니다

[1강의 방법 B](LESSON_PREPARE.md#방법-b-버려도-되는-로컬-데이터베이스가-필요합니다)로 옮겨졌습니다.

---

## 1단계: 가상 환경에 sqlalchemy-cubrid 설치

[1강](LESSON_PREPARE.md#가상-환경에-sqlalchemy-cubrid-설치)으로 옮겨졌습니다.

---

## 2단계: 첫 쿼리 실행

[2강: 첫 쿼리 실행](LESSON_FIRST_QUERY.md)으로 옮겨졌습니다.
