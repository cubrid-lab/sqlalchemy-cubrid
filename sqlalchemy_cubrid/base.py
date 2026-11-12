# sqlalchemy_cubrid/base.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""CUBRID identifier preparation, execution context, and reserved words."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from sqlalchemy import types as sqltypes
from sqlalchemy.engine import default
from sqlalchemy.sql import compiler

log = logging.getLogger(__name__)

# CUBRID Reserved words
# https://www.cubrid.org/manual/en/11.0/sql/keyword.html
RESERVED_WORDS = frozenset(
    {
        "absolute",
        "action",
        "add",
        "add_months",
        "after",
        "all",
        "allocate",
        "alter",
        "and",
        "any",
        "are",
        "as",
        "asc",
        "assertion",
        "at",
        "attach",
        "attribute",
        "avg",
        "before",
        "between",
        "bigint",
        "bit",
        "bit_length",
        "blob",
        "boolean",
        "both",
        "breadth",
        "by",
        "call",
        "cascade",
        "cascaded",
        "case",
        "cast",
        "catalog",
        "change",
        "char",
        "character",
        "check",
        "class",
        "classes",
        "clob",
        "close",
        "coalesce",
        "collate",
        "collation",
        "column",
        "commit",
        "connect",
        "connect_by_iscycle",
        "connect_by_isleaf",
        "connect_by_root",
        "connection",
        "constraint",
        "constraints",
        "continue",
        "convert",
        "corresponding",
        "count",
        "create",
        "cross",
        "current",
        "current_date",
        "current_datetime",
        "current_time",
        "current_timestamp",
        "current_user",
        "cursor",
        "cycle",
        "data",
        "data_type",
        "database",
        "date",
        "datetime",
        "day",
        "day_hour",
        "day_millisecond",
        "day_minute",
        "day_second",
        "deallocate",
        "dec",
        "decimal",
        "declare",
        "default",
        "deferrable",
        "deferred",
        "delete",
        "depth",
        "desc",
        "describe",
        "descriptor",
        "diagnostics",
        "difference",
        "disconnect",
        "distinct",
        "distinctrow",
        "div",
        "do",
        "domain",
        "double",
        "duplicate",
        "drop",
        "each",
        "else",
        "elseif",
        "end",
        "equals",
        "escape",
        "evaluate",
        "except",
        "exception",
        "exec",
        "execute",
        "exists",
        "external",
        "extract",
        "false",
        "fetch",
        "file",
        "first",
        "float",
        "for",
        "foreign",
        "found",
        "from",
        "full",
        "function",
        "general",
        "get",
        "global",
        "go",
        "goto",
        "grant",
        "group",
        "having",
        "hour",
        "hour_millisecond",
        "hour_minute",
        "hour_second",
        "identity",
        "if",
        "ignore",
        "immediate",
        "in",
        "index",
        "indicator",
        "inherit",
        "initially",
        "inner",
        "inout",
        "input",
        "insert",
        "int",
        "integer",
        "intersect",
        "intersection",
        "interval",
        "into",
        "is",
        "isolation",
        "join",
        "key",
        "language",
        "last",
        "leading",
        "leave",
        "left",
        "less",
        "level",
        "like",
        "limit",
        "list",
        "local",
        "local_transaction_id",
        "localtime",
        "localtimestamp",
        "loop",
        "lower",
        "match",
        "max",
        "method",
        "millisecond",
        "min",
        "minute",
        "minute_millisecond",
        "minute_second",
        "mod",
        "modify",
        "module",
        "month",
        "multiset",
        "multiset_of",
        "na",
        "names",
        "national",
        "natural",
        "nchar",
        "next",
        "no",
        "none",
        "not",
        "null",
        "nullif",
        "numeric",
        "object",
        "octet_length",
        "of",
        "off",
        "on",
        "only",
        "open",
        "optimization",
        "option",
        "or",
        "order",
        "out",
        "outer",
        "output",
        "overlaps",
        "parameters",
        "partial",
        "position",
        "precision",
        "prepare",
        "preserve",
        "primary",
        "prior",
        "privileges",
        "procedure",
        "query",
        "read",
        "real",
        "recursive",
        "ref",
        "references",
        "referencing",
        "relative",
        "rename",
        "replace",
        "resignal",
        "restrict",
        "return",
        "returns",
        "revoke",
        "right",
        "role",
        "rollback",
        "rollup",
        "routine",
        "row",
        "rownum",
        "rows",
        "savepoint",
        "schema",
        "scope",
        "scroll",
        "search",
        "second",
        "second_millisecond",
        "section",
        "select",
        "sensitive",
        "sequence",
        "sequence_of",
        "serializable",
        "session",
        "session_user",
        "set",
        "set_of",
        "seteq",
        "shared",
        "siblings",
        "signal",
        "similar",
        "size",
        "smallint",
        "some",
        "sql",
        "sqlcode",
        "sqlerror",
        "sqlexception",
        "sqlstate",
        "sqlwarning",
        "statistics",
        "string",
        "subclass",
        "subset",
        "subseteq",
        "substring",
        "sum",
        "superclass",
        "superset",
        "superseteq",
        "sys_connect_by_path",
        "sys_date",
        "sys_datetime",
        "sys_time",
        "sys_timestamp",
        "sysdate",
        "sysdatetime",
        "system_user",
        "systime",
        "table",
        "temporary",
        "then",
        "time",
        "timestamp",
        "timezone_hour",
        "timezone_minute",
        "to",
        "trailing",
        "transaction",
        "translate",
        "translation",
        "trigger",
        "trim",
        "true",
        "truncate",
        "under",
        "union",
        "unique",
        "unknown",
        "update",
        "upper",
        "usage",
        "use",
        "user",
        "using",
        "utime",
        "value",
        "values",
        "varchar",
        "variable",
        "varying",
        "vclass",
        "view",
        "when",
        "whenever",
        "where",
        "while",
        "with",
        "without",
        "work",
        "write",
        "xor",
        "year",
        "year_month",
        "zone",
    }
)


