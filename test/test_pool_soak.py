# test/test_pool_soak.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""A bounded mixed request workload on a pycubrid ``QueuePool`` (#1151).

Worker threads act as application requests on one synchronous engine: short
reads, write transactions that commit, write transactions that roll back, and
idle gaps that leave pooled connections unused before they are checked out
again. The run counts every request outcome, the pool's connect, checkout,
checkin and invalidate events, per-kind latency percentiles, and samples the
process RSS, open file descriptors and sockets. At the end every write is
audited against the table, as in the broker-restart test in
``test_server_restart.py``: an acknowledged commit is stored exactly once, a
rolled-back write is never stored, nothing appears that was never attempted,
and a failed write may be stored only when its COMMIT lost the reply (in doubt).

Environment:

* ``CUBRID_SOAK_SECONDS`` (default 3): how long workers start new requests.
  The default keeps the test a small deterministic regression inside every
  ``make integration``; the multi-minute run is manual (docs/DEVELOPMENT.md).
* ``CUBRID_SOAK_BROKER_RESTART=1``: run ``cubrid broker restart`` once, 40% into
  the run. Needs ``CUBRID_TEST_DOCKER_CONTAINER`` and fails without it.
* ``CUBRID_SOAK_REPORT``: path of a JSON report with the counts, resource
  samples and exact environment. Key counts also go to the JUnit report.
