"""Deterministic documentation checks: local links, anchors, fences, commands (#908, #921)."""

from __future__ import annotations

import importlib.util
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "check_docs_links", ROOT / "scripts/check_docs_links.py"
)
assert _SPEC is not None and _SPEC.loader is not None
check = importlib.util.module_from_spec(_SPEC)
sys.modules["check_docs_links"] = check
_SPEC.loader.exec_module(check)

# check_docs_links imports the shared parser; reuse that module.
_markdown = sys.modules["_markdown"]
github_slug, make_goals, parse = _markdown.github_slug, _markdown.make_goals, _markdown.parse

TARGET = """# Target

## Connection options {#options}

<a id="legacy-anchor"></a>

## 한글 제목

## Same

## Same
"""


def _tree(tmp_path: Path, page: str, extra: dict[str, str] | None = None) -> Path:
    (tmp_path / "docs").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/tool.py").write_text("", encoding="utf-8")
    (tmp_path / "Makefile").write_text("test:\n\tpytest\nlint:\n\truff\n", encoding="utf-8")
    (tmp_path / "docs/TARGET.md").write_text(TARGET, encoding="utf-8")
    (tmp_path / "docs/PAGE.md").write_text(page, encoding="utf-8")
    for name, text in (extra or {}).items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def test_repository_documentation_has_no_deterministic_defects() -> None:
    assert check.run(ROOT) == []


def test_valid_relative_links_and_anchors_pass(tmp_path: Path) -> None:
    page = (
        "# Page\n\n[t](TARGET.md), [o](TARGET.md#options), [a](TARGET.md#legacy-anchor),\n"
        "[k](TARGET.md#한글-제목), [d](TARGET.md#same-1), [s](TARGET.md#same_1),\n"
        '[self](#page), [dir](../docs/), [img](TARGET.md "title") and ![i](TARGET.md).\n'
    )
    assert check.run(_tree(tmp_path, page)) == []


def test_external_links_are_not_fetched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def no_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the documentation check must not open a connection")

    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket.socket, "connect", no_network)
    page = "[x](https://unreachable.invalid/page) [m](mailto:a@b.invalid) [h](http://x.invalid)\n"
    assert check.run(_tree(tmp_path, page)) == []


def test_broken_relative_link_fails_with_location_and_suggestion(tmp_path: Path) -> None:
    root = _tree(tmp_path, "# Page\n\nSee [the target](TARGTE.md).\n")
    assert check.run(root) == [
        "docs/PAGE.md:3: link target 'TARGTE.md' does not exist; did you mean 'TARGET.md'?"
    ]


def test_deleted_reference_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, "# Page\n\nSee [the target](TARGET.md#options).\n")
    assert check.run(root) == []
    (root / "docs/TARGET.md").unlink()
    assert check.run(root) == ["docs/PAGE.md:3: link target 'TARGET.md#options' does not exist"]


def test_invalid_anchor_fails_with_suggestion(tmp_path: Path) -> None:
    root = _tree(tmp_path, "# Page\n\nSee [options](TARGET.md#option) and [x](#nowhere).\n")
    assert check.run(root) == [
        "docs/PAGE.md:3: anchor #nowhere is not a heading or anchor of docs/PAGE.md",
        (
            "docs/PAGE.md:3: anchor #option is not a heading or anchor of docs/TARGET.md; "
            + "did you mean 'options'?"
        ),
    ]


def test_absolute_and_escaping_paths_fail(tmp_path: Path) -> None:
    root = _tree(tmp_path, "[a](/docs/TARGET.md) and [b](../../outside.md)\n")
    assert check.run(root) == [
        "docs/PAGE.md:1: link target '../../outside.md' points outside the repository",
        (
            "docs/PAGE.md:1: link target '/docs/TARGET.md' is absolute; use a path relative to "
            + "the file"
        ),
    ]


