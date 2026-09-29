#!/usr/bin/env python3
"""Fail closed when a release file already on PyPI differs from the verified build.

``publish-pypi.yml`` runs this in the ``deploy`` job, right before
``pypa/gh-action-pypi-publish`` (which no longer uses ``skip-existing``). For
each wheel/sdist in ``dist/`` the PyPI JSON API of the exact release
(``https://pypi.org/pypi/<project>/<version>/json``) decides:

* release not on PyPI (HTTP 404) or filename not in it -> keep the file, upload it
* filename on PyPI with the same SHA-256 -> remove it from ``dist/``: an earlier
  attempt of this same run already uploaded these exact bytes (partial-upload
  recovery through ``gh run rerun <run-id> --failed``)
* filename on PyPI with a different SHA-256 -> fail
* PyPI serves a file for this release that the verified build did not produce
  -> fail (the release must be a subset of ``dist/``)
* PyPI unreachable, an unexpected HTTP status, or an ambiguous response -> fail

Transient errors (HTTP 5xx, connection errors, timeouts, truncated responses)
are retried with a short backoff; when every attempt fails, the guard fails.
Only an actual HTTP 404 response means "not published"; an error never does.

Nothing is removed unless every file passes. The script writes
``upload=true`` (files left to upload) or ``upload=false`` (every file is
already on PyPI byte for byte) to ``$GITHUB_OUTPUT``; the workflow skips the
publish step on ``upload=false``.

Standard library only. Kept identical across pycubrid, sqlalchemy-cubrid and
cubrid-mcp-server; see RELEASING.md (Recovery).
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PYPI_JSON_URL = "https://pypi.org/pypi/{project}/{version}/json"
TIMEOUT_SECONDS = 30
RETRY_DELAYS_SECONDS = (2, 5)  # sleep before the 2nd and 3rd attempt
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PROJECT = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?$")
_VERSION = re.compile(r"^[0-9][A-Za-z0-9.+!-]*$")


class GuardError(Exception):
    """The guard cannot prove that publishing ``dist/`` is safe."""


def normalize(name: str) -> str:
    """PEP 503 project-name normalization."""
    return re.sub(r"[-_.]+", "-", name).lower()


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_files(dist: Path, project: str, version: str) -> dict[str, str]:
    """Return ``{filename: sha256}`` for the wheel/sdist files in ``dist``."""
    if not dist.is_dir():
        raise GuardError(f"{dist} is not a directory")
    prefix = f"{normalize(project).replace('-', '_')}-{version}"
    files: dict[str, str] = {}
    for path in sorted(dist.iterdir()):
        name = path.name
        if not path.is_file() or not (
            (name.startswith(prefix + "-") and name.endswith(".whl")) or name == prefix + ".tar.gz"
        ):
            raise GuardError(f"unexpected entry in {dist}: {name} (expected {prefix} wheel/sdist)")
        files[name] = sha256_of(path)
    if not files:
        raise GuardError(f"{dist} contains no distribution files")
    return files


def published_files(project: str, version: str) -> dict[str, str]:
    """Return ``{filename: sha256}`` of the files PyPI serves for this release.

    An empty mapping means PyPI has no such release (HTTP 404). Every other
    failure raises GuardError so that the caller fails closed.
    """
    url = PYPI_JSON_URL.format(
        project=urllib.parse.quote(project, safe=""),
        version=urllib.parse.quote(version, safe=""),
    )
    request = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "pypi-duplicate-guard"}
    )
    body = None
    error = ""
    for attempt, delay in enumerate((0, *RETRY_DELAYS_SECONDS), start=1):
        if delay:
            time.sleep(delay)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                body = response.read()
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return {}
            if exc.code < 500:
                raise GuardError(f"GET {url} returned HTTP {exc.code}") from exc
            error = f"HTTP {exc.code}"
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            error = f"{type(exc).__name__}: {exc}"
        print(f"::warning::GET {url} attempt {attempt} failed: {error}")
    if body is None:
        raise GuardError(
            f"GET {url} failed after {1 + len(RETRY_DELAYS_SECONDS)} attempts: {error}"
        )

    try:
        data = json.loads(body)
        info = data["info"]
        entries = data["urls"]
    except (ValueError, TypeError, KeyError) as exc:
        raise GuardError(f"GET {url} returned an unexpected payload: {exc!r}") from exc
    if not isinstance(info, dict) or not isinstance(entries, list):
        raise GuardError(f"GET {url} returned an unexpected payload shape")
    if normalize(str(info.get("name", ""))) != normalize(project) or info.get("version") != version:
        raise GuardError(
            f"GET {url} described {info.get('name')!r} {info.get('version')!r}, "
            f"not {project} {version}"
        )

    files: dict[str, str] = {}
    for entry in entries:
        filename = entry.get("filename") if isinstance(entry, dict) else None
        digests = entry.get("digests") if isinstance(entry, dict) else None
        sha256 = digests.get("sha256") if isinstance(digests, dict) else None
        if not isinstance(filename, str) or not isinstance(sha256, str):
            raise GuardError(f"GET {url} listed a file without a filename or sha256: {entry!r}")
        if not _SHA256.match(sha256):
            raise GuardError(f"GET {url} listed {filename} with a malformed sha256 {sha256!r}")
        if filename in files:
            raise GuardError(f"GET {url} listed {filename} twice")
        files[filename] = sha256
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", required=True, help="PyPI project name")
    parser.add_argument("--version", required=True, help="release version, without the v")
    parser.add_argument("--dist", type=Path, default=Path("dist"), help="default: dist")
    args = parser.parse_args(argv)

    try:
        if not _PROJECT.match(args.project) or not _VERSION.match(args.version):
            raise GuardError(f"invalid project/version: {args.project!r} {args.version!r}")
        local = local_files(args.dist, args.project, args.version)
        published = published_files(args.project, args.version)
    except GuardError as exc:
        print(f"::error::PyPI duplicate guard: {exc}")
        return 1

    identical = []
    mismatched = []
    for filename, sha256 in local.items():
        if filename not in published:
            print(f"not on PyPI yet, will upload: {filename} sha256={sha256}")
        elif published[filename] == sha256:
            identical.append(filename)
            print(f"already on PyPI with the same sha256, will skip: {filename} sha256={sha256}")
        else:
            mismatched.append(filename)
            print(
                f"::error::{filename} is already on PyPI with sha256={published[filename]}, "
                f"but the verified build has sha256={sha256}"
            )
    unverified = sorted(set(published) - set(local))
    for filename in unverified:
        print(f"::error::PyPI also serves {filename}, which this verified build did not produce")

    if mismatched or unverified:
        print(
            "::error::PyPI already serves files for this release that this verified build "
            "does not match. PyPI filenames are immutable: recover a partial upload only with "
            "`gh run rerun <run-id> --failed` of the run that uploaded it (see RELEASING.md)."
        )
        return 1

    for filename in identical:
        (args.dist / filename).unlink()
    upload = len(identical) < len(local)
    if identical:
        print(
            f"::notice::{len(identical)} of {len(local)} file(s) already on PyPI with the same "
            "sha256 were removed from the upload set (partial-upload recovery)"
        )
    if not upload:
        print("::notice::Every file is already on PyPI with the same sha256; nothing to upload")

    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"upload={'true' if upload else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
