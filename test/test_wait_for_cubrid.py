"""Offline tests for the ``make integration`` readiness wait (#575)."""

from __future__ import annotations

import pytest

from scripts import wait_for_cubrid
from scripts.integration_urls import PYCUBRID_TIMEOUTS


class _FakeEngine:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.attempts = 0
        self.disposed = False

    def connect(self):  # noqa: ANN201
        self.attempts += 1
        if self.attempts <= self.failures:
            raise ConnectionError("ERROR: CCI, -20004, Cannot communicate with server\nmore")
        return self

    def __enter__(self):  # noqa: ANN204
        return self

    def __exit__(self, *exc) -> None:  # noqa: ANN002
        return None

    def execute(self, statement):  # noqa: ANN001, ANN201
        return self

    def scalar_one(self) -> int:
        return 1

    def dispose(self) -> None:
        self.disposed = True


@pytest.fixture
def fake_engine(monkeypatch):
    def install(failures: int) -> _FakeEngine:
        engine = _FakeEngine(failures)
        monkeypatch.setattr(wait_for_cubrid, "create_engine", lambda *a, **k: engine)
        return engine

    monkeypatch.setenv("CUBRID_TEST_URL", "cubrid+pycubrid://dba:secret@localhost:33000/testdb")
    return install


def test_returns_once_the_server_answers(fake_engine, capsys):
    engine = fake_engine(failures=3)
    assert wait_for_cubrid.main(["--timeout", "5", "--interval", "0"]) == 0
    assert engine.attempts == 4
    assert engine.disposed
    out = capsys.readouterr().out
    assert "ready" in out and "attempt 4" in out
    assert "secret" not in out


def test_times_out_with_the_last_error(fake_engine, capsys):
    engine = fake_engine(failures=10**6)
    assert wait_for_cubrid.main(["--timeout", "0", "--interval", "0"]) == 1
    assert engine.attempts == 1
    assert engine.disposed
    err = capsys.readouterr().err
    assert "not ready after 0s" in err
    assert "ConnectionError: ERROR: CCI, -20004, Cannot communicate with server" in err
    assert "more" not in err
    assert "secret" not in err


def test_waits_the_full_timeout_before_giving_up(fake_engine, monkeypatch):
    # Copilot review on #581: an interval longer than the remaining budget must
    # not end the wait early; the last attempt runs at the deadline.
    clock = {"now": 100.0}
    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        clock["now"] += seconds

    monkeypatch.setattr(wait_for_cubrid.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(wait_for_cubrid.time, "sleep", fake_sleep)
    engine = fake_engine(failures=10**6)
    assert wait_for_cubrid.main(["--timeout", "5", "--interval", "2"]) == 1
    assert sleeps == [2, 2, 1]
    assert engine.attempts == 4
    assert clock["now"] == 105.0


def test_requires_a_url(monkeypatch, capsys):
    monkeypatch.delenv("CUBRID_TEST_URL", raising=False)
    assert wait_for_cubrid.main([]) == 1
    assert "CUBRID_TEST_URL is not set" in capsys.readouterr().err


def test_fails_at_once_for_an_unusable_driver(monkeypatch, capsys):
    monkeypatch.setenv("CUBRID_TEST_URL", "cubrid+nosuchdriver://dba@localhost:33000/testdb")
    assert wait_for_cubrid.main(["--timeout", "60"]) == 1
    assert "Cannot use CUBRID_TEST_URL" in capsys.readouterr().err


def test_an_unparsable_url_is_not_echoed(monkeypatch, capsys):
    # make_url()'s own error repeats the raw value, credentials included (#593).
    monkeypatch.setenv("CUBRID_TEST_URL", "not a url with s3cret-password")
    assert wait_for_cubrid.main(["--timeout", "60"]) == 1
    err = capsys.readouterr().err
    assert "Cannot use CUBRID_TEST_URL" in err
    assert "s3cret" not in err


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("cubrid+pycubrid://dba@localhost:33000/testdb", PYCUBRID_TIMEOUTS),
        ("cubrid://dba@localhost:33000/testdb", {}),
    ],
)
def test_bounds_each_pycubrid_attempt(monkeypatch, url, expected):
    seen = {}

    def fake_create_engine(url, **kwargs):  # noqa: ANN001, ANN003, ANN202
        seen.update(kwargs)
        return _FakeEngine(failures=0)

    monkeypatch.setattr(wait_for_cubrid, "create_engine", fake_create_engine)
    monkeypatch.setenv("CUBRID_TEST_URL", url)
    assert wait_for_cubrid.main(["--interval", "0"]) == 0
    assert seen["connect_args"] == expected
