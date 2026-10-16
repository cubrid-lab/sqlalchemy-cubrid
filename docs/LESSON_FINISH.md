# Lesson 5: Clean up

**Goal:** remove what the course created, and only that: the tutorial table and,
if you used it, the local lab.

**Prerequisites:** the earlier lessons, or any part of them; the cleanup is safe
to run at any point.

---

## Remove the tutorial table

`cleanup_quickstart.py` removes the tutorial table, and only if the table of
that name owned by your user carries the tutorial's comment. A table of the
same name that you created yourself, or one that belongs to another user, is
left alone:

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

It prints `Dropped sqlalchemy_quickstart_notes.`, or
`Nothing to clean up: sqlalchemy_quickstart_notes does not exist.` when there is
nothing left to remove, for example on a second run. An interrupted Lesson 3 can
leave the table behind; this script removes it all the same.

---

## Remove the local lab

If you used the Docker lab from Lesson 1, remove it with
`docker rm -f -v sqlalchemy-cubrid-quickstart`. The image keeps its database in
an anonymous Docker volume that belongs to this container; `-v` deletes that
volume too, and with it `testdb`. Without `-v` the container goes but the
volume stays behind (`docker volume ls` lists it).

---

## Next

You have finished the course. [Next steps](QUICKSTART.md#next-steps) lists where
to go from here: the ORM, connection options, other drivers, async code and
Alembic.
