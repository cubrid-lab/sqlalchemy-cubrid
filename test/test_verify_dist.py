"""Offline tests for scripts/verify_dist.py (publish checks against build outputs).

Kept identical across pycubrid, sqlalchemy-cubrid and cubrid-mcp-server.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("_verify_dist", ROOT / "scripts" / "verify_dist.py")
assert _spec is not None and _spec.loader is not None
verify_dist = importlib.util.module_from_spec(_spec)
sys.modules["_verify_dist"] = verify_dist
_spec.loader.exec_module(verify_dist)

CONTENT = {
    "example_pkg-1.2.3-py3-none-any.whl": b"verified wheel bytes",
    "example_pkg-1.2.3.tar.gz": b"verified sdist bytes",
}


def digests(content: dict[str, bytes]) -> dict[str, str]:
    return {name: hashlib.sha256(data).hexdigest() for name, data in content.items()}


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    folder = tmp_path / "dist"
    folder.mkdir()
    for name, data in CONTENT.items():
        (folder / name).write_bytes(data)
    return folder


def run(
    folder: Path, expected: object, monkeypatch: pytest.MonkeyPatch, raw: str | None = None
) -> int:
    value = raw if raw is not None else json.dumps(expected)
    monkeypatch.setenv("EXPECTED", value)
    return verify_dist.main(["--dir", str(folder), "--expected-env", "EXPECTED"])


def test_exact_match_passes(
    dist: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(dist, digests(CONTENT), monkeypatch) == 0
    assert "2 files match EXPECTED" in capsys.readouterr().out


def test_extra_file_fails(dist: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (dist / "extra.whl").write_bytes(b"x")
    assert run(dist, digests(CONTENT), monkeypatch) == 1


def test_missing_file_fails(dist: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (dist / "example_pkg-1.2.3.tar.gz").unlink()
    assert run(dist, digests(CONTENT), monkeypatch) == 1


def test_digest_mismatch_fails(
    dist: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (dist / "example_pkg-1.2.3-py3-none-any.whl").write_bytes(b"replaced wheel bytes")
    assert run(dist, digests(CONTENT), monkeypatch) == 1
    assert "::error::" in capsys.readouterr().out


def test_subdirectory_fails(dist: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (dist / "nested").mkdir()
    assert run(dist, digests(CONTENT), monkeypatch) == 1


def test_symlink_fails(dist: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    name = "example_pkg-1.2.3.tar.gz"
    target = tmp_path / "elsewhere"
    target.write_bytes(CONTENT[name])
    (dist / name).unlink()
    (dist / name).symlink_to(target)
    assert run(dist, digests(CONTENT), monkeypatch) == 1


def test_missing_directory_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert run(tmp_path / "absent", digests(CONTENT), monkeypatch) == 1


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param("", id="empty"),
        pytest.param("not json", id="not-json"),
        pytest.param("[]", id="list"),
        pytest.param("{}", id="empty-object"),
        pytest.param(json.dumps({"a.whl": "A" * 64}), id="uppercase-digest"),
        pytest.param(json.dumps({"a.whl": "1" * 63}), id="short-digest"),
        pytest.param(json.dumps({"a.whl": 1}), id="non-string-digest"),
        pytest.param(json.dumps({"../a.whl": "1" * 64}), id="path-like-key"),
        pytest.param(json.dumps({"sub/a.whl": "1" * 64}), id="slash-key"),
    ],
)
def test_bad_expected_map_fails(dist: Path, monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    assert run(dist, None, monkeypatch, raw=raw) == 1


def test_unset_environment_variable_fails(dist: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EXPECTED", raising=False)
    assert verify_dist.main(["--dir", str(dist), "--expected-env", "EXPECTED"]) == 1


def test_os_error_fails_with_an_error_line(
    dist: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def unreadable(self: Path) -> bytes:
        raise PermissionError(13, "Permission denied", str(self))

    monkeypatch.setattr(Path, "read_bytes", unreadable)
    assert run(dist, digests(CONTENT), monkeypatch) == 1
    assert "::error::" in capsys.readouterr().out
