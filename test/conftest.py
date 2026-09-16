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

try:
    from hypothesis import HealthCheck, settings

    settings.register_profile("dev", max_examples=50)
    settings.register_profile(
        "ci",
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    settings.register_profile(
        "nightly",
        max_examples=2000,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))
except ModuleNotFoundError:  # hypothesis is a dev-only dependency
    pass


def _item_is_skipped(item) -> bool:  # noqa: ANN001
    """True if the item carries an active skip/skipif for the current run.

    ``pytest.mark.skipif(cond, ...)`` always attaches a ``skipif`` marker
    regardless of ``cond``, so marker *presence* is not enough — the boolean
    condition (``not _available``, evaluated at import) is the first positional
    arg and must itself be truthy for the test to actually skip.
    """
    for marker in item.iter_markers(name="skip"):
        return True
    return any(
        any(bool(cond) for cond in marker.args) for marker in item.iter_markers(name="skipif")
    )


def _ci_integration_guard(items) -> None:  # noqa: ANN001
    """Fail-hard when CI runs integration tests but every one is skipped.

    The live-DB files mark themselves ``integration`` + ``skipif`` when no
    CUBRID is reachable. That skip is correct locally and in the offline job
    (``-m "not integration"`` deselects them entirely), but a CI job that runs
    integration tests against a broken/absent CUBRID must fail loudly rather
    than silently skip. ``items`` here is post-deselection (see the
    ``trylast`` hookwrapper below), so it only contains tests that will run.
    """
    if os.environ.get("CI", "").lower() not in ("true", "1"):
        return
    integration_items = [
        item for item in items if item.get_closest_marker("integration") is not None
    ]
    if not integration_items:
        return
    if all(_item_is_skipped(item) for item in integration_items):
        import pytest

        pytest.exit(
            f"CI=true is running {len(integration_items)} integration test(s) "
            "but every one is skipped — CUBRID is not reachable. Integration "
            "tests must not be silently skipped in CI; check the CUBRID service "
            "container / CUBRID_TEST_URL.",
            returncode=1,
        )


if not ("--dburi" in sys.argv or any(a.startswith("--dburi=") for a in sys.argv)):
    import pytest

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(items):  # noqa: ANN001
        _ci_integration_guard(items)


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

    # Python enum.Flag repr renders combined members in a non-deterministic
    # order across environments (e.g. `TABLE|VIEW` vs `VIEW|TABLE`), so sort the
    # `A|B` parameter fragments before matching to keep the manifest stable.
    _FLAG_FRAGMENT = re.compile(r"([A-Za-z_]+(?:\|[A-Za-z_]+)+)")

    def _load_known_failures() -> set[str]:
        if not _KNOWN_FAILURES_FILE.exists():
            return set()
        entries: set[str] = set()
        for raw in _KNOWN_FAILURES_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#"):
                entries.add(_normalize_nodeid(line))
        return entries

    def _normalize_nodeid(nodeid: str) -> str:
        stripped = _VERSION_SUFFIX.sub("", nodeid)
        return _FLAG_FRAGMENT.sub(lambda m: "|".join(sorted(m.group(1).split("|"))), stripped)

    _KNOWN_FAILURES = _load_known_failures()

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
