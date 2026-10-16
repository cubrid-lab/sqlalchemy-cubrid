# 2강: 첫 쿼리 실행

> 🌐 [LESSON_FIRST_QUERY.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/LESSON_FIRST_QUERY.md)의 번역입니다. 영어 원문이 표준이며, CI가 영어 원문과의 구조 일치를 검사합니다.

**목표:** SQLAlchemy로 CUBRID에 SQL 쿼리 하나를 보내고, 직접 만든 스크립트가 결과 `2`를
출력합니다.

**사전 준비:** [1강](LESSON_PREPARE.md)의 접속 가능한 데이터베이스와, 이 터미널에서 활성화된
가상 환경.

---

## 스크립트를 만들고 실행하기

같은 폴더에 `first_query.py` 파일을 만드세요.

```python
from sqlalchemy import create_engine, text

# The URL names the dialect and driver, then
# user[:password]@host:port/database: the disposable local lab's values
# (the lab's dba has no password).
engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")

# connect() is when SQLAlchemy actually opens a connection.
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1 + 1"))
    # scalar() reads the single value of the result.
    print(result.scalar())

# Close the engine's pooled connections.
engine.dispose()
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

---

## 실패하면

드라이버 누락, URL 오타, 서버에 닿지 않음, 알 수 없는 데이터베이스·사용자·비밀번호 같은 경우의
메시지는 [첫 연결이 실패하면](QUICKSTART.md#첫-연결이-실패하면)에 있습니다.

---

## 다음

[행을 저장하고 다시 읽기](QUICKSTART.md#3단계-행을-저장하고-다시-읽기)는 과정 페이지에서
이어집니다.
