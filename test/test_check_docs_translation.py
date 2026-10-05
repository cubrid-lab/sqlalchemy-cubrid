"""The Korean documentation structure check (#710)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "_check_docs_translation", ROOT / "scripts" / "check_docs_translation.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

ENGLISH = """# Title

## Section

### Part

#### Detail

| Name | Value |
|---|---|
| a | 1 |

```python
## not a heading
| not | a row |
```
"""
KOREAN = """# 제목

## 절

### 부분

#### 세부

| 이름 | 값 |
|---|---|
| a | 1 |

```python
## not a heading
| not | a row |
```
"""


def _tree(tmp_path: Path, english: str = ENGLISH, korean: str | None = KOREAN) -> Path:
    (tmp_path / "docs" / "ko").mkdir(parents=True)
    (tmp_path / "docs" / "GUIDE.md").write_text(english, encoding="utf-8")
    if korean is not None:
        (tmp_path / "docs" / "ko" / "GUIDE.md").write_text(korean, encoding="utf-8")
    return tmp_path


def test_structure_ignores_headings_and_rows_inside_code_blocks() -> None:
    assert MODULE.structure(ENGLISH) == {
        "h2": 1,
        "h3": 1,
        "h4": 1,
        "code blocks": 1,
        "table rows": 2,
    }


def test_a_fence_closes_only_with_its_own_marker() -> None:
    text = "~~~\n```\n## inside\n~~~\n## outside\n"
    assert MODULE.structure(text)["h2"] == 1
    assert MODULE.structure(text)["code blocks"] == 1


def test_matching_pair_passes(tmp_path: Path) -> None:
    assert MODULE.check(_tree(tmp_path), {}) == []


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        ("\n## Added\n", "h2 2 vs 1"),
        ("\n### Added\n", "h3 2 vs 1"),
        ("\n#### Added\n", "h4 2 vs 1"),
        ("\n```\ncode\n```\n", "code blocks 2 vs 1"),
        ("\n| b | 2 |\n", "table rows 3 vs 2"),
    ],
)
def test_each_kind_of_drift_is_reported(tmp_path: Path, extra: str, expected: str) -> None:
    problems = MODULE.check(_tree(tmp_path, english=ENGLISH + extra), {})
    assert problems == [f"GUIDE.md: English vs Korean: {expected}"]


def test_missing_korean_file_is_reported(tmp_path: Path) -> None:
    assert MODULE.check(_tree(tmp_path, korean=None), {}) == [
        "GUIDE.md: docs/ko/GUIDE.md is missing"
    ]


def test_an_exception_skips_a_missing_translation(tmp_path: Path) -> None:
    assert MODULE.check(_tree(tmp_path, korean=None), {"GUIDE.md": "English only"}) == []


def test_a_stale_exception_is_reported(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    assert MODULE.check(root, {"GUIDE.md": "English only"}) == [
        "GUIDE.md: listed as an exception but docs/ko/GUIDE.md exists"
    ]
    assert MODULE.check(root, {"GONE.md": "English only"}) == [
        "GONE.md: listed as an exception but docs/GONE.md does not exist"
    ]


def test_readme_translations_are_not_sources(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "docs" / "README.ko.md").write_text("# 읽어보기\n", encoding="utf-8")
    (root / "docs" / "CONTRIBUTING.ko.md").write_text("# 기여\n", encoding="utf-8")
    assert [path.name for path in MODULE.sources(root / "docs")] == ["GUIDE.md"]


def test_main_reports_and_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _tree(tmp_path, korean=None)
    assert MODULE.main(["--root", str(root)]) == 1
    assert "GUIDE.md: docs/ko/GUIDE.md is missing" in capsys.readouterr().out


def test_the_repository_documents_are_in_sync() -> None:
    assert MODULE.check(ROOT) == []