def test_reference_links_and_definitions(tmp_path: Path) -> None:
    page = (
        "# Page\n\nSee [ok][t], [bad][gone] and [x][missing].\n\n"
        "[t]: TARGET.md#options\n[gone]: GONE.md\n[unused]: ALSO_GONE.md\n"
    )
    assert check.run(_tree(tmp_path, page)) == [
        "docs/PAGE.md:3: link target 'GONE.md' does not exist",
        "docs/PAGE.md:3: reference [missing] has no definition",
        "docs/PAGE.md:6: link target 'GONE.md' does not exist",
        "docs/PAGE.md:7: link target 'ALSO_GONE.md' does not exist",
    ]


def test_links_in_code_are_examples(tmp_path: Path) -> None:
    page = (
        "`[a](GONE.md)` and ``[b](GONE.md) with ` inside``\n\n"
        "```md\n[c](GONE.md)\n```\n\n~~~\n[d](GONE.md)\n~~~\n\n"
        "````\n```\n[e](GONE.md)\n```\n````\n"
    )
    assert check.run(_tree(tmp_path, page)) == []


@pytest.mark.parametrize(
    ("page", "line"),
    [("# Page\n\n```bash\nmake test\n", 3), ("~~~\nx\n```\n", 1), ("````\nx\n```\n", 1)],
)
def test_unclosed_fence_fails(tmp_path: Path, page: str, line: int) -> None:
    assert check.run(_tree(tmp_path, page)) == [f"docs/PAGE.md:{line}: code fence is never closed"]


def test_closed_fences_pass(tmp_path: Path) -> None:
    page = (
        "```\nx\n```\n\n~~~~\n~~~\n~~~~\n\n> ~~~\n> quoted\n> ~~~\n\n"
        "- item\n\n  ```bash\n  make test\n  ```\n\n```\nlast\n```\n"
    )
    assert check.run(_tree(tmp_path, page)) == []


@pytest.mark.parametrize("closing", ["> ~~~", "    ~~~"])
def test_a_quoted_or_over_indented_line_does_not_close_a_fence(
    tmp_path: Path, closing: str
) -> None:
    page = f"~~~\nx\n{closing}\n"
    assert check.run(_tree(tmp_path, page)) == ["docs/PAGE.md:1: code fence is never closed"]


@pytest.mark.parametrize(
    ("page", "line"),
    [
        ("> ~~~\n> text\n\nAfter the quote.\n", 1),
        ("- item\n\n  ```\n  code\n\nnot indented\n", 3),
    ],
)
def test_unclosed_fence_inside_a_container_fails(tmp_path: Path, page: str, line: int) -> None:
    assert check.run(_tree(tmp_path, page)) == [f"docs/PAGE.md:{line}: code fence is never closed"]


def test_commands_are_checked_only_in_code(tmp_path: Path) -> None:
    page = (
        "Make sure to make good use of it.\n\n"
        "Run `make test lnit` then:\n\n```bash\nmake -j2 lint && make tset\n"
        "python scripts/tool.py && python scripts/gone.py\n```\n"
    )
    assert check.run(_tree(tmp_path, page)) == [
        "docs/PAGE.md:3: `make lnit` is not a Makefile target; did you mean 'lint'?",
        "docs/PAGE.md:6: `make tset` is not a Makefile target; did you mean 'test'?",
        "docs/PAGE.md:7: scripts/gone.py does not exist",
    ]


def test_release_history_keeps_old_commands(tmp_path: Path) -> None:
    history = "# Changelog\n\n- Removed `make release` and scripts/check_version.py.\n"
    root = _tree(tmp_path, "# Page\n", {"CHANGELOG.md": history})
    assert check.run(root) == []
    (root / "CHANGELOG.md").write_text(history + "\nSee [gone](GONE.md).\n", encoding="utf-8")
    assert check.run(root) == ["CHANGELOG.md:5: link target 'GONE.md' does not exist"]


