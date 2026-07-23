# sqlalchemy_cubrid/dml.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""CUBRID DML constructs."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

from sqlalchemy import exc, util
from sqlalchemy.sql._typing import _DMLTableArgument
from sqlalchemy.sql.base import (
    _exclusive_against,
    _generative,
    ColumnCollection,
    Generative,
    ReadOnlyColumnCollection,
)
from sqlalchemy.sql.dml import Insert as StandardInsert
from sqlalchemy.sql.elements import ClauseElement, KeyedColumnElement
from sqlalchemy.sql.expression import Executable, alias
from sqlalchemy.sql.selectable import NamedFromClause
from sqlalchemy.util.typing import Self

__all__ = ("Insert", "Merge", "Replace", "insert", "merge", "replace")

_UpdateArg = Union[
    Mapping[str, Any],
    List[Tuple[str, Any]],
]


def insert(table: _DMLTableArgument) -> Insert:
    """Construct a CUBRID-specific variant :class:`Insert` construct.

    Includes :meth:`Insert.on_duplicate_key_update`.
    """
    return Insert(table)


class Insert(StandardInsert):
    """CUBRID-specific implementation of INSERT.

    Adds methods for CUBRID-specific syntaxes such as ON DUPLICATE KEY UPDATE.
    """

    stringify_dialect = "cubrid"
    inherit_cache = True

    @property
    def inserted(self) -> ReadOnlyColumnCollection[str, KeyedColumnElement[Any]]:
        """Provide the "inserted" namespace for an ON DUPLICATE KEY UPDATE statement.

        CUBRID uses VALUES() to reference the row being inserted,
        identical to MySQL's pre-8.0 syntax.
        """
        return self.inserted_alias.columns

    @util.memoized_property
    def inserted_alias(self) -> NamedFromClause:
        return alias(self.table, name="inserted")

    @_generative
    @_exclusive_against(
        "_post_values_clause",
        msgs={
            "_post_values_clause": "This Insert construct already "
            "has an ON DUPLICATE KEY clause present"
        },
    )
    def on_duplicate_key_update(self, *args: _UpdateArg, **kw: Any) -> Self:
        """Specifies the ON DUPLICATE KEY UPDATE clause.

        :param **kw: Column keys linked to UPDATE values.
        :param *args: A dictionary or list of 2-tuples as a single positional argument.
        """
        arg_values = list(args)
        values: _UpdateArg = dict(kw)

        if arg_values and kw:
            raise exc.ArgumentError("Can't pass kwargs and positional arguments simultaneously")
        if arg_values:
            if len(arg_values) > 1:
                raise exc.ArgumentError(
                    "Only a single dictionary or list of tuples is accepted positionally."
                )
            values = arg_values[0]

        self._post_values_clause = OnDuplicateClause(self.inserted_alias, values)
        return self


def replace(table: _DMLTableArgument) -> Replace:
    """Construct a CUBRID REPLACE INTO statement.

    CUBRID's REPLACE works like MySQL's REPLACE - it inserts a new row,
    or if a duplicate key violation occurs, deletes the old row and inserts
    the new one.

    Usage::

        from sqlalchemy_cubrid import replace

        stmt = replace(users).values(id=1, name="updated")
    """
    return Replace(table)


class Replace(StandardInsert):
    """CUBRID-specific REPLACE INTO statement.

    Extends StandardInsert to generate REPLACE INTO instead of INSERT INTO.
    Supports all standard INSERT syntax (values, from_select, etc.)
    but does NOT support ON DUPLICATE KEY UPDATE (use Insert for that).
    """

    stringify_dialect = "cubrid"
    inherit_cache = True
    __visit_name__ = "replace"

    @property
    def _effective_plugin_target(self) -> str:
        return "insert"


class OnDuplicateClause(ClauseElement):
    __visit_name__ = "on_duplicate_key_update"

    _parameter_ordering: Optional[List[str]] = None
    update: Dict[str, Any]
    stringify_dialect = "cubrid"

    def __init__(self, inserted_alias: NamedFromClause, update: _UpdateArg) -> None:
        self.inserted_alias = inserted_alias
        if isinstance(update, list) and (update and isinstance(update[0], tuple)):
            self._parameter_ordering = [key for key, _ in update]
            update = dict(update)
        if isinstance(update, dict):
            if not update:
                raise ValueError("update parameter dictionary must not be empty")
        elif isinstance(update, ColumnCollection):
            update = dict(update)
        else:
            raise ValueError(
                "update parameter must be a non-empty dictionary "
                "or a ColumnCollection such as the `.c.` collection "
                "of a Table object"
            )
        self.update = update


def merge(target: _DMLTableArgument) -> Merge:
    """Construct a CUBRID-specific MERGE statement.

    CUBRID's MERGE matches rows from a source against a target table
    using an ON condition, then executes UPDATE for matched rows and/or
    INSERT for unmatched rows.

    Usage::

        from sqlalchemy_cubrid import merge

        stmt = (
            merge(target_table)
            .using(source_table)
            .on(target_table.c.id == source_table.c.id)
            .when_matched_then_update({"name": source_table.c.name})
            .when_not_matched_then_insert({"id": source_table.c.id, "name": source_table.c.name})
        )
    """
    return Merge(target)


