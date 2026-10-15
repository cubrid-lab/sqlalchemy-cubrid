#!/usr/bin/env python3
"""Check the agent guidance: root ``AGENTS.md`` plus the guides in ``docs/agents/`` (#907).

Deterministic checks only, no network:

* every relative Markdown link (inline, titled or reference-style) resolves to a
  file, and every ``#anchor`` to a heading of its target (GitHub heading slugs);
* every guide under ``docs/agents/`` is linked from the root ``AGENTS.md``;
* every ``make <target>`` written as a command (inline code or a fenced block)
  names a Makefile target, and every ``scripts/<name>`` path exists;
* a file that names a Python or CUBRID version links the support matrix or the
  CI policy, which own version lists;
* a ``requires-python = "..."`` or ``sqlalchemy>=...`` pin quoted in the root
  file equals ``pyproject.toml``, which owns dependency bounds.

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

ROOT_DOC = "AGENTS.md"
GUIDE_DIR = "docs/agents"
VERSION_OWNERS = ("docs/SUPPORT_MATRIX.md", "docs/CI_POLICY.md")

# An inline link or image target, with an optional "title", 'title' or (title).
_LINK = re.compile(r"\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)")
# A reference definition: [label]: target "optional title"
_REF_DEF = re.compile(r"^ {0,3}\[([^\]]+)\]:\s*<?(\S+?)>?(?:\s+.*)?$")
# A full or collapsed reference link: [text][label] or [label][]
_REF_USE = re.compile(r"\[([^\]]+)\]\[([^\]]*)\]")
# A fence: up to three spaces, then three or more backticks or tildes.
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_CODE_SPAN = re.compile(r"`([^`]*)`")
_MAKE = re.compile(r"(?:^|[\s;&|(])make\s+([a-z][a-z0-9_-]*)")
_SCRIPT = re.compile(r"\bscripts/[A-Za-z0-9_./-]+\.(?:py|cjs|sh)\b")
_VERSION = re.compile(r"\b(?:Python\s+3\.\d+|CUBRID\s+1\d\.\d)")
_MAKE_TARGET = re.compile(r"^([a-zA-Z0-9_-]+)\s*:(?!=)", re.M)
_REQUIRES_PYTHON = re.compile(r"`requires-python\s*=\s*\"([^\"]+)\"`")
_SQLALCHEMY_PIN = re.compile(r"`sqlalchemy([<>=!~][^`]*)`")


def agent_files(root: Path) -> list[Path]:
    """Return the root entry point and the guides, in a stable order."""
    files = [root / ROOT_DOC]
    files += sorted((root / GUIDE_DIR).glob("*.md"))
    return [path for path in files if path.is_file()]


def _prose_and_code(text: str) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """Split numbered lines into prose and fenced-code lines."""
    prose: list[tuple[int, str]] = []
    code: list[tuple[int, str]] = []
    fence = ""  # the opening fence run, while inside a fenced block
    for number, line in enumerate(text.splitlines(), 1):
        if not fence:
            opening = _FENCE.match(line)
            if opening:
                fence = opening.group(1)
                continue
            prose.append((number, line))
            continue
        # CommonMark: the same character, at least as long, nothing after it.
        closing = _FENCE.match(line)
        if closing and closing.group(1)[0] == fence[0] and len(closing.group(1)) >= len(fence):
            if not closing.group(2).strip():
                fence = ""
                continue
        code.append((number, line))
    return prose, code


def reference_definitions(text: str) -> list[tuple[int, str, str]]:
    """Return ``(line, label, target)`` of the reference definitions outside code."""
    prose, _ = _prose_and_code(text)
    result = []
    for number, line in prose:
        match = _REF_DEF.match(line)
        if match:
            result.append((number, match.group(1).strip().lower(), match.group(2)))
    return result


def navigable_links(text: str) -> list[tuple[int, str]]:
    """Return ``(line, target)`` of the links a reader can follow.

    Inline links (titled or not) and used reference-style links count; a
    definition alone renders nothing, and fenced code and inline code spans
    are examples, not links. An undefined reference label is returned with the
    target ``"[label]"`` so it can be reported.
    """
    prose, _ = _prose_and_code(text)
    definitions: dict[str, str] = {}
    for _, label, target in reference_definitions(text):
        definitions.setdefault(label, target)
    links: list[tuple[int, str]] = []
    for number, line in prose:
        if _REF_DEF.match(line):
            continue
        bare = _CODE_SPAN.sub("", line)
        links += [(number, match.group(1)) for match in _LINK.finditer(bare)]
        for match in _REF_USE.finditer(_LINK.sub("", bare)):
            label = (match.group(2) or match.group(1)).strip().lower()
            if label in definitions:
                links.append((number, definitions[label]))
            else:
                links.append((number, f"[{label}]"))
    return links


def slugify(heading: str) -> str:
    """Return GitHub's base anchor for a Markdown heading text."""
    text = _CODE_SPAN.sub(r"\1", heading)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors(path: Path) -> set[str]:
    """Return the heading anchors of a Markdown file, deduplicated as GitHub does.

    A repeated slug gets the first free ``-1``, ``-2``, ... suffix, checked
    against every anchor already allocated, so ``Same``, ``Same``, ``Same-1``
    give ``same``, ``same-1`` and ``same-1-1``.
    """
    used: set[str] = set()
    prose, _ = _prose_and_code(path.read_text(encoding="utf-8"))
    for _, line in prose:
        match = _HEADING.match(line)
        if not match:
            continue
        base = slugify(match.group(2))
        slug, count = base, 0
        while slug in used:
            count += 1
            slug = f"{base}-{count}"
        used.add(slug)
    return used


