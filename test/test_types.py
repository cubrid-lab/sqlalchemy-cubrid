# test/test_types.py
"""Offline type tests — no live CUBRID required.

Verify that custom type classes instantiate correctly and have proper
visit names, repr, and inheritance.
"""

from __future__ import annotations

import types
from typing import Any

import pytest
from sqlalchemy import Integer, column, exc, select
from sqlalchemy.sql import sqltypes

from sqlalchemy_cubrid import types as cubrid_types
from sqlalchemy_cubrid.aio_pycubrid_dialect import PyCubridAsyncDialect
from sqlalchemy_cubrid.dialect import CubridDialect
from sqlalchemy_cubrid.pycubrid_dialect import PyCubridDialect

from sqlalchemy_cubrid.types import (
    BIGINT,
    BIT,
    BLOB,
    CHAR,
    CLOB,
    DECIMAL,
    DOUBLE,
    DOUBLE_PRECISION,
    FLOAT,
    MONETARY,
    MULTISET,
    NCHAR,
    NUMERIC,
    NVARCHAR,
    OBJECT,
    REAL,
    SEQUENCE,
    SET,
    SMALLINT,
    STRING,
    VARCHAR,
)


class TestVisitNames:
    """Every type must declare a __visit_name__ matching the CUBRID type."""

    def test_smallint(self):
        assert SMALLINT.__visit_name__ == "SMALLINT"

    def test_bigint(self):
        assert BIGINT.__visit_name__ == "BIGINT"

    def test_numeric(self):
        assert NUMERIC.__visit_name__ == "NUMERIC"

    def test_decimal(self):
        assert DECIMAL.__visit_name__ == "DECIMAL"

    def test_float(self):
        assert FLOAT.__visit_name__ == "FLOAT"

    def test_real(self):
        assert REAL.__visit_name__ == "REAL"

    def test_double(self):
        assert DOUBLE.__visit_name__ == "DOUBLE"

    def test_double_precision(self):
        assert DOUBLE_PRECISION.__visit_name__ == "DOUBLE_PRECISION"

    def test_bit(self):
        assert BIT.__visit_name__ == "BIT"

    def test_char(self):
        assert CHAR.__visit_name__ == "CHAR"

    def test_varchar(self):
        assert VARCHAR.__visit_name__ == "VARCHAR"

    def test_nchar(self):
        assert NCHAR.__visit_name__ == "NCHAR"

    def test_nvarchar(self):
        assert NVARCHAR.__visit_name__ == "NVARCHAR"

    def test_string(self):
        assert STRING.__visit_name__ == "STRING"

    def test_blob(self):
        assert BLOB.__visit_name__ == "BLOB"

    def test_clob(self):
        assert CLOB.__visit_name__ == "CLOB"

    def test_set(self):
        assert SET.__visit_name__ == "SET"

    def test_multiset(self):
        assert MULTISET.__visit_name__ == "MULTISET"

    def test_sequence(self):
        assert SEQUENCE.__visit_name__ == "SEQUENCE"

    def test_monetary(self):
        assert MONETARY.__visit_name__ == "MONETARY"

    def test_object(self):
        assert OBJECT.__visit_name__ == "OBJECT"


