"""Offline URL and failure-contract tests for the pure-driver tox profile."""

from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.engine import make_url

from scripts import check_integration_connection as preflight
from scripts.integration_urls import async_url, pure_sync_url


@pytest.mark.parametrize("scheme", ["cubrid", "cubrid+pycubrid"])
def test_async_url_retains_encoded_auth_ipv6_port_and_query(scheme: str) -> None:
    original = make_url(
        scheme + "://user%40name:p%40ss%2F%3F%23@[::1]:33091/testdb?tag=one&tag=two&read_timeout=7"
    )
    converted = async_url(original)
    assert converted == original.set(drivername="cubrid+aiopycubrid")
    assert converted.username == "user@name"
    assert converted.password == "p@ss/?#"
    assert converted.host == "::1"
    assert converted.port == 33091
    assert converted.query["tag"] == ("one", "two")


def test_explicit_async_override_is_preserved() -> None:
    override = "cubrid+aiopycubrid://other:secret@async-host:33092/testdb?read_timeout=9"
    assert async_url("cubrid+pycubrid://dba@sync-host:33091/testdb", override) == make_url(override)


@pytest.mark.parametrize("module_name", ["test.test_aio_integration", "test.test_stress_pool"])
def test_async_suite_consumers_follow_the_selected_sync_endpoint(
    monkeypatch, module_name: str
) -> None:
    module = importlib.import_module(module_name)
    selected = "cubrid+pycubrid://user:secret@127.0.0.1:33091/testdb?read_timeout=7"
    monkeypatch.setenv("CUBRID_TEST_URL", selected)
    monkeypatch.delenv("CUBRID_TEST_AURL", raising=False)
    assert module._async_url() == make_url(selected).set(drivername="cubrid+aiopycubrid")


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "cubrid://dba@localhost/testdb",
        "postgresql://user@localhost/db",
        "cubrid+pycubrid://dba@localhost",
    ],
)
def test_tox_profile_rejects_missing_legacy_or_invalid_database(value: str | None) -> None:
    with pytest.raises(ValueError):
        pure_sync_url(value)


def test_invalid_url_error_does_not_expose_credentials() -> None:
    with pytest.raises(ValueError) as caught:
        pure_sync_url("not-a-url-with-secret-password")
    assert "secret-password" not in str(caught.value)


def test_preflight_fails_before_connecting_without_required_url(monkeypatch, capsys) -> None:
    monkeypatch.delenv("CUBRID_TEST_URL", raising=False)
    probe = MagicMock()
    monkeypatch.setattr(preflight, "sync_probe", probe)
    assert preflight.main() == 1
    probe.assert_not_called()
    assert "preflight failed" in capsys.readouterr().err


def test_preflight_connection_error_is_redacted(monkeypatch, capsys) -> None:
    monkeypatch.setenv("CUBRID_TEST_URL", "cubrid+pycubrid://user:secret-password@localhost/testdb")
    monkeypatch.setattr(
        preflight, "sync_probe", MagicMock(side_effect=RuntimeError("secret-password"))
    )
    assert preflight.main() == 1
    assert "secret-password" not in capsys.readouterr().err


def test_sync_probe_disposes_engine_on_failure(monkeypatch) -> None:
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value.execute.side_effect = RuntimeError("probe")
    monkeypatch.setattr(preflight, "create_engine", MagicMock(return_value=engine))
    with pytest.raises(RuntimeError, match="probe"):
        preflight.sync_probe(make_url("cubrid+pycubrid://dba@localhost/testdb"))
    engine.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_async_probe_disposes_engine_on_failure(monkeypatch) -> None:
    engine = MagicMock()
    connection = MagicMock()
    connection.execute = AsyncMock(side_effect=RuntimeError("probe"))
    engine.connect.return_value.__aenter__ = AsyncMock(return_value=connection)
    engine.dispose = AsyncMock()
    monkeypatch.setattr(preflight, "create_async_engine", MagicMock(return_value=engine))
    with pytest.raises(RuntimeError, match="probe"):
        await preflight.async_probe(make_url("cubrid+aiopycubrid://dba@localhost/testdb"))
    engine.dispose.assert_awaited_once()
