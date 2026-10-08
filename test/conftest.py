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


_UNCONFIGURED_REASON = (
    "requires a live CUBRID server (set CUBRID_TEST_URL, or run `make integration`)"
)
# Outcome of the one live probe per session (#593): None = not probed yet,
# "" = reachable, otherwise the error every integration test reports.
_probe_error: str | None = None

#: Repository-tooling test modules (#594): they exercise the Makefile, its
#: signal handling and repository scripts through subprocesses, not the
#: dialect, and dominate the offline run's wall-clock time. Every test they
#: collect gets the ``repo`` marker, so ``make test`` (``-m "not integration
#: and not repo"``) skips them and ``make test-repo`` (``-m repo``) and the
#: required ``repo-tests`` CI job run them. The list lives here rather than in
#: a ``pytestmark`` because ``test_release_detect.py`` is kept identical
#: across repositories.
REPO_TOOLING_MODULES = frozenset(
    {
        "test_make_integration.py",
        "test_docs_reason.py",
        "test_release_detect.py",
        "test_check_docs_translation.py",
        "test_workflow_timeouts.py",
        "test_workflow_installs.py",
        "test_workflow_cubriddb_cache.py",
    }
)
_missing_repo_modules = sorted(
    name for name in REPO_TOOLING_MODULES if not Path(__file__).with_name(name).is_file()
)
if _missing_repo_modules:
    raise RuntimeError(f"REPO_TOOLING_MODULES lists missing test modules: {_missing_repo_modules}")


def pytest_itemcollected(item):  # noqa: ANN001
    """Mark every test of a ``REPO_TOOLING_MODULES`` module ``repo`` (#594).

    Runs before ``-m`` deselection, so ``-m repo`` and ``-m "not repo"`` see
    the marker for pytest-style and ``unittest`` tests alike.
    """
    # Compare the directory too: the list names modules of this directory, so
    # a same-named module in a subdirectory is not repository tooling (#624).
    if (
        item.path.name in REPO_TOOLING_MODULES
        and item.path.parent.resolve() == Path(__file__).resolve().parent
    ):
        import pytest

        item.add_marker(pytest.mark.repo)


def _endpoint_error() -> str:
    """Probe the ``CUBRID_TEST_URL`` server once per session; "" when it answers."""
    global _probe_error
    if _probe_error is None:
        from scripts import integration_urls as urls

        try:
            url = urls.configured_url()
            aurl, overridden = urls.configured_async_url(url)
        except ValueError as exc:
            _probe_error = f"CUBRID test URL is set but unusable: {exc}"
            return _probe_error
        # CUBRID_TEST_AURL is an explicit second endpoint (the async suites use
        # it instead of the route derived from CUBRID_TEST_URL), so it must
        # answer too; the derived route is exercised by the async tests themselves.
        checks = [("CUBRID_TEST_URL", url, urls.probe)]
        if overridden:
            checks.append(("CUBRID_TEST_AURL", aurl, urls.async_probe))
        for var, target, check in checks:
            try:
                check(target)
            except Exception as exc:  # noqa: BLE001 - any failure means "not usable"
                _probe_error = (
                    f"{var} is set, but CUBRID at {urls.describe(target)} does not answer "
                    f"SELECT 1 through the driver the URL selects: "
                    f"{urls.error_summary(exc, target)}. Start the server (or run "
                    f"`make integration`), fix {var} or install its driver; unset "
                    "CUBRID_TEST_URL to skip the integration tests."
                )
                return _probe_error
        _probe_error = ""
    return _probe_error


