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
    "DRIVER_COMPAT.md",
]


def main() -> None:
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    docs_dir = repo_root / "docs"
    output = docs_dir / "llms-full.txt"

    sections: list[str] = []
    for filename in DOC_FILES:
        filepath = docs_dir / filename
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8").strip()
            sections.append(content)

    _ = output.write_text("\n\n---\n\n".join(sections) + "\n", encoding="utf-8")
    print(f"Generated {output} ({output.stat().st_size:,} bytes)")

    root_index = repo_root / "llms.txt"
    _ = root_index.write_bytes((docs_dir / "llms.txt").read_bytes())
    print(f"Synced {root_index} from docs/llms.txt")


if __name__ == "__main__":
    main()
