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

from typing import Any

from sqlalchemy.testing import exclusions
from sqlalchemy.testing.exclusions import compound
from sqlalchemy.testing.requirements import SuiteRequirements


# Every property must return a NEW compound. When @testing.requires decorators
# are stacked, SQLAlchemy stores the first compound on the test function and
# extends it in place with the others (compound._extend), so a shared
# module-level instance would absorb every other rule's skips: after one
# `@requires.sequences @requires.views` test, all "open" requirements became
# closed and silently skipped large parts of the compliance suite (#463).
def _open() -> compound:
    rule: compound = exclusions.open()  # type: ignore[no-untyped-call]
    return rule


def _closed() -> compound:
    rule: compound = exclusions.closed()  # type: ignore[no-untyped-call]
    return rule


def _database_is_utf8(config: Any) -> bool:
    """True when the target database's charset (that of a string literal) is UTF-8."""
    with config.db.connect() as conn:
        charset = conn.exec_driver_sql("SELECT CHARSET('a')").scalar()
    return str(charset).lower() == "utf8"


class Requirements(SuiteRequirements):
    """CUBRID-specific requirement flags for the SA test suite."""

    # ----- RETURNING -----

    @property
    def returning(self) -> compound:
        """CUBRID does not support INSERT/UPDATE/DELETE … RETURNING."""
        return _closed()

    @property
    def insert_returning(self) -> compound:
        return _closed()

    @property
    def update_returning(self) -> compound:
        return _closed()

    @property
    def delete_returning(self) -> compound:
        return _closed()

    # ----- Booleans -----

    @property
    def nullable_booleans(self) -> compound:
        """CUBRID maps BOOLEAN to SMALLINT which is nullable."""
        return _open()

    @property
    def non_native_boolean_unconstrained(self) -> compound:
        """The SMALLINT emulation has no CHECK constraint."""
        return _open()

    # ----- Sequences -----

    @property
    def sequences(self) -> compound:
        """CUBRID does not support sequences."""
        return _closed()

    @property
    def sequences_optional(self) -> compound:
        return _closed()

    # ----- Schema / DDL -----

    @property
    def schemas(self) -> compound:
        """CUBRID does not support multiple schemas."""
        return _closed()

    @property
    def temp_table_names(self) -> compound:
        return _closed()

    @property
    def has_temp_table(self) -> compound:
        """CUBRID has no CREATE TEMPORARY TABLE, so the reflection suite must
        not try to provision a temp table via ``temp_table_keyword_args``."""
        return _closed()

    @property
    def temp_table_reflection(self) -> compound:
        """CUBRID has no temp tables to reflect; skip the temp-table branch of
        ComponentReflectionTest's fixture setup."""
        return _closed()

    @property
    def temporary_tables(self) -> compound:
        return _closed()

    @property
    def temporary_views(self) -> compound:
        return _closed()

    @property
    def table_ddl_if_exists(self) -> compound:
        """CUBRID supports IF NOT EXISTS / IF EXISTS in DDL."""
        return _open()

    @property
    def comment_reflection(self) -> compound:
        """CUBRID supports table and column comments."""
        return _open()

    @property
    def check_constraint_reflection(self) -> compound:
        return _closed()

    # ----- DML -----

    @property
    def empty_inserts(self) -> compound:
        """CUBRID supports INSERT INTO t DEFAULT VALUES."""
        return _open()

    @property
    def insert_from_select(self) -> compound:
        return _open()

    @property
    def ctes(self) -> compound:
        """CUBRID 11 supports CTEs."""
        return _open()

    @property
    def ctes_on_dml(self) -> compound:
        return _closed()

    # ----- SELECT features -----

    @property
    def window_functions(self) -> compound:
        """CUBRID supports window functions (ROW_NUMBER, RANK, etc.) with OVER()."""
        return _open()

    @property
    def intersect(self) -> compound:
        return _open()

    @property
    def except_(self) -> compound:
        return _open()

    @property
    def fetch_no_order(self) -> compound:
        return _closed()

    @property
    def order_by_col_from_union(self) -> compound:
        return _open()

    # ----- Type support -----

    @property
    def unicode_ddl(self) -> compound:
        """Non-ASCII identifiers need a UTF-8 database. The official Docker
        image (and so CI) creates ISO-8859-1 databases (CUBRID_LOCALE=en_US),
        where both drivers fail to decode the catalog once such a table exists,
        and the undroppable leftovers break every later test (#463)."""
        rule: compound = exclusions.skip_if(  # type: ignore[no-untyped-call]
            lambda config: not _database_is_utf8(config),
            "database charset is not UTF-8",
        )
        return rule

    @property
    def datetime_literals(self) -> compound:
        return _closed()

    @property
    def date(self) -> compound:
        return _open()

    @property
    def time(self) -> compound:
        return _open()

    @property
    def datetime(self) -> compound:
        return _open()

    @property
    def timestamp(self) -> compound:
        return _open()

    @property
    def datetime_microseconds(self) -> compound:
        """CUBRID DATETIME stores millisecond precision only (39642µs → 39000µs)."""
        return _closed()

    @property
    def time_microseconds(self) -> compound:
        """CUBRID TIME stores no fractional seconds."""
        return _closed()

    @property
    def precision_generic_float_type(self) -> compound:
        """CUBRID FLOAT is IEEE single precision (~7 significant digits), so the
        generic Float type cannot return seven decimal places (15.7563827 comes
        back as 15.7563829) on either driver. SQLAlchemy excludes MySQL's FLOAT
        for the same reason."""
        return _closed()

    @property
    def text_type(self) -> compound:
        return _open()

    @property
    def json_type(self) -> compound:
        """CUBRID supports JSON as of version 10.2 (RFC 7159 compliant)."""
        return _open()

    @property
    def array_type(self) -> compound:
        return _closed()

    @property
    def uuid_data_type(self) -> compound:
        return _closed()

    # ----- Misc -----

    @property
    def views(self) -> compound:
        return _open()

    @property
    def savepoints(self) -> compound:
        return _open()

    @property
    def foreign_keys(self) -> compound:
        return _open()

    @property
    def self_referential_foreign_keys(self) -> compound:
        return _open()

    @property
    def unique_constraint_reflection(self) -> compound:
        return _open()

    @property
    def foreign_key_constraint_reflection(self) -> compound:
        return _open()

    @property
    def index_reflection(self) -> compound:
        return _open()

    @property
    def primary_key_constraint_reflection(self) -> compound:
        return _open()

    @property
    def on_update_cascade(self) -> compound:
        return _open()

    @property
    def on_delete_cascade(self) -> compound:
        return _open()

    @property
    def server_side_cursors(self) -> compound:
        return _closed()

    @property
    def independent_connections(self) -> compound:
        return _open()

    # ----- Binary / LOB -----

    @property
    def binary_comparisons(self) -> compound:
        """CUBRID BLOB roundtrip has driver-level issues."""
        return _closed()

    @property
    def binary_literals(self) -> compound:
        """CUBRID does not support binary literal syntax."""
        return _closed()

    # ----- Identifier quoting -----

    @property
    def unusual_column_name_characters(self) -> compound:
        """CUBRID has limited support for special characters in identifiers."""
        return _closed()

    @property
    def implicitly_named_constraints(self) -> compound:
        """CUBRID names unnamed constraints itself (e.g. ``fk_<table>_<col>``); the
        suite reports an unexpected success when this is closed (#463)."""
        return _open()

    @property
    def reflects_pk_names(self) -> compound:
        """Primary-key names (``pk_<table>_<col>``) are reflected; the suite
        reports an unexpected success when this is closed (#463)."""
        return _open()

    # ----- SELECT FOR UPDATE -----

    @property
    def update_nowait(self) -> compound:
        """CUBRID does not support SELECT ... FOR UPDATE NOWAIT."""
        return _closed()

    @property
    def for_update(self) -> compound:
        """CUBRID supports SELECT ... FOR UPDATE [OF col1, col2]."""
        return _open()

    # ----- Two-phase commit -----

    @property
    def two_phase_transactions(self) -> compound:
        """CUBRID does not support two-phase commit (XA)."""
        return _closed()
