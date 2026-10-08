"""Changed-path selection follows a per-workflow impact table (#746).

Only ``ci.yml`` itself selects the live PR lanes: it defines and runs them. Every
other workflow selects the tooling lane, and as a non-documentation change it also
runs the full offline suite, which covers the workflow-contract tests outside the
tooling lane. ``integration-full.yml`` and ``upstream-canary.yml`` changes are
validated by a manual dispatch on the PR head.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _filters() -> dict[str, list[str]]:
    steps = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())["jobs"][
        "detect-changes"
    ]["steps"]
    return yaml.safe_load(steps[-1]["with"]["filters"])


def _glob_re(pattern: str) -> re.Pattern[str]:
    """Translate a paths-filter (picomatch) glob into a regex for these tests."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        elif pattern[i] == "{":
            end = pattern.index("}", i)
            alts = [_glob_re(alt).pattern for alt in pattern[i + 1 : end].split(",")]
            out, i = out + "(?:" + "|".join(alts) + ")", end + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out)


def _selected(path: str) -> set[str]:
    groups = set()
    for group, patterns in _filters().items():
        for pattern in patterns:
            if pattern.startswith("!"):
                hit = not _glob_re(pattern[1:]).fullmatch(path)
            else:
                hit = bool(_glob_re(pattern).fullmatch(path))
            if hit:
                groups.add(group)
                break
    return groups


WORKFLOWS = sorted(p.name for p in (ROOT / ".github/workflows").glob("*.y*ml"))


@pytest.mark.parametrize("name", WORKFLOWS)
def test_workflow_impact_table(name: str) -> None:
    groups = _selected(f".github/workflows/{name}")
    # Every workflow is validated by the tooling lane and the full offline suite.
    assert {"code", "tooling"} <= groups, name
    if name == "ci.yml":
        assert "risk" in groups, "ci.yml defines and runs the live lanes"
    else:
        assert "risk" not in groups, f"{name} does not run in ci.yml's live lanes"


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("sqlalchemy_cubrid/compiler.py", {"code", "risk"}),
        ("sqlalchemy_cubrid/pycubrid_dialect.py", {"code", "risk"}),
        ("test/test_integration_basic.py", {"code", "risk"}),
        ("scripts/check_not_all_skipped.py", {"code", "risk", "tooling"}),
        ("pyproject.toml", {"code", "risk", "tooling"}),
        ("test/test_compiler.py", {"code"}),
        ("docs/CI_POLICY.md", {"docs"}),
        ("README.md", {"docs"}),
    ],
)
def test_representative_paths_select_the_expected_tiers(path: str, expected: set[str]) -> None:
    assert _selected(path) == expected, path


def test_tests_that_read_workflows_still_run_on_workflow_only_prs() -> None:
    # A workflow-only PR runs the full offline suite (not integration) and the
    # tooling lane, so a workflow-reading test must not be integration-marked.
    offenders = []
    for path in sorted((ROOT / "test").glob("test_*.py")):
        source = path.read_text()
        if ".github/workflows" not in source:
            continue
        tree = ast.parse(source)
        module_integration = any(
            isinstance(node, ast.Assign)
            and any(getattr(t, "id", "") == "pytestmark" for t in node.targets)
            and re.search(r"\bmark\.integration\b", ast.unparse(node.value))
            for node in tree.body
        )
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue
            if ".github/workflows" not in (ast.get_source_segment(source, node) or ""):
                continue
            marked = any(
                re.search(r"\bmark\.integration\b", ast.unparse(d)) for d in node.decorator_list
            )
            if module_integration or marked:
                offenders.append(f"{path.name}:{node.name}")
    assert not offenders, offenders
