#!/usr/bin/env python3
"""Fail on deterministic defects in the repository's Markdown files (#908; shared with pycubrid #927).

Checks every tracked ``*.md`` file, offline and without network access:

* a relative link or image target that does not exist, or that leaves the
  repository;
* an ``#anchor`` that is not a heading (GitHub slug, ``{#id}``) or an
  ``<a id>``/``<a name>`` of the target Markdown file;
* a full reference link ``[text][label]`` without a definition;
* a fenced code block that is never closed;
* a ``make`` goal, written as a command in inline code or a fenced block, that
  the Makefile does not define, and a ``scripts/...`` path that does not exist.
  Release history (``CHANGELOG.md``, ``RELEASE_CHANGELOG.md``) records commands
  and scripts as they were, so only its links are checked.

External links (any URI scheme) are never fetched: the shared doc-lint
workflow checks them, advisory. Style is not checked here either.

Suppress a reviewed false positive with ``<!-- docs-check: ignore -->`` on the
reported line or on the line before it. Each finding prints
``file:line: problem`` and, when one is close, a suggested replacement.

Usage: ``python scripts/check_docs_links.py [--root DIR] [FILE ...]``
"""

from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _markdown import Parsed, is_external, make_goals, parse  # noqa: E402

IGNORE = "<!-- docs-check: ignore -->"
# Dated release notes describe commands and scripts of their time; never rewrite them.
HISTORY = frozenset({"CHANGELOG.md", "RELEASE_CHANGELOG.md"})
_SCRIPT = re.compile(r"(?<![\w/.-])scripts/[A-Za-z0-9_./-]+\.(?:py|cjs|sh)\b")
_MAKE_TARGET = re.compile(r"^([a-zA-Z0-9_.-]+)\s*:(?!=)", re.M)


def markdown_files(root: Path) -> list[Path]:
    """Return the tracked Markdown files, or every ``*.md`` outside git."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--", "*.md"],
            capture_output=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return sorted(p for p in root.rglob("*.md") if ".venv" not in p.parts)
    return sorted(root / name for name in out.decode().split("\0") if name)


def _suppressed(lines: list[str], number: int) -> bool:
    return any(
        IGNORE in lines[index] for index in (number - 1, number - 2) if 0 <= index < len(lines)
    )


def _suggest(choice: str, options: list[str], cutoff: float = 0.75) -> str:
    close = difflib.get_close_matches(choice, options, n=1, cutoff=cutoff)
    return f"; did you mean {close[0]!r}?" if close else ""


class Checker:
    """Check Markdown files of one repository, caching parses."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self._parsed: dict[Path, Parsed] = {}
        makefile = self.root / "Makefile"
        self.make_targets = (
            set(_MAKE_TARGET.findall(makefile.read_text(encoding="utf-8")))
            if makefile.is_file()
            else set()
        )

    def parsed(self, path: Path) -> Parsed:
        path = path.resolve()
        if path not in self._parsed:
            self._parsed[path] = parse(path)
        return self._parsed[path]

    def rel(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    def check_target(self, path: Path, target: str) -> str | None:
        """Return the problem with one link target, or ``None``."""
        if not target or is_external(target):
            return None
        file_part, _, anchor = target.partition("#")
        file_part = unquote(file_part.split("?", 1)[0])
        if file_part.startswith("/"):
            return f"link target {target!r} is absolute; use a path relative to the file"
        dest = path.resolve() if not file_part else (path.parent / file_part).resolve()
        if not dest.is_relative_to(self.root):
            return f"link target {target!r} points outside the repository"
        if not dest.exists():
            siblings = [p.name for p in dest.parent.iterdir()] if dest.parent.is_dir() else []
            # File names share suffixes (".md"), so ask for a closer match.
            return f"link target {target!r} does not exist" + _suggest(
                dest.name, siblings, cutoff=0.8
            )
        if anchor and dest.suffix == ".md":
            anchors = self.parsed(dest).anchors
            if unquote(anchor) not in anchors:
                return (
                    f"anchor #{anchor} is not a heading or anchor of {self.rel(dest)}"
                    + _suggest(unquote(anchor), sorted(anchors))
                )
        return None

    def check_file(self, path: Path) -> list[str]:
        """Return every problem of one Markdown file as ``file:line: problem``."""
        lines = path.read_text(encoding="utf-8").splitlines()
        parsed = self.parsed(path)
        found: list[tuple[int, str]] = []
        for link in parsed.links + parsed.definitions:
            problem = self.check_target(path, link.target)
            if problem:
                found.append((link.line, problem))
        for ref in parsed.undefined_references:
            found.append((ref.line, f"reference {ref.target} has no definition"))
        for line in parsed.unclosed_fences:
            found.append((line, "code fence is never closed"))
        historical = self.rel(path) in HISTORY
        for line, command in [] if historical else parsed.code:
            for goal in make_goals(command):
                # A missing or emptied Makefile fails closed: no goal exists.
                if goal not in self.make_targets:
                    found.append(
                        (
                            line,
                            f"`make {goal}` is not a Makefile target"
                            + _suggest(goal, sorted(self.make_targets)),
                        )
                    )
        for number, line in enumerate([] if historical else lines, 1):
            for script in _SCRIPT.findall(line):
                if not (self.root / script).is_file():
                    names = [p.name for p in (self.root / "scripts").glob("*")]
                    found.append(
                        (
                            number,
                            f"{script} does not exist"
                            + _suggest(Path(script).name, names, cutoff=0.8),
                        )
                    )
        rel = self.rel(path)
        return [
            f"{rel}:{line}: {problem}"
            for line, problem in sorted(set(found))
            if not _suppressed(lines, line)
        ]


def run(root: Path, files: list[Path] | None = None) -> list[str]:
    """Return every problem in ``files`` (default: all Markdown files)."""
    checker = Checker(root)
    problems: list[str] = []
    for path in files if files is not None else markdown_files(checker.root):
        problems += checker.check_file(path)
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("files", nargs="*", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    files = [path.resolve() for path in args.files] or None
    problems = run(root, files)
    if problems:
        print(f"Documentation defects ({len(problems)}):")
        for problem in problems:
            print(f"  {problem}")
        print(f"Fix the target, or mark a reviewed false positive with {IGNORE}.")
        return 1
    count = len(files) if files else len(markdown_files(root))
    print(f"OK: {count} Markdown files; local links, anchors, fences and commands resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
