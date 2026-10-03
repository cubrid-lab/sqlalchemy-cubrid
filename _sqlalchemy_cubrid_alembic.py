# _sqlalchemy_cubrid_alembic.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Alembic plugin that registers ``CubridImpl`` (Alembic 1.18+, #595).

``pyproject.toml`` publishes this module in the ``alembic.plugins`` entry
point group.  Alembic 1.18 and later load that group while ``import alembic``
runs, before any ``env.py`` can look up an implementation, so the dialect
module no longer has to import Alembic itself on those versions.
``setup()`` imports :mod:`sqlalchemy_cubrid.alembic_impl`, whose
``CubridImpl`` registers itself under ``"cubrid"``.  Older Alembic releases
never read the group; :mod:`sqlalchemy_cubrid.dialect` imports
``alembic_impl`` for them.

Everything here runs inside ``import alembic`` for every Alembic user who has
sqlalchemy-cubrid installed, and Alembic does not guard the entry point load,
so this module must not raise:

* It is a top-level module that imports only the standard library.  Loading
  it never imports the ``sqlalchemy_cubrid`` package, whose import can fail
  (for example after an unsupported SQLAlchemy is installed over it).
* ``setup()`` imports ``sqlalchemy_cubrid.alembic_impl`` inside a ``try``
  and turns any failure into a warning instead of an exception.
* Alembic documents the entry point value as the plugin module, but Alembic
  1.18 through 1.20 run ``for mod in entrypoint.load()``, which fails with
  ``TypeError: 'module' object is not iterable`` for a plain module.  This
  module is therefore made iterable, yielding itself.  It keeps working if
  Alembic calls ``setup()`` on the loaded object directly, as documented.
"""

from __future__ import annotations

import importlib
import logging
import sys
import types
import warnings
from typing import Any, Iterator

log = logging.getLogger("sqlalchemy_cubrid.alembic_plugin")


def setup(plugin: Any = None) -> None:
    """Register ``CubridImpl`` with Alembic.

    Called by Alembic with its ``Plugin`` object, which is not used: the
    CUBRID implementation registers no autogenerate comparators.
    """
    try:
        importlib.import_module("sqlalchemy_cubrid.alembic_impl")
    except Exception as exc:
        msg = (
            "sqlalchemy-cubrid: could not register the CUBRID implementation "
            f"with Alembic ({type(exc).__name__}: {exc}); Alembic migrations "
            "against cubrid:// URLs will fail with KeyError: 'cubrid'."
        )
        # A warning filter set to "error" turns warn() into a raise, which
        # would break ``import alembic``; fall back to the logger.
        try:
            warnings.warn(msg, RuntimeWarning, stacklevel=2)
        except Exception:
            log.warning(msg)


class _IterablePluginModule(types.ModuleType):
    """Module type whose instances iterate over themselves.

    Alembic 1.18-1.20 iterate the loaded entry point object and pass each
    item to ``Plugin.setup_plugin_from_module()``; see the module docstring.
    """

    def __iter__(self) -> Iterator[types.ModuleType]:
        yield self


# Setting ``__class__`` to a ModuleType subclass is the documented way to
# customize a module object (Python data model, "Customizing module attribute
# access").
sys.modules[__name__].__class__ = _IterablePluginModule
