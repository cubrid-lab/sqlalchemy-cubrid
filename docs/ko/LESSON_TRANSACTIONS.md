# 4강: 롤백으로 변경 취소하기

> 🌐 [LESSON_TRANSACTIONS.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/LESSON_TRANSACTIONS.md)의 번역입니다. 영어 원문이 표준이며, CI가 영어 원문과의 구조 일치를 검사합니다.

**목표:** 트랜잭션 안의 변경은 커밋하기 전까지 임시이고, 롤백하면 버려진다는 것을 확인합니다.

**사전 준비:** [3강](LESSON_SAVE_ROW.md)의 테이블 `sqlalchemy_quickstart_notes`와 저장된 행.

---

## 스크립트를 만들고 실행하기

`rollback_row.py`를 만드세요.

```python
from sqlalchemy import create_engine, text

URL = "cubrid+pycubrid://dba@localhost:33000/testdb"
engine = create_engine(URL)

# Insert a second row inside a transaction, look at it, then undo it.
with engine.connect() as conn:  # the first execute() starts a transaction
    conn.execute(
        text("INSERT INTO sqlalchemy_quickstart_notes (id, note) VALUES (:id, :note)"),
        {"id": 2, "note": "this row is rolled back"},
    )
    count = conn.execute(text("SELECT COUNT(*) FROM sqlalchemy_quickstart_notes")).scalar()
    print("Rows inside the transaction:", count)
    conn.rollback()  # discard everything since the transaction began

engine.dispose()

check = create_engine(URL)
with check.connect() as conn:
    rows = conn.execute(text("SELECT id, note FROM sqlalchemy_quickstart_notes ORDER BY id")).all()
    print("Rows after the rollback:", rows)
check.dispose()
```

`engine.begin()`과 달리 `engine.connect()`는 대신 커밋하지 않습니다. 첫 문장이 트랜잭션을 시작하며,
`commit()`을 호출하기 전까지 그 안의 어떤 변경도 영구적이지 않습니다. 트랜잭션 안에서는 이 연결이
새 행을 볼 수 있으므로 개수가 `2`입니다. `rollback()`은 트랜잭션이 시작된 이후의 모든 변경을
버립니다. 파일을 실행하세요.

```bash
python rollback_row.py
```

```text
Rows inside the transaction: 2
Rows after the rollback: [(1, 'my first saved row')]
```

롤백한 행은 사라졌습니다. 아무것도 커밋하지 않았으므로 몇 번을 실행해도 같은 결과가 나옵니다.
`Unknown class "dba.sqlalchemy_quickstart_notes"`로 실패하면 테이블이 없는 것이니 먼저 3강의
`save_row.py`를 실행하세요.

---

## 다음

[5강: 정리](LESSON_FINISH.md).