class CubridIdentifierPreparer(compiler.IdentifierPreparer):
    """Quoting logic for CUBRID identifiers."""

    reserved_words = set(RESERVED_WORDS)

    def __init__(
        self,
        dialect: Any,
        initial_quote: str = '"',
        final_quote: str | None = None,
        escape_quote: str = '"',
        omit_schema: bool = False,
    ) -> None:
        super().__init__(dialect, initial_quote, final_quote, escape_quote, omit_schema)


# DB-API type code CUBRIDdb reports in cursor.description for a BIGINT column
# (CUBRIDdb.FIELD_TYPE.BIGINT, the CCI U_TYPE_BIGINT value).
_CUBRIDDB_BIGINT_TYPE_CODE = 21


class CubridExecutionContext(default.DefaultExecutionContext):
    """Execution context for CUBRID connections."""

    def get_result_processor(
        self, type_: Any, colname: str, coltype: Any
    ) -> Optional[Callable[[Any], Any]]:
        """Convert BIGINT values that CUBRIDdb older than 11.3 returns as ``str``.

        Those releases fetch BIGINT, ``COUNT(*)`` and ``ROWNUM`` values as
        decimal strings (``'5'``), while CUBRIDdb 11.3 and pycubrid return
        ``int`` (#1145). Only a ``str`` value in a column that the driver
        reports as BIGINT and that SQLAlchemy types as an integer or leaves
        untyped is converted, before the type's own result processor runs.
        Text from any other column or type is never parsed, and DDL, casts and
        bind processing are unaffected.
        """
        processor = super().get_result_processor(type_, colname, coltype)
        if not (
            getattr(self.dialect, "_bigint_results_as_str", False)
            and coltype == _CUBRIDDB_BIGINT_TYPE_CODE
            and type_._type_affinity in (sqltypes.Integer, sqltypes.NullType)
        ):
            return processor

        def process(value: Any) -> Any:
            if isinstance(value, str):
                value = int(value)
            return processor(value) if processor is not None else value

        return process

    def get_lastrowid(self) -> int | None:  # type: ignore[override]
        """Return the last inserted row ID.

        CUBRID's Python driver does not expose ``cursor.lastrowid``.
        Instead, the connection object provides ``get_last_insert_id()``.
        We also fall back to ``SELECT LAST_INSERT_ID()`` if the method
        is unavailable.
        """
        try:
            # CUBRID Python driver exposes this on the raw connection
            raw_conn = self.root_connection.connection.dbapi_connection
            if raw_conn is not None and hasattr(raw_conn, "get_last_insert_id"):
                last_id = raw_conn.get_last_insert_id()
                return None if last_id is None else int(last_id)
        except Exception:  # nosec B110 — fallback to SQL when driver lacks method
            log.debug("get_last_insert_id via driver failed, falling back to SQL", exc_info=True)

        # Fallback: use SQL function
        cursor = self._dbapi_connection.cursor()
        try:
            cursor.execute("SELECT LAST_INSERT_ID()")
            row = cursor.fetchone()
            # LAST_INSERT_ID() is NULL until the connection has inserted into an
            # AUTO_INCREMENT column. SQLAlchemy asks for lastrowid after every
            # single-row INSERT, including tables without one (#1302).
            if row and row[0] is not None:
                return int(row[0])
        finally:
            cursor.close()
        return None
