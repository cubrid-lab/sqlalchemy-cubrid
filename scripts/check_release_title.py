#!/usr/bin/env python3
"""Fail closed when an existing GitHub Release title is not exactly its tag.

The GitHub Release policy (AGENTS.md) requires every Release title, drafts
included, to equal its stable tag ``vMAJOR.MINOR.PATCH``: no package name,
feature, date or suffix. publish-pypi.yml creates Releases with
``--title "$TAG"``; on a resume or recovery run that finds an existing Release,
it runs this check and stops instead of silently reusing a mistitled Release.
The check never renames anything; a maintainer fixes the title by hand
(resending ``tag_name`` when the Release is a draft).

Usage:
    python scripts/check_release_title.py --tag vX.Y.Z --title TITLE --draft true|false

Exit codes:
    0 — the title equals the tag
    1 — the title differs from the tag, or the tag is not vMAJOR.MINOR.PATCH
"""

from __future__ import annotations

import argparse
import re
import sys

STABLE_TAG = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")


def release_title_error(tag: str, title: str, *, draft: bool = False) -> str | None:
    """Return why ``title`` violates the policy for ``tag``, or None when it complies."""
    kind = "draft Release" if draft else "Release"
    if not STABLE_TAG.fullmatch(tag):
        return f"tag {tag!r} is not vMAJOR.MINOR.PATCH"
    if title != tag:
        return (
            f"existing {kind} {tag} is titled {title!r}; the title must be exactly {tag!r}. "
            "Fix the title by hand (resend tag_name for a draft); it is never renamed automatically"
        )
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--draft", choices=("true", "false"), required=True)
    args = parser.parse_args(argv)
    error = release_title_error(args.tag, args.title, draft=args.draft == "true")
    if error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    print(f"Release title {args.title!r} equals tag {args.tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
