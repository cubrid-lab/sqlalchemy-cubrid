# test/version_differential/compare_snapshots.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Version-differential comparator (stabilization Phase 6).

Loads two or more snapshots produced by ``snapshot.py`` (one per CUBRID version)
and asserts that the dialect-visible behavior is identical across versions,
except where a difference is explicitly declared in ``KNOWN_DIFFERENCES``.

The contract this enforces: sqlalchemy-cubrid claims support for CUBRID
10.2/11.0/11.2/11.4, and that claim means a program sees the *same* dialect
behavior on all of them. An undeclared divergence is either

* a real portability bug (a ``supports_*`` flag or reflection path that is only
  correct on the version the maintainer happened to test), or
* a genuine server behavior change that must be handled and then recorded here.

Either way the nightly matrix should go red until a human decides which.

Exit code is non-zero when an undeclared difference is found, so this doubles as
a CI gate.

Usage::

    python -m test.version_differential.compare_snapshots \\
        snapshot-10.2.json snapshot-11.0.json \\
        snapshot-11.2.json snapshot-11.4.json
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Declared, understood cross-version differences.
#
# Key format: "<section>.<dotted-path>" where section is "server_capabilities"
# or "type_reflection". Value is a human-readable reason. A field listed here is
# excluded from the equality check — its divergence is expected and owned.
#
# Empty by design: today the dialect targets identical behavior on every
# supported version. When a real, understood difference appears, add it here
# with a reason and (ideally) an issue link, rather than weakening the check.
# ---------------------------------------------------------------------------
KNOWN_DIFFERENCES: dict[str, str] = {}


def _load(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _flatten(prefix: str, obj: Any, out: dict[str, Any]) -> None:
    """Flatten a nested dict into ``{dotted.path: leaf_value}``."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            _flatten(f"{prefix}.{k}" if prefix else k, v, out)
    else:
        out[prefix] = obj


def _comparable_fields(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Behavior fields that must match across versions.

    Excludes ``label`` and ``server_version`` (expected to differ) and folds the
    two behavior sections into a flat ``section.path -> value`` mapping.
    """
    flat: dict[str, Any] = {}
    _flatten("server_capabilities", snapshot.get("server_capabilities", {}), flat)
    _flatten("type_reflection", snapshot.get("type_reflection", {}), flat)
    return flat


def compare(snapshots: list[dict[str, Any]]) -> list[str]:
    """Return a list of human-readable divergence messages (empty == all agree).

    The first snapshot is the reference; every other snapshot is compared field
    by field against it. Fields in ``KNOWN_DIFFERENCES`` are skipped.
    """
    if len(snapshots) < 2:
        return ["need at least two snapshots to compare"]

    ref = snapshots[0]
    ref_label = ref.get("label", "?")
    ref_fields = _comparable_fields(ref)

    problems: list[str] = []
    for other in snapshots[1:]:
        other_label = other.get("label", "?")
        other_fields = _comparable_fields(other)

        all_keys = set(ref_fields) | set(other_fields)
        for key in sorted(all_keys):
            if key in KNOWN_DIFFERENCES:
                continue
            ref_val = ref_fields.get(key, "<missing>")
            other_val = other_fields.get(key, "<missing>")
            if ref_val != other_val:
                problems.append(f"{key}: {ref_label}={ref_val!r} vs {other_label}={other_val!r}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare CUBRID version-differential snapshots.")
    parser.add_argument("snapshots", nargs="+", help="Snapshot JSON files (>=2)")
    args = parser.parse_args()

    snapshots = [_load(p) for p in args.snapshots]
    labels = ", ".join(s.get("label", "?") for s in snapshots)
    print(f"comparing {len(snapshots)} snapshots: {labels}")

    problems = compare(snapshots)
    if problems:
        print(f"\nFOUND {len(problems)} undeclared cross-version difference(s):")
        for p in problems:
            print(f"  - {p}")
        print(
            "\nEach line is a dialect-visible behavior that differs across CUBRID "
            "versions.\nEither fix the dialect to normalize it, or record it in "
            "KNOWN_DIFFERENCES with a reason."
        )
        return 1

    print(f"OK: all {len(snapshots)} versions agree on every compared field.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
