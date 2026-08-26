# test/test_alembic.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Tests for Alembic migration support (sqlalchemy_cubrid.alembic_impl).

These tests verify that the CubridImpl class is correctly configured and
can be discovered by Alembic via the entry-point mechanism.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any
from unittest import mock

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from sqlalchemy_cubrid import types as cubrid_types
from sqlalchemy_cubrid.dialect import CubridDialect

if sys.version_info >= (3, 11):
    import tomllib as toml_mod
else:
    import tomli as toml_mod


def _load_pyproject():
    """Load pyproject.toml."""
    import pathlib

    pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    with open(pyproject, "rb") as f:
        return toml_mod.load(f)


class _AutogenContext:
    def __init__(self):
        self.imports: set[str] = set()


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


class TestCubridImpl:
    """Tests for the CubridImpl Alembic implementation class."""

    def test_import(self):
        """CubridImpl can be imported from the alembic_impl module."""
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        assert CubridImpl is not None

    def test_dialect_name(self):
        """CubridImpl.__dialect__ is set to 'cubrid'."""
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        assert CubridImpl.__dialect__ == "cubrid"

    def test_transactional_ddl_false(self):
        """CUBRID auto-commits DDL, so transactional_ddl must be False."""
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        assert CubridImpl.transactional_ddl is False

    def test_subclass_of_default_impl(self):
        """CubridImpl inherits from alembic.ddl.impl.DefaultImpl."""
        from alembic.ddl.impl import DefaultImpl

        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        assert issubclass(CubridImpl, DefaultImpl)

    def test_class_registered_in_impl_registry(self):
        """Alembic's DefaultImpl registry should know about 'cubrid'."""
        from alembic.ddl.impl import _impls

        # Import triggers class registration via metaclass
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        # _impls is the internal registry keyed by dialect name
        assert "cubrid" in _impls
        assert _impls["cubrid"] is CubridImpl

    def test_entry_point_registered(self):
        """Verify the entry point is declared in pyproject.toml."""
        config = _load_pyproject()

        entry_points = config["project"]["entry-points"]
        assert "alembic.ddl" in entry_points
        assert entry_points["alembic.ddl"]["cubrid"] == (
            "sqlalchemy_cubrid.alembic_impl:CubridImpl"
        )

    def test_optional_dependency_declared(self):
        """Verify the [alembic] optional dependency is declared in pyproject.toml."""
        config = _load_pyproject()

        optional_deps = config["project"]["optional-dependencies"]
        assert "alembic" in optional_deps
        assert any("alembic" in dep for dep in optional_deps["alembic"])

    @staticmethod
    def _capture_alter_column_sql(**kwargs: Any) -> str:
        """Route ``alter_column`` through CubridImpl and compile the emitted DDL.

        ``_exec`` is patched to capture the DDL construct instead of running it
        against a live connection, then the construct is compiled with the
        CUBRID dialect so we assert on the *actual* SQL CUBRID would receive.
        """
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        captured: list[Any] = []
        with mock.patch.object(
            CubridImpl, "_exec", side_effect=lambda element, *a, **k: captured.append(element)
        ):
            impl.alter_column(**kwargs)
        assert len(captured) == 1
        return str(captured[0].compile(dialect=CubridDialect())).strip()

    def test_alter_column_type_emits_modify(self):
        """A type-only change emits native ``ALTER TABLE ... MODIFY``.

        CUBRID has supported in-place column type changes for years; the old
        NotImplementedError was wrong (see cubrid-lab/sqlalchemy-cubrid#305).
        """
        sql = self._capture_alter_column_sql(
            table_name="users",
            column_name="age",
            type_=sa.BigInteger(),
        )
        assert sql == "ALTER TABLE users MODIFY age BIGINT"

    def test_alter_column_type_reconstructs_existing_attributes(self):
        """MODIFY restates the whole column, so existing_* metadata is preserved."""
        sql = self._capture_alter_column_sql(
            table_name="users",
            column_name="age",
            type_=sa.BigInteger(),
            existing_nullable=False,
            existing_server_default="0",
        )
        assert sql == "ALTER TABLE users MODIFY age BIGINT NOT NULL DEFAULT '0'"

    def test_alter_column_rename_emits_rename_column(self):
        """A rename-only change emits native ``ALTER TABLE ... RENAME COLUMN``."""
        sql = self._capture_alter_column_sql(
            table_name="users",
            column_name="old_name",
            name="new_name",
        )
        assert sql == "ALTER TABLE users RENAME COLUMN old_name TO new_name"

    def test_alter_column_rename_and_type_emits_change(self):
        """A combined rename + type change emits native ``ALTER TABLE ... CHANGE``."""
        sql = self._capture_alter_column_sql(
            table_name="users",
            column_name="age",
            name="years",
            type_=sa.BigInteger(),
            existing_nullable=True,
        )
        assert sql == "ALTER TABLE users CHANGE age years BIGINT"

    def test_modify_column_requires_type(self):
        """The DDL element guards against a missing column type."""
        from sqlalchemy_cubrid.alembic_impl import CubridModifyColumn

        with pytest.raises(ValueError, match="requires the column type"):
            CubridModifyColumn("users", "age", type_=None)

    def test_alter_column_nullable_delegates(self):
        from alembic.ddl.impl import DefaultImpl

        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)

        with mock.patch.object(DefaultImpl, "alter_column", return_value=None) as mocked:
            impl.alter_column("users", "email", nullable=False)

        mocked.assert_called_once_with(
            "users",
            "email",
            nullable=False,
            server_default=False,
            name=None,
            type_=None,
        )


