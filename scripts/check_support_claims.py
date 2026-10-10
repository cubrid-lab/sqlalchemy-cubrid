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

ROOT = Path(__file__).resolve().parents[1]


def _section(document: str, heading: str) -> str:
    match = re.search(rf"(?ms)^### {re.escape(heading)}\n(.*?)(?=^### |^## |\Z)", document)
    return match.group(1) if match else ""


def check_claims(metadata: str, readme: str, matrix: str) -> list[str]:
    """Return discrepancies in current English support declarations."""
    project = tomllib.loads(metadata)["project"]
    extras = project["optional-dependencies"]
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
            "dev": extras["dev"],
            "pycubrid": extras["pycubrid"],
            "cubrid": extras["cubrid"],
            "cubriddb": extras["cubriddb"],
        }.items()
    }
    for group in ("cubrid", "cubriddb"):
        if len(requirements[group]) != 1 or requirements[group][0].name.lower() != "cubrid-python":
            problems.append(f"pyproject.toml: deprecated {group} extra must install CUBRID-Python")
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
            for name, document in (("README.md", readme), ("docs/SUPPORT_MATRIX.md", matrix)):
                stated = re.findall(
                    r"pycubrid\s*>=\s*(\d+\.\d+\.\d+)\s*,\s*<\s*(\d+\.\d+)", document
                )
                if any(f">={floor},<{ceiling}" != py_bound for floor, ceiling in stated):
                    problems.append(f"{name}: pycubrid package bounds differ from metadata")
    sqlalchemy_specs = {
        group: [str(item.specifier) for item in values if item.name.lower() == "sqlalchemy"]
        for group, values in requirements.items()
        if group in ("project", "dev", "pycubrid")
    }
    if (
        any(len(specs) != 1 for specs in sqlalchemy_specs.values())
        or len({spec for specs in sqlalchemy_specs.values() for spec in specs}) != 1
    ):
        problems.append("pyproject.toml: project, dev and pycubrid SQLAlchemy bounds differ")
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

    driver_rows = _section(matrix, "Drivers")
    driver = re.search(r"^\| CUBRIDdb \(CCI\) \|([^\n]+)$", driver_rows, re.M)
    if driver is None:
        problems.append("docs/SUPPORT_MATRIX.md: CUBRIDdb driver row is missing")
    else:
        cells = [cell.strip() for cell in driver.group(0).strip("|").split("|")]
        if len(cells) != 4:
            problems.append("docs/SUPPORT_MATRIX.md: CUBRIDdb driver row is malformed")
        else:
            install, status = cells[1], cells[3]
            if not all(token in install for token in ("v11.3.0.51+", "[cubrid]", "[cubriddb]")):
                problems.append(
                    "docs/SUPPORT_MATRIX.md: CUBRIDdb source and extras need distinct install guidance"
                )
            if "deprecated" not in install.lower():
                problems.append(
                    "docs/SUPPORT_MATRIX.md: deprecated installation extras are not identified"
                )
            if "Supported" not in status or re.search(r"deprecated|legacy|obsolete", status, re.I):
                problems.append(
                    "docs/SUPPORT_MATRIX.md: supported CUBRIDdb driver is misclassified"
                )
    return problems


def main() -> int:
    problems = check_claims(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
        (ROOT / "README.md").read_text(encoding="utf-8"),
        (ROOT / "docs/SUPPORT_MATRIX.md").read_text(encoding="utf-8"),
    )
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    print("Current support claims match package metadata and driver policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
