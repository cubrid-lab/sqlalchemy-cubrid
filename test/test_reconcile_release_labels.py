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
    "draft,published,tag_sha,run_sha,run_conclusion,job_names,expected",
    [
        (False, "2026-10-03", "abc", "abc", "success", "complete", True),
        (True, "2026-10-03", "abc", "abc", "success", "complete", False),
        (False, None, "abc", "abc", "success", "complete", False),
        (False, "2026-10-03", "different", "abc", "success", "complete", False),
        (False, "2026-10-03", "abc", "different", "success", "complete", False),
        (False, "2026-10-03", "abc", "abc", "failure", "complete", False),
        (False, "2026-10-03", "abc", "abc", "success", "publish-only", False),
        (False, "2026-10-03", "abc", "abc", "success", "legacy", False),
    ],
)
def test_pending_transition_requires_completed_publication(
    draft, published, tag_sha, run_sha, run_conclusion, job_names, expected
):
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
            assert endpoint == (
                "repos/cubrid-lab/pycubrid/actions/workflows/publish-pypi.yml/runs"
                "?head_sha=abc&per_page=100"
            )
            return {
                "workflow_runs": [{"head_sha": run_sha, "conclusion": run_conclusion, "id": 123}]
            }
        assert endpoint == "repos/cubrid-lab/pycubrid/actions/runs/123/jobs?per_page=100"
        names = {
            "complete": ["Tag, GitHub Release and PyPI", "Require a verified release"],
            "publish-only": ["Tag, GitHub Release and PyPI"],
            # This filename was used by the old publish-only workflow too.
            "legacy": ["Publish to PyPI"],
        }[job_names]
        return {"jobs": [{"name": name, "conclusion": "success"} for name in names]}

    assert MODULE.ready("cubrid-lab/pycubrid", "abc", api) is expected


def test_missing_or_invalid_release_facts_remain_pending():
    assert not MODULE.ready("cubrid-lab/pycubrid", "abc", lambda *args: {})
