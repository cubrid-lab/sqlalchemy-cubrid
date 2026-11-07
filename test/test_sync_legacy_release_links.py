"""Regression tests for reviewed, link-only corrections to published Releases."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "sync_legacy_release_links", ROOT / "scripts" / "sync_legacy_release_links.py"
)
assert spec and spec.loader
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

TAG = "v1.2.0"
BEFORE = "**Full Changelog**: https://github.com/cubrid-labs/" + sync.REPO.split("/")[1] + "/compare/v1.1.0...v1.2.0\n"
AFTER = sync.corrected(BEFORE)


def release(body: str, **overrides: object) -> dict:
    result = {
        "id": 123,
        "tag_name": TAG,
        "body": body,
        "draft": False,
        "published_at": "2026-11-07T01:00:00Z",
        "prerelease": False,
    }
    result.update(overrides)
    return result


@pytest.fixture
def prepared(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(sync, "ROOT", tmp_path)
    monkeypatch.setattr(sync, "TAGS", (TAG,))
    (tmp_path / (TAG + ".original.md")).write_text(BEFORE, encoding="utf-8")
    (tmp_path / (TAG + ".corrected.md")).write_text(AFTER, encoding="utf-8")
    return tmp_path


def simulate(monkeypatch: pytest.MonkeyPatch, responses: list[dict]) -> list[tuple]:
    calls: list[tuple] = []

    def fake_gh(path: str, payload: dict | None = None) -> dict:
        calls.append((path, payload))
        return responses.pop(0)

    monkeypatch.setattr(sync, "gh", fake_gh)
    sync.run(apply=True)
    return calls


def test_source_preview_checks_allowlisted_navigation_links(
    prepared: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def reject_network(*args: object) -> None:
        raise AssertionError("Preview must not contact GitHub")

    monkeypatch.setattr(sync, "gh", reject_network)
    assert AFTER != BEFORE
    sync.run(apply=False)
    assert sync.corrected(BEFORE) == AFTER
    assert sync.corrected("https://github.com/cubrid-labs/" + sync.REPO.split("/")[1] + "/tree/old") != AFTER


def test_updates_body_only_and_refetches(prepared: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = simulate(
        monkeypatch,
        [release(BEFORE), release(BEFORE), release(AFTER), release(AFTER)],
    )
    assert [call[1] is not None for call in calls] == [False, False, True, False]
    assert calls[2][1] == {"body": AFTER}


def test_idempotent_recheck_does_not_write(
    prepared: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = simulate(monkeypatch, [release(AFTER)])
    assert len(calls) == 1


@pytest.mark.parametrize(
    "invalid",
    [
        release("someone changed this text"),
        release(BEFORE, draft=True),
        release(BEFORE, published_at=None),
        release(BEFORE, tag_name="v2.0.0"),
    ],
)
def test_rejects_unverified_or_changed_release(
    prepared: Path, monkeypatch: pytest.MonkeyPatch, invalid: dict
) -> None:
    with pytest.raises(ValueError):
        simulate(monkeypatch, [invalid])


def test_rejects_second_read_drift(
    prepared: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(ValueError, match="concurrent"):
        simulate(monkeypatch, [release(BEFORE), release("edited")])


def test_rejects_unexpected_patch_response(
    prepared: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(ValueError, match="verification"):
        simulate(monkeypatch, [release(BEFORE), release(BEFORE), release("wrong"), release(AFTER)])


def test_rejects_published_date_or_prerelease_change(
    prepared: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(ValueError, match="metadata"):
        simulate(
            monkeypatch,
            [
                release(BEFORE),
                release(BEFORE),
                release(AFTER),
                release(AFTER, prerelease=True),
            ],
        )


def test_rejects_wider_source_changes(
    prepared: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (prepared / (TAG + ".corrected.md")).write_text(AFTER + "unreviewed", encoding="utf-8")
    with pytest.raises(ValueError, match="link-only correction"):
        simulate(monkeypatch, [])
