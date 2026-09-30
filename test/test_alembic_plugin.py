# test/test_alembic_plugin.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""``CubridImpl`` registration through the ``alembic.plugins`` entry point (#595).

Alembic 1.18+ loads the ``alembic.plugins`` group while ``import alembic``
runs, so the dialect no longer imports Alembic on those versions; Alembic
1.7.2-1.17 keep the eager import in ``sqlalchemy_cubrid.dialect``.  The plugin
runs inside every ``import alembic`` on a machine with sqlalchemy-cubrid
installed, so these tests also check that it cannot break that import, with
both the loader shape Alembic 1.18-1.20 use (``for mod in
entrypoint.load()``) and the documented one (``entrypoint.load().setup()``).
"""

from __future__ import annotations

import importlib
import importlib.metadata
import logging
import os
import subprocess
import sys
import types
import warnings
from typing import Any

import pytest

import sqlalchemy_cubrid.alembic_plugin as alembic_plugin
from sqlalchemy_cubrid import dialect as cubrid_dialect

_PLUGIN_VALUE = "sqlalchemy_cubrid.alembic_plugin"


def _installed_entry_point() -> importlib.metadata.EntryPoint | None:
    for ep in importlib.metadata.entry_points(group="alembic.plugins"):
        if ep.value == _PLUGIN_VALUE:
            return ep
    return None


def _alembic_version() -> tuple[int, int] | None:
    try:
        major, minor = importlib.metadata.version("alembic").split(".")[:2]
    except importlib.metadata.PackageNotFoundError:
        return None
    return int(major), int(minor)


_ALEMBIC = _alembic_version()
_HAS_PLUGINS = _ALEMBIC is not None and _ALEMBIC >= (1, 18)
_needs_install = pytest.mark.skipif(
    _installed_entry_point() is None,
    reason="sqlalchemy-cubrid is not installed with its alembic.plugins entry point "
    "(pip install -e .)",
)


def _run(script: str, *flags: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    return subprocess.run(
        [sys.executable, *flags, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


class TestPluginModule:
    def test_module_iterates_to_itself(self) -> None:
        # Alembic 1.18-1.20 iterate the loaded entry point object.
        assert isinstance(alembic_plugin, types.ModuleType)
        assert list(alembic_plugin) == [alembic_plugin]

    def test_setup_registers_cubrid_impl(self) -> None:
        pytest.importorskip("alembic")
        from alembic.ddl.impl import _impls

        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        alembic_plugin.setup(object())

        assert _impls["cubrid"] is CubridImpl

    def test_setup_failure_warns_instead_of_raising(self, monkeypatch: Any) -> None:
        # ``None`` in sys.modules makes the import raise ImportError.
        monkeypatch.setitem(sys.modules, "sqlalchemy_cubrid.alembic_impl", None)
        monkeypatch.delattr("sqlalchemy_cubrid.alembic_impl", raising=False)

        with pytest.warns(RuntimeWarning, match="could not register the CUBRID implementation"):
            alembic_plugin.setup(object())

    def test_setup_failure_logs_under_error_warning_filter(
        self, monkeypatch: Any, caplog: Any
    ) -> None:
        monkeypatch.setitem(sys.modules, "sqlalchemy_cubrid.alembic_impl", None)
        monkeypatch.delattr("sqlalchemy_cubrid.alembic_impl", raising=False)

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            with caplog.at_level(logging.WARNING, logger="sqlalchemy_cubrid.alembic_plugin"):
                alembic_plugin.setup(object())

        assert "could not register the CUBRID implementation" in caplog.text


class TestEntryPoint:
    @_needs_install
    def test_entry_point_loads_this_module(self) -> None:
        ep = _installed_entry_point()
        assert ep is not None
        assert ep.name == "sqlalchemy_cubrid"
        assert ep.load() is alembic_plugin

    @_needs_install
    @pytest.mark.skipif(not _HAS_PLUGINS, reason="alembic.plugins needs Alembic 1.18+")
    @pytest.mark.parametrize("shape", ["iterate", "documented"])
    def test_both_loader_shapes_work(self, shape: str) -> None:
        # ``iterate`` is Alembic 1.18-1.20's ``_setup()``; ``documented`` is what
        # the Alembic docs describe.  Either must set the plugin up.
        from alembic.runtime.plugins import Plugin

        ep = _installed_entry_point()
        assert ep is not None
        name = f"sqlalchemy_cubrid_test_{shape}"
        try:
            if shape == "iterate":
                for mod in ep.load():
                    Plugin.setup_plugin_from_module(mod, name)
            else:
                Plugin.setup_plugin_from_module(ep.load(), name)
        finally:
            from alembic.runtime import plugins

            plugins._all_plugins.pop(name, None)

    @_needs_install
    @pytest.mark.skipif(not _HAS_PLUGINS, reason="alembic.plugins needs Alembic 1.18+")
    def test_import_alembic_registers_without_dialect(self) -> None:
        # A fresh ``import alembic`` under ``-W error`` must succeed and register
        # CubridImpl through the plugin alone, without loading the dialect.
        result = _run(
            "import sys, alembic\n"
            "from alembic.ddl.impl import _impls\n"
            "from alembic.runtime.plugins import _all_plugins\n"
            "print(_impls['cubrid'].__module__, 'sqlalchemy_cubrid' in _all_plugins,"
            " 'sqlalchemy_cubrid.dialect' in sys.modules)\n",
            "-W",
            "error",
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout.split() == ["sqlalchemy_cubrid.alembic_impl", "True", "False"]


class TestDialectFallback:
    """``sqlalchemy_cubrid.dialect`` imports Alembic only when the plugin cannot."""

    @_needs_install
    @pytest.mark.skipif(_ALEMBIC is None, reason="Alembic is not installed")
    def test_dialect_imports_alembic_only_without_plugin_support(self) -> None:
        # Regression test for #595: with Alembic 1.18+ loading any CUBRID
        # dialect leaves Alembic unimported and logs none of its INFO lines
        # (#561); older Alembic keeps the eager import.
        result = _run(
            "import logging, sys\n"
            "logging.basicConfig(level=logging.INFO)\n"
            "from sqlalchemy.dialects import registry\n"
            "for n in ('cubrid', 'cubrid.pycubrid', 'cubrid.aiopycubrid'):\n"
            "    registry.load(n)\n"
            "print('alembic' in sys.modules, 'sqlalchemy_cubrid.alembic_impl' in sys.modules)\n"
        )

        assert result.returncode == 0, result.stderr
        if _HAS_PLUGINS:
            assert result.stdout.split() == ["False", "False"]
            assert "setup plugin" not in result.stderr
        else:
            assert result.stdout.split() == ["True", "True"]

    def test_already_imported_alembic_uses_eager_import(self, monkeypatch: Any) -> None:
        monkeypatch.setitem(sys.modules, "alembic", types.ModuleType("alembic"))

        assert cubrid_dialect._alembic_loads_cubrid_plugin() is False

    @pytest.mark.parametrize("version", ["1.7.2", "1.17.2", "not-a-version"])
    def test_old_or_unknown_alembic_uses_eager_import(self, monkeypatch: Any, version: str) -> None:
        monkeypatch.delitem(sys.modules, "alembic", raising=False)
        monkeypatch.setattr(importlib.metadata, "version", lambda name: version)

        assert cubrid_dialect._alembic_loads_cubrid_plugin() is False

    def test_missing_alembic_uses_eager_import(self, monkeypatch: Any) -> None:
        def missing(name: str) -> str:
            raise importlib.metadata.PackageNotFoundError(name)

        monkeypatch.delitem(sys.modules, "alembic", raising=False)
        monkeypatch.setattr(importlib.metadata, "version", missing)

        assert cubrid_dialect._alembic_loads_cubrid_plugin() is False

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(_PLUGIN_VALUE, True), ("other.module", False), (None, False)],
        ids=["declared", "other-value", "not-installed"],
    )
    def test_new_alembic_uses_plugin_only_when_declared(
        self, monkeypatch: Any, value: str | None, expected: bool
    ) -> None:
        eps = (
            [] if value is None else [importlib.metadata.EntryPoint("x", value, "alembic.plugins")]
        )
        dist = types.SimpleNamespace(entry_points=eps)
        monkeypatch.delitem(sys.modules, "alembic", raising=False)
        monkeypatch.setattr(importlib.metadata, "version", lambda name: "1.18.0")
        monkeypatch.setattr(importlib.metadata, "distribution", lambda name: dist)

        assert cubrid_dialect._alembic_loads_cubrid_plugin() is expected