def test_literal_brackets_are_not_references(tmp_path: Path) -> None:
    page = (
        "Escaped \\[text\\]\\[label\\], an index rows[0][1], a closing ][label] alone,\n"
        "`[x][y]` in code and a defined [link][t].\n\n[t]: TARGET.md\n"
    )
    assert check.run(_tree(tmp_path, page)) == []


def test_html_link_and_image_targets_are_checked(tmp_path: Path) -> None:
    page = (
        '<p align="center"><img src="demo.gif" alt="Demo"></p>\n\n'
        'Inline <a href="TARGET.md#options">options</a> and <img src="dem0.gif">.\n\n'
        '<!-- <img src="commented.gif"> -->\n\n`<img src="code.gif">`\n'
    )
    root = _tree(tmp_path, page, {"docs/demo.gif": ""})
    assert check.run(root) == [
        "docs/PAGE.md:3: link target 'dem0.gif' does not exist; did you mean 'demo.gif'?"
    ]


@pytest.mark.parametrize(
    "first",
    [
        'Inline <a\nhref="https://example.invalid">x</a>',
        '[t](TARGET.md "a\nb") then',
        '![i](TARGET.md "a\nb") then',
    ],
)
def test_lines_after_multi_line_tags_and_titles_are_exact(tmp_path: Path, first: str) -> None:
    page = f"{first}\n[bad](GONE.md)\n\n{first}\n[ok](GONE.md) <!-- docs-check: ignore -->\n"
    assert check.run(_tree(tmp_path, page)) == [
        "docs/PAGE.md:3: link target 'GONE.md' does not exist"
    ]


@pytest.mark.parametrize("use", ["[ok][r]", "![ok][r]"])
def test_reference_titles_add_no_lines_at_the_use_site(tmp_path: Path, use: str) -> None:
    page = (
        f"{use}\n[bad](GONE.md)\n\n{use} [ok2](GONE.md) <!-- docs-check: ignore -->\n\n"
        '[r]: TARGET.md "a\nb\nc"\n'
    )
    assert check.run(_tree(tmp_path, page)) == [
        "docs/PAGE.md:2: link target 'GONE.md' does not exist"
    ]


def test_a_malformed_link_tail_does_not_hide_later_references(tmp_path: Path) -> None:
    page = "[example]( and [broken][missing]\n"
    assert check.run(_tree(tmp_path, page)) == [
        "docs/PAGE.md:1: reference [missing] has no definition"
    ]


def test_an_angle_bracket_destination_keeps_its_title_masked(tmp_path: Path) -> None:
    page = '[site](<https://example.invalid/> "See ) [foo][bar]")\n'
    assert check.run(_tree(tmp_path, page)) == []


@pytest.mark.parametrize(
    "block",
    [
        "echo \\\\\nmake removed",  # an escaped backslash: two commands
        "echo x\\  \nmake removed",  # a backslash before spaces does not continue
        "echo 'a\\\nb'\nmake removed",  # a backslash in single quotes is literal
    ],
)
def test_only_a_real_continuation_joins_lines(tmp_path: Path, block: str) -> None:
    page = f"```bash\n{block}\n```\n"
    findings = check.run(_tree(tmp_path, page))
    assert [p.split(": ", 1)[1] for p in findings] == ["`make removed` is not a Makefile target"]


def test_grouped_and_double_colon_make_rules_declare_every_target(tmp_path: Path) -> None:
    root = _tree(tmp_path, "Run `make check-docs`, `make alpha beta` and `make again`.\n")
    (root / "Makefile").write_text(
        "check-docs alpha: ## grouped\n\ttrue\nbeta again::\n\ttrue\n"
        "var := x\nother ?= y\nlate ::= z\n\tnot-a-rule: z\n",
        encoding="utf-8",
    )
    assert check.run(root) == []
    (root / "docs/PAGE.md").write_text(
        "Run `make var`, `make late` and `make not-a-rule`.\n", encoding="utf-8"
    )
    assert [p.split(": ", 1)[1] for p in check.run(root)] == [
        "`make late` is not a Makefile target",
        "`make not-a-rule` is not a Makefile target",
        "`make var` is not a Makefile target",
    ]


