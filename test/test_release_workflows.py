"""Static contract checks for the automated release workflows (#601).

Parses publish-pypi.yml, release-please.yml and integration-full.yml offline (PyYAML
comes with pre-commit in the dev extra). Shared release behavior across pycubrid,
sqlalchemy-cubrid and cubrid-mcp-server; this repo retains its registered publisher filename.
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
COOKBOOK_SMOKE = re.compile(
    r"^cubrid-lab/cubrid-cookbook-python/\.github/workflows/smoke-test\.yml@[0-9a-f]{40}$"
)
DETECT_SHA = "${{ needs.detect.outputs.sha }}"


def load(name: str) -> dict[str, Any]:
    data = yaml.safe_load((WORKFLOWS / name).read_text())
    # PyYAML reads the bare `on:` key as boolean True.
    data["on"] = data.pop(True, data.get("on"))
    return dict(data)


RELEASE = load("publish-pypi.yml")
PREPARE = load("release-please.yml")
FULL = load("integration-full.yml")


def steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return list(job.get("steps", []))


def checkouts(job: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        s.get("with", {})
        for s in steps(job)
        if str(s.get("uses", "")).startswith("actions/checkout@")
    ]


def test_registered_publisher_is_the_only_release_path() -> None:
    assert (WORKFLOWS / "publish-pypi.yml").exists()
    assert not (WORKFLOWS / "release.yml").exists()
    assert not (WORKFLOWS / "create-release.yml").exists()
    for path in WORKFLOWS.glob("*.yml"):
        text = path.read_text()
        assert "create-release.yml" not in text, path.name
        for job in load(path.name).get("jobs", {}).values():
            if job.get("permissions", {}).get("id-token") == "write":
                assert path.name == "publish-pypi.yml"
                assert job["environment"]["name"] == "pypi"
            for step in steps(job):
                if str(step.get("uses", "")).startswith("pypa/gh-action-pypi-publish@"):
                    assert path.name == "publish-pypi.yml"
                    assert job["environment"]["name"] == "pypi"
                    assert job["permissions"]["id-token"] == "write"
    publish = load("publish-pypi.yml")["jobs"]["publish"]
    assert publish["permissions"]["id-token"] == "write"
    assert publish["environment"]["name"] == "pypi"


def test_release_triggers() -> None:
    on = RELEASE["on"]
    assert set(on) == {"push", "workflow_dispatch"}
    assert on["push"] == {"branches": ["main"]}
    inputs = on["workflow_dispatch"]["inputs"]
    assert inputs["action"]["options"] == ["dry-run", "verify-only", "resume"]
    assert set(inputs) == {"action", "version"}


def test_prepare_release_is_pr_only() -> None:
    assert set(PREPARE["on"]) == {"push", "workflow_dispatch"}
    assert PREPARE["on"]["push"] == {"branches": ["main"]}
    assert not (WORKFLOWS / "prepare-release.yml").exists()
    action = next(
        s
        for s in steps(PREPARE["jobs"]["prepare"])
        if "release-please-action@" in s.get("uses", "")
    )
    assert action["with"]["skip-github-release"] is True
    assert action["if"] == "steps.freeze.outputs.frozen == 'false'"


@pytest.mark.parametrize(
    "workflow", ["publish-pypi.yml", "release-please.yml", "integration-full.yml"]
)
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


@pytest.mark.parametrize("workflow", ["publish-pypi.yml", "release-please.yml"])
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
    "verify-cookbook": {"contents": "read"},
    "require-cookbook": {},
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
    assert job["permissions"] == {"contents": "write", "pull-requests": "write", "actions": "read"}


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
    assert jobs["require-cookbook"]["needs"] == ["detect", "verify-cookbook"]
    assert jobs["summary"]["needs"] == [
        "detect",
        "consistency",
        "matrix",
        "build",
        "publish",
        "verify-cookbook",
        "require-cookbook",
    ]
    for name in ("consistency", "matrix", "build"):
        assert jobs[name]["if"] == "needs.detect.outputs.build == 'true'", name
    # No status function: publish runs only when every earlier job succeeded.
    assert jobs["publish"]["if"] == "needs.detect.outputs.publish == 'true'"
    assert jobs["publish"]["environment"]["name"] == "pypi"
    verify_if = " ".join(jobs["verify-cookbook"]["if"].split())
    # Not always(): cancelling a dry run must not start the cookbook smoke test.
    assert verify_if.startswith("!cancelled() && needs.detect.outputs.verify == 'true' &&")
    assert "needs.publish.result == 'success'" in verify_if
    assert jobs["require-cookbook"]["if"] == (
        "always() && needs.verify-cookbook.result != 'skipped'"
    )
    assert jobs["summary"]["if"] == "always()"


def test_release_content_comes_from_the_detected_sha() -> None:
    jobs = RELEASE["jobs"]
    assert jobs["matrix"]["with"] == {"sha": DETECT_SHA}
    for name in ("consistency", "build"):
        (checkout,) = checkouts(jobs[name])
        assert checkout["ref"] == DETECT_SHA, name
        assert checkout["persist-credentials"] is False
    # Tooling-only jobs sparse-check out their scripts from the workflow commit.
    for name, script in (
        ("publish", "scripts/pypi_duplicate_guard.py\nscripts/check_release_title.py\n"),
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
    # New Releases are titled exactly $TAG; a reused draft or published Release
    # must already carry that title (fail closed, never renamed).
    create = body["Create the draft GitHub Release with the SBOM"]
    assert '--verify-tag --title "$TAG"' in create
    lines = [line.strip() for line in create.splitlines()]
    guard = 'if [ "$drafts" = true ] || [ "$drafts" = false ]; then'
    title = "--jq '.[] | select(.tag_name == env.TAG) | .name // \"\"')"
    check = 'python3 scripts/check_release_title.py --tag "$TAG" --title="$title" --draft "$drafts"'
    # Exact lines: any existing Release (draft or published) is checked, a missing
    # name reads as "" (never as the tag) and a failed check stops the step.
    assert lines.index(guard) < lines.index(title) < lines.index(check)
    assert lines[lines.index(check) + 1] == "fi"
    assert lines.index(check) < lines.index('case "$drafts" in')
    assert create.startswith("set -euo pipefail\n")
    assert "set +e" not in create
    assert "|| true" not in create and "|| :" not in create
    assert "gh release edit" not in create
    assert body["Publish the GitHub Release"] == 'gh release edit "$TAG" --draft=false'
    text = (WORKFLOWS / "publish-pypi.yml").read_text()
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


def test_cookbook_is_verified_through_the_pinned_reusable_workflow() -> None:
    verify = RELEASE["jobs"]["verify-cookbook"]
    assert COOKBOOK_SMOKE.match(verify["uses"]), verify["uses"]
    line = next(
        line
        for line in (WORKFLOWS / "publish-pypi.yml").read_text().splitlines()
        if "cubrid-cookbook-python/.github/workflows/smoke-test.yml@" in line
    )
    assert line.endswith(" # main"), line
    assert verify["permissions"] == {"contents": "read"}
    assert set(verify) == {"name", "needs", "if", "permissions", "uses", "with"}
    assert verify["with"] == {
        "package": "sqlalchemy-cubrid",
        "version": "${{ needs.detect.outputs.version }}",
        "request_id": (
            "sqlalchemy-cubrid-v${{ needs.detect.outputs.version }}-${{ github.run_id }}"
            "-${{ github.run_attempt }}"
        ),
    }
    require = RELEASE["jobs"]["require-cookbook"]
    (step,) = steps(require)
    assert step["env"] == {
        "RESULT": "${{ needs.verify-cookbook.result }}",
        "STATUS": "${{ needs.verify-cookbook.outputs.status }}",
        "REQUESTED": "${{ needs.verify-cookbook.outputs.requested_version }}",
        "INSTALLED": "${{ needs.verify-cookbook.outputs.installed_version }}",
        "ARTIFACT": "${{ needs.verify-cookbook.outputs.artifact }}",
        "VERSION": "${{ needs.detect.outputs.version }}",
    }
    for check in (
        '[ "$RESULT" = success ]',
        '[ "$STATUS" = success ]',
        '[ -n "$INSTALLED" ]',
        '[ "$INSTALLED" = "$REQUESTED" ]',
        '[ "$REQUESTED" = "$VERSION" ]',
        "exit 1",
    ):
        assert check in step["run"], check


def test_no_secrets_or_dispatch_token() -> None:
    text = (WORKFLOWS / "publish-pypi.yml").read_text()
    assert "secrets." not in text and "secrets: inherit" not in text
    assert "COOKBOOK_DISPATCH_TOKEN" not in text
    assert "cookbook_wait" not in text
    assert not (ROOT / "scripts" / "cookbook_wait.py").exists()
    for job in RELEASE["jobs"].values():
        assert "secrets" not in job


def test_recovery_dispatch_is_limited_to_main() -> None:
    validate = steps(RELEASE["jobs"]["detect"])[0]
    assert validate["if"] == "github.event_name == 'workflow_dispatch'"
    assert '[ "$ACTION" != "dry-run" ] && [ "$GITHUB_REF" != "refs/heads/main" ]' in validate["run"]
    assert PREPARE["jobs"]["prepare"]["if"] == "github.ref == 'refs/heads/main'"


def test_prepare_release_composes_checked_notes_with_freeze() -> None:
    runs = "\n".join(s.get("run", "") for s in steps(PREPARE["jobs"]["prepare"]))
    assert (
        runs.index("compose-release.py")
        < runs.index("make release-check")
        < runs.index("push origin")
    )
    assert runs.count("--label 'autorelease: review'") == 2
    assert "release-please--branches--main" in runs
    assert 'git show "$GITHUB_SHA:CHANGELOG.md"' in runs
    assert runs.count('git rev-parse FETCH_HEAD)" != "$GITHUB_SHA"') == 3


def test_integration_full_is_callable_at_a_sha_and_keeps_its_triggers() -> None:
    on = FULL["on"]
    assert set(on) == {"workflow_dispatch", "workflow_call"}
    assert on["workflow_call"]["inputs"]["sha"]["required"] is True
    for name, job in FULL["jobs"].items():
        for checkout in checkouts(job):
            assert checkout["ref"] == "${{ inputs.sha || github.sha }}", name


def test_blocked_publication_fails_preparation_before_release_please() -> None:
    # A blocked release must turn "Prepare release" red instead of hiding behind
    # release-please's own "untagged, merged release PRs outstanding" abort.
    prepare = steps(PREPARE["jobs"]["prepare"])
    names = [s.get("name") or s.get("uses", "") for s in prepare]
    reconcile = prepare[names.index("Reconcile completed external releases")]
    assert reconcile["run"] == "python scripts/reconcile_release_labels.py"
    assert reconcile["if"] == "steps.freeze.outputs.frozen == 'false'"
    assert "continue-on-error" not in reconcile
    release = next(i for i, name in enumerate(names) if "release-please-action" in name)
    assert names.index("Reconcile completed external releases") < release
