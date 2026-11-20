#!/usr/bin/env python3
"""Reflection diagnostic probe for CUBRID databases.

Connects to a CUBRID database and dumps reflection output for one or all
tables.  Useful for diagnosing Alembic autogenerate false-positive diffs.

Usage::

    export CUBRID_TEST_URL="cubrid://dba@localhost:33000/testdb"

    # Probe all tables
    python scripts/reflection_probe.py

    # Probe a specific table
    python scripts/reflection_probe.py --table users

    # Compare reflected metadata with ORM declarations
    python scripts/reflection_probe.py --compare myapp.models
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from typing import Any

from sqlalchemy import MetaData, create_engine, inspect


def _serialize(obj: Any) -> Any:
    if isinstance(obj, type):
        return f"{obj.__module__}.{obj.__qualname__}"
    return str(obj)


def probe_table(inspector: Any, table_name: str) -> dict[str, Any]:
    return {
        "columns": inspector.get_columns(table_name),
        "pk_constraint": inspector.get_pk_constraint(table_name),
        "foreign_keys": inspector.get_foreign_keys(table_name),
        "indexes": inspector.get_indexes(table_name),
        "unique_constraints": inspector.get_unique_constraints(table_name),
        "table_comment": inspector.get_table_comment(table_name),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="CUBRID reflection diagnostic probe")
    parser.add_argument("--table", help="Specific table to probe (default: all)")
    parser.add_argument(
        "--compare",
        help="Python module with DeclarativeBase models to compare against",
    )
    parser.add_argument("--url", default=os.environ.get("CUBRID_TEST_URL", ""))
    args = parser.parse_args()

    if not args.url:
        print("Set CUBRID_TEST_URL or pass --url", file=sys.stderr)
        sys.exit(1)

    engine = create_engine(args.url, echo=False)
    try:
        inspector = inspect(engine)

        tables = [args.table] if args.table else inspector.get_table_names()
        print(f"Probing {len(tables)} table(s)...\n")

        result: dict[str, Any] = {}
        for table in sorted(tables):
            result[table] = probe_table(inspector, table)

        print(json.dumps(result, indent=2, default=_serialize))

        if args.compare:
            module = importlib.import_module(args.compare)
            declared_registries: list[MetaData] = []
            for attr in dir(module):
                obj = getattr(module, attr)
                if isinstance(obj, type) and hasattr(obj, "metadata"):
                    meta = getattr(obj, "metadata", None)
                    if isinstance(meta, MetaData) and all(
                        meta is not seen for seen in declared_registries
                    ):
                        declared_registries.append(meta)

            if not declared_registries:
                print(f"\nNo MetaData found in {args.compare}", file=sys.stderr)
                sys.exit(1)

            if len(declared_registries) > 1:
                print(
                    f"\n{args.compare} declares {len(declared_registries)} distinct "
                    "MetaData registries; --compare only compares a single registry "
                    "and the others would be silently skipped. Point --compare at a "
                    "module that uses one DeclarativeBase metadata.",
                    file=sys.stderr,
                )
                sys.exit(1)

            declared_meta = declared_registries[0]

            reflected_meta = MetaData()
            reflected_meta.reflect(bind=engine)

            print("\n--- Comparison ---")
            for table_name in sorted(declared_meta.tables):
                if table_name in reflected_meta.tables:
                    declared = declared_meta.tables[table_name]
                    reflected = reflected_meta.tables[table_name]
                    dcols = {c.name for c in declared.columns}
                    rcols = {c.name for c in reflected.columns}
                    missing = dcols - rcols
                    extra = rcols - dcols
                    if missing:
                        print(f"  {table_name}: declared but not reflected: {missing}")
                    if extra:
                        print(f"  {table_name}: reflected but not declared: {extra}")
                    if not missing and not extra:
                        print(f"  {table_name}: columns match ✓")
                else:
                    print(f"  {table_name}: not in database")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
