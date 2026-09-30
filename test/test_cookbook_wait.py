"""Offline tests for scripts/cookbook_wait.py (cookbook release verification).

A fake GitHub client replaces urllib and a fake clock replaces time; nothing
here reaches the network. Kept identical across pycubrid, sqlalchemy-cubrid and
cubrid-mcp-server.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "_cookbook_wait", ROOT / "scripts" / "cookbook_wait.py"
)
assert _spec is not None and _spec.loader is not None
cw = importlib.util.module_from_spec(_spec)
sys.modules["_cookbook_wait"] = cw
_spec.loader.exec_module(cw)

PACKAGE = "pycubrid"
VERSION = "1.8.0"
RID = "pycubrid-v1.8.0-123456789-1"
REPO = "cubrid-lab/cubrid-cookbook-python"


def title(request_id: str, package: str = PACKAGE, ref: str = f"v{VERSION}") -> str:
    return f"Release verification {package}@{ref} [request_id={request_id}]"


def run_entry(
    run_id: int, display_title: str, status: str = "completed", conclusion: str | None = "success"
) -> dict[str, Any]:
    return {
        "id": run_id,
        "display_title": display_title,
        "status": status,
        "conclusion": conclusion,
        "html_url": f"https://github.com/{REPO}/actions/runs/{run_id}",
    }


def report(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "schema_version": 1,
        "request_id": RID,
        "package": PACKAGE,
        "requested_version": VERSION,
        "installed_version": VERSION,
        "status": "success",
        "reasons": [],
    }
    data.update(overrides)
    return data


def archive(payload: Any, name: str = cw.REPORT_FILE) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        bundle.writestr(name, json.dumps(payload))
    return buffer.getvalue()


class FakeClient(cw.Client):
    """Serves successive run listings; artifacts by run id."""

    def __init__(
        self,
        listings: list[list[dict[str, Any]] | Exception],
        artifacts: dict[int, bytes] | None = None,
    ) -> None:
        self.listings = listings
        self.artifacts = artifacts or {}
        self.calls: list[str] = []
        self.posts: list[tuple[str, dict[str, Any]]] = []
        self.polls = 0

    def get_json(self, url: str) -> Any:
        self.calls.append(url)
        if "/workflows/smoke-test.yml/runs" in url:
            index = min(self.polls, len(self.listings) - 1)
            if "event=workflow_dispatch" in url:
                self.polls += 1
                return {"workflow_runs": []}
            listing = self.listings[index]
            if isinstance(listing, Exception):
                self.polls += 1
                raise listing
            return {"workflow_runs": listing}
        if "/artifacts?" in url:
            run_id = int(url.split("/runs/")[1].split("/")[0])
            if run_id not in self.artifacts:
                return {"artifacts": []}
            return {
                "artifacts": [
                    {
                        "id": run_id * 10,
                        "name": f"release-verification-{RID}",
                        "expired": False,
                        "created_at": "x",
                    }
                ]
            }
        raise AssertionError(url)

    def get_bytes(self, url: str) -> bytes:
        self.calls.append(url)
        artifact_id = int(url.split("/artifacts/")[1].split("/")[0])
        return self.artifacts[artifact_id // 10]

    def post_json(self, url: str, payload: dict[str, Any]) -> None:
        self.posts.append((url, payload))


class Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def wait(
    client: FakeClient, clock: Clock | None = None, timeout: float = 600, request_id: str = RID
) -> Any:
    clock = clock or Clock()
    return cw.wait(
        client,
        repo=REPO,
        package=PACKAGE,
        version=VERSION,
        request_id=request_id,
        since="",
        timeout=timeout,
        interval=30,
        clock=clock,
        sleep=clock.sleep,
    )


def test_success_after_waiting_for_the_run() -> None:
    client = FakeClient(
        [
            [],
            [run_entry(7, title(RID), status="in_progress", conclusion=None)],
            [run_entry(7, title(RID))],
        ],
        {7: archive(report())},
    )
    result = wait(client)
    assert result.status == "success"
    assert result.installed_version == VERSION
    assert result.run_url.endswith("/runs/7")
    assert any(url.endswith("/actions/artifacts/70/zip") for url in client.calls)


def test_ignores_unrelated_runs_and_other_request_ids() -> None:
    client = FakeClient(
        [
            [
                run_entry(1, " ", conclusion="failure"),  # push/schedule runs keep the default name
                run_entry(2, title("pycubrid-v1.8.0-999-1"), conclusion="failure"),
                run_entry(3, title("none"), conclusion="failure"),
                run_entry(
                    4, "ci: identify release verification runs by request id", conclusion="failure"
                ),
                run_entry(5, title(RID)),
            ]
        ],
        {5: archive(report())},
    )
    assert wait(client).status == "success"


@pytest.mark.parametrize(
    "other",
    [
        RID + "0",  # longer id sharing our prefix
        "x" + RID,  # id ending with ours
        RID[:-1],  # our id minus its last character
    ],
)
def test_prefix_collisions_never_match(other: str) -> None:
    client = FakeClient([[run_entry(2, title(other), conclusion="failure")]])
    result = wait(client, timeout=60)
    assert result.status == "failure"
    assert result.reason.startswith("timed out")


def test_timeout_is_a_failure() -> None:
    clock = Clock()
    client = FakeClient([[run_entry(7, title(RID), status="queued", conclusion=None)]])
    result = wait(client, clock, timeout=45 * 60)
    assert result.status == "failure"
    assert result.reason == "timed out after 45 min: run 7 is queued"
    assert clock.now >= 45 * 60
    assert set(clock.sleeps) == {30}


def test_failed_run_conclusion_fails() -> None:
    client = FakeClient([[run_entry(7, title(RID), conclusion="failure")]], {7: archive(report())})
    result = wait(client)
    assert (result.status, result.reason) == ("failure", "cookbook run concluded failure")


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        (
            {"status": "failure", "reasons": ["job smoke (11.4) failed"]},
            "status 'failure' (job smoke (11.4) failed)",
        ),
        ({"installed_version": "1.7.1"}, "installed_version '1.7.1' != '1.8.0'"),
        ({"installed_version": None}, "installed_version None != '1.8.0'"),
        ({"requested_version": "1.7.1"}, "requested_version '1.7.1' != '1.8.0'"),
        ({"package": "sqlalchemy-cubrid"}, "package 'sqlalchemy-cubrid' != 'pycubrid'"),
        ({"request_id": "someone-else-1"}, "request_id 'someone-else-1'"),
    ],
)
def test_report_must_prove_the_requested_release(overrides: dict[str, Any], expected: str) -> None:
    client = FakeClient([[run_entry(7, title(RID))]], {7: archive(report(**overrides))})
    result = wait(client)
    assert result.status == "failure"
    assert expected in result.reason


def test_missing_or_unreadable_artifact_fails_after_retries() -> None:
    client = FakeClient([[run_entry(7, title(RID))]])
    result = wait(client, timeout=60)
    assert result.status == "failure"
    assert "has no artifact release-verification-" in result.reason
    client = FakeClient([[run_entry(7, title(RID))]], {7: archive(report(), name="other.json")})
    assert "no readable release-verification.json" in wait(client, timeout=60).reason


def test_two_runs_with_our_request_id_fail_closed() -> None:
    client = FakeClient([[run_entry(7, title(RID)), run_entry(8, title(RID))]])
    result = wait(client)
    assert result.status == "failure"
    assert result.reason.startswith("ambiguous")


def test_transient_api_errors_are_retried() -> None:
    client = FakeClient(
        [cw.ApiError("HTTP 502", 502), [run_entry(7, title(RID))]],
        {7: archive(report())},
    )
    assert wait(client).status == "success"


# main(): dispatch, token handling and outputs --------------------------------


def outputs(path: Path) -> dict[str, str]:
    return dict(line.split("=", 1) for line in path.read_text().splitlines())


@pytest.fixture
def github_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "out"
    path.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(path))
    return path


ARGS = ["--package", PACKAGE, "--version", VERSION, "--request-id", RID]


def test_missing_dispatch_token_is_incomplete(github_output: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cw, "Client", lambda token="": pytest.fail("no request without a token"))
    assert cw.main(ARGS, env={"GITHUB_TOKEN": "read"}) == 2
    out = outputs(github_output)
    assert out["status"] == "incomplete"
    assert "COOKBOOK_DISPATCH_TOKEN is not configured" in out["reason"]
    assert out["run_url"] == ""
    assert "::warning::cookbook verification incomplete" in capsys.readouterr().out


def test_dispatch_sends_the_contract_payload(github_output: Path, monkeypatch) -> None:
    client = FakeClient([[run_entry(7, title(RID))]], {7: archive(report())})
    tokens: list[str] = []

    def make(token: str = "") -> FakeClient:
        tokens.append(token)
        return client

    monkeypatch.setattr(cw, "Client", make)
    assert (
        cw.main(
            [*ARGS, "--interval", "0"], env={"COOKBOOK_DISPATCH_TOKEN": "pat", "GITHUB_TOKEN": "gt"}
        )
        == 0
    )
    assert tokens == ["pat", "gt"]  # the PAT is used for the dispatch only
    assert client.posts == [
        (
            f"https://api.github.com/repos/{REPO}/dispatches",
            {
                "event_type": "upstream-released",
                "client_payload": {"package": PACKAGE, "ref": "v1.8.0", "request_id": RID},
            },
        )
    ]
    assert all("created=%3E%3D" in url for url in client.calls if "/runs?" in url)
    assert outputs(github_output)["status"] == "success"


def test_dispatch_error_fails(github_output: Path, monkeypatch) -> None:
    class Refusing(FakeClient):
        def post_json(self, url: str, payload: dict[str, Any]) -> None:
            raise cw.ApiError("POST returned HTTP 401", 401)

    monkeypatch.setattr(cw, "Client", lambda token="": Refusing([[]]))
    assert cw.main(ARGS, env={"COOKBOOK_DISPATCH_TOKEN": "bad"}) == 1
    assert outputs(github_output)["reason"] == "dispatch failed: POST returned HTTP 401"


def test_no_dispatch_waits_for_an_existing_request(github_output: Path, monkeypatch) -> None:
    client = FakeClient([[run_entry(7, title(RID))]], {7: archive(report())})
    monkeypatch.setattr(cw, "Client", lambda token="": client)
    assert cw.main([*ARGS, "--no-dispatch"], env={}) == 0
    assert client.posts == []


@pytest.mark.parametrize(
    "args",
    [
        ["--package", PACKAGE, "--version", "1.8", "--request-id", RID],
        ["--package", PACKAGE, "--version", VERSION, "--request-id", "short"],
        ["--package", PACKAGE, "--version", VERSION, "--request-id", "bad id with spaces"],
        ["--package", "../x", "--version", VERSION, "--request-id", RID],
        ["--package", PACKAGE],
    ],
)
def test_usage_errors(args: list[str], github_output: Path) -> None:
    assert cw.main(args, env={"COOKBOOK_DISPATCH_TOKEN": "pat"}) == 3
    assert github_output.read_text() == ""


def test_redirected_download_never_forwards_the_token(monkeypatch: pytest.MonkeyPatch) -> None:
    import email.message
    import urllib.error

    headers = email.message.Message()
    headers["Location"] = "https://storage.example.invalid/blob?sig=x"
    seen: list[Any] = []

    def api_open(request: Any, timeout: float) -> Any:
        seen.append(request)
        raise urllib.error.HTTPError(request.full_url, 302, "Found", headers, None)

    def storage_open(request: Any, timeout: float) -> Any:
        seen.append(request)
        return io.BytesIO(b"zip bytes")

    client = cw.Client("secret-token")
    monkeypatch.setattr(client._opener, "open", api_open)
    monkeypatch.setattr(cw.urllib.request, "urlopen", storage_open)
    assert (
        client.get_bytes("https://api.github.com/repos/o/r/actions/artifacts/1/zip") == b"zip bytes"
    )
    assert seen[0].get_header("Authorization") == "Bearer secret-token"
    assert seen[1].full_url == "https://storage.example.invalid/blob?sig=x"
    assert seen[1].get_header("Authorization") is None


def test_rejected_token_fails_without_waiting() -> None:
    clock = Clock()
    client = FakeClient([cw.ApiError("GET runs returned HTTP 401", 401)])
    result = wait(client, clock)
    assert (result.status, result.reason) == ("failure", "GET runs returned HTTP 401")
    assert clock.sleeps == []


def test_outputs_are_single_line(github_output: Path) -> None:
    cw.write_outputs(cw.Result("failure", "line one\nstatus=success", RID).outputs())
    assert outputs(github_output)["status"] == "failure"
    assert outputs(github_output)["reason"] == "line one status=success"
