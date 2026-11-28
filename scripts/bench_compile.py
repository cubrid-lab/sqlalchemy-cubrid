#!/usr/bin/env python3
"""Microbenchmark for CUBRID dialect query compilation.

Measures compile time for:
- Simple SELECT with LIMIT/OFFSET
- INSERT ... ON DUPLICATE KEY UPDATE (the known hot path)
- Simple INSERT
- SELECT with FOR UPDATE

Usage:
    python scripts/bench_compile.py [--iterations N]
"""

from __future__ import annotations

import argparse
import time

from sqlalchemy import Column, Integer, MetaData, String, Table, create_mock_engine, insert, select


def positive_int(value: str) -> int:
    """Return *value* as an integer greater than zero for ``argparse``."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def create_test_objects():
    engine = create_mock_engine("cubrid://", executor=lambda *a, **kw: None)
    metadata = MetaData()
    users = Table(
        "users",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(100)),
        Column("email", String(200)),
        Column("age", Integer),
    )
    return engine, users


def bench_select_limit(engine, users, n: int) -> float:
    stmt = select(users).where(users.c.age > 25).limit(100).offset(50)
    dialect = engine.dialect
    start = time.perf_counter()
    for _ in range(n):
        stmt.compile(dialect=dialect)
    return time.perf_counter() - start


def bench_on_duplicate_key_update(engine, users, n: int) -> float:
    from sqlalchemy_cubrid import insert as cubrid_insert

    stmt = (
        cubrid_insert(users)
        .values(name="Alice", email="alice@example.com", age=30)
        .on_duplicate_key_update(name="Alice Updated", age=31)
    )
    dialect = engine.dialect
    start = time.perf_counter()
    for _ in range(n):
        stmt.compile(dialect=dialect)
    return time.perf_counter() - start


def bench_select_for_update(engine, users, n: int) -> float:
    stmt = select(users).where(users.c.id == 1).with_for_update()
    dialect = engine.dialect
    start = time.perf_counter()
    for _ in range(n):
        stmt.compile(dialect=dialect)
    return time.perf_counter() - start


def bench_simple_insert(engine, users, n: int) -> float:
    stmt = insert(users).values(name="Bob", email="bob@example.com", age=25)
    dialect = engine.dialect
    start = time.perf_counter()
    for _ in range(n):
        stmt.compile(dialect=dialect)
    return time.perf_counter() - start


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compiler microbenchmark")
    parser.add_argument("--iterations", "-n", type=positive_int, default=10000)
    args = parser.parse_args(argv)
    n = args.iterations

    engine, users = create_test_objects()

    iteration_word = "iteration" if n == 1 else "iterations"
    print(
    f"Benchmarking CUBRID dialect compilation "
    f"({n} {iteration_word} each)\n"
)
    print(f"{'Benchmark':<35} {'Total (ms)':>12} {'Per-op (µs)':>12}")
    print("-" * 62)

    benchmarks = [
        ("SELECT + LIMIT/OFFSET", bench_select_limit),
        ("INSERT (simple)", bench_simple_insert),
        ("INSERT ON DUPLICATE KEY UPDATE", bench_on_duplicate_key_update),
        ("SELECT FOR UPDATE", bench_select_for_update),
    ]

    for name, func in benchmarks:
        elapsed = func(engine, users, n)
        total_ms = elapsed * 1000
        per_op_us = (elapsed / n) * 1_000_000
        print(f"{name:<35} {total_ms:>10.1f}ms {per_op_us:>10.1f}µs")

    print(f"\n{'=' * 62}")
    print("Done. Compare results before/after optimization attempts.")


if __name__ == "__main__":
    main()
