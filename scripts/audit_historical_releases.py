#!/usr/bin/env python3
"""Inventory and back up all published GitHub Release bodies before editing.

Read-only: this tool never patches GitHub releases, tags, or CHANGELOG.md.
The output is an auditable snapshot for a separately reviewed historical
release-note cleanup.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

TAG = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")
HISTORY = re.compile(r"^## \[([0-9]+\.[0-9]+\.[0-9]+)\]", re.MULTILINE)


def get_json(path: str) -> object:
    result = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def list_releases(repo: str) -> list[dict]:
    """Page through every published release: GitHub's order is not version order."""
    collected: list[dict] = []
    page = 1
    while True:
        result = get_json(f"repos/{repo}/releases?per_page=100&page={page}")
        if not isinstance(result, list):
            raise ValueError(f"unexpected GitHub releases result (page {page})")
        collected.extend(x for x in result if isinstance(x, dict))
        if len(result) < 100:
            return collected
        page += 1


def create_audit(releases: list[dict], changelog: str, directory: Path) -> dict:
    """Store the exact original bodies; report discrepancies without rewriting."""
    if directory.exists() and any(directory.iterdir()):
        raise ValueError(f"audit output directory is not empty: {directory}")
    directory.mkdir(parents=True, exist_ok=True)
    recorded = set(HISTORY.findall(changelog))
    rows = []
    seen: set[str] = set()
    for release in releases:
        if release.get("draft"):
            continue
        tag = release.get("tag_name")
        if not isinstance(tag, str) or not TAG.fullmatch(tag):
            continue
        if tag in seen:
            raise ValueError(f"duplicate tag in API response: {tag}")
        seen.add(tag)
        name = release.get("name")
        body = release.get("body") or ""
        if not isinstance(body, str):
            raise ValueError(f"invalid release body for {tag}")
        folder = directory / tag
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "original-body.md").write_bytes(body.encode("utf-8"))
        metadata = {
            "id": release.get("id"),
            "tag_name": tag,
            "name": name,
            "draft": release.get("draft"),
            "prerelease": release.get("prerelease"),
            "published_at": release.get("published_at"),
            "html_url": release.get("html_url"),
        }
        (folder / "metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        rows.append(
            {
                "tag": tag,
                "version_in_changelog": tag[1:] in recorded,
                "title_matches_tag": tag == name,
                "has_comparison_link": "**Full Changelog**" in body,
                "body_characters": len(body),
                "draft": bool(release.get("draft")),
            }
        )
    rows.sort(key=lambda x: tuple(int(n) for n in x["tag"][1:].split(".")), reverse=True)
    report = {
        "release_count": len(rows),
        "versions_in_changelog_without_published_release": sorted(
            recorded - {row["tag"][1:] for row in rows}
        ),
        "releases": rows,
    }
    (directory / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default="cubrid-lab/sqlalchemy-cubrid")
    parser.add_argument("--changelog", default="CHANGELOG.md")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    try:
        report = create_audit(
            list_releases(args.repo),
            Path(args.changelog).read_text(encoding="utf-8"),
            Path(args.output_dir),
        )
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    print(
        f"Backed up {report['release_count']} GitHub Release bodies; "
        f"report: {args.output_dir}/report.json"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
