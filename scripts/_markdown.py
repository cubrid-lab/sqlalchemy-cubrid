"""Shared CommonMark helpers for the repository documentation checks (#908; shared with pycubrid #927).

``markdown-it-py`` parses each file, so fenced code (backtick or tilde, any
length, inside lists and block quotes), inline code spans of any backtick
length and reference-style links follow CommonMark instead of hand-written
regular expressions. Only links a reader can follow are returned: a reference
definition without a use renders nothing, and links inside code are examples.
Every link, code span and undefined reference keeps its own source line, so a
diagnostic and its suppression comment refer to the same line.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.token import Token

_PARSER = MarkdownIt("commonmark").enable("table")
_ATTR_ID = re.compile(r"\s*\{[^}]*#([\w-]+)[^}]*\}\s*$")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_BACKTICKS = re.compile(r"`+")
# A full or collapsed reference link whose brackets are not escaped; an opening
# bracket after a word character (``rows[0][1]``) is an index, not a link.
_REFERENCE = re.compile(r"(?<![\\\]\w])\[((?:[^\[\]\\]|\\.)+)\]\[((?:[^\[\]\\]|\\.)*)\](?!\s*[(:])")
_MAKE_GOAL = re.compile(r"[a-z][a-z0-9_.-]*\Z")
# make options that take a separate argument (``-C dir``) or an optional one (``-j 4``).
_MAKE_ARG = {
    "-C",
    "-f",
    "-I",
    "-o",
    "-W",
    "--directory",
    "--file",
    "--makefile",
    "--include-dir",
    "--old-file",
    "--assume-old",
    "--new-file",
    "--assume-new",
    "--what-if",
}
_MAKE_OPTIONAL_NUMBER = {"-j", "-l", "--jobs", "--load-average", "--max-load"}


@dataclass(frozen=True)
class Link:
    """A followable link: 1-based source line and its raw target."""

    line: int
    target: str


@dataclass(frozen=True)
class Parsed:
    """The parts of a Markdown file the checks need."""

    links: list[Link]
    definitions: list[Link]
    undefined_references: list[Link]
    anchors: set[str]
    code: list[tuple[int, str]]
    unclosed_fences: list[int]


def github_slug(text: str) -> str:
    """Return GitHub's base anchor for a heading's rendered text.

    Lowercase; keep letters, marks, numbers, ``_``, ``-`` and spaces; turn each
    space into ``-`` (github-slugger).
    """
    kept = []
    for char in text.lower():
        category = unicodedata.category(char)
        if char in " -_" or category[0] in "LMN" or category == "Pc":
            kept.append(char)
    return "".join(kept).replace(" ", "-")


def _site_slug(text: str) -> str:
    """Return the MkDocs site's base anchor: GitHub's, without combining marks.

    ``pymdownx.slugs.slugify`` (mkdocs.yml) drops marks such as Devanagari
    vowel signs that GitHub keeps.
    """
    return "".join(c for c in github_slug(text) if unicodedata.category(c)[0] != "M")


def _allocate(base: str, used: set[str], separator: str) -> str:
    """Return ``base`` or its first free ``<separator>N`` duplicate suffix."""
    slug, count = base, 0
    while slug in used:
        count += 1
        slug = f"{base}{separator}{count}"
    used.add(slug)
    return slug


def _inline_text(token: Token) -> str:
    return "".join(
        child.content for child in token.children or [] if child.type in ("text", "code_inline")
    )


def _mask_code_spans(raw: str) -> str:
    """Replace inline code spans (any backtick run length) by spaces, keeping newlines."""
    out = list(raw)
    position = 0
    while True:
        opening = _BACKTICKS.search(raw, position)
        if opening is None:
            return "".join(out)
        run = opening.group(0)
        closing = re.compile(rf"(?<!`){run}(?!`)").search(raw, opening.end())
        if closing is None:
            position = opening.end()
            continue
        for index in range(opening.start(), closing.end()):
            if out[index] != "\n":
                out[index] = " "
        position = closing.end()


def _inline_items(token: Token) -> list[tuple[int, Token]]:
    """Return ``(line offset, child)`` for the children of an inline token.

    Soft and hard breaks start a new line; a code span that spans lines moves
    the following children down by its newlines, found in the raw source.
    """
    raw = token.content
    cursor, offset = 0, 0
    items = []
    for child in token.children or []:
        items.append((offset, child))
        if child.type in ("softbreak", "hardbreak"):
            newline = raw.find("\n", cursor)
            if newline >= 0:
                cursor = newline + 1
            offset += 1
        elif child.type == "code_inline" and child.markup:
            start = raw.find(child.markup, cursor)
            end = raw.find(child.markup, start + len(child.markup)) if start >= 0 else -1
            if start >= 0 and end >= 0:
                offset += raw.count("\n", start, end)
                cursor = end + len(child.markup)
    return items


def _unclosed_fences(tokens: list[Token]) -> list[int]:
    """Return the opening lines of fences that run to the end of their container.

    markdown-it maps a closed fence to its opening line, its content lines and
    its closing line, and an unclosed one to the opening and content lines
    only. That is exact inside lists and block quotes, and for a line such as
    ``> ~~~`` or an over-indented ``~~~`` that does not close a top-level fence.
    """
    unclosed = []
    for token in tokens:
        if token.type != "fence" or token.map is None:
            continue
        start, end = token.map
        if end - start != len(token.content.splitlines()) + 2:
            unclosed.append(start + 1)
    return unclosed


def _blank(text: str) -> str:
    return re.sub(r"[^\n]", " ", text)


def _mask_link_tails(raw: str) -> str:
    """Blank inline link destinations and titles: ``](dest "title")``.

    The scan follows CommonMark: backslash escapes, quoted titles and balanced
    parentheses inside the destination.
    """
    out = list(raw)
    position = 0
    while (opening := raw.find("](", position)) >= 0:
        index, depth, quote = opening + 2, 1, ""
        while index < len(raw) and depth:
            char = raw[index]
            if char == "\\":
                index += 2
                continue
            if quote:
                quote = "" if char == quote else quote
            elif char in "\"'":
                quote = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            index += 1
        for spot in range(opening + 1, index):
            if out[spot] != "\n":
                out[spot] = " "
        position = index
    return "".join(out)


def _undefined_references(token: Token, defined: set[str]) -> list[Link]:
    """Return unescaped ``[text][label]`` uses, outside code, whose label is undefined.

    Code spans, HTML (tags, autolinks, comments) and inline link destinations
    and titles are blanked first, so brackets in a URL or a title are not links.
    """
    if token.map is None:
        return []
    raw = _mask_code_spans(token.content)
    raw = _HTML_COMMENT.sub(lambda m: _blank(m.group(0)), raw)
    raw = re.sub(r"<[^<>\n]*>", lambda m: _blank(m.group(0)), raw)
    raw = _mask_link_tails(raw)
    found = []
    for match in _REFERENCE.finditer(raw):
        label = " ".join((match.group(2) or match.group(1)).split()).casefold()
        if label not in defined:
            line = token.map[0] + 1 + raw.count("\n", 0, match.start())
            found.append(Link(line, f"[{label}]"))
    return found


class _HtmlAttributes(HTMLParser):
    """Collect link targets and ``<a>`` anchors from HTML, as a browser parses it.

    The standard library parser reads quoted and unquoted attribute values,
    decodes entities and skips comments, so ``data-src`` is not ``src``.
    """

    TARGETS = {"a": "href", "img": "src", "source": "src"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.targets: list[tuple[int, str]] = []
        self.anchors: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value for name, value in attrs if value is not None}
        wanted = self.TARGETS.get(tag)
        if wanted and values.get(wanted):
            self.targets.append((self.getpos()[0], values[wanted]))
        if tag == "a":
            self.anchors |= {values[name] for name in ("id", "name") if values.get(name)}

    handle_startendtag = handle_starttag


def _html_parse(source: str) -> _HtmlAttributes:
    parser = _HtmlAttributes()
    parser.feed(source)
    parser.close()
    return parser


def _html_targets(line: int, source: str) -> list[Link]:
    """Return ``href``/``src`` targets of HTML, outside comments, with their lines."""
    return [Link(line + row - 1, target) for row, target in _html_parse(source).targets]


def _html_anchors(tokens: list[Token]) -> set[str]:
    """Return ``<a id>``/``<a name>`` anchors of HTML blocks and inline HTML, not comments."""
    found: set[str] = set()
    for token in tokens:
        sources = [token.content] if token.type == "html_block" else []
        if token.type == "inline":
            sources += [c.content for c in token.children or [] if c.type == "html_inline"]
        for source in sources:
            found |= _html_parse(source).anchors
    return found


def parse(path: Path) -> Parsed:
    """Parse one Markdown file."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    env: dict[str, object] = {}
    tokens = _PARSER.parse(text, env)
    references = env.get("references", {})
    references = references if isinstance(references, dict) else {}
    defined = {" ".join(str(label).split()).casefold() for label in references}
    links: list[Link] = []
    code: list[tuple[int, str]] = []
    undefined: list[Link] = []
    # GitHub keeps a literal ``{#id}`` in its slug and suffixes duplicates with
    # -1, -2 ...; the MkDocs site (attr_list, toc) uses the id and _1, _2 ...
    github_used: set[str] = set()
    site_used: set[str] = set()
    anchors = _html_anchors(tokens)
    for index, token in enumerate(tokens):
        if token.map is None:
            continue
        line = token.map[0] + 1
        if token.type == "fence":
            code += _logical_lines(line + 1, token.content.splitlines())
            continue
        if token.type == "html_block":
            links += _html_targets(line, token.content)
            continue
        if token.type != "inline":
            continue
        for offset, child in _inline_items(token):
            if child.type == "link_open":
                links.append(Link(line + offset, str(child.attrGet("href") or "")))
            elif child.type == "image":
                links.append(Link(line + offset, str(child.attrGet("src") or "")))
            elif child.type == "code_inline":
                code.append((line + offset, child.content))
            elif child.type == "html_inline":
                links += _html_targets(line + offset, child.content)
        undefined += _undefined_references(token, defined)
        if index and tokens[index - 1].type == "heading_open":
            heading = _inline_text(token).strip()
            anchors.add(_allocate(github_slug(heading), github_used, "-"))
            explicit = _ATTR_ID.search(heading)
            if explicit:
                anchors.add(explicit.group(1))
                site_used.add(explicit.group(1))
            else:
                anchors.add(_allocate(_site_slug(heading), site_used, "_"))
    definitions = []
    for label, ref in references.items():
        if isinstance(ref, dict):
            map_ = ref.get("map")
            number = map_[0] + 1 if map_ else _definition_line(lines, str(label))
            definitions.append(Link(number, str(ref.get("href", ""))))
    return Parsed(
        links=links,
        definitions=definitions,
        undefined_references=undefined,
        anchors=anchors,
        code=sorted(code),
        unclosed_fences=_unclosed_fences(tokens),
    )


