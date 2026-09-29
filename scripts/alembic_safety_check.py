#!/usr/bin/env python3
"""Check Alembic revisions for multiple DDL operations (advisory).

CUBRID DDL is transactional, so a failing revision is rolled back as a
whole. Every DDL statement holds a schema lock on its table until the
transaction commits, though, so this lists revisions with several DDL
calls: they keep tables locked longer and are candidates for running with
``transaction_per_migration=True`` or for splitting.

Only calls such as ``op.create_table(...)`` or ``batch_op.add_column(...)``
count; a bare reference like ``op.drop_table`` is not a DDL operation. This is
a heuristic AST scan, not control-flow analysis: a call in a loop or branch
counts once, as written, and DDL issued from helpers defined outside
``upgrade()``/``downgrade()`` is not seen.

Usage:
    python scripts/alembic_safety_check.py alembic/versions/

Exit codes:
    0 — no revision has more than one DDL call per function
    0 — warnings found (advisory only, does not fail CI)
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

DDL_CALLS = {
    "create_table",
    "drop_table",
    "add_column",
    "drop_column",
    "create_index",
    "drop_index",
    "alter_column",
    "add_constraint",
    "drop_constraint",
    "create_unique_constraint",
    "create_foreign_key",
    "create_check_constraint",
    "create_primary_key",
}


def check_revision(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    warnings: list[str] = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name not in ("upgrade", "downgrade"):
            continue
        ddl_count = sum(
            1
            for node in ast.walk(func)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in DDL_CALLS
        )
        if ddl_count > 1:
            warnings.append(
                f"{path.name}:{func.name}() has {ddl_count} DDL operations "
                "(schema locks are held until the transaction commits)"
            )
    return warnings


def main() -> None:
    versions_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("alembic/versions")
    if not versions_dir.is_dir():
        print(f"Directory not found: {versions_dir}")
        sys.exit(1)

    all_warnings: list[str] = []
    for py_file in sorted(versions_dir.glob("*.py")):
        all_warnings.extend(check_revision(py_file))

    if all_warnings:
        print("\u26a0\ufe0f  Alembic safety warnings (advisory):")
        for w in all_warnings:
            print(f"  \u2022 {w}")
        print(f"\nTotal: {len(all_warnings)} warning(s)")
        print(
            "Tip: these revisions roll back whole on failure but hold schema locks "
            "until commit; use transaction_per_migration=True for long or "
            "large-table migrations."
        )
    else:
        print("\u2713 No revision has more than one DDL call per function.")


if __name__ == "__main__":
    main()
