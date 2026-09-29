"""Offline tests for the advisory Alembic safety checker (#447)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from scripts import alembic_safety_check


def _check(tmp_path: Path, source: str) -> list[str]:
    revision = tmp_path / "abc123_rev.py"
    revision.write_text(textwrap.dedent(source), encoding="utf-8")
    return alembic_safety_check.check_revision(revision)


def test_two_constraint_calls_warn(tmp_path: Path) -> None:
    warnings = _check(
        tmp_path,
        """
        from alembic import op

        def upgrade():
            op.create_unique_constraint("uq_a", "items", ["a"])
            op.create_foreign_key("fk_b", "items", "other", ["b"], ["id"])
        """,
    )
    assert warnings == [
        "abc123_rev.py:upgrade() has 2 DDL operations "
        "(schema locks are held until the transaction commits)"
    ]


@pytest.mark.parametrize(
    "call",
    [
        'op.create_unique_constraint("uq_a", "items", ["a"])',
        'op.create_foreign_key("fk_b", "items", "other", ["b"], ["id"])',
        'op.create_check_constraint("ck_a", "items", "a > 0")',
        'op.create_primary_key("pk_items", "items", ["id"])',
    ],
)
def test_each_constraint_operation_is_counted(tmp_path: Path, call: str) -> None:
    warnings = _check(
        tmp_path,
        f"""
        from alembic import op

        def upgrade():
            op.add_column("items", None)
            {call}
        """,
    )
    assert len(warnings) == 1
    assert "upgrade() has 2 DDL operations" in warnings[0]


def test_single_ddl_call_does_not_warn(tmp_path: Path) -> None:
    source = """
        from alembic import op

        def upgrade():
            op.create_unique_constraint("uq_a", "items", ["a"])
        """
    assert _check(tmp_path, source) == []


def test_bare_method_references_do_not_warn(tmp_path: Path) -> None:
    source = """
        from alembic import op

        def upgrade():
            operations = [op.create_table, op.drop_table]
        """
    assert _check(tmp_path, source) == []


def test_batch_op_calls_are_counted(tmp_path: Path) -> None:
    warnings = _check(
        tmp_path,
        """
        from alembic import op

        def upgrade():
            with op.batch_alter_table("items") as batch_op:
                batch_op.add_column(None)
                batch_op.create_index("ix_a", ["a"])
        """,
    )
    assert len(warnings) == 1
    assert "upgrade() has 2 DDL operations" in warnings[0]


def test_upgrade_and_downgrade_are_assessed_separately(tmp_path: Path) -> None:
    source = """
        from alembic import op

        def upgrade():
            op.create_table("items")

        def downgrade():
            op.drop_table("items")
        """
    assert _check(tmp_path, source) == []

    warnings = _check(
        tmp_path,
        """
        from alembic import op

        def upgrade():
            op.create_table("items")

        def downgrade():
            op.drop_constraint("uq_a", "items")
            op.drop_table("items")
        """,
    )
    assert warnings == [
        "abc123_rev.py:downgrade() has 2 DDL operations "
        "(schema locks are held until the transaction commits)"
    ]


def test_other_functions_are_ignored(tmp_path: Path) -> None:
    source = """
        from alembic import op

        def helper():
            op.create_table("a")
            op.create_table("b")

        def upgrade():
            helper()
        """
    assert _check(tmp_path, source) == []


def test_main_reports_warnings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "a_rev.py").write_text(
        textwrap.dedent(
            """
            from alembic import op

            def upgrade():
                op.create_unique_constraint("uq_a", "items", ["a"])
                op.create_foreign_key("fk_b", "items", "other", ["b"], ["id"])
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("sys.argv", ["alembic_safety_check.py", str(tmp_path)])
    alembic_safety_check.main()
    out = capsys.readouterr().out
    assert "a_rev.py:upgrade() has 2 DDL operations" in out
    assert "Total: 1 warning(s)" in out


def test_main_reports_clean_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "a_rev.py").write_text(
        "from alembic import op\n\ndef upgrade():\n    ops = [op.create_table, op.drop_table]\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("sys.argv", ["alembic_safety_check.py", str(tmp_path)])
    alembic_safety_check.main()
    assert "No revision has more than one DDL call per function." in capsys.readouterr().out
