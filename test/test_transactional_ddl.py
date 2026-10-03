# test/test_transactional_ddl.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""CUBRID DDL is transactional (#503).

With client autocommit off, CUBRID runs DDL inside the current transaction:
``ROLLBACK`` undoes it and it never commits earlier DML.  Client autocommit
(``CCI_DEFAULT_AUTOCOMMIT``, which the dialect turns off on every connection)
is the only auto-commit behaviour.  These tests prove that on the server the
CI job points at, through both drivers:

* the raw DBAPI drivers (pycubrid and CUBRIDdb) roll back every DDL statement
  below, and a pending INSERT is not committed by a following CREATE TABLE;
* SQLAlchemy's ``metadata.create_all()`` rolls back with the connection;
* Alembic, now that ``CubridImpl.transactional_ddl`` is ``True``, runs the
  whole upgrade in one transaction: a failing multi-revision upgrade leaves no
  partial schema and no version row, while ``transaction_per_migration=True``
  keeps each revision atomic on its own;
* offline ``--sql`` output (no ``BEGIN;``, ``COMMIT;`` per transaction) runs
  in ``csql --no-auto-commit --no-single-line``, and a failing script exits
  non-zero and keeps nothing after the last ``COMMIT;``.  Set ``CUBRID_CSQL`` to a csql command prefix to run that check,
  e.g. ``docker exec -i <container> csql -u dba testdb``.

