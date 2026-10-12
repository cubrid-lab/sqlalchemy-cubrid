from __future__ import annotations

import argparse
import cProfile
import json
import pstats
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, cast

from sqlalchemy import DateTime, Integer, String, Table, create_engine, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


DEFAULT_DSN = "cubrid+pycubrid://dba@localhost:33000/benchdb"
DEFAULT_OUTPUT_PATH = Path("profile_orm_report.json")
MAX_RESULTS = 5
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DIALECT_MODULES = {
    "compiler.py": str(REPO_ROOT / "sqlalchemy_cubrid" / "compiler.py"),
    "dialect.py": str(REPO_ROOT / "sqlalchemy_cubrid" / "dialect.py"),
    "types.py": str(REPO_ROOT / "sqlalchemy_cubrid" / "types.py"),
    "base.py": str(REPO_ROOT / "sqlalchemy_cubrid" / "base.py"),
}
SQLALCHEMY_FRAGMENT = "/site-packages/sqlalchemy/"
PYCUBRID_FRAGMENT = "/site-packages/pycubrid/"
StatsEntryKey = tuple[str, int, str]
StatsEntryValue = tuple[int, int, float, float, object]
StatsTable = dict[StatsEntryKey, StatsEntryValue]


class Base(DeclarativeBase):
    pass


class BenchUser(Base):
    __tablename__ = "bench_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(200))
    age: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime)


SessionFactory = sessionmaker[Session]


@dataclass
class Hotspot:
    function: str
    calls: int
    primitive_calls: int
    self_time_s: float
    cumulative_time_s: float


def _top_dialect_hotspots(stats: pstats.Stats) -> list[Hotspot]:
    hotspots: list[Hotspot] = []
    stats_table = cast(StatsTable, getattr(stats, "stats"))
    for (filename, lineno, funcname), entry in stats_table.items():
        primitive_calls, total_calls, self_time, cumulative_time, _callers = entry
        normalized = _normalized_path(filename)
        for label, expected_path in DIALECT_MODULES.items():
            if normalized == expected_path:
                hotspots.append(
                    Hotspot(
                        function=f"{label}:{lineno}:{funcname}",
                        calls=total_calls,
                        primitive_calls=primitive_calls,
                        self_time_s=self_time,
                        cumulative_time_s=cumulative_time,
                    )
                )
                break

    return sorted(
        hotspots,
        key=lambda hotspot: (hotspot.cumulative_time_s, hotspot.self_time_s),
        reverse=True,
    )[:MAX_RESULTS]


def _build_user(index: int, prefix: str) -> BenchUser:
    return BenchUser(
        name=f"{prefix}_{index:05d}",
        email=f"{prefix}_{index:05d}@example.com",
        age=20 + (index % 50),
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )


