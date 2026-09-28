# sqlalchemy_cubrid/pycubrid_dialect.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""CUBRID dialect variant using the pycubrid pure-Python DB-API 2.0 driver."""

from __future__ import annotations

import logging
import weakref
from importlib import import_module
from typing import Any, Callable, cast

from sqlalchemy.engine.interfaces import DBAPIConnection, ConnectArgsType
from sqlalchemy_cubrid._compat import DBAPIModule
from sqlalchemy.engine.url import URL

from sqlalchemy_cubrid.base import CubridExecutionContext
from sqlalchemy_cubrid.dialect import CubridDialect

log = logging.getLogger(__name__)


def _unwrap(connection: Any) -> Any:
    """Return the DBAPI connection behind a SQLAlchemy pool proxy, else *connection*."""
    inner = getattr(connection, "dbapi_connection", None)
    return connection if inner is None else inner


class PyCubridExecutionContext(CubridExecutionContext):
    """Execution context for pycubrid connections.

    pycubrid exposes ``cursor.lastrowid`` as a proper ``int | None``,
    so we use it directly instead of the CUBRIDdb workaround.
    """

    def get_lastrowid(self) -> int | None:  # type: ignore[override]
        """Return the last inserted row ID from pycubrid's cursor."""
        try:
            lastrowid = self.cursor.lastrowid
            return None if lastrowid is None else int(lastrowid)
        except AttributeError:
            pass

        # Fallback: use SQL function
        cursor = self._dbapi_connection.cursor()
        try:
            cursor.execute("SELECT LAST_INSERT_ID()")
            row = cursor.fetchone()
            if row:
                return int(row[0])
        finally:
            cursor.close()
        return None


