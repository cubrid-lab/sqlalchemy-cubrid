"""Offline regressions for scripts/pypi_duplicate_guard.py and its publish wiring.

urllib is mocked; nothing here reaches PyPI. Kept identical across pycubrid,
sqlalchemy-cubrid and cubrid-mcp-server.
"""

from __future__ import annotations

import hashlib
import http.client
import importlib.util
import io
import json
import re
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "publish-pypi.yml"
_spec = importlib.util.spec_from_file_location(
    "_pypi_duplicate_guard", ROOT / "scripts" / "pypi_duplicate_guard.py"
)
assert _spec is not None and _spec.loader is not None
guard = importlib.util.module_from_spec(_spec)
sys.modules["_pypi_duplicate_guard"] = guard
_spec.loader.exec_module(guard)

PROJECT = "example-pkg"
VERSION = "1.2.3"
WHEEL = "example_pkg-1.2.3-py3-none-any.whl"
SDIST = "example_pkg-1.2.3.tar.gz"
CONTENT = {WHEEL: b"verified wheel bytes", SDIST: b"verified sdist bytes"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    path = tmp_path / "dist"
    path.mkdir()
    for name, data in CONTENT.items():
        (path / name).write_bytes(data)
    return path


@pytest.fixture
def output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "github_output"
    path.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(path))
    return path


def release(files: dict[str, str], name: str = PROJECT, version: str = VERSION) -> bytes:
    return json.dumps(
        {
            "info": {"name": name, "version": version},
            "urls": [{"filename": f, "digests": {"sha256": h}} for f, h in files.items()],
        }
    ).encode()


@pytest.fixture(autouse=True)
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    slept: list[float] = []
    monkeypatch.setattr(guard.time, "sleep", slept.append)
    return slept


class TruncatedResponse(io.BytesIO):
    def read(self, *args: object) -> bytes:
        raise http.client.IncompleteRead(b"{", 100)


def serve(monkeypatch: pytest.MonkeyPatch, *results: object) -> list[str]:
    """Answer successive requests with ``results``; the last one repeats."""
    requested: list[str] = []

    def fake_urlopen(request, timeout=None):
        requested.append(request.full_url)
        assert timeout == guard.TIMEOUT_SECONDS
        result = results[min(len(requested), len(results)) - 1]
        if isinstance(result, BaseException):
            raise result
        if isinstance(result, io.BytesIO):
            return result
        return io.BytesIO(result)

    monkeypatch.setattr(guard.urllib.request, "urlopen", fake_urlopen)
    return requested


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://pypi.org/x", code, "status", {}, None)


def run(dist: Path) -> int:
    return guard.main(["--project", PROJECT, "--version", VERSION, "--dist", str(dist)])


def remaining(dist: Path) -> set[str]:
    return {p.name for p in dist.iterdir()}


def test_clean_publication_404_uploads_everything(dist: Path, output: Path, monkeypatch) -> None:
    requested = serve(monkeypatch, http_error(404))
    assert run(dist) == 0
    assert requested == [f"https://pypi.org/pypi/{PROJECT}/{VERSION}/json"]
    assert remaining(dist) == set(CONTENT)
    assert output.read_text() == "upload=true\n"


def test_release_without_our_filenames_uploads_everything(dist, output, monkeypatch) -> None:
    serve(monkeypatch, release({}))
    assert run(dist) == 0
    assert remaining(dist) == set(CONTENT)
    assert output.read_text() == "upload=true\n"


def test_same_file_retry_removes_only_identical_file(dist, output, monkeypatch, capsys) -> None:
    serve(monkeypatch, release({WHEEL: sha(CONTENT[WHEEL])}))
    assert run(dist) == 0
    assert remaining(dist) == {SDIST}
    assert output.read_text() == "upload=true\n"
    assert "1 of 2 file(s) already on PyPI" in capsys.readouterr().out


