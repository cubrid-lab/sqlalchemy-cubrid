# Your First SQLAlchemy Connection to CUBRID

Four pieces work together when you use SQLAlchemy with CUBRID:

- **SQLAlchemy** is the Python library you write your code against;
- **sqlalchemy-cubrid** is the *dialect*: it teaches SQLAlchemy CUBRID's flavour of SQL;
- **pycubrid** is the *driver*: it carries the SQL over the network to the database;
- the **CUBRID server** is the database itself, a separate program that must already be running somewhere.

Installing the Python packages does not install CUBRID or create a database.
This page takes you from an empty folder to a first query and a first saved
row on the recommended path: the `sqlalchemy-cubrid[pycubrid]` package and the
synchronous `cubrid+pycubrid://` URL. Other drivers, the ORM, async code and
Alembic come [afterwards](#next-steps).

---

## Before you start

You need Python 3.11 or later and a CUBRID database you can connect to. Pick
the option that matches your situation.

### Option A: I already have a CUBRID database

Ask its administrator (or look in your own setup) for these five values:

- **host**: the machine that runs CUBRID, for example `db.example.com` or `localhost`;
- **port**: the CUBRID broker port, the entry point that accepts connections (the default is `33000`);
- **database**: the database name, for example `testdb`;
- **user** and **password**: an account for that database.

Step 3 creates and later removes one small table. Use a practice database, or
an account that is allowed to create tables there. Do not use a production
database or its `dba` account for this tutorial. In Steps 2 and 3, replace the
lab URL `cubrid+pycubrid://dba@localhost:33000/testdb` with
`cubrid+pycubrid://USER:PASSWORD@HOST:PORT/DATABASE` filled in with your
values, then continue with Step 1. Keep real passwords out of files you share
or commit.

### Option B: I need a disposable local database

This starts a throwaway CUBRID 11.4 server with a database named `testdb` in
Docker. It needs [Docker](https://docs.docker.com/get-started/get-docker/)
and a shell such as bash. The commands were verified on Linux on x86_64
(amd64); the `cubrid/cubrid:11.4` image is published for amd64 only, so other
architectures (for example Apple silicon) and Windows are unverified.

```bash
docker run -d --name sqlalchemy-cubrid-quickstart -e CUBRID_DB=testdb -p 127.0.0.1:33000:33000 cubrid/cubrid:11.4
ready=no; for i in $(seq 36); do if docker exec sqlalchemy-cubrid-quickstart csql -u dba testdb -c "SELECT 1" >/dev/null 2>&1; then ready=yes; break; fi; sleep 5; done; if [ "$ready" = yes ]; then echo "CUBRID is ready"; else echo "CUBRID did not answer within 3 minutes; see: docker logs sqlalchemy-cubrid-quickstart"; fi
```

`127.0.0.1:` publishes the port on this computer only, so no other machine can
connect to the lab. The second command waits up to three minutes for the
database to answer (it usually takes well under a minute) and prints
`CUBRID is ready`. If it prints `CUBRID did not answer within 3 minutes`
instead, `docker logs sqlalchemy-cubrid-quickstart` shows why; if `docker run`
itself failed, for example because port 33000 is already in use, fix that
first, remove the container with `docker rm -f -v sqlalchemy-cubrid-quickstart`
and start again. The lab uses the `dba` account with an empty password. That
is only acceptable for this local, disposable container: never use an empty
password on a server other people can reach.

When you are done with the whole tutorial, remove the lab with
`docker rm -f -v sqlalchemy-cubrid-quickstart`. The image keeps its database in
an anonymous Docker volume that belongs to this container; `-v` deletes that
volume too, and with it `testdb`. Without `-v` the container goes but the volume
stays behind (`docker volume ls` lists it).

---

## Step 1: Install sqlalchemy-cubrid in a virtual environment

A virtual environment keeps this project's packages separate from the rest of
your system. First check that `python3 --version` prints 3.11 or later; if it
prints an older version, use a newer interpreter by name (for example
`python3.12`) in the first command. pip installs only the releases that
support your Python, so an old interpreter gets old packages. Then run these
commands in an empty folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "sqlalchemy-cubrid[pycubrid]"
python -c "import sqlalchemy, sqlalchemy_cubrid, pycubrid; print(sqlalchemy.__version__, sqlalchemy_cubrid.__version__, pycubrid.__version__)"
```

The `[pycubrid]` part installs the recommended pure-Python driver together with
the dialect. The last command prints the three installed versions, for example
`2.1.4 1.11.0 1.13.0`. Run every `python` command below in this same terminal,
with the virtual environment active.

---

## Step 2: Run your first query

Create a file named `first_query.py` in the same folder:

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

If you see an error instead, go to [If the first connection fails](#if-the-first-connection-fails).

---

## Step 3: Save a row and read it back

This step needs the URL that worked in Step 2. Create `first_saved_row.py` with
the same URL:

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

A **transaction** groups changes so that they become permanent together. With
`engine.begin()`, the block commits when it finishes and rolls back if it
raises an error; `rollback()` throws away everything since the transaction
began. `:id` and `:note` are bound parameters: always pass values this way
instead of pasting them into the SQL text yourself. Run the file:

```bash
python first_saved_row.py
```

The rolled-back row is gone, and a separate connection sees the saved row:

```text
Rows seen by a new connection: [(1, 'my first saved row')]
```

Running the file a second time, or again after it was interrupted, stops at
the first statement with `Class dba.sqlalchemy_quickstart_notes already exists`
(the owner name, here `dba`, is your user). The table from the earlier run is
still there; run the cleanup below and then run `first_saved_row.py` again.

### Clean up

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
`Nothing to clean up: sqlalchemy_quickstart_notes does not exist.` when there
is nothing left to remove. If you used the Docker lab, you can also remove the
whole lab with `docker rm -f -v sqlalchemy-cubrid-quickstart`.

---

## If the first connection fails

These are the messages printed for each mistake against the CUBRID 11.4 lab
with SQLAlchemy 2.1.4, sqlalchemy-cubrid 1.11.0 and pycubrid 1.13.0 (the last
line of the traceback). SQLAlchemy wraps the driver's error, which is shown in
parentheses:

| Message | What it means | What to check |
|---|---|---|
| `ModuleNotFoundError: No module named 'pycubrid'` | The driver is not installed in this Python. | Install with the `[pycubrid]` extra as in Step 1, activate the virtual environment and run `python`, not a system `python3`. |
| `NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:cubrid.pycubird` | The URL names a dialect or driver that does not exist (here a typo). | The URL starts with exactly `cubrid+pycubrid://`. |
| `OperationalError: (pycubrid.exceptions.OperationalError) failed to connect to CUBRID broker` | Nothing answered at that host and port. | The server is running (for the lab: `docker ps` lists `sqlalchemy-cubrid-quickstart`), the host and port in the URL are right, and no firewall blocks the port. |
| `DatabaseError: (pycubrid.exceptions.DatabaseError) Failed to connect to database server, 'nosuchdb', ...` | The broker answered, but there is no running database with that name. | The database name at the end of the URL; ask the administrator whether that database is started. |
| `OperationalError: (pycubrid.exceptions.OperationalError) User "nobody" is invalid. ...` | The user does not exist in that database. | The user name in the URL. |
| `OperationalError: (pycubrid.exceptions.OperationalError) Incorrect or missing password. ...` | The user exists, but the password is wrong. | The password in the URL (`user:password@...`). |

Leaving out the port (`cubrid+pycubrid://dba@localhost/testdb`) uses the
default `33000`. Fix the value instead of working around it: do not switch to a
production `dba` account, and do not turn off TLS certificate checks to make an
error go away. A password containing `@`, `:` or `/` must be percent-encoded in
the URL; see SQLAlchemy's
[escaping special characters](https://docs.sqlalchemy.org/en/20/core/engines.html#escaping-special-characters-such-as-signs-in-passwords).
More cases are in [Troubleshooting](TROUBLESHOOTING.md).

---

## Next steps

You ran SQL through SQLAlchemy **Core**, which works with SQL statements and
tables directly. The **ORM** maps Python classes to tables instead, so you work
with objects; it builds on the same engine and connection ideas.

- [README Usage](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/README.md#quick-start): short Core, ORM and async examples.
- [ORM Cookbook](ORM_COOKBOOK.md): models, relationships and common ORM patterns.
- [Connection Guide](CONNECTION.md): every URL form, connection options and the async `cubrid+aiopycubrid://` driver.
- [Driver Compatibility](DRIVER_COMPAT.md): the supported CUBRIDdb C-extension driver, built from source, and what differs between drivers.
- [Alembic Migrations](ALEMBIC.md), [Type Mapping](TYPES.md) and [Feature Support](FEATURE_SUPPORT.md), including CUBRID's limits such as no `RETURNING` clause.
