# sqlalchemy_cubrid/alembic_impl.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Alembic migration support for the CUBRID dialect.

This module provides the Alembic ``DefaultImpl`` subclass that enables
Alembic migrations against a CUBRID database.  Alembic keys its
implementations by dialect name, and ``DefaultImpl`` subclasses register
themselves on import via ``__dialect__``.  Alembic 1.18+ imports this module
through the ``alembic.plugins`` entry point
(:mod:`_sqlalchemy_cubrid_alembic`); with Alembic 1.7.2-1.17
``sqlalchemy_cubrid.dialect`` imports it.  Either way every CUBRID URL
(``cubrid://``, ``cubrid+pycubrid://``, ``cubrid+aiopycubrid://``) finds it.

Usage::

    # alembic.ini
    [alembic]
    sqlalchemy.url = cubrid://dba:password@localhost:33000/demodb

    # That's it — the CUBRID implementation is registered automatically;
    # the default env.py needs no extra import.

CUBRID-specific notes
---------------------
* **DDL is transactional** — CUBRID does not implicitly commit DDL.
  With client autocommit off (the dialect always turns it off),
  ``CREATE``/``ALTER``/``DROP``/``TRUNCATE``/``CREATE INDEX``/``RENAME``
  and friends are undone by ``ROLLBACK`` and never commit earlier DML, so
  ``transactional_ddl`` is ``True``: by default Alembic runs the whole
  upgrade in one transaction.  Pass ``transaction_per_migration=True`` to
  ``context.configure()`` to commit after each revision instead, which
  releases schema locks sooner on long or large-table migrations.
* **Offline scripts have no ``BEGIN``** — CUBRID has no ``BEGIN``
  statement (csql rejects it); a transaction starts implicitly, so
  :meth:`CubridImpl.emit_begin` emits nothing and ``--sql`` output ends
  each transaction with ``COMMIT;`` only.
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
    AlterTable,
    alter_table,
    format_column_name,
    format_server_default,
)
from sqlalchemy.ext.compiler import compiles

from sqlalchemy_cubrid.types import STRING as CUBRID_STRING

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
        # Skip AlterColumn.__init__ (which requires column_name and sets up
        # existing_* attrs); call the grandparent AlterTable.__init__ directly.
        AlterTable.__init__(self, name, schema=schema)
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
        # Skip AlterColumn.__init__ (see CubridRenameColumn); call the
        # grandparent AlterTable.__init__ directly.
        AlterTable.__init__(self, name, schema=schema)
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


class CubridDropColumnDefault(AlterColumn):
    """Represents ``ALTER TABLE t ALTER COLUMN c SET DEFAULT NULL`` for CUBRID.

    CUBRID has no ``ALTER COLUMN ... DROP DEFAULT`` (a syntax error on 10.2
    and 11.4); setting the default to ``NULL`` removes it (#861).
    """

    def __init__(self, name: str, column_name: str, schema: str | None = None) -> None:
        AlterTable.__init__(self, name, schema=schema)
        self.column_name = column_name


class CubridChangeColumn(CubridModifyColumn):
    """Represents ``ALTER TABLE t CHANGE old new <definition>`` for CUBRID."""

    def __init__(self, *args: Any, newname: str, **kw: Any) -> None:
        super().__init__(*args, **kw)
        self.newname = newname


def _cubrid_colspec(compiler: Any, element: CubridModifyColumn) -> str:
    """Build the CUBRID column definition for MODIFY/CHANGE clauses.

    Every known attribute is stated explicitly (#861): CUBRID 11.4 keeps an
    attribute that MODIFY/CHANGE omits (NOT NULL, the default, the comment)
    while 10.2 resets it, so only an explicit ``NULL``, ``DEFAULT NULL`` or
    ``COMMENT ''`` has the same effect on both. ``nullable=None``,
    ``default=False`` and ``comment=False`` mean "unknown" and are omitted.
    """
    spec = [compiler.dialect.type_compiler_instance.process(element.type_)]
    if element.nullable is not None:
        spec.append("NULL" if element.nullable else "NOT NULL")
    if element.autoincrement:
        spec.append("AUTO_INCREMENT")
    elif element.default is None:
        spec.append("DEFAULT NULL")
    elif element.default is not False:
        spec.append("DEFAULT " + format_server_default(compiler, element.default))
    if element.comment is not False:
        spec.append(
            "COMMENT "
            + compiler.sql_compiler.render_literal_value(element.comment or "", sa.types.String())
        )
    return " ".join(spec)


