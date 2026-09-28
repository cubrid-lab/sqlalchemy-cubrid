"""Check issue metadata without making contributors manage GitHub labels."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path

_TITLE = re.compile(
    r"^(fix|feat|docs|ci|chore|test|perf|refactor|epic)"
    r"(?:\([a-z0-9_-]+\))?: \S"
)
_TYPES_BY_PREFIX = {
    "fix": frozenset({"bug"}),
    "feat": frozenset({"enhancement"}),
    "docs": frozenset({"documentation"}),
    "ci": frozenset({"ci"}),
    "chore": frozenset({"chore"}),
    "test": frozenset({"bug", "enhancement", "ci"}),
    "perf": frozenset({"enhancement", "performance"}),
    "refactor": frozenset({"chore", "enhancement"}),
    "epic": frozenset({"enhancement"}),
}
_TYPES = frozenset().union(*_TYPES_BY_PREFIX.values())
_PRIORITIES = frozenset(
    {"priority: critical", "priority: high", "priority: medium", "priority: low"}
)
_SIZES = frozenset({"size: XS", "size: S", "size: M", "size: L", "size: XL"})


def metadata_gaps(title: str, labels: Iterable[str]) -> tuple[str, ...]:
    names = set(labels)
    gaps = []
    title_match = _TITLE.match(title)
    if title_match is None:
        gaps.append("title")
    expected_types = _TYPES_BY_PREFIX[title_match.group(1)] if title_match else _TYPES
    type_labels = names.intersection(_TYPES)
    if len(type_labels) != 1 or not type_labels.intersection(expected_types):
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
