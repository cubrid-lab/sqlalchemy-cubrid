"""GitHub Release title policy: the title is exactly the stable tag (AGENTS.md)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "check_release_title",
    Path(__file__).resolve().parents[1] / "scripts/check_release_title.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
release_title_error = MODULE.release_title_error
main = MODULE.main


@pytest.mark.parametrize("draft", [False, True])
def test_title_equal_to_stable_tag_is_valid(draft: bool) -> None:
    assert release_title_error("v1.2.3", "v1.2.3", draft=draft) is None


@pytest.mark.parametrize(
    "title",
    [
        "sqlalchemy-cubrid 1.2.3",
        "v1.2.3 — Foo",
        "v1.2.3 (corrected)",
        "Release v1.2.3",
        "1.2.3",
        "v1.2.3 ",
        "",
    ],
)
@pytest.mark.parametrize("draft", [False, True])
def test_title_other_than_tag_is_rejected(title: str, draft: bool) -> None:
    error = release_title_error("v1.2.3", title, draft=draft)
    assert error is not None
    assert ("draft Release" in error) is draft
    assert "never renamed automatically" in error


@pytest.mark.parametrize("tag", ["1.2.3", "v1.2", "v1.2.3rc1", "sqlalchemy-cubrid-v1.2.3"])
def test_non_stable_tag_is_rejected(tag: str) -> None:
    assert release_title_error(tag, tag) is not None


def test_cli_fails_closed_for_a_mistitled_draft(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--tag", "v1.2.3", "--title", "v1.2.3 (corrected)", "--draft", "true"]) == 1
    assert "::error::existing draft Release v1.2.3" in capsys.readouterr().err


def test_cli_accepts_a_published_release_titled_by_its_tag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--tag", "v1.2.3", "--title", "v1.2.3", "--draft", "false"]) == 0
    assert "equals tag v1.2.3" in capsys.readouterr().out


def test_cli_title_starting_with_a_dash_gets_the_policy_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The workflow passes --title="$title", so a leading "-" is a value, not an option.
    assert main(["--tag", "v1.2.3", "--title=-v1.2.3", "--draft", "false"]) == 1
    assert "titled '-v1.2.3'; the title must be exactly 'v1.2.3'" in capsys.readouterr().err
