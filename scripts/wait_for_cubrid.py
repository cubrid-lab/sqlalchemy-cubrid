"""Wait until the CUBRID at ``CUBRID_TEST_URL`` answers ``SELECT 1`` (#575).

``make integration`` runs this after ``docker compose up -d`` instead of a fixed
sleep. A fresh container creates its database and starts the broker first, which
takes about 20 seconds; tests that start earlier fail with connection errors, and
the live test modules that probe the server at import time skip themselves.

The probe connects through the driver that ``CUBRID_TEST_URL`` selects, so it
also fails early when that driver is not installed. Exits 0 once the server
answers, 1 when ``--timeout`` seconds pass first (or the URL or driver is
unusable). Credentials are never printed.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

# pycubrid accepts socket timeouts, so one attempt cannot hang on a server that
# accepts the connection but does not answer yet; CUBRIDdb takes no such options.
_PYCUBRID_TIMEOUTS = {"connect_timeout": 5, "read_timeout": 5}


def _probe(engine) -> None:  # noqa: ANN001
    with engine.connect() as connection:
        if connection.execute(text("SELECT 1")).scalar_one() != 1:
            raise RuntimeError("unexpected SELECT 1 result")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--timeout", type=float, default=180.0, help="seconds to wait")
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between attempts")
    args = parser.parse_args(argv)

    raw_url = os.environ.get("CUBRID_TEST_URL")
    if not raw_url:
        print("CUBRID_TEST_URL is not set", file=sys.stderr)
        return 1
    try:
        url = make_url(raw_url)
        connect_args = _PYCUBRID_TIMEOUTS if url.get_driver_name() == "pycubrid" else {}
        engine = create_engine(url, poolclass=NullPool, connect_args=connect_args)
    except Exception as exc:
        print(f"Cannot use CUBRID_TEST_URL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    target = url.render_as_string(hide_password=True)

    deadline = time.monotonic() + args.timeout
    attempt = 0
    try:
        while True:
            attempt += 1
            try:
                _probe(engine)
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {str(exc).splitlines()[0]}"
            else:
                print(f"CUBRID is ready at {target} (attempt {attempt})")
                return 0
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                print(
                    f"CUBRID at {target} was not ready after {args.timeout:g}s "
                    f"({attempt} attempts); last error: {last_error}",
                    file=sys.stderr,
                )
                return 1
            # Never sleep past the deadline: the last attempt runs at the deadline.
            time.sleep(min(args.interval, remaining))
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
