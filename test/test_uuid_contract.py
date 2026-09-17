# test/test_uuid_contract.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""UUID type contract tests (#376) — live CUBRID execution.

CUBRID has no native UUID type; the dialect stores `sa.Uuid` as `CHAR(32)`.
These tests pin the full round-trip contract for both `sa.Uuid()` (Python
`uuid.UUID` values) and `sa.Uuid(as_uuid=False)` (string values) across INSERT,
SELECT, WHERE, UPDATE, and reflection, so a regression in the CHAR-backed
storage or the value coercion is caught immediately.
"""

from __future__ import annotations

import os
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    Table,
    create_engine,
    inspect,
    select,
    text,
)


def _cubrid_url() -> str:
    return os.environ.get("CUBRID_TEST_URL", "cubrid+pycubrid://dba@localhost:33000/testdb")


def _can_connect() -> bool:
    try:
        engine = create_engine(_cubrid_url())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


_available = _can_connect()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _available,
        reason="CUBRID instance not available (set CUBRID_TEST_URL)",
    ),
]


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(_cubrid_url(), echo=False)
    yield eng
    eng.dispose()


@pytest.fixture()
def uuid_native_table(engine):
    meta = MetaData()
    table = Table(
        "uuid_native",
        meta,
        Column("id", Integer, primary_key=True),
        Column("val", sa.Uuid()),
    )
    meta.drop_all(engine)
    meta.create_all(engine)
    yield table
    meta.drop_all(engine)


@pytest.fixture()
def uuid_string_table(engine):
    meta = MetaData()
    table = Table(
        "uuid_string",
        meta,
        Column("id", Integer, primary_key=True),
        Column("val", sa.Uuid(as_uuid=False)),
    )
    meta.drop_all(engine)
    meta.create_all(engine)
    yield table
    meta.drop_all(engine)


class TestUuidNative:
    """`sa.Uuid()` — Python `uuid.UUID` values."""

    def test_insert_select_returns_uuid(self, engine, uuid_native_table):
        value = uuid.uuid4()
        with engine.begin() as conn:
            conn.execute(uuid_native_table.insert().values(id=1, val=value))
        with engine.connect() as conn:
            got = conn.execute(select(uuid_native_table.c.val).where(uuid_native_table.c.id == 1))
            result = got.scalar()
        assert isinstance(result, uuid.UUID)
        assert result == value

    def test_where_by_uuid(self, engine, uuid_native_table):
        value = uuid.uuid4()
        other = uuid.uuid4()
        with engine.begin() as conn:
            conn.execute(
                uuid_native_table.insert(),
                [{"id": 1, "val": value}, {"id": 2, "val": other}],
            )
        with engine.connect() as conn:
            found = conn.execute(
                select(uuid_native_table.c.id).where(uuid_native_table.c.val == value)
            ).scalar()
        assert found == 1

    def test_update_with_uuid_in_where(self, engine, uuid_native_table):
        original = uuid.uuid4()
        replacement = uuid.uuid4()
        with engine.begin() as conn:
            conn.execute(uuid_native_table.insert().values(id=1, val=original))
            conn.execute(
                uuid_native_table.update()
                .where(uuid_native_table.c.val == original)
                .values(val=replacement)
            )
        with engine.connect() as conn:
            got = conn.execute(
                select(uuid_native_table.c.val).where(uuid_native_table.c.id == 1)
            ).scalar()
        assert got == replacement

    def test_reflection_reports_char(self, engine, uuid_native_table):
        cols = {c["name"]: c["type"] for c in inspect(engine).get_columns("uuid_native")}
        assert "val" in cols
        # CUBRID has no native UUID type; the dialect stores it as CHAR.
        assert type(cols["val"]).__name__ == "CHAR"


class TestUuidString:
    """`sa.Uuid(as_uuid=False)` — string values."""

    def test_insert_select_returns_str(self, engine, uuid_string_table):
        value = str(uuid.uuid4())
        with engine.begin() as conn:
            conn.execute(uuid_string_table.insert().values(id=1, val=value))
        with engine.connect() as conn:
            result = conn.execute(
                select(uuid_string_table.c.val).where(uuid_string_table.c.id == 1)
            ).scalar()
        assert isinstance(result, str)
        assert result == value

    def test_where_by_string(self, engine, uuid_string_table):
        value = str(uuid.uuid4())
        other = str(uuid.uuid4())
        with engine.begin() as conn:
            conn.execute(
                uuid_string_table.insert(),
                [{"id": 1, "val": value}, {"id": 2, "val": other}],
            )
        with engine.connect() as conn:
            found = conn.execute(
                select(uuid_string_table.c.id).where(uuid_string_table.c.val == value)
            ).scalar()
        assert found == 1

    def test_update_with_string_in_where(self, engine, uuid_string_table):
        original = str(uuid.uuid4())
        replacement = str(uuid.uuid4())
        with engine.begin() as conn:
            conn.execute(uuid_string_table.insert().values(id=1, val=original))
            conn.execute(
                uuid_string_table.update()
                .where(uuid_string_table.c.val == original)
                .values(val=replacement)
            )
        with engine.connect() as conn:
            got = conn.execute(
                select(uuid_string_table.c.val).where(uuid_string_table.c.id == 1)
            ).scalar()
        assert got == replacement

    def test_reflection_reports_char(self, engine, uuid_string_table):
        cols = {c["name"]: c["type"] for c in inspect(engine).get_columns("uuid_string")}
        assert "val" in cols
        assert type(cols["val"]).__name__ == "CHAR"
