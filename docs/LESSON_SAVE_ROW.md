# Lesson 3: Save a row and read it back

**Goal:** a small table of your own with one saved row, and proof that the row
is stored: a separate connection reads it back.

**Prerequisites:** [Lesson 2](LESSON_FIRST_QUERY.md), with the URL that worked
there. With your own database (Option A in [Lesson 1](LESSON_PREPARE.md)), use an
account that may create tables, never a production database or its `dba`
account.

---

## Write and run the script

Create `save_row.py` with the same URL:

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

A **transaction** groups changes so that they become permanent together. With
`engine.begin()`, the block commits when it finishes and rolls back if it
raises an error. `:id` and `:note` are bound parameters: always pass values
this way instead of pasting them into the SQL text yourself. Run the file:

```bash
python save_row.py
```

A separate connection sees the saved row, so it really was committed:

```text
Rows seen by a new connection: [(1, 'my first saved row')]
```

---

## Running it again

Running the file again stops at the first statement with
`Class dba.sqlalchemy_quickstart_notes already exists` (the owner name, here
`dba`, is your user), because the table from the earlier run is still there:

- **The earlier run printed the row.** The table and its row are complete:
  continue with Lesson 4 as it is.
- **The earlier run was interrupted before it printed the row.** The table can
  exist without its row, and Lesson 4 would then print `1` and `[]`. Run
  [the table cleanup from Lesson 5](LESSON_FINISH.md#remove-the-tutorial-table),
  which removes only this tutorial's table, then run `save_row.py` again until it
  prints the row.

---

## Next

[Lesson 4: Undo changes with a rollback](LESSON_TRANSACTIONS.md).
