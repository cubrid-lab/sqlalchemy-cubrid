# test/capability/test_capability_probes.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Capability probe suite (stabilization Phase 7).

Each probe runs raw SQL against a live CUBRID and asserts that the server's
*actual* behavior matches what the dialect *declares* (``supports_*`` flags and
``requirements.py``). The failure mode this catches is a silent drift where the
dialect claims a capability CUBRID lacks (or denies one CUBRID has), which then
surfaces as a confusing runtime error or a wrongly-skipped test far downstream.

All probes are ``integration``-marked (they need a live CUBRID). The mapping is
the contract: if a future CUBRID version changes a capability, exactly one probe
flips and points at the flag to update.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from sqlalchemy import create_engine, text

from sqlalchemy_cubrid.dialect import CubridDialect

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def engine() -> Any:
    url = os.environ.get("CUBRID_TEST_URL")
    if not url:
        pytest.skip("CUBRID_TEST_URL not set")
    eng = create_engine(url)
    yield eng
    eng.dispose()


def _server_supports(engine: Any, sql: str) -> bool:
    """True if *sql* runs on CUBRID without raising."""
    try:
        with engine.begin() as conn:
            conn.execute(text(sql))
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Type capabilities
# ---------------------------------------------------------------------------


def test_native_enum_matches_declaration(engine: Any) -> None:
    supported = _server_supports(engine, "SELECT CAST('a' AS ENUM('a','b'))")
    assert supported == CubridDialect.supports_native_enum, (
        f"CUBRID native ENUM support ({supported}) != "
        f"dialect.supports_native_enum ({CubridDialect.supports_native_enum})"
    )


def test_native_boolean_matches_declaration(engine: Any) -> None:
    # CUBRID has no native BOOLEAN cast — it maps booleans to SMALLINT.
    supported = _server_supports(engine, "SELECT CAST(1 AS BOOLEAN)")
    assert supported == CubridDialect.supports_native_boolean, (
        f"CUBRID native BOOLEAN support ({supported}) != "
        f"dialect.supports_native_boolean ({CubridDialect.supports_native_boolean})"
    )


def test_is_distinct_from_operator_available(engine: Any) -> None:
    # supports_is_distinct_from=True is implemented via CUBRID's `<=>`.
    assert CubridDialect.supports_is_distinct_from is True
    with engine.connect() as conn:
        assert conn.execute(text("SELECT (1 <=> NULL)")).scalar() == 0
        assert conn.execute(text("SELECT (1 <=> 1)")).scalar() == 1


# ---------------------------------------------------------------------------
# SQL feature capabilities
# ---------------------------------------------------------------------------


def test_multivalues_insert_matches_declaration(engine: Any) -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS cap_multivalues"))
        conn.execute(text("CREATE TABLE cap_multivalues (id INT PRIMARY KEY, v INT)"))
    supported = _server_supports(engine, "INSERT INTO cap_multivalues VALUES (1, 1), (2, 2)")
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS cap_multivalues"))
    assert supported == CubridDialect.supports_multivalues_insert


def test_cte_supported(engine: Any) -> None:
    with engine.connect() as conn:
        assert conn.execute(text("WITH x AS (SELECT 1 AS n) SELECT n FROM x")).scalar() == 1


def test_window_functions_supported(engine: Any) -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS cap_window"))
        conn.execute(text("CREATE TABLE cap_window (id INT PRIMARY KEY)"))
        conn.execute(text("INSERT INTO cap_window VALUES (1), (2), (3)"))
    with engine.connect() as conn:
        rows = list(conn.execute(text("SELECT ROW_NUMBER() OVER (ORDER BY id) FROM cap_window")))
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS cap_window"))
    assert [r[0] for r in rows] == [1, 2, 3]


def test_limit_offset_supported(engine: Any) -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS cap_limit"))
        conn.execute(text("CREATE TABLE cap_limit (id INT PRIMARY KEY)"))
        conn.execute(text("INSERT INTO cap_limit VALUES (1), (2), (3), (4)"))
    with engine.connect() as conn:
        page = [
            r[0]
            for r in conn.execute(text("SELECT id FROM cap_limit ORDER BY id LIMIT 2 OFFSET 1"))
        ]
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS cap_limit"))
    assert page == [2, 3]


# ---------------------------------------------------------------------------
# DDL capabilities
# ---------------------------------------------------------------------------


def test_alter_table_supported(engine: Any) -> None:
    assert CubridDialect.supports_alter is True
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS cap_alter"))
        conn.execute(text("CREATE TABLE cap_alter (id INT PRIMARY KEY)"))
    supported = _server_supports(engine, "ALTER TABLE cap_alter ADD COLUMN extra INT")
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS cap_alter"))
    assert supported == CubridDialect.supports_alter


def test_column_and_table_comments_supported(engine: Any) -> None:
    assert CubridDialect.supports_comments is True
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS cap_comment"))
    supported = _server_supports(
        engine,
        "CREATE TABLE cap_comment (id INT PRIMARY KEY COMMENT 'c') COMMENT = 't'",
    )
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS cap_comment"))
    assert supported == CubridDialect.supports_comments


def test_returning_unsupported_matches_declaration(engine: Any) -> None:
    # CUBRID has no RETURNING; the dialect declares insert_returning=False.
    assert CubridDialect.insert_returning is False
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS cap_returning"))
        conn.execute(text("CREATE TABLE cap_returning (id INT PRIMARY KEY)"))
    supported = _server_supports(engine, "INSERT INTO cap_returning VALUES (1) RETURNING id")
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS cap_returning"))
    assert supported is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