def _logical_lines(first: int, lines: list[str]) -> list[tuple[int, str]]:
    """Join backslash-continued lines into one command, reported at its first line."""
    result: list[tuple[int, str]] = []
    start, parts = first, []
    for number, line in enumerate(lines, first):
        if not parts:
            start = number
        if line.rstrip().endswith("\\"):
            parts.append(line.rstrip()[:-1])
            continue
        parts.append(line)
        result.append((start, " ".join(parts)))
        parts = []
    if parts:
        result.append((start, " ".join(parts)))
    return result


def _definition_line(lines: list[str], label: str) -> int:
    pattern = re.compile(rf"^ {{0,3}}\[{re.escape(label)}\]:", re.I)
    for number, line in enumerate(lines, 1):
        if pattern.match(line):
            return number
    return 1


_OPERATOR_CHARS = frozenset(";&|()<>")


def _shell_tokens(command: str) -> list[tuple[str, bool]]:
    """Split a shell command into ``(text, is_operator)`` tokens.

    Quotes and backslashes make text literal, so a quoted or escaped ``;`` is
    a word, not a separator. ``#`` starts a comment at the start of a word.
    An unbalanced quote means the text is not a shell command: no tokens.
    """
    tokens: list[tuple[str, bool]] = []
    word: list[str] = []
    in_word = False
    index, size = 0, len(command)

    def flush() -> None:
        nonlocal in_word
        if in_word:
            tokens.append(("".join(word), False))
            word.clear()
            in_word = False

    while index < size:
        char = command[index]
        if char in " \t\n":
            flush()
            index += 1
        elif char == "#" and not in_word:
            break
        elif char == "\\":
            word.append(command[index + 1 : index + 2])
            in_word = True
            index += 2
        elif char in "'\"":
            end = index + 1
            while end < size and command[end] != char:
                end += 2 if char == '"' and command[end] == "\\" else 1
            if end >= size:
                return []
            text = command[index + 1 : end]
            word.append(re.sub(r'\\(["\\$`])', r"\1", text) if char == '"' else text)
            in_word = True
            index = end + 1
        elif char in _OPERATOR_CHARS:
            flush()
            end = index
            while end < size and command[end] in _OPERATOR_CHARS:
                end += 1
            tokens.append((command[index:end], True))
            index = end
        else:
            word.append(char)
            in_word = True
            index += 1
    flush()
    return tokens


