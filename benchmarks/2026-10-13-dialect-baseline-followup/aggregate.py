"""Collect the per-run summaries of this follow-up into summary.json (#830).

Usage: python aggregate.py   (reads raw/ next to this file, writes summary.json)

Each raw file already holds the medians, IQRs and per-trial values that
scripts/bench_dialect_baseline.py computed; this keeps them side by side with
the server, driver and package versions each run recorded.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
SERVERS = ("102", "110", "112", "114")
DRIVERS = ("pycubrid", "cubriddb", "aiopycubrid")
ENV_KEYS = (
    "cubrid_server",
    "driver",
    "pool",
    "python",
    "sqlalchemy",
    "pycubrid",
    "cubrid_python",
    "sqlalchemy_cubrid",
    "source_sha",
    "cpu",
    "platform",
)


def main() -> None:
    runs = {}
    for server in SERVERS:
        for driver in DRIVERS:
            data = json.loads(
                (RAW / f"bench_dialect_baseline_cubrid{server}_{driver}.json").read_text()
            )
            env = data["environment"]
            runs[f"cubrid{server}_{driver}"] = {
                "environment": {k: env[k] for k in ENV_KEYS if k in env},
                "summary": data["summary"],
            }
    (HERE / "summary.json").write_text(json.dumps(runs, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {HERE / 'summary.json'}")


if __name__ == "__main__":
    main()
