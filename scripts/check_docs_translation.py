#!/usr/bin/env python3
"""Fail when a Korean document drifts structurally from its English source.

English under ``docs/`` is the source of truth and Korean under ``docs/ko/`` is
the one translation kept complete (#705). For every ``docs/<name>.md`` this
compares, with ``docs/ko/<name>.md``, the number of

* headings of level 2, 3 and 4,
* fenced code blocks,
* table rows (separator rows excluded),

all counted outside fenced code blocks. A missing Korean file or any different
count fails. It does not judge wording: two documents with the same structure
can still disagree in a sentence.

``EXCEPTIONS`` lists documents that are deliberately English-only, each with
its reason. README translations are covered by ``check_translation_sync.py``.

Usage::

    python scripts/check_docs_translation.py [--root DIR]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# name -> reason. Keep this short and reviewed; remove an entry when the
# translation lands.
EXCEPTIONS: dict[str, str] = {}

_HEADING = re.compile(r"(#{2,4}) ")
_SEPARATOR = re.compile(r"\|[\s:|-]+\|?\s*$")
_FENCE = re.compile(r"\s*(`{3,}|~{3,})")

Structure = dict[str, int]


def structure(text: str) -> Structure:
    """Count headings, fenced code blocks and table rows outside code blocks."""
    counts: Structure = {"h2": 0, "h3": 0, "h4": 0, "code blocks": 0, "table rows": 0}
    # An open fence closes only with the same character, at least as long as
    # the opener, so a longer fence can hold a shorter one as an example.
    fence: str | None = None
    for line in text.splitlines():
        match = _FENCE.match(line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
                counts["code blocks"] += 1
                continue
            if marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
                continue
        if fence is not None:
            continue
        heading = _HEADING.match(line)
        if heading:
            counts[f"h{len(heading.group(1))}"] += 1
        elif line.startswith("|") and not _SEPARATOR.match(line):
            counts["table rows"] += 1
    return counts


def sources(docs: Path) -> list[Path]:
    """English documents that must have a Korean counterpart."""
    return sorted(
        path
        for path in docs.glob("*.md")
        if not path.name.startswith("README.") and not path.name.endswith(".ko.md")
    )


def check(root: Path, exceptions: dict[str, str] | None = None) -> list[str]:
    """Return one message per problem; an empty list means the set is in sync."""
    allowed = EXCEPTIONS if exceptions is None else exceptions
    docs = root / "docs"
    problems: list[str] = []
    names = {path.name for path in sources(docs)}
    for name in sorted(allowed):
        if not allowed[name].strip():
            problems.append(f"{name}: listed as an exception without a reason")
        if name not in names:
            problems.append(f"{name}: listed as an exception but docs/{name} does not exist")
        elif (docs / "ko" / name).exists():
            problems.append(f"{name}: listed as an exception but docs/ko/{name} exists")
    for path in sources(docs):
        if path.name in allowed:
            continue
        korean = docs / "ko" / path.name
        if not korean.exists():
            problems.append(f"{path.name}: docs/ko/{path.name} is missing")
            continue
        english = structure(path.read_text(encoding="utf-8"))
        translated = structure(korean.read_text(encoding="utf-8"))
        differences = [
            f"{key} {english[key]} vs {translated[key]}"
            for key in english
            if english[key] != translated[key]
        ]
        if differences:
            problems.append(f"{path.name}: English vs Korean: " + ", ".join(differences))
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    problems = check(args.root)
    if problems:
        print("Korean documentation is out of sync with docs/ (see docs/DEVELOPMENT.md):")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print(f"OK: {len(sources(args.root / 'docs')) - len(EXCEPTIONS)} documents match docs/ko/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
