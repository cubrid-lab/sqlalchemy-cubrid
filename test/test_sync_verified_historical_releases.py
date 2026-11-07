"""Regression tests for the reviewed historical release write path."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "sync_verified_historical_releases",
    ROOT / "scripts/sync_verified_historical_releases.py",
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

SECTION = "### Fixed\n\n- Kept original release notes."
TAG = "v1.10.0"
PREVIOUS = "v1.9.0"
TARGET = module.make_body(SECTION, PREVIOUS, TAG, module.REPO)


def release(body: str, **changes: object) -> dict:
    result = {
        "id": 123,
        "tag_name": TAG,
        "draft": False,
        "published_at": "2026-01-01T00:00:00Z",
        "body": body,
    }
    result.update(changes)
    return result


def run_case(responses: list[dict], monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    calls: list[tuple] = []

    def fake_api(path: str, *, method: str = "GET", body: str | None = None) -> dict:
        calls.append((path, method, body))
        return responses.pop(0)

    monkeypatch.setattr(module, "RELEASES", ((TAG, PREVIOUS),))
    monkeypatch.setattr(module, "extract_version", lambda text, version: SECTION)
    monkeypatch.setattr(Path, "read_text", lambda self, **kwargs: "changelog")
    monkeypatch.setattr(module, "github_json", fake_api)
    module.main()
    return calls


def test_publishes_verified_notes_and_refetches(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = run_case(
        [
            release("\n" + SECTION + "\n"),
            release("\n" + SECTION + "\n"),
            release(TARGET),
            release(TARGET),
        ],
        monkeypatch,
    )
    assert [call[1] for call in calls] == ["GET", "GET", "PATCH", "GET"]
    assert '"tag_name": "v1.10.0"' in calls[2][2]


def test_idempotent_rerun_does_not_write(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = run_case([release(TARGET)], monkeypatch)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "bad",
    [
        release("unexpected"),
        release(SECTION, draft=True),
        release(SECTION, published_at=None),
    ],
)
def test_refuses_drift_or_unpublished(
    monkeypatch: pytest.MonkeyPatch, bad: dict
) -> None:
    with pytest.raises(ValueError):
        run_case([bad], monkeypatch)


def test_refuses_state_change_before_patch(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="concurrent modification"):
        run_case([release(SECTION), release(SECTION, draft=True)], monkeypatch)


def test_refuses_failed_post_patch_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="post-update verification"):
        run_case(
            [release(SECTION), release(SECTION), release(TARGET), release("unexpected")],
            monkeypatch,
        )
