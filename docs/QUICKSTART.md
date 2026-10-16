# Your First SQLAlchemy Connection to CUBRID

Four pieces work together when you use SQLAlchemy with CUBRID:

- **SQLAlchemy** is the Python library you write your code against;
- **sqlalchemy-cubrid** is the *dialect*: it teaches SQLAlchemy CUBRID's flavour of SQL;
- **pycubrid** is the *driver*: it carries the SQL over the network to the database;
- the **CUBRID server** is the database itself, a separate program that must already be running somewhere.

Installing the Python packages does not install CUBRID or create a database.
This course takes you from an empty folder to a first query and a first saved
row on the recommended path: the `sqlalchemy-cubrid[pycubrid]` package and the
synchronous `cubrid+pycubrid://` URL. Each lesson has one goal and ends with a
result you can see:

1. [Prepare CUBRID and Python](LESSON_PREPARE.md): a database you can reach and
   a virtual environment with the dialect and driver.
2. [Run your first query](LESSON_FIRST_QUERY.md): `SELECT 1 + 1` prints `2`.
3. [Save a row and read it back](LESSON_SAVE_ROW.md): a separate connection reads
   your committed row.
4. [Undo changes with a rollback](LESSON_TRANSACTIONS.md): a rolled-back row
   never appears.
5. [Clean up](LESSON_FINISH.md): remove only what the course created.

If a lesson fails, [If the first connection fails](#if-the-first-connection-fails)
below lists the real error messages and what to check.

Other drivers, the ORM, async code and Alembic come [afterwards](#next-steps).

---

## If the first connection fails

These are the messages printed for each mistake against the CUBRID 11.4 lab
with SQLAlchemy 2.1.4, sqlalchemy-cubrid 1.11.0 and pycubrid 1.13.0 (the last
line of the traceback). SQLAlchemy wraps the driver's error, which is shown in
parentheses:

| Message | What it means | What to check |
|---|---|---|
| `ModuleNotFoundError: No module named 'pycubrid'` | The driver is not installed in this Python. | Install with the `[pycubrid]` extra as in [Lesson 1](LESSON_PREPARE.md#install-sqlalchemy-cubrid-in-a-virtual-environment), activate the virtual environment and run `python`, not a system `python3`. |
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

---

## Before you start

Moved to [Lesson 1: Prepare CUBRID and Python](LESSON_PREPARE.md).

### Option A: I already have a CUBRID database

Moved to [Lesson 1, Option A](LESSON_PREPARE.md#option-a-i-already-have-a-cubrid-database).

### Option B: I need a disposable local database

Moved to [Lesson 1, Option B](LESSON_PREPARE.md#option-b-i-need-a-disposable-local-database).

---

## Step 1: Install sqlalchemy-cubrid in a virtual environment

Moved to [Lesson 1](LESSON_PREPARE.md#install-sqlalchemy-cubrid-in-a-virtual-environment).

---

## Step 2: Run your first query

Moved to [Lesson 2: Run your first query](LESSON_FIRST_QUERY.md).

---

## Step 3: Save a row and read it back

Moved to [Lesson 3: Save a row and read it back](LESSON_SAVE_ROW.md) and
[Lesson 4: Undo changes with a rollback](LESSON_TRANSACTIONS.md).

### Clean up

Moved to [Lesson 5: Clean up](LESSON_FINISH.md).
