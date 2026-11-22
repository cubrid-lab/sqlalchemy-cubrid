"""Live run of the published ``samples/async_basic.py`` on the integration lab (#1403).

The offline tests in ``test_samples_async_basic.py`` cover engine disposal with a
fake engine; these run the unmodified script as a user would
(``python samples/async_basic.py``) against the lab ``CUBRID_TEST_URL`` names, and
check what it did with independent SQL through the suite's own sync connection.

The sample drops and recreates the fixed-name ``async_sample_users`` table, so a
database that already has that table is never touched: the test skips. The script
is pointed at the lab only through ``CUBRID_SAMPLE_URL``; it never falls back to
``CUBRID_TEST_URL`` or to its own default address on its own.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
from collections.abc import Callable, Iterator
from importlib import metadata
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import URL, Engine
from sqlalchemy.pool import NullPool

import sqlalchemy_cubrid
from scripts import integration_urls as urls

REPO = Path(__file__).resolve().parents[1]
SAMPLE = REPO / "samples" / "async_basic.py"
SAMPLE_TABLE = "async_sample_users"
SAMPLE_TIMEOUT = 180

# The shared gate in test/conftest.py skips these tests when CUBRID_TEST_URL is
# unset and errors them when its server is unreachable (#593).
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def sync_engine() -> Iterator[Engine]:
    url = urls.configured_url()
    engine = sa.create_engine(url, poolclass=NullPool, connect_args=urls.connect_args(url))
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def sample_url() -> URL:
    # The sample is async-only (cubrid+aiopycubrid://), which needs pycubrid even
    # when the sync suite runs through CUBRIDdb.
    pytest.importorskip("pycubrid.aio")
    aurl, _ = urls.configured_async_url(urls.configured_url())
    return aurl


def _user_tables(engine: Engine) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(sa.text("SELECT class_name FROM db_class WHERE is_system_class = 'NO'"))
        return {row[0].lower() for row in rows}


def _versions(engine: Engine) -> str:
    with engine.connect() as conn:
        server = conn.execute(sa.text("SELECT VERSION()")).scalar_one()
    # The sample imports the checked-out dialect (see _run_sample), so report its
    # version rather than whichever copy happens to be installed.
    packages = (
        f"SQLAlchemy {sa.__version__}, sqlalchemy-cubrid {sqlalchemy_cubrid.__version__}, "
        f"pycubrid {metadata.version('pycubrid')}"
    )
    return f"CUBRID {server}; Python {sys.version.split()[0]}; {packages}"


class SampleRun:
    """The sample's exit code and output, with the lab password masked."""

    def __init__(self, returncode: int, stdout: str, stderr: str) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self) -> str:
        return f"exit code {self.returncode}\nstdout:\n{self.stdout}\nstderr:\n{self.stderr}"


def _redact(text: str | bytes | None, url: URL) -> str:
    if isinstance(text, bytes):
        text = text.decode(errors="replace")
    text = text or ""
    # Assertion messages reach CI logs and JUnit XML; a driver error could echo
    # the credential the sample was given, so mask it as error_summary() does.
    return text.replace(url.password, "***") if url.password else text


def _run_sample(url: URL) -> SampleRun:
    env = dict(os.environ)
    # Only CUBRID_SAMPLE_URL points the sample at a database; drop the suite's own
    # variables so the script cannot pick them up by accident.
    env.pop(urls.TEST_URL_VAR, None)
    env.pop(urls.ASYNC_URL_VAR, None)
    env["CUBRID_SAMPLE_URL"] = url.render_as_string(hide_password=False)
    # Import the checked-out dialect, not whatever copy happens to be installed.
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(REPO), env.get("PYTHONPATH")]))
    try:
        result = subprocess.run(
            [sys.executable, str(SAMPLE)],
            cwd=REPO,
            env=env,
            capture_output=True,
            text=True,
            timeout=SAMPLE_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(
            f"samples/async_basic.py did not finish within {SAMPLE_TIMEOUT}s\n"
            f"stdout:\n{_redact(exc.stdout, url)}\nstderr:\n{_redact(exc.stderr, url)}",
            pytrace=False,
        )
    return SampleRun(result.returncode, _redact(result.stdout, url), _redact(result.stderr, url))


def _closed_port() -> int:
    """A local port nothing listens on: bound once by the OS, then released."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_sample_runs_against_the_lab_and_drops_its_table(
    sync_engine: Engine, sample_url: URL, record_property: Callable[[str, object], None]
) -> None:
    before = _user_tables(sync_engine)
    if SAMPLE_TABLE in before:
        pytest.skip(
            f"{SAMPLE_TABLE} already exists in the integration database; the sample "
            "would drop it, so it is not run here"
        )
    versions = _versions(sync_engine)
    record_property("versions", versions)

    try:
        result = _run_sample(sample_url)
        record_property("sample_exit_code", result.returncode)

        assert result.returncode == 0, f"{versions}\n{result}"
        out = result.stdout
        assert "Connected! SELECT 1 = 1" in out, result
        assert "Inserted 2 rows." in out, result
        names = [line.split("name=", 1)[1].strip() for line in out.splitlines() if "name=" in line]
        assert names == ["Alice", "Bob"], result
        assert out.rstrip().endswith("Done!"), result

        # Independent check: the sample removed its own table and touched nothing else.
        assert _user_tables(sync_engine) == before
    finally:
        # The table did not exist before this run, so a sample that failed halfway
        # left it behind; drop it so later runs do not skip forever.
        if SAMPLE_TABLE in _user_tables(sync_engine):
            with sync_engine.begin() as conn:
                conn.execute(sa.text("DROP TABLE async_sample_users"))


def test_sample_reports_a_connection_failure_with_a_nonzero_exit(
    sync_engine: Engine, sample_url: URL
) -> None:
    before = _user_tables(sync_engine)
    unreachable = sample_url.set(host="127.0.0.1", port=_closed_port())

    result = _run_sample(unreachable)

    assert result.returncode != 0, result
    assert "Connected!" not in result.stdout, result
    assert "Done!" not in result.stdout, result
    # The failure is the refused connection, not some other crash (an import error
    # would also exit nonzero), and the lab itself is unchanged.
    assert "OperationalError" in result.stderr, result
    assert _user_tables(sync_engine) == before
