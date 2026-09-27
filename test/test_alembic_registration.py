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
does.  The online test needs a live CUBRID and ``CUBRID_TEST_URL``.
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


def _make_project(tmp_path: Path, url: str, table: str) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    init = _alembic(project, "init", "migrations")
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


def test_missing_alembic_is_silent() -> None:
    loaded = _load_dialects(_NO_ALEMBIC)

    assert loaded["names"] == ["cubrid", "cubrid", "cubrid"]
    assert loaded["impl_loaded"] is False
    assert loaded["warnings"] == []


def test_working_alembic_registers_without_warning() -> None:
    loaded = _load_dialects("")

    assert loaded["names"] == ["cubrid", "cubrid", "cubrid"]
    assert loaded["impl_loaded"] is True
    assert loaded["warnings"] == []


def _live_url() -> str | None:
    url = os.environ.get("CUBRID_TEST_URL")
    if not url:
        return None
    try:
        import sqlalchemy as sa

        engine = sa.create_engine(url)
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
        engine.dispose()
    except Exception:
        return None
    return url


_LIVE_URL = _live_url()


@pytest.mark.integration
@pytest.mark.skipif(_LIVE_URL is None, reason="CUBRID instance not available (set CUBRID_TEST_URL)")
def test_online_upgrade_with_default_env_py(tmp_path: Path) -> None:
    import sqlalchemy as sa

    assert _LIVE_URL is not None
    table = f"sa504_{uuid.uuid4().hex[:8]}"
    project = _make_project(tmp_path, _LIVE_URL, table)
    engine = sa.create_engine(_LIVE_URL)
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
        with engine.begin() as conn:
            conn.execute(sa.text(f"DROP TABLE IF EXISTS {table}"))
            conn.execute(sa.text("DROP TABLE IF EXISTS alembic_version"))
        engine.dispose()