def test_an_apostrophe_in_a_destination_does_not_open_a_title(tmp_path: Path) -> None:
    page = "[site](https://example.invalid/it's) and [broken][missing]\n"
    assert check.run(_tree(tmp_path, page)) == [
        "docs/PAGE.md:1: reference [missing] has no definition"
    ]


def test_a_word_split_across_a_continuation_is_one_word(tmp_path: Path) -> None:
    assert check.run(_tree(tmp_path, "```bash\nmake te\\\nst\n```\n")) == []
    (tmp_path / "split").mkdir()
    assert check.run(_tree(tmp_path / "split", "```bash\nmake te\\\n st\n```\n")) == [
        "docs/PAGE.md:2: `make st` is not a Makefile target",
        "docs/PAGE.md:2: `make te` is not a Makefile target",
    ]


@pytest.mark.parametrize(
    ("command", "goals"),
    [
        ("make test;>log make lint", ["test", "lint"]),
        ("echo ok;>log make removed", ["removed"]),
        ("make a&&make b", ["a", "b"]),
        ("make test &>log", ["test"]),
        ("make test &>>build.log", ["test"]),
    ],
)
def test_adjacent_shell_operators_are_separate(command: str, goals: list[str]) -> None:
    assert make_goals(command) == goals


@pytest.mark.parametrize(
    "first",
    ['[t](TARGET.md "a &amp;\nb") then', '![i](TARGET.md "a \\" q\nb") then'],
)
def test_decoded_inline_titles_still_count_their_lines(tmp_path: Path, first: str) -> None:
    page = f"{first}\n[bad](GONE.md)\n\n{first}\n[ok](GONE.md) <!-- docs-check: ignore -->\n"
    assert check.run(_tree(tmp_path, page)) == [
        "docs/PAGE.md:3: link target 'GONE.md' does not exist"
    ]


def test_a_backslash_in_a_comment_does_not_continue(tmp_path: Path) -> None:
    page = "```bash\necho ok # note \\\nmake removed\necho 'a # b\\\nc'\n```\n"
    assert check.run(_tree(tmp_path, page)) == [
        "docs/PAGE.md:3: `make removed` is not a Makefile target"
    ]


def test_an_entity_newline_in_a_title_adds_no_line(tmp_path: Path) -> None:
    page = '[t](TARGET.md "a&#10;b")\n[bad](GONE.md)\n'
    assert check.run(_tree(tmp_path, page)) == [
        "docs/PAGE.md:2: link target 'GONE.md' does not exist"
    ]


def test_an_inline_title_equal_to_a_definition_title_still_counts(tmp_path: Path) -> None:
    page = '[t](TARGET.md "a &amp;\nb") then\n[bad](GONE.md)\n\n[r]: TARGET.md "a &\nb"\n'
    assert check.run(_tree(tmp_path, page)) == [
        "docs/PAGE.md:3: link target 'GONE.md' does not exist"
    ]


def test_a_link_like_fragment_in_a_comment_does_not_hide_references(tmp_path: Path) -> None:
    page = "Inline <!-- [x](https://example.invalid/-->[broken][missing])\n"
    assert check.run(_tree(tmp_path, page)) == [
        "docs/PAGE.md:1: reference [missing] has no definition"
    ]


def test_a_make_line_inside_a_multi_line_quote_is_not_a_command(tmp_path: Path) -> None:
    page = "```bash\necho 'a\\\nmake removed\nb'\nmake gone\n```\n"
    assert check.run(_tree(tmp_path, page)) == [
        "docs/PAGE.md:5: `make gone` is not a Makefile target"
    ]


def test_a_quote_never_closed_in_a_block_is_not_shell(tmp_path: Path) -> None:
    page = "```text\nDon't run\nmake removed\n```\n"
    assert check.run(_tree(tmp_path, page)) == [
        "docs/PAGE.md:3: `make removed` is not a Makefile target"
    ]