def _ci_integration_guard(items) -> None:  # noqa: ANN001
    """Fail-hard when CI selects integration tests but ``CUBRID_TEST_URL`` is unset.

    Without the URL every ``integration``-marked test skips (see
    ``pytest_runtest_setup`` below). That is correct locally and in the offline
    job (``-m "not integration"`` deselects them entirely), but a CI job that
    runs integration tests without a configured CUBRID must fail loudly rather
    than silently skip. ``items`` here is post-deselection (see the
    ``trylast`` hookwrapper below), so it only contains tests that will run.
    """
    from scripts.integration_urls import is_configured

    if os.environ.get("CI", "").lower() not in ("true", "1") or is_configured():
        return
    count = sum(1 for item in items if item.get_closest_marker("integration") is not None)
    if count:
        import pytest

        pytest.exit(
            f"CI=true is running {count} integration test(s) but CUBRID_TEST_URL is "
            "not set, so every one would be skipped. Integration tests must not be "
            "silently skipped in CI; set CUBRID_TEST_URL to the CUBRID service or "
            'deselect them with -m "not integration".',
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

    def pytest_runtest_setup(item):  # noqa: ANN001
        """Gate ``integration``-marked tests on a configured, reachable CUBRID (#593).

        Classification lives entirely in the ``integration`` marker; no test
        module probes the server at import time. This hook runs after ``skipif``
        markers are evaluated but before any fixture is set up (including
        module-scoped engines):

        * ``CUBRID_TEST_URL`` unset: skip, so a bare ``pytest`` stays green locally
          (in CI, ``_ci_integration_guard`` fails the run instead);
        * ``CUBRID_TEST_URL`` set but its server does not answer ``SELECT 1``
          through the driver the URL selects (or a ``CUBRID_TEST_AURL``
          override does not answer through ``cubrid+aiopycubrid://``), or either
          URL is not a CUBRID URL with a database: error, never skip. The
          endpoints are probed once per session, and every integration test
          reports the same error, naming the URL without its password.

        Per-driver skips inside a module (both drivers needed, a Docker
        container needed) still apply after the gate passes, with their own
        ``CUBRID_REQUIRE_*`` switches (#486).
        """
        from scripts.integration_urls import is_configured

        if item.get_closest_marker("integration") is None:
            return
        if not is_configured():
            pytest.skip(_UNCONFIGURED_REASON)
        error = _endpoint_error()
        if error:
            pytest.fail(error, pytrace=False)

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

#: The SQLAlchemy release each gated lane's baseline was captured with (the CI
#: steps pin the same versions). A strict run on another release fails.
_PINNED_SQLALCHEMY = {
    "cubrid@sa2.0": "2.0.53",
    "pycubrid@sa2.0": "2.0.53",
    "pycubrid@sa2.1": "2.1.1",
}
#: Supported CUBRID servers, and the (lane, server) pairs CI actually gates. A
#: server-narrowed tag outside these pairs could never be verified, so it is a
#: load error instead of an unreviewed, never-exercised entry.
_CUBRID_SERVERS = frozenset({"10.2", "11.0", "11.2", "11.4"})
_GATED_SERVER_LANES = frozenset(
    {"cubrid@sa2.0@cubrid11.4", "pycubrid@sa2.0@cubrid10.2", "pycubrid@sa2.1@cubrid11.4"}
)


def _load_known_failures(path: Path) -> dict[str, set[str]]:
    """Map each lane to the normalized node ids listed for it in *path*."""
    lanes: dict[str, set[str]] = {}
    if not path.exists():
        return lanes
    seen: dict[str, int] = {}
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
        nodeid = _normalize_nodeid(match["nodeid"])
        if nodeid in seen:
            raise ValueError(
                f"{path.name}:{lineno}: {nodeid} is already listed on line {seen[nodeid]}; "
                f"list each node once with all of its lane tags"
            )
        seen[nodeid] = lineno
        for tag in match["tags"].split():
            lane, _, server = tag.partition("@cubrid")
            if lane not in _PINNED_SQLALCHEMY:
                raise ValueError(
                    f"{path.name}:{lineno}: unknown lane {lane!r}; CI gates only "
                    f"{sorted(_PINNED_SQLALCHEMY)}"
                )
            if server and (server not in _CUBRID_SERVERS or tag not in _GATED_SERVER_LANES):
                raise ValueError(
                    f"{path.name}:{lineno}: server-narrowed tag {tag!r} is not a gated "
                    f"(lane, CUBRID server) pair: {sorted(_GATED_SERVER_LANES)}"
                )
            lanes.setdefault(tag, set()).add(nodeid)
    return lanes


def _normalize_nodeid(nodeid: str) -> str:
    stripped = _VERSION_SUFFIX.sub("", nodeid)
    return _FLAG_FRAGMENT.sub(lambda m: "|".join(sorted(m.group(1).split("|"))), stripped)


def _skipped_known_failure(report, known: set[str]) -> str | None:  # noqa: ANN001
    """The normalized node id when *report* skips a listed known failure.

    A listed test that is skipped (a requirement closed it, or a fixture
    skipped) is neither xfailed nor XPASSed, so strict mode would silently stop
    checking it. Strict xfails report as skipped too, but carry ``wasxfail``.
    """
    if not report.skipped or hasattr(report, "wasxfail"):
        return None
    nodeid = _normalize_nodeid(report.nodeid)
    return nodeid if nodeid in known else None


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
    from sqlalchemy.testing.plugin.pytestplugin import (  # noqa: E402
        pytest_runtest_logreport as _sa_runtest_logreport,
    )
    from sqlalchemy.testing.plugin.pytestplugin import (  # noqa: E402
        pytest_sessionfinish as _sa_sessionfinish,
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
    _STRICT = os.environ.get("CUBRID_STRICT_KNOWN_FAILURES") == "1"
    _active_known: set[str] = set()
    _skipped_known: set[str] = set()
    _xfailed_known: set[str] = set()

    def pytest_collection_modifyitems(session, config, items):  # noqa: ANN001
        import sqlalchemy

        _sa_collection_modifyitems(session, config, items)
        lane, server_lane = _current_lanes()
        known = _KNOWN_FAILURES_BY_LANE.get(lane, set()) | _KNOWN_FAILURES_BY_LANE.get(
            server_lane, set()
        )
        strict_mode = _STRICT
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
        # The baseline is a snapshot of one SQLAlchemy release (suite
        # parametrization changes between releases); gate only on that release.
        pinned = _PINNED_SQLALCHEMY.get(lane)
        if strict_mode and pinned is not None and sqlalchemy.__version__ != pinned:
            pytest.exit(
                f"CUBRID_STRICT_KNOWN_FAILURES=1: lane {lane} was captured with "
                f"SQLAlchemy {pinned}, but {sqlalchemy.__version__} is installed; pin it "
                f"or recapture the lane (see docs/DEVELOPMENT.md).",
                returncode=1,
            )
        if not known:
            return
        _active_known.update(known)
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

    def pytest_runtest_logreport(report):  # noqa: ANN001
        _sa_runtest_logreport(report)
        if hasattr(report, "wasxfail"):
            # Any phase counts: e.g. CTETest::test_delete_from_round_trip skips its
            # body but xfails in teardown, which still exercises the entry.
            _xfailed_known.add(_normalize_nodeid(report.nodeid))
        nodeid = _skipped_known_failure(report, _active_known)
        if nodeid is not None:
            _skipped_known.add(nodeid)

    def pytest_sessionfinish(session):  # noqa: ANN001
        """In strict mode, fail when a listed known failure was skipped.

        A skipped entry no longer proves anything (it can neither xfail nor
        XPASS), so the baseline must drop it or the skip must be fixed.
        """
        _sa_sessionfinish(session)
        only_skipped = _skipped_known - _xfailed_known
        if not (_STRICT and only_skipped):
            return
        listing = "\n  ".join(sorted(only_skipped))
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            reporter.write_line(
                f"CUBRID_STRICT_KNOWN_FAILURES=1: {len(only_skipped)} known_failures.txt "
                f"entries were SKIPPED instead of xfailed (remove them or fix the skip):"
                f"\n  {listing}",
                red=True,
                bold=True,
            )
        if session.exitstatus in (pytest.ExitCode.OK, pytest.ExitCode.NO_TESTS_COLLECTED):
            session.exitstatus = pytest.ExitCode.TESTS_FAILED
