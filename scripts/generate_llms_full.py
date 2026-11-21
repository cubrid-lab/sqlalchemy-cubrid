"""Generate the LLM-facing documentation artifacts.

* ``docs/llms-full.txt`` is the documentation Markdown files concatenated.
* ``llms.txt`` (repository root) is a byte-identical copy of the canonical
  ``docs/llms.txt`` index, which the docs site also serves as ``/llms.txt``.
  Edit ``docs/llms.txt`` only; CI fails if either artifact is stale.
"""

from __future__ import annotations

import pathlib

# Ordered list of doc files to include (exclude README translations, PRD.md, agent-playbook.md)
DOC_FILES: list[str] = [
    "index.md",
    "QUICKSTART.md",
    "LESSON_PREPARE.md",
    "LESSON_FIRST_QUERY.md",
    "LESSON_SAVE_ROW.md",
    "LESSON_TRANSACTIONS.md",
    "LESSON_FINISH.md",
    "CONNECTION.md",
    "ORM_COOKBOOK.md",
    "DML_EXTENSIONS.md",
    "TYPES.md",
    "ISOLATION_LEVELS.md",
    "ALEMBIC.md",
    "FEATURE_SUPPORT.md",
    "SUPPORT_MATRIX.md",
    "ARCHITECTURE.md",
    "PERFORMANCE.md",
    "TROUBLESHOOTING.md",
    "DEVELOPMENT.md",
    "CI_POLICY.md",
    "RELEASE_PLEASE_VALIDATION.md",
    "DRIVER_COMPAT.md",
]


def generate(repo_root: pathlib.Path) -> None:
    docs_dir = repo_root / "docs"
    output = docs_dir / "llms-full.txt"

    # Fail before writing anything: a renamed or moved page must not silently
    # produce an incomplete llms-full.txt.
    missing = [name for name in [*DOC_FILES, "llms.txt"] if not (docs_dir / name).is_file()]
    if missing:
        raise SystemExit(
            f"generate_llms_full: missing canonical docs under {docs_dir}: "
            f"{', '.join(missing)}. Restore the page(s) or update DOC_FILES in "
            "scripts/generate_llms_full.py."
        )

    sections = [(docs_dir / filename).read_text(encoding="utf-8").strip() for filename in DOC_FILES]

    _ = output.write_text("\n\n---\n\n".join(sections) + "\n", encoding="utf-8")
    print(f"Generated {output} ({output.stat().st_size:,} bytes)")

    root_index = repo_root / "llms.txt"
    _ = root_index.write_bytes((docs_dir / "llms.txt").read_bytes())
    print(f"Synced {root_index} from docs/llms.txt")


def main() -> None:
    generate(pathlib.Path(__file__).resolve().parent.parent)


if __name__ == "__main__":
    main()
