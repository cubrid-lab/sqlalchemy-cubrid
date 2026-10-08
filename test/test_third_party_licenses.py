"""THIRD_PARTY_LICENSES.md stays consistent with pyproject.toml (#727).

The inventory is a generated snapshot; this check makes drift visible instead of
silent: every dependency declared for each install scope must appear in that
scope's table (within its declared range, unless it is an exact ``==`` pin, which
pyproject.toml already records), every row's category must
be what the generator assigns to its license, every MPL or "Needs review" row
must be explained in the prose, and the CUBRID-Python BSD variant stays
explicitly unresolved.
"""

from __future__ import annotations

import importlib.util
import re
import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
DOC = (ROOT / "THIRD_PARTY_LICENSES.md").read_text(encoding="utf-8")
PROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

_spec = importlib.util.spec_from_file_location(
    "generate_third_party_licenses", ROOT / "scripts" / "generate_third_party_licenses.py"
)
assert _spec and _spec.loader
generator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(generator)

# Install scope -> heading of the table that inventories it.
SECTIONS = {
    "runtime": "## Default runtime",
    "pycubrid": "## `[pycubrid]` extra",
    "alembic": "## `[alembic]` extra",
    "cubrid": "## `[cubrid]` / `[cubriddb]` extra",
    "cubriddb": "## `[cubrid]` / `[cubriddb]` extra",
    "dev": "## Development / test dependencies: `[dev]`",
}


def table(scope: str) -> dict[str, dict[str, str]]:
    start = DOC.index(SECTIONS[scope])
    end = DOC.find("\n## ", start + 1)
    end = len(DOC) if end == -1 else end
    rows = {}
    for line in DOC[start:end].splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5 or cells[0] == "Name" or set(cells[0]) <= {"-"}:
            continue
        rows[canonicalize_name(cells[0])] = {
            "version": cells[1],
            "license": cells[2],
            "category": cells[3],
        }
    return rows


def requirements(scope: str) -> list[Requirement]:
    declared = (
        PROJECT["dependencies"] if scope == "runtime" else PROJECT["optional-dependencies"][scope]
    )
    return [Requirement(req) for req in declared]


def test_every_declared_scope_has_a_table() -> None:
    assert set(PROJECT["optional-dependencies"]) | {"runtime"} == set(SECTIONS)


@pytest.mark.parametrize("scope", sorted(SECTIONS))
def test_every_declared_dependency_is_inventoried_within_its_range(scope: str) -> None:
    rows = table(scope)
    for req in requirements(scope):
        name = canonicalize_name(req.name)
        assert name in rows, f"{name} from {scope} is missing from THIRD_PARTY_LICENSES.md"
        if any(spec.operator == "==" for spec in req.specifier):
            continue  # Exact pins are authoritative in pyproject.toml; bumps need no regen.
        version = rows[name]["version"]
        assert req.specifier.contains(version, prereleases=True), (
            f"{name} {version} is outside {req.specifier} declared for {scope}"
        )


@pytest.mark.parametrize("scope", sorted(SECTIONS))
def test_every_category_matches_the_generator(scope: str) -> None:
    for name, row in table(scope).items():
        assert generator.category(row["license"]) == row["category"], (name, row)


def test_every_review_and_mpl_row_is_explained() -> None:
    categories = DOC[DOC.index("## License categories") : DOC.index("## How the inventories")]
    reviewed = categories[categories.index("### Reviewed entries") :]
    for scope in SECTIONS:
        for name, row in table(scope).items():
            if row["category"] == "Needs review":
                assert re.search(rf"\*\*{re.escape(name)}\*\*", reviewed, re.I), name
            elif row["category"].startswith("Weak copyleft"):
                assert f"`{name}`" in categories, f"MPL package {name} not named in the prose"
            else:
                assert row["category"] == "Permissive", (name, row)


def test_reviewed_rows_keep_their_review() -> None:
    # Transitive rows are not declared in pyproject.toml; pin the reviewed ones.
    assert table("dev")["docutils"]["category"] == "Needs review"
    assert "greenlet" in table("pycubrid")


def test_cubrid_python_bsd_variant_stays_unresolved() -> None:
    assert table("cubrid")["cubrid-python"]["license"] == "BSD"
    reviewed = DOC[DOC.index("### Reviewed entries") : DOC.index("## How the inventories")]
    entry = reviewed[reviewed.index("**CUBRID-Python**") :]
    assert "**unresolved**" in entry
    assert "BSD, variant unspecified" in entry


def test_no_blanket_permissive_claim() -> None:
    for stale in ("No dependency is copyleft", "All listed dependencies are distributed under"):
        assert stale not in DOC


def test_generation_inputs_are_recorded() -> None:
    record = DOC[DOC.index("## How the inventories were generated") :]
    assert re.search(r"commit `[0-9a-f]{40}`", record)
    assert re.search(r"CPython 3\.\d+\.\d+ on Linux", record)
    assert "scripts/generate_third_party_licenses.py --exclude sqlalchemy-cubrid" in record
    for scope in ("pycubrid", "alembic", "cubrid", "dev"):
        assert f".[{scope}]" in record
