"""Ensure soft wrapping never changes release-note links or heading semantics."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.repo_tooling
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
