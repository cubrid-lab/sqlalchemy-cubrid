"""Detect drift between the repository's deliberately pinned tooling surfaces."""

from __future__ import annotations

import configparser
import re
import shlex
from importlib import metadata
from pathlib import Path
from typing import Callable


def _unique(pattern: str, text: str, label: str) -> str:
    matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
    if len(matches) != 1:
        raise ValueError(f"{label}: expected one declaration, found {len(matches)}")
    return matches[0]


def declared_pins(root: Path) -> dict[str, str]:
    project = (root / "pyproject.toml").read_text()
    dev = _unique(r"^dev\s*=\s*\[\n(.*?)^\]", project, "dev dependencies")
    return {
        tool: _unique(rf'^\s*"{tool}==([^"\n]+)"\s*,?\s*$', dev, tool) for tool in ("ruff", "mypy")
    }


def check_environment(
    pins: dict[str, str],
    installed: Callable[[str], str] | None = None,
) -> list[str]:
    """Verify the active environment actually has what the local/system hooks
    will run. `language: system` hooks trust whatever `python3 -m <tool>`
    resolves to in the environment that invoked Git/pre-commit; unlike the
    former pinned mirror repos, nothing installs or refreshes the tool for
    you, so a checkout where `pyproject.toml` was bumped without reinstalling
    `.[dev]` would otherwise silently run a stale or missing tool version."""
    version = installed or metadata.version
    errors = []
    for tool, expected in pins.items():
        try:
            actual = version(tool)
        except metadata.PackageNotFoundError:
            errors.append(f"{tool}: not installed in the active environment; install .[dev]")
            continue
        if actual != expected:
            errors.append(
                f"{tool}: installed {actual}, expected {expected}; install .[dev] in the "
                "active environment"
            )
    return errors


def check(root: Path) -> list[str]:
    project = (root / "pyproject.toml").read_text()
    dev = _unique(r"^dev\s*=\s*\[\n(.*?)^\]", project, "dev dependencies")
    # Each tool must still declare exactly one exact dev pin (the single source
    # of truth); check_environment() verifies the active environment actually
    # matches it, since the local/system hooks and dev-extra-sourced tox envs
    # always run whatever is installed instead of a separately declared version.
    declared_pins(root)
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

    # Ruff and Mypy pre-commit hooks are `repo: local` / `language: system` hooks
    # that invoke `python3 -m <tool>` against the active `.[dev]` environment, so
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
                    f".[dev] environment, matching the pyproject {tool} pin"
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

    if "dev" not in _extras("testenv:lint"):
        errors.append(
            "tox lint must install the project's dev extra (extras = dev) so Ruff tracks "
            "the pyproject pin instead of a hardcoded tox version"
        )
    if tox.has_option("testenv:lint", "deps") and re.search(
        r"^\s*ruff==", tox.get("testenv:lint", "deps"), re.MULTILINE
    ):
        errors.append("tox lint must not hardcode a ruff version; the dev extra already pins it")
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
        expected = {f"sqlalchemy[asyncio]=={sa_version}"}
        deps = {
            line.strip().lower() for line in tox.get(section, "deps").splitlines() if line.strip()
        }
        if deps != expected:
            errors.append(f"{name} dependencies: expected " + ", ".join(sorted(expected)))
        if tox.get(section, "basepython") != f"python{python_version}":
            errors.append(f"{name}: expected Python {python_version}")
        if _extras(section) != {"alembic", "dev"}:
            errors.append(
                f"{name}: extras must be exactly alembic and dev (dev supplies the pinned Mypy)"
            )
        if tox.get(section, "commands").strip() != "make typecheck PYTHON={envpython}":
            errors.append(f"{name}: use the Makefile typecheck target")
    if re.search(r'"mypy==', typecheck):
        errors.append(
            "CI typecheck: must not hardcode a mypy version; install the dev extra instead"
        )
    if not re.search(r'"\.\[[^\]"]*\bdev\b[^\]"]*\]"', typecheck):
        errors.append(
            "CI typecheck: must install the project's dev extra (e.g. .[dev,alembic]) so "
            "mypy tracks the pyproject pin"
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
