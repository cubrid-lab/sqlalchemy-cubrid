#!/usr/bin/env python3
"""Clear release-please pending labels only after the guarded publisher finishes.

release-please PR-only mode does not mark merged PRs tagged. Verify immutable
tag ownership and an actually published GitHub Release before that transition.
Missing/partial publication remains pending and prevents another candidate.

A pending PR that cannot be marked tagged is classified so the block is
visible: while its publisher is still running (or has not started shortly
after the merge) the run emits a notice and stays green; once the publisher
failed, or never ran long after the merge, the run emits an error with the
recovery and exits non-zero. Nothing is relabelled, rerun or dispatched.

It also checks the lifecycle of a top-level ``last-release-sha`` override in
``release-please-config.json`` (#945), the temporary baseline for an abandoned
version (RELEASING.md, "A merged X.Y.Z is abandoned"). The override must be
the merge of a release PR on main whose abandonment is recorded: no
``autorelease: pending`` or ``autorelease: tagged`` label, an ``abandon``
comment, and no tag for its version. It stays valid until a later version
whose tag contains it is proven published, as for the pending transition;
then it is obsolete and preparation stops until a normal PR removes it. An
invalid override, and release facts that cannot be read, also stop
preparation. Nothing is edited: no configuration, tag or label.
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
from datetime import UTC, datetime, timedelta

# A merge with no publish-pypi.yml run yet is normal right after the merge (the
# push event may not have created the run). The publisher is created within
# seconds and runs well under an hour, so after this window a missing run is a
# block, not latency. Queued/in-progress runs are never blocked by age.
PUBLISHER_START_GRACE = timedelta(hours=2)
IN_PROGRESS = "in-progress"
BLOCKED = "blocked"


def gh(*args: str) -> object:
    result = subprocess.run(["gh", *args], check=True, text=True, capture_output=True)
    return json.loads(result.stdout) if result.stdout.strip() else None


def ready(repository: str, sha: str, api=gh, strict: bool = False) -> bool:
    """Fail closed on absent/partial/mismatched release facts.

    With ``strict``, only a 404 counts as absent: any other read or parse
    failure is raised, so the caller can report it as unresolved (#945).
    """
    try:
        blob = api("api", f"repos/{repository}/contents/.release-please-manifest.json?ref={sha}")
        manifest = json.loads(base64.b64decode(blob["content"]))
        version = manifest["."]
        if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
            return False
        tag = "v" + version
        release = api("api", f"repos/{repository}/releases/tags/{tag}")
        if release["draft"] or not release.get("published_at") or release["tag_name"] != tag:
            return False
        ref = api("api", f"repos/{repository}/git/ref/tags/{tag}")["object"]
        if ref["type"] == "tag":
            ref = api("api", f"repos/{repository}/git/tags/{ref['sha']}")["object"]
        if ref["type"] != "commit" or ref["sha"] != sha:
            return False
        runs = api(
            "api",
            f"repos/{repository}/actions/workflows/publish-pypi.yml/runs?head_sha={sha}&per_page=100",
        )
        for run in runs["workflow_runs"]:
            if run.get("head_sha") != sha or run.get("conclusion") != "success":
                continue
            jobs = api("api", f"repos/{repository}/actions/runs/{run['id']}/jobs?per_page=100")
            successful = {job["name"] for job in jobs["jobs"] if job.get("conclusion") == "success"}
            if {"Tag, GitHub Release and PyPI", "Require a verified release"} <= successful:
                return True
        return False
    except subprocess.CalledProcessError as exc:
        if strict and not _absent(exc):
            raise
        return False
    except (KeyError, ValueError, TypeError):
        if strict:
            raise
        return False


def _absent(exc: subprocess.CalledProcessError) -> bool:
    """A 404 proves absence; any other failure proves nothing."""
    return "HTTP 404" in (exc.stderr or "")


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _age(delta: timedelta) -> str:
    minutes = max(int(delta.total_seconds() // 60), 0)
    return f"{minutes // 60}h{minutes % 60:02d}m"


# Conclusions that `rerun-failed-jobs` can recover. Others (action_required,
# skipped, stale, neutral, ...) need a look at the run, not a blind rerun.
RERUNNABLE = {"failure", "cancelled", "timed_out"}


def classify(
    repository: str, number: int, sha: str, merged_at: str, now: datetime, api=gh
) -> tuple[str, str]:
    """Classify a merged pending PR that ready() could not prove published."""
    recovery = (
        "See RELEASING.md, 'When preparation is blocked' and 'Failure and recovery'. "
        "If recovery ran as a dispatch at another SHA, label the PR manually per RELEASING.md."
    )
    head = f"Release PR #{number} (merge {sha}) is still autorelease: pending"
    try:
        runs = api(
            "api",
            f"repos/{repository}/actions/workflows/publish-pypi.yml/runs?head_sha={sha}&per_page=100",
        )["workflow_runs"]
        runs = [run for run in runs if run.get("head_sha") == sha]
        age = now - _parse_time(merged_at)
    except (subprocess.CalledProcessError, KeyError, ValueError, TypeError) as exc:
        return BLOCKED, f"{head}; publisher state could not be read ({exc!r}). {recovery}"
    if not runs:
        if age < PUBLISHER_START_GRACE:
            return IN_PROGRESS, f"{head}; no publish-pypi.yml run yet, merged {_age(age)} ago."
        return BLOCKED, (
            f"{head}; no publish-pypi.yml run for that SHA {_age(age)} after the merge. "
            f"Check why the publisher did not start or detected no release. {recovery}"
        )
    # Any unfinished run (including a re-run of an older, lower-id run) is progress.
    active = [run for run in runs if run.get("status") != "completed"]
    run = max(active or runs, key=lambda item: item.get("id", 0))
    url = run.get("html_url", f"https://github.com/{repository}/actions/runs/{run.get('id')}")
    if active:
        return IN_PROGRESS, f"{head}; publisher run {url} is {run.get('status')}."
    conclusion = run.get("conclusion")
    if conclusion == "success":
        return BLOCKED, (
            f"{head}; publisher run {url} succeeded but publication is not proven "
            f"(Release, tag or required jobs missing). Check the run summary. If the run "
            f"summary shows a complete publication, re-run Prepare release; the proof read "
            f"may have failed transiently. {recovery}"
        )
    if conclusion in RERUNNABLE:
        return BLOCKED, (
            f"{head}; publisher run {url} concluded {conclusion}. After fixing the cause, "
            f"re-run its failed jobs: gh api -X POST "
            f"repos/{repository}/actions/runs/{run.get('id')}/rerun-failed-jobs. {recovery}"
        )
    return BLOCKED, (
        f"{head}; publisher run {url} concluded {conclusion}. Inspect the run before any "
        f"rerun. {recovery}"
    )


RELEASE_BRANCH_PREFIX = "release-please--branches--main"
VERSION_TAG = re.compile(r"v([0-9]+)\.([0-9]+)\.([0-9]+)")


def _version_at(repository: str, sha: str, api) -> str:
    blob = api("api", f"repos/{repository}/contents/.release-please-manifest.json?ref={sha}")
    version = json.loads(base64.b64decode(blob["content"]))["."]
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError(f"manifest at {sha} has no MAJOR.MINOR.PATCH version")
    return version


def _key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _contains(repository: str, ancestor: str, head: str, api) -> bool:
    try:
        status = api("api", f"repos/{repository}/compare/{ancestor}...{head}")["status"]
    except subprocess.CalledProcessError as exc:
        if _absent(exc):  # not a commit of this repository
            return False
        raise
    return status in ("ahead", "identical")


COMMENT_PAGES = 10


def _abandonment_recorded(repository: str, number: int, api) -> bool:
    """A person's comment containing "abandon" on the release PR, on any page."""
    for page in range(1, COMMENT_PAGES + 1):
        comments = api(
            "api", f"repos/{repository}/issues/{number}/comments?per_page=100&page={page}"
        )
        if any(
            "abandon" in (comment.get("body") or "").lower()
            and (comment.get("user") or {}).get("type") != "Bot"
            for comment in comments
        ):
            return True
        if len(comments) < 100:
            return False
    raise ValueError(f"release PR #{number} has more than {COMMENT_PAGES * 100} comments")


def _recovered(repository: str, release: dict, sha: str, api) -> bool:
    """A replacement published through a recovery dispatch at another SHA.

    Its own publisher run then stays failed, so ready() cannot prove it; per
    RELEASING.md the maintainer verifies the release and labels its release PR
    ``autorelease: tagged``. Accept that label on the PR merged at the tag
    commit, together with the published Release.
    """
    if release.get("draft") or not release.get("published_at"):
        return False
    for pull in api("api", f"repos/{repository}/commits/{sha}/pulls"):
        if (
            pull.get("merge_commit_sha") == sha
            and pull.get("merged_at")
            and pull["head"]["ref"].startswith(RELEASE_BRANCH_PREFIX)
            and "autorelease: tagged" in {label["name"] for label in pull.get("labels", [])}
        ):
            return True
    return False


def override_status(repository: str, sha: object, head: str, api=gh) -> tuple[str, str]:
    """Classify a ``last-release-sha`` override: none, active, obsolete or blocked."""
    if sha is None:
        return "none", "No last-release-sha override is configured."
    see = 'See RELEASING.md, "A merged X.Y.Z is abandoned".'
    name = f"last-release-sha {sha}"
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        return BLOCKED, f"{name} is not a full 40-character commit SHA. {see}"
    try:
        if not _contains(repository, sha, head, api):
            return BLOCKED, f"{name} is not in the history of main at {head}. {see}"
        pulls = [
            pull
            for pull in api("api", f"repos/{repository}/commits/{sha}/pulls")
            if pull.get("merge_commit_sha") == sha
            and pull.get("merged_at")
            and pull["head"]["ref"].startswith(RELEASE_BRANCH_PREFIX)
        ]
        if len(pulls) != 1:
            return BLOCKED, f"{name} is not the merge commit of a release PR. {see}"
        number = pulls[0]["number"]
        labels = {label["name"] for label in pulls[0].get("labels", [])}
        if "autorelease: tagged" in labels:
            return (
                BLOCKED,
                f"{name}: release PR #{number} was published (autorelease: tagged). {see}",
            )
        if "autorelease: pending" in labels:
            return BLOCKED, (
                f"{name}: release PR #{number} is still autorelease: pending; record the "
                f"abandonment and remove that label first. {see}"
            )
        if not _abandonment_recorded(repository, number, api):
            return BLOCKED, f"{name}: release PR #{number} has no recorded abandonment. {see}"
        version = _version_at(repository, sha, api)
        try:
            api("api", f"repos/{repository}/git/ref/tags/v{version}")
        except subprocess.CalledProcessError as exc:
            if not _absent(exc):
                raise
        else:
            return BLOCKED, f"{name}: v{version} is tagged, so it was not abandoned. {see}"
        replacement = None
        for release in api("api", f"repos/{repository}/releases?per_page=100"):
            match = VERSION_TAG.fullmatch(release.get("tag_name") or "")
            if release.get("draft") or not match or _key(".".join(match.groups())) <= _key(version):
                continue
            ref = api("api", f"repos/{repository}/git/ref/tags/{release['tag_name']}")["object"]
            if ref["type"] == "tag":
                ref = api("api", f"repos/{repository}/git/tags/{ref['sha']}")["object"]
            if ref["type"] != "commit" or not _contains(repository, sha, ref["sha"], api):
                continue
            # Strict: an unreadable proof must not pass as "not published yet".
            if ready(repository, ref["sha"], api, strict=True) or _recovered(
                repository, release, ref["sha"], api
            ):
                return BLOCKED, (
                    f"{name} (abandoned v{version}, release PR #{number}) is obsolete: "
                    f"{release['tag_name']} contains it and is published and verified. Remove "
                    f"last-release-sha from release-please-config.json in a normal PR before "
                    f"the next release is prepared. {see}"
                )
            replacement = release["tag_name"]
    except (subprocess.CalledProcessError, KeyError, ValueError, TypeError) as exc:
        return BLOCKED, f"{name}: release facts could not be read ({exc!r}); unresolved. {see}"
    note = f"; {replacement} is not proven published yet" if replacement else ""
    return "active", (
        f"{name} is the baseline for abandoned v{version} (release PR #{number}){note}. "
        f"Remove it once the next release is published and verified."
    )


def report(blocked: list[str], env=os.environ) -> int:
    """Make blocked publications visible in the log, the step summary and the exit code."""
    for message in blocked:
        print(f"::error::{message}")
    path = env.get("GITHUB_STEP_SUMMARY")
    if blocked and path:
        with open(path, "a", encoding="utf-8") as summary:
            summary.write("## Release preparation is blocked\n\n")
            summary.write("".join(f"- {message}\n" for message in blocked))
    return 1 if blocked else 0


def main(
    api=gh,
    now: datetime | None = None,
    env=os.environ,
    config_path: str = "release-please-config.json",
) -> int:
    now = now or datetime.now(UTC)
    repository = env["GITHUB_REPOSITORY"]
    pulls = api(
        "pr",
        "list",
        "--repo",
        repository,
        "--state",
        "merged",
        "--base",
        "main",
        "--label",
        "autorelease: pending",
        "--limit",
        "1000",
        "--json",
        "number,mergeCommit,mergedAt",
    )
    blocked = []
    for pull in pulls:
        sha = pull["mergeCommit"]["oid"]
        if not ready(repository, sha, api):
            print(f"PR #{pull['number']} remains pending: publication not proven")
            state, message = classify(repository, pull["number"], sha, pull["mergedAt"], now, api)
            if state == IN_PROGRESS:
                print(f"::notice::{message}")
            else:
                blocked.append(message)
            continue
        # Add the success label first. If either mutation fails, pending remains
        # blocking; the next run safely retries the idempotent transition.
        api(
            "api",
            f"repos/{repository}/issues/{pull['number']}/labels",
            "--method",
            "POST",
            "-f",
            "labels[]=autorelease: tagged",
        )
        api(
            "api",
            f"repos/{repository}/issues/{pull['number']}/labels/autorelease%3A%20pending",
            "--method",
            "DELETE",
        )
        print(f"PR #{pull['number']} marked tagged after publication proof")
    with open(config_path, encoding="utf-8") as handle:
        override = json.load(handle).get("last-release-sha")
    state, message = override_status(repository, override, env.get("GITHUB_SHA", "main"), api)
    if state == BLOCKED:
        blocked.append(message)
    elif state == "active":
        print(f"::notice::{message}")
    return report(blocked, env)


if __name__ == "__main__":
    raise SystemExit(main())
