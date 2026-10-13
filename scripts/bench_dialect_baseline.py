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
* ``concurrency`` (with ``--concurrency``, #830 follow-up) N workers, each on its
                  own connection, start together: ``--concurrent-ops`` one-row
                  SELECTs by primary key per worker (raw, Core, ORM), then
                  ``--concurrent-writes`` single-row Core UPDATEs, each committed,
                  on the worker's own rows. Reports the p50 latency and the throughput
                  from the first counted operation's start to the last one's end
                  (connection setup and cleanup excluded).

Drivers: ``cubrid+pycubrid://`` runs everything; ``cubrid://`` (CUBRIDdb) runs
the same workloads with a raw CUBRIDdb connection and without the two
``prepared=True`` variants, which only pycubrid has (the raw CUBRIDdb
``rowcount`` after ``executemany()`` is the last row's, so only the table
check applies to it);
``cubrid+aiopycubrid://`` runs the async counterparts (``pycubrid.aio`` raw,
``AsyncConnection`` Core, ``AsyncSession`` ORM, ``asyncio`` tasks for
concurrency) of ``select_pk``, ``fetch_all``, ``batch`` (no prepared variants)
and ``concurrency``; reflection is skipped there (it runs the same synchronous
dialect code through ``run_sync``).

Usage:
    python scripts/bench_dialect_baseline.py \\
        --dsn cubrid+pycubrid://dba@localhost:33000/testdb --trials 5 \\
        --output baseline.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
import statistics
import sys
import threading
import time
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pycubrid
import pycubrid.aio
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
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
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
    engine: Engine, prepared_engine: Engine | None, raw: Any, n: int, rounds: int, trial: int
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
            if prepared_engine is not None:  # pycubrid; CUBRIDdb reports the last row's count
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
        ("core_prepared_experiment", lambda: core_round(prepared_engine or engine)),
        ("orm", orm_round),
    ]
    if prepared_engine is None:
        variants = [v for v in variants if "prepared" not in v[0]]
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


# ----- concurrency -----------------------------------------------------------------------


Span = tuple[int, int]  # perf_counter_ns at the start and the end of one operation


def concurrency_result(spans: list[list[Span]]) -> dict[str, float]:
    """Throughput from the first counted operation's start to the last one's end."""
    flat = [s for worker in spans for s in worker]
    wall_ns = max(end for _, end in flat) - min(start for start, _ in flat)
    return {"ops_per_s": len(flat) / (wall_ns / 1e9), "p50_us": us([e - s for s, e in flat])}


