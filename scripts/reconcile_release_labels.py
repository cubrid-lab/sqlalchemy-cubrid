#!/usr/bin/env python3
"""Clear release-please pending labels only after the guarded publisher finishes.

release-please PR-only mode does not mark merged PRs tagged. Verify immutable
tag ownership and an actually published GitHub Release before that transition.
Missing/partial publication remains pending and prevents another candidate.
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess


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


def main() -> int:
    repository = os.environ["GITHUB_REPOSITORY"]
    pulls = gh(
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
        "number,mergeCommit",
    )
    for pull in pulls:
        sha = pull["mergeCommit"]["oid"]
        if not ready(repository, sha):
            print(f"PR #{pull['number']} remains pending: publication not proven")
            continue
        # Add the success label first. If either mutation fails, pending remains
        # blocking; the next run safely retries the idempotent transition.
        gh(
            "api",
            f"repos/{repository}/issues/{pull['number']}/labels",
            "--method",
            "POST",
            "-f",
            "labels[]=autorelease: tagged",
        )
        gh(
            "api",
            f"repos/{repository}/issues/{pull['number']}/labels/autorelease%3A%20pending",
            "--method",
            "DELETE",
        )
        print(f"PR #{pull['number']} marked tagged after publication proof")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
