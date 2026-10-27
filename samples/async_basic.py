#!/usr/bin/env python3
"""Minimal async usage example for sqlalchemy-cubrid.

Requirements:
    pip install "sqlalchemy-cubrid[pycubrid]"

Usage:
    # Start CUBRID (e.g. via Docker, from docs/LESSON_PREPARE.md):
    #   docker run -d --name sqlalchemy-cubrid-quickstart -e CUBRID_DB=testdb \
    #     -p 127.0.0.1:33000:33000 cubrid/cubrid:11.4
    python samples/async_basic.py
"""

from __future__ import annotations

import asyncio

from sqlalchemy import Column, Integer, MetaData, String, Table, text
from sqlalchemy.ext.asyncio import create_async_engine

DB_URL = "cubrid+aiopycubrid://dba:@127.0.0.1:33000/testdb"


async def main() -> None:
    engine = create_async_engine(DB_URL, echo=True)

    # 1. Verify connectivity
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        print("Connected! SELECT 1 =", result.scalar())

    # 2. Create table
    metadata = MetaData()
    users = Table(
        "async_sample_users",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("name", String(100)),
    )

    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS async_sample_users"))
        await conn.run_sync(metadata.create_all)
        print("Table created.")

    # 3. Insert
    async with engine.begin() as conn:
        await conn.execute(users.insert(), [{"name": "Alice"}, {"name": "Bob"}])
        print("Inserted 2 rows.")

    # 4. Query
    async with engine.connect() as conn:
        result = await conn.execute(users.select())
        for row in result:
            print(f"  id={row.id}, name={row.name}")

    # 5. Cleanup
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS async_sample_users"))

    await engine.dispose()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
