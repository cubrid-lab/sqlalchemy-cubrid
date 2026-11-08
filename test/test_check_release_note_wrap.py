"""Ensure soft wrapping never changes release-note links or heading semantics."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_release_note_wrap.py"
SPEC = importlib.util.spec_from_file_location("check_release_note_wrap", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_safe_soft_wrapping_is_allowed() -> None:
    notes = (
        "### Fixed\n\n"
        "- **Connection** — Correct reconnect handling in the database\n"
        "  connection path ([#123](https://github.com/example/repo/pull/123))"
        " by @author.\n"
    )
    assert MODULE.violations(notes) == []


@pytest.mark.parametrize(
    "bad",
    [
        "- Resolved an issue\n#123 after retry",
        "- Resolved an issue\n# 123 after retry",
        "- Incorrectly wrapped [pull\nrequest](https://github.com/example/pull/1)",
        "- Incorrectly wrapped [pull request]\n(https://github.com/example/pull/1)",
        "- Corrected behavior  \nwith a forced line break",
        "- Fixed the bug\nby @author",
        "- Fixed the bug\nby @author (first contribution 🎉).",
    ],
)
def test_unintended_markdown_breaks_are_detected(bad: str) -> None:
    assert MODULE.violations(bad)


def test_code_examples_do_not_trigger_false_positives() -> None:
    fence = chr(96) * 3
    notes = fence + "text\n#123\nby @contributor\n" + fence + "\n"
    assert MODULE.violations(notes) == []


def test_only_the_requested_release_is_inspected() -> None:
    changelog = (
        "# Changelog\n\n## [Unreleased]\n\n"
        "## [1.12.3] - 2026-11-07\n\n### Fixed\n\n- No wrapping issue.\n\n"
        "## [1.12.2] - 2026-11-05\n\n### Documentation\n\n"
        "- Broken reference\n#123\n"
    )
    assert MODULE.violations(MODULE.release_section(changelog, "1.12.3")) == []
    assert MODULE.violations(MODULE.release_section(changelog, "1.12.2"))
    with pytest.raises(ValueError, match="not found"):
        MODULE.release_section(changelog, "9.9.9")


@pytest.mark.parametrize(
    "bad",
    [
        "### Fixed\n- Missing heading gap.\n",
        "### Tests\n\n- Existing test.\n\n"
        "Floating history text between list entries.\n\n- Next test.\n",
    ],
)
def test_release_list_structure_errors_are_detected(bad: str) -> None:
    assert MODULE.violations(bad)


def test_all_published_release_sections_have_intact_markdown_structure() -> None:
    changelog = (SCRIPT.parent.parent / "CHANGELOG.md").read_text(encoding="utf-8")
    published = (
        "1.12.2", "1.12.1", "1.12.0", "1.11.7", "1.11.6",
        "1.11.5", "1.11.0", "1.10.0", "1.9.0", "1.8.0",
        "1.7.1", "1.7.0", "1.6.0", "1.5.1", "1.5.0",
        "1.4.3", "1.4.2", "1.4.1", "1.4.0", "1.3.0",
        "1.2.3", "1.2.2", "1.2.1", "1.2.0", "1.1.0",
        "1.0.0", "0.8.0", "0.7.1",
    )
    for version in published:
        section = MODULE.release_section(changelog, version)
        problems = MODULE.violations(section)
        assert not problems, f"v{version} has malformed release Markdown: {problems}"
