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
