# test/test_show_create_table.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Golden tests for SHOW CREATE TABLE parsing (FK + UNIQUE reflection).

The dialect parses ``SHOW CREATE TABLE`` DDL output via regex to extract
foreign key and unique constraint metadata.  This test module provides a
comprehensive fixture corpus to lock the parsing behaviour against
regressions.

Addresses: https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/125
"""

from __future__ import annotations

from typing import Any

import pytest

# Import the internal regexes used by the dialect
from sqlalchemy_cubrid.dialect import _RE_BRACKET_IDENT, _RE_FOREIGN_KEY, _RE_UNIQUE_KEY


# ---------------------------------------------------------------------------
# Helpers — mirror the parsing logic in dialect.py so we test the regexes
# directly without needing a mock connection.
# ---------------------------------------------------------------------------


def parse_foreign_keys(ddl: str) -> list[dict[str, Any]]:
    """Parse FK constraints from a DDL string (same logic as dialect.get_foreign_keys)."""
    foreign_keys: list[dict[str, Any]] = []
    for fk_match in _RE_FOREIGN_KEY.finditer(ddl):
        constraint_name = fk_match.group("name")
        constrained_columns = [
            col.strip() for col in _RE_BRACKET_IDENT.findall(fk_match.group("cols"))
        ]
        ref_table_raw = fk_match.group("ref_table")
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
                "referred_table": ref_table,
                "referred_columns": referred_columns,
            }
        )
    return foreign_keys


def parse_unique_constraints(ddl: str) -> list[dict[str, Any]]:
    """Parse UNIQUE constraints from a DDL string (same logic as dialect.get_unique_constraints)."""
    unique_constraints: list[dict[str, Any]] = []
    for uc_match in _RE_UNIQUE_KEY.finditer(ddl):
        constraint_name = uc_match.group("name")
        column_names = [col.strip() for col in _RE_BRACKET_IDENT.findall(uc_match.group("cols"))]
        unique_constraints.append({"name": constraint_name, "column_names": column_names})
    return unique_constraints


# ---------------------------------------------------------------------------
# FK fixture corpus
# ---------------------------------------------------------------------------

FK_FIXTURES: list[tuple[str, str, list[dict[str, Any]]]] = [
    # (id, ddl, expected_fks)
    (
        "single_column_fk",
        (
            "CREATE TABLE [orders] (\n"
            "  [id] INTEGER NOT NULL,\n"
            "  [user_id] INTEGER,\n"
            "  CONSTRAINT [pk_orders] PRIMARY KEY ([id]),\n"
            "  CONSTRAINT [fk_orders_user] FOREIGN KEY ([user_id]) "
            "REFERENCES [users] ([id])\n"
            ")"
        ),
        [
            {
                "name": "fk_orders_user",
                "constrained_columns": ["user_id"],
                "options": {},
                "referred_table": "users",
                "referred_columns": ["id"],
            }
        ],
    ),
    (
        "multi_column_composite_fk",
        (
            "CREATE TABLE [order_items] (\n"
            "  [order_id] INTEGER NOT NULL,\n"
            "  [tenant_id] INTEGER NOT NULL,\n"
            "  CONSTRAINT [fk_items_order] FOREIGN KEY ([order_id], [tenant_id]) "
            "REFERENCES [orders] ([id], [tenant_id])\n"
            ")"
        ),
        [
            {
                "name": "fk_items_order",
                "constrained_columns": ["order_id", "tenant_id"],
                "options": {},
                "referred_table": "orders",
                "referred_columns": ["id", "tenant_id"],
            }
        ],
    ),
    (
        "owner_qualified_ref_table",
        (
            "CREATE TABLE [orders] (\n"
            "  [user_id] INTEGER,\n"
            "  CONSTRAINT [fk_order_user] FOREIGN KEY ([user_id]) "
            "REFERENCES [dba.users] ([id])\n"
            ")"
        ),
        [
            {
                "name": "fk_order_user",
                "constrained_columns": ["user_id"],
                "options": {},
                "referred_table": "users",  # owner prefix stripped
                "referred_columns": ["id"],
            }
        ],
    ),
    (
        "multiple_fks_same_table",
        (
            "CREATE TABLE [shipments] (\n"
            "  [id] INTEGER NOT NULL,\n"
            "  [from_addr_id] INTEGER,\n"
            "  [to_addr_id] INTEGER,\n"
            "  CONSTRAINT [pk_ship] PRIMARY KEY ([id]),\n"
            "  CONSTRAINT [fk_ship_from] FOREIGN KEY ([from_addr_id]) "
            "REFERENCES [addresses] ([id]),\n"
            "  CONSTRAINT [fk_ship_to] FOREIGN KEY ([to_addr_id]) "
            "REFERENCES [addresses] ([id])\n"
            ")"
        ),
        [
            {
                "name": "fk_ship_from",
                "constrained_columns": ["from_addr_id"],
                "options": {},
                "referred_table": "addresses",
                "referred_columns": ["id"],
            },
            {
                "name": "fk_ship_to",
                "constrained_columns": ["to_addr_id"],
                "options": {},
                "referred_table": "addresses",
                "referred_columns": ["id"],
            },
        ],
    ),
    (
        "fk_with_on_delete_cascade",
        (
            "CREATE TABLE [comments] (\n"
            "  [id] INTEGER NOT NULL,\n"
            "  [post_id] INTEGER,\n"
            "  CONSTRAINT [fk_comment_post] FOREIGN KEY ([post_id]) "
            "REFERENCES [posts] ([id]) ON DELETE CASCADE ON UPDATE RESTRICT\n"
            ")"
        ),
        [
            {
                "name": "fk_comment_post",
                "constrained_columns": ["post_id"],
                "options": {"ondelete": "CASCADE", "onupdate": "RESTRICT"},
                "referred_table": "posts",
                "referred_columns": ["id"],
            }
        ],
    ),
    (
        "fk_with_on_delete_set_null",
        (
            "CREATE TABLE [tasks] (\n"
            "  [assignee_id] INTEGER,\n"
            "  CONSTRAINT [fk_task_assignee] FOREIGN KEY ([assignee_id]) "
            "REFERENCES [employees] ([id]) ON DELETE SET NULL ON UPDATE NO ACTION\n"
            ")"
        ),
        [
            {
                "name": "fk_task_assignee",
                "constrained_columns": ["assignee_id"],
                "options": {"ondelete": "SET NULL", "onupdate": "NO ACTION"},
                "referred_table": "employees",
                "referred_columns": ["id"],
            }
        ],
    ),
    (
        "mixed_pk_fk_unique",
        (
            "CREATE TABLE [enrollments] (\n"
            "  [id] INTEGER AUTO_INCREMENT NOT NULL,\n"
            "  [student_id] INTEGER NOT NULL,\n"
            "  [course_id] INTEGER NOT NULL,\n"
            "  CONSTRAINT [pk_enroll] PRIMARY KEY ([id]),\n"
            "  CONSTRAINT [uq_enroll_pair] UNIQUE KEY ([student_id], [course_id]),\n"
            "  CONSTRAINT [fk_enroll_student] FOREIGN KEY ([student_id]) "
            "REFERENCES [students] ([id]),\n"
            "  CONSTRAINT [fk_enroll_course] FOREIGN KEY ([course_id]) "
            "REFERENCES [dba.courses] ([id])\n"
            ")"
        ),
        [
            {
                "name": "fk_enroll_student",
                "constrained_columns": ["student_id"],
                "options": {},
                "referred_table": "students",
                "referred_columns": ["id"],
            },
            {
                "name": "fk_enroll_course",
                "constrained_columns": ["course_id"],
                "options": {},
                "referred_table": "courses",
                "referred_columns": ["id"],
            },
        ],
    ),
    (
        "no_constraints",
        ("CREATE TABLE [simple] (\n  [id] INTEGER NOT NULL,\n  [name] VARCHAR(100)\n)"),
        [],
    ),
    (
        "extra_whitespace_newlines",
        (
            "CREATE TABLE [orders] (\n"
            "  [id]    INTEGER   NOT NULL,\n"
            "  [user_id]  INTEGER,\n"
            "  CONSTRAINT   [fk_ws_test]   FOREIGN   KEY   ([user_id])   "
            "REFERENCES   [users]   ([id])\n"
            ")"
        ),
        [
            {
                "name": "fk_ws_test",
                "constrained_columns": ["user_id"],
                "options": {},
                "referred_table": "users",
                "referred_columns": ["id"],
            }
        ],
    ),
    (
        "fk_case_insensitive",
        (
            "CREATE TABLE [test] (\n"
            "  [ref_id] INTEGER,\n"
            "  constraint [fk_lower] foreign key ([ref_id]) "
            "references [other] ([id])\n"
            ")"
        ),
        [
            {
                "name": "fk_lower",
                "constrained_columns": ["ref_id"],
                "options": {},
                "referred_table": "other",
                "referred_columns": ["id"],
            }
        ],
    ),
    (
        "fk_three_column_composite",
        (
            "CREATE TABLE [detail] (\n"
            "  [a] INTEGER, [b] INTEGER, [c] INTEGER,\n"
            "  CONSTRAINT [fk_abc] FOREIGN KEY ([a], [b], [c]) "
            "REFERENCES [master] ([x], [y], [z])\n"
            ")"
        ),
        [
            {
                "name": "fk_abc",
                "constrained_columns": ["a", "b", "c"],
                "options": {},
                "referred_table": "master",
                "referred_columns": ["x", "y", "z"],
            }
        ],
    ),
    (
        "fk_multi_column_with_actions",
        (
            "CREATE TABLE [order_items] (\n"
            "  [order_id] INTEGER NOT NULL,\n"
            "  [tenant_id] INTEGER NOT NULL,\n"
            "  CONSTRAINT [fk_items_order_action] FOREIGN KEY ([order_id], [tenant_id]) "
            "REFERENCES [orders] ([id], [tenant_id]) ON DELETE CASCADE ON UPDATE SET NULL\n"
            ")"
        ),
        [
            {
                "name": "fk_items_order_action",
                "constrained_columns": ["order_id", "tenant_id"],
                "options": {"ondelete": "CASCADE", "onupdate": "SET NULL"},
                "referred_table": "orders",
                "referred_columns": ["id", "tenant_id"],
            }
        ],
    ),
    (
        "fk_owner_prefix_with_multiple_dots",
        (
            "CREATE TABLE [orders] (\n"
            "  [item_id] INTEGER,\n"
            "  CONSTRAINT [fk_order_item] FOREIGN KEY ([item_id]) "
            "REFERENCES [dba.schema.items] ([id]) ON DELETE RESTRICT\n"
            ")"
        ),
        [
            {
                "name": "fk_order_item",
                "constrained_columns": ["item_id"],
                "options": {"ondelete": "RESTRICT"},
                "referred_table": "schema.items",
                "referred_columns": ["id"],
            }
        ],
    ),
    (
        "fk_extra_whitespace_with_actions",
        (
            "CREATE TABLE [audit] (\n"
            "  [actor_id] INTEGER,\n"
            "  CONSTRAINT  [fk_audit_actor]  FOREIGN KEY  ([actor_id])\n"
            "    REFERENCES   [users]  ([id])   ON DELETE   NO ACTION   ON UPDATE   CASCADE\n"
            ")"
        ),
        [
            {
                "name": "fk_audit_actor",
                "constrained_columns": ["actor_id"],
                "options": {"ondelete": "NO ACTION", "onupdate": "CASCADE"},
                "referred_table": "users",
                "referred_columns": ["id"],
            }
        ],
    ),
    # Names containing ( ) , and spaces (#532), as printed by CUBRID 11.4:
    # the column lists must not stop at the first ")".
    (
        "fk_bracketed_names_with_parens_commas_spaces",
        (
            "CREATE TABLE [c532] ([id] INTEGER NOT NULL, [r(1)] INTEGER, [r, 2] INTEGER,  "
            "CONSTRAINT [pk_c532_id] PRIMARY KEY  ([id]),  "
            "CONSTRAINT [fk (odd), name] FOREIGN KEY  ([r(1)], [r, 2]) "
            "REFERENCES [dba.p532] ([(3)], [a, b]) ON DELETE CASCADE ON UPDATE RESTRICT"
            ") REUSE_OID, COLLATE iso88591_bin"
        ),
        [
            {
                "name": "fk (odd), name",
                "constrained_columns": ["r(1)", "r, 2"],
                "options": {"ondelete": "CASCADE", "onupdate": "RESTRICT"},
                "referred_table": "p532",
                "referred_columns": ["(3)", "a, b"],
            }
        ],
    ),
    (
        "fk_whitespace_inside_parentheses",
        "CONSTRAINT [fk_ws] FOREIGN KEY (  [c (1)], [d] ) REFERENCES [dba.p] ( [(3)] ,[e] )",
        [
            {
                "name": "fk_ws",
                "constrained_columns": ["c (1)", "d"],
                "options": {},
                "referred_table": "p",
                "referred_columns": ["(3)", "e"],
            }
        ],
    ),
    (
        "fk_referred_column_is_parenthesized",
        (
            "CREATE TABLE [c] ([id] INTEGER NOT NULL, [plain] INTEGER,  "
            "CONSTRAINT [fk_c_plain] FOREIGN KEY  ([plain]) REFERENCES [dba.p] ([(3)]) "
            "ON DELETE RESTRICT ON UPDATE RESTRICT)"
        ),
        [
            {
                "name": "fk_c_plain",
                "constrained_columns": ["plain"],
                "options": {"ondelete": "RESTRICT", "onupdate": "RESTRICT"},
                "referred_table": "p",
                "referred_columns": ["(3)"],
            }
        ],
    ),
    (
        "fk_constrained_column_has_closing_paren_and_percent",
        (
            "CONSTRAINT [fk_x] FOREIGN KEY ([x ) y], [per % cent]) "
            "REFERENCES [dba.p] ([(2)], [two words])"
        ),
        [
            {
                "name": "fk_x",
                "constrained_columns": ["x ) y", "per % cent"],
                "options": {},
                "referred_table": "p",
                "referred_columns": ["(2)", "two words"],
            }
        ],
    ),
]


# ---------------------------------------------------------------------------
# UNIQUE constraint fixture corpus
# ---------------------------------------------------------------------------

UNIQUE_FIXTURES: list[tuple[str, str, list[dict[str, Any]]]] = [
    (
        "single_column_unique",
        (
            "CREATE TABLE [users] (\n"
            "  [id] INTEGER NOT NULL,\n"
            "  [email] VARCHAR(200),\n"
            "  CONSTRAINT [pk_users] PRIMARY KEY ([id]),\n"
            "  CONSTRAINT [uq_email] UNIQUE KEY ([email])\n"
            ")"
        ),
        [{"name": "uq_email", "column_names": ["email"]}],
    ),
    (
        "multi_column_unique",
        (
            "CREATE TABLE [users] (\n"
            "  [id] INTEGER NOT NULL,\n"
            "  CONSTRAINT [uq_multi] UNIQUE KEY ([email], [tenant_id])\n"
            ")"
        ),
        [{"name": "uq_multi", "column_names": ["email", "tenant_id"]}],
    ),
    (
        "multiple_unique_constraints",
        (
            "CREATE TABLE [products] (\n"
            "  [id] INTEGER NOT NULL,\n"
            "  [sku] VARCHAR(50),\n"
            "  [barcode] VARCHAR(50),\n"
            "  CONSTRAINT [uq_sku] UNIQUE KEY ([sku]),\n"
            "  CONSTRAINT [uq_barcode] UNIQUE KEY ([barcode])\n"
            ")"
        ),
        [
            {"name": "uq_sku", "column_names": ["sku"]},
            {"name": "uq_barcode", "column_names": ["barcode"]},
        ],
    ),
    (
        "no_unique_constraints",
        ("CREATE TABLE [plain] (\n  [id] INTEGER NOT NULL,\n  [name] VARCHAR(100)\n)"),
        [],
    ),
    (
        "unique_case_insensitive",
        (
            "CREATE TABLE [test] (\n"
            "  [code] VARCHAR(10),\n"
            "  constraint [uq_lower] unique key ([code])\n"
            ")"
        ),
        [{"name": "uq_lower", "column_names": ["code"]}],
    ),
    (
        "unique_with_extra_whitespace",
        (
            "CREATE TABLE [test] (\n"
            "  [a] INTEGER,\n"
            "  CONSTRAINT   [uq_ws]   UNIQUE   KEY   ([a],   [b])\n"
            ")"
        ),
        [{"name": "uq_ws", "column_names": ["a", "b"]}],
    ),
    (
        "mixed_fk_and_unique",
        (
            "CREATE TABLE [enrollments] (\n"
            "  [id] INTEGER AUTO_INCREMENT NOT NULL,\n"
            "  [student_id] INTEGER NOT NULL,\n"
            "  [course_id] INTEGER NOT NULL,\n"
            "  CONSTRAINT [pk_enroll] PRIMARY KEY ([id]),\n"
            "  CONSTRAINT [uq_enroll_pair] UNIQUE KEY ([student_id], [course_id]),\n"
            "  CONSTRAINT [fk_enroll_student] FOREIGN KEY ([student_id]) "
            "REFERENCES [students] ([id])\n"
            ")"
        ),
        [{"name": "uq_enroll_pair", "column_names": ["student_id", "course_id"]}],
    ),
    (
        "three_column_unique",
        (
            "CREATE TABLE [audit] (\n"
            "  [year] INTEGER, [month] INTEGER, [day] INTEGER,\n"
            "  CONSTRAINT [uq_date] UNIQUE KEY ([year], [month], [day])\n"
            ")"
        ),
        [{"name": "uq_date", "column_names": ["year", "month", "day"]}],
    ),
    (
        "unique_with_descending_key_order",
        (
            "CREATE TABLE [events] (\n"
            "  [created_at] DATETIME,\n"
            "  [tenant_id] INTEGER,\n"
            "  CONSTRAINT [uq_events_created] UNIQUE KEY ([created_at] DESC, [tenant_id])\n"
            ")"
        ),
        [{"name": "uq_events_created", "column_names": ["created_at", "tenant_id"]}],
    ),
    (
        "unique_with_multiline_whitespace",
        (
            "CREATE TABLE [test] (\n"
            "  [a] INTEGER,\n"
            "  [b] INTEGER,\n"
            "  CONSTRAINT\n"
            "    [uq_multiline]\n"
            "    UNIQUE\n"
            "    KEY\n"
            "    ([a],\n"
            "     [b])\n"
            ")"
        ),
        [{"name": "uq_multiline", "column_names": ["a", "b"]}],
    ),
    # Names containing ( ) , and spaces (#532), as printed by CUBRID 11.4.
    (
        "unique_bracketed_names_with_parens_commas_spaces",
        (
            "CREATE TABLE [p532] ([(3)] INTEGER NOT NULL, [a, b] INTEGER NOT NULL, "
            "[x ) y] INTEGER, [per % cent] INTEGER,  "
            "CONSTRAINT [pk_p532_(3)_a, b] PRIMARY KEY  ([(3)], [a, b]),  "
            "CONSTRAINT [uq (w), z] UNIQUE KEY  ([x ) y], [per % cent])"
            ") REUSE_OID, COLLATE iso88591_bin"
        ),
        [{"name": "uq (w), z", "column_names": ["x ) y", "per % cent"]}],
    ),
    (
        "unique_whitespace_inside_parentheses",
        "CONSTRAINT [uq_ws] UNIQUE KEY ( [a (1)] ,  [b] DESC )",
        [{"name": "uq_ws", "column_names": ["a (1)", "b"]}],
    ),
    (
        "unique_parenthesized_name_with_descending_key_order",
        (
            "CREATE TABLE [d532] ([a] INTEGER, [b (x)] CHARACTER VARYING(20),  "
            "CONSTRAINT [u1] UNIQUE KEY  ([a] DESC, [b (x)]),  "
            "CONSTRAINT [u3] UNIQUE KEY  ([b (x)] DESC, [a])) REUSE_OID, COLLATE iso88591_bin"
        ),
        [
            {"name": "u1", "column_names": ["a", "b (x)"]},
            {"name": "u3", "column_names": ["b (x)", "a"]},
        ],
    ),
]


# ---------------------------------------------------------------------------
# Malformed / edge-case DDL that should NOT crash
# ---------------------------------------------------------------------------

MALFORMED_FIXTURES: list[tuple[str, str]] = [
    ("empty_string", ""),
    ("no_create_table", "SELECT 1"),
    ("truncated_constraint", "CREATE TABLE [t] (\n  CONSTRAINT [fk_broken] FOREIGN KEY"),
    (
        "unmatched_brackets",
        "CREATE TABLE [t] (\n  CONSTRAINT [fk FOREIGN KEY ([a) REFERENCES [b] ([c)",
    ),
    ("no_parens", "CREATE TABLE [t] (\n  CONSTRAINT [fk_no_parens] FOREIGN KEY REFERENCES [other]"),
    (
        "partial_unique",
        "CREATE TABLE [t] (\n  CONSTRAINT [uq_partial] UNIQUE KEY",
    ),
    ("just_columns", "  [id] INTEGER NOT NULL,\n  [name] VARCHAR(100)"),
]


# ===================================================================
# Tests
# ===================================================================


class TestForeignKeyParsing:
    """Golden tests for _RE_FOREIGN_KEY regex parsing."""

    @pytest.mark.parametrize(
        "ddl, expected",
        [(ddl, exp) for _, ddl, exp in FK_FIXTURES],
        ids=[fid for fid, _, _ in FK_FIXTURES],
    )
    def test_parse_foreign_keys(self, ddl: str, expected: list[dict[str, Any]]) -> None:
        result = parse_foreign_keys(ddl)
        assert result == expected

    def test_fk_regex_does_not_match_unique(self) -> None:
        """Ensure FK regex doesn't accidentally match UNIQUE KEY constraints."""
        ddl = "CONSTRAINT [uq_test] UNIQUE KEY ([col1])"
        assert list(_RE_FOREIGN_KEY.finditer(ddl)) == []

    def test_fk_regex_does_not_match_pk(self) -> None:
        """Ensure FK regex doesn't accidentally match PRIMARY KEY constraints."""
        ddl = "CONSTRAINT [pk_test] PRIMARY KEY ([id])"
        assert list(_RE_FOREIGN_KEY.finditer(ddl)) == []


