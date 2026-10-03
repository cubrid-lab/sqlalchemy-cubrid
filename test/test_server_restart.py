# test/test_server_restart.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""The pool recovers when cub_server stops or restarts under it (#565).

Stopping cub_server fails a connection that is inside a transaction with
-111 (``ER_TM_SERVER_DOWN_UNILATERALLY_ABORTED``) and then -224
(``ER_OBJ_NO_CONNECT``) on every statement until the transaction ends, even
after cub_server is back.  An idle pycubrid connection fails its CHECK_CAS
reconnect while the server is down.  ``is_disconnect()`` must classify these
errors so SQLAlchemy invalidates the connection and the pool hands out a
fresh one, with and without ``pool_pre_ping``, through both drivers.

These tests stop and start cub_server inside a Docker container, so they
need ``CUBRID_TEST_URL`` and ``CUBRID_TEST_DOCKER_CONTAINER`` (the name or
ID of the container that serves that URL), e.g.::

    export CUBRID_TEST_URL="cubrid://dba@localhost:33000/testdb"
    export CUBRID_TEST_DOCKER_CONTAINER=<container>

They run ``docker exec -u cubrid <container> bash -lc "cubrid server
stop|start <db>"``, as the ``cubrid/cubrid`` images allow.  Without the
container, or with a driver that cannot connect, they skip locally.  The CI
step sets ``CUBRID_REQUIRE_SERVER_RESTART=1``, which turns every such skip
into a failure.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import time
from collections.abc import Callable, Iterator
from typing import Any, NoReturn

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.integration

_DEFAULT_URL = "cubrid://dba@localhost:33000/testdb"
_REQUIRE_ENV = "CUBRID_REQUIRE_SERVER_RESTART"
_CONTAINER_ENV = "CUBRID_TEST_DOCKER_CONTAINER"
_DRIVERS = {"CUBRIDdb": "cubrid", "pycubrid": "cubrid+pycubrid"}
_READY_TIMEOUT = 120.0
_SELECT_1 = sa.text("SELECT 1")


def _unavailable(reason: str) -> NoReturn:
    """Skip locally; fail in the required CI step (``CUBRID_REQUIRE_SERVER_RESTART=1``)."""
    if os.environ.get(_REQUIRE_ENV) == "1":
        pytest.fail(f"{_REQUIRE_ENV}=1 but {reason}", pytrace=False)
    pytest.skip(reason)


def _base_url() -> sa.engine.URL:
    return sa.engine.make_url(os.environ.get("CUBRID_TEST_URL", _DEFAULT_URL))


def _can_connect(url: sa.engine.URL) -> bool:
    try:
        # create_engine() raises ImportError when the driver is not installed.
        engine = sa.create_engine(url, poolclass=sa.pool.NullPool)
    except Exception:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(_SELECT_1)
        return True
    except Exception:
        return False
    finally:
        engine.dispose()


def _docker_exec(container: str, command: str) -> subprocess.CompletedProcess[str]:
    """Run *command* as the ``cubrid`` user in a login shell inside *container*."""
    return subprocess.run(  # noqa: S603 - container name comes from the test environment
        ["docker", "exec", "-u", "cubrid", container, "bash", "-lc", command],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )


class _Server:
    """Stop and start cub_server for the test database inside its container."""

    def __init__(self, container: str, url: sa.engine.URL) -> None:
        self.container = container
        self.url = url
        self.db = shlex.quote(str(url.database))
        # Set by ``driver_url``: the driver the current test uses.
        self.ready_url: sa.engine.URL | None = None
        self.stopped = False

    def _cubrid(self, action: str) -> None:
        result = _docker_exec(self.container, f"cubrid server {action} {self.db}")
        if result.returncode != 0:
            pytest.fail(
                f"cubrid server {action} failed (rc={result.returncode}):\n"
                f"{result.stdout}\n{result.stderr}",
                pytrace=False,
            )

    def stop(self) -> None:
        self.stopped = True
        self._cubrid("stop")

    def start(self) -> None:
        self._cubrid("start")
        self.stopped = False
        self.wait_ready()

    def restart(self) -> None:
        self.stop()
        self.start()

    def wait_ready(self) -> None:
        """Wait until the server answers csql, then the test's driver.

        csql (the service container's healthcheck) needs no Python driver.
        Right after "cubrid server start" returns, broker connections can
        still fail for a few seconds, so the test's own driver is probed too.
        """
        deadline = time.monotonic() + _READY_TIMEOUT
        csql = f"csql -u dba {self.db} -c 'SELECT 1'"
        while _docker_exec(self.container, csql).returncode != 0:
            if time.monotonic() > deadline:
                pytest.fail(f"cub_server did not answer csql within {_READY_TIMEOUT}s")
            time.sleep(1)
        while self.ready_url is not None and not _can_connect(self.ready_url):
            if time.monotonic() > deadline:
                pytest.fail(f"cub_server did not accept connections within {_READY_TIMEOUT}s")
            time.sleep(1)