class Merge(Executable, ClauseElement, Generative):
    __visit_name__ = "merge"
    stringify_dialect = "cubrid"
    inherit_cache = True

    _target: _DMLTableArgument
    _using_source: Optional[Any]
    _on_condition: Optional[ClauseElement]
    _when_matched: Optional[Dict[str, Any]]
    _when_not_matched: Optional[Dict[str, Any]]

    def __init__(self, target: _DMLTableArgument) -> None:
        self._target = target
        self._using_source = None
        self._on_condition = None
        self._when_matched = None
        self._when_not_matched = None

    @_generative
    def into(self, target_table: _DMLTableArgument) -> Self:
        self._target = target_table
        return self

    @_generative
    def using(self, source: Any) -> Self:
        self._using_source = source
        return self

    @_generative
    def on(self, condition: ClauseElement) -> Self:
        self._on_condition = condition
        return self

    @_generative
    def when_matched_then_update(
        self,
        values_dict: Union[Mapping[Any, Any], List[Tuple[Any, Any]], Tuple[Tuple[Any, Any], ...]],
        where: Optional[ClauseElement] = None,
        delete_where: Optional[ClauseElement] = None,
    ) -> Self:
        values = self._normalize_key_value_pairs(values_dict, argument_name="values_dict")
        existing_delete_where = (
            self._when_matched.get("delete_where") if self._when_matched is not None else None
        )
        self._when_matched = {
            "values": dict(values),
            "where": where,
            "delete_where": (delete_where if delete_where is not None else existing_delete_where),
        }
        return self

    @_generative
    def when_matched_then_delete(self, where: Optional[ClauseElement] = None) -> Self:
        if self._when_matched is None:
            raise ValueError("WHEN MATCHED UPDATE clause must be specified before DELETE WHERE")

        self._when_matched = {
            "values": dict(self._when_matched["values"]),
            "where": self._when_matched.get("where"),
            "delete_where": where,
        }
        return self

    @_generative
    def when_not_matched_then_insert(
        self,
        values_dict_or_column_list: Union[
            Mapping[Any, Any],
            List[Tuple[Any, Any]],
            Tuple[Tuple[Any, Any], ...],
            List[Any],
            Tuple[Any, ...],
        ],
        where: Optional[ClauseElement] = None,
    ) -> Self:
        columns: List[Any]
        values: List[Any]

        if isinstance(values_dict_or_column_list, Mapping):
            pairs = self._normalize_key_value_pairs(
                values_dict_or_column_list,
                argument_name="values_dict_or_column_list",
            )
            columns = [column for column, _ in pairs]
            values = [value for _, value in pairs]
        elif isinstance(values_dict_or_column_list, ColumnCollection):
            pairs = self._normalize_key_value_pairs(
                dict(values_dict_or_column_list),
                argument_name="values_dict_or_column_list",
            )
            columns = [column for column, _ in pairs]
            values = [value for _, value in pairs]
        elif isinstance(values_dict_or_column_list, (list, tuple)):
            if values_dict_or_column_list and isinstance(values_dict_or_column_list[0], tuple):
                pairs = self._normalize_key_value_pairs(
                    list(values_dict_or_column_list),
                    argument_name="values_dict_or_column_list",
                )
                columns = [column for column, _ in pairs]
                values = [value for _, value in pairs]
            else:
                columns = list(values_dict_or_column_list)
                if not columns:
                    raise ValueError(
                        "values_dict_or_column_list must be a non-empty dictionary, "
                        "a list of tuples, or a non-empty column list"
                    )
                values = list(columns)
        else:
            raise ValueError(
                "values_dict_or_column_list must be a non-empty dictionary, "
                "a list of tuples, or a non-empty column list"
            )

        self._when_not_matched = {
            "columns": columns,
            "values": values,
            "where": where,
        }
        return self

    def _normalize_key_value_pairs(
        self,
        values: Union[Mapping[Any, Any], List[Tuple[Any, Any]], Tuple[Tuple[Any, Any], ...]],
        argument_name: str,
    ) -> List[Tuple[Any, Any]]:
        if isinstance(values, Mapping):
            pairs = list(values.items())
        elif isinstance(values, list):
            pairs = list(values)
        elif isinstance(values, tuple):
            pairs = list(values)
        else:
            raise ValueError(f"{argument_name} must be a non-empty dictionary or a list of tuples")

        if not pairs:
            raise ValueError(f"{argument_name} must be a non-empty dictionary or a list of tuples")

        if not all(isinstance(pair, tuple) and len(pair) == 2 for pair in pairs):
            raise ValueError(f"{argument_name} must be a non-empty dictionary or a list of tuples")

        return pairs
