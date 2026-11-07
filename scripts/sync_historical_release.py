#!/usr/bin/env python3
"""Preview or safely synchronize one approved historical GitHub Release.

Dry-run is the default. Publishing requires --apply, an explicit expected
SHA-256 of the original GitHub body, and a non-draft published Release.
Only the release body is patched. Tags, titles, dates and assets are untouched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

SECTION = re.compile(r"^## \[([0-9]+\.[0-9]+\.[0-9]+)\][^\n]*\n", re.MULTILINE)
FULL = re.compile(r"^\*\*Full Changelog\*\*:.*$", re.MULTILINE)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def github_json(path: str, *, method: str = "GET", body: str | None = None) -> dict:
    command = ["gh", "api", "--method", method, path]
    if body is not None:
        command += ["--input", "-"]
    result = subprocess.run(
        command, input=body, capture_output=True, text=True, check=True
    )
    parsed = json.loads(result.stdout)
    if not isinstance(parsed, dict):
        raise ValueError("unexpected GitHub API response")
    return parsed


def extract_version(changelog: str, version: str) -> str:
    matches = list(SECTION.finditer(changelog))
    for i, match in enumerate(matches):
        if match.group(1) == version:
            end = matches[i + 1].start() if i + 1 < len(matches) else len(changelog)
            return changelog[match.end() : end].strip()
    raise ValueError(f"changelog version not found: {version}")


def make_body(section: str, previous_tag: str, current_tag: str, repo: str) -> str:
    """Keep curated section unchanged and add exactly one comparison link."""
    if not re.fullmatch(r"v\d+\.\d+\.\d+", previous_tag):
        raise ValueError("invalid previous tag")
    if not re.fullmatch(r"v\d+\.\d+\.\d+", current_tag):
        raise ValueError("invalid current tag")
    if FULL.search(section):
        raise ValueError("canonical section already contains Full Changelog")
    if "Full Changelog" in section:
        raise ValueError("ambiguous Full Changelog text in canonical section")
    return (
        section.rstrip()
        + "\n\n"
        + f"**Full Changelog**: https://github.com/{repo}/compare/"
        + f"{previous_tag}...{current_tag}"
    )


def prepare(
    release: dict,
    changelog: str,
    *,
    repo: str,
    tag: str,
    previous_tag: str,
    expected_sha256: str,
) -> tuple[str, str]:
    if release.get("tag_name") != tag:
        raise ValueError("tag mismatch")
    if release.get("draft") is not False or not release.get("published_at"):
        raise ValueError("draft or unpublished release cannot be modified")
    if release.get("body") is None or not isinstance(release.get("body"), str):
        raise ValueError("release body missing")
    original = release["body"]
    if digest(original) != expected_sha256:
        raise ValueError("remote release body changed since approved backup")
    section = extract_version(changelog, tag[1:])
    target = make_body(section, previous_tag, tag, repo)
    return original, target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default="cubrid-lab/sqlalchemy-cubrid")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--previous-tag", required=True)
    parser.add_argument("--changelog", default="CHANGELOG.md")
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"v\d+\.\d+\.\d+", args.tag):
        parser.error("--tag must be a semantic version tag")
    if not re.fullmatch(r"[a-f0-9]{64}", args.expected_sha256):
        parser.error("--expected-sha256 must be a lowercase SHA-256 hex digest")
    try:
        release = github_json(
            f"repos/{args.repo}/releases/tags/{quote(args.tag, safe='')}"
        )
        original, target = prepare(
            release,
            Path(args.changelog).read_text(encoding="utf-8"),
            repo=args.repo,
            tag=args.tag,
            previous_tag=args.previous_tag,
            expected_sha256=args.expected_sha256,
        )
        print(
            f"{args.tag}: original sha256={digest(original)}; "
            f"target sha256={digest(target)}; "
            f"original chars={len(original)}; target chars={len(target)}"
        )
        if original == target:
            print("Already synchronized; no changes made.")
            return 0
        if not args.apply:
            print("DRY RUN: no changes made. Review the full Markdown diff first.")
            return 0
        # Re-fetch immediately before PATCH to catch changes since preparation.
        latest = github_json(
            f"repos/{args.repo}/releases/{release['id']}"
        )
        if latest.get("tag_name") != args.tag or latest.get("body") != original:
            raise ValueError("release changed before update; aborting")
        updated = github_json(
            f"repos/{args.repo}/releases/{release['id']}",
            method="PATCH",
            body=json.dumps({"body": target}),
        )
        if updated.get("tag_name") != args.tag or updated.get("body") != target:
            raise ValueError("release update response differs from approved body")
        print(f"Updated GitHub Release body for {args.tag}.")
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
