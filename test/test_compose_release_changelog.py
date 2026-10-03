"""Publisher-format and regeneration regressions; no publication or database."""

from __future__ import annotations

import importlib.util
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
NOTES = "# Changelog\n\n## [1.9.0](https://github.com/example/compare/v1.8.0...v1.9.0) (2026-10-03)\n\n### Features\n\n* new API\n"


def test_preserves_curated_notes_history_and_canonical_header() -> None:
    actual = compose(BASE, NOTES, "1.9.0")
    assert actual.startswith("# Changelog\n\n## [Unreleased]\n\n## [1.9.0] - 2026-10-03\n")
    assert "### Upgrade notes\n\nKeep this **exactly**." in actual
    assert "### Conventional commits\n\n#### Features\n\n* new API" in actual
    assert actual[actual.index("## [1.8.0]") :] == BASE[BASE.index("## [1.8.0]") :]
    assert compose(BASE, NOTES, "1.9.0") == actual


def test_regeneration_updates_generated_notes_without_losing_curated_notes() -> None:
    updated = compose(BASE, NOTES.replace("new API", "new API and fix"), "1.9.0")
    assert "Keep this **exactly**." in updated
    assert "new API and fix" in updated
    assert updated.count("### Conventional commits") == 1


@pytest.mark.parametrize(
    "generated",
    [
        NOTES.replace("1.9.0", "2.0.0"),
        NOTES.replace("2026-10-03", "2026-02-31"),
        NOTES + NOTES,
        NOTES + "\n## unexpected\n",
        NOTES[: NOTES.index("### Features")],
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


def test_pinned_upstream_candidate_preserves_repository_notes() -> None:
    root = Path(__file__).resolve().parents[1]
    base = BASE
    generated = (root / "test/fixtures/release-please/17.6.0-feature.md").read_text()
    actual = compose(base, generated, "1.9.0")
    history = base[base.index("## [1.8.0]") :]
    assert actual[actual.index("## [1.8.0]") :] == history
    assert actual.count("## [Unreleased]") == 1
    assert "### Conventional commits\n\n#### Features" in actual
    assert compose(base, generated, "1.9.0") == actual
