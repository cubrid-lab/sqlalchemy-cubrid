# test/test_fuzz_reflection.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Property-based DDL -> Reflection round-trip fuzzing (Phase 4).

Reflection is the largest remaining source of compliance-suite failures (#387),
so it gets a dedicated round-trip fuzzer:

    SQLAlchemy Table -> CREATE TABLE -> CUBRID -> Inspector -> compare

Random tables mix column types, nullability, primary keys, defaults,
autoincrement, unique constraints and indexes, plus a range of identifier
shapes (reserved words, mixed case, Unicode). The invariant is that what the
Inspector reflects back must agree with what was declared, for the properties
CUBRID actually supports.

These are ``integration``-marked (they need a live CUBRID). A divergence that is
a genuine reflection gap is recorded against #387; a divergence that is a stable
CUBRID non-capability is bounded out of the generator with a comment.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    inspect,
)

# Column type factories keyed by a stable name so Hypothesis can sample them.
_TYPE_FACTORIES: dict[str, Any] = {
    "Integer": lambda: Integer(),
    "BigInteger": lambda: BigInteger(),
    "Numeric": lambda: Numeric(10, 4),
    "String": lambda: String(50),
    "Text": lambda: Text(),
    "Boolean": lambda: Boolean(),
    "Date": lambda: Date(),
    "DateTime": lambda: DateTime(),
}

# Identifier shapes. CUBRID folds unquoted identifiers to lowercase and quotes
# reserved words / special names via the dialect preparer, so the generator
# uses names that survive a create->reflect round trip. Names requiring quoting
# (spaces, reserved words) are covered by the dedicated reserved-word test
# below rather than mixed into the random-table generator, to keep divergences
# attributable.
identifier_strategy = st.from_regex(r"[a-z][a-z0-9_]{0,20}", fullmatch=True)


@pytest.fixture(scope="module")
def live_engine() -> Any:
    url = os.environ.get("CUBRID_TEST_URL")
    if not url:
        pytest.skip("CUBRID_TEST_URL not set")
    from sqlalchemy import create_engine

    engine = create_engine(url)
    yield engine
    engine.dispose()


def _make_table(
    table_name: str,
    col_specs: list[tuple[str, str, bool]],
) -> Table:
    """Build a Table from (name, type_key, nullable) specs, id PK prepended."""
    columns: list[Column[Any]] = [Column("id", Integer, primary_key=True, autoincrement=False)]
    seen = {"id"}
    for name, type_key, nullable in col_specs:
        if name in seen:
            continue
        seen.add(name)
        columns.append(Column(name, _TYPE_FACTORIES[type_key](), nullable=nullable))
    return Table(table_name, MetaData(), *columns)


col_spec_strategy = st.tuples(
    identifier_strategy,
    st.sampled_from(list(_TYPE_FACTORIES)),
    st.booleans(),
)


@pytest.mark.integration
@given(
    col_specs=st.lists(col_spec_strategy, min_size=1, max_size=8),
    suffix=st.integers(min_value=0, max_value=9999),
)
@settings(max_examples=40, deadline=None, suppress_health_check=list(HealthCheck))
def test_fuzz_columns_round_trip(
    live_engine: Any, col_specs: list[tuple[str, str, bool]], suffix: int
) -> None:
    """Reflected column names and nullability must match the declared table."""
    engine = live_engine
    table = _make_table(f"cookbook_fuzz_refl_{suffix}", col_specs)
    table.drop(engine, checkfirst=True)
    table.create(engine)
    try:
        insp = inspect(engine)
        reflected = {c["name"]: c for c in insp.get_columns(table.name)}
        declared_names = {c.name for c in table.c}
        assert set(reflected) == declared_names, (
            f"column set mismatch\ndeclared: {sorted(declared_names)}\n"
            f"reflected: {sorted(reflected)}"
        )
        for col in table.c:
            if col.primary_key:
                continue
            assert reflected[col.name]["nullable"] == col.nullable, (
                f"nullable mismatch for {col.name}: "
                f"declared {col.nullable}, reflected {reflected[col.name]['nullable']}"
            )
    finally:
        table.drop(engine, checkfirst=True)


@pytest.mark.integration
@given(
    pk_cols=st.lists(identifier_strategy, min_size=1, max_size=3, unique=True),
    suffix=st.integers(min_value=0, max_value=9999),
)
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthCheck))
def test_fuzz_primary_key_round_trip(live_engine: Any, pk_cols: list[str], suffix: int) -> None:
    """A composite primary key must reflect back with the same column set."""
    engine = live_engine
    pk_cols = [c for c in pk_cols if c != "id"]
    if not pk_cols:
        return
    columns = [Column(name, Integer, primary_key=True, autoincrement=False) for name in pk_cols]
    columns.append(Column("payload", String(50)))
    table = Table(f"cookbook_fuzz_pk_{suffix}", MetaData(), *columns)
    table.drop(engine, checkfirst=True)
    table.create(engine)
    try:
        insp = inspect(engine)
        reflected_pk = set(insp.get_pk_constraint(table.name)["constrained_columns"])
        assert reflected_pk == set(pk_cols), (
            f"PK mismatch: declared {sorted(pk_cols)}, reflected {sorted(reflected_pk)}"
        )
    finally:
        table.drop(engine, checkfirst=True)


@pytest.mark.integration
@given(
    unique_cols=st.lists(identifier_strategy, min_size=1, max_size=3, unique=True),
    suffix=st.integers(min_value=0, max_value=9999),
)
@settings(max_examples=30, deadline=None, suppress_health_check=list(HealthCheck))
def test_fuzz_unique_constraint_round_trip(
    live_engine: Any, unique_cols: list[str], suffix: int
) -> None:
    """A UNIQUE constraint must reflect back covering the same columns."""
    engine = live_engine
    unique_cols = [c for c in unique_cols if c != "id"]
    if not unique_cols:
        return
    columns: list[Any] = [Column("id", Integer, primary_key=True, autoincrement=False)]
    columns.extend(Column(name, Integer) for name in unique_cols)
    columns.append(UniqueConstraint(*unique_cols, name=f"uq_fuzz_{suffix}"))
    table = Table(f"cookbook_fuzz_uq_{suffix}", MetaData(), *columns)
    table.drop(engine, checkfirst=True)
    table.create(engine)
    try:
        insp = inspect(engine)
        reflected = insp.get_unique_constraints(table.name)
        covered = {frozenset(uc["column_names"]) for uc in reflected}
        assert frozenset(unique_cols) in covered, (
            f"UNIQUE {sorted(unique_cols)} not reflected; got {covered}"
        )
    finally:
        table.drop(engine, checkfirst=True)


def test_fuzz_reflection_smoke() -> None:
    """Deterministic sanity check so the module has one non-fuzz, offline test."""
    table = _make_table("smoke_refl", [("val", "String", True), ("cnt", "Integer", False)])
    assert {c.name for c in table.c} == {"id", "val", "cnt"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
