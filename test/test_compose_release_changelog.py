"""Publisher-format and regeneration regressions; no publication or database."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.repo_tooling
SPEC = importlib.util.spec_from_file_location(
    "compose_release_changelog",
    Path(__file__).resolve().parents[1] / "scripts/compose_release_changelog.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
compose = MODULE.compose
BASE = "# Changelog\n\n## [Unreleased]\n\n### Upgrade notes\n\nKeep this **exactly**.\n\n## [1.8.0] - 2026-09-01\n\nOld history.\n"
NOTES = "# Changelog\n\n## [1.9.0](https://github.com/example/compare/v1.8.0...v1.9.0) (2026-10-03)\n\n### Added\n\n* new API\n"


def test_preserves_curated_notes_history_and_canonical_header() -> None:
    actual = compose(BASE, NOTES, "1.9.0")
    assert actual.startswith("# Changelog\n\n## [Unreleased]\n\n## [1.9.0] - 2026-10-03\n")
    assert "### Upgrade notes\n\nKeep this **exactly**." in actual
    assert "### Added\n\n* new API" in actual
    assert "Conventional commits" not in actual and "####" not in actual
    assert actual[actual.index("## [1.8.0]") :] == BASE[BASE.index("## [1.8.0]") :]
    assert compose(BASE, NOTES, "1.9.0") == actual


def test_regeneration_updates_generated_notes_without_losing_curated_notes() -> None:
    updated = compose(BASE, NOTES.replace("new API", "new API and fix"), "1.9.0")
    assert "Keep this **exactly**." in updated
    assert "new API and fix" in updated
    assert updated.count("### Added") == 1


CURATED = (
    "# Changelog\n\n## [Unreleased]\n\n"
    "### Upgrade notes\n\n- Curated upgrade.\n\n"
    "### Fixed\n\n- Curated fix.\n  Continued line.\n\n"
    "### Documentation\n\n- Curated docs.\n\n"
    "### CI\n\n- Curated CI.\n\n"
    "## [1.8.0] - 2026-09-01\n\n### Conventional commits\n\nOld history.\n"
)
# release-please 17.6.0 output with the repo's changelog-sections: config order,
# not the standard order, plus its breaking-change heading.
GENERATED = (
    "# Changelog\n\n## [1.9.0](https://github.com/example/compare/v1.8.0...v1.9.0) (2026-10-03)"
    "\n\n\n### ⚠ BREAKING CHANGES\n\n* drop old API\n\n"
    "### Added\n\n* new API ([aaaaaaa](https://example/commit/a))\n\n\n"
    "### Fixed\n\n* generated fix\n\n\n"
    "### Performance\n\n* faster\n\n\n"
    "### Changed\n\n* reverted thing\n\n\n"
    "### Documentation\n\n* generated docs\n"
)


def test_merges_curated_and_generated_under_standard_headings_in_order() -> None:
    actual = compose(CURATED, GENERATED, "1.9.0")
    candidate = actual[actual.index("## [1.9.0]") : actual.index("## [1.8.0]")]
    assert candidate == (
        "## [1.9.0] - 2026-10-03\n\n"
        "### Upgrade notes\n\n- Curated upgrade.\n\n* drop old API\n\n"
        "### Added\n\n* new API ([aaaaaaa](https://example/commit/a))\n\n"
        "### Changed\n\n* reverted thing\n\n"
        "### Fixed\n\n- Curated fix.\n  Continued line.\n\n* generated fix\n\n"
        "### Performance\n\n* faster\n\n"
        "### Documentation\n\n- Curated docs.\n\n* generated docs\n\n"
        "### CI\n\n- Curated CI.\n\n"
    )
    # Pre-cutoff history keeps its historical heading, byte for byte.
    assert actual[actual.index("## [1.8.0]") :] == CURATED[CURATED.index("## [1.8.0]") :]


def test_composed_candidate_passes_the_changelog_lint(tmp_path: Path) -> None:
    import shutil
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    (tmp_path / "scripts").mkdir()
    shutil.copy(root / "scripts/lint_changelog.py", tmp_path / "scripts")
    candidate = compose(CURATED, GENERATED, "1.9.0")
    # Move the fixture past the lint cutoff so the candidate is checked.
    candidate = candidate.replace("[1.9.0]", "[9.9.0]").replace("[1.8.0]", "[1.0.0]")
    (tmp_path / "CHANGELOG.md").write_text(candidate, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(tmp_path / "scripts/lint_changelog.py")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "base,generated",
    [
        (CURATED.replace("### CI", "### Docs"), GENERATED),
        (CURATED, GENERATED.replace("### Performance", "### Performance Improvements")),
        (CURATED, GENERATED.replace("\n\n\n### ⚠", "\n\nstray text\n\n### ⚠")),
    ],
)
def test_rejects_nonstandard_headings_or_stray_text(base: str, generated: str) -> None:
    with pytest.raises(ValueError):
        compose(base, generated, "1.9.0")


@pytest.mark.parametrize(
    "generated",
    [
        NOTES.replace("1.9.0", "2.0.0"),
        NOTES.replace("2026-10-03", "2026-02-31"),
        NOTES + NOTES,
        NOTES + "\n## unexpected\n",
        NOTES[: NOTES.index("### Added")],
    ],
)
def test_rejects_unsupported_candidate_without_writing(generated: str) -> None:
    with pytest.raises(ValueError):
        compose(BASE, generated, "1.9.0")


@pytest.mark.parametrize(
    "base,version",
    [
        (BASE.replace("Unreleased", "1.9.0"), "1.9.0"),
        (BASE + "\n## [Unreleased]\n", "1.9.0"),
        (BASE, "1.8.0"),
        (BASE, "1.7.0"),
        (BASE, "1.9.0rc1"),
    ],
)
def test_rejects_invalid_base_or_version(base: str, version: str) -> None:
    with pytest.raises(ValueError):
        compose(base, NOTES, version)


def test_curated_preamble_before_the_first_heading_is_kept_verbatim() -> None:
    preamble = "Curated lead paragraph with **markup**.\n  Indented continuation."
    base = CURATED.replace("## [Unreleased]\n\n", f"## [Unreleased]\n\n{preamble}\n\n", 1)
    actual = compose(base, GENERATED, "1.9.0")
    assert f"## [1.9.0] - 2026-10-03\n\n{preamble}\n\n### Upgrade notes\n" in actual


def test_empty_curated_section_is_dropped() -> None:
    base = BASE.replace("### Upgrade notes", "### Added\n\n### Upgrade notes")
    generated = NOTES.replace("### Added", "### Fixed")
    actual = compose(base, generated, "1.9.0")
    assert "### Added" not in actual
    assert "### Upgrade notes\n\nKeep this **exactly**.\n\n### Fixed\n\n* new API" in actual


def test_pinned_upstream_candidate_preserves_repository_notes() -> None:
    # Captured from release-please 17.6.0 with this repository's changelog-sections
    # (docs/RELEASE_PLEASE_VALIDATION.md): feat renders as ### Added.
    root = Path(__file__).resolve().parents[1]
    base = BASE
    generated = (root / "test/fixtures/release-please/17.6.0-feature.md").read_text()
    actual = compose(base, generated, "1.9.0")
    history = base[base.index("## [1.8.0]") :]
    assert actual[actual.index("## [1.8.0]") :] == history
    assert actual.count("## [Unreleased]") == 1
    assert (
        "### Upgrade notes\n\nKeep this **exactly**.\n\n### Added\n\n* new optional API" in actual
    )
    assert "Conventional commits" not in actual
    assert compose(base, generated, "1.9.0") == actual


FENCED_CURATED = (
    "# Changelog\n\n## [Unreleased]\n\n### Added\n\n- Example:\n\n"
    "```markdown\n### Not a heading\n```\n\n"
    "## [1.8.0] - 2026-09-01\n\nOld history.\n"
)


def test_fenced_heading_in_curated_entry_is_content() -> None:
    actual = compose(FENCED_CURATED, NOTES, "1.9.0")
    assert "```markdown\n### Not a heading\n```" in actual
    assert actual.count("### Added") == 1
    assert (
        actual[actual.index("## [1.8.0]") :] == FENCED_CURATED[FENCED_CURATED.index("## [1.8.0]") :]
    )


def test_fenced_heading_in_generated_entry_is_content() -> None:
    generated = NOTES + "\n```\n### Not a heading\n## also not\n```\n"
    actual = compose(BASE, generated, "1.9.0")
    assert "```\n### Not a heading\n## also not\n```" in actual


def test_fenced_curated_entry_passes_the_changelog_lint(tmp_path: Path) -> None:
    actual = compose(FENCED_CURATED, NOTES, "1.9.0")
    (tmp_path / "scripts").mkdir()
    script = tmp_path / "scripts/lint_changelog.py"
    script.write_text((Path(MODULE.__file__).parent / "lint_changelog.py").read_text())
    (tmp_path / "CHANGELOG.md").write_text(actual)
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "base,generated,message",
    [
        (BASE.replace("Keep this", "```\n### Fixed\nKeep this"), NOTES, "release header inside"),
        ("# Changelog\n\n## [Unreleased]\n\n```\n### Fixed\nx\n", NOTES, "unclosed code fence"),
        (BASE, NOTES + "\n```\n### Fixed\n", "unclosed code fence"),
    ],
)
def test_unclosed_code_fence_fails_closed(base: str, generated: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        compose(base, generated, "1.9.0")


@pytest.mark.parametrize(
    "base,generated",
    [
        (FENCED_CURATED.replace("### Not a heading\n", "## [9.9.9] - 2000-01-01\n"), NOTES),
        (BASE, NOTES + "\n```\n## [1.9.0](x) (2026-01-01)\n```\n"),
        (BASE, NOTES.replace("### Added", "```\n## [1.9.0](x) (2026-01-01)\n### Added")),
    ],
)
def test_fenced_release_header_fails_closed(base: str, generated: str) -> None:
    with pytest.raises(ValueError, match="release header inside an open code fence"):
        compose(base, generated, "1.9.0")
