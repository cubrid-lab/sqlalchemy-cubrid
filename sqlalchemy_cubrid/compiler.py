# sqlalchemy_cubrid/compiler.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""CUBRID SQL, DDL, and type compilers for SQLAlchemy 2.0."""

from __future__ import annotations

from typing import Any

from sqlalchemy.exc import CompileError
from sqlalchemy.sql import compiler, elements
from sqlalchemy.sql import sqltypes

from sqlalchemy_cubrid._compat import (
    bind_with_type,
    get_distinct,
    get_for_update_arg,
    get_limit_clause,
    get_offset_clause,
    is_literal_value,
)


class CubridCompiler(compiler.SQLCompiler):
    """SQLCompiler subclass for CUBRID."""

    def visit_sysdate_func(self, fn: Any, **kw: Any) -> str:
        return "SYSDATE"

    def visit_utc_timestamp_func(self, fn: Any, **kw: Any) -> str:
        return "UTC_TIMESTAMP()"

    def visit_cardinality_func(self, fn: Any, **kw: Any) -> str:
        """Raise clear error for CARDINALITY() which is broken in CUBRID 11.x.

        CUBRID documents CARDINALITY() but the server returns runtime errors.
        See: https://github.com/cubrid-lab/.github/issues/3
        """
        raise CompileError(
            "CUBRID does not support CARDINALITY() at runtime (server bug). "
            "Workaround: use a subquery with COUNT(*) after unnesting the "
            "collection via TABLE(column), e.g.: "
            "SELECT (SELECT COUNT(*) FROM TABLE(t.tags) AS u) FROM t"
        )

    def visit_group_concat_func(self, fn: Any, **kw: Any) -> str:
        """Render GROUP_CONCAT aggregate function.

        CUBRID supports GROUP_CONCAT([DISTINCT] expr [ORDER BY ...] [SEPARATOR '...'])
        """
        return "GROUP_CONCAT(%s)" % self.function_argspec(fn, **kw)

    def visit_cast(self, cast: Any, **kw: Any) -> str:
        # https://www.cubrid.org/manual/en/11.0/sql/function/typecast_fn.html#cast
        type_ = self.process(cast.typeclause)
        if type_ is None:
            return self.process(cast.clause.self_group())
        return f"CAST({self.process(cast.clause)} AS {type_})"

    def render_literal_value(self, value: Any, type_: Any) -> str:
        # SQLAlchemy's base render_literal_value escapes single quotes, which is
        # correct for CUBRID. Backslash handling depends on the server's
        # `no_backslash_escapes` setting (default `yes` => backslash is literal).
        rendered = str(super().render_literal_value(value, type_))
        if getattr(self.dialect, "no_backslash_escapes", True):
            # Default CUBRID behavior: backslash is a literal character, do NOT
            # double it. Doing so would silently corrupt data (e.g. C:\temp).
            return rendered
        # Legacy escape mode (no_backslash_escapes=no): backslash is an escape
        # character, so it must be doubled to be preserved as a literal.
        rendered = rendered.replace("\\", "\\\\")
        return rendered

    def get_select_precolumns(self, select: Any, **kw: Any) -> str:
        if bool(get_distinct(select)):
            return "DISTINCT "
        return ""

    def visit_join(
        self,
        join: Any,
        asfrom: bool = False,
        from_linter: Any = None,
        **kwargs: Any,
    ) -> str:
        # https://www.cubrid.org/manual/en/11.0/sql/query/select.html#join-query
        if getattr(join, "full", False):
            raise CompileError("CUBRID does not support FULL OUTER JOIN")
        return "".join(
            (
                self.process(join.left, asfrom=True, **kwargs),
                (join.isouter and " LEFT OUTER JOIN " or " INNER JOIN "),
                self.process(join.right, asfrom=True, **kwargs),
                " ON ",
                self.process(join.onclause, **kwargs),
            )
        )

    def visit_lateral(self, lateral_: Any, **kw: Any) -> str:
        raise CompileError("CUBRID does not support LATERAL")

    @staticmethod
    def _check_returning(stmt: Any, operation: str) -> None:
        """Raise CompileError if RETURNING is requested (not supported by CUBRID).

        CUBRID does not support INSERT/UPDATE/DELETE ... RETURNING.
        For auto-increment PK retrieval on INSERT, the dialect uses
        LAST_INSERT_ID() automatically via ``result.inserted_primary_key``.
        """
        if getattr(stmt, "_returning", None):
            raise CompileError(
                f"CUBRID does not support {operation} ... RETURNING. "
                "For auto-increment PK retrieval on INSERT, use "
                "result.inserted_primary_key (uses LAST_INSERT_ID() automatically)."
            )

    def visit_insert(self, insert_stmt: Any, **kw: Any) -> Any:
        self._check_returning(insert_stmt, "INSERT")
        return super().visit_insert(insert_stmt, **kw)

    def visit_update(self, update_stmt: Any, **kw: Any) -> Any:
        self._check_returning(update_stmt, "UPDATE")
        return super().visit_update(update_stmt, **kw)

    def visit_delete(self, delete_stmt: Any, **kw: Any) -> Any:
        self._check_returning(delete_stmt, "DELETE")
        return super().visit_delete(delete_stmt, **kw)

    def for_update_clause(self, select: Any, **kw: Any) -> str:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Render FOR UPDATE clause.

        CUBRID supports::

            SELECT ... FOR UPDATE
            SELECT ... FOR UPDATE OF col1, col2

        CUBRID does NOT support NOWAIT or SKIP LOCKED.
        """
        for_update_arg = get_for_update_arg(select)
        if for_update_arg is None:
            return ""
        if for_update_arg.nowait:
            raise CompileError("CUBRID does not support FOR UPDATE NOWAIT")
        if for_update_arg.skip_locked:
            raise CompileError("CUBRID does not support FOR UPDATE SKIP LOCKED")
        if for_update_arg.read:
            raise CompileError("CUBRID does not support FOR SHARE / FOR KEY SHARE")
        if getattr(for_update_arg, "key_share", False):
            raise CompileError("CUBRID does not support FOR KEY SHARE")
        text = " FOR UPDATE"
        if for_update_arg.of:
            text += " OF " + ", ".join(self.process(col, **kw) for col in for_update_arg.of)
        return text

    def limit_clause(self, select: Any, **kw: Any) -> str:
        # https://www.cubrid.org/manual/en/11.0/sql/query/select.html#limit-clause
        # SA 2.0: _limit_clause / _offset_clause are ClauseElements, not raw ints.
        limit_clause = get_limit_clause(select)
        offset_clause = get_offset_clause(select)
        if limit_clause is None and offset_clause is None:
            return ""
        if limit_clause is None:
            assert offset_clause is not None
            return " \n LIMIT %s, 1073741823" % (self.process(offset_clause, **kw),)
        if offset_clause is not None:
            return " \n LIMIT %s, %s" % (
                self.process(offset_clause, **kw),
                self.process(limit_clause, **kw),
            )
        return " \n LIMIT %s" % (self.process(limit_clause, **kw),)

    def update_limit_clause(self, update_stmt: Any) -> str | None:  # pyright: ignore[reportIncompatibleMethodOverride]
        # https://www.cubrid.org/manual/en/11.0/sql/query/update.html
        limit = update_stmt.kwargs.get(f"{self.dialect.name}_limit", None)
        if limit is not None:
            if type(limit) is not int or limit < 0:
                raise CompileError("cubrid_limit must be a non-negative integer, got %r" % (limit,))
            return f"LIMIT {limit}"
        return None

    def update_post_criteria_clause(self, update_stmt: Any, **kw: Any) -> str | None:
        # SA 2.1 replaced the dialect-level ``update_limit_clause`` hook with
        # ``update_post_criteria_clause``. SA 2.0 never calls this method, so
        # the override is harmless there.
        parts: list[str] = []
        try:
            base = super().update_post_criteria_clause(update_stmt, **kw)
        except AttributeError:  # pragma: no cover — SA 2.0 base class lacks this hook
            base = None
        if base:
            parts.append(base)
        limit_text = self.update_limit_clause(update_stmt)
        if limit_text:
            parts.append(limit_text)
        return " ".join(parts) if parts else None

    def update_tables_clause(
        self,
        update_stmt: Any,
        from_table: Any,
        extra_froms: Any,
        **kw: Any,
    ) -> str:
        return ", ".join(
            t._compiler_dispatch(self, asfrom=True, **kw) for t in [from_table] + list(extra_froms)
        )

    def update_from_clause(
        self,
        update_stmt: Any,
        from_table: Any,
        extra_froms: Any,
        from_hints: Any,
        **kw: Any,
    ) -> str:
        raise CompileError(
            "CUBRID does not support UPDATE ... FROM (multi-table UPDATE). "
            "Use a subquery in the SET clause instead."
        )

    def visit_on_duplicate_key_update(self, on_duplicate: Any, **kw: Any) -> str:
        """Render ON DUPLICATE KEY UPDATE clause.

        CUBRID uses VALUES() function to reference inserted values,
        identical to MySQL's pre-8.0 syntax.
        """
        from sqlalchemy.sql import coercions, elements, roles, visitors
        from sqlalchemy.sql.expression import literal_column

        statement = self.current_executable
        table = getattr(statement, "table", None)
        if table is None:
            return "ON DUPLICATE KEY UPDATE"

        if on_duplicate._parameter_ordering:
            parameter_ordering = [
                coercions.expect(roles.DMLColumnRole, key)
                for key in on_duplicate._parameter_ordering
            ]
            ordered_keys = set(parameter_ordering)
            cols = [table.c[key] for key in parameter_ordering if key in table.c] + [
                c for c in table.c if c.key not in ordered_keys
            ]
        else:
            cols = list(table.c)

        clauses = []
        on_duplicate_update = {
            coercions.expect_as_key(roles.DMLColumnRole, key): value
            for key, value in on_duplicate.update.items()
        }

        for column in (col for col in cols if col.key in on_duplicate_update):
            val = on_duplicate_update[column.key]
            if is_literal_value(val):
                val = elements.BindParameter(None, val, type_=column.type)
                value_text = self.process(val.self_group(), use_schema=False)
            else:

                def replace(element: Any, captured_column: Any = column, **kw: Any) -> Any | None:
                    if isinstance(element, elements.BindParameter) and element.type._isnull:
                        return bind_with_type(element, captured_column.type)
                    elif (
                        isinstance(element, elements.ColumnClause)
                        and element.table is on_duplicate.inserted_alias
                    ):
                        return literal_column(f"VALUES({self.preparer.quote(element.name)})")
                    else:
                        return None

                val = visitors.replacement_traverse(val, {}, replace)
                value_text = self.process(val.self_group(), use_schema=False)

            name_text = self.preparer.quote(column.name)
            clauses.append(f"{name_text} = {value_text}")

        non_matching = set(on_duplicate_update) - {c.key for c in cols}
        if non_matching:
            from sqlalchemy import util

            table_name = getattr(table, "name", "<unknown>")
            util.warn(
                "Additional column names not matching "
                "any column keys in table '%s': %s"
                % (
                    table_name,
                    (", ".join("'%s'" % c for c in non_matching)),
                )
            )

        if not clauses:
            raise CompileError("ON DUPLICATE KEY UPDATE has no effective columns to update")

        return f"ON DUPLICATE KEY UPDATE {', '.join(clauses)}"

    def _validate_merge_params(self, merge_stmt: Any) -> None:
        """Validate MERGE statement has required components."""
        from sqlalchemy import exc

        if merge_stmt._target is None:
            raise exc.CompileError("MERGE statement requires a target table")
        if merge_stmt._using_source is None:
            raise exc.CompileError("MERGE statement requires a USING source")
        if merge_stmt._on_condition is None:
            raise exc.CompileError("MERGE statement requires an ON condition")
        if merge_stmt._when_matched is None and merge_stmt._when_not_matched is None:
            raise exc.CompileError(
                "MERGE statement must include WHEN MATCHED and/or WHEN NOT MATCHED"
            )

    def visit_merge(self, merge_stmt: Any, **kw: Any) -> str:
        from sqlalchemy import exc
        from sqlalchemy.sql import elements

        self._validate_merge_params(merge_stmt)

        target = merge_stmt._target
        source = merge_stmt._using_source
        on_condition = merge_stmt._on_condition
        when_matched = merge_stmt._when_matched
        when_not_matched = merge_stmt._when_not_matched

        target_columns = getattr(target, "c", None)

        def _resolve_target_column(column_key: Any) -> Any | None:
            if isinstance(column_key, str):
                if target_columns is not None and column_key in target_columns:
                    return target_columns[column_key]
                return None
            if hasattr(column_key, "name"):
                name = column_key.name
                if target_columns is not None and name in target_columns:
                    return target_columns[name]
                if target_columns is not None:
                    raise exc.CompileError(f"MERGE: column '{name}' not found in target table")
                return column_key
            return None

        def _render_column_name(column_key: Any, resolved: Any | None = None) -> str:
            # If we resolved a target column, always use its actual DB name
            if resolved is not None and hasattr(resolved, "name"):
                return self.preparer.quote(resolved.name)
            if isinstance(column_key, str):
                return self.preparer.quote(column_key)
            if hasattr(column_key, "name"):
                return self.preparer.quote(column_key.name)
            return self.process(column_key, **kw)

        def _render_value(value: Any, target_column: Any | None) -> str:
            if is_literal_value(value):
                value = elements.BindParameter(
                    None,
                    value,
                    type_=getattr(target_column, "type", None),
                )
            return self.process(value.self_group(), use_schema=False, **kw)

        lines = [
            f"MERGE INTO {self.process(target, asfrom=True, **kw)}",
            f"USING {self.process(source, asfrom=True, **kw)}",
            f"ON ({self.process(on_condition, **kw)})",
        ]

        if when_matched is not None:
            matched_values = when_matched.get("values") or {}
            if not matched_values:
                raise exc.CompileError(
                    "MERGE WHEN MATCHED clause requires at least one UPDATE value"
                )

            set_clauses = []
            for column_key, value in matched_values.items():
                target_column = _resolve_target_column(column_key)
                if target_column is None and isinstance(column_key, str):
                    raise exc.CompileError(
                        f"MERGE WHEN MATCHED: column '{column_key}' not found in target table"
                    )
                set_clauses.append(
                    f"{_render_column_name(column_key, target_column)} = {_render_value(value, target_column)}"
                )

            matched_clause = f"WHEN MATCHED THEN UPDATE SET {', '.join(set_clauses)}"  # nosec B608
            matched_where = when_matched.get("where")
            if matched_where is not None:
                matched_clause += f" WHERE {self.process(matched_where, **kw)}"

            delete_where = when_matched.get("delete_where")
            if delete_where is not None:
                matched_clause += f" DELETE WHERE {self.process(delete_where, **kw)}"

            lines.append(matched_clause)

        if when_not_matched is not None:
            insert_columns = when_not_matched.get("columns") or []
            insert_values = when_not_matched.get("values") or []

            if not insert_columns or not insert_values:
                raise exc.CompileError(
                    "MERGE WHEN NOT MATCHED clause requires INSERT columns and values"
                )
            if len(insert_columns) != len(insert_values):
                raise exc.CompileError(
                    "MERGE WHEN NOT MATCHED INSERT columns and values must match"
                )

            rendered_columns = []
            rendered_values = []
            for column_key, value in zip(insert_columns, insert_values):
                target_column = _resolve_target_column(column_key)
                if target_column is None and isinstance(column_key, str):
                    raise exc.CompileError(
                        f"MERGE WHEN NOT MATCHED: column '{column_key}' not found in target table"
                    )
                rendered_columns.append(_render_column_name(column_key, target_column))
                rendered_values.append(_render_value(value, target_column))

            not_matched_clause = (
                "WHEN NOT MATCHED THEN INSERT "
                f"({', '.join(rendered_columns)}) "
                f"VALUES ({', '.join(rendered_values)})"
            )
            insert_where = when_not_matched.get("where")
            if insert_where is not None:
                not_matched_clause += f" WHERE {self.process(insert_where, **kw)}"

            lines.append(not_matched_clause)

        return "\n".join(lines)

    def visit_replace(self, replace_stmt: Any, **kw: Any) -> str:
        text = str(super().visit_insert(replace_stmt, **kw))  # type: ignore[no-untyped-call]
        if "INSERT INTO" in text:
            return text.replace("INSERT INTO", "REPLACE INTO", 1)
        if text.startswith("INSERT"):
            return "REPLACE" + text[len("INSERT") :]
        raise NotImplementedError(
            f"Could not convert INSERT to REPLACE: unexpected SQL format: {text!r}"
        )

    def _render_json_extract_from_binary(
        self, binary: elements.BinaryExpression[Any], operator: Any, **kw: Any
    ) -> str:
        if binary.type._type_affinity is sqltypes.JSON:
            return "JSON_EXTRACT(%s, %s)" % (
                self.process(binary.left, **kw),
                self.process(binary.right, **kw),
            )

        # When the target type is not JSON, convert JSON 'null' to SQL NULL
        case_expression = "CASE JSON_EXTRACT(%s, %s) WHEN 'null' THEN NULL" % (
            self.process(binary.left, **kw),
            self.process(binary.right, **kw),
        )

        if binary.type._type_affinity is sqltypes.Boolean:
            type_expression = (
                "WHEN 'true' THEN 1 WHEN 'false' THEN 0 ELSE CAST(JSON_EXTRACT(%s, %s) AS INTEGER)"
            ) % (
                self.process(binary.left, **kw),
                self.process(binary.right, **kw),
            )
        elif binary.type._type_affinity is sqltypes.Integer:
            type_expression = "ELSE CAST(JSON_EXTRACT(%s, %s) AS INTEGER)" % (
                self.process(binary.left, **kw),
                self.process(binary.right, **kw),
            )
        elif binary.type._type_affinity is sqltypes.Numeric or (
            # SA 2.1 split Float out of the Numeric affinity; treat both as DOUBLE.
            binary.type._type_affinity is sqltypes.Float
        ):
            type_expression = "ELSE CAST(JSON_EXTRACT(%s, %s) AS DOUBLE)" % (
                self.process(binary.left, **kw),
                self.process(binary.right, **kw),
            )
        else:
            type_expression = "ELSE JSON_UNQUOTE(JSON_EXTRACT(%s, %s))" % (
                self.process(binary.left, **kw),
                self.process(binary.right, **kw),
            )

        return case_expression + " " + type_expression + " END"

    def visit_json_getitem_op_binary(
        self, binary: elements.BinaryExpression[Any], operator: Any, **kw: Any
    ) -> str:
        return self._render_json_extract_from_binary(binary, operator, **kw)

    def visit_json_path_getitem_op_binary(
        self, binary: elements.BinaryExpression[Any], operator: Any, **kw: Any
    ) -> str:
        return self._render_json_extract_from_binary(binary, operator, **kw)


class CubridDDLCompiler(compiler.DDLCompiler):
    """DDLCompiler subclass for CUBRID.

    Handles AUTO_INCREMENT for autoincrement columns and column defaults.
    """

    def get_column_specification(self, column: Any, **kw: Any) -> str:
        """Build column DDL specification.

        CUBRID syntax::

            column_name TYPE [NOT NULL] [AUTO_INCREMENT] [DEFAULT value]
        """
        colspec = [
            self.preparer.format_column(column),
            self.dialect.type_compiler_instance.process(column.type, type_expression=column),
        ]

        if not column.nullable:
            colspec.append("NOT NULL")

        if (
            column.table is not None
            and column is column.table._autoincrement_column
            and (column.server_default is None)
        ):
            colspec.append("AUTO_INCREMENT")
        else:
            default = self.get_column_default_string(column)
            if default is not None:
                colspec.append("DEFAULT " + default)

        if column.comment is not None:
            literal = self.sql_compiler.render_literal_value(
                column.comment,
                sqltypes.String(),
            )
            colspec.append("COMMENT " + literal)

        return " ".join(colspec)

    def post_create_table(self, table: Any) -> str:  # pyright: ignore[reportIncompatibleMethodOverride]
        table_opts = []
        if table.comment is not None:
            literal = self.sql_compiler.render_literal_value(
                table.comment,
                sqltypes.String(),
            )
            table_opts.append(f"\n COMMENT = {literal}")
        return "".join(table_opts)

    def visit_set_table_comment(self, create: Any, **kw: Any) -> str:
        return "ALTER TABLE %s COMMENT = %s" % (
            self.preparer.format_table(create.element),
            self.sql_compiler.render_literal_value(
                create.element.comment,
                sqltypes.String(),
            ),
        )

    def visit_drop_table_comment(self, drop: Any, **kw: Any) -> str:
        return "ALTER TABLE %s COMMENT = ''" % (self.preparer.format_table(drop.element),)

    def visit_set_column_comment(self, create: Any, **kw: Any) -> str:
        return "ALTER TABLE %s MODIFY %s %s COMMENT %s" % (
            self.preparer.format_table(create.element.table),
            self.preparer.format_column(create.element),
            self.dialect.type_compiler_instance.process(
                create.element.type,
                type_expression=create.element,
            ),
            self.sql_compiler.render_literal_value(
                create.element.comment,
                sqltypes.String(),
            ),
        )


class CubridTypeCompiler(compiler.GenericTypeCompiler):
    """TypeCompiler for CUBRID data types."""

    def _get(self, key: str, type_: Any, kw: dict[str, Any]) -> Any:
        return kw.get(key, getattr(type_, key, None))

    def visit_BOOLEAN(self, type_: Any, **kw: Any) -> str:
        # CUBRID has no native BOOLEAN; map to SMALLINT.
        return self.visit_SMALLINT(type_)

    def visit_NUMERIC(self, type_: Any, **kw: Any) -> str:
        if type_.precision is None:
            return "NUMERIC"
        elif type_.scale is None:
            return f"NUMERIC({type_.precision})"
        else:
            return f"NUMERIC({type_.precision}, {type_.scale})"

    def visit_DECIMAL(self, type_: Any, **kw: Any) -> str:
        if type_.precision is None:
            return "DECIMAL"
        elif type_.scale is None:
            return f"DECIMAL({type_.precision})"
        else:
            return f"DECIMAL({type_.precision}, {type_.scale})"

    def visit_FLOAT(self, type_: Any, **kw: Any) -> str:
        if type_.precision is None:
            return "FLOAT"
        else:
            return f"FLOAT({type_.precision})"

    def visit_DOUBLE(self, type_: Any, **kw: Any) -> str:
        return "DOUBLE"

    visit_double = visit_DOUBLE

    def visit_MONETARY(self, type_: Any, **kw: Any) -> str:
        return "MONETARY"

    def visit_SMALLINT(self, type_: Any, **kw: Any) -> str:
        return "SMALLINT"

    def visit_BIGINT(self, type_: Any, **kw: Any) -> str:
        return "BIGINT"

    def visit_BIT(self, type_: Any, **kw: Any) -> str:
        if type_.varying:
            compiled = "BIT VARYING"
            if type_.length is not None:
                compiled += f"({type_.length})"
        else:
            compiled = f"BIT({type_.length})"
        return compiled

    def visit_datetime(self, type_: Any, **kw: Any) -> str:
        if getattr(type_, "timezone", False):
            return "DATETIMETZ"
        return "DATETIME"

    def visit_DATETIME(self, type_: Any, **kw: Any) -> str:
        if getattr(type_, "timezone", False):
            return "DATETIMETZ"
        return "DATETIME"

    def visit_DATE(self, type_: Any, **kw: Any) -> str:
        return "DATE"

    def visit_TIME(self, type_: Any, **kw: Any) -> str:
        return "TIME"

    def visit_TIMESTAMP(self, type_: Any, **kw: Any) -> str:
        if getattr(type_, "timezone", False):
            return "TIMESTAMPLTZ"
        return "TIMESTAMP"

    def visit_TIMESTAMPTZ(self, type_: Any, **kw: Any) -> str:
        return "TIMESTAMPTZ"

    def visit_TIMESTAMPLTZ(self, type_: Any, **kw: Any) -> str:
        return "TIMESTAMPLTZ"

    def visit_DATETIMETZ(self, type_: Any, **kw: Any) -> str:
        return "DATETIMETZ"

    def visit_DATETIMELTZ(self, type_: Any, **kw: Any) -> str:
        return "DATETIMELTZ"

    def visit_VARCHAR(self, type_: Any, **kw: Any) -> str:
        if hasattr(type_, "national") and type_.national:
            return self.visit_NVARCHAR(type_)
        elif type_.length:
            return "VARCHAR(%d)" % type_.length
        else:
            return "VARCHAR(4096)"

    def visit_CHAR(self, type_: Any, **kw: Any) -> str:
        if hasattr(type_, "national") and type_.national:
            return self.visit_NCHAR(type_)
        elif type_.length:
            return f"CHAR({type_.length})"
        else:
            return "CHAR"

    def visit_NVARCHAR(self, type_: Any, **kw: Any) -> str:
        if type_.length:
            return f"NCHAR VARYING({type_.length})"
        else:
            return "NCHAR VARYING(4096)"

    def visit_NCHAR(self, type_: Any, **kw: Any) -> str:
        if type_.length:
            return f"NCHAR({type_.length})"
        else:
            return "NCHAR"

    def visit_OBJECT(self, type_: Any, **kw: Any) -> str:
        return "OBJECT"

    def visit_large_binary(self, type_: Any, **kw: Any) -> str:
        return self.visit_BLOB(type_)

    def visit_text(self, type_: Any, **kw: Any) -> str:
        return self.visit_STRING(type_)

    def visit_BLOB(self, type_: Any, **kw: Any) -> str:
        return "BLOB"

    def visit_CLOB(self, type_: Any, **kw: Any) -> str:
        return "CLOB"

    def visit_STRING(self, type_: Any, **kw: Any) -> str:
        if hasattr(type_, "national") and type_.national:
            return self.visit_NVARCHAR(type_)
        return "STRING"

    def visit_SET(self, type_: Any, **kw: Any) -> str:
        return self._visit_collection(type_, "SET")

    def visit_MULTISET(self, type_: Any, **kw: Any) -> str:
        return self._visit_collection(type_, "MULTISET")

    def visit_SEQUENCE(self, type_: Any, **kw: Any) -> str:
        return self._visit_collection(type_, "SEQUENCE")

    def _visit_collection(self, type_: Any, collection_type: str, **kw: Any) -> str:
        """Compile CUBRID collection types (SET, MULTISET, LIST/SEQUENCE).

        See: https://www.cubrid.org/manual/en/11.0/sql/datatype.html#collection-types
        """
        parts = []
        for value in type_._ddl_values:
            if isinstance(value, str):
                parts.append(value)
            else:
                parts.append(self.process(value))
        return f"{collection_type}({','.join(parts)})"

    def visit_JSON(self, type_: Any, **kw: Any) -> str:
        return "JSON"
