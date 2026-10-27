"""Offline coverage for the README translation-drift policy (#852)."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from typing import Any

import pytest

SPEC = importlib.util.spec_from_file_location(
    "check_translation_sync",
    Path(__file__).resolve().parents[1] / "scripts" / "check_translation_sync.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

SOURCE_LINE = "README.md"


def _setup_docs(tmp_path: Path, *languages: str) -> None:
    """Create the checked-out ``docs/README.<lang>.md`` files the policy globs for."""
    docs = tmp_path / "docs"
    docs.mkdir()
    for language in languages:
        (docs / f"README.{language}.md").write_text("# 번역\n", encoding="utf-8")


def _patch_git(monkeypatch: pytest.MonkeyPatch, changed: str) -> list[list[str]]:
    """Replace ``git diff`` with a fake that reports ``changed`` and record its calls."""
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, changed, "")

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)
    return calls


def test_no_translations_present_reports_nothing_to_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    assert MODULE.main() == 0
    assert "no translations present — nothing to sync" in capsys.readouterr().out


def test_english_readme_unchanged_is_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _setup_docs(tmp_path, "ko")
    monkeypatch.chdir(tmp_path)
    _patch_git(monkeypatch, "docs/README.ko.md\n")

    assert MODULE.main() == 0
    captured = capsys.readouterr()
    assert "README.md unchanged in this PR — translation sync OK" in captured.out
    assert "::error::" not in captured.out


def test_english_and_korean_changed_is_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _setup_docs(tmp_path, "ko")
    monkeypatch.chdir(tmp_path)
    _patch_git(monkeypatch, "README.md\ndocs/README.ko.md\n")

    assert MODULE.main() == 0
    captured = capsys.readouterr()
    assert "translation sync OK" in captured.out
    assert "::error::" not in captured.out
    assert "::warning" not in captured.out


def test_english_only_change_fails_with_a_required_translation_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _setup_docs(tmp_path, "ko")
    monkeypatch.chdir(tmp_path)
    _patch_git(monkeypatch, "README.md\n")

    assert MODULE.main() == 1
    captured = capsys.readouterr()
    assert (
        "::error::README.md changed but the required translation did not: docs/README.ko.md (한국어)"
        in captured.out
    )
    assert "translation sync OK" not in captured.out


def test_community_translation_drift_warns_without_failing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _setup_docs(tmp_path, "ko", "de")
    monkeypatch.chdir(tmp_path)
    _patch_git(monkeypatch, "README.md\ndocs/README.ko.md\n")

    assert MODULE.main() == 0
    captured = capsys.readouterr()
    assert (
        "::warning file=README.md::community translation drifted: docs/README.de.md (Deutsch)"
        in captured.out
    )
    assert "::error::" not in captured.out
    assert "translation sync OK" in captured.out


def test_changed_files_splits_tab_separated_rename_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_git(monkeypatch, "docs/README.old.md\tdocs/README.ko.md\n")

    assert MODULE.changed_files() == {"docs/README.old.md", "docs/README.ko.md"}
    assert calls == [["git", "diff", "--name-only", "--find-renames", "origin/main...HEAD"]]


def test_changed_files_ignores_blank_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_git(monkeypatch, "\nREADME.md\n\n  docs/README.ko.md  \n")

    assert MODULE.changed_files() == {"README.md", "docs/README.ko.md"}


@pytest.mark.parametrize(
    ("base_ref", "expected_range"),
    [
        (None, "origin/main...HEAD"),
        ("release", "origin/release...HEAD"),
        ("origin/release", "origin/release...HEAD"),
    ],
)
def test_base_ref_selects_the_git_range(
    monkeypatch: pytest.MonkeyPatch, base_ref: str | None, expected_range: str
) -> None:
    if base_ref is None:
        monkeypatch.delenv("BASE_REF", raising=False)
    else:
        monkeypatch.setenv("BASE_REF", base_ref)
    calls = _patch_git(monkeypatch, "")

    assert MODULE.changed_files() == set()
    assert calls[0][-1] == expected_range


def test_source_constant_names_the_canonical_readme() -> None:
    assert MODULE.SOURCE.as_posix() == SOURCE_LINE
    assert MODULE.REQUIRED_LANGS == {"ko"}
