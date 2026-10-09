#!/usr/bin/env python3
"""Compose canonical release notes from main's curated notes and release-please.

Read main's CHANGELOG at the generator base SHA, never a previously composed
candidate. Generated headers belong in RELEASE_CHANGELOG.md; publication keeps
its strict bracket/date contract. Curated and generated entries are merged under
the standard ``###`` headings in the standard order, so the candidate passes
scripts/lint_changelog.py. Call only after the freeze-label check.
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
SUBSECTION = re.compile(r"^### (.+)$", re.MULTILINE)
HEADING_1_2 = re.compile(r"^#{1,2} ", re.MULTILINE)
# Standard ``###`` headings, in order (AGENTS.md "GitHub Release Policy"; kept in
# sync with scripts/lint_changelog.py). release-please renders breaking changes
# under its own heading; they are upgrade notes.
ALLOWED_SECTIONS = (
    "Upgrade notes",
    "Added",
    "Changed",
    "Deprecated",
    "Removed",
    "Fixed",
    "Security",
    "Performance",
    "Documentation",
    "CI",
    "Tests",
)
GENERATED_ALIASES = {"⚠ BREAKING CHANGES": "Upgrade notes"}


def _find(pattern: re.Pattern[str], text: str, origin: str) -> list[re.Match[str]]:
    """Line-anchored matches outside fenced code blocks; an unclosed fence fails closed.

    Lines inside a fenced code block are content, never headings (the same rule as
    scripts/lint_changelog.py). Fence lines themselves stay part of the surrounding text.
    A release header (``## [``) inside an open fence is an error, not content.
    """
    matches: list[re.Match[str]] = []
    in_fence = False
    pos = 0
    for line in text.splitlines(keepends=True):
        if in_fence and re.match(r"#{1,2} \[", line):
            raise ValueError(f"release header inside an open code fence in {origin}")
        if not in_fence and (match := pattern.match(text, pos)):
            matches.append(match)
        if line.startswith("```"):
            in_fence = not in_fence
        pos += len(line)
    if in_fence:
        raise ValueError(f"unclosed code fence in {origin}")
    return matches


def _split(text: str, origin: str, aliases: dict[str, str]) -> tuple[str, dict[str, list[str]]]:
    """Split notes into the text before the first ``###`` and per-heading bodies."""
    heads = _find(SUBSECTION, text, origin)
    preamble = text[: heads[0].start() if heads else len(text)].strip("\n")
    bodies: dict[str, list[str]] = {}
    for i, head in enumerate(heads):
        title = head.group(1).strip()
        title = aliases.get(title, title)
        if title not in ALLOWED_SECTIONS:
            raise ValueError(f"unsupported {origin} section '### {head.group(1).strip()}'")
        stop = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[head.end() : stop].strip("\n")
        if body.strip():
            bodies.setdefault(title, []).append(body)
    return preamble, bodies


def compose(base: str, generated: str, version: str) -> str:
    """Pure, fail-closed and deterministic at a given generator base/input."""
    if not VERSION.fullmatch(version):
        raise ValueError("candidate version must be MAJOR.MINOR.PATCH")
    sections = _find(SECTION, base, "main CHANGELOG")
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
    headers = _find(GENERATED, generated, "generated notes")
    if not headers or headers[0].group("version") != version:
        raise ValueError("generated top section must match the candidate")
    if sum(h.group("version") == version for h in headers) != 1:
        raise ValueError("duplicate generated candidate section")
    date = headers[0].group("date")
    dt.date.fromisoformat(date)
    stop = headers[1].start() if len(headers) > 1 else len(generated)
    notes = generated[headers[0].end() : stop].strip()
    if not notes or _find(HEADING_1_2, notes, "generated notes"):
        raise ValueError("empty or unsupported generated section")
    generated_preamble, generated_bodies = _split(notes, "generated", GENERATED_ALIASES)
    if generated_preamble.strip() or not generated_bodies:
        raise ValueError("generated notes must sit under ### headings")
    head = sections[0]
    history_start = sections[1].start() if len(sections) > 1 else len(base)
    curated_preamble, curated_bodies = _split(
        base[head.end() : history_start], "curated [Unreleased]", {}
    )
    # Merge curated and generated entries under one standard heading each, in the
    # standard order; curated text comes first and is copied unchanged.
    blocks = [curated_preamble] if curated_preamble.strip() else []
    for title in ALLOWED_SECTIONS:
        parts = curated_bodies.get(title, []) + generated_bodies.get(title, [])
        if parts:
            blocks.append(f"### {title}\n\n" + "\n\n".join(p.strip("\n") for p in parts))
    body = "\n\n".join(blocks)
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
