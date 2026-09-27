"""URL contracts for the existing pure-Python tox integration profile."""

from __future__ import annotations

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError


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
