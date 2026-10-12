"""Summarize the raw files of this run into summary.json (#830).

Usage: python aggregate.py   (reads raw/ next to this file, writes summary.json)
"""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
TRIALS = range(1, 6)
WORKERS = {
    "raw_pycubrid": "worker_raw_pycubrid_trial{t}.json",
    "core_sa21": "worker_sqlalchemy_core_sa21_trial{t}.json",
    "core_sa20": "worker_sqlalchemy_core_sa20_trial{t}.json",
    "orm_sa21": "worker_sqlalchemy_orm_sa21_trial{t}.json",
    "orm_sa20": "worker_sqlalchemy_orm_sa20_trial{t}.json",
}
COMPILE_LINE = re.compile(r"^(.+?)\s{2,}([\d.]+)ms\s+([\d.]+)µs$")


def stats(values: list[float]) -> dict[str, object]:
    q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return {
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "q1": q1,
        "q3": q3,
        "trials": values,
    }


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"aggregate.py: {msg}")


def workers() -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for label, pattern in WORKERS.items():
        runs = [json.loads((RAW / pattern.format(t=t)).read_text()) for t in TRIALS]
        check(all(r["status"] == "ok" for r in runs), f"{label}: a worker run failed")
        ops: dict[str, object] = {}
        for i, step in enumerate(runs[0]["steps"]):
            name = step["name"]
            steps = [r["steps"][i] for r in runs]
            check(all(s["name"] == name for s in steps), f"{label}: step order differs")
            check(
                all(s["errors"] == 0 and s["ops"] > 0 for s in steps),
                f"{label} {name}: failed or missing operations",
            )
            ops[name] = {
                "p50_ms": stats([s["latency_summary"]["p50_ns"] / 1e6 for s in steps]),
                "p95_ms": stats([s["latency_summary"]["p95_ns"] / 1e6 for s in steps]),
                "ops": [s["ops"] for s in steps],
                "errors": [s["errors"] for s in steps],
            }
        out[label] = ops
    return out


def compile_bench(sa: str) -> dict[str, object]:
    per: dict[str, list[float]] = {}
    for t in TRIALS:
        for line in (RAW / f"bench_compile_{sa}_trial{t}.txt").read_text().splitlines():
            m = COMPILE_LINE.match(line.strip())
            if m:
                per.setdefault(m.group(1).strip(), []).append(float(m.group(3)))
    return {name: stats(values) for name, values in per.items()}


def main() -> None:
    summary = {
        "orm_overhead_workers": workers(),
        "bench_compile_us_per_op": {sa: compile_bench(sa) for sa in ("sa21", "sa20")},
        "bench_dialect_baseline": {
            sa: json.loads((RAW / f"bench_dialect_baseline_{sa}.json").read_text())["summary"]
            for sa in ("sa21", "sa20")
        },
        "profile_orm": {
            sa: json.loads((RAW / f"profile_orm_{sa}.json").read_text()) for sa in ("sa21", "sa20")
        },
    }
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {HERE / 'summary.json'}")


if __name__ == "__main__":
    main()
