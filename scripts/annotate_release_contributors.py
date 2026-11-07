#!/usr/bin/env python3
"""Add verified PR author credits to generated release-note entries.

This annotates a temporary copy of RELEASE_CHANGELOG.md, not release-please's
generated source. Only a unique merged PR associated with the linked commit
is evidence of authorship. A failed lookup never guesses a contributor.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable
from urllib.parse import quote

COMMIT = re.compile(
    r"\(\[[0-9a-f]{7,40}\]\(https://github\.com/"
    r"(?P<repo>[^/)\s]+/[^/)\s]+)/commit/(?P<sha>[0-9a-f]{7,40})\)\)"
)
CREDIT = re.compile(r"\bby @[-\w]+")
FIRST = " (first contribution 🎉)"


def github_json(path: str) -> object:
    completed = subprocess.run(
        ["gh", "api", path], check=True, capture_output=True, text=True
    )
    return json.loads(completed.stdout)


def verified_credit(
    repo: str, sha: str, get: Callable[[str], object] = github_json
) -> str | None:
    """Return an attribution only if a single merged non-bot PR is identified."""
    try:
        prs = get(f"repos/{repo}/commits/{sha}/pulls")
        if not isinstance(prs, list):
            return None
        merged = [pr for pr in prs if isinstance(pr, dict) and pr.get("merged_at")]
        if len(merged) != 1:
            return None
        pr = merged[0]
        user = pr.get("user")
        if not isinstance(user, dict):
            return None
        name = user.get("login")
        if (
            not isinstance(name, str)
            or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37})", name)
            or user.get("type") == "Bot"
            or name.lower().endswith("[bot]")
        ):
            return None
        suffix = f" by @{name}"
        merged_at = pr.get("merged_at")
        if isinstance(merged_at, str) and re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", merged_at
        ):
            query = (
                f"repo:{repo} is:pr is:merged author:{name} "
                f"merged:<{merged_at}"
            )
            results = get(f"search/issues?q={quote(query, safe='')}&per_page=1")
            if isinstance(results, dict) and results.get("total_count") == 0:
                suffix += FIRST
        return suffix
    except (OSError, subprocess.CalledProcessError, ValueError, TypeError) as error:
        print(f"::warning::Contributor lookup skipped for {sha}: {error}", file=sys.stderr)
        return None


def annotate(
    notes: str,
    repo: str,
    resolve: Callable[[str, str], str | None] = verified_credit,
) -> str:
    """Keep every original line and append a credit only to evidenced entries."""
    result: list[str] = []
    fence: str | None = None
    cache: dict[str, str | None] = {}
    for line in notes.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith((chr(96) * 3, "~" * 3)):
            mark = stripped[0]
            fence = None if fence == mark else mark
            result.append(line)
            continue
        if fence is None and line.startswith(("* ", "- ")) and not CREDIT.search(line):
            matches = [
                m for m in COMMIT.finditer(line) if m.group("repo").lower() == repo.lower()
            ]
            if len(matches) == 1:
                sha = matches[0].group("sha")
                if sha not in cache:
                    cache[sha] = resolve(repo, sha)
                if cache[sha]:
                    ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
                    line = line.removesuffix(ending) + cache[sha] + ending
        result.append(line)
    return "".join(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()
    from pathlib import Path

    source = Path(args.input).read_text(encoding="utf-8")
    result = annotate(source, args.repo)
    Path(args.output).write_text(result, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
