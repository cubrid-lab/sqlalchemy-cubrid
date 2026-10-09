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
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone

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


def ready(repository: str, sha: str, api=gh) -> bool:
    """Fail closed on absent/partial/mismatched release facts."""
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
    except (subprocess.CalledProcessError, KeyError, ValueError, TypeError):
        return False


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


def main(api=gh, now: datetime | None = None, env=os.environ) -> int:
    now = now or datetime.now(timezone.utc)
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
    return report(blocked, env)


if __name__ == "__main__":
    raise SystemExit(main())
