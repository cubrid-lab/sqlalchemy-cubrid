# sqlalchemy_cubrid/requirements.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""CUBRID test-suite requirement flags.

These tell SQLAlchemy's built-in test suite which features this dialect
supports so tests are automatically skipped when the feature is absent.

Reference: https://github.com/sqlalchemy/sqlalchemy/blob/main/README.dialects.rst
"""

from __future__ import annotations

from typing import Final

from sqlalchemy.testing import exclusions
from sqlalchemy.testing.exclusions import compound
from sqlalchemy.testing.requirements import SuiteRequirements

_OPEN: Final[compound] = exclusions.open()  # type: ignore[no-untyped-call]
_CLOSED: Final[compound] = exclusions.closed()  # type: ignore[no-untyped-call]


class Requirements(SuiteRequirements):
    """CUBRID-specific requirement flags for the SA test suite."""

    # ----- RETURNING -----

    @property
    def returning(self) -> compound:
        """CUBRID does not support INSERT/UPDATE/DELETE … RETURNING."""
        return _CLOSED

    @property
    def insert_returning(self) -> compound:
        return _CLOSED

    @property
    def update_returning(self) -> compound:
        return _CLOSED

    @property
    def delete_returning(self) -> compound:
        return _CLOSED

    # ----- Booleans -----

    @property
    def nullable_booleans(self) -> compound:
        """CUBRID maps BOOLEAN to SMALLINT which is nullable."""
        return _OPEN

    @property
    def non_native_boolean_unconstrained(self) -> compound:
        """The SMALLINT emulation has no CHECK constraint."""
        return _OPEN

    # ----- Sequences -----

    @property
    def sequences(self) -> compound:
        """CUBRID does not support sequences."""
        return _CLOSED

    @property
    def sequences_optional(self) -> compound:
        return _CLOSED

    # ----- Schema / DDL -----

    @property
    def schemas(self) -> compound:
        """CUBRID does not support multiple schemas."""
        return _CLOSED

    @property
    def temp_table_names(self) -> compound:
        return _CLOSED

    @property
    def temporary_tables(self) -> compound:
        return _CLOSED

    @property
    def temporary_views(self) -> compound:
        return _CLOSED

    @property
    def table_ddl_if_exists(self) -> compound:
        """CUBRID supports IF NOT EXISTS / IF EXISTS in DDL."""
        return _OPEN

    @property
    def comment_reflection(self) -> compound:
        """CUBRID supports table and column comments."""
        return _OPEN

    @property
    def check_constraint_reflection(self) -> compound:
        return _CLOSED

    # ----- DML -----

    @property
    def empty_inserts(self) -> compound:
        """CUBRID supports INSERT INTO t DEFAULT VALUES."""
        return _OPEN

    @property
    def insert_from_select(self) -> compound:
        return _OPEN

    @property
    def ctes(self) -> compound:
        """CUBRID 11 supports CTEs."""
        return _OPEN

    @property
    def ctes_on_dml(self) -> compound:
        return _CLOSED

    # ----- SELECT features -----

    @property
    def window_functions(self) -> compound:
        """CUBRID supports window functions (ROW_NUMBER, RANK, etc.) with OVER()."""
        return _OPEN

    @property
    def intersect(self) -> compound:
        return _OPEN

    @property
    def except_(self) -> compound:
        return _OPEN

    @property
    def fetch_no_order(self) -> compound:
        return _CLOSED

    @property
    def order_by_col_from_union(self) -> compound:
        return _OPEN

    # ----- Type support -----

    @property
    def unicode_ddl(self) -> compound:
        return _OPEN

    @property
    def datetime_literals(self) -> compound:
        return _CLOSED

    @property
    def date(self) -> compound:
        return _OPEN

    @property
    def time(self) -> compound:
        return _OPEN

    @property
    def datetime(self) -> compound:
        return _OPEN

    @property
    def timestamp(self) -> compound:
        return _OPEN

    @property
    def text_type(self) -> compound:
        return _OPEN

    @property
    def json_type(self) -> compound:
        """CUBRID supports JSON as of version 10.2 (RFC 7159 compliant)."""
        return _OPEN

    @property
    def array_type(self) -> compound:
        return _CLOSED

    @property
    def uuid_data_type(self) -> compound:
        return _CLOSED

    # ----- Misc -----

    @property
    def views(self) -> compound:
        return _OPEN

    @property
    def savepoints(self) -> compound:
        return _OPEN

    @property
    def foreign_keys(self) -> compound:
        return _OPEN

    @property
    def self_referential_foreign_keys(self) -> compound:
        return _OPEN

    @property
    def unique_constraint_reflection(self) -> compound:
        return _OPEN

    @property
    def foreign_key_constraint_reflection(self) -> compound:
        return _OPEN

    @property
    def index_reflection(self) -> compound:
        return _OPEN

    @property
    def primary_key_constraint_reflection(self) -> compound:
        return _OPEN

    @property
    def on_update_cascade(self) -> compound:
        return _OPEN

    @property
    def on_delete_cascade(self) -> compound:
        return _OPEN

    @property
    def server_side_cursors(self) -> compound:
        return _CLOSED

    @property
    def independent_connections(self) -> compound:
        return _OPEN

    # ----- Binary / LOB -----

    @property
    def binary_comparisons(self) -> compound:
        """CUBRID BLOB roundtrip has driver-level issues."""
        return _CLOSED

    @property
    def binary_literals(self) -> compound:
        """CUBRID does not support binary literal syntax."""
        return _CLOSED

    # ----- Identifier quoting -----

    @property
    def unusual_column_name_characters(self) -> compound:
        """CUBRID has limited support for special characters in identifiers."""
        return _CLOSED

    @property
    def implicitly_named_constraints(self) -> compound:
        """CUBRID FK reflection has issues with special-character table names."""
        return _CLOSED

    # ----- SELECT FOR UPDATE -----

    @property
    def update_nowait(self) -> compound:
        """CUBRID does not support SELECT ... FOR UPDATE NOWAIT."""
        return _CLOSED

    @property
    def for_update(self) -> compound:
        """CUBRID supports SELECT ... FOR UPDATE [OF col1, col2]."""
        return _OPEN

    # ----- Two-phase commit -----

    @property
    def two_phase_transactions(self) -> compound:
        """CUBRID does not support two-phase commit (XA)."""
        return _CLOSED
