"""Check issue metadata without making contributors manage GitHub labels."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path

_TITLE = re.compile(
    r"^(?:feat|fix|docs|test|perf|refactor|ci|build|chore|style|revert)"
    r"(?:\([a-z0-9][a-z0-9_-]*\))?!?: \S"
)
_TYPE_LABELS = frozenset(
    {"bug", "enhancement", "documentation", "chore", "ci", "testing", "refactor", "performance"}
)
_PRIORITIES = frozenset(
    {"priority: critical", "priority: high", "priority: medium", "priority: low"}
)
_SIZES = frozenset({"size: XS", "size: S", "size: M", "size: L", "size: XL"})


def metadata_gaps(title: str, labels: Iterable[str]) -> tuple[str, ...]:
    names = set(labels)
    gaps = []
    if _TITLE.match(title) is None:
        gaps.append("title")
    if not names.intersection(_TYPE_LABELS):
        gaps.append("type")
    priority = [name for name in names if name.startswith("priority:")]
    if len(priority) != 1 or priority[0] not in _PRIORITIES:
        gaps.append("priority")
    size = [name for name in names if name.startswith("size:")]
    if len(size) != 1 or size[0] not in _SIZES:
        gaps.append("size")
    return tuple(gaps)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        raise ValueError("expected the GitHub issue event JSON path")
    event = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    issue = event["issue"]
    gaps = metadata_gaps(issue["title"], (label["name"] for label in issue["labels"]))
    print(f"needs_triage={'true' if gaps else 'false'}")
    if gaps:
        print(f"Issue metadata needs maintainer triage: {', '.join(gaps)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