class PyCubridDialect(CubridDialect):
    """SQLAlchemy dialect for CUBRID using the pycubrid pure-Python driver.

    Connection URL: ``cubrid+pycubrid://user:password@host:port/dbname``

    This dialect subclasses :class:`CubridDialect` and overrides only
    the driver-specific methods: ``import_dbapi``, ``create_connect_args``,
    ``on_connect``, ``do_executemany``, and ``do_ping``.  All SQL
    compilation, type mapping, and schema reflection is inherited unchanged.
    """

    driver = "pycubrid"
    supports_statement_cache = True
    execution_ctx_cls = PyCubridExecutionContext

    # pycubrid uses qmark paramstyle natively
    default_paramstyle = "qmark"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Isolation level last applied to each DBAPI connection, re-applied
        # after every driver commit/rollback in case pycubrid replaced the CAS
        # session (#505, #559).
        self._connection_isolation_levels: weakref.WeakKeyDictionary[Any, str] = (
            weakref.WeakKeyDictionary()
        )
        # Connections whose re-apply failed after a successful commit/rollback;
        # do_begin() retries before the next transaction does any work.
        self._isolation_reapply_pending: weakref.WeakSet[Any] = weakref.WeakSet()

    @classmethod
    def import_dbapi(cls) -> DBAPIModule:
        """Import and return the pycubrid DBAPI module."""
        dbapi_module = import_module("pycubrid")
        log.debug("Loaded pycubrid DBAPI (version %s)", getattr(dbapi_module, "__version__", "?"))
        return cast(DBAPIModule, dbapi_module)  # pyright: ignore[reportInvalidCast]

    def create_connect_args(self, url: URL) -> ConnectArgsType:
        """Build DB-API connection arguments for pycubrid.

        pycubrid accepts keyword arguments directly::

            pycubrid.connect(host=..., port=..., database=..., user=..., password=...)
        """
        if url is None:
            raise ValueError("Unexpected database URL format")

        opts = url.translate_connect_args(username="user", database="database")
        kwargs = {
            "host": opts.get("host", "localhost"),
            "port": opts.get("port", 33000),
            "database": opts.get("database", ""),
            "user": opts.get("user", "dba"),
            "password": opts.get("password", ""),
        }
        log.debug(
            "connect args: host=%s port=%s database=%s user=%s",
            kwargs["host"],
            kwargs["port"],
            kwargs["database"],
            kwargs["user"],
        )
        return (), kwargs

    def on_connect(self) -> Callable[[Any], None] | None:
        """Return a callable to set up a new pycubrid connection.

        Disables autocommit so that SQLAlchemy manages transactions.
        SQLAlchemy applies an engine-level ``isolation_level`` after this hook.
        """

        def connect(conn: Any) -> None:
            # pycubrid uses a property setter for autocommit
            conn.autocommit = False
            log.debug("on_connect: autocommit=False")

        return connect

    def set_isolation_level(self, dbapi_connection: DBAPIConnection, level: str) -> None:
        """Set the isolation level and remember it for :meth:`do_commit` / :meth:`do_rollback`."""
        super().set_isolation_level(dbapi_connection, level)
        if level.upper() == "AUTOCOMMIT":
            # pycubrid restores autocommit itself after its reconnect.
            self._connection_isolation_levels.pop(_unwrap(dbapi_connection), None)
        else:
            self._connection_isolation_levels[_unwrap(dbapi_connection)] = level

    def reset_isolation_level(self, dbapi_conn: DBAPIConnection) -> None:
        """Reset on checkin; stop re-applying when the engine has no configured level.

        Without an engine-level ``isolation_level`` the reset level is the
        server default, which a replaced pycubrid session also starts at, so the
        per-commit re-apply after a one-off per-connection override is dropped.
        """
        super().reset_isolation_level(dbapi_conn)  # type: ignore[no-untyped-call]  # unannotated in SQLAlchemy
        if self.isolation_level is None:
            raw_connection = _unwrap(dbapi_conn)
            self._connection_isolation_levels.pop(raw_connection, None)
            self._isolation_reapply_pending.discard(raw_connection)

    def do_begin(self, dbapi_connection: DBAPIConnection) -> None:
        """Retry a re-apply that failed at the previous commit/rollback (#505).

        Runs before any statement of the new transaction; if it fails again the
        error surfaces here, before the transaction does any work.
        """
        super().do_begin(dbapi_connection)  # type: ignore[no-untyped-call]  # unannotated in SQLAlchemy
        raw_connection = _unwrap(dbapi_connection)
        if raw_connection in self._isolation_reapply_pending:
            self._isolation_reapply_pending.discard(raw_connection)
            self._restore_isolation_level(raw_connection)

    def do_commit(self, dbapi_connection: DBAPIConnection) -> None:
        """Commit, then re-apply the connection's isolation level (#505)."""
        super().do_commit(dbapi_connection)  # type: ignore[no-untyped-call]  # unannotated in SQLAlchemy
        self._restore_isolation_level_after_end(dbapi_connection)

    def do_rollback(self, dbapi_connection: DBAPIConnection) -> None:
        """Roll back, then re-apply the connection's isolation level (#505)."""
        super().do_rollback(dbapi_connection)  # type: ignore[no-untyped-call]  # unannotated in SQLAlchemy
        self._restore_isolation_level_after_end(dbapi_connection)

    def _restore_isolation_level_after_end(self, dbapi_connection: DBAPIConnection) -> None:
        """Re-apply after a commit/rollback that succeeded; never raise from here.

        The transaction already ended: raising would report a committed
        transaction as failed (inviting a duplicate retry) or replace the
        exception that caused a rollback. A failure is logged and deferred to
        :meth:`do_begin`.
        """
        try:
            self._restore_isolation_level(dbapi_connection)
        except Exception:
            log.warning(
                "re-applying the isolation level after commit/rollback failed; "
                "retrying at the next transaction start",
                exc_info=True,
            )
            self._isolation_reapply_pending.add(_unwrap(dbapi_connection))

    def _restore_isolation_level(self, dbapi_connection: DBAPIConnection) -> None:
        """Re-apply the isolation level in case pycubrid replaced the CAS session.

        pycubrid 1.8.0, the minimum supported version, keeps the CAS session
        across ``commit()`` / ``rollback()`` (cubrid-lab/pycubrid#468, #472).
        It still opens a new session when the CAS itself went away out of
        transaction (for example a CAS restart after the transaction or a
        broker reset), and that session starts at the server default level
        with only ``autocommit`` restored. This re-apply is the first request
        after the transaction ends, so a CAS replaced at that point gets the
        level back before the next transaction. `CUBRIDdb` needs none of this.

        The re-apply (``SET TRANSACTION ISOLATION LEVEL`` + ``COMMIT``) runs
        once per commit/rollback, never per statement, and only on
        connections whose level was set through the dialect (engine- or
        connection-level ``isolation_level``); other connections pay nothing.
        Its SQL ``COMMIT`` leaves the CAS marked in transaction, so pycubrid
        does not silently reconnect such a connection at the default level if
        its CAS dies while idle: the next statement fails as a disconnect
        instead (see Known Issue 10 in ``docs/DRIVER_COMPAT.md``).
        """
        # SQLAlchemy passes a pool proxy to do_commit/do_rollback but the raw
        # DBAPI connection to set_isolation_level.
        raw_connection = _unwrap(dbapi_connection)
        level = self._connection_isolation_levels.get(raw_connection)
        if level is not None:
            super().set_isolation_level(raw_connection, level)

    def do_executemany(
        self,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any = None,
    ) -> None:
        """Use pycubrid's prepare-once ``executemany`` directly.

        Opts out of :meth:`CubridDialect.do_executemany`'s per-row CUBRIDdb
        guard: pycubrid binds ``None`` as NULL and reports the summed rowcount
        (#502). Also inherited by the async ``aiopycubrid`` dialect.
        """
        cursor.executemany(statement, parameters)

    def do_ping(self, dbapi_connection: DBAPIConnection) -> bool:
        """Ping using native pycubrid CHECK_CAS (FC=32). Requires pycubrid>=1.3.2."""
        return bool(dbapi_connection.ping(False))


dialect = PyCubridDialect
