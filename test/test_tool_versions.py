"""Regression coverage for tooling drift and single-sourced hook/tox pins."""

from __future__ import annotations

import shutil
import tomllib
from pathlib import Path

import pytest

from scripts.check_tool_versions import check, check_environment, declared_pins

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


def test_declared_pins_and_active_environment_agree() -> None:
    assert check_environment(declared_pins(ROOT)) == []


def test_wrong_installed_version_is_detected() -> None:
    pins = declared_pins(ROOT)
    errors = check_environment(pins, lambda tool: "0.0.0" if tool == "ruff" else pins[tool])
    assert any("ruff" in error and "installed 0.0.0" in error for error in errors)


def test_missing_installed_tool_is_detected() -> None:
    import importlib.metadata as metadata

    pins = declared_pins(ROOT)

    def missing(tool: str) -> str:
        if tool == "mypy":
            raise metadata.PackageNotFoundError(tool)
        return pins[tool]

    errors = check_environment(pins, missing)
    assert any("mypy" in error and "not installed" in error for error in errors)


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


def test_ruff_hook_args_is_detected(tooling_config: Path) -> None:
    """pre-commit appends `args:` to `entry:`, so an added `args: ["--check"]`
    on ruff-format would silently turn formatting into a no-op check while
    the exact-entry check alone still sees the pinned entry line."""
    config = tooling_config / ".pre-commit-config.yaml"
    config.write_text(
        config.read_text().replace(
            "        entry: python3 -m ruff format\n        language: system\n",
            '        entry: python3 -m ruff format\n        language: system\n        args: ["--check"]\n',
        )
    )
    assert any(
        "ruff-format" in error and "must not add args" in error for error in check(tooling_config)
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
    """The whole point of local/system pre-commit hooks and group-sourced
    tox envs: bumping only the pyproject.toml pin (what Dependabot's pip
    ecosystem does) must not require touching .pre-commit-config.yaml or
    tox.ini, since neither has a separate version to keep in sync."""
    config = tooling_config / "pyproject.toml"
    original = config.read_text()
    pins = declared_pins(tooling_config)
    bumped = {tool: f"{version}.999" for tool, version in pins.items()}
    updated = original
    for tool in pins:
        current = f'"{tool}=={pins[tool]}"'
        assert current in updated
        updated = updated.replace(current, f'"{tool}=={bumped[tool]}"', 1)
    assert updated != original
    config.write_text(updated)
    assert declared_pins(tooling_config) == bumped
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
    assert any("shared Makefile lint" in error for error in check(tooling_config))


@pytest.mark.parametrize("surface", ["tox.ini", ".github/workflows/ci.yml"])
def test_format_check_target_drift_is_detected(tooling_config: Path, surface: str) -> None:
    # `make lint` no longer checks formatting (#1009); both runners need format-check.
    config = tooling_config / surface
    text = config.read_text()
    if surface == "tox.ini":
        text = text.replace("make lint format-check", "make lint")
    else:
        text = text.replace("run: make format-check", "run: ruff format --check .")
    config.write_text(text)
    assert any("format-check target" in error for error in check(tooling_config))


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


def test_pins_are_read_from_their_dependency_groups() -> None:
    # #765: Ruff and Mypy are pinned once, in the lint and typecheck groups.
    pins = declared_pins(ROOT)
    assert set(pins) == {"ruff", "mypy"}
    assert all(pins.values())


@pytest.mark.parametrize("requirement", ["ruff[toml]=={pin}", "ruff[toml] == {pin} "])
def test_exact_tool_pin_with_extras_is_read_structurally(
    tooling_config: Path, requirement: str
) -> None:
    config = tooling_config / "pyproject.toml"
    original = config.read_text()
    pin = declared_pins(tooling_config)["ruff"]
    updated = original.replace(f'"ruff=={pin}"', f'"{requirement.format(pin=pin)}"')
    assert updated != original
    config.write_text(updated)
    assert declared_pins(tooling_config)["ruff"] == pin
    assert check(tooling_config) == []


def test_valid_toml_list_formatting_is_accepted(tooling_config: Path) -> None:
    config = tooling_config / "pyproject.toml"
    original = config.read_text()
    pin = declared_pins(tooling_config)["ruff"]
    updated = original.replace(
        f'lint = [\n    "ruff=={pin}",\n]', f'lint = ["ruff=={pin}"]'
    ).replace('include = ["*.py", "*.pyi"]', 'include = [\n    "*.py",\n    "*.pyi",\n]')
    assert updated != original
    config.write_text(updated)
    assert check(tooling_config) == []


def test_dependency_group_include_is_accepted(tooling_config: Path) -> None:
    config = tooling_config / "pyproject.toml"
    original = config.read_text()
    pin = declared_pins(tooling_config)["ruff"]
    updated = original.replace(
        f'lint = [\n    "ruff=={pin}",',
        f'lint = [\n    "ruff=={pin}",\n    {{include-group = "release"}},',
    )
    assert updated != original
    config.write_text(updated)
    assert check(tooling_config) == []


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ("", "lint dependency group: expected one declaration, found 0"),
        ('lint = ["ruff>={pin}"]', "ruff: expected one declaration, found 0"),
        ('lint = ["""ruff=={pin}\ninvalid"""]', "ruff: expected one declaration, found 0"),
        (
            'lint = ["ruff=={pin}", "ruff[toml]=={pin}"]',
            "ruff: expected one declaration, found 2",
        ),
        (
            'lint = ["ruff=={pin}", "ruff>={pin}"]',
            "ruff: expected one declaration, found 2",
        ),
        ('lint = "ruff=={pin}"', "lint dependency group: expected a list of strings"),
    ],
)
def test_invalid_tool_pins_fail_clearly(
    tooling_config: Path, replacement: str, message: str
) -> None:
    config = tooling_config / "pyproject.toml"
    original = config.read_text()
    pin = declared_pins(tooling_config)["ruff"]
    updated = original.replace(f'lint = [\n    "ruff=={pin}",\n]', replacement.format(pin=pin))
    assert updated != original
    config.write_text(updated)
    with pytest.raises(ValueError, match=message):
        declared_pins(tooling_config)