def test_html_attributes_are_parsed_like_a_browser(tmp_path: Path) -> None:
    page = (
        '<img data-src="https://example.invalid/lazy.svg" src="GONE.svg">\n\n'
        "<img src=GONE2.svg alt=x>\n\n"
        '<img src="demo&#46;gif"> <a data-href="x" href="TARGET.md#options">o</a>\n'
    )
    root = _tree(tmp_path, page, {"docs/demo.gif": ""})
    assert check.run(root) == [
        "docs/PAGE.md:1: link target 'GONE.svg' does not exist",
        "docs/PAGE.md:3: link target 'GONE2.svg' does not exist",
    ]


def test_protocol_relative_urls_are_external(tmp_path: Path) -> None:
    page = (
        "![logo](//cdn.example.invalid/logo.svg) "
        '<img src="//cdn.example.invalid/a.svg"> [x](//example.invalid/page)\n'
    )
    assert check.run(_tree(tmp_path, page)) == []


def test_continued_shell_lines_are_one_command(tmp_path: Path) -> None:
    page = "```bash\nmake removed \\\n  VAR=1\nmake \\\n  removed lint\n```\n"
    assert check.run(_tree(tmp_path, page)) == [
        "docs/PAGE.md:2: `make removed` is not a Makefile target",
        "docs/PAGE.md:4: `make removed` is not a Makefile target",
    ]


@pytest.mark.parametrize(
    "command", ["echo ';' make tset", "echo \\; make tset", 'echo "a && make" tset']
)
def test_quoted_or_escaped_separators_are_words(tmp_path: Path, command: str) -> None:
    assert make_goals(command) == []
    assert check.run(_tree(tmp_path, f"Run `{command}`.\n")) == []


def test_brackets_in_urls_titles_and_comments_are_not_references(tmp_path: Path) -> None:
    page = (
        "[search](https://example.invalid/?filter=[a][b]) and\n"
        '[site](https://example.invalid/ "See [foo][bar]") and\n'
        "[nested](TARGET.md#options (title [x][y])) <!-- [c][d] --> <https://x.invalid/[e][f]>\n"
    )
    assert check.run(_tree(tmp_path, page)) == []


def test_html_anchors_in_code_or_comments_do_not_count(tmp_path: Path) -> None:
    target = (
        '# T\n\n`<a id="inline"></a>`\n\n```html\n<a id="fenced"></a>\n```\n\n'
        '<!-- <a id="commented"></a> -->\n\n<a id="real"></a>\n'
    )
    page = "[a](T.md#inline) [b](T.md#fenced) [c](T.md#commented) [d](T.md#real)\n"
    root = _tree(tmp_path, page, {"docs/T.md": target})
    assert [p.split(": ", 1)[1].split(" is ")[0] for p in check.run(root)] == [
        "anchor #commented",
        "anchor #fenced",
        "anchor #inline",
    ]


def test_explicit_heading_ids_follow_each_renderer(tmp_path: Path) -> None:
    page = (
        "[gh](TARGET.md#connection-options-options) [site](TARGET.md#options)\n"
        "[stripped](TARGET.md#connection-options)\n"
    )
    assert check.run(_tree(tmp_path, page)) == [
        (
            "docs/PAGE.md:2: anchor #connection-options is not a heading or anchor of "
            + "docs/TARGET.md; did you mean 'connection-options-options'?"
        )
    ]


def test_findings_use_the_line_of_each_occurrence(tmp_path: Path) -> None:
    page = (
        "Intro line\n[a](GONE.md) <!-- docs-check: ignore -->\nthen `a code\nspan` and\n"
        "[b](GONE.md) with [c][missing] and `make tset`.\n"
    )
    assert check.run(_tree(tmp_path, page)) == [
        "docs/PAGE.md:5: `make tset` is not a Makefile target; did you mean 'test'?",
        "docs/PAGE.md:5: link target 'GONE.md' does not exist",
        "docs/PAGE.md:5: reference [missing] has no definition",
    ]


