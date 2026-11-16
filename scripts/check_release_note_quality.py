#!/usr/bin/env python3
"""Check the reader-facing quality of one proposed GitHub Release section.

The policy is deliberately scoped to one candidate. Historic sections are not
retroactively blocked merely because a new policy was introduced. The automated
checks catch objective regressions; a human still verifies technical accuracy,
migration guidance and contributor attribution before publication.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HEADER = re.compile(r"^## \[([^\]]+)\][^\n]*$", re.MULTILINE)
HEADING = re.compile(r"^### ")
CURATED = re.compile(r"^- \*\*([^*]+)\*\*\s+—\s+\S")
LINK_URL = re.compile(r"\]\(https?://[^\s)]+\)")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

MAX_SUMMARY_CHARS = 900
MAX_ENTRY_CHARS = 1100
CHARS_PER_ENTRY = 850
MIN_BODY_BUDGET = 6000
MAX_BODY_CHARS = 30000


def release_section(changelog: str, version: str) -> str:
    """Extract exactly the requested section; no silent fallback to another version."""
    name = version.removeprefix("v")
    matches = list(HEADER.finditer(changelog))
    for index, match in enumerate(matches):
        if match.group(1) == name:
            end = matches[index + 1].start() if index + 1 < len(matches) else len(changelog)
            return changelog[match.end() : end]
    raise ValueError(f"release [{name}] not found in CHANGELOG")


def _readable(text: str) -> str:
    """Measure reader-visible words rather than the length of GitHub URLs."""
    text = HTML_COMMENT.sub("", text)
    text = LINK_URL.sub("]", text)
    return re.sub(r"\s+", " ", text).strip()


def violations(section: str) -> list[str]:
    """Find deterministic editorial regressions in a single release candidate."""
    issues: list[str] = []
    summary: list[str] = []
    entries: list[tuple[int, str]] = []
    current_line = 0
    current_parts: list[str] = []
    in_fence = False
    in_sections = False

    def finish_entry() -> None:
        if current_parts:
            entries.append((current_line, "\n".join(current_parts)))

    for number, line in enumerate(section.splitlines(), 1):
        if line.lstrip().startswith((chr(96) * 3, "~" * 3)):
            in_fence = not in_fence
        if in_fence:
            if current_parts:
                current_parts.append(line)
            continue
        if HEADING.match(line):
            finish_entry()
            current_parts = []
            in_sections = True
            continue
        if not in_sections:
            if line.strip():
                summary.append(line.strip())
            continue
        if line.startswith(("- ", "* ")):
            finish_entry()
            current_line = number
            current_parts = [line]
        elif current_parts:
            current_parts.append(line)
        elif line.strip():
            issues.append(f"line {number}: orphan text outside a change entry")

    finish_entry()
    lead = _readable("\n".join(summary))
    if not lead:
        issues.append("missing introductory user-impact summary before the first ### heading")
    elif len(lead) > MAX_SUMMARY_CHARS:
        issues.append(
            f"introductory summary is {len(lead)} characters (max {MAX_SUMMARY_CHARS}); "
            "move details to the appropriate entries"
        )
    if not in_sections:
        issues.append("missing standard ### change sections")
    if not entries:
        issues.append("no change entries found")

    seen: dict[str, int] = {}
    for line_no, entry in entries:
        first = entry.splitlines()[0]
        if not CURATED.match(first):
            issues.append(
                f"line {line_no}: uncurated change entry; use '- **User-visible area** — result ...' "
                "instead of a raw release-please commit subject"
            )
        prose = _readable(entry)
        if len(prose) > MAX_ENTRY_CHARS:
            issues.append(
                f"line {line_no}: change entry is {len(prose)} readable characters "
                f"(max {MAX_ENTRY_CHARS}); shorten or link to technical details"
            )
        key = prose.casefold()
        if key in seen:
            issues.append(f"line {line_no}: duplicate of line {seen[key]}")
        else:
            seen[key] = line_no
    body_chars = len(_readable(section))
    budget = min(MAX_BODY_CHARS, max(MIN_BODY_BUDGET, CHARS_PER_ENTRY * len(entries)))
    if body_chars > budget:
        issues.append(
            f"release body is {body_chars} readable characters for {len(entries)} entries "
            f"(review budget {budget}); group implementation details and link to PRs"
        )
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", default="CHANGELOG.md", help="Canonical changelog file")
    parser.add_argument("--version", required=True, help="Only the release being reviewed")
    parser.add_argument(
        "--advisory",
        action="store_true",
        help="Report findings without failing release-please preparation; never use for publishing",
    )
    args = parser.parse_args(argv)
    try:
        section = release_section(Path(args.input).read_text(encoding="utf-8"), args.version)
    except (OSError, ValueError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1  # Even advisory mode cannot pass a missing or unreadable release.
    problems = violations(section)
    for problem in problems:
        kind = "warning" if args.advisory else "error"
        print(f"::{kind}::{args.version}: {problem}", file=sys.stderr)
    if problems and not args.advisory:
        return 1
    print(
        f"OK: [{args.version}] quality review "
        + ("requires human curation" if problems else "passed")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
