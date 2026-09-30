"""Static contract checks for the automated release workflows (#601).

Parses release.yml, prepare-release.yml and integration-full.yml offline (PyYAML
comes with pre-commit in the dev extra). Kept identical across pycubrid,
sqlalchemy-cubrid and cubrid-mcp-server.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
DETECT_SHA = "${{ needs.detect.outputs.sha }}"


def load(name: str) -> dict[str, Any]:
    data = yaml.safe_load((WORKFLOWS / name).read_text())
    # PyYAML reads the bare `on:` key as boolean True.
    data["on"] = data.pop(True, data.get("on"))
    return dict(data)


RELEASE = load("release.yml")
PREPARE = load("prepare-release.yml")
FULL = load("integration-full.yml")


def steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return list(job.get("steps", []))


def checkouts(job: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        s.get("with", {})
        for s in steps(job)
        if str(s.get("uses", "")).startswith("actions/checkout@")
    ]


def test_manual_publish_path_is_gone() -> None:
    assert not (WORKFLOWS / "publish-pypi.yml").exists()
    assert not (WORKFLOWS / "create-release.yml").exists()
    for path in WORKFLOWS.glob("*.yml"):
        text = path.read_text()
        assert "publish-pypi.yml" not in text and "create-release.yml" not in text, path.name


def test_release_triggers() -> None:
    on = RELEASE["on"]
    assert set(on) == {"push", "workflow_dispatch"}
    assert on["push"] == {"branches": ["main"]}
    inputs = on["workflow_dispatch"]["inputs"]
    assert inputs["action"]["options"] == ["dry-run", "verify-only", "resume"]
    assert set(inputs) == {"action", "version", "request_id"}


def test_prepare_release_is_dispatch_only() -> None:
    assert set(PREPARE["on"]) == {"workflow_dispatch"}
    assert set(PREPARE["on"]["workflow_dispatch"]["inputs"]) == {"version"}


@pytest.mark.parametrize("workflow", ["release.yml", "prepare-release.yml", "integration-full.yml"])
def test_actions_are_sha_pinned(workflow: str) -> None:
    data = load(workflow)
    for name, job in data["jobs"].items():
        if "uses" in job:
            # integration-full.yml also calls the SHA-pinned org live-smoke workflow.
            local = job["uses"] == "./.github/workflows/integration-full.yml"
            assert local or PINNED.match(job["uses"]), name
        for step in steps(job):
            if "uses" in step:
                assert PINNED.match(step["uses"]), (name, step["uses"])


@pytest.mark.parametrize("workflow", ["release.yml", "prepare-release.yml"])
def test_no_expression_interpolation_in_run(workflow: str) -> None:
    # Inputs, outputs and secrets reach shell code only through env:.
    for name, job in load(workflow)["jobs"].items():
        for step in steps(job):
            assert "${{" not in step.get("run", ""), (name, step.get("name"))


EXPECTED_PERMISSIONS = {
    "detect": {"contents": "read"},
    "consistency": {"contents": "read"},
    "matrix": {"contents": "read"},
    "build": {"contents": "read"},
    "publish": {"contents": "write", "id-token": "write"},
    "verify-cookbook": {"contents": "read", "actions": "read"},
    "summary": {"contents": "read"},
}


def test_release_permissions_are_minimal_per_job() -> None:
    assert RELEASE["permissions"] == {}
    jobs = RELEASE["jobs"]
    assert set(jobs) == set(EXPECTED_PERMISSIONS)
    for name, expected in EXPECTED_PERMISSIONS.items():
        assert jobs[name]["permissions"] == expected, name


def test_prepare_permissions() -> None:
    assert PREPARE["permissions"] == {}
    (job,) = PREPARE["jobs"].values()
    assert job["permissions"] == {"contents": "write", "pull-requests": "write"}


def test_concurrency_never_cancels_a_release() -> None:
    assert RELEASE["concurrency"]["cancel-in-progress"] is False
    assert "inputs.version" in RELEASE["concurrency"]["group"]
    assert "github.sha" in RELEASE["concurrency"]["group"]
    publish = RELEASE["jobs"]["publish"]["concurrency"]
    assert publish == {
        "group": "release-publish-${{ needs.detect.outputs.tag }}",
        "cancel-in-progress": False,
    }
    assert PREPARE["concurrency"]["cancel-in-progress"] is False
    assert FULL["concurrency"]["cancel-in-progress"] == "${{ !inputs.sha }}"
    assert "inputs.sha" in FULL["concurrency"]["group"]


def test_job_graph() -> None:
    jobs = RELEASE["jobs"]
    assert "needs" not in jobs["detect"]
    assert jobs["consistency"]["needs"] == ["detect"]
    assert jobs["matrix"]["needs"] == ["detect", "consistency"]
    assert jobs["build"]["needs"] == ["detect", "matrix"]
    assert jobs["publish"]["needs"] == ["detect", "consistency", "matrix", "build"]
    assert jobs["verify-cookbook"]["needs"] == ["detect", "build", "publish"]
    assert jobs["summary"]["needs"] == [
        "detect",
        "consistency",
        "matrix",
        "build",
        "publish",
        "verify-cookbook",
    ]
    for name in ("consistency", "matrix", "build"):
        assert jobs[name]["if"] == "needs.detect.outputs.build == 'true'", name
    # No status function: publish runs only when every earlier job succeeded.
    assert jobs["publish"]["if"] == "needs.detect.outputs.publish == 'true'"
    assert jobs["publish"]["environment"]["name"] == "pypi"
    verify_if = " ".join(jobs["verify-cookbook"]["if"].split())
    # Not always(): cancelling a dry run must not dispatch the cookbook.
    assert verify_if.startswith("!cancelled() && needs.detect.outputs.verify == 'true' &&")
    assert "needs.publish.result == 'success'" in verify_if
    assert jobs["summary"]["if"] == "always()"


def test_release_content_comes_from_the_detected_sha() -> None:
    jobs = RELEASE["jobs"]
    assert jobs["matrix"]["with"] == {"sha": DETECT_SHA}
    for name in ("consistency", "build"):
        (checkout,) = checkouts(jobs[name])
        assert checkout["ref"] == DETECT_SHA, name
        assert checkout["persist-credentials"] is False
    # Tooling-only jobs sparse-check out one script from the workflow commit.
    for name, script in (
        ("publish", "scripts/pypi_duplicate_guard.py"),
        ("verify-cookbook", "scripts/cookbook_wait.py"),
        ("summary", "scripts/release_summary.py"),
    ):
        (checkout,) = checkouts(jobs[name])
        assert checkout == {
            "ref": "${{ github.sha }}",
            "sparse-checkout": script,
            "sparse-checkout-cone-mode": False,
            "persist-credentials": False,
        }, name
    for job in jobs.values():
        for checkout in checkouts(job):
            assert checkout.get("persist-credentials") is False


def test_publish_order_tag_draft_pypi_undraft() -> None:
    names = [s.get("name", s.get("uses", "")) for s in steps(RELEASE["jobs"]["publish"])]
    order = [
        "Check the distribution against the recorded hashes",
        "Create the annotated tag",
        "Create the draft GitHub Release with the SBOM",
        "Compare dist/ with files already on PyPI",
        "Publish to PyPI",
        "Publish the GitHub Release",
    ]
    assert [n for n in names if n in order] == order
    body = {s.get("name"): s.get("run", "") for s in steps(RELEASE["jobs"]["publish"])}
    assert "tags are never moved" in body["Create the annotated tag"]
    assert (
        'gh release create "$TAG" --draft --verify-tag'
        in body["Create the draft GitHub Release with the SBOM"]
    )
    # An API error must fail the step, never read as "no Release yet".
    assert "2>/dev/null" not in body["Create the draft GitHub Release with the SBOM"]
    assert body["Publish the GitHub Release"] == 'gh release edit "$TAG" --draft=false'
    text = (WORKFLOWS / "release.yml").read_text()
    assert (
        "gh release delete" not in text
        and "git push --delete" not in text
        and ":refs/tags/" not in text
    )


def test_build_once_with_hashes_and_recoverable_artifacts() -> None:
    build = steps(RELEASE["jobs"]["build"])
    runs = "\n".join(s.get("run", "") for s in build)
    assert runs.count("python -m build") == 1
    assert "twine check dist/*" in runs
    assert "sha256sum" in runs
    uploads = [
        s["with"] for s in build if str(s.get("uses", "")).startswith("actions/upload-artifact@")
    ]
    assert {u["name"] for u in uploads} == {"release-dist", "release-meta"}
    assert all(u["retention-days"] == 14 for u in uploads)
    publish_runs = "\n".join(s.get("run", "") for s in steps(RELEASE["jobs"]["publish"]))
    assert "python -m build" not in publish_runs


def test_dispatch_token_only_in_the_verify_job() -> None:
    for name, job in RELEASE["jobs"].items():
        uses_secret = "secrets." in str(job)
        assert uses_secret == (name == "verify-cookbook"), name
    verify = steps(RELEASE["jobs"]["verify-cookbook"])
    wait = next(s for s in verify if s.get("id") == "wait")
    assert wait["continue-on-error"] is True
    assert wait["env"]["COOKBOOK_DISPATCH_TOKEN"] == "${{ secrets.COOKBOOK_DISPATCH_TOKEN }}"
    final = verify[-1]["run"]
    assert "incomplete)" in final and "exit 1" in final


def test_recovery_dispatch_is_limited_to_main() -> None:
    validate = steps(RELEASE["jobs"]["detect"])[0]
    assert validate["if"] == "github.event_name == 'workflow_dispatch'"
    assert '[ "$ACTION" != "dry-run" ] && [ "$GITHUB_REF" != "refs/heads/main" ]' in validate["run"]
    prepare = steps(next(iter(PREPARE["jobs"].values())))[0]["run"]
    assert '"$GITHUB_REF" != "refs/heads/main"' in prepare


def test_prepare_release_opens_a_checked_pr() -> None:
    runs = "\n".join(s.get("run", "") for s in steps(next(iter(PREPARE["jobs"].values()))))
    assert (
        runs.index("scripts/prepare_release.py")
        < runs.index("make release-check")
        < runs.index("gh pr create")
    )
    assert '--title "chore: release v$VERSION"' in runs
    assert 'branch="release/v$VERSION"' in runs


def test_integration_full_is_callable_at_a_sha_and_keeps_its_triggers() -> None:
    on = FULL["on"]
    assert set(on) == {"schedule", "workflow_dispatch", "workflow_call"}
    assert on["workflow_call"]["inputs"]["sha"]["required"] is True
    for name, job in FULL["jobs"].items():
        for checkout in checkouts(job):
            assert checkout["ref"] == "${{ inputs.sha || github.sha }}", name
