"""release-please changelog-sections map commit types to the standard headings."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("lint_changelog", ROOT / "scripts/lint_changelog.py")
assert SPEC and SPEC.loader
LINT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LINT)

# type -> (section, hidden); hidden types never create a release on their own.
EXPECTED = {
    "feat": ("Added", False),
    "fix": ("Fixed", False),
    "perf": ("Performance", False),
    "deps": ("Changed", False),
    "revert": ("Changed", False),
    "docs": ("Documentation", False),
    "ci": ("CI", True),
    "test": ("Tests", True),
    "refactor": ("Changed", True),
    "chore": ("Changed", True),
    "build": ("Changed", True),
    "style": ("Changed", True),
}


def sections() -> list[dict[str, object]]:
    config = json.loads((ROOT / "release-please-config.json").read_text(encoding="utf-8"))
    return list(config["packages"]["."]["changelog-sections"])


def test_changelog_sections_table_is_exact() -> None:
    entries = sections()
    assert len(entries) == len({e["type"] for e in entries})
    for entry in entries:
        assert set(entry) <= {"type", "section", "hidden"}
    actual = {e["type"]: (e["section"], e.get("hidden", False)) for e in entries}
    assert actual == EXPECTED


def test_every_section_is_a_standard_changelog_section() -> None:
    assert {e["section"] for e in sections()} <= set(LINT.ALLOWED_SECTIONS)


def test_hidden_types_are_exactly_the_non_releasing_types() -> None:
    hidden = {e["type"] for e in sections() if e.get("hidden") is True}
    assert hidden == {"ci", "test", "refactor", "chore", "build", "style"}
