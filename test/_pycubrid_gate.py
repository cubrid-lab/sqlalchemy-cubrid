"""Strict xfail for a pycubrid release older than the one that fixed a behavior (#479).

The ``[pycubrid]`` floor is 1.8.0, but most lanes install the latest release.
A regression test for a pycubrid fix released later calls
:func:`xfail_before_pycubrid` with that release and the pycubrid issue: on an
older pycubrid the test is a strict xfail, so it still runs there and turns
into an XPASS failure if the old release ever passes; on the fixed release and
later it must pass.
"""

from __future__ import annotations

import re

import pytest


def installed_pycubrid_version() -> tuple[int, ...] | None:
    """The installed ``pycubrid.__version__`` as ``(major, minor, patch)``, or ``None``."""
    try:
        import pycubrid
    except ImportError:
        return None
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", pycubrid.__version__)
    if match is None:
        raise ValueError(f"unparsable pycubrid version {pycubrid.__version__!r}")
    return tuple(int(part) for part in match.groups())


def xfail_before_pycubrid(
    request: pytest.FixtureRequest,
    fixed_in: tuple[int, int, int],
    issue: str,
    *,
    raises: type[BaseException] | tuple[type[BaseException], ...] | None = None,
) -> None:
    """Mark the running test a strict xfail when pycubrid is older than *fixed_in*."""
    installed = installed_pycubrid_version()
    if installed is None or installed >= fixed_in:
        return
    request.applymarker(
        pytest.mark.xfail(
            strict=True,
            raises=raises,
            reason=(
                f"fixed in pycubrid {'.'.join(map(str, fixed_in))} ({issue}); "
                f"the installed pycubrid is {'.'.join(map(str, installed))}"
            ),
        )
    )
