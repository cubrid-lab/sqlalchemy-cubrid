"""Evaluator-owned checks for the alembic-alter-column-sql task (#861).

They render Alembic's offline (``--sql``) output and check the statement shapes
CUBRID accepts, not one implementation's exact text. This is compiled-SQL
evidence only: it says nothing about how a live server applies the statements.
Copied into the candidate's worktree only by ``scripts/agent_eval.py run``.
"""

from __future__ import annotations

import io
import re

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

GENERIC = ("SET NOT NULL", "DROP NOT NULL", "DROP DEFAULT", "COMMENT ON")


def _sql(**kwargs):
    buf = io.StringIO()
    ctx = MigrationContext.configure(
        dialect_name="cubrid", opts={"as_sql": True, "output_buffer": buf}
    )
    Operations(ctx).alter_column("users", "email", **kwargs)
    text = " ".join(buf.getvalue().split())
    for clause in GENERIC:
        assert clause not in text.upper(), text
    return text


def test_not_null_goes_through_modify_or_change():
    text = _sql(nullable=False, existing_type=sa.Integer())
    assert re.search(r"\b(MODIFY|CHANGE)\b", text)
    assert "NOT NULL" in text


def test_nullable_from_not_null_is_stated():
    text = _sql(nullable=True, existing_type=sa.Integer(), existing_nullable=False)
    assert re.search(r"\b(MODIFY|CHANGE)\b", text)
    # The NULL of a DEFAULT NULL clause is not a nullability clause.
    nullability = text.replace("DEFAULT NULL", "")
    assert re.search(r"(?<!NOT )\bNULL\b", nullability) and "NOT NULL" not in text


def test_nullability_change_needs_the_column_type():
    with pytest.raises(ValueError):
        _sql(nullable=False)


def test_dropped_default_is_set_to_null():
    text = _sql(server_default=None, existing_type=sa.Integer())
    assert "DEFAULT NULL" in text


def test_dropped_default_of_a_not_null_column_keeps_it_not_null():
    # SET DEFAULT NULL is rejected for a NOT NULL column: the change must make the
    # column nullable, drop the default, then restore NOT NULL, keeping the comment.
    text = _sql(
        server_default=None,
        existing_type=sa.Integer(),
        existing_nullable=False,
        existing_comment="c",
    )
    statements = [s.strip() for s in text.split(";") if s.strip()]
    assert "SET DEFAULT NULL" not in text
    assert len(statements) >= 2
    first, last = statements[0], statements[-1]
    assert "DEFAULT NULL" in first and "NOT NULL" not in first
    # The first statement must also state NULL itself: from 11.2 MODIFY keeps NOT
    # NULL unless told otherwise, and then rejects DEFAULT NULL.
    assert re.search(r"(?<!NOT )\bNULL\b", first.replace("DEFAULT NULL", "")), first
    assert "NOT NULL" in last and "DEFAULT" not in last
    assert all("COMMENT 'c'" in s for s in statements)


def test_comment_change_and_removal_go_through_modify():
    added = _sql(comment="it's", existing_type=sa.Integer())
    assert "COMMENT 'it''s'" in added
    removed = _sql(comment=None, existing_type=sa.Integer(), existing_comment="old")
    assert "COMMENT ''" in removed
