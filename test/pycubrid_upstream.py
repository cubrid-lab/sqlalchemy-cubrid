# test/pycubrid_upstream.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Strict xfail markers for pycubrid fixes merged upstream but not yet released.

Downstream contract tests (tracker #479) land before the pycubrid release that
fixes the behavior they check. On the released driver such a case is a strict
xfail naming the upstream issue, scoped to the pycubrid drivers only, so the
test documents the gap without breaking CI.

pycubrid ``main`` keeps reporting the last released ``__version__`` until the
next release, so the installed version cannot tell a fixed build from a
released one. Instead, ``CUBRID_PYCUBRID_UPSTREAM=1`` is the explicit signal
that the installed pycubrid is expected to contain the upstream fixes; the
weekly ``upstream-canary.yml`` integration job that installs ``pycubrid@main``
sets it. With the variable set the markers are no-ops, so the same tests must
pass there, and any regression on ``main`` fails the canary.

Once a pycubrid release containing a fix is adopted (the dependency lower bound
includes it), delete the matching helper call and its issue from
``UNRELEASED_FIXES``; a strict XPASS on the released lanes signals when that is
due. See ``docs/DEVELOPMENT.md``.
"""

from __future__ import annotations

import os

import pytest

UPSTREAM_ENV = "CUBRID_PYCUBRID_UPSTREAM"

#: SQLAlchemy driver names (``engine.dialect.driver``) backed by pycubrid.
PYCUBRID_DRIVERS = frozenset({"pycubrid", "aiopycubrid"})

#: cubrid-lab/pycubrid issues fixed on ``main`` but not in a released version.
UNRELEASED_FIXES = frozenset({390})


def expects_upstream_pycubrid() -> bool:
    """True when the run declares that pycubrid ``main`` fixes are installed."""
    return os.environ.get(UPSTREAM_ENV) == "1"


def xfail_unreleased_pycubrid_fix(
    request: pytest.FixtureRequest,
    driver: str,
    issue: int,
    *,
    raises: type[BaseException] | tuple[type[BaseException], ...] | None = None,
) -> None:
    """Strictly xfail the running test on a released pycubrid lacking *issue*.

    No-op for non-pycubrid drivers and when ``CUBRID_PYCUBRID_UPSTREAM=1``.
    """
    if issue not in UNRELEASED_FIXES:
        raise ValueError(f"cubrid-lab/pycubrid#{issue} is not listed as an unreleased fix")
    if driver not in PYCUBRID_DRIVERS or expects_upstream_pycubrid():
        return
    request.applymarker(
        pytest.mark.xfail(
            strict=True,
            raises=raises,
            reason=f"cubrid-lab/pycubrid#{issue}, fixed on main, unreleased",
        )
    )
