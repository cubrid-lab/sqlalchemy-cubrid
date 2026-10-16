"""The docs site links its home pages to the source commit it was built from (#946)."""

from __future__ import annotations

import importlib.util
import subprocess
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "docs_provenance_hook", ROOT / "scripts/docs_provenance_hook.py"
)
assert SPEC and SPEC.loader
HOOK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOOK)

SHA = "767a0bcd72466518f38ef667e1ab51d3eb36eee8"


def test_github_sha_is_preferred() -> None:
    assert HOOK.source_revision({"GITHUB_SHA": SHA.upper()}) == SHA


def test_git_head_is_the_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(*_args: object, **_kwargs: object) -> types.SimpleNamespace:
        return types.SimpleNamespace(stdout=SHA + "\n")

    monkeypatch.setattr(HOOK.subprocess, "run", run)
    assert HOOK.source_revision({"GITHUB_SHA": "not-a-sha"}) == SHA


@pytest.mark.parametrize("error", [OSError("no git"), subprocess.CalledProcessError(128, "git")])
def test_unknown_revision_is_none(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    def run(*_args: object, **_kwargs: object) -> None:
        raise error

    monkeypatch.setattr(HOOK.subprocess, "run", run)
    assert HOOK.source_revision({}) is None


def page(src_uri: str) -> types.SimpleNamespace:
    return types.SimpleNamespace(file=types.SimpleNamespace(src_uri=src_uri))


@pytest.mark.parametrize(
    ("src_uri", "sha", "text"),
    [
        ("index.md", SHA, f"built from source commit [`{SHA[:12]}`]"),
        ("ko/index.md", SHA, f"소스 커밋 [`{SHA[:12]}`]"),
        ("index.md", None, "was not recorded"),
        ("ko/index.md", None, "기록되지 않았습니다"),
    ],
)
def test_marker_is_replaced_with_the_revision(src_uri: str, sha: str | None, text: str) -> None:
    markdown = f"before\n{HOOK.MARKER}\nafter"
    config = {"extra": {"docs_source_revision": sha}}
    rendered = HOOK.on_page_markdown(markdown, page(src_uri), config)
    assert HOOK.MARKER not in rendered and text in rendered
    if sha:
        assert f"https://github.com/cubrid-lab/sqlalchemy-cubrid/tree/{sha}" in rendered


def test_pages_without_the_marker_are_unchanged() -> None:
    assert HOOK.on_page_markdown("text", page("TYPES.md"), {"extra": {}}) == "text"


def test_both_home_pages_carry_the_marker_and_the_site_runs_the_hook() -> None:
    for name in ("docs/index.md", "docs/ko/index.md"):
        assert HOOK.MARKER in (ROOT / name).read_text(encoding="utf-8"), name
    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert "hooks:\n  - scripts/docs_provenance_hook.py\n" in config
