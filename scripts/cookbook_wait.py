#!/usr/bin/env python3
"""Dispatch the cookbook release verification and wait for that exact run.

Implements the upstream side of the "Release verification contract" in
cubrid-lab/cubrid-cookbook-python (CONTRIBUTING.md):

1. ``repository_dispatch`` with ``event_type: upstream-released`` and
   ``client_payload {"package", "ref": "vX.Y.Z", "request_id"}``, sent with
   ``COOKBOOK_DISPATCH_TOKEN``. Without that token nothing is dispatched and the
   result is **incomplete**, never success. ``--no-dispatch`` waits for a run
   that was already requested with ``--request-id`` (for example a manual
   ``gh workflow run smoke-test.yml ... -f request_id=<id>``).
2. Poll ``actions/workflows/smoke-test.yml/runs`` (``repository_dispatch`` and
   ``workflow_dispatch`` events) and select the one run whose ``display_title``
   contains the exact token ``[request_id=<id>]``. Unrelated runs and runs of
   other request ids are ignored; two runs with the same token fail closed.
3. Require the run conclusion ``success`` and the artifact
   ``release-verification-<id>`` whose ``release-verification.json`` reports
   ``status == "success"`` and ``installed_version == requested_version ==
   --version`` for ``--package``.

Polling is bounded (``--timeout``, default 45 minutes); a timeout is a failure.
Transient API errors while polling are retried until the deadline. Reads use
``GITHUB_TOKEN`` (artifact downloads need an authenticated request even for a
public repository); only the dispatch uses ``COOKBOOK_DISPATCH_TOKEN``.

Writes ``status`` (``success``/``failure``/``incomplete``), ``reason``,
``request_id``, ``run_url`` and ``installed_version`` to ``$GITHUB_OUTPUT``.
Exit codes: 0 success, 1 failure, 2 incomplete, 3 usage error.

Standard library only; kept identical across pycubrid, sqlalchemy-cubrid and
cubrid-mcp-server (see RELEASING.md).
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

API = "https://api.github.com"
DEFAULT_REPO = "cubrid-lab/cubrid-cookbook-python"
WORKFLOW = "smoke-test.yml"
EVENTS = ("repository_dispatch", "workflow_dispatch")
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
PACKAGE_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
REPORT_FILE = "release-verification.json"
TIMEOUT_SECONDS = 30

SUCCESS, FAILURE, INCOMPLETE = "success", "failure", "incomplete"
EXIT_CODES = {SUCCESS: 0, FAILURE: 1, INCOMPLETE: 2}


class ApiError(Exception):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass
class Result:
    status: str
    reason: str
    request_id: str
    run_url: str = ""
    installed_version: str = ""

    def outputs(self) -> dict[str, str]:
        return {
            "status": self.status,
            "reason": self.reason,
            "request_id": self.request_id,
            "run_url": self.run_url,
            "installed_version": self.installed_version,
        }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


class Client:
    """Minimal GitHub REST client (urllib). Never forwards a token off api.github.com."""

    def __init__(self, token: str = "") -> None:
        self.token = token
        self._opener = urllib.request.build_opener(_NoRedirect)

    def _request(self, method: str, url: str, body: bytes | None = None) -> bytes:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cubrid-lab-cookbook-wait",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=TIMEOUT_SECONDS) as response:
                return bytes(response.read())
        except urllib.error.HTTPError as exc:
            location = exc.headers.get("Location") if exc.headers else None
            if exc.code in (301, 302, 303, 307, 308) and location:
                # Signed storage URL: fetch without the GitHub token.
                plain = urllib.request.Request(
                    location, headers={"User-Agent": headers["User-Agent"]}
                )
                try:
                    with urllib.request.urlopen(plain, timeout=TIMEOUT_SECONDS) as response:  # nosec B310
                        return bytes(response.read())
                except (urllib.error.URLError, OSError) as inner:
                    raise ApiError(f"GET {location.split('?')[0]} failed: {inner}") from inner
            raise ApiError(f"{method} {url} returned HTTP {exc.code}", exc.code) from exc
        except (urllib.error.URLError, OSError) as exc:
            raise ApiError(f"{method} {url} failed: {exc}") from exc

    def get_json(self, url: str) -> Any:
        body = self._request("GET", url)
        try:
            return json.loads(body)
        except ValueError as exc:
            raise ApiError(f"GET {url} returned invalid JSON") from exc

    def get_bytes(self, url: str) -> bytes:
        return self._request("GET", url)

    def post_json(self, url: str, payload: dict[str, Any]) -> None:
        self._request("POST", url, json.dumps(payload).encode())


def token_for(request_id: str) -> str:
    return f"[request_id={request_id}]"


def dispatch(client: Client, repo: str, package: str, version: str, request_id: str) -> None:
    client.post_json(
        f"{API}/repos/{repo}/dispatches",
        {
            "event_type": "upstream-released",
            "client_payload": {"package": package, "ref": f"v{version}", "request_id": request_id},
        },
    )


def matching_runs(runs: list[dict[str, Any]], request_id: str) -> list[dict[str, Any]]:
    token = token_for(request_id)
    unique: dict[Any, dict[str, Any]] = {}
    for run in runs:
        if token in str(run.get("display_title", "")):
            unique[run.get("id")] = run
    return list(unique.values())


def list_runs(client: Client, repo: str, since: str) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for event in EVENTS:
        query = {"event": event, "per_page": "100"}
        if since:
            query["created"] = f">={since}"
        data = client.get_json(
            f"{API}/repos/{repo}/actions/workflows/{WORKFLOW}/runs?{urllib.parse.urlencode(query)}"
        )
        if not isinstance(data, dict) or not isinstance(data.get("workflow_runs"), list):
            raise ApiError("unexpected workflow runs payload")
        runs.extend(data["workflow_runs"])
    return runs


def read_report(client: Client, repo: str, run_id: Any, request_id: str) -> dict[str, Any]:
    name = f"release-verification-{request_id}"
    data = client.get_json(
        f"{API}/repos/{repo}/actions/runs/{run_id}/artifacts?"
        + urllib.parse.urlencode({"name": name, "per_page": "100"})
    )
    artifacts = [
        a
        for a in (data.get("artifacts", []) if isinstance(data, dict) else [])
        if a.get("name") == name and not a.get("expired")
    ]
    if not artifacts:
        raise ApiError(f"run has no artifact {name}")
    newest = max(artifacts, key=lambda a: str(a.get("created_at", "")))
    archive = client.get_bytes(f"{API}/repos/{repo}/actions/artifacts/{newest['id']}/zip")
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            report = json.loads(bundle.read(REPORT_FILE))
    except (zipfile.BadZipFile, KeyError, ValueError) as exc:
        raise ApiError(f"artifact {name} has no readable {REPORT_FILE}: {exc}") from exc
    if not isinstance(report, dict):
        raise ApiError(f"{REPORT_FILE} is not a JSON object")
    return report


def validate_report(report: dict[str, Any], package: str, version: str, request_id: str) -> str:
    """Return "" when the report proves the requested release, else the reason."""
    problems = []
    if report.get("request_id") != request_id:
        problems.append(f"request_id {report.get('request_id')!r} != {request_id!r}")
    if report.get("package") != package:
        problems.append(f"package {report.get('package')!r} != {package!r}")
    if report.get("requested_version") != version:
        problems.append(f"requested_version {report.get('requested_version')!r} != {version!r}")
    if report.get("status") != SUCCESS:
        reasons = report.get("reasons") or []
        problems.append(
            f"status {report.get('status')!r} ({'; '.join(map(str, reasons)) or 'no reasons'})"
        )
    if report.get("installed_version") != version:
        problems.append(f"installed_version {report.get('installed_version')!r} != {version!r}")
    return ", ".join(problems)


def wait(
    client: Client,
    *,
    repo: str,
    package: str,
    version: str,
    request_id: str,
    since: str,
    timeout: float,
    interval: float,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> Result:
    deadline = clock() + timeout
    last = "no matching run yet"
    while True:
        try:
            runs = matching_runs(list_runs(client, repo, since), request_id)
            if len(runs) > 1:
                ids = ", ".join(str(r.get("id")) for r in runs)
                return Result(
                    FAILURE,
                    f"ambiguous: several runs carry request_id {request_id} ({ids})",
                    request_id,
                )
            if runs:
                run = runs[0]
                url = str(run.get("html_url", ""))
                if run.get("status") != "completed":
                    last = f"run {run.get('id')} is {run.get('status')}"
                else:
                    conclusion = run.get("conclusion")
                    if conclusion != SUCCESS:
                        return Result(
                            FAILURE, f"cookbook run concluded {conclusion}", request_id, url
                        )
                    report = read_report(client, repo, run.get("id"), request_id)
                    problem = validate_report(report, package, version, request_id)
                    installed = str(report.get("installed_version") or "")
                    if problem:
                        return Result(
                            FAILURE, f"verification report: {problem}", request_id, url, installed
                        )
                    return Result(
                        SUCCESS,
                        f"cookbook installed {package}=={installed} from PyPI",
                        request_id,
                        url,
                        installed,
                    )
        except ApiError as exc:
            last = str(exc)
            if exc.status == 401:
                # A rejected token does not recover by waiting.
                return Result(FAILURE, last, request_id)
            print(f"::warning::{last}")
        if clock() >= deadline:
            return Result(FAILURE, f"timed out after {timeout / 60:.0f} min: {last}", request_id)
        print(f"waiting: {last}")
        sleep(interval)


def run(args: argparse.Namespace, env: dict[str, str]) -> Result:
    request_id = args.request_id
    if not args.dispatch:
        # Only wait for a run requested elsewhere; no dispatch token is needed.
        client = Client(env.get("GITHUB_TOKEN", ""))
        return wait(
            client,
            repo=args.repo,
            package=args.package,
            version=args.version,
            request_id=request_id,
            since="",
            timeout=args.timeout,
            interval=args.interval,
        )
    dispatch_token = env.get("COOKBOOK_DISPATCH_TOKEN", "")
    if not dispatch_token:
        return Result(
            INCOMPLETE,
            "COOKBOOK_DISPATCH_TOKEN is not configured; the cookbook verification was not requested",
            request_id,
        )
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=2)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    try:
        dispatch(Client(dispatch_token), args.repo, args.package, args.version, request_id)
    except ApiError as exc:
        return Result(FAILURE, f"dispatch failed: {exc}", request_id)
    print(f"dispatched upstream-released {args.package} v{args.version} request_id={request_id}")
    return wait(
        Client(env.get("GITHUB_TOKEN", "")),
        repo=args.repo,
        package=args.package,
        version=args.version,
        request_id=request_id,
        since=since,
        timeout=args.timeout,
        interval=args.interval,
    )


def write_outputs(outputs: dict[str, str]) -> None:
    # One line per output: a newline in a value could forge another output.
    lines = [f"{key}={' '.join(value.splitlines())}" for key, value in outputs.items()]
    print("\n".join(lines))
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None, env: dict[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--package", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--no-dispatch", dest="dispatch", action="store_false")
    parser.add_argument("--timeout", type=float, default=45 * 60)
    parser.add_argument("--interval", type=float, default=30)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 3 if exc.code else 0
    if not PACKAGE_RE.match(args.package) or not VERSION_RE.match(args.version):
        print(f"::error::invalid package {args.package!r} or version {args.version!r}")
        return 3
    if not REQUEST_ID_RE.match(args.request_id) or "/" not in args.repo:
        print(f"::error::invalid request_id {args.request_id!r} or repo {args.repo!r}")
        return 3
    result = run(args, dict(os.environ) if env is None else env)
    level = {SUCCESS: "notice", INCOMPLETE: "warning"}.get(result.status, "error")
    print(f"::{level}::cookbook verification {result.status}: {result.reason}")
    write_outputs(result.outputs())
    return EXIT_CODES[result.status]


if __name__ == "__main__":
    sys.exit(main())
