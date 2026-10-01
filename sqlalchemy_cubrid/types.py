# sqlalchemy_cubrid/types.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""CUBRID-specific SQLAlchemy type definitions.

See: https://www.cubrid.org/manual/en/11.0/sql/datatype.html
"""

from __future__ import annotations

import inspect
from importlib import import_module
from typing import Any, Callable, Sequence

from sqlalchemy import exc
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.sql import sqltypes


# ---------------------------------------------------------------------------
# Base Mixins
# ---------------------------------------------------------------------------


class _NumericType:
    """Base for CUBRID numeric types."""

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)


class _FloatType(_NumericType, sqltypes.Float[Any]):  # pyright: ignore[reportUnsafeMultipleInheritance]
    def __init__(self, precision: int | None = None, **kw: Any) -> None:
        super().__init__(precision=precision, **kw)


class _IntegerType(_NumericType, sqltypes.Integer):
    def __init__(self, display_width: int | None = None, **kw: Any) -> None:
        self.display_width = display_width
        super().__init__(**kw)


class _StringType(sqltypes.String):
    """Base for CUBRID string types."""

    def __init__(
        self,
        national: bool = False,
        values: Sequence[Any] | None = None,
        **kw: Any,
    ) -> None:
        self.national = national
        self.values = values
        super().__init__(**kw)

    def __repr__(self) -> str:
        try:
            sig = inspect.signature(self.__class__.__init__)
            attributes = [p.name for p in sig.parameters.values() if p.name != "self"]
        except (ValueError, TypeError):
            attributes = []

        params = {}
        for attr in attributes:
            val = getattr(self, attr, None)
            if val is not None and val is not False:
                params[attr] = val

        return "{}({})".format(
            self.__class__.__name__,
            ", ".join(f"{k}={v!r}" for k, v in params.items()),
        )


# ---------------------------------------------------------------------------
# Numeric Types
# ---------------------------------------------------------------------------


class SMALLINT(_IntegerType, sqltypes.SMALLINT):
    """CUBRID SMALLINT type."""

    __visit_name__ = "SMALLINT"


class BIGINT(_IntegerType, sqltypes.BIGINT):
    """CUBRID BIGINT type."""

    __visit_name__ = "BIGINT"


class NUMERIC(_NumericType, sqltypes.NUMERIC[Any]):  # pyright: ignore[reportUnsafeMultipleInheritance]
    """CUBRID NUMERIC type."""

    __visit_name__ = "NUMERIC"
    render_bind_cast = True

    def __init__(self, precision: int | None = None, scale: int | None = None, **kw: Any) -> None:
        """Construct a NUMERIC.

        :param precision: Total digits in this number.  If scale and precision
          are both None, values are stored to limits allowed by the server.
        :param scale: The number of digits after the decimal point.
        """
        super().__init__(precision=precision, scale=scale, **kw)


class DECIMAL(_NumericType, sqltypes.DECIMAL[Any]):  # pyright: ignore[reportUnsafeMultipleInheritance]
    """CUBRID DECIMAL type."""

    __visit_name__ = "DECIMAL"
    render_bind_cast = True

    def __init__(self, precision: int | None = None, scale: int | None = None, **kw: Any) -> None:
        """Construct a DECIMAL.

        :param precision: Total digits in this number.  If scale and precision
          are both None, values are stored to limits allowed by the server.
          (range from 1 thru 38)
        :param scale: The number of digits following the decimal point.
        """
        super().__init__(precision=precision, scale=scale, **kw)


class FLOAT(_FloatType, sqltypes.FLOAT[Any]):  # pyright: ignore[reportUnsafeMultipleInheritance]
    """CUBRID FLOAT type."""

    __visit_name__ = "FLOAT"

    def __init__(self, precision: int | None = 7, **kw: Any) -> None:
        """Construct a FLOAT.

        :param precision: Defaults to 7.  Total digits in this number.
          (range from 1 thru 38)
        """
        super().__init__(precision=precision, **kw)

    def bind_processor(self, dialect: Any) -> None:
        return None


class REAL(_FloatType, sqltypes.FLOAT[Any]):  # pyright: ignore[reportUnsafeMultipleInheritance]
    """CUBRID REAL type."""

    __visit_name__ = "REAL"

    def __init__(self, precision: int | None = None, **kw: Any) -> None:
        """Construct a REAL.

        :param precision: Total digits in this number.
        """
        super().__init__(precision=precision, **kw)

    def bind_processor(self, dialect: Any) -> None:
        return None


class DOUBLE(_FloatType):
    """CUBRID DOUBLE type."""

    __visit_name__ = "DOUBLE"


class DOUBLE_PRECISION(_FloatType):
    """CUBRID DOUBLE PRECISION type."""

    __visit_name__ = "DOUBLE_PRECISION"


# ---------------------------------------------------------------------------
# Bit String Types
# ---------------------------------------------------------------------------


class BIT(sqltypes.TypeEngine[Any]):
    """CUBRID BIT type."""

    __visit_name__ = "BIT"

    def __init__(self, length: int | None = 1, varying: bool = False) -> None:
        """Construct a BIT.

        :param length: Defaults to 1.  Optional, number of bits.
        :param varying: If True, use BIT VARYING.
        """
        self.length: int | None
        if not varying:
            # ``length is None`` means unspecified and defaults to 1.
            # An explicit ``length=0`` is kept so the compiler can reject it
            # instead of silently coercing to BIT(1).
            self.length = 1 if length is None else length
        else:
            self.length = length  # BIT VARYING can be unlimited-length
        self.varying = varying


# ---------------------------------------------------------------------------
# Character String Types
# ---------------------------------------------------------------------------


class CHAR(_StringType, sqltypes.CHAR):  # pyright: ignore[reportUnsafeMultipleInheritance]
    """CUBRID CHAR type, for fixed-length character data."""

    __visit_name__ = "CHAR"

    def __init__(self, length: int | None = None, **kwargs: Any) -> None:
        """Construct a CHAR.

        :param length: The number of characters.
        """
        super().__init__(length=length, **kwargs)


class VARCHAR(_StringType, sqltypes.VARCHAR):  # pyright: ignore[reportUnsafeMultipleInheritance]
    """CUBRID VARCHAR type, for variable-length character data."""

    __visit_name__ = "VARCHAR"

    def __init__(self, length: int | None = None, **kwargs: Any) -> None:
        """Construct a VARCHAR.

        :param length: The number of characters.
        """
        super().__init__(length=length, **kwargs)


class NCHAR(_StringType, sqltypes.NCHAR):  # pyright: ignore[reportUnsafeMultipleInheritance]
    """CUBRID NCHAR type.

    For fixed-length character data in the server's configured national
    character set.
    """

    __visit_name__ = "NCHAR"

    def __init__(self, length: int | None = None, **kwargs: Any) -> None:
        """Construct a NCHAR.

        :param length: The number of characters.
        """
        kwargs["national"] = True
        super().__init__(length=length, **kwargs)


class NVARCHAR(_StringType, sqltypes.NVARCHAR):  # pyright: ignore[reportUnsafeMultipleInheritance]
    """CUBRID NVARCHAR type.

    For variable-length character data in the server's configured national
    character set.
    """

    __visit_name__ = "NVARCHAR"

    def __init__(self, length: int | None = None, **kwargs: Any) -> None:
        """Construct a NVARCHAR.

        :param length: The number of characters.
        """
        kwargs["national"] = True
        super().__init__(length=length, **kwargs)


class STRING(_StringType):
    """CUBRID STRING type.

    STRING is a variable-length character string data type.
    STRING is the same as the VARCHAR with the length specified to the maximum value.
    That is, STRING and VARCHAR(1,073,741,823) have the same value.
    """

    __visit_name__ = "STRING"

    def __init__(self, length: int | None = None, national: bool = False, **kwargs: Any) -> None:
        super().__init__(length=length, national=national, **kwargs)


# ---------------------------------------------------------------------------
# Enum Type
# ---------------------------------------------------------------------------


class ENUM(sqltypes.Enum):
    """CUBRID native ENUM type.

    CUBRID supports a native ``ENUM('a', 'b', ...)`` column type across all
    versions the dialect targets (verified live on 10.2, 11.0, and 11.4).
    Plain ``sa.Enum("a", "b")`` maps to this type via the dialect colspecs,
    so native ENUM DDL is emitted by default. ``native_enum=False`` honours
    the SQLAlchemy contract and emits ``VARCHAR(n)`` instead (n sized to the
    longest element).

    Reflected ``ENUM(...)`` columns round-trip through ``SHOW COLUMNS``,
    which reports the full element list.
    """

    __visit_name__ = "ENUM"


# ---------------------------------------------------------------------------
# LOB Types
# ---------------------------------------------------------------------------


class BLOB(sqltypes.LargeBinary):
    """CUBRID BLOB type."""

    __visit_name__ = "BLOB"


class CLOB(sqltypes.Text):
    """CUBRID CLOB type."""

    __visit_name__ = "CLOB"


# ---------------------------------------------------------------------------
# Collection Types
# ---------------------------------------------------------------------------


#: Python values the collection bind processors wrap in a pycubrid typed
#: collection. Anything else (``None``, an already typed value, a string, ...)
#: goes to the driver unchanged.
_PLAIN_COLLECTIONS = (list, tuple, set, frozenset)

#: Unordered Python collections, which a SEQUENCE (ordered) column rejects.
_UNORDERED_COLLECTIONS = (set, frozenset)


def _pycubrid_collection_class(name: str) -> Any | None:
    """Return ``pycubrid.types.<name>`` when the installed pycubrid has it.

    pycubrid added ``Set``, ``Multiset`` and ``Sequence`` parameters for
    ordinary cursors in cubrid-lab/pycubrid#567; older releases (including the
    1.8.0 floor) do not define them and reject collection parameters.
    """
    try:
        module = import_module("pycubrid.types")
    except ImportError:
        return None
    return getattr(module, name, None)


def _is_pycubrid_dialect(dialect: Dialect) -> bool:
    """True for ``cubrid+pycubrid://`` and ``cubrid+aiopycubrid://``.

    ``PyCubridDialect`` sets the marker (the async dialect inherits it); a
    class attribute avoids importing the dialect module, which imports this one.
    """
    return getattr(dialect, "_cubrid_pycubrid_dbapi", False) is True


class _CollectionType(_StringType):
    """Base for the CUBRID collection types.

    On the pycubrid drivers, when the installed pycubrid provides typed
    collection parameters, a ``list``/``tuple`` value (and, except for
    ``SEQUENCE``, a ``set``/``frozenset``) is bound as the matching typed
    collection (``SET{...}``, ``MULTISET{...}``, ``SEQUENCE{...}``). Values are
    returned as the driver decodes them; see docs/TYPES.md ("Collection
    values").
    """

    #: Name of the matching class in ``pycubrid.types``.
    _pycubrid_name: str

    #: Whether the collection keeps its elements' order (only ``SEQUENCE``).
    _ordered: bool = False

    def __init__(self, *values: Any, **kw: Any) -> None:
        """Construct the type; *values* are the element types for the DDL."""
        self._ddl_values = values
        super().__init__(**kw)

    def bind_processor(self, dialect: Dialect) -> Callable[[Any], Any] | None:
        """Wrap plain collections in the pycubrid typed collection.

        A ``set``/``frozenset`` bound to a ``SEQUENCE`` raises ``TypeError`` on
        the pycubrid drivers whatever the pycubrid version: it has no order.
        """
        if not _is_pycubrid_dialect(dialect):
            return None
        typed = _pycubrid_collection_class(self._pycubrid_name)
        if typed is None and not self._ordered:
            return None
        visit_name = self.__visit_name__

        def process(value: Any) -> Any:
            if self._ordered and isinstance(value, _UNORDERED_COLLECTIONS):
                raise TypeError(
                    f"{visit_name} is ordered; pass a list or tuple, not a {type(value).__name__}"
                )
            if typed is not None and isinstance(value, _PLAIN_COLLECTIONS):
                return typed(value)
            return value

        return process

    def literal_processor(self, dialect: Dialect) -> Callable[[Any], str]:
        """Render ``NULL``; reject collection values as inline literals."""
        visit_name = self.__visit_name__

        def process(value: Any) -> str:
            if value is None:
                return "NULL"
            raise exc.CompileError(
                f"{visit_name} values cannot be rendered as inline literals "
                "(literal_binds / literal_execute); bind them as parameters"
            )

        return process


class SET(_CollectionType):
    """CUBRID SET type."""

    __visit_name__ = "SET"
    _pycubrid_name = "Set"


class MULTISET(_CollectionType):
    """CUBRID MULTISET type."""

    __visit_name__ = "MULTISET"
    _pycubrid_name = "Multiset"


class SEQUENCE(_CollectionType):
    """CUBRID SEQUENCE type."""

    __visit_name__ = "SEQUENCE"
    _pycubrid_name = "Sequence"
    _ordered = True


# ---------------------------------------------------------------------------
# Timezone-aware Date/Time Types
# ---------------------------------------------------------------------------


class TIMESTAMPTZ(sqltypes.TIMESTAMP):
    """CUBRID TIMESTAMPTZ — timestamp with explicit timezone."""

    __visit_name__ = "TIMESTAMPTZ"
    timezone = True

    def __init__(self, **kwargs: bool) -> None:
        kwargs.pop("timezone", None)  # Discard it if passed in kwargs
        super().__init__(timezone=True, **kwargs)


class TIMESTAMPLTZ(sqltypes.TIMESTAMP):
    """CUBRID TIMESTAMPLTZ — timestamp with local timezone."""

    __visit_name__ = "TIMESTAMPLTZ"
    timezone = True

    def __init__(self, **kwargs: bool) -> None:
        kwargs.pop("timezone", None)  # Discard it if passed in kwargs
        super().__init__(timezone=True, **kwargs)


class DATETIMETZ(sqltypes.DATETIME):
    """CUBRID DATETIMETZ — datetime with explicit timezone."""

    __visit_name__ = "DATETIMETZ"
    timezone = True

    def __init__(self, **kwargs: bool) -> None:
        kwargs.pop("timezone", None)  # Discard it if passed in kwargs
        super().__init__(timezone=True, **kwargs)


class DATETIMELTZ(sqltypes.DATETIME):
    """CUBRID DATETIMELTZ — datetime with local timezone."""

    __visit_name__ = "DATETIMELTZ"
    timezone = True

    def __init__(self, **kwargs: bool) -> None:
        kwargs.pop("timezone", None)  # Discard it if passed in kwargs
        super().__init__(timezone=True, **kwargs)


# ---------------------------------------------------------------------------
# Monetary Type
# ---------------------------------------------------------------------------


class MONETARY(sqltypes.TypeEngine[Any]):
    """CUBRID MONETARY type.

    Stores monetary values with currency.  Internally represented as a
    DOUBLE with an associated currency code.
    """

    __visit_name__ = "MONETARY"


# ---------------------------------------------------------------------------
# Object Type
# ---------------------------------------------------------------------------


class OBJECT(sqltypes.TypeEngine[Any]):
    """CUBRID OBJECT type.

    Represents a reference to another CUBRID class instance (OID).
    This is a CUBRID-specific type with no direct equivalent in other databases.
    """

    __visit_name__ = "OBJECT"


# ---------------------------------------------------------------------------
# JSON Type (CUBRID 10.2+)
# ---------------------------------------------------------------------------


class _FormatTypeMixin:
    """Mixin for formatting JSON path index/path values for bind parameters."""

    def _format_value(self, value: Any) -> str:
        raise NotImplementedError()

    def bind_processor(self, dialect: Any) -> Any:
        super_proc = self.string_bind_processor(dialect)  # type: ignore[attr-defined]  # noqa: E501

        def process(value: Any) -> Any:
            if value is None:
                return None
            value = self._format_value(value)
            if super_proc:
                value = super_proc(value)
            return value

        return process

    def literal_processor(self, dialect: Any) -> Any:
        super_proc = self.string_literal_processor(dialect)  # type: ignore[attr-defined]  # noqa: E501

        def process(value: Any) -> str | None:
            if value is None:
                return None
            value = self._format_value(value)
            if super_proc:
                value = super_proc(value)
            return str(value)

        return process


class JSONIndexType(_FormatTypeMixin, sqltypes.JSON.JSONIndexType):
    """CUBRID JSON index type for single-key access.

    Converts Python index values to CUBRID JSON path syntax:
    - Integer index: ``$[0]``
    - String key: ``$."key"``
    """

    def _format_value(self, value: Any) -> str:
        if isinstance(value, int):
            return "$[%s]" % value
        else:
            return '$."%s"' % str(value).replace('"', '""')


class JSONPathType(_FormatTypeMixin, sqltypes.JSON.JSONPathType):
    """CUBRID JSON path type for multi-level access.

    Converts Python tuple paths to CUBRID JSON path syntax:
    - ``("a", 1, "b")`` → ``$."a"[1]."b"``
    """

    def _format_value(self, value: Any) -> str:
        return "$%s" % (
            "".join(
                "[%s]" % elem if isinstance(elem, int) else '."%s"' % str(elem).replace('"', '""')
                for elem in value
            )
        )


class JSON(sqltypes.JSON):
    """CUBRID JSON type.

    CUBRID supports JSON as of version 10.2 (RFC 7159 compliant).

    :class:`_cubrid.JSON` is used automatically whenever the base
    :class:`_types.JSON` datatype is used against a CUBRID backend.

    The :class:`.cubrid.JSON` type supports persistence of JSON values
    as well as the core index operations provided by :class:`_types.JSON`
    datatype, by adapting the operations to render the ``JSON_EXTRACT``
    function at the database level.

    .. seealso::

        :class:`_types.JSON` - main documentation for the generic
        cross-platform JSON datatype.

    .. versionadded:: 1.2.0
    """

    __visit_name__ = "JSON"
