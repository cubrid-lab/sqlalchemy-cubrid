# sqlalchemy_cubrid/aio_pycubrid_dialect.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from __future__ import annotations

import contextlib
import logging
from importlib import import_module
from typing import TYPE_CHECKING, Any, cast

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
from sqlalchemy_cubrid._compat import DBAPIModule
from sqlalchemy.engine.url import URL
from sqlalchemy.util.concurrency import await_only

from sqlalchemy_cubrid.pycubrid_dialect import PyCubridDialect, PyCubridExecutionContext

# AsyncAdapt_terminate (terminate support for garbage-collected connections)
# arrived in SQLAlchemy 2.0.44; before it the pool keeps its "cannot be safely
# terminated" fallback.
if TYPE_CHECKING:
    from sqlalchemy.connectors.asyncio import AsyncAdapt_terminate as _TerminateMixin

    _HAS_TERMINATE = True
else:
    try:
        from sqlalchemy.connectors.asyncio import AsyncAdapt_terminate as _TerminateMixin

        _HAS_TERMINATE = True
    except ImportError:  # SQLAlchemy 2.0.0 to 2.0.43

        class _TerminateMixin:
            """Empty stand-in: ``object`` itself would give an inconsistent MRO."""

        _HAS_TERMINATE = False

_LOGGER = logging.getLogger(__name__)


class AsyncAdapt_pycubrid_cursor(AsyncAdapt_dbapi_cursor):
    _awaitable_cursor_close: bool = True

    def setinputsizes(self, *inputsizes: Any) -> None:
        pass

    def nextset(self) -> None:
        pass


class AsyncAdapt_pycubrid_connection(_TerminateMixin, AsyncAdapt_dbapi_connection):
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

    async def _terminate_graceful_close(self) -> None:
        # Invalidation inside a greenlet: the normal CLOSE_DATABASE shutdown.
        await self._connection.close()

    def _terminate_force_close(self) -> None:
        # Garbage-collection cleanup outside a greenlet (#872): nothing can be
        # awaited, so close the socket synchronously and mark the session
        # disconnected, which is what pycubrid's own failure path does.
        driver = self._connection
        transport = getattr(getattr(driver, "_writer", None), "transport", None)
        try:
            driver._drop_connection()
            return
        except (OSError, RuntimeError):
            _LOGGER.debug("Suppressed error force-closing a pycubrid.aio connection", exc_info=True)
        # The event loop that owned the transport is closed: StreamWriter.close()
        # could not schedule connection_lost, so _drop_connection() stopped
        # before retiring the session. Close the socket and retire it here.
        sock = getattr(transport, "_sock", None)
        if transport is not None and sock is not None:
            with contextlib.suppress(OSError):
                sock.close()
            transport._sock = None
        driver._connected = False
        invalidate = getattr(driver, "_invalidate_query_handles", None)
        if invalidate is not None:
            invalidate()


# PEP 249 module-level names copied from the sync ``pycubrid`` module onto the
# async adapter. SQLAlchemy reads several of these from ``dialect.dbapi`` (e.g.
# ``LargeBinary``'s bind processor reads ``Binary``), so the adapter must expose
# the same surface as ``pycubrid`` itself.
PEP249_MODULE_NAMES: tuple[str, ...] = (
    "apilevel",
    "threadsafety",
    "paramstyle",
    "Warning",
    "Error",
    "InterfaceError",
    "DatabaseError",
    "DataError",
    "OperationalError",
    "IntegrityError",
    "InternalError",
    "ProgrammingError",
    "NotSupportedError",
    "Date",
    "Time",
    "Timestamp",
    "DateFromTicks",
    "TimeFromTicks",
    "TimestampFromTicks",
    "Binary",
    "STRING",
    "BINARY",
    "NUMBER",
    "DATETIME",
    "ROWID",
)


class AsyncAdapt_pycubrid_dbapi(AsyncAdapt_dbapi_module):
    def __init__(self, aio_module: Any) -> None:
        self._aio_module = aio_module

        sync_module = import_module("pycubrid")
        for name in PEP249_MODULE_NAMES:
            setattr(self, name, getattr(sync_module, name))

    def connect(self, *arg: Any, **kw: Any) -> AsyncAdapt_pycubrid_connection:
        creator_fn = kw.pop("async_creator_fn", self._aio_module.connect)
        async_conn = await_only(creator_fn(*arg, **kw))
        return AsyncAdapt_pycubrid_connection(self, async_conn)


class PyCubridAsyncDialect(PyCubridDialect):
    """Async variant of :class:`PyCubridDialect` over ``pycubrid.aio``.

    Only the async plumbing lives here: the DB-API adapter, the pool class
    and :meth:`get_driver_connection`. Every driver policy (``on_connect``,
    ``do_ping``, ``do_executemany``, isolation re-apply, disconnect
    classification) is inherited from the sync dialect and reaches
    ``pycubrid.aio`` through :class:`AsyncAdapt_pycubrid_connection`, whose
    ``autocommit`` setter and ``ping()`` await the async driver.
    """

    driver = "aiopycubrid"
    is_async = True
    has_terminate = _HAS_TERMINATE
    supports_statement_cache = True
    execution_ctx_cls = PyCubridExecutionContext

    @classmethod
    def get_pool_class(cls, url: URL) -> type[pool_module.Pool]:
        return pool_module.AsyncAdaptedQueuePool

    @classmethod
    def import_dbapi(cls) -> DBAPIModule:
        aio_module = import_module("pycubrid.aio")

        return cast(DBAPIModule, AsyncAdapt_pycubrid_dbapi(aio_module))

    def do_terminate(self, dbapi_connection: Any) -> None:
        """Terminate a connection the pool cannot close normally (#872)."""
        dbapi_connection.terminate()

    def get_driver_connection(self, connection: Any) -> Any:
        # ``connection`` is the AsyncAdapt adapter; return the ``pycubrid.aio``
        # connection it wraps, as SQLAlchemy's asyncpg/aiomysql dialects do, so
        # ``driver_connection`` is the driver's own connection object.
        return connection._connection


dialect = PyCubridAsyncDialect