def test_unbounded_alembic_requirement_is_rejected(tooling_config: Path) -> None:
    config = tooling_config / "pyproject.toml"
    original = config.read_text()
    requirement = tomllib.loads(original)["project"]["optional-dependencies"]["alembic"][0]
    assert original.count(f'"{requirement}"') == 2
    config.write_text(original.replace(f'"{requirement}"', '"alembic"'))
    with pytest.raises(ValueError, match="Alembic requirement: expected one declaration, found 0"):
        check(tooling_config)


def test_published_dev_extra_is_detected(tooling_config: Path) -> None:
    config = tooling_config / "pyproject.toml"
    config.write_text(
        config.read_text().replace(
            "[project.optional-dependencies]\n",
            '[project.optional-dependencies]\ndev = [\n    "pytest>=7.0",\n]\n',
        )
    )
    assert any("[dependency-groups], not an extra" in error for error in check(tooling_config))


def test_tox_test_requirements_repeated_in_deps_are_detected(tooling_config: Path) -> None:
    config = tooling_config / "tox.ini"
    config.write_text(
        config.read_text().replace(
            "    typecheck\ncommands =\n    pytest",
            "    typecheck\ndeps =\n    pytest>=7.0\ncommands =\n    pytest",
        )
    )
    assert any(
        "tox testenv must install the test, lint and typecheck" in e for e in check(tooling_config)
    )


def test_ci_typecheck_without_the_typecheck_group_is_detected(tooling_config: Path) -> None:
    config = tooling_config / ".github/workflows/ci.yml"
    config.write_text(
        config.read_text().replace('-e ".[alembic]" --group typecheck', '-e ".[alembic]"')
    )
    assert any("--group typecheck" in error for error in check(tooling_config))
