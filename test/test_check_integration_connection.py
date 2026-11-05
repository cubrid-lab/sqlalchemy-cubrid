"""Pin sync_probe() engine disposal on success and failure paths (issue #858)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SPEC = importlib.util.spec_from_file_location(
    "check_integration_connection",
    REPO_ROOT / "scripts/check_integration_connection.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
sync_probe = MODULE.sync_probe
_TIME_OUTS = MODULE._TIMEOUTS


class _FakeResult:
    def __init__(self, scalar: int) -> None:
        self.scalar = scalar

    def scalar_one(self) -> int:
        return self.scalar


class _FakeConnection:
    def __init__(self, scalar: int) -> None:
        self.scalar = scalar

    def execute(self, statement):  # noqa: ANN001, ANN202
        return _FakeResult(self.scalar)


class _ConnectionContext:
    def __init__(self, scalar: int) -> None:
        self.scalar = scalar

    def __enter__(self) -> _FakeConnection:
        return _FakeConnection(self.scalar)

    def __exit__(self, *exc_info) -> None:  # noqa: ANN002, ANN003
        return None


class _FakeEngine:
    def __init__(self, url, connect_args) -> None:  # noqa: ANN001
        self.url = url
        self.connect_args = connect_args
        self.disposed = False
        self.scalar = 1
        self.connect_raises: Exception | None = None

    def connect(self) -> _ConnectionContext:
        if self.connect_raises is not None:
            raise self.connect_raises
        return _ConnectionContext(self.scalar)

    def dispose(self) -> None:
        self.disposed = True


def _patch_engine(monkeypatch: pytest.MonkeyPatch) -> _FakeEngine:
    engine = _FakeEngine(None, None)
    created: dict[str, _FakeEngine] = {}

    def fake_create_engine(url, **kwargs):  # noqa: ANN001, ANN003, ANN202
        engine.url = url
        engine.connect_args = kwargs.get("connect_args")
        created["engine"] = engine
        return engine

    monkeypatch.setattr(MODULE, "create_engine", fake_create_engine)
    return engine


def test_disposes_engine_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _patch_engine(monkeypatch)
    sync_probe("cubrid://dba@localhost:33000/testdb")
    assert engine.disposed
    assert engine.connect_args == _TIME_OUTS
    assert engine.connect_args == {"connect_timeout": 5, "read_timeout": 5}


def test_disposes_engine_on_unexpected_scalar(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _patch_engine(monkeypatch)
    engine.scalar = 2
    with pytest.raises(RuntimeError, match="Unexpected database probe result"):
        sync_probe("cubrid://dba@localhost:33000/testdb")
    assert engine.disposed


def test_disposes_engine_when_connect_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _patch_engine(monkeypatch)
    engine.connect_raises = OSError("connection refused")
    with pytest.raises(OSError, match="connection refused"):
        sync_probe("cubrid://dba@localhost:33000/testdb")
    assert engine.disposed


def test_main_success_default_async_url(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    test_url = "cubrid+pycubrid://dba:secretpw@localhost:33000/testdb"
    monkeypatch.setenv("CUBRID_TEST_URL", test_url)
    monkeypatch.delenv("CUBRID_TEST_AURL", raising=False)

    calls = []

    def fake_sync_probe(url):
        calls.append(("sync", url))

    async def fake_async_probe(url):
        calls.append(("async", url))

    monkeypatch.setattr(MODULE, "sync_probe", fake_sync_probe)
    monkeypatch.setattr(MODULE, "async_probe", fake_async_probe)

    exit_code = MODULE.main()

    assert exit_code == 0
    assert len(calls) == 2
    assert calls[0][0] == "sync"
    assert calls[0][1].drivername == "cubrid+pycubrid"
    assert calls[1][0] == "async"
    assert calls[1][1].drivername == "cubrid+aiopycubrid"

    out, err = capsys.readouterr()
    assert "Pure-driver integration preflight passed: pycubrid sync and aiopycubrid async\n" in out
    assert err == ""


def test_main_success_custom_async_url(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    test_url = "cubrid+pycubrid://dba:secretpw@localhost:33000/testdb"
    test_aurl = "cubrid+aiopycubrid://dba:secretpw@customhost:33000/customdb"

    monkeypatch.setenv("CUBRID_TEST_URL", test_url)
    monkeypatch.setenv("CUBRID_TEST_AURL", test_aurl)

    calls = []

    def fake_sync_probe(url):
        calls.append(("sync", url))

    async def fake_async_probe(url):
        calls.append(("async", url))

    monkeypatch.setattr(
        MODULE,
        "sync_probe",
        fake_sync_probe,
    )
    monkeypatch.setattr(
        MODULE,
        "async_probe",
        fake_async_probe,
    )

    exit_code = MODULE.main()

    assert exit_code == 0
    assert len(calls) == 2
    assert calls[0][0] == "sync"
    assert calls[0][1].drivername == "cubrid+pycubrid"
    assert calls[1][0] == "async"
    assert calls[1][1].drivername == "cubrid+aiopycubrid"
    assert calls[1][1].host == "customhost"
    assert calls[1][1].database == "customdb"

    out, err = capsys.readouterr()

    assert "Pure-driver integration preflight passed: pycubrid sync and aiopycubrid async\n" in out
    assert err == ""


def test_main_fails_when_test_url_unset(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:

    monkeypatch.delenv("CUBRID_TEST_URL", raising=False)
    monkeypatch.delenv("CUBRID_TEST_AURL", raising=False)

    calls = []

    def fake_sync_probe(url):
        calls.append(("sync", url))

    async def fake_async_probe(url):
        calls.append(("async", url))

    monkeypatch.setattr(MODULE, "sync_probe", fake_sync_probe)
    monkeypatch.setattr(MODULE, "async_probe", fake_async_probe)

    exit_code = MODULE.main()

    assert exit_code == 1
    assert calls == []

    out, err = capsys.readouterr()
    assert out == ""
    assert err.split()[-1] == "(ValueError)"


def test_main_fails_on_non_pycubrid_driver(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    test_url = "cubrid://dba:secretpw@localhost:33000/testdb"

    monkeypatch.setenv("CUBRID_TEST_URL", test_url)
    monkeypatch.delenv("CUBRID_TEST_AURL", raising=False)

    calls = []

    def fake_sync_probe(url):
        calls.append(("sync", url))

    async def fake_async_probe(url):
        calls.append(("async", url))

    monkeypatch.setattr(MODULE, "sync_probe", fake_sync_probe)
    monkeypatch.setattr(MODULE, "async_probe", fake_async_probe)

    exit_code = MODULE.main()

    assert exit_code == 1
    assert calls == []

    out, err = capsys.readouterr()

    assert out == ""
    assert err.split()[-1] == "(ValueError)"
    assert "secretpw" not in err


def test_main_fails_and_redacts_on_probe_exception(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    test_url = "cubrid+pycubrid://dba:secretpw@localhost:33000/testdb"

    monkeypatch.setenv("CUBRID_TEST_URL", test_url)
    monkeypatch.delenv("CUBRID_TEST_AURL", raising=False)

    calls = []

    def fake_sync_probe(url):
        calls.append(("sync", url))
        raise OSError("refused secretpw")

    async def fake_async_probe(url):
        calls.append(("async", url))

    monkeypatch.setattr(MODULE, "sync_probe", fake_sync_probe)
    monkeypatch.setattr(MODULE, "async_probe", fake_async_probe)

    exit_code = MODULE.main()

    assert exit_code == 1
    assert len(calls) == 1
    assert calls[0][0] == "sync"

    out, err = capsys.readouterr()
    assert out == ""
    assert err.split()[-1] == "(OSError)"
    assert "secretpw" not in err
    assert "refused" not in err


def test_main_fails_and_redacts_on_async_probe_exception(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    test_url = "cubrid+pycubrid://dba:secretpw@localhost:33000/testdb"
    test_aurl = "cubrid+aiopycubrid://dba:secretpw@localhost:33000/testdb"

    monkeypatch.setenv("CUBRID_TEST_URL", test_url)
    monkeypatch.setenv("CUBRID_TEST_AURL", test_aurl)

    calls = []

    def fake_sync_probe(url):
        calls.append(("sync", url))

    async def fake_async_probe(url):
        calls.append(("async", url))
        raise RuntimeError("async timeout secretpw")

    monkeypatch.setattr(MODULE, "sync_probe", fake_sync_probe)
    monkeypatch.setattr(MODULE, "async_probe", fake_async_probe)

    exit_code = MODULE.main()

    assert exit_code == 1
    assert len(calls) == 2
    assert calls[0][0] == "sync"
    assert calls[1][0] == "async"

    out, err = capsys.readouterr()
    assert out == ""
    assert err.split()[-1] == "(RuntimeError)"
    assert "secretpw" not in err
    assert "timeout" not in err


def test_main_fails_on_invalid_custom_async_url(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    test_url = "cubrid+pycubrid://dba:secretpw@localhost:33000/testdb"
    test_aurl = "cubrid+pycubrid://dba:secretpw@localhost:33000/testdb"

    monkeypatch.setenv("CUBRID_TEST_URL", test_url)
    monkeypatch.setenv("CUBRID_TEST_AURL", test_aurl)

    calls = []

    def fake_sync_probe(url):
        calls.append(("sync", url))

    async def fake_async_probe(url):
        calls.append(("async", url))

    monkeypatch.setattr(MODULE, "sync_probe", fake_sync_probe)
    monkeypatch.setattr(MODULE, "async_probe", fake_async_probe)

    exit_code = MODULE.main()

    assert exit_code == 1
    assert calls == []

    out, err = capsys.readouterr()
    assert out == ""
    assert err.split()[-1] == "(ValueError)"
    assert "secretpw" not in err


def test_main_fails_and_redacts_on_async_timeout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    test_url = "cubrid+pycubrid://dba:secretpw@localhost:33000/testdb"

    monkeypatch.setenv("CUBRID_TEST_URL", test_url)
    monkeypatch.delenv("CUBRID_TEST_AURL", raising=False)

    calls = []

    def fake_sync_probe(url):
        calls.append(("sync", url))

    async def fake_async_probe(url):
        calls.append(("async", url))
        raise TimeoutError("probe timed out secretpw")

    monkeypatch.setattr(MODULE, "sync_probe", fake_sync_probe)
    monkeypatch.setattr(MODULE, "async_probe", fake_async_probe)

    exit_code = MODULE.main()

    assert exit_code == 1
    assert len(calls) == 2
    assert calls[0][0] == "sync"
    assert calls[1][0] == "async"

    out, err = capsys.readouterr()
    assert out == ""
    assert err.split()[-1] == "(TimeoutError)"
    assert "secretpw" not in err
    assert "timed out" not in err
