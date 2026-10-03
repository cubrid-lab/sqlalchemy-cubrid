# test/test_integration_gate.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Offline checks for the shared integration gate in ``test/conftest.py`` (#593).

``CUBRID_TEST_URL`` unset: every ``integration``-marked test skips (and CI
refuses such a run). ``CUBRID_TEST_URL`` set but its server unreachable: every
integration test errors with one message that names the URL without its
password, from a single probe per session, instead of silently skipping.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.engine import make_url

from scripts import integration_urls
from test import conftest

_ROOT = Path(__file__).resolve().parent.parent
_SECRET = "s3cret-pw"


@pytest.fixture
def fresh_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Forget the session's cached probe result for the duration of one test."""
    monkeypatch.setattr(conftest, "_probe_error", None)
    monkeypatch.delenv("CUBRID_TEST_AURL", raising=False)


# ----- scripts/integration_urls.py helpers -----


def test_is_configured_reads_only_cubrid_test_url() -> None:
    assert integration_urls.is_configured({"CUBRID_TEST_URL": "cubrid://dba@h/db"})
    assert not integration_urls.is_configured({})
    assert not integration_urls.is_configured({"CUBRID_TEST_URL": ""})


def test_configured_url_errors_do_not_expose_credentials() -> None:
    with pytest.raises(ValueError, match="CUBRID_TEST_URL is not set"):
        integration_urls.configured_url({})
    with pytest.raises(ValueError) as caught:
        integration_urls.configured_url({"CUBRID_TEST_URL": f"not a url {_SECRET}"})
    assert _SECRET not in str(caught.value)


@pytest.mark.parametrize(
    "value",
    [
        "sqlite:///:memory:",
        "postgresql://u@h/db",
        "cubrid+aiopycubrid://dba@h/db",
        "cubrid://dba@h",
    ],
)
def test_configured_url_accepts_only_sync_cubrid_urls_with_a_database(value: str) -> None:
    # Copilot review on #604: the fixtures run destructive DDL, so a URL that is
    # not a synchronous CUBRID database must never pass the gate.
    with pytest.raises(ValueError, match="must be a cubrid"):
        integration_urls.configured_url({"CUBRID_TEST_URL": value})


@pytest.mark.parametrize("scheme", ["cubrid", "cubrid+cubriddb", "cubrid+pycubrid"])
def test_configured_url_accepts_the_sync_cubrid_schemes(scheme: str) -> None:
    url = integration_urls.configured_url({"CUBRID_TEST_URL": f"{scheme}://dba@h:1/testdb"})
    assert url.drivername == scheme


def test_configured_async_url_reports_an_explicit_override() -> None:
    sync = make_url("cubrid://dba@h:1/testdb")
    derived, overridden = integration_urls.configured_async_url(sync, {})
    assert (derived.drivername, overridden) == ("cubrid+aiopycubrid", False)
    override = "cubrid+aiopycubrid://dba@other:2/testdb"
    aurl, overridden = integration_urls.configured_async_url(sync, {"CUBRID_TEST_AURL": override})
    assert (aurl, overridden) == (make_url(override), True)


def test_describe_masks_the_password() -> None:
    url = make_url(f"cubrid+pycubrid://dba:{_SECRET}@db.example:33123/testdb")
    described = integration_urls.describe(url)
    assert _SECRET not in described
    assert "db.example:33123/testdb" in described


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("cubrid+pycubrid://dba@h/db", integration_urls.PYCUBRID_TIMEOUTS),
        ("cubrid://dba@h/db", {}),
    ],
)
def test_connect_args_bound_only_pycubrid(url: str, expected: dict[str, int]) -> None:
    assert integration_urls.connect_args(make_url(url)) == expected


def test_error_summary_keeps_the_first_line_and_masks_the_password() -> None:
    url = make_url(f"cubrid+pycubrid://dba:{_SECRET}@h/db")
    exc = ConnectionError(f"refused for {_SECRET}\nsecond line")
    assert integration_urls.error_summary(exc, url) == "ConnectionError: refused for ***"
    assert integration_urls.error_summary(ConnectionError(), url) == "ConnectionError"


def test_probe_disposes_the_engine_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value.execute.side_effect = RuntimeError("down")
    create = MagicMock(return_value=engine)
    monkeypatch.setattr(integration_urls, "create_engine", create)
    url = make_url("cubrid+pycubrid://dba@h/db")
    with pytest.raises(RuntimeError, match="down"):
        integration_urls.probe(url)
    engine.dispose.assert_called_once()
    assert create.call_args.kwargs["connect_args"] == integration_urls.PYCUBRID_TIMEOUTS


# ----- the conftest gate -----


@pytest.mark.usefixtures("fresh_probe")
def test_unreachable_server_is_probed_once_and_named_without_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CUBRID_TEST_URL", f"cubrid+pycubrid://dba:{_SECRET}@h:33123/testdb")
    probe = MagicMock(side_effect=ConnectionError(f"refused ({_SECRET})"))
    monkeypatch.setattr(integration_urls, "probe", probe)

    first = conftest._endpoint_error()
    assert conftest._endpoint_error() == first
    probe.assert_called_once()
    assert "CUBRID_TEST_URL is set, but CUBRID at cubrid+pycubrid://dba:***@h:33123/testdb" in first
    assert "ConnectionError: refused (***)" in first
    assert _SECRET not in first


