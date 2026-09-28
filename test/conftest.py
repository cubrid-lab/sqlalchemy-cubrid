"""conftest.py — test configuration for sqlalchemy-cubrid.

The SA testing plugin (pytestplugin) is only loaded when running the full
SA test suite against a live CUBRID instance via ``--dburi``.  Offline tests
(test_dialects, test_compiler, test_types) work without it.

When the compliance suite runs, a strict xfail is applied to every node id
listed in ``test/known_failures.txt`` for the current lane (driver from the
``--dburi`` dialect + SQLAlchemy major.minor, e.g. ``pycubrid@sa2.1``; #463) so
the suite can gate CI (see #380) while tolerating the documented baseline: a
listed test that still fails is xfailed, a listed test that starts passing
becomes an XPASS (hard failure), and any new failure not listed for the lane
fails CI.
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


#: Set only in the required driver-differential CI lane (#486). The comparison
#: tests skip at fixture time when either driver cannot connect, which the
#: collection-time guard above cannot see, so the lane must count real passes.
_REQUIRE_DIFFERENTIAL_ENV = "CUBRID_REQUIRE_DRIVER_DIFFERENTIAL"
_DIFFERENTIAL_MODULE = "test_driver_differential.py"
_differential_passed: set[str] = set()


if not ("--dburi" in sys.argv or any(a.startswith("--dburi=") for a in sys.argv)):
    import pytest

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(items):  # noqa: ANN001
        _ci_integration_guard(items)

    def pytest_runtest_logreport(report):  # noqa: ANN001
        if (
            report.when == "call"
            and report.passed
            and report.nodeid.split("::", 1)[0].endswith(_DIFFERENTIAL_MODULE)
        ):
            _differential_passed.add(report.nodeid)

    def pytest_sessionfinish(session, exitstatus):  # noqa: ANN001
        """Fail the required differential lane when no comparison actually ran.

        Zero collected, all skipped (e.g. CUBRIDdb not built or the server
        unreachable) and all deselected are indistinguishable from success in
        pytest's exit code, so require at least one passing comparison.
        """
        if os.environ.get(_REQUIRE_DIFFERENTIAL_ENV) != "1":
            return
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        count = len(_differential_passed)
        if count:
            message = f"{_REQUIRE_DIFFERENTIAL_ENV}=1: {count} driver-differential case(s) passed"
        else:
            message = (
                f"{_REQUIRE_DIFFERENTIAL_ENV}=1 but no {_DIFFERENTIAL_MODULE} case ran and "
                "passed (zero collected or all skipped); both pycubrid and CUBRIDdb must "
                "connect in the required driver-differential lane"
            )
            if exitstatus in (pytest.ExitCode.OK, pytest.ExitCode.NO_TESTS_COLLECTED):
                session.exitstatus = pytest.ExitCode.TESTS_FAILED
        if reporter is not None:
            reporter.write_line(message, red=not count, green=bool(count), bold=True)


# ----- Compliance-suite known-failure manifest (#380, #463) -----
# Module level so the offline suite can validate the manifest format.

_KNOWN_FAILURES_FILE = Path(__file__).with_name("known_failures.txt")

# Strips the suite's server-version suffix, e.g. `_cubrid+cubrid_11_4_6_1963`
# or `_cubrid+pycubrid_10_2_1_8849`, so the manifest matches the bare class
# name across CUBRID builds.
_VERSION_SUFFIX = re.compile(r"_cubrid\+(?:py)?cubrid_[0-9_]+")

# Python enum.Flag repr renders combined members in a non-deterministic
# order across environments (e.g. `TABLE|VIEW` vs `VIEW|TABLE`), so sort the
# `A|B` parameter fragments before matching to keep the manifest stable.
_FLAG_FRAGMENT = re.compile(r"([A-Za-z_]+(?:\|[A-Za-z_]+)+)")

# A manifest lane is `<driver>@sa<major.minor>`, optionally narrowed to one
# CUBRID server as `<driver>@sa<major.minor>@cubrid<major.minor>` (#463): each
# entry xfails only in the lanes it names, so one driver's baseline cannot hide
# a regression on the other. Lane tags follow the node id, which may itself
# contain spaces (e.g. BizarroCharacterTest's `per % cent` parameter).
_LANE = r"(?:cubrid|pycubrid)@sa[0-9]+\.[0-9]+(?:@cubrid[0-9]+\.[0-9]+)?"
_ENTRY = re.compile(rf"(?P<nodeid>\S.*?)(?P<tags>(?:\s+{_LANE})+)")


def _load_known_failures(path: Path) -> dict[str, set[str]]:
    """Map each lane to the normalized node ids listed for it in *path*."""
    lanes: dict[str, set[str]] = {}
    if not path.exists():
        return lanes
    text = path.read_text(encoding="utf-8")
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _ENTRY.fullmatch(line)
        if match is None or " " not in line:
            raise ValueError(
                f"{path.name}:{lineno}: every entry is a node id followed by one or "
                f"more <driver>@sa<major.minor>[@cubrid<major.minor>] lane tags"
            )
        for tag in match["tags"].split():
            lanes.setdefault(tag, set()).add(_normalize_nodeid(match["nodeid"]))
    return lanes


def _normalize_nodeid(nodeid: str) -> str:
    stripped = _VERSION_SUFFIX.sub("", nodeid)
    return _FLAG_FRAGMENT.sub(lambda m: "|".join(sorted(m.group(1).split("|"))), stripped)


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

    def _current_lanes() -> tuple[str, str]:
        """The lane (`driver@saX.Y`) and its server-specific form (`...@cubridA.B`)."""
        import sqlalchemy
        from sqlalchemy.testing import config as sa_config

        dialect = sa_config.db.dialect
        if dialect.server_version_info is None:  # not initialized until first connect
            sa_config.db.connect().close()
        sa_version = ".".join(sqlalchemy.__version__.split(".")[:2])
        server = ".".join(str(part) for part in dialect.server_version_info[:2])
        lane = f"{dialect.driver}@sa{sa_version}"
        return lane, f"{lane}@cubrid{server}"

    _KNOWN_FAILURES_BY_LANE = _load_known_failures(_KNOWN_FAILURES_FILE)

    def pytest_collection_modifyitems(session, config, items):  # noqa: ANN001
        _sa_collection_modifyitems(session, config, items)
        lane, server_lane = _current_lanes()
        known = _KNOWN_FAILURES_BY_LANE.get(lane, set()) | _KNOWN_FAILURES_BY_LANE.get(
            server_lane, set()
        )
        strict_mode = os.environ.get("CUBRID_STRICT_KNOWN_FAILURES") == "1"
        reporter = config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            reporter.write_line(
                f"compliance lane {server_lane}: {len(known)} known failure(s) from "
                f"{_KNOWN_FAILURES_FILE.name}" + (" (strict)" if strict_mode else ""),
                bold=True,
            )

        # A gating cell must run against a reviewed baseline for its exact lane;
        # an unknown driver/SQLAlchemy combination must not gate on an empty list.
        if strict_mode and not known:
            pytest.exit(
                f"CUBRID_STRICT_KNOWN_FAILURES=1 but {_KNOWN_FAILURES_FILE.name} has no "
                f"entries for lane {lane!r}; capture and review its baseline first "
                f"(see docs/DEVELOPMENT.md).",
                returncode=1,
            )
        if not known:
            return
        strict_xfail = pytest.mark.xfail(
            reason=f"known failure for lane {lane} baselined in test/known_failures.txt (#380, #463)",
            strict=True,
        )
        collected = {_normalize_nodeid(item.nodeid) for item in items}
        for item in items:
            if _normalize_nodeid(item.nodeid) in known:
                item.add_marker(strict_xfail)

        # In a gating cell (CUBRID_STRICT_KNOWN_FAILURES=1), a manifest entry for
        # this lane that no longer matches any collected node is a stale
        # baseline: fail loudly so the manifest is trimmed instead of silently
        # losing its strict-XPASS guarantee. Off by default so partial local runs
        # (e.g. `-k something`) do not trip it.
        if strict_mode:
            unmatched = sorted(known - collected)
            if unmatched:
                listing = "\n  ".join(unmatched)
                pytest.exit(
                    f"{len(unmatched)} known_failures.txt entries for lane {lane} matched "
                    f"no collected test (stale baseline — recapture after a "
                    f"SQLAlchemy bump?):\n  {listing}",
                    returncode=1,
                )