class TestTypeInstantiation:
    """Verify types can be constructed without errors."""

    def test_smallint(self):
        t = SMALLINT()
        assert isinstance(t, sqltypes.SMALLINT)

    def test_bigint(self):
        t = BIGINT()
        assert isinstance(t, sqltypes.BIGINT)

    def test_numeric_defaults(self):
        t = NUMERIC()
        assert t.precision is None
        assert t.scale is None

    def test_numeric_with_params(self):
        t = NUMERIC(precision=10, scale=2)
        assert t.precision == 10
        assert t.scale == 2

    def test_decimal_with_params(self):
        t = DECIMAL(precision=15, scale=4)
        assert t.precision == 15
        assert t.scale == 4

    def test_float_default_precision(self):
        t = FLOAT()
        assert t.precision == 7

    def test_float_custom_precision(self):
        t = FLOAT(precision=14)
        assert t.precision == 14

    def test_real(self):
        t = REAL()
        assert isinstance(t, sqltypes.Float)

    def test_double(self):
        t = DOUBLE()
        assert isinstance(t, sqltypes.Float)

    def test_bit_default(self):
        t = BIT()
        assert t.length == 1
        assert t.varying is False

    def test_bit_varying(self):
        t = BIT(length=256, varying=True)
        assert t.length == 256
        assert t.varying is True

    def test_char(self):
        t = CHAR(length=50)
        assert isinstance(t, sqltypes.CHAR)
        assert t.length == 50

    def test_varchar(self):
        t = VARCHAR(length=255)
        assert isinstance(t, sqltypes.VARCHAR)
        assert t.length == 255

    def test_nchar_national(self):
        t = NCHAR(length=100)
        assert t.national is True

    def test_nvarchar_national(self):
        t = NVARCHAR(length=200)
        assert t.national is True

    def test_string(self):
        t = STRING()
        assert isinstance(t, sqltypes.String)

    def test_string_national_passed_to_parent(self):
        """Regression: STRING(national=True) must propagate to _StringType. (#182)"""
        t = STRING(national=True)
        assert t.national is True

    def test_blob(self):
        t = BLOB()
        assert isinstance(t, sqltypes.LargeBinary)

    def test_clob(self):
        t = CLOB()
        assert isinstance(t, sqltypes.Text)

    def test_monetary(self):
        t = MONETARY()
        assert isinstance(t, sqltypes.TypeEngine)

    def test_object(self):
        t = OBJECT()
        assert isinstance(t, sqltypes.TypeEngine)


class TestCollectionTypes:
    """Test SET, MULTISET, SEQUENCE (CUBRID collection types)."""

    def test_set_stores_values(self):
        t = SET("a", "b", "c")
        assert t._ddl_values == ("a", "b", "c")

    def test_multiset_stores_values(self):
        t = MULTISET("x", "y")
        assert t._ddl_values == ("x", "y")

    def test_sequence_stores_values(self):
        t = SEQUENCE("p", "q")
        assert t._ddl_values == ("p", "q")

    def test_set_with_type_objects(self):
        t = SET(CHAR(10), VARCHAR(255))
        assert len(t._ddl_values) == 2

    def test_empty_set(self):
        t = SET()
        assert t._ddl_values == ()


class _Typed:
    """Stand-in for a pycubrid typed collection (``pycubrid.types.Set`` etc.)."""

    def __init__(self, elements: Any = ()) -> None:
        self.elements = tuple(elements)

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and self.elements == getattr(other, "elements", None)


class _TypedSequence(_Typed):
    """Like ``pycubrid.types.Sequence`` after cubrid-lab/pycubrid#580."""

    def __init__(self, elements: Any = ()) -> None:
        if isinstance(elements, (set, frozenset)):
            raise TypeError("Sequence() does not accept a set")
        super().__init__(elements)


def _fake_pycubrid_types(*names: str) -> types.ModuleType:
    module = types.ModuleType("pycubrid.types")
    for name in names:
        base = _TypedSequence if name == "Sequence" else _Typed
        setattr(module, name, type(name, (base,), {}))
    return module


@pytest.fixture
def pycubrid_types(monkeypatch: pytest.MonkeyPatch):
    """Install a fake ``pycubrid.types`` with the given class names."""

    def install(*names: str) -> types.ModuleType:
        module = _fake_pycubrid_types(*names)

        def fake_import(name: str) -> types.ModuleType:
            assert name == "pycubrid.types"
            return module

        monkeypatch.setattr(cubrid_types, "import_module", fake_import)
        return module

    return install


_COLLECTION_CLASSES = [(SET, "Set"), (MULTISET, "Multiset"), (SEQUENCE, "Sequence")]