def test_every_file_identical_skips_upload(dist, output, monkeypatch) -> None:
    serve(monkeypatch, release({name: sha(data) for name, data in CONTENT.items()}))
    assert run(dist) == 0
    assert remaining(dist) == set()
    assert output.read_text() == "upload=false\n"


def test_different_file_duplicate_fails_and_keeps_dist(dist, output, monkeypatch, capsys) -> None:
    # The sdist matches, but the wheel differs: nothing may be removed.
    serve(monkeypatch, release({WHEEL: sha(b"other bytes"), SDIST: sha(CONTENT[SDIST])}))
    assert run(dist) == 1
    assert remaining(dist) == set(CONTENT)
    assert output.read_text() == ""
    assert f"::error::{WHEEL} is already on PyPI" in capsys.readouterr().out


def test_published_file_missing_from_dist_fails(dist, output, monkeypatch, capsys) -> None:
    # The release on PyPI must be a subset of the verified dist/: a file this
    # build did not produce (e.g. a platform wheel) would stay unverified.
    extra = "example_pkg-1.2.3-cp312-cp312-manylinux_2_17_x86_64.whl"
    serve(monkeypatch, release({WHEEL: sha(CONTENT[WHEEL]), extra: sha(b"unverified")}))
    assert run(dist) == 1
    assert remaining(dist) == set(CONTENT)
    assert output.read_text() == ""
    assert f"::error::PyPI also serves {extra}" in capsys.readouterr().out


TRANSIENT = [
    pytest.param(lambda: urllib.error.URLError("name resolution"), id="URLError"),
    pytest.param(lambda: TimeoutError("timed out"), id="timeout"),
    pytest.param(lambda: ConnectionResetError("reset"), id="reset"),
    pytest.param(lambda: http_error(500), id="HTTP500"),
    pytest.param(lambda: http_error(503), id="HTTP503"),
    pytest.param(TruncatedResponse, id="IncompleteRead"),
]


@pytest.mark.parametrize("failure", TRANSIENT)
def test_network_error_fails_closed_after_retries(
    dist, output, monkeypatch, sleeps, capsys, failure
) -> None:
    requested = serve(monkeypatch, failure(), failure(), failure())
    assert run(dist) == 1
    assert len(requested) == 3
    assert sleeps == list(guard.RETRY_DELAYS_SECONDS)
    assert remaining(dist) == set(CONTENT)
    assert output.read_text() == ""
    assert "::error::PyPI duplicate guard: GET" in capsys.readouterr().out


@pytest.mark.parametrize("failure", TRANSIENT)
def test_transient_error_is_retried(dist, output, monkeypatch, sleeps, failure) -> None:
    requested = serve(monkeypatch, failure(), release({WHEEL: sha(CONTENT[WHEEL])}))
    assert run(dist) == 0
    assert len(requested) == 2
    assert sleeps == [guard.RETRY_DELAYS_SECONDS[0]]
    assert remaining(dist) == {SDIST}
    assert output.read_text() == "upload=true\n"


@pytest.mark.parametrize("code", [400, 403, 410, 429])
def test_other_http_status_fails_without_retry(dist, output, monkeypatch, sleeps, code) -> None:
    requested = serve(monkeypatch, http_error(code), http_error(404))
    assert run(dist) == 1
    assert len(requested) == 1
    assert sleeps == []
    assert remaining(dist) == set(CONTENT)
    assert output.read_text() == ""


def test_only_a_real_404_means_unpublished(dist, output, monkeypatch) -> None:
    # Errors never turn into "upload everything"; a later genuine 404 does.
    requested = serve(monkeypatch, http_error(503), http_error(404))
    assert run(dist) == 0
    assert len(requested) == 2
    assert output.read_text() == "upload=true\n"