@compiles(CubridRenameColumn, "cubrid")
def _cubrid_rename_column(element: CubridRenameColumn, compiler: Any, **kw: Any) -> str:
    return "%s RENAME COLUMN %s TO %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_column_name(compiler, element.column_name),
        format_column_name(compiler, element.newname),
    )


@compiles(CubridDropColumnDefault, "cubrid")
def _cubrid_drop_column_default(element: CubridDropColumnDefault, compiler: Any, **kw: Any) -> str:
    return "%s ALTER COLUMN %s SET DEFAULT NULL" % (
        alter_table(compiler, element.table_name, element.schema),
        format_column_name(compiler, element.column_name),
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

    Registered on import through ``__dialect__``; the CUBRID dialect
    module imports it when Alembic is installed.

    Attributes
    ----------
    __dialect__ : str
        ``"cubrid"`` — matches the SQLAlchemy dialect name.
    transactional_ddl : bool
        ``True`` — CUBRID DDL runs inside the current transaction and is
        undone by ``ROLLBACK``; only client autocommit commits it early.
    """

    __dialect__: str = "cubrid"
    transactional_ddl: bool = True

    _collection_type_names: set[str] = {"SET", "MULTISET", "SEQUENCE"}

    # CUBRID's STRING / CLOB / Text are stored physically as
    # VARCHAR(1073741823).  When SQLAlchemy's reflection round-trips a
    # ``Text`` / ``CLOB`` / ``STRING`` column it sees a VARCHAR with that
    # exact length, which trips Alembic's default compare_type into
    # reporting a spurious type change on every autogenerate run
    # (see cubrid-lab/sqlalchemy-cubrid#120). ``UnicodeText`` also compiles
    # to STRING (#534). The dialect's own ``STRING`` type is matched by
    # class, not by name: the generic ``sa.String`` has the same upper-cased
    # name, and ``String(n)`` must go through the length comparison (#544).
    _CUBRID_UNBOUNDED_VARCHAR_LENGTH: int = 1073741823
    _unbounded_string_type_names: set[str] = {"TEXT", "UNICODETEXT", "CLOB"}

    def emit_begin(self) -> None:
        """Emit nothing: CUBRID has no ``BEGIN`` statement.

        A CUBRID transaction starts implicitly with the first statement
        after a ``COMMIT``/``ROLLBACK``, and csql rejects ``BEGIN``.  The
        inherited :meth:`emit_commit` still writes ``COMMIT;``, which ends
        each transaction in ``--sql`` output.
        """

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
        not silently dropped.  A ``nullable`` or ``comment`` change also needs
        that definition, so it is emitted the same way and requires ``type_``
        or ``existing_type``.  Dropping a default (``server_default=None``)
        without other changes emits ``ALTER COLUMN c SET DEFAULT NULL``, since
        CUBRID has no ``DROP DEFAULT`` (#861).  Incompatible conversions may be
        rejected by the server depending on the ``alter_table_change_type_strict`` system
        parameter; use ``batch_alter_table`` as a fallback for lossy
        migrations.
        """
        schema = kw.get("schema")
        comment = kw.get("comment", False)
        existing_nullable = kw.get("existing_nullable")
        existing_default = kw.get("existing_server_default", False)
        drop_default = server_default is None and existing_default is not None
        if drop_default and existing_nullable is False and nullable is None:
            # SET DEFAULT NULL is rejected for a NOT NULL column (#861).
            nullable_target: bool | None = False
        else:
            nullable_target = nullable
        if type_ is None and nullable_target is None and comment is False:
            if name is not None:
                self._exec(CubridRenameColumn(table_name, column_name, newname=name, schema=schema))
                column_name = name
            if drop_default:
                self._exec(CubridDropColumnDefault(table_name, column_name, schema=schema))
            elif server_default is not False and server_default is not None:
                super().alter_column(
                    table_name,
                    column_name,
                    server_default=server_default,
                    type_=type_,
                    **kw,
                )
            return

        # NOT NULL and COMMENT exist only in a full column definition on
        # CUBRID (no ALTER COLUMN SET/DROP NOT NULL, no COMMENT ON), so a
        # nullability or comment change is a MODIFY/CHANGE too (#861).
        # CUBRID 10.2/11.0 reset an attribute that MODIFY omits, 11.2+ keep
        # it, so every known attribute is stated and only changes use NULL /
        # DEFAULT NULL / COMMENT '' (an explicit NULL on a nullable column is
        # error -709 from 11.2).
        resolved_type = type_ if type_ is not None else kw.get("existing_type")
        resolved_nullable = nullable_target if nullable_target is not None else existing_nullable
        if resolved_nullable is True and existing_nullable is True:
            resolved_nullable = None
        if server_default is not False and server_default is not None:
            resolved_default: Any = server_default
        elif drop_default:
            resolved_default = None
        elif existing_default is None:
            resolved_default = False
        else:
            resolved_default = existing_default
        autoincrement = kw.get("autoincrement")
        resolved_autoincrement = (
            autoincrement if autoincrement is not None else kw.get("existing_autoincrement")
        )
        # Alembic's existing_comment defaults to None, which cannot tell
        # "no comment" from "not given"; only a real one is restated.
        resolved_comment = comment if comment is not False else kw.get("existing_comment")
        if comment is False and not resolved_comment:
            resolved_comment = False

        definition = {
            "type_": resolved_type,
            "autoincrement": resolved_autoincrement,
            "comment": resolved_comment,
            "schema": schema,
        }
        steps: list[dict[str, Any]] = [{"nullable": resolved_nullable, "default": resolved_default}]
        if resolved_default is None and resolved_nullable is False:
            # A NOT NULL column cannot get a NULL default, and dropping the
            # default by omission works only before 11.2: drop it while the
            # column is nullable, then restore NOT NULL.
            steps = [
                {"nullable": True if existing_nullable is not True else None, "default": None},
                {"nullable": False, "default": False},
            ]
        for step in steps:
            if name is not None:
                self._exec(
                    CubridChangeColumn(table_name, column_name, newname=name, **definition, **step)
                )
                column_name, name = name, None
            else:
                self._exec(CubridModifyColumn(table_name, column_name, **definition, **step))

    def correct_for_autogen_foreignkeys(
        self,
        conn_fks: set[sa.ForeignKeyConstraint],
        metadata_fks: set[sa.ForeignKeyConstraint],
    ) -> None:
        """Treat a reflected ``RESTRICT`` as the default referential action (#597).

        CUBRID's default for ``ON DELETE`` / ``ON UPDATE`` is ``RESTRICT``
        and ``SHOW CREATE TABLE`` always prints it, so a foreign key created
        without actions reflects as ``ondelete="RESTRICT"`` /
        ``onupdate="RESTRICT"``. Where the matching model foreign key has no
        action, clear the reflected ``RESTRICT`` so autogenerate does not
        drop and re-create an unchanged constraint. Reflection itself stays
        truthful; other actions (including ``NO ACTION``, which CUBRID
        prints as such) still compare as they are.
        """
        metadata_by_name: dict[str, sa.ForeignKeyConstraint] = {}
        metadata_by_key: dict[tuple[Any, ...], list[sa.ForeignKeyConstraint]] = {}
        for fk in metadata_fks:
            if isinstance(fk.name, str):
                metadata_by_name[fk.name] = fk
            metadata_by_key.setdefault(self._fk_match_key(fk), []).append(fk)
        for conn_fk in conn_fks:
            # Match by name when both sides are named and cover the same
            # columns and target; a same-named model FK on other columns is
            # a different constraint (#624). Otherwise every model FK on the
            # same columns and target is a candidate. The reflected FK
            # cannot be paired with one of them, so RESTRICT is cleared only
            # if none names an action: keeping it reports at most a real
            # difference, while clearing it could hide one.
            conn_key = self._fk_match_key(conn_fk)
            named = metadata_by_name.get(conn_fk.name) if isinstance(conn_fk.name, str) else None
            if named is not None and self._fk_match_key(named) != conn_key:
                named = None
            candidates = [named] if named is not None else metadata_by_key.get(conn_key, [])
            if not candidates:
                continue
            for option in ("ondelete", "onupdate"):
                conn_action = getattr(conn_fk, option)
                if (
                    conn_action is not None
                    and conn_action.upper() == "RESTRICT"
                    and all(getattr(fk, option) is None for fk in candidates)
                ):
                    # The rebuilt FK (e.g. in a downgrade) then omits
                    # RESTRICT, which is the same action on CUBRID.
                    setattr(conn_fk, option, None)

    @staticmethod
    def _fk_match_key(fk: sa.ForeignKeyConstraint) -> tuple[Any, ...]:
        """Identify a foreign key by its columns, ignoring name and actions.

        The target schema is left out: CUBRID is single-schema and
        ``get_foreign_keys()`` sets ``referred_schema`` to the schema it was
        called with (``None`` by default), while a model may name the owner
        explicitly, so including it would only cause mismatches.
        """
        return (
            tuple(fk.columns[key].name for key in fk.column_keys),
            tuple((element.column.table.name, element.column.name) for element in fk.elements),
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
        if isinstance(unbounded_side, CUBRID_STRING):
            return True
        # A generic String() with no length declared is treated as unbounded
        # too; String(n) falls through to the normal length comparison (#544).
        if unbounded_name == "STRING" or unbounded_name.endswith("STRING"):
            return getattr(unbounded_side, "length", None) is None
        return False

    def create_index(self, index: Any, **kw: Any) -> None:
        """Error on UNIQUE index that collides with an FK auto-index.

        CUBRID auto-creates a B-tree index for FK columns.  A subsequent
        ``CREATE UNIQUE INDEX`` on the same columns fails (errno=-272),
        and ``ALTER TABLE ADD CONSTRAINT UNIQUE`` also fails.

        Non-unique indexes are passed through — CUBRID accepts them.

        For the Alembic path the table metadata from ``op.create_index()``
        may lack FK info, so we reflect the live schema to check.
        """
        from sqlalchemy import inspect as sa_inspect
        from sqlalchemy.exc import CompileError

        table = index.table
        if index.unique and table is not None and table.name:
            # Offline (--sql) mode has a MockConnection, not None, and
            # cannot be inspected (#861).
            if self.as_sql or self.connection is None:
                raise CompileError(
                    "CUBRID UNIQUE index FK collision checks require a live connection"
                )
            insp = sa_inspect(self.connection)
            fks = insp.get_foreign_keys(table.name, schema=getattr(table, "schema", None))
            idx_cols = tuple(c.name for c in index.columns)
            for fk in fks:
                fk_cols = tuple(fk.get("constrained_columns", []))
                if idx_cols == fk_cols:
                    cols = ", ".join(idx_cols)
                    if len(idx_cols) == 1:
                        hint = (
                            "Declare the column with unique=True "
                            "instead of using a separate Index(..., unique=True)."
                        )
                    else:
                        hint = (
                            "Use a table-level UniqueConstraint(%s) "
                            "instead of Index(..., unique=True)." % cols
                        )
                    raise CompileError(
                        "CUBRID cannot create a UNIQUE index on columns "
                        "that already have an FK auto-index (%s). %s" % (cols, hint)
                    )

        super().create_index(index, **kw)

    def drop_index(self, index: Any, **kw: Any) -> None:
        """Require ``table_name`` for ``op.drop_index()`` (#533).

        CUBRID needs ``DROP INDEX <name> ON <table>``. Without
        ``table_name`` Alembic binds the index to a placeholder table named
        ``no_table``, which would otherwise be emitted verbatim.
        """
        from sqlalchemy.exc import CompileError

        table = index.table
        if table is not None and table.name == "no_table":
            raise CompileError(
                "CUBRID DROP INDEX requires the table (DROP INDEX <name> ON <table>); "
                "pass table_name to op.drop_index(%r, table_name=...)" % index.name
            )
        super().drop_index(index, **kw)