class TestAlembicImportError:
    """Test that a clear error is raised when alembic is not installed."""

    def test_import_error_without_alembic(self):
        """If alembic is not installed, importing alembic_impl raises ImportError."""
        # Remove alembic_impl from cache so we can re-import it
        module_key = "sqlalchemy_cubrid.alembic_impl"
        saved = sys.modules.pop(module_key, None)

        try:
            with mock.patch.dict(
                sys.modules,
                {"alembic": None, "alembic.ddl": None, "alembic.ddl.impl": None},
            ):
                # Force re-import
                if module_key in sys.modules:
                    del sys.modules[module_key]
                with pytest.raises(ImportError, match="Alembic is required"):
                    importlib.import_module(module_key)
        finally:
            # Restore
            if saved is not None:
                sys.modules[module_key] = saved
            elif module_key in sys.modules:
                del sys.modules[module_key]


class TestCubridImplAutogenerate:
    def test_render_type_set_multiset_sequence_with_strings(self):
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        autogen_context = _AutogenContext()

        set_render = impl.render_type(cubrid_types.SET("A", "b"), autogen_context)
        multiset_render = impl.render_type(cubrid_types.MULTISET("x", "y"), autogen_context)
        sequence_render = impl.render_type(cubrid_types.SEQUENCE("f", "s"), autogen_context)

        assert set_render == "cubrid_types.SET('A', 'b')"
        assert multiset_render == "cubrid_types.MULTISET('x', 'y')"
        assert sequence_render == "cubrid_types.SEQUENCE('f', 's')"
        assert autogen_context.imports == {
            "from sqlalchemy_cubrid import types as cubrid_types",
        }

    def test_render_type_collection_with_typeengine_values(self):
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        autogen_context = _AutogenContext()

        rendered = impl.render_type(cubrid_types.SET(sa.String(), sa.Integer()), autogen_context)

        assert rendered == "cubrid_types.SET(sa.String(), sa.Integer())"
        assert "from sqlalchemy_cubrid import types as cubrid_types" in autogen_context.imports
        assert "import sqlalchemy as sa" in autogen_context.imports

    def test_render_type_collection_preserves_type_args(self):
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        autogen_context = _AutogenContext()

        rendered = impl.render_type(
            cubrid_types.SET(sa.String(50), sa.Numeric(10, 2)), autogen_context
        )

        assert (
            rendered == "cubrid_types.SET(sa.String(length=50), sa.Numeric(precision=10, scale=2))"
        )
        assert "import sqlalchemy as sa" in autogen_context.imports

    def test_render_type_non_cubrid_type_returns_false(self):
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        autogen_context = _AutogenContext()

        assert impl.render_type(sa.String(), autogen_context) is False
        assert autogen_context.imports == set()

    def test_compare_type_set_same_values_different_order(self):
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        inspector_column = sa.Column("v", cubrid_types.SET(" A ", "B"))
        metadata_column = sa.Column("v", cubrid_types.SET("b", "a"))

        assert impl.compare_type(inspector_column, metadata_column) is False

    def test_compare_type_set_different_values(self):
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        inspector_column = sa.Column("v", cubrid_types.SET("a", "b"))
        metadata_column = sa.Column("v", cubrid_types.SET("a", "c"))

        assert impl.compare_type(inspector_column, metadata_column) is True

    def test_compare_type_sequence_order_matters(self):
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        inspector_column = sa.Column("v", cubrid_types.SEQUENCE("a", "b"))
        metadata_column = sa.Column("v", cubrid_types.SEQUENCE("b", "a"))

        assert impl.compare_type(inspector_column, metadata_column) is True

    def test_compare_type_delegates_to_super_for_non_collection(self):
        from alembic.ddl.impl import DefaultImpl

        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        inspector_column = sa.Column("v", sa.String())
        metadata_column = sa.Column("v", sa.String())

        with mock.patch.object(DefaultImpl, "compare_type", return_value=True) as mock_super:
            result = impl.compare_type(inspector_column, metadata_column)

        assert result is True
        mock_super.assert_called_once_with(inspector_column, metadata_column)

    def test_normalize_collection_value_typeengine(self):
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        result = CubridImpl._normalize_collection_value(sa.String())
        assert result == "string()"

    def test_normalize_collection_value_non_string_non_type(self):
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        result = CubridImpl._normalize_collection_value(42)
        assert result == "42"

    def test_render_type_cubrid_non_collection_returns_false(self):
        """CUBRID types that are NOT collections (e.g., MONETARY) return False."""
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        autogen_context = _AutogenContext()

        assert impl.render_type(cubrid_types.MONETARY(), autogen_context) is False
        assert autogen_context.imports == set()

    def test_render_type_collection_with_non_string_non_type_values(self):
        """Values that are neither str nor TypeEngine use repr()."""
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        autogen_context = _AutogenContext()

        rendered = impl.render_type(cubrid_types.SET(42, 3.14), autogen_context)
        assert rendered == "cubrid_types.SET(42, 3.14)"

    def test_compare_type_collection_vs_non_collection(self):
        """When one type is collection and the other is not, they differ."""
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        inspector_column = sa.Column("v", cubrid_types.SET("a"))
        metadata_column = sa.Column("v", sa.String())

        assert impl.compare_type(inspector_column, metadata_column) is True

    def test_compare_type_different_collection_names(self):
        """SET vs MULTISET with same values should still differ."""
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        inspector_column = sa.Column("v", cubrid_types.SET("a", "b"))
        metadata_column = sa.Column("v", cubrid_types.MULTISET("a", "b"))

        assert impl.compare_type(inspector_column, metadata_column) is True

    def test_compare_type_text_vs_varchar_max_no_diff(self):
        """Text() vs VARCHAR(1073741823) must NOT be reported as a type change.

        See cubrid-lab/sqlalchemy-cubrid#120 — CUBRID stores Text/CLOB/STRING
        as VARCHAR(1073741823) so reflection round-trips trip Alembic's
        default compare_type.
        """
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        inspector_column = sa.Column("v", cubrid_types.VARCHAR(1073741823))
        for metadata_type in (sa.Text(), cubrid_types.CLOB(), cubrid_types.STRING()):
            metadata_column = sa.Column("v", metadata_type)
            assert impl.compare_type(inspector_column, metadata_column) is False
            # Reverse direction must also hold.
            assert impl.compare_type(metadata_column, inspector_column) is False

    def test_compare_type_varchar_max_vs_string_no_length_no_diff(self):
        """Plain String() (no length) maps to VARCHAR(max) on CUBRID."""
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        inspector_column = sa.Column("v", cubrid_types.VARCHAR(1073741823))
        metadata_column = sa.Column("v", sa.String())
        assert impl.compare_type(inspector_column, metadata_column) is False

    def test_compare_type_varchar_bounded_still_compared(self):
        """VARCHAR(100) vs Text() must still be detected as a real diff."""
        from alembic.ddl.impl import DefaultImpl

        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        inspector_column = sa.Column("v", cubrid_types.VARCHAR(100))
        metadata_column = sa.Column("v", sa.Text())
        with mock.patch.object(DefaultImpl, "compare_type", return_value=True) as m:
            result = impl.compare_type(inspector_column, metadata_column)
        assert result is True
        m.assert_called_once()


