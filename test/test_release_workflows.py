"""Static contract checks for the automated release workflows (#601).

Parses publish-pypi.yml, release-please.yml and integration-full.yml offline (PyYAML
comes from the test dependency group). Shared release behavior across pycubrid,
sqlalchemy-cubrid and cubrid-mcp-server; this repo retains its registered publisher filename.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
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
COOKBOOK_REF = re.compile(r"cubrid-cookbook-python/\.github/workflows/smoke-test\.yml@(\S*)")
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
    "verify-candidate": {"contents": "read"},
    "require-candidate": {},
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
    assert jobs["verify-candidate"]["needs"] == ["detect", "build"]
    assert jobs["require-candidate"]["needs"] == ["detect", "build", "verify-candidate"]
    assert jobs["publish"]["needs"] == [
        "detect",
        "consistency",
        "matrix",
        "build",
        "require-candidate",
    ]
    assert jobs["verify-cookbook"]["needs"] == ["detect", "build", "publish"]
    assert jobs["require-cookbook"]["needs"] == ["detect", "verify-cookbook"]
    assert jobs["summary"]["needs"] == [
        "detect",
        "consistency",
        "matrix",
        "build",
        "verify-candidate",
        "require-candidate",
        "publish",
        "verify-cookbook",
        "require-cookbook",
    ]
    for name in ("consistency", "matrix", "build"):
        assert jobs[name]["if"] == "needs.detect.outputs.build == 'true'", name
    # The candidate gate runs after every successful build: dry run, push and
    # resume alike. Builds are not reproducible, so a resume (which rebuilds)
    # never inherits an earlier run's verification; there is no tag-state skip.
    assert jobs["verify-candidate"]["if"] == "needs.build.result == 'success'"
    for name in ("verify-candidate", "require-candidate", "publish"):
        assert "tag_state" not in str(jobs[name].get("if", "")), name
    # A status function, so a failed verify-candidate still reaches the gate,
    # which lists every failed check.
    assert jobs["require-candidate"]["if"] == "!cancelled() && needs.build.result == 'success'"
    # !cancelled() plus explicit results: only these results gate publish.
    assert " ".join(jobs["publish"]["if"].split()) == (
        "!cancelled() && needs.detect.outputs.publish == 'true' && "
        "needs.consistency.result == 'success' && needs.matrix.result == 'success' && "
        "needs.build.result == 'success' && needs.require-candidate.result == 'success'"
    )
    assert jobs["publish"]["environment"]["name"] == "pypi"
    verify_if = " ".join(jobs["verify-cookbook"]["if"].split())
    # Not always(): cancelling a run must not start the cookbook smoke test. A dry
    # run publishes nothing, so only verify-candidate verifies it.
    assert verify_if == (
        "!cancelled() && needs.detect.outputs.verify == 'true' && "
        "(needs.publish.result == 'success' || needs.detect.outputs.mode == 'verify-only')"
    )
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
        (
            "publish",
            "scripts/pypi_duplicate_guard.py\nscripts/check_release_title.py\n"
            "scripts/verify_dist.py\n",
        ),
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
        "Check dist/ and release-meta/ against the build job outputs",
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
    assert RELEASE["jobs"]["build"]["outputs"] == {
        "sha256": "${{ steps.hashes.outputs.sha256 }}",
        "meta_sha256": "${{ steps.hashes.outputs.meta_sha256 }}",
    }
    (hashes,) = [s for s in build if s.get("id") == "hashes"]
    assert '("meta_sha256", "release-meta")' in hashes["run"]
    # Nothing writes to release-meta/ after its digests are recorded.
    after = build[build.index(hashes) + 1 :]
    assert all("release-meta" not in s.get("run", "") for s in after)


def test_publish_checks_artifacts_against_the_build_job_outputs() -> None:
    publish = steps(RELEASE["jobs"]["publish"])
    (check,) = [
        s
        for s in publish
        if s.get("name") == "Check dist/ and release-meta/ against the build job outputs"
    ]
    assert check["env"] == {
        "DIST_SHA256": "${{ needs.build.outputs.sha256 }}",
        "META_SHA256": "${{ needs.build.outputs.meta_sha256 }}",
    }
    assert check["run"].splitlines() == [
        "python3 scripts/verify_dist.py --dir dist --expected-env DIST_SHA256",
        "python3 scripts/verify_dist.py --dir release-meta --expected-env META_SHA256",
    ]
    names = [s.get("name", "") for s in publish]
    assert names.index("Download the verified distribution") < names.index(check["name"])
    assert names.index("Download release notes, SBOM and hashes") < names.index(check["name"])
    # Before the tag and anything public; before the guard trims dist/.
    assert names.index(check["name"]) < names.index("Create the annotated tag")
    assert names.index(check["name"]) < names.index("Compare dist/ with files already on PyPI")


def test_every_cookbook_reference_uses_one_pinned_main_commit() -> None:
    lines = [
        line
        for line in (WORKFLOWS / "publish-pypi.yml").read_text().splitlines()
        if "cubrid-cookbook-python/.github/workflows/smoke-test.yml@" in line
    ]
    assert len(lines) == 2, lines
    for line in lines:
        assert line.endswith(" # main"), line
    refs = {match.group(1) for line in lines for match in COOKBOOK_REF.finditer(line)}
    assert len(refs) == 1, refs
    (ref,) = refs
    assert re.fullmatch(r"[0-9a-f]{40}", ref), ref
    for name in ("verify-candidate", "verify-cookbook"):
        uses = RELEASE["jobs"][name]["uses"]
        assert COOKBOOK_SMOKE.match(uses), (name, uses)
        assert uses.endswith("@" + ref), (name, uses)


def test_candidate_is_verified_before_publish_through_the_same_workflow() -> None:
    verify = RELEASE["jobs"]["verify-candidate"]
    assert verify["permissions"] == {"contents": "read"}
    assert set(verify) == {"name", "needs", "if", "permissions", "uses", "with"}
    assert verify["with"] == {
        "package": "sqlalchemy-cubrid",
        "version": "${{ needs.detect.outputs.version }}",
        "request_id": "sqlalchemy-cubrid-rc-v${{ needs.detect.outputs.version }}-${{ github.run_id }}",
        "mode": "candidate",
        "candidate_artifact": "release-dist",
        "candidate_hashes": "${{ needs.build.outputs.sha256 }}",
        "candidate_source_sha": DETECT_SHA,
    }
    # Stable across attempts, so `gh run rerun --failed` replaces only the
    # failed cells' parts; `--` is reserved by the cookbook part names.
    assert "run_attempt" not in verify["with"]["request_id"]
    assert "--" not in verify["with"]["request_id"]
    uploads = [
        s["with"]["name"]
        for s in steps(RELEASE["jobs"]["build"])
        if str(s.get("uses", "")).startswith("actions/upload-artifact@")
    ]
    assert verify["with"]["candidate_artifact"] in uploads
    # publish uploads the same artifact the cookbook verified, never a rebuild.
    downloads = [
        s["with"]["name"]
        for s in steps(RELEASE["jobs"]["publish"])
        if str(s.get("uses", "")).startswith("actions/download-artifact@")
    ]
    assert verify["with"]["candidate_artifact"] in downloads


def require_steps() -> tuple[dict[str, Any], dict[str, Any]]:
    download, check = steps(RELEASE["jobs"]["require-candidate"])
    return download, check


def test_require_candidate_reads_the_report_of_this_request() -> None:
    require = RELEASE["jobs"]["require-candidate"]
    assert require["permissions"] == {}
    download, _ = require_steps()
    assert str(download["uses"]).startswith("actions/download-artifact@")
    # A missing report must not hide the diagnostics: the check step still runs
    # and fails on it with every other failed check.
    assert "if" not in download
    assert download["continue-on-error"] is True
    assert download["id"] == "download"
    # Named from this run's own request_id, never from a call output.
    request_id = RELEASE["jobs"]["verify-candidate"]["with"]["request_id"]
    assert download["with"] == {
        "name": "release-candidate-verification-${{ env.PACKAGE }}-rc-v"
        "${{ needs.detect.outputs.version }}-${{ github.run_id }}",
        "path": "candidate-report/",
    }
    assert request_id.replace(RELEASE["env"]["PACKAGE"], "${{ env.PACKAGE }}", 1) == (
        download["with"]["name"].removeprefix("release-candidate-verification-")
    )


def test_require_candidate_parses_the_outputs_through_env() -> None:
    _, step = require_steps()
    assert step["env"] == {
        "RESULT": "${{ needs.verify-candidate.result }}",
        "STATUS": "${{ needs.verify-candidate.outputs.status }}",
        "EVIDENCE": "${{ needs.verify-candidate.outputs.evidence }}",
        "REQUESTED": "${{ needs.verify-candidate.outputs.requested_version }}",
        "INSTALLED": "${{ needs.verify-candidate.outputs.installed_version }}",
        "CANDIDATE_SHA256": "${{ needs.verify-candidate.outputs.candidate_sha256 }}",
        "ARTIFACT": "${{ needs.verify-candidate.outputs.artifact }}",
        "DIST_SHA256": "${{ needs.build.outputs.sha256 }}",
        "VERSION": "${{ needs.detect.outputs.version }}",
        "SHA": DETECT_SHA,
        "DOWNLOAD_OUTCOME": "${{ steps.download.outcome }}",
    }
    run = step["run"]
    assert "${{" not in run
    # No pass without a verified candidate: no early exit, no skip branch.
    assert run.startswith("python3 - <<'PY'\n")
    assert "exit 0" not in run and "skipped" not in run
    for check in (
        'run.get("caller_repository")',
        'env["GITHUB_REPOSITORY"]',
        'hashes = json.loads(env["DIST_SHA256"])',
        'candidate.get("files") == hashes',
        'candidate.get("source_sha") == env["SHA"]',
        "sys.exit(1)",
    ):
        assert check in run, check
    # The candidate artifact name the report must carry is the one passed in.
    candidate_artifact = RELEASE["jobs"]["verify-candidate"]["with"]["candidate_artifact"]
    assert f'== "{candidate_artifact}"' in run


def test_cookbook_is_verified_through_the_pinned_reusable_workflow() -> None:
    verify = RELEASE["jobs"]["verify-cookbook"]
    assert COOKBOOK_SMOKE.match(verify["uses"]), verify["uses"]
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


# The freeze and compose/push steps of release-please.yml are shared verbatim by
# pycubrid, sqlalchemy-cubrid and cubrid-mcp-server, and so are these tests (#801).
REVIEW_COUNT = (
    "count=$(gh pr list --state open --base main --limit 100"
    " --label 'autorelease: review' --json number --jq 'length')"
)
STALE_MAIN = 'if [ "$(git rev-parse FETCH_HEAD)" != "$GITHUB_SHA" ]; then'
PUSH = 'git -c "http.https://github.com/.extraheader=AUTHORIZATION: basic $auth" push origin "HEAD:refs/heads/$branch"'  # noqa: E501


def prepare_step(name: str) -> list[str]:
    (step,) = [s for s in steps(PREPARE["jobs"]["prepare"]) if s.get("name") == name]
    return [line.strip() for line in step["run"].splitlines()]


def test_release_please_checkout_does_not_persist_credentials() -> None:
    (checkout,) = checkouts(PREPARE["jobs"]["prepare"])
    assert checkout == {"persist-credentials": False}


def test_release_please_freeze_uses_the_review_label() -> None:
    lines = prepare_step("Freeze reviewed release PRs")
    assert lines[lines.index(STALE_MAIN) + 1] == (
        "echo '::error::Stale generator run; wait for current main'; exit 1"
    )
    i = lines.index(REVIEW_COUNT)
    assert lines[i + 1 : i + 4] == [
        'if [ "$count" != 0 ]; then',
        "echo 'frozen=true' >> \"$GITHUB_OUTPUT\"",
        "echo 'Release preparation frozen: remove autorelease: review only when regeneration is safe.'",  # noqa: E501
    ]


def test_release_please_only_touches_its_own_branch() -> None:
    lines = prepare_step("Compose and validate reviewed release notes")
    assert lines[0] == "set -euo pipefail"
    guard = lines.index(
        'case "$branch" in release-please--branches--main*) ;; '
        "*) echo '::error::Unexpected release branch'; exit 1 ;; esac"
    )
    assert lines[guard - 1].startswith("branch=$(")
    assert lines[guard + 1 : guard + 5] == [
        "git fetch origin main",
        STALE_MAIN,
        "echo '::error::Main changed during generation; wait for the queued run'; exit 1",
        "fi",
    ]
    assert guard < lines.index('git checkout -B "$branch" FETCH_HEAD')


def test_release_please_push_is_guarded_by_stale_main_and_review_checks() -> None:
    lines = prepare_step("Compose and validate reviewed release notes")
    assert sum(" push " in line for line in lines) == 1
    push = lines.index(PUSH)
    assert lines[push - 8 : push] == [
        'git commit -m "chore: curate release notes for v$version"',
        "git fetch origin main",
        STALE_MAIN,
        "echo '::error::Main changed before push; refusing stale notes'; exit 1",
        "fi",
        REVIEW_COUNT,
        "if [ \"$count\" != 0 ]; then echo '::error::Review freeze applied; refusing push'; exit 1; fi",  # noqa: E501
        "auth=$(printf 'x-access-token:%s' \"$GH_TOKEN\" | base64 -w0)",
    ]


def test_release_please_rewrites_generated_references_in_the_pr_body() -> None:
    # The bot-written PR body keeps release-please's ", closes [#N]" wording, which
    # GitHub treats as closing keywords; the composer rewrites it right after
    # release-please, before composition.
    prepare = steps(PREPARE["jobs"]["prepare"])
    names = [s.get("name") for s in prepare]
    body = prepare[names.index("Rewrite generated references in the release PR body")]
    # Directly after release-please, so a failed composition cannot leave the body.
    release = next(i for i, s in enumerate(prepare) if "release-please-action" in s.get("uses", ""))
    rewrite = names.index("Rewrite generated references in the release PR body")
    assert release < rewrite < names.index("Compose and validate reviewed release notes")
    assert body["if"] == "steps.release.outputs.pr != ''"
    lines = prepare_step("Rewrite generated references in the release PR body")
    assert lines[0] == "set -euo pipefail"
    assert lines[2] == (
        "if [ \"$number\" -le 0 ]; then echo 'No release PR number; nothing to rewrite'; exit 0; fi"
    )
    # The composer comes from main's checkout, never from the release branch.
    assert lines[3] == "cp scripts/compose_release_changelog.py /tmp/compose-release-body.py"
    assert (
        "python /tmp/compose-release-body.py --pr-body /tmp/release-pr.json"
        " --output /tmp/release-pr-body.json"
    ) in lines
    patch = next(i for i, line in enumerate(lines) if "gh api -X PATCH" in line)
    assert lines[patch - 1] == "if [ -s /tmp/release-pr-body.json ]; then"
    assert "--input /tmp/release-pr-body.json" in lines[patch]
    assert PREPARE["jobs"]["prepare"]["permissions"] == {
        "contents": "write",
        "pull-requests": "write",
        "actions": "read",
    }


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
    assert "if" not in reconcile and "continue-on-error" not in reconcile
    release = next(i for i, name in enumerate(names) if "release-please-action" in name)
    assert names.index("Reconcile completed external releases") < release
    assert names.index("Reconcile completed external releases") < names.index(
        "Freeze reviewed release PRs"
    )


WHEEL_SHA = "1" * 64
RUN_ID = "4242"
SOURCE_SHA = "c" * 40
PACKAGE_UNDERSCORE = RELEASE["env"]["PACKAGE"].replace("-", "_")
DIST = {
    f"{PACKAGE_UNDERSCORE}-1.9.0-py3-none-any.whl": WHEEL_SHA,
    f"{PACKAGE_UNDERSCORE}-1.9.0.tar.gz": "2" * 64,
}
REQUEST_ID = f"{RELEASE['env']['PACKAGE']}-rc-v1.9.0-{RUN_ID}"
GOOD_CANDIDATE = {
    "RESULT": "success",
    "STATUS": "success",
    "EVIDENCE": "candidate artifact",
    "REQUESTED": "1.9.0",
    "INSTALLED": "1.9.0",
    "CANDIDATE_SHA256": WHEEL_SHA,
    "ARTIFACT": f"release-candidate-verification-{REQUEST_ID}",
    "DIST_SHA256": json.dumps(DIST),
    "VERSION": "1.9.0",
    "SHA": SOURCE_SHA,
    "DOWNLOAD_OUTCOME": "success",
}
REPOSITORY = "cubrid-lab/example"


def good_report() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "request_id": REQUEST_ID,
        "package": RELEASE["env"]["PACKAGE"],
        "requested_version": "1.9.0",
        "installed_version": "1.9.0",
        "status": "success",
        "reasons": [],
        "evidence": "candidate artifact",
        "run": {"id": RUN_ID, "attempt": "1", "caller_repository": REPOSITORY},
        "candidate": {
            "artifact": "release-dist",
            "wheel": f"{PACKAGE_UNDERSCORE}-1.9.0-py3-none-any.whl",
            "source_sha": SOURCE_SHA,
            "files": dict(DIST),
            "expected_sha256": WHEEL_SHA,
            "candidate_sha256": WHEEL_SHA,
        },
    }


def run_require_candidate(
    tmp_path: Path, report: Any = None, **overrides: str
) -> subprocess.CompletedProcess[str]:
    _, step = require_steps()
    if report is not None:
        (tmp_path / "candidate-report").mkdir()
        text = report if isinstance(report, str) else json.dumps(report)
        (tmp_path / "candidate-report" / "release-verification.json").write_text(text)
    env = {
        "PATH": os.environ["PATH"],
        "PACKAGE": RELEASE["env"]["PACKAGE"],
        "GITHUB_RUN_ID": RUN_ID,
        "GITHUB_REPOSITORY": REPOSITORY,
        **GOOD_CANDIDATE,
        **overrides,
    }
    return subprocess.run(
        ["bash", "-e", "-c", step["run"]],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )


def test_require_candidate_passes_the_built_wheel(tmp_path: Path) -> None:
    result = run_require_candidate(tmp_path, good_report())
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"sha256 {WHEEL_SHA} from {SOURCE_SHA}" in result.stdout


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"CANDIDATE_SHA256": "0" * 64}, id="bad-digest"),
        pytest.param({"CANDIDATE_SHA256": ""}, id="no-digest"),
        pytest.param({"RESULT": "failure"}, id="call-failed"),
        pytest.param({"RESULT": "skipped"}, id="call-skipped"),
        pytest.param({"RESULT": "cancelled"}, id="call-cancelled"),
        pytest.param({"GITHUB_REPOSITORY": "someone/fork"}, id="other-repository"),
        # The action can extract the report before failing its digest check.
        pytest.param({"DOWNLOAD_OUTCOME": "failure"}, id="download-failed-after-extract"),
        pytest.param({"DOWNLOAD_OUTCOME": ""}, id="download-not-run"),
        pytest.param({"STATUS": "failure"}, id="status-failure"),
        pytest.param({"EVIDENCE": "published package"}, id="published-evidence"),
        pytest.param({"INSTALLED": "1.8.0"}, id="installed-differs"),
        pytest.param({"INSTALLED": ""}, id="installed-empty"),
        pytest.param({"REQUESTED": "1.8.0", "INSTALLED": "1.8.0"}, id="not-the-release"),
        pytest.param({"ARTIFACT": "release-candidate-verification-other"}, id="other-report"),
        pytest.param({"SHA": "d" * 40}, id="other-source-commit"),
        pytest.param({"GITHUB_RUN_ID": "1"}, id="other-run"),
        pytest.param({"DIST_SHA256": "not json"}, id="map-not-json"),
        pytest.param({"DIST_SHA256": "[]"}, id="map-not-object"),
        pytest.param({"DIST_SHA256": json.dumps({"x.tar.gz": WHEEL_SHA})}, id="no-wheel"),
        pytest.param(
            {"DIST_SHA256": json.dumps({"a-1.9.0-py3-none-any.whl": WHEEL_SHA})},
            id="wheel-of-another-package",
        ),
    ],
)
def test_require_candidate_fails_closed(tmp_path: Path, overrides: dict[str, str]) -> None:
    result = run_require_candidate(tmp_path, good_report(), **overrides)
    assert result.returncode != 0, result.stdout
    assert "::error::Candidate verification failed" in result.stdout, result.stderr


def _report(path: str, value: Any) -> dict[str, Any]:
    report = good_report()
    target = report
    *parents, key = path.split(".")
    for parent in parents:
        target = target[parent]
    target[key] = value
    return report


@pytest.mark.parametrize(
    "report",
    [
        pytest.param(None, id="report-missing"),
        pytest.param("not json", id="report-not-json"),
        pytest.param([], id="report-not-object"),
        pytest.param(_report("package", "sqlalchemy-cubrid-x"), id="report-other-package"),
        pytest.param(_report("request_id", "x-rc-v1.9.0-4242"), id="report-other-request"),
        pytest.param(_report("requested_version", "1.8.0"), id="report-other-version"),
        pytest.param(_report("installed_version", None), id="report-not-installed"),
        pytest.param(_report("status", "failure"), id="report-failure"),
        pytest.param(_report("evidence", "published package"), id="report-published"),
        pytest.param(_report("run.id", "1"), id="report-other-run"),
        pytest.param(_report("run.caller_repository", "someone/fork"), id="report-other-repo"),
        pytest.param(_report("run.caller_repository", None), id="report-no-repo"),
        pytest.param(_report("candidate", None), id="report-no-candidate"),
        pytest.param(_report("candidate.artifact", "other-dist"), id="report-other-artifact"),
        pytest.param(_report("candidate.source_sha", "d" * 40), id="report-other-source"),
        pytest.param(_report("candidate.files", {"x.whl": WHEEL_SHA}), id="report-other-files"),
        pytest.param(
            _report("candidate.wheel", "x-1.9.0-py3-none-any.whl"), id="report-other-wheel"
        ),
        pytest.param(_report("candidate.candidate_sha256", None), id="report-unverified"),
    ],
)
def test_require_candidate_fails_closed_on_the_report(tmp_path: Path, report: Any) -> None:
    result = run_require_candidate(tmp_path, report)
    assert result.returncode != 0, result.stdout
    assert "::error::Candidate verification failed" in result.stdout, result.stderr


def test_require_candidate_never_passes_without_a_call(tmp_path: Path) -> None:
    # A skipped call (formerly the tagged-resume pass) fails like any other.
    result = run_require_candidate(tmp_path, None, RESULT="skipped", CANDIDATE_SHA256="")
    assert result.returncode != 0, result.stdout
    assert "::error::Candidate verification failed" in result.stdout, result.stderr


def test_missing_report_lists_every_failed_check(tmp_path: Path) -> None:
    result = run_require_candidate(tmp_path, None)
    assert result.returncode != 0
    (error,) = [line for line in result.stdout.splitlines() if line.startswith("::error::")]
    for check in ("report names this package", "report files == build job map"):
        assert check in error, error
