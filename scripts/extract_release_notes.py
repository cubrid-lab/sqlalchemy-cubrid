#!/usr/bin/env python3
"""Extract a single version's section from CHANGELOG.md for GitHub Release notes.

The CHANGELOG is the single source of truth for release notes. This script is
fail-closed: if the requested version has no dated section (or the section is
empty), it exits non-zero and writes nothing. There is no fallback to generated
notes or the whole changelog.

Usage:
    python scripts/extract_release_notes.py vX.Y.Z

On success, writes the section body (without the header line) to
RELEASE_NOTES.md in the current working directory, followed by exactly one
``**Full Changelog**: <REPO_URL>/compare/<PREV_TAG>...<TAG>`` line. PREV_TAG is
the next older version section of the CHANGELOG; the link is omitted for the
first release and when the section already contains a compare link.

Exit codes:
    0 — section extracted and written to RELEASE_NOTES.md
    1 — missing or empty CHANGELOG section for the requested version
    2 — usage error
"""

from __future__ import annotations

import pathlib
import re
import sys

REPO_URL = "https://github.com/cubrid-lab/sqlalchemy-cubrid"
COMPARE_LINK = re.compile(r"https://github\.com/[^/\s]+/[^/\s]+/compare/")


def full_changelog_link(tag: str, history: str) -> str | None:
    """Compare link from the next older version section in ``history``, if any."""
    previous = re.search(r"^## \[(\d+\.\d+\.\d+)\]", history, re.MULTILINE)
    if previous is None:
        return None
    return f"**Full Changelog**: {REPO_URL}/compare/v{previous.group(1)}...{tag}"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: extract_release_notes.py vX.Y.Z", file=sys.stderr)
        return 2

    tag = sys.argv[1]
    version = tag[1:] if tag.startswith("v") else tag

    changelog = pathlib.Path("CHANGELOG.md")
    if not changelog.exists():
        print("ERROR: CHANGELOG.md not found", file=sys.stderr)
        return 1

    text = changelog.read_text(encoding="utf-8")
    header_re = re.compile(
        rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}\s*$",
        re.MULTILINE,
    )
    match = header_re.search(text)
    if not match:
        print(f"ERROR: Missing dated CHANGELOG section for {version}", file=sys.stderr)
        return 1

    next_match = re.search(r"^## \[", text[match.end() :], re.MULTILINE)
    end = match.end() + next_match.start() if next_match else len(text)
    body = text[match.end() : end].strip()
    if not body:
        print(f"ERROR: Empty CHANGELOG section for {version}", file=sys.stderr)
        return 1

    notes = body + "\n"
    link = full_changelog_link(f"v{version}", text[end:])
    if link and not COMPARE_LINK.search(body):
        notes += "\n" + link + "\n"
    pathlib.Path("RELEASE_NOTES.md").write_text(notes, encoding="utf-8")
    print(f"OK: wrote RELEASE_NOTES.md for {version} ({len(body)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