def _clear_users(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM bench_users"))


def _seed_users(session_factory: SessionFactory, engine: Engine, count: int, prefix: str) -> None:
    _clear_users(engine)
    with session_factory() as session:
        session.add_all(_build_user(index, prefix) for index in range(1, count + 1))
        session.commit()


def _run_single_row_crud(
    session_factory: SessionFactory,
    engine: Engine,
    loops: int,
) -> None:
    _clear_users(engine)
    for index in range(1, loops + 1):
        with session_factory() as session:
            user = _build_user(index, "crud")
            session.add(user)
            session.commit()
            user_id = user.id

        with session_factory() as session:
            selected = session.get(BenchUser, user_id)
            assert selected is not None
            selected.age += 1
            session.commit()

        with session_factory() as session:
            selected = session.get(BenchUser, user_id)
            assert selected is not None
            session.delete(selected)
            session.commit()


def _run_bulk_insert(
    session_factory: SessionFactory,
    engine: Engine,
    count: int,
    rounds: int,
) -> None:
    for round_index in range(rounds):
        _clear_users(engine)
        with session_factory() as session:
            session.add_all(
                _build_user(index, f"bulk_{count}_{round_index}") for index in range(1, count + 1)
            )
            session.commit()


def _run_query_builder_select(
    session_factory: SessionFactory, rounds: int, expected_rows: int
) -> None:
    for _ in range(rounds):
        with session_factory() as session:
            rows = session.execute(select(BenchUser).order_by(BenchUser.id)).scalars().all()
            assert len(rows) == expected_rows


def _run_raw_sql_select(session_factory: SessionFactory, rounds: int, expected_rows: int) -> None:
    for _ in range(rounds):
        with session_factory() as session:
            rows = session.execute(
                text("SELECT id, name, email, age, created_at FROM bench_users ORDER BY id")
            ).all()
            assert len(rows) == expected_rows


def _run_compile_workload(engine: Engine, loops: int) -> None:
    from sqlalchemy import delete, update

    from sqlalchemy_cubrid.dml import insert

    bench_users_table: Table = Base.metadata.tables[BenchUser.__tablename__]
    select_stmt = select(BenchUser).order_by(BenchUser.id).limit(25).offset(5)
    insert_stmt = insert(bench_users_table).values(
        id=1,
        name="compile_user",
        email="compile_user@example.com",
        age=30,
        created_at=datetime(2026, 1, 1),
    )
    odku_stmt = insert_stmt.on_duplicate_key_update(
        name=insert_stmt.inserted.name,
        email=insert_stmt.inserted.email,
    )
    update_stmt = update(BenchUser).where(BenchUser.id == 1).values(age=31)
    delete_stmt = delete(BenchUser).where(BenchUser.id == 1)

    for _ in range(loops):
        _ = select_stmt.compile(dialect=engine.dialect)
        _ = insert_stmt.compile(dialect=engine.dialect)
        _ = odku_stmt.compile(dialect=engine.dialect)
        _ = update_stmt.compile(dialect=engine.dialect)
        _ = delete_stmt.compile(dialect=engine.dialect)


def _normalized_path(filename: str) -> str:
    if filename.startswith("<"):
        return filename
    try:
        return str(Path(filename).resolve())
    except OSError:
        return filename


def _measure_operation(fn: Any, *args: Any, **kwargs: Any) -> float:
    started_at = perf_counter()
    fn(*args, **kwargs)
    return perf_counter() - started_at


def _build_report(
    stats: pstats.Stats,
    total_wall_time_s: float,
    orm_select_time_s: float,
    raw_select_time_s: float,
    top_dialect_hotspots: list[Hotspot],
) -> dict[str, Any]:
    stats_table = cast(StatsTable, getattr(stats, "stats"))
    total_self_time = sum(entry[2] for entry in stats_table.values())
    module_self_time: dict[str, float] = defaultdict(float)
    sqlalchemy_core_self_time = 0.0
    pycubrid_self_time = 0.0

    for (filename, lineno, funcname), entry in stats_table.items():
        primitive_calls, total_calls, self_time, cumulative_time, _callers = entry
        normalized = _normalized_path(filename)

        matched_module = None
        for label, expected_path in DIALECT_MODULES.items():
            if normalized == expected_path:
                module_self_time[label] += self_time
                matched_module = label
                break

        if matched_module is not None:
            continue

        if SQLALCHEMY_FRAGMENT in normalized:
            sqlalchemy_core_self_time += self_time
        elif PYCUBRID_FRAGMENT in normalized:
            pycubrid_self_time += self_time

    module_report = {}
    for label in DIALECT_MODULES:
        value = module_self_time[label]
        module_report[label] = {
            "self_time_s": value,
            "pct_of_total_request_time": (value / total_wall_time_s * 100)
            if total_wall_time_s
            else 0.0,
            "pct_of_profiled_self_time": (value / total_self_time * 100)
            if total_self_time
            else 0.0,
        }

    orm_select_overhead_s = max(0.0, orm_select_time_s - raw_select_time_s)
    dialect_total_self_time = sum(module_self_time.values())

    return {
        "total_request_time_s": total_wall_time_s,
        "profiled_self_time_s": total_self_time,
        "sqlalchemy_core": {
            "self_time_s": sqlalchemy_core_self_time,
            "pct_of_total_request_time": (
                sqlalchemy_core_self_time / total_wall_time_s * 100 if total_wall_time_s else 0.0
            ),
        },
        "pycubrid": {
            "self_time_s": pycubrid_self_time,
            "pct_of_total_request_time": (pycubrid_self_time / total_wall_time_s * 100)
            if total_wall_time_s
            else 0.0,
        },
        "dialect_modules": module_report,
        "dialect_total": {
            "self_time_s": dialect_total_self_time,
            "pct_of_total_request_time": (
                dialect_total_self_time / total_wall_time_s * 100 if total_wall_time_s else 0.0
            ),
        },
        "orm_overhead": {
            "select_overhead_s": orm_select_overhead_s,
            "select_overhead_pct_of_orm_select": (
                orm_select_overhead_s / orm_select_time_s * 100 if orm_select_time_s else 0.0
            ),
            "select_overhead_pct_of_total_request_time": (
                orm_select_overhead_s / total_wall_time_s * 100 if total_wall_time_s else 0.0
            ),
            "orm_select_time_s": orm_select_time_s,
            "raw_select_time_s": raw_select_time_s,
        },
        "top_dialect_hotspots": [asdict(hotspot) for hotspot in top_dialect_hotspots],
    }


def _print_report(report: dict[str, Any]) -> None:
    print("== ORM profile summary ==")
    print(f"Total request time: {report['total_request_time_s']:.6f}s")
    print(f"Dialect self time: {report['dialect_total']['self_time_s']:.6f}s")
    print(
        "Dialect overhead: "
        f"{report['dialect_total']['pct_of_total_request_time']:.4f}% of total request time"
    )
    print(
        "SQLAlchemy core self time: "
        f"{report['sqlalchemy_core']['self_time_s']:.6f}s "
        f"({report['sqlalchemy_core']['pct_of_total_request_time']:.4f}% of total)"
    )
    print(
        "pycubrid self time: "
        f"{report['pycubrid']['self_time_s']:.6f}s "
        f"({report['pycubrid']['pct_of_total_request_time']:.4f}% of total)"
    )
    print("\nDialect module breakdown:")
    for module_name, data in report["dialect_modules"].items():
        print(
            f"- {module_name}: {data['self_time_s']:.6f}s "
            f"({data['pct_of_total_request_time']:.4f}% of total request time)"
        )
    print("\nORM select overhead:")
    print(
        f"- raw SQL select: {report['orm_overhead']['raw_select_time_s']:.6f}s\n"
        f"- ORM select: {report['orm_overhead']['orm_select_time_s']:.6f}s\n"
        f"- overhead: {report['orm_overhead']['select_overhead_s']:.6f}s "
        f"({report['orm_overhead']['select_overhead_pct_of_orm_select']:.2f}% of ORM select, "
        f"{report['orm_overhead']['select_overhead_pct_of_total_request_time']:.2f}% of total request time)"
    )
    print("\nTop dialect hotspots:")
    for hotspot in report["top_dialect_hotspots"]:
        print(
            f"- {hotspot['function']} | calls={hotspot['primitive_calls']}/{hotspot['calls']} "
            f"| self={hotspot['self_time_s']:.6f}s | cumulative={hotspot['cumulative_time_s']:.6f}s"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--dsn", default=DEFAULT_DSN, help="SQLAlchemy DSN for CUBRID")
    _ = parser.add_argument(
        "--crud-loops",
        type=int,
        default=20,
        help="Number of single-row CRUD iterations",
    )
    _ = parser.add_argument(
        "--bulk-count",
        type=int,
        default=300,
        help="Number of rows per bulk insert round",
    )
    _ = parser.add_argument(
        "--bulk-rounds",
        type=int,
        default=3,
        help="Number of bulk insert rounds",
    )
    _ = parser.add_argument(
        "--select-rounds",
        type=int,
        default=10,
        help="Number of ORM/raw select rounds",
    )
    _ = parser.add_argument(
        "--select-seed-count",
        type=int,
        default=300,
        help="Number of rows to seed for select profiling",
    )
    _ = parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Optional JSON report path",
    )
    _ = parser.add_argument(
        "--compile-loops",
        type=int,
        default=250,
        help="Number of statement compilation loops for hotspot identification",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = create_engine(args.dsn)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    try:
        profiler = cProfile.Profile()

        def workload() -> None:
            _run_single_row_crud(session_factory, engine, args.crud_loops)
            _run_bulk_insert(session_factory, engine, args.bulk_count, args.bulk_rounds)

        total_started_at = perf_counter()
        profiler.enable()
        workload()
        profiler.disable()
        total_wall_time_s = perf_counter() - total_started_at

        _seed_users(session_factory, engine, args.select_seed_count, "orm_profile")
        orm_select_time_s = _measure_operation(
            _run_query_builder_select,
            session_factory,
            args.select_rounds,
            args.select_seed_count,
        )
        raw_select_time_s = _measure_operation(
            _run_raw_sql_select,
            session_factory,
            args.select_rounds,
            args.select_seed_count,
        )

        compile_profiler = cProfile.Profile()
        compile_profiler.runcall(_run_compile_workload, engine, args.compile_loops)

        stats = pstats.Stats(profiler)
        report = _build_report(
            stats,
            total_wall_time_s,
            orm_select_time_s,
            raw_select_time_s,
            _top_dialect_hotspots(pstats.Stats(compile_profiler)),
        )
        _print_report(report)

        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote JSON report to {args.output}")
    finally:
        _clear_users(engine)
        Base.metadata.drop_all(engine)
        engine.dispose()


if __name__ == "__main__":
    main()
