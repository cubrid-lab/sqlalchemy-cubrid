# Lesson 2: Run your first query

**Goal:** one SQL query sent through SQLAlchemy to CUBRID, and its result, `2`,
printed by your own script.

**Prerequisites:** [Lesson 1](LESSON_PREPARE.md): a reachable database and the
virtual environment, active in this terminal.

---

## Write and run the script

Create a file named `first_query.py` in the same folder:

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

An **engine** holds the URL and a pool of connections, but creating it does not
contact the server. `engine.connect()` opens a **connection**, your session with
the database, and `execute` sends one SQL statement over it; `text()` marks a
string as plain SQL. Run the file:

```bash
python first_query.py
```

It prints the value the database computed, which proves that a query really
reached the server:

```text
2
```

---

## If it fails

The messages for a missing driver, a mistyped URL, an unreachable server, an
unknown database, user or password are in
[If the first connection fails](QUICKSTART.md#if-the-first-connection-fails).

---

## Next

[Lesson 3: Save a row and read it back](LESSON_SAVE_ROW.md).
