"""Changed-path selection follows a per-workflow impact table (#746).

Only ``ci.yml`` itself selects the live PR lanes: it defines and runs them. Every
other workflow selects the tooling lane, and as a non-documentation change it also
runs the full offline suite, which covers the workflow-contract tests outside the
tooling lane. ``integration-full.yml`` and ``upstream-canary.yml`` changes are
validated by a manual dispatch on the PR head.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _filters() -> dict[str, list[str]]:
    steps = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())["jobs"][
        "detect-changes"
    ]["steps"]
    step = next(s for s in steps if s.get("id") == "filter")
    return yaml.safe_load(step["with"]["filters"])


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
        ("THIRD_PARTY_LICENSES.md", {"docs", "tooling"}),
        ("test/test_third_party_licenses.py", {"code", "tooling"}),
    ],
)
def test_representative_paths_select_the_expected_tiers(path: str, expected: set[str]) -> None:
    assert _selected(path) == expected, path


WORKFLOW_REF = re.compile(r"\.github['\"]?\s*[/,]\s*['\"]?workflows")
INTEGRATION_MARK = re.compile(r"\bmark\.integration\b")


def _workflow_modules_with_integration_marks(test_dir: Path) -> list[str]:
    # Module-level on purpose: workflow paths usually live in a module constant or
    # helper (``ROOT / ".github" / "workflows"``), not in the test function body.
    return sorted(
        path.name
        for path in test_dir.glob("test_*.py")
        if WORKFLOW_REF.search(source := path.read_text()) and INTEGRATION_MARK.search(source)
    )


def test_tests_that_read_workflows_still_run_on_workflow_only_prs() -> None:
    # A workflow-only PR runs the full offline suite (not integration) and the
    # tooling lane, so no module that reads a workflow may carry integration tests.
    found = _workflow_modules_with_integration_marks(ROOT / "test")
    # This module's own probe strings contain both patterns by design.
    assert [name for name in found if name != Path(__file__).name] == []


@pytest.mark.parametrize(
    "body",
    [
        'P = ROOT / ".github" / "workflows" / "ci.yml"\n\n@pytest.mark.integration\ndef test_x(): ...',
        'W = ".github/workflows/ci.yml"\n\nclass TestX:\n    @pytest.mark.integration\n    def test_x(self): ...',
        'W = ".github/workflows/x.yml"\npytestmark = [pytest.mark.integration]\n\nasync def test_x(): ...',
    ],
    ids=["split-path-constant", "class-method", "module-mark-async"],
)
def test_guard_catches_indirect_workflow_readers(tmp_path: Path, body: str) -> None:
    (tmp_path / "test_probe.py").write_text("import pytest\n" + body + "\n")
    assert _workflow_modules_with_integration_marks(tmp_path) == ["test_probe.py"]
