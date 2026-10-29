"""Release notes are the CHANGELOG section byte for byte plus one Full Changelog link."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/extract_release_notes.py"
LINK = "**Full Changelog**: https://github.com/cubrid-lab/sqlalchemy-cubrid/compare/"
SECTION = (
    "### Fixed\n\n- **Bold** entry with `code`, trailing spaces  \n"
    "  and a continued line — unicode.\n\n### CI\n\n- Another entry.\n"
)
CHANGELOG = (
    "# Changelog\n\n## [Unreleased]\n\n### Added\n\n- Not released.\n\n"
    f"## [1.2.0] - 2026-10-01\n\n{SECTION}\n"
    "## [1.1.0] - 2026-09-01\n\n### Fixed\n\n- Older.\n\n"
    "## [1.0.0] - 2026-08-01\n\n### Added\n\n- First.\n"
)


def extract(tmp_path: Path, changelog: str, tag: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), tag], cwd=tmp_path, capture_output=True, text=True
    )


def notes(tmp_path: Path) -> str:
    return (tmp_path / "RELEASE_NOTES.md").read_text(encoding="utf-8")


def test_section_is_reproduced_byte_for_byte_with_one_link(tmp_path: Path) -> None:
    assert extract(tmp_path, CHANGELOG, "v1.2.0").returncode == 0
    assert notes(tmp_path) == SECTION + "\n" + LINK + "v1.1.0...v1.2.0\n"
    assert notes(tmp_path).count("**Full Changelog**") == 1


def test_previous_tag_is_the_next_older_version_section(tmp_path: Path) -> None:
    assert extract(tmp_path, CHANGELOG, "v1.1.0").returncode == 0
    assert notes(tmp_path) == "### Fixed\n\n- Older.\n\n" + LINK + "v1.0.0...v1.1.0\n"


def test_first_release_has_no_link(tmp_path: Path) -> None:
    assert extract(tmp_path, CHANGELOG, "v1.0.0").returncode == 0
    assert notes(tmp_path) == "### Added\n\n- First.\n"


def test_existing_compare_link_is_not_duplicated(tmp_path: Path) -> None:
    linked = (
        SECTION + "\nSee https://github.com/cubrid-lab/sqlalchemy-cubrid/compare/v1.1.0...v1.2.0\n"
    )
    assert extract(tmp_path, CHANGELOG.replace(SECTION, linked), "v1.2.0").returncode == 0
    assert notes(tmp_path) == linked.strip() + "\n"
    assert "**Full Changelog**" not in notes(tmp_path)


def test_missing_section_still_fails_closed(tmp_path: Path) -> None:
    result = extract(tmp_path, CHANGELOG, "v9.9.9")
    assert result.returncode == 1
    assert not (tmp_path / "RELEASE_NOTES.md").exists()


def test_wrong_argument_count_prints_usage_and_exits_2(tmp_path: Path) -> None:
    """No tag and two tags are both usage errors, not a silent success."""
    for args in ([], ["v1.2.0", "v1.1.0"]):
        (tmp_path / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 2
        assert "usage: extract_release_notes.py vX.Y.Z" in result.stderr
        assert not (tmp_path / "RELEASE_NOTES.md").exists()


def test_missing_changelog_fails_closed(tmp_path: Path) -> None:
    """No CHANGELOG.md is an error, not an empty release body."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "v1.2.0"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "ERROR: CHANGELOG.md not found" in result.stderr
    assert not (tmp_path / "RELEASE_NOTES.md").exists()


def test_undated_header_is_treated_as_missing(tmp_path: Path) -> None:
    """A `## [1.2.0]` header without a date is not a release section."""
    changelog = "# Changelog\n\n## [1.2.0]\n\n- Not dated.\n"

    result = extract(tmp_path, changelog, "v1.2.0")

    assert result.returncode == 1
    assert "ERROR: Missing dated CHANGELOG section for 1.2.0" in result.stderr
    assert not (tmp_path / "RELEASE_NOTES.md").exists()


def test_empty_section_fails_closed(tmp_path: Path) -> None:
    """A dated header with no body must not produce an empty release."""
    changelog = (
        "# Changelog\n\n## [1.2.0] - 2026-10-01\n\n"
        "## [1.1.0] - 2026-09-01\n\n### Fixed\n\n- Older.\n"
    )

    result = extract(tmp_path, changelog, "v1.2.0")

    assert result.returncode == 1
    assert "ERROR: Empty CHANGELOG section for 1.2.0" in result.stderr
    assert not (tmp_path / "RELEASE_NOTES.md").exists()


def test_version_without_the_leading_v_still_gets_a_v_prefixed_link(tmp_path: Path) -> None:
    """The release workflow passes the tag, but the bare version must work too."""
    assert extract(tmp_path, CHANGELOG, "1.1.0").returncode == 0
    assert notes(tmp_path) == "### Fixed\n\n- Older.\n\n" + LINK + "v1.0.0...v1.1.0\n"
