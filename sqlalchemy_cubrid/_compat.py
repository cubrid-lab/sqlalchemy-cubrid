from __future__ import annotations

from typing import Any

from sqlalchemy.sql import elements, visitors

# DBAPIModule was added in SQLAlchemy 2.1; fall back to Any for 2.0 compat.
try:
    from sqlalchemy.engine.interfaces import DBAPIModule
except ImportError:  # pragma: no cover — SA 2.0
    DBAPIModule = Any  # type: ignore[assignment,misc]

__all__ = [
    "DBAPIModule",
    "is_literal_value",
    "bind_with_type",
    "get_for_update_arg",
    "get_limit_clause",
    "get_offset_clause",
    "get_distinct",
]


def is_literal_value(value: Any) -> bool:
    """Check if value is a plain Python literal (not a SQL element or schema object)."""
    if isinstance(value, visitors.Visitable):
        return False
    if hasattr(value, "__clause_element__"):
        return False
    return True


def bind_with_type(element: elements.BindParameter[Any], type_: Any) -> elements.BindParameter[Any]:
    """Create a copy of *element* with *type_* overridden, preserving all internal state.

    Uses ``_clone()`` when available (SA 2.0–2.1); falls back to constructing
    a fresh ``BindParameter`` if the private ``_clone()`` API is removed or
    renamed in a future SA release (e.g. 2.2+).
    """
    try:
        cloned = element._clone()
    except AttributeError:
        # Fallback: construct a new BindParameter with same key/value/type.
        # This path only fires if SA removes _clone(); covered by canary CI.
        return elements.BindParameter(element.key, element.value, type_=type_, unique=True)  # type: ignore[call-arg]
    cloned.type = type_
    return cloned


def get_for_update_arg(select: Any) -> Any | None:
    return getattr(select, "_for_update_arg", None)


def get_limit_clause(select: Any) -> Any | None:
    return getattr(select, "_limit_clause", None)


def get_offset_clause(select: Any) -> Any | None:
    return getattr(select, "_offset_clause", None)


def get_distinct(select: Any) -> Any:
    return getattr(select, "_distinct", False)
