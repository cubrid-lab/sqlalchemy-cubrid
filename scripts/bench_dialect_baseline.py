#!/usr/bin/env python3
"""Same-CUBRID baseline: raw pycubrid vs SQLAlchemy Core vs ORM (#830).

Covers what ``scripts/bench_compile.py`` (offline compilation),
``scripts/profile_orm.py`` (one cProfile pass) and the cubrid-benchmark
``orm-overhead`` workers (single-row CRUD) do not: the statement cache on and
off, fetch/materialization, ``executemany`` and bulk INSERT/UPDATE/DELETE, and
reflection, all on one table and one connection, repeated over trials, with
each result checked.

Workloads (per trial; the variant order rotates from trial to trial):

* ``select_pk``   one-row SELECT by primary key: raw cursor, Core with the
                  statement cache, Core with ``compiled_cache=None``, ORM.
* ``fetch_all``   SELECT of every seeded row: raw ``fetchall()``, Core ``.all()``,
                  ORM ``scalars().all()`` in a new ``Session``.
* ``batch``       INSERT, UPDATE and DELETE of ``--batch`` rows, each timed with
                  its commit: raw ``executemany()``, raw
                  ``executemany(prepared=True)``, Core (INSERT goes through
                  insertmanyvalues, UPDATE/DELETE through ``do_executemany``),
                  Core with an experimental ``prepared=True`` ``do_executemany``
                  (benchmark only, never the dialect default) and ORM (bulk
                  INSERT, bulk UPDATE by primary key, unit-of-work DELETE).
* ``reflect``     a fresh ``Inspector``'s column/PK/FK/index/unique-constraint
                  calls and ``MetaData.reflect()`` for the table, with the number
                  of SQL statements each sends.

Usage:
    python scripts/bench_dialect_baseline.py \\
        --dsn cubrid+pycubrid://dba@localhost:33000/testdb --trials 5 \\
        --output baseline.json
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pycubrid
from sqlalchemy import (
    Integer,
    MetaData,
    String,
    Table,
    bindparam,
    create_engine,
    delete,
    event,
    func,
    insert,
    inspect,
    select,
    text,
    update,
)
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

TABLE = "bench_dialect_baseline"
pc = time.perf_counter_ns


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = TABLE

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(64))
    amount: Mapped[int] = mapped_column(Integer)


ITEMS: Table = Item.__table__  # type: ignore[assignment]


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def summary(values: list[float]) -> dict[str, Any]:
    if len(values) > 1:
        q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
    else:
        q1 = q3 = values[0]
    return {
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "q1": q1,
        "q3": q3,
        "trials": values,
    }


def us(ns: list[int]) -> float:
    return statistics.median(ns) / 1000.0


def rotate(items: list[Any], trial: int) -> list[Any]:
    k = trial % len(items)
    return items[k:] + items[:k]


def reset(conn: Connection, rows: int) -> None:
    conn.execute(delete(ITEMS))
    if rows:
        conn.execute(insert(ITEMS), [{"id": i, "name": f"n{i}", "amount": i} for i in range(rows)])
    conn.commit()


# ----- select_pk / fetch_all -------------------------------------------------------------


def bench_select_pk(engine: Engine, raw: Any, rows: int, iterations: int, trial: int) -> dict:
    keys = [(i * 7919) % rows for i in range(iterations)]
    stmt = select(ITEMS.c.id, ITEMS.c.name, ITEMS.c.amount).where(ITEMS.c.id == bindparam("k"))
    orm_stmt = select(Item).where(Item.id == bindparam("k"))
    out: dict[str, float] = {}

    def run_raw() -> list[int]:
        cur = raw.cursor()
        times = []
        for k in keys:
            t0 = pc()
            cur.execute("SELECT id, name, amount FROM bench_dialect_baseline WHERE id = ?", (k,))
            row = cur.fetchone()
            times.append(pc() - t0)
            check(row[0] == k, "raw select_pk returned the wrong row")
        cur.close()
        return times

    def run_core(cache: bool) -> list[int]:
        with engine.connect() as conn:
            if not cache:
                conn = conn.execution_options(compiled_cache=None)
            times = []
            for k in keys:
                t0 = pc()
                row = conn.execute(stmt, {"k": k}).first()
                times.append(pc() - t0)
                check(row is not None and row.id == k, "Core select_pk returned the wrong row")
            return times

    def run_orm() -> list[int]:
        with Session(engine) as session:
            times = []
            for k in keys:
                t0 = pc()
                obj = session.execute(orm_stmt, {"k": k}).scalar_one()
                times.append(pc() - t0)
                check(obj.id == k, "ORM select_pk returned the wrong row")
                session.expunge_all()
            return times

    variants: list[tuple[str, Callable[[], list[int]]]] = [
        ("raw", run_raw),
        ("core_cached", lambda: run_core(True)),
        ("core_uncached", lambda: run_core(False)),
        ("orm", run_orm),
    ]
    for name, fn in rotate(variants, trial):
        fn()  # warm-up pass, not recorded
        out[name] = us(fn())
    return out


def bench_fetch_all(engine: Engine, raw: Any, rows: int, rounds: int, trial: int) -> dict:
    core_stmt = select(ITEMS.c.id, ITEMS.c.name, ITEMS.c.amount)
    orm_stmt = select(Item)
    out: dict[str, float] = {}

    def run_raw() -> list[int]:
        cur = raw.cursor()
        times = []
        for _ in range(rounds):
            t0 = pc()
            cur.execute("SELECT id, name, amount FROM bench_dialect_baseline")
            got = cur.fetchall()
            times.append(pc() - t0)
            check(len(got) == rows, "raw fetch_all row count")
        cur.close()
        return times

    def run_core() -> list[int]:
        with engine.connect() as conn:
            times = []
            for _ in range(rounds):
                t0 = pc()
                got = conn.execute(core_stmt).all()
                times.append(pc() - t0)
                check(len(got) == rows, "Core fetch_all row count")
            return times

    def run_orm() -> list[int]:
        times = []
        for _ in range(rounds):
            with Session(engine) as session:
                t0 = pc()
                got = session.scalars(orm_stmt).all()
                times.append(pc() - t0)
                check(len(got) == rows, "ORM fetch_all row count")
        return times

    variants = [("raw", run_raw), ("core", run_core), ("orm", run_orm)]
    for name, fn in rotate(variants, trial):
        fn()
        out[name] = us(fn())
    return out


# ----- batch -----------------------------------------------------------------------------


def verify_batch(conn: Connection, stage: str, n: int) -> None:
    count, total = conn.execute(select(func.count(), func.sum(ITEMS.c.amount))).one()
    if stage == "insert":
        check(count == n and total == sum(range(n)), f"after INSERT: {count} rows, sum {total}")
    elif stage == "update":
        check(count == n and total == sum(range(n)) + n, f"after UPDATE: {count}, sum {total}")
    else:
        check(count == 0, f"after DELETE: {count} rows left")


def bench_batch(
    engine: Engine, prepared_engine: Engine, raw: Any, n: int, rounds: int, trial: int
) -> dict:
    tuples_ins = [(i, f"n{i}", i) for i in range(n)]
    tuples_upd = [(i + 1, i) for i in range(n)]
    tuples_del = [(i,) for i in range(n)]
    dicts_ins = [{"id": i, "name": f"n{i}", "amount": i} for i in range(n)]
    dicts_upd = [{"b_id": i, "b_amount": i + 1} for i in range(n)]
    dicts_del = [{"b_id": i} for i in range(n)]
    upd = update(ITEMS).where(ITEMS.c.id == bindparam("b_id")).values(amount=bindparam("b_amount"))
    dele = delete(ITEMS).where(ITEMS.c.id == bindparam("b_id"))

    def raw_round(prepared: bool) -> dict[str, int]:
        cur = raw.cursor()
        kw = {"prepared": True} if prepared else {}
        res = {}
        for stage, sql, params in (
            (
                "insert",
                "INSERT INTO bench_dialect_baseline (id, name, amount) VALUES (?, ?, ?)",
                tuples_ins,
            ),
            ("update", "UPDATE bench_dialect_baseline SET amount = ? WHERE id = ?", tuples_upd),
            ("delete", "DELETE FROM bench_dialect_baseline WHERE id = ?", tuples_del),
        ):
            t0 = pc()
            cur.executemany(sql, params, **kw)
            raw.commit()
            res[stage] = pc() - t0
            check(cur.rowcount == n, f"raw {stage} rowcount {cur.rowcount}")
            with engine.connect() as conn:
                verify_batch(conn, stage, n)
        cur.close()
        return res

    def core_round(eng: Engine) -> dict[str, int]:
        res = {}
        with eng.connect() as conn:
            for stage, stmt, params in (
                ("insert", insert(ITEMS), dicts_ins),
                ("update", upd, dicts_upd),
                ("delete", dele, dicts_del),
            ):
                t0 = pc()
                result = conn.execute(stmt, params)
                conn.commit()
                res[stage] = pc() - t0
                if stage != "insert":
                    check(result.rowcount == n, f"Core {stage} rowcount {result.rowcount}")
                verify_batch(conn, stage, n)
        return res

    def orm_round() -> dict[str, int]:
        res = {}
        with Session(engine) as session:
            t0 = pc()
            session.execute(insert(Item), dicts_ins)
            session.commit()
            res["insert"] = pc() - t0
            verify_batch(session.connection(), "insert", n)
            session.commit()
            t0 = pc()
            session.execute(update(Item), [{"id": i, "amount": i + 1} for i in range(n)])
            session.commit()
            res["update"] = pc() - t0
            verify_batch(session.connection(), "update", n)
            objs = session.scalars(select(Item)).all()
            check(len(objs) == n, "ORM load before DELETE")
            t0 = pc()
            for obj in objs:
                session.delete(obj)
            session.commit()
            res["delete"] = pc() - t0
            verify_batch(session.connection(), "delete", n)
            session.commit()
        return res

    variants: list[tuple[str, Callable[[], dict[str, int]]]] = [
        ("raw", lambda: raw_round(False)),
        ("raw_prepared", lambda: raw_round(True)),
        ("core", lambda: core_round(engine)),
        ("core_prepared_experiment", lambda: core_round(prepared_engine)),
        ("orm", orm_round),
    ]
    out: dict[str, dict[str, float]] = {}
    for name, fn in rotate(variants, trial):
        with engine.connect() as conn:
            reset(conn, 0)
        fn()  # warm-up round
        samples: dict[str, list[int]] = {"insert": [], "update": [], "delete": []}
        for _ in range(rounds):
            for stage, ns in fn().items():
                samples[stage].append(ns)
        out[name] = {stage: statistics.median(v) / 1e6 for stage, v in samples.items()}
    return out


# ----- reflection ------------------------------------------------------------------------


def bench_reflect(engine: Engine, rounds: int) -> dict:
    statements = 0

    @event.listens_for(engine, "before_cursor_execute")
    def _count(*_args: Any) -> None:
        nonlocal statements
        statements += 1

    out: dict[str, Any] = {}
    calls: dict[str, Callable[[Connection], Any]] = {
        "inspector_table": lambda c: (
            (insp := inspect(c)).get_columns(TABLE),
            insp.get_pk_constraint(TABLE),
            insp.get_foreign_keys(TABLE),
            insp.get_indexes(TABLE),
            insp.get_unique_constraints(TABLE),
        ),
        "metadata_reflect": lambda c: MetaData().reflect(bind=c, only=[TABLE]),
    }
    try:
        with engine.connect() as conn:
            for name, fn in calls.items():
                fn(conn)
                times = []
                for _ in range(rounds):
                    statements = 0
                    t0 = pc()
                    fn(conn)
                    times.append(pc() - t0)
                out[name] = {"ms": statistics.median(times) / 1e6, "sql_statements": statements}
            cols = [c["name"] for c in inspect(conn).get_columns(TABLE)]
            check(cols == ["id", "name", "amount"], f"reflected columns {cols}")
    finally:
        event.remove(engine, "before_cursor_execute", _count)
    return out


# ----- driver ----------------------------------------------------------------------------


def prepared_executemany_engine(dsn: str) -> Engine:
    """Engine whose dialect passes ``prepared=True`` (benchmark experiment only)."""
    engine = create_engine(dsn)

    def do_executemany(cursor: Any, statement: str, parameters: Any, context: Any = None) -> None:
        cursor.executemany(statement, parameters, prepared=True)

    engine.dialect.do_executemany = do_executemany  # type: ignore[method-assign]
    return engine


def environment(engine: Engine, args: argparse.Namespace) -> dict[str, Any]:
    cpu = ""
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    with engine.connect() as conn:
        server = conn.execute(text("SELECT version()")).scalar()
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "cpu": cpu,
        "sqlalchemy": version("SQLAlchemy"),
        "pycubrid": version("pycubrid"),
        "sqlalchemy_cubrid": version("sqlalchemy-cubrid"),
        "source_sha": args.source_sha,
        "cubrid_server": server,
        "driver": engine.dialect.driver,
        "pool": type(engine.pool).__name__,
        "args": {k: v for k, v in vars(args).items() if k not in ("dsn", "output")},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dsn", default="cubrid+pycubrid://dba@localhost:33000/testdb")
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--rows", type=int, default=1000, help="seeded rows for select/fetch")
    ap.add_argument("--iterations", type=int, default=1000, help="select_pk calls per variant")
    ap.add_argument("--fetch-rounds", type=int, default=30)
    ap.add_argument("--batch", type=int, default=1000, help="rows per batch statement")
    ap.add_argument("--batch-rounds", type=int, default=5)
    ap.add_argument("--reflect-rounds", type=int, default=20)
    ap.add_argument("--source-sha", default="unknown", help="sqlalchemy-cubrid commit measured")
    ap.add_argument("--output", type=Path, default=Path("bench_dialect_baseline.json"))
    args = ap.parse_args()

    engine = create_engine(args.dsn)
    check(engine.dialect.driver == "pycubrid", "this baseline needs cubrid+pycubrid://")
    prepared_engine = prepared_executemany_engine(args.dsn)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS bench_dialect_baseline"))
    Base.metadata.create_all(engine)
    url = engine.url
    raw = pycubrid.connect(
        host=url.host,
        port=url.port,
        database=url.database,
        user=url.username or "dba",
        password=url.password or "",
    )
    raw.autocommit = False
    report: dict[str, Any] = {"environment": environment(engine, args), "trials": []}
    try:
        for trial in range(args.trials):
            print(f"trial {trial + 1}/{args.trials}", file=sys.stderr, flush=True)
            with engine.connect() as conn:
                reset(conn, args.rows)
            result = {
                "select_pk_us": bench_select_pk(engine, raw, args.rows, args.iterations, trial),
                "fetch_all_us": bench_fetch_all(engine, raw, args.rows, args.fetch_rounds, trial),
                "reflect": bench_reflect(engine, args.reflect_rounds),
            }
            raw.commit()
            result["batch_ms"] = bench_batch(
                engine, prepared_engine, raw, args.batch, args.batch_rounds, trial
            )
            report["trials"].append(result)
    finally:
        raw.close()
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS bench_dialect_baseline"))
        engine.dispose()
        prepared_engine.dispose()

    agg: dict[str, Any] = {}
    first = report["trials"][0]
    for section in ("select_pk_us", "fetch_all_us"):
        agg[section] = {
            v: summary([t[section][v] for t in report["trials"]]) for v in first[section]
        }
    agg["batch_ms"] = {
        v: {
            s: summary([t["batch_ms"][v][s] for t in report["trials"]])
            for s in first["batch_ms"][v]
        }
        for v in first["batch_ms"]
    }
    agg["reflect_ms"] = {
        k: summary([t["reflect"][k]["ms"] for t in report["trials"]]) for k in first["reflect"]
    }
    agg["reflect_sql_statements"] = {
        k: first["reflect"][k]["sql_statements"] for k in first["reflect"]
    }
    report["summary"] = agg
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for section, data in agg.items():
        print(f"== {section}")
        for k, v in data.items():
            if isinstance(v, dict) and "median" in v:
                print(f"  {k:<26} median {v['median']:.3f}  [{v['min']:.3f}..{v['max']:.3f}]")
            elif isinstance(v, dict):
                for s, sv in v.items():
                    print(
                        f"  {k + ' ' + s:<34} median {sv['median']:.3f}  "
                        f"[{sv['min']:.3f}..{sv['max']:.3f}]"
                    )
            else:
                print(f"  {k:<26} {v}")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
