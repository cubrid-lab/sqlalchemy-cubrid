#!/usr/bin/env python3
"""Fail unless a directory holds exactly the files a JSON digest map names.

``publish-pypi.yml`` runs this in the ``publish`` job before the tag step, once
for ``dist/`` against the ``build`` job output ``sha256`` and once for
``release-meta/`` against ``meta_sha256``. A finished job's outputs cannot be
changed by a later job of the run, while any job of the run (the cookbook
candidate and post-publication calls included) could replace a same-named
artifact. So the bytes uploaded to PyPI and attached to the GitHub Release are
checked against the digests ``build`` recorded, which are also the digests the
cookbook candidate verification checked.

The map is read from the environment variable named by ``--expected-env`` (it
never passes through shell code) and must be a non-empty JSON object whose keys
are plain file names and whose values are 64-character lowercase hex SHA-256
digests. The directory must hold only regular files (no subdirectory, no
symlink), its file names must equal the map keys exactly, and every file's
SHA-256 must equal its entry. Any other case, or an OS error while reading,
exits 1 with an ``::error::``.

Standard library only. Kept identical across pycubrid, sqlalchemy-cubrid and
cubrid-mcp-server; see RELEASING.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,199}$")


class VerifyError(Exception):
    """The directory does not match the expected digest map."""


def parse_expected(raw: str | None) -> dict[str, str]:
    if not raw:
        raise VerifyError("the expected digest map is empty or missing")
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise VerifyError(f"the expected digest map is not JSON: {exc}") from exc
    if not isinstance(data, dict) or not data:
        raise VerifyError("the expected digest map must be a non-empty JSON object")
    for name, digest in data.items():
        if not isinstance(name, str) or not _NAME.match(name) or ".." in name:
            raise VerifyError(f"not a plain file name: {name!r}")
        if not isinstance(digest, str) or not _SHA256.match(digest):
            raise VerifyError(f"not a lowercase hex SHA-256 for {name}: {digest!r}")
    return data


def verify(directory: Path, expected: dict[str, str]) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise VerifyError(f"{directory} is not a directory")
    found: dict[str, Path] = {}
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file():
            raise VerifyError(f"{path} is not a regular file")
        found[path.name] = path
    missing = sorted(set(expected) - set(found))
    extra = sorted(set(found) - set(expected))
    if missing or extra:
        raise VerifyError(
            f"file set differs from the build output: missing {missing}, extra {extra}"
        )
    for name in sorted(expected):
        actual = hashlib.sha256(found[name].read_bytes()).hexdigest()
        if actual != expected[name]:
            raise VerifyError(f"SHA-256 of {name} is {actual}, expected {expected[name]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", required=True, type=Path, help="directory to check")
    parser.add_argument(
        "--expected-env", required=True, help="environment variable holding the JSON digest map"
    )
    args = parser.parse_args(argv)
    try:
        expected = parse_expected(os.environ.get(args.expected_env))
        verify(args.dir, expected)
    except (VerifyError, OSError) as exc:
        print(f"::error::{args.dir}: {exc}")
        return 1
    print(f"{args.dir}: {len(expected)} files match {args.expected_env}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
