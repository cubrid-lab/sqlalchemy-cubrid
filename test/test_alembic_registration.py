# test/test_alembic_registration.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Alembic finds ``CubridImpl`` with an unmodified ``env.py`` (#504).

Alembic resolves its migration implementation with
``_impls[dialect.name]`` and raises ``KeyError: 'cubrid'`` when nothing has
registered one.  Other tests import ``sqlalchemy_cubrid.alembic_impl`` in
process, which would hide a missing registration, so these tests run the
``alembic`` command line in a fresh interpreter against a project made by
``alembic init`` whose ``env.py`` never mentions ``sqlalchemy_cubrid``.

Offline (``--sql``) mode needs no database: ``context.configure(url=...)``
builds the dialect from the URL and looks up the impl exactly as online mode
does.  The online tests need a live CUBRID and ``CUBRID_TEST_URL``: they run
the default template with a synchronous URL, and Alembic's async template
(``alembic init -t async``) with ``cubrid+aiopycubrid://``.
"""

from __future__ import annotations

import importlib.metadata
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

pytest.importorskip("alembic")

if not any(
    ep.name == "cubrid" for ep in importlib.metadata.entry_points(group="sqlalchemy.dialects")
):
    pytest.skip(
        "sqlalchemy-cubrid is not installed (pip install -e .), so a subprocess "
        "cannot resolve the cubrid:// dialect",
        allow_module_level=True,
    )


def _alembic(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    # A clean interpreter: nothing from this pytest process (including an
    # already-imported alembic_impl) can leak into the migration run.
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _make_project(tmp_path: Path, url: str, table: str, template: str = "generic") -> Path:
    project = tmp_path / "project"
    project.mkdir()
    init = _alembic(project, "init", "-t", template, "migrations")
    assert init.returncode == 0, init.stderr

    ini = project / "alembic.ini"
    lines = ini.read_text(encoding="utf-8").splitlines()
    lines = [f"sqlalchemy.url = {url}" if ln.startswith("sqlalchemy.url") else ln for ln in lines]
    ini.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # The generated env.py must stay untouched: no CUBRID import anywhere.
    env_py = (project / "migrations" / "env.py").read_text(encoding="utf-8")
    assert "sqlalchemy_cubrid" not in env_py
    assert "cubrid" not in env_py.lower()

    versions = project / "migrations" / "versions"
    versions.mkdir(exist_ok=True)
    (versions / "0001_create.py").write_text(
        f'''"""create {table}"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "{table}",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(50), nullable=False),
    )
    op.alter_column("{table}", "name", new_column_name="label", existing_type=sa.String(50))


def downgrade():
    op.drop_table("{table}")
