"""Regression tests for the pre-publication release-note editorial gate (#1356)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_release_note_quality.py"
SPEC = importlib.util.spec_from_file_location("check_release_note_quality", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

GOOD = (
    "This release fixes connection retries without changing the SQLAlchemy API.\n\n"
    "### Fixed\n\n"
    "- **Connections** — Retry transient failures without replaying writes "
    "([#1356](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1356)) by @alice.\n"
)


def test_short_user_facing_release_passes() -> None:
    assert MODULE.violations(GOOD) == []


@pytest.mark.parametrize(
    ("notes", "message"),
    [
        ("### Fixed\n\n- **Connections** — Fixed retries.\n", "summary"),
        (
            "This patch fixes retries.\n\n### Fixed\n\n"
            "* **connections:** fix retry behaviour ([abcdef0](https://example.org/commit/1))\n",
            "uncurated",
        ),
        (
            "This patch fixes retries.\n\n### Fixed\n\n"
            "- Fixed retry behaviour without explaining the affected API.\n",
            "uncurated",
        ),
        (
            "This patch fixes retries.\n\n### Fixed\n\n"
            "- **Connections** — " + "Detailed implementation history. " * 55 + "\n",
            "change entry",
        ),
        (
            "This patch fixes retries.\n\n### Fixed\n\n"
            "- **Connections** — Fixed retries.\n"
            "- **Connections** — Fixed retries.\n",
            "duplicate",
        ),
        (
            "This patch fixes retries.\n\n### Fixed\n\n"
            "- **Connections** — Fixed retries.\n\n"
            "Unattached prose that could be rendered as a separate paragraph.\n",
            "no-errors-expected",
        ),
    ],
)
def test_objective_regressions(notes: str, message: str) -> None:
    problems = MODULE.violations(notes)
    if message == "no-errors-expected":
        assert not problems
    else:
        assert any(message in p for p in problems), problems


def test_large_body_requires_consolidation_even_when_each_entry_is_short() -> None:
    notes = "This version improves diagnostic messages.\n\n### Fixed\n\n"
    notes += "".join(
        f"- **Diagnostic {n}** — " + "Reworded a single error message. " * 28 + "\n"
        for n in range(20)
    )
    problems = MODULE.violations(notes)
    assert any("release body" in p for p in problems), problems


def test_large_number_of_entries_does_not_bypass_total_length_gate() -> None:
    notes = "This release corrects many SQL compilation edge cases.\\n\\n### Fixed\\n\\n"
    notes += "".join(
        f"- **Compiler case {n}** — " + "Corrected operator compilation. " * 18 + "\\n"
        for n in range(70)
    )
    problems = MODULE.violations(notes)
    assert any("release body" in p and "30000" in p for p in problems), problems


def test_publisher_and_candidate_ci_keep_strict_quality_review() -> None:
    publish = (ROOT / ".github/workflows/publish-pypi.yml").read_text()
    prepare = (ROOT / ".github/workflows/release-please.yml").read_text()
    ci = (ROOT / ".github/workflows/ci.yml").read_text()
    makefile = (ROOT / "Makefile").read_text()
    assert 'run: make release-check VERSION="$VERSION"' in publish
    assert "RELEASE_NOTES_ADVISORY" not in publish
    assert 'RELEASE_NOTES_ADVISORY=1' in prepare
    assert "Reject uncurated release candidate notes" in ci
    assert "python3 scripts/check_release_note_quality.py" in ci
    assert "$(PYTHON) scripts/check_release_note_quality.py --version $(VERSION)" in makefile


def test_link_urls_do_not_count_as_visible_prose() -> None:
    huge_url = "https://example.org/" + "a" * 1500
    notes = GOOD.replace("https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1356", huge_url)
    assert MODULE.violations(notes) == []


def test_markdown_code_block_cannot_be_mistaken_for_generated_changes() -> None:
    notes = GOOD + "\n  ```text\n  * raw example in a code block\n  ```\n"
    assert MODULE.violations(notes) == []


def test_only_targeted_release_is_checked() -> None:
    changelog = (
        "# Changelog\n\n## [Unreleased]\n\n"
        "### Fixed\n\n* uncurated change\n\n"
        "## [1.12.3] - 2026-11-13\n\n" + GOOD + "\n"
        "## [1.12.2] - 2026-11-05\n\n### Fixed\n* uncurated history\n"
    )
    assert MODULE.violations(MODULE.release_section(changelog, "v1.12.3")) == []
    assert MODULE.violations(MODULE.release_section(changelog, "1.12.2"))
    with pytest.raises(ValueError, match="not found"):
        MODULE.release_section(changelog, "1.99.9")


def test_cli_advisory_only_relaxes_editorial_verdict(tmp_path: Path) -> None:
    notes = tmp_path / "CHANGELOG.md"
    notes.write_text("## [1.12.3] - 2026-11-13\n### Fixed\n\n* raw notes\n")
    args = [sys.executable, str(SCRIPT), "--input", str(notes), "--version", "1.12.3"]
    strict = subprocess.run(args, capture_output=True, text=True, check=False)
    advisory = subprocess.run(args + ["--advisory"], capture_output=True, text=True, check=False)
    missing = subprocess.run(
        [*args[:-1], "9.9.9", "--advisory"], capture_output=True, text=True, check=False
    )
    assert strict.returncode == 1 and "::error::" in strict.stderr
    assert advisory.returncode == 0 and "::warning::" in advisory.stderr
    assert missing.returncode == 1 and "not found" in missing.stderr


def test_changelog_source_has_not_been_replaced_by_release_pr_body() -> None:
    # Guard against accidentally calling the public checker on release-please's
    # raw PR description rather than the curated CHANGELOG section.
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [Unreleased]" in changelog
    assert MODULE.release_section(changelog, "1.12.2")
