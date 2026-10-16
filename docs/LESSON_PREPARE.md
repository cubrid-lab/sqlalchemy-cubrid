# Lesson 1: Prepare CUBRID and Python

**Goal:** a CUBRID database you can reach, and a Python virtual environment
with the dialect and the driver. You will see `CUBRID is ready` (for the local
lab) and the three installed package versions.

**Prerequisites:** Python 3.11 or later. For the local lab, also Docker and a
shell such as bash. This is the first lesson of
[Your First SQLAlchemy Connection to CUBRID](QUICKSTART.md); the course page
explains how SQLAlchemy, the dialect, the driver and the server fit together.

---

## Choose a database

Pick the option that matches your situation.

### Option A: I already have a CUBRID database

Ask its administrator (or look in your own setup) for these five values:

- **host**: the machine that runs CUBRID, for example `db.example.com` or `localhost`;
- **port**: the CUBRID broker port, the entry point that accepts connections (the default is `33000`);
- **database**: the database name, for example `testdb`;
- **user** and **password**: an account for that database.

Lesson 3 creates and later removes one small table. Use a practice database, or
an account that is allowed to create tables there. Do not use a production
database or its `dba` account for this tutorial. In Lessons 2 and 3, replace the
lab URL `cubrid+pycubrid://dba@localhost:33000/testdb` with
`cubrid+pycubrid://USER:PASSWORD@HOST:PORT/DATABASE` filled in with your
values, then continue with
[Install sqlalchemy-cubrid](#install-sqlalchemy-cubrid-in-a-virtual-environment). Keep real passwords out of files you share
or commit.

### Option B: I need a disposable local database

This starts a throwaway CUBRID 11.4 server with a database named `testdb` in
Docker. It needs [Docker](https://docs.docker.com/get-started/get-docker/)
and a shell such as bash. The commands were verified on Linux on x86_64
(amd64); the `cubrid/cubrid:11.4` image is published for amd64 only, so other
architectures (for example Apple silicon) and Windows are unverified.

```bash
docker run -d --name sqlalchemy-cubrid-quickstart -e CUBRID_DB=testdb \
  -p 127.0.0.1:33000:33000 cubrid/cubrid:11.4
ready=no
for i in $(seq 36); do
  if docker exec sqlalchemy-cubrid-quickstart csql -u dba testdb -c "SELECT 1" >/dev/null 2>&1; then
    ready=yes; break
  fi
  sleep 5
done
if [ "$ready" = yes ]; then echo "CUBRID is ready"
else echo "CUBRID did not answer within 3 minutes; see: docker logs sqlalchemy-cubrid-quickstart"; fi
```

`127.0.0.1:` publishes the port on this computer only, so no other machine can
connect to the lab. The loop after `docker run` waits up to three minutes for the
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

## Install sqlalchemy-cubrid in a virtual environment

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
`2.1.4 1.11.0 1.13.0`: SQLAlchemy, sqlalchemy-cubrid and pycubrid. Those are the
published PyPI releases this guide was last run with, on 2026-10-15; a newer
release prints higher numbers. Run every `python` command of the next lessons in
this same terminal, with the virtual environment active.

---

## Next

[Lesson 2: Run your first query](LESSON_FIRST_QUERY.md).
