# sqlalchemy_cubrid/dialect.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""CUBRID dialect for SQLAlchemy 2.0."""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Optional, Sequence, cast

from sqlalchemy import types as sqltypes
from sqlalchemy.engine import default, reflection
from sqlalchemy.engine.interfaces import (
    DBAPIConnection,
    ConnectArgsType,
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

# Pre-compiled patterns for column type parsing in get_columns().
# Avoids re-compilation on every reflection call.
_RE_TYPE_PARAMS = re.compile(r"\([\d,]+\)")
_RE_COLLECTION = re.compile(r"^(SET|MULTISET|SEQUENCE)\s*\((.+)\)$", re.IGNORECASE)
_RE_LENGTH = re.compile(r"\((\d+)\)")


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
_RE_FOREIGN_KEY = re.compile(
    r"CONSTRAINT\s+\[(?P<name>[^\]]+)\]\s+FOREIGN\s+KEY\s*"
    r"\((?P<cols>[^)]+)\)\s+REFERENCES\s+"
    r"\[(?P<ref_table>[^\]]+)\]\s*\((?P<ref_cols>[^)]+)\)"
    r"(?:\s+ON\s+DELETE\s+(?P<ondelete>CASCADE|SET\s+NULL|NO\s+ACTION|RESTRICT))?"
    r"(?:\s+ON\s+UPDATE\s+(?P<onupdate>CASCADE|SET\s+NULL|NO\s+ACTION|RESTRICT))?",
    re.IGNORECASE,
)
# Parses ``CONSTRAINT [name] UNIQUE KEY ([col1], [col2])`` from
# ``SHOW CREATE TABLE`` output. Used as a fallback when the
# ``_db_index`` system catalog query fails.
_RE_UNIQUE_KEY = re.compile(
    r"CONSTRAINT\s+\[(?P<name>[^\]]+)\]\s+UNIQUE\s+KEY\s*"
    r"\((?P<cols>[^)]+)\)",
    re.IGNORECASE,
)
_RE_BRACKET_IDENT = re.compile(r"\[([^\]]+)\]")


# -----------------------------------------------------------------------
# Column-spec and ischema_names mappings
# -----------------------------------------------------------------------

colspecs = {
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
    # LOB
    "BLOB": BLOB,
    "CLOB": CLOB,
    # Collection
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

    requires_name_normalize = True

    # Data type support
    supports_native_enum = False
    supports_native_boolean = False  # CUBRID uses SMALLINT for booleans
    supports_native_decimal = True
    supports_native_lateral = False

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
    supports_is_distinct_from = False

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
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.isolation_level = isolation_level
        self._json_serializer = json_serializer
        self._json_deserializer = json_deserializer

    @classmethod
    def import_dbapi(cls) -> DBAPIModule:
        """Import and return the CUBRID DBAPI module (SA 2.0 API)."""
        try:
            import CUBRIDdb as cubrid_dbapi  # type: ignore[import-not-found]  # pyright: ignore[reportMissingImports]
        except ImportError as e:
            raise ImportError(
                "Could not import CUBRIDdb. Install 'CUBRID-Python' for "
                "cubrid:// URLs, or use cubrid+pycubrid:// with 'pycubrid': "
                "pip install CUBRID-Python"
            ) from e
        return cast(DBAPIModule, cubrid_dbapi)  # pyright: ignore[reportInvalidCast]

    # Keep legacy dbapi() for SA 1.x compat if needed
    @classmethod
    def dbapi(cls) -> DBAPIModule:  # type: ignore[override]
        return cls.import_dbapi()

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
        log.debug(
            "CUBRID dialect initialized: server_version=%s",
            self.server_version_info,
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
        columns: list[ReflectedColumn] = []
        quoted = self.identifier_preparer.quote_identifier(table_name)
        result = connection.execute(text(f"SHOW COLUMNS IN {quoted}"))
        for row in result:
            colname = row[0]
            coltype_raw = row[1]
            nullable = row[2] == "YES"
            default_val = row[4]
            autoincrement = "auto_increment" in row[5] if row[5] else False

            # Strip length/precision from type string for lookup
            coltype_key = _RE_TYPE_PARAMS.sub("", coltype_raw).strip()

            # Collection types: SET(VARCHAR(100)), MULTISET(INT), etc.
            collection_match = _RE_COLLECTION.match(coltype_raw)
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

        try:
            comment_result = connection.execute(
                text(
                    "SELECT attr_name, comment FROM _db_attribute "
                    "WHERE class_name = :name ORDER BY def_order"
                ),
                {"name": table_name},
            )
            comment_map = {row[0]: row[1] for row in comment_result}
        except Exception:
            log.debug("Column comment query failed for %s", table_name, exc_info=True)
            comment_map = {}

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
        constraint_name = None
        constrained_columns: list[str] = []

        quoted = self.identifier_preparer.quote_identifier(table_name)
        result = connection.execute(text(f"SHOW COLUMNS IN {quoted}"))
        for row in result:
            if row[3] == "PRI":
                constrained_columns.append(row[0])

        # Find the PK constraint name from _db_index (the authoritative
        # system catalog view for index metadata).
        if constrained_columns:
            try:
                constraint_result = connection.execute(
                    text(
                        "SELECT index_name FROM _db_index "
                        "WHERE class_of.class_name = :table AND is_primary_key = 1"
                    ),
                    {"table": table_name},
                )
                row = constraint_result.fetchone()
                if row:
                    constraint_name = row[0]
            except Exception:  # nosec B110 — constraint name is optional metadata
                log.debug("PK constraint name query failed for %s", table_name, exc_info=True)

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
        """
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
            row = result.fetchone()
        except Exception:  # nosec B110 — graceful fallback when DDL unavailable
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
                "WHERE class_type = 'CLASS' AND is_system_class = 'NO'"
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
            text("SELECT class_name FROM db_class WHERE class_type = 'VCLASS'")
        )
        return [row[0] for row in result]

    @reflection.cache
    def get_view_definition(
        self, connection: Any, view_name: str, schema: str | None = None, **kw: Any
    ) -> str:
        """Return the CREATE VIEW definition."""
        quoted = self.identifier_preparer.quote_identifier(view_name)
        result = connection.execute(text(f"SHOW CREATE VIEW {quoted}"))
        row = result.fetchone()
        if row is None:
            return ""
        return str(row[1])

    @reflection.cache
    def get_indexes(
        self,
        connection: Any,
        table_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> list[ReflectedIndex]:
        """Return index information for *table_name*."""
        idict: dict[str, ReflectedIndex] = {}

        # Batch-fetch primary-key and foreign-key flags for all indexes on
        # this table from CUBRID's ``_db_index`` catalog (single query for
        # both, instead of N+1 lookups).
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
        try:
            flag_result = connection.execute(
                text(
                    "SELECT index_name, is_primary_key, is_foreign_key "
                    "FROM _db_index WHERE class_of.class_name = :table"
                ),
                {"table": table_name},
            )
            for flag_row in flag_result:
                if flag_row[1]:
                    pk_indexes.add(flag_row[0])
                if flag_row[2]:
                    fk_indexes.add(flag_row[0])
        except Exception:
            # Fallback: if the catalog query fails, both sets stay empty so
            # no indexes will be wrongly excluded.
            log.debug(
                "Batch index-flag query failed for table %s, falling back",
                table_name,
                exc_info=True,
            )

        quoted = self.identifier_preparer.quote_identifier(table_name)
        result = connection.execute(text(f"SHOW INDEXES IN {quoted}"))
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

        Primary path: query the ``_db_index`` system catalog for unique
        indexes (excluding PK and FK auto-indexes), then resolve column
        names via ``SHOW INDEXES``. Fallback: parse ``SHOW CREATE TABLE``
        DDL output via regex.
        """
        # Primary path: system catalog + SHOW INDEXES
        try:
            uqs = self._get_unique_constraints_from_catalog(connection, table_name)
            if uqs:
                return uqs
        except Exception:  # nosec B110 — graceful fallback
            log.debug(
                "Catalog query failed for unique constraints on %s; falling back to DDL regex",
                table_name,
                exc_info=True,
            )

        # Fallback: DDL regex (legacy path)
        return self._get_unique_constraints_from_ddl(connection, table_name)

    def _get_unique_constraints_from_catalog(
        self,
        connection: Any,
        table_name: str,
    ) -> list[ReflectedUniqueConstraint]:
        """Query _db_index + SHOW INDEXES for UNIQUE constraints.

        Uses the same two-query pattern as ``get_indexes()``: first fetch
        unique index names from ``_db_index`` (filtering out PK and FK
        auto-indexes), then resolve column names from ``SHOW INDEXES``.
        """
        # Step 1: get unique index names (excluding PK and FK auto-indexes)
        unique_names: set[str] = set()
        name_result = connection.execute(
            text(
                "SELECT index_name FROM _db_index "
                "WHERE class_of.class_name = :table "
                "AND is_unique = 1 AND is_primary_key = 0 AND is_foreign_key = 0"
            ),
            {"table": table_name},
        )
        for row in name_result:
            unique_names.add(row[0])
        if not unique_names:
            return []

        # Step 2: resolve column names from SHOW INDEXES
        quoted = self.identifier_preparer.quote_identifier(table_name)
        col_result = connection.execute(text(f"SHOW INDEXES IN {quoted}"))
        constraints: dict[str, list[str]] = {}
        for row in col_result:
            index_name = row[2]
            if index_name in unique_names:
                constraints.setdefault(index_name, []).append(row[4])

        return [{"name": name, "column_names": cols} for name, cols in constraints.items()]

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
            row = result.fetchone()
        except Exception:  # nosec B110 — graceful fallback when DDL unavailable
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
            unique_constraints.append({"name": constraint_name, "column_names": column_names})
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
        """Return table comment from CUBRID system catalog."""
        result = connection.execute(
            text("SELECT comment FROM db_class WHERE class_name = :name"),
            {"name": table_name},
        )
        row = result.fetchone()
        return {"text": row[0] if row and row[0] else None}

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
        always accepted.  A non-``None`` schema is accepted only when it matches
        :attr:`default_schema_name`.  Every list/existence reflection method uses
        this so that ``schema=`` is honoured uniformly instead of some methods
        silently ignoring it (which previously produced, e.g., 0 tables but all
        views for ``MetaData.reflect(schema=...)``).
        """
        return schema is None or schema == self.default_schema_name

    def has_table(
        self,
        connection: Any,
        table_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> bool:
        """Check if *table_name* exists."""
        if not self._schema_is_default(schema):
            return False
        result = connection.execute(
            text(
                "SELECT COUNT(*) FROM db_class "
                "WHERE class_type IN ('CLASS', 'VCLASS') "
                "AND is_system_class = 'NO' "
                "AND class_name = :name"
            ),
            {"name": table_name},
        )
        return bool(result.scalar())

    def has_index(
        self,
        connection: Any,
        table_name: str,
        index_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> bool:
        """Check if an index named *index_name* exists on *table_name*."""
        if not self._schema_is_default(schema):
            return False
        try:
            result = connection.execute(
                text(
                    "SELECT COUNT(*) FROM _db_index "
                    "WHERE class_of.class_name = :table AND index_name = :name"
                ),
                {"table": table_name, "name": index_name},
            )
            return bool(result.scalar())
        except Exception:
            log.debug("has_index query failed for %s.%s", table_name, index_name, exc_info=True)
            return False

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
        SQLAlchemy can manage transactions properly.
        """
        isolation_level = self.isolation_level

        def connect(conn: Any) -> None:
            # CUBRID Python driver defaults to autocommit=True;
            # SA manages transactions, so we turn it off.
            conn.set_autocommit(False)
            if isolation_level is not None:
                self.set_isolation_level(conn, isolation_level)

        return connect

    def _get_server_version_info(self, connection: Any) -> tuple[int, int, int, int] | None:
        """Return server version as a tuple of ints."""
        versions = connection.execute(text("SELECT VERSION()")).scalar()
        m = re.match(r"(\d+)\.(\d+)\.(\d+)\.(\d+)", versions)
        if m:
            return (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
        return None

    def _get_default_schema_name(self, connection: Any) -> str:
        """Return the default schema name."""
        return str(connection.execute(text("SELECT SCHEMA()")).scalar())

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
        "REPEATABLE READ SCHEMA, READ UNCOMMITTED INSTANCES": 3,
        "READ COMMITTED SCHEMA, READ COMMITTED INSTANCES": 2,
        "READ COMMITTED SCHEMA, READ UNCOMMITTED INSTANCES": 1,
    }

    _ISOLATION_LEVEL_REVERSE: dict[int, str] = {
        6: "SERIALIZABLE",
        5: "REPEATABLE READ SCHEMA, REPEATABLE READ INSTANCES",
        4: "REPEATABLE READ SCHEMA, READ COMMITTED INSTANCES",
        3: "REPEATABLE READ SCHEMA, READ UNCOMMITTED INSTANCES",
        2: "READ COMMITTED SCHEMA, READ COMMITTED INSTANCES",
        1: "READ COMMITTED SCHEMA, READ UNCOMMITTED INSTANCES",
    }

    def get_isolation_level(self, dbapi_connection: DBAPIConnection) -> str:  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]
        """Return the current isolation level for *dbapi_conn*."""
        # https://www.cubrid.org/manual/en/11.0/sql/transaction.html
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("GET TRANSACTION ISOLATION LEVEL TO X")
            cursor.execute("SELECT X")
            row = cursor.fetchone()
            if row is None:
                return "REPEATABLE READ SCHEMA, READ COMMITTED INSTANCES"
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
            "REPEATABLE READ SCHEMA, READ UNCOMMITTED INSTANCES",
            "READ COMMITTED SCHEMA, READ COMMITTED INSTANCES",
            "READ COMMITTED SCHEMA, READ UNCOMMITTED INSTANCES",
        ]

    def set_isolation_level(
        self,
        dbapi_connection: DBAPIConnection,
        level: str,
    ) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Set the isolation level for *dbapi_conn*."""
        # Note: do NOT unwrap dbapi_conn.connection — the inner C-level
        # _cubrid.connection cursor cannot handle SET TRANSACTION SQL.
        # SA already passes the correct Python-level CUBRIDdb.connections.Connection.
        # Map string level to numeric
        numeric_level = self._ISOLATION_LEVEL_MAP.get(level.upper())
        if numeric_level is None:
            raise ValueError(
                f"Invalid isolation level: {level!r}. "
                f"Valid values: {list(self._ISOLATION_LEVEL_MAP.keys())}"
            )
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f"SET TRANSACTION ISOLATION LEVEL {numeric_level}")
            cursor.execute("COMMIT")
        finally:
            cursor.close()

    def reset_isolation_level(self, dbapi_conn: DBAPIConnection) -> None:
        """Revert isolation level to the CUBRID default (level 4)."""
        self.set_isolation_level(dbapi_conn, "REPEATABLE READ SCHEMA, READ COMMITTED INSTANCES")

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
    )

    def is_disconnect(self, e: Exception, connection: Any, cursor: Any) -> bool:
        """Return True if *e* indicates a dropped connection.

        CUBRID's Python driver exposes a limited exception hierarchy:
        ``Error``, ``InterfaceError``, ``DatabaseError``, and
        ``NotSupportedError``.  There is no ``OperationalError`` class,
        so we rely primarily on string-based message matching (similar
        to psycopg2) supplemented by known numeric error codes.
        """
        dbapi_module = getattr(self, "dbapi", None)
        if dbapi_module is None or not hasattr(dbapi_module, "Error"):
            try:
                dbapi_module = self.import_dbapi()
            except ImportError:
                dbapi_module = None

        if dbapi_module is not None and isinstance(e, dbapi_module.Error):
            msg = str(e).lower()
            for pattern in self._disconnect_messages:
                if pattern in msg:
                    return True

            # Check numeric error code for known disconnect codes
            error_code = self._extract_error_code(e)
            if error_code is not None and error_code in (
                -21003,  # CAS_ER_COMMUNICATION
                -21005,  # CAS_ER_COMMUNICATION (alternate)
                -10005,  # ER_NET_CANT_CONNECT
                -10007,  # ER_NET_SERVER_COMM_ERROR
            ):
                return True
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
            # Some errors embed the code at the start: "-21003 ..."
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
