"""Detect drift between the repository's deliberately pinned tooling surfaces."""

from __future__ import annotations

import configparser
import re
import shlex
import tomllib
from collections.abc import Mapping
from importlib import metadata
from pathlib import Path
from typing import Callable


def _unique(pattern: str, text: str, label: str) -> str:
    matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
    if len(matches) != 1:
        raise ValueError(f"{label}: expected one declaration, found {len(matches)}")
    return matches[0]


# Contributor tooling lives in PEP 735 dependency groups (#765), not in a
# published extra. Each pinned tool belongs to exactly one purpose group.
PIN_GROUPS = {"ruff": "lint", "mypy": "typecheck"}


def _project(root: Path) -> dict[str, object]:
    with (root / "pyproject.toml").open("rb") as source:
        return tomllib.load(source)


def _table(source: Mapping[str, object], key: str, label: str) -> dict[str, object]:
    value = source.get(key)
    if value is None:
        raise ValueError(f"{label}: expected one declaration, found 0")
    if not isinstance(value, dict):
        raise ValueError(f"{label}: expected a TOML table")
    return value


def _strings(source: Mapping[str, object], key: str, label: str) -> list[str]:
    value = source.get(key)
    if value is None:
        raise ValueError(f"{label}: expected one declaration, found 0")
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{label}: expected a list of strings")
    return value


def _one(values: list[str], label: str) -> str:
    if len(values) != 1:
        raise ValueError(f"{label}: expected one declaration, found {len(values)}")
    return values[0]


def _group(project: Mapping[str, object], name: str) -> list[str]:
    groups = _table(project, "dependency-groups", "dependency groups")
    label = f"{name} dependency group"
    values = groups.get(name)
    if values is None:
        raise ValueError(f"{label}: expected one declaration, found 0")
    if not isinstance(values, list):
        raise ValueError(f"{label}: expected a list of strings")
    requirements = []
    for value in values:
        if isinstance(value, str):
            requirements.append(value)
        elif not (
            isinstance(value, dict)
            and set(value) == {"include-group"}
            and isinstance(value["include-group"], str)
        ):
            raise ValueError(f"{label}: expected requirements or include-group entries")
    return requirements


def _requirement_name(requirement: str) -> str:
    for index, char in enumerate(requirement):
        if char in "[<>=!~; \t":
            return requirement[:index]
    return requirement


def _exact_pin(requirement: str, tool: str) -> str | None:
    name, separator, version = requirement.partition("==")
    name = name.strip()
    version = version.strip()
    if (
        not separator
        or not version
        or any(char.isspace() or char in "<>=~;*#@," for char in version)
    ):
        return None
    if name != tool:
        prefix = f"{tool}["
        if not name.startswith(prefix) or not name.endswith("]"):
            return None
        extras = name[len(prefix) : -1]
        if not extras or "[" in extras or "]" in extras:
            return None
    return version


def _declared_pins(project: Mapping[str, object]) -> dict[str, str]:
    pins = {}
    for tool, group in PIN_GROUPS.items():
        requirements = [
            requirement
            for requirement in _group(project, group)
            if _requirement_name(requirement) == tool
        ]
        version = _exact_pin(_one(requirements, tool), tool)
        if version is None:
            raise ValueError(f"{tool}: expected one declaration, found 0")
        pins[tool] = version
    return pins


def declared_pins(root: Path) -> dict[str, str]:
    return _declared_pins(_project(root))


def check_environment(
    pins: dict[str, str],
    installed: Callable[[str], str] | None = None,
) -> list[str]:
    """Verify the active environment actually has what the local/system hooks
    will run. `language: system` hooks trust whatever `python3 -m <tool>`
    resolves to in the environment that invoked Git/pre-commit; unlike the
    former pinned mirror repos, nothing installs or refreshes the tool for
    you, so a checkout where `pyproject.toml` was bumped without reinstalling
    the dev dependency group would otherwise silently run a stale or missing
    tool version."""
    version = installed or metadata.version
    errors = []
    for tool, expected in pins.items():
        try:
            actual = version(tool)
        except metadata.PackageNotFoundError:
            errors.append(
                f"{tool}: not installed in the active environment; install the dev "
                "dependency group (make install)"
            )
            continue
        if actual != expected:
            errors.append(
                f"{tool}: installed {actual}, expected {expected}; install the dev "
                "dependency group (make install) in the active environment"
            )
    return errors


