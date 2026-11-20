# sqlalchemy_cubrid/trace.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""CUBRID query trace utility.

CUBRID does not support standard ``EXPLAIN`` syntax. Instead, it provides
a trace facility via ``SET TRACE ON`` / ``SHOW TRACE`` session commands.

Usage::

    from sqlalchemy import create_engine, text
    from sqlalchemy_cubrid.trace import trace_query

    # Disposable local lab database only (for example the Docker test database
    # from CONTRIBUTING.md). Replace the host, port, database and credentials
    # with your own values, loaded from configuration rather than committed.
    # ``cubrid+pycubrid://`` is the recommended pure-Python driver
    # (``pip install "sqlalchemy-cubrid[pycubrid]"``).
    engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")
    with engine.connect() as conn:
        result = trace_query(conn, text("SELECT * FROM users WHERE id = 1"))
        print(result)
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.sql.expression import Executable

_logger = logging.getLogger(__name__)

__all__ = ("trace_query",)


def trace_query(
    connection: Connection,
    statement: Executable,
    *,
    parameters: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
) -> list[str]:
    """Execute a statement with CUBRID's trace facility and return trace output.

    CUBRID uses ``SET TRACE ON`` / ``SHOW TRACE`` instead of ``EXPLAIN``.
    This function wraps that workflow:

    1. ``SET TRACE ON`` — enables trace collection for the session
    2. Executes the provided statement
    3. ``SHOW TRACE`` — retrieves trace statistics
    4. ``SET TRACE OFF`` — disables trace collection

    :param connection: An active SQLAlchemy connection to a CUBRID database.
    :param statement: The SQL statement (text or ORM construct) to trace.
    :param parameters: Optional parameters for the statement.
    :returns: A list of trace output strings. Each string contains trace
              statistics for the executed query.

    Usage::

        from sqlalchemy import create_engine, text
        from sqlalchemy_cubrid.trace import trace_query

        # Disposable local lab database only; supply your own URL from
        # configuration instead of committing credentials or deployed hosts.
        engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")
        with engine.connect() as conn:
            traces = trace_query(conn, text("SELECT * FROM users WHERE id = 1"))
            for line in traces:
                print(line)

    .. note::

        This function requires a live CUBRID connection. It cannot be used
        in offline (compilation-only) mode. The trace facility is session-scoped
        and does not affect other connections.
    """
    try:
        connection.execute(text("SET TRACE ON"))

        if parameters is not None:
            stmt_result = connection.execute(statement, parameters)
        else:
            stmt_result = connection.execute(statement)
        stmt_result.close()

        result = connection.execute(text("SHOW TRACE"))
        try:
            rows = result.fetchall()
        finally:
            result.close()

        trace_output: list[str] = []
        for row in rows:
            if row and row[0] is not None:
                trace_output.append(str(row[0]))

        return trace_output
    finally:
        # Best-effort cleanup: intentionally swallow any exception from
        # `SET TRACE OFF` so we never mask the original exception (if any)
        # raised inside the try block. Log at debug level for observability.
        try:
            connection.execute(text("SET TRACE OFF"))
        except Exception as exc:  # noqa: BLE001 - cleanup must not mask original error
            _logger.debug("Failed to disable CUBRID trace during cleanup: %s", exc)