@pytest.mark.usefixtures("fresh_probe")
def test_reachable_server_passes_the_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CUBRID_TEST_URL", "cubrid://dba@h/testdb")
    monkeypatch.setattr(integration_urls, "probe", MagicMock(return_value=None))
    assert conftest._endpoint_error() == ""


@pytest.mark.usefixtures("fresh_probe")
def test_async_override_is_probed_too(monkeypatch: pytest.MonkeyPatch) -> None:
    # Copilot review on #604: the async suites connect to CUBRID_TEST_AURL when
    # it is set, so an unreachable override must fail the gate as well.
    monkeypatch.setenv("CUBRID_TEST_URL", "cubrid+pycubrid://dba@h/testdb")
    monkeypatch.setenv("CUBRID_TEST_AURL", f"cubrid+aiopycubrid://dba:{_SECRET}@other:2/testdb")
    probe = MagicMock(return_value=None)
    async_probe = MagicMock(side_effect=TimeoutError())
    monkeypatch.setattr(integration_urls, "probe", probe)
    monkeypatch.setattr(integration_urls, "async_probe", async_probe)
    error = conftest._endpoint_error()
    probe.assert_called_once()
    async_probe.assert_called_once()
    assert error.startswith(
        "CUBRID_TEST_AURL is set, but CUBRID at cubrid+aiopycubrid://dba:***@other:2/testdb"
    )
    assert _SECRET not in error


@pytest.mark.usefixtures("fresh_probe")
def test_the_derived_async_route_is_not_probed_separately(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CUBRID_TEST_URL", "cubrid+pycubrid://dba@h/testdb")
    monkeypatch.delenv("CUBRID_TEST_AURL", raising=False)
    async_probe = MagicMock()
    monkeypatch.setattr(integration_urls, "probe", MagicMock(return_value=None))
    monkeypatch.setattr(integration_urls, "async_probe", async_probe)
    assert conftest._endpoint_error() == ""
    async_probe.assert_not_called()


@pytest.mark.usefixtures("fresh_probe")
def test_unparsable_url_errors_without_probing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CUBRID_TEST_URL", f"not a url {_SECRET}")
    probe = MagicMock()
    monkeypatch.setattr(integration_urls, "probe", probe)
    error = conftest._endpoint_error()
    assert error.startswith("CUBRID test URL is set but unusable")
    assert _SECRET not in error
    probe.assert_not_called()


def _item(integration: bool) -> SimpleNamespace:
    return SimpleNamespace(get_closest_marker=lambda name: object() if integration else None)


@pytest.mark.parametrize(
    ("ci", "url", "items", "exits"),
    [
        ("true", None, [_item(True), _item(False)], True),
        ("1", None, [_item(True)], True),
        ("true", "cubrid://dba@h/db", [_item(True)], False),
        ("true", None, [_item(False)], False),
        (None, None, [_item(True)], False),
    ],
)
def test_ci_refuses_integration_tests_without_a_url(
    monkeypatch: pytest.MonkeyPatch,
    ci: str | None,
    url: str | None,
    items: list[SimpleNamespace],
    exits: bool,
) -> None:
    for name, value in (("CI", ci), ("CUBRID_TEST_URL", url)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    if exits:
        with pytest.raises(pytest.exit.Exception, match="CUBRID_TEST_URL is not set"):
            conftest._ci_integration_guard(items)
    else:
        conftest._ci_integration_guard(items)


# ----- end to end: a child pytest on a live-DB module, no server -----


def _unused_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _run_regression_module(**env_overrides: str) -> subprocess.CompletedProcess[str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("CI", "CUBRID_TEST_URL", "CUBRID_TEST_AURL") and not k.startswith("COV_CORE_")
    }
    env.update(env_overrides)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "test/test_regression.py",
            "-p",
            "no:cacheprovider",
            "-q",
        ],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_unconfigured_integration_tests_skip() -> None:
    proc = _run_regression_module()
    assert proc.returncode == pytest.ExitCode.OK, proc.stdout + proc.stderr
    assert " skipped" in proc.stdout
    assert " passed" not in proc.stdout
    assert " error" not in proc.stdout


def test_unconfigured_integration_tests_fail_in_ci() -> None:
    proc = _run_regression_module(CI="true")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "CUBRID_TEST_URL is not set" in proc.stdout + proc.stderr


def test_configured_but_unreachable_server_errors_every_test() -> None:
    url = f"cubrid+pycubrid://dba:{_SECRET}@127.0.0.1:{_unused_port()}/testdb"
    proc = _run_regression_module(CUBRID_TEST_URL=url)
    out = proc.stdout + proc.stderr
    assert proc.returncode == pytest.ExitCode.TESTS_FAILED, out
    assert " skipped" not in proc.stdout
    assert " error" in proc.stdout
    assert "does not answer SELECT 1" in out
    assert _SECRET not in out