def check(root: Path) -> list[str]:
    project = _project(root)
    # Each tool must still declare exactly one exact group pin (the single source
    # of truth); check_environment() verifies the active environment actually
    # matches it, since the local/system hooks and group-sourced tox envs always
    # run whatever is installed instead of a separately declared version.
    _declared_pins(project)
    project_metadata = _table(project, "project", "project metadata")
    extras = _table(project_metadata, "optional-dependencies", "published extras")
    test_group = _group(project, "test")
    alembic = _one(
        [requirement for requirement in test_group if _requirement_name(requirement) == "alembic"],
        "Alembic requirement",
    )
    if not any(char in alembic for char in "<>=!~"):
        raise ValueError("Alembic requirement: expected one declaration, found 0")
    alembic_extra = _strings(extras, "alembic", "Alembic extra")
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
    if "dev" in extras:
        errors.append(
            "pyproject.toml: the dev tooling belongs in [dependency-groups], not an extra"
        )
    source = _unique(r"^SRC\s*=\s*([^\n]+)", makefile, "Makefile source directory")
    tests = _unique(r"^TESTS\s*=\s*([^\n]+)", makefile, "Makefile test directory")
    lint_paths = _unique(r"^LINT_PATHS\s*=\s*([^\n]+)", makefile, "Makefile Ruff scope")
    paths = set(lint_paths.replace("$(SRC)", source).replace("$(TESTS)", tests).split())
    if not {source, tests, "scripts", "demos", "samples", "docs/source"} <= paths:
        errors.append("Makefile Ruff scope must include all maintained Python source directories")
    lint_job = _unique(r"^  lint:\n(.*?)(?=^  [\w-]+:|\Z)", workflow, "CI lint job")
    if not re.search(r"^\s*run: make lint\s*$", lint_job, re.MULTILINE):
        errors.append("CI lint must call the shared Makefile lint target")
    # `make lint` is `ruff check` only; formatting is the separate format-check (#1009).
    if not re.search(r"^\s*run: make format-check\s*$", lint_job, re.MULTILINE):
        errors.append("CI lint must call the shared Makefile format-check target")
    if tox.get("testenv:lint", "commands").strip() != "make lint format-check PYTHON={envpython}":
        errors.append("tox lint must call the shared Makefile lint and format-check targets")
    if "--ignore=test/test_suite.py" not in shlex.split(tox.get("testenv:integration", "commands")):
        errors.append(
            "tox integration must exclude the formal suite that requires explicit --dburi"
        )
    if tox.get("testenv:integration", "commands").strip().splitlines()[0].strip() != (
        "python -m scripts.check_integration_connection"
    ):
        errors.append("tox integration must run its pure-driver connection preflight first")
    ruff = _table(_table(project, "tool", "tool configuration"), "ruff", "Ruff configuration")
    included = _strings(ruff, "include", "Ruff file scope")
    if included != ["*.py", "*.pyi"]:
        errors.append("Ruff CLI file scope must be Python/pyi, matching the source hooks")
    if _one(alembic_extra, "Alembic extra requirement") != alembic:
        errors.append("Alembic test-group requirement and the alembic extra must agree")

    # Ruff and Mypy pre-commit hooks are `repo: local` / `language: system` hooks
    # that invoke `python3 -m <tool>` against the active dev-group environment, so
    # there is no separate hook revision to keep in sync with the pyproject pin
    # (that's what previously broke Dependabot's routine pip-ecosystem bumps).
    local_block = _unique(
        r"^  - repo: local\s*\n(.*?)(?=^  - repo:|\Z)", hooks, "local hook repository"
    )
    hook_pairs = re.findall(
        r"^      - id: (\S+)\n(.*?)(?=^      - id:|\Z)", local_block, re.MULTILINE | re.DOTALL
    )
    hook_ids = [hook_id for hook_id, _ in hook_pairs]
    duplicates = {hook_id for hook_id in hook_ids if hook_ids.count(hook_id) > 1}
    if duplicates:
        raise ValueError(f"duplicate local hook id(s): {sorted(duplicates)}")
    hook_blocks = dict(hook_pairs)
    # Exact required `entry:` per hook id. Local hook ids carry no inherent
    # behavior (unlike a pinned remote hook manifest), so the full command --
    # not just the `python3 -m <tool>` prefix -- must be pinned, or a hook
    # could drift to the wrong Ruff subcommand while still reporting success.
    expected_entry = {
        "ruff-format": "python3 -m ruff format",
        "ruff": "python3 -m ruff check --fix",
        "mypy": "python3 -m mypy",
    }
    for tool, hook_ids_for_tool in (("ruff", ("ruff", "ruff-format")), ("mypy", ("mypy",))):
        for hook_id in hook_ids_for_tool:
            if hook_id not in hook_blocks:
                errors.append(f"{hook_id}: local hook is required")
                continue
            body = hook_blocks[hook_id]
            if not re.search(r"^        language: system\s*$", body, re.MULTILINE):
                errors.append(
                    f"{hook_id}: hook must run via language: system against the active "
                    f"dev-group environment, matching the pyproject {tool} pin"
                )
            entry = expected_entry[hook_id]
            if not re.search(rf"^        entry: {re.escape(entry)}\s*$", body, re.MULTILINE):
                errors.append(
                    f"{hook_id}: hook entry must be exactly `{entry}` so it always runs the "
                    f"pyproject-pinned, actively-installed {tool} (no silently-different "
                    "subcommand)"
                )
    if "ruff" in hook_blocks and "ruff-format" in hook_blocks:
        scopes = [
            re.findall(r"^        types_or:\s*\[([^\n]+)\]", hook_blocks[hook_id], re.MULTILINE)
            for hook_id in ("ruff", "ruff-format")
        ]
        if any(len(scope) != 1 for scope in scopes) or any(
            {item.strip() for item in scope[0].split(",")} != {"python", "pyi"} for scope in scopes
        ):
            errors.append("Both Ruff hooks must use the same Python/pyi scope as the CLI")
        for hook_id in ("ruff", "ruff-format"):
            if re.search(r"^        args:", hook_blocks[hook_id], re.MULTILINE):
                errors.append(
                    f"{hook_id}: Ruff hook must not add args (pre-commit appends them to "
                    "entry, e.g. `--check` on ruff-format silently disables formatting); the "
                    "full command already lives in entry"
                )
    if "mypy" in hook_blocks:
        body = hook_blocks["mypy"]
        args = _unique(r"^\s*args:\s*\[(.*?)\]", body, "mypy hook arguments")
        if not re.search(r"""["']sqlalchemy_cubrid/["']""", args) or not re.search(
            r"""["']--config-file=pyproject.toml["']""", args
        ):
            errors.append("mypy hook: explicit package target and project config are required")
        if "--install-types" in body or "--ignore-missing-imports" in body:
            errors.append("mypy hook: automatic stub installation/import suppression is disallowed")

    def _extras(section: str) -> set[str]:
        if not tox.has_option(section, "extras"):
            return set()
        return {line.strip() for line in tox.get(section, "extras").splitlines() if line.strip()}

    def _groups(section: str) -> set[str]:
        if not tox.has_option(section, "dependency_groups"):
            return set()
        return set(tox.get(section, "dependency_groups").split())

    if not {"lint", "typecheck"} <= _groups("testenv:lint"):
        errors.append(
            "tox lint must install the lint and typecheck dependency groups "
            "(dependency_groups = lint typecheck) so Ruff and Mypy track the pyproject pins "
            "instead of a hardcoded tox version"
        )
    if tox.has_option("testenv:lint", "deps") and re.search(
        r"^\s*ruff==", tox.get("testenv:lint", "deps"), re.MULTILINE
    ):
        errors.append("tox lint must not hardcode a ruff version; the lint group already pins it")
    if _groups("testenv") != {"test", "lint", "typecheck"} or (
        tox.has_option("testenv", "deps") and tox.get("testenv", "deps").strip()
    ):
        errors.append(
            "tox testenv must install the test, lint and typecheck dependency groups "
            "instead of repeating their requirements in deps"
        )
    python_classifier = "Programming Language :: Python :: "
    declared = {
        "py" + version.replace(".", "")
        for classifier in _strings(project_metadata, "classifiers", "Python classifiers")
        if classifier.startswith(python_classifier)
        and (version := classifier.removeprefix(python_classifier)).startswith("3.")
        and version[2:].isdigit()
    }
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
        expected = {f"sqlalchemy[asyncio]=={sa_version}"}
        deps = {
            line.strip().lower() for line in tox.get(section, "deps").splitlines() if line.strip()
        }
        if deps != expected:
            errors.append(f"{name} dependencies: expected " + ", ".join(sorted(expected)))
        if tox.get(section, "basepython") != f"python{python_version}":
            errors.append(f"{name}: expected Python {python_version}")
        if _extras(section) != {"alembic"} or _groups(section) != {"typecheck"}:
            errors.append(
                f"{name}: install exactly the alembic extra and the typecheck dependency "
                "group (the group supplies the pinned Mypy)"
            )
        if tox.get(section, "commands").strip() != "make typecheck PYTHON={envpython}":
            errors.append(f"{name}: use the Makefile typecheck target")
    if re.search(r'"mypy==', typecheck):
        errors.append(
            "CI typecheck: must not hardcode a mypy version; install the typecheck group instead"
        )
    if not re.search(r"--group typecheck\b", typecheck):
        errors.append(
            "CI typecheck: must install the project's typecheck dependency group "
            "(--group typecheck) so mypy tracks the pyproject pin"
        )
    return errors


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    try:
        errors = check(root)
        errors += check_environment(declared_pins(root))
    except (ValueError, configparser.Error, metadata.PackageNotFoundError) as exc:
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
