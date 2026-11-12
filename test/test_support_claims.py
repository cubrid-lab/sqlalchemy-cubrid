"""Current support declarations remain distinct from historical evidence (#780)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.check_support_claims import check_claims

ROOT = Path(__file__).resolve().parents[1]
METADATA = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
MATRIX = (ROOT / "docs/SUPPORT_MATRIX.md").read_text(encoding="utf-8")


def test_current_support_contract() -> None:
    assert check_claims(METADATA, README, MATRIX) == []


def test_historical_python_and_cas_terms_are_allowed() -> None:
    historical = (
        "\n## Release history\nPython 3.10 was supported in 1.9.x. Legacy CAS error-code format. "
        "The old pycubrid>=1.7.0,<2.0 bound applied to that release.\n"
    )
    assert check_claims(METADATA, README + historical, MATRIX + historical) == []


def test_current_python_minimum_conflict_is_rejected() -> None:
    readme = README.replace("- Python 3.11 or later", "- Python 3.10 or later")
    assert "README.md: current Python minimum must be 3.11" in check_claims(
        METADATA, readme, MATRIX
    )


POLICY_ROW = "| CUBRIDdb (CCI) |"
PYPI_ROW = "| CUBRIDdb, PyPI `CUBRID-Python` 9.3"
SOURCE_ROW = "| CUBRIDdb, built from cubrid-python v11.3.0.51"


def _row(prefix: str) -> str:
    rows = [line for line in MATRIX.splitlines() if line.startswith(prefix)]
    assert len(rows) == 1, f"support matrix fixture changed: {prefix}"
    return rows[0]


def _set_row(prefix: str, replacement: str) -> str:
    """Return the support matrix with the row starting with ``prefix`` replaced."""
    row = _row(prefix)
    assert replacement != row, f"mutation did not change the row: {prefix}"
    return MATRIX.replace(row, replacement, 1)


def _set_cell(prefix: str, index: int, value: str) -> str:
    """Return the support matrix with one cell (0-based, after the row start) replaced."""
    cells = _row(prefix).split("|")
    cells[index + 1] = f" {value} "
    return _set_row(prefix, "|".join(cells))


def _edit_row(prefix: str, old: str, new: str) -> str:
    row = _row(prefix)
    assert old in row, f"support matrix fixture changed: {old}"
    return _set_row(prefix, row.replace(old, new, 1))


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("[cubrid]", "CUBRIDdb install guidance needs both driver lines"),
        ("[cubriddb]", "CUBRIDdb install guidance needs both driver lines"),
        ("9.3.0", "CUBRIDdb install guidance needs both driver lines"),
        ("v11.3.0.51", "CUBRIDdb install guidance needs both driver lines"),
    ],
)
def test_cubriddb_policy_row_must_name_both_driver_lines(token: str, expected: str) -> None:
    """Removing either maintained installation option fails the check (#1144)."""
    install = _row(POLICY_ROW).split("|")[2]
    assert token in install, f"support matrix fixture changed: {token}"
    matrix = _set_cell(POLICY_ROW, 1, install.replace(token, "").strip())
    assert f"docs/SUPPORT_MATRIX.md: {expected}" in check_claims(METADATA, README, matrix)


@pytest.mark.parametrize(
    "wording",
    ["deprecated", "Legacy", "obsolete", "discontinued", "unsupported", "not supported"],
)
def test_maintained_extras_cannot_be_called_discontinued(wording: str) -> None:
    """The extras are maintained installation options, not a removal path (#1139)."""
    matrix = _edit_row(POLICY_ROW, "Two maintained installation options", f"Two {wording} options")
    assert (
        "docs/SUPPORT_MATRIX.md: maintained CUBRIDdb installation extras are misclassified"
        in check_claims(METADATA, README, matrix)
    )


@pytest.mark.parametrize(
    "status",
    [
        "✅ Deprecated C-extension driver",
        "Untested driver",
        "✅ Supported C-extension driver (v11.3.0.51 only)",
        "✅ Supported C-extension driver; 9.3.0 no longer maintained",
    ],
)
def test_supported_cubriddb_driver_cannot_be_misclassified(status: str) -> None:
    matrix = _set_cell(POLICY_ROW, 3, status)
    assert "docs/SUPPORT_MATRIX.md: supported CUBRIDdb driver is misclassified" in check_claims(
        METADATA, README, matrix
    )


def test_legacy_cubriddb_driver_in_readme_is_rejected() -> None:
    readme = README.replace(
        "With the CUBRIDdb C-extension driver", "With the legacy CUBRIDdb C-extension driver"
    )
    assert readme != README
    assert "README.md: supported CUBRIDdb driver is misclassified" in check_claims(
        METADATA, readme, MATRIX
    )


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ("missing", "CUBRIDdb driver row is missing"),
        ("malformed", "CUBRIDdb driver row is malformed"),
    ],
)
def test_cubriddb_policy_row_errors_are_reported(change: str, expected: str) -> None:
    matrix = _set_row(POLICY_ROW, "" if change == "missing" else _row(POLICY_ROW) + " extra |")
    assert f"docs/SUPPORT_MATRIX.md: {expected}" in check_claims(METADATA, README, matrix)


