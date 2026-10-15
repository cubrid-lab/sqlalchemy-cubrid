#!/usr/bin/env python3
"""Check the agent guidance: root ``AGENTS.md`` plus the guides in ``docs/agents/`` (#907).

Deterministic checks only, no network:

* the documentation checks of ``scripts/check_docs_links.py`` on these files:
  relative links and anchors, reference definitions, closed code fences,
  ``make`` goals and ``scripts/`` paths (#908);
* every guide under ``docs/agents/`` is linked from the root ``AGENTS.md``;
* a file that names a Python or CUBRID version links the support matrix or the
  CI policy, which own version lists, instead of carrying its own;
* a ``requires-python = "..."`` or ``sqlalchemy>=...`` pin quoted in the root
  file equals ``pyproject.toml``, which owns dependency bounds.

Links are read with a CommonMark parser (``scripts/_markdown.py``): links in
code are examples, and a reference definition counts only where it is used.

``--retained-from REF`` also checks that every non-blank line of ``AGENTS.md``
at git ``REF`` still appears in the agent guidance, with relative link targets
compared after resolving them to repository paths. Use it when moving rules
between these files: a moved rule must keep its text.

Usage: ``python scripts/check_agents_docs.py [--root DIR] [--retained-from REF]``
"""

from __future__ import annotations

import argparse
import posixpath
import re
import subprocess
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _markdown import Link, github_slug, is_external, parse  # noqa: E402
from check_docs_links import Checker  # noqa: E402

ROOT_DOC = "AGENTS.md"
GUIDE_DIR = "docs/agents"
VERSION_OWNERS = ("docs/SUPPORT_MATRIX.md", "docs/CI_POLICY.md")

# Inline link targets, for the text comparison of --retained-from only.
_LINK = re.compile(r"\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)")
_VERSION = re.compile(r"\b(?:Python\s+3\.\d+|CUBRID\s+1\d\.\d)")
_REQUIRES_PYTHON = re.compile(r"`requires-python\s*=\s*\"([^\"]+)\"`")
_SQLALCHEMY_PIN = re.compile(r"`sqlalchemy([<>=!~][^`]*)`")

slugify = github_slug


def agent_files(root: Path) -> list[Path]:
    """Return the root entry point and the guides, in a stable order."""
    files = [root / ROOT_DOC]
    files += sorted((root / GUIDE_DIR).glob("*.md"))
    return [path for path in files if path.is_file()]


def anchors(path: Path) -> set[str]:
    """Return the anchors a link into ``path`` may use."""
    return parse(path).anchors


def _linked_files(path: Path) -> set[Path]:
    """Return the local files that ``path`` links to with a followable link."""
    files = set()
    for link in parse(path).links:
        file_part = link.target.partition("#")[0]
        if file_part and not is_external(file_part):
            files.add((path.parent / file_part).resolve())
    return files


def check_reachable(root: Path) -> list[str]:
    """Report guides that the root entry point does not link."""
    entry = root / ROOT_DOC
    if not entry.is_file():
        return [f"{ROOT_DOC}: missing"]
    linked = _linked_files(entry)
    return [
        f"{guide.relative_to(root).as_posix()}: not linked from {ROOT_DOC}"
        for guide in sorted((root / GUIDE_DIR).glob("*.md"))
        if guide.resolve() not in linked
    ]


def check_versions(root: Path, path: Path) -> list[str]:
    """Require a file that names versions to link the documents that own them."""
    text = path.read_text(encoding="utf-8")
    found = _VERSION.search(text)
    if not found:
        return []
    owners = {(root / owner).resolve() for owner in VERSION_OWNERS}
    if _linked_files(path) & owners:
        return []
    number = text[: found.start()].count("\n") + 1
    return [
        f"{path.relative_to(root).as_posix()}:{number}: names {found.group(0)!r} but links "
        f"neither {' nor '.join(VERSION_OWNERS)}, which own version lists"
    ]


def check_pins(root: Path) -> list[str]:
    """Report root pins that disagree with ``pyproject.toml``."""
    entry, pyproject = root / ROOT_DOC, root / "pyproject.toml"
    if not entry.is_file() or not pyproject.is_file():
        return []
    project = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {})
    sqlalchemy = [
        re.sub(r"\s", "", dep)[len("sqlalchemy") :]
        for dep in project.get("dependencies", [])
        if re.match(r"sqlalchemy\s*[<>=!~]", dep, re.I)
    ]
    problems = []
    for number, line in enumerate(entry.read_text(encoding="utf-8").splitlines(), 1):
        for value in _REQUIRES_PYTHON.findall(line):
            if value != project.get("requires-python"):
                problems.append(
                    f"{ROOT_DOC}:{number}: requires-python {value!r} differs from "
                    f"pyproject.toml {project.get('requires-python')!r}"
                )
        for value in _SQLALCHEMY_PIN.findall(line):
            if re.sub(r"\s", "", value) not in sqlalchemy:
                problems.append(
                    f"{ROOT_DOC}:{number}: sqlalchemy{value} differs from pyproject.toml "
                    f"{', '.join('sqlalchemy' + pin for pin in sqlalchemy) or 'no pin'}"
                )
    return problems


def _normalized(root: Path, path: Path, line: str) -> str:
    """Return a line with collapsed spaces and repository-relative link targets."""

    def resolve(match: re.Match[str]) -> str:
        target = match.group(1)
        if is_external(target) or target.startswith("#"):
            return match.group(0)
        file_part, sep, anchor = target.partition("#")
        base = path.parent.relative_to(root).as_posix()
        joined = posixpath.normpath(posixpath.join(base, file_part)) if file_part else ""
        return match.group(0).replace(target, joined + sep + anchor)

    return " ".join(_LINK.sub(resolve, line).split())


def check_retained(root: Path, ref: str) -> list[str]:
    """Report lines of ``AGENTS.md`` at ``ref`` missing from the current guidance."""
    old = subprocess.run(
        ["git", "-C", str(root), "show", f"{ref}:{ROOT_DOC}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    current = set()
    for path in agent_files(root):
        for line in path.read_text(encoding="utf-8").splitlines():
            current.add(_normalized(root, path, line))
    missing = []
    for number, line in enumerate(old.splitlines(), 1):
        normalized = _normalized(root, root / ROOT_DOC, line)
        if normalized and normalized not in current:
            missing.append(f"{ref}:{ROOT_DOC}:{number}: not retained: {line.strip()[:100]}")
    return missing


def run(root: Path, retained_from: str | None = None) -> list[str]:
    """Return every problem found under ``root``."""
    root = root.resolve()
    checker = Checker(root)
    problems = check_reachable(root) + check_pins(root)
    for path in agent_files(root):
        problems += checker.check_file(path)
        problems += check_versions(root, path)
    if retained_from:
        problems += check_retained(root, retained_from)
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--retained-from", metavar="REF")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    problems = run(root, args.retained_from)
    if problems:
        print("Agent guidance problems:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    files = agent_files(root)
    print(f"OK: {len(files)} agent guidance files; links, guides and commands resolve")
    return 0


__all__ = [
    "Link",
    "anchors",
    "check_pins",
    "check_reachable",
    "check_versions",
    "main",
    "run",
    "slugify",
]

if __name__ == "__main__":
    sys.exit(main())
