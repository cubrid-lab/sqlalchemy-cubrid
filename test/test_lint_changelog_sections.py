"""Standard ``###`` release-note sections (AGENTS.md "GitHub Release Policy").

Runs the real ``scripts/lint_changelog.py`` CLI against independent fixtures.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def run_lint(tmp_path: Path, changelog: str) -> subprocess.CompletedProcess[str]:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    script = scripts / "lint_changelog.py"
    script.write_text((ROOT / "scripts/lint_changelog.py").read_text())
    (tmp_path / "CHANGELOG.md").write_text(changelog)
    return subprocess.run([sys.executable, str(script)], capture_output=True, text=True)


ALL_SECTIONS = (
    "Upgrade notes",
    "Added",
    "Changed",
    "Deprecated",
    "Removed",
    "Fixed",
    "Security",
    "Performance",
    "Documentation",
    "CI",
    "Tests",
)


@pytest.mark.parametrize("release", ["Unreleased", "1.10.1"])
def test_standard_sections_in_order_are_valid(tmp_path: Path, release: str) -> None:
    prefix = "## [Unreleased]\n" if release != "Unreleased" else ""
    body = "".join(f"### {title}\n- Entry\n" for title in ALL_SECTIONS)
    result = run_lint(tmp_path, prefix + f"## [{release}]\n{body}## [1.10.0]\n### Fixed\n- Old\n")
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("release", ["Unreleased", "1.10.1", "2.0.0"])
@pytest.mark.parametrize(
    "heading", ["Docs", "Release automation", "Conventional commits", "Bug Fixes"]
)
def test_nonstandard_section_is_rejected(tmp_path: Path, release: str, heading: str) -> None:
    prefix = "## [Unreleased]\n" if release != "Unreleased" else ""
    result = run_lint(tmp_path, prefix + f"## [{release}]\n### {heading}\n- Entry\n")
    assert result.returncode == 1
    assert f"Subsection '### {heading}' in [{release}] is not a standard section" in result.stderr


@pytest.mark.parametrize(
    "first,second", [("Fixed", "Added"), ("Tests", "CI"), ("Documentation", "Upgrade notes")]
)
def test_out_of_order_sections_are_rejected(tmp_path: Path, first: str, second: str) -> None:
    result = run_lint(tmp_path, f"## [Unreleased]\n### {first}\n- A\n### {second}\n- B\n")
    assert result.returncode == 1
    assert f"'### {second}' in [Unreleased] must come before '### {first}'" in result.stderr


def test_empty_section_is_rejected(tmp_path: Path) -> None:
    result = run_lint(tmp_path, "## [Unreleased]\n### Added\n\n### Fixed\n- Entry\n")
    assert result.returncode == 1
    assert "Subsection '### Added' in [Unreleased] is empty" in result.stderr


@pytest.mark.parametrize("release", ["1.10.0", "1.9.0", "0.1.0"])
def test_cutoff_and_older_releases_keep_historical_sections(tmp_path: Path, release: str) -> None:
    result = run_lint(
        tmp_path,
        f"## [Unreleased]\n## [{release}]\n### Docs\n- A\n### Conventional commits\n- B\n"
        "### Fixed\n- C\n### Added\n- D\n### Release automation\n",
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("release", ["Unreleased", "1.10.1"])
@pytest.mark.parametrize("heading", ["Fixed", "Documentation"])
def test_duplicate_section_is_rejected_after_the_cutoff(
    tmp_path: Path, release: str, heading: str
) -> None:
    prefix = "## [Unreleased]\n" if release != "Unreleased" else ""
    result = run_lint(
        tmp_path, prefix + f"## [{release}]\n### {heading}\n- First\n### {heading}\n- Second\n"
    )
    assert result.returncode == 1
    assert f"Duplicate subsection heading '### {heading}' in [{release}]" in result.stderr


@pytest.mark.parametrize("release", ["Unreleased", "1.10.1"])
def test_non_adjacent_duplicate_section_is_rejected_after_the_cutoff(
    tmp_path: Path, release: str
) -> None:
    prefix = "## [Unreleased]\n" if release != "Unreleased" else ""
    result = run_lint(
        tmp_path,
        prefix + f"## [{release}]\n### Changed\n- A\n### Documentation\n- B\n### Changed\n- C\n",
    )
    assert result.returncode == 1
    assert f"Duplicate subsection heading '### Changed' in [{release}]" in result.stderr


@pytest.mark.parametrize("release", ["1.10.0", "1.9.0", "1.7.1", "0.1.0"])
@pytest.mark.parametrize("heading", ["Changed", "Documentation", "Docs"])
def test_duplicate_section_in_released_history_is_accepted(
    tmp_path: Path, release: str, heading: str
) -> None:
    # Rule 5 is gated by SECTION_POLICY_CUTOFF: released notes up to the cutoff are
    # never rewritten, and [1.9.0] and [1.7.1] carry historical duplicate headings.
    result = run_lint(
        tmp_path,
        f"## [Unreleased]\n## [{release}]\n### {heading}\n- A\n### Fixed\n- B\n"
        f"### {heading}\n- C\n",
    )
    assert result.returncode == 0, result.stderr


def test_section_check_runs_without_released_versions(tmp_path: Path) -> None:
    # An Unreleased-only file returns early for the version checks; the section
    # policy must still apply.
    result = run_lint(tmp_path, "## [Unreleased]\n### Docs\n- Entry\n")
    assert result.returncode == 1
    assert "'### Docs' in [Unreleased] is not a standard section" in result.stderr


def test_repository_changelog_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/lint_changelog.py")], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_same_subsection_across_releases_is_valid(tmp_path: Path) -> None:
    # The order and duplicate checks restart for every release.
    result = run_lint(
        tmp_path,
        "## [Unreleased]\n### Fixed\n- New\n## [1.10.2]\n### Fixed\n- Newer\n"
        "## [1.10.1]\n### Fixed\n- New\n## [1.10.0]\n### Fixed\n- Old\n",
    )
    assert result.returncode == 0, result.stderr


def test_fenced_lines_are_content_not_headings(tmp_path: Path) -> None:
    result = run_lint(
        tmp_path, "## [Unreleased]\n### Added\n```\n### Docs\n```\n### Fixed\n- Entry\n"
    )
    assert result.returncode == 0, result.stderr


def test_fenced_release_header_is_rejected(tmp_path: Path) -> None:
    # extract_release_notes.py is not fence-aware, so a fenced "## [9.9.9]" would truncate
    # the Release body; it fails closed instead of being read as content.
    result = run_lint(
        tmp_path, "## [Unreleased]\n### Added\n```\n## [9.9.9]\n### Added\n```\n### Added\n- x\n"
    )
    assert result.returncode == 1
    assert "ERROR: Release header inside an open code fence in CHANGELOG.md" in result.stderr


def test_fenced_duplicate_heading_is_content(tmp_path: Path) -> None:
    # Rule 5 skips fenced lines: a fenced "### Added" is not a second heading.
    result = run_lint(tmp_path, "## [Unreleased]\n### Added\n```\n### Added\n```\n- x\n")
    assert result.returncode == 0, result.stderr


def test_unclosed_code_fence_is_rejected(tmp_path: Path) -> None:
    # An unclosed fence would otherwise hide every later heading from rules 5 and 6.
    result = run_lint(
        tmp_path,
        "## [Unreleased]\n### Added\n```python\nx = 1\n### Docs\n- a\n### Fixed\n- b\n"
        "### Fixed\n- c\n",
    )
    assert result.returncode == 1
    assert "ERROR: Unclosed code fence in CHANGELOG.md" in result.stderr
