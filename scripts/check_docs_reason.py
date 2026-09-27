r"""Recognize a real standalone docs exception, outside Markdown examples.

>>> has_docs_not_needed_reason(None)
False
>>> has_docs_not_needed_reason('Docs: not needed - tests only')
True
>>> has_docs_not_needed_reason('Docs: not needed - <reason>')
False
>>> has_docs_not_needed_reason('> Docs: not needed - tests only')
False
>>> has_docs_not_needed_reason('````text\n```\nDocs: not needed - tests only\n````')
False
>>> has_docs_not_needed_reason('<!--\nDocs: not needed - tests only\n-->')
False
"""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from string import punctuation
from unicodedata import category

_PREFIX = "Docs: not needed -"
_MARKDOWN_ESCAPE = re.compile(r"\\([" + re.escape(punctuation) + r"])")
_LITERAL_RUN = re.compile(r"`+|\\+|\[[^\[\]\n\\`<>]*\]\(<[^<>\n]*>\)")
_BLOCK_PREFIX = r" {0,3}(?:(?:[-+*]|[0-9]{1,9}[.)])[ \t]+)?"
_ATX_HEADING = r" {0,3}#{1,6}(?=[ \t\n]|$)"
_THEMATIC_BREAK = r" {0,3}(?:(?:\*[ \t]*){3,}|(?:_[ \t]*){3,}|(?:-[ \t]*){3,})"
_HTML_BLOCK_START = re.compile(
    r" {0,3}(?:<!--|<(?:pre|script|style|textarea)(?=[ \t>]|$)"
    r"|<(?:blockquote|iframe)(?=[ \t>]|/>|$))",
    re.IGNORECASE,
)


def _reason_text(text: str) -> str:
    return "".join(
        character for character in text if category(character) not in {"Cc", "Cf"}
    ).strip()


def _placeholder(text: str) -> bool:
    reason = _reason_text(unescape(_MARKDOWN_ESCAPE.sub(r"\1", text)))
    if reason.startswith("<reason>"):
        return True
    wrapper = re.match(r"`+|\*{1,3}|_{1,3}|~{1,2}", reason)
    if wrapper is None:
        return False
    contents = reason[wrapper.end() :].lstrip()
    if not contents.startswith("<reason>"):
        return False
    closing = re.match(re.escape(wrapper[0][0]) + "+", contents[len("<reason>") :].lstrip())
    return closing is not None and closing[0] == wrapper[0]


class _HTMLContext(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=False)
        self.blocked: list[str] = []
        self.lines: dict[int, str] = {}
        self.marker_lines: set[int] = set()
        self.literal_positions: set[tuple[int, int]] = set()
        self.source = source
        self.fed_text = ""
        self.row_starts: list[int] = [0]
        self.inline_end = -1
        self.inline_spans: list[tuple[int, int]] = []

    def feed(self, data: str) -> None:
        base = len(self.fed_text)
        self.row_starts.extend(base + match.end() for match in re.finditer("\n", data))
        self.fed_text += data
        super().feed(data)

    def checkpoint(self) -> None:
        line, column = self.getpos()
        start = self.row_starts[line - 1] + column
        pending = self.fed_text[start:]
        safe = "<" not in pending and "&" not in pending
        if pending.startswith("<!--"):
            closer = pending.rfind("-->")
            tail = pending[closer + 3 :]
            safe = closer > pending.rfind("<!--") and "<" not in tail and "&" not in tail
        if pending and safe:
            self.close()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"blockquote", "pre", "code", "script", "style", "textarea", "iframe"}:
            self.blocked.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # These non-void containers still need an explicit closing tag in HTML.
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if self.blocked and self.blocked[-1] == tag:
            self.blocked.pop()

    def handle_data(self, data: str) -> None:
        if not self.blocked:
            line, column = self.getpos()
            for offset, text in enumerate(data.split("\n")):
                number = line + offset
                self.lines[number] = self.lines.get(number, "") + text
                indentation = len(text) - len(text.lstrip(" "))
                origin = column if offset == 0 else 0
                if origin + indentation <= 3 and text.lstrip(" ").startswith(_PREFIX):
                    self.marker_lines.add(number)
                for index, character in enumerate(text):
                    if character in "`\\[":
                        self.literal_positions.add((number, origin + index))

    def handle_entityref(self, name: str) -> None:
        self.handle_data(unescape(f"&{name};").replace("\r", " ").replace("\n", " "))

    def handle_charref(self, name: str) -> None:
        self.handle_data(unescape(f"&#{name};").replace("\r", " ").replace("\n", " "))

    def outside_prefix(self, number: int, prefix: str) -> bool:
        self.feed(prefix)
        self.checkpoint()
        return not self.blocked and self.lines.get(number) == prefix

    def feed_literals(self, text: str, number: int, column: int, offset: int) -> None:
        cursor = 0
        while cursor < len(text):
            if offset + cursor < self.inline_end:
                end = min(len(text), self.inline_end - offset)
                self.feed(text[cursor:end].replace("<", " ").replace("&", " "))
                cursor = end
                continue
            run = _LITERAL_RUN.search(text, cursor)
            if run is None:
                self.feed(text[cursor:])
                break
            if run[0][0] == "[":
                self.feed(text[cursor : run.start() + 1])
                self.checkpoint()
                escaped = re.search(r"\\+$", self.source[: offset + run.start()])
                outside = (
                    not self.blocked and (number, column + run.start()) in self.literal_positions
                )
                literal = outside and (escaped is None or len(escaped[0]) % 2 == 0)
                destination = run[0].index("](<") + 2
                self.feed(run[0][1:destination])
                tail = run[0][destination:]
                self.feed(tail.replace("<", " ").replace("&", " ") if literal else tail)
                cursor = run.end()
                continue
            self.feed(text[cursor : run.end()])
            self.checkpoint()
            outside = not self.blocked and (number, column + run.start()) in self.literal_positions
            cursor = run.end()
            if not outside:
                continue
            if run[0][0] == "\\":
                if len(run[0]) % 2 and cursor < len(text) and text[cursor] in "<`":
                    self.feed(" " if text[cursor] == "<" else "`")
                    cursor += 1
                continue
            start = offset + cursor
            paragraph = re.search(r"\n[ \t]*\n", self.source[start:])
            limit = start + paragraph.start() if paragraph else len(self.source)
            quote_boundary = re.search(r"\n" + _BLOCK_PREFIX + ">", self.source[start:limit])
            if quote_boundary:
                limit = start + quote_boundary.start() + 1
            heading = re.search(r"\n" + _ATX_HEADING, self.source[start:limit])
            if heading:
                limit = start + heading.start() + 1
            thematic = re.search(r"\n" + _THEMATIC_BREAK + r"(?=\n|$)", self.source[start:limit])
            if thematic:
                limit = start + thematic.start() + 1
            for boundary in re.finditer(
                r"\n" + _BLOCK_PREFIX + r"(`{3,}|~{3,})([^\n]*)", self.source[start:limit]
            ):
                if boundary[1][0] == "~" or "`" not in boundary[2]:
                    limit = start + boundary.start() + 1
                    break
            closing = next(
                (
                    match
                    for match in re.finditer(r"`+", self.source[start:limit])
                    if len(match[0]) == len(run[0])
                ),
                None,
            )
            if closing is not None:
                self.inline_end = start + closing.end()
                self.inline_spans.append((offset + run.start(), self.inline_end))


