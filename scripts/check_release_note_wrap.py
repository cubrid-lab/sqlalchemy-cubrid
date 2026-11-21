#!/usr/bin/env python3
"""Check one release section for unintended Markdown wrapping regressions.

A soft-wrapped paragraph is valid Markdown. This check targets *semantic*
breakage: an issue number or split reference rendered as a heading, a broken
Markdown link, or attribution placed on a separate line. Historical sections
are not changed or linted unless explicitly selected for review.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HEADER = re.compile(r"^## \[(\d+\.\d+\.\d+)\]", re.MULTILINE)
BROKEN_LABEL = re.compile(r"\[[^\]\n]{1,100}\n[^\]\n]{1,100}\]\(")
BROKEN_DESTINATION = re.compile(r"\[[^\]\n]{1,100}\]\s*\n\s*\(")
ISSUE_LINE = re.compile(r"^\s{0,3}#\s*\d+(?:\s|$)")
BYLINE = re.compile(r"^\s*(?:by @\S+|\(first contribution 🎉\))")


def release_section(text: str, version: str) -> str:
    matches = list(HEADER.finditer(text))
    for idx, match in enumerate(matches):
        if match.group(1) == version:
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            return text[match.end() : end]
    raise ValueError(f"release [{version}] not found")


def violations(text: str) -> list[str]:
    """Return line-numbered issues without modifying the original Markdown."""
    errors: list[str] = []
    prose: list[tuple[int, str]] = []
    fence: str | None = None
    lines = text.splitlines()
    for n, line in enumerate(lines, start=1):
        content = line.lstrip()
        marker = content[:1] if content.startswith((chr(96) * 3, "~" * 3)) else None
        if marker is not None:
            fence = None if fence == marker else marker
            continue
        if fence is not None:
            continue
        if line.startswith("### ") and n < len(lines) and lines[n].strip():
            errors.append(f"line {n}: add a blank line after the section heading")
        if ISSUE_LINE.match(line):
            errors.append(f"line {n}: issue reference at line start may render as a heading")
        if BYLINE.match(line):
            errors.append(f"line {n}: byline must stay on the change bullet")
        if line.endswith("  "):
            errors.append(f"line {n}: unintended Markdown hard line break")
        prose.append((n, line))
    # Keep original newlines in prose to detect accidentally split inline links.
    combined = "\n".join(line for _, line in prose)
    for pattern, message in (
        (BROKEN_LABEL, "Markdown link label split across lines"),
        (BROKEN_DESTINATION, "Markdown link target split across lines"),
    ):
        for match in pattern.finditer(combined):
            index = combined.count("\n", 0, match.start())
            n = prose[index][0] if index < len(prose) else 1
            errors.append(f"line {n}: {message}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args(argv)
    try:
        section = release_section(Path(args.input).read_text(encoding="utf-8"), args.version)
    except (OSError, ValueError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    problems = violations(section)
    for issue in problems:
        print(f"::error::{issue}", file=sys.stderr)
    if problems:
        return 1
    print(f"OK: [{args.version}] Markdown wrapping verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