class TestAutogenerateRegression:
    @staticmethod
    def _make_connection():
        connection = mock.Mock()
        dialect = CubridDialect()
        dialect.supports_comments = True
        connection.dialect = dialect
        connection.engine = mock.Mock()
        connection.execute.return_value = []
        return connection

    def _compare_metadata(
        self,
        metadata,
        reflected_schema,
        *,
        compare_type: bool | Any = True,
    ):
        import sqlalchemy_cubrid.alembic_impl  # noqa: F401

        connection = self._make_connection()
        inspector = _MockInspector(connection, reflected_schema)

        with (
            mock.patch("alembic.autogenerate.api.inspect", return_value=inspector),
            mock.patch("alembic.autogenerate.compare.schema.inspect", return_value=inspector),
        ):
            context = MigrationContext.configure(
                connection=connection,
                opts={"compare_type": compare_type},
            )
            return compare_metadata(context, metadata)

    def _assert_empty_diff_twice(
        self,
        metadata,
        reflected_schema,
        *,
        compare_type: bool | Any = True,
    ):
        assert self._compare_metadata(metadata, reflected_schema, compare_type=compare_type) == []
        assert self._compare_metadata(metadata, reflected_schema, compare_type=compare_type) == []

    @staticmethod
    def _compare_type_with_collection_alias(
        migration_context,
        inspector_column,
        metadata_column,
        inspector_type,
        metadata_type,
    ):
        if (
            isinstance(inspector_type, cubrid_types.SET)
            and isinstance(metadata_type, cubrid_types.SET)
            and len(getattr(inspector_type, "_ddl_values", ())) == 1
            and isinstance(inspector_type._ddl_values[0], sa.types.TypeEngine)
            and all(isinstance(value, str) for value in getattr(metadata_type, "_ddl_values", ()))
        ):
            return False

        return migration_context.impl.compare_type(inspector_column, metadata_column)

    def test_compare_metadata_no_diffs_for_representative_schema(self):
        metadata = sa.MetaData()

        sa.Table(
            "accounts",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("name", cubrid_types.VARCHAR(255), nullable=False),
            sa.Column("age", sa.Integer),
        )
        sa.Table(
            "tag_sets",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("tags", cubrid_types.SET(cubrid_types.VARCHAR(100))),
            sa.Column("scores", cubrid_types.MULTISET(sa.Integer())),
            sa.Column("aliases", cubrid_types.SEQUENCE(cubrid_types.VARCHAR(50))),
        )
        sa.Table(
            "profiles",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("account_id", sa.Integer, sa.ForeignKey("accounts.id"), nullable=False),
        )
        sa.Table(
            "email_registry",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("email", cubrid_types.VARCHAR(255), nullable=False),
            sa.UniqueConstraint("email", name="uq_email_registry_email"),
        )
        sa.Table(
            "documented",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True, comment="Primary key"),
            sa.Column("label", cubrid_types.VARCHAR(100), comment="Display label"),
            comment="Representative comments",
        )
        sa.Table(
            "json_docs",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("payload", cubrid_types.JSON()),
        )

        reflected_schema = {
            "accounts": {
                "columns": [
                    {"name": "id", "type": sa.Integer(), "nullable": False, "autoincrement": True},
                    {"name": "name", "type": cubrid_types.VARCHAR(255), "nullable": False},
                    {"name": "age", "type": sa.Integer(), "nullable": True},
                ],
                "pk_constraint": {"name": None, "constrained_columns": ["id"]},
            },
            "tag_sets": {
                "columns": [
                    {"name": "id", "type": sa.Integer(), "nullable": False},
                    {"name": "tags", "type": cubrid_types.SET(cubrid_types.VARCHAR(100))},
                    {"name": "scores", "type": cubrid_types.MULTISET(sa.Integer())},
                    {"name": "aliases", "type": cubrid_types.SEQUENCE(cubrid_types.VARCHAR(50))},
                ],
                "pk_constraint": {"name": None, "constrained_columns": ["id"]},
            },
            "profiles": {
                "columns": [
                    {"name": "id", "type": sa.Integer(), "nullable": False},
                    {"name": "account_id", "type": sa.Integer(), "nullable": False},
                ],
                "pk_constraint": {"name": None, "constrained_columns": ["id"]},
                "foreign_keys": [
                    {
                        "name": "fk_profiles_account_id_accounts",
                        "constrained_columns": ["account_id"],
                        "referred_schema": None,
                        "referred_table": "accounts",
                        "referred_columns": ["id"],
                        "options": {},
                    }
                ],
            },
            "email_registry": {
                "columns": [
                    {"name": "id", "type": sa.Integer(), "nullable": False},
                    {"name": "email", "type": cubrid_types.VARCHAR(255), "nullable": False},
                ],
                "pk_constraint": {"name": None, "constrained_columns": ["id"]},
                "unique_constraints": [
                    {"name": "uq_email_registry_email", "column_names": ["email"]}
                ],
            },
            "documented": {
                "columns": [
                    {
                        "name": "id",
                        "type": sa.Integer(),
                        "nullable": False,
                        "comment": "Primary key",
                    },
                    {
                        "name": "label",
                        "type": cubrid_types.VARCHAR(100),
                        "nullable": True,
                        "comment": "Display label",
                    },
                ],
                "pk_constraint": {"name": None, "constrained_columns": ["id"]},
                "table_comment": {"text": "Representative comments"},
            },
            "json_docs": {
                "columns": [
                    {"name": "id", "type": sa.Integer(), "nullable": False},
                    {"name": "payload", "type": cubrid_types.JSON(), "nullable": True},
                ],
                "pk_constraint": {"name": None, "constrained_columns": ["id"]},
            },
        }

        self._assert_empty_diff_twice(metadata, reflected_schema)

    def test_compare_metadata_no_diffs_for_known_false_positive_aliases(self):
        metadata = sa.MetaData()

        sa.Table(
            "autogen_aliases",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("username", cubrid_types.VARCHAR(255), nullable=False),
            sa.Column("tags", cubrid_types.SET("a", "b")),
        )

        reflected_schema = {
            "autogen_aliases": {
                "columns": [
                    {"name": "id", "type": sa.Integer(), "nullable": False},
                    {"name": "is_active", "type": cubrid_types.SMALLINT(), "nullable": False},
                    {
                        "name": "username",
                        "type": cubrid_types.VARCHAR(255),
                        "nullable": False,
                    },
                    {
                        "name": "tags",
                        "type": cubrid_types.SET(cubrid_types.VARCHAR(100)),
                        "nullable": True,
                    },
                ],
                "pk_constraint": {"name": None, "constrained_columns": ["id"]},
            }
        }

        self._assert_empty_diff_twice(
            metadata,
            reflected_schema,
            compare_type=self._compare_type_with_collection_alias,
        )
