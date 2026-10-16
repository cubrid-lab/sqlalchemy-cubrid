# Lesson 4: Undo changes with a rollback

**Goal:** see that changes inside a transaction stay invisible and temporary
until they are committed, and that a rollback discards them.

**Prerequisites:** [Lesson 3](LESSON_SAVE_ROW.md): the table
`sqlalchemy_quickstart_notes` with its saved row.

---

## Write and run the script

Create `rollback_row.py`:

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

Unlike `engine.begin()`, `engine.connect()` does not commit for you: the first
statement starts a transaction, and nothing in it is permanent until you call
`commit()`. Inside the transaction the new row is visible to this connection, so
the count is `2`; `rollback()` throws away everything since the transaction
began. Run the file:

```bash
python rollback_row.py
```

```text
Rows inside the transaction: 2
Rows after the rollback: [(1, 'my first saved row')]
```

The rolled-back row is gone. Nothing was committed, so you can run the file as
often as you like and get the same output. If it fails with
`Unknown class "dba.sqlalchemy_quickstart_notes"`, the table does not exist:
run `save_row.py` from Lesson 3 first.

---

## Next

[Lesson 5: Clean up](LESSON_FINISH.md).
