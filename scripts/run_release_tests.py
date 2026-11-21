#!/usr/bin/env python3
"""Run the release-automation regression tests selected by ``ci.yml`` (#1154).

The test modules are the ``test/`` entries of the ``release_tooling`` paths
filter, plus any other ``test/test_*release*.py`` or ``test/test_*changelog*.py``
module. A listed path that no longer exists fails the run instead of being
skipped: a pull request that deletes or renames a listed module must edit
``ci.yml``, and that edit selects the full validation.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def release_tooling_paths(root: Path = ROOT) -> list[str]:
    jobs = yaml.safe_load((root / ".github/workflows/ci.yml").read_text())["jobs"]
    step = next(s for s in jobs["detect-changes"]["steps"] if s.get("id") == "filter")
    return list(yaml.safe_load(step["with"]["filters"])["release_tooling"])


def select(root: Path = ROOT) -> list[str]:
    listed = release_tooling_paths(root)
    missing = sorted(p for p in listed if not (root / p).is_file())
    if missing:
        raise SystemExit(
            "release_tooling paths in ci.yml do not exist: "
            + ", ".join(missing)
            + "; update the filter (this selects the full validation)"
        )
    tests = {p for p in listed if p.startswith("test/")}
    for pattern in ("test_*release*.py", "test_*changelog*.py"):
        tests.update(p.relative_to(root).as_posix() for p in (root / "test").glob(pattern))
    if not tests:
        raise SystemExit("no release automation tests selected")
    return sorted(tests)


def main() -> int:
    tests = select()
    return subprocess.run([sys.executable, "-m", "pytest", "-q", *tests], cwd=ROOT).returncode


if __name__ == "__main__":
    sys.exit(main())
