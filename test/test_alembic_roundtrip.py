from __future__ import annotations

from unittest import mock

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from sqlalchemy_cubrid.dialect import CubridDialect
from sqlalchemy_cubrid.types import VARCHAR

# Older alembic shipped ``autogenerate.compare`` as a package with a ``schema``
# submodule that binds ``inspect``; alembic >=1.9 ships ``compare`` as a single
# module that binds ``inspect`` at module level. Importing the ``compare``
# package does not necessarily import the ``schema`` submodule, so probe for it
# explicitly (``hasattr`` can mis-detect) and resolve the correct mock.patch
# target for whichever layout is installed so the tests do not raise
# ModuleNotFoundError on newer alembic (#323).
try:
    import alembic.autogenerate.compare.schema  # noqa: F401

    _COMPARE_INSPECT_TARGET = "alembic.autogenerate.compare.schema.inspect"
except ImportError:
    _COMPARE_INSPECT_TARGET = "alembic.autogenerate.compare.inspect"


class _MockInspector:
    def __init__(self, bind, tables):
        self.bind = bind
        self.dialect = bind.dialect
        self.info_cache = {}
        self._tables = tables

    def _table(self, table_name):
        return self._tables[table_name]

    def get_table_names(self, schema=None):
        return list(self._tables)

    def get_columns(self, table_name, schema=None, **kw):
        return self._table(table_name)["columns"]

    def get_pk_constraint(self, table_name, schema=None, **kw):
        return self._table(table_name).get(
            "pk_constraint", {"name": None, "constrained_columns": []}
        )

    def get_foreign_keys(self, table_name, schema=None, **kw):
        return self._table(table_name).get("foreign_keys", [])

    def get_indexes(self, table_name, schema=None, **kw):
        return self._table(table_name).get("indexes", [])

    def get_unique_constraints(self, table_name, schema=None, **kw):
        return self._table(table_name).get("unique_constraints", [])

    def get_table_comment(self, table_name, schema=None, **kw):
        return self._table(table_name).get("table_comment", {"text": None})

    def get_check_constraints(self, table_name, schema=None, **kw):
        return []

    def get_table_options(self, table_name, schema=None, **kw):
        return {}

    def _get_multi(self, method_name, schema=None, filter_names=None):
        names = filter_names or list(self._tables)
        method = getattr(self, method_name)
        return {(schema, name): method(name, schema=schema) for name in names}

    def get_multi_columns(self, schema=None, filter_names=None, **kw):
        return self._get_multi("get_columns", schema=schema, filter_names=filter_names)

    def get_multi_pk_constraint(self, schema=None, filter_names=None, **kw):
        return self._get_multi("get_pk_constraint", schema=schema, filter_names=filter_names)

    def get_multi_foreign_keys(self, schema=None, filter_names=None, **kw):
        return self._get_multi("get_foreign_keys", schema=schema, filter_names=filter_names)

    def get_multi_indexes(self, schema=None, filter_names=None, **kw):
        return self._get_multi("get_indexes", schema=schema, filter_names=filter_names)

    def get_multi_unique_constraints(self, schema=None, filter_names=None, **kw):
        return self._get_multi("get_unique_constraints", schema=schema, filter_names=filter_names)

    def get_multi_table_comment(self, schema=None, filter_names=None, **kw):
        return self._get_multi("get_table_comment", schema=schema, filter_names=filter_names)

    def get_multi_check_constraints(self, schema=None, filter_names=None, **kw):
        return {(schema, name): [] for name in (filter_names or list(self._tables))}

    def get_multi_table_options(self, schema=None, filter_names=None, **kw):
        return {(schema, name): {} for name in (filter_names or list(self._tables))}

    def reflect_table(self, table, include_columns=None, resolve_fks=False, _reflect_info=None):
        table_data = self._table(table.name)

        for column in table_data["columns"]:
            table.append_column(
                sa.Column(
                    column["name"],
                    column["type"],
                    nullable=column.get("nullable", True),
                    comment=column.get("comment"),
                )
            )

        pk_constraint = table_data.get("pk_constraint")
        if pk_constraint and pk_constraint.get("constrained_columns"):
            table.append_constraint(
                sa.PrimaryKeyConstraint(
                    *[table.c[name] for name in pk_constraint["constrained_columns"]],
                    name=pk_constraint.get("name"),
                )
            )

        for unique_constraint in table_data.get("unique_constraints", []):
            table.append_constraint(
                sa.UniqueConstraint(
                    *[table.c[name] for name in unique_constraint["column_names"]],
                    name=unique_constraint.get("name"),
                )
            )

        for foreign_key in table_data.get("foreign_keys", []):
            referred_schema = foreign_key.get("referred_schema")
            referred_table = foreign_key["referred_table"]
            table_name = (
                f"{referred_schema}.{referred_table}" if referred_schema else referred_table
            )
            table.append_constraint(
                sa.ForeignKeyConstraint(
                    [table.c[name] for name in foreign_key["constrained_columns"]],
                    [f"{table_name}.{name}" for name in foreign_key["referred_columns"]],
                    name=foreign_key.get("name"),
                )
            )

        table.comment = table_data.get("table_comment", {}).get("text")