def _container() -> str:
    container = os.environ.get(_CONTAINER_ENV)
    if not container:
        _unavailable(f"{_CONTAINER_ENV} not set")
    try:
        subprocess.run(  # noqa: S603 - container name comes from the test environment
            ["docker", "exec", container, "true"],
            check=True,
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _unavailable(f"cannot docker exec into {container!r}: {exc}")
    return container


@pytest.fixture(scope="module", autouse=True)
def _server_started_after_module() -> Iterator[None]:
    """Whatever happened, leave cub_server running for later test modules."""
    yield
    container = os.environ.get(_CONTAINER_ENV)
    if container:
        try:
            _docker_exec(container, f"cubrid server start {shlex.quote(str(_base_url().database))}")
        except (OSError, subprocess.SubprocessError):
            pass  # best effort; the per-test teardown reports real failures


@pytest.fixture
def server() -> Iterator[_Server]:
    srv = _Server(_container(), _base_url())
    yield srv
    if srv.stopped:
        # A failed test must not leave the server down for the next test.
        try:
            _docker_exec(srv.container, f"cubrid server start {srv.db}")
        except (OSError, subprocess.SubprocessError) as exc:
            pytest.fail(f"could not restart cub_server after the test: {exc}", pytrace=False)
        srv.wait_ready()


@pytest.fixture(params=sorted(_DRIVERS))
def driver_url(request: pytest.FixtureRequest, server: _Server) -> sa.engine.URL:
    url = server.url.set(drivername=_DRIVERS[request.param])
    if not _can_connect(url):
        _unavailable(f"{request.param} cannot connect to {url.render_as_string()}")
    server.ready_url = url
    return url


@pytest.fixture(params=[False, True], ids=["no_pre_ping", "pre_ping"])
def engine_factory(
    request: pytest.FixtureRequest, driver_url: sa.engine.URL
) -> Iterator[Callable[[], sa.engine.Engine]]:
    engines: list[sa.engine.Engine] = []

    def make() -> sa.engine.Engine:
        # One pooled connection: a broken one cannot hide behind another.
        engine = sa.create_engine(
            driver_url, pool_size=1, max_overflow=0, pool_pre_ping=request.param
        )
        engines.append(engine)
        return engine

    yield make
    for engine in engines:
        engine.dispose()


def _error_code(exc: DBAPIError) -> Any:
    orig = exc.orig
    errno = getattr(orig, "errno", None)  # pycubrid
    if errno is not None:
        return errno
    return orig.args[0] if orig.args else None  # CUBRIDdb


def _dbapi_connection(conn: sa.engine.Connection) -> Any:
    return conn.connection.dbapi_connection


def test_restart_mid_transaction_invalidates(
    server: _Server, engine_factory: Callable[[], sa.engine.Engine]
) -> None:
    """-111 after a restart invalidates the connection; the next use reconnects.

    Without the invalidation, the CAS keeps answering -224 on this connection
    until the transaction ends.
    """
    engine = engine_factory()
    conn = engine.connect()
    try:
        conn.execute(_SELECT_1)  # autobegin: the CAS is now in a transaction
        old = _dbapi_connection(conn)
        server.restart()

        with pytest.raises(DBAPIError) as info:
            conn.execute(_SELECT_1)
        assert _error_code(info.value) == -111
        assert info.value.connection_invalidated

        conn.rollback()
        assert conn.execute(_SELECT_1).scalar() == 1
        assert _dbapi_connection(conn) is not old
    finally:
        conn.close()

    with engine.connect() as conn:
        assert conn.execute(_SELECT_1).scalar() == 1


def test_stop_mid_transaction_invalidates(
    server: _Server, engine_factory: Callable[[], sa.engine.Engine]
) -> None:
    """A statement failing while cub_server is down invalidates; the pool recovers."""
    engine = engine_factory()
    conn = engine.connect()
    try:
        conn.execute(_SELECT_1)
        old = _dbapi_connection(conn)
        server.stop()

        with pytest.raises(DBAPIError) as info:
            conn.execute(_SELECT_1)
        assert _error_code(info.value) == -111
        assert info.value.connection_invalidated
    finally:
        conn.close()

    server.start()
    with engine.connect() as conn:
        assert conn.execute(_SELECT_1).scalar() == 1
        assert _dbapi_connection(conn) is not old


def test_stop_while_idle_invalidates(
    server: _Server, engine_factory: Callable[[], sa.engine.Engine]
) -> None:
    """An idle pooled connection is invalidated while cub_server is down; the pool recovers."""
    engine = engine_factory()
    with engine.connect() as conn:
        conn.execute(_SELECT_1)
        conn.commit()
    server.stop()

    # Depending on driver and pool_pre_ping this fails at checkout (the ping
    # and the reconnect fail) or at the statement; either way it is a
    # disconnect.
    with pytest.raises(DBAPIError) as info:
        with engine.connect() as conn:
            conn.execute(_SELECT_1)
    assert info.value.connection_invalidated

    server.start()
    with engine.connect() as conn:
        assert conn.execute(_SELECT_1).scalar() == 1


def test_stop_after_commit_invalidates(
    server: _Server, engine_factory: Callable[[], sa.engine.Engine]
) -> None:
    """A checked-out connection idle after COMMIT is invalidated while cub_server is down.

    pycubrid probes the CAS with CHECK_CAS before the next statement, fails to
    reconnect and closes the connection.
    """
    engine = engine_factory()
    conn = engine.connect()
    try:
        conn.execute(_SELECT_1)
        conn.commit()
        server.stop()

        with pytest.raises(DBAPIError) as info:
            conn.execute(_SELECT_1)
        assert info.value.connection_invalidated
    finally:
        conn.close()

    server.start()
    with engine.connect() as conn:
        assert conn.execute(_SELECT_1).scalar() == 1
