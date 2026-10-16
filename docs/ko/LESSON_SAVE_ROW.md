# 3강: 행을 저장하고 다시 읽기

> 🌐 [LESSON_SAVE_ROW.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/LESSON_SAVE_ROW.md)의 번역입니다. 영어 원문이 표준이며, CI가 영어 원문과의 구조 일치를 검사합니다.

**목표:** 직접 만든 작은 테이블에 행 하나를 저장하고, 별도의 연결이 그 행을 다시 읽어 실제로
저장되었음을 확인합니다.

**사전 준비:** [2강](LESSON_FIRST_QUERY.md)과 거기서 동작한 URL. 여러분의 데이터베이스를 쓴다면
([1강](LESSON_PREPARE.md)의 방법 A) 테이블을 만들 수 있는 계정을 쓰고, 운영 데이터베이스나 그 `dba`
계정은 절대 쓰지 마세요.

---

## 스크립트를 만들고 실행하기

같은 URL로 `save_row.py`를 만드세요.

```python
from sqlalchemy import create_engine, text

URL = "cubrid+pycubrid://dba@localhost:33000/testdb"
engine = create_engine(URL)

# 1. Create a table that belongs to this tutorial. Its comment marks it, so the
#    cleanup in Lesson 5 only ever drops this tutorial's own table.
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

engine.dispose()

# 3. Read the table through a brand-new engine, so through a different connection.
check = create_engine(URL)
with check.connect() as conn:
    rows = conn.execute(text("SELECT id, note FROM sqlalchemy_quickstart_notes ORDER BY id")).all()
    print("Rows seen by a new connection:", rows)
check.dispose()
```

**트랜잭션**은 변경 사항을 묶어 함께 영구 반영되게 합니다. `engine.begin()`을 쓰면 블록이 끝날
때 커밋하고, 오류가 발생하면 롤백합니다. `:id`와 `:note`는 바인딩 파라미터입니다. 값을 SQL
텍스트에 직접 붙여 넣지 말고 항상 이렇게 전달하세요. 파일을 실행하세요.

```bash
python save_row.py
```

별도의 연결이 저장된 행을 보므로 실제로 커밋되었습니다.

```text
Rows seen by a new connection: [(1, 'my first saved row')]
```

---

## 다시 실행하면

파일을 다시 실행하면 이전 실행의 테이블이 아직 남아 있으므로 첫 문장에서
`Class dba.sqlalchemy_quickstart_notes already exists`로 멈춥니다(소유자 이름, 여기서는 `dba`는
여러분의 사용자입니다).

- **이전 실행이 행을 출력했다면** 테이블과 행이 모두 있으니 그대로 4강으로 진행하세요.
- **이전 실행이 행을 출력하기 전에 중단되었다면** 테이블만 있고 행이 없을 수 있으며, 그러면 4강은
  `1`과 `[]`를 출력합니다. 이 튜토리얼의 테이블만 지우는
  [5강의 테이블 정리](LESSON_FINISH.md#튜토리얼-테이블-지우기)를 실행한 뒤, 행이 출력될 때까지
  `save_row.py`를 다시 실행하세요.

---

## 다음

[4강: 롤백으로 변경 취소하기](LESSON_TRANSACTIONS.md).