def _make_connection():
    connection = mock.Mock()
    dialect = CubridDialect()
    dialect.supports_comments = True
    connection.dialect = dialect
    connection.engine = mock.Mock()
    return connection


def test_create_reflect_compare_roundtrip_no_diffs() -> None:
    metadata = sa.MetaData()

    sa.Table(
        "accounts",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("email", VARCHAR(200), nullable=False),
        sa.Column("display_name", VARCHAR(100), nullable=True),
        sa.UniqueConstraint("email", name="uq_accounts_email"),
        comment="account records",
    )

    sa.Table(
        "projects",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("account_id", sa.Integer, sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("slug", VARCHAR(60), nullable=False),
        sa.Index("ix_projects_slug", "slug"),
    )

    reflected_schema = {
        "accounts": {
            "columns": [
                {"name": "id", "type": sa.Integer(), "nullable": False, "autoincrement": True},
                {"name": "email", "type": VARCHAR(200), "nullable": False},
                {"name": "display_name", "type": VARCHAR(100), "nullable": True},
            ],
            "pk_constraint": {"name": None, "constrained_columns": ["id"]},
            "unique_constraints": [{"name": "uq_accounts_email", "column_names": ["email"]}],
            "table_comment": {"text": "account records"},
        },
        "projects": {
            "columns": [
                {"name": "id", "type": sa.Integer(), "nullable": False},
                {"name": "account_id", "type": sa.Integer(), "nullable": False},
                {"name": "slug", "type": VARCHAR(60), "nullable": False},
            ],
            "pk_constraint": {"name": None, "constrained_columns": ["id"]},
            "foreign_keys": [
                {
                    "name": "fk_projects_account_id_accounts",
                    "constrained_columns": ["account_id"],
                    "referred_schema": None,
                    "referred_table": "accounts",
                    "referred_columns": ["id"],
                    "options": {},
                }
            ],
            "indexes": [{"name": "ix_projects_slug", "column_names": ["slug"], "unique": False}],
        },
    }

    connection = _make_connection()
    inspector = _MockInspector(connection, reflected_schema)

    with (
        mock.patch("alembic.autogenerate.api.inspect", return_value=inspector),
        mock.patch(_COMPARE_INSPECT_TARGET, return_value=inspector),
    ):
        context = MigrationContext.configure(connection=connection, opts={"compare_type": True})
        assert compare_metadata(context, metadata) == []
        assert compare_metadata(context, metadata) == []


def test_roundtrip_composite_pk_multi_fk_defaults_no_diffs() -> None:
    """Complex schema: composite PK, multiple FKs, multi-col unique, defaults."""
    metadata = sa.MetaData()

    sa.Table(
        "departments",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", VARCHAR(100), nullable=False),
    )

    sa.Table(
        "employees",
        metadata,
        sa.Column("dept_id", sa.Integer, nullable=False),
        sa.Column("emp_id", sa.Integer, nullable=False),
        sa.Column("name", VARCHAR(200), nullable=False),
        sa.Column("manager_dept_id", sa.Integer, nullable=True),
        sa.Column("manager_emp_id", sa.Integer, nullable=True),
        sa.Column("salary", sa.Numeric(12, 2), server_default="0.00"),
        sa.PrimaryKeyConstraint("dept_id", "emp_id"),
        sa.ForeignKeyConstraint(["dept_id"], ["departments.id"], name="fk_emp_dept"),
        sa.ForeignKeyConstraint(
            ["manager_dept_id", "manager_emp_id"],
            ["employees.dept_id", "employees.emp_id"],
            name="fk_emp_manager",
        ),
        sa.UniqueConstraint("dept_id", "name", name="uq_emp_dept_name"),
    )

    reflected_schema = {
        "departments": {
            "columns": [
                {"name": "id", "type": sa.Integer(), "nullable": False},
                {"name": "name", "type": VARCHAR(100), "nullable": False},
            ],
            "pk_constraint": {"name": None, "constrained_columns": ["id"]},
        },
        "employees": {
            "columns": [
                {"name": "dept_id", "type": sa.Integer(), "nullable": False},
                {"name": "emp_id", "type": sa.Integer(), "nullable": False},
                {"name": "name", "type": VARCHAR(200), "nullable": False},
                {"name": "manager_dept_id", "type": sa.Integer(), "nullable": True},
                {"name": "manager_emp_id", "type": sa.Integer(), "nullable": True},
                {
                    "name": "salary",
                    "type": sa.Numeric(12, 2),
                    "nullable": True,
                    "default": "0.00",
                },
            ],
            "pk_constraint": {
                "name": None,
                "constrained_columns": ["dept_id", "emp_id"],
            },
            "foreign_keys": [
                {
                    "name": "fk_emp_dept",
                    "constrained_columns": ["dept_id"],
                    "referred_schema": None,
                    "referred_table": "departments",
                    "referred_columns": ["id"],
                    "options": {},
                },
                {
                    "name": "fk_emp_manager",
                    "constrained_columns": ["manager_dept_id", "manager_emp_id"],
                    "referred_schema": None,
                    "referred_table": "employees",
                    "referred_columns": ["dept_id", "emp_id"],
                    "options": {},
                },
            ],
            "unique_constraints": [
                {"name": "uq_emp_dept_name", "column_names": ["dept_id", "name"]},
            ],
        },
    }

    connection = _make_connection()
    inspector = _MockInspector(connection, reflected_schema)

    with (
        mock.patch("alembic.autogenerate.api.inspect", return_value=inspector),
        mock.patch(_COMPARE_INSPECT_TARGET, return_value=inspector),
    ):
        context = MigrationContext.configure(connection=connection, opts={"compare_type": True})
        diffs = compare_metadata(context, metadata)
        assert diffs == [], f"Unexpected diffs: {diffs}"


def _fk_action_diffs(
    model_ondelete: str | None,
    model_onupdate: str | None,
    reflected_options: dict[str, str],
) -> list:
    """Compare a one-FK model against a reflected FK carrying *reflected_options*."""
    metadata = sa.MetaData()
    sa.Table("parent", metadata, sa.Column("id", sa.Integer, primary_key=True))
    sa.Table(
        "child",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "pid",
            sa.Integer,
            sa.ForeignKey(
                "parent.id",
                name="fk_child_pid",
                ondelete=model_ondelete,
                onupdate=model_onupdate,
            ),
        ),
    )
    reflected_schema = {
        "parent": {
            "columns": [{"name": "id", "type": sa.Integer(), "nullable": False}],
            "pk_constraint": {"name": None, "constrained_columns": ["id"]},
        },
        "child": {
            "columns": [
                {"name": "id", "type": sa.Integer(), "nullable": False},
                {"name": "pid", "type": sa.Integer(), "nullable": True},
            ],
            "pk_constraint": {"name": None, "constrained_columns": ["id"]},
            "foreign_keys": [
                {
                    "name": "fk_child_pid",
                    "constrained_columns": ["pid"],
                    "referred_schema": None,
                    "referred_table": "parent",
                    "referred_columns": ["id"],
                    "options": reflected_options,
                }
            ],
        },
    }
    connection = _make_connection()
    inspector = _MockInspector(connection, reflected_schema)
    with (
        mock.patch("alembic.autogenerate.api.inspect", return_value=inspector),
        mock.patch(_COMPARE_INSPECT_TARGET, return_value=inspector),
    ):
        context = MigrationContext.configure(connection=connection)
        return compare_metadata(context, metadata)


