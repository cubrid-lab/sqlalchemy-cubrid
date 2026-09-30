"""The live CUBRID test endpoint shared by the integration tests and scripts.

``CUBRID_TEST_URL`` is the one switch for a live run (#593): unset, every
``integration``-marked test skips; set, the server behind it must answer, or
every integration test errors. ``test/conftest.py`` (the gate),
``scripts/wait_for_cubrid.py`` (``make integration``'s readiness wait) and the
pure-Python tox profile read the URL, describe it and probe it through the
helpers here, so they cannot disagree about which server is under test.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.pool import NullPool

TEST_URL_VAR = "CUBRID_TEST_URL"
ASYNC_URL_VAR = "CUBRID_TEST_AURL"
#: Synchronous CUBRID schemes the integration suite accepts in CUBRID_TEST_URL.
SYNC_DRIVERNAMES = frozenset({"cubrid", "cubrid+cubrid", "cubrid+cubriddb", "cubrid+pycubrid"})

# pycubrid accepts socket timeouts, so one attempt cannot hang on a server that
# accepts the connection but does not answer; CUBRIDdb takes no such options.
PYCUBRID_TIMEOUTS = {"connect_timeout": 5, "read_timeout": 5}


def _parse(value: str | URL) -> URL:
    try:
        return make_url(value)
    except (ArgumentError, ValueError):
        # Upstream parse errors may contain the original URL and credentials.
        raise ValueError("A valid CUBRID test database URL is required") from None


def pure_sync_url(value: str | None) -> URL:
    """Require an explicit pure-driver database URL without exposing credentials."""
    if not value:
        raise ValueError("Set CUBRID_TEST_URL to a cubrid+pycubrid URL for a test database")
    url = _parse(value)
    if url.drivername != "cubrid+pycubrid" or not url.database:
        raise ValueError("Tox integration requires a cubrid+pycubrid URL with a database")
    return url


def async_url(value: str | URL, override: str | None = None) -> URL:
    """Derive the async route while retaining authentication, endpoint and query."""
    url = _parse(override if override is not None else value)
    if override is not None:
        if url.drivername != "cubrid+aiopycubrid":
            raise ValueError("CUBRID_TEST_AURL must use cubrid+aiopycubrid")
        return url
    if url.drivername not in {"cubrid", "cubrid+pycubrid", "cubrid+aiopycubrid"}:
        raise ValueError("A CUBRID test URL is required to derive the async route")
    return url.set(drivername="cubrid+aiopycubrid")


def is_configured(environ: Mapping[str, str] | None = None) -> bool:
    """True when ``CUBRID_TEST_URL`` asks for a live integration run."""
    env = os.environ if environ is None else environ
    return bool(env.get(TEST_URL_VAR))


def configured_url(environ: Mapping[str, str] | None = None) -> URL:
    """Parse ``CUBRID_TEST_URL``; ``ValueError`` (without credentials) when unset or invalid."""
    env = os.environ if environ is None else environ
    value = env.get(TEST_URL_VAR)
    if not value:
        raise ValueError(f"{TEST_URL_VAR} is not set")
    url = _parse(value)
    # Integration fixtures run destructive DDL: never probe, let alone pass, a
    # non-CUBRID database or a URL without one.
    if url.drivername not in SYNC_DRIVERNAMES or not url.database:
        raise ValueError(
            f"{TEST_URL_VAR} must be a {' / '.join(sorted(SYNC_DRIVERNAMES))} URL "
            "with a database, e.g. cubrid+pycubrid://dba@localhost:33000/testdb"
        )
    return url


def configured_async_url(sync: URL, environ: Mapping[str, str] | None = None) -> tuple[URL, bool]:
    """The async route the async suites use, and whether ``CUBRID_TEST_AURL`` set it."""
    env = os.environ if environ is None else environ
    # Like the async suites, treat a set-but-empty override as set (and invalid).
    override = env.get(ASYNC_URL_VAR)
    return async_url(sync, override), override is not None


def describe(url: URL) -> str:
    """The URL with its password masked, for messages."""
    return url.render_as_string(hide_password=True)


def connect_args(url: URL) -> dict[str, Any]:
    """Driver options for a bounded probe through the driver *url* selects."""
    return dict(PYCUBRID_TIMEOUTS) if url.get_driver_name() == "pycubrid" else {}


def probe(url: URL) -> None:
    """Connect through the driver *url* selects and run ``SELECT 1``; raise on any failure."""
    engine = create_engine(url, poolclass=NullPool, connect_args=connect_args(url))
    try:
        with engine.connect() as connection:
            if connection.execute(text("SELECT 1")).scalar_one() != 1:
                raise RuntimeError("unexpected SELECT 1 result")
    finally:
        engine.dispose()


def async_probe(url: URL, timeout: float = 15.0) -> None:
    """Like :func:`probe`, through ``cubrid+aiopycubrid://``, bounded by *timeout* seconds."""
    from sqlalchemy.ext.asyncio import create_async_engine

    async def run() -> None:
        engine = create_async_engine(url, poolclass=NullPool, connect_args=PYCUBRID_TIMEOUTS)
        try:
            async with engine.connect() as connection:
                result = await connection.execute(text("SELECT 1"))
                if result.scalar_one() != 1:
                    raise RuntimeError("unexpected SELECT 1 result")
        finally:
            await engine.dispose()

    asyncio.run(asyncio.wait_for(run(), timeout))


def error_summary(exc: BaseException, url: URL) -> str:
    """``Type: first line`` of *exc*, with *url*'s password masked if a driver echoed it."""
    lines = str(exc).strip().splitlines()
    summary = f"{type(exc).__name__}: {lines[0]}" if lines else type(exc).__name__
    if url.password:
        summary = summary.replace(str(url.password), "***")
    return summary
