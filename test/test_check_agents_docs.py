"""Agent guidance checks: root AGENTS.md and the docs/agents/ guides (#907)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "check_agents_docs", ROOT / "scripts/check_agents_docs.py"
)
assert _SPEC is not None and _SPEC.loader is not None
check = importlib.util.module_from_spec(_SPEC)
sys.modules["check_agents_docs"] = check
_SPEC.loader.exec_module(check)

ROOT_DOC = """# AGENTS.md

## Task Routing

| Task | Read |
|---|---|
| Dialect | [Dialect guide](docs/agents/dialect.md#cubrid-specific-knowledge) |

## Release Process

Run `make test` and `python scripts/tool.py`. Versions: [matrix](docs/SUPPORT_MATRIX.md).
"""

GUIDE = """# Dialect guide

> Moved from the root [AGENTS.md](../../AGENTS.md#release-process).

## CUBRID-Specific Knowledge

CUBRID 10.2 behavior; see the [support matrix](../SUPPORT_MATRIX.md).
"""

PYPROJECT = """[project]
requires-python = ">=3.11"
dependencies = ["sqlalchemy>=2.0,<2.2"]
"""


def _tree(tmp_path: Path, root_doc: str = ROOT_DOC, guide: str = GUIDE) -> Path:
    (tmp_path / "docs/agents").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "AGENTS.md").write_text(root_doc, encoding="utf-8")
    (tmp_path / "docs/agents/dialect.md").write_text(guide, encoding="utf-8")
    (tmp_path / "docs/SUPPORT_MATRIX.md").write_text("# Support\n", encoding="utf-8")
    (tmp_path / "scripts/tool.py").write_text("", encoding="utf-8")
    (tmp_path / "Makefile").write_text("test: ## Run tests\n\tpytest\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    return tmp_path


def test_repository_agent_guidance_is_valid() -> None:
    assert check.run(ROOT) == []


def test_valid_fixture_passes(tmp_path: Path) -> None:
    assert check.run(_tree(tmp_path)) == []


def test_broken_relative_link_reports_file_and_line(tmp_path: Path) -> None:
    root = _tree(tmp_path, ROOT_DOC + "\nSee [gone](docs/GONE.md).\n")
    assert check.run(root) == ["AGENTS.md:13: link target 'docs/GONE.md' does not exist"]


def test_missing_anchor_is_reported(tmp_path: Path) -> None:
    guide = GUIDE.replace("#release-process", "#release-processes")
    assert check.run(_tree(tmp_path, guide=guide)) == [
        "docs/agents/dialect.md:3: anchor #release-processes is not a heading or anchor of "
        + "AGENTS.md; did you mean 'release-process'?"
    ]


def test_titled_and_angle_bracket_links_are_checked(tmp_path: Path) -> None:
    titled = ROOT_DOC.replace(
        "(docs/agents/dialect.md#cubrid-specific-knowledge)",
        '(docs/agents/dialect.md#cubrid-specific-knowledge "Dialect")',
    )
    assert check.run(_tree(tmp_path, titled)) == []
    broken = titled + "\nSee [gone](docs/GONE.md 'title') and [x](<docs/agents/dialect.md#no>).\n"
    assert check.run(_tree(tmp_path / "broken", broken)) == [
        "AGENTS.md:13: anchor #no is not a heading or anchor of docs/agents/dialect.md",
        "AGENTS.md:13: link target 'docs/GONE.md' does not exist",
    ]


def test_reference_style_links_are_resolved(tmp_path: Path) -> None:
    valid = (
        ROOT_DOC.replace(
            "[Dialect guide](docs/agents/dialect.md#cubrid-specific-knowledge)",
            "[Dialect guide][dialect]",
        )
        + "\n[dialect]: docs/agents/dialect.md#cubrid-specific-knowledge\n"
    )
    assert check.run(_tree(tmp_path, valid)) == []
    broken = valid + "\nSee [the guide][gone] and [missing][].\n\n[gone]: docs/GONE.md\n"
    assert check.run(_tree(tmp_path / "broken", broken)) == [
        "AGENTS.md:15: link target 'docs/GONE.md' does not exist",
        "AGENTS.md:15: reference [missing] has no definition",
        "AGENTS.md:17: link target 'docs/GONE.md' does not exist",
    ]


def test_definition_without_a_use_is_not_a_link(tmp_path: Path) -> None:
    unused = (
        ROOT_DOC.replace(
            "[Dialect guide](docs/agents/dialect.md#cubrid-specific-knowledge)", "Dialect guide"
        )
        + "\n[dialect]: docs/agents/dialect.md\n"
    )
    assert check.run(_tree(tmp_path, unused)) == [
        "docs/agents/dialect.md: not linked from AGENTS.md"
    ]
    guide = (
        GUIDE.replace("see the [support matrix](../SUPPORT_MATRIX.md)", "see the support matrix")
        + "\n[matrix]: ../SUPPORT_MATRIX.md\n"
    )
    (problem,) = check.run(_tree(tmp_path / "owner", guide=guide))
    assert "names 'CUBRID 10.2' but links neither" in problem
    broken = ROOT_DOC + "\n[unused]: docs/GONE.md\n"
    assert check.run(_tree(tmp_path / "broken", broken)) == [
        "AGENTS.md:13: link target 'docs/GONE.md' does not exist"
    ]


@pytest.mark.parametrize(
    "block",
    [
        "~~~\n[x](docs/NOPE.md)\n~~~",
        "````md\n```\n[x](docs/NOPE.md)\n```\n````",
        "```\n```not-a-close\n[x](docs/NOPE.md)\n```",
    ],
)
def test_tilde_and_nested_fences_hide_their_content(tmp_path: Path, block: str) -> None:
    assert check.run(_tree(tmp_path, ROOT_DOC + "\n" + block + "\n")) == []


def test_commands_in_tilde_fences_are_checked(tmp_path: Path) -> None:
    root_doc = ROOT_DOC + "\n~~~bash\nmake tset\n~~~\n"
    assert check.run(_tree(tmp_path, root_doc)) == [
        "AGENTS.md:14: `make tset` is not a Makefile target; did you mean 'test'?"
    ]


def test_external_links_and_code_are_not_checked(tmp_path: Path) -> None:
    extra = (
        "\n[site](https://example.invalid/x) and `[x](docs/NOPE.md)`\n\n```\n[y](nope.md)\n```\n"
    )
    assert check.run(_tree(tmp_path, ROOT_DOC + extra)) == []


def test_guide_not_linked_from_root_is_reported(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "docs/agents/release.md").write_text("# Release guide\n", encoding="utf-8")
    assert check.run(root) == ["docs/agents/release.md: not linked from AGENTS.md"]


@pytest.mark.parametrize(
    ("cell", "after"),
    [
        ("`[Dialect guide](docs/agents/dialect.md)`", ""),
        ("Dialect guide", "\n```\n[Dialect guide](docs/agents/dialect.md)\n```\n"),
    ],
)
def test_guide_named_only_in_code_is_not_reachable(tmp_path: Path, cell: str, after: str) -> None:
    root_doc = (
        ROOT_DOC.replace("[Dialect guide](docs/agents/dialect.md#cubrid-specific-knowledge)", cell)
        + after
    )
    assert check.run(_tree(tmp_path, root_doc)) == [
        "docs/agents/dialect.md: not linked from AGENTS.md"
    ]


def test_invalid_commands_are_reported_but_prose_is_not(tmp_path: Path) -> None:
    extra = (
        "\nBefore editing, make sure the server is available; make good use of it.\n"
        "\n```bash\nmake tset\npython scripts/missing.py\n```\n\nRun `make lnit` first.\n"
    )
    assert check.run(_tree(tmp_path, ROOT_DOC + extra)) == [
        "AGENTS.md:16: `make tset` is not a Makefile target; did you mean 'test'?",
        "AGENTS.md:17: scripts/missing.py does not exist",
        "AGENTS.md:20: `make lnit` is not a Makefile target",
    ]


def test_version_without_an_owning_document_link_is_reported(tmp_path: Path) -> None:
    guide = GUIDE.replace("; see the [support matrix](../SUPPORT_MATRIX.md)", "")
    (problem,) = check.run(_tree(tmp_path, guide=guide))
    assert problem.startswith("docs/agents/dialect.md:7: names 'CUBRID 10.2' but links neither")


@pytest.mark.parametrize(
    "owner",
    [
        "`[support matrix](../SUPPORT_MATRIX.md)`",
        "\n```\n[support matrix](../SUPPORT_MATRIX.md)\n```\n",
    ],
)
def test_version_owner_link_in_code_does_not_count(tmp_path: Path, owner: str) -> None:
    # The fence closes on its own line; "```." would leave it open (CommonMark).
    guide = GUIDE.replace("; see the [support matrix](../SUPPORT_MATRIX.md).", owner)
    (problem,) = check.run(_tree(tmp_path, guide=guide))
    assert "names 'CUBRID 10.2' but links neither" in problem


def test_multi_backtick_code_spans_are_code(tmp_path: Path) -> None:
    root_doc = (
        ROOT_DOC.replace(
            "[Dialect guide](docs/agents/dialect.md#cubrid-specific-knowledge)",
            "``[Dialect guide](docs/agents/dialect.md)``",
        )
        + "\nAn example: ``[x](docs/NOPE.md) with a ` backtick``.\n"
    )
    assert check.run(_tree(tmp_path, root_doc)) == [
        "docs/agents/dialect.md: not linked from AGENTS.md"
    ]


def test_every_goal_of_a_make_command_is_checked(tmp_path: Path) -> None:
    extra = "\nRun `make test tset`, `make -j2 lint` and `make -C . tset VAR=1`.\n"
    assert check.run(_tree(tmp_path, ROOT_DOC + extra)) == [
        "AGENTS.md:13: `make lint` is not a Makefile target",
        "AGENTS.md:13: `make tset` is not a Makefile target; did you mean 'test'?",
    ]


def test_pins_must_match_pyproject(tmp_path: Path) -> None:
    pins = '\n- `requires-python = ">=3.11"`, `sqlalchemy>=2.0,<2.2`\n'
    assert check.run(_tree(tmp_path, ROOT_DOC + pins)) == []
    stale = '\n- `requires-python = ">=3.10"`, `sqlalchemy>=2.0,<2.1`\n'
    assert check.run(_tree(tmp_path / "stale", ROOT_DOC + stale)) == [
        "AGENTS.md:13: requires-python '>=3.10' differs from pyproject.toml '>=3.11'",
        "AGENTS.md:13: sqlalchemy>=2.0,<2.1 differs from pyproject.toml sqlalchemy>=2.0,<2.2",
    ]


def test_duplicate_heading_anchors_follow_github_and_the_site(tmp_path: Path) -> None:
    path = tmp_path / "x.md"
    path.write_text(
        "# A\n## Same\n## Same\n## Same-1\n```\n## Not a heading\n```\n", encoding="utf-8"
    )
    # GitHub skips a suffix another heading took (same-1-1); the site uses _1.
    assert check.anchors(path) == {"a", "same", "same-1", "same-1-1", "same_1"}
    assert check.slugify("Development Workflow (cubrid-lab org standard)") == (
        "development-workflow-cubrid-lab-org-standard"
    )


def _git_tree(tmp_path: Path) -> Path:
    root = _tree(tmp_path)
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "base"],
    ):
        subprocess.run(["git", "-C", str(root), *args], check=True)
    return root


def test_moved_rule_with_rebased_link_is_retained(tmp_path: Path) -> None:
    root = _git_tree(tmp_path)
    moved = "Run `make test` and `python scripts/tool.py`. "
    moved += "Versions: [matrix](docs/SUPPORT_MATRIX.md)."
    (root / "AGENTS.md").write_text(ROOT_DOC.replace(moved, "Run.\n"), encoding="utf-8")
    (root / "docs/agents/dialect.md").write_text(
        GUIDE + "\nRun `make test` and `python scripts/tool.py`. "
        "Versions: [matrix](../SUPPORT_MATRIX.md).\n",
        encoding="utf-8",
    )
    assert check.run(root, "HEAD") == []


def test_dropped_rule_is_reported(tmp_path: Path) -> None:
    root = _git_tree(tmp_path)
    (root / "AGENTS.md").write_text(
        ROOT_DOC.replace("Run `make test` and", "Run"), encoding="utf-8"
    )
    (problem,) = check.run(root, "HEAD")
    assert problem.startswith("HEAD:AGENTS.md:11: not retained: Run `make test` and")


def test_cli_exit_status(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert check.main(["--root", str(_tree(tmp_path))]) == 0
    assert "OK: 2 agent guidance files" in capsys.readouterr().out
    root = tmp_path / "bad"
    root.mkdir()
    _tree(root, ROOT_DOC.replace("dialect.md#", "dialect2.md#"))
    assert check.main(["--root", str(root)]) == 1
    assert "does not exist" in capsys.readouterr().out
