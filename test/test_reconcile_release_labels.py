"""Release-please lifecycle proof: publication and immutable tag, no live API."""

from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.repo_tooling
SPEC = importlib.util.spec_from_file_location(
    "reconcile_release_labels",
    Path(__file__).resolve().parents[1] / "scripts/reconcile_release_labels.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "draft,published,tag_sha,expected",
    [
        (False, "2026-10-03", "abc", True),
        (True, "2026-10-03", "abc", False),
        (False, None, "abc", False),
        (False, "2026-10-03", "different", False),
    ],
)
def test_pending_transition_requires_completed_publication(draft, published, tag_sha, expected):
    def api(*args):
        endpoint = args[1]
        if "/contents/" in endpoint:
            return {"content": base64.b64encode(json.dumps({".": "1.9.0"}).encode()).decode()}
        if "/releases/" in endpoint:
            return {"draft": draft, "published_at": published, "tag_name": "v1.9.0"}
        if "/git/ref/" in endpoint:
            return {"object": {"type": "tag", "sha": "annotated"}}
        if "/git/tags/" in endpoint:
            return {"object": {"type": "commit", "sha": tag_sha}}
        if "/workflows/" in endpoint:
            return {"workflow_runs": [{"head_sha": "abc", "conclusion": "success", "id": 123}]}
        return {
            "jobs": [
                {"name": name, "conclusion": "success"}
                for name in ["Tag, GitHub Release and PyPI", "Require a verified release"]
            ]
        }

    assert MODULE.ready("cubrid-lab/pycubrid", "abc", api) is expected


def test_missing_or_invalid_release_facts_remain_pending():
    assert not MODULE.ready("cubrid-lab/pycubrid", "abc", lambda *args: {})