# What ``get_foreign_keys`` returns for an FK created without ON DELETE /
# ON UPDATE: CUBRID's SHOW CREATE TABLE always prints its default, RESTRICT.
_CUBRID_DEFAULT_ACTIONS = {"ondelete": "RESTRICT", "onupdate": "RESTRICT"}


@pytest.mark.parametrize(
    ("model_ondelete", "model_onupdate"),
    [
        (None, None),
        ("RESTRICT", "RESTRICT"),
        ("restrict", "restrict"),
        ("RESTRICT", None),
        (None, "RESTRICT"),
    ],
)
def test_fk_default_restrict_is_not_a_diff(model_ondelete, model_onupdate) -> None:
    """#597: an FK without actions reflects as RESTRICT; that is not a change."""
    assert _fk_action_diffs(model_ondelete, model_onupdate, _CUBRID_DEFAULT_ACTIONS) == []


@pytest.mark.parametrize(
    ("model_ondelete", "model_onupdate", "reflected_options"),
    [
        # Adding an action to an FK that has the default.
        ("CASCADE", None, _CUBRID_DEFAULT_ACTIONS),
        (None, "SET NULL", _CUBRID_DEFAULT_ACTIONS),
        ("SET NULL", None, _CUBRID_DEFAULT_ACTIONS),
        # Removing an action: the model goes back to the default.
        (None, None, {"ondelete": "CASCADE", "onupdate": "RESTRICT"}),
        (None, None, {"ondelete": "RESTRICT", "onupdate": "SET NULL"}),
        (None, None, {"ondelete": "SET NULL", "onupdate": "RESTRICT"}),
        # Changing one non-default action to another.
        ("CASCADE", None, {"ondelete": "SET NULL", "onupdate": "RESTRICT"}),
    ],
)
def test_fk_action_change_is_still_detected(
    model_ondelete, model_onupdate, reflected_options
) -> None:
    diffs = _fk_action_diffs(model_ondelete, model_onupdate, reflected_options)
    assert [diff[0] for diff in diffs] == ["remove_fk", "add_fk"]


