# sqlalchemy_cubrid/alembic_impl.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Alembic migration support for the CUBRID dialect.

This module provides the Alembic ``DefaultImpl`` subclass that enables
Alembic migrations against a CUBRID database.  It is registered as an
entry-point under ``alembic.ddl`` so that Alembic auto-discovers it
when the target database URL uses the ``cubrid://`` scheme.

Usage::

    # alembic.ini
    [alembic]
    sqlalchemy.url = cubrid://dba:password@localhost:33000/demodb

    # That's it — Alembic will pick up the CUBRID implementation
    # automatically via the ``alembic.ddl`` entry point.

CUBRID-specific notes
---------------------
* **DDL is auto-committed** — CUBRID implicitly commits every DDL
  statement, so ``transactional_ddl`` is set to ``False``.
* **Native column rename** — CUBRID supports
  ``ALTER TABLE … RENAME COLUMN old TO new``.  Alembic's
  ``alter_column(new_column_name=…)`` emits it directly.
* **Native column type change** — CUBRID supports in-place type
  changes via ``ALTER TABLE … MODIFY col <definition>`` (and
  ``CHANGE old new <definition>`` when combined with a rename).
  Because CUBRID restates the *entire* column definition, existing
  attributes are reconstructed from Alembic's ``existing_*`` metadata.
  Incompatible conversions may be rejected depending on the
  ``alter_table_change_type_strict`` system parameter; use
  ``batch_alter_table`` as a fallback for lossy migrations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import sqlalchemy as sa

try:
    from alembic.ddl.impl import DefaultImpl
except ImportError:  # pragma: no cover — optional dependency
    raise ImportError(
        "Alembic is required for migration support. Install it with: pip install sqlalchemy-cubrid[alembic]"
    ) from None

from alembic.ddl.base import (
    AlterColumn,
    alter_table,
    format_column_name,
    format_server_default,
)
from sqlalchemy.ext.compiler import compiles

if TYPE_CHECKING:
    from typing import Protocol

    from sqlalchemy.sql.type_api import TypeEngine

    class AutogenContextLike(Protocol):
        imports: set[str]


class CubridRenameColumn(AlterColumn):
    """Represents ``ALTER TABLE t RENAME COLUMN old TO new`` for CUBRID."""

    def __init__(
        self,
        name: str,
        column_name: str,
        newname: str,
        schema: str | None = None,
    ) -> None:
        super(AlterColumn, self).__init__(name, schema=schema)
        self.column_name = column_name
        self.newname = newname


class CubridModifyColumn(AlterColumn):
    """Represents ``ALTER TABLE t MODIFY col <definition>`` for CUBRID."""

    def __init__(
        self,
        name: str,
        column_name: str,
        *,
        type_: Any,
        nullable: bool | None = None,
        default: Any = False,
        autoincrement: bool | None = None,
        comment: Any = False,
        schema: str | None = None,
    ) -> None:
        super(AlterColumn, self).__init__(name, schema=schema)
        self.column_name = column_name
        self.nullable = nullable
        self.default = default
        self.autoincrement = autoincrement
        self.comment = comment
        if type_ is None:
            raise ValueError(
                f"CUBRID MODIFY/CHANGE COLUMN for '{column_name}' on table "
                f"'{name}' requires the column type. Pass ``type_`` or "
                f"``existing_type`` so the full column definition can be built."
            )
        self.type_ = sa.types.to_instance(type_)


class CubridChangeColumn(CubridModifyColumn):
    """Represents ``ALTER TABLE t CHANGE old new <definition>`` for CUBRID."""

    def __init__(self, *args: Any, newname: str, **kw: Any) -> None:
        super().__init__(*args, **kw)
        self.newname = newname


def _cubrid_colspec(compiler: Any, element: CubridModifyColumn) -> str:
    """Build the CUBRID column definition for MODIFY/CHANGE clauses."""
    spec = [compiler.dialect.type_compiler_instance.process(element.type_)]
    if element.nullable is False:
        spec.append("NOT NULL")
    if element.autoincrement:
        spec.append("AUTO_INCREMENT")
    elif element.default is not False and element.default is not None:
        spec.append("DEFAULT " + format_server_default(compiler, element.default))
    if element.comment:
        spec.append(
            "COMMENT "
            + compiler.sql_compiler.render_literal_value(element.comment, sa.types.String())
        )
    return " ".join(spec)


