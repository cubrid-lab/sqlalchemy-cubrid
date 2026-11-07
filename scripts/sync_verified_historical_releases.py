#!/usr/bin/env python3
"""Synchronize only historical releases whose live body exactly matches CHANGELOG.

This migration deliberately refuses releases with editorial differences. It only
adds a missing comparison link to four verified unchanged release bodies.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sync_historical_release import extract_version, github_json, make_body

RELEASES = (
    ("v1.10.0", "v1.9.0"),
    ("v1.9.0", "v1.8.0"),
    ("v1.8.0", "v1.7.1"),
    ("v1.7.1", "v1.7.0"),
)
REPO = "cubrid-lab/sqlalchemy-cubrid"


def main() -> int:
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    for tag, previous in RELEASES:
        section = extract_version(changelog, tag[1:])
        expected = make_body(section, previous, tag, REPO)
        release = github_json(f"repos/{REPO}/releases/tags/{tag}")
        if release.get("draft") is not False or not release.get("published_at"):
            raise ValueError(f"{tag}: draft or unpublished")
        if release.get("tag_name") != tag:
            raise ValueError(f"{tag}: wrong tag")
        actual = release.get("body")
        if actual == expected:
            print(f"{tag}: already synchronized")
            continue
        if not isinstance(actual, str) or actual.strip() != section:
            raise ValueError(
                f"{tag}: live body differs from canonical section; manual review required"
            )
        latest = github_json(f"repos/{REPO}/releases/{release['id']}")
        if (
            latest.get("body") != actual
            or latest.get("tag_name") != tag
            or latest.get("draft") is not False
            or not latest.get("published_at")
        ):
            raise ValueError(f"{tag}: concurrent modification detected")
        updated = github_json(
            f"repos/{REPO}/releases/{release['id']}",
            method="PATCH",
            body=json.dumps({"tag_name": tag, "body": expected}),
        )
        if updated.get("body") != expected or updated.get("tag_name") != tag:
            raise ValueError(f"{tag}: patch response mismatch")
        verified = github_json(f"repos/{REPO}/releases/{release['id']}")
        if (
            verified.get("body") != expected
            or verified.get("tag_name") != tag
            or verified.get("draft") is not False
            or not verified.get("published_at")
        ):
            raise ValueError(f"{tag}: post-update verification failed")
        print(f"{tag}: added comparison link; no existing note text changed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"::error::{error}", file=sys.stderr)
        sys.exit(1)
