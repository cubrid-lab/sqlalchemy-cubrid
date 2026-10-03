"""Regression coverage for the mutmut sandbox's first-party imports (#628).

``mutmut run`` copies ``source_paths`` and the test directory into ``mutants/``
and runs pytest with that as the root. Anything else a collected test module or
``test/conftest.py`` imports has to be listed in ``also_copy``, or the import
fails inside the sandbox. When the failing import sits in a pytest hook — as
``scripts.integration_urls`` does in ``pytest_collection_modifyitems`` (#604) —
pytest reports an INTERNALERROR, exits 3, and ``mutmut run`` stops with
``failed to collect stats. runner returned 3`` before measuring anything.
"""

from __future__ import annotations

import ast
import configparser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SETUP_CFG = ROOT / "setup.cfg"


def _mutmut_paths(key: str) -> frozenset[str]:
    parser = configparser.ConfigParser()
    parser.read(SETUP_CFG, encoding="utf-8")
    raw = parser.get("mutmut", key, fallback="")
    return frozenset(line.strip() for line in raw.splitlines() if line.strip())


def _first_party_top_level_imports(path: Path) -> frozenset[str]:
    """Top-level names *path* imports that are directories in the repository."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return frozenset(name for name in names if (ROOT / name).is_dir())


#: Copied into ``mutants/`` by mutmut itself, so they need no ``also_copy`` entry.
_SANDBOX_BUILTIN = frozenset({"test"})


def _sandbox_available() -> frozenset[str]:
    return _mutmut_paths("source_paths") | _mutmut_paths("also_copy") | _SANDBOX_BUILTIN


@pytest.mark.parametrize(
    "module",
    sorted(
        # Only the modules the stats run actually imports: conftest plus the
        # selected test modules. A module outside the selection cannot break it.
        {"test/conftest.py"} | _mutmut_paths("pytest_add_cli_args_test_selection")
    ),
)
def test_mutmut_sandbox_can_import_first_party_packages(module: str) -> None:
    path = ROOT / module
    assert path.is_file(), f"{module} is listed in setup.cfg [mutmut] but does not exist"
    missing = sorted(_first_party_top_level_imports(path) - _sandbox_available())
    assert not missing, (
        f"{module} imports {missing} which mutmut does not copy into mutants/. "
        "Add them to also_copy in setup.cfg [mutmut], or mutmut run fails with "
        "'failed to collect stats'."
    )


def test_scripts_is_copied_into_the_mutmut_sandbox() -> None:
    """``scripts`` is the case that broke the lane in #628; pin it explicitly."""
    assert "scripts" in _mutmut_paths("also_copy")
