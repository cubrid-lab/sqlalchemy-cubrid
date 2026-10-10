"""Current support declarations remain distinct from historical evidence (#780)."""

from __future__ import annotations

from pathlib import Path

from scripts.check_support_claims import check_claims

ROOT = Path(__file__).resolve().parents[1]
METADATA = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MATRIX = (ROOT / "docs/SUPPORT_MATRIX.md").read_text(encoding="utf-8")


def test_current_support_contract() -> None:
    assert check_claims(METADATA, README, MATRIX) == []


def test_historical_python_and_cas_terms_are_allowed() -> None:
    historical = (
        "\n## Release history\nPython 3.10 was supported in 1.9.x. Legacy CAS error-code format.\n"
    )
    assert check_claims(METADATA, README + historical, MATRIX + historical) == []


def test_current_python_minimum_conflict_is_rejected() -> None:
    readme = README.replace("- Python 3.11 or later", "- Python 3.10 or later")
    assert "README.md: current Python minimum must be 3.11" in check_claims(
        METADATA, readme, MATRIX
    )


def test_deprecated_extra_is_allowed_but_deprecated_driver_is_rejected() -> None:
    assert check_claims(METADATA, README, MATRIX) == []
    matrix = MATRIX.replace("✅ Supported C-extension driver", "✅ Deprecated C-extension driver")
    assert "docs/SUPPORT_MATRIX.md: supported CUBRIDdb driver is misclassified" in check_claims(
        METADATA, README, matrix
    )
    readme = README.replace(
        "With the CUBRIDdb C-extension driver", "With the legacy CUBRIDdb C-extension driver"
    )
    assert "README.md: supported CUBRIDdb driver is misclassified" in check_claims(
        METADATA, readme, MATRIX
    )


def test_dev_and_pycubrid_sqlalchemy_bounds_must_match_project() -> None:
    for group in ("dev", "pycubrid"):
        start = METADATA.index(f"{group} = [")
        end = METADATA.index("\n]", start)
        section = METADATA[start:end]
        assert section.count("sqlalchemy[asyncio]>=2.0,<2.2") == 1
        metadata = (
            METADATA[:start]
            + section.replace("sqlalchemy[asyncio]>=2.0,<2.2", "sqlalchemy[asyncio]>=2.0,<2.3")
            + METADATA[end:]
        )
        assert "pyproject.toml: project, dev and pycubrid SQLAlchemy bounds differ" in check_claims(
            metadata, README, MATRIX
        )


def test_current_sqlalchemy_support_disagreement_is_rejected() -> None:
    matrix = MATRIX.replace("| ≥ 2.2 | ❌ Not supported", "| ≥ 2.3 | ❌ Not supported")
    assert "docs/SUPPORT_MATRIX.md: SQLAlchemy 2.2+ must be excluded" in check_claims(
        METADATA, README, matrix
    )


def test_pycubrid_driver_floor_must_match_readme() -> None:
    metadata = METADATA.replace('"pycubrid>=1.8.0,<2.0"', '"pycubrid>=1.7.0,<2.0"')
    assert "README.md: pycubrid sync bound must match metadata" in check_claims(
        metadata, README, MATRIX
    )


def test_deprecated_extras_must_keep_pypi_driver_package() -> None:
    metadata = METADATA.replace('"CUBRID-Python"', '"pycubrid"')
    problems = check_claims(metadata, README, MATRIX)
    assert "pyproject.toml: deprecated cubrid extra must install CUBRID-Python" in problems
    assert "pyproject.toml: deprecated cubriddb extra must install CUBRID-Python" in problems


def test_readme_requirements_sqlalchemy_range_must_match_metadata() -> None:
    readme = README.replace("- SQLAlchemy 2.0 – 2.1", "- SQLAlchemy 2.0 – 2.2")
    assert "README.md: SQLAlchemy Requirements range differs" in check_claims(
        METADATA, readme, MATRIX
    )
    readme = README.replace(
        "Supported matrix: SQLAlchemy `>=2.0,<2.2`", "Supported matrix: SQLAlchemy `>=2.0,<2.3`"
    )
    assert "README.md: SQLAlchemy support matrix bound differs" in check_claims(
        METADATA, readme, MATRIX
    )