"""

from __future__ import annotations

import json
import os
import platform
import random
import threading
import time
from collections import Counter
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import TimeoutError as SATimeoutError

from test.test_server_restart import (
    _CONTAINER_ENV,
    _DRIVERS,
    _SELECT_1,
    _base_url,
    _can_connect,
    _container,
    _restart_broker,
    _Server,
)

pytestmark = pytest.mark.integration

_SECONDS_ENV = "CUBRID_SOAK_SECONDS"
_RESTART_ENV = "CUBRID_SOAK_BROKER_RESTART"
_REPORT_ENV = "CUBRID_SOAK_REPORT"
_SEED = 1151
_WORKERS = 6
_POOL = {"pool_size": 4, "max_overflow": 2, "pool_timeout": 30, "pool_pre_ping": True}
# Requests keep running this long after the restart, so recovery is observed.
_AFTER_RESTART = 5.0
# Share of each request kind; "idle" holds no connection and sleeps.
_MIX = (("read", 50), ("commit", 25), ("rollback", 10), ("idle", 15))


def _seconds() -> float:
    raw = os.environ.get(_SECONDS_ENV, "3")
    try:
        seconds = float(raw)
    except ValueError:
        pytest.fail(f"{_SECONDS_ENV}={raw!r} is not a number of seconds", pytrace=False)
    if seconds <= 0:
        pytest.fail(f"{_SECONDS_ENV} must be positive, got {raw!r}", pytrace=False)
    return seconds


def _resources() -> dict[str, int | None]:
    """RSS in KiB, open file descriptors and sockets of this process (Linux /proc)."""
    rss: int | None = None
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                rss = int(line.split()[1])
        fds = os.listdir("/proc/self/fd")
    except OSError:
        return {"rss_kib": rss, "fds": None, "sockets": None}
    sockets = 0
    for fd in fds:
        try:
            if os.readlink(f"/proc/self/fd/{fd}").startswith("socket:"):
                sockets += 1
        except OSError:
            pass  # the descriptor closed between listdir and readlink
    return {"rss_kib": rss, "fds": len(fds), "sockets": sockets}


def _percentiles(samples: list[float]) -> dict[str, float | int]:
    if not samples:
        return {"count": 0}
    ordered = sorted(samples)

    def at(q: float) -> float:
        return round(ordered[min(len(ordered) - 1, int(q * len(ordered)))] * 1000, 2)

    return {
        "count": len(ordered),
        "p50_ms": at(0.50),
        "p95_ms": at(0.95),
        "p99_ms": at(0.99),
        "max_ms": round(ordered[-1] * 1000, 2),
    }


def _version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def test_mixed_request_workload_is_audited(
    record_property: Callable[[str, object], None],
) -> None:
    seconds = _seconds()
    restart = os.environ.get(_RESTART_ENV) == "1"
    if restart and not os.environ.get(_CONTAINER_ENV):
        pytest.fail(f"{_RESTART_ENV}=1 needs {_CONTAINER_ENV}", pytrace=False)
    url = _base_url().set(drivername=_DRIVERS["pycubrid"])
    if not _can_connect(url):
        pytest.skip(f"pycubrid cannot connect to {url.render_as_string()}")
    server = _Server(_container(), _base_url()) if restart else None
    if server is not None:
        server.ready_url = url

    table = sa.Table("pool_soak_1151", sa.MetaData(), sa.Column("id", sa.Integer, primary_key=True))
    admin = sa.create_engine(url, poolclass=sa.pool.NullPool)
    table.drop(admin, checkfirst=True)
    table.create(admin)
    with admin.connect() as conn:
        server_version = conn.execute(sa.text("SELECT VERSION()")).scalar()

    baseline = _resources()
    engine = sa.create_engine(url, **_POOL)
    lock = threading.Lock()
    pool_events: Counter[str] = Counter()
    checked_in_at: dict[int, float] = {}
    idle_reuse = {"over_1s": 0, "max_idle_s": 0.0}

    def on_checkout(dbapi_conn: Any, *_: Any) -> None:
        with lock:
            pool_events["checkout"] += 1
            since = checked_in_at.pop(id(dbapi_conn), None)
            if since is not None:
                idle = time.monotonic() - since
                idle_reuse["max_idle_s"] = max(idle_reuse["max_idle_s"], round(idle, 3))
                idle_reuse["over_1s"] += idle >= 1.0

    def on_checkin(dbapi_conn: Any, *_: Any) -> None:
        with lock:
            pool_events["checkin"] += 1
            if dbapi_conn is not None:
                checked_in_at[id(dbapi_conn)] = time.monotonic()

    def counter(name: str) -> Any:
        def listener(*_: Any) -> None:
            with lock:
                pool_events[name] += 1

        return listener

    sa.event.listen(engine, "checkout", on_checkout)
    sa.event.listen(engine, "checkin", on_checkin)
    for name in ("connect", "invalidate", "soft_invalidate", "close"):
        sa.event.listen(engine, name, counter(name))

    outcomes: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    latencies: dict[str, list[float]] = {kind: [] for kind, _ in _MIX if kind != "idle"}
    acknowledged: set[int] = set()
    rolled_back: set[int] = set()
    failed_at: dict[int, str] = {}
    failed_after_restart: list[str] = []
    restart_window: dict[str, float] = {}
    samples: list[dict[str, Any]] = []
    stop = threading.Event()
    started = time.monotonic()
    kinds = [kind for kind, _ in _MIX]
    weights = [weight for _, weight in _MIX]

    def request(kind: str, write_id: int) -> None:
        stage = "checkout"
        begun = time.monotonic()
        try:
            with engine.connect() as conn:
                if kind == "read":
                    stage = "select"
                    conn.execute(sa.select(sa.func.count()).select_from(table)).scalar()
                    conn.execute(_SELECT_1)
                    conn.commit()
                else:
                    stage = "insert"
                    conn.execute(table.insert().values(id=write_id))
                    stage = "select"
                    conn.execute(_SELECT_1)
                    stage = kind
                    if kind == "commit":
                        conn.commit()
                    else:
                        conn.rollback()
        except (DBAPIError, SATimeoutError) as exc:
            invalidated = getattr(exc, "connection_invalidated", False)
            label = f"{kind}/{stage}/{type(exc).__name__}{'/invalidated' if invalidated else ''}"
            with lock:
                outcomes[f"{kind}_failed"] += 1
                errors[label] += 1
                if kind != "read":
                    failed_at[write_id] = stage
                if "end" in restart_window and begun > restart_window["end"]:
                    failed_after_restart.append(label)
            return
        with lock:
            outcomes[f"{kind}_ok"] += 1
            if "end" in restart_window and begun > restart_window["end"]:
                outcomes["ok_after_restart"] += 1
            latencies[kind].append(time.monotonic() - begun)
            if kind == "commit":
                acknowledged.add(write_id)
            elif kind == "rollback":
                rolled_back.add(write_id)

    def worker(index: int) -> None:
        rng = random.Random(_SEED + index)
        sequence = 0
        while not stop.is_set():
            kind = rng.choices(kinds, weights)[0]
            if kind == "idle":
                with lock:
                    outcomes["idle"] += 1
                # Long enough for pooled connections to sit unused, short
                # enough that the stop flag is seen promptly.
                stop.wait(rng.uniform(0.2, min(2.0, max(0.3, seconds / 10))))
                continue
            sequence += 1
            request(kind, index * 10_000_000 + sequence)

    def sampler() -> None:
        interval = max(0.5, min(10.0, seconds / 30))
        while True:
            sample = {
                "t_s": round(time.monotonic() - started, 1),
                **_resources(),
                "checked_out": engine.pool.checkedout(),
            }
            samples.append(sample)
            if stop.wait(interval):
                return

    restart_error: list[BaseException] = []

    def restarter() -> None:
        assert server is not None
        time.sleep(seconds * 0.4)
        restart_window["start"] = round(time.monotonic() - started, 3)
        try:
            _restart_broker(server)
        except BaseException as exc:  # pytest.fail() raises an OutcomeException
            restart_error.append(exc)
        restart_window["end"] = time.monotonic()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(_WORKERS)]
    threads.append(threading.Thread(target=sampler))
    restart_thread = threading.Thread(target=restarter) if restart else None
    try:
        for thread in threads:
            thread.start()
        if restart_thread is not None:
            restart_thread.start()
        time.sleep(seconds)
        if restart_thread is not None:
            restart_thread.join()
            remaining = restart_window["end"] + _AFTER_RESTART - time.monotonic()
            if remaining > 0:
                time.sleep(remaining)
        stop.set()
        for thread in threads:
            thread.join()
        elapsed = time.monotonic() - started
        checked_out_at_end = engine.pool.checkedout()
    finally:
        stop.set()
        engine.dispose()
    after_dispose = _resources()
    if restart_error:
        raise restart_error[0]

    with admin.connect() as conn:
        stored_list = [row[0] for row in conn.execute(sa.select(table.c.id))]
    table.drop(admin, checkfirst=True)
    admin.dispose()

    stored = set(stored_list)
    failed = set(failed_at)
    in_doubt = {write_id: failed_at[write_id] for write_id in failed & stored}
    requests = sum(n for key, n in outcomes.items() if key.endswith(("_ok", "_failed")))
    failures = sum(n for key, n in outcomes.items() if key.endswith("_failed"))
    if "end" in restart_window:
        restart_window["end"] = round(restart_window["end"] - started, 3)
    report = {
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "sqlalchemy": sa.__version__,
            "sqlalchemy_cubrid": _version("sqlalchemy-cubrid"),
            "pycubrid": _version("pycubrid"),
            "cubrid_server": server_version,
            "url": url.render_as_string(hide_password=True),
            "pool": {"class": "QueuePool", **_POOL},
            "workers": _WORKERS,
            "mix_percent": dict(_MIX),
            "seed": _SEED,
            "seconds": seconds,
            "broker_restart": restart,
        },
        "elapsed_s": round(elapsed, 1),
        "restart_window_s": restart_window,
        "requests": requests,
        "succeeded": requests - failures,
        "failed": failures,
        "in_doubt": len(in_doubt),
        "outcomes": dict(sorted(outcomes.items())),
        "errors": dict(sorted(errors.items())),
        "failed_after_restart": failed_after_restart,
        "writes": {
            "acknowledged": len(acknowledged),
            "rolled_back": len(rolled_back),
            "failed": len(failed),
            "stored": len(stored),
        },
        "pool_events": dict(sorted(pool_events.items())),
        "idle_reuse": idle_reuse,
        "checked_out_at_end": checked_out_at_end,
        "latency": {kind: _percentiles(values) for kind, values in latencies.items()},
        "resources": {"baseline": baseline, "after_dispose": after_dispose, "samples": samples},
    }
    report_path = os.environ.get(_REPORT_ENV)
    if report_path:
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        Path(report_path).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for name in ("requests", "succeeded", "failed", "in_doubt"):
        record_property(name, report[name])
    for name in ("checkout", "checkin", "connect", "invalidate"):
        record_property(f"pool_{name}", pool_events[name])
    record_property("rss_kib_start_end", f"{samples[0]['rss_kib']}->{samples[-1]['rss_kib']}")
    record_property("fds_start_end", f"{samples[0]['fds']}->{samples[-1]['fds']}")

    # Durable outcomes: nothing lost, invented, replayed or misreported.
    assert len(stored_list) == len(stored)
    assert acknowledged <= stored, "an acknowledged commit was lost"
    assert not rolled_back & stored, "a rolled-back write was stored"
    assert stored <= acknowledged | failed, "a row appeared that was never attempted"
    assert set(in_doubt.values()) <= {"commit"}, (
        f"a write failed before COMMIT yet was stored: {in_doubt}"
    )
    # The pool returns every connection and the workload exercised it.
    assert checked_out_at_end == 0
    # A checkout that fails (pre-ping and reconnect fail while the broker is
    # down) returns its pool slot with a checkin event but fires no checkout.
    failed_checkouts = sum(n for label, n in errors.items() if "/checkout/" in label)
    assert pool_events["checkin"] == pool_events["checkout"] + failed_checkouts
    assert outcomes["read_ok"] and outcomes["commit_ok"] and outcomes["rollback_ok"]
    # Pooled sockets are bounded by the pool size: no connection leaks over time.
    if baseline["sockets"] is not None:
        cap = baseline["sockets"] + _POOL["pool_size"] + _POOL["max_overflow"]
        peak = max(sample["sockets"] for sample in samples)
        assert peak <= cap, f"{peak} sockets open, more than the pool allows ({cap})"
    if restart:
        assert not failed_after_restart, (
            f"requests failed after the restart: {failed_after_restart}"
        )
        assert outcomes["ok_after_restart"], "no request ran after the restart"
    else:
        # A healthy server: every request succeeds and nothing is invalidated.
        assert failures == 0, report["errors"]
        assert pool_events["invalidate"] == 0