class TestCollectionBindProcessor:
    """#484: plain collections bind as pycubrid typed collections."""

    @pytest.mark.parametrize("dialect_cls", [PyCubridDialect, PyCubridAsyncDialect])
    @pytest.mark.parametrize(("type_cls", "name"), _COLLECTION_CLASSES)
    def test_wraps_plain_collections(self, pycubrid_types, dialect_cls, type_cls, name):
        module = pycubrid_types("Set", "Multiset", "Sequence")
        typed = getattr(module, name)
        process = type_cls(Integer()).bind_processor(dialect_cls())
        assert process is not None
        values: list[Any] = [[3, 1, 1], (3, 1, 1), []]
        if type_cls is not SEQUENCE:
            values += [{1, 3}, frozenset({1, 3})]
        for value in values:
            got = process(value)
            assert type(got) is typed
            assert got.elements == tuple(value)

    @pytest.mark.parametrize("feature", [True, False], ids=["typed", "pycubrid-1.8.0"])
    @pytest.mark.parametrize("dialect_cls", [PyCubridDialect, PyCubridAsyncDialect])
    @pytest.mark.parametrize("value", [{2, 1}, frozenset({2, 1}), set()])
    def test_sequence_rejects_unordered(self, pycubrid_types, dialect_cls, feature, value):
        # A set has no order, so it cannot be a SEQUENCE; never sorted for you.
        pycubrid_types(*(("Set", "Multiset", "Sequence") if feature else ()))
        process = SEQUENCE(Integer()).bind_processor(dialect_cls())
        assert process is not None
        with pytest.raises(TypeError, match="SEQUENCE is ordered; pass a list or tuple"):
            process(value)

    def test_sequence_without_typed_collections_passes_lists_through(self, pycubrid_types):
        pycubrid_types()
        process = SEQUENCE(Integer()).bind_processor(PyCubridDialect())
        assert process is not None
        value = [2, 1]
        assert process(value) is value
        assert process(None) is None

    @pytest.mark.parametrize(("type_cls", "name"), _COLLECTION_CLASSES)
    def test_passes_other_values_through(self, pycubrid_types, type_cls, name):
        module = pycubrid_types("Set", "Multiset", "Sequence")
        process = type_cls(Integer()).bind_processor(PyCubridDialect())
        assert process is not None
        already_typed = module.Multiset([1])
        text = "{1, 2}"
        mapping = {"a": 1}
        assert process(None) is None
        assert process(already_typed) is already_typed
        assert process(text) is text
        assert process(mapping) is mapping

    @pytest.mark.parametrize("type_cls", [SET, MULTISET])
    def test_no_processor_without_typed_collections(self, pycubrid_types, type_cls):
        # Released pycubrid 1.8.0: no typed classes, so values reach the driver
        # unchanged (and pycubrid rejects a plain collection parameter).
        pycubrid_types()
        assert type_cls(Integer()).bind_processor(PyCubridDialect()) is None

    def test_no_processor_without_pycubrid(self, monkeypatch):
        def missing(name: str) -> types.ModuleType:
            raise ImportError(name)

        monkeypatch.setattr(cubrid_types, "import_module", missing)
        assert SET(Integer()).bind_processor(PyCubridDialect()) is None

    @pytest.mark.parametrize(("type_cls", "name"), _COLLECTION_CLASSES)
    def test_no_processor_on_cubriddb(self, pycubrid_types, type_cls, name):
        # CUBRIDdb binds list/tuple/set values itself (as a SET host variable).
        pycubrid_types("Set", "Multiset", "Sequence")
        assert type_cls(Integer()).bind_processor(CubridDialect()) is None

    @pytest.mark.parametrize("dialect_cls", [CubridDialect, PyCubridDialect])
    @pytest.mark.parametrize(("type_cls", "name"), _COLLECTION_CLASSES)
    def test_values_are_returned_as_the_driver_decodes_them(self, dialect_cls, type_cls, name):
        dialect = dialect_cls()
        assert type_cls(Integer()).result_processor(dialect, None) is None

    def test_compiled_statement_uses_the_processor(self, pycubrid_types):
        module = pycubrid_types("Set", "Multiset", "Sequence")
        stmt = select(column("id")).where(column("sq", SEQUENCE(Integer())) == [2, 1])
        compiled = stmt.compile(dialect=PyCubridDialect())
        (process,) = compiled._bind_processors.values()
        assert process([2, 1]) == module.Sequence([2, 1])

    def test_installed_pycubrid(self):
        typed = pytest.importorskip("pycubrid.types")
        dialect = PyCubridDialect()
        sequence = SEQUENCE(Integer()).bind_processor(dialect)
        set_ = SET(Integer()).bind_processor(dialect)
        multiset = MULTISET(Integer()).bind_processor(dialect)
        assert sequence is not None
        with pytest.raises(TypeError, match="SEQUENCE is ordered"):
            sequence({1, 2})
        if not hasattr(typed, "Sequence"):
            assert set_ is None and multiset is None
            return
        assert set_ is not None and multiset is not None
        assert sequence((2, 1, 2)) == typed.Sequence([2, 1, 2])
        assert set_(frozenset({1})) == typed.Set([1])
        assert multiset({1}) == typed.Multiset([1])

    @pytest.mark.parametrize("dialect_cls", [CubridDialect, PyCubridDialect])
    @pytest.mark.parametrize(("type_cls", "name"), _COLLECTION_CLASSES)
    def test_literal_rendering(self, dialect_cls, type_cls, name):
        col = column("c", type_cls(Integer()))
        dialect = dialect_cls()
        null = (
            select(column("id"))
            .where(col.is_(None))
            .compile(dialect=dialect, compile_kwargs={"literal_binds": True})
        )
        assert "IS NULL" in str(null)
        stmt = select(column("id")).where(col == [1, 2])
        with pytest.raises(exc.CompileError) as info:
            stmt.compile(dialect=dialect, compile_kwargs={"literal_binds": True})
        # SQLAlchemy wraps the processor's error; the cause names the type.
        assert f"{type_cls.__visit_name__} values cannot be rendered" in str(info.value.__cause__)
        processor = type_cls(Integer()).literal_processor(dialect)
        assert processor(None) == "NULL"


