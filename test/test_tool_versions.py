"""Regression coverage for tooling drift and single-sourced hook/tox pins."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts.check_tool_versions import check

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def tooling_config(tmp_path: Path) -> Path:
    for name in (
        "pyproject.toml",
        ".pre-commit-config.yaml",
        "tox.ini",
        "Makefile",
        ".github/workflows/ci.yml",
    ):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return tmp_path


def test_current_tooling_config_agrees() -> None:
    assert check(ROOT) == []


def test_hook_entry_drift_is_detected(tooling_config: Path) -> None:
    config = tooling_config / ".pre-commit-config.yaml"
    config.write_text(
        config.read_text().replace("entry: python3 -m ruff format", "entry: ruff format")
    )
    assert any(
        "ruff-format" in error and "entry must be exactly" in error
        for error in check(tooling_config)
    )


def test_hook_swapped_subcommand_is_detected(tooling_config: Path) -> None:
    """A hook that still invokes `python3 -m ruff` but runs the wrong
    subcommand (formatting instead of checking, or vice versa) must be
    rejected even though the module prefix looks right."""
    config = tooling_config / ".pre-commit-config.yaml"
    config.write_text(
        config.read_text().replace("entry: python3 -m ruff format", "entry: python3 -m ruff check")
    )
    assert any(
        "ruff-format" in error and "entry must be exactly" in error
        for error in check(tooling_config)
    )


def test_hook_missing_language_system_is_detected(tooling_config: Path) -> None:
    config = tooling_config / ".pre-commit-config.yaml"
    config.write_text(
        config.read_text().replace(
            "        entry: python3 -m mypy\n        language: system\n",
            "        entry: python3 -m mypy\n",
        )
    )
    assert any("language: system" in error for error in check(tooling_config))


def test_duplicate_local_hook_id_fails(tooling_config: Path) -> None:
    config = tooling_config / ".pre-commit-config.yaml"
    original = config.read_text()
    anchor = "      - id: ruff\n        name: ruff\n"
    assert original.count(anchor) == 1
    duplicate = (
        "      - id: ruff\n"
        "        name: ruff (unpinned duplicate)\n"
        "        entry: ruff check\n"
        "        language: system\n"
        "        types_or: [python, pyi]\n"
    )
    config.write_text(original.replace(anchor, duplicate + anchor, 1))
    with pytest.raises(ValueError, match="duplicate local hook id"):
        check(tooling_config)


def test_dependabot_style_pin_bump_alone_does_not_require_hook_or_tox_edit(
    tooling_config: Path,
) -> None:
    """The whole point of local/system pre-commit hooks and dev-extra-sourced
    tox envs: bumping only the pyproject.toml pin (what Dependabot's pip
    ecosystem does) must not require touching .pre-commit-config.yaml or
    tox.ini, since neither has a separate version to keep in sync."""
    config = tooling_config / "pyproject.toml"
    original = config.read_text()
    config.write_text(
        original.replace('"ruff==0.16.9"', '"ruff==99.0.0"').replace(
            '"mypy==2.3.1"', '"mypy==99.0.0"'
        )
    )
    assert check(tooling_config) == []


def test_expanded_ruff_cli_scope_is_detected(tooling_config: Path) -> None:
    config = tooling_config / "pyproject.toml"
    config.write_text(config.read_text().replace('["*.py", "*.pyi"]', '["*.py", "*.pyi", "*.md"]'))
    assert any("Ruff CLI file scope" in error for error in check(tooling_config))


def test_omitted_maintained_source_directory_is_detected(tooling_config: Path) -> None:
    config = tooling_config / "Makefile"
    config.write_text(
        config.read_text().replace(
            " scripts demos samples docs/source", " scripts demos docs/source"
        )
    )
    assert any(
        "all maintained Python source directories" in error for error in check(tooling_config)
    )


@pytest.mark.parametrize("surface", ["tox.ini", ".github/workflows/ci.yml"])
def test_lint_target_drift_is_detected(tooling_config: Path, surface: str) -> None:
    config = tooling_config / surface
    config.write_text(
        config.read_text().replace("make lint", "ruff check sqlalchemy_cubrid/ test/")
    )
    assert any("shared Makefile lint target" in error for error in check(tooling_config))


def test_formal_suite_cannot_enter_regular_tox_integration(tooling_config: Path) -> None:
    config = tooling_config / "tox.ini"
    config.write_text(config.read_text().replace("--ignore=test/test_suite.py", ""))
    assert any("formal suite" in error and "--dburi" in error for error in check(tooling_config))


def test_integration_preflight_cannot_be_omitted(tooling_config: Path) -> None:
    config = tooling_config / "tox.ini"
    config.write_text(
        config.read_text().replace("python -m scripts.check_integration_connection", "")
    )
    assert any("preflight first" in error for error in check(tooling_config))