@compiles(CubridRenameColumn, "cubrid")
def _cubrid_rename_column(element: CubridRenameColumn, compiler: Any, **kw: Any) -> str:
    return "%s RENAME COLUMN %s TO %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_column_name(compiler, element.column_name),
        format_column_name(compiler, element.newname),
    )


@compiles(CubridChangeColumn, "cubrid")
def _cubrid_change_column(element: CubridChangeColumn, compiler: Any, **kw: Any) -> str:
    return "%s CHANGE %s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_column_name(compiler, element.column_name),
        format_column_name(compiler, element.newname),
        _cubrid_colspec(compiler, element),
    )


@compiles(CubridModifyColumn, "cubrid")
def _cubrid_modify_column(element: CubridModifyColumn, compiler: Any, **kw: Any) -> str:
    return "%s MODIFY %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_column_name(compiler, element.column_name),
        _cubrid_colspec(compiler, element),
    )


class CubridImpl(DefaultImpl):
    """Alembic migration implementation for CUBRID.

    Registered via the ``alembic.ddl`` entry-point so Alembic
    auto-discovers it for ``cubrid://`` URLs.

    Attributes
    ----------
    __dialect__ : str
        ``"cubrid"`` — matches the SQLAlchemy dialect name.
    transactional_ddl : bool
        ``False`` — CUBRID implicitly commits DDL statements.
    """

    __dialect__: str = "cubrid"
    transactional_ddl: bool = False

    _collection_type_names: set[str] = {"SET", "MULTISET", "SEQUENCE"}

    # CUBRID's STRING / CLOB / Text are stored physically as
    # VARCHAR(1073741823).  When SQLAlchemy's reflection round-trips a
    # ``Text`` / ``CLOB`` / ``STRING`` column it sees a VARCHAR with that
    # exact length, which trips Alembic's default compare_type into
    # reporting a spurious type change on every autogenerate run
    # (see cubrid-lab/sqlalchemy-cubrid#120).
    _CUBRID_UNBOUNDED_VARCHAR_LENGTH: int = 1073741823
    _unbounded_string_type_names: set[str] = {"TEXT", "CLOB", "STRING"}

    @staticmethod
    def _normalize_collection_value(value: object) -> str:
        if isinstance(value, str):
            return value.strip().lower()
        if isinstance(value, sa.types.TypeEngine):
            return repr(value).strip().lower()
        return repr(value).strip().lower()

    def render_type(
        self, type_obj: TypeEngine[Any], autogen_context: AutogenContextLike
    ) -> str | Literal[False]:
        if type(type_obj).__module__ != "sqlalchemy_cubrid.types":
            return False

        type_name = type_obj.__class__.__name__
        if type_name not in self._collection_type_names:
            return False

        values = getattr(type_obj, "_ddl_values", ())
        rendered_values: list[str] = []

        for value in values:
            if isinstance(value, str):
                rendered_values.append(repr(value))
            elif isinstance(value, sa.types.TypeEngine):
                # Render as sa.TypeName(...) preserving constructor args
                autogen_context.imports.add("import sqlalchemy as sa")
                rendered_values.append(f"sa.{repr(value)}")
            else:
                rendered_values.append(repr(value))

        autogen_context.imports.add("from sqlalchemy_cubrid import types as cubrid_types")
        args = ", ".join(rendered_values)
        return f"cubrid_types.{type_name}({args})"

    def compare_type(
        self, inspector_column: sa.Column[Any], metadata_column: sa.Column[Any]
    ) -> bool:
        inspector_type = inspector_column.type
        metadata_type = metadata_column.type

        # Suppress false-positive Text/CLOB/STRING vs VARCHAR(max) diffs.
        # See ``_CUBRID_UNBOUNDED_VARCHAR_LENGTH`` docstring above.
        if self._is_unbounded_string_match(inspector_type, metadata_type):
            return False

        inspector_name = inspector_type.__class__.__name__
        metadata_name = metadata_type.__class__.__name__

        is_inspector_collection = inspector_name in self._collection_type_names
        is_metadata_collection = metadata_name in self._collection_type_names

        if not is_inspector_collection and not is_metadata_collection:
            return super().compare_type(inspector_column, metadata_column)

        if is_inspector_collection != is_metadata_collection:
            return True

        if inspector_name != metadata_name:
            return True

        inspector_values = [
            self._normalize_collection_value(value)
            for value in getattr(inspector_type, "_ddl_values", ())
        ]
        metadata_values = [
            self._normalize_collection_value(value)
            for value in getattr(metadata_type, "_ddl_values", ())
        ]

        if inspector_name == "SEQUENCE":
            return inspector_values != metadata_values

        return set(inspector_values) != set(metadata_values)

    def alter_column(
        self,
        table_name: str,
        column_name: str,
        nullable: Any = None,
        server_default: Any = False,
        name: str | None = None,
        type_: Any = None,
        **kw: Any,
    ) -> None:
        """Emit CUBRID-native ALTER TABLE DDL for a column change.

        CUBRID supports column rename and in-place type changes with
        MySQL-compatible syntax::

            ALTER TABLE t RENAME COLUMN old TO new
            ALTER TABLE t MODIFY col <definition>
            ALTER TABLE t CHANGE old new <definition>

        A type change (``type_``) is emitted as ``MODIFY`` (or ``CHANGE``
        when combined with a rename).  Because CUBRID's ``MODIFY``/``CHANGE``
        restates the *entire* column definition, this method reconstructs the
        definition from the ``existing_*`` metadata that Alembic supplies so
        that attributes such as ``NOT NULL`` / ``DEFAULT`` / ``COMMENT`` are
        not silently dropped.  Incompatible conversions may be rejected by the
        server depending on the ``alter_table_change_type_strict`` system
        parameter; use ``batch_alter_table`` as a fallback for lossy
        migrations.
        """
        if type_ is not None:
            schema = kw.get("schema")
            resolved_type = type_ if type_ is not None else kw.get("existing_type")
            resolved_nullable = nullable if nullable is not None else kw.get("existing_nullable")
            resolved_default = (
                server_default if server_default is not False else kw.get("existing_server_default")
            )
            autoincrement = kw.get("autoincrement")
            resolved_autoincrement = (
                autoincrement if autoincrement is not None else kw.get("existing_autoincrement")
            )
            comment = kw.get("comment", False)
            resolved_comment = comment if comment is not False else kw.get("existing_comment")
            if name is not None:
                self._exec(
                    CubridChangeColumn(
                        table_name,
                        column_name,
                        newname=name,
                        type_=resolved_type,
                        nullable=resolved_nullable,
                        default=resolved_default,
                        autoincrement=resolved_autoincrement,
                        comment=resolved_comment,
                        schema=schema,
                    )
                )
            else:
                self._exec(
                    CubridModifyColumn(
                        table_name,
                        column_name,
                        type_=resolved_type,
                        nullable=resolved_nullable,
                        default=resolved_default,
                        autoincrement=resolved_autoincrement,
                        comment=resolved_comment,
                        schema=schema,
                    )
                )
            return
        if name is not None:
            self._exec(
                CubridRenameColumn(
                    table_name,
                    column_name,
                    newname=name,
                    schema=kw.get("schema"),
                )
            )
            return
        super().alter_column(
            table_name,
            column_name,
            nullable=nullable,
            server_default=server_default,
            name=name,
            type_=type_,
            **kw,
        )

    @classmethod
    def _is_unbounded_string_match(
        cls, inspector_type: TypeEngine[Any], metadata_type: TypeEngine[Any]
    ) -> bool:
        """Return ``True`` when one side is an unbounded string type and the other is a VARCHAR sized to CUBRID's STRING maximum length."""
        return cls._matches_unbounded_pair(
            inspector_type, metadata_type
        ) or cls._matches_unbounded_pair(metadata_type, inspector_type)

    @classmethod
    def _matches_unbounded_pair(
        cls, varchar_side: TypeEngine[Any], unbounded_side: TypeEngine[Any]
    ) -> bool:
        if varchar_side.__class__.__name__ != "VARCHAR":
            return False
        if getattr(varchar_side, "length", None) != cls._CUBRID_UNBOUNDED_VARCHAR_LENGTH:
            return False
        unbounded_name = unbounded_side.__class__.__name__.upper()
        if unbounded_name in cls._unbounded_string_type_names:
            return True
        # Plain SQLAlchemy String() with no length declared also maps to
        # VARCHAR(1073741823) on CUBRID.
        if unbounded_name == "STRING" or unbounded_name.endswith("STRING"):
            return getattr(unbounded_side, "length", None) is None
        return False