def make_goals(command: str) -> list[str]:
    """Return the explicit goals of every ``make`` invocation in a command line.

    Separators (``;``, ``&&``, ``||``, ``|``, ``&``, parentheses) end an
    invocation, with or without spaces, but only outside quotes. Redirections
    (``>``, ``2>&1``, ``<``) are skipped with their operand, options with
    their arguments (``-C dir``, ``--directory=dir``, ``-j 4``), and
    ``VAR=value`` assignments; every other operand is a goal.
    """
    goals = []
    tokens = _shell_tokens(command)
    # ``make`` counts only as the command word of a simple command, after any
    # ``VAR=value`` prefixes: ``echo make test`` names no goal.
    index, in_make, at_start = 0, False, True
    while index < len(tokens):
        token, operator = tokens[index]
        index += 1
        if operator:
            if "<" in token or ">" in token:
                index += 1  # the redirection's operand
            else:
                in_make, at_start = False, True
            continue
        if not in_make:
            if at_start and "=" in token and not token.startswith("-"):
                continue  # an environment prefix: the command word is still ahead
            in_make, at_start = at_start and token == "make", False
            continue
        if token in _MAKE_ARG:
            index += 1
        elif token in _MAKE_OPTIONAL_NUMBER:
            if index < len(tokens) and tokens[index][0].isdigit():
                index += 1
        elif token.startswith("-") or "=" in token:
            continue
        elif _MAKE_GOAL.match(token):
            goals.append(token)
    return goals


def is_external(target: str) -> bool:
    """Return whether a target is a URL: a scheme (``https:``, ``mailto:``) or ``//host``."""
    return target.startswith("//") or bool(re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target))
