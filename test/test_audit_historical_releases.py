"""Historical release migration starts from an exact read-only snapshot."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.repo_tooling
path = Path(__file__).resolve().parents[1] / "scripts/audit_historical_releases.py"
spec = importlib.util.spec_from_file_location("audit_historical_releases", path)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_all_published_bodies_are_backed_up_without_changes(tmp_path: Path) -> None:
    releases = [
        {
            "id": 1,
            "tag_name": "v1.12.2",
            "name": "v1.12.2",
            "body": "### Documentation\n\nOriginal body.\n",
            "draft": False,
            "prerelease": False,
        },
        {
            "id": 2,
            "tag_name": "v1.12.1",
            "name": "v1.12.1",
            "body": "Existing notes.\r\n",
            "draft": False,
            "prerelease": False,
        },
    ]
    changelog = "# Changelog\n\n## [1.12.2] - 2026-11-05\n## [1.12.1] - 2026-10-27\n"
    report = module.create_audit(releases, changelog, tmp_path)
    assert report["release_count"] == 2
    assert (tmp_path / "v1.12.1" / "original-body.md").read_bytes() == b"Existing notes.\r\n"
    assert (tmp_path / "v1.12.2" / "original-body.md").read_text() == releases[0]["body"]
    assert json.loads((tmp_path / "report.json").read_text()) == report


def test_unpublished_changelog_versions_are_reported(tmp_path: Path) -> None:
    report = module.create_audit(
        [{"tag_name": "v1.12.2", "name": "v1.12.2", "body": ""}],
        "## [1.12.2]\n## [0.0.1]\n",
        tmp_path,
    )
    assert report["versions_in_changelog_without_published_release"] == ["0.0.1"]


def test_duplicate_tags_are_not_silently_overwritten(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="duplicate tag"):
        module.create_audit(
            [
                {"tag_name": "v1.12.2", "name": "v1.12.2", "body": "one"},
                {"tag_name": "v1.12.2", "name": "v1.12.2", "body": "two"},
            ],
            "## [1.12.2]\n",
            tmp_path,
        )
