"""The README async examples stay complete, runnable scripts (#941).

They used to put ``async with`` and ``await`` at module level, a ``SyntaxError``
in an ordinary ``.py`` file. Every Python block that uses the async driver in
the README and its translations must compile as a plain script (no top-level
await flag), start from ``asyncio.run(main())`` and dispose of its engine. The
English README is the canonical source: the Korean README repeats both
programs byte for byte, and the community translations may only repeat them.
The fenced blocks come from the shared Markdown parser of the docs checks.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from _markdown import _PARSER  # noqa: E402

ASYNC_URL = "cubrid+aiopycubrid://"
TRANSLATIONS = sorted((ROOT / "docs").glob("README.*.md"))


def async_blocks(path: Path) -> list[str]:
    """Return the Python fenced blocks of ``path`` that use the async driver."""
    tokens = _PARSER.parse(path.read_text(encoding="utf-8"))
    return [
        token.content
        for token in tokens
        if token.type == "fence" and token.info.strip() == "python" and ASYNC_URL in token.content
    ]


CANONICAL = async_blocks(ROOT / "README.md")


def test_readme_has_the_two_async_programs() -> None:
    assert len(CANONICAL) == 2


@pytest.mark.parametrize("source", CANONICAL, ids=["query", "insert"])
def test_async_example_is_a_complete_script(source: str) -> None:
    # Full compile, no top-level await flag: a module-level await raises SyntaxError.
    compile(source, "<README async example>", "exec")
    tree = ast.parse(source)
    for node in tree.body:
        assert not isinstance(node, (ast.AsyncWith, ast.AsyncFor)), ast.unparse(node)
    assert 'if __name__ == "__main__":\n    asyncio.run(main())\n' in source
    assert "async def main() -> None:" in source
    assert "await engine.dispose()" in source


def test_korean_readme_repeats_the_canonical_programs() -> None:
    assert async_blocks(ROOT / "docs" / "README.ko.md") == CANONICAL


@pytest.mark.parametrize("path", TRANSLATIONS, ids=[p.name for p in TRANSLATIONS])
def test_translations_only_repeat_canonical_programs(path: Path) -> None:
    for block in async_blocks(path):
        assert block in CANONICAL, f"{path.name} has an async example that is not in README.md"