def test_pypi_driver_line_cannot_be_reported_as_verified() -> None:
    """A passing 9.3.x claim needs reviewed evidence and a coordinated check update."""
    for verified in (
        "✅ Tested in CI",
        "Passed on CUBRID 11.4",
        "Not run in CI. ✔ Passed all integration tests on Python 3.12 / CUBRID 11.4",
        "Not run in CI; verified on Python 3.12",
    ):
        matrix = _set_cell(PYPI_ROW, 1, verified)
        assert (
            "docs/SUPPORT_MATRIX.md: PyPI CUBRID-Python 9.3.x is reported as verified"
            in check_claims(METADATA, README, matrix)
        )


def test_pypi_driver_line_keeps_known_limitations() -> None:
    matrix = _edit_row(PYPI_ROW, "#585, ", "")
    assert (
        "docs/SUPPORT_MATRIX.md: PyPI CUBRID-Python 9.3.x known limitations are missing"
        in check_claims(METADATA, README, matrix)
    )


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ("no-table", "driver verification table is missing"),
        ("no-pypi-row", "a CUBRIDdb driver line lacks a verification row"),
        ("no-source-row", "a CUBRIDdb driver line lacks a verification row"),
        ("malformed", "CUBRIDdb verification row is malformed"),
        ("duplicate", "PyPI CUBRID-Python 9.3.x has several rows"),
    ],
)
def test_driver_verification_table_errors_are_reported(change: str, expected: str) -> None:
    if change == "no-table":
        assert MATRIX.count("#### Driver verification\n") == 1
        matrix = MATRIX.replace("#### Driver verification\n", "#### Driver notes\n")
    elif change == "no-pypi-row":
        matrix = _set_row(PYPI_ROW, "")
    elif change == "no-source-row":
        matrix = _set_row(SOURCE_ROW, "")
    elif change == "duplicate":
        matrix = _set_row(PYPI_ROW, _row(PYPI_ROW) + "\n" + _row(PYPI_ROW).replace("#583", "#1"))
    else:
        matrix = _set_row(PYPI_ROW, _row(PYPI_ROW) + " extra |")
    assert f"docs/SUPPORT_MATRIX.md: {expected}" in check_claims(METADATA, README, matrix)


