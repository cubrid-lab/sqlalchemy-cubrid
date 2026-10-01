# test/test_offline_lanes.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""The fast offline lane and the repository-tooling lane cover every offline test (#594).

``make test`` deselects the ``repo`` marker that ``test/conftest.py`` applies
to ``REPO_TOOLING_MODULES``. These checks keep that split from silently
dropping tests: the fast selections exclude ``repo``, the repository-tooling
selections are ``-m repo``, and the ``repo-tests`` CI job stays required.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from test.conftest import REPO_TOOLING_MODULES

ROOT = Path(__file__).resolve().parents[1]
FAST = '-m "not integration and not repo"'


def _ci_job(name: str) -> str:
    """Return the body of one top-level job in ``.github/workflows/ci.yml``."""
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    match = re.search(rf"^  {re.escape(name)}:\n(.*?)(?=^  [a-z0-9-]+:\n|\Z)", text, re.M | re.S)
    assert match, f"job {name!r} not found in ci.yml"
    return match.group(1)


def _make_recipe(target: str) -> str:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    match = re.search(rf"^{re.escape(target)}:.*\n((?:\t.*\n)+)", text, re.M)
    assert match, f"target {target!r} not found in Makefile"
    return match.group(1)


def test_repo_tooling_modules_exist_and_are_test_modules():
    assert REPO_TOOLING_MODULES
    for name in REPO_TOOLING_MODULES:
        assert name.startswith("test_") and name.endswith(".py")
        assert (ROOT / "test" / name).is_file()


@pytest.mark.parametrize(
    ("target", "selection"),
    [("test", FAST), ("test-repo", "-m repo"), ("test-offline", '-m "not integration"')],
)
def test_make_targets_select_their_lane(target, selection):
    assert selection in _make_recipe(target)


def test_tox_runs_both_lanes():
    text = (ROOT / "tox.ini").read_text(encoding="utf-8")
    assert FAST in text
    assert re.search(r"^\[testenv:repo\]\ncommands = pytest test/ -v -m repo$", text, re.M)
    envlist = re.search(r"^envlist = (.*)$", text, re.M)
    assert envlist and "repo" in [env.strip() for env in envlist.group(1).split(",")]


def test_ci_offline_job_is_fast_lane():
    assert '-m "not integration and not repo"' in _ci_job("offline-tests")


def test_ci_repo_job_runs_repo_lane_on_every_python():
    job = _ci_job("repo-tests")
    assert "python -m pytest test/ -m repo" in job
    assert "if:" not in job.split("steps:", 1)[0], "repo-tests must run on every event"
    offline = _ci_job("offline-tests")
    versions = re.compile(r"python-version: (\[.*?\])")
    assert versions.search(job).group(1) == versions.search(offline).group(1)


def test_ci_repo_job_is_required():
    result = _ci_job("matrix-result")
    needs = re.search(r"needs: \[(.*?)\]", result)
    assert needs and "repo-tests" in [n.strip() for n in needs.group(1).split(",")]
    assert "needs.repo-tests.result != 'success'" in result
