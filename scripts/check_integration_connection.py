"""Fail before tox integration when its selected pure-driver database is unavailable."""

from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine

from scripts.integration_urls import async_url, pure_sync_url

_TIMEOUTS = {"connect_timeout": 5, "read_timeout": 5}


def sync_probe(url: URL) -> None:
    engine = create_engine(url, connect_args=_TIMEOUTS)
    try:
        with engine.connect() as connection:
            if connection.execute(text("SELECT 1")).scalar_one() != 1:
                raise RuntimeError("Unexpected database probe result")
    finally:
        engine.dispose()


async def async_probe(url: URL) -> None:
    engine = create_async_engine(url, connect_args=_TIMEOUTS)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            if result.scalar_one() != 1:
                raise RuntimeError("Unexpected async database probe result")
    finally:
        await engine.dispose()


def main() -> int:
    try:
        sync = pure_sync_url(os.environ.get("CUBRID_TEST_URL"))
        asynchronous = async_url(sync, os.environ.get("CUBRID_TEST_AURL"))
        sync_probe(sync)

        async def bounded_probe() -> None:
            await asyncio.wait_for(async_probe(asynchronous), timeout=15)

        asyncio.run(bounded_probe())
    except Exception as exc:
        print(
            "Pure-driver integration preflight failed; CUBRID_TEST_URL must use "
            "cubrid+pycubrid and optional CUBRID_TEST_AURL must use cubrid+aiopycubrid. "
            f"Check the test database is available ({type(exc).__name__})",
            file=sys.stderr,
        )
        return 1
    print("Pure-driver integration preflight passed: pycubrid sync and aiopycubrid async")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