def _is_external(target: str) -> bool:
    return bool(re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target))


def check_links(root: Path, path: Path) -> list[str]:
    """Report relative links whose file, anchor or reference does not exist."""
    problems = []
    rel = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    targets = navigable_links(text)
    # Every definition target must resolve too, used or not.
    targets += [(number, target) for number, _, target in reference_definitions(text)]
    for number, target in sorted(targets):
        if target.startswith("["):
            problems.append(f"{rel}:{number}: reference {target} has no definition")
            continue
        if _is_external(target):
            continue
        file_part, _, anchor = target.partition("#")
        dest = path if not file_part else (path.parent / file_part).resolve()
        if not dest.exists():
            problems.append(f"{rel}:{number}: link target {target!r} does not exist")
            continue
        if anchor and dest.suffix == ".md" and anchor not in anchors(dest):
            problems.append(
                f"{rel}:{number}: anchor #{anchor} is not a heading of "
                f"{dest.relative_to(root).as_posix()}"
            )
    return problems


def check_reachable(root: Path) -> list[str]:
    """Report guides that the root entry point does not link."""
    entry = root / ROOT_DOC
    if not entry.is_file():
        return [f"{ROOT_DOC}: missing"]
    linked = set()
    for _, target in navigable_links(entry.read_text(encoding="utf-8")):
        file_part = target.partition("#")[0]
        if file_part and not target.startswith("[") and not _is_external(file_part):
            linked.add((root / file_part).resolve())
    return [
        f"{guide.relative_to(root).as_posix()}: not linked from {ROOT_DOC}"
        for guide in sorted((root / GUIDE_DIR).glob("*.md"))
        if guide.resolve() not in linked
    ]


def _command_text(text: str) -> list[tuple[int, str]]:
    """Return the numbered command text: fenced lines and inline code spans."""
    prose, code = _prose_and_code(text)
    spans = [(n, span) for n, line in prose for span in _CODE_SPAN.findall(line)]
    return sorted(code + spans)


def check_commands(root: Path, path: Path) -> list[str]:
    """Report ``make`` targets and ``scripts/`` paths that do not exist."""
    makefile = root / "Makefile"
    targets = (
        set(_MAKE_TARGET.findall(makefile.read_text(encoding="utf-8")))
        if makefile.exists()
        else set()
    )
    problems = []
    rel = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    for number, command in _command_text(text):
        for target in _MAKE.findall(command):
            if target not in targets:
                problems.append(f"{rel}:{number}: `make {target}` is not a Makefile target")
    for number, line in enumerate(text.splitlines(), 1):
        for script in _SCRIPT.findall(line):
            if not (root / script).is_file():
                problems.append(f"{rel}:{number}: {script} does not exist")
    return problems


def check_versions(root: Path, path: Path) -> list[str]:
    """Require a file that names versions to link the documents that own them."""
    text = path.read_text(encoding="utf-8")
    found = _VERSION.search(text)
    if not found:
        return []
    owners = {(root / owner).resolve() for owner in VERSION_OWNERS}
    for _, target in navigable_links(text):
        file_part = target.partition("#")[0]
        if file_part and not target.startswith("[") and not _is_external(file_part):
            if (path.parent / file_part).resolve() in owners:
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
        if _is_external(target) or target.startswith("#"):
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
    problems = check_reachable(root) + check_pins(root)
    for path in agent_files(root):
        problems += check_links(root, path)
        problems += check_commands(root, path)
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
    print(f"OK: {len(agent_files(root))} agent guidance files; links, guides and commands resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
