"""MkDocs hook: show which source revision the documentation site was built from (#946).

The site is built from ``main`` on every push, independently of package
publication, so it can describe changes that no published release contains.
This hook replaces the marker ``<!-- docs-source-revision -->`` in a page with
a link to the exact commit. The commit comes from ``GITHUB_SHA`` (set in
GitHub Actions) or ``git rev-parse HEAD``; when neither is available the page
says the revision was not recorded. It never contacts GitHub or PyPI.
"""

from __future__ import annotations

import os
import re
import subprocess
from typing import Any

MARKER = "<!-- docs-source-revision -->"
REPOSITORY = "https://github.com/cubrid-lab/sqlalchemy-cubrid"
_SHA = re.compile(r"[0-9a-f]{40}")


def source_revision(env: dict[str, str] | None = None) -> str | None:
    """Return the full commit SHA of the documentation source, or ``None``."""
    env = os.environ if env is None else env
    sha = env.get("GITHUB_SHA", "").strip().lower()
    if _SHA.fullmatch(sha):
        return sha
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    sha = result.stdout.strip().lower()
    return sha if _SHA.fullmatch(sha) else None


def revision_text(sha: str | None, korean: bool = False) -> str:
    """The sentence that replaces the marker."""
    if sha is None:
        if korean:
            return "이 사본을 빌드한 소스 커밋은 기록되지 않았습니다."
        return "The source commit of this copy was not recorded."
    link = f"[`{sha[:12]}`]({REPOSITORY}/tree/{sha})"
    if korean:
        return f"이 사이트는 소스 커밋 {link}에서 빌드되었습니다."
    return f"This site was built from source commit {link}."


def on_config(config: Any, **_kwargs: Any) -> Any:
    config["extra"]["docs_source_revision"] = source_revision()
    return config


def on_page_markdown(markdown: str, page: Any, config: Any, **_kwargs: Any) -> str:
    if MARKER not in markdown:
        return markdown
    korean = page.file.src_uri.startswith("ko/")
    return markdown.replace(
        MARKER, revision_text(config["extra"].get("docs_source_revision"), korean)
    )
