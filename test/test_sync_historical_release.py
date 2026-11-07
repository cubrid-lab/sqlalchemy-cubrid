"""Safety tests for historical GitHub Release body synchronization."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "sync_historical_release",
    Path(__file__).resolve().parents[1] / "scripts/sync_historical_release.py",
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

REPO = "cubrid-lab/sqlalchemy-cubrid"
CHANGELOG = (
    "# Changelog\n\n"
    "## [1.12.2] - 2026-11-05\n\n"
    "### Documentation\n\n- Corrected a command by @author.\n\n"
    "## [1.12.1] - 2026-10-31\n\n### Fixed\n\n- Fixed something.\n"
)


def release(body: str = "old body", **kwargs: object) -> dict:
    result = {
        "tag_name": "v1.12.2",
        "draft": False,
        "published_at": "2026-11-05T00:00:00Z",
        "body": body,
        "id": 123,
    }
    result.update(kwargs)
    return result


def prepare(value: dict, expected: str = "old body") -> tuple[str, str]:
    return module.prepare(
        value,
        CHANGELOG,
        repo=REPO,
        tag="v1.12.2",
        previous_tag="v1.12.1",
        expected_sha256=module.digest(expected),
    )


def test_generates_single_comparison_link_and_keeps_approved_section() -> None:
    original, target = prepare(release())
    assert original == "old body"
    assert "Corrected a command by @author." in target
    assert target.count("**Full Changelog**") == 1
    assert "compare/v1.12.1...v1.12.2" in target
    assert "Fixed something" not in target


def test_rejects_stale_backup_hash() -> None:
    with pytest.raises(ValueError, match="changed"):
        prepare(release(body="modified remotely"))


def test_rejects_draft_or_unpublished_release() -> None:
    for value in (dict(release(), draft=True), dict(release(), published_at=None)):
        with pytest.raises(ValueError, match="draft or unpublished"):
            prepare(value)


def test_rejects_wrong_tag() -> None:
    with pytest.raises(ValueError, match="tag mismatch"):
        prepare(dict(release(), tag_name="v1.12.1"))


def test_rejects_ambiguous_existing_changelog_link() -> None:
    with pytest.raises(ValueError, match="Full Changelog"):
        module.make_body("**Full Changelog**: other", "v1.12.1", "v1.12.2", REPO)


def test_version_extraction_is_exact() -> None:
    assert "Corrected a command" in module.extract_version(CHANGELOG, "1.12.2")
    assert "Fixed something" not in module.extract_version(CHANGELOG, "1.12.2")
    with pytest.raises(ValueError, match="not found"):
        module.extract_version(CHANGELOG, "1.12.3")


def test_main_verifies_published_release_after_patch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from unittest.mock import Mock
    import sys

    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(CHANGELOG, encoding="utf-8")
    _, target = prepare(release())
    api = Mock(side_effect=[release(), release(), release(body=target), release(body=target)])
    monkeypatch.setattr(module, "github_json", api)
    monkeypatch.setattr(sys, "argv", ["sync", "--tag", "v1.12.2", "--previous-tag", "v1.12.1", "--changelog", str(changelog), "--expected-sha256", module.digest("old body"), "--apply"])

    assert module.main() == 0
    assert [call.kwargs.get("method", "GET") for call in api.call_args_list] == ["GET", "GET", "PATCH", "GET"]
    assert "Verified published" in capsys.readouterr().out


@pytest.mark.parametrize(
    "final_response",
    [release(body="unexpected"), release(body="different", draft=True), OSError("GET failed")],
)
def test_main_rejects_unverified_publication(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    final_response: object,
) -> None:
    from unittest.mock import Mock
    import sys

    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(CHANGELOG, encoding="utf-8")
    _, target = prepare(release())
    api = Mock(side_effect=[release(), release(), release(body=target), final_response])
    monkeypatch.setattr(module, "github_json", api)
    monkeypatch.setattr(sys, "argv", ["sync", "--tag", "v1.12.2", "--previous-tag", "v1.12.1", "--changelog", str(changelog), "--expected-sha256", module.digest("old body"), "--apply"])

    assert module.main() == 1
    assert "Verified published" not in capsys.readouterr().out
    assert api.call_count == 4
