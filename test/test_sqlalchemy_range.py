"""The SQLAlchemy range in package metadata and the documented support stay equal (#774)."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

ROOT = Path(__file__).resolve().parents[1]
README_TRANSLATIONS = sorted((ROOT / "docs").glob("README.*.md"))
# User-facing documents that state the project pin as "<N.M".
PIN_DOCS = [
    "README.md",
    "THIRD_PARTY_LICENSES.md",
    "docs/ARCHITECTURE.md",
    "docs/ko/ARCHITECTURE.md",
    "docs/PRD.md",
    "docs/ko/PRD.md",
    "docs/SA_COMPAT.md",
    "docs/ko/SA_COMPAT.md",
    "docs/SUPPORT_MATRIX.md",
    "docs/ko/SUPPORT_MATRIX.md",
    *(str(p.relative_to(ROOT)) for p in README_TRANSLATIONS),
]
# The project pin always starts at the 2.0 floor; the canary starts at a pre-release.
PIN_PATTERN = re.compile(r">=\s?2\.0,\s?<\s?(\d+\.\d+)")


def _sqlalchemy_requirements() -> list[Requirement]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    lists = [project["dependencies"], *project["optional-dependencies"].values()]
    reqs = [Requirement(r) for deps in lists for r in deps]
    return [r for r in reqs if r.name.lower() == "sqlalchemy"]


def _cap() -> tuple[int, int]:
    """Return the exclusive upper bound ``(major, minor)`` shared by every requirement."""
    reqs = _sqlalchemy_requirements()
    assert reqs, "pyproject.toml declares no sqlalchemy requirement"
    specs = {str(r.specifier) for r in reqs}
    assert len(specs) == 1, f"sqlalchemy specifiers differ across pyproject extras: {specs}"
    uppers = [s.version for s in SpecifierSet(specs.pop()) if s.operator == "<"]
    assert len(uppers) == 1, "sqlalchemy needs exactly one '<' upper bound"
    major, minor, *rest = (int(p) for p in uppers[0].split("."))
    assert not any(rest), "the upper bound must be a minor boundary like <2.2"
    return major, minor


def _read(rel: str) -> str:
    return (ROOT / rel).read_text()


def test_every_documented_pin_equals_the_pyproject_cap() -> None:
    cap = ".".join(map(str, _cap()))
    for rel in PIN_DOCS:
        found = set(PIN_PATTERN.findall(_read(rel)))
        assert found <= {cap}, f"{rel} states <{found}, pyproject caps at <{cap}"
    stated = [rel for rel in PIN_DOCS if re.search(rf"<\s?{re.escape(cap)}", _read(rel))]
    assert set(stated) == set(PIN_DOCS), f"missing '<{cap}': {set(PIN_DOCS) - set(stated)}"


def test_support_matrix_marks_every_minor_from_the_cap_up_as_unsupported() -> None:
    major, cap_minor = _cap()
    for rel in ("docs/SUPPORT_MATRIX.md", "docs/ko/SUPPORT_MATRIX.md"):
        text = _read(rel)
        for minor in range(cap_minor):
            assert re.search(rf"^\| {major}\.{minor}\.x \| ✅", text, re.M), (rel, minor)
        assert re.search(rf"^\| ≥ {major}\.{cap_minor} \| ❌", text, re.M), rel
        assert f"`<{major}.{cap_minor}`" in text, rel


def test_readme_states_the_supported_minors() -> None:
    major, cap_minor = _cap()
    text = _read("README.md")
    assert f"SQLAlchemy {major}.0–{major}.{cap_minor - 1} only" in text
    for rel in (str(p.relative_to(ROOT)) for p in README_TRANSLATIONS):
        assert f"SQLAlchemy {major}.0–{major}.{cap_minor - 1}" in _read(rel), rel
