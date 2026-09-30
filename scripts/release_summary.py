#!/usr/bin/env python3
"""Render the single run summary of release.yml and name its final state.

The ``summary`` job always runs and passes ``toJSON(needs)`` in ``NEEDS``. This
script renders one Markdown table (SHA, tag, version, artifact hashes, matrix
result, PyPI URLs, cookbook verification and final state) to
``$GITHUB_STEP_SUMMARY`` and stdout. The final state separates failures before
publishing (nothing was tagged or uploaded) from "published; post-release
verification failed". The cookbook verification is ``success`` only when the
called smoke-test workflow (``verify-cookbook``) and ``require-cookbook``
succeeded and its outputs report ``status == success`` with
``installed_version == requested_version`` == the released version; a failed,
cancelled or skipped call once verification was due (after a successful
publish, a successful dry-run build, or for verify-only) is a failure, never a
verified release.

Environment: ``NEEDS`` (required), ``PACKAGE``, ``GITHUB_REPOSITORY``,
``GITHUB_SERVER_URL``, ``GITHUB_RUN_ID``. Always exits 0 unless ``NEEDS`` is
unreadable (the failing job already fails the run). Standard library only;
kept identical across pycubrid, sqlalchemy-cubrid and cubrid-mcp-server.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

PRE_PUBLISH = ("consistency", "matrix", "build")


def job(needs: dict[str, Any], name: str) -> tuple[str, dict[str, str]]:
    entry = needs.get(name) or {}
    return str(entry.get("result") or "not run"), dict(entry.get("outputs") or {})


def verification_due(needs: dict[str, Any]) -> bool:
    """Mirror the ``verify-cookbook`` condition: a published release, a successful
    dry-run build, or verify-only. A call skipped or cancelled after that point is
    a failed verification, not one that was never due."""
    _, detect = job(needs, "detect")
    if detect.get("verify") != "true":
        return False
    if job(needs, "publish")[0] == "success":
        return True
    return detect.get("publish") != "true" and (
        detect.get("mode") == "verify-only" or job(needs, "build")[0] == "success"
    )


def verification(needs: dict[str, Any]) -> tuple[str, str]:
    """Return (``success`` | ``failure`` | ``not run``, reason) for the cookbook."""
    result, outputs = job(needs, "verify-cookbook")
    if result in ("skipped", "not run") and not outputs and not verification_due(needs):
        return "not run", ""
    require_result, _ = job(needs, "require-cookbook")
    version = job(needs, "detect")[1].get("version", "")
    status = outputs.get("status", "")
    requested = outputs.get("requested_version", "")
    installed = outputs.get("installed_version", "")
    problems: list[str] = []
    if result != "success":
        problems.append(f"called workflow {result}")
    if status != "success":
        problems.append(f"status {status or 'missing'}")
    if not installed or installed != requested or requested != version:
        problems.append(
            f"requested {requested or '-'}, installed {installed or '-'}, released {version or '-'}"
        )
    if require_result != "success":
        problems.append(f"require-cookbook {require_result}")
    if problems:
        return "failure", "; ".join(problems)
    return "success", f"installed {installed} == requested {requested}"


def final_state(needs: dict[str, Any]) -> str:
    detect_result, detect = job(needs, "detect")
    if detect_result != "success":
        return f"failed in detect ({detect_result}); nothing was published"
    if detect.get("release") != "true":
        return f"no release: {detect.get('reason', '')}".rstrip(": ")
    mode = detect.get("mode", "")
    status, _ = verification(needs)
    if mode == "verify-only":
        return f"verification only of {detect.get('tag')}: {status}"
    for name in PRE_PUBLISH:
        result, _ = job(needs, name)
        if result != "success":
            prefix = "dry run failed" if mode == "dry-run" else "failed before publish"
            return f"{prefix} in {name} ({result}); nothing was tagged, released or uploaded"
    if mode == "dry-run":
        return f"dry run passed; nothing published; cookbook verification {status}"
    publish_result, _ = job(needs, "publish")
    if publish_result != "success":
        return (
            f"publish {publish_result}; the tag, draft Release or PyPI upload may be partial "
            "(recover with `gh run rerun <run-id> --failed`)"
        )
    if status == "success":
        return "published and verified"
    return f"published; post-release verification {'failed' if status == 'failure' else status}"


def hashes_cell(build: dict[str, str]) -> str:
    try:
        hashes = json.loads(build.get("sha256", "") or "{}")
    except ValueError:
        return "unreadable"
    if not isinstance(hashes, dict) or not hashes:
        return "-"
    return "<br>".join(f"`{name}` `{digest}`" for name, digest in sorted(hashes.items()))


def render(needs: dict[str, Any], env: dict[str, str]) -> str:
    package = env.get("PACKAGE", "")
    server = env.get("GITHUB_SERVER_URL", "https://github.com")
    repo = env.get("GITHUB_REPOSITORY", "")
    _, detect = job(needs, "detect")
    version, tag, sha = detect.get("version", ""), detect.get("tag", ""), detect.get("sha", "")
    mode = detect.get("mode", "")
    published = job(needs, "publish")[0] == "success"
    matrix_result, _ = job(needs, "matrix")
    _, build = job(needs, "build")
    status, reason = verification(needs)
    _, verify = job(needs, "verify-cookbook")
    artifact = verify.get("artifact", "")
    cookbook = (
        f"{status}"
        + (f": {reason}" if reason else "")
        + (f" (report artifact `{artifact}`)" if artifact else "")
    )
    rows = [
        ("Final state", f"**{final_state(needs)}**"),
        ("Mode", mode or "-"),
        ("Decision", detect.get("reason", "") or "-"),
        ("Commit", f"[`{sha}`]({server}/{repo}/commit/{sha})" if sha else "-"),
        ("Version", version or "-"),
        ("Tag", f"{tag} ({detect.get('tag_state', 'unknown')} before this run)" if tag else "-"),
        ("Full matrix", matrix_result),
        ("Build", job(needs, "build")[0]),
        ("Artifact SHA-256", hashes_cell(build)),
        ("Publish", job(needs, "publish")[0]),
        (
            "PyPI",
            f"https://pypi.org/project/{package}/{version}/"
            if published and package and version
            else "-",
        ),
        ("GitHub Release", f"{server}/{repo}/releases/tag/{tag}" if published and tag else "-"),
        ("Cookbook verification", cookbook),
    ]
    lines = ["## Release summary", "", "| Item | Value |", "| --- | --- |"]
    lines += [f"| {key} | {str(value).replace('|', '/')} |" for key, value in rows]
    return "\n".join(lines) + "\n"


def main(env: dict[str, str] | None = None) -> int:
    env = dict(os.environ) if env is None else env
    try:
        needs = json.loads(env.get("NEEDS", ""))
    except ValueError:
        print("::error::NEEDS is not the JSON of the needs context")
        return 1
    if not isinstance(needs, dict):
        print("::error::NEEDS is not the JSON of the needs context")
        return 1
    text = render(needs, env)
    print(text)
    print(f"::notice::{final_state(needs)}")
    path = env.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
