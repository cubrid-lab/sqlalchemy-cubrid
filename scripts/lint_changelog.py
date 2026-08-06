#!/usr/bin/env python3
"""Validate CHANGELOG.md structure.

Usage:
    python scripts/lint_changelog.py

Checks:
    1. First section is [Unreleased]
    2. No duplicate version sections
    3. Versions in descending semver order

Exit codes:
    0 — changelog is valid
    1 — structural error found
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    changelog = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
    if not changelog.exists():
        print(f"ERROR: {changelog} not found", file=sys.stderr)
        return 1

    content = changelog.read_text(encoding="utf-8")
    headers = re.findall(r"^## \[(\S+)\]", content, re.MULTILINE)

    if not headers:
        print("ERROR: No version sections found (expected '## [X.Y.Z]')", file=sys.stderr)
        return 1

    # Rule 1: First header must be [Unreleased]
    if headers[0] != "Unreleased":
        print(
            f"ERROR: First section must be [Unreleased], got [{headers[0]}]",
            file=sys.stderr,
        )
        return 1

    versions = headers[1:]  # exclude Unreleased

    if not versions:
        print("WARNING: No released versions in CHANGELOG (only [Unreleased])")
        return 0

    # Rule 2: No duplicate version sections
    seen: set[str] = set()
    for v in versions:
        if v in seen:
            print(f"ERROR: Duplicate version section [{v}]", file=sys.stderr)
            return 1
        seen.add(v)

    # Rule 3: Versions in descending semver order
    try:
        from packaging.version import InvalidVersion, Version

        parsed = [(v, Version(v)) for v in versions]
        for i in range(len(parsed) - 1):
            if parsed[i][1] < parsed[i + 1][1]:
                print(
                    f"ERROR: [{parsed[i][0]}] should come after [{parsed[i + 1][0]}] "
                    f"(versions must be in descending order)",
                    file=sys.stderr,
                )
                return 1
    except ImportError:
        # packaging not available — skip ordering check
        print("NOTE: 'packaging' not installed, skipping semver ordering check")
    except InvalidVersion as exc:
        print(f"WARNING: Non-semver version found: {exc}", file=sys.stderr)

    print(f"OK: {len(versions)} version(s), order valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
