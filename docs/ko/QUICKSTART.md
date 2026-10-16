# SQLAlchemy로 CUBRID에 처음 연결하기

> 🌐 [QUICKSTART.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/QUICKSTART.md)의 번역입니다. 영어 원문이 표준이며, CI가 영어 원문과의 구조 일치를 검사합니다.

SQLAlchemy로 CUBRID를 사용할 때는 네 가지 구성 요소가 함께 동작합니다.

- **SQLAlchemy**는 여러분이 코드를 작성하는 Python 라이브러리입니다.
- **sqlalchemy-cubrid**는 *방언(dialect)*으로, SQLAlchemy에 CUBRID의 SQL 방식을 알려 줍니다.
- **pycubrid**는 *드라이버*로, SQL을 네트워크를 통해 데이터베이스로 전달합니다.
- **CUBRID 서버**는 데이터베이스 자체로, 어딘가에서 이미 실행 중이어야 하는 별도의 프로그램입니다.

Python 패키지를 설치해도 CUBRID가 설치되거나 데이터베이스가 만들어지지는 않습니다.
이 페이지는 권장 경로인 `sqlalchemy-cubrid[pycubrid]` 패키지와 동기
`cubrid+pycubrid://` URL로, 빈 폴더에서 시작해 첫 쿼리와 첫 저장 행까지 안내합니다.
다른 드라이버, ORM, 비동기 코드와 Alembic은 [그다음](#다음-단계)에 다룹니다.

---

## 시작하기 전에

Python 3.11 이상과 연결할 수 있는 CUBRID 데이터베이스가 필요합니다. 상황에 맞는
방법을 고르세요.

### 방법 A: 이미 CUBRID 데이터베이스가 있습니다

관리자에게 묻거나 직접 구성한 환경에서 다음 다섯 값을 확인하세요.

- **host**: CUBRID가 실행되는 머신, 예: `db.example.com` 또는 `localhost`
- **port**: 연결을 받는 입구인 CUBRID 브로커 포트(기본값 `33000`)
- **database**: 데이터베이스 이름, 예: `testdb`
- **user**와 **password**: 그 데이터베이스의 계정

3단계는 작은 테이블 하나를 만들고 나중에 지웁니다. 연습용 데이터베이스나 그곳에서
테이블을 만들 수 있는 계정을 사용하세요. 이 튜토리얼에 운영 데이터베이스나 그
`dba` 계정을 사용하지 마세요. 2단계와 3단계에서 실습 환경 URL
`cubrid+pycubrid://dba@localhost:33000/testdb`를 여러분의 값으로 채운
`cubrid+pycubrid://USER:PASSWORD@HOST:PORT/DATABASE`로 바꾼 뒤 1단계로 진행하세요.
실제 비밀번호는 공유하거나 커밋하는 파일에 넣지 마세요.

### 방법 B: 버려도 되는 로컬 데이터베이스가 필요합니다

Docker에서 `testdb` 데이터베이스가 있는 일회용 CUBRID 11.4 서버를 시작합니다.
[Docker](https://docs.docker.com/get-started/get-docker/)와 bash 같은 셸이 필요합니다.
명령은 x86_64(amd64) Linux에서 검증했습니다. `cubrid/cubrid:11.4` 이미지는 amd64용으로만
배포되므로 다른 아키텍처(예: Apple silicon)와 Windows는 검증하지 않았습니다.

```bash
docker run -d --name sqlalchemy-cubrid-quickstart -e CUBRID_DB=testdb -p 127.0.0.1:33000:33000 cubrid/cubrid:11.4
ready=no; for i in $(seq 36); do if docker exec sqlalchemy-cubrid-quickstart csql -u dba testdb -c "SELECT 1" >/dev/null 2>&1; then ready=yes; break; fi; sleep 5; done; if [ "$ready" = yes ]; then echo "CUBRID is ready"; else echo "CUBRID did not answer within 3 minutes; see: docker logs sqlalchemy-cubrid-quickstart"; fi
```

`127.0.0.1:`은 이 컴퓨터에만 포트를 열어 다른 머신이 실습 환경에 연결할 수 없게 합니다.
두 번째 명령은 데이터베이스가 응답할 때까지 최대 3분을 기다린 뒤(보통 1분이 채 걸리지
않습니다) `CUBRID is ready`를 출력합니다. 대신 `CUBRID did not answer within 3 minutes`가
출력되면 `docker logs sqlalchemy-cubrid-quickstart`로 원인을 확인하세요. 포트 33000이
이미 사용 중인 경우처럼 `docker run` 자체가 실패했다면 먼저 그 문제를 해결하고
`docker rm -f -v sqlalchemy-cubrid-quickstart`로 컨테이너를 지운 뒤 다시 시작하세요.
실습 환경은 비밀번호가 비어 있는 `dba` 계정을 사용합니다. 이는 이 로컬 일회용
컨테이너에서만 허용됩니다. 다른 사람이 접근할 수 있는 서버에서는 절대 빈 비밀번호를
사용하지 마세요.

튜토리얼을 모두 마치면 `docker rm -f -v sqlalchemy-cubrid-quickstart`로 실습 환경을 지우세요.
이미지는 데이터베이스를 이 컨테이너에 속한 익명 Docker 볼륨에 보관합니다. `-v`가 그 볼륨도 지우므로
`testdb`가 함께 지워집니다. `-v` 없이 지우면 컨테이너만 지워지고 볼륨은 남습니다(`docker volume ls`에
보입니다).

---

## 1단계: 가상 환경에 sqlalchemy-cubrid 설치

가상 환경은 이 프로젝트의 패키지를 시스템의 나머지 부분과 분리합니다. 먼저
`python3 --version`이 3.11 이상을 출력하는지 확인하세요. 더 오래된 버전이 나오면 첫 명령에서
더 새로운 인터프리터를 이름으로 지정하세요(예: `python3.12`). pip은 사용하는 Python을
지원하는 릴리스만 설치하므로, 오래된 인터프리터에는 오래된 패키지가 설치됩니다.
그런 다음 빈 폴더에서 다음 명령을 실행하세요.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "sqlalchemy-cubrid[pycubrid]"
python -c "import sqlalchemy, sqlalchemy_cubrid, pycubrid; print(sqlalchemy.__version__, sqlalchemy_cubrid.__version__, pycubrid.__version__)"
```

`[pycubrid]` 부분은 방언과 함께 권장 순수 Python 드라이버를 설치합니다. 마지막 명령은
설치된 세 버전(SQLAlchemy, sqlalchemy-cubrid, pycubrid)을 출력합니다(예: `2.1.4 1.11.0 1.13.0`).
이 가이드를 마지막으로 실행한 2026-10-15의 PyPI 공개 릴리스이며, 더 새로운 릴리스가 있으면 더 높은
번호가 출력됩니다. 아래의 모든 `python` 명령은 가상 환경이 활성화된 이 터미널에서 실행하세요.

---

## 2단계: 첫 쿼리 실행

같은 폴더에 `first_query.py` 파일을 만드세요.

```python
from sqlalchemy import create_engine, text

# The URL names the dialect and driver, then user[:password]@host:port/database.
# These are the disposable local lab's values; the lab's dba has no password.
engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")

with engine.connect() as conn:  # this is when SQLAlchemy actually connects
    result = conn.execute(text("SELECT 1 + 1"))
    print(result.scalar())  # scalar() reads the single value of the result

engine.dispose()  # close the engine's pooled connections
```

**엔진(engine)**은 URL과 연결 풀을 가지고 있지만, 만들 때 서버에 접속하지는 않습니다.
`engine.connect()`가 데이터베이스와의 세션인 **연결(connection)**을 열고, `execute`가
그 연결로 SQL 문 하나를 보냅니다. `text()`는 문자열을 일반 SQL로 표시합니다. 파일을
실행하세요.

```bash
python first_query.py
```

데이터베이스가 계산한 값을 출력하며, 쿼리가 실제로 서버에 도달했음을 보여 줍니다.

```text
2
```

대신 오류가 나오면 [첫 연결이 실패하면](#첫-연결이-실패하면)으로 가세요.

---

## 3단계: 행을 저장하고 다시 읽기

이 단계에는 2단계에서 동작한 URL이 필요합니다. 같은 URL로 `first_saved_row.py`를
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
| `ModuleNotFoundError: No module named 'pycubrid'` | 이 Python에 드라이버가 설치되지 않았습니다. | 1단계처럼 `[pycubrid]` extra로 설치하고, 가상 환경을 활성화한 뒤 시스템 `python3`이 아닌 `python`을 실행하세요. |
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
