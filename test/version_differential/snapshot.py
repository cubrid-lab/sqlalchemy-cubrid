# test/version_differential/snapshot.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Version-differential snapshot generator (stabilization Phase 6).

Connects to one live CUBRID server, exercises a fixed battery of dialect-visible
behaviors, and writes the observations to a deterministic JSON file. Running this
against every supported CUBRID version (10.2/11.0/11.2/11.4) and then diffing the
snapshots (see ``compare_snapshots.py``) tells us exactly where server behavior
that the dialect depends on diverges across versions.

The snapshot deliberately records two orthogonal things:

* ``server_capabilities`` — whether a raw SQL construct runs on this server. This
  is the ground truth a ``supports_*`` flag is asserting.
* ``type_reflection`` — for each ``CREATE TABLE`` column type, what the dialect's
  own reflection (``get_columns``) reports back. Reflection is where most
  cross-version drift actually bites, because the server catalog representation
  can change between versions.

Usage::

    python -m test.version_differential.snapshot \\
        --url cubrid+pycubrid://dba@localhost:33000/testdb \\
        --out snapshot-11.4.json \\
        --label 11.4
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

# ---------------------------------------------------------------------------
# Capability probes: (name, SQL that only succeeds if the server supports it)
# ---------------------------------------------------------------------------

_CAPABILITY_PROBES: list[tuple[str, str]] = [
    ("native_enum", "SELECT CAST('a' AS ENUM('a','b'))"),
    ("native_boolean_cast", "SELECT CAST(1 AS BOOLEAN)"),
    ("is_distinct_from", "SELECT (1 <=> NULL)"),
    ("cte", "WITH x AS (SELECT 1 AS n) SELECT n FROM x"),
    (
        "window_function",
        "SELECT ROW_NUMBER() OVER (ORDER BY n) FROM (SELECT 1 AS n) t",
    ),
    ("insert_returning", "SELECT 1 RETURNING 1"),
    ("intersect", "SELECT 1 INTERSECT SELECT 1"),
    ("except", "SELECT 1 EXCEPT SELECT 1"),
]

# Columns whose reflected type we record. Kept small and stable so a diff points
# at a genuine cross-version change, not at churn in the probe set itself.
_TYPE_COLUMNS: list[tuple[str, str]] = [
    ("c_int", "INTEGER"),
    ("c_bigint", "BIGINT"),
    ("c_smallint", "SMALLINT"),
    ("c_numeric", "NUMERIC(10,2)"),
    ("c_float", "FLOAT"),
    ("c_double", "DOUBLE"),
    ("c_char", "CHAR(4)"),
    ("c_varchar", "VARCHAR(32)"),
    ("c_date", "DATE"),
    ("c_time", "TIME"),
    ("c_datetime", "DATETIME"),
    ("c_timestamp", "TIMESTAMP"),
]

_SNAPSHOT_TABLE = "vdiff_type_snapshot"


def _server_supports(engine: Engine, sql: str) -> bool:
    """True if *sql* executes on the server without raising."""
    try:
        with engine.begin() as conn:
            conn.execute(text(sql))
        return True
    except Exception:
        return False


def _collect_capabilities(engine: Engine) -> dict[str, bool]:
    return {name: _server_supports(engine, sql) for name, sql in _CAPABILITY_PROBES}


def _collect_server_version(engine: Engine) -> str:
    """Raw server version string, normalized to major.minor.

    The exact build/patch component is intentionally dropped so two snapshots
    from the same minor line compare equal even across patch builds.
    """
    with engine.connect() as conn:
        raw = conn.execute(text("SELECT VERSION()")).scalar()
    if raw is None:
        return "unknown"
    m = re.match(r"(\d+)\.(\d+)", str(raw))
    return f"{m.group(1)}.{m.group(2)}" if m else str(raw)


def _collect_type_reflection(engine: Engine) -> dict[str, dict[str, Any]]:
    """Create a table with each probe column, then reflect it back.

    Records, per column, the dialect's reported type class and a small set of
    stable attributes. Anything the server represents differently across
    versions surfaces here as a diff.
    """
    cols_ddl = ", ".join(f"{name} {ddl}" for name, ddl in _TYPE_COLUMNS)
    with engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {_SNAPSHOT_TABLE}"))
        conn.execute(text(f"CREATE TABLE {_SNAPSHOT_TABLE} (id INTEGER PRIMARY KEY, {cols_ddl})"))

    try:
        insp = inspect(engine)
        reflected = {c["name"]: c for c in insp.get_columns(_SNAPSHOT_TABLE)}
        out: dict[str, dict[str, Any]] = {}
        for name, _ddl in _TYPE_COLUMNS:
            col = reflected.get(name)
            if col is None:
                out[name] = {"reflected": False}
                continue
            col_type = col["type"]
            out[name] = {
                "reflected": True,
                "type_class": type(col_type).__name__,
                "type_repr": str(col_type),
                "nullable": bool(col.get("nullable", True)),
            }
        return out
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {_SNAPSHOT_TABLE}"))


def build_snapshot(url: str, label: str) -> dict[str, Any]:
    """Run every probe against *url* and return the snapshot dict."""
    engine = create_engine(url)
    try:
        return {
            "label": label,
            "server_version": _collect_server_version(engine),
            "server_capabilities": _collect_capabilities(engine),
            "type_reflection": _collect_type_reflection(engine),
        }
    finally:
        engine.dispose()


def _dump(snapshot: dict[str, Any]) -> str:
    """Deterministic JSON (sorted keys, stable separators)."""
    return json.dumps(snapshot, indent=2, sort_keys=True) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a CUBRID version-differential snapshot.")
    parser.add_argument("--url", required=True, help="SQLAlchemy CUBRID URL")
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument("--label", required=True, help="Version label, e.g. 11.4")
    args = parser.parse_args()

    snapshot = build_snapshot(args.url, args.label)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(_dump(snapshot))
    print(f"wrote {args.out} (server_version={snapshot['server_version']})")


if __name__ == "__main__":
    main()
