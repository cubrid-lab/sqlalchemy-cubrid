"""Evaluator-owned checks for the reflect-string-server-defaults task (#865).

The fake connection answers by statement text, not call order, so any
implementation that reads the recorded SHOW COLUMNS / SHOW CREATE TABLE rows can
pass. Copied into the candidate's worktree only by ``scripts/agent_eval.py run``.
"""

from __future__ import annotations

from sqlalchemy_cubrid.dialect import CubridDialect

COLUMNS = [
    ("q", "VARCHAR(20)", "YES", "", "it''s", ""),
    ("em", "VARCHAR(20)", "YES", "", "", ""),
    ("nl", "VARCHAR(20)", "YES", "", "NULL", ""),
    ("nn", "VARCHAR(20)", "YES", "", None, ""),
    ("d", "DATE", "YES", "", "01/02/2020", ""),
    ("w", "VARCHAR(20)", "YES", "", "CURRENT_USER", ""),
    # SHOW COLUMNS prints the string 'CURRENT_USER' and the function alike.
    ("w2", "VARCHAR(20)", "YES", "", "CURRENT_USER", ""),
    ("neg", "INTEGER", "YES", "", "-3", ""),
]
DDL = (
    "CREATE TABLE [d865] ([q] CHARACTER VARYING(20) DEFAULT 'it''s', "
    "[em] CHARACTER VARYING(20) DEFAULT '', [nl] CHARACTER VARYING(20) DEFAULT 'NULL', "
    "[nn] CHARACTER VARYING(20), [d] DATE DEFAULT date '01/02/2020', "
    "[w] CHARACTER VARYING(20) DEFAULT 'CURRENT_USER', "
    "[w2] CHARACTER VARYING(20) DEFAULT CURRENT_USER, [neg] INTEGER DEFAULT -3) "
    "REUSE_OID, COLLATE iso88591_bin"
)


class _Result:
    def __init__(self, rows):
        self._rows = list(rows)

    def __iter__(self):
        return iter(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)

    def fetchone(self):
        return self.first()

    def scalar(self):
        row = self.first()
        return None if row is None else row[0]


class _Connection:
    def execute(self, statement, *args, **kwargs):
        sql = str(statement).upper()
        if "SHOW COLUMNS" in sql:
            return _Result(COLUMNS)
        if "SHOW CREATE TABLE" in sql:
            return _Result([("d865", DDL)])
        if "CLASS_TYPE" in sql:
            return _Result([("CLASS", "DBA")])
        return _Result([])

    def exec_driver_sql(self, statement, *args, **kwargs):
        return self.execute(statement)


def _defaults():
    dialect = CubridDialect()
    method = dialect.get_columns
    method = getattr(method, "__wrapped__", None)
    connection = _Connection()
    columns = (
        method(dialect, connection, "d865") if method else dialect.get_columns(connection, "d865")
    )
    return {c["name"]: c["default"] for c in columns}


def test_string_and_date_defaults_reflect_as_sql_literals():
    defaults = _defaults()
    assert defaults["q"] == "'it''s'"
    assert defaults["em"] == "''"
    assert defaults["nl"] == "'NULL'"
    assert defaults["d"] == "date '01/02/2020'"
    assert defaults["w"] == "'CURRENT_USER'"


def test_a_function_default_stays_a_function():
    # Same SHOW COLUMNS text as the string above; only the DDL tells them apart.
    assert _defaults()["w2"].upper() in ("CURRENT_USER", "USER")


def test_missing_and_numeric_defaults_are_unchanged():
    defaults = _defaults()
    assert defaults["nn"] is None
    assert defaults["neg"] == "-3"
