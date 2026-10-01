"""Kill only a query owned by this test's dedicated CUBRID account (#634)."""

from __future__ import annotations

import re
import sys
import time
from typing import Any

import sqlalchemy as sa

_OWNED_USER = re.compile(r"kq634_[0-9a-f]{16}\Z")


def running_targets(cursor: Any, username: str) -> set[int]:
    """Return active transaction indexes for exactly *username*.

    SHOW TRANSACTION TABLES exposes the authenticated database user, unlike
    Client_info or Client_pid. An idle transaction has no Query_start_time.
    Missing columns or malformed indexes are errors, never a fallback to
    selecting a transaction by timing or by another client's attributes.
    """
    if _OWNED_USER.fullmatch(username) is None:
        raise ValueError("KILL QUERY target must be a generated kq634_ account")
    cursor.execute("SHOW TRANSACTION TABLES")
    columns = [str(column[0]).casefold() for column in cursor.description]
    required = ("tran_index", "client_db_user", "query_start_time")
    missing = [name for name in required if name not in columns]
    if missing:
        raise RuntimeError(f"SHOW TRANSACTION TABLES omits {', '.join(missing)}")
    index, user, started = (columns.index(name) for name in required)

    targets: set[int] = set()
    for row in cursor.fetchall():
        if str(row[user]).strip().casefold() != username or row[started] is None:
            continue
        tran_index = row[index]
        if type(tran_index) is not int or tran_index <= 0:
            raise RuntimeError(f"invalid tran_index for {username}: {tran_index!r}")
        targets.add(tran_index)
    return targets


def kill_unique_query(cursor: Any, username: str) -> bool:
    """Kill one owned active query, wait on zero, or fail on ambiguity."""
    targets = running_targets(cursor, username)
    if len(targets) > 1:
        raise RuntimeError(f"multiple active queries for {username}; refusing KILL QUERY")
    if not targets:
        return False
    # KILL has no bind parameter; the index was validated as a positive int.
    cursor.execute("KILL QUERY " + str(targets.pop()))
    return True


def main(url: str, username: str) -> int:
    if _OWNED_USER.fullmatch(username) is None:
        raise ValueError("KILL QUERY target must be a generated kq634_ account")
    engine = sa.create_engine(url, poolclass=sa.pool.NullPool)
    raw = None
    cursor = None
    try:
        raw = engine.raw_connection()
        cursor = raw.cursor()
        # Establish the catalog contract before telling the parent to start
        # its already-connected victim statement.
        running_targets(cursor, username)
        print("ready", flush=True)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if kill_unique_query(cursor, username):
                print("killed", flush=True)
                return 0
            time.sleep(0.1)
        raise RuntimeError(f"no active query for owned account {username} within 30 seconds")
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            try:
                if raw is not None:
                    raw.close()
            finally:
                engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python -m test._kill_query CUBRID_URL OWNED_USER")
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
