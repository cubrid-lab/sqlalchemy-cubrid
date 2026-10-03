#!/usr/bin/env python3
"""Compose canonical release notes from main's curated notes and release-please.

Read main's CHANGELOG at the generator base SHA, never a previously composed
candidate. Generated headers belong in RELEASE_CHANGELOG.md; publication keeps
its strict bracket/date contract. Call only after the freeze-label check.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
SECTION = re.compile(r"^## \[([^\]]+)\][^\n]*$", re.MULTILINE)
GENERATED = re.compile(
    r"^##? \[(?P<version>[0-9]+\.[0-9]+\.[0-9]+)\]"
    r"(?:\([^\n]+\))? \((?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})\)$",
    re.MULTILINE,
)


def compose(base: str, generated: str, version: str) -> str:
    """Pure, fail-closed and deterministic at a given generator base/input."""
    if not VERSION.fullmatch(version):
        raise ValueError("candidate version must be MAJOR.MINOR.PATCH")
    sections = list(SECTION.finditer(base))
    if not sections or sections[0].group(1) != "Unreleased":
        raise ValueError("main CHANGELOG must start with [Unreleased]")
    if sum(s.group(1) == "Unreleased" for s in sections) != 1:
        raise ValueError("main CHANGELOG must have exactly one [Unreleased]")
    if any(s.group(1) == version for s in sections):
        raise ValueError("candidate already exists in main CHANGELOG")
    if len(sections) > 1:
        latest = sections[1].group(1)

        def key(value: str) -> tuple[int, ...]:
            return tuple(int(n) for n in value.split("."))

        if not VERSION.fullmatch(latest) or key(version) <= key(latest):
            raise ValueError("candidate must be newer than main's latest section")
    headers = list(GENERATED.finditer(generated))
    if not headers or headers[0].group("version") != version:
        raise ValueError("generated top section must match the candidate")
    if sum(h.group("version") == version for h in headers) != 1:
        raise ValueError("duplicate generated candidate section")
    date = headers[0].group("date")
    dt.date.fromisoformat(date)
    stop = headers[1].start() if len(headers) > 1 else len(generated)
    notes = generated[headers[0].end() : stop].strip()
    if not notes or re.search(r"^#{1,2} ", notes, re.MULTILINE):
        raise ValueError("empty or unsupported generated section")
    # Keep generated headings below a single section, avoiding duplicate curated
    # ### Fixed/Documentation/etc. headings (external changelog-validator work).
    notes = re.sub(r"^(#{3,}) ", r"#\1 ", notes, flags=re.MULTILINE)
    head = sections[0]
    history_start = sections[1].start() if len(sections) > 1 else len(base)
    curated = base[head.end() : history_start].strip("\n")
    body = curated + ("\n\n" if curated else "")
    body += "### Conventional commits\n\n" + notes
    return (
        base[: head.end()]
        + f"\n\n## [{version}] - {date}\n\n"
        + body
        + ("\n\n" if history_start < len(base) else "\n")
        + base[history_start:]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-changelog", required=True)
    parser.add_argument("--generated-changelog", default="RELEASE_CHANGELOG.md")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", default="CHANGELOG.md")
    args = parser.parse_args(argv)
    try:
        result = compose(
            Path(args.base_changelog).read_text(encoding="utf-8"),
            Path(args.generated_changelog).read_text(encoding="utf-8"),
            args.version,
        )
    except (ValueError, OSError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    Path(args.output).write_text(result, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