class TestRepr:
    """Test _StringType __repr__."""

    def test_char_repr(self):
        t = CHAR(length=50)
        r = repr(t)
        assert "CHAR" in r
        assert "50" in r

    def test_varchar_repr(self):
        t = VARCHAR(length=255)
        r = repr(t)
        assert "VARCHAR" in r
        assert "255" in r

    def test_nchar_repr(self):
        t = NCHAR(length=100)
        r = repr(t)
        assert "NCHAR" in r


class TestBindProcessor:
    """FLOAT and REAL bind_processor should return None (pass-through)."""

    def test_float_bind_processor(self):
        t = FLOAT()
        assert t.bind_processor(None) is None

    def test_real_bind_processor(self):
        t = REAL()
        assert t.bind_processor(None) is None

    def test_repr_exception_path_valueerror(self):
        """Test __repr__ when inspect.signature raises ValueError."""
        from unittest.mock import patch
        from sqlalchemy_cubrid.types import CHAR

        t = CHAR(length=50)
        with patch("sqlalchemy_cubrid.types.inspect.signature", side_effect=ValueError("no sig")):
            r = repr(t)
            assert "CHAR" in r
            # When signature fails, attributes=[] so no params shown
            assert r == "CHAR()"

    def test_repr_exception_path_typeerror(self):
        """Test __repr__ when inspect.signature raises TypeError."""
        from unittest.mock import patch
        from sqlalchemy_cubrid.types import VARCHAR

        t = VARCHAR(length=100)
        with patch("sqlalchemy_cubrid.types.inspect.signature", side_effect=TypeError("bad")):
            r = repr(t)
            assert "VARCHAR" in r
            assert r == "VARCHAR()"
