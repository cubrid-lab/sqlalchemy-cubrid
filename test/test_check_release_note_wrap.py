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


def test_heading_requires_a_blank_line_before_its_content() -> None:
    assert MODULE.violations("### Fixed\n- Missing heading gap.\n")


def test_valid_lazy_list_wrapping_and_following_prose_are_allowed() -> None:
    notes = (
        "### Tests\n\n- Valid bullet content\n"
        "continues on a lazy-wrapped line.\n\n"
        "A separate explanatory paragraph is allowed.\n"
    )
    assert MODULE.violations(notes) == []


def test_branding_revision_history_stays_in_the_documentation_section() -> None:
    changelog = (SCRIPT.parent.parent / "CHANGELOG.md").read_text(encoding="utf-8")
    notes = MODULE.release_section(changelog, "1.12.1")
    documentation = notes.split("### Documentation", 1)[1].split("### CI", 1)[0]
    tests = notes.split("### Tests", 1)[1]
    assert "Branding revision PRs and commits" in documentation
    assert "Branding change history:" not in tests


def test_all_published_release_sections_have_intact_markdown_structure() -> None:
    changelog = (SCRIPT.parent.parent / "CHANGELOG.md").read_text(encoding="utf-8")
    published = (
        "1.12.2",
        "1.12.1",
        "1.12.0",
        "1.11.7",
        "1.11.6",
        "1.11.5",
        "1.11.0",
        "1.10.0",
        "1.9.0",
        "1.8.0",
        "1.7.1",
        "1.7.0",
        "1.6.0",
        "1.5.1",
        "1.5.0",
        "1.4.3",
        "1.4.2",
        "1.4.1",
        "1.4.0",
        "1.3.0",
        "1.2.3",
        "1.2.2",
        "1.2.1",
        "1.2.0",
        "1.1.0",
        "1.0.0",
        "0.8.0",
        "0.7.1",
    )
    for version in published:
        section = MODULE.release_section(changelog, version)
        problems = MODULE.violations(section)
        assert not problems, f"v{version} has malformed release Markdown: {problems}"


@pytest.mark.parametrize(
    "version",
    [
        "0.1.0",
        "0.2.0",
        "0.3.0",
        "0.3.1",
        "0.3.2",
        "0.4.0",
        "0.5.0",
        "0.6.0",
        "0.7.0",
    ],
)
def test_unpublished_historical_draft_sections_have_valid_markdown_and_provenance(
    version: str,
) -> None:
    changelog = (SCRIPT.parent.parent / "CHANGELOG.md").read_text(encoding="utf-8")
    section = MODULE.release_section(changelog, version)
    assert not MODULE.violations(section), version
    assert section.endswith("\n\n"), f"v{version} needs a blank line before the next version"
    assert "by @yeongseon" in section
    assert "https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/" in section
    assert "by @sisyphus-dev-ai" not in section