def run_threads(n: int, work: Callable[[int, threading.Barrier], list[Span]]) -> dict:
    """Run ``work(i, barrier)`` in ``n`` threads; each opens its connection, then waits."""
    barrier = threading.Barrier(n + 1)
    times: list[list[Span]] = [[] for _ in range(n)]
    errors: list[Exception] = []

    def target(i: int) -> None:
        try:
            times[i] = work(i, barrier)
        except Exception as exc:  # reported after join
            errors.append(exc)
            barrier.abort()

    threads = [threading.Thread(target=target, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    try:
        barrier.wait()
    except threading.BrokenBarrierError:
        pass  # a worker failed before the start; its error is raised below
    for t in threads:
        t.join()
    if errors:
        raise errors[0]
    return concurrency_result(times)


def bench_concurrency(
    engine: Engine, raw_connect: Callable[[], Any], args: argparse.Namespace, n: int, trial: int
) -> dict:
    rows, ops = args.rows, args.concurrent_ops
    stmt = select(ITEMS.c.id, ITEMS.c.name, ITEMS.c.amount).where(ITEMS.c.id == bindparam("k"))
    orm_stmt = select(Item).where(Item.id == bindparam("k"))
    upd = update(ITEMS).where(ITEMS.c.id == bindparam("k")).values(amount=bindparam("a"))

    def keys(i: int) -> list[int]:
        return [((i * ops + j) * 7919) % rows for j in range(ops)]

    def raw_select(i: int, barrier: threading.Barrier) -> list[Span]:
        raw = raw_connect()
        try:
            cur = raw.cursor()
            barrier.wait()
            times = []
            for k in keys(i):
                t0 = pc()
                cur.execute(
                    "SELECT id, name, amount FROM bench_dialect_baseline WHERE id = ?", (k,)
                )
                row = cur.fetchone()
                times.append((t0, pc()))
                check(row[0] == k, "raw concurrent select returned the wrong row")
            cur.close()
            raw.commit()
            return times
        finally:
            raw.close()

    def core_select(i: int, barrier: threading.Barrier) -> list[Span]:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM db_root")).all()  # check out before the start
            barrier.wait()
            times = []
            for k in keys(i):
                t0 = pc()
                row = conn.execute(stmt, {"k": k}).first()
                times.append((t0, pc()))
                check(row is not None and row.id == k, "Core concurrent select wrong row")
            return times

    def orm_select(i: int, barrier: threading.Barrier) -> list[Span]:
        with Session(engine) as session:
            session.execute(text("SELECT 1 FROM db_root")).all()
            barrier.wait()
            times = []
            for k in keys(i):
                t0 = pc()
                obj = session.execute(orm_stmt, {"k": k}).scalar_one()
                times.append((t0, pc()))
                check(obj.id == k, "ORM concurrent select returned the wrong row")
                session.expunge_all()
            return times

    def core_update_commit(i: int, barrier: threading.Barrier) -> list[Span]:
        own = list(range(i, rows, n))  # rows no other worker touches
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM db_root")).all()
            conn.commit()
            barrier.wait()
            times = []
            for j in range(args.concurrent_writes):
                k = own[j % len(own)]
                t0 = pc()
                result = conn.execute(upd, {"k": k, "a": j})
                conn.commit()
                times.append((t0, pc()))
                check(result.rowcount == 1, f"concurrent UPDATE rowcount {result.rowcount}")
            return times

    variants: list[tuple[str, Callable[[int, threading.Barrier], list[Span]]]] = [
        ("raw_select_pk", raw_select),
        ("core_select_pk", core_select),
        ("orm_select_pk", orm_select),
        ("core_update_commit", core_update_commit),
    ]
    out: dict[str, dict[str, float]] = {}
    for name, fn in rotate(variants, trial):
        run_threads(n, fn)  # warm-up pass, not recorded
        out[name] = run_threads(n, fn)
    return out


# ----- async (cubrid+aiopycubrid://) -----------------------------------------------------


async def async_reset(engine: AsyncEngine, rows: int) -> None:
    async with engine.connect() as conn:
        await conn.execute(delete(ITEMS))
        if rows:
            await conn.execute(
                insert(ITEMS), [{"id": i, "name": f"n{i}", "amount": i} for i in range(rows)]
            )
        await conn.commit()


async def async_verify_batch(engine: AsyncEngine, stage: str, n: int) -> None:
    async with engine.connect() as conn:
        await conn.run_sync(verify_batch, stage, n)


async def async_select_pk(
    engine: AsyncEngine, raw: Any, rows: int, iterations: int, trial: int
) -> dict:
    keys = [(i * 7919) % rows for i in range(iterations)]
    stmt = select(ITEMS.c.id, ITEMS.c.name, ITEMS.c.amount).where(ITEMS.c.id == bindparam("k"))
    orm_stmt = select(Item).where(Item.id == bindparam("k"))

    async def run_raw() -> list[int]:
        cur = raw.cursor()
        times = []
        for k in keys:
            t0 = pc()
            await cur.execute(
                "SELECT id, name, amount FROM bench_dialect_baseline WHERE id = ?", (k,)
            )
            row = await cur.fetchone()
            times.append(pc() - t0)
            check(row[0] == k, "async raw select_pk returned the wrong row")
        await cur.close()
        return times

    async def run_core(cache: bool) -> list[int]:
        async with engine.connect() as conn:
            if not cache:
                conn = await conn.execution_options(compiled_cache=None)
            times = []
            for k in keys:
                t0 = pc()
                row = (await conn.execute(stmt, {"k": k})).first()
                times.append(pc() - t0)
                check(row is not None and row.id == k, "async Core select_pk wrong row")
            return times

    async def run_orm() -> list[int]:
        async with AsyncSession(engine) as session:
            times = []
            for k in keys:
                t0 = pc()
                obj = (await session.execute(orm_stmt, {"k": k})).scalar_one()
                times.append(pc() - t0)
                check(obj.id == k, "async ORM select_pk returned the wrong row")
                session.expunge_all()
            return times

    variants: list[tuple[str, Callable[[], Any]]] = [
        ("raw", run_raw),
        ("core_cached", lambda: run_core(True)),
        ("core_uncached", lambda: run_core(False)),
        ("orm", run_orm),
    ]
    out: dict[str, float] = {}
    for name, fn in rotate(variants, trial):
        await fn()
        out[name] = us(await fn())
    return out


async def async_fetch_all(
    engine: AsyncEngine, raw: Any, rows: int, rounds: int, trial: int
) -> dict:
    core_stmt = select(ITEMS.c.id, ITEMS.c.name, ITEMS.c.amount)
    orm_stmt = select(Item)

    async def run_raw() -> list[int]:
        cur = raw.cursor()
        times = []
        for _ in range(rounds):
            t0 = pc()
            await cur.execute("SELECT id, name, amount FROM bench_dialect_baseline")
            got = await cur.fetchall()
            times.append(pc() - t0)
            check(len(got) == rows, "async raw fetch_all row count")
        await cur.close()
        return times

    async def run_core() -> list[int]:
        async with engine.connect() as conn:
            times = []
            for _ in range(rounds):
                t0 = pc()
                got = (await conn.execute(core_stmt)).all()
                times.append(pc() - t0)
                check(len(got) == rows, "async Core fetch_all row count")
            return times

    async def run_orm() -> list[int]:
        times = []
        for _ in range(rounds):
            async with AsyncSession(engine) as session:
                t0 = pc()
                got = (await session.scalars(orm_stmt)).all()
                times.append(pc() - t0)
                check(len(got) == rows, "async ORM fetch_all row count")
        return times

    variants: list[tuple[str, Callable[[], Any]]] = [
        ("raw", run_raw),
        ("core", run_core),
        ("orm", run_orm),
    ]
    out: dict[str, float] = {}
    for name, fn in rotate(variants, trial):
        await fn()
        out[name] = us(await fn())
    return out


async def async_batch(engine: AsyncEngine, raw: Any, n: int, rounds: int, trial: int) -> dict:
    tuples_ins = [(i, f"n{i}", i) for i in range(n)]
    tuples_upd = [(i + 1, i) for i in range(n)]
    tuples_del = [(i,) for i in range(n)]
    dicts_ins = [{"id": i, "name": f"n{i}", "amount": i} for i in range(n)]
    dicts_upd = [{"b_id": i, "b_amount": i + 1} for i in range(n)]
    dicts_del = [{"b_id": i} for i in range(n)]
    upd = update(ITEMS).where(ITEMS.c.id == bindparam("b_id")).values(amount=bindparam("b_amount"))
    dele = delete(ITEMS).where(ITEMS.c.id == bindparam("b_id"))

    async def raw_round() -> dict[str, int]:
        cur = raw.cursor()
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
            await cur.executemany(sql, params)
            await raw.commit()
            res[stage] = pc() - t0
            check(cur.rowcount == n, f"async raw {stage} rowcount {cur.rowcount}")
            await async_verify_batch(engine, stage, n)
        await cur.close()
        return res

    async def core_round() -> dict[str, int]:
        res = {}
        async with engine.connect() as conn:
            for stage, stmt, params in (
                ("insert", insert(ITEMS), dicts_ins),
                ("update", upd, dicts_upd),
                ("delete", dele, dicts_del),
            ):
                t0 = pc()
                result = await conn.execute(stmt, params)
                await conn.commit()
                res[stage] = pc() - t0
                if stage != "insert":
                    check(result.rowcount == n, f"async Core {stage} rowcount {result.rowcount}")
                await conn.run_sync(verify_batch, stage, n)
        return res

    async def orm_round() -> dict[str, int]:
        res = {}
        async with AsyncSession(engine) as session:
            t0 = pc()
            await session.execute(insert(Item), dicts_ins)
            await session.commit()
            res["insert"] = pc() - t0
            await async_verify_batch(engine, "insert", n)
            t0 = pc()
            await session.execute(update(Item), [{"id": i, "amount": i + 1} for i in range(n)])
            await session.commit()
            res["update"] = pc() - t0
            await async_verify_batch(engine, "update", n)
            objs = (await session.scalars(select(Item))).all()
            check(len(objs) == n, "async ORM load before DELETE")
            t0 = pc()
            for obj in objs:
                await session.delete(obj)
            await session.commit()
            res["delete"] = pc() - t0
            await async_verify_batch(engine, "delete", n)
        return res

    variants: list[tuple[str, Callable[[], Any]]] = [
        ("raw", raw_round),
        ("core", core_round),
        ("orm", orm_round),
    ]
    out: dict[str, dict[str, float]] = {}
    for name, fn in rotate(variants, trial):
        await async_reset(engine, 0)
        await fn()  # warm-up round
        samples: dict[str, list[int]] = {"insert": [], "update": [], "delete": []}
        for _ in range(rounds):
            for stage, ns in (await fn()).items():
                samples[stage].append(ns)
        out[name] = {stage: statistics.median(v) / 1e6 for stage, v in samples.items()}
    return out


async def run_tasks(n: int, work: Callable[[int, asyncio.Barrier], Any]) -> dict:
    """Run ``work(i, barrier)`` as ``n`` tasks; each opens its connection, then waits."""
    barrier = asyncio.Barrier(n + 1)
    tasks = [asyncio.create_task(work(i, barrier)) for i in range(n)]
    waiter = asyncio.create_task(barrier.wait())
    done, _ = await asyncio.wait([waiter, *tasks], return_when=asyncio.FIRST_COMPLETED)
    if waiter not in done:  # a task failed before the start
        await barrier.abort()
        await asyncio.gather(*tasks)
    return concurrency_result(list(await asyncio.gather(*tasks)))


async def async_concurrency(
    engine: AsyncEngine, raw_kw: dict[str, Any], args: argparse.Namespace, n: int, trial: int
) -> dict:
    rows, ops = args.rows, args.concurrent_ops
    stmt = select(ITEMS.c.id, ITEMS.c.name, ITEMS.c.amount).where(ITEMS.c.id == bindparam("k"))
    orm_stmt = select(Item).where(Item.id == bindparam("k"))
    upd = update(ITEMS).where(ITEMS.c.id == bindparam("k")).values(amount=bindparam("a"))

    def keys(i: int) -> list[int]:
        return [((i * ops + j) * 7919) % rows for j in range(ops)]

    async def raw_select(i: int, barrier: asyncio.Barrier) -> list[Span]:
        raw = await pycubrid.aio.connect(**raw_kw, autocommit=False)
        try:
            cur = raw.cursor()
            await barrier.wait()
            times = []
            for k in keys(i):
                t0 = pc()
                await cur.execute(
                    "SELECT id, name, amount FROM bench_dialect_baseline WHERE id = ?", (k,)
                )
                row = await cur.fetchone()
                times.append((t0, pc()))
                check(row[0] == k, "async raw concurrent select returned the wrong row")
            await cur.close()
            await raw.commit()
            return times
        finally:
            await raw.close()

    async def core_select(i: int, barrier: asyncio.Barrier) -> list[Span]:
        async with engine.connect() as conn:
            (await conn.execute(text("SELECT 1 FROM db_root"))).all()
            await barrier.wait()
            times = []
            for k in keys(i):
                t0 = pc()
                row = (await conn.execute(stmt, {"k": k})).first()
                times.append((t0, pc()))
                check(row is not None and row.id == k, "async Core concurrent select wrong row")
            return times

    async def orm_select(i: int, barrier: asyncio.Barrier) -> list[Span]:
        async with AsyncSession(engine) as session:
            (await session.execute(text("SELECT 1 FROM db_root"))).all()
            await barrier.wait()
            times = []
            for k in keys(i):
                t0 = pc()
                obj = (await session.execute(orm_stmt, {"k": k})).scalar_one()
                times.append((t0, pc()))
                check(obj.id == k, "async ORM concurrent select returned the wrong row")
                session.expunge_all()
            return times

    async def core_update_commit(i: int, barrier: asyncio.Barrier) -> list[Span]:
        own = list(range(i, rows, n))
        async with engine.connect() as conn:
            (await conn.execute(text("SELECT 1 FROM db_root"))).all()
            await conn.commit()
            await barrier.wait()
            times = []
            for j in range(args.concurrent_writes):
                k = own[j % len(own)]
                t0 = pc()
                result = await conn.execute(upd, {"k": k, "a": j})
                await conn.commit()
                times.append((t0, pc()))
                check(result.rowcount == 1, f"async concurrent UPDATE rowcount {result.rowcount}")
            return times

    variants: list[tuple[str, Callable[[int, asyncio.Barrier], Any]]] = [
        ("raw_select_pk", raw_select),
        ("core_select_pk", core_select),
        ("orm_select_pk", orm_select),
        ("core_update_commit", core_update_commit),
    ]
    out: dict[str, dict[str, float]] = {}
    for name, fn in rotate(variants, trial):
        await run_tasks(n, fn)
        out[name] = await run_tasks(n, fn)
    return out


# ----- driver ----------------------------------------------------------------------------


def prepared_executemany_engine(dsn: str) -> Engine:
    """Engine whose dialect passes ``prepared=True`` (benchmark experiment only)."""
    engine = create_engine(dsn)

    def do_executemany(cursor: Any, statement: str, parameters: Any, context: Any = None) -> None:
        cursor.executemany(statement, parameters, prepared=True)

    engine.dialect.do_executemany = do_executemany  # type: ignore[method-assign]
    return engine


def raw_kwargs(engine: Engine | AsyncEngine) -> dict[str, Any]:
    url = engine.url
    return {
        "host": url.host,
        "port": url.port,
        "database": url.database,
        "user": url.username or "dba",
        "password": url.password or "",
    }


def raw_connector(engine: Engine) -> Callable[[], Any]:
    """A raw DB-API connection factory for the engine's driver, autocommit off."""
    kw = raw_kwargs(engine)
    if engine.dialect.driver == "pycubrid":

        def connect_pycubrid() -> Any:
            raw = pycubrid.connect(**kw)
            raw.autocommit = False
            return raw

        return connect_pycubrid
    import CUBRIDdb

    def connect_cubriddb() -> Any:
        dsn = f"CUBRID:{kw['host'] or 'localhost'}:{kw['port'] or 33000}:{kw['database']}:::"
        raw = CUBRIDdb.connect(dsn, kw["user"], kw["password"])
        raw.set_autocommit(False)
        return raw

    return connect_cubriddb


def environment(server: str, driver: str, pool: str, args: argparse.Namespace) -> dict[str, Any]:
    cpu = ""
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    env = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "cpu": cpu,
        "sqlalchemy": version("SQLAlchemy"),
        "pycubrid": version("pycubrid"),
        "sqlalchemy_cubrid": version("sqlalchemy-cubrid"),
        "source_sha": args.source_sha,
        "cubrid_server": server,
        "driver": driver,
        "pool": pool,
        "args": {k: v for k, v in vars(args).items() if k not in ("dsn", "output")},
    }
    if driver == "cubrid":
        env["cubrid_python"] = version("cubrid_python")
    return env


def run_sync(args: argparse.Namespace) -> dict[str, Any]:
    pool_size = max([5, *args.concurrency])
    engine = create_engine(args.dsn, pool_size=pool_size)
    check(
        engine.dialect.driver in ("pycubrid", "cubrid"),
        "this baseline needs cubrid+pycubrid://, cubrid:// or cubrid+aiopycubrid://",
    )
    prepared_engine = None
    if engine.dialect.driver == "pycubrid":
        prepared_engine = prepared_executemany_engine(args.dsn)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS bench_dialect_baseline"))
    Base.metadata.create_all(engine)
    raw_connect = raw_connector(engine)
    raw = raw_connect()
    with engine.connect() as conn:
        server = conn.execute(text("SELECT version()")).scalar()
    env = environment(str(server), engine.dialect.driver, type(engine.pool).__name__, args)
    report: dict[str, Any] = {"environment": env, "trials": []}
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
            if args.concurrency:
                result["concurrency"] = {
                    str(n): bench_concurrency(engine, raw_connect, args, n, trial)
                    for n in args.concurrency
                }
            result["batch_ms"] = bench_batch(
                engine, prepared_engine, raw, args.batch, args.batch_rounds, trial
            )
            report["trials"].append(result)
    finally:
        raw.close()
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS bench_dialect_baseline"))
        engine.dispose()
        if prepared_engine is not None:
            prepared_engine.dispose()
    return report


async def run_async(args: argparse.Namespace) -> dict[str, Any]:
    pool_size = max([5, *args.concurrency])
    engine = create_async_engine(args.dsn, pool_size=pool_size)
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS bench_dialect_baseline"))
        await conn.run_sync(Base.metadata.create_all)
    raw_kw = raw_kwargs(engine)
    raw = await pycubrid.aio.connect(**raw_kw, autocommit=False)
    async with engine.connect() as conn:
        server = (await conn.execute(text("SELECT version()"))).scalar()
    env = environment(str(server), engine.dialect.driver, type(engine.pool).__name__, args)
    report: dict[str, Any] = {"environment": env, "trials": []}
    try:
        for trial in range(args.trials):
            print(f"trial {trial + 1}/{args.trials}", file=sys.stderr, flush=True)
            await async_reset(engine, args.rows)
            result = {
                "select_pk_us": await async_select_pk(
                    engine, raw, args.rows, args.iterations, trial
                ),
                "fetch_all_us": await async_fetch_all(
                    engine, raw, args.rows, args.fetch_rounds, trial
                ),
            }
            await raw.commit()
            if args.concurrency:
                result["concurrency"] = {
                    str(n): await async_concurrency(engine, raw_kw, args, n, trial)
                    for n in args.concurrency
                }
            result["batch_ms"] = await async_batch(
                engine, raw, args.batch, args.batch_rounds, trial
            )
            report["trials"].append(result)
    finally:
        await raw.close()
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS bench_dialect_baseline"))
        await engine.dispose()
    return report


def aggregate(trials: list[dict[str, Any]]) -> dict[str, Any]:
    def walk(values: list[Any]) -> Any:
        if isinstance(values[0], dict):
            return {k: walk([v[k] for v in values]) for k in values[0]}
        return summary(values)

    first = trials[0]
    agg: dict[str, Any] = {}
    for section in ("select_pk_us", "fetch_all_us", "batch_ms", "concurrency"):
        if section in first:
            agg[section] = walk([t[section] for t in trials])
    if "reflect" in first:
        agg["reflect_ms"] = {
            k: summary([t["reflect"][k]["ms"] for t in trials]) for k in first["reflect"]
        }
        agg["reflect_sql_statements"] = {
            k: first["reflect"][k]["sql_statements"] for k in first["reflect"]
        }
    return agg


def show(data: dict[str, Any], prefix: str = "") -> None:
    for k, v in data.items():
        name = f"{prefix} {k}".strip()
        if isinstance(v, dict) and "median" in v:
            print(f"  {name:<40} median {v['median']:.3f}  [{v['min']:.3f}..{v['max']:.3f}]")
        elif isinstance(v, dict):
            show(v, name)
        else:
            print(f"  {name:<40} {v}")


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
    ap.add_argument(
        "--concurrency",
        type=lambda s: [int(x) for x in s.split(",") if x],
        default=[],
        help="comma-separated worker counts for the concurrency workload (default: skip it)",
    )
    ap.add_argument("--concurrent-ops", type=int, default=500, help="SELECTs per worker")
    ap.add_argument("--concurrent-writes", type=int, default=50, help="UPDATEs per worker")
    ap.add_argument("--source-sha", default="unknown", help="sqlalchemy-cubrid commit measured")
    ap.add_argument("--output", type=Path, default=Path("bench_dialect_baseline.json"))
    args = ap.parse_args()

    if args.dsn.startswith("cubrid+aiopycubrid://"):
        report = asyncio.run(run_async(args))
    else:
        report = run_sync(args)
    report["summary"] = aggregate(report["trials"])
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for section, data in report["summary"].items():
        print(f"== {section}")
        show(data)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