''',
        encoding="utf-8",
    )
    return project


@pytest.mark.parametrize(
    "scheme",
    ["cubrid", "cubrid+cubriddb", "cubrid+pycubrid", "cubrid+aiopycubrid"],
)
def test_offline_upgrade_with_default_env_py(tmp_path: Path, scheme: str) -> None:
    project = _make_project(tmp_path, f"{scheme}://dba@localhost:33000/testdb", "sa504_t")

    result = _alembic(project, "upgrade", "head", "--sql")

    assert "KeyError" not in result.stderr, result.stderr
    assert result.returncode == 0, result.stderr
    assert "CREATE TABLE sa504_t" in result.stdout
    # CubridImpl-specific rendering proves the CUBRID impl, not a generic
    # fallback, handled the migration.
    assert "RENAME COLUMN name TO label" in result.stdout
    # transactional_ddl is True, but CUBRID has no BEGIN statement (#503).
    lines = [ln.strip() for ln in result.stdout.splitlines()]
    assert "BEGIN;" not in lines
    assert "COMMIT;" in lines


# Loads every CUBRID dialect in a fresh interpreter after ``setup`` has shaped
# how ``alembic`` imports, and reports the warnings raised while loading.
_LOAD_DIALECTS = """
import json, sys, warnings
{setup}
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    from sqlalchemy.dialects import registry
    names = [registry.load(n).name for n in ("cubrid", "cubrid.pycubrid", "cubrid.aiopycubrid")]
print(json.dumps({{
    "names": names,
    "impl_loaded": "sqlalchemy_cubrid.alembic_impl" in sys.modules,
    "warnings": [
        [w.category.__name__, str(w.message)]
        for w in caught
        if "sqlalchemy-cubrid" in str(w.message) or "Alembic" in str(w.message)
    ],
}}))
"""

# Alembic 1.7.0/1.7.1 fail on SQLAlchemy 2.x with NameError while executing
# ``alembic/__init__.py``; this finder reproduces that without installing them.
_BROKEN_ALEMBIC = """
import importlib.abc, importlib.machinery

class _BrokenLoader(importlib.abc.Loader):
    def create_module(self, spec):
        return None

    def exec_module(self, module):
        raise NameError("name 'TextClause' is not defined")

class _BrokenFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name == "alembic":
            return importlib.machinery.ModuleSpec(name, _BrokenLoader())
        return None

sys.meta_path.insert(0, _BrokenFinder())

# Report the broken versions, so the dialect takes the eager-import path it
# uses for Alembic < 1.18 (#595).
import importlib.metadata
_version = importlib.metadata.version
importlib.metadata.version = lambda name: "1.7.1" if name == "alembic" else _version(name)
"""

# ``None`` in sys.modules makes ``import alembic`` raise ModuleNotFoundError,
# exactly as when Alembic is not installed.
_NO_ALEMBIC = 'sys.modules["alembic"] = None'


def _load_dialects(setup: str) -> dict[str, object]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    result = subprocess.run(
        [sys.executable, "-c", _LOAD_DIALECTS.format(setup=setup)],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    loaded: dict[str, object] = json.loads(result.stdout.strip().splitlines()[-1])
    return loaded


def test_broken_alembic_warns_and_dialect_still_loads() -> None:
    loaded = _load_dialects(_BROKEN_ALEMBIC)

    assert loaded["names"] == ["cubrid", "cubrid", "cubrid"]
    assert loaded["impl_loaded"] is False
    assert loaded["warnings"] == [
        [
            "RuntimeWarning",
            "sqlalchemy-cubrid: Alembic integration is disabled because the installed "
            "Alembic failed to import (NameError: name 'TextClause' is not defined). "
            'Install "alembic>=1.7.2,<2.0" to enable CUBRID migrations.',
        ]
    ]


@pytest.mark.parametrize("setup", [_BROKEN_ALEMBIC, _NO_ALEMBIC], ids=["broken", "missing"])
def test_error_warning_filter_cannot_abort_dialect_loading(setup: str) -> None:
    # ``-W error::RuntimeWarning`` turns warnings.warn() into a raise; the
    # diagnostic must then fall back to logging instead of propagating.
    script = (
        "import sys\n"
        + setup
        + "\nfrom sqlalchemy.dialects import registry\n"
        + 'print([registry.load(n).name for n in ("cubrid", "cubrid.pycubrid", '
        + '"cubrid.aiopycubrid")])\n'
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    result = subprocess.run(
        [sys.executable, "-W", "error::RuntimeWarning", "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "['cubrid', 'cubrid', 'cubrid']"
    disabled = "Alembic integration is disabled because the installed Alembic failed"
    if setup is _BROKEN_ALEMBIC:
        # No logging configured: the logging module's last-resort handler
        # writes the fallback record to stderr.
        assert disabled in result.stderr
        assert "NameError: name 'TextClause' is not defined" in result.stderr
    else:
        assert disabled not in result.stderr


def test_missing_alembic_is_silent() -> None:
    loaded = _load_dialects(_NO_ALEMBIC)

    assert loaded["names"] == ["cubrid", "cubrid", "cubrid"]
    assert loaded["impl_loaded"] is False
    assert loaded["warnings"] == []


def test_working_alembic_registers_without_warning() -> None:
    # Alembic 1.18+ registers CubridImpl through the alembic.plugins entry
    # point when it is imported; older Alembic is imported by the dialect
    # (#595).  Either way Alembic finds it once it is in use.
    loaded = _load_dialects("")
    result = subprocess.run(
        [
            sys.executable,
            "-W",
            "error",
            "-c",
            "from sqlalchemy.dialects import registry; registry.load('cubrid.pycubrid'); "
            "from alembic.ddl.impl import _impls; print(_impls['cubrid'].__module__)",
        ],
        env={k: v for k, v in os.environ.items() if not k.startswith("PYTHON")},
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert loaded["names"] == ["cubrid", "cubrid", "cubrid"]
    assert loaded["warnings"] == []
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "sqlalchemy_cubrid.alembic_impl"


# Collection only looks at the environment variable, so the offline suite never
# opens a database connection; the conftest gate checks reachability (#593).
_LIVE_URL = os.environ.get("CUBRID_TEST_URL")


@pytest.mark.integration
@pytest.mark.skipif(not _LIVE_URL, reason="CUBRID instance not available (set CUBRID_TEST_URL)")
@pytest.mark.parametrize(
    ("template", "drivername"),
    [
        # Alembic's default template drives a synchronous engine.
        ("generic", None),
        # cubrid+aiopycubrid:// needs Alembic's async template
        # (``alembic init -t async``); the default one cannot drive it.
        ("async", "cubrid+aiopycubrid"),
    ],
)
def test_online_upgrade_with_unmodified_template(
    tmp_path: Path, template: str, drivername: str | None
) -> None:
    import sqlalchemy as sa

    assert _LIVE_URL is not None
    # test/conftest.py has already errored this test if the server is unreachable (#593).
    engine = sa.create_engine(_LIVE_URL)

    # The default env.py uses the ``alembic_version`` table.  Never touch one
    # that already exists: it may hold a real database's migration history.
    if sa.inspect(engine).has_table("alembic_version"):
        engine.dispose()
        pytest.skip("target database already has an alembic_version table")

    table = f"sa504_{uuid.uuid4().hex[:8]}"
    url = sa.make_url(_LIVE_URL)
    if drivername is not None:
        url = url.set(drivername=drivername)
    project = _make_project(tmp_path, url.render_as_string(hide_password=False), table, template)
    try:
        upgrade = _alembic(project, "upgrade", "head")
        assert "KeyError" not in upgrade.stderr, upgrade.stderr
        assert upgrade.returncode == 0, upgrade.stderr

        columns = {c["name"] for c in sa.inspect(engine).get_columns(table)}
        assert columns == {"id", "label"}

        downgrade = _alembic(project, "downgrade", "base")
        assert downgrade.returncode == 0, downgrade.stderr
        assert not sa.inspect(engine).has_table(table)
    finally:
        # Both tables were created by this test (checked above), so dropping
        # them only removes this test's own objects.
        cleanup = sa.MetaData()
        with engine.begin() as conn:
            for name in (table, "alembic_version"):
                sa.Table(name, cleanup).drop(conn, checkfirst=True)
        engine.dispose()