class TestUniqueConstraintParsing:
    """Golden tests for _RE_UNIQUE_KEY regex parsing."""

    @pytest.mark.parametrize(
        "ddl, expected",
        [(ddl, exp) for _, ddl, exp in UNIQUE_FIXTURES],
        ids=[fid for fid, _, _ in UNIQUE_FIXTURES],
    )
    def test_parse_unique_constraints(self, ddl: str, expected: list[dict[str, Any]]) -> None:
        result = parse_unique_constraints(ddl)
        assert result == expected

    def test_unique_regex_does_not_match_fk(self) -> None:
        """Ensure UNIQUE regex doesn't match FK constraints."""
        ddl = "CONSTRAINT [fk_test] FOREIGN KEY ([col1]) REFERENCES [other] ([id])"
        assert list(_RE_UNIQUE_KEY.finditer(ddl)) == []

    def test_unique_regex_does_not_match_pk(self) -> None:
        """Ensure UNIQUE regex doesn't match PRIMARY KEY constraints."""
        ddl = "CONSTRAINT [pk_test] PRIMARY KEY ([id])"
        assert list(_RE_UNIQUE_KEY.finditer(ddl)) == []


class TestMalformedDDL:
    """Ensure malformed DDL doesn't crash the regex parsing."""

    @pytest.mark.parametrize(
        "ddl",
        [ddl for _, ddl in MALFORMED_FIXTURES],
        ids=[mid for mid, _ in MALFORMED_FIXTURES],
    )
    def test_fk_parsing_no_crash(self, ddl: str) -> None:
        result = parse_foreign_keys(ddl)
        assert isinstance(result, list)

    @pytest.mark.parametrize(
        "ddl",
        [ddl for _, ddl in MALFORMED_FIXTURES],
        ids=[mid for mid, _ in MALFORMED_FIXTURES],
    )
    def test_unique_parsing_no_crash(self, ddl: str) -> None:
        result = parse_unique_constraints(ddl)
        assert isinstance(result, list)


class TestBracketIdentRegex:
    """Tests for _RE_BRACKET_IDENT helper regex."""

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("[col1]", ["col1"]),
            ("[col1], [col2]", ["col1", "col2"]),
            ("[col1], [col2], [col3]", ["col1", "col2", "col3"]),
            ("no brackets here", []),
            ("", []),
            ("[dba.users]", ["dba.users"]),
            ("[col with spaces]", ["col with spaces"]),
        ],
        ids=[
            "single",
            "two_columns",
            "three_columns",
            "no_brackets",
            "empty",
            "dotted_name",
            "spaces_in_name",
        ],
    )
    def test_bracket_ident(self, text: str, expected: list[str]) -> None:
        assert _RE_BRACKET_IDENT.findall(text) == expected
