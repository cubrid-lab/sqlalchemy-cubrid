"""conftest.py — test configuration for sqlalchemy-cubrid.

The SA testing plugin (pytestplugin) is only loaded when running the full
SA test suite against a live CUBRID instance via ``--dburi``.  Offline tests
(test_dialects, test_compiler, test_types) work without it.

When the compliance suite runs, a strict xfail is applied to every node id
listed in ``test/known_failures.txt`` so the suite can gate CI (see #380)
while tolerating the documented baseline: a listed test that still fails is
xfailed, a listed test that starts passing becomes an XPASS (hard failure),
and any new failure not in the manifest fails CI.
"""

import os
import re
import sys
from pathlib import Path

# Only load the heavy SA testing plugin when a DB URI is provided.
# This allows offline tests to run without CUBRIDdb installed.
if "--dburi" in sys.argv or any(a.startswith("--dburi=") for a in sys.argv):
    from sqlalchemy.dialects import registry

    registry.register("cubrid", "sqlalchemy_cubrid.dialect", "CubridDialect")
    registry.register("cubrid.cubrid", "sqlalchemy_cubrid.dialect", "CubridDialect")
    registry.register("cubrid.pycubrid", "sqlalchemy_cubrid.pycubrid_dialect", "PyCubridDialect")

    import pytest

    pytest.register_assert_rewrite("sqlalchemy.testing.assertions")

    from sqlalchemy.testing.plugin.pytestplugin import (  # noqa: E402
        pytest_collection_modifyitems as _sa_collection_modifyitems,
    )
    from sqlalchemy.testing.plugin.pytestplugin import *  # noqa: E402, F401, F403

    _KNOWN_FAILURES_FILE = Path(__file__).with_name("known_failures.txt")

    # Strips the suite's server-version suffix, e.g. `_cubrid+cubrid_11_4_6_1963`,
    # so the manifest matches the bare class name across CUBRID builds.
    _VERSION_SUFFIX = re.compile(r"_cubrid\+cubrid_[0-9_]+")

    def _load_known_failures() -> set[str]:
        if not _KNOWN_FAILURES_FILE.exists():
            return set()
        entries: set[str] = set()
        for raw in _KNOWN_FAILURES_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#"):
                entries.add(line)
        return entries

    _KNOWN_FAILURES = _load_known_failures()

    def _normalize_nodeid(nodeid: str) -> str:
        return _VERSION_SUFFIX.sub("", nodeid)

    def pytest_collection_modifyitems(session, config, items):  # noqa: ANN001
        _sa_collection_modifyitems(session, config, items)
        if not _KNOWN_FAILURES:
            return
        strict_xfail = pytest.mark.xfail(
            reason="known failure baselined in test/known_failures.txt (#380)",
            strict=True,
        )
        collected = {_normalize_nodeid(item.nodeid) for item in items}
        for item in items:
            if _normalize_nodeid(item.nodeid) in _KNOWN_FAILURES:
                item.add_marker(strict_xfail)

        # In the pinned gating cell (CUBRID_STRICT_KNOWN_FAILURES=1), a manifest
        # entry that no longer matches any collected node is a stale baseline:
        # fail loudly so the manifest is trimmed instead of silently losing its
        # strict-XPASS guarantee. Off by default so partial local runs
        # (e.g. `-k something`) do not trip it.
        if os.environ.get("CUBRID_STRICT_KNOWN_FAILURES") == "1":
            unmatched = sorted(_KNOWN_FAILURES - collected)
            if unmatched:
                listing = "\n  ".join(unmatched)
                pytest.exit(
                    f"{len(unmatched)} known_failures.txt entries matched no "
                    f"collected test (stale baseline — recapture after a "
                    f"SQLAlchemy bump?):\n  {listing}",
                    returncode=1,
                )