def has_docs_not_needed_reason(body: str | None) -> bool:
    prefix = _PREFIX
    raw_lines = re.split(r"\r\n|\r|\n", body or "")
    html = _HTMLContext("\n".join(raw_lines))
    candidates = []
    fence = None
    quoted = False
    offset = 0
    for number, raw in enumerate(raw_lines, 1):
        origin = offset
        offset += len(raw) + 1
        line = raw.rstrip()
        stripped = line.lstrip()
        opener = re.match(_BLOCK_PREFIX + r"(`{3,}|~{3,})", line)
        if origin < html.inline_end:
            html.feed_literals(line + "\n", number, 0, origin)
            continue
        if fence:
            marker = re.match(r"[ \t]*(`{3,}|~{3,})", line)
            fence_indent = len(line[: marker.start(1)].expandtabs(4)) if marker else -1
            if (
                marker
                and fence[2] <= fence_indent <= fence[2] + 3
                and marker[1][0] == fence[0]
                and len(marker[1]) >= fence[1]
            ):
                if not line[marker.end() :].strip():
                    fence = None
            html.feed("\n")
            continue
        if not stripped:
            quoted = False
        if quoted and re.fullmatch(r" {0,3}>[ \t]*", line):
            quoted = False
            html.feed("\n")
            continue
        if quoted and (
            re.match(_ATX_HEADING, line)
            or re.fullmatch(_THEMATIC_BREAK, raw)
            or _HTML_BLOCK_START.match(line)
            or (opener and (opener[1][0] == "~" or "`" not in line[opener.end() :]))
        ):
            quoted = False
        if quoted:
            html.feed("\n")
            continue
        indentation = re.match(r"(?: {4,}| {0,3}\t)", line)
        quote = re.match(_BLOCK_PREFIX + ">", line)
        if indentation:
            if html.outside_prefix(number, line[: indentation.end()]):
                html.feed("\n")
                continue
            html.feed_literals(
                line[indentation.end() :] + "\n",
                number,
                indentation.end(),
                origin + indentation.end(),
            )
        elif quote:
            if html.outside_prefix(number, line[: quote.end()]):
                quoted = True
                html.feed("\n")
                continue
            html.feed_literals(
                line[quote.end() :] + "\n", number, quote.end(), origin + quote.end()
            )
        elif opener and (opener[1][0] == "~" or "`" not in line[opener.end() :]):
            if html.outside_prefix(number, line[: opener.end()]):
                list_item = re.match(r" {0,3}(?:[-+*]|[0-9]{1,9}[.)])[ \t]+", line)
                base = len(line[: opener.start(1)].expandtabs(4)) if list_item else 0
                fence = (opener[1][0], len(opener[1]), base)
                html.feed("\n")
                continue
            html.feed_literals(
                line[opener.end() :] + "\n", number, opener.end(), origin + opener.end()
            )
        else:
            html.feed_literals(line + "\n", number, 0, origin)
        if re.match(r" {0,3}" + re.escape(prefix), line):
            position = origin + len(line) - len(line.lstrip(" "))
            if not _placeholder(line.lstrip(" ")[len(prefix) :]):
                candidates.append((number, position))
    html.close()
    for number, position in candidates:
        line = html.lines.get(number, "").lstrip(" ")
        inside = any(start <= position < end for start, end in html.inline_spans)
        if not inside and number in html.marker_lines and line.startswith(prefix):
            reason = _reason_text(line[len(prefix) :])
            if reason and not _placeholder(reason):
                return True
    return False
