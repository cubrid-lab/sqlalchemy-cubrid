# sqlalchemy_cubrid/pycubrid_dialect.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""CUBRID dialect variant using the pycubrid pure-Python DB-API 2.0 driver."""

from __future__ import annotations

import logging
from importlib import import_module
from typing import Any, Callable, cast

from sqlalchemy.engine.interfaces import DBAPIConnection, ConnectArgsType
from sqlalchemy_cubrid._compat import DBAPIModule
from sqlalchemy.engine.url import URL

from sqlalchemy_cubrid.base import CubridExecutionContext
from sqlalchemy_cubrid.dialect import CubridDialect

log = logging.getLogger(__name__)


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
        cursor = self.create_server_side_cursor()
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
    ``on_connect``, and ``do_ping``.  All SQL compilation, type mapping,
    and schema reflection is inherited unchanged.
    """

    driver = "pycubrid"
    supports_statement_cache = True
    execution_ctx_cls = PyCubridExecutionContext

    # pycubrid uses qmark paramstyle natively
    default_paramstyle = "qmark"

    @classmethod
    def import_dbapi(cls) -> DBAPIModule:
        """Import and return the pycubrid DBAPI module."""
        try:
            dbapi_module = import_module("pycubrid")
        except ImportError as exc:  # pragma: no cover - exercised via message
            raise ImportError(
                "The bare 'cubrid://' URL uses the pure-Python pycubrid driver "
                "(since sqlalchemy-cubrid 2.0), but pycubrid is not installed. "
                "Install it with 'pip install sqlalchemy-cubrid[cubrid]' or "
                "'pip install sqlalchemy-cubrid[pycubrid]', or use the "
                "'cubrid+cubriddb://' URL (with the [cubriddb] extra) for the "
                "legacy CUBRIDdb C-extension driver."
            ) from exc
        dbapi_module = import_module("pycubrid")
        log.debug("Loaded pycubrid DBAPI (version %s)", getattr(dbapi_module, "__version__", "?"))
        return cast(DBAPIModule, dbapi_module)  # pyright: ignore[reportInvalidCast]

    # Keep legacy dbapi() for SA 1.x compat
    @classmethod
    def dbapi(cls) -> DBAPIModule:  # type: ignore[override]
        return cls.import_dbapi()

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
        """
        isolation_level = self.isolation_level

        def connect(conn: Any) -> None:
            # pycubrid uses a property setter for autocommit
            conn.autocommit = False
            if isolation_level is not None:
                self.set_isolation_level(conn, isolation_level)
            log.debug("on_connect: autocommit=False isolation_level=%s", isolation_level)

        return connect

    def do_ping(self, dbapi_connection: DBAPIConnection) -> bool:
        """Ping using native pycubrid CHECK_CAS (FC=32). Requires pycubrid>=1.3.2."""
        return bool(dbapi_connection.ping(False))


dialect = PyCubridDialect
