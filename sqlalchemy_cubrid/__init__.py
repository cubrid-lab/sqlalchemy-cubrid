# sqlalchemy_cubrid/__init__.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""CUBRID dialect for SQLAlchemy.

Each dialect provides the full set of typenames supported by that backend
with its ``__all__`` collection.

See: https://docs.sqlalchemy.org/en/20/core/type_basics.html#vendor-specific-types
"""

from __future__ import annotations

from .types import (
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
    MONETARY,
    MULTISET,
    NCHAR,
    NUMERIC,
    NVARCHAR,
    OBJECT,
    REAL,
    SEQUENCE,
    SET,
    SMALLINT,
    STRING,
    VARCHAR,
)
from .dml import insert, merge, replace
from .trace import trace_query

from sqlalchemy.sql.sqltypes import (
    DATE,
    DATETIME,
    INTEGER,
    TIME,
    TIMESTAMP,
)

__version__ = "1.6.0"

__all__ = (
    "insert",
    "merge",
    "replace",
    "trace_query",
    "SMALLINT",
    "INTEGER",
    "BIGINT",
    "NUMERIC",
    "DECIMAL",
    "FLOAT",
    "REAL",
    "DOUBLE",
    "DOUBLE_PRECISION",
    "MONETARY",
    "DATE",
    "TIME",
    "TIMESTAMP",
    "DATETIME",
    "BIT",
    "CHAR",
    "VARCHAR",
    "NCHAR",
    "NVARCHAR",
    "STRING",
    "BLOB",
    "CLOB",
    "SET",
    "MULTISET",
    "SEQUENCE",
    "OBJECT",
    "JSON",
    "JSONIndexType",
    "JSONPathType",
)
