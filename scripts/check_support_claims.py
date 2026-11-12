"""Check structured current-support claims against package metadata (#780).

Update this check with the reviewed support matrix when policy intentionally
changes. Historical PRD and release snapshots are outside this current-support
contract; see the dated evidence in their own documents.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]


def _section(document: str, heading: str) -> str:
    match = re.search(rf"(?ms)^### {re.escape(heading)}\n(.*?)(?=^### |^## |\Z)", document)
    return match.group(1) if match else ""


def _top_section(document: str, heading: str) -> str:
    match = re.search(rf"(?ms)^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", document)
    return match.group(1) if match else ""


def check_claims(metadata: str, readme: str, matrix: str) -> list[str]:
    """Return discrepancies in current English support declarations."""
    document = tomllib.loads(metadata)
    project = document["project"]
    extras = project["optional-dependencies"]
    # Contributor tooling is a PEP 735 dependency group (#765); the test group
    # carries the SQLAlchemy bound the offline suite installs.
    test_group = [item for item in document["dependency-groups"]["test"] if isinstance(item, str)]
    problems: list[str] = []

    minimum_match = re.fullmatch(r">=(\d+)\.(\d+)", project["requires-python"])
    if minimum_match is None:
        return ["pyproject.toml: requires-python needs a reviewed minimum"]
    major, minor = (int(part) for part in minimum_match.groups())
    minimum = f"{major}.{minor}"
    previous = f"{major}.{minor - 1}"

    requirements = {
        group: [Requirement(item) for item in values]
        for group, values in {
            "project": project["dependencies"],
            "test": test_group,
            "pycubrid": extras["pycubrid"],
            "cubrid": extras.get("cubrid", []),
            "cubriddb": extras.get("cubriddb", []),
        }.items()
    }
    for group in ("cubrid", "cubriddb"):
        if len(requirements[group]) != 1 or requirements[group][0].name.lower() != "cubrid-python":
            problems.append(f"pyproject.toml: {group} extra must install CUBRID-Python")
        elif not requirements[group][0].specifier.contains(Version("9.3.0.1")):
            # The docs promise that these extras install the PyPI 9.3.0 release, which
            # pip resolves as 9.3.0.1 because the 9.3.0.0002 archive's metadata also
            # declares 9.3.0.1 (#1139).
            problems.append(f"pyproject.toml: {group} extra must admit CUBRID-Python 9.3.0.1")
    pycubrid = [item for item in requirements["pycubrid"] if item.name.lower() == "pycubrid"]
    if len(pycubrid) != 1:
        problems.append("pyproject.toml: pycubrid extra needs one driver requirement")
    else:
        py_lower = [item.version for item in pycubrid[0].specifier if item.operator == ">="]
        py_upper = [item.version for item in pycubrid[0].specifier if item.operator == "<"]
        if len(py_lower) != 1 or len(py_upper) != 1:
            problems.append("pyproject.toml: pycubrid needs reviewed lower and upper bounds")
        else:
            py_bound = f">={py_lower[0]},<{py_upper[0]}"
            for variant in ("sync", "async"):
                if f"| pycubrid ({variant}) | {py_bound} |" not in readme:
                    problems.append(f"README.md: pycubrid {variant} bound must match metadata")
            current_claims = (
                ("README.md", _top_section(readme, "Known Limitations")),
                ("README.md", _top_section(readme, "FAQ")),
                ("docs/SUPPORT_MATRIX.md", _section(matrix, "Known Limitations")),
            )
            for name, section in current_claims:
                stated = re.findall(
                    r"pycubrid\s*>=\s*(\d+\.\d+\.\d+)\s*,\s*<\s*(\d+\.\d+)", section
                )
                if not stated or any(
                    f">={floor},<{ceiling}" != py_bound for floor, ceiling in stated
                ):
                    problems.append(f"{name}: pycubrid package bounds differ from metadata")
    sqlalchemy_specs = {
        group: [str(item.specifier) for item in values if item.name.lower() == "sqlalchemy"]
        for group, values in requirements.items()
        if group in ("project", "test", "pycubrid")
    }
    if (
        any(len(specs) != 1 for specs in sqlalchemy_specs.values())
        or len({spec for specs in sqlalchemy_specs.values() for spec in specs}) != 1
    ):
        problems.append("pyproject.toml: project, test group and pycubrid SQLAlchemy bounds differ")
    else:
        sqlalchemy = next(
            item for item in requirements["project"] if item.name.lower() == "sqlalchemy"
        )
        upper = [item.version for item in sqlalchemy.specifier if item.operator == "<"]
        lower = [item.version for item in sqlalchemy.specifier if item.operator == ">="]
        if len(upper) != 1 or len(lower) != 1:
            problems.append("pyproject.toml: SQLAlchemy needs reviewed lower and upper bounds")
        else:
            sqlalchemy_rows = _section(matrix, "SQLAlchemy")
            for version in lower:
                if not re.search(
                    rf"^\| {re.escape(version)}\.x \| ✅ Supported \|",
                    sqlalchemy_rows,
                    re.M,
                ):
                    problems.append(
                        f"docs/SUPPORT_MATRIX.md: SQLAlchemy {version} must be supported"
                    )
            for version in upper:
                if not re.search(
                    rf"^\| ≥ {re.escape(version)} \| ❌ Not supported \|",
                    sqlalchemy_rows,
                    re.M,
                ):
                    problems.append(
                        f"docs/SUPPORT_MATRIX.md: SQLAlchemy {version}+ must be excluded"
                    )
            bound = f">={lower[0]},<{upper[0]}"
            support_status = re.search(r"(?ms)^## Support Status\n(.*?)(?=^## |\Z)", readme)
            if support_status is None or not re.search(
                rf"^- Supported matrix: SQLAlchemy `{re.escape(bound)}`[,]",
                support_status.group(1),
                re.M,
            ):
                problems.append("README.md: SQLAlchemy support matrix bound differs")
            lower_parts = lower[0].split(".")
            upper_parts = upper[0].split(".")
            if (
                len(lower_parts) != 2
                or len(upper_parts) != 2
                or lower_parts[0] != upper_parts[0]
                or int(upper_parts[1]) <= int(lower_parts[1])
            ):
                problems.append("pyproject.toml: README SQLAlchemy range needs review")
            else:
                range_label = f"SQLAlchemy {lower[0]} – {upper_parts[0]}.{int(upper_parts[1]) - 1}"
                requirements_text = re.search(r"(?ms)^## Requirements\n(.*?)(?=^## |\Z)", readme)
                if requirements_text is None or not re.search(
                    rf"^- {re.escape(range_label)}$", requirements_text.group(1), re.M
                ):
                    problems.append("README.md: SQLAlchemy Requirements range differs")

    python_rows = _section(matrix, "Python")
    if not re.search(rf"^\| {re.escape(minimum)} \| ✅ Supported \|", python_rows, re.M):
        problems.append(f"docs/SUPPORT_MATRIX.md: Python {minimum} must be supported")
    if minor > 0 and not re.search(
        rf"^\| {re.escape(previous)} \| ❌ Not supported", python_rows, re.M
    ):
        problems.append(f"docs/SUPPORT_MATRIX.md: Python {previous} must not be current")
    requirements_text = re.search(r"(?ms)^## Requirements\n(.*?)(?=^## |\Z)", readme)
    if requirements_text is None or not re.search(
        rf"^- Python {re.escape(minimum)} or later$", requirements_text.group(1), re.M
    ):
        problems.append(f"README.md: current Python minimum must be {minimum}")
    current_parts: list[str] = []
    for heading in ("Requirements", "Installation", "FAQ"):
        match = re.search(rf"(?ms)^## {heading}\n(.*?)(?=^## |\Z)", readme)
        if match:
            current_parts.append(match.group(1))
    current_readme = "\n".join(current_parts)
    if re.search(
        r"\b(?:legacy|deprecated|obsolete) (?:CUBRIDdb(?: C-extension)?|C-extension) driver\b"
        r"|\bCUBRIDdb (?:driver|C-extension driver) is (?:deprecated|obsolete)\b",
        current_readme,
        re.I,
    ):
        problems.append("README.md: supported CUBRIDdb driver is misclassified")

    problems.extend(_check_cubriddb_policy(_section(matrix, "Drivers")))
    return problems


# Words that would declare a supported driver line or a maintained extra out of
# support. Known limitations belong in the verification table instead (#1139).
_DISCONTINUED = re.compile(
    r"deprecat|legacy|obsolete|discontinu|unsupported|not supported|untested|no longer"
    r"|end[- ]of[- ]life|\bEOL\b|\bdropped\b",
    re.I,
)
# A status limited to one driver line ("v11.3.0.51 only") drops the other one.
_ONE_LINE_ONLY = re.compile(r"\bonly\b", re.I)
# Pass claims that a reviewed 9.3.x run must exist for before they are allowed.
_PASS_CLAIM = re.compile(r"[✅✔✓]|\bpass(?:ed|es|ing)?\b|tested in CI|(?<!not )\bverified\b", re.I)


def _row(rows: str, prefix: str) -> list[str] | None:
    match = re.search(rf"^{re.escape(prefix)}[^\n]*$", rows, re.M)
    if match is None:
        return None
    return [cell.strip() for cell in match.group(0).strip().strip("|").split("|")]


def _check_cubriddb_policy(driver_rows: str) -> list[str]:
    """Both CUBRIDdb lines stay supported, and verification is reported apart (#1144).

    The policy row must name both maintained installation options (the PyPI
    9.3.0 release behind the ``[cubrid]`` / ``[cubriddb]`` extras and the
    v11.3.0.51 source build) without calling either one discontinued. The
    verification table must keep the PyPI 9.3.x line marked as not verified
    until a reviewed passing run exists; changing that is a policy change that
    updates this check and its tests together.
    """
    problems: list[str] = []
    policy = _row(driver_rows, "| CUBRIDdb (CCI) |")
    if policy is None:
        problems.append("docs/SUPPORT_MATRIX.md: CUBRIDdb driver row is missing")
    elif len(policy) != 4:
        problems.append("docs/SUPPORT_MATRIX.md: CUBRIDdb driver row is malformed")
    else:
        install, status = policy[1], policy[3]
        if not all(token in install for token in ("[cubrid]", "[cubriddb]", "9.3.0", "v11.3.0.51")):
            problems.append(
                "docs/SUPPORT_MATRIX.md: CUBRIDdb install guidance needs both driver lines"
            )
        if _DISCONTINUED.search(install):
            problems.append(
                "docs/SUPPORT_MATRIX.md: maintained CUBRIDdb installation extras are misclassified"
            )
        if (
            "Supported" not in status
            or _DISCONTINUED.search(status)
            or _ONE_LINE_ONLY.search(status)
        ):
            problems.append("docs/SUPPORT_MATRIX.md: supported CUBRIDdb driver is misclassified")

    verification = re.search(r"(?ms)^#### Driver verification\n(.*)", driver_rows)
    if verification is None:
        problems.append("docs/SUPPORT_MATRIX.md: driver verification table is missing")
        return problems
    rows = verification.group(1)
    pypi_prefix = "| CUBRIDdb, PyPI `CUBRID-Python` 9.3"
    if len(re.findall(rf"^{re.escape(pypi_prefix)}", rows, re.M)) > 1:
        problems.append("docs/SUPPORT_MATRIX.md: PyPI CUBRID-Python 9.3.x has several rows")
        return problems
    pypi = _row(rows, pypi_prefix)
    source = _row(rows, "| CUBRIDdb, built from cubrid-python v11.3.0.51")
    if pypi is None or source is None:
        problems.append("docs/SUPPORT_MATRIX.md: a CUBRIDdb driver line lacks a verification row")
    elif len(pypi) != 3 or len(source) != 3:
        problems.append("docs/SUPPORT_MATRIX.md: CUBRIDdb verification row is malformed")
    else:
        verified, limitations = pypi[1], pypi[2]
        if _PASS_CLAIM.search(verified) or not re.search(
            r"\bnot (?:run|verified)\b", verified, re.I
        ):
            problems.append(
                "docs/SUPPORT_MATRIX.md: PyPI CUBRID-Python 9.3.x is reported as verified"
            )
        if not all(issue in limitations for issue in ("#583", "#585")):
            problems.append(
                "docs/SUPPORT_MATRIX.md: PyPI CUBRID-Python 9.3.x known limitations are missing"
            )
    return problems


# Korean wording that would classify a maintained driver line as discontinued.
_KO_DISCONTINUED = re.compile(
    r"폐기|레거시|지원되지 않|지원하지 않|지원 중단|더 이상|테스트되지 않|deprecat|legacy|unsupported",
    re.I,
)


def check_korean_cubriddb_policy(ko_matrix: str) -> list[str]:
    """Keep the Korean support matrix on the same CUBRIDdb policy as English (#1148).

    The Korean page is a translation, so this checks the policy facts rather
    than wording: the CUBRIDdb row names both installation options and calls
    neither discontinued, and the verification table keeps exactly one PyPI
    9.3.x row that is not reported as tested and cites #583 and #585.
    """
    where = "docs/ko/SUPPORT_MATRIX.md"
    problems: list[str] = []
    policy = _row(ko_matrix, "| CUBRIDdb (CCI) |")
    if policy is None or len(policy) != 4:
        problems.append(f"{where}: CUBRIDdb driver row is missing or malformed")
    else:
        install, status = policy[1], policy[3]
        if not all(token in install for token in ("[cubrid]", "[cubriddb]", "9.3.0", "v11.3.0.51")):
            problems.append(f"{where}: CUBRIDdb install guidance needs both driver lines")
        if _KO_DISCONTINUED.search(install) or _KO_DISCONTINUED.search(status):
            problems.append(f"{where}: supported CUBRIDdb driver is misclassified")
        if "지원" not in status:
            problems.append(f"{where}: supported CUBRIDdb driver is misclassified")

    verification = re.search(r"(?ms)^#### 드라이버 검증 현황\n(.*)", ko_matrix)
    if verification is None:
        problems.append(f"{where}: driver verification table is missing")
        return problems
    rows = verification.group(1)
    pypi_prefix = "| CUBRIDdb, PyPI `CUBRID-Python` 9.3"
    if len(re.findall(rf"^{re.escape(pypi_prefix)}", rows, re.M)) != 1:
        problems.append(f"{where}: PyPI CUBRID-Python 9.3.x needs exactly one verification row")
        return problems
    pypi = _row(rows, pypi_prefix)
    assert pypi is not None
    if len(pypi) != 3:
        problems.append(f"{where}: CUBRIDdb verification row is malformed")
        return problems
    verified, limitations = pypi[1], pypi[2]
    if re.search(r"[✅✔✓]|CI에서 테스트", verified) or not re.search(
        r"실행하지 않음|검증되지 않음", verified
    ):
        problems.append(f"{where}: PyPI CUBRID-Python 9.3.x is reported as verified")
    if not all(issue in limitations for issue in ("#583", "#585")):
        problems.append(f"{where}: PyPI CUBRID-Python 9.3.x known limitations are missing")
    return problems


def main() -> int:
    problems = check_claims(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
        (ROOT / "README.md").read_text(encoding="utf-8"),
        (ROOT / "docs/SUPPORT_MATRIX.md").read_text(encoding="utf-8"),
    )
    problems.extend(
        check_korean_cubriddb_policy(
            (ROOT / "docs/ko/SUPPORT_MATRIX.md").read_text(encoding="utf-8")
        )
    )
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    print("Current support claims match package metadata and driver policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
