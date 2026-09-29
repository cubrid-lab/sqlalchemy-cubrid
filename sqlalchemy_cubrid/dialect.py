# sqlalchemy_cubrid/dialect.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""CUBRID dialect for SQLAlchemy 2.0.

Schema reflection uses SQLAlchemy's standard :func:`~sqlalchemy.inspect` API::

    from sqlalchemy import create_engine, inspect

    engine = create_engine("cubrid+pycubrid://dba:pw@localhost:33000/demodb")
    insp = inspect(engine)
    insp.get_table_names()
    insp.get_columns("users")
    insp.get_pk_constraint("users")["constrained_columns"]
"""

from __future__ import annotations

import importlib.util
import logging
import re
import warnings

from typing import Any, Callable, Optional, Sequence, cast

from sqlalchemy import types as sqltypes
from sqlalchemy import util
from sqlalchemy.exc import ArgumentError, NoSuchTableError
from sqlalchemy.engine import default, reflection
from sqlalchemy.engine.interfaces import (
    DBAPIConnection,
    BindTyping,
    ConnectArgsType,
    IsolationLevel,
    ReflectedCheckConstraint,
    ReflectedColumn,
    ReflectedForeignKeyConstraint,
    ReflectedIndex,
    ReflectedPrimaryKeyConstraint,
    ReflectedTableComment,
    ReflectedUniqueConstraint,
)

from sqlalchemy_cubrid._compat import DBAPIModule
from sqlalchemy.engine.url import URL
from sqlalchemy.sql import text
from sqlalchemy.sql.elements import quoted_name
from sqlalchemy.sql.compiler import IdentifierPreparer
from sqlalchemy.sql.compiler import InsertmanyvaluesSentinelOpts

from sqlalchemy_cubrid.base import CubridExecutionContext, CubridIdentifierPreparer
from sqlalchemy_cubrid.compiler import (
    CubridCompiler,
    CubridDDLCompiler,
    CubridTypeCompiler,
)
from sqlalchemy_cubrid.types import (
    BIGINT,
    BIT,
    BLOB,
    CHAR,
    CLOB,
    DECIMAL,
    DOUBLE,
    DOUBLE_PRECISION,
    FLOAT,
    JSON,
    JSONIndexType,
    JSONPathType,
    MULTISET,
    NCHAR,
    NUMERIC,
    NVARCHAR,
    SEQUENCE,
    SET,
    SMALLINT,
    ENUM,
    STRING,
    TIMESTAMPLTZ,
    TIMESTAMPTZ,
    DATETIMELTZ,
    DATETIMETZ,
    VARCHAR,
)

from sqlalchemy.types import (
    DATE,
    DATETIME,
    INTEGER,
    TIME,
    TIMESTAMP,
)

log = logging.getLogger(__name__)


def _count_is_positive(count: Any) -> bool:
    """True if a catalog ``COUNT(*)`` result is greater than zero.

    ``COUNT(*)`` is ``BIGINT`` in CUBRID, and the ``CUBRID-Python`` releases
    on PyPI (9.3.x) fetch ``BIGINT`` as ``str``, so ``bool('0')`` would be
    ``True``. Coerce first, so ``int``, ``str``, ``Decimal`` and ``None`` all
    work (#583).
    """
    return int(count or 0) > 0


# Oldest CUBRIDdb release line the dialect is tested with: CI builds
# cubrid-python v11.3.0.51 from source. PyPI only has CUBRID-Python 9.3.x and
# older, which fetches BIGINT as str and fails parts of the integration suite
# (#583, #585). Only (major, minor) is compared: a source build's fourth
# component is a git commit count, not the release tag.
_MIN_TESTED_CUBRIDDB = (11, 3)


def _cubriddb_version(dbapi: Any) -> tuple[str, tuple[int, int]] | None:
    """Return the loaded CUBRIDdb C extension's version string and (major, minor).

    ``CUBRIDdb`` imports its ``_cubrid`` extension module, whose ``__version__``
    is the compiled-in driver version (``b'9.3.0.0001'`` from PyPI,
    ``b'11.3.0.0001'`` from a v11.3.0.51 source build). ``None`` if it is
    missing or unparseable.
    """
    raw = getattr(getattr(dbapi, "_cubrid", None), "__version__", None)
    if isinstance(raw, bytes):
        raw = raw.decode("ascii", "replace")
    if not isinstance(raw, str):
        return None
    m = re.match(r"(\d+)\.(\d+)", raw)
    if m is None:
        return None
    return raw, (int(m.group(1)), int(m.group(2)))


def _is_unknown_class_error(error: BaseException) -> bool:
    """True only for CUBRID's ``Unknown class "<owner>.<name>"`` error.

    Used to translate a driver error from a reflection query on a missing
    table or view into SQLAlchemy's ``NoSuchTableError``. The native code
    (-493) and SQLSTATE (42S02) are not enough: CUBRID uses -493 for every
    parser error, and pycubrid before 1.8.0 reports syntax errors, ``<name>
    is not a class`` and some permission errors with SQLSTATE 42S02 and a
    ``Table not found`` description, so only the server message identifies a missing
    object (#454, #530). Only the driver error (``orig``) is inspected, never
    the SQLAlchemy wrapper, whose text includes the SQL statement.
    """
    return "Unknown class" in str(getattr(error, "orig", error))


# Pre-compiled patterns for column type parsing in get_columns().
# Avoids re-compilation on every reflection call.
_RE_TYPE_PARAMS = re.compile(r"\([\d,]+\)")
_RE_ENUM = re.compile(r"^ENUM\s*\((.*)\)\s*$", re.IGNORECASE)


def _parse_enum_elements(raw: str) -> list[str]:
    """Extract quoted element strings from an ENUM(...) type string.

    Handles doubled single-quote escaping inside elements
    (e.g. ENUM('it''s', 'b') -> ["it's", "b"]).
    """
    return [m.replace("''", "'") for m in re.findall(r"'((?:[^']|'')*)'", raw)]


_RE_COLLECTION = re.compile(r"^(SET|MULTISET|SEQUENCE)\s*\((.+)\)$", re.IGNORECASE)
_RE_LENGTH = re.compile(r"\((\d+)\)")


def _is_explicitly_quoted_name(value: object) -> bool:
    """Return whether *value* is a name the user forced to be case-sensitive.

    A :class:`~sqlalchemy.sql.elements.quoted_name` with ``quote is True`` was
    explicitly quoted by the user, so its case is significant and must not be
    normalized away when comparing schema names.
    """
    return isinstance(value, quoted_name) and value.quote is True


def _split_collection_members(inner: str) -> list[str]:
    """Split collection member types respecting parenthesis depth."""
    if not inner.strip():
        return []
    parts: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(inner):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return [inner]
        elif ch == "," and depth == 0:
            parts.append(inner[start:i])
            start = i + 1
    parts.append(inner[start:])
    return parts


_RE_PRECISION_SCALE = re.compile(r"\((\d+)(?:,\s*(\d+))?\)")

# CUBRID's ``SHOW CREATE TABLE`` emits foreign-key clauses such as::
#
#     CONSTRAINT [fk_name] FOREIGN KEY ([col1], [col2]) REFERENCES
#         [owner.ref_table] ([rcol1], [rcol2]) ON DELETE ... ON UPDATE ...
#
# We parse this DDL fragment because CUBRID exposes no queryable view that
# carries the referenced table/columns alongside the constraint name.
#
# A column list is matched as bracketed names only (each optionally followed
# by ASC/DESC), because a name may itself contain ``(``, ``)``, ``,`` or spaces
# (``([(3)], [a, b])``, #532). CUBRID cannot put ``]`` inside an identifier, so
# ``[^\]]+`` spans one whole name. Whitespace is allowed inside the parentheses.
_BRACKETED_COLUMN = r"\[[^\]]+\](?:\s+(?:ASC|DESC))?"
_BRACKETED_COLUMN_LIST = rf"{_BRACKETED_COLUMN}(?:\s*,\s*{_BRACKETED_COLUMN})*"
_RE_FOREIGN_KEY = re.compile(
    r"CONSTRAINT\s+\[(?P<name>[^\]]+)\]\s+FOREIGN\s+KEY\s*"
    rf"\(\s*(?P<cols>{_BRACKETED_COLUMN_LIST})\s*\)\s+REFERENCES\s+"
    rf"\[(?P<ref_table>[^\]]+)\]\s*\(\s*(?P<ref_cols>{_BRACKETED_COLUMN_LIST})\s*\)"
    r"(?:\s+ON\s+DELETE\s+(?P<ondelete>CASCADE|SET\s+NULL|NO\s+ACTION|RESTRICT))?"
    r"(?:\s+ON\s+UPDATE\s+(?P<onupdate>CASCADE|SET\s+NULL|NO\s+ACTION|RESTRICT))?",
    re.IGNORECASE,
)
# Parses ``CONSTRAINT [name] UNIQUE KEY ([col1], [col2])`` from
# ``SHOW CREATE TABLE`` output. Used as a fallback when the
# ``db_index`` catalog view finds no unique index.
_RE_UNIQUE_KEY = re.compile(
    r"CONSTRAINT\s+\[(?P<name>[^\]]+)\]\s+UNIQUE\s+KEY\s*"
    rf"\(\s*(?P<cols>{_BRACKETED_COLUMN_LIST})\s*\)",
    re.IGNORECASE,
)
_RE_BRACKET_IDENT = re.compile(r"\[([^\]]+)\]")


# -----------------------------------------------------------------------
# Column-spec and ischema_names mappings
# -----------------------------------------------------------------------

colspecs = {
    sqltypes.Enum: ENUM,
    sqltypes.Numeric: NUMERIC,
    sqltypes.Float: FLOAT,
    sqltypes.Time: TIME,
    sqltypes.JSON: JSON,
    sqltypes.JSON.JSONIndexType: JSONIndexType,
    sqltypes.JSON.JSONPathType: JSONPathType,
}

# ischema_names maps CUBRID type names from SHOW COLUMNS to SA types.
# https://www.cubrid.org/manual/en/11.0/sql/datatype.html
ischema_names = {
    # Numeric
    "SHORT": SMALLINT,
    "SMALLINT": SMALLINT,
    "INTEGER": INTEGER,
    "BIGINT": BIGINT,
    "NUMERIC": NUMERIC,
    "DECIMAL": DECIMAL,
    "FLOAT": FLOAT,
    "DOUBLE": DOUBLE,
    "DOUBLE PRECISION": DOUBLE_PRECISION,
    # Date/Time
    "DATE": DATE,
    "TIME": TIME,
    "TIMESTAMP": TIMESTAMP,
    "TIMESTAMPTZ": TIMESTAMPTZ,
    "TIMESTAMPLTZ": TIMESTAMPLTZ,
    "DATETIME": DATETIME,
    "DATETIMETZ": DATETIMETZ,
    "DATETIMELTZ": DATETIMELTZ,
    # Bit Strings
    "BIT": BIT,
    "BIT VARYING": BIT,
    # Character Strings
    "CHAR": CHAR,
    "VARCHAR": VARCHAR,
    "NCHAR": NCHAR,
    "CHAR VARYING": VARCHAR,
    "NCHAR VARYING": NVARCHAR,
    "STRING": STRING,
    "ENUM": ENUM,
    # LOB
    "BLOB": BLOB,
    "CLOB": CLOB,
    # Collection
    # Note: CUBRID's LIST is a synonym for SEQUENCE and is normalized to
    # SEQUENCE at DDL-parse time, so the catalog never reports "LIST" — there is
    # deliberately no "LIST" entry here (it would be unreachable dead code).
    "SET": SET,
    "MULTISET": MULTISET,
    "SEQUENCE": SEQUENCE,
    # JSON (CUBRID 10.2+)
    "JSON": JSON,
}


# -----------------------------------------------------------------------
# Dialect
# -----------------------------------------------------------------------


class CubridDialect(default.DefaultDialect):
    """SQLAlchemy dialect for CUBRID."""

    name = "cubrid"
    driver = "cubrid"

    # SA 2.0 statement caching
    supports_statement_cache = True

    # Compiler classes
    statement_compiler = CubridCompiler
    ddl_compiler = CubridDDLCompiler
    type_compiler = CubridTypeCompiler
    preparer: type[IdentifierPreparer] = CubridIdentifierPreparer
    execution_ctx_cls = CubridExecutionContext

    # DBAPI
    # https://www.cubrid.org/manual/en/11.0/api/python.html
    default_paramstyle = "qmark"

    # Type mappings
    colspecs = colspecs  # pyright: ignore[reportAssignmentType]
    ischema_names = ischema_names

    # Identifiers
    # https://www.cubrid.org/manual/en/11.0/sql/identifier.html
    max_identifier_length = 254
    max_index_name_length = 254
    max_constraint_name_length = 254

    requires_name_normalize = False

    # Data type support
    supports_native_enum = True
    supports_native_boolean = False  # CUBRID uses SMALLINT for booleans
    supports_native_decimal = True
    supports_native_lateral = False

    # Render CAST(... AS NUMERIC(p,s)) on scaled numeric binds so CUBRID does
    # not coerce them to integers in arithmetic; see CubridSQLCompiler.
    bind_typing = BindTyping.RENDER_CASTS

    # Column options
    supports_sequences = False

    # DDL
    supports_alter = True
    supports_comments = True
    inline_comments = True

    # DML
    supports_default_values = True
    supports_default_metavalue = True
    supports_empty_insert = True
    supports_multivalues_insert = True
    use_insertmanyvalues = True
    use_insertmanyvalues_wo_returning = True
    insertmanyvalues_implicit_sentinel = InsertmanyvaluesSentinelOpts.ANY_AUTOINCREMENT
    supports_is_distinct_from = True

    # Accurate on both drivers: pycubrid sums executemany rowcount itself, and
    # CUBRIDdb's last-row-only rowcount is corrected by do_executemany (#502).
    supports_sane_multi_rowcount = True

    # RETURNING
    insert_returning = False
    update_returning = False
    delete_returning = False

    postfetch_lastrowid = True

    # Two-phase commit not supported by CUBRID
    supports_twophase_commit = False

    def __init__(
        self,
        isolation_level: str | None = None,
        json_serializer: Any = None,
        json_deserializer: Any = None,
        no_backslash_escapes: bool = True,
        **kwargs: Any,
    ) -> None:
        if isolation_level is not None:
            if not isinstance(isolation_level, str):
                raise ArgumentError(
                    f"isolation_level must be a string such as 'SERIALIZABLE' or "
                    f"'AUTOCOMMIT', got {isolation_level!r}"
                )
            # SQLAlchemy applies the engine-level level on connect and restores
            # it on pool checkin, asserting that it equals the level read back
            # at first connect, so pass the canonical spelling of an alias.
            name = isolation_level.replace("_", " ").upper()
            code = self._ISOLATION_LEVEL_MAP.get(name)
            isolation_level = self._ISOLATION_LEVEL_REVERSE[code] if code is not None else name
        # An unknown name is passed through so SQLAlchemy raises ArgumentError.
        super().__init__(isolation_level=cast(Optional[IsolationLevel], isolation_level), **kwargs)
        self.isolation_level = isolation_level
        self._json_serializer = json_serializer
        self._json_deserializer = json_deserializer
        # CUBRID's `no_backslash_escapes` system parameter defaults to `yes`,
        # meaning a backslash is a LITERAL character (opposite of MySQL). When
        # True (the default) literal rendering does NOT double backslashes.
        # Set False only for servers configured with no_backslash_escapes=no,
        # where a backslash acts as an escape character and must be doubled.
        self.no_backslash_escapes = no_backslash_escapes

    @classmethod
    def import_dbapi(cls) -> DBAPIModule:
        """Import and return the CUBRID DBAPI module (SA 2.0 API)."""
        try:
            import CUBRIDdb as cubrid_dbapi  # type: ignore[import-not-found]  # pyright: ignore[reportMissingImports]
        except ImportError as e:
            raise ImportError(
                "Could not import CUBRIDdb. The bare cubrid:// URL uses the "
                "legacy CUBRIDdb C-extension driver. Switch to the maintained "
                "pure-Python driver with a cubrid+pycubrid:// URL "
                '(pip install "sqlalchemy-cubrid[pycubrid]"), or build CUBRIDdb '
                "from cubrid-python v11.3.0.51 or later (the CUBRID-Python "
                "9.3.x releases on PyPI are untested)."
            ) from e
        return cast(DBAPIModule, cubrid_dbapi)  # pyright: ignore[reportInvalidCast]

    def do_executemany(
        self,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any = None,
    ) -> None:
        """Run ``executemany`` as one ``execute`` per row, summing rowcount.

        CUBRIDdb (up to at least 11.3.0.51) prepares an ``executemany``
        statement once and never binds ``None``, so a ``None`` parameter
        silently reuses the previous row's value; its ``rowcount`` also
        reflects only the last row. Both are fixed by executing each row
        separately (each ``execute`` re-prepares, so unbound parameters are
        NULL) and reporting the total, which keeps
        ``supports_sane_multi_rowcount`` accurate for ORM batched UPDATE and
        DELETE. The guard applies to every statement, not only when a row
        contains ``None``, because the last-row rowcount is wrong either way.
        insertmanyvalues batches go through ``do_execute`` and are not
        affected, but an INSERT into a table with a ``bind_expression()`` type
        falls back to executemany (#421) and does use this guard.
        :class:`PyCubridDialect` restores the driver's own ``executemany``.
        Remove once a fixed CUBRIDdb is the minimum (#502).
        """
        rowcount = 0
        for params in parameters:
            cursor.execute(statement, params)
            if rowcount >= 0:
                rowcount = -1 if cursor.rowcount < 0 else rowcount + cursor.rowcount
        cursor.rowcount = rowcount

    def create_connect_args(self, url: URL) -> ConnectArgsType:
        """Build DB-API connection arguments for CUBRID.

        CUBRID connection string format::

            CUBRID:host:port:db_name:::
        """
        if url is None:
            raise ValueError("Unexpected database URL format")

        opts = url.translate_connect_args(username="user", database="database")
        host = opts.get("host", "localhost")
        port = opts.get("port", 33000)
        database = opts.get("database", "")
        username = opts.get("user", "")
        password = opts.get("password", "")

        connect_url = f"CUBRID:{host}:{port}:{database}:::"
        args = (connect_url, username, password)
        return args, {}

    def initialize(self, connection: Any) -> None:
        super().initialize(connection)
        self._warn_if_untested_cubriddb()
        log.debug(
            "CUBRID dialect initialized: server_version=%s",
            self.server_version_info,
        )

    def _warn_if_untested_cubriddb(self) -> None:
        """Warn once per engine when CUBRIDdb is older than the tested line (#585).

        A warning rather than ``NotSupportedError``: the ``[cubrid]`` /
        ``[cubriddb]`` extras have always installed the PyPI 9.3.x release, so
        refusing to connect would break existing deployments in a minor
        release. The pycubrid variants inherit :meth:`initialize` and skip this.
        """
        if self.driver != "cubrid":
            return
        found = _cubriddb_version(self.dbapi)
        if found is None:
            log.debug("CUBRIDdb version could not be determined; skipping version check")
            return
        raw, major_minor = found
        if major_minor >= _MIN_TESTED_CUBRIDDB:
            return
        util.warn(
            f"CUBRIDdb {raw} is older than the CUBRIDdb 11.3 line that "
            "sqlalchemy-cubrid is tested with. The CUBRID-Python releases on "
            "PyPI (9.3.x, installed by the [cubrid] and [cubriddb] extras) are "
            "untested: they return BIGINT as str and fail parts of the "
            "integration suite. Use the recommended cubrid+pycubrid:// URL "
            '(pip install "sqlalchemy-cubrid[pycubrid]"), or build CUBRIDdb '
            "from cubrid-python v11.3.0.51 or later; see "
            "https://cubrid-lab.github.io/sqlalchemy-cubrid/DRIVER_COMPAT/"
        )

    # ----- Reflection methods -----

    @reflection.cache
    def get_columns(
        self,
        connection: Any,
        table_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> list[ReflectedColumn]:
        """Return column information for *table_name*.

        Uses ``SHOW COLUMNS IN <table>`` which is available since CUBRID 9.x.
        """
        self._raise_if_non_default_schema(schema, table_name)

        columns: list[ReflectedColumn] = []
        quoted = self.identifier_preparer.quote_identifier(table_name)
        try:
            result = connection.execute(text(f"SHOW COLUMNS IN {quoted}"))
        except Exception as error:
            if _is_unknown_class_error(error):
                raise NoSuchTableError(table_name) from error
            raise
        for row in result:
            colname = row[0]
            coltype_raw = row[1]
            nullable = row[2] == "YES"
            default_val = row[4]
            autoincrement = "auto_increment" in row[5] if row[5] else False

            # Strip length/precision from type string for lookup
            coltype_key = _RE_TYPE_PARAMS.sub("", coltype_raw).strip()

            coltype: Any  # noqa: F842 — type varies per branch below

            # ENUM('a', 'b', ...) — native enum with its element list
            enum_match = _RE_ENUM.match(coltype_raw.strip())
            if enum_match:
                coltype = ENUM(*_parse_enum_elements(enum_match.group(1)))

            # Collection types: SET(VARCHAR(100)), MULTISET(INT), etc.
            collection_match = None if enum_match else _RE_COLLECTION.match(coltype_raw)
            if collection_match:
                coll_name = collection_match.group(1).upper()
                inner_raw = collection_match.group(2)
                coll_cls = self.ischema_names[coll_name]
                members: list[Any] = []
                for member_str in _split_collection_members(inner_raw):
                    member_str = member_str.strip()
                    member_key = _RE_TYPE_PARAMS.sub("", member_str).strip()
                    if member_key in ("CHAR", "VARCHAR", "NCHAR", "CHAR VARYING", "NCHAR VARYING"):
                        length_match = _RE_LENGTH.search(member_str)
                        length = int(length_match.group(1)) if length_match else None
                        members.append(self.ischema_names[member_key](length))  # pyright: ignore[reportCallIssue, reportArgumentType]
                    elif member_key in ("NUMERIC", "DECIMAL"):
                        params_match = _RE_PRECISION_SCALE.search(member_str)
                        if params_match:
                            precision = int(params_match.group(1))
                            scale = int(params_match.group(2)) if params_match.group(2) else None
                            members.append(
                                self.ischema_names[member_key](precision=precision, scale=scale)
                            )  # pyright: ignore[reportCallIssue]
                        else:
                            members.append(self.ischema_names[member_key]())
                    elif member_key in self.ischema_names:
                        cls = self.ischema_names[member_key]
                        members.append(cls() if callable(cls) else cls)
                    else:
                        members.append(member_str)
                coltype = coll_cls(*members)
            elif coltype_key in ("CHAR", "VARCHAR", "NCHAR", "CHAR VARYING", "NCHAR VARYING"):
                length_match = _RE_LENGTH.search(coltype_raw)
                length = int(length_match.group(1)) if length_match else None
                coltype = self.ischema_names[coltype_key](length)  # pyright: ignore[reportCallIssue, reportArgumentType]
            elif coltype_key in ("NUMERIC", "DECIMAL"):
                params_match = _RE_PRECISION_SCALE.search(coltype_raw)
                if params_match:
                    precision = int(params_match.group(1))
                    scale = int(params_match.group(2)) if params_match.group(2) else None
                    coltype = self.ischema_names[coltype_key](precision=precision, scale=scale)  # pyright: ignore[reportCallIssue]
                else:
                    coltype = self.ischema_names[coltype_key]()
            elif coltype_key in ("BIT", "BIT VARYING"):
                # Keep the bit length and VARYING so a reflected BIT(32) /
                # BIT VARYING(64) compiles back to the same DDL (#545).
                length_match = _RE_LENGTH.search(coltype_raw)
                coltype = BIT(
                    length=int(length_match.group(1)) if length_match else None,
                    varying=coltype_key == "BIT VARYING",
                )
            else:
                try:
                    coltype_cls = self.ischema_names[coltype_key]
                    # Some ischema entries are classes, some are instances
                    coltype = coltype_cls() if callable(coltype_cls) else coltype_cls
                except KeyError:
                    from sqlalchemy import util

                    util.warn("Did not recognize type '%s' of column '%s'" % (coltype_raw, colname))
                    coltype = sqltypes.NULLTYPE

            # Preserve timezone=True for TZ/LTZ type variants (#181)
            if coltype_key.endswith(("TZ", "LTZ")) and hasattr(coltype, "timezone"):
                coltype = coltype.__class__(timezone=True)

            columns.append(
                {
                    "name": colname,
                    "type": coltype,
                    "nullable": nullable,
                    "default": default_val,
                    "autoincrement": autoincrement,
                }
            )

        # ``db_attribute`` is the public catalog view; ``_db_attribute`` is
        # readable only by DBA (#549). A failing query raises instead of
        # silently dropping every column comment.
        class_filter, filter_params = self._catalog_class_filter(connection, table_name, **kw)
        comment_result = connection.execute(
            text(
                "SELECT attr_name, comment FROM db_attribute "  # nosec B608 - constant clause
                "WHERE " + class_filter + " ORDER BY def_order"
            ),
            filter_params,
        )
        comment_map = {row[0]: row[1] for row in comment_result}

        for column in columns:
            column["comment"] = comment_map.get(column["name"])

        return columns

    @reflection.cache
    def get_pk_constraint(
        self,
        connection: Any,
        table_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> ReflectedPrimaryKeyConstraint:
        """Return the primary key constraint for *table_name*."""
        self._raise_if_non_default_schema(schema, table_name)

        constraint_name = None
        constrained_columns: list[str] = []

        # Read the PK columns from the public ``db_index`` / ``db_index_key``
        # catalog views (the ``_db_index`` tables are DBA-only, #549).
        # ``SHOW COLUMNS`` marks only the *first* column of a composite PK as
        # ``PRI`` and gives no column order, so it drops the trailing columns of
        # a multi-column key (#426). The catalog gives every column in
        # ``key_order``. A failing query raises.
        class_filter, filter_params = self._catalog_class_filter(
            connection, table_name, "i", "k", **kw
        )
        pk_result = connection.execute(
            text(
                "SELECT k.key_attr_name, i.index_name "  # nosec B608 - constant clause
                "FROM db_index i, db_index_key k WHERE "
                + class_filter
                + " AND i.is_primary_key = 'YES' "
                "AND k.class_name = i.class_name AND k.index_name = i.index_name "
                "ORDER BY k.key_order"
            ),
            filter_params,
        )
        for row in pk_result:
            constrained_columns.append(row[0])
            constraint_name = row[1]

        # No catalog row: the table has no PK or does not exist. ``SHOW
        # COLUMNS`` resolves the name like the server and raises for a missing
        # table.
        if not constrained_columns:
            quoted = self.identifier_preparer.quote_identifier(table_name)
            try:
                result = connection.execute(text(f"SHOW COLUMNS IN {quoted}"))
            except Exception as error:
                if _is_unknown_class_error(error):
                    raise NoSuchTableError(table_name) from error
                raise
            for row in result:
                if row[3] == "PRI":
                    constrained_columns.append(row[0])

        return {
            "name": constraint_name,
            "constrained_columns": constrained_columns,
        }

    @reflection.cache
    def get_foreign_keys(
        self,
        connection: Any,
        table_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> list[ReflectedForeignKeyConstraint]:
        """Return foreign key information for *table_name*.

        CUBRID does not expose FK metadata (referenced table, columns,
        ON DELETE/UPDATE actions) in any system catalog view. The DDL
        output of ``SHOW CREATE TABLE`` is the only reliable source.
        See cubrid-lab/sqlalchemy-cubrid#120.

        The constraints are returned sorted by name. Raises
        :class:`NoSuchTableError` when *table_name* does not exist; a view has
        no foreign keys.
        """
        self._raise_if_non_default_schema(schema, table_name)

        class_type = self._get_class_type(connection, table_name, **kw)
        if class_type is None:
            raise NoSuchTableError(table_name)
        if class_type == "VCLASS":
            return []
        return self._get_foreign_keys_from_ddl(connection, table_name, schema)

    def _get_foreign_keys_from_ddl(
        self,
        connection: Any,
        table_name: str,
        schema: str | None,
    ) -> list[ReflectedForeignKeyConstraint]:
        """Parse SHOW CREATE TABLE output for FK constraints.

        This is the sole FK reflection path — no system catalog alternative
        exists because CUBRID's system views do not expose referenced table
        or column metadata for foreign keys.
        """
        foreign_keys: list[ReflectedForeignKeyConstraint] = []
        try:
            quoted = self.identifier_preparer.quote_identifier(table_name)
            result = connection.execute(text(f"SHOW CREATE TABLE {quoted}"))
            row = result.first()
        except Exception as error:  # nosec B110 — graceful fallback when DDL unavailable
            if _is_unknown_class_error(error):
                raise NoSuchTableError(table_name) from error
            log.warning(
                "SHOW CREATE TABLE failed for %s; foreign keys will be empty",
                table_name,
                exc_info=True,
            )
            return foreign_keys
        if row is None:
            return foreign_keys
        ddl = str(row[1]) if len(row) > 1 else str(row[0])
        for fk_match in _RE_FOREIGN_KEY.finditer(ddl):
            constraint_name = fk_match.group("name")
            constrained_columns = [
                col.strip() for col in _RE_BRACKET_IDENT.findall(fk_match.group("cols"))
            ]
            ref_table_raw = fk_match.group("ref_table")
            # CUBRID prefixes referenced tables with the owner (e.g.
            # ``dba.budget_categories``) — strip it for SQLAlchemy.
            ref_table = ref_table_raw.split(".", 1)[-1]
            referred_columns = [
                col.strip() for col in _RE_BRACKET_IDENT.findall(fk_match.group("ref_cols"))
            ]
            options: dict[str, str] = {}
            if fk_match.group("ondelete"):
                options["ondelete"] = fk_match.group("ondelete").upper()
            if fk_match.group("onupdate"):
                options["onupdate"] = fk_match.group("onupdate").upper()
            foreign_keys.append(
                {
                    "name": constraint_name,
                    "constrained_columns": constrained_columns,
                    "options": options,
                    "referred_schema": schema,
                    "referred_table": ref_table,
                    "referred_columns": referred_columns,
                }
            )
        # ``SHOW CREATE TABLE`` lists constraints in its own order, not by
        # name; return them sorted by name like SQLAlchemy's built-in
        # dialects so the result is deterministic (#531).
        foreign_keys.sort(key=lambda fk: fk["name"] or "")
        return foreign_keys

    @reflection.cache
    def get_table_names(
        self,
        connection: Any,
        schema: str | None = None,
        **kw: Any,
    ) -> list[str]:
        """Return a list of table names for *schema*."""
        if not self._schema_is_default(schema):
            return []
        result = connection.execute(
            text(
                "SELECT class_name FROM db_class "
                "WHERE class_type = 'CLASS' AND is_system_class = 'NO' "
                "ORDER BY class_name"
            )
        )
        return [row[0] for row in result]

    @reflection.cache
    def get_view_names(
        self,
        connection: Any,
        schema: str | None = None,
        **kw: Any,
    ) -> list[str]:
        """Return a list of view names."""
        if not self._schema_is_default(schema):
            return []
        result = connection.execute(
            text(
                "SELECT class_name FROM db_class "
                "WHERE class_type = 'VCLASS' AND is_system_class = 'NO' "
                "ORDER BY class_name"
            )
        )
        return [row[0] for row in result]

    @reflection.cache
    def get_view_definition(
        self, connection: Any, view_name: str, schema: str | None = None, **kw: Any
    ) -> str:
        """Return the CREATE VIEW definition.

        Raises :class:`NoSuchTableError` when *view_name* does not exist or is
        not a view (``SHOW CREATE VIEW`` on a table returns no row).
        """
        self._raise_if_non_default_schema(schema, view_name)

        quoted = self.identifier_preparer.quote_identifier(view_name)
        try:
            result = connection.execute(text(f"SHOW CREATE VIEW {quoted}"))
        except Exception as error:
            if _is_unknown_class_error(error):
                raise NoSuchTableError(view_name) from error
            raise
        row = result.first()
        if row is None:
            raise NoSuchTableError(view_name)
        return str(row[1])

    @reflection.cache
    def get_indexes(
        self,
        connection: Any,
        table_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> list[ReflectedIndex]:
        """Return index information for *table_name*.

        A view has no indexes of its own, so an empty list is returned for
        one (``SHOW INDEXES IN <view>`` lists the base table's indexes).
        """
        self._raise_if_non_default_schema(schema, table_name)

        if self._get_class_type(connection, table_name, **kw) == "VCLASS":
            return []

        idict: dict[str, ReflectedIndex] = {}

        # Batch-fetch primary-key and foreign-key flags for all indexes on
        # this table from CUBRID's public ``db_index`` catalog view (single
        # query for both, instead of N+1 lookups). ``_db_index`` is readable
        # only by DBA (#549); a failing query raises rather than silently
        # reporting the PK and FK indexes as ordinary ones.
        #
        # PK indexes are filtered because SQLAlchemy reports the PK via
        # ``get_pk_constraint`` separately.  FK indexes are filtered because
        # CUBRID auto-creates an index for every foreign key (with the same
        # name as the FK constraint) and these are an implementation detail
        # — if reported they cause Alembic autogenerate to emit spurious
        # ``op.drop_index`` / ``op.create_index`` diffs on every run.
        # See cubrid-lab/sqlalchemy-cubrid#120.
        pk_indexes: set[str] = set()
        fk_indexes: set[str] = set()
        class_filter, filter_params = self._catalog_class_filter(connection, table_name, **kw)
        flag_result = connection.execute(
            text(
                "SELECT index_name, is_primary_key, is_foreign_key "  # nosec B608 - constant clause
                "FROM db_index WHERE " + class_filter
            ),
            filter_params,
        )
        for flag_row in flag_result:
            if flag_row[1] == "YES":
                pk_indexes.add(flag_row[0])
            if flag_row[2] == "YES":
                fk_indexes.add(flag_row[0])

        quoted = self.identifier_preparer.quote_identifier(table_name)
        try:
            result = connection.execute(text(f"SHOW INDEXES IN {quoted}"))
        except Exception as error:
            if _is_unknown_class_error(error):
                raise NoSuchTableError(table_name) from error
            raise
        for row in result:
            index_name = row[2]

            if index_name not in pk_indexes and index_name not in fk_indexes:
                if index_name in idict:
                    idict[index_name]["column_names"].append(row[4])
                else:
                    idict[index_name] = {
                        "name": index_name,
                        "column_names": [row[4]],
                        "unique": row[1] == 0,
                    }

        return list(idict.values())

    @reflection.cache
    def get_unique_constraints(
        self,
        connection: Any,
        table_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> list[ReflectedUniqueConstraint]:
        """Return unique constraints for *table_name*.

        CUBRID implements a ``UNIQUE`` constraint as a unique index and cannot
        tell it apart from ``CREATE UNIQUE INDEX`` (same ``db_index`` flags,
        and ``SHOW CREATE TABLE`` prints both as ``UNIQUE KEY``), so, as in
        SQLAlchemy's MySQL dialect, every entry is also returned by
        :meth:`get_indexes` and carries ``duplicates_index`` naming that index.
        ``Table`` reflection then keeps the unique index and skips the
        duplicate constraint.

        Primary path: query the public ``db_index`` catalog view for unique
        indexes (excluding PK and FK auto-indexes), then resolve column
        names via ``SHOW INDEXES``. When it finds none, parse ``SHOW CREATE
        TABLE`` DDL output via regex. A failing catalog query raises (#549).

        Raises :class:`NoSuchTableError` when *table_name* does not exist; a
        view has no unique constraints.
        """
        self._raise_if_non_default_schema(schema, table_name)

        class_type = self._get_class_type(connection, table_name, **kw)
        if class_type is None:
            raise NoSuchTableError(table_name)
        if class_type == "VCLASS":
            return []

        # Primary path: system catalog + SHOW INDEXES
        uqs = self._get_unique_constraints_from_catalog(connection, table_name, **kw)
        if uqs:
            return uqs

        # Fallback: DDL regex (legacy path)
        return self._get_unique_constraints_from_ddl(connection, table_name)

    def _get_unique_constraints_from_catalog(
        self,
        connection: Any,
        table_name: str,
        **kw: Any,
    ) -> list[ReflectedUniqueConstraint]:
        """Query db_index + SHOW INDEXES for UNIQUE constraints.

        Uses the same two-query pattern as ``get_indexes()``: first fetch
        unique index names from ``db_index`` (filtering out PK and FK
        auto-indexes), then resolve column names from ``SHOW INDEXES``.
        """
        # Step 1: get unique index names (excluding PK and FK auto-indexes)
        unique_names: set[str] = set()
        class_filter, filter_params = self._catalog_class_filter(connection, table_name, **kw)
        name_result = connection.execute(
            text(
                "SELECT index_name FROM db_index WHERE "  # nosec B608 - constant clause
                + class_filter
                + " AND is_unique = 'YES' AND is_primary_key = 'NO' AND is_foreign_key = 'NO'"
            ),
            filter_params,
        )
        for row in name_result:
            unique_names.add(row[0])
        if not unique_names:
            return []

        # Step 2: resolve column names from SHOW INDEXES
        quoted = self.identifier_preparer.quote_identifier(table_name)
        try:
            col_result = connection.execute(text(f"SHOW INDEXES IN {quoted}"))
        except Exception as error:
            if _is_unknown_class_error(error):
                raise NoSuchTableError(table_name) from error
            raise
        constraints: dict[str, list[str]] = {}
        for row in col_result:
            index_name = row[2]
            if index_name in unique_names:
                constraints.setdefault(index_name, []).append(row[4])

        return [
            {"name": name, "column_names": cols, "duplicates_index": name}
            for name, cols in constraints.items()
        ]

    def _get_unique_constraints_from_ddl(
        self,
        connection: Any,
        table_name: str,
    ) -> list[ReflectedUniqueConstraint]:
        """Parse SHOW CREATE TABLE output for UNIQUE constraints (legacy fallback)."""
        unique_constraints: list[ReflectedUniqueConstraint] = []
        try:
            quoted = self.identifier_preparer.quote_identifier(table_name)
            result = connection.execute(text(f"SHOW CREATE TABLE {quoted}"))
            row = result.first()
        except Exception as error:  # nosec B110 — graceful fallback when DDL unavailable
            if _is_unknown_class_error(error):
                raise NoSuchTableError(table_name) from error
            log.warning(
                "SHOW CREATE TABLE failed for %s; unique constraints will be empty",
                table_name,
                exc_info=True,
            )
            return unique_constraints
        if row is None:
            return unique_constraints
        ddl = str(row[1]) if len(row) > 1 else str(row[0])
        for uc_match in _RE_UNIQUE_KEY.finditer(ddl):
            constraint_name = uc_match.group("name")
            column_names = [
                col.strip() for col in _RE_BRACKET_IDENT.findall(uc_match.group("cols"))
            ]
            unique_constraints.append(
                {
                    "name": constraint_name,
                    "column_names": column_names,
                    "duplicates_index": constraint_name,
                }
            )
        return unique_constraints

    @reflection.cache
    def get_check_constraints(
        self,
        connection: Any,
        table_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> list[ReflectedCheckConstraint]:
        """Return check constraints for *table_name*.

        CUBRID parses CHECK constraint syntax but does not enforce them
        at runtime (official CUBRID behavior). Reflecting them would be
        misleading, so we return an empty list.
        """
        log.debug(
            "get_check_constraints(%s): returning empty — CUBRID does not enforce CHECK constraints",
            table_name,
        )
        return []

    @reflection.cache
    def get_table_comment(
        self,
        connection: Any,
        table_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> ReflectedTableComment:
        """Return table comment from CUBRID system catalog.

        Raises :class:`NoSuchTableError` when *table_name* does not exist. The
        name and owner are matched like :meth:`_get_class_type`: the name as
        given or folded to lower case, and the current user's class first.
        """
        self._raise_if_non_default_schema(schema, table_name)

        row = connection.execute(
            text(
                "SELECT comment FROM db_class "
                "WHERE class_name IN (:name, LOWER(:name)) "
                "ORDER BY CASE WHEN owner_name = CURRENT_USER THEN 0 "
                "WHEN is_system_class = 'YES' THEN 1 ELSE 2 END"
            ),
            {"name": table_name},
        ).first()
        if row is None:
            raise NoSuchTableError(table_name)
        return {"text": row[0] if row[0] else None}

    def get_schema_names(self, connection: Any, **kw: Any) -> list[str]:
        """Return the schema names visible to this connection.

        CUBRID exposes a single effective schema per connection (the current
        user's schema, as reported by ``SELECT SCHEMA()``; see
        :meth:`_get_default_schema_name`).  This dialect therefore operates in a
        consistent single-schema mode: the only schema name it recognises is the
        default one.  Returning ``[default_schema_name]`` (rather than the empty
        list it historically returned) keeps this method consistent with
        :meth:`_get_default_schema_name` and makes Alembic autogenerate with
        ``include_schemas=True`` usable.

        Owner-qualified cross-schema reflection is intentionally *not* attempted
        here; every reflection method applies the same single-schema policy via
        :meth:`_schema_is_default`.
        """
        if self.default_schema_name is None:
            return []
        return [self.default_schema_name]

    def _schema_is_default(self, schema: str | None) -> bool:
        """Return whether *schema* refers to this connection's only schema.

        ``schema is None`` means "the default schema" in SQLAlchemy, so it is
        always accepted; a non-``None`` schema is accepted only when it matches
        :attr:`default_schema_name`.  CUBRID folds unquoted identifiers to lower
        case, so the comparison is case-insensitive for unquoted names and
        ``schema="DBA"`` matches a default of ``"dba"``.  Explicitly-quoted names
        (``quoted_name`` with ``quote=True``) are compared case-sensitively,
        honouring the user's intent to preserve case.  List/existence reflection
        methods
        (:meth:`get_table_names`, :meth:`get_view_names`, :meth:`has_table`,
        :meth:`has_index`) use this directly to return empty/false for a
        non-default schema, while object-detail methods go through
        :meth:`_raise_if_non_default_schema`.
        """
        if schema is None:
            return True
        default = self.default_schema_name
        if default is None:
            return False
        if schema == default:
            return True
        # A name the user explicitly quoted is case-sensitive; do not normalize.
        if _is_explicitly_quoted_name(schema) or _is_explicitly_quoted_name(default):
            return False
        # Both inputs are concrete strings; the base hook returns a string
        # (including quoted_name) but remains unannotated in SQLAlchemy 2.x.
        normalize = cast(Callable[[str], str], self.normalize_name)
        return normalize(str(schema)) == normalize(str(default))

    def _raise_if_non_default_schema(self, schema: str | None, object_name: str) -> None:
        """Raise :class:`NoSuchTableError` if *schema* is not the default schema.

        CUBRID exposes a single effective schema per connection, so an object
        qualified with any non-default schema cannot exist.  Object-detail
        reflection methods (columns, PK/FK/unique constraints, indexes, view
        definition, table comment) call this to report the object as missing
        rather than silently returning empty metadata (which would mask a real
        "not found").  List/existence methods instead return empty/false via
        :meth:`_schema_is_default` directly.
        """
        if not self._schema_is_default(schema):
            qualified = f"{schema}.{object_name}" if schema else object_name
            raise NoSuchTableError(qualified)

    def _get_class_type(self, connection: Any, name: str, **kw: Any) -> str | None:
        """Return ``'CLASS'`` (table), ``'VCLASS'`` (view) or ``None`` (missing).

        See :meth:`_get_class_info` for how *name* is matched.
        """
        info = self._get_class_info(connection, name, **kw)
        return info[0] if info is not None else None

    @reflection.cache
    def _get_class_info(self, connection: Any, name: str, **kw: Any) -> tuple[str, str] | None:
        """Return ``(class_type, owner_name)`` of *name*, or ``None`` if missing.

        CUBRID stores identifiers folded to lower case, so a mixed-case *name*
        also matches its lower-case form, as in ``SHOW COLUMNS IN <name>``.
        Since CUBRID 11.2 classes of different owners may share a name; the
        row of the current user's own class wins (it is what ``SHOW ... IN
        <name>`` resolves to), then a system class, then any other visible
        class. CUBRID 10.2 class names are global, so there is one row at most.
        ``info_cache`` is passed through ``**kw``, so an ``Inspector`` looks a
        name up once.
        """
        # .first() closes the result: an open result keeps one of the
        # connection's server query entries (at most 100, then -830).
        row = connection.execute(
            text(
                "SELECT class_type, owner_name FROM db_class "
                "WHERE class_name IN (:name, LOWER(:name)) "
                "ORDER BY CASE WHEN owner_name = CURRENT_USER THEN 0 "
                "WHEN is_system_class = 'YES' THEN 1 ELSE 2 END"
            ),
            {"name": name},
        ).first()
        if row is None or row[0] is None:
            return None
        return str(row[0]), str(row[1])

    def _catalog_class_filter(
        self, connection: Any, table_name: str, *aliases: str, **kw: Any
    ) -> tuple[str, dict[str, str]]:
        """Return a condition selecting *table_name*'s rows in a catalog view.

        For the public ``db_index``, ``db_index_key`` and ``db_attribute``
        views (the ``_db_*`` tables are DBA-only, #549). The name matches as
        given or folded to lower case, like :meth:`_get_class_info`. Since
        CUBRID 11.2 classes of different owners may share a name and these
        views list every class the user may read, so the rows are limited to
        the owner :meth:`_get_class_info` prefers (the current user's class
        first). Before 11.2 class names are global and the views have no
        ``owner_name``.
        *aliases* are the (constant) table aliases to filter, the first one
        also by name; the result is SQL with bound parameters only.
        """
        first, *others = [f"{alias}." if alias else "" for alias in aliases or ("",)]
        condition = f"{first}class_name IN (:table, LOWER(:table))"
        params = {"table": table_name}
        version = self.server_version_info
        if version is None or version < (11, 2):
            return condition, params
        info = self._get_class_info(connection, table_name, **kw)
        if info is None:
            return condition, params
        condition += "".join(f" AND {prefix}owner_name = :owner" for prefix in (first, *others))
        return condition, {**params, "owner": info[1]}

    @reflection.cache
    def has_table(
        self,
        connection: Any,
        table_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> bool:
        """Check if *table_name* exists.

        CUBRID stores identifiers folded to lower case, even quoted ones, so a
        mixed-case *table_name* also matches its lower-case form, as in
        :meth:`_get_class_type` (#543).
        """
        if not self._schema_is_default(schema):
            return False
        result = connection.execute(
            text(
                "SELECT COUNT(*) FROM db_class "
                "WHERE class_type IN ('CLASS', 'VCLASS') "
                "AND is_system_class = 'NO' "
                "AND class_name IN (:name, LOWER(:name))"
            ),
            {"name": table_name},
        )
        return _count_is_positive(result.scalar())

    @reflection.cache
    def has_index(
        self,
        connection: Any,
        table_name: str,
        index_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> bool:
        """Check if an index named *index_name* exists on *table_name*.

        Cached per ``info_cache`` like the other reflection methods, so an
        ``Inspector`` answers from its cache until ``clear_cache()`` (#533).
        A missing table or index returns ``False``; a failing catalog query
        raises instead of caching a false negative.

        CUBRID stores identifiers folded to lower case, even quoted ones, so
        both names also match their lower-case form, and the table is resolved
        like :meth:`_get_class_type`: the current user's own class first
        (#543).
        """
        if not self._schema_is_default(schema):
            return False
        class_filter, filter_params = self._catalog_class_filter(connection, table_name, **kw)
        result = connection.execute(
            text(
                "SELECT COUNT(*) FROM db_index WHERE "  # nosec B608 - constant clause
                + class_filter
                + " AND index_name IN (:name, LOWER(:name))"
            ),
            {**filter_params, "name": index_name},
        )
        return _count_is_positive(result.scalar())

    def has_sequence(
        self,
        connection: Any,
        sequence_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> bool:
        """CUBRID does not support sequences."""
        return False

    # ----- Connection lifecycle -----

    def on_connect(self) -> Callable[[Any], None] | None:
        """Return a callable to set up a new DBAPI connection.

        Disables autocommit on the CUBRID driver so that
        SQLAlchemy can manage transactions properly. SQLAlchemy applies an
        engine-level ``isolation_level`` itself, after this hook.
        """

        def connect(conn: Any) -> None:
            # CUBRID Python driver defaults to autocommit=True;
            # SA manages transactions, so we turn it off.
            conn.set_autocommit(False)

        return connect

    def _get_server_version_info(self, connection: Any) -> tuple[int, int, int, int] | None:
        """Return server version as a tuple of ints."""
        versions = connection.execute(text("SELECT VERSION()")).scalar()
        m = re.match(r"(\d+)\.(\d+)\.(\d+)\.(\d+)", versions)
        if m:
            return (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
        return None

    def _get_default_schema_name(  # type: ignore[override]  # SQLAlchemy stub typing is inconsistent: Dialect.default_schema_name is Optional[str] but Dialect._get_default_schema_name() is annotated -> str; we must be able to return None.
        self, connection: Any
    ) -> Optional[str]:
        """Return the default schema name, or ``None`` if unavailable.

        CUBRID's ``SCHEMA()`` can return SQL ``NULL`` (surfaced as Python
        ``None``) when the connection has no current schema.  We must return
        ``None`` in that case rather than ``str(None)`` -> the literal string
        ``"None"``, which would otherwise leak as a fake schema name through
        :meth:`get_schema_names` and :meth:`_schema_is_default` (both of which
        test the object against ``None``).  SQLAlchemy declares
        :attr:`default_schema_name` as ``Optional[str]`` and
        :meth:`DefaultDialect.initialize` already tolerates a ``None`` value.
        """
        schema = connection.execute(text("SELECT SCHEMA()")).scalar()
        if schema is None:
            return None
        return str(schema)

    # ----- Isolation level -----

    # CUBRID isolation level mapping
    # https://www.cubrid.org/manual/en/11.0/sql/transaction.html
    _ISOLATION_LEVEL_MAP: dict[str, int] = {
        "SERIALIZABLE": 6,
        "REPEATABLE READ": 5,
        "REPEATABLE READ SCHEMA, REPEATABLE READ INSTANCES": 5,
        "READ COMMITTED": 4,
        "REPEATABLE READ SCHEMA, READ COMMITTED INSTANCES": 4,
        "CURSOR STABILITY": 4,
    }

    # Canonical spelling returned per integer code. Multiple input aliases map
    # to the same code (e.g. "READ COMMITTED" / "CURSOR STABILITY" / the long
    # granular spelling all map to 4); get_isolation_level() returns the single
    # canonical name below so that set -> get round-trips to the same code. The
    # short standard names are used for the three MVCC levels 4/5/6 (the only
    # levels CUBRID's MVCC engine accepts). Every value here is also present in
    # get_isolation_level_values().
    _ISOLATION_LEVEL_REVERSE: dict[int, str] = {
        6: "SERIALIZABLE",
        5: "REPEATABLE READ",
        4: "READ COMMITTED",
    }

    # CUBRID's default transaction isolation level (level 4 = READ COMMITTED).
    _DEFAULT_ISOLATION_CODE: int = 4

    def get_isolation_level(self, dbapi_connection: DBAPIConnection) -> str:  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]
        """Return the current isolation level for *dbapi_conn*.

        The returned name is the **canonical** name for the level, which may
        differ from the alias passed to :meth:`set_isolation_level`.  CUBRID's
        ``_ISOLATION_LEVEL_MAP`` accepts several aliases per numeric level (for
        example both ``"REPEATABLE READ"`` and
        ``"REPEATABLE READ SCHEMA, REPEATABLE READ INSTANCES"`` map to code 5),
        but ``get_isolation_level`` resolves the numeric code back through a
        single canonical entry.  A ``set`` -> ``get`` round-trip therefore
        returns the canonical name (e.g. ``"REPEATABLE READ"``), not
        necessarily the exact string originally supplied.
        """
        # https://www.cubrid.org/manual/en/11.0/sql/transaction.html
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("GET TRANSACTION ISOLATION LEVEL TO X")
            cursor.execute("SELECT X")
            row = cursor.fetchone()
            if row is None:
                return self._ISOLATION_LEVEL_REVERSE[self._DEFAULT_ISOLATION_CODE]
            val = row[0]
        finally:
            cursor.close()
        # CUBRID returns numeric level; map to string for SA
        if isinstance(val, int):
            return self._ISOLATION_LEVEL_REVERSE.get(val, str(val))
        return str(val)

    def get_isolation_level_values(  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]
        self, dbapi_conn: DBAPIConnection | None = None
    ) -> Sequence[str]:
        """Return the list of valid isolation level values."""
        del dbapi_conn
        return [
            "SERIALIZABLE",
            "REPEATABLE READ",
            "REPEATABLE READ SCHEMA, REPEATABLE READ INSTANCES",
            "READ COMMITTED",
            "REPEATABLE READ SCHEMA, READ COMMITTED INSTANCES",
            "CURSOR STABILITY",
            "AUTOCOMMIT",
        ]

    def set_isolation_level(
        self,
        dbapi_connection: DBAPIConnection,
        level: str,
    ) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Set the isolation level for *dbapi_conn*.

        ``AUTOCOMMIT`` turns on the driver's autocommit mode. Any other level
        turns it off (if on) and runs ``SET TRANSACTION ISOLATION LEVEL``.
        All three drivers (CUBRIDdb, pycubrid and the async adapter) expose an
        ``autocommit`` property.
        """
        if level.upper() == "AUTOCOMMIT":
            if not dbapi_connection.autocommit:  # pyright: ignore[reportAttributeAccessIssue]
                dbapi_connection.autocommit = True  # pyright: ignore[reportAttributeAccessIssue]
            return
        # Note: do NOT unwrap dbapi_conn.connection — the inner C-level
        # _cubrid.connection cursor cannot handle SET TRANSACTION SQL.
        # SA already passes the correct Python-level CUBRIDdb.connections.Connection.
        # Map string level to numeric
        numeric_level = self._ISOLATION_LEVEL_MAP.get(level.upper())
        if numeric_level is None:
            raise ValueError(
                f"Invalid isolation level: {level!r}. "
                f"Valid values: {list(self.get_isolation_level_values())}"
            )
        if dbapi_connection.autocommit:  # pyright: ignore[reportAttributeAccessIssue]
            dbapi_connection.autocommit = False  # pyright: ignore[reportAttributeAccessIssue]
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f"SET TRANSACTION ISOLATION LEVEL {numeric_level}")
            cursor.execute("COMMIT")
        finally:
            cursor.close()

    def detect_autocommit_setting(self, dbapi_conn: DBAPIConnection) -> bool:
        """Return the driver's autocommit mode (no round trip on any driver)."""
        return bool(dbapi_conn.autocommit)  # pyright: ignore[reportAttributeAccessIssue]

    def do_release_savepoint(self, connection: Any, name: str) -> None:
        """CUBRID does not support RELEASE SAVEPOINT; no-op."""
        pass

    # ----- Error handling & connection health -----

    # Disconnect message patterns (lowercase) for is_disconnect().
    # Modeled after psycopg2's string-based approach since CUBRIDdb has
    # only Error, InterfaceError, DatabaseError, and NotSupportedError.
    _disconnect_messages = (
        "connection is closed",
        "closed connection",
        "lost connection",
        "connection lost",  # pycubrid: "connection lost during receive" (#322)
        "server has gone away",
        "connection reset",
        "broken pipe",
        "cannot communicate with the broker",
        "received invalid packet",
        "broker is not available",
        "communication error",
        "connection timed out",
        "connection refused",
        "connection was killed",
        "failed to connect",
        # pycubrid closes the connection when its CHECK_CAS reconnect fails
        # ("CAS did not answer CHECK_CAS out of transaction and reconnecting
        # failed"), e.g. an idle connection while cub_server is down (#565).
        "reconnecting failed",
    )

    # Client-side error codes that CUBRIDdb puts in ``args[0]`` for a dead or
    # unusable connection. CUBRIDdb's ``args[0]`` holds a CCI code (-20xxx,
    # CUBRID ``cas_cci.h``) or a CAS code (-10xxx, ``cas_error.h``) when the
    # call failed before or instead of a server error, and the server's own
    # code (``error_code.h``) otherwise, so server codes such as -4
    # (``ER_INTERRUPTED``, an interrupted query) must not appear here (#572).
    # pycubrid doesn't negotiate CUBRID's renewed CAS/CCI error-code protocol
    # (the -10xxx/-20xxx numbering below), so the CAS answers it with the
    # legacy, unprefixed codes instead -- e.g. -4 for ``ER_INTERRUPTED``, the
    # same code CUBRID's server uses internally (``error_code.h``). pycubrid
    # keeps that legacy code in ``errno``, not in ``args[0]``. This applies
    # to server codes (``error_code.h``, e.g. -4); a *CAS* code (``cas_error.h``,
    # sent with ``CAS_ERROR_INDICATOR``) is instead legacy-renumbered by the
    # CAS itself, from -10xxx to -1xxx: CUBRID's ``CAS_CONV_ERROR_TO_OLD``
    # (``src/broker/cas_protocol.h``) adds 9000, so e.g. CAS_ER_COMMUNICATION
    # reaches pycubrid as -1003, not -10003. See ``_pycubrid_legacy_cas_codes``
    # below for the one such code this dialect currently matches.
    #
    # -10002 (CAS_ER_NO_MORE_MEMORY) is included below because cas.c's
    # process_request() sends it when the CAS's read-buffer allocation fails,
    # then returns FN_CLOSE_CONN, closing the connection (CUBRID v11.4.6
    # src/broker/cas.c).
    _disconnect_error_codes = frozenset(
        {
            -10002,  # CAS_ER_NO_MORE_MEMORY: CAS out of memory (see above)
            -10003,  # CAS_ER_COMMUNICATION (CCI's IS_ER_COMMUNICATION, with -20004)
            -20002,  # CCI_ER_CON_HANDLE: the connection handle is closed or invalid
            -20004,  # CCI_ER_COMMUNICATION: "Cannot communicate with server"
            -20016,  # CCI_ER_CONNECT: "Cannot connect to CUBRID CAS"
        }
    )

    # Server error codes for which the CUBRID broker marks the CAS for reset
    # (``reset_flag`` in CUBRID's src/broker/cas_error.c): the CAS's session
    # with cub_server is gone. The CAS reconnects only after the client ends
    # its transaction, so until then every statement fails, e.g. -111 and
    # then -224 even after cub_server restarts (#565). Matched for both
    # drivers: CUBRIDdb puts the code in ``args[0]``, pycubrid in ``errno``.
    _server_session_lost_codes = frozenset(
        {
            -111,  # ER_TM_SERVER_DOWN_UNILATERALLY_ABORTED
            -199,  # ER_NET_SERVER_CRASHED
            -224,  # ER_OBJ_NO_CONNECT ("A database has not been restarted")
            -677,  # ER_BO_CONNECT_FAILED
        }
    )

    # CAS codes (``cas_error.h``) as pycubrid actually receives them: pycubrid
    # never advertises understanding CUBRID's renewed error-code protocol (no
    # ``driver_info`` flags in its handshake), so the CAS legacy-renumbers
    # them with ``CAS_CONV_ERROR_TO_OLD`` (``src/broker/cas_protocol.h``:
    # ``V + 9000``) before sending them. -1002 is legacy CAS_ER_NO_MORE_MEMORY
    # (-10002 + 9000); see ``_disconnect_error_codes`` above for what it means
    # and why it disconnects (#578).
    _pycubrid_legacy_cas_codes = frozenset(
        {
            -1002,  # legacy CAS_ER_NO_MORE_MEMORY
        }
    )

    def is_disconnect(self, e: Exception, connection: Any, cursor: Any) -> bool:
        """Return True if *e* indicates a dropped connection.

        This dialect supports multiple drivers. Both CUBRIDdb 11.3 and
        pycubrid define the PEP 249 exception classes (CUBRIDdb has no
        ``Warning``), but the dialect does not classify disconnects by
        exception class.

        To stay robust across drivers *and* resilient to error-message
        wording drift, detection is layered: we anchor first on stable
        numeric error codes, then on an ``OSError`` in the exception's
        explicit ``__cause__`` chain (which captures socket/transport
        failures raised ``from`` a socket error without depending on
        wording), and finally fall back to string matching for driver
        errors that carry neither a code nor an ``OSError`` cause (e.g.
        pycubrid's client-side "connection lost during receive").

        Codes come from ``args[0]`` (CUBRIDdb) and, for pycubrid, from its
        ``errno`` attribute; ``errno`` is matched against the server-session
        codes (``_server_session_lost_codes``, #565) and the legacy-renumbered
        CAS codes pycubrid receives (``_pycubrid_legacy_cas_codes``, #578).
        The message fallback reads the driver's own message (``args[0]``
        when it is a string), not pycubrid's ``str()`` with its code
        description.
        """
        dbapi_module = getattr(self, "dbapi", None)
        if dbapi_module is None or not hasattr(dbapi_module, "Error"):
            try:
                dbapi_module = self.import_dbapi()
            except ImportError:
                dbapi_module = None

        if dbapi_module is None or not isinstance(e, dbapi_module.Error):
            return False

        # 1. Stable numeric error codes (wording-independent).
        error_code = self._extract_error_code(e)
        if error_code is not None and (
            error_code in self._disconnect_error_codes
            or error_code in self._server_session_lost_codes
        ):
            return True
        # pycubrid keeps the server code in ``errno`` (its ``args`` hold only
        # the message). An ``errno`` of -4 is the server's ER_INTERRUPTED (an
        # interrupted query), not a disconnect. The CCI codes in
        # ``_disconnect_error_codes`` above are CUBRIDdb's; the CAS codes
        # there reach pycubrid legacy-renumbered instead, in
        # ``_pycubrid_legacy_cas_codes`` (#578).
        pycubrid_errno = getattr(e, "errno", None)
        if (
            pycubrid_errno in self._server_session_lost_codes
            or pycubrid_errno in self._pycubrid_legacy_cas_codes
        ):
            return True

        # 2. An OSError in the explicit cause chain means a transport-level
        #    failure (socket.error is OSError on modern Python).
        if self._has_oserror_cause(e):
            return True

        # 3. Message fallback for string-only driver errors that carry
        #    neither a numeric code nor an OSError cause. Match the driver's
        #    own message: pycubrid's ``str()`` appends a description looked
        #    up from ``errno`` (-4 and -671 read "Communication error"), which
        #    must not decide the outcome. For any exception that does not
        #    override ``__str__`` a single string arg *is* ``str(e)``, and
        #    CUBRIDdb's ``(code, message)`` errors keep matching ``str(e)``.
        if len(e.args) == 1 and isinstance(e.args[0], str):
            msg = e.args[0].lower()
        else:
            msg = str(e).lower()
        return any(pattern in msg for pattern in self._disconnect_messages)

    @staticmethod
    def _has_oserror_cause(exception: BaseException) -> bool:
        """Return True if any ``OSError`` appears in *exception*'s cause chain.

        Walks only the *explicit* ``__cause__`` links (with a cycle guard)
        so that driver errors raised ``from`` a socket failure are
        recognized as disconnects regardless of their message wording.
        Implicit ``__context__`` is deliberately ignored: an unrelated
        ``OSError`` merely being handled when a DBAPI error is raised
        (or a context suppressed via ``raise ... from None``) must not
        trigger a false pool invalidation.
        """
        seen: set[int] = set()
        current: Optional[BaseException] = exception.__cause__
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if isinstance(current, OSError):
                return True
            current = current.__cause__
        return False

    @staticmethod
    def _extract_error_code(exception: Exception) -> Optional[int]:
        """Extract a numeric error code from a CUBRID DBAPI exception.

        CUBRIDdb stores the error code in ``exception.args[0]``.
        Returns ``None`` if no numeric code can be extracted.
        """
        if exception.args:
            first_arg = exception.args[0]
            if isinstance(first_arg, int):
                return first_arg
            # Some errors embed the code at the start: "-20004 ..."
            if isinstance(first_arg, str):
                parts = first_arg.split(None, 1)
                if parts:
                    try:
                        return int(parts[0])
                    except (ValueError, IndexError):
                        pass
        return None

    def do_ping(self, dbapi_connection: DBAPIConnection) -> bool:
        """Ping the server to check connection liveness.

        Used by SQLAlchemy's ``pool_pre_ping`` feature.  The CUBRID
        Python driver exposes a ``ping()`` method on the connection
        that delegates to the C-level CCI ping.
        """
        try:
            dbapi_connection.ping()
            return True
        except Exception:
            return False


dialect = CubridDialect


# Register ``CubridImpl`` with Alembic whenever Alembic is installed.
# Alembic resolves its migration implementation from ``_impls[dialect.name]``,
# which ``DefaultImpl`` subclasses populate on import via ``__dialect__``; it
# never reads a package entry point for this.  Every CUBRID dialect variant
# (``cubrid``, ``cubrid+cubriddb``, ``cubrid+pycubrid``,
# ``cubrid+aiopycubrid``) imports this module and has ``name = "cubrid"``, so
# importing ``alembic_impl`` here makes a default ``env.py`` work with no
# extra import.  Alembic stays optional: without it the import is skipped
# silently.  A broken Alembic install (for example 1.7.0/1.7.1, which raise
# ``NameError`` on SQLAlchemy 2.x) must never stop the dialect from loading,
# so any other failure only disables the integration with a warning.
try:
    from sqlalchemy_cubrid import alembic_impl as _alembic_impl  # noqa: F401
except Exception as _exc:
    try:
        _alembic_absent = importlib.util.find_spec("alembic") is None
    except Exception:  # pragma: no cover - e.g. alembic in sys.modules without a spec
        _alembic_absent = False
    if not (isinstance(_exc, ImportError) and _alembic_absent):
        _alembic_msg = (
            "sqlalchemy-cubrid: Alembic integration is disabled because the "
            f"installed Alembic failed to import ({type(_exc).__name__}: {_exc}). "
            'Install "alembic>=1.7.2,<2.0" to enable CUBRID migrations.'
        )
        # A warning filter set to "error" (``-W error``) turns warn() into a
        # raise; fall back to the logger so the dialect still loads.
        try:
            warnings.warn(_alembic_msg, RuntimeWarning, stacklevel=2)
        except Exception:
            log.warning(_alembic_msg)
