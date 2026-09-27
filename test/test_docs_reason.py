"""Docs exemption proofs use real event JSON and the workflow's inline Python."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = json.loads((ROOT / "test/fixtures/docs-reason-events.json").read_text())
WORKFLOW = ROOT / ".github/workflows/docs-sync.yml"


def workflow_python() -> str:
    text = WORKFLOW.read_text()
    return textwrap.dedent(text.split("python - <<'PY'\n", 1)[1].split("\n          PY", 1)[0])


class DocsReasonWorkflowTests(unittest.TestCase):
    def test_reviewed_physical_and_rendered_contexts(self) -> None:
        from scripts.check_docs_reason import _HTMLContext, has_docs_not_needed_reason

        link = "[A &amp; B](<blockquote>)\n"
        html = _HTMLContext(link)
        html.feed_literals(link, 1, 0, 0)
        self.assertIn("A & B", html.lines[1])
        self.assertFalse(html.blocked)
        for blank in (">", ">   "):
            self.assertTrue(
                has_docs_not_needed_reason(f"> quote\n{blank}\nDocs: not needed - tests only")
            )
        self.assertTrue(
            has_docs_not_needed_reason(
                "Ordinary prose.\nDocs: not needed - tests only\nMore prose."
            )
        )
        for separator in ("\u2028", "\u0085", "\f"):
            self.assertFalse(
                has_docs_not_needed_reason("Example" + separator + "Docs: not needed - hidden")
            )
        for tag in ("script", "style", "textarea", "iframe"):
            self.assertFalse(
                has_docs_not_needed_reason(f"<{tag}>\nDocs: not needed - hidden\n</{tag}>")
            )
            self.assertTrue(
                has_docs_not_needed_reason(
                    f"<{tag}>hidden</{tag}>\n\nDocs: not needed - tests only"
                )
            )
        for reason in ("\u200b", "\ufeff", "&#8203;"):
            self.assertFalse(has_docs_not_needed_reason("Docs: not needed - " + reason))
        self.assertFalse(has_docs_not_needed_reason("-\t> quoted\nDocs: not needed - hidden"))
        self.assertTrue(
            has_docs_not_needed_reason("[example](<blockquote>)\n\nDocs: not needed - tests only")
        )
        self.assertTrue(
            has_docs_not_needed_reason(
                "`unmatched\n# First\nDocs: not needed - tests only\n# Last `"
            )
        )
        for heading in ("####### invalid", "#no-space", "\\# escaped"):
            self.assertFalse(
                has_docs_not_needed_reason(
                    f"`unmatched\n{heading}\nDocs: not needed - hidden\nlast `"
                )
            )
        self.assertFalse(
            has_docs_not_needed_reason(
                "Docs: not needed - \u200b<reason> because docs are unchanged"
            )
        )
        self.assertTrue(has_docs_not_needed_reason("Docs: not needed - \u200btests only"))
        self.assertTrue(
            has_docs_not_needed_reason(
                "-\t~~~text\n\tDocs: not needed - hidden\n\t~~~\n\nDocs: not needed - tests only"
            )
        )
        for link in ("\\[example](<blockquote>)", "[example](<blockquote>"):
            self.assertFalse(
                has_docs_not_needed_reason(link + "\n\nDocs: not needed - hidden\n</blockquote>")
            )
        self.assertFalse(
            has_docs_not_needed_reason(
                '<blockquote title="[example](<blockquote>)">\nDocs: not needed - hidden\n</blockquote>'
            )
        )
        self.assertFalse(
            has_docs_not_needed_reason("[<blockquote>](<dest>)\n\nDocs: not needed - hidden")
        )
        self.assertTrue(
            has_docs_not_needed_reason(
                "<!-- [example](<blockquote>) -->\nDocs: not needed - tests only"
            )
        )

    def test_list_contained_examples_are_not_reasons(self) -> None:
        from scripts.check_docs_reason import has_docs_not_needed_reason

        for bullet in ("10.", "100."):
            indentation = " " * (len(bullet) + 1)
            self.assertTrue(
                has_docs_not_needed_reason(
                    f"{bullet} ~~~text\n{indentation}Docs: not needed - hidden\n{indentation}~~~\n\nDocs: not needed - tests only"
                )
            )
        self.assertFalse(
            has_docs_not_needed_reason("~~~text\n    ~~~\nDocs: not needed - hidden\n~~~")
        )
        for bullet in ("-", "+", "*", "1.", "2)"):
            with self.subTest(bullet=bullet):
                indentation = " " * (len(bullet) + 1)
                self.assertFalse(
                    has_docs_not_needed_reason(
                        f"{bullet} ```text\n{indentation}Docs: not needed - example\n{indentation}```"
                    )
                )
                self.assertFalse(
                    has_docs_not_needed_reason(f"{bullet} > quoted\n  Docs: not needed - example")
                )
                self.assertTrue(
                    has_docs_not_needed_reason(
                        f"{bullet} ```text\n{indentation}Docs: not needed - example\n{indentation}```\n\nDocs: not needed - tests only"
                    )
                )
                self.assertTrue(
                    has_docs_not_needed_reason(
                        f"{bullet} > quoted\n\nDocs: not needed - tests only"
                    )
                )
        self.assertFalse(
            has_docs_not_needed_reason("`literal\n- > quoted`\n  Docs: not needed - example")
        )
        self.assertTrue(
            has_docs_not_needed_reason(
                "`literal\n- ~~~text\n  <blockquote>\n  ~~~\n\nDocs: not needed - tests only\n`"
            )
        )
        self.assertFalse(
            has_docs_not_needed_reason("```text\n- ```\n  Docs: not needed - example\n```")
        )
        self.assertFalse(has_docs_not_needed_reason("- Docs: not needed - example"))
        for opener in ("<!--", '<blockquote title="example">'):
            close = "-->" if opener == "<!--" else "</blockquote>"
            self.assertTrue(
                has_docs_not_needed_reason(
                    f"{opener}\n- ```text\n{close}\nDocs: not needed - tests only"
                )
            )

    def test_unexpanded_placeholder_is_not_a_reason(self) -> None:
        from scripts.check_docs_reason import _placeholder, has_docs_not_needed_reason

        for unmatched in ("`<reason>``", "``<reason>`", "*<reason>**"):
            self.assertFalse(_placeholder(unmatched))
        self.assertFalse(has_docs_not_needed_reason("Docs: not needed - `<reason>`"))
        for wrapper in ("``", "*", "**", "***", "_", "__", "___"):
            self.assertFalse(
                has_docs_not_needed_reason(f"Docs: not needed - {wrapper}&lt;reason&gt;{wrapper}")
            )
        for heading in ("####### invalid", "#no-space", "\\# escaped"):
            self.assertFalse(
                has_docs_not_needed_reason(f"> quote\n{heading}\nDocs: not needed - hidden")
            )
        self.assertFalse(
            has_docs_not_needed_reason("> quote\n```text\nDocs: not needed - hidden\n```")
        )
        self.assertTrue(
            has_docs_not_needed_reason(
                "> quote\n```text\nhidden\n```\nDocs: not needed - tests only"
            )
        )
        self.assertTrue(
            has_docs_not_needed_reason("> quote\n# Details\nDocs: not needed - tests only")
        )
        self.assertFalse(
            has_docs_not_needed_reason("Docs: not needed - <reason> because docs are unchanged")
        )
        self.assertFalse(
            has_docs_not_needed_reason(
                "Docs: not needed - &lt;reason&gt; because docs are unchanged"
            )
        )
        self.assertTrue(
            has_docs_not_needed_reason("Docs: not needed - only `<reason>` fixture changed")
        )

    def test_inline_literal_html_does_not_change_outer_context(self) -> None:
        from scripts.check_docs_reason import has_docs_not_needed_reason

        self.assertTrue(
            has_docs_not_needed_reason(
                "Example `unmatched\n~~~html\n<blockquote>\n~~~\nDocs: not needed - tests only\n`"
            )
        )
        self.assertFalse(
            has_docs_not_needed_reason("`literal\n> quoted`\nDocs: not needed - hidden")
        )
        self.assertTrue(
            has_docs_not_needed_reason("`literal\n> quoted`\n\nDocs: not needed - tests only")
        )

        for literal in (
            "`<blockquote>`",
            "``<blockquote>`literal``",
            "\u005c<blockquote>",
            "\u005c\u005c\u005c<blockquote>",
            "`<pre>`",
            "`<code>`",
            "`Example\n<blockquote>\n`",
        ):
            with self.subTest(literal=literal):
                self.assertTrue(
                    has_docs_not_needed_reason(literal + "\n\nDocs: not needed - tests only")
                )
        for opener in ("`<blockquote>", "``<blockquote>`", "\u005c\u005c<blockquote>"):
            with self.subTest(opener=opener):
                self.assertFalse(
                    has_docs_not_needed_reason(
                        opener + "\nDocs: not needed - hidden\n</blockquote>"
                    )
                )
        self.assertFalse(has_docs_not_needed_reason("`Example\nDocs: not needed - hidden\n`"))
        self.assertTrue(
            has_docs_not_needed_reason(
                "Docs: not needed - only `<blockquote>` fixture text changed"
            )
        )
        self.assertFalse(
            has_docs_not_needed_reason(
                '<blockquote title="`literal`">\nDocs: not needed - hidden\n</blockquote>'
            )
        )
        self.assertTrue(
            has_docs_not_needed_reason(
                "<blockquote>\n`</blockquote>`\nDocs: not needed - tests only"
            )
        )
        self.assertTrue(
            has_docs_not_needed_reason(
                "`<blockquote>\n\nExample\n</blockquote>\nDocs: not needed - tests only\n`"
            )
        )
        self.assertTrue(
            has_docs_not_needed_reason(
                "\u005c`<blockquote>\nExample</blockquote>\nDocs: not needed - tests only\n`"
            )
        )
        self.assertFalse(
            has_docs_not_needed_reason(
                "`literal`<blockquote>\nDocs: not needed - hidden\n</blockquote>"
            )
        )
        self.assertFalse(
            has_docs_not_needed_reason(
                "``<blockquote>```\nDocs: not needed - hidden\n</blockquote>"
            )
        )

    def test_html_entities_do_not_create_physical_lines(self) -> None:
        from scripts.check_docs_reason import has_docs_not_needed_reason

        for reference in ("&NewLine;", "&#10;", "&#13;&#10;"):
            with self.subTest(reference=reference):
                self.assertFalse(
                    has_docs_not_needed_reason(
                        f"text{reference}Docs: not needed - hidden example\nDocs: not needed -"
                    )
                )
        self.assertFalse(has_docs_not_needed_reason("Docs: not needed - &lt;reason&gt;"))
        self.assertFalse(has_docs_not_needed_reason("Docs: not needed - &#10;"))
        self.assertTrue(
            has_docs_not_needed_reason("Docs: not needed - only A &amp; B fixture changed")
        )

    def test_html_context_reason_indentation_and_fence_info(self) -> None:
        from scripts.check_docs_reason import has_docs_not_needed_reason

        for literal in ("    <blockquote>", "    <pre>", "\t<code>"):
            with self.subTest(literal=literal):
                self.assertTrue(
                    has_docs_not_needed_reason(literal + "\n\nDocs: not needed - tests only")
                )
        self.assertTrue(
            has_docs_not_needed_reason(
                "<blockquote>\nExample\n    </blockquote>\nDocs: not needed - tests only"
            )
        )
        self.assertTrue(
            has_docs_not_needed_reason("<!--\nExample\n    -->\nDocs: not needed - tests only")
        )

        for tag in ("blockquote", "pre", "code"):
            with self.subTest(tag=tag):
                self.assertFalse(
                    has_docs_not_needed_reason(
                        f'<{tag.upper()} title="example">\nDocs: not needed - hidden\n</{tag}>'
                    )
                )
                self.assertFalse(
                    has_docs_not_needed_reason(
                        f"<{tag}><{tag}>\n</{tag}>\nDocs: not needed - hidden\n</{tag}>"
                    )
                )
                self.assertTrue(
                    has_docs_not_needed_reason(
                        f"<{tag}>\nExample\n</{tag}>\nDocs: not needed - tests only"
                    )
                )
        for indentation in ("", " ", "  ", "   "):
            self.assertTrue(
                has_docs_not_needed_reason(indentation + "Docs: not needed - tests only")
            )
        for indentation in ("    ", "\t", " \t"):
            self.assertFalse(
                has_docs_not_needed_reason(indentation + "Docs: not needed - code example")
            )
        self.assertTrue(has_docs_not_needed_reason("```foo`bar\nDocs: not needed - tests only"))
        self.assertFalse(has_docs_not_needed_reason("~~~foo`bar\nDocs: not needed - hidden\n~~~"))
        self.assertTrue(
            has_docs_not_needed_reason("```html\n<blockquote>\n```\nDocs: not needed - tests only")
        )
        self.assertFalse(
            has_docs_not_needed_reason("Docs: not needed - <!--\nhidden\n-->tests only")
        )
        self.assertFalse(
            has_docs_not_needed_reason(
                "<!--\nDocs: not needed - hidden -->Docs: not needed - inline example"
            )
        )
        self.assertFalse(
            has_docs_not_needed_reason(
                '<blockquote title="\nDocs: not needed - hidden">quoted</blockquote>Docs: not needed - inline example'
            )
        )
        self.assertFalse(
            has_docs_not_needed_reason("Docs: not needed - <span\n>\ntests only\n</span>")
        )
        self.assertTrue(
            has_docs_not_needed_reason("<!--\n```html\n-->\nDocs: not needed - tests only")
        )
        self.assertTrue(
            has_docs_not_needed_reason(
                "```html <blockquote>\n<pre>\n```\nDocs: not needed - tests only"
            )
        )
        self.assertTrue(
            has_docs_not_needed_reason(
                "<blockquote>\n```html\n</blockquote>\nDocs: not needed - tests only"
            )
        )
        self.assertFalse(
            has_docs_not_needed_reason("<blockquote/>\nDocs: not needed - hidden\n</blockquote>")
        )
        self.assertTrue(
            has_docs_not_needed_reason(
                "<blockquote>\n> Example\n</blockquote>\nDocs: not needed - tests only"
            )
        )
        self.assertTrue(
            has_docs_not_needed_reason("<!--\n> Example\n-->\nDocs: not needed - tests only")
        )

    def test_comment_reopening_and_fence_indentation(self) -> None:
        from scripts.check_docs_reason import has_docs_not_needed_reason

        self.assertFalse(
            has_docs_not_needed_reason(
                "<!-- first\n--> <!-- second\nDocs: not needed - hidden example\n-->"
            )
        )
        self.assertTrue(
            has_docs_not_needed_reason(
                "<!-- first\n--> <!-- second -->\nDocs: not needed - tests only"
            )
        )
        for indentation in ("", " ", "  ", "   "):
            with self.subTest(indentation=indentation):
                self.assertFalse(
                    has_docs_not_needed_reason(
                        indentation + "```text\nDocs: not needed - hidden example\n```"
                    )
                )
                self.assertTrue(
                    has_docs_not_needed_reason(
                        "```text\n" + indentation + "```\nDocs: not needed - tests only"
                    )
                )
        for indentation in ("    ", "     ", "\t"):
            with self.subTest(indentation=indentation):
                self.assertTrue(
                    has_docs_not_needed_reason(indentation + "```\nDocs: not needed - tests only")
                )
                self.assertFalse(
                    has_docs_not_needed_reason(
                        "```text\n" + indentation + "```\nDocs: not needed - hidden example\n```"
                    )
                )

    def test_mixed_fences_and_visible_reason(self) -> None:
        from scripts.check_docs_reason import has_docs_not_needed_reason

        for body in (
            "````text\n```\nDocs: not needed - tests only\n````",
            "~~~text\n```\nDocs: not needed - tests only\n~~~",
            "```text\n~~~\nDocs: not needed - tests only\n```",
            "```text\n```example\nDocs: not needed - tests only\n```",
            "<!--\n```\nDocs: not needed - tests only\n-->\n```",
            "Docs: not needed - <!-- placeholder -->",
            "> Example\nDocs: not needed - tests only",
        ):
            with self.subTest(body=body):
                self.assertFalse(has_docs_not_needed_reason(body))
        self.assertTrue(
            has_docs_not_needed_reason("````text\n~~~\n`````\nDocs: not needed - tests only")
        )
        self.assertTrue(has_docs_not_needed_reason("Docs: not needed - tests only <!-- note -->"))

    def test_event_json_exemptions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            git = temporary / "git"
            git.write_text(
                f"#!{sys.executable}\n"
                "import os, sys\n"
                "if sys.argv[1] == 'diff':\n"
                "    sys.stdout.write(os.environ['DOCS_TEST_CHANGED'])\n"
            )
            git.chmod(0o755)
            event = temporary / "event.json"
            env = {
                **os.environ,
                "PATH": str(temporary) + os.pathsep + os.environ.get("PATH", ""),
                "BASE_REF": "main",
                "EVENT_PATH": str(event),
                "IMPACT_GLOBS": "sqlalchemy_cubrid/**\npyproject.toml\nsetup.cfg\nsetup.py",
                "DOC_GLOBS": "CHANGELOG*\nREADME*\ndocs/**\nSUPPORT_MATRIX*",
                "IGNORE_GLOBS": "tests/**\n**/tests/**\n.github/**\n**/*.md\n**/*.rst\n**/*.txt",
                "DOCS_TEST_CHANGED": "sqlalchemy_cubrid/demo.py\n",
            }
            for case in FIXTURES:
                with self.subTest(case=case["id"]):
                    event.write_text(json.dumps(case["event"]))
                    run = subprocess.run(
                        [sys.executable, "-"],
                        input=workflow_python(),
                        cwd=ROOT,
                        env=env,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(
                        run.returncode == 0,
                        case["expected_docs_exemption"],
                        run.stdout + run.stderr,
                    )

    def test_body_is_json_data_and_translation_requires_existing_label(self) -> None:
        text = WORKFLOW.read_text()
        self.assertIn("json.load(_f)", text)
        self.assertNotIn("${{ github.event.pull_request.body }}", text)
        translation = text.split("  translation-sync:", 1)[1]
        self.assertIn(
            "!contains(github.event.pull_request.labels.*.name, 'translations-deferred')",
            translation,
        )
        self.assertNotIn("pull_request.body", translation)
        script = (ROOT / "scripts/check_translation_sync.py").read_text()
        self.assertIn('REQUIRED_LANGS = {"ko"}', script)
        self.assertNotIn('print("  Docs: not needed - <reason>")', text)
        self.assertIn("Replace the example explanation with your actual reason", text)
        template = (ROOT / ".github/PULL_REQUEST_TEMPLATE.md").read_text()
        self.assertNotIn("apply the `docs-not-needed` label", template)
        self.assertIn("request the maintainer-managed `docs-not-needed` label", template)


if __name__ == "__main__":
    unittest.main()
