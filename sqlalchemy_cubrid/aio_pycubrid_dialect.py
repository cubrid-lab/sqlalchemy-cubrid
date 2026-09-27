# sqlalchemy_cubrid/aio_pycubrid_dialect.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from __future__ import annotations

from importlib import import_module
from typing import Any, Callable, cast

from sqlalchemy.connectors.asyncio import (
    AsyncAdapt_dbapi_connection,
    AsyncAdapt_dbapi_cursor,
)

# AsyncAdapt_dbapi_module was added in SQLAlchemy 2.1.
try:
    from sqlalchemy.connectors.asyncio import AsyncAdapt_dbapi_module
except ImportError:  # pragma: no cover — SA 2.0
    AsyncAdapt_dbapi_module = object  # type: ignore[assignment,misc]
from sqlalchemy import pool as pool_module
from sqlalchemy.engine.interfaces import ConnectArgsType
from sqlalchemy_cubrid._compat import DBAPIModule
from sqlalchemy.engine.url import URL
from sqlalchemy.util.concurrency import await_only

from sqlalchemy_cubrid.pycubrid_dialect import PyCubridDialect, PyCubridExecutionContext


class AsyncAdapt_pycubrid_cursor(AsyncAdapt_dbapi_cursor):
    _awaitable_cursor_close: bool = True

    def setinputsizes(self, *inputsizes: Any) -> None:
        pass

    def nextset(self) -> None:
        pass


class AsyncAdapt_pycubrid_connection(AsyncAdapt_dbapi_connection):
    _cursor_cls = AsyncAdapt_pycubrid_cursor
    # SA 2.0 exposed ``await_`` on AsyncAdapt_dbapi_connection; SA 2.1 dropped
    # it in favour of the module-level helper. Redeclare so ``self.await_(...)``
    # works on both versions and remains patchable in tests.
    await_ = staticmethod(await_only)

    @property
    def autocommit(self) -> bool:
        return bool(self._connection.autocommit)

    @autocommit.setter
    def autocommit(self, value: bool) -> None:
        self.await_(self._connection.set_autocommit(value))

    def ping(self, reconnect: bool = True) -> bool:
        return bool(self.await_(self._connection.ping(reconnect)))


class AsyncAdapt_pycubrid_dbapi(AsyncAdapt_dbapi_module):
    def __init__(self, aio_module: Any) -> None:
        self._aio_module = aio_module

        sync_module = import_module("pycubrid")

        self.paramstyle = sync_module.paramstyle
        self.Error = sync_module.Error
        self.OperationalError = sync_module.OperationalError
        self.InterfaceError = sync_module.InterfaceError
        self.IntegrityError = sync_module.IntegrityError
        self.ProgrammingError = sync_module.ProgrammingError
        self.DatabaseError = sync_module.DatabaseError
        self.InternalError = sync_module.InternalError
        self.DataError = sync_module.DataError
        self.NotSupportedError = sync_module.NotSupportedError
        self.Warning = sync_module.Warning

        self.STRING = sync_module.STRING
        self.BINARY = sync_module.BINARY
        self.NUMBER = sync_module.NUMBER
        self.DATETIME = sync_module.DATETIME
        self.ROWID = sync_module.ROWID

    def connect(self, *arg: Any, **kw: Any) -> AsyncAdapt_pycubrid_connection:
        creator_fn = kw.pop("async_creator_fn", self._aio_module.connect)
        async_conn = await_only(creator_fn(*arg, **kw))
        return AsyncAdapt_pycubrid_connection(self, async_conn)


class PyCubridAsyncDialect(PyCubridDialect):
    driver = "aiopycubrid"
    is_async = True
    supports_statement_cache = True
    execution_ctx_cls = PyCubridExecutionContext

    @classmethod
    def get_pool_class(cls, url: URL) -> type[pool_module.Pool]:
        return pool_module.AsyncAdaptedQueuePool

    @classmethod
    def import_dbapi(cls) -> DBAPIModule:
        aio_module = import_module("pycubrid.aio")

        return cast(DBAPIModule, AsyncAdapt_pycubrid_dbapi(aio_module))

    def create_connect_args(self, url: URL) -> ConnectArgsType:
        if url is None:
            raise ValueError("Unexpected database URL format")

        opts = url.translate_connect_args(username="user", database="database")
        return (), {
            "host": opts.get("host", "localhost"),
            "port": opts.get("port", 33000),
            "database": opts.get("database", ""),
            "user": opts.get("user", "dba"),
            "password": opts.get("password", ""),
        }

    def on_connect(self) -> Callable[[Any], None] | None:
        isolation_level = self.isolation_level

        def connect(conn: Any) -> None:
            conn.autocommit = False
            if isolation_level is not None:
                self.set_isolation_level(conn, isolation_level)

        return connect

    def do_ping(self, dbapi_connection: Any) -> bool:
        return bool(dbapi_connection.ping(False))


dialect = PyCubridAsyncDialect