@pytest.mark.parametrize(
    "body",
    [
        b"<html>not json</html>",
        b"[]",
        json.dumps({"info": {"name": PROJECT, "version": VERSION}}).encode(),
        release({}, version="1.2.4"),
        release({}, name="other-pkg"),
        release({WHEEL: "not-a-sha256"}),
        json.dumps(
            {"info": {"name": PROJECT, "version": VERSION}, "urls": [{"filename": WHEEL}]}
        ).encode(),
        json.dumps(
            {
                "info": {"name": PROJECT, "version": VERSION},
                "urls": [{"filename": WHEEL, "digests": {"sha256": sha(b"x")}}] * 2,
            }
        ).encode(),
    ],
)
def test_ambiguous_response_fails_closed(dist, output, monkeypatch, body) -> None:
    serve(monkeypatch, body)
    assert run(dist) == 1
    assert remaining(dist) == set(CONTENT)
    assert output.read_text() == ""


def test_project_name_is_normalized(dist, output, monkeypatch) -> None:
    serve(monkeypatch, release({WHEEL: sha(CONTENT[WHEEL])}, name="Example_Pkg"))
    assert run(dist) == 0
    assert remaining(dist) == {SDIST}


@pytest.mark.parametrize(
    "extra", ["notes.txt", "other_pkg-1.2.3.tar.gz", "example_pkg-1.2.4.tar.gz"]
)
def test_unexpected_dist_entry_fails_before_network(dist, output, monkeypatch, extra) -> None:
    (dist / extra).write_bytes(b"x")
    requested = serve(monkeypatch, http_error(404))
    assert run(dist) == 1
    assert requested == []
    assert output.read_text() == ""


def test_empty_or_missing_dist_fails(tmp_path, output, monkeypatch) -> None:
    serve(monkeypatch, http_error(404))
    (tmp_path / "empty").mkdir()
    assert run(tmp_path / "empty") == 1
    assert run(tmp_path / "missing") == 1
    assert output.read_text() == ""


def test_invalid_project_or_version_is_rejected(dist, output, monkeypatch) -> None:
    requested = serve(monkeypatch, http_error(404))
    assert guard.main(["--project", "../x", "--version", VERSION, "--dist", str(dist)]) == 1
    assert guard.main(["--project", PROJECT, "--version", "1/2", "--dist", str(dist)]) == 1
    assert requested == []


def _deploy_job() -> str:
    text = WORKFLOW.read_text()
    match = re.search(r"^  deploy:\n(.*?)(?=^  [\w-]+:\n)", text, re.MULTILINE | re.DOTALL)
    assert match is not None
    return match.group(1)


def test_workflow_publishes_through_the_guard() -> None:
    text = WORKFLOW.read_text()
    assert not re.search(r"^\s*skip-existing\s*:", text, re.MULTILINE)
    deploy = _deploy_job()
    guard_at = deploy.index("scripts/pypi_duplicate_guard.py --project")
    publish_at = deploy.index("uses: pypa/gh-action-pypi-publish@")
    assert deploy.index("uses: actions/download-artifact@") < guard_at < publish_at
    publish_step = deploy[deploy.rindex("- name:", 0, publish_at) : publish_at]
    # A missing guard output must not skip the upload: only an explicit
    # upload=false (every file already identical on PyPI) may.
    assert "if: steps.guard.outputs.upload != 'false'" in publish_step
    assert "attestations: true" in deploy
    permissions = re.search(r"^    permissions:\n((?:      .*\n)+)", deploy, re.MULTILINE)
    assert permissions is not None
    assert {line.split("#")[0].strip() for line in permissions.group(1).splitlines()} == {
        "contents: read",
        "id-token: write",
    }
    start = deploy.index("uses: actions/checkout@")
    checkout = deploy[start : deploy.index("- name:", start)]
    assert "sparse-checkout: scripts/pypi_duplicate_guard.py\n" in checkout
    assert "persist-credentials: false" in checkout
    # The guard must come from the workflow commit, never from the release tag.
    assert not re.search(r"^\s*ref\s*:", checkout, re.MULTILINE)
    assert re.search(
        r"^concurrency:\n  group: publish-pypi-\$\{\{ inputs\.tag \}\}\n"
        r"  cancel-in-progress: false\n",
        text,
        re.MULTILINE,
    )