A driver that cannot connect (e.g. CUBRIDdb not built) skips its cases
locally.  The CI steps set ``CUBRID_REQUIRE_TRANSACTIONAL_DDL=1``, which turns
every such skip (no URL, driver missing, server unreachable, no ``CUBRID_CSQL``)
into a failure, so the lane cannot pass with every case skipped.
"""

from __future__ import annotations

import importlib.util
import io
import os
import shlex
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, NoReturn

import pytest
import sqlalchemy as sa

pytestmark = pytest.mark.integration

_PREFIX = "tddl503_"
_REQUIRE_ENV = "CUBRID_REQUIRE_TRANSACTIONAL_DDL"
_DRIVERS = ["pycubrid", "CUBRIDdb"]


def _unavailable(reason: str) -> NoReturn:
    """Skip locally; fail in the required CI lane (``CUBRID_REQUIRE_TRANSACTIONAL_DDL=1``)."""
    if os.environ.get(_REQUIRE_ENV) == "1":
        pytest.fail(f"{_REQUIRE_ENV}=1 but {reason}", pytrace=False)
    pytest.skip(reason)


def _url() -> sa.engine.URL:
    url = os.environ.get("CUBRID_TEST_URL")
    if not url:
        _unavailable("CUBRID_TEST_URL not set")
    return sa.make_url(url)


def _sa_url(driver: str) -> sa.engine.URL:
    return _url().set(drivername="cubrid+pycubrid" if driver == "pycubrid" else "cubrid")


def _raw_connect(driver: str) -> Any:
    """Open a raw DBAPI connection with client autocommit off."""
    url = _url()
    host, port = url.host or "localhost", url.port or 33000
    user, password = url.username or "dba", url.password or ""
    try:
        if driver == "pycubrid":
            import pycubrid

            conn = pycubrid.connect(
                host=host, port=port, database=url.database, user=user, password=password
            )
            conn.autocommit = False
            return conn
        else:
            import CUBRIDdb

            conn = CUBRIDdb.connect(f"CUBRID:{host}:{port}:{url.database}:::", user, password)
            conn.set_autocommit(False)
            return conn
    except Exception as exc:  # driver not installed / not built / unreachable
        _unavailable(f"{driver} cannot connect: {type(exc).__name__}: {exc}")
    raise AssertionError("unreachable")  # every branch above returns or raises


def _q(conn: Any, sql: str) -> list[Any] | None:
    cur = conn.cursor()
    try:
        cur.execute(sql)
        try:
            return list(cur.fetchall())
        except Exception:  # statement returns no result set
            return None
    finally:
        cur.close()


def _scalar(conn: Any, sql: str) -> Any:
    rows = _q(conn, sql)
    assert rows
    return rows[0][0]


def _class_exists(conn: Any, name: str) -> bool:
    return _scalar(conn, f"SELECT COUNT(*) FROM db_class WHERE class_name = '{name}'") == 1


def _columns(conn: Any, table: str) -> list[str]:
    rows = _q(
        conn,
        f"SELECT attr_name FROM db_attribute WHERE class_name = '{table}' ORDER BY def_order",
    )
    return [r[0] for r in rows or []]


def _index_exists(conn: Any, name: str) -> bool:
    return _scalar(conn, f"SELECT COUNT(*) FROM db_index WHERE index_name = '{name}'") == 1


def _serial_exists(conn: Any, name: str) -> bool:
    return _scalar(conn, f"SELECT COUNT(*) FROM db_serial WHERE name = '{name}'") == 1


def _row_count(conn: Any, table: str) -> int:
    return int(_scalar(conn, f"SELECT COUNT(*) FROM {table}"))


_T = f"{_PREFIX}t"
_T2 = f"{_PREFIX}t2"
_V = f"{_PREFIX}v"
_S = f"{_PREFIX}s"
_IX = f"{_PREFIX}ix"


def _drop_objects(conn: Any) -> None:
    for sql in (
        f"DROP VIEW IF EXISTS {_V}",
        f"DROP TABLE IF EXISTS {_T}",
        f"DROP TABLE IF EXISTS {_T2}",
        f"DROP SERIAL IF EXISTS {_S}",
    ):
        _q(conn, sql)
    conn.commit()


@pytest.fixture(params=_DRIVERS)
def raw_conn(request: pytest.FixtureRequest) -> Iterator[Any]:
    conn = _raw_connect(request.param)
    try:
        _drop_objects(conn)
        # One committed row in a committed table: the baseline every case
        # must return to after ROLLBACK.
        _q(conn, f"CREATE TABLE {_T} (id INT, x INT)")
        _q(conn, f"INSERT INTO {_T} VALUES (1, 1)")
        conn.commit()
        yield conn
    finally:
        conn.rollback()
        _drop_objects(conn)
        conn.close()


# (statement, "applied" probe).  Each probe is True once the statement's
# effect is visible, so a case checks that the DDL really ran in the
# transaction and that ROLLBACK then undid it.
_DDL_CASES: dict[str, tuple[str, Callable[[Any], bool]]] = {
    "create_table": (f"CREATE TABLE {_T2} (id INT)", lambda c: _class_exists(c, _T2)),
    "alter_add_column": (
        f"ALTER TABLE {_T} ADD COLUMN y INT",
        lambda c: "y" in _columns(c, _T),
    ),
    "alter_drop_column": (
        f"ALTER TABLE {_T} DROP COLUMN x",
        lambda c: "x" not in _columns(c, _T),
    ),
    "drop_table": (f"DROP TABLE {_T}", lambda c: not _class_exists(c, _T)),
    "truncate": (f"TRUNCATE TABLE {_T}", lambda c: _row_count(c, _T) == 0),
    "create_index": (f"CREATE INDEX {_IX} ON {_T} (id)", lambda c: _index_exists(c, _IX)),
    "create_index_online": (
        f"CREATE INDEX {_IX} ON {_T} (id) WITH ONLINE",
        lambda c: _index_exists(c, _IX),
    ),
    "create_index_online_parallel": (
        f"CREATE INDEX {_IX} ON {_T} (id) WITH ONLINE PARALLEL 2",
        lambda c: _index_exists(c, _IX),
    ),
    "create_view": (f"CREATE VIEW {_V} AS SELECT id FROM {_T}", lambda c: _class_exists(c, _V)),
    "create_serial": (f"CREATE SERIAL {_S}", lambda c: _serial_exists(c, _S)),
    "rename_table": (
        f"RENAME TABLE {_T} TO {_T2}",
        lambda c: _class_exists(c, _T2) and not _class_exists(c, _T),
    ),
}


def _assert_baseline(conn: Any) -> None:
    assert _class_exists(conn, _T)
    assert not _class_exists(conn, _T2)
    assert not _class_exists(conn, _V)
    assert not _index_exists(conn, _IX)
    assert not _serial_exists(conn, _S)
    assert _columns(conn, _T) == ["id", "x"]
    assert _row_count(conn, _T) == 1


@pytest.mark.parametrize("case", list(_DDL_CASES))
def test_rollback_undoes_ddl(raw_conn: Any, case: str) -> None:
    statement, applied = _DDL_CASES[case]

    _q(raw_conn, statement)
    assert applied(raw_conn), f"{statement!r} had no visible effect inside the transaction"

    raw_conn.rollback()
    assert not applied(raw_conn), f"ROLLBACK did not undo {statement!r}"
    _assert_baseline(raw_conn)


def test_ddl_does_not_commit_pending_dml(raw_conn: Any) -> None:
    """A CREATE TABLE after an uncommitted INSERT does not commit the INSERT."""
    _q(raw_conn, f"INSERT INTO {_T} VALUES (2, 2)")
    _q(raw_conn, f"CREATE TABLE {_T2} (id INT)")
    assert _row_count(raw_conn, _T) == 2

    raw_conn.rollback()
    _assert_baseline(raw_conn)


def test_ddl_and_dml_commit_together(raw_conn: Any) -> None:
    _q(raw_conn, f"CREATE TABLE {_T2} (id INT)")
    _q(raw_conn, f"INSERT INTO {_T2} VALUES (1)")
    raw_conn.commit()

    assert _class_exists(raw_conn, _T2)
    assert _row_count(raw_conn, _T2) == 1


def _connectable_engine(driver: str) -> sa.engine.Engine:
    if importlib.util.find_spec(driver) is None:  # not installed / not built
        _unavailable(f"{driver} is not installed")
    eng = sa.create_engine(_sa_url(driver))
    try:
        with eng.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
    except Exception as exc:
        eng.dispose()
        _unavailable(f"{driver} cannot connect: {type(exc).__name__}: {exc}")
    return eng


@pytest.fixture(params=_DRIVERS)
def engine(request: pytest.FixtureRequest) -> Iterator[sa.engine.Engine]:
    eng = _connectable_engine(request.param)
    yield eng
    eng.dispose()


def test_sqlalchemy_create_all_rolls_back(engine: sa.engine.Engine) -> None:
    md = sa.MetaData()
    sa.Table(f"{_PREFIX}sa_a", md, sa.Column("id", sa.Integer, primary_key=True))
    sa.Table(
        f"{_PREFIX}sa_b",
        md,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("a_id", sa.Integer, sa.ForeignKey(f"{_PREFIX}sa_a.id")),
        sa.Index(f"{_PREFIX}sa_ix", "a_id"),
    )
    md.drop_all(engine)
    try:
        with engine.connect() as conn:
            md.create_all(conn)
            assert sa.inspect(conn).has_table(f"{_PREFIX}sa_b")
            conn.rollback()
        with engine.connect() as conn:
            insp = sa.inspect(conn)
            assert not insp.has_table(f"{_PREFIX}sa_a")
            assert not insp.has_table(f"{_PREFIX}sa_b")
    finally:
        md.drop_all(engine)


# ---------------------------------------------------------------------------
# Alembic
# ---------------------------------------------------------------------------

_A1 = f"{_PREFIX}al_one"
_A2 = f"{_PREFIX}al_two"
_VERSION_TABLE = f"{_PREFIX}alembic_version"

_ENV_PY = f"""
from alembic import context
from sqlalchemy import create_engine