def test_correct_for_autogen_foreignkeys_only_clears_default_restrict() -> None:
    """The reflected RESTRICT is cleared only where the model has no action."""
    from sqlalchemy_cubrid.alembic_impl import CubridImpl

    def _fk(metadata, ondelete, onupdate):
        sa.Table("parent", metadata, sa.Column("id", sa.Integer, primary_key=True))
        child = sa.Table(
            "child",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("pid", sa.Integer),
            sa.Column("other", sa.Integer),
        )
        fk = sa.ForeignKeyConstraint(
            ["pid"], ["parent.id"], name="fk_child_pid", ondelete=ondelete, onupdate=onupdate
        )
        unmatched = sa.ForeignKeyConstraint(["other"], ["parent.id"], ondelete="RESTRICT")
        child.append_constraint(fk)
        child.append_constraint(unmatched)
        return fk, unmatched

    conn_fk, conn_unmatched = _fk(sa.MetaData(), "RESTRICT", "Restrict")
    metadata_fk, _ = _fk(sa.MetaData(), None, "SET NULL")

    impl = CubridImpl(CubridDialect(), None, False, False, None, {})
    impl.correct_for_autogen_foreignkeys({conn_fk, conn_unmatched}, {metadata_fk})

    assert conn_fk.ondelete is None  # model has no ON DELETE: RESTRICT is the default
    assert conn_fk.onupdate == "Restrict"  # model has SET NULL: a real difference
    assert conn_unmatched.ondelete == "RESTRICT"  # no model FK to compare against


def _child_fks(metadata, *fks):
    """Attach *fks* to a ``child(pid)`` table referencing ``parent(id)``."""
    sa.Table("parent", metadata, sa.Column("id", sa.Integer, primary_key=True))
    child = sa.Table(
        "child",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("pid", sa.Integer),
    )
    for fk in fks:
        child.append_constraint(fk)
    return fks


def test_correct_for_autogen_foreignkeys_same_columns_needs_every_candidate_default() -> None:
    """Two unnamed model FKs on the same columns: RESTRICT is cleared only if
    neither names an action, whatever order the sets iterate in."""
    from sqlalchemy_cubrid.alembic_impl import CubridImpl

    impl = CubridImpl(CubridDialect(), None, False, False, None, {})
    for _ in range(20):
        (conn_fk,) = _child_fks(
            sa.MetaData(),
            sa.ForeignKeyConstraint(["pid"], ["parent.id"], ondelete="RESTRICT"),
        )
        plain, cascade = _child_fks(
            sa.MetaData(),
            sa.ForeignKeyConstraint(["pid"], ["parent.id"]),
            sa.ForeignKeyConstraint(["pid"], ["parent.id"], ondelete="CASCADE"),
        )
        impl.correct_for_autogen_foreignkeys({conn_fk}, {plain, cascade})
        assert conn_fk.ondelete == "RESTRICT"


def test_correct_for_autogen_foreignkeys_matches_by_name_first() -> None:
    """A named reflected FK is compared with the model FK of the same name."""
    from sqlalchemy_cubrid.alembic_impl import CubridImpl

    impl = CubridImpl(CubridDialect(), None, False, False, None, {})
    conn_plain, conn_cascade = _child_fks(
        sa.MetaData(),
        sa.ForeignKeyConstraint(["pid"], ["parent.id"], name="fk_plain", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pid"], ["parent.id"], name="fk_cascade", ondelete="RESTRICT"),
    )
    md_plain, md_cascade = _child_fks(
        sa.MetaData(),
        sa.ForeignKeyConstraint(["pid"], ["parent.id"], name="fk_plain"),
        sa.ForeignKeyConstraint(["pid"], ["parent.id"], name="fk_cascade", ondelete="CASCADE"),
    )
    impl.correct_for_autogen_foreignkeys({conn_plain, conn_cascade}, {md_plain, md_cascade})
    assert conn_plain.ondelete is None
    assert conn_cascade.ondelete == "RESTRICT"
