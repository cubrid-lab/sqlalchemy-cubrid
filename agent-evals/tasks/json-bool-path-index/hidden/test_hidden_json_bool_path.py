"""Evaluator-owned checks for the json-bool-path-index task (#914).

They test the contract in task.json (exception types, unchanged output), not one
implementation's messages, and are copied into the candidate's worktree only by
``scripts/agent_eval.py run``.
"""

from __future__ import annotations

import pytest
import sqlalchemy as sa
from sqlalchemy import Column, Integer, MetaData, Table, select

from sqlalchemy_cubrid.dialect import CubridDialect
from sqlalchemy_cubrid.types import JSON

table = Table("t", MetaData(), Column("id", Integer, primary_key=True), Column("data", JSON))


def _bound(index):
    compiled = select(table.c.data[index]).compile(dialect=CubridDialect())
    (name,) = compiled._bind_processors
    return compiled._bind_processors[name](compiled.construct_params()[name])


def _literal(index):
    stmt = select(table.c.data[index])
    return stmt.compile(dialect=CubridDialect(), compile_kwargs={"literal_binds": True}).string


@pytest.mark.parametrize("index", [True, False, ("items", False), ("a", 0, True), (True,)])
def test_bound_bool_component_is_rejected(index):
    with pytest.raises(TypeError):
        _bound(index)


@pytest.mark.parametrize("index", [True, ("items", False)])
def test_literal_bool_component_is_rejected(index):
    with pytest.raises(sa.exc.CompileError):
        _literal(index)


@pytest.mark.parametrize(
    ("index", "expected"),
    [(0, "$[0]"), (1, "$[1]"), (-1, "$[-1]"), ("True", '$."True"'), (("items", 1), '$."items"[1]')],
)
def test_int_and_string_components_are_unchanged(index, expected):
    assert _bound(index) == expected
    assert expected in _literal(index)