config = context.config
url = config.get_main_option("sqlalchemy.url")
opts = dict(
    version_table="{_VERSION_TABLE}",
    transaction_per_migration=config.attributes.get("transaction_per_migration", False),
)

if context.is_offline_mode():
    context.configure(url=url, literal_binds=True, **opts)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, **opts)
            assert context.get_context().impl.transactional_ddl is True
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
"""

_R1 = f'''
import sqlalchemy as sa
from alembic import op

revision = "r1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "{_A1}",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(20)),
    )
    op.create_index("{_PREFIX}al_ix", "{_A1}", ["name"])


def downgrade():
    op.drop_table("{_A1}")
'''

_R2 = f'''
import sqlalchemy as sa
from alembic import context, op

revision = "r2"
down_revision = "r1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("{_A2}", sa.Column("id", sa.Integer, primary_key=True))
    op.add_column("{_A1}", sa.Column("x", sa.Integer))
    op.execute("INSERT INTO {_A1} (id, x) VALUES (1, 1)")
    if context.config.attributes.get("fail"):
        op.execute("ALTER TABLE {_PREFIX}does_not_exist ADD COLUMN y INT")


def downgrade():
    op.drop_table("{_A2}")
    op.drop_column("{_A1}", "x")
'''


def _alembic_config(
    tmp_path: Path, url: sa.engine.URL, output_buffer: io.StringIO | None = None
) -> Any:
    from alembic.config import Config

    project = tmp_path / "migrations"
    (project / "versions").mkdir(parents=True)
    (project / "env.py").write_text(_ENV_PY, encoding="utf-8")
    (project / "script.py.mako").write_text("", encoding="utf-8")
    (project / "versions" / "r1.py").write_text(_R1, encoding="utf-8")
    (project / "versions" / "r2.py").write_text(_R2, encoding="utf-8")

    cfg = Config(output_buffer=output_buffer)
    cfg.set_main_option("script_location", str(project))
    cfg.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False))
    return cfg


def _drop_alembic_objects(engine: sa.engine.Engine) -> None:
    md = sa.MetaData()
    with engine.begin() as conn:
        for name in (_A2, _A1, _VERSION_TABLE):
            sa.Table(name, md).drop(conn, checkfirst=True)


def _schema_state(engine: sa.engine.Engine) -> dict[str, Any]:
    with engine.connect() as conn:
        insp = sa.inspect(conn)
        state: dict[str, Any] = {
            "tables": sorted(t for t in insp.get_table_names() if t.startswith(_PREFIX + "al")),
            "al_one_columns": (
                [c["name"] for c in insp.get_columns(_A1)] if insp.has_table(_A1) else None
            ),
            "version": None,
        }
        if insp.has_table(_VERSION_TABLE):
            state["version"] = [
                r[0] for r in conn.execute(sa.text(f"SELECT version_num FROM {_VERSION_TABLE}"))
            ]
    return state


@pytest.fixture(params=_DRIVERS)
def alembic_engine(request: pytest.FixtureRequest) -> Iterator[sa.engine.Engine]:
    if importlib.util.find_spec("alembic") is None:
        _unavailable("alembic is not installed")
    import sqlalchemy_cubrid.alembic_impl  # noqa: F401

    eng = _connectable_engine(request.param)
    _drop_alembic_objects(eng)
    yield eng
    _drop_alembic_objects(eng)
    eng.dispose()


def test_alembic_failing_upgrade_is_atomic_by_default(
    tmp_path: Path, alembic_engine: sa.engine.Engine
) -> None:
    """r2 fails after r1 ran and r2 created a table, added a column and
    inserted a row: nothing survives, not even the version table."""
    from alembic import command

    cfg = _alembic_config(tmp_path, alembic_engine.url)
    cfg.attributes["fail"] = True

    with pytest.raises(sa.exc.DatabaseError):
        command.upgrade(cfg, "head")

    assert _schema_state(alembic_engine) == {
        "tables": [],
        "al_one_columns": None,
        "version": None,
    }


def test_alembic_transaction_per_migration_keeps_completed_revisions(
    tmp_path: Path, alembic_engine: sa.engine.Engine
) -> None:
    """With transaction_per_migration=True, r1 commits and r2 rolls back whole."""
    from alembic import command

    cfg = _alembic_config(tmp_path, alembic_engine.url)
    cfg.attributes["fail"] = True
    cfg.attributes["transaction_per_migration"] = True

    with pytest.raises(sa.exc.DatabaseError):
        command.upgrade(cfg, "head")

    assert _schema_state(alembic_engine) == {
        "tables": [_A1, _VERSION_TABLE],
        "al_one_columns": ["id", "name"],
        "version": ["r1"],
    }


@pytest.mark.parametrize("per_migration", [False, True])
def test_alembic_upgrade_and_downgrade_commit(
    tmp_path: Path, alembic_engine: sa.engine.Engine, per_migration: bool
) -> None:
    from alembic import command

    cfg = _alembic_config(tmp_path, alembic_engine.url)
    cfg.attributes["transaction_per_migration"] = per_migration

    command.upgrade(cfg, "head")
    assert _schema_state(alembic_engine) == {
        "tables": sorted([_A1, _A2, _VERSION_TABLE]),
        "al_one_columns": ["id", "name", "x"],
        "version": ["r2"],
    }

    command.downgrade(cfg, "base")
    assert _schema_state(alembic_engine) == {
        "tables": [_VERSION_TABLE],
        "al_one_columns": None,
        "version": [],
    }


def _offline_sql(tmp_path: Path, url: sa.engine.URL, per_migration: bool, fail: bool) -> str:
    from alembic import command

    buf = io.StringIO()
    cfg = _alembic_config(tmp_path, url, output_buffer=buf)
    cfg.attributes["transaction_per_migration"] = per_migration
    cfg.attributes["fail"] = fail
    command.upgrade(cfg, "head", sql=True)
    return buf.getvalue()


def _run_csql(sql: str) -> subprocess.CompletedProcess[str]:
    """Run an offline script the way the docs tell users to."""
    csql = os.environ.get("CUBRID_CSQL")
    if not csql:
        _unavailable("CUBRID_CSQL not set (e.g. 'docker exec -i <container> csql -u dba testdb')")
    # --no-auto-commit makes the script's COMMIT; the only commit points.
    # --no-single-line makes csql stop at the first failing statement and exit
    # 1; in the default single-line mode it reports the error, runs the rest of
    # the script (including COMMIT;) and exits 0.
    return subprocess.run(  # noqa: S603 - command comes from the test environment
        [*shlex.split(csql), "--no-auto-commit", "--no-single-line", "-i", "/dev/stdin"],
        input=sql,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.parametrize("per_migration", [False, True])
def test_alembic_offline_sql_runs_in_csql(
    tmp_path: Path, alembic_engine: sa.engine.Engine, per_migration: bool
) -> None:
    """Feed ``upgrade head --sql`` output to csql and check the resulting schema."""
    sql = _offline_sql(tmp_path, alembic_engine.url, per_migration, fail=False)
    result = _run_csql(sql)

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "ERROR" not in output, output
    assert _schema_state(alembic_engine) == {
        "tables": sorted([_A1, _A2, _VERSION_TABLE]),
        "al_one_columns": ["id", "name", "x"],
        "version": ["r2"],
    }


@pytest.mark.parametrize("per_migration", [False, True])
def test_alembic_failing_offline_sql_rolls_back_in_csql(
    tmp_path: Path, alembic_engine: sa.engine.Engine, per_migration: bool
) -> None:
    """A failing statement stops csql with a non-zero exit and nothing past the
    last COMMIT; is kept: the whole upgrade by default, only r2 per migration."""
    sql = _offline_sql(tmp_path, alembic_engine.url, per_migration, fail=True)
    assert f"{_PREFIX}does_not_exist" in sql
    result = _run_csql(sql)

    assert result.returncode != 0, result.stdout + result.stderr
    if per_migration:
        expected: dict[str, Any] = {
            "tables": [_A1, _VERSION_TABLE],
            "al_one_columns": ["id", "name"],
            "version": ["r1"],
        }
    else:
        expected = {"tables": [], "al_one_columns": None, "version": None}
    assert _schema_state(alembic_engine) == expected
