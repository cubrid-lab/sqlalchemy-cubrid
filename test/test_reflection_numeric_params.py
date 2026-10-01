# test/test_reflection_numeric_params.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Whitespace in numeric type parameters during column reflection (#609).

``get_columns`` strips the parameter list from a ``SHOW COLUMNS`` type string
to look the type up in ``ischema_names``. It must treat ``NUMERIC(10, 2)`` like
``NUMERIC(10,2)`` instead of reflecting it as ``NullType`` with a warning.

The whitespace cases below are parser robustness inputs, not server output.
``SHOW COLUMNS`` on CUBRID 10.2.18, 11.0.16, 11.2.9 and 11.4.6 printed the
compact form for every declaration tried::

    NUMERIC(10,2)   -> NUMERIC(10,2)
    DECIMAL(10, 2)  -> NUMERIC(10,2)
    NUMERIC(5)      -> NUMERIC(5,0)
    NUMERIC         -> NUMERIC(15,0)

and printed collections as ``SET OF NUMERIC,VARCHAR`` (no member parameters),
so the parenthesized collection-member cases are robustness inputs as well.
"""

from __future__ import annotations

import warnings
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy import exc as sa_exc
from sqlalchemy.types import NullType

from sqlalchemy_cubrid.dialect import CubridDialect
from sqlalchemy_cubrid.types import BIT


def _reflect(coltypes: list[str]) -> list[Any]:
    """Run the real ``get_columns`` over fake ``SHOW COLUMNS`` rows and return
    the reflected types, failing on any warning."""
    dialect = CubridDialect()
    connection = MagicMock()
    rows = [(f"c{i}", coltype, "YES", "", None, "") for i, coltype in enumerate(coltypes)]
    connection.execute.side_effect = [rows, []]
    with warnings.catch_warnings():
        warnings.simplefilter("error", sa_exc.SAWarning)
        columns = dialect.get_columns(connection, "t")
    return [column["type"] for column in columns]


@pytest.mark.parametrize("name", ["NUMERIC", "DECIMAL"])
@pytest.mark.parametrize(
    "params",
    ["(10,2)", "(10, 2)", "(10 ,2)", "(10 , 2)", "(10,  2)"],
    ids=["compact", "space_after_comma", "space_before_comma", "both", "two_spaces"],
)
def test_numeric_precision_scale(name: str, params: str) -> None:
    (coltype,) = _reflect([f"{name}{params}"])
    assert type(coltype).__name__ == name
    assert (coltype.precision, coltype.scale) == (10, 2)


@pytest.mark.parametrize("name", ["NUMERIC", "DECIMAL"])
def test_numeric_precision_only_and_bare(name: str) -> None:
    precision_only, bare = _reflect([f"{name}(15)", name])
    assert type(precision_only).__name__ == name
    assert (precision_only.precision, precision_only.scale) == (15, None)
    assert type(bare).__name__ == name
    assert (bare.precision, bare.scale) == (None, None)


@pytest.mark.parametrize("collection", ["SET", "MULTISET", "SEQUENCE"])
@pytest.mark.parametrize("member", ["NUMERIC(10, 2)", "DECIMAL(10 , 2)", "NUMERIC(10,2)"])
def test_collection_numeric_member(collection: str, member: str) -> None:
    (coltype,) = _reflect([f"{collection}({member}, VARCHAR(50))"])
    assert type(coltype).__name__ == collection
    numeric, varchar = coltype._ddl_values
    assert type(numeric).__name__ == member.split("(")[0]
    assert (numeric.precision, numeric.scale) == (10, 2)
    assert type(varchar).__name__ == "VARCHAR"
    assert varchar.length == 50


def test_other_parameterized_types_unchanged() -> None:
    char, varchar, bit, bit_varying = _reflect(
        ["CHAR(3)", "VARCHAR(100)", "BIT(32)", "BIT VARYING(64)"]
    )
    assert (type(char).__name__, char.length) == ("CHAR", 3)
    assert (type(varchar).__name__, varchar.length) == ("VARCHAR", 100)
    assert isinstance(bit, BIT) and (bit.length, bit.varying) == (32, False)
    assert isinstance(bit_varying, BIT) and (bit_varying.length, bit_varying.varying) == (64, True)


def test_unsupported_parameter_grammar_still_unrecognized() -> None:
    """Only digit lists are stripped: a non-numeric parameter list is not
    silently accepted as a known type."""
    dialect = CubridDialect()
    connection = MagicMock()
    connection.execute.side_effect = [[("c0", "NUMERIC(p, s)", "YES", "", None, "")], []]
    with pytest.warns(sa_exc.SAWarning, match="Did not recognize type"):
        (column,) = dialect.get_columns(connection, "t")
    assert isinstance(column["type"], NullType)
