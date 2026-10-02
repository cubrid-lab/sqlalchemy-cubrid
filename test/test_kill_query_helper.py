"""Fail-closed KILL QUERY selection without a live or shared CUBRID server."""

from __future__ import annotations

import pytest
from sqlalchemy.engine import make_url

from test._kill_query import kill_unique_query, running_targets
from test.test_integration import _kill_query_victim_url


@pytest.mark.parametrize("admin_password", ["", "nonempty-dba-secret"])
@pytest.mark.parametrize("driver", ["cubrid", "cubrid+pycubrid"])
def test_victim_url_uses_its_own_passwordless_account(admin_password: str, driver: str) -> None:
    admin_url = make_url(f"{driver}://dba@db.example:33000/testdb?connect_timeout=5").set(
        password=admin_password
    )

    victim_url = _kill_query_victim_url(admin_url, "kq634_1234abcd5678ef90")

    assert victim_url.username == "kq634_1234abcd5678ef90"
    assert victim_url.password == ""
    assert victim_url.drivername == admin_url.drivername
    assert victim_url.host == admin_url.host
    assert victim_url.port == admin_url.port
    assert victim_url.database == admin_url.database
    assert victim_url.query == admin_url.query
    assert admin_url.username == "dba"
    assert admin_url.password == admin_password
    args, kwargs = victim_url.get_dialect()().create_connect_args(victim_url)
    if driver == "cubrid":
        assert args[1:] == ("kq634_1234abcd5678ef90", "")
    else:
        assert kwargs["user"] == "kq634_1234abcd5678ef90"
        assert kwargs["password"] == ""


class _TransactionCursor:
    def __init__(self, rows: list[tuple[object, ...]], columns: tuple[str, ...] | None = None):
        self.description = [(name,) for name in (columns or self.COLUMNS)]
        self.rows = rows
        self.statements: list[str] = []

    COLUMNS = ("Tran_index", "Client_db_user", "Query_start_time")

    def execute(self, statement: str) -> None:
        self.statements.append(statement)

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows


def test_selects_only_the_active_query_of_the_exact_victim_account() -> None:
    cursor = _TransactionCursor(
        [
            (41, "DBA", "2026-10-02 08:00:00"),  # unrelated slow query
            (42, "kq634_1234abcd5678ef90", None),  # same user's idle transaction
            (43, "KQ634_1234ABCD5678EF90", "2026-10-02 08:00:01"),
            (44, "kq634_99999999aaaaaaaa", "2026-10-02 08:00:02"),
        ]
    )

    assert running_targets(cursor, "kq634_1234abcd5678ef90") == {43}
    assert cursor.statements == ["SHOW TRANSACTION TABLES"]
    cursor.statements.clear()
    assert kill_unique_query(cursor, "kq634_1234abcd5678ef90") is True
    assert cursor.statements == ["SHOW TRANSACTION TABLES", "KILL QUERY 43"]


def test_zero_matches_waits_without_killing_any_query() -> None:
    cursor = _TransactionCursor([(41, "DBA", "2026-10-02 08:00:00")])
    assert kill_unique_query(cursor, "kq634_1234abcd5678ef90") is False
    assert cursor.statements == ["SHOW TRANSACTION TABLES"]


@pytest.mark.parametrize("username", [" kq634_1234abcd5678ef90", "kq634_1234abcd5678ef90 "])
def test_whitespace_changes_account_identity_and_cannot_select_a_victim(username: str) -> None:
    cursor = _TransactionCursor([(41, username, "2026-10-02 08:00:00")])
    assert kill_unique_query(cursor, "kq634_1234abcd5678ef90") is False
    assert cursor.statements == ["SHOW TRANSACTION TABLES"]


def test_multiple_active_queries_for_the_same_account_fail_closed() -> None:
    cursor = _TransactionCursor(
        [
            (43, "kq634_1234abcd5678ef90", "2026-10-02 08:00:01"),
            (44, "kq634_1234abcd5678ef90", "2026-10-02 08:00:02"),
        ]
    )
    with pytest.raises(RuntimeError, match="multiple active queries"):
        kill_unique_query(cursor, "kq634_1234abcd5678ef90")
    assert cursor.statements == ["SHOW TRANSACTION TABLES"]


@pytest.mark.parametrize("missing", _TransactionCursor.COLUMNS)
def test_missing_identity_or_start_column_fails_closed(missing: str) -> None:
    columns = tuple(name for name in _TransactionCursor.COLUMNS if name != missing)
    cursor = _TransactionCursor([(43, "kq634_1234abcd5678ef90", "2026-10-02 08:00:01")], columns)
    with pytest.raises(RuntimeError, match=missing.lower()):
        kill_unique_query(cursor, "kq634_1234abcd5678ef90")
    assert cursor.statements == ["SHOW TRANSACTION TABLES"]


@pytest.mark.parametrize("bad_index", [None, True, 0, -1, "43", "43; DROP USER DBA"])
def test_invalid_tran_index_cannot_reach_kill_statement(bad_index: object) -> None:
    cursor = _TransactionCursor([(bad_index, "kq634_1234abcd5678ef90", "started")])
    with pytest.raises(RuntimeError, match="invalid tran_index"):
        kill_unique_query(cursor, "kq634_1234abcd5678ef90")
    assert cursor.statements == ["SHOW TRANSACTION TABLES"]


@pytest.mark.parametrize("username", ["DBA", "kq634_1234abcd", "kq634_1234abcd5678ef90;--"])
def test_only_generated_account_names_can_be_targets(username: str) -> None:
    cursor = _TransactionCursor([])
    with pytest.raises(ValueError, match="generated kq634_"):
        kill_unique_query(cursor, username)
    assert cursor.statements == []
