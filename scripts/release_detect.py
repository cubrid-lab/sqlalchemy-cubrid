#!/usr/bin/env python3
"""Decide from verifiable repository facts whether a commit is a release.

``release.yml`` runs this in its ``detect`` job. The decision never depends on
a PR title or commit message, only on git objects:

``--mode push`` (every push to main, ``--sha`` = the pushed commit)
    A release when all of these hold, otherwise "no release":

    * ``__version__`` in the version file differs from the first parent,
    * the new version is ``MAJOR.MINOR.PATCH``,
    * CHANGELOG.md at the commit has a dated ``## [X.Y.Z] - YYYY-MM-DD`` section,
    * tag ``vX.Y.Z`` is absent, or already points at this commit (a rerun of an
      interrupted release resumes; the workflow never moves a tag).

``--mode resume`` (recovery dispatch; ``--version`` required)
    Finish an interrupted release: tag ``vX.Y.Z`` must exist, its commit must be
    on main, and the version file and CHANGELOG at that commit must match.
    Never a new version. Any mismatch is an error, not "no release".

``--mode verify-only`` (recovery dispatch; ``--version`` required)
    Re-run only the cookbook verification of an already tagged version, with
    the same tag/main/version/CHANGELOG checks as ``resume``. Publishes nothing.

``--mode dry-run`` (dispatch on any branch; ``--sha`` = the dispatched commit)
    Rehearse consistency, matrix, build and cookbook verification of the version
    already in the version file at ``--sha`` (``--version`` must match it).
    Publishes nothing; the tag state is only reported.

Outputs (``$GITHUB_OUTPUT`` and stdout): ``release``, ``build``, ``publish``,
``verify`` (``true``/``false``), ``mode``, ``version``, ``tag``, ``sha``,
``tag_state`` (``absent``/``same``/``different``/``unknown``) and ``reason``.

Exit codes: 0 decided (including "no release"), 1 a recovery or dry-run request
that fails its checks, 2 usage error. Standard library only; kept identical
across pycubrid, sqlalchemy-cubrid and cubrid-mcp-server (see RELEASING.md).
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess  # nosec B404 - fixed git argv, no shell
import sys
from dataclasses import dataclass, field

VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MODES = ("push", "resume", "verify-only", "dry-run")


class DetectError(Exception):
    """A recovery or dry-run request that must fail instead of being skipped."""


@dataclass
class Decision:
    mode: str
    sha: str
    version: str = ""
    tag_state: str = "unknown"
    reason: str = ""
    build: bool = False
    publish: bool = False
    verify: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def tag(self) -> str:
        return f"v{self.version}" if self.version else ""

    @property
    def release(self) -> bool:
        return self.build or self.publish or self.verify

    def outputs(self) -> dict[str, str]:
        def flag(value: bool) -> str:
            return "true" if value else "false"

        return {
            "release": flag(self.release),
            "build": flag(self.build),
            "publish": flag(self.publish),
            "verify": flag(self.verify),
            "mode": self.mode,
            "version": self.version,
            "tag": self.tag,
            "sha": self.sha,
            "tag_state": self.tag_state,
            "reason": self.reason,
        }


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 B607 - fixed git argv
        ["git", *args], capture_output=True, text=True, check=False
    )


def resolve_commit(rev: str) -> str:
    result = git("rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}")
    return result.stdout.strip() if result.returncode == 0 else ""


def read_at(sha: str, path: str) -> str | None:
    result = git("show", f"{sha}:{path}")
    return result.stdout if result.returncode == 0 else None


def parse_version(source: str | None) -> str:
    """Return the string assigned to ``__version__`` (AST, no import), or ""."""
    if source is None:
        return ""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "__version__"
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)
                ):
                    return node.value.value
    return ""


def has_dated_section(changelog: str | None, version: str) -> bool:
    if not changelog:
        return False
    header = re.compile(
        rf"^## \[{re.escape(version)}\] - [0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}\s*$", re.MULTILINE
    )
    return header.search(changelog) is not None


def remote_tag_commit(remote: str, tag: str) -> str:
    """Return the commit ``refs/tags/<tag>`` points at on ``remote``, or ""."""
    ref = f"refs/tags/{tag}"
    result = git("ls-remote", "--tags", remote, ref, f"{ref}^{{}}")
    if result.returncode != 0:
        raise DetectError(f"git ls-remote {remote} failed: {result.stderr.strip()}")
    direct = peeled = ""
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        if parts[1] == ref:
            direct = parts[0]
        elif parts[1] == f"{ref}^{{}}":
            peeled = parts[0]
    return peeled or direct


def is_on_main(sha: str, main_ref: str) -> bool:
    return git("merge-base", "--is-ancestor", sha, main_ref).returncode == 0


def tag_state(tag_commit: str, sha: str) -> str:
    if not tag_commit:
        return "absent"
    return "same" if tag_commit == sha else "different"


def detect_push(sha: str, version_file: str, changelog: str, remote: str) -> Decision:
    decision = Decision(mode="push", sha=sha)
    version = parse_version(read_at(sha, version_file))
    parent = resolve_commit(f"{sha}^1")
    previous = parse_version(read_at(parent, version_file)) if parent else ""
    if not version:
        decision.reason = f"no __version__ found in {version_file}"
        return decision
    if not VERSION_RE.match(version):
        # Never echo an unvalidated string into $GITHUB_OUTPUT.
        decision.reason = "__version__ is not MAJOR.MINOR.PATCH"
        if version != previous:
            decision.warnings.append(decision.reason)
        return decision
    decision.version = version
    if version == previous:
        decision.reason = f"__version__ unchanged ({version}) compared with the first parent"
        return decision
    if not has_dated_section(read_at(sha, changelog), version):
        decision.reason = (
            f"__version__ changed to {version} but {changelog} has no dated "
            f"'## [{version}] - YYYY-MM-DD' section"
        )
        decision.warnings.append(decision.reason)
        return decision
    decision.tag_state = tag_state(remote_tag_commit(remote, f"v{version}"), sha)
    if decision.tag_state == "different":
        decision.reason = f"tag v{version} already exists at another commit; tags are never moved"
        decision.warnings.append(decision.reason)
        return decision
    decision.build = decision.publish = decision.verify = True
    decision.reason = (
        f"release v{version}"
        if decision.tag_state == "absent"
        else f"resume v{version} (tag already at this commit)"
    )
    return decision


def detect_existing(
    mode: str, version: str, version_file: str, changelog: str, remote: str, main_ref: str
) -> Decision:
    tag = f"v{version}"
    sha = remote_tag_commit(remote, tag)
    if not sha:
        raise DetectError(
            f"{mode}: tag {tag} does not exist; a new version is only released by merging a release PR"
        )
    decision = Decision(mode=mode, sha=sha, version=version, tag_state="same")
    if not resolve_commit(sha):
        raise DetectError(
            f"{mode}: tag {tag} commit {sha} is not available locally (fetch-depth 0?)"
        )
    if not is_on_main(sha, main_ref):
        raise DetectError(f"{mode}: tag {tag} commit {sha} is not contained in {main_ref}")
    actual = parse_version(read_at(sha, version_file))
    if actual != version:
        raise DetectError(
            f"{mode}: {version_file} at {tag} has __version__ {actual!r}, not {version}"
        )
    if not has_dated_section(read_at(sha, changelog), version):
        raise DetectError(f"{mode}: {changelog} at {tag} has no dated '## [{version}]' section")
    if mode == "resume":
        decision.build = decision.publish = decision.verify = True
        decision.reason = f"resume v{version} at the existing tag"
    else:
        decision.verify = True
        decision.reason = f"re-run the cookbook verification of v{version} only"
    return decision


def detect_dry_run(
    sha: str, version: str, version_file: str, changelog: str, remote: str
) -> Decision:
    actual = parse_version(read_at(sha, version_file))
    if actual != version:
        raise DetectError(
            f"dry-run: {version_file} at {sha} has __version__ {actual!r}, not {version}"
        )
    if not has_dated_section(read_at(sha, changelog), version):
        raise DetectError(f"dry-run: {changelog} at {sha} has no dated '## [{version}]' section")
    decision = Decision(mode="dry-run", sha=sha, version=version, build=True, verify=True)
    decision.tag_state = tag_state(remote_tag_commit(remote, f"v{version}"), sha)
    decision.reason = f"dry run of v{version}: nothing is tagged, released or uploaded"
    return decision


def detect(args: argparse.Namespace) -> Decision:
    if args.mode in ("resume", "verify-only", "dry-run") and not VERSION_RE.match(
        args.version or ""
    ):
        raise DetectError(f"{args.mode}: --version must be MAJOR.MINOR.PATCH, got {args.version!r}")
    if args.mode in ("push", "dry-run"):
        sha = resolve_commit(args.sha or "")
        if not SHA_RE.match(args.sha or "") or sha != args.sha:
            raise DetectError(f"--sha {args.sha!r} is not a full commit SHA present in this clone")
        if args.mode == "push":
            return detect_push(sha, args.version_file, args.changelog, args.remote)
        return detect_dry_run(sha, args.version, args.version_file, args.changelog, args.remote)
    return detect_existing(
        args.mode, args.version, args.version_file, args.changelog, args.remote, args.main_ref
    )


def write_outputs(outputs: dict[str, str]) -> None:
    # One line per output: a newline in a value could forge another output.
    lines = [f"{key}={' '.join(value.splitlines())}" for key, value in outputs.items()]
    print("\n".join(lines))
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mode", choices=MODES, default="push")
    parser.add_argument("--sha", default="")
    parser.add_argument("--version", default="")
    parser.add_argument("--version-file", required=True)
    parser.add_argument("--changelog", default="CHANGELOG.md")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--main-ref", default="origin/main")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        decision = detect(args)
    except DetectError as exc:
        print(f"::error::{exc}")
        return 1
    for warning in decision.warnings:
        print(f"::warning::{warning}")
    write_outputs(decision.outputs())
    return 0


if __name__ == "__main__":
    sys.exit(main())