def test_test_group_and_pycubrid_sqlalchemy_bounds_must_match_project() -> None:
    for group in ("test", "pycubrid"):
        start = METADATA.index(f"{group} = [")
        end = METADATA.index("\n]", start)
        section = METADATA[start:end]
        assert section.count("sqlalchemy[asyncio]>=2.0,<2.2") == 1
        metadata = (
            METADATA[:start]
            + section.replace("sqlalchemy[asyncio]>=2.0,<2.2", "sqlalchemy[asyncio]>=2.0,<2.3")
            + METADATA[end:]
        )
        assert (
            "pyproject.toml: project, test group and pycubrid SQLAlchemy bounds differ"
            in check_claims(metadata, README, MATRIX)
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


def test_pycubrid_floor_change_needs_all_current_claims_updated() -> None:
    metadata = METADATA.replace('"pycubrid>=1.8.0,<2.0"', '"pycubrid>=1.9.0,<2.0"')
    readme = README.replace(
        "| pycubrid (sync) | >=1.8.0,<2.0 |", "| pycubrid (sync) | >=1.9.0,<2.0 |"
    )
    readme = readme.replace(
        "| pycubrid (async) | >=1.8.0,<2.0 |", "| pycubrid (async) | >=1.9.0,<2.0 |"
    )
    problems = check_claims(metadata, readme, MATRIX)
    assert "README.md: pycubrid package bounds differ from metadata" in problems
    assert "docs/SUPPORT_MATRIX.md: pycubrid package bounds differ from metadata" in problems


def test_missing_current_pycubrid_claim_is_rejected() -> None:
    matrix = MATRIX.replace("requires pycubrid >= 1.8.0,<2.0", "requires pycubrid")
    assert "docs/SUPPORT_MATRIX.md: pycubrid package bounds differ from metadata" in check_claims(
        METADATA, README, matrix
    )


def test_coordinated_pycubrid_floor_change_is_allowed() -> None:
    metadata = METADATA.replace('"pycubrid>=1.8.0,<2.0"', '"pycubrid>=1.9.0,<2.0"')
    readme = README.replace(">=1.8.0,<2.0", ">=1.9.0,<2.0")
    readme = readme.replace(">= 1.8.0,<2.0", ">= 1.9.0,<2.0")
    matrix = MATRIX.replace(">= 1.8.0,<2.0", ">= 1.9.0,<2.0")
    assert check_claims(metadata, readme, matrix) == []


def test_maintained_extras_must_keep_pypi_driver_package() -> None:
    metadata = METADATA.replace('"CUBRID-Python"', '"pycubrid"')
    problems = check_claims(metadata, README, MATRIX)
    assert "pyproject.toml: cubrid extra must install CUBRID-Python" in problems
    assert "pyproject.toml: cubriddb extra must install CUBRID-Python" in problems


def test_removed_extra_is_reported() -> None:
    start = METADATA.index("cubriddb = [")
    end = METADATA.index("]", start) + 1
    metadata = METADATA[:start] + METADATA[end:]
    assert "pyproject.toml: cubriddb extra must install CUBRID-Python" in check_claims(
        metadata, README, MATRIX
    )


def test_extras_must_admit_the_pypi_release() -> None:
    assert METADATA.count('"CUBRID-Python"') == 2
    metadata = METADATA.replace('"CUBRID-Python"', '"CUBRID-Python>=11.3"')
    problems = check_claims(metadata, README, MATRIX)
    assert "pyproject.toml: cubrid extra must admit CUBRID-Python 9.3.0.1" in problems
    assert "pyproject.toml: cubriddb extra must admit CUBRID-Python 9.3.0.1" in problems


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


KO_MATRIX = (ROOT / "docs/ko/SUPPORT_MATRIX.md").read_text(encoding="utf-8")
KO_POLICY_ROW = "| CUBRIDdb (CCI) |"


def _ko_line(prefix: str) -> str:
    return next(line for line in KO_MATRIX.splitlines() if line.startswith(prefix))


def _ko_edit(prefix: str, old: str, new: str) -> str:
    line = _ko_line(prefix)
    assert old in line
    return KO_MATRIX.replace(line, line.replace(old, new, 1), 1)


def test_korean_matrix_keeps_the_cubriddb_policy() -> None:
    from scripts.check_support_claims import check_korean_cubriddb_policy

    assert check_korean_cubriddb_policy(KO_MATRIX) == []


@pytest.mark.parametrize(
    ("matrix", "expected"),
    [
        (
            _ko_edit(KO_POLICY_ROW, "유지되는 두 가지 설치 방법", "폐기 예정인 설치 방법"),
            "supported CUBRIDdb driver is misclassified",
        ),
        (
            _ko_edit(KO_POLICY_ROW, "v11.3.0.51", "v11.3"),
            "CUBRIDdb install guidance needs both driver lines",
        ),
        (
            _ko_edit(KO_POLICY_ROW, "[cubriddb]", "[pycubrid]"),
            "CUBRIDdb install guidance needs both driver lines",
        ),
        (
            KO_MATRIX.replace(_ko_line(KO_POLICY_ROW), "| CUBRIDdb (CCI) | 설치 |", 1),
            "CUBRIDdb driver row is missing or malformed",
        ),
        (
            _ko_edit(PYPI_ROW, "CI에서 실행하지 않음", "✅ CI에서 테스트됨"),
            "PyPI CUBRID-Python 9.3.x is reported as verified",
        ),
        (
            _ko_edit(PYPI_ROW, "#585", "#999"),
            "PyPI CUBRID-Python 9.3.x known limitations are missing",
        ),
        (
            KO_MATRIX.replace("#### 드라이버 검증 현황\n", "#### 드라이버 참고\n", 1),
            "driver verification table is missing",
        ),
        (
            KO_MATRIX.replace(_ko_line(PYPI_ROW), _ko_line(PYPI_ROW) + "\n" + _ko_line(PYPI_ROW)),
            "PyPI CUBRID-Python 9.3.x needs exactly one verification row",
        ),
        (
            KO_MATRIX.replace(_ko_line(PYPI_ROW), "| CUBRIDdb, PyPI `CUBRID-Python` 9.3.0 | x |"),
            "CUBRIDdb verification row is malformed",
        ),
    ],
)
def test_korean_matrix_policy_errors_are_reported(matrix: str, expected: str) -> None:
    from scripts.check_support_claims import check_korean_cubriddb_policy

    assert f"docs/ko/SUPPORT_MATRIX.md: {expected}" in check_korean_cubriddb_policy(matrix)


def test_korean_status_must_say_supported() -> None:
    from scripts.check_support_claims import check_korean_cubriddb_policy

    line = _ko_line(KO_POLICY_ROW)
    cells = line.split("|")
    cells[4] = " C 확장 드라이버 "
    matrix = KO_MATRIX.replace(line, "|".join(cells), 1)
    assert "docs/ko/SUPPORT_MATRIX.md: supported CUBRIDdb driver is misclassified" in (
        check_korean_cubriddb_policy(matrix)
    )


def test_main_checks_the_korean_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import scripts.check_support_claims as checker

    for name in (
        "pyproject.toml",
        "README.md",
        "docs/SUPPORT_MATRIX.md",
        "docs/ko/SUPPORT_MATRIX.md",
    ):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((ROOT / name).read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    assert checker.main() == 0

    ko = tmp_path / "docs/ko/SUPPORT_MATRIX.md"
    ko.write_text(KO_MATRIX.replace("#### 드라이버 검증 현황\n", "", 1), encoding="utf-8")
    assert checker.main() == 1
    assert "docs/ko/SUPPORT_MATRIX.md: driver verification table is missing" in (
        capsys.readouterr().err
    )
