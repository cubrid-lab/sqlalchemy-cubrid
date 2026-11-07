"""Attribution is evidence-based and preserves existing release-note content."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from urllib.parse import unquote

import pytest

pytestmark = pytest.mark.repo_tooling
source = Path(__file__).resolve().parents[1] / "scripts/annotate_release_contributors.py"
spec = importlib.util.spec_from_file_location("annotate_release_contributors", source)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

REPO = "cubrid-lab/sqlalchemy-cubrid"
ENTRY = (
    "* docs: clarify install ([#42](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/42)) "
    "([abc1234](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/abc1234))\n"
)


def mock_get(path: str) -> object:
    if path.endswith("/pulls"):
        return [
            {
                "number": 99,
                "merged_at": "2026-10-30T04:41:38Z",
                "user": {"login": "community-dev", "type": "User"},
            }
        ]
    assert "search/issues" in path
    assert "merged:<2026-10-30T04:41:38Z" in unquote(path)
    return {"total_count": 0}


def test_verified_first_contribution() -> None:
    assert module.verified_credit(REPO, "abc1234", mock_get) == (
        " by @community-dev (first contribution 🎉)"
    )


def test_existing_contributor_has_plain_credit() -> None:
    def get(path: str) -> object:
        if path.endswith("/pulls"):
            return mock_get(path)
        return {"total_count": 2}

    assert module.verified_credit(REPO, "abc1234", get) == " by @community-dev"


@pytest.mark.parametrize("prs", [[], [{}], [{"merged_at": None}], [
    {"merged_at": "2026-10-30T04:41:38Z", "user": {"login": "bot[bot]", "type": "Bot"}}
], [
    {"merged_at": "2026-10-30T04:41:38Z", "user": {"login": "a", "type": "User"}},
    {"merged_at": "2026-10-30T04:41:38Z", "user": {"login": "b", "type": "User"}},
]])
def test_no_guess_for_missing_bot_or_ambiguous_authorship(prs: list) -> None:
    assert module.verified_credit(REPO, "abc1234", lambda _: prs) is None


def test_network_lookup_errors_never_invent_authorship() -> None:
    def fail(_: str) -> object:
        raise OSError("unavailable")

    assert module.verified_credit(REPO, "abc1234", fail) is None


def test_annotations_are_idempotent_and_do_not_touch_curated_notes() -> None:
    notes = (
        "# Changelog\n\n### Documentation\n\n"
        "- Curated documentation summary.\n\n"
        + ENTRY
        + "\n"
        + "### Fixed\n\n"
        + "- Existing attribution by @someone.\n"
    )
    expected = notes.replace(
        ENTRY, ENTRY.rstrip("\n") + " by @community-dev (first contribution 🎉)\n"
    )
    calls = []

    def resolve(repo: str, sha: str) -> str | None:
        calls.append((repo, sha))
        return " by @community-dev (first contribution 🎉)"

    assert module.annotate(notes, REPO, resolve) == expected
    assert calls == [(REPO, "abc1234")]
    assert module.annotate(expected, REPO, resolve) == expected


def test_code_fences_and_other_repositories_are_untouched() -> None:
    other = ENTRY.replace("cubrid-lab/sqlalchemy-cubrid", "another/repo")
    fenced = chr(96) * 3 + "\n" + ENTRY + chr(96) * 3 + "\n"
    notes = fenced + other + ENTRY + ENTRY
    seen = []

    def resolve(repo: str, sha: str) -> str | None:
        seen.append((repo, sha))
        return " by @author"

    result = module.annotate(notes, REPO, resolve)
    assert result.count("by @author") == 2
    assert result.startswith(fenced + other)
    assert seen == [(REPO, "abc1234")]


def test_absent_api_evidence_leaves_note_unchanged() -> None:
    assert module.annotate(ENTRY, REPO, lambda *_: None) == ENTRY


def test_wrapped_entry_appends_credit_after_the_complete_markdown_link() -> None:
    wrapped = (
        "* **Types** — Correct decoding ([#123]"
        "(https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/123))\n"
        "  and preserve the documented behavior "
        "([abc1234](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/abc1234))\n"
    )
    changed = module.annotate(wrapped, REPO, lambda *_: " by @alice")
    assert changed == wrapped.rstrip("\n") + " by @alice\n"
    assert "[#123](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/123)" in changed
    assert "\n  and preserve" in changed
    assert "by @alice" not in changed.splitlines()[0]


def test_wrapped_entry_without_author_remains_byte_for_byte() -> None:
    wrapped = (
        "* Documentation notes with\n"
        "  an existing wrapped sentence\n\n"
        "### Fixed\n"
        "* unrelated\n"
    )
    assert module.annotate(wrapped, REPO, lambda *_: None) == wrapped


def test_first_contribution_lookup_failure_preserves_verified_byline() -> None:
    def get(path: str) -> object:
        if path.endswith("/pulls"):
            return mock_get(path)
        raise OSError("search unavailable")

    assert module.verified_credit(REPO, "abc1234", get) == " by @community-dev"
