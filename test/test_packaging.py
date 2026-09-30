"""Packaging and entry point verification tests.

These tests verify that:
- All expected modules are importable
- All __all__ exports resolve to real objects
- Entry points are declared correctly in pyproject.toml
- py.typed marker exists
- Package version is consistent
"""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.resources
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy.engine.url import make_url

import sqlalchemy_cubrid


PACKAGE_DIR = Path(sqlalchemy_cubrid.__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"


def _read_pyproject() -> str:
    return PYPROJECT_PATH.read_text(encoding="utf-8")


def _entry_points_by_name(group: str) -> dict[str, importlib.metadata.EntryPoint]:
    return {
        entry_point.name: entry_point
        for entry_point in importlib.metadata.entry_points(group=group)
        if entry_point.name.startswith("cubrid")
    }


class TestModuleImports:
    @pytest.mark.parametrize(
        "module_name",
        [
            "sqlalchemy_cubrid.dialect",
            "sqlalchemy_cubrid.compiler",
            "sqlalchemy_cubrid.types",
            "sqlalchemy_cubrid.dml",
            "sqlalchemy_cubrid.base",
            "sqlalchemy_cubrid.pycubrid_dialect",
            "sqlalchemy_cubrid.aio_pycubrid_dialect",
            "sqlalchemy_cubrid.alembic_impl",
            "sqlalchemy_cubrid.alembic_plugin",
            "sqlalchemy_cubrid.trace",
            "sqlalchemy_cubrid.requirements",
        ],
    )
    def test_all_modules_importable(self, module_name: str):
        assert importlib.import_module(module_name) is not None


class TestExports:
    def test_all_exports_resolve(self):
        for export_name in sqlalchemy_cubrid.__all__:
            assert getattr(sqlalchemy_cubrid, export_name) is not None

    def test_version_consistency(self):
        # Version is now dynamic (derived from __version__), so check
        # importlib.metadata instead of parsing pyproject.toml.
        import importlib.metadata

        dist_version = importlib.metadata.version("sqlalchemy-cubrid")
        assert sqlalchemy_cubrid.__version__ == dist_version

    def test_py_typed_marker_exists(self):
        marker = importlib.resources.files("sqlalchemy_cubrid").joinpath("py.typed")
        assert marker.is_file()
        assert (PACKAGE_DIR / "py.typed").is_file()


class TestEntryPoints:
    @pytest.mark.parametrize(
        "entry_line",
        [
            'cubrid = "sqlalchemy_cubrid.dialect:CubridDialect"',
            '"cubrid.cubrid" = "sqlalchemy_cubrid.dialect:CubridDialect"',
            '"cubrid.cubriddb" = "sqlalchemy_cubrid.dialect:CubridDialect"',
            '"cubrid.pycubrid" = "sqlalchemy_cubrid.pycubrid_dialect:PyCubridDialect"',
            (
                '"cubrid.aiopycubrid" = '
                '"sqlalchemy_cubrid.aio_pycubrid_dialect:PyCubridAsyncDialect"'
            ),
        ],
    )
    def test_sqlalchemy_dialect_entry_points_declared(self, entry_line: str):
        pyproject_text = _read_pyproject()

        assert '[project.entry-points."sqlalchemy.dialects"]' in pyproject_text
        assert entry_line in pyproject_text

    def test_no_alembic_ddl_entry_point_declared(self):
        # Alembic never reads an ``alembic.ddl`` group; CubridImpl is registered
        # by the alembic.plugins entry point or the dialect module (#504, #595).
        assert '[project.entry-points."alembic.ddl"]' not in _read_pyproject()

    def test_alembic_plugin_entry_point_declared(self):
        # Alembic 1.18+ loads this group on import and registers CubridImpl (#595).
        pyproject_text = _read_pyproject()

        assert '[project.entry-points."alembic.plugins"]' in pyproject_text
        assert 'sqlalchemy_cubrid = "sqlalchemy_cubrid.alembic_plugin"' in pyproject_text

    @pytest.mark.parametrize(
        ("entry_name", "expected_module", "expected_class_name"),
        [
            ("cubrid", "sqlalchemy_cubrid.dialect", "CubridDialect"),
            ("cubrid.cubrid", "sqlalchemy_cubrid.dialect", "CubridDialect"),
            ("cubrid.cubriddb", "sqlalchemy_cubrid.dialect", "CubridDialect"),
            ("cubrid.pycubrid", "sqlalchemy_cubrid.pycubrid_dialect", "PyCubridDialect"),
            (
                "cubrid.aiopycubrid",
                "sqlalchemy_cubrid.aio_pycubrid_dialect",
                "PyCubridAsyncDialect",
            ),
        ],
    )
    def test_entry_points_loadable_via_importlib(
        self,
        entry_name: str,
        expected_module: str,
        expected_class_name: str,
    ):
        entry_points = _entry_points_by_name("sqlalchemy.dialects")

        assert entry_name in entry_points

        loaded = cast(type[object], entry_points[entry_name].load())

        assert loaded.__module__ == expected_module
        assert loaded.__name__ == expected_class_name

    @pytest.mark.parametrize(
        "entry_name",
        ["cubrid", "cubrid.cubrid", "cubrid.cubriddb", "cubrid.pycubrid", "cubrid.aiopycubrid"],
    )
    def test_every_dialect_entry_point_resolves_alembic_impl(self, entry_name: str):
        # Alembic looks up its impl by ``dialect.name``; loading any CUBRID
        # dialect must leave CubridImpl registered under that name (#504).
        from alembic.ddl.impl import _impls

        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        loaded = cast(type[object], _entry_points_by_name("sqlalchemy.dialects")[entry_name].load())

        assert getattr(loaded, "name") == "cubrid"
        assert _impls[getattr(loaded, "name")] is CubridImpl


class TestDialectResolution:
    def test_async_engine_creation_without_database(self):
        import asyncio

        from sqlalchemy.ext.asyncio import create_async_engine

        pytest.importorskip("pycubrid")
        engine = create_async_engine("cubrid+aiopycubrid://dba@localhost:33000/testdb")

        assert engine.dialect.is_async
        asyncio.run(engine.dispose())

    @pytest.mark.parametrize(
        ("url", "expected_module", "expected_class_name"),
        [
            ("cubrid://host/db", "sqlalchemy_cubrid.dialect", "CubridDialect"),
            ("cubrid+cubrid://host/db", "sqlalchemy_cubrid.dialect", "CubridDialect"),
            ("cubrid+cubriddb://host/db", "sqlalchemy_cubrid.dialect", "CubridDialect"),
            (
                "cubrid+pycubrid://host/db",
                "sqlalchemy_cubrid.pycubrid_dialect",
                "PyCubridDialect",
            ),
            (
                "cubrid+aiopycubrid://host/db",
                "sqlalchemy_cubrid.aio_pycubrid_dialect",
                "PyCubridAsyncDialect",
            ),
        ],
    )
    def test_dialect_url_resolution(self, url: str, expected_module: str, expected_class_name: str):
        dialect = make_url(url).get_dialect()

        assert dialect.__module__ == expected_module
        assert dialect.__name__ == expected_class_name


class TestBareDefaultIsCubriddb:
    """The bare ``cubrid://`` URL binds the legacy CUBRIDdb driver and does not warn."""

    def test_bare_url_resolves_to_cubriddb_dialect(self):
        dialect_cls = make_url("cubrid://host/db").get_dialect()

        assert dialect_cls.__module__ == "sqlalchemy_cubrid.dialect"
        assert dialect_cls.__name__ == "CubridDialect"

    def test_bare_url_dialect_does_not_warn(self):
        import warnings

        dialect_cls = make_url("cubrid://host/db").get_dialect()
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            dialect_cls()

    def test_explicit_legacy_dialect_does_not_warn(self):
        import warnings

        from sqlalchemy_cubrid.dialect import CubridDialect

        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            CubridDialect()

    def test_explicit_pycubrid_dialect_does_not_warn(self):
        import warnings

        from sqlalchemy_cubrid.pycubrid_dialect import PyCubridDialect

        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            PyCubridDialect()