def test_missing_or_empty_makefile_fails_closed(tmp_path: Path) -> None:
    root = _tree(tmp_path, "Run `make test`.\n")
    assert check.run(root) == []
    (root / "Makefile").write_text("# no targets\n", encoding="utf-8")
    assert check.run(root) == ["docs/PAGE.md:1: `make test` is not a Makefile target"]
    (root / "Makefile").unlink()
    assert check.run(root) == ["docs/PAGE.md:1: `make test` is not a Makefile target"]


def test_suppression_comment_on_the_line_or_the_line_before(tmp_path: Path) -> None:
    page = (
        "<!-- docs-check: ignore -->\n[a](GONE.md)\n\n[b](GONE.md) <!-- docs-check: ignore -->\n"
        "\n[c](GONE.md)\n"
    )
    assert check.run(_tree(tmp_path, page)) == [
        "docs/PAGE.md:6: link target 'GONE.md' does not exist"
    ]


def test_only_tracked_files_are_checked_in_git(tmp_path: Path) -> None:
    root = _tree(tmp_path, "# Page\n", {"untracked/NOTES.md": "[x](GONE.md)\n"})
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "add", "docs", "Makefile", "scripts"], check=True)
    assert check.run(root) == []
    assert [p.name for p in check.markdown_files(root)] == ["PAGE.md", "TARGET.md"]


def test_github_slug_matches_github_rendering() -> None:
    assert github_slug("Development Workflow (cubrid-lab org standard)") == (
        "development-workflow-cubrid-lab-org-standard"
    )
    assert github_slug("`ping(reconnect=True)` and #485") == "pingreconnecttrue-and-485"
    assert github_slug("한글 제목 (Korean)") == "한글-제목-korean"


@pytest.mark.parametrize(
    ("command", "goals"),
    [
        ("make test", ["test"]),
        ("make -j2 -C sub lint VAR=1 test # comment", ["lint", "test"]),
        ("cd x && make integration CUBRID_TEST_PORT=1 | tee log", ["integration"]),
        ("make -j 2 tset", ["tset"]),
        ("make --directory . tset", ["tset"]),
        ("make --directory docs tset", ["tset"]),
        ("make --directory=docs --jobs=4 tset", ["tset"]),
        ("make tset;make lint", ["tset", "lint"]),
        ("(make a)&&make b||make c", ["a", "b", "c"]),
        ("make sure", ["sure"]),
        ("cmake build", []),
        ("make 'unbalanced", []),
        ("make test VAR='value; make removed; tail'", ["test"]),
        ("make test > test.log", ["test"]),
        ("make test >> log 2>&1 | tee x", ["test"]),
        ("make test < in.txt", ["test"]),
        ("make test 2> err.txt", ["test"]),
        ("echo make test", []),
        ("VAR=1 make lint", ["lint"]),
    ],
)
def test_make_goals(command: str, goals: list[str]) -> None:
    assert make_goals(command) == goals


def test_parse_reports_heading_anchors(tmp_path: Path) -> None:
    path = tmp_path / "t.md"
    path.write_text(TARGET, encoding="utf-8")
    assert parse(path).anchors == {
        "target",
        "options",  # the site uses the explicit id
        "connection-options-options",  # GitHub keeps the literal {#options} text
        "legacy-anchor",
        "한글-제목",
        "same",
        "same-1",
        "same_1",
    }


def test_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _tree(tmp_path, "# Page\n\n[x](GONE.md)\n")
    assert check.main(["--root", str(root)]) == 1
    out = capsys.readouterr().out
    assert "docs/PAGE.md:3: link target 'GONE.md' does not exist" in out
    assert "<!-- docs-check: ignore -->" in out
    (root / "docs/PAGE.md").write_text("# Page\n", encoding="utf-8")
    assert check.main(["--root", str(root), str(root / "docs/PAGE.md")]) == 0
    assert "OK: 1 Markdown files" in capsys.readouterr().out
