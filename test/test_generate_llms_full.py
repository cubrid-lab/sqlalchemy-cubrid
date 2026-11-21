"""Offline tests for scripts/generate_llms_full.py: canonical page handling."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "generate_llms_full", ROOT / "scripts/generate_llms_full.py"
)
assert _SPEC is not None and _SPEC.loader is not None
gen = importlib.util.module_from_spec(_SPEC)
sys.modules["generate_llms_full"] = gen
_SPEC.loader.exec_module(gen)


def _make_repo(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    for name in gen.DOC_FILES:
        (docs / name).write_text(f"# {name}\n\nBody of {name}.\n", encoding="utf-8")
    (docs / "llms.txt").write_text("# index\n- canonical\n", encoding="utf-8")
    return tmp_path


def test_concatenates_canonical_docs_in_listed_order(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    gen.generate(repo)

    sections = (repo / "docs" / "llms-full.txt").read_text(encoding="utf-8").split("\n\n---\n\n")
    assert [section.splitlines()[0] for section in sections] == [
        f"# {name}" for name in gen.DOC_FILES
    ]


def test_excludes_pages_outside_the_canonical_list(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    (repo / "docs" / "README.ko.md").write_text("translation", encoding="utf-8")
    (repo / "docs" / "PRD.md").write_text("product notes", encoding="utf-8")

    gen.generate(repo)

    generated = (repo / "docs" / "llms-full.txt").read_text(encoding="utf-8")
    assert "translation" not in generated
    assert "product notes" not in generated


def test_root_llms_txt_is_a_byte_identical_copy_of_the_docs_index(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    (repo / "llms.txt").write_text("stale root index", encoding="utf-8")

    gen.generate(repo)

    assert (repo / "llms.txt").read_bytes() == (repo / "docs" / "llms.txt").read_bytes()


def test_missing_listed_page_fails_before_overwriting_any_output(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    output = repo / "docs" / "llms-full.txt"
    output.write_text("previous full text", encoding="utf-8")
    (repo / "llms.txt").write_text("previous root index", encoding="utf-8")
    missing = gen.DOC_FILES[2]
    (repo / "docs" / missing).unlink()

    with pytest.raises(SystemExit) as excinfo:
        gen.generate(repo)

    assert missing in str(excinfo.value)
    assert "DOC_FILES" in str(excinfo.value)
    assert output.read_text(encoding="utf-8") == "previous full text"
    assert (repo / "llms.txt").read_text(encoding="utf-8") == "previous root index"


def test_missing_docs_index_fails_before_overwriting_any_output(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    output = repo / "docs" / "llms-full.txt"
    output.write_text("previous full text", encoding="utf-8")
    (repo / "docs" / "llms.txt").unlink()

    with pytest.raises(SystemExit) as excinfo:
        gen.generate(repo)

    assert "llms.txt" in str(excinfo.value)
    assert output.read_text(encoding="utf-8") == "previous full text"


def test_every_listed_page_exists_in_this_repository() -> None:
    """The real docs/ tree satisfies the canonical-page check."""
    missing = [name for name in gen.DOC_FILES if not (ROOT / "docs" / name).is_file()]

    assert missing == []
