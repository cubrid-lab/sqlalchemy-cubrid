"""Detect drift between the repository's deliberately pinned tooling surfaces."""

from __future__ import annotations

import configparser
import re
import shlex
from pathlib import Path


def _unique(pattern: str, text: str, label: str) -> str:
    matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
    if len(matches) != 1:
        raise ValueError(f"{label}: expected one declaration, found {len(matches)}")
    return matches[0]


def check(root: Path) -> list[str]:
    project = (root / "pyproject.toml").read_text()
    dev = _unique(r"^dev\s*=\s*\[\n(.*?)^\]", project, "dev dependencies")
    pins = {
        tool: _unique(rf'^\s*"{tool}==([^"\n]+)"\s*,?\s*$', dev, tool) for tool in ("ruff", "mypy")
    }
    alembic = _unique(r'^\s*"(alembic[^"\n]+)"\s*,?\s*$', dev, "Alembic requirement")
    alembic_extra = _unique(r"^alembic\s*=\s*\[\n(.*?)^\]", project, "Alembic extra")
    hooks = (root / ".pre-commit-config.yaml").read_text()
    workflow = (root / ".github/workflows/ci.yml").read_text()
    typecheck = _unique(r"^  typecheck:\n(.*?)(?=^  [\w-]+:|\Z)", workflow, "CI typecheck job")
    cells = re.findall(
        r'python-version:\s*"([\d.]+)"\s*\n\s*sqlalchemy-version:\s*"([\d.]+)"',
        typecheck,
    )
    if not cells:
        raise ValueError("CI typecheck matrix: no pinned Python/SQLAlchemy pairs found")
    tox = configparser.ConfigParser(interpolation=None)
    tox.read(root / "tox.ini")
    makefile = (root / "Makefile").read_text()
    errors: list[str] = []
    source = _unique(r"^SRC\s*=\s*([^\n]+)", makefile, "Makefile source directory")
    tests = _unique(r"^TESTS\s*=\s*([^\n]+)", makefile, "Makefile test directory")
    lint_paths = _unique(r"^LINT_PATHS\s*=\s*([^\n]+)", makefile, "Makefile Ruff scope")
    paths = set(lint_paths.replace("$(SRC)", source).replace("$(TESTS)", tests).split())
    if not {source, tests, "scripts", "demos", "samples", "docs/source"} <= paths:
        errors.append("Makefile Ruff scope must include all maintained Python source directories")
    lint_job = _unique(r"^  lint:\n(.*?)(?=^  [\w-]+:|\Z)", workflow, "CI lint job")
    if not re.search(r"^\s*run: make lint\s*$", lint_job, re.MULTILINE):
        errors.append("CI lint must call the shared Makefile lint target")
    if tox.get("testenv:lint", "commands").strip() != "make lint PYTHON={envpython}":
        errors.append("tox lint must call the shared Makefile lint target")
    if "--ignore=test/test_suite.py" not in shlex.split(tox.get("testenv:integration", "commands")):
        errors.append(
            "tox integration must exclude the formal suite that requires explicit --dburi"
        )
    if tox.get("testenv:integration", "commands").strip().splitlines()[0].strip() != (
        "python -m scripts.check_integration_connection"
    ):
        errors.append("tox integration must run its pure-driver connection preflight first")
    ruff = _unique(r"^\[tool.ruff\]\n(.*?)(?=^\[|\Z)", project, "Ruff configuration")
    included = _unique(r"^include\s*=\s*\[([^\n]+)\]", ruff, "Ruff file scope")
    if re.findall(r'"([^"\n]+)"', included) != ["*.py", "*.pyi"]:
        errors.append("Ruff CLI file scope must be Python/pyi, matching the source hooks")
    if _unique(r'^\s*"([^"\n]+)"\s*,?\s*$', alembic_extra, "Alembic extra requirement") != alembic:
        errors.append("Alembic dev requirement and existing install extra must agree")
    for tool, repo in (
        ("ruff", "https://github.com/astral-sh/ruff-pre-commit"),
        ("mypy", "https://github.com/pre-commit/mirrors-mypy"),
    ):
        block = _unique(
            rf"^\s*- repo: {re.escape(repo)}\n(.*?)(?=^\s*- repo:|\Z)", hooks, f"{tool} hook"
        )
        revision = _unique(r"^\s*rev:\s*([^\s#]+)", block, f"{tool} hook revision")
        if revision.removeprefix("v") != pins[tool]:
            errors.append(f"{tool} hook revision: expected {pins[tool]}, found {revision}")
        if tool == "ruff":
            scopes = re.findall(r"^\s*types_or:\s*\[([^\n]+)\]", block, re.MULTILINE)
            if len(scopes) != 2 or any(
                {item.strip() for item in scope.split(",")} != {"python", "pyi"} for scope in scopes
            ):
                errors.append("Both Ruff hooks must use the same Python/pyi scope as the CLI")
        if tool == "mypy":
            sa_pins = {".".join(sa.split(".")[:2]): sa for _, sa in cells}
            if "2.0" not in sa_pins or "2.1" not in sa_pins:
                raise ValueError(
                    "Mypy hook markers require CI's designated SQLAlchemy 2.0/2.1 pins"
                )
            dependencies = (
                f"sqlalchemy[asyncio]=={sa_pins['2.0']}; python_version < '3.11'",
                f"sqlalchemy[asyncio]=={sa_pins['2.1']}; python_version >= '3.11'",
                alembic,
            )
            for dependency in dependencies:
                if not re.search(
                    rf"^\s*- [\"']?{re.escape(dependency)}[\"']?\s*$", block, re.MULTILINE | re.I
                ):
                    errors.append(f"mypy hook dependencies: missing {dependency}")
            args = _unique(r"^\s*args:\s*\[(.*?)\]", block, "mypy hook arguments")
            if not re.search(r"""["']sqlalchemy_cubrid/["']""", args) or not re.search(
                r"""["']--config-file=pyproject.toml["']""", args
            ):
                errors.append("mypy hook: explicit package target and project config are required")
            if "--install-types" in block or "--ignore-missing-imports" in block:
                errors.append(
                    "mypy hook: automatic stub installation/import suppression is disallowed"
                )
    if tox.get("testenv:lint", "deps").strip() != f"ruff=={pins['ruff']}":
        errors.append(f"tox lint dependencies: expected ruff=={pins['ruff']}")
    declared = {"py" + v.replace(".", "") for v in re.findall(r"Python :: (3\.\d+)", project)}
    envs = {env.strip() for env in tox.get("tox", "envlist").replace("\n", "").split(",")}
    if not declared <= envs:
        errors.append("tox envlist: missing " + ", ".join(sorted(declared - envs)))
    for python_version, sa_version in cells:
        suffix = "".join(sa_version.split(".")[:2])
        name = f"typecheck-sa{suffix}"
        section = f"testenv:{name}"
        if not tox.has_section(section):
            errors.append(f"tox: missing {name}")
            continue
        expected = {f"mypy=={pins['mypy']}", f"sqlalchemy[asyncio]=={sa_version}"}
        deps = {
            line.strip().lower() for line in tox.get(section, "deps").splitlines() if line.strip()
        }
        if deps != expected:
            errors.append(f"{name} dependencies: expected " + ", ".join(sorted(expected)))
        if tox.get(section, "basepython") != f"python{python_version}":
            errors.append(f"{name}: expected Python {python_version}")
        if tox.get(section, "extras") != "alembic":
            errors.append(f"{name}: use the project's existing Alembic extra")
        if tox.get(section, "commands").strip() != "make typecheck PYTHON={envpython}":
            errors.append(f"{name}: use the Makefile typecheck target")
    ci_mypy = re.findall(r"mypy==([\d.]+)", typecheck)
    if ci_mypy != [pins["mypy"]]:
        errors.append(f"CI typecheck: expected mypy=={pins['mypy']}")
    return errors


def main() -> int:
    try:
        errors = check(Path(__file__).resolve().parent.parent)
    except (ValueError, configparser.Error) as exc:
        errors = [str(exc)]
    if errors:
        print("Tooling drift detected:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Tooling pins, hook dependencies and tox type-check cells are synchronized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
