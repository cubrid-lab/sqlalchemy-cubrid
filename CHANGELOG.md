# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project normally follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html),
with a narrowly scoped, explicit **repository-local exception**: after a
maintainer decision, documented migration guidance and any revised published
notice previously promised to users, dialect-specific convenience APIs may
change incompatibly in a 1.x MINOR. Unlike strict SemVer, this exception can
break callers using those extensions; see
[the 1.x API policy](RELEASING.md#public-api-compatibility-in-1x).
Core SQLAlchemy/database semantics and PATCH compatibility remain protected.

## [Unreleased]

This maintenance release revises one deprecation warning, rewords the missing-CUBRIDdb error and raises the setuptools version needed to build from source. SQL generation, reflection and connection behavior are unchanged.

### Upgrade notes

- **Revised deprecation notice for ignored type arguments (#892)** — the `DeprecationWarning` for the ignored `SMALLINT`/`BIGINT` `display_width` argument (including positional `SMALLINT(11)`) and the string-type `values` argument now says they may be removed in a future reviewed **1.x MINOR** instead of the next major release. The arguments are still accepted in this release and generate no different DDL. Migrate `SMALLINT(11)` to `SMALLINT()`, `BIGINT(20)` to `BIGINT()` and `VARCHAR(30, values=["x"])` to `VARCHAR(30)`, or pin a narrower version range. The 1.x compatibility policy behind this change is in [RELEASING.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/RELEASING.md#public-api-compatibility-in-1x) ([#1115](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1115), [#1122](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1122)) by @yeongseon.
- **Building from source needs setuptools 77 or newer** — the build backend requirement is now `setuptools>=77` for SPDX license metadata. Installing the published wheel is unaffected; source builds without build isolation need an up-to-date setuptools ([#1113](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1113)) by @CloudCorpRecords.

### Changed

- **Missing-CUBRIDdb error** — the `Could not import CUBRIDdb` error for `cubrid://` and `cubrid+cubriddb://` URLs no longer calls the CUBRIDdb C-extension driver legacy or the PyPI `CUBRID-Python` releases untested. It lists both installation paths (`sqlalchemy-cubrid[cubriddb]` or an official CUBRID/cubrid-python source build) and the pure-Python `cubrid+pycubrid://` alternative. The message prefix and the chained original `ImportError` are unchanged ([#1150](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1150)) by @yeongseon.

### Documentation

- **First connection and troubleshooting** — troubleshooting now shows the actual missing-pycubrid and authentication error messages, explains missing `greenlet` errors for async engines and broker readiness, and adds Windows virtual-environment setup to the first-connection lesson and Apple silicon options for the CUBRID lab. Translated READMEs guide readers to their first connection with `cubrid+pycubrid://` URLs and no longer overstate live CI coverage ([#1116](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1116), [#1118](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1118), [#1124](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1124), [#1126](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1126), [#1127](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1127), [#1131](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1131), [#1134](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1134), [#1137](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1137)) by @yeongseon.
- **CUBRIDdb troubleshooting** — the entry quotes the actual `Could not import CUBRIDdb` error and lists the supported `sqlalchemy-cubrid[cubriddb]` and official source-build installation paths, keeping the heading and anchor correction first proposed in #1110 ([#1205](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1205)) by @yeongseon.
- **Feature support and versions** — corrected the CUBRID 10.2 feature-support guidance and separated database server versions from Python driver versions, with a version check that works without CUBRIDdb installed ([#1117](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1117), [#1149](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1149)) by @yeongseon.
- **Getting help** — the issue chooser and documentation now point to one support and questions path, and bug reports ask for the driver and URL scheme ([#1125](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1125), [#1129](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1129), [#1135](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1135)) by @yeongseon.
- **Published pages** — fixed links from the documentation site and the PyPI README to repository files, made the PyPI demo render, and removed the unused Sphinx scaffold ([#1123](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1123), [#1132](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1132), [#1138](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1138)) by @yeongseon.
- **Historical release notes** — earlier `CHANGELOG.md` sections now use the standard headings, credit verified human contributors (#1214), restore merged changes and published details they had omitted, and correct factual errors such as the PyPI 1.2.2 statement; all 28 published GitHub Release pages were updated to match and re-verified ([#1153](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1153)) by @yeongseon.

### Tests

- **Pool recovery across CUBRID broker restarts** — live tests in `test/test_server_restart.py` run `cubrid broker restart` under a pycubrid `QueuePool`. They check that idle pooled connections are reused safely, that work interrupted by the restart fails as a disconnect and is neither stored nor replayed, and that concurrent write requests stay consistent with the table, where a request reported as failed may be stored only when its COMMIT reply was lost. Verified on CUBRID 10.2 and 11.4 with pycubrid 1.17.0 ([#1151](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1151)) by @yeongseon.

## [1.12.2] - 2026-11-05

This release clarifies setup and troubleshooting instructions, refreshes the documentation design, and expands development-tool tests. Application runtime behavior is unchanged.

### Changed

- **Contribution guidance** — Clarified how to report issues and write comments that explain the affected behavior ([#1060](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1060), [#1103](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1103)) by @yeongseon.

- **Documentation generation** — The documentation generator now stops if a required source page is missing, preventing incomplete output. Regression tests cover this check ([#1065](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1065)) by @anaylab (first contribution 🎉), co-authored by @yeongseon.

### Documentation

- **Documentation icons** — Updated the README, translations, site logo, and favicon to use the transparent ORM icon ([#1089](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1089), [#1090](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1090)) by @yeongseon.

- **Documentation theme** — Made the site's Python Yellow colors consistent ([#1093](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1093)) by @yeongseon.

- **FAQ and troubleshooting** — Clarified terminology in help text and diagnostic examples ([#1105](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1105)) by @AzalHoseinian (first contribution 🎉).

- **Async example setup** — Corrected the installation command and Docker instructions ([#1092](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1092)) by @bfs2021 (first contribution 🎉).

### Tests

- **Development-tool regression tests** — Added coverage for ORM profiler results, README translation checks, and release-note extraction failures ([#1068](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1068), [#1069](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1069), [#1094](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1094)) by @kcncb (first contribution 🎉).

- **Integration connection checks** — Added tests for running the connection-check script from the command line ([#1104](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1104)) by @WATSONSK14 (first contribution 🎉).

## [1.12.1] - 2026-10-27

This maintenance release updates documentation and improves development-test reliability. SQL generation, schema reflection, connections, and ORM behavior are unchanged.

### Documentation

- **Documentation icons** — Updated the README, its five translations, and the documentation site's logo and favicon to the Python Yellow cube icon ([#1051](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1051), [#1055](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1055), [#1064](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1064), [#1067](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1067)) by @yeongseon.

- **Contributor guidance** — Clarified how to write understandable issues, PRs, reviews, and release notes ([#1056](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1056)) by @yeongseon.

### CI

- **Driver-dependent tests** — CI now installs the optional `[pycubrid]` extra so benchmark-helper tests run. Local environments without the driver still skip those tests ([#1052](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1052), [#1049](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1049)) by @yeongseon.

- **Development dependencies** — Updated CI actions and release tooling; application runtime dependencies are unchanged.

  Updates: Ruff from 0.17.1 to 0.17.2, `actions/setup-python` from 7.0.0 to 7.1.0, `astral-sh/setup-uv` from 10.3.0 to 10.3.2, and `pypa/gh-action-pypi-publish` from 1.14.2 to 1.14.3; refreshed the pinned cookbook smoke-test workflow ([#1057](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1057), [#1058](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1058), [#1059](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1059)); automated dependency PRs, with a verified human co-author @yeongseon on #1058.

### Tests

- **Benchmark tests** — Added offline tests for summary statistics, timing conversion, and test-order rotation. These tests skip when `pycubrid` is unavailable ([#1039](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1039)) by @Nandankumarjv (first contribution 🎉), co-authored by @yeongseon.

- **Interrupted-query tests** — Fixed test cleanup and warning collection to prevent unrelated `ResourceWarning` failures in CUBRIDdb compatibility tests ([#1062](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1062), fixes [#1061](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1061)) by @yeongseon.

## [1.12.0] - 2026-10-25

This release improves the contributor verification workflow and its test reports. Contributors running `make verify` now need Docker; the published dialect's runtime API is unchanged.

### Upgrade notes

- **`make verify` requires Docker** — It now runs `make check`, the complete offline test suite, and live integration tests in sequence, including with `make -j`. For offline-only verification, use `make check test`.

  Live tests use `pycubrid` by default and fail if the database never becomes ready or every test is skipped. `make install` now includes `[pycubrid]`; the existing `CUBRID_PORT` fallback is unchanged ([#1045](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1045), [#1018](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1018)) by @yeongseon.

### Added

- **Verification reports** — `make verify` writes overall and per-phase results to `test-results/verify/summary.json`, including when a phase fails or the run is interrupted. Missing results and all-skipped live tests cannot report success; phases that never started are marked `NOT_RUN`.

  Available JUnit reports and redacted environment details are included. Each run clears previous test results; `make -n verify` writes no files ([#1047](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1047), [#1020](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1020)) by @yeongseon.

### Changed

- **New issues now enter maintainer triage** — issue templates, the issue-opening workflow, and issues created by the upstream canary apply `status: needs triage` without automatically deciding priority or size. The previous issue-metadata checking script was removed ([#1030](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1030), [#1028](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1028)) by @yeongseon.

### CI

- **CI test reports** — Live integration jobs now show their results in the GitHub Actions summary, including failed runs. Test selection, permissions, and log uploads are unchanged ([#1048](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1048), [#1021](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1021)) by @yeongseon.

## [1.11.7] - 2026-10-25

### Documentation

- **Simplified the agent commit-message example** — removed the agent-specific and tool-specific footer guidance from the repository's commit example. This is a documentation-only update; it does not change the dialect or runtime behavior ([#1043](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1043), [commit b51b29f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b51b29fa793d12d4ec54d9ef65adb3c43cd2ae5f)) by @yeongseon.

## [1.11.6] - 2026-10-24

### Documentation

- **Corrected an outdated pytest test reference** — updated the development documentation so its example points to a current test rather than a stale pytest node. This is a documentation-only update; it does not change runtime behavior ([#1034](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1034), [#1033](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1033), [commit 003dca4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/003dca4d9bf79aeb1d67814c5fa8e92824216405)) by @WilliamK112.

### CI

- **Removed a temporary release-preparation override** — after v1.11.5 was successfully published, the repository removed the now-obsolete `last-release-sha` setting from `release-please-config.json`. This allows subsequent release preparation runs to resume normal tag-based discovery; it does not change the dialect's runtime behavior or rewrite previously published releases ([#1038](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1038)) by @yeongseon.

## [1.11.5] - 2026-10-24

This release fixes SQL compilation and connection-handling issues, improves inline-literal safety, and strengthens development and test workflows. Versions 1.11.1–1.11.4 were not published; upgrade directly from v1.11.0 and review the notes below.

### Upgrade notes

- **Unpublished release candidates (1.11.1–1.11.4; #838, #910, #1005, #1011)** — None has a tag, GitHub Release, or PyPI version. Their gates failed on Python 3.15, CUBRIDdb integration (#1003), cookbook verification, and `make integration` (#1035), respectively. All their changes are included here; upgrade directly from v1.11.0 to v1.11.5.

- **Development test and lint commands changed (#1009)** — `make test` now runs all offline tests (previously `make test-offline`); the former fast suite is `make test-fast`. `make lint` checks Ruff lint only; use `make format-check` or `make check` for formatting. `make check` also runs type checking, security, and documentation checks. The old `make test-offline` and `make check-all` aliases still work ([#1010](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1010)) by @yeongseon.

- **Local Docker cleanup and broker access changed (#1008)** — `make docker-down` now preserves test data; use `make docker-clean` to remove volumes (the old `docker-down` behavior). The broker binds to `127.0.0.1` instead of all host interfaces. `CUBRID_TEST_PORT` (default 33000) controls the host port for `docker-up`, Compose, and integration; Compose may use `.env` when not explicitly set. `make integration` still cleans up its own test project ([#1017](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1017)) by @yeongseon.

- **MERGE assignment keys from other tables now raise `CompileError` (#847)** — A source-table column used as an UPDATE or INSERT assignment key previously resolved as the target column with the same name. Use the target's column (`target.c.name`) or string key `"name"`. The column-list shorthand `when_not_matched_then_insert([source.c.id, ...])` is unchanged ([#895](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/895)) by @yeongseon.

### Added

- **Offline tests now save results (#1019)** — `make test` writes `junit.xml`, `coverage.xml`, and `summary.json` to `test-results/test/`, including execution counts and `PASS`/`FAIL`/`INCOMPLETE` status. Failed suites still exit nonzero; test selection and the 95% coverage threshold are unchanged. Results are gitignored and removable with `make clean` ([#1022](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1022)) by @yeongseon.

- **Integration tests now save diagnostics (#1020)** — `make integration` writes JUnit results, a summary, and redacted environment details under `test-results/integration/`, plus `service.log` on failure. Missing results or all-skipped tests report `INCOMPLETE` and exit nonzero; cleanup failures and rejected runs report `FAIL`, not a stale success. Credentials are masked in recorded commands and logs. `INTEGRATION_RESULTS` changes the output directory ([#1032](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1032)) by @yeongseon.

### Changed

- **Development commands are clearer and interrupted integration runs clean up predictably (#1009)** — `make integration` delegates startup, readiness, signals, failure reporting, and cleanup to `scripts/run_integration.py`. If interrupted during `docker compose up -d`, it waits one `INTEGRATION_STOP_GRACE` interval for startup to finish, then sends SIGTERM and allows a second interval before SIGKILL; other interrupted steps receive SIGTERM immediately, then SIGKILL after the grace period. **Ordinary stalled Compose calls do not have a timeout.** New `test-fast`, `format-check`, and offline-only `verify` targets complement `make doctor` checks for Python 3.11+, missing tools, and Ruff/Mypy pins. `make format` verifies tool versions; CI runs lint and formatting separately. Tool commands remain overrideable through Make variables ([#1010](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1010)) by @yeongseon.

- **MERGE assignments validate target-column identity (#847)** — A bound assignment key in `when_matched_then_update()` or `when_not_matched_then_insert()` must refer to the target (including its alias), rather than a different table with the same column name. Invalid keys raise `CompileError` naming the other table. String keys, unbound `sa.column()` keys, and the column-list shorthand retain their previous name-based behavior; valid SQL and bind ordering are unchanged ([#895](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/895)) by @yeongseon.

### Deprecated

- **`make check-all` (#1009)** — an alias of `make check` that prints a deprecation notice on stderr; it will be removed after the next minor release. `make test-offline` remains an alias of `make test` ([#1010](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1010)) by @yeongseon.

- **`CUBRID_PORT` (#1008)** — the former name of `CUBRID_TEST_PORT`. It is still used when `CUBRID_TEST_PORT` is unset, by `make docker-up` and `make integration` (which then print a deprecation warning) and by `docker-compose.yml`; `CUBRID_TEST_PORT` wins when both are set. Other targets ignore it, so a `CUBRID_PORT` exported for another CUBRID tool does not make them warn ([#1017](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1017)) by @yeongseon.

- **Unused `display_width` and `values` type arguments (#870)** — `SMALLINT` / `BIGINT` accept `display_width` and `CHAR` / `VARCHAR` / `NCHAR` / `NVARCHAR` / `STRING` accept `values`, but neither ever changed the DDL or any behavior. Passing them now emits a `DeprecationWarning`; they are still accepted and ignored, and will be removed in a future major release. The unused private `CubridTypeCompiler._get` helper is gone ([#891](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/891)) by @yeongseon.

### Fixed

- **aggregate_order_by() on a filtered GROUP_CONCAT names FILTER in its error (#995)** — on SQLAlchemy 2.1, `aggregate_order_by(func.group_concat(col).filter(cond), col)` raised a `CompileError` saying `aggregate_order_by()` works only for `GROUP_CONCAT`, although the call already was one. The error now says that CUBRID has no `FILTER (WHERE ...)` clause. It still raises, and the rendered SQL of every other form is unchanged ([#996](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/996)) by @yeongseon.

- **aggregate_order_by() no longer drops its ORDER BY (#991)** — on SQLAlchemy 2.1, `func.group_concat(col).aggregate_order_by(col.desc())` rendered `GROUP_CONCAT(col)` and returned the values in an unspecified order without an error. It now renders `GROUP_CONCAT(col ORDER BY col DESC)`, also with `DISTINCT` and in `HAVING`; a boolean argument or `ORDER BY` item is grouped like any function argument (#970). Any other function with `aggregate_order_by()`, including `aggregate_strings()`, raises `CompileError`, because no other CUBRID aggregate takes an `ORDER BY` (verified for `JSON_ARRAYAGG`, `COUNT`, `MAX`, `SUM` and `MEDIAN`). `within_group()` and SQLAlchemy 2.0 are unchanged. Verified on CUBRID 11.4; not verified on 10.2, 11.0 or 11.2 ([#994](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/994)) by @yeongseon.

- **GROUP_CONCAT DISTINCT, ORDER BY and SEPARATOR no longer fail (#990, #984)** — the `GROUP_CONCAT` visitor wrapped its arguments in a second pair of parentheses, which CUBRID rejects around its modifiers (-493). `func.group_concat(col.distinct())` and a `literal_column("col ORDER BY col DESC SEPARATOR ';'")` argument now run. `GROUP_CONCAT` renders with only its argument-list parentheses, so `GROUP_CONCAT((x))` becomes `GROUP_CONCAT(x)`, as the documentation already showed. A boolean `EXISTS`, `NOT`, `AND` or `OR` argument is grouped once, like any function argument (#970), instead of three times: `GROUP_CONCAT((a = 1 AND b = 2))`. Values are unchanged; the change is otherwise compatible. `FEATURE_SUPPORT` now shows the supported forms and lists the unsupported ones: a separate `SEPARATOR` argument, more than one argument, and SQLAlchemy 2.1's `aggregate_strings()` (`aggregate_order_by()` is fixed by #991). Verified on CUBRID 11.4; not verified on 10.2, 11.0 or 11.2 ([#989](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/989)) by @yeongseon.

- **EXISTS and AND/OR as a simple CASE value no longer fail (#987)** — CUBRID rejects a bare `a AND b`, `a OR b`, `NOT (...)` or `EXISTS (...)` as the value operand of a simple `CASE` but accepts it inside parentheses. The `value=` operand of `case()` is now grouped like a `THEN` or `ELSE` value (#982), so `case({True: 10}, value=and_(...), else_=20)` and `case({True: 10}, value=exists(), else_=20)` run. A column, bind parameter, comparison or other non-boolean value and every other rendering are unchanged. The documentation now also states that CUBRID can reject a `CASE` whose results are boolean without a non-NULL `ELSE` (for example one with a single `WHEN`; "semantic error", -495), with or without grouping, so pass `else_=`; that CUBRID 11.4 evaluates any `CASE` used as a window `ORDER BY` or `PARTITION BY` item as a constant, without an error; and that a `CASE` with a boolean value fails as a `GROUP BY` item (-493). Verified on CUBRID 11.4; not verified on 10.2, 11.0 or 11.2 ([#988](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/988)) by @yeongseon.

- **EXISTS and AND/OR as a CASE THEN or ELSE value no longer fail (#982)** — CUBRID rejects a bare `a AND b`, `a OR b`, `NOT (...)` or `EXISTS (...)` as a `CASE` result value but accepts it inside parentheses. A `THEN` or `ELSE` value of a searched or simple (`value=`) `case()` is now grouped like a CAST or function argument, so `case((t.c.id > 0, and_(...)), else_=literal(False))` and `case((t.c.id > 0, exists()), else_=literal(False))` run. `CASE` `WHEN` conditions and every other rendering are unchanged. Verified on CUBRID 11.4; not verified on 10.2, 11.0 or 11.2 ([#985](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/985)) by @yeongseon.

- **Boolean expressions now compile in CAST, function, and some window arguments (#970)** — CUBRID requires parentheses around bare `EXISTS`, `NOT`, `AND`, or `OR` expressions used as CAST or function arguments in SELECT, filtering, joins, or updates. Window and `WITHIN GROUP` ordering/partitioning now group `EXISTS` and `NOT` items; for a directly supplied window `and_()` or `or_()`, SQLAlchemy first splits the expression into separate items (which can change the meaning). To retain that expression, use a list such as `over(order_by=[and_(...)])` or `.self_group()`. Bare `WHERE`/`HAVING`/`ON` conditions remain unchanged. CUBRID still rejects Boolean `GROUP BY` items, including function-wrapped items. The earlier unsupported-position guidance (#971) is updated in `docs/FEATURE_SUPPORT.md`. Verified on CUBRID 11.4; not verified on 10.2, 11.0 or 11.2 ([#972](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/972)) by @paikend.

- **EXISTS and AND/OR inside a CAST, a function or ORDER BY no longer fail (#968)** — CUBRID also rejects a bare `EXISTS (...)`, `NOT (...)` or `a AND b` / `a OR b` as a CAST or function argument and as an ORDER BY item (-493). The compiler now groups such an expression when the CAST or function is itself a SELECT column or ORDER BY item, also through `type_coerce()`, labels and sort modifiers. `select(type_coerce(exists(), Boolean))`, `select(cast(and_(...), Integer))`, `select(func.coalesce(exists(), False))`, a Boolean `TypeDecorator` whose `column_expression()` wraps the column, `order_by(and_(...))` and `order_by(exists())` now run. `WHERE`, `HAVING`, `ON`, `GROUP BY`, `CASE` conditions and window `ORDER BY` render as before. A boolean `GROUP BY` item stays unsupported: CUBRID rejects a search condition there even inside parentheses. Group by a SELECT-list label instead (documented in `docs/FEATURE_SUPPORT.md`) ([#969](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/969)) by @yeongseon.

- **Boolean expressions in SELECT lists now compile (#966)** — CUBRID rejects unparenthesized `EXISTS`, `NOT`, `AND`, and `OR` expressions in SELECT results. The dialect now groups these expressions, including labeled columns, subqueries, and CTEs; `select(exists().where(...))` and `session.query(q.exists()).scalar()` work. Their use in `WHERE`, `HAVING`, join conditions, and `CASE` conditions remains unchanged ([#967](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/967)) by @paikend.

- **Repeated isolation re-apply failures no longer lose the retry marker (#937)** — After a successful commit or rollback, `do_begin()` already retried an isolation-level re-apply that failed. Previously, if this retry also failed, it cleared the pending marker too early, so a subsequent **direct dialect `do_begin()`** could start work without restoring the level. The marker now stays pending until re-apply succeeds; setting a new level settles it. SQLAlchemy's normal `Connection` rollback had masked this gap in the observed reproduction. The preceding commit/rollback remains successful and no work is replayed. Applies to `cubrid+pycubrid://` and `cubrid+aiopycubrid://` ([#947](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/947)) by @yeongseon.

- **Server errors no longer cause false disconnects (#916)** — With pycubrid 1.13's `error_source == "server"`, sync and async connections no longer treat unrelated server error codes (-1000 to -1200) or misleading error text as CAS connection failures. Actual CAS errors, unknown origins, and pycubrid versions before 1.13 retain previous behavior; the supported pycubrid range is unchanged ([#938](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/938)) by @yeongseon.

- **`bool` JSON path indices are rejected (#914)** — `bool` is an `int` subclass, so `json_col[True]` and `json_col[("items", False)]` rendered the paths `$[True]` and `$."items"[False]`. CUBRID 10.2 and 11.4 reject these as invalid JSON paths (`-494`), but the statement had already been sent. `JSONIndexType` and `JSONPathType` now raise `TypeError` for a `bool` component. Execution reports it as `sqlalchemy.exc.StatementError` before any SQL is sent, and `literal_binds` rendering as `sqlalchemy.exc.CompileError`. Integer (including `0`, `1` and negative) and string components render byte for byte as before, on SQLAlchemy 2.0 and 2.1. The Types guide lists the supported path component types ([#917](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/917)) by @yeongseon.

* **scripts:** dispose reflection probe engine on every exit path ([#977](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/977)) ([1303262](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/13032624148045302d0edcdfe245a28ce4c20f01)) by @CloudCorpRecords

- **`INSERT` / `REPLACE ... FROM SELECT` over a CTE renders the `WITH` clause after the column list (#897)** — SQLAlchemy put the CTE first (`WITH c AS (...) INSERT INTO t (...) SELECT ...`), which CUBRID 10.2 and 11.4 reject with a -493 syntax error, so `insert(t).from_select([...], select(cte))` and the dialect's `replace()` equivalent always failed. The dialect now sets `cte_follows_insert`, rendering `INSERT INTO t (...) WITH c AS (...) SELECT ...`, the order CUBRID accepts; recursive CTEs and bind order are unchanged. `TestIsolatedCTE849::test_insert_from_select` is no longer a strict xfail, and live INSERT, recursive INSERT and REPLACE cases pass on CUBRID 10.2 and 11.4 ([#899](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/899)) by @yeongseon.

- **Unique-constraint reflection fails closed on a catalog mismatch (#848)** — `get_unique_constraints()` took the unique index names from `db_index` and their columns from `SHOW INDEXES`, and returned only the names `SHOW INDEXES` resolved. A unique index the catalog listed but `SHOW INDEXES` omitted was therefore reported as absent, which Alembic autogenerate would read as a constraint to create. Such a mismatch now raises `InvalidRequestError` naming the unresolved and resolved indexes. A verified-empty catalog still returns `[]`. No such mismatch has been seen on a live CUBRID server; this hardens the reflection invariant ([#896](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/896)) by @yeongseon.

- **Garbage-collected async connections are terminated (#872)** — the `cubrid+aiopycubrid://` adapter had no terminate support, so when a checked-out connection was garbage-collected the pool logged "cannot be safely terminated" and the unclosed stream raised a `ResourceWarning`. The adapter now uses SQLAlchemy's `AsyncAdapt_terminate` (SQLAlchemy 2.0.44+; earlier 2.0 releases keep the old behavior): the garbage-collection path closes the socket synchronously and retires the pycubrid session, also when the connection's event loop has already closed, an invalidated connection closes with `CLOSE_DATABASE`, and the dialect sets `has_terminate` ([#894](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/894)) by @yeongseon.

- **`on_duplicate_key_update()` is cacheable (#871)** — `OnDuplicateClause` had no `_traverse_internals`, so the first `INSERT ... ON DUPLICATE KEY UPDATE` emitted SQLAlchemy's "will not make use of SQL compilation caching" `SAWarning` and every such statement was compiled again on each execution. It now declares the column order and the update values as cache-key elements (the traversal of SQLAlchemy 2.1's MySQL construct), with the update values coerced to SQL expressions; a cached statement binds each execution's own values, on SQLAlchemy 2.0 and 2.1 ([#893](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/893)) by @yeongseon.

- **Reflection of names containing `:name`, collection type classes and join linting (#870)** — the `SHOW COLUMNS` / `SHOW INDEXES` / `SHOW CREATE TABLE` / `SHOW CREATE VIEW` statements were built with `text()`, so a table named `x :y` or `w (:z)` failed with "A value is required for bind parameter 'y'"; colons are now escaped, and the SQL sent is unchanged. `SET(Integer)` (a type class, which SQLAlchemy accepts elsewhere) failed `create_all` with "_compiler_dispatch() missing ... 'visitor'"; collection member classes are now instantiated. `visit_join` dropped `from_linter`, so SQLAlchemy reported a joined select as a cartesian product and missed a real one; the join edges are now recorded as in the base compiler ([#891](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/891)) by @yeongseon.

- **Expression, descending, filtered and prefix indexes reflect and autogenerate (#869)** — `get_indexes()` reported `CREATE INDEX ix ON t (LOWER(a))` as `column_names: [None]` without `expressions`, so `Table` reflection warned "Skipping index" and dropped it and autogenerate proposed it again on every run, and `b DESC`, `WHERE c > 3` and the prefix `a(5)` reflected as plain columns. The `SHOW INDEXES` `Func`, `Collation` and `Sub_part` columns and `db_index.filter_expression` now map to `expressions`, `column_sorting` and the new `cubrid_where` / `cubrid_length` index options, with the table qualifier CUBRID prints dropped (`lower([a])`, `c>3`). `CREATE INDEX` renders `cubrid_where` and `cubrid_length`, which were silently ignored before, and the Alembic implementation compares these keys after normalizing both sides (outside string literals), so autogenerate no longer proposes an unchanged index again; detecting a changed sort order, filter or prefix length needs Alembic 1.12+ ([#885](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/885)) by @yeongseon.

- **Alembic renders CUBRID collection member types with the dialect prefix (#868)** — `render_type` wrote every member type with `sa.`, so autogenerate produced `cubrid_types.MULTISET(sa.MONETARY())` or `cubrid_types.SEQUENCE(sa.BIT(length=8))`, which raised `AttributeError` when the migration file was loaded. Member types from `sqlalchemy_cubrid.types` now render as `cubrid_types.MONETARY()`, `cubrid_types.BIT(length=8)` and so on; generic SQLAlchemy members keep `sa.` ([#884](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/884)) by @yeongseon.

- **`Select.fetch()` renders as `LIMIT` (#867)** — there was no `fetch_clause` override, so `select(...).fetch(2)` and `.offset(1).fetch(2)` emitted the generic `OFFSET ... ROWS FETCH FIRST n ROWS ONLY`, which CUBRID rejects with -493. They now render as `LIMIT 2` and `LIMIT 1, 2`; `percent=True` and `with_ties=True` raise `CompileError`, since CUBRID has no `LIMIT` form for them ([#880](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/880)) by @yeongseon.

- **JSON path keys use JSON string escaping (#866)** — `col["key"]` and `col[("a", "b")]` doubled a `"` in the key, which CUBRID reads as a JSON string: `doc['a"b']` failed with -1200 "Invalid JSON path" and `doc['a\\b']` silently returned `None`. Keys are now built with `json.dumps()`, so `"` and `\` are backslash-escaped and non-ASCII characters become `\uXXXX` escapes that do not depend on the connection charset ([#879](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/879)) by @yeongseon.

- **String and date server defaults reflect as quoted SQL literals (#865)** — `get_columns()` returned the `SHOW COLUMNS` default text, which drops a string's quotes: `DEFAULT 'it''s'` reflected as `it''s`, `''` as an empty string and the string `'NULL'` as `NULL`, a date as `01/02/2020`, and `'CURRENT_USER'` the same as the `USER` function. Reflecting and then emitting `CreateTable` produced `DEFAULT it''s` and `DEFAULT ,`, and Alembic's `existing_server_default` carried the bad value into `MODIFY`. Non-numeric defaults are now read from `SHOW CREATE TABLE` (one extra query per table that has one) and reflect as `'it''s'`, `''`, `'NULL'`, `date '01/02/2020'` or the function itself (a string column's `'5'` as `'5'`); numeric defaults of numeric columns are unchanged ([#878](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/878)) by @yeongseon.

- **Alembic `alter_column` emits CUBRID-compatible SQL for nullability, dropped defaults and comments (#861)** — these changes went to Alembic's generic SQL, which CUBRID rejects: `nullable=` emitted `ALTER COLUMN c SET/DROP NOT NULL`, `server_default=None` emitted `DROP DEFAULT` (both syntax errors), and `comment=` raised "can't render element of type ColumnComment", so any autogenerated nullability change failed at `upgrade`. Nullability and comment changes now go through `MODIFY` / `CHANGE` (a missing `existing_type` raises `ValueError`), and a dropped default emits `ALTER COLUMN c SET DEFAULT NULL`, or two `MODIFY` statements for a `NOT NULL` column. Because CUBRID 10.2/11.0 reset an attribute that `MODIFY` omits and 11.2+ keep it, the definition now states `NULL` for a NOT NULL to nullable change, `DEFAULT NULL` for a dropped default and `COMMENT ''` for a removed comment; an existing column without a default no longer gets `DEFAULT NULL`. A UNIQUE `create_index` in offline `--sql` mode raises the documented "live connection" `CompileError` instead of `NoInspectionAvailable` ([#877](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/877)) by @yeongseon.

- **`literal_binds` and other compile options reach CAST operands, ON DUPLICATE KEY UPDATE values and collection members (#862)** — the nested `process()` calls in four places (`visit_cast`, both ON DUPLICATE KEY UPDATE value paths and collection member DDL) dropped the compile keyword arguments, so `CAST(t.name || ? AS VARCHAR(10))` and `ON DUPLICATE KEY UPDATE name = ?` kept placeholders under `literal_binds`, `server_default=cast(literal(5), String(10))` rendered `DEFAULT CAST(? AS VARCHAR(10))` and failed `create_all` with "wrong number of parameters", a functional `Index` over a `CAST` rendered a `?`, and Alembic `--sql` output contained placeholders. CUBRID itself still rejects `CAST` in a function-based index on 10.2 and 11.4 ([#875](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/875)) by @yeongseon.

- **`has_table()`, `get_table_names()` and `get_view_names()` see only the current owner's classes on CUBRID 11.2 and later (#864)** — `db_class` lists every owner's classes the user may read, but an unqualified name resolves only in the current user's schema. With another user's `own_t` present, `has_table("own_t")` was `True` for `dba`, so `create_all()` skipped `dba.own_t` and the next `INSERT` failed with `Unknown class "dba.own_t"`; `MetaData.reflect()` aborted with `NoSuchTableError`; and two owners' same-named tables were listed twice. These methods now filter on `owner_name = CURRENT_USER`. CUBRID 10.2 and 11.0 are unchanged ([#876](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/876)) by @yeongseon.


### Security

- **Inline literals follow the server's backslash mode (#863)** — the dialect assumed `no_backslash_escapes=yes` unless told otherwise, so on a server with `no_backslash_escapes=no` the value `\' OR 1=1 -- ` rendered with `literal_binds` as `'\'' OR 1=1 -- '` and the compiled SQL matched every row. When `create_engine(no_backslash_escapes=...)` is not passed, the first connection now probes the server with `SELECT CHAR_LENGTH('\\')` and literal rendering doubles backslashes when the server treats them as escapes; an unexpected probe result fails the connection. Native `ENUM` labels now use the same escaping. An explicit option still pins the mode and skips the probe; a dialect that has not connected still assumes the server default ([#874](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/874)) by @yeongseon.

### Documentation

- **The architecture pages show the end-to-end driver communication flow (#1013)** — `docs/ARCHITECTURE.md` and `docs/ko/ARCHITECTURE.md` gain an "End-to-End Communication Architecture" section with a Mermaid component diagram that maps the three URL variants (`CubridDialect` with `CUBRIDdb` and CCI, `PyCubridDialect` with `pycubrid`, `PyCubridAsyncDialect` with `pycubrid.aio`) to the Broker, the CAS process and the database server, with the dialect's responsibilities, the meaning of CCI, CAS and the CAS wire protocol, and the connection lifecycle. The README architecture diagram links to it. `mkdocs.yml` now registers the `mermaid` SuperFences custom fence, so the documentation site renders the Mermaid diagrams on every page (they were shown as code listings before). Documentation only; no behavior change ([#1016](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1016)) by @yeongseon.

* **agents:** require repository-local issue authoring checks ([#1012](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1012)) ([7a15ad7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7a15ad76d2fb0e98e8026f0fae9c1324463db781)) by @yeongseon.

* **contributing:** fix single-test pytest node example ([c04a380](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c04a380f4b9a512fa8ecb892324fe6b59fde31b7)), refs [#881](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/881) ([#1029](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1029)) by @HarshRajSinghania

* **triage:** clarify PR overlap and execution precedence ([1d082cc](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1d082ccccb2010b2ab6db474eaeca770431a6b7e)), refs [#1023](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1023) by @yeongseon.

- **Two CUBRIDdb result differences are documented (#1003)** — CUBRIDdb binds values on the server, where pycubrid writes them into the SQL. With CUBRIDdb a `CASE` whose `THEN`/`ELSE` values are all bound parameters returns a string (`'10'`, not `10`), and a `GROUP_CONCAT` argument and `aggregate_order_by()` item that contain bound parameters fail with -494, because the server does not treat the two copies as the same expression. The Driver Compatibility guide describes both with their workarounds (`cast(..., Integer)`; an argument position such as `aggregate_order_by(literal_column("1"))`), and the Feature Support pages link to it. The dialect is unchanged ([#1004](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1004)) by @yeongseon.

- **Boolean expressions that still failed on CUBRID (#968)** — superseded by the #970 fix above: those forms now run, and the `docs/FEATURE_SUPPORT.md` note that listed them, with its `case()` workaround, is replaced. Do not use that workaround inside a window: CUBRID 11.4 evaluates a `CASE` (or `if()`) in a window `ORDER BY` or `PARTITION BY` as a constant, so the window ignores it ([#971](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/971)) by @yeongseon.

- **The first-connection course has one page per lesson (#943)** — the rest of the course moves out of the Quick Start page into Lesson 3 (save a row and read it back through a separate connection, `save_row.py`), Lesson 4 (a transaction undone with `rollback()`, `rollback_row.py`, which shows the row count inside the transaction and can be rerun) and Lesson 5 (the owner- and comment-checked cleanup and removing the lab with `docker rm -f -v`), in English and Korean. The former single `first_saved_row.py` is split between Lessons 3 and 4; the table, its marker comment and the cleanup script are unchanged. The Quick Start page lists all five lessons, keeps the first-connection error table and next steps, and keeps its former "Step 3" and "Clean up" anchors as short "moved to" sections. Every command was rerun against `cubrid/cubrid:11.4` with the published SQLAlchemy 2.1.4, sqlalchemy-cubrid 1.11.0 and pycubrid 1.13.0, including reruns and the rollback before Lesson 3 ([#956](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/956)) by @yeongseon.

- **The first-connection course starts with two lesson pages (#943)** — preparing CUBRID and Python (`docs/LESSON_PREPARE.md`: an existing database's values or the disposable Docker lab, and the virtual environment) and running the first query (`docs/LESSON_FIRST_QUERY.md`) are now separate pages, each with a goal, prerequisites, the commands, the real output and a next step, in English and Korean, listed under Start here. The Quick Start page is the course landing: it lists the lessons, keeps the save-a-row, cleanup and first-connection-errors sections, and keeps its former anchors as short "moved to" sections. The lab's readiness loop and the first script are wrapped to fit narrow screens, the site shows previous/next links at the bottom of each page, and the documentation home links the lab in Lesson 1. Every command was rerun as written against `cubrid/cubrid:11.4` with the published SQLAlchemy 2.1.4, sqlalchemy-cubrid 1.11.0 and pycubrid 1.13.0 ([#955](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/955)) by @yeongseon.

- **The documentation site is organized by reader question (#943)** — the navigation (English and Korean) now has Start here (the first-connection course), How-to guides (connecting and configuring the driver, the ORM, Alembic, CUBRID-specific DML, isolation levels), Reference (types, feature support, support matrix, driver compatibility, including the supported CUBRIDdb C-extension driver), Help (troubleshooting, issues, private security reports) and Project and internals, instead of Getting Started/Usage/Reference/Operations/Project; the home pages list the same sections. No page moved and no URL changed. `docs/agents/documentation.md` records the page map with each page's reader, question and decision, and the lesson pattern for the upcoming first-connection lessons. Two paragraphs that a following `---` rule turned into accidental headings (in the Connection guide and Feature Support) are plain paragraphs again, so they no longer appear in the page tables of contents ([#954](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/954)) by @yeongseon.

- **Development documentation now identifies unreleased content (#946)** — The English and Korean documentation home pages explain that the site is built from `main` and may describe candidate or abandoned changes. The MkDocs provenance hook records the exact source commit from `GITHUB_SHA` or `git rev-parse HEAD`, not PyPI; the Quick Start identifies the published 2026-10-15 package versions used for its examples. `RELEASING.md` distinguishes candidates, partial publication, abandoned versions and verified published distributions (or unknown status when external services cannot be read). It also explains observed bot-PR CI states, including `action_required` (observed on #910), zero-job runs and stale heads, plus the evidence to record before merging and after publication. A value in `main`'s `__version__` is not proof of a published package ([#951](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/951)) by @yeongseon.
- **The quickstart removes the lab's Docker volume too (#948)** — the `cubrid/cubrid` images keep their database in an anonymous volume (`/home/cubrid/CUBRID/databases` in 11.4), and `docker rm -f` without `-v` left that volume, with the tutorial's `testdb`, behind on every run. The Quick Start (English and Korean) now removes the lab with `docker rm -f -v sqlalchemy-cubrid-quickstart` and explains what `-v` deletes ([#949](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/949)) by @yeongseon.

- **The README async examples are complete programs (#941)** — the `Async` and `Async insert with PK retrieval` examples put `async with` and `await` at module level, a `SyntaxError` in an ordinary script. Each is now a named script that runs `async def main()` through `asyncio.run(main())`, creates its engine inside the event loop and always awaits `engine.dispose()`. The query example prints `2`. The insert example creates its own `sqlalchemy_async_example_notes` table instead of assuming a `users` table, refuses to reuse an existing one, reads the flushed row back through a new session and drops the table again, also after a failed statement or Ctrl+C. Both were run against CUBRID 11.4. The Korean README carries the same programs, and the German, Hindi, Russian and Chinese READMEs the corrected query example. A new offline test compiles every async README example as a plain script and checks that the translations repeat the English programs; the always-running lint job runs it, so README-only changes are checked too ([#944](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/944)) by @yeongseon.

- **A first SQLAlchemy connection for CUBRID beginners (#940)** — the Quick Start guide (English and Korean) is now one recommended path: the roles of SQLAlchemy, the dialect, the pycubrid driver and the CUBRID server, the five connection values for an existing database or a disposable local Docker lab, `sqlalchemy-cubrid[pycubrid]` in a virtual environment, a first `SELECT 1 + 1`, and a first committed row read back by a separate connection with a rollback demonstration, followed by an owner- and comment-checked cleanup script and the real first-connection error messages. Every command was run as written against CUBRID 11.4. Alternative drivers, URL forms, the ORM, async code and Alembic follow as next steps. The README and the documentation home start with a link to it, the README Quick Start states its `demodb` placeholder values, and the home page's minimal example uses the recommended `cubrid+pycubrid://` URL. The CUBRIDdb C-extension driver built from source stays supported; only the `[cubrid]` and `[cubriddb]` extras are deprecated ([#942](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/942)) by @yeongseon.

- **CAS error -4 is described as an interrupted statement (#873)** — pycubrid 1.13.0 reports -4 (`ER_INTERRUPTED`, a `KILL QUERY`) as `Interrupted` with SQLSTATE `HY008`. The Driver Compatibility, Connection and Troubleshooting guides (English and Korean) and a dialect comment now say so, and note that earlier pycubrid releases reported it as a communication error (`08S01`). The dialect's behavior is unchanged: -4 remains a non-disconnect, as it has been since 1.9.0 (#572). The Driver Compatibility guide also cites the CUBRID source for why -671 (`ER_CSS_RECV_OR_SEND`) is not a disconnect code: the CAS resets only for the four session-lost server codes ([#939](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/939)) by @yeongseon.

- **A maintainer's review is the standalone-agent alternative to Copilot (#926)** — `AGENTS.md` and `CONTRIBUTING.md` now say that a standalone agent PR waits for a substantive submitted GitHub Copilot review or a maintainer's review, recorded on the PR, instead of "another person's" review (maintainer decision, 2026-10-15). A reviewer agent run by the implementer does not count. The Korean contributor guide's review process now states the same route instead of "at least one review" ([#927](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/927)) by @yeongseon.

- **Agent guidance split into task guides (#907)** — the root `AGENTS.md` (618 lines, 36,498 bytes) keeps the overview, commands, code conventions and every review, issue, label, documentation, commit and release rule, and gains a task routing table for compiler and DML, reflection and types, Alembic, drivers and async, tests and CI, documentation and support claims, release and performance work. The architecture map, CUBRID-specific dialect knowledge, test structure, CI/CD, documentation map and performance context moved unchanged to `docs/agents/`. The root file is now 453 lines and 28,029 bytes. `scripts/check_agents_docs.py` checks the links, anchors, guide reachability, `make` targets, script paths and the `requires-python`/SQLAlchemy pins quoted in the root file against `pyproject.toml`, and with `--retained-from REF` that no line of an earlier `AGENTS.md` was dropped. No code, CI or release behavior changes ([#918](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/918)) by @yeongseon.

- **Python 3.15 limitation of garbage-collected connection cleanup (#872)** — with SQLAlchemy 2.1 (2.1.0 to 2.1.4 checked) on CPython 3.15, the pool never cleans up a pooled connection that Python's cycle collector reclaims, such as one lost while its autobegun transaction is still open. CPython 3.15 clears weak references later (python/cpython#136189), and SQLAlchemy 2.1's pool finalizer then returns early: the connection is not terminated, its socket closes only through Python's stream finalizer with a `ResourceWarning`, and the pool slot stays checked out. This affects every dialect, sync pools included. SQLAlchemy 2.0 and Python 3.14 and earlier are not affected, and the dialect's own terminate path is unchanged. The Connection Guide and the Support Matrix describe the limitation ([#909](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/909)) by @yeongseon.

* **contributing:** clarify good-first-issue access for human contributors ([#913](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/913)) ([7a2512f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7a2512f4694ee5129081ad87a449cae8bb3d4a88)) by @yeongseon.

* correct the documented boolean expression positions ([#986](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/986)) ([7c7958b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7c7958be8e82fa49dd3fb56591ad5a5108e16e30)) by @SuellenQwQ (first contribution 🎉)

* **types:** correct the namespace of reflected timezone types ([#973](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/973)) ([9480036](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/9480036c1a184d6227c93562c67452ded57cfbc8)), refs [#882](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/882) by @CloudCorpRecords (first contribution 🎉)

- **The README and the documentation site show the CUBRID Lab repository icon (#886)** — the English README and its Korean, Chinese, Hindi, German and Russian translations open with the sqlalchemy-cubrid ORM icon, centered and without a caption, and the documentation site uses it as its header logo and favicon. All of them load the SVG from one immutable [cubrid-lab/brand](https://github.com/cubrid-lab/brand) commit ([#900](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/900)) by @yeongseon.

- **`ROADMAP.md` no longer presents shipped releases as plans (#833)** — the stale "Current Release Line — v1.8.x" heading is now "Current Focus", the Python 3.10 retirement (shipped in 1.10.0) and Python 3.15 support (shipped in 1.11.0) moved to Completed with their release dates, and the Compatibility section and the header link to `CHANGELOG.md`, PyPI and `docs/SUPPORT_MATRIX.md` instead of repeating version numbers. The 2026-10-02 decisions are kept as dated history ([#844](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/844)) by @yeongseon.

- **`docs/PERFORMANCE.md` has a current same-CUBRID baseline (#830)** — raw pycubrid, SQLAlchemy Core and ORM measured on one CUBRID 11.4 server at `main` `a570ea4` (dialect source as in v1.11.0) with pycubrid 1.12.0, SQLAlchemy 2.1.4 and 2.0.54 and Python 3.12: single-row CRUD, fetch, the statement cache on and off, 1,000-row `executemany` and bulk INSERT/UPDATE/DELETE, reflection and offline compilation, 5 trials each with medians and interquartile ranges. The new `scripts/bench_dialect_baseline.py` covers what the existing tools did not (cache, batch DML, reflection, checked results); the raw files, the exact commands and `summary.json` are in `benchmarks/2026-10-12-dialect-baseline/`. The section also records the feasibility of pycubrid's opt-in `executemany(prepared=True)`, which the dialect does not use. Historical figures are now dated. No dialect hotspot or regression was found; runtime behavior is unchanged ([#843](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/843)) by @yeongseon.

- **The dialect baseline now covers CUBRID 10.2, 11.0 and 11.2, CUBRIDdb, the async driver and concurrent connections (#830 follow-up)** — `docs/PERFORMANCE.md` (+ Korean) adds a 2026-10-13 run of `scripts/bench_dialect_baseline.py` on CUBRID 10.2, 11.0, 11.2 and 11.4 through `cubrid+pycubrid://`, `cubrid://` (CUBRIDdb built from cubrid-python v11.3.0.51) and `cubrid+aiopycubrid://`, 5 trials each. The script gained a CUBRIDdb route, an async mode and a `--concurrency` workload (one-row SELECTs and committed UPDATEs on 1, 4 and 8 connections); raw files, commands and `summary.json` are in `benchmarks/2026-10-13-dialect-baseline-followup/`. Reads differ little between servers and drivers; pycubrid and the async driver scale with connections, while CUBRIDdb, whose C extension never releases the GIL, does not scale across threads. Runtime behavior is unchanged ([#860](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/860)) by @yeongseon.

- **The feature support table no longer marks CUBRID `BLOB` / `CLOB` as fully supported (#829)** — `docs/FEATURE_SUPPORT.md` (and its Korean page) shows ⚠️ in the CUBRID `BLOB` and `CLOB` cells, with a note that separates the supported parts (DDL and type mapping, reflection, binding `bytes` / `str`, `NULL` round trips) from the ordinary Core/ORM read of a non-NULL value, which returns the driver's LOB locator on `cubrid://`, `cubrid+pycubrid://` and `cubrid+aiopycubrid://`. The note links Known Issue 6 in `docs/DRIVER_COMPAT.md`. Documentation only; runtime behavior is unchanged ([#842](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/842)) by @yeongseon.

* **agents:** correct stale entry points, integration commands and doc map in AGENTS.md ([#846](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/846)) ([340a587](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/340a587ae1cfe6f98123669f25555948f84255cd)) by @yeongseon.

* **i18n:** update the Python requirement in the German README ([#837](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/837)) ([fcdb443](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fcdb443891cef3a2109e9f419b5ba374434401b9)), refs [#698](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/698) by @yeongseon.

* **i18n:** update the Python requirement in the Hindi README ([#839](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/839)) ([3f79d2d](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3f79d2db34694417f31b46f0573f2038d6c2a0ee)), refs [#699](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/699) by @yeongseon.

* **i18n:** update the Python requirement in the Russian README ([#840](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/840)) ([793b6ef](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/793b6ef8d6a5b7a764b8589bef6d77b90da84fbf)), refs [#700](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/700) by @yeongseon.

### CI

* **release:** restart release preparation after the abandoned 1.11.4 ([#1037](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1037)) ([3184d9b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3184d9b462bae6e2dd50d187e33abf83f44e5775)), refs [#1011](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1011) by @yeongseon.

- **CI publishes the offline test summary and uploads results on success and failure (#1021)** — the `offline-tests` and `offline-endpoints` jobs write JUnit, coverage and `summary.json` under `test-results/offline/` with `scripts/report_test_results.py`, append the summary to the job summary through its new `step-summary` subcommand and upload `test-results/`; the integration jobs upload their pytest logs. Every one of those steps runs with `if: always()`, so a failing run keeps its evidence. Test selection, the 95% coverage floor and the permissions are unchanged. The summary of the live lanes follows #1020 ([#1027](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1027)) by @yeongseon.

- **The `make-integration` jobs also upload `test-results/integration/` (#1020)** — the live results of `make integration` join `make-integration.log` in the existing `pytest-logs-make-integration-*` artifact; nothing else in the workflows changes ([#1032](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1032)) by @yeongseon.

- **A change to `docker-compose.yml` runs the test that pins it (#997)** — `test/test_make_integration.py` checks the Compose file's `CUBRID_DB_HOST`, but it is a repository-tooling module, which runs only in `repo-tests` when the `tooling` path filter matches, and that filter did not list `docker-compose.yml`. A pull request changing only that file ran none of the tests that check it. The filter now lists it; which tests each lane runs is unchanged ([#999](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/999)) by @yeongseon.

* **release:** verify against the current cookbook and restart after the abandoned 1.11.3 ([#1007](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1007)) ([72bf7be](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/72bf7be9fa0ab27454401b21972a080edd796d13)) by @yeongseon.

* **release:** start release preparation after the abandoned 1.11.2 ([#1006](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1006)) ([b1a2dfe](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b1a2dfe825c983a2114025b8cbaa82ff4da6c09d)) by @yeongseon.

- **The CUBRID 11.4 local Docker test database is kept in a named volume (#1000)** — `docker-compose.yml` mounted its named volume only at `/var/lib/cubrid`, where images up to 11.3 keep their databases; `cubrid/cubrid:11.4` keeps them in `/home/cubrid/CUBRID/databases`, so with `CUBRID_VERSION=11.4` the database lived in an anonymous volume, `docker compose down` lost it (`Unknown class "dba.keep_me"` after the next `up`) and left that volume dangling. A second named volume, `cubrid-databases`, now holds that path, `make docker-down` deletes both, and `make integration`'s ownership check also refuses a pre-existing `<project>_cubrid-databases`. Checked on CUBRID 10.2, 11.2 and 11.4: a table created before `down` is still there after `up`, and `make docker-down` leaves no volume behind. Opening a database created by another CUBRID version is not verified, so the guides say to reset before switching `CUBRID_VERSION`. The same fix landed in pycubrid (cubrid-lab/pycubrid#1004) ([#1001](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1001)) by @yeongseon.

- **The local Docker test database keeps working after its container is recreated (#997)** — the image registers the database in `databases.txt`, which images up to 11.3 keep on the `cubrid-data` volume (11.4: see #1000 above), for `CUBRID_DB_HOST`, or, when that is unset, for the creating container's hostname, its container ID. `docker-compose.yml` did not set it, and `docker compose down` keeps the volume, so after `make docker-up` or `docker compose up -d` recreated the container, every connection failed with -353 (`Failed to connect to database server, 'testdb', on the following host(s): <old container ID>`). `docker-compose.yml` now sets `CUBRID_DB_HOST: localhost`, which a recreated container resolves. A volume created before this change keeps the old ID: `make docker-fix-db-host` rewrites only `testdb`'s host field to `localhost`, keeps the data and saves the previous file as `databases.txt.before-fix-db-host` on its first run, and `make docker-down` (`docker compose down -v`) deletes the volume and its data. `make integration` was not affected (it uses a run-owned Compose project removed with `down -v`), though its fresh containers now also register `localhost`; CI (service containers) and the dialect are unchanged. The same fix landed in pycubrid (cubrid-lab/pycubrid#1001) ([#998](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/998)) by @yeongseon.

- **Repository-tooling tests run when only their inputs change (#964)** — `repo`-marked tests run only in the `repo-tests` job, which starts when the `tooling` path filter matches, and the filter missed `agent-evals/**` and ten repository-tooling test modules (`test_agent_eval.py`, `test_bench_artifact.py`, `test_check_docs_translation.py`, `test_docs_provenance_hook.py`, `test_docs_reason.py`, `test_make_integration.py`, `test_release_detect.py`, `test_sqlalchemy_range.py`, `test_support_claims.py`, `test_verify_dist.py`). A pull request changing only an agent-evals task or one of those modules ran none of them. `ci.yml` now lists them and `test/conftest.py`, where `REPO_TOOLING_MODULES` is defined, and `test_workflow_path_impact.py` checks that every `REPO_TOOLING_MODULES` entry selects the tooling lane. `docs/CI_POLICY.md` (English and Korean) says so. No lane, marker or other filter changes ([#965](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/965)) by @yeongseon.

- **Manual agent runs are recorded and summarized as distributions (#906)** — `scripts/agent_eval.py` adds `prompt` (the task statement and the `report.json` format without the grading key: no fix commit, allowed files, docs decision or expected result), `record` (one run's agent and model identity, task revision and prompt digest, starting SHA, reported and observed commands, live checks reported as not run, changed files, optional wall-clock time, review findings, an optional exclusion reason for a run that is not a fair sample, and the rubric result) and `summarize` (per task revision and model: run count, verdict counts, criteria that did not pass, wall-clock range, excluded runs counted apart, and a 95% Wilson interval, never a bare pass percentage). `agent-evals/README.md` describes the manual-only protocol: an isolated clone without later history or a push remote, no publish credentials, and the grader run from the repository's own checkout. Nothing runs an agent in CI, and no score gates a pull request ([#963](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/963)) by @yeongseon.

- **Agent evaluation tasks for reflection and Alembic (#906)** — `agent-evals/` adds two tasks from documented fixes: `reflect-string-server-defaults` (#865, server defaults reflected against recorded catalog rows) and `alembic-alter-column-sql` (#861, Alembic `alter_column` SQL). Neither has recorded live evidence; the Alembic task is the deliberate case where the fix depends on server-version behavior, so a candidate passes only if it reports the live migration check as not run and says live behavior is not verified. Each task has evaluator-owned hidden tests of its contract (failing at the base SHA, passing at the fix; the reflection one answers by statement text, so it does not depend on query order), a reference fix and failure fixtures (tests and docs without the source fix, a false live claim, offline results reported as live, and for Alembic a missing *not verified* statement) whose dry-run results are real `run` output. No dialect source or CI lane changes ([#962](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/962)) by @yeongseon.

- **Offline agent evaluation tasks and grader (#906)** — `agent-evals/` adds a versioned task format for benchmarking coding agents on frozen historical fixes, and `scripts/agent_eval.py` grades a candidate's patch, test report and dry-run result: the task's offline tests and evaluator-owned hidden tests at its base SHA (a pytest run that skips every test is not a pass), the regression test, allowed files, affected documentation, the CHANGELOG section, and claims. A live CUBRID claim without a passing recorded live run (each clause is checked on its own), an unreported live check, compiled or bound SQL reported as live evidence, and calling the supported CUBRIDdb driver deprecated all fail; a candidate without a dry-run result is at best incomplete. The first task is the #914 JSON bool path fix, with recorded fixtures for each failure. `make agent-eval-check` re-grades them deterministically; it calls no model and needs no database, and its tests run in the existing `repo` lane. No agent score gates a pull request, and no other CI lane changes. See `agent-evals/README.md` ([#961](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/961)) by @yeongseon.

- **The documentation check's shell scanner matches pycubrid again (#959)** — `scripts/_markdown.py` takes pycubrid's final `_substitution_end()` byte for byte (cubrid-lab/pycubrid#978): `case` inside arithmetic is a variable name, `esac` closes an empty `case` but is a pattern after `(`, `|` or with a quoted suffix, `;&` and `;;&` end a clause, and a `#` comment inside a substitution changes nothing; the unused `_keyword_at()` is removed. The file now differs from pycubrid's only in its header line and one issue reference; pycubrid's regression cases are added to `test_adjacent_shell_operators_are_separate`. No other checker rule changes ([#960](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/960)) by @yeongseon.

- **The documentation check allocates site anchors as the site does (#957)** — `scripts/_markdown.py`, the parser shared with pycubrid and cubrid-cookbook-python, now reads this repository's `mkdocs.yml` and uses the slugifier it configures (`pymdownx.slugs`, as before; Python-Markdown's default for a site that sets none), and allocates site ids with the `toc` extension's rule: a heading with an empty slug gets `_1` instead of an empty id, and a taken `_N` id is incremented (`_1` then `_2`) instead of becoming `_N_1`. Ordinary headings keep their anchors. The change is the one merged in cubrid-lab/cubrid-cookbook-python#402 and cubrid-lab/pycubrid#976, so the shared functions stay identical; tests cover accented and Korean headings under both slugifiers, the `mkdocs.yml` detection and the collision rules ([#958](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/958)) by @yeongseon.

- **The site build runs when the MkDocs provenance hook changes (#952)** — `scripts/docs_provenance_hook.py`, which `mkdocs.yml` loads since #951, was not in `ci.yml`'s `site` path filter, so a pull request changing only the hook skipped `mkdocs build --strict` and a broken hook would first fail on `main`. It is now a site input; `docs/CI_POLICY.md` (English and Korean) lists it ([#953](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/953)) by @yeongseon.

- **Prepare release checks the `last-release-sha` baseline override (#945)** — the override set after abandoning 1.11.1 is meant to last only until the next release is published, but nothing enforced that, and a stale override makes a later recovery silently list commits that already shipped. The reconciliation step that runs before release-please now classifies the override: it is active only while it is the merge of a release PR on `main` with a recorded abandonment, no `autorelease: pending`/`tagged` label and no tag for its version; once a later release containing it passes the existing publication proof, it is obsolete and preparation stops with a request to remove it in a normal PR. A malformed, unrelated or unreadable override also stops preparation, and an API error is reported as unresolved rather than as absence. Nothing is edited automatically. `RELEASING.md` ("Baseline override lifecycle") and `AGENTS.md` describe the rule; the current 1.11.1 override is active ([#950](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/950)) by @yeongseon.

- **The documentation check handles shell substitutions as pycubrid does (#934)** — `scripts/_markdown.py` takes the three shell fixes from cubrid-lab/pycubrid#947:
  - a command or process substitution (`$(...)`, `<(...)`, `>(...)`) is part of its word, so
    `make test ENV_FILE=<(true)` names only `test`, `make VAR=$(pwd) test` keeps the goal `test`,
    and its body is checked as a command of its own;
  - a `#` right after a substitution is not a comment;
  - a quote the block never closes is prose, also before a final backslash ([#935](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/935)).

  This change's review adds three more shell fixes, which pycubrid receives next: a `case` pattern's `)` does not close a substitution; a substitution inside double quotes is checked (`echo "$(make removed)"`), but not one inside single quotes; and text that is not shell names no goal, even from substitutions read before the error. Arithmetic expansion (`$((make - removed))`) runs no command except the substitutions nested in it, `case` and `esac` are keywords only at the start of a command, and an unquoted newline in a substitution body separates commands by @yeongseon.

- **`agent-review` no longer counts empty reply-only Copilot records as review rounds (#933)** — a Copilot record with no body and no thread-opening comment, such as a reply to an existing thread, is now ignored like an error or quota notice instead of counting as a summary-only round, which could put a PR past the two-round budget and reject valid evidence. A record that opens a thread still counts. Ported unchanged from cubrid-lab/cubrid-mcp-server#349, so the gate copies stay identical outside their constants ([#936](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/936)) by @yeongseon.

- **Advisory review-evidence check added (#905)** — `agent-review.yml` uses a read-only token and the base-branch `scripts/agent_review_gate.py` to inspect GitHub's actual review records, rather than PR checkboxes or bot summaries. The configured review route accepts a substantive Copilot review within the two-round budget, a maintainer `APPROVED` review, or a maintainer `COMMENTED` review opening an inline thread. Changes to literal rendering, identifiers, dialect connections/disconnects, Alembic, workflows, release configuration or gate scripts require maintainer approval; stale reviews, **unresolved or author-resolved** critical/security threads, incomplete API data or missing commit identities do not pass. An author resolving their own critical/security finding does not satisfy the gate; maintainer resolution is required. Release-please-only and Dependabot PRs are exempt. The implementation adapts an existing organizational check (cubrid-lab/cubrid-mcp-server#341) but **remains advisory**: PRs can spoof its check name, so it must not be required until a trusted identity posts it (#929). The reviewer and contributor guides document the rule ([#1015](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1015)) by @yeongseon.

- **Issue-number lines in block quotes inside list items are reported (#925)** — the `#<digit>` line check now accepts block quote markers after a list marker or after list indentation (`- > #750`, a quote in a later paragraph of an item), where Python-Markdown also renders a heading. Container prefixes are consumed one at a time, in any order, in linear time (a backtracking pattern took seconds on a long run of list markers); the existing exclusions (an indented continuation line, `1)`, two spaces after `>`) are unchanged ([#930](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/930)) by @yeongseon.

- **The documentation check takes link lines from the source and masks inline HTML (#923)** — markdown-it's link and image rules now record each link's source tail, so the lines after a link come from its own destination, title or reference label. A reference link no longer takes an equal inline title's newlines, backticks in a title no longer hide its line, and a reference label that spans lines counts its line. Before references are checked, only what markdown-it parsed is masked, at its source positions: inline HTML (tags and comments), autolinks and inline link tails. A link-like fragment in an attribute no longer hides an undefined reference, a tag name in a destination no longer exposes the title, and text that only looks like a link tail is checked. In a shell block, `#` starts a comment only at the start of a word, so `echo x\ #note \` still continues the line. `[site]( "See [foo][bar]")` stays reported: CommonMark does not parse it as a link ([#928](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/928)) by @yeongseon.

- **The documentation check reports lines that the site renders as headings (#920)** — a paragraph line under `docs/` that starts with `#` and a digit, such as a wrapped issue number, is plain text on GitHub but an `<h1>` on the MkDocs site, where Python-Markdown reads it as a heading. `scripts/check_docs_links.py` now reports such a line, as a list item or in a block quote too, following Python-Markdown's list and quote rules, and asks for `\#`. The 11 such lines on 7 pages (`docs/CI_POLICY.md`, `docs/DRIVER_COMPAT.md`, `docs/RELEASE_PLEASE_VALIDATION.md` and four Korean pages) are escaped; they read the same on GitHub ([#924](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/924)) by @yeongseon.

- **Documentation link checks handle more Markdown, HTML, Makefile and shell cases (#921)** — The shared parser preserves source line numbers across multiline HTML and inline titles; an `&#10;` entity is not counted as a real newline. It recognizes grouped and double-colon Makefile targets without confusing assignments with rules. Malformed links, apostrophes, HTML comments and angle-bracket destinations no longer hide undefined references. Shell continuation parsing distinguishes a real trailing backslash from escaped, commented or quoted text, handles multiline quotes and adjacent redirections such as `;>` and `&>>`, and checks HTML `<source src>` links. This aligns `scripts/_markdown.py` and `scripts/check_docs_links.py` with the reviewed pycubrid parser (cubrid-lab/pycubrid#940, cubrid-lab/pycubrid#941) ([#922](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/922)) by @yeongseon.
- **Deterministic documentation defects block the merge (#908)** — a new `docs-check` job in `ci.yml` runs `scripts/check_docs_links.py` and `scripts/check_agents_docs.py` on every tracked Markdown file when Markdown, `scripts/` or the `Makefile` change, and `matrix-result` requires it then. It fails with `file:line` and a suggested fix on:
  - a missing, absolute or out-of-repository Markdown or HTML link target;
  - an anchor that is not a heading or `<a id>` of its target;
  - an undefined reference link, or an unclosed code fence;
  - a `make` goal or `scripts/` path in a command that does not exist.

  Release history keeps its old commands. Markdown is parsed as CommonMark with `markdown-it-py`, pinned in `.github/docs-requirements/requirements.txt`, the same parser as pycubrid's gate, including its review follow-ups (cubrid-lab/pycubrid#939). `check_agents_docs.py` now uses it too, so multi-backtick code spans are code and every goal of a `make` command is checked. External links are never fetched, `scripts/check_support_claims.py` stays the authority for support wording, and the shared `doc-lint` workflow stays advisory; its measured findings are in `docs/CI_POLICY.md`. `<!-- docs-check: ignore -->` marks a reviewed false positive ([#919](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/919)) by @yeongseon.

- **Release preparation starts after the abandoned 1.11.1** — 1.11.1 has no tag, so release-please fell back to `bootstrap-sha` and proposed 1.12.0 with every commit since 1.8.0. `release-please-config.json` now sets `last-release-sha` to the 1.11.1 merge, so the next candidate is computed from the commits after it, and RELEASING.md's abandoned-version recovery documents setting that override and removing it after the next release is tagged ([#912](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/912)) by @yeongseon.

- **A release commit's `main` push no longer repeats the release's runtime lanes (#737)** — `ci.yml` runs `scripts/release_detect.py --mode push`, the decision `publish-pypi.yml` makes on the same SHA, and on a release commit skips `typecheck`, `offline-tests`, `alembic-compat`, `packaging-smoke-test`, `integration-tests` and `make-integration`, which `integration-full.yml` already runs there behind the fail-closed `full-matrix-result`. Lint, documentation and tooling checks still run. `integration-full.yml` gains the two endpoint-cell steps it lacked (pycubrid sync integration and regression tests) on Python 3.11/CUBRID 10.2 and 3.14/11.4. On the 1.11.0 release commit this would have saved 14.1 runner minutes for about 1.4 added to the release. `docs/CI_POLICY.md` records measured runner minutes after the #760 and #797 consolidation and the first grouped Dependabot run ([#841](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/841)) by @yeongseon.

### Tests

- **The live test for garbage-collected async connections passes in `make integration` again (#872)** — `TestAsyncTerminateLive872::test_garbage_collected_connection_is_terminated` failed in every `make integration` lane after #1017 published the Compose broker on `127.0.0.1` only, which stopped the 1.11.4 release matrix. On a host where `localhost` resolves to `::1` first (GitHub runners), asyncio's `create_connection` keeps the refused `::1` attempt's exception in a reference cycle, and the frames of that cycle kept the test's connection alive until the cycle collector ran. The test now opens the pooled connection before the leak and asserts that the leaked checkout reused it, so it still requires the refcount-freed connection's socket to be terminated, with no ResourceWarning and nothing checked out ([#1035](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1035)) by @yeongseon.

- **The CASE value and GROUP_CONCAT ORDER BY live tests pass with CUBRIDdb (#1003)** — the tests added for #987 and #991 asserted pycubrid's results, so the release matrix's `make integration (cubriddb, …)` lanes failed on CUBRID 10.2 and 11.4 and 1.11.2 was not published. They now pin the CUBRIDdb results above and keep the exact pycubrid assertions ([#1004](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1004)) by @yeongseon.

- **ORDER BY output matches SQLAlchemy's for plain items (#968)** — the dialect renders ORDER BY one item at a time, so a guard test compares its output with SQLAlchemy's own `order_by_clause` for ORDER BY items that need no grouping ([#969](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/969)) by @yeongseon.

- **SHOW TRACE read failures release both result handles (#854)** — `test/test_trace.py` gains the missing offline test for `trace_query()`'s read path: when reading the `SHOW TRACE` rows raises, the traced statement result and the `SHOW TRACE` result must both be closed, `SET TRACE OFF` must still be attempted, and the read error must reach the caller instead of being replaced by the cleanup statement's own failure. The trace is mocked, so the test is offline and does not replace integration coverage on a real server. No production code changes: the described behaviour already holds, so no failure could be demonstrated ([#931](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/931)) by @tnalbant (first contribution 🎉).

- **Garbage-collection tests no longer depend on the cycle collector (#872)** — the live async terminate test and the closed-event-loop test now commit before losing the connection, so the pool's cleanup runs when the last reference goes and terminates the connection on every supported Python, including 3.15, and they assert that the cleanup chose terminate. The reference-cycle case is a separate test that probes the installed SQLAlchemy and is an expected failure where the pool cannot clean such a connection up (SQLAlchemy 2.1 on CPython 3.15). Both failed on all four Python 3.15 cells of the full compatibility matrix ([#894](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/894)) by @yeongseon.

- **Benchmark artifacts verify the measured dialect and carry their provenance in the report (#903)** — before measuring, `scripts/bench_dialect_baseline.py` now checks the installed `sqlalchemy_cubrid` against `--source-sha`. An install from a local git checkout must have that commit's `*.py` files, and a VCS install must record that commit; a mismatch stops the run. The report records the package SHA-256, the verification method, and the image digest, host label and comparable group, which are now benchmark arguments (`--server-image-digest`, `--host-label`, `--comparable-group`) instead of `export` arguments. Contract `sqlalchemy-cubrid-benchmark-artifact/2`: `export` rejects an unverified install such as a PyPI wheel; `validate` rejects an in-place edit of those fields, because it rebuilds them from the hashed report; and `validate`/`compare --source-repo DIR` recompute the package hash from git. `/1` manifests, including the first pinned pair, are rejected and kept unchanged; the re-recorded pair is in `benchmarks/2026-10-14-artifact-pair-v2`. Benchmark tooling only ([#904](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/904)) by @yeongseon.

- **Benchmark results can now be archived and compared with provenance (#901)** — `scripts/bench_artifact.py` exports and validates a `sqlalchemy-cubrid-benchmark-artifact/1` manifest from a complete dialect benchmark report, then compares baseline and candidate runs. It records dialect SHA, driver and SQLAlchemy versions, CUBRID image/server, Python/host, password-redacted connection target (database user and URL query parameters are still recorded), pool settings, workload identity and every trial; advisory metrics distinguish literal FC20, opt-in FC21 and insertmanyvalues from CUBRIDdb's per-row path. Missing files, corrupt data or mixed source revisions are rejected, and differences other than the dialect make results `not comparable`. The baseline script now records SHA-256, connection, autocommit and completion metadata. **Operator-supplied SHA, image digest and host labels are not independently verified** (#903). The pinned v1.11.0-to-main CUBRID 11.4 pair is in `benchmarks/2026-10-14-artifact-pair`; the older #830 archives remain unchanged. Benchmark tooling only: no dialect change and no new CI gate ([#902](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/902)) by @yeongseon.

- **Isolated live CTE coverage (#849)** — the 14 SQLAlchemy `CTETest` compliance nodes are strict xfails because their fixture cleanup fails on CUBRID's per-row foreign-key check, so they supplied no behavior evidence. `TestIsolatedCTE849` replays their scenarios on fresh FK-safe tables against CUBRID 10.2 to 11.4. SELECT, recursive SELECT, bound parameters, UPDATE and DELETE with a CTE scalar subquery and every values-via-CTE variant pass; UPDATE/DELETE ... FROM are asserted as the documented limits; INSERT FROM SELECT over a CTE passes since #897. The ledger entries are kept, with a pointer to this evidence ([#898](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/898)) by @yeongseon.

- **Offline tests for identifier quoting, preflight engine disposal and the reflection probe report (#859, #858, #857)** — `test/test_base.py` covers escaped and reserved identifier quoting, `test/test_check_integration_connection.py` pins disposal of the preflight sync engine on success and on errors, and `test/test_reflection_probe_shape.py` pins the `reflection_probe` report shape with a fake inspector ([#978](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/978), [#979](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/979), [#981](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/981)) by @CloudCorpRecords.

- **Offline tests for select attribute accessors, compile benchmark iterations and version-report fallbacks (#855, #850, #851)** — `test/test_compiler.py` covers select attribute accessors, `scripts/bench_compile.py` validates its iteration count (`test/test_bench_compile.py`), and `test/test_report_driver_versions.py` covers the version report fallbacks ([#1025](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1025), [#1026](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1026), [#1031](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1031)) by @WilliamK112 (first contribution 🎉).

## [1.11.0] - 2026-10-12

This release introduces Python 3.15 support and a broad set of compatibility, reliability, and test improvements. Review the upgrade notes before adopting it; detailed changes and references follow.

### Upgrade notes

- **Python 3.15 is supported (#666).** Standard GIL builds only. The pycubrid routes (`cubrid+pycubrid://`, `cubrid+aiopycubrid://`) are covered with the pycubrid release that declares Python 3.15 (cubrid-lab/pycubrid#831); the `[pycubrid]` floor stays `pycubrid>=1.8.0,<2.0`. On 3.15, pycubrid 1.10.0 and earlier reject `?charset=ksc5601` because Python 3.15 maps that codec alias to CP949; use `?charset=euckr` or the newer pycubrid. Building the official CUBRIDdb driver with GCC 14 fails on Python 3.14 and 3.15 alike (the two versions compared); see `docs/DRIVER_COMPAT.md` ([#807](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/807)) by @yeongseon.

- **`sqlalchemy-cubrid` no longer installs with SQLAlchemy 2.2 or newer (#774).** The package metadata now requires `sqlalchemy>=2.0,<2.2`, matching the supported range already documented (2.0 and 2.1). SQLAlchemy 2.2 is not released yet (PyPI latest 2.1.4), so no current install changes: 2.0.x and 2.1.x resolve exactly as before. Once 2.2 ships, `pip` keeps resolving SQLAlchemy 2.1.x for this package. SQLAlchemy 2.2 was never verified against the full compatibility matrix and is excluded until it ships and passes it; the cap is then lifted in a later release ([#777](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/777)) by @yeongseon.

- **The `dev` extra is gone; contributors install the `dev` dependency group (#765).** Use `pip install -e . --group dev` (pip 25.1 or later) or `make install` instead of `pip install -e ".[dev]"`, which now installs only the package and warns that the extra does not exist. End users are not affected: the runtime extras (`pycubrid`, `alembic`, `cubrid`, `cubriddb`) are unchanged ([#808](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/808)) by @yeongseon.

### Added

- **Python 3.15 is included in release compatibility testing (#666)** — The package adds the Python 3.15 classifier and `py315` tox environment. Manual and release runs cover Python 3.11–3.15 × CUBRID 10.2/11.0/11.2/11.4 (20 cells), including CUBRIDdb, synchronous/asynchronous pycubrid, cross-driver comparisons, transactional DDL and server restart. The minimum remains Python 3.11; free-threaded Python is not claimed. English/Korean support and developer guides document the pycubrid dependency, CUBRIDdb's GCC 14 build limitation, compliance lanes retained on 3.14/11.4 and 3.11/10.2, and the C `_decimal` requirement for Decimal subclasses. German/Hindi/Russian/Chinese README translations remain tracked in #698–#701 ([#807](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/807)) by @yeongseon.
### Changed

- **Contributor tools now use dependency groups, not the published `dev` extra (#765)** — `pyproject.toml` defines PEP 735 groups for `test`, `lint` (Ruff), `typecheck` (Mypy), `security` (Bandit), `mutation` (mutmut), `release` (build/twine), and `dev` (all of these plus pre-commit/tox), keeping each pin in one place. Contributor installs switch from `pip install -e ".[dev]"` to the `dev` group; runtime extras are unchanged. Tox 4.22+ installs dependency groups, CI type-check, canary, and security jobs use their declared groups, and `scripts/check_tool_versions.py` checks the pins and group configuration. MkDocs tools remain under `.github/docs-requirements/requirements.txt` (#761). The new `dev` group resolves to the same 73 packages as the former extra. Packaging and contributor tooling only; **no dialect runtime change** ([#808](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/808)) by @yeongseon.

- **SQLAlchemy is capped below 2.2 (#774)** — `sqlalchemy>=2.0,<2.3` became `>=2.0,<2.2` in `dependencies` and in the `dev` and `pycubrid` extras, so package metadata matches `docs/SUPPORT_MATRIX.md` (`≥ 2.2` unsupported). README, the translated READMEs, `SUPPORT_MATRIX`, `SA_COMPAT`, `ARCHITECTURE`, `PRD` (English and Korean) and `THIRD_PARTY_LICENSES.md` state the same range. The 2.2 forward-compat shims and the weekly `--pre` canary stay: the canary installs SQLAlchemy in a separate explicit step (`>=2.1.0b1,<2.3`), which is not bound by the package cap, so it still forward-tests 2.2 pre-releases. Packaging metadata only (release type: patch); no dialect code changes ([#777](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/777)) by @yeongseon.

- **Cookbook release verification pinned to the shared cookbook SHA** — the `verify-cookbook` call to `cubrid-cookbook-python`'s `smoke-test.yml` in `.github/workflows/publish-pypi.yml` is pinned to `bd6749093813d3a447f993fec72ac733adbeae63`, the same commit as the other two package repositories (pycubrid, sqlalchemy-cubrid, cubrid-mcp-server). Since the previous pin the cookbook adds the Python 3.11 cell on release calls (`Smoke Tests (CUBRID 11.4, Python 3.11)`), so the release verification report now needs all three cells (11.2/3.12, 11.4/3.12, 11.4/3.11). `RELEASING.md` lists the third job. CI only; the dialect is unchanged ([#771](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/771)) by @yeongseon.

- **Documentation site build on pull requests (#786)** — `ci.yml` gains a `docs-build` job that runs the `docs.yml` build (install `.github/docs-requirements/requirements.txt`, `scripts/generate_llms_full.py`, `mkdocs build --strict`) when `docs/**`, `mkdocs.yml`, `scripts/generate_llms_full.py`, `.github/docs-requirements/**`, `docs.yml` or `ci.yml` change. The new `site` path filter selects it, `matrix-result` expects it exactly when selected, and it never uploads or deploys anything. Previously a broken strict build or docs-tool pin bump only failed on `main`. CI only; the dialect is unchanged ([#769](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/769)) by @yeongseon.

- **Documentation tools are pinned and superseded security scans are canceled (#761, #762, #764, #747)** — `docs.yml` installs `mkdocs`, `mkdocs-material` and `pymdown-extensions` from Dependabot-maintained exact pins in `.github/docs-requirements/requirements.txt`. CodeQL and security scans cancel only superseded pull-request runs; other events get independent groups so scheduled or `main` runs are not dropped. `test/test_workflow_hygiene.py` checks that the compliance job's pinned pycubrid matches the declared dependency floor. Full-integration fuzz and mutation job names no longer promise a nonexistent nightly schedule; fuzz still gates releases. CI only; no dialect change ([#766](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/766)) by @yeongseon.
- **Mutation testing no longer delays releases (#747)** — `publish-pypi.yml`'s `build` waits for the whole called `integration-full.yml`, so the non-gating `mutation-testing` job added its run time (historical median 9.6, maximum 18.1 minutes) to every release. It now runs only when `integration-full.yml` is dispatched manually and is skipped on the release call (`if: ${{ !inputs.sha }}`; the release call always passes `sha`). The Hypothesis fuzz pass still gates the release, and `full-matrix-result` is unchanged. `publish-pypi.yml` is unchanged. CI only; the dialect is unchanged ([#805](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/805)) by @yeongseon.

- **Offline tests run on the oldest and newest supported Python outside PRs (#734)** — in `ci.yml` the `offline-tests` matrix is chosen by event: pull requests keep the single representative Python 3.12 cell, while main pushes, the weekly schedule and manual dispatches run the full offline suite (`-m "not integration and not repo"`, 95% coverage floor) on Python 3.11 and 3.14. Each cell uploads its own `coverage-report-py<version>` artifact, and `matrix-result` still fails when an offline cell fails, is cancelled or is unexpectedly skipped. CI only; the dialect is unchanged ([#756](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/756)) by @yeongseon.

- **Release validation replaces redundant CI runs (#737)** — The duplicate Python 3.12/CUBRID 11.4/pycubrid `live-smoke` lane was removed because `make-integration` covers it at the same commit. Advisory SQLAlchemy pre-release and oldest-cell CUBRIDdb checks moved from each main push to scheduled/manual runs; `upstream-canary` moved to Thursday 06:00 UTC. The release's required `integration-full.yml` now runs its own Python 3.11/3.14 offline endpoints, instead of relying on an unrelated main-push run. **PR checks are unchanged**, and `docs/CI_POLICY.md` records before/after job counts, runner time, failure yield, and coverage ownership. CI only, no dialect behavior change ([#760](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/760)) by @yeongseon.

### Documentation

- **Connection, driver-compatibility and PRD docs state the Python 3.11+ requirement (#697)** — after 1.10.0 raised `requires-python` to `>=3.11`, the `docs/CONNECTION.md` prerequisite row, the `docs/DRIVER_COMPAT.md` Python table (3.10 as the minimum, 3.14 as pre-release) and the `docs/PRD.md` CI matrix, success criteria and dependency rows, with their Korean copies, still described Python 3.10. They now give 3.11 as the minimum, 3.11–3.14 as the tested range, as the full compatibility matrix runs them, and mark 3.10 as not supported from 1.10.0. Historical rows and measurements are unchanged. Docs only ([#803](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/803)) by @yeongseon.

- **The compliance-lane pycubrid pin is labelled as the declared floor (#479)** — `docs/SUPPORT_MATRIX.md` (+ ko) listed the pycubrid compliance lanes as "pycubrid 1.8.0 (recommended)", which read as a recommendation to install 1.8.0. The pin is the declared floor of `pycubrid>=1.8.0,<2.0`, kept on purpose; pycubrid is the recommended driver, and the integration lanes test the latest release. Docs only ([#801](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/801)) by @yeongseon.

- **Private vulnerability reporting is the preferred security channel (#738)** — GitHub private vulnerability reporting is now enabled for the repository. `SECURITY.md` names it as the preferred private route and keeps the maintainer email as the fallback; `README.md` and the translated READMEs say the same. Docs only ([#796](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/796)) by @yeongseon.

- **No more "nightly" full integration (#747)** — the PRD CI matrix (+ ko) listed a "Nightly" full integration run with Python 3.10. `integration-full.yml` has no schedule: it runs on manual dispatch and as the release gate, on Python 3.11–3.14. `docs/TYPES.md` (+ ko), the `test/test_dogfood_orm.py` docstring and `test/version_differential/compare_snapshots.py` also referred to a nightly run; all now describe the current triggers, and the dogfood docstring names the CUBRID versions it actually runs on (10.2 and 11.4). `nightly` remains only as the Hypothesis profile name. Docs and comments only ([#792](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/792)) by @yeongseon.

- **`AGENTS.md` no longer carries stale planning context (#736)** — the "Performance Loop System" snapshot (R3 phases, issues #68/#70 as current work) is replaced by a short performance-context statement pointing to `docs/PERFORMANCE.md`, cubrid-benchmark, `ROADMAP.md` and the org project board. Volatile counts and inventories (module count, requirement-flag count, tested CUBRID versions, default Docker version, test file list including the nonexistent `test_dml.py`) are removed or point to their canonical source. CUBRID dialect and Alembic invariants are unchanged. Docs only ([#757](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/757)) by @yeongseon.

- **Stale facts removed from PRD and DEVELOPMENT docs (#758)** — the nonexistent `test_dml.py` is no longer listed in `docs/DEVELOPMENT.md` and `docs/PRD.md` (and their Korean counterparts); DML tests live in `test/test_compiler.py` (ODKU regressions also in `test/test_regression.py`). The unguarded "12 Python modules", "40+ properties", "314 offline tests" and "3 uncovered lines" counts in `docs/PRD.md` are replaced with descriptions or pointers to the source. `docs/llms-full.txt` is regenerated. Docs only ([#759](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/759)) by @yeongseon.

- **`charset` names pycubrid 1.9.0 (#479)** — `docs/CONNECTION.md` (+ ko) said the `charset` URL option needs a pycubrid release "newer than 1.8.0"; it now names 1.9.0, the release that added it. Docs only ([#800](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/800)) by @yeongseon.

* **agents:** add support-claim review checklist ([#784](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/784)) ([a8ffc4b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a8ffc4bbd2ae41279f86ca125dfaba242ff2909e)) by @yeongseon.

* **ci:** clarify SQLAlchemy pre-release canary coverage ([#788](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/788)) ([85817ca](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/85817ca476e05604ba1347d6b99ff525da706489)) by @yeongseon.

* correct the older closing-guard CHANGELOG notes ([#819](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/819)) ([a508694](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a508694d34ec8f66243c3a97f5f46adaf5c991bc)) by @yeongseon.

* **driver:** distinguish the supported CUBRIDdb driver from optional installation extras ([#781](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/781)) ([d20a6b2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/d20a6b25cba37cc9d9a55aef330600242cd038e6)) by @yeongseon.

* **i18n:** update the Python requirement in the Chinese README ([#825](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/825)) ([6430aad](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6430aad77013ce353245258192371477ed70ddc1)) by @Vieta100-omo (first contribution 🎉)

* **release:** record live release-please evidence and candidate regeneration ([#817](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/817)) ([27134e0](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/27134e081f2e7285f563e0fde54f301339ebb5a1)) by @yeongseon.

* **review:** distinguish agent review routes and dispositions ([#802](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/802)) ([24743d6](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/24743d604461fc681b84ecfadc0e4ec46b2c2668)) by @yeongseon.

* **support:** distinguish current guarantees from historical evidence ([#783](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/783)) ([92307cf](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/92307cfcb856103827a488d5f4bf8895c02c192d)) by @yeongseon.

* **types:** identify pycubrid 1.9.0 collection binding ([#782](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/782)) ([81fc4ff](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/81fc4ff7744d5a200c2077183c601125e21f09f0)) by @yeongseon.

### CI

- **The closing guard catches a closing keyword used as link text** — the `PR title` check now looks past link, image and link-reference syntax between a closing keyword and a foreign reference, in time linear in the body length (from the review of cubrid-lab/pycubrid#849) ([#822](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/822)) by @yeongseon.

- **The release PR body also writes generated issue references as "refs"** — the **Prepare release** workflow rewrites release-please's `, closes [#N](…)` in the release PR body to `refs`, using the same rule as for `CHANGELOG.md`; no permission changes (#821) ([#821](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/821)) by @yeongseon.

- **Generated release notes write issue references as "refs", not "closes"** — `scripts/compose_release_changelog.py` rewrites release-please 17.6.0's `, closes [#N](…)` to `, refs [#N](…)` in `CHANGELOG.md`, so a commit that only said `Refs #N` is no longer listed as closing it (#770) ([#820](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/820)) by @yeongseon.

- **The closing guard also checks the PR title and commit messages, and owners with an underscore** — the `PR title` check also reads the PR title and each commit message (with a read-only `pull-requests` token; it fails when a PR has 250 or more commits), and matches owners such as `alice_acme/repo#N` (cubrid-lab/pycubrid#845; same change in cubrid-lab/cubrid-mcp-server#276 and cubrid-lab/cubrid-cookbook-python#294) ([#818](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/818)) by @yeongseon.

- **The PR-body closing guard catches emphasized, linked, escaped and split closures, and fails closed where Markdown structure is uncertain** — emphasis, HTML, links, URLs, escapes, entities and split keywords around a foreign closure are rejected; only fenced and indented code blocks and HTML comment blocks are ignored, and once a fence's extent is uncertain no later text is hidden (same guard in cubrid-lab/cubrid-mcp-server#275 and cubrid-lab/cubrid-cookbook-python#293) ([#816](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/816)) by @yeongseon.

- **The PR-body closing guard checks list-continuation lines** — lines indented under a list item are scanned as the paragraph text GitHub renders ([#815](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/815)) by @yeongseon.

- **Repository-local issue closure in PRs** — the required `PR title` check rejects direct cross-repository auto-closing keywords, while local `Closes #N` and cross-repository `Refs owner/repo#N` remain valid (partly superseded by the entries above) ([#811](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/811)) by @yeongseon.

- **The cookbook verifies the built wheel before it is published (cubrid-lab/cubrid-cookbook-python#240)** — `publish-pypi.yml` gains `verify-candidate` and `require-candidate`, which run the cookbook smoke test on the exact built wheel (SHA-256 checked) before `publish`; a release that needs an unpublished pycubrid must wait until that pycubrid is published. No runtime change ([#812](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/812)) by @yeongseon.

- **The PyPI duplicate guard uses `hashlib.file_digest()` (#730)** — same digests, shared with pycubrid and cubrid-mcp-server. No runtime change ([#806](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/806)) by @yeongseon.

- **Python 3.15 is the newest offline endpoint (#666)** — the non-PR offline endpoint cells move from Python 3.11/3.14 to 3.11/3.15 (pull requests keep 3.12), and the live Decimal-subclass round trip is skipped on a Python without the C `_decimal` module ([#807](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/807)) by @yeongseon.

- **The cub_server restart tests run on the latest pycubrid again (#479)** — the restart step upgrades pycubrid after the compliance step had pinned the job to `pycubrid==1.8.0`. CI only ([#798](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/798)) by @yeongseon.

- **The release runs the remaining `ci.yml` push lanes itself (#737)** — `integration-full.yml` runs `typecheck`, `alembic-compat`, `packaging-smoke-test` and `sqlalchemy-compliance` on the release SHA, and `full-matrix-result` blocks publication on any failed, cancelled or skipped lane. CI only ([#797](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/797)) by @yeongseon.

- **Dependabot groups minor and patch updates (#737)** — one PR per ecosystem and directory; major and security updates and SQLAlchemy, pycubrid, Alembic and CUBRID-Python stay in their own PRs. No runtime change ([#791](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/791)) by @yeongseon.

- **"Prepare release" fails visibly when a merged release is blocked** — `scripts/reconcile_release_labels.py` fails the run with the PR, merge SHA and run URL when a merged release PR has no successful publication. A queued or running publisher run at that SHA, or a merge under 2 hours old with no run yet, only emits a notice and stays green. Before, after the 1.10.0 cookbook failure (PR #704), the run stayed green (see RELEASING.md, "When preparation is blocked"). CI only ([#776](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/776)) by @yeongseon.

- **Cookbook release verification pinned to the cookbook SHA with the PyPI wait** — `verify-cookbook` is pinned to `32e80c6ea9ae78324f764d7b873ffb64b000ddcc` (cubrid-cookbook-python#274), which waits up to 10 minutes for PyPI to serve the requested version; this fixes the 1.10.0 post-publish stale-CDN failure. CI only ([#775](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/775)) by @yeongseon.

- **Shared fence-aware CHANGELOG lint and composer** — `scripts/lint_changelog.py` and `scripts/compose_release_changelog.py` treat lines inside fenced code as entry content, and the lint gains the duplicate-`###` rule for `[Unreleased]` and releases after 1.10.0. CI only ([#773](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/773)) by @yeongseon.

- **GitHub Release naming and standard release-note sections** — a Release title is exactly its tag (`scripts/check_release_title.py` fails closed on resume or recovery), `scripts/extract_release_notes.py` appends one Full Changelog link, and the lint requires the standard `###` sections for `[Unreleased]` and releases after 1.10.0. CI and release tooling only ([#772](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/772)) by @yeongseon.

### Tests

- **Async cancellation and driver deadlines discard the connection (#479)** — `test/test_aio_integration.py::TestAsyncCancellationAndDeadline` checks that a cancelled (`asyncio.wait_for`) or timed-out (`read_timeout=0.5`) `SELECT SLEEP(5)` invalidates the connection without leaking a pool slot (cubrid-lab/pycubrid#554, cubrid-lab/pycubrid#556, cubrid-lab/pycubrid#687, cubrid-lab/pycubrid#744). Tests only ([#798](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/798)) by @yeongseon.

- **pycubrid 1.9.0 error classification through SQLAlchemy (#479)** — live sync and async tests on CUBRID 10.2 and 11.4: a zero `DATE`/`DATETIME` raises `sqlalchemy.exc.DataError` without invalidating the connection (cubrid-lab/pycubrid#492/#512/#543), and foreign-key-restricted `DELETE`/`UPDATE` and a `TRUNCATE` of a referenced table raise `IntegrityError` (cubrid-lab/pycubrid#493; strict expected failures on the pycubrid 1.8.x floor). `docs/DRIVER_COMPAT.md` records two `CUBRIDdb` differences: a zero date escapes as a bare `SystemError`, and a -1284 `TRUNCATE` is `DatabaseError`. Tests and docs only ([#799](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/799)) by @yeongseon.

- **Release-please push guards are pinned (cubrid-lab/pycubrid#801)** — `test/test_release_workflows.py` asserts the exact, ordered guards of `release-please.yml`, and `RELEASING.md` gains the recovery row for abandoning a merged release. Test and docs only ([#789](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/789)) by @yeongseon.

- **Guard for the SQLAlchemy range (#774)** — `test/test_sqlalchemy_range.py` (a `repo` test) fails when the `sqlalchemy` upper bound in `pyproject.toml` (all extras) differs from the pin stated in the README, translated READMEs and docs, or when `SUPPORT_MATRIX` (English and Korean) does not list every minor below the cap as supported and the cap minor as unsupported ([#777](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/777)) by @yeongseon.

- **Live value round trips for pycubrid 1.9.0 fixes (#479)** — sync and async tests cover plain-notation and subclass `Decimal` values, aware datetimes in `DATETIMETZ`/`TIMESTAMPTZ` including the repeated DST hour, NULL-typed results, years 999 and 99, a `?charset=utf8` round trip and all-`NULL` collections, (cubrid-lab/pycubrid#517, #518, #413, #542, #519, #86, #483); only the cases that fail on pycubrid 1.8.0, the `[pycubrid]` floor, are strict expected failures there. Known limitation: a `fold=1` datetime in the repeated hour is stored one hour off, because pycubrid binds `DATETIMETZ` without the fold (cubrid-lab/pycubrid#819). Tests only ([#800](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/800)) by @yeongseon.

## [1.10.0] - 2026-10-08

This release raises the minimum supported Python version to 3.11. Applications on Python 3.10 should remain on the compatible 1.9.x line until upgraded. Review the upgrade notes and detailed changes below.

### Upgrade notes

- **Python 3.11 or newer is required (#686).** Python 3.10 reached upstream end of life on 2026-10-01 and its retirement was announced in 1.9.0. On Python 3.10 `pip` keeps installing 1.9.x, the last line that supports it; only the latest release line receives fixes, so 1.9.x gets no further releases. Upgrade Python, recreate your virtual environment and validate your application before upgrading ([#703](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/703)) by @yeongseon.

### Changed

- **tox no longer lists Python 3.10 (#687)** — `py310` is removed from `envlist`, and `typecheck-sa20` type-checks SQLAlchemy 2.0.53 on Python 3.11 instead of 3.10. Local tooling only; CI and the dialect are unchanged ([#728](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/728)) by @yeongseon.

- **Ruff and mypy target Python 3.11 (#688)** — `target-version = "py311"` and `python_version = "3.11"` in `pyproject.toml`, matching the minimum supported version. The rule selection is unchanged and no source needed a fix ([#729](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/729)) by @yeongseon.

- **Disconnect detection drops the Python 3.10 timeout case (#689)** — `CubridDialect._has_oserror_cause` now checks `OSError` directly: from Python 3.11, `asyncio.TimeoutError` is the built-in `TimeoutError`, an `OSError` subclass, so the separate check was obsolete after #686. A `TimeoutError` cause is still treated as a disconnect ([#732](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/732)) by @UsmanGhias.

### Removed

- **Python 3.10 support (#686)** — `requires-python` is `>=3.11` and the 3.10 classifier is gone. CI no longer tests 3.10: the oldest integration cell is Python 3.11 × CUBRID 10.2 × SQLAlchemy 2.0.53, the full matrix covers Python 3.11–3.14 and the Alembic compatibility job runs on 3.11. Python 3.10 used to select SQLAlchemy 2.0 by itself (SQLAlchemy 2.1 needs Python 3.11), so the oldest CI cell and the Python 3.11 row of the full matrix now pin `sqlalchemy>=2.0,<2.1`; without the pin no live lane would run the ordinary integration tests on the minimum supported SQLAlchemy line. No dialect behavior changes on Python 3.11 or newer ([#703](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/703)) by @yeongseon.

### Documentation

- **Third-party licenses are tracked separately for each installation option (#727)** — The generated `THIRD_PARTY_LICENSES.md` records dependency versions, environment and license classification for runtime, `[pycubrid]`, `[alembic]`, `[cubrid]`/`[cubriddb]` and development installs, using `scripts/generate_third_party_licenses.py`. It distinguishes installed dependencies from packaged wheel/sdist contents and notes that SQLAlchemy 2.1 no longer installs greenlet by default. MPL-2.0 dependencies are identified separately (`certifi`, `hypothesis`, `pathspec` in development), and GPL-family metadata (including `docutils`) is flagged for review. CUBRID-Python is classified as permissive BSD, but the **exact BSD variant is unresolved**. Repository tests check dependency ranges, classifications and review flags; CI runs them for inventory changes. No runtime change ([#755](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/755)) by @yeongseon.
- **The README and quickstart state Python 3.11 or later (#695)** — the requirement lines, the tested and supported ranges (3.11–3.14) and the FAQ answer in `README.md` and `docs/README.ko.md`, and the prerequisites in `docs/QUICKSTART.md` and `docs/ko/QUICKSTART.md`. The Python 3.10 retirement notice in both READMEs now describes the requirement as in effect from 1.10.0 ([#731](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/731)) by @yeongseon.

- **In-page links work on the documentation site (#721)** — the site used the default heading slugifier, which drops non-ASCII characters, so Korean headings got ids such as `_2` and every Korean table of contents entry was dead; English links written for GitHub's slugs missed as well (208 broken anchors). `mkdocs.yml` now uses the Unicode-aware slugifier from `pymdown-extensions`, the eight anchors that were still wrong are fixed (among them a misspelled Korean heading and links to repeated "Basic Usage" headings), and `validation.links.anchors: warn` makes the strict build fail on a new broken anchor ([#722](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/722)) by @yeongseon.

- **Korean documentation clarifies behavior and verification limits (#719)** — Corrected the `cursor.lastrowid` fallback's cursor lifetime, `stmt.inserted` support and native Enum support-matrix entry. The new Korean PRD, SQLAlchemy compatibility, release validation and contribution pages were checked for meaning, including the difference between “checks not run” and “could not run.” Their banner makes clear that CI checks documentation structure, **not sentence-level translation accuracy**. English documentation and runtime behavior are unchanged ([#720](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/720)) by @yeongseon.
- **The documentation home page states one SQLAlchemy range (#716)** — its ecosystem list said "SQLAlchemy 2.0–2.2" while its first line, the README and the support matrix say 2.0–2.1. Both languages now say 2.0–2.1; the dependency pin (`>=2.0,<2.3`) is unchanged ([#717](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/717)) by @yeongseon.

- **CI fails when a Korean document drifts from its English source (#710)** — `scripts/check_docs_translation.py` compares every `docs/<name>.md` with `docs/ko/<name>.md` and fails on a missing Korean file or a different number of headings (levels 2-4), fenced code blocks or table rows; the lint job runs it on every event. Until now only README drift was checked. Documents that are deliberately English-only are listed in the script with a reason. The check compares structure, not wording. Same script as cubrid-lab/pycubrid#721 ([#715](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/715)) by @yeongseon.

- **SA_COMPAT, PRD and the release-please validation record are available in Korean (#709)** — `docs/ko/SA_COMPAT.md`, `docs/ko/PRD.md` and `docs/ko/RELEASE_PLEASE_VALIDATION.md` are added, and the three documents, which were not in the site navigation, are listed in both languages. With these, every document under `docs/` has a Korean counterpart ([#714](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/714)) by @yeongseon.

- **Korean contribution guide (#708)** — `docs/CONTRIBUTING.ko.md` translates the current `CONTRIBUTING.md`, keeping commands, English GitHub conventions, label names and title examples unchanged. It is linked from the Korean README and the Korean navigation. English stays the authoritative version ([#713](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/713)) by @yeongseon.

- **Korean documentation home page and one Korean navigation section (#707)** — `docs/ko/index.md` is the Korean landing page, linked from the English home page and back. The Korean guides sat three levels deep under "Project → Translations"; they are now one top-level "한국어" section grouped like the English navigation, and every Korean page is reachable from it ([#712](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/712)) by @yeongseon.

- **Korean support matrix, feature table and CI policy match the English documents (#706)** — `docs/ko/SUPPORT_MATRIX.md` shows the CI matrix as a table and loses a Korean-only closing section; `docs/ko/FEATURE_SUPPORT.md` drops a limitation row (`IS DISTINCT FROM`) that the English table does not list; `docs/ko/CI_POLICY.md` is a full translation instead of a summary. Both CI policy pages are in the site navigation. The English text is unchanged ([#711](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/711)) by @yeongseon.

* **agents:** align contributor ownership and good-first-issue guardrails ([#739](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/739)) ([41153c4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/41153c4d3d88cb7ce3beaf488ca508e40ab570ab)), closes [#733](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/733) by @yeongseon.

* **llms:** update the Python requirement in the canonical index ([#740](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/740)) ([c67f6af](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c67f6af859f71d203c76a8fac3e678f907918f7f)), closes [#702](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/702), refs [#685](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/685) by @anush-933 (first contribution 🎉)

* **python:** update contributor and CI docs for Python 3.11 ([#718](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/718)) ([f31ff01](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f31ff0158821aabf6b4cd77bcaeeeedb2a5936ca)), closes [#696](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/696) by @kragent66-glitch (first contribution 🎉)
### CI

- **CI jobs have bounded execution times** — added explicit timeouts to executing GitHub Actions jobs and checks that keep those limits in place, preventing stalled jobs from blocking validation indefinitely ([#748](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/748)) by @yeongseon.

- **Pull requests run the complete offline test suite** — offline test selection on pull requests now covers the full non-integration suite rather than relying on narrower subsets ([#749](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/749)) by @yeongseon.

- **Live validation starts independently and selects relevant workflow changes** — live integration lanes no longer wait for lint, type checking or offline tests to finish before starting. Pull-request path selection also includes relevant changes to `ci.yml` without triggering live lanes for unrelated workflow edits ([#751](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/751), [#754](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/754)) by @yeongseon.

- **Python tooling installs and caches are more reproducible** — CI, the complete integration matrix and canary jobs use a pinned `uv` installation path. The cache key follows the job's requested Python version rather than the changing patch release ([#750](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/750), [#752](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/752)) by @yeongseon.

- **CUBRIDdb wheel cache avoids unrelated binary reuse** — CI caches the compiled driver wheel using the Python ABI, runner image and source commit as cache identity ([#753](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/753)) by @yeongseon.

- **Maintenance dependency pins updated** — refreshed the development-tool pins for Ruff (0.16.10) and mypy (2.4.0), the SBOM GitHub Action (0.24.3) and the pinned cookbook smoke-test workflow. These automated dependency updates do not change the installed dialect's runtime dependencies ([#723](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/723), [#724](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/724), [#725](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/725), [#726](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/726)).

## [1.9.0] - 2026-10-04

This release contains a substantial set of dialect and development improvements. Read the upgrade notes and compatibility guidance before upgrading; the detailed changes below preserve the full technical history.

### Added

- **Python 3.15 preview preparation** — add a manual-only Ubuntu/standard-GIL offline and wheel/sdist installation lane at an immutable commit. Python 3.15 is not yet officially supported; final-runtime and live CUBRID evidence are required before promotion. Routine PR test frequency and supported versions remain unchanged ([#667](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/667), [#679](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/679)) by @yeongseon.

- **Driver comparison now covers collections and CI detects all-skipped test runs (#486)** — `test_collection_roundtrip_agrees` compares `SET` / `MULTISET` / `SEQUENCE` and `NULL` collections between CUBRIDdb and pycubrid. Released pycubrid cannot bind typed-collection parameters (cubrid-lab/pycubrid#567 is on pycubrid main), so this test writes collection literals directly in SQL, then normalizes CUBRIDdb's string values and pycubrid's native decoded types (`?decode_collections=true`) before comparing. With #480–#484 closed, this covers the remaining differential contract gap under #479 **except LOBs (#485, out of scope)**. Separately, ordinary pytest exits successfully when everything skips, so `scripts/check_not_all_skipped.py` now requires a genuinely executed test (`passed`, `failed`, `error`, `xpassed` or `xfailed`) or an explicit `--allow-all-skipped "<reason>"`. PR/full integration and `make integration` jobs use the check; existing strict driver-differential, transactional-DDL, restart and SQLAlchemy compliance gates, plus result-job dependencies, remain unchanged. Verified on a fresh CUBRID 11.4 container with pycubrid 1.8.0 and CI-built CUBRIDdb; normal and all-skipped cases behaved as expected ([#644](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/644)) by @yeongseon.

- **Recorded supported-server `SHOW CREATE TABLE` output for constraint reflection (#611)** — foreign keys are reflected only by parsing `SHOW CREATE TABLE`, so `test/fixtures/show_create_table/cubrid-{10.2,11.0,11.2,11.4}.json` now record what CUBRID 10.2.18, 11.0.16, 11.2.9 and 11.4.6 print for a small schema (composite and self-referencing foreign keys, every supported action and the default, identifiers with spaces, commas and parentheses, a `UNIQUE` constraint and a `CREATE UNIQUE INDEX` with a `DESC` key part), together with the generating SQL, the server build and the tables' `db_index` and `SHOW INDEXES` rows; the files contain no credentials. `test/test_show_create_table_server_output.py` runs every recording through the real dialect parsers via the #590 adapter in `test/test_show_create_table.py`, checks that the catalog path and the DDL path report the same unique constraints (each also a unique index named by `duplicates_index`), and, as an integration test, recreates the schema on the server under test and fails with a diff when its normalized output or reflected constraints differ from the recording for its version; PR CI's pycubrid integration step runs it on 10.2 and 11.4, and the nightly / release `integration-full.yml` matrix on all four versions (Python 3.12 lane). `python -m test.test_show_create_table_server_output <url>` records a version. `docs/FEATURE_SUPPORT.md` (+ Korean) documents the output assumptions. No dialect change ([#627](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/627)) by @yeongseon.

- **`SET`, `MULTISET` and `SEQUENCE` values bind through pycubrid typed collections (#484)** — on `cubrid+pycubrid://` and `cubrid+aiopycubrid://`, the collection types now have a bind processor that wraps a `list` or `tuple` value (and, for `SET` and `MULTISET`, a `set` or `frozenset`) in `pycubrid.types.Set`, `Multiset` or `Sequence` (matching the column type), which pycubrid sends as a `SET{...}` / `MULTISET{...}` / `SEQUENCE{...}` literal through ordinary `execute()` / `executemany()` (cubrid-lab/pycubrid#567). The feature is detected in the installed pycubrid: the typed classes are on pycubrid main but not in a release yet, and with released pycubrid 1.8.0 values reach the driver unchanged and a collection parameter still raises `ProgrammingError`. A `SEQUENCE` is ordered, so a `set` or `frozenset` bound to it raises `TypeError` ("SEQUENCE is ordered; pass a list or tuple") on the pycubrid drivers with every pycubrid version; it is never sorted. Non-`NULL` collection values cannot be rendered inline (`literal_binds` / `literal_execute` raise `CompileError`). `None`, an already typed value and any other value pass through unchanged; values read back are not converted (`frozenset` / `list` with `?decode_collections=true`). CUBRIDdb is unchanged: it binds every collection itself as a SET, so a MULTISET loses its duplicates and a SEQUENCE its order (Known Issue 11 in `docs/DRIVER_COMPAT.md`). New offline tests cover the processor with and without the pycubrid feature; the new live module `test/test_collection_roundtrip.py` covers Core and ORM, sync and async round trips (SET uniqueness, MULTISET duplicates, SEQUENCE order, Unicode, empty, NULL and NULL elements, executemany, predicates, updates), verified on CUBRID 10.2 and 11.4 with pycubrid main. On released pycubrid these cases are strict xfails; the upstream canary runs them against pycubrid main with `CUBRID_REQUIRE_TYPED_COLLECTIONS=1`. `docs/TYPES.md` ("Collection values"), `docs/DRIVER_COMPAT.md` (+ Korean) and `docs/llms.txt` document the value shapes per driver ([#623](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/623)) by @yeongseon.

- **Re-verified the BLOB/CLOB value contract on pycubrid 1.8.0 and pycubrid main, and moved it to a dedicated module (#485)** — the SQLAlchemy-facing `LargeBinary`/`BLOB`/`Text`/`CLOB` value contract first verified in #490 is moved out of `test_integration.py`/`test_aio_integration.py` into a new `test/test_lob_value_contract.py` (Core and ORM, sync and async, in one module, following the #484/`test_collection_roundtrip.py` pattern), and re-run against the pycubrid 1.8.0 floor, pycubrid main, and CUBRIDdb, on CUBRID 10.2 and 11.4. Binding `bytes`/`str` (and `NULL`) into these columns, and `Text`/`STRING` in general, is unaffected and asserted directly; selecting a non-`NULL` `BLOB`/`CLOB` still returns the driver's own LOB locator shape instead of the documented value on every driver tested (a `dict` handle on sync pycubrid, the bare `file_locator` string on `cubrid+aiopycubrid://`, and CUBRIDdb's `'file:...'` string), so those read cases stay strict xfails, named to the pycubrid feature that would resolve them (cubrid-lab/pycubrid#441) rather than to a pinned version: pycubrid main does not implement official LOB fetch for ordinary cursors yet either (cubrid-lab/pycubrid#441/#442 remain open upstream), so the same xfail applies to both the release and main, and `strict=True` turns a future fix into a failing XPASS instead of silently staying green. Values are still verified to reach the LOB intact via server-side `BLOB_TO_BIT`/`CLOB_TO_CHAR` conversion. `docs/DRIVER_COMPAT.md` Known Issue 6 and `docs/TYPES.md` (+ Korean) are corrected to the 1.8.0/main pin and the async locator's actual shape (a bare string, not a `dict`). CI runs the new module alongside `test_integration.py`/`test_aio_integration.py` in every PR CI lane that already ran those (CUBRIDdb, pycubrid sync, async) and in `integration-full.yml`'s nightly/release CUBRIDdb matrix; `make integration` already picked it up via its directory-wide `-m integration` run. Tests, CI and docs only; no dialect behavior change ([#636](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/636), [#678](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/678)) by @yeongseon.

- **Verified ordinary scalar execution never uses pycubrid's `compat.native` prepared core (#483)** — pycubrid#439 (closed) added an additive, opt-in sync prepared/typed scalar-binding cursor under `pycubrid.compat.native` (INT32, UTF-8 `CHAR` and SQL `NULL` only), already part of the released pycubrid 1.8.0 floor. Ordinary sync/async DB-API execution is unaffected: neither `cubrid+pycubrid://` nor `cubrid+aiopycubrid://` import or call `pycubrid.compat` anywhere, so SQLAlchemy cannot transparently gain typed FC3 binding merely because the installed driver now has it. New dedicated module `test/test_scalar_execution_contract.py` (Core and ORM, sync and async) verifies integer, UTF-8/CJK string, `NULL`, repeated execution of the same compiled statement, ordinary `executemany()`, Core inserts/updates, ORM flush, and a failed scalar bind (NOT NULL violation) followed by connection/session reuse, through the ordinary SQLAlchemy DB-API path only — none of it is blocked or xfailed, verified on CUBRID 10.2 and 11.4 with pycubrid 1.8.0, pycubrid main and CUBRIDdb. An offline test scans the dialect source for any `pycubrid.compat` reference, and a live test monkeypatches `pycubrid.compat.native.connect` to fail if called, then runs ordinary engine operations, to keep the "no dialect implementation change" claim from pycubrid#439's design verified rather than assumed. `docs/DRIVER_COMPAT.md` (+ Korean) documents this as Known Issue 12 (not a bug: a compatibility note). No dialect change ([#637](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/637)) by @yeongseon.


### Changed

- Release preparation moves to SHA-pinned release-please in PR-only mode. Generated Conventional Commit notes are composed with curated Upgrade notes; reviewed candidates still use the existing guarded publisher. Maintainers freeze candidate edits and explicitly start final-head PR CI; see RELEASING.md ([commit ccacf037](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ccacf0375f97576a90eb226155861f5bf96f9d4d)) by @yeongseon.

- **PyPI Trusted Publisher filename** — the sole guarded release orchestrator is renamed from `release.yml` back to `publish-pypi.yml` (environment `pypi`), the filename that published 1.8.0 and that the PyPI Trusted Publisher is bound to. Under `release.yml` the first publication would have been refused with `invalid-publisher`, as happened in pycubrid (cubrid-lab/pycubrid#681). Release, full-matrix, artifact, tag and cookbook gates are unchanged; recovery commands and the successful-publication label reconciliation use the new filename, and a run of the former publish-only workflow of the same name does not count as a completed release. No dialect behavior, version, dependency or support change ([#683](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/683)) by @yeongseon.

- Omit unsupported coverage badges from badge-sync until a coverage feed exists (#645); workflow correction by @yeongseon ([commit fb683495](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fb683495319085debedb18b0272b997530f275b2)); the follow-up automated update was published in [commit c2265867](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c2265867f14fca5b90a2f4ac4c53d324b57b9295).

- Reduce routine PR CI to one representative offline lane and targeted live checks; move full compatibility matrices to explicit dispatch/releases and schedule representative checks weekly ([#659](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/659)) by @yeongseon.

- **KILL QUERY integration test selects only its own active database account (#634)** — the helper used to pick the one transaction that appeared after a timing snapshot and remained active half a second later, so another server session could be killed or make the test ambiguous. The test now creates one fresh `kq634_<16 hex>` account, opens its victim connection before the helper is ready, and the separate helper matches exact `Client_db_user` plus non-null `Query_start_time` in `SHOW TRANSACTION TABLES`. The victim URL explicitly clears any DBA password because the new account has none. Zero matches wait within a bounded deadline; missing columns, invalid indexes or multiple matches fail without KILL. The helper is stopped before the victim connection closes, then only the run-created account is removed with verified cleanup. KILL is not an atomic user-qualified operation, so the disruptive class stays serialized. Offline candidate regressions and live CUBRID 10.2/11.4 tests with both Python drivers preserve -4 and a usable same connection; a separate 11.4 run left an unrelated DBA slow query unharmed. No dialect runtime behavior changed; `docs/DEVELOPMENT.md` (+ Korean) describes the constraint ([#640](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/640)) by @yeongseon.

- **Alembic 1.18+ registers `CubridImpl` through the `alembic.plugins` entry point, so the dialect no longer imports Alembic (#595)** — `pyproject.toml` publishes `_sqlalchemy_cubrid_alembic` in the `alembic.plugins` group, which Alembic 1.18 and later load during `import alembic`; its `setup()` imports `sqlalchemy_cubrid.alembic_impl`. Loading a CUBRID dialect now leaves Alembic unimported on those versions: with Alembic 1.20.0, SQLAlchemy 2.0.54 and Python 3.10 the first `create_engine("cubrid+pycubrid://...")` takes about 18 ms instead of about 80 ms, the `sqlalchemy_cubrid.pycubrid_dialect` import about 147 ms instead of about 207 ms, and it no longer emits Alembic's seven `INFO` `setup plugin ...` lines (#561). `import alembic` logs one more line, `setup plugin sqlalchemy_cubrid`, and takes about 3 ms longer. The dialect decides from installed metadata (Alembic version and this entry point) and keeps the direct import for Alembic 1.7.2–1.17, when Alembic is already imported, or when the metadata cannot be read or does not belong to the importable `alembic` package, so a default `env.py` keeps working on every supported Alembic. Alembic 1.18–1.20 iterate the loaded entry point object although the Alembic documentation describes it as the plugin module, so the plugin module iterates to itself and works with either loader; the plugin is a top-level, standard-library-only module (`_sqlalchemy_cubrid_alembic`), so loading it never imports the `sqlalchemy_cubrid` package, and its `setup()` imports `alembic_impl` inside a `try` and warns instead of raising, so it cannot break `import alembic`. A new `alembic-compat` CI job runs the registration tests on Alembic 1.7.2, 1.17.2, 1.18.0 and the latest release. `docs/ALEMBIC.md` (+ Korean) replaces the #561 statement that no lazy hook exists ([#616](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/616)) by @yeongseon.

- **pycubrid driver policy isolated in the pycubrid dialects; redundant async overrides removed (#596)** — internal refactor, no behavior change on any supported driver path. The pycubrid part of disconnect classification moved from `CubridDialect.is_disconnect()` to `PyCubridDialect`: matching pycubrid's `errno` against the server-session codes (-111, -199, -224, -677) and the legacy-renumbered CAS code -1002, and its client-side messages (`connection lost`, `reconnecting failed`). `CubridDialect` keeps the shared layering (code, `OSError` cause, message) and reads only CUBRIDdb's error shape, an `int` code in `args[0]`, with its CCI/CAS codes; CUBRIDdb's exceptions carry no `errno` and neither CUBRIDdb, CCI nor the CUBRID 11.4 message catalog produces those two messages. `PyCubridAsyncDialect` no longer redefines `on_connect()` and `do_ping()`; it inherits the sync implementations, which reach `pycubrid.aio` through the adapter connection's `autocommit` setter and `ping()`. Verified by the offline suite on SQLAlchemy 2.0 and 2.1, live integration on CUBRID 11.4 for `cubrid://`, `cubrid+pycubrid://` and `cubrid+aiopycubrid://`, and a before/after dump of every dialect attribute plus 12,801 `is_disconnect()` probes: the pycubrid dialects classify every probe identically, and `CubridDialect` differs only for pycubrid-shaped errors. Contributors adding a pycubrid-specific error rule now extend `PyCubridDialect._has_disconnect_code()` or `_disconnect_messages`; `AGENTS.md` and `docs/ARCHITECTURE.md` (+ Korean) describe the split ([#633](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/633)) by @yeongseon.

- **`get_unique_constraints()` skips `SHOW CREATE TABLE` for a table whose catalog shows no unique index (#610)** — the `SHOW CREATE TABLE` fallback ran whenever the `db_index` catalog found no unique index, so reflecting an ordinary table with a primary key and no `UNIQUE` cost a third request and a DDL parse. The catalog query now reads every index of the table with its `is_unique` / PK / FK flags (still one query; on CUBRID 11.2+ it also selects `CURRENT_USER`), and returns `[]` without the fallback when it lists some index of the table but no unique one and the class is the current user's (before 11.2, where class names are global, any visible class). The fallback, and with it the previous result, is kept when the catalog lists no index of the table, and on 11.2+ when the name resolves to another owner's class: an unqualified `SHOW` resolves in the current user's schema, so a granted table of another owner, or for DBA a table only another user owns, still raises `NoSuchTableError` (and is left out of `get_multi_unique_constraints()`) as before. Measured against `main` with a `before_cursor_execute` listener and a fresh `Inspector` on CUBRID 10.2, 11.2 and 11.4 (42 cases, identical results), a current-user table with only a primary key or a foreign key takes 2 requests instead of 3 (median 4.3–5.2 ms → 3.9–4.8 ms per call over 200 calls, local Docker), as DBA and as a non-DBA owner, and so does another owner's table on 10.2; a table with no index (3), a unique constraint or unique index (3), a view (1), a missing table (1, `NoSuchTableError`) and, on 11.2 / 11.4, another owner's class (3, `NoSuchTableError`) are unchanged. A failing catalog query still raises; `duplicates_index` and the PK/FK filtering are unchanged. `test/test_unique_constraint_fallback.py` runs in CI's pycubrid integration step and in the full matrix. `docs/FEATURE_SUPPORT.md` (+ Korean) and `docs/PRD.md` describe the condition ([#629](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/629)) by @yeongseon.

- **Repository-tooling tests moved out of the fast offline run into a separate required lane (#594)** — `make test` (and tox's `py3xx` environments and CI's `offline-tests` job) now select `-m "not integration and not repo"`. `test/conftest.py` applies the new `repo` marker to every test in `REPO_TOOLING_MODULES`: `test_make_integration.py` (the Makefile `integration` recipe and its sh/bash signal handling), `test_docs_reason.py` and `test_release_detect.py`, which run the Makefile and repository scripts through subprocesses. Measured on Python 3.12 with SQLAlchemy 2.0 on the same host: the offline run went from 1,677 tests in 103.4 s (`test_make_integration.py` alone 66.9 s) to 1,495 tests in 22.0 s, with coverage unchanged at 97.32%; the 182 repository-tooling tests take about 95 s on their own. They stay required: the new `repo-tests` CI job runs `-m repo` on Python 3.10–3.14 and `matrix-result` fails unless it succeeds. New targets: `make test-repo` (`-m repo`) and `make test-offline` (both lanes, with coverage); tox gains a `repo` environment. `CONTRIBUTING.md`, `AGENTS.md` and `docs/DEVELOPMENT.md` (+ Korean) describe the lanes ([#621](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/621)) by @yeongseon.

- **Ruff/Mypy pre-commit hooks and tox lint/typecheck envs are single-sourced from the `pyproject.toml` dev pin (#558)** — the Ruff and Mypy pre-commit hooks are now `repo: local` / `language: system` hooks invoking `python3 -m ruff`/`python3 -m mypy` from the active `.[dev]` environment, instead of separately versioned `ruff-pre-commit`/`mirrors-mypy` mirror repos with a `rev:` to keep in sync. `tox -e lint` and `tox -e typecheck-sa20`/`typecheck-sa21` now install the project's own `dev` extra (`extras = dev`) instead of a hardcoded `ruff==`/`mypy==` version in `tox.ini`, and CI's `typecheck` job installs `.[dev,alembic]` instead of a hardcoded `"mypy==2.3.1"`. `scripts/ check_tool_versions.py` was updated to match. This fixes Dependabot's routine `pip`-ecosystem Ruff/Mypy bumps, which previously left `.pre-commit-config.yaml` and `tox.ini` stale and failed the tooling consistency gate (#558) ([#570](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/570)) by @yeongseon.

- **pycubrid 1.8.0 is now the minimum (#559)** — the `[pycubrid]` extra requires `pycubrid>=1.8.0,<2.0` (was `>=1.3.2,<2.0`), because the contract tests already require the 1.8.0 fixes (NOT NULL / foreign-key `IntegrityError`, no silently truncated result after `commit()` / `rollback()`, `cursor.description` `null_ok` and collection type codes) and 1.8.0 keeps the CAS session across `commit()` / `rollback()` and in autocommit mode. README (and translations, several of which still said `>=1.2.0`), `docs/CONNECTION.md`, `docs/DRIVER_COMPAT.md`, `docs/SUPPORT_MATRIX.md`, `docs/DEVELOPMENT.md` (+ Korean) and the workflow comments state the new range ([#564](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/564)) by @yeongseon.

- **pycubrid compliance lanes re-baselined on pycubrid 1.8.0 (#559)** — the `pycubrid@sa2.0` and `pycubrid@sa2.1` steps in `ci.yml` pin `pycubrid==1.8.0` (was 1.7.1). Re-captured on fresh CUBRID 10.2 and 11.4 databases, both lanes fail exactly the same tests as on 1.7.1 (54 on 10.2 for `pycubrid@sa2.0`; 58 / 51 on 11.4 / 10.2 for `pycubrid@sa2.1`), so `test/known_failures.txt` keeps every entry; its header and the CTETest note are updated (pycubrid 1.8.0 still raises the -924 foreign-key restriction as `DatabaseError`; cubrid-lab/pycubrid#390 fixed -631 and -922 only). `docs/SUPPORT_MATRIX.md` and `docs/DEVELOPMENT.md` (+ Korean) list the new pin ([#564](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/564)) by @yeongseon.

- **The pycubrid isolation-level re-apply is kept, and its documentation now describes pycubrid 1.8.0 (#559)** — pycubrid 1.8.0 no longer drops the level at every `commit()` / `rollback()`, but it still opens a new session at the server default level when the CAS itself went away out of transaction (a CAS restart after the transaction, a broker reset). Verified on CUBRID 11.4: when the CAS is killed right after `commit()`, the re-apply keeps SERIALIZABLE, and without it the level falls to READ COMMITTED. The re-apply's SQL `COMMIT` keeps the CAS bound to an idle pooled connection with a configured level (`CLIENT_WAIT` rather than `CLOSE_WAIT`), so if that CAS dies while idle the next statement fails as a disconnect instead of silently running at the default level; `pool_pre_ping=True` replaces such a connection at checkout. `docs/DRIVER_COMPAT.md` Known Issue 10 (renamed), `docs/ISOLATION_LEVELS.md` and `docs/TROUBLESHOOTING.md` (+ Korean) no longer claim that pycubrid reconnects after every commit, rollback or autocommitted statement. No code behavior change ([#564](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/564)) by @yeongseon.

- **`cubrid://` warns at first connect when CUBRIDdb is older than 11.3 (#585)** — `CubridDialect.initialize()` reads the loaded driver's compiled-in version (`CUBRIDdb._cubrid.__version__`, `b'9.3.0.0001'` for the PyPI release) and emits a `SAWarning` naming the version, the recommended `cubrid+pycubrid://` driver and the source-build path when its major.minor is below 11.3. Only major.minor is compared, because a source build's fourth component is a git commit count (a shallow v11.3.0.51 clone reports `11.3.0.0001`). It warns instead of raising `NotSupportedError` so that deployments that followed the old install instructions keep connecting; filter the warning to `"error"` to fail fast. pycubrid engines and a driver whose version cannot be read are not affected. The `ImportError` for a missing CUBRIDdb no longer suggests `pip install CUBRID-Python` ([#588](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/588)) by @yeongseon.

- **`test_show_create_table.py`'s golden cases now run through the real dialect parser instead of a mirror (#590)** — the FK and UNIQUE golden fixtures are parsed by calling `CubridDialect._get_foreign_keys_from_ddl` / `_get_unique_constraints_from_ddl` (the same entry points `get_foreign_keys` / `get_unique_constraints` use, post-#598's `_get_show_create_table_ddl`) through a stub connection, instead of a hand-maintained copy of the parsing logic that had already drifted: it omitted the real parser's `referred_schema` / `duplicates_index` fields and, for a table with more than one foreign key, the real parser's sort-by-name ordering (#531) — the `mixed_pk_fk_unique` fixture is corrected to that sorted order. Test-suite only; no dialect behavior changed ([#618](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/618)) by @yeongseon.

- Earlier release workflow unification with the sibling repos: new `RELEASING.md`; `make release` replaced by the read-only `make release-check VERSION=x.y.z`; `publish-pypi.yml` was manual-dispatch only and then dispatched the cookbook smoke test after a successful publish (replacing `notify-cookbook.yml`); CI lints `CHANGELOG.md` ([#563](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/563)) by @yeongseon.

- **PyPI publish fails closed on duplicate files (#566)** — `publish-pypi.yml` no longer passes `skip-existing: true`. The new stdlib-only `scripts/pypi_duplicate_guard.py` compares the SHA-256 of every verified file with the file PyPI already serves under the same name: an identical file (a partial upload recovered with `gh run rerun --failed`) is dropped from the upload, and a different hash or an unreachable PyPI fails the job. `RELEASING.md` documents the bounded recovery; offline tests cover the guard ([#573](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/573)) by @yeongseon.

- **CI: releases happen automatically when a reviewed release PR is merged (#601)** — `prepare-release.yml` opens the `chore: release vX.Y.Z` PR (moves `[Unreleased]` into a dated section, bumps `__version__`, runs `make release-check`). On every push to `main`, the guarded workflow introduced as `release.yml` decides from git facts only (`scripts/release_detect.py`: version changed against the first parent, dated CHANGELOG section, tag absent or at the same commit) and then runs, pinned to the merge SHA: release check, the full `integration-full.yml` matrix (now also a `workflow_call` workflow, no longer run on tag pushes), one build with SHA-256 hashes, the annotated tag, a draft GitHub Release with SBOM, the PyPI upload through the duplicate guard, and the cookbook verification of that exact version, with one run summary. The cookbook smoke test runs inside the release run as a reusable workflow pinned to a cookbook commit, so it needs no cross-repository token or secret; the release fails unless it reports the requested version installed (#605). `create-release.yml` and the manual `publish-pypi.yml` were removed; a narrow recovery dispatch (`resume`, `verify-only`, `dry-run`) remains. The guarded workflow now uses `publish-pypi.yml` to match the PyPI publisher identity; the former manual publisher is not restored. Ported from cubrid-lab/pycubrid#540 ([#603](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/603)) by @yeongseon.

### Deprecated

- **Python 3.10 support** — advance notice for the 1.9.x release. Python 3.10 reached upstream end of life on 2026-10-01 ([PEP 619](https://peps.python.org/pep-0619/#310-lifespan)). The current 1.8.x line and 1.9.x retain Python 3.10 support. After this notice ships in 1.9.0, the following minor release (planned 1.10.0) will require Python >=3.11. Upgrade Python, recreate your virtual environment and validate your application before upgrading. Current package metadata, CI coverage and runtime behavior remain unchanged; see [support matrix](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/SUPPORT_MATRIX.md) and [roadmap](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/ROADMAP.md).

- **The `[cubrid]` and `[cubriddb]` extras (#585)** — both depend on an unbounded `CUBRID-Python`, and PyPI has no release newer than 9.3.0.2 (sdist only, 2015), so they install a driver this dialect has never tested: on CUBRID 11.4 it returns `BIGINT` as `str` (#583) and fails parts of the integration suite. A version floor would make the extras uninstallable and removing them would change what an existing `pip install "sqlalchemy-cubrid[cubriddb]"` resolves to, so they are kept unchanged for now and marked deprecated. The supported CUBRIDdb is built from cubrid-python v11.3.0.51 or later; `cubrid+pycubrid://` remains the recommended driver. README (+ Korean), `docs/CONNECTION.md`, `docs/DRIVER_COMPAT.md`, `docs/TROUBLESHOOTING.md`, `docs/SUPPORT_MATRIX.md`, `docs/QUICKSTART.md` (+ Korean) and `docs/llms.txt` now document that install path instead of `pip install CUBRID-Python`, and `docs/DRIVER_COMPAT.md`'s build recipe now clones with `--recurse-submodules` and its version check reads `CUBRIDdb._cubrid.__version__` (`CUBRIDdb.__version__` does not exist).

### Fixed

- **Alembic autogenerate no longer pairs a reflected foreign key with a same-named model foreign key on different columns (#624)** — the default-`RESTRICT` correction from #597 matched by name alone, so a reflected `fk_x(a)` was compared with a model `fk_x(b)` and its `RESTRICT` cleared even when the model foreign key on `a` named `RESTRICT` explicitly. A name match now also needs the same columns and target; otherwise the model foreign keys on the same columns are compared.

- **Negative character and bit lengths now fail at compile time (#491)** — VARCHAR, NVARCHAR/NCHAR VARYING, CHAR, NCHAR, BIT, BIT VARYING, BINARY and VARBINARY reject explicit negative lengths with `CompileError`, matching the existing zero-length contract; omitted and positive lengths are unchanged ([#662](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/662)).

- **The nightly mutation-testing lane measures again instead of stopping at "failed to collect stats" (#628)** — `test/conftest.py` imports `scripts.integration_urls` inside its `pytest_collection_modifyitems` hook (added with the integration gate in #604), but `mutmut run` populates `mutants/` with `source_paths` (`sqlalchemy_cubrid`) plus a fixed list — `test/`, `tests/`, `setup.cfg`, `pyproject.toml`, the lock files — and nothing else unless `also_copy` names it. Inside that sandbox the hook raised `ModuleNotFoundError: No module named 'scripts'`; because it raised from a pytest hook rather than a test module, pytest reported an `INTERNALERROR` and exited 3, and mutmut stopped with `failed to collect stats. runner returned 3` before generating any result — reproduced locally on `main` (da752c4). The job's history pins the cause: #604 merged at 2026-09-30T11:46Z, the last passing run started at 2026-09-30T09:29Z (56d4d90) and the first failing one at 2026-09-30T13:21Z (5f1e07e), with every run since failing the same way. `setup.cfg [mutmut]` now sets `also_copy = scripts`; mutmut appends that to its built-in list rather than replacing it, so the sandbox keeps everything it copied before and can now import `scripts` as well. The lane completes and reports a score again (949 killed of 1340 mutants, 70.8%, on Python 3.12 with SQLAlchemy 2.1.1), which satisfies the workflow's total-greater-than-zero and killed-greater-than-zero checks; the job stays `continue-on-error` and non-gating. `test/test_mutmut_sandbox.py` guards the next occurrence: it parses the imports of `conftest.py` and of each module in `pytest_add_cli_args_test_selection`, and fails when a first-party top-level package is neither a `source_paths` entry nor listed in `also_copy` ([#639](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/639)) by @paikend.

- **An aiopycubrid read timeout invalidates the connection on Python 3.10 (#624)** — pycubrid's async driver retires the session and raises `OperationalError` from `asyncio.TimeoutError`, which is an `OSError` only from Python 3.11. On 3.10 `is_disconnect()` returned `False` for it, so the pool kept a connection the driver had already closed. An `asyncio.TimeoutError` in the explicit cause chain now counts as a transport failure on every supported Python.

- **A server error whose text happens to contain a disconnect phrase no longer invalidates the connection (#624)** — CUBRID error messages echo application data, so `SELECT 1 FROM [connection refused]` (-493), a failed cast of the literal `'lost connection'` (-494) or `RAISE_APPLICATION_ERROR(1001, 'connection refused by policy')` (-889) matched the message fallback of `is_disconnect()` and the pool discarded a healthy connection. The fallback is now skipped for an error that carries a server error code, except -190, -191 and -368, whose own text reports a failed server connection. Disconnect codes, `OSError` causes and driver errors without a server code are classified as before. Recorded on CUBRID 11.4.6 with pycubrid.

- **`get_unique_constraints()` no longer trusts an empty catalog result when the server version is unknown (#624)** — the owner check added in #610 applies from CUBRID 11.2, so with no `server_version_info` a table whose catalog rows might belong to another owner's class was reported as having no unique constraint. `SHOW CREATE TABLE` now decides in that case, as it did before #610. A connected engine always knows its server version, so ordinary reflection is unchanged.

- **pycubrid's malformed-reply error invalidates the connection (#680)** — when a broker reply cannot be parsed, pycubrid closes the connection and raises `OperationalError("malformed response from broker")`. `is_disconnect()` did not recognize it, so the closed connection went back to the pool and the next statement failed with "connection is closed" before it was replaced. The message is now a disconnect pattern of the pycubrid dialects ([#681](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/681)).

- Isolate CI cancellation by event/ref; include the CI execution policy in generated documentation and use a working policy URL in both LLM indices (PR #659 follow-up).

- **Empty emphasized link captions no longer exempt documentation updates (#648)** — synchronize `scripts/check_docs_reason.py` with the reviewed pycubrid#573 helper so emphasis around an empty comment or image is not counted as a visible explanation. Regression tests retain all four pycubrid#429 case families and a populated emphasized-reason control; existing event-JSON tests and maintainer-label exceptions are unchanged ([#649](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/649)).

- **Collection domains and authorized ENUM values reflect without guessing (#631)** — `get_columns()` no longer overwrites a native ENUM with `NullType` or misses the server's `SET OF` / `MULTISET OF` / `SEQUENCE OF` forms. CUBRID prints ENUM labels without escaping, so a single label containing `', '` can look exactly like two labels; an authorized reader now gets exact ordered values from `_db_domain.enumeration` through SQL rows, while a specific non-DBA `-494` denial warns and returns `NullType` instead of inventing labels. Other catalog failures propagate. Collection members use the public `db_attr_setdomain_elm` view; incomplete or inconsistent member rows warn and return `NullType`; so does an OBJECT member whose class was dropped, or a member type the dialect cannot express, which no longer fails the rest of the table; and `MONETARY` members reflect as `MONETARY`; the catalog lookups read instance attributes only, and an ENUM or collection column whose name `SHOW COLUMNS` lists twice (a `CLASS ATTRIBUTE` of the same name) warns and returns `NullType`; on 11.2+ an OBJECT member of another owner than the table reflects as `owner.class`, and an `ENUM` member warns and returns `NullType`. Member collations are not reflected. An untyped collection uses `db_attribute` for its kind. The #611 recordings and `test/test_reflection_enum_collection.py` exercise the supported server outputs and authorized reflect→create round trips. Full ENUM reflection for non-DBA users remains unsupported pending an authorized public metadata source; see `docs/TYPES.md` (+ Korean).

- **Column reflection accepts whitespace in numeric type parameters (#609)** — `get_columns()` stripped the parameter list from a `SHOW COLUMNS` type only when it had no spaces, so `NUMERIC(10, 2)` / `DECIMAL(10 , 2)` was looked up as an unknown type and reflected as `NullType` with a "Did not recognize type" warning, while `NUMERIC(10,2)` reflected as `NUMERIC(10, 2)`. Whitespace around the comma is now accepted for top-level columns and for `SET` / `MULTISET` / `SEQUENCE` members, and precision and scale are read from it. Only digit lists are stripped, so `CHAR` / `VARCHAR` lengths, `BIT` / `BIT VARYING`, collection splitting and the warning for unrecognized types are unchanged. This is parser robustness: on CUBRID 10.2, 11.0, 11.2 and 11.4, `SHOW COLUMNS` prints the compact form (`DECIMAL(10, 2)` is shown as `NUMERIC(10,2)`), so no supported-server regression was observed ([#626](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/626), refs [#615](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/615)).

- **Alembic autogenerate no longer drops and re-creates an unchanged foreign key declared without `ondelete` / `onupdate` (#597)** — CUBRID's default referential action is `RESTRICT` and `SHOW CREATE TABLE` always prints it, so `get_foreign_keys()` reflects such a key as `ondelete="RESTRICT"`, `onupdate="RESTRICT"`, and every `alembic revision --autogenerate` proposed `drop_constraint` + `create_foreign_key` for it. `CubridImpl.correct_for_autogen_foreignkeys()` now clears a reflected `RESTRICT` where the matching model foreign key has no action, the same Alembic hook its MySQL implementation uses for MySQL's defaults. Reflection is unchanged and still reports `RESTRICT`. Adding, removing or changing `CASCADE` / `SET NULL` is still detected; a reflected key is matched to the model by name first, and an unnamed one has its `RESTRICT` cleared only when every model key on the same columns and target has no action. `NO ACTION` versus no action stays undetected, as before (Alembic treats them as equal). Verified with a default `env.py` on CUBRID 11.4 and 10.2 ([#622](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/622)).

- **`is_disconnect()` no longer reads an error code out of message text (#608)** — `_extract_error_code()` parsed the first token of any string `args[0]` as an integer, so a message that merely started with a number was classified by that number: `pycubrid.DataError("-20004 rows rejected by application validation", errno=-495)` was reported as a disconnect and SQLAlchemy invalidated a working pooled connection. Neither driver puts a code in its message (CUBRIDdb raises `(int code, message)`, pycubrid keeps the code in `errno`), so codes are now read only from an integer `args[0]` (not `bool`) and an integer pycubrid `errno`. The disconnect code tables, the `OSError` cause check and the message-pattern fallback are unchanged, so a CAS killed mid-transaction (CUBRIDdb -20004, pycubrid `connection lost during receive`) and a stopped `cub_server` (-190/-191 `Failed to connect to database server`) are still detected on `cubrid://`, `cubrid+pycubrid://` and `cubrid+aiopycubrid://`. `docs/CONNECTION.md` and `docs/DRIVER_COMPAT.md` (+ Korean) describe the rule ([#620](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/620)).

- **Unreachable configured CUBRID servers fail integration tests instead of silently skipping (#593)** — Previously six live test modules skipped at import time when their server could not be reached; an unreachable `CUBRID_TEST_URL` made 421 of 447 integration tests skip, even with `CI=true`. A single `pytest_runtest_setup` gate now probes `SELECT 1` once per session using the driver named by the configured synchronous URL (`cubrid://`, `cubrid+cubriddb://` or `cubrid+pycubrid://`); it reports errors rather than skipped tests when that server is unavailable. With `CI=true`, selecting integration tests without `CUBRID_TEST_URL` fails before execution; without a configured URL, ordinary local integration tests may skip. An optional `CUBRID_TEST_AURL` is checked through `cubrid+aiopycubrid://`. URL validation and password masking are shared with `scripts/wait_for_cubrid.py`; `--dburi` compliance runs and per-driver `CUBRID_REQUIRE_*` switches (#486) retain their behavior. The old unreachable-server example now yields 447 errors and exit code 1; dedicated test database requirements and canary configuration are documented in the development guides.
- **`replace()` emits `REPLACE` as the statement verb instead of rewriting the first `INSERT INTO` in the compiled SQL (#591)** — `visit_replace()` compiled the statement as an `INSERT` and replaced the first `INSERT INTO` substring. With `prefix_with()`, SQLAlchemy renders `INSERT <prefix> INTO`, so the substitution hit an `INSERT INTO` inside the prefix, a comment, a string literal (`literal()` / `literal_column()` / `literal_binds`) or a quoted identifier instead: the statement stayed a plain `INSERT` (a duplicate key raised `IntegrityError` instead of replacing the row) and the stored value became `'REPLACE INTO'`. The compiler now swaps only the verb SQLAlchemy writes first (after the `WITH` clause, if any), so `replace(t).prefix_with("/* c */")` renders `REPLACE /* c */ INTO t ...` and values, identifiers, comments, bind parameters and their order are left untouched, including multi-row `values()`, `executemany` and `from_select()`. An unexpected compiled form now raises `CompileError` instead of `NotImplementedError`. Verified on CUBRID 11.4 with SQLAlchemy 2.0 and 2.1 ([#600](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/600)).

- **`cubrid+pycubrid://` and `cubrid+aiopycubrid://` forward URL query options to pycubrid (#592)** — `create_connect_args()` read only the host, port, database, user and password, so `?connect_timeout=5` or `?charset=euckr` connected without error and had no effect. Both dialects now share one implementation that forwards `charset`, `connect_timeout`, `read_timeout`, `fetch_size`, `ssl`, `decode_collections`, `no_backslash_escapes` and `enable_timing`, converted to the type pycubrid expects (positive float seconds, integer
  >= 1, boolean). An invalid or repeated value, an option that belongs in the URL itself (`host`,
  `port`, `database`, `user`, `password`), `autocommit` and `json_deserializer` raise `ArgumentError` from `create_engine()`; other keys are ignored with pycubrid's `UnknownConnectionOptionWarning` and a spelling suggestion, as `pycubrid.connect()` reports unknown keywords (cubrid-lab/pycubrid#377). `charset` needs a pycubrid release newer than 1.8.0 (cubrid-lab/pycubrid#510): with pycubrid 1.8.0 it raises `ArgumentError` naming the installed version instead of a `TypeError` or a silently ignored option. The CUBRIDdb `cubrid://` dialect is unchanged (CUBRIDdb's `connect()` takes no keyword options). `docs/CONNECTION.md` (+ Korean) documents the URL query options ([#599](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/599)).

- **`get_foreign_keys()` and `get_unique_constraints()` no longer report a failed `SHOW CREATE TABLE` as "no constraints" (#589)** — both methods (for `get_unique_constraints()`, only its `SHOW CREATE TABLE` fallback, taken when `db_index` lists no unique index) caught every exception from `SHOW CREATE TABLE`, logged a warning and returned `[]`, so a disconnect, an authorization error or a driver bug looked like a table without foreign keys and Alembic autogenerate emitted `add_fk` for foreign keys that already exist. **Behavior change:** `Unknown class` still raises `NoSuchTableError` (#530), and no `SHOW CREATE TABLE` row for a table the catalog listed now raises `NoSuchTableError` too; every other exception propagates unchanged (a disconnect keeps `connection_invalidated`), and the `SHOW CREATE TABLE failed ...` warning is gone. `[]` now means the query succeeded and found no constraint. No leniency is kept for non-DBA users: on CUBRID 10.2 and 11.4 a non-DBA user sees in `db_class` only tables it holds `SELECT` on, and `SHOW CREATE TABLE` on such a table does not fail with an authorization error (without `SELECT` the table is not listed and reflection raises `NoSuchTableError` before running it), and no catalog view exposes the referenced table or columns of a foreign key. Views still return `[]` without running `SHOW CREATE TABLE`. `docs/FEATURE_SUPPORT.md`, `docs/TROUBLESHOOTING.md` and `docs/ALEMBIC.md` (+ Korean) describe the contract.

- **The advisory Alembic safety checker now counts DDL calls, not attribute references (#447)** — `scripts/alembic_safety_check.py` counted every `ast.Attribute` whose name was a DDL operation, so `operations = [op.create_table, op.drop_table]` produced a two-DDL warning although nothing was called, and its operation list lacked `create_unique_constraint`, `create_foreign_key`, `create_check_constraint` and `create_primary_key`, so a revision with two constraint calls was reported clean. It now counts only calls (`op.x(...)`, `batch_op.x(...)`) and includes those four operations; `upgrade()` and `downgrade()` are still assessed separately and the checker stays advisory. New offline tests in `test/test_alembic_safety_check.py`; the copied script in `docs/ALEMBIC.md` (+ Korean) and `docs/llms-full.txt` are updated ([#587](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/587)).

- **`has_table()` / `has_index()` no longer report missing objects as existing under `cubrid://` with the PyPI `CUBRID-Python` driver (#583)** — both methods returned `bool(result.scalar())` on a catalog `COUNT(*)`, which is `BIGINT` in CUBRID. The `CUBRID-Python` 9.3.x releases on PyPI fetch `BIGINT` as `str`, so `bool('0')` was `True`: every missing table or index looked present, `create_all(checkfirst=True)` silently skipped the `CREATE`, and `drop_all(checkfirst=True)` failed with `-494 Unknown class`. The count is now coerced with `int(...)` before the comparison, so `int`, `str`, `Decimal` and `None` results all work. CUBRIDdb built from `cubrid-python` v11.3.0.51 (the CI driver) and pycubrid return `int` and were not affected ([#584](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/584)).

- **Follow-ups from the #577 disconnect-code audit (#578)** — -10002 (`CAS_ER_NO_MORE_MEMORY`) is added to `_disconnect_error_codes`: `cas.c`'s `process_request()` sends it when the CAS's read-buffer allocation fails and then returns `FN_CLOSE_CONN`, closing the connection (CUBRID v11.4.6 `src/broker/cas.c`); before this, the disconnect was only caught one call late, on the next statement's or the rollback's -20004. The `dialect.py` comment on why pycubrid does not report the CAS/CCI codes above is reworded: pycubrid does not negotiate CUBRID's renewed error-code protocol, so the CAS answers it with the legacy, unprefixed codes instead (e.g. -4 for `ER_INTERRUPTED`), which pycubrid keeps in `errno`. A CAS code specifically (`cas_error.h`, sent with `CAS_ERROR_INDICATOR`) is instead legacy-renumbered by the CAS itself (`CAS_CONV_ERROR_TO_OLD`, `src/broker/cas_protocol.h`: `+9000`) before it reaches a driver that doesn't advertise understanding the renewed protocol, so pycubrid actually receives -1002 for `CAS_ER_NO_MORE_MEMORY`, not -10002; this was previously undetected (the errno check only covered the four server-session codes from #565) and is now matched too, in a new `_pycubrid_legacy_cas_codes`, with an offline test (found in review). `docs/TROUBLESHOOTING.md` (+ Korean)'s Interrupted Query (-4) section now shows the real, driver-specific strings instead of an abbreviated one: CUBRIDdb's `(-4, 'ERROR: DBMS, -4, Has been interrupted.[CAS INFO-...]')` and pycubrid's `Has been interrupted. (errno=-4, description='Communication error', sqlstate='08S01')`, both captured live on CUBRID 11.4. The `KILL QUERY` integration test helper (`test/test_integration.py`) still identifies its victim by timing, not by SQL text: CUBRID's `SHOW TRANSACTION TABLES` and `SHOW THREADS` expose neither the running statement's text nor any field an application can tag (verified live), so the slow query is now tagged with a unique SQL comment for finding it by eye in a broker SQL log, and the helper's docstring and the script now document that it identifies the victim by timing and is reliable only when it is the sole session running a slow query against the target instance, and that waiting on it through a pipe with `select()` is POSIX-only. Offline tests cover -10002 alongside the other kept codes; verified live on a dedicated CUBRID 11.4 container with both drivers (5 repeated runs each) ([#582](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/582)).

- **Integration runs now wait for a ready CUBRID server instead of sleeping (#575)** — A fixed 10-second delay after Docker startup caused false CCI -20004 failures, incorrect Enum capability results, flaky reflection fuzz tests and skipped live tests on cold containers; these were **startup timing issues, not dialect or driver limitations**. The prior full suite already passed with both drivers on running CUBRID 10.2/11.2/11.4 and SQLAlchemy 2.0.53/2.1.1. `scripts/wait_for_cubrid.py` now retries `SELECT 1` using the selected driver until readiness or `INTEGRATION_READY_TIMEOUT` (default 180 seconds); pycubrid attempts have five-second socket timeouts. `make integration` defaults to `cubrid+pycubrid://`; `INTEGRATION_DRIVER=cubriddb` selects the CUBRIDdb extension, while invalid drivers exit 2 **before any Docker command**. Existing ownership, signals and cleanup remain unchanged (#567 and #568). A required PR CI job runs the complete pycubrid integration suite on CUBRID 11.4; nightly/tag jobs run both drivers on 10.2 and 11.4 (CUBRIDdb builds its native extension, so those cells are not per-PR). `integration-local` still uses the caller's `CUBRID_TEST_URL`. New regression tests pin readiness and driver selection; English/Korean development docs and contribution guidance explain coverage ([#581](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/581)).

- **The pool invalidates connections broken by a `cub_server` stop, restart or crash (#565)** — after `cub_server` goes away, a connection inside a transaction fails with -111 (`ER_TM_SERVER_DOWN_UNILATERALLY_ABORTED`) and then -224 (`ER_OBJ_NO_CONNECT`) on every statement until the transaction ends, even after the server is back, because the broker's CAS reconnects only then. `is_disconnect()` did not classify these codes, so SQLAlchemy kept the connection, and `pool_pre_ping` cannot catch it because the CAS still answers the ping. The dialect now treats the four codes for which the broker resets the CAS (`reset_flag` in CUBRID's `cas_error.c`) as disconnects on both drivers: -111, -199 (`ER_NET_SERVER_CRASHED`), -224 and -677 (`ER_BO_CONNECT_FAILED`). CUBRIDdb carries the code in `args[0]`; pycubrid carries it only in `errno`, which is now read for these four codes (the older code table is still not matched against pycubrid's `errno`, whose -4 is the server's `ER_INTERRUPTED`). pycubrid's `CAS did not answer CHECK_CAS out of transaction and reconnecting failed`, raised after it closes the connection, is also a disconnect. The message patterns are now matched against the driver's own message instead of pycubrid's `str()`, which appends a description of `errno`: a pycubrid error with errno -4 (the server's `ER_INTERRUPTED`, e.g. an interrupted query) or -671 read `Communication error` there and was wrongly treated as a disconnect (CUBRIDdb's -4 is tracked in #572). -671 (`ER_CSS_RECV_OR_SEND`) stays out, as evaluated in #564. The new `test/test_server_restart.py` stops and starts `cub_server` in the test container (`CUBRID_TEST_DOCKER_CONTAINER`) and checks, through both drivers and with and without `pool_pre_ping`, that the connection is invalidated and the pool recovers; it runs as the last step of the CI and nightly integration jobs. `docs/CONNECTION.md`, `docs/DRIVER_COMPAT.md` and `docs/TROUBLESHOOTING.md` (+ Korean) describe the codes, and `docs/DEVELOPMENT.md` (+ Korean) the test ([#571](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/571)).

- **An interrupted query no longer invalidates a CUBRIDdb connection, and a dead CAS now does (#572)** — the numeric disconnect code table matched against CUBRIDdb's `args[0]` was audited against CUBRID's `error_code.h`, `cas_error.h` and CCI's `cas_cci.h`. It listed -4, -10005, -10007, -21003 and -21005, none of them a disconnect for either driver: -4 is the server's `ER_INTERRUPTED` (a query interrupted by `KILL QUERY`), so CUBRIDdb connections were replaced although they still worked; -10005 and -10007 are `CAS_ER_TRAN_TYPE` and `CAS_ER_NUM_BIND`; -21003 and -21005 are CUBRID JDBC codes (`ER_COMMUNICATION`, `ER_TYPE_CONVERSION`) that neither Python driver raises. The table now holds the codes CUBRIDdb raises for a dead or unusable connection: -20004 (`CCI_ER_COMMUNICATION`) and -10003 (`CAS_ER_COMMUNICATION`), which CCI itself treats as communication errors, -20002 (`CCI_ER_CON_HANDLE`) and -20016 (`CCI_ER_CONNECT`). -20004 was missing: when the CAS died in a transaction, CUBRIDdb's `Cannot communicate with server` matched neither a code nor a message pattern, so the broken connection stayed in the pool. The four server-session codes from #565 are unchanged, and pycubrid's `errno` is still matched only against them. Offline tests pin every removed code as a non-disconnect and every kept code as a disconnect for CUBRIDdb-style and pycubrid errors; a new integration test interrupts a running query with `KILL QUERY` from a second process and checks, on whichever driver `CUBRID_TEST_URL` selects, that the error is -4 and the connection is kept. `docs/CONNECTION.md`, `docs/DRIVER_COMPAT.md` and `docs/TROUBLESHOOTING.md` (+ Korean) are updated ([#577](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/577)).

- **`CHAR(0)` / `NCHAR(0)` no longer silently compile to bare `CHAR` / `NCHAR` (#476)** — the type compiler still checked fixed-width lengths by truthiness after #456, so an explicit `length=0` was treated as unspecified. `length=None` still emits bare `CHAR` / `NCHAR`; an explicit zero now raises `CompileError` ([#477](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/477)) by @HarshRajSinghania.

- **`BIT(length=0)` is no longer silently coerced to `BIT(1)` (#441)** — `BIT.__init__` used `length or 1`, so an explicit zero became 1 before the compiler ran. Unspecified length still defaults to `BIT(1)`; `BIT VARYING` with no length is still unlimited. An explicit zero now raises `CompileError` ([#478](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/478)) by @HarshRajSinghania.

- **Reflection no longer reports a syntax error as a missing table (#454)** — `get_columns()` and `get_indexes()` raised `NoSuchTableError` for any `SHOW COLUMNS` / `SHOW INDEXES` failure with native code -493, SQLSTATE `42S02` or a `Table not found` message. CUBRID uses -493 for every parser error (pycubrid before 1.8.0 also reports SQLSTATE `42S02` with a `Table not found` description for all of them), so a syntax error, such as the one CUBRID 11.4 raises for a table name containing `]`, was hidden behind `NoSuchTableError`. Both methods now translate only the server's `Unknown class "<owner>.<name>"` error, like the other reflection methods since #530, and let any other error propagate unchanged. Missing tables still raise `NoSuchTableError`; a live test in `test/test_integration.py` covers both cases. `docs/TROUBLESHOOTING.md` (+ Korean) documents the rule. Thanks to @UsmanGhias for the fix and tests ([#455](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/455), co-authored by @yeongseon).

- **Interrupted `make integration` runs clean up their own Docker stack (#568)** — The recipe now traps `SIGINT`, `SIGTERM` and `SIGHUP`, including Ctrl-C and `timeout`, rather than relying only on an EXIT trap. Compose startup, readiness checks and pytest run as waited background steps. An in-progress `docker compose up -d` gets up to `INTEGRATION_STOP_GRACE` (10 seconds by default) to finish before its process group is terminated, avoiding containers and volumes left by interrupted startup; other steps are terminated and, if necessary, killed after the same grace period. The recipe invokes `docker compose -p <project> down -v` once in an isolated session, only for resources owned by this run (#567), and returns status 128 plus the signal number. Cleanup ignores subsequent signals; `SIGKILL`, host shutdown and `SIGQUIT` are outside the guarantee. Pytest retains terminal stdin for `--pdb`, and `integration-local` does not use Docker. Shell and process-group regressions and English/Korean development guidance document these boundaries ([#574](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/574)).
- **`make integration` no longer removes a Compose project or volume it did not create (#567)** — since #446 the recipe ran `docker compose down -v` on every exit, including a failed `docker compose up -d`, against the default Compose project. If a stack of that project already existed (for example from `docker compose up -d` or `make docker-up`), a failed startup could delete its named `cubrid-data` volume. Each run now uses its own Compose project (`sqlalchemy-cubrid-it-<timestamp>-<pid>`, overridable with `INTEGRATION_PROJECT`, which must match `^[a-z0-9][a-z0-9_-]*$` and is validated before any Docker command), checks that the project has no containers, volumes, networks or `<project>_cubrid-data` volume, and refuses to run, starting and removing nothing, if it does; a failing probe (for example an unreachable daemon) also stops the run before startup, with an explicit "nothing was started" message. Two concurrent runs with the same fixed `INTEGRATION_PROJECT` are not supported. Cleanup is registered only after that check and runs `docker compose -p <project> down -v`. The original failure is still preserved when cleanup also fails, and `integration-local` still never touches Docker. `docker-compose.yml` and `make integration` accept `CUBRID_PORT` for the host port (default 33000). Stub-based subprocess regressions cover a pre-existing project or volume with successful and failed startup, each failing ownership probe, exact volume-name matching, setup and test failures, cleanup failure and success. `docs/DEVELOPMENT.md` (+ Korean) and `CONTRIBUTING.md` document the ownership boundary ([#574](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/574)).

- **Docker integration cleanup runs after failures (#446)** — `make integration` now registers shell-exit cleanup before starting Docker, so failed startup, readiness waiting and tests all attempt `docker compose down -v`. An original failure is preserved if cleanup also fails; cleanup-only failure is reported and returns a failing status. Offline subprocess regressions cover both test outcomes, cleanup failures, setup failures and the unchanged Docker-free `integration-local` target ([#508](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/508)) by @soyeladice-svg.

* **alembic:** require matching columns for a foreign key name match ([#668](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/668)) ([147d201](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/147d201abd618d51144afec67f77e6454bf41a3c)), refs [#624](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/624)

* **ci:** isolate scheduled runs and publish the CI policy ([5eb6c26](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5eb6c26403c360d19237bbad5fbaecf3258f75dd))

* **dialect:** ignore disconnect phrases in server error text ([#676](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/676)) ([fb4eccd](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fb4eccde05cb2f62ce365c27b083526ad93c6488))

* **dialect:** treat an asyncio timeout cause as a disconnect ([#672](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/672)) ([caa3fbe](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/caa3fbeec4d63f831192e967129acf98b9af5eea)), refs [#624](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/624)

* **reflection:** avoid fabricating ENUM and collection domains ([#635](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/635)) ([dd74cdb](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/dd74cdb292ee8733862e662647985b744b8504c9)), refs [#631](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/631)

* **reflection:** avoid false-empty constraints after DDL lookup failures ([09014a1](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/09014a14938712a346b9e4cc02181e8510dcafa7))

* **reflection:** keep the DDL fallback when the server version is unknown ([#675](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/675)) ([cc4aa9a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/cc4aa9a4727e997fa7d5c19c51588786b0ac3fa2)), refs [#624](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/624)

### Documentation

- Prepare an ORM/Alembic video recording script and defer the Quick Start embed until a verified MP4 is present (#374).

- **Refreshed current support claims and removed stale test statistics (#461)** — README, AGENTS.md, ROADMAP.md, SECURITY.md, `docs/SUPPORT_MATRIX.md`, `docs/DEVELOPMENT.md`, `docs/TYPES.md` and `docs/PRD.md` (+ Korean where applicable) carried a hardcoded `619 offline tests` / `~98.26% coverage` snapshot in half a dozen places (several already disagreeing with each other, e.g. `603` in one and `619` in another), AGENTS.md still listed version `1.4.3.dev0`, ROADMAP.md still said the current line was `v1.6.x`, and SECURITY.md's supported-version table stopped at `1.4.x`. These are replaced with durable statements (the CI coverage gate is `--cov-fail-under=95`; run the `offline-tests` job or `make test` (`pytest --cov=sqlalchemy_cubrid --cov-report=term-missing`) locally for current counts) instead of another pinned snapshot that would go stale again. `docs/DEVELOPMENT.md` and `docs/SUPPORT_MATRIX.md` (+ Korean) also described the reduced PR integration matrix as a full `{3.10, 3.14} × {10.2, 11.0, 11.2, 11.4}` cross product (a `CI Matrix` checkmark table in `docs/DEVELOPMENT.md` literally marked all four CUBRID rows for both Python columns); it is corrected to the actual 2 combinations `ci.yml` runs (3.14×11.4, 3.10×10.2). README's Known Limitations and `docs/TYPES.md`/`docs/SUPPORT_MATRIX.md` (+ Korean) said CUBRID's `TIMESTAMPTZ`/`TIMESTAMPLTZ`/`DATETIMETZ`/`DATETIMELTZ` reflection was indistinguishable from plain `TIMESTAMP`/`DATETIME`; `dialect.py`'s `ischema_names` has reflected them as four distinct `timezone=True` dialect types since #181/#442, so the type-mapping tables now document them. SECURITY.md's supported-versions table is replaced with the project's actual policy (a single rolling release line on `main`, no parallel maintenance branches; only the latest release gets security fixes). The non-functional `codecov` badge (no upload step exists in any workflow) is removed from README and its translations rather than left pointing at a permanently "unknown" status. `docs/llms-full.txt`/`llms.txt` regenerated ([#643](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/643)).

- **Quick Start uses the recommended pycubrid driver (#495)** — English and Korean Quick Start docs now use `sqlalchemy-cubrid[pycubrid]` / `cubrid+pycubrid://` as the primary path and point C-extension users to the supported CUBRID-Python 11.3.0.51+ source-build path ([#516](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/516)) by @soyeladice-svg.

- Contributor setup docs no longer list redundant `pip install` steps for tools included in the `[dev]` extra (#497).

- **`llms.txt` capabilities corrected and the two entry points single-sourced (#460)** — the root `llms.txt` said CUBRID has no JSON support, advertised six isolation levels, described only two driver backends and linked to the retired `cubrid-cookbook/python` paths, while `docs/llms.txt` was a separately maintained, differing index. `docs/llms.txt` is now the only maintained index, checked against the code: native `JSON` (CUBRID 10.2+), the three MVCC isolation levels (4/5/6) plus `AUTOCOMMIT` with `CURSOR STABILITY` and the long `SCHEMA, INSTANCES` spellings as aliases only, the three driver variants (`cubrid+pycubrid://`, `cubrid+aiopycubrid://`, `cubrid://` / `cubrid+cubriddb://`) with their install extras, no driver in the bare install, single-schema reflection and `cubrid-cookbook-python` links. `scripts/generate_llms_full.py` copies it byte-for-byte to the root `llms.txt`, and the CI `lint` job now fails when either `docs/llms-full.txt` or `llms.txt` is stale. `CONTRIBUTING.md` documents the workflow ([#579](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/579)).

- **Alembic import log lines (#561)** — `docs/ALEMBIC.md` (+ Korean) explains that loading the dialect imports Alembic when it is installed (about 0.1 s), so Alembic 1.18+ logs seven `INFO` `setup plugin ...` lines under `INFO` root logging, and gives the application-side fix `logging.getLogger("alembic").setLevel(logging.WARNING)`. No supported Alembic hook defers the registration; no behavior change ([#562](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/562)).

- **SQLAlchemy 2.1 is documented as released and tested, not a pre-release (#492)** — `docs/SUPPORT_MATRIX.md` (+ Korean) listed 2.1.x as the "latest tested pre-release until GA"; it now says CI tests SQLAlchemy 2.1.1. `docs/SA_COMPAT.md` describes the non-blocking canary as what it is: a `--pre` install of `SQLAlchemy>=2.1.0b1,<2.3` that tracks upcoming SQLAlchemy pre-releases with `continue-on-error` ([#506](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/506)) by @PandaHUN777 (first contribution 🎉).

- **Samples use the recommended pycubrid driver (#498)** — `samples/create_engine.py` and `samples/cubrid_datatypes.py` connected with `cubrid://`, the CUBRID-Python C-extension dialect, which a plain install does not provide. They now use `cubrid+pycubrid://` and name the install command `pip install "sqlalchemy-cubrid[pycubrid]"` in their docstrings ([#509](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/509)) by @soyeladice-svg (first contribution 🎉).

* add MP4 demo tape + QUICKSTART video embed ([#346](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/346)) ([ed4893b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ed4893b2945d06bfd811278b105466c09b212889))

* **contributing:** keep issue specifications current and assign owners ([#650](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/650)) ([7414fdb](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7414fdbf6c513758b2f5590e55bcf7f3e361d68f))

* **demo:** prepare ORM and Alembic recording; defer MP4 embed ([#374](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/374)) ([ed4893b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ed4893b2945d06bfd811278b105466c09b212889))

* derive Sphinx release from package version ([#499](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/499)) ([3f5c4f5](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3f5c4f5135bd3cc7f209905edc794419aa442e09)) by @HarshRajSinghania (first contribution 🎉)

* **development:** avoid duplicate installs of dev dependencies ([#663](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/663)) ([9ef691b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/9ef691b8e0a85b8227ee81e7d64de721e1a162f8))

* mention repository and full offline test lanes ([#647](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/647)) ([e4b90f0](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/e4b90f050324154a23306a8b8b88ec05f2a28423)) by @soyeladice-svg

* pin cookbook smoke-test fallback to the exact release ([#576](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/576)) ([ad47e3b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ad47e3bac6484d5dda4c8faa5b5736c58a363f21))

* **python:** announce Python 3.10 support retirement ([#665](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/665)) ([4221b25](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/4221b252fabf2aa67b6d1c02cab531fa02ba1597))

* **reflection:** state when another owner's class reaches the DDL fallback ([#673](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/673)) ([7c676fa](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7c676fafe3bafcc7e85772328d22362cfae023ea))

* **release:** document release-please review and recovery ([#657](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/657)) ([a01c338](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a01c3385ed4d8f4327c6dae55c13b386cc07cdef))

* **types:** record the tested non-DBA ENUM reflection limitation ([#677](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/677)) ([112fde7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/112fde7d934b15a099ba9a044acc6429dd170e5d))

## [1.8.0] - 2026-09-29

This release includes substantial dialect and integration changes. Review the upgrade notes and the detailed sections below to assess compatibility and migration impact.

### Upgrade notes

Behavior changes you may notice (details in the entries below):

- **Alembic upgrades are atomic by default (#503).** CUBRID DDL is transactional, so a failed multi-revision `alembic upgrade` now rolls back the whole run, including the `alembic_version` update. Set `transaction_per_migration=True` in `context.configure()` to keep per-revision commits (recommended for long or large-table migrations). Offline `--sql` scripts no longer contain `BEGIN;`; run them with `csql --no-auto-commit --no-single-line` so a failing statement stops the script.

- **Alembic registration (#504).** `CubridImpl` is registered when the dialect loads, so a default `env.py` works without importing `sqlalchemy_cubrid.alembic_impl`. The `[alembic]` and `[dev]` extras now require `alembic>=1.7.2`; `cubrid+aiopycubrid://` online migrations need Alembic's async template (`alembic init -t async`).

- **Reflection.** Unique constraints are no longer reported twice and reflect as unique indexes, as on MySQL (#529); non-DBA users get complete metadata from the public catalog views (#549); a missing table or view raises `NoSuchTableError` (#530); `has_table()` / `has_index()` match mixed-case names (#543); `get_foreign_keys()` is sorted by name (#531); `BIT(n)` / `BIT VARYING(n)` keep their length (#545); a failing catalog query raises instead of silently returning incomplete metadata (#533, #549). Autogenerate also detects `Text` ↔ `String(n)` changes (#544). Review the first Alembic autogenerate diff after upgrading.

- **DDL and types.** `UnicodeText` and `TEXT` compile to `STRING` (#534); `BINARY(n)` / `VARBINARY(n)` compile to `BIT(n*8)` / `BIT VARYING(n*8)` and `UUID` to `CHAR(32)` (#545); `Index.drop()` and `op.drop_index()` emit `DROP INDEX <name> ON <table>`, so `op.drop_index()` needs `table_name` (#533); `if_exists=True` on index drops and `if_not_exists=True` on index creates raise `CompileError` (#533, #540), as does an explicit `String(0)` (#440); Boolean `is_()` / `is_not()` against a value render with `<=>` (#465); JSON `as_numeric(p, s)` returns `Decimal` (#535).

- **Transactions.** `isolation_level="AUTOCOMMIT"` works on every driver, invalid levels raise `ArgumentError`, and `dialect.on_connect()` no longer applies `isolation_level` (a hand-built pool must apply it) (#501). Engine- and connection-level isolation levels survive `commit()` / `rollback()` on pycubrid (#505). On `cubrid://`, `executemany` runs each parameter set separately: `None` values and rowcounts are correct, large batches are slower (#502).

- **Async.** `driver_connection` on `cubrid+aiopycubrid://` is now the `pycubrid.aio` connection; use `dbapi_connection` for the SQLAlchemy adapter (#520). Async `LargeBinary` / `BLOB` binding works (#500).

- **Removed** the unreachable SQLAlchemy 1.x hooks `should_autocommit_text()`, `AUTOCOMMIT_REGEXP` and the `dbapi()` classmethods (#462).

- **pycubrid 1.8.0 is recommended.** It raises `IntegrityError` for NOT NULL and foreign-key violations, raises instead of silently returning a truncated result after `commit()` / `rollback()`, reports correct `null_ok` and collection type codes in `cursor.description`, and keeps the CAS session across commits and rollbacks except when the CAS itself is restarted (`docs/DRIVER_COMPAT.md` Known Issue 10); the pycubrid contract tests require it (#480, #481, #482). The declared range stays `pycubrid>=1.3.2,<2.0` (raising it is tracked in #559), so the dialect's isolation-level re-apply workaround is kept for older pycubrid and is a harmless no-op on 1.8.0.

### Added

- **Upstream canary failures are reported as an issue (#521)** — `.github/workflows/upstream-canary.yml` keeps its canary jobs non-blocking (`continue-on-error`, schedule and manual dispatch only), so a failing run against `pycubrid@main` used to pass silently. A new `report` job runs after both canary jobs on scheduled and dispatched runs of the default branch (dispatches from feature branches never touch the shared issue, and cancelled runs are not reported): on failure it opens an issue titled "Upstream canary failing against pycubrid@main" with the `ci` label, or comments on the open one instead of creating a duplicate, listing each job's outcome, the run URL, the pycubrid commit tested and the sqlalchemy-cubrid ref and commit; once both jobs pass again it closes that issue with a comment. Each canary job now resolves `pycubrid@main` with `git ls-remote`, installs that exact commit and exposes it and its own status as job outputs, because job-level `continue-on-error` hides failures from `needs.<job>.result`. The workflow defaults to `contents: read`; only the report job has `issues: write`, and it uses the `gh` CLI with `GITHUB_TOKEN` (no third-party action), runs one at a time (`concurrency`), and has no `continue-on-error`, so a failure to report turns the run red. `docs/DEVELOPMENT.md` (+ Korean) describes the reporting.

- **Blocking SQLAlchemy compliance lanes for released pycubrid (#463)** — the official SQLAlchemy compliance suite now gates merges for `cubrid+pycubrid://` as well as CUBRIDdb, as steps of the existing `integration-tests` cells (no new job or CUBRID service): lane `pycubrid@sa2.1` (pycubrid 1.7.1, SQLAlchemy 2.1.1) on Python 3.14 × CUBRID 11.4 and lane `pycubrid@sa2.0` (pycubrid 1.7.1, SQLAlchemy 2.0.53) on Python 3.10 × CUBRID 10.2, both pinned and both recording versions via `scripts/report_driver_versions.py`; the CUBRIDdb lane (`cubrid@sa2.0`, CUBRID 11.4) is unchanged. `test/known_failures.txt` is now keyed per lane: every entry names the `<driver>@sa<major.minor>` lanes (optionally `@cubrid<major.minor>` for a server-specific failure) it fails in and is strict-xfailed only there, so a failure baselined for one driver cannot hide a regression on the other. With `CUBRID_STRICT_KNOWN_FAILURES=1` a strict XPASS, a stale entry, a listed entry that is skipped instead of xfailed, a lane with no reviewed baseline, or a SQLAlchemy release other than the lane's pinned one fails the run; a malformed entry, a duplicated node id or a server-narrowed tag outside the (lane, server) pairs CI gates is a load error. The pycubrid compliance step runs even when the CUBRIDdb lane failed. A new offline `test/test_known_failures.py` validates the manifest format. `docs/DEVELOPMENT.md` and `docs/SUPPORT_MATRIX.md` (+ Korean) describe the lanes and the baseline update process.

- **Required driver-differential lane with an all-skipped guard and version record (#486)** — the regular and full integration jobs now run `test/test_driver_differential.py` with pycubrid and CUBRIDdb and `CUBRID_REQUIRE_DRIVER_DIFFERENTIAL=1`; with that variable set, `test/conftest.py` fails the session when no comparison ran and passed, so a lane where every case skipped or none was collected no longer reports success. Local runs without the variable still skip cleanly. `scripts/report_driver_versions.py` records the exact Python, SQLAlchemy, pycubrid, CUBRIDdb and CUBRID server versions in the job log and the GitHub step summary. New differential cases cover Core `executemany` with integer, UTF-8/CJK and NULL values, textual `executemany` with integer and UTF-8/CJK values (CUBRIDdb 11.3.0.51 reuses the previous row's value for a NULL parameter there), scalar binds, textual-SQL result column names, and commit/rollback visibility; contract areas blocked upstream are tracked in #480–#484 (#480 and #481 have since added differential cases). `docs/DEVELOPMENT.md` now states that a specific pycubrid release candidate must pass the downstream contract suite before the `pycubrid>=1.3.2,<2.0` bound is widened, while the weekly `pycubrid@main` canary stays non-blocking. Tests and CI only; no dialect behavior change.

- **Live BLOB/CLOB value-contract tests on released drivers (#485)** — `test_integration.py` (CUBRIDdb and `cubrid+pycubrid://` lanes) and `test_aio_integration.py` (`cubrid+aiopycubrid://`) now round-trip `LargeBinary`, `BLOB`, `CLOB` and `Text` through Core and ORM with small, Unicode/CJK, `NULL` and 256 KiB payloads (larger than pycubrid's ~80 KB `LOB_READ` chunk), and assert the returned value is `bytes`/`str`, never a driver LOB handle. Verified on CUBRID 10.2 and 11.4: writes store the full value and `NULL`/`Text` round-trip, but non-NULL `BLOB`/`CLOB` reads return a driver LOB locator (pycubrid `dict` handle, CUBRIDdb `'file:...'` string), and async `LargeBinary`/`BLOB` binding fails because the async DB-API adapter lacks `Binary`. Those cases are strict per-driver xfails; `docs/TYPES.md`, `docs/DRIVER_COMPAT.md` and `docs/SUPPORT_MATRIX.md` document the current behavior (reflection is unaffected), and the `CLOB` type row no longer lists `sqlalchemy.Text`, which compiles to `STRING`. No dialect behavior changes.

- **Live tests that results are never silently truncated across commit or rollback (#481)** — `test_integration.py` (CUBRIDdb and `cubrid+pycubrid://` lanes) and `test_aio_integration.py` read a 500-row, 1000-byte-per-row result (more than pycubrid's 100-row FETCH batch; the broker's first response holds ~16 rows) with `fetchone()`, `fetchmany()` and `fetchall()` after `commit()`, `rollback()` or no boundary, and require every row or a DB-API error, never a successful partial `Result`. The driver-differential suite adds the rollback case for both drivers. Verified on CUBRID 10.2 and 11.4: CUBRIDdb 11.3.0.51 returns all rows after commit and raises `InterfaceError` after rollback; pycubrid `main` raises `InterfaceError`; released pycubrid 1.7.1 silently returns only the buffered rows on a warm connection (cubrid-lab/pycubrid#395), so those sync cases are strict xfails for pycubrid only via `test/pycubrid_upstream.py` (no-op under `CUBRID_PYCUBRID_UPSTREAM=1`, set by the `pycubrid@main` integration canary; see `docs/DEVELOPMENT.md`). Async results pass on every driver because `AsyncConnection.execute()` buffers the whole result. `docs/DRIVER_COMPAT.md` documents the per-driver behavior. Tests, CI and docs only; no dialect behavior change.

- **Live `IntegrityError` contract tests for constraint violations (#480)** — `test_integration.py` (CUBRIDdb and `cubrid+pycubrid://` lanes), `test_aio_integration.py` (`cubrid+aiopycubrid://`) and the driver-differential suite now check through Core and ORM that NOT NULL, foreign-key and unique/primary-key (control) violations raise `sqlalchemy.exc.IntegrityError`, and that the same connection or `Session` runs new statements after `rollback()`. Verified on CUBRID 10.2 and 11.4: CUBRIDdb 11.3.0.51 and pycubrid `main` pass every case; released pycubrid 1.7.1 raises NOT NULL (-631) and foreign-key (-922) violations as `DatabaseError` (cubrid-lab/pycubrid#390), so those cases are strict xfails for the pycubrid drivers only. The new `test/pycubrid_upstream.py` helper applies such xfails unless `CUBRID_PYCUBRID_UPSTREAM=1`, which the weekly `pycubrid@main` integration canary sets; `docs/DEVELOPMENT.md` documents it and when to remove it. `docs/DRIVER_COMPAT.md` documents the per-driver exception classes. Tests, CI and docs only; no dialect behavior change.

- **Stronger `IntegrityError` contract tests (#480)** — the Core, ORM, async and driver-differential constraint-violation tests now prove same-connection reuse: the error does not invalidate the connection, and after `rollback()` the same `Connection` (and, for the ORM, a `Session` bound to it) keeps the same DBAPI connection. Before the pycubrid-only xfail is applied, they also assert the native server error code (-631 NOT NULL, -922 foreign key, -670 unique; pycubrid `Error.code`, CUBRIDdb `args[0]`), and the class assertion also checks that `exc.orig` is the driver's `IntegrityError`. A patched `is_disconnect()` that always returns `True` now fails these tests. The `is_disconnect()` docstring no longer claims CUBRIDdb lacks `OperationalError`. Tests and docs only; no behavior change.

- **Stronger result-completeness tests (#481)** — the sync test now asserts that CUBRIDdb raises `sqlalchemy.exc.InterfaceError` after rollback (and no error otherwise). It reads the FETCH batch size from pycubrid's `Connection` signature instead of hardcoding 100. Every fetched prefix must be in order with intact payloads before the pycubrid#395 xfail applies, and the marker now covers only the completeness assertion; an explicit error still turns into a strict XPASS on a fixed build. The driver-differential case also checks that pycubrid's first response does not hold the whole result. A new async case drives the lazily fetching `pycubrid.aio` cursor directly (execute, fetch one, commit or rollback, fetch the rest); released pycubrid 1.7.1 silently returns 16 of 500 rows there, so it is a strict xfail for pycubrid#395. `docs/DRIVER_COMPAT.md` Known Issue 8 (en/ko) records the raw async cursor behavior. Tests and docs only; no behavior change.

- **Live `cursor.description` contract tests (#482)** — `test_integration.py` (CUBRIDdb and `cubrid+pycubrid://` lanes) and `test_aio_integration.py` (`cubrid+aiopycubrid://`) check the subset SQLAlchemy exposes: `Result.keys()` versus description names for `text()` aliases/expressions and Core `select()`, representative scalar type codes, `null_ok` for nullable and NOT NULL columns, `SET`/`MULTISET`/`SEQUENCE` type codes, reflected nullability, and sync/async pycubrid agreement; the driver-differential suite adds a scalar-description comparison. Verified on CUBRID 10.2 and 11.4: CUBRIDdb 11.3.0.51 and pycubrid `main` pass (CUBRIDdb reports collection columns with CCI composite codes such as 40 for `SET(INTEGER)`, recorded per driver); released pycubrid 1.7.1 reports `null_ok` inverted (cubrid-lab/pycubrid#431) and collection columns as their element type (cubrid-lab/pycubrid#430), so those cases are strict xfails for pycubrid only via `test/pycubrid_upstream.py` (no-op under `CUBRID_PYCUBRID_UPSTREAM=1`, set by the `pycubrid@main` integration canary; see `docs/DEVELOPMENT.md`). `docs/FEATURE_SUPPORT.md` documents that the dialect passes `cursor.description` through without normalization. Tests, CI and docs only; no dialect behavior change.

- **Review follow-ups for the #480/#481 contract tests** — the result-completeness checks (sync, raw async cursor and driver-differential) now validate the order and payload of every returned row, including the one consumed by `fetchone()`, before the pycubrid#395 xfail applies. The driver-differential constraint-violation case now also asserts that `exc.orig` is the driver's own `IntegrityError` for CUBRIDdb and, behind the existing pycubrid#390 marker, for pycubrid. Tests only; no behavior change.

### Changed

- **Contract tests now require the pycubrid 1.8.0 fixes (#480, #481, #482)** — the strict `xfail_unreleased_pycubrid_fix` markers for cubrid-lab/pycubrid#390 (NOT NULL / foreign-key violations raise `IntegrityError`), #395 (no silently truncated result after commit/rollback), #430 (collection `cursor.description` type codes) and #431 (`null_ok` not inverted) are removed from `test_integration.py`, `test_aio_integration.py` and `test_driver_differential.py`, so those assertions run unconditionally on the pycubrid lanes and require pycubrid 1.8.0 or later. `test/pycubrid_upstream.py` and the `CUBRID_PYCUBRID_UPSTREAM` switch in `upstream-canary.yml` are removed; `DRIVER_COMPAT.md` Known Issues 8 and 9 and `FEATURE_SUPPORT.md` now mark these pycubrid bugs as fixed in 1.8.0. The `pycubrid>=1.3.2,<2.0` dependency bound is unchanged.

- **Alembic: CUBRID DDL is transactional, so the whole upgrade is now atomic by default (#503)** — `CubridImpl.transactional_ddl` is now `True` (was `False`). The docs and docstrings claimed CUBRID implicitly commits DDL; it does not. With client autocommit off, which the dialect always sets, `ROLLBACK` undoes `CREATE TABLE`, `ALTER TABLE`, `DROP TABLE`, `TRUNCATE`, `CREATE INDEX` (including `WITH ONLINE [PARALLEL n]`), `CREATE VIEW`, `CREATE SERIAL` and `RENAME TABLE`, and DDL never commits pending DML; client autocommit is the only auto-commit behavior. **Behavior change:** a failed `alembic upgrade` now rolls back every revision of that run, including the `alembic_version` update, instead of keeping the revisions that finished before the failure (each revision was already atomic on its own, because Alembic's online mode wraps it in `connection.begin()`), and `context.is_transactional_ddl()` returns `True`. Set `transaction_per_migration=True` in `context.configure()` to keep per-revision commits; it is recommended for long or large-table migrations, because uncommitted DDL holds schema locks (other sessions wait on `SCH_S_LOCK`). `CubridImpl.emit_begin()` now emits nothing, because CUBRID has no `BEGIN` statement (csql rejects it), so offline `--sql` scripts contain no `BEGIN;` and end each transaction with `COMMIT;`; run them with `csql --no-auto-commit --no-single-line` (csql's default single-line mode continues past a failing statement, still runs the trailing `COMMIT;` and exits 0). New live tests in `test/test_transactional_ddl.py` (run in the PR and full integration matrices with `CUBRID_REQUIRE_TRANSACTIONAL_DDL=1`, which turns an unavailable driver, server or csql into a failure instead of a skip) prove, on CUBRID 10.2 and 11.4 with pycubrid and CUBRIDdb, that each of those statements rolls back, that DDL does not commit earlier DML and that `metadata.create_all()` rolls back; that a failing multi-revision Alembic upgrade leaves no partial schema and no version row, while `transaction_per_migration=True` keeps the completed revision; and that offline `--sql` output runs in csql. README (and translations), `docs/ALEMBIC.md`, `docs/TROUBLESHOOTING.md`, `docs/ISOLATION_LEVELS.md`, `docs/SUPPORT_MATRIX.md`, `docs/ARCHITECTURE.md`, `docs/ORM_COOKBOOK.md` (+ Korean), `docs/PRD.md`, AGENTS.md, `llms.txt` and `scripts/alembic_safety_check.py` no longer describe DDL as auto-committed or recommend one DDL operation per revision.

### Removed

- **Removed the dead SQLAlchemy 1.x `should_autocommit_text()` hook, its `AUTOCOMMIT_REGEXP`, and the legacy `dbapi()` classmethods (#462)** — SQLAlchemy 2.0 and 2.1 `DefaultExecutionContext` no longer define or call `should_autocommit_text()`, so the regex it consulted never affected a supported runtime (this also retires #439's request to add `REPLACE` to it, surfaced by @biggdawg320 in #468: there is no longer a regex to be inconsistent with the dialect's `REPLACE INTO` construct). `create_engine()` only falls back to a `dbapi()` classmethod when the dialect class does not define `import_dbapi()` itself, and `CubridDialect`, `PyCubridDialect` and `PyCubridAsyncDialect` all do, so the `dbapi()` wrappers were unreachable. Transactions are unchanged: DML and DDL text commits only via `conn.commit()`, `engine.begin()` or a `Session`. Added offline regression tests asserting the hooks stay gone, that engine creation resolves the DBAPI via `import_dbapi()` without a deprecation warning, and that `DELETE`/`REPLACE`/`CREATE` text is rolled back unless explicitly committed; `docs/CONNECTION.md`, `docs/FEATURE_SUPPORT.md`, `docs/DML_EXTENSIONS.md`, `docs/SUPPORT_MATRIX.md` (+ Korean) and `docs/PRD.md` no longer describe the non-existent statement-text autocommit detection.

### Fixed

- **Alembic autogenerate detects `Text` ↔ `String(n)` changes (#544)** — `CubridImpl` matched the reflected `VARCHAR(1073741823)` of a `STRING` column by upper-cased class name, and the dialect's `STRING` type shares that name with the generic `sa.String`, so a model column changed from `Text` to `String(10)` produced no diff and the migration that shrinks the column was never generated. The dialect's `STRING` is now matched by class; `Text`, `UnicodeText`, `CLOB` and a `String()` without a length still match a reflected `STRING` column, while `String(n)` goes through Alembic's normal length comparison. Live autogenerate tests on both drivers cover both directions (`Text` → `String(10)` and `String(10)` → `Text` are detected, applied, and compare clean afterwards) and the unbounded types that must not report a diff.

- **`BINARY`, `VARBINARY` and `UUID` create columns CUBRID accepts (#545)** — `sqlalchemy.BINARY`, `VARBINARY` and `UUID` fell through to SQLAlchemy's generic `BINARY` / `VARBINARY` / `UUID` DDL, which CUBRID 10.2 and 11.4 reject, so a model using them could not be created. `BINARY(n)` now compiles to `BIT(n*8)` (`BINARY()` to `BIT(8)`) and `VARBINARY(n)` to `BIT VARYING(n*8)` (`VARBINARY()` to `BIT VARYING`); both drivers bind and return the values as `bytes`, and a zero length raises `CompileError`. `UUID` compiles to `CHAR(32)` like `Uuid`, with SQLAlchemy's non-native UUID handling for `as_uuid=True` and `False`. Reflection now keeps the length and `VARYING` of `BIT(n)` / `BIT VARYING(n)` columns (they reflected as `BIT(1)`), so these columns compile back to the same DDL and Alembic autogenerate reports no false type change. A new compiler test sweeps every generic SQLAlchemy type and fails if one compiles to a type name that CUBRID rejects in `CREATE TABLE` (list taken from live runs on 10.2 and 11.4) or to one not yet checked live. `docs/TYPES.md` (+ Korean) documents the mappings and fixes the `CHAR VARYING` reflection rows, which said `NVARCHAR` although it reflects as `VARCHAR`.

- **Boolean `IS` / `IS NOT` predicates compile to SQL CUBRID accepts (#465)** — without a native BOOLEAN, SQLAlchemy renders `col.is_(True)`, `is_(False)`, `is_not(True)` and `is_not(False)` (also with `true()`/`false()`, a bound parameter, or any expression such as `(col == 5).is_(True)`) as `IS 1` / `IS 0` / `IS NOT 1` / `IS NOT 0`, which CUBRID rejects with a syntax error on 10.2 and 11.4: its `IS` accepts only `[NOT] NULL` and `[NOT] TRUE/FALSE`, and since 11.2 `IS TRUE` also needs a logical operand (`b IS TRUE` fails for a `SMALLINT` column), while `(x = 1) IS NOT TRUE` is rejected in a SELECT list. `CubridCompiler` now renders `IS` against a value with the null-safe equal operator, like `IS [NOT] DISTINCT FROM`: `a IS b` as `a <=> b` and `a IS NOT b` as `(a <=> b) = 0`, which keeps the SQL semantics exactly (`IS TRUE` is never `NULL`; `IS NOT TRUE` is its complement) in `WHERE` clauses and SELECT lists; `IS [NOT] NULL` is unchanged. `col == True`, `not_(col)`, `true()`/`false()` and `and_()`/`or_()` already compiled to valid SQL (`col = 1`, `col = 0`, `1 = 1`) and are unchanged; CUBRID itself rejects logical operators (`AND`, `OR`, `NOT`) in a SELECT list, which is documented. New compiler tests and a live truth-table test (stored 1, 0 and NULL; `WHERE` and projection) on CUBRID 10.2 and 11.4 with CUBRIDdb and pycubrid cover it; `docs/TYPES.md` and `docs/FEATURE_SUPPORT.md` (+ Korean) document the rendering and its semantics.

- **Reflection works for non-DBA users: read the public catalog views instead of the DBA-only `_db_*` tables (#549)** — `_db_index`, `_db_index_key` and `_db_attribute` (and `_db_class`) are readable only by DBA on CUBRID 10.2, 11.0, 11.2 and 11.4; for any other user a query fails with `SELECT is not authorized on _db_index` (-494). The dialect swallowed that error, so reflection silently degraded: `get_indexes()` reported the primary-key index and the foreign-key auto-indexes as ordinary indexes (spurious Alembic autogenerate `drop_index`/`create_index` diffs, the #120 problem), `get_pk_constraint()` fell back to `SHOW COLUMNS` and lost the PK name and every column of a composite key after the first (#426), `get_unique_constraints()` fell back to `SHOW CREATE TABLE` parsing, `get_columns()` returned no column comments, and `has_index()` raised. `has_index()` keeps the name matching and owner preference from #543 on the public view. These methods now read the public `db_index`, `db_index_key` and `db_attribute` views, which every user can read (flags are `'YES'`/`'NO'` there). Since CUBRID 11.2 those views also list same-named classes of other owners that the user may read, so the rows are limited to the owner the cached `db_class` lookup from #529 prefers (the current user's class first); before 11.2 class names are global and the views have no `owner_name` column. This also stops a same-named class of another owner from adding its indexes or comments on 11.2+. The catalog lookups also match the table name as given or folded to lower case, like the `db_class` lookup and `SHOW ... IN <name>`: `get_indexes("Users")` used to report the PK and FK auto-indexes (and `get_pk_constraint()` lost composite columns, `get_columns()` the comments) even for DBA. A failing catalog query now raises instead of silently falling back to incomplete metadata; `get_pk_constraint()` still uses `SHOW COLUMNS` and `get_unique_constraints()` still parses `SHOW CREATE TABLE` when the catalog has no matching row, and `get_unique_constraints()` maps an `Unknown class` error from its `SHOW INDEXES` step to `NoSuchTableError`. A new live test reflects a table with a named composite PK, a foreign key, a unique constraint, an index and a column comment as DBA and as a newly created user, by its name and in upper case, on CUBRID 10.2 and 11.4 with both drivers (on 11.2+ with a same-named decoy table of the other user). `docs/FEATURE_SUPPORT.md`, `docs/ARCHITECTURE.md` (+ Korean) and `docs/PRD.md` describe the catalog sources.

- **`has_table()` and `has_index()` find mixed-case names, so `checkfirst=True` no longer silently skips (#543)** — CUBRID stores identifiers in lower case, even quoted ones, but both methods compared the names exactly as passed in. For `Index("IX_Mixed543", Table("Users543", ...))`, `has_index()` returned `False`, so `Index.drop(checkfirst=True)` did nothing and the index stayed; `has_table()` had the same gap. Both now also match the lower-case form (`IN (:name, LOWER(:name))`), like `_get_class_type()` and the other reflection methods, and `has_index()` resolves the table with the same owner preference (the current user's own class first, which matters on CUBRID 11.2+ where owners can share a class name). `@reflection.cache` and error propagation (#444, #538) are unchanged. Live tests cover mixed-case `checkfirst` create and drop on CUBRID 10.2 and 11.4 with both drivers.

- **`CreateIndex(..., if_not_exists=True)` raises `CompileError` instead of emitting `CREATE INDEX IF NOT EXISTS` (#540)** — CUBRID 10.2, 11.0, 11.2 and 11.4 reject `CREATE INDEX IF NOT EXISTS` (and `CREATE UNIQUE INDEX IF NOT EXISTS`) with a syntax error, but the DDL compiler emitted it for `Index(...)` / `CreateIndex(..., if_not_exists=True)` and Alembic `op.create_index(..., if_not_exists=True)`. `CubridDDLCompiler.visit_create_index` now refuses it with a `CompileError` that points to `inspect(conn).has_index()` and `Index.create(checkfirst=True)`, mirroring `DROP INDEX IF EXISTS` (#533). A plain `CREATE INDEX` is unchanged. `docs/ALEMBIC.md` and `docs/FEATURE_SUPPORT.md` (+ Korean) document the limitation.

- **Reflecting a missing table or view raises `NoSuchTableError` (#530)** — `get_foreign_keys()` and `get_unique_constraints()` returned `[]` for an object that does not exist (the `SHOW CREATE TABLE` fallbacks swallowed the server's `Unknown class` error with a WARNING traceback), `get_table_comment()` returned `{"text": None}`, and `get_pk_constraint()` and `get_view_definition()` let the raw -493 `ProgrammingError` escape. Because SQLAlchemy's default `get_multi_*()` implementations leave out only the names whose single-object method raises `NoSuchTableError`, the multi variants also reported the missing object. `get_foreign_keys()` and `get_unique_constraints()` now look up the class type first (the cached, owner-aware `db_class` lookup from #529): no row raises `NoSuchTableError`, and a view (`VCLASS`) returns `[]` without running the table-only `SHOW CREATE TABLE`, which removes the WARNING traceback logged for every reflected view. `get_table_comment()` raises when `db_class` has no row, and matches the name like the class-type lookup (as given or lower-cased, the current user's class first). `get_pk_constraint()` (`SHOW COLUMNS` fallback), `get_view_definition()` (`SHOW CREATE VIEW`) and the `SHOW CREATE TABLE` fallbacks of `get_foreign_keys()` / `get_unique_constraints()` map an error to `NoSuchTableError` only when its message is CUBRID's `Unknown class`: pycubrid reports syntax errors, `<name> is not a class` and some permission errors with the same -493 / SQLSTATE 42S02 (#454), so a generic -493 still propagates (or, in the DDL fallbacks, keeps the logged empty result). `get_view_definition()` on a table (for which `SHOW CREATE VIEW` returns no row) now raises `NoSuchTableError` instead of returning `""`, as SQLAlchemy's suite expects. The 9 entries of the #530 group, including `test_get_multi_unique_constraints[True-ObjectKind.ANY-ObjectScope.ANY…]` that also needed #529, are removed from `test/known_failures.txt` for all three lanes; `docs/FEATURE_SUPPORT.md` (+ Korean) documents the behavior, and the per-lane counts in the `test/known_failures.txt` header and `docs/SUPPORT_MATRIX.md` (+ Korean) are updated (cubrid@sa2.0 68 / 61, pycubrid@sa2.0 54, pycubrid@sa2.1 58 / 51).

- **`UnicodeText` creates a CUBRID `STRING` column instead of the non-existent `TEXT` (#534)** — `CubridTypeCompiler` overrode `visit_text` (`Text` → `STRING`) but not `visit_unicode_text` or `visit_TEXT`, so `UnicodeText` and `sqlalchemy.TEXT` fell through to SQLAlchemy's generic `TEXT`, and `CREATE TABLE` failed with "dba.TEXT is not defined" (-494) on every CUBRID version. Both now compile to `STRING`, like `Text`; CUBRID strings use the database charset, so there is no separate national text type. Alembic's `compare_type` now also treats `UnicodeText` like `Text` against a reflected `VARCHAR(1073741823)`, so autogenerate does not report a spurious type change for it. New compiler tests and a live `CREATE TABLE` + Korean/Japanese/Chinese/emoji round trip on CUBRIDdb and pycubrid cover it, and the six `UnicodeTextTest` compliance entries are removed from `test/known_failures.txt` for every lane. `docs/TYPES.md` (+ Korean) and `docs/PRD.md` now list `UnicodeText` as `STRING`, and `Unicode(n)` as the `VARCHAR(n)` it actually compiles to; `docs/TYPES.md` (+ Korean) also notes that no column-level `CHARSET`/`COLLATE` is rendered for string and text types (`collation=` is dropped) and that non-ASCII text needs a UTF-8 database. The per-lane known-failure counts in the `test/known_failures.txt` header and `docs/SUPPORT_MATRIX.md` (+ Korean) are updated (cubrid@sa2.0 77 / 70, pycubrid@sa2.0 63, pycubrid@sa2.1 67 / 60).

- **Reflection no longer duplicates unique constraints or returns table indexes for views (#529)** — CUBRID represents both unique constraints and unique indexes as the same unique-index metadata. `get_unique_constraints()` now marks each one as `duplicates_index`, so SQLAlchemy reflection and Alembic autogenerate retain the unique index rather than creating a second `UniqueConstraint` (the corresponding SQLAlchemy test requirements are enabled). `get_indexes()` returns `[]` for views instead of copying the base table's indexes. Class-type lookup handles case folding, caches by Inspector and prefers the current user's object over a same-named DBA view on CUBRID 11.2+. **Resource safety (#548):** single-row catalog and `SHOW CREATE` reads now use closing `Result.first()` instead of leaving query entries open with `fetchone()`; previously reflecting ~50–60 tables on pycubrid could hit the server's 100-entry limit (-830). Live tests reflect 150 tables on CUBRID 10.2/11.4 via pycubrid and CUBRIDdb, plus the same-name owner case on 11.2+. The 36 resolved `ComponentReflectionTest` failures were removed from the baseline, with per-lane counts updated in `test/known_failures.txt` and `docs/SUPPORT_MATRIX.md`.

- **`get_foreign_keys()` returns foreign keys sorted by name (#531)** — the constraints were returned in the order `SHOW CREATE TABLE` lists them, which is not name order, so the SQLAlchemy compliance suite's `ComponentReflectionTest::test_get_multi_foreign_keys` (which expects `fk_dingalings_id_user` before `zz_email_add_id_fg`) compared the wrong foreign keys even though each reflected constraint was correct. `get_foreign_keys()` (and therefore `get_multi_foreign_keys()`) now sorts by constraint name, like SQLAlchemy's built-in dialects. The 8 `test_get_multi_foreign_keys[False-…]` entries are removed from `test/known_failures.txt` for all three lanes; the per-lane counts in its header and in `docs/SUPPORT_MATRIX.md` (+ Korean) are updated (cubrid@sa2.0 119 / 112, pycubrid@sa2.0 105, pycubrid@sa2.1 109 / 102).

- **Foreign keys and unique constraints on column names containing parentheses are reflected (#532)** — the `SHOW CREATE TABLE` parser matched a constraint's column list up to the first `)`, so a bracketed name such as `[(3)]` cut the list short: `REFERENCES [dba.p] ([(3)])` reflected `referred_columns: []`, and autoloading the child table raised `ArgumentError`. `_RE_FOREIGN_KEY` and `_RE_UNIQUE_KEY` now match the column list as a sequence of bracketed names (each optionally followed by `ASC`/`DESC`, with optional whitespace inside the parentheses), so names containing `(`, `)`, `,` or spaces parse correctly. New offline regex tests use DDL captured from CUBRID 11.4 for such names. The 6 `BizarroCharacterTest::test_fk_ref[…-(3)-…]` entries are removed from `test/known_failures.txt` for all three lanes; the per-lane counts in its header and in `docs/SUPPORT_MATRIX.md` (+ Korean) are updated (cubrid@sa2.0 127 / 120, pycubrid@sa2.0 113, pycubrid@sa2.1 117 / 110).

- **`Index.drop()` and Alembic `op.drop_index()` emit `DROP INDEX <name> ON <table>` (#533)** — `CubridDDLCompiler` had no `visit_drop_index`, so SQLAlchemy's generic `DROP INDEX <name>` was emitted and CUBRID rejected it with a -493 syntax error (CUBRID scopes an index to its table). The compiler now emits `DROP INDEX <quoted name> ON <quoted table>`, including the table's schema when one is set. CUBRID 10.2, 11.0, 11.2 and 11.4 have no `DROP INDEX IF EXISTS` (all four answer a syntax error), so `DropIndex(..., if_exists=True)` and `op.drop_index(..., if_exists=True)` now raise `CompileError` instead of emitting SQL the server rejects; check `inspect(conn).has_index()` first, as `Index.drop(checkfirst=True)` does. An index not bound to a table also raises `CompileError`, and `op.drop_index()` without `table_name` (which Alembic binds to a placeholder table named `no_table`) raises `CompileError` asking for `table_name` instead of emitting `DROP INDEX <name> ON no_table`. `CubridDialect.has_index()` is now `@reflection.cache`d like `has_table()` and the `get_*` methods, so an `Inspector` answers `has_index()` from its cache until `clear_cache()` (calls without an `info_cache`, such as `Index.drop(checkfirst=True)`, still query the catalog each time); with the drop fixed this was the remaining `HasIndexTest::test_has_index[inspector]` failure. Because a cached answer lives as long as the `Inspector`, a failing catalog query in `has_index()` now raises instead of being swallowed as `False`; a missing table or index still returns `False`. The per-lane known-failure counts in the `test/known_failures.txt` header and `docs/SUPPORT_MATRIX.md` (+ Korean) are updated (cubrid@sa2.0 133 / 126, pycubrid@sa2.0 119, pycubrid@sa2.1 123 / 116). New compiler tests, an offline cache test, offline Alembic `--sql` tests and live `Index.drop()` / `op.drop_index()` tests cover it, and the `HasIndexTest::test_has_index[dialect|inspector]` compliance entries are removed from `test/known_failures.txt` for every lane. `docs/ALEMBIC.md` (+ Korean) documents the `ON <table>` form and the `if_exists` limitation.

- **JSON `.as_numeric(p, s)` returns `Decimal` instead of `float` (#535)** — a JSON element cast with `as_numeric()` was rendered `CAST(JSON_EXTRACT(...) AS DOUBLE)`, so the driver returned a `float`, and because the dialect declares native decimal support no result processor converted it: `select(t.c.data["a"].as_numeric(10, 2))` returned `15.0` instead of `Decimal('15.00')` and lost precision, on SQLAlchemy 2.0 and 2.1 alike. A `Numeric` target with both precision and scale now renders `CAST(JSON_EXTRACT(...) AS NUMERIC(p,s))`, as SQLAlchemy's MySQL dialect renders `DECIMAL(p, s)`, and both drivers return a `Decimal` at scale `s` (JSON numbers, including exponent notation such as `1e3`, plain-decimal numeric strings such as `"15.5"`, and `true`/`false` cast; JSON `null` is still SQL `NULL`). CUBRID raises -181 ("Cannot coerce value of domain json to domain numeric") for a string in exponent notation (`"1e3"`) and for a non-numeric string such as `"abc"` or `""`, and -427 (data overflow) for a value that does not fit `NUMERIC(p,s)`. For exponent-notation strings and values outside `NUMERIC(p,s)`, use `as_float()`, which casts to `DOUBLE`. `as_float()` also raises -181 for a non-numeric string, so validate or filter such values before casting; with `asdecimal=False` the result is still converted to `float`. `as_float()` and any `Float` stay `DOUBLE`, and a `Numeric` without both precision and scale also stays `DOUBLE`, because a bare CUBRID `NUMERIC` means `NUMERIC(15,0)` and would truncate. Verified on CUBRID 10.2 and 11.4. New offline compiler tests and a live round trip in `test_integration.py` (CUBRIDdb and pycubrid, SQLAlchemy 2.0.53 and 2.1.1) cover it; the 18 `JSONTest::test_index_cross_casts[...-numeric]` entries are removed from `test/known_failures.txt` (lane `pycubrid@sa2.1`: 143 / 136 → 125 / 118), and `docs/FEATURE_SUPPORT.md` (+ Korean) lists `as_numeric()`.

- **AUTOCOMMIT now works across CUBRIDdb and sync/async pycubrid, and pooled isolation is restored (#501)** — Previously, `execution_options(isolation_level="AUTOCOMMIT")` failed with `ArgumentError` and engine-level AUTOCOMMIT could raise `ValueError`. The dialect now registers AUTOCOMMIT, sets the driver's `autocommit` flag and uses SQLAlchemy's built-in engine/connection isolation handling rather than applying levels in its own `on_connect()` hook. This also restores an engine-level level (including an alias such as `CURSOR STABILITY` → `READ COMMITTED`) when a connection with a temporary override returns to the pool. Other isolation levels disable autocommit before issuing `SET TRANSACTION ISOLATION LEVEL`; the flag is changed only when needed because pycubrid toggles end transactions and reconnect the broker session. Invalid levels now raise SQLAlchemy `ArgumentError` through `create_engine()` / engine and connection options, while direct `dialect.set_isolation_level()` still raises `ValueError`; a DB-API connection lacking an `autocommit` property raises `AttributeError`. **Custom pools:** a caller manually invoking `dialect.on_connect()` must now apply its own isolation setting (or use `dialect._builtin_onconnect()`), and `dialect.isolation_level` reports the canonical name. For pycubrid with engine-level AUTOCOMMIT, each statement reconnects at the server-default isolation level (cubrid-lab/pycubrid#468); `skip_autocommit_rollback=True` is recommended and now works with driver flag detection. Live tests on all three drivers verified commit visibility, rollback behavior, check-in restores, aliases and invalid levels. See `docs/ISOLATION_LEVELS.md` and `docs/TROUBLESHOOTING.md`.

- **Engine- and connection-level `isolation_level` no longer falls back to READ COMMITTED on pycubrid after `commit()` / `rollback()` (#505)** — after the driver's `commit()` or `rollback()` the broker returns the CAS status byte as inactive (out of transaction), and pycubrid 1.7.1 (and `main`) then opens a new broker connection before the next request. The new session starts at the server default level, and pycubrid restores only `autocommit`, so `create_engine("cubrid+pycubrid://…", isolation_level="SERIALIZABLE")` already reported READ COMMITTED on the first checkout (SQLAlchemy rolls back after its first-connect checks), and a per-connection level was lost at the next commit. `CUBRIDdb` keeps the same session and was not affected; the driver bug is cubrid-lab/pycubrid#468. `PyCubridDialect` (and the async dialect) now remember the level they set on each DBAPI connection and re-apply it in `do_commit()` / `do_rollback()`. This costs one `SET TRANSACTION ISOLATION LEVEL` + `COMMIT` per commit/rollback, only on connections with a configured level; nothing runs per statement, and such a pooled connection holds a broker CAS while idle. A failed re-apply never turns a successful commit into an error or masks the exception that caused a rollback: it is logged and retried in `do_begin()` before the next transaction's first statement. On an engine without a configured level, checkin after a per-connection override stops the re-apply for that connection. Remove the workaround once a pycubrid release fixing pycubrid#468 is the minimum. New live tests on all three drivers check `get_isolation_level()` after commit, rollback, pool checkin (including the pool's reset-on-return rollback alone), `engine.begin()` and a `Session`, and fail without the fix on pycubrid; pycubrid-only live tests simulate a failed re-apply and check that the commit stands, the rollback's `IntegrityError` propagates and the next transaction runs at the configured level. `docs/DRIVER_COMPAT.md` Known Issue 10 and `docs/ISOLATION_LEVELS.md` (+ Korean) document the driver behavior and the re-apply. Resetting to the engine level after a per-connection override is tracked in #501.

- **`driver_connection` on `cubrid+aiopycubrid://` is now the `pycubrid.aio` connection (#520)** — `PyCubridAsyncDialect` did not override `get_driver_connection()`, so `(await conn.get_raw_connection()).driver_connection` returned SQLAlchemy's `AsyncAdapt_pycubrid_connection` adapter instead of the driver's own connection. The dialect now returns the wrapped `pycubrid.aio.AsyncConnection`, as SQLAlchemy's asyncpg and aiomysql dialects do, so driver-specific async APIs (`ping()`, `cursor()`, ...) are reachable through the documented accessor. A unit test and a live async test cover it, and the async integration tests no longer reach the driver connection through `.dbapi_connection.driver_connection` or the adapter's `_connection`. Code that relied on `driver_connection` being the adapter should use `dbapi_connection` instead.

- **SQLAlchemy compliance tests no longer silently skip hundreds of valid cases (#463)** — Requirement properties now return independent `exclusions.open()` and `exclusions.closed()` objects instead of sharing mutable exclusions that caused stacked `@testing.requires` decorators to skip valid tests. With pycubrid, SQLAlchemy 2.0.53 and CUBRID 11.4, the suite increased from 334 to 631 passing tests; all three lanes were re-baselined on fresh CUBRID 10.2 and 11.4 databases. The recapture also enabled `reflects_pk_names` and `implicitly_named_constraints`, requires a UTF-8 database for `unicode_ddl` (the official Docker image creates ISO-8859-1 databases), and marks `precision_generic_float_type` unsupported because CUBRID `FLOAT` is single precision. Strict follow-up issues record the newly exposed bugs: duplicated unique constraints and view indexes (#529), missing-object reflection (#530), foreign-key order (#531), names containing parentheses (#532), `DROP INDEX` syntax (#533), `UnicodeText` DDL (#534) and JSON decimal precision (#535).
- **`Inspector.has_table()` honors the inspector cache (#463)** — `CubridDialect.has_table()` was not decorated with `@reflection.cache`, so `inspect(engine).has_table()` queried the catalog on every call and reported a table created after the first call before `clear_cache()`, unlike SQLAlchemy's built-in dialects. Found by the SQLAlchemy 2.1 `HasTableTest::test_has_table_cache` in the new pycubrid compliance lane (SQLAlchemy 2.0's harness never reached it). Direct `dialect.has_table()` calls without an `info_cache` and `create_all(checkfirst=True)` are unaffected.

- **`cubrid://` executemany no longer stores the previous row's value for `None` or reports a last-row rowcount (#502)** — CUBRIDdb 11.3.0.51 skips binding `None` and prepares `executemany` once, so a `None` parameter kept the previous row's value, and its `rowcount` counted only the last row. Through SQLAlchemy this silently corrupted `text()` and Core `UPDATE`/`DELETE` executemany and made batched ORM UPDATEs raise `StaleDataError`. `CubridDialect.do_executemany` now executes each parameter set and reports the summed rowcount, so `supports_sane_multi_rowcount` is accurate on both drivers. `cubrid+pycubrid://` and `cubrid+aiopycubrid://` keep the driver's prepare-once `executemany`, and a multi-row Core `insert()` that uses insertmanyvalues is unaffected. An INSERT into a table with a column whose type defines `bind_expression()` falls back to executemany (#421), so on `cubrid://` it uses the per-row guard. The textual executemany differential case now includes NULL, the CUBRIDdb `RowCountTest` multi-row entries are removed from `test/known_failures.txt`, `docs/DRIVER_COMPAT.md` (+ Korean) records the driver bug and when the guard will be removed, and `docs/SUPPORT_MATRIX.md` (+ Korean) documents executemany rowcount behavior and the guard's per-row cost.

- **Alembic finds `CubridImpl` with a default `env.py` (#504)** — `alembic upgrade` against a `cubrid://`, `cubrid+pycubrid://` or `cubrid+aiopycubrid://` URL failed with `KeyError: 'cubrid'` unless `env.py` imported `sqlalchemy_cubrid.alembic_impl` by hand. The package declared an `alembic.ddl` entry point, but no Alembic release reads that group: Alembic looks the impl up in a registry keyed by `dialect.name` that `DefaultImpl` subclasses fill on import, and the `alembic.plugins` entry points it does read exist only from 1.18 onward. `sqlalchemy_cubrid/dialect.py` now imports `alembic_impl` when Alembic is installed and skips it when it is not, which is how other third-party dialects register their impl and works on every supported Alembic release; all dialect variants share `name = "cubrid"`. The dead `alembic.ddl` entry point is removed. The standard `alembic init` template works unchanged for the synchronous URLs; for `cubrid+aiopycubrid://` online migrations, `docs/ALEMBIC.md` now points to Alembic's async template (`alembic init -t async`), whose unmodified `env.py` was verified live on CUBRID 11.4 (the standard template's synchronous engine fails there with `MissingGreenlet`). The import never stops the dialect from loading: a missing Alembic is skipped silently, and an installed Alembic that fails to import (1.7.0/1.7.1 raise `NameError` on SQLAlchemy 2.x) only disables the integration with one `RuntimeWarning` naming the exception (logged via the `sqlalchemy_cubrid.dialect` logger instead if a warning filter turns it into an error). The `[alembic]`/`[dev]` extras, the pre-commit mypy hook and the docs now require `alembic>=1.7.2,<2.0`, the oldest release that imports on SQLAlchemy 2.x. A new `test/test_alembic_registration.py` runs the `alembic` CLI in a fresh interpreter on an unmodified `alembic init` project, offline (`--sql`) for all four URL forms and online against a live CUBRID; it fails on the previous code with the reported `KeyError`. The roundtrip tests no longer import `alembic_impl` themselves. README (and translations), `docs/ALEMBIC.md`, `docs/TROUBLESHOOTING.md`, `docs/SUPPORT_MATRIX.md`, `docs/ARCHITECTURE.md` (+ Korean), `docs/PRD.md`, `docs/FEATURE_SUPPORT.md`, AGENTS.md and the wheel smoke checks now describe and verify registration on dialect import.

- **Async `LargeBinary` / `BLOB` binding no longer raises `AttributeError` (#500)** — `AsyncAdapt_pycubrid_dbapi` copied only `paramstyle`, the exception classes and the type objects from `pycubrid`, but SQLAlchemy's `LargeBinary` bind processor reads `dialect.dbapi.Binary` whenever the statement compiles, so every `cubrid+aiopycubrid://` INSERT/UPDATE touching a binary column failed, even with `None` or an unset ORM attribute. The adapter now copies the full PEP 249 module surface (`apilevel`, `threadsafety`, `paramstyle`, all exception classes, `Date`/`Time`/`Timestamp`, the `*FromTicks` constructors, `Binary` and the `STRING`/`BINARY`/`NUMBER`/`DATETIME`/`ROWID` type objects) from the sync module via one declared tuple. A unit test asserts every PEP 249 name on `pycubrid` is on the adapter; live async tests cover Core inserts of `None` and `bytes` into `LargeBinary`/`BLOB` and an ORM insert with an unset `LargeBinary`. The async binding xfails from #485 are removed, leaving only the strict LOB-read locator xfails (cubrid-lab/pycubrid#441); `docs/DRIVER_COMPAT.md` and `docs/TYPES.md` (+ Korean) no longer list the async `Binary` issue.

- **`String(0)` / `VARCHAR(0)` / `NVARCHAR(0)` no longer silently compile to the 4096 default (#440)** — the type compiler checked the length by truthiness, so an explicit `length=0` was treated as "no length" and rendered `VARCHAR(4096)` (or `NCHAR VARYING(4096)`). `length=None` still gets the documented default; an explicit zero now raises `CompileError`, since `VARCHAR(0)` is not a valid CUBRID length ([#456](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/456)) by @anyingiit (first contribution 🎉).

- **Reflection now returns table and view names in deterministic order (#443)** — added `ORDER BY class_name` to `get_table_names()` and `get_view_names()` catalog queries so reflection results no longer depend on database row order ([#457](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/457)) by @itsdevcode (first contribution 🎉).

- **Contributor workflow and docs exceptions clarified** — normal contributions use shared checks and matching docs; maintainers coordinate project-specific reviews, labels, translation deferrals and releases. Docs-not-needed body reasons require a populated standalone statement, with quoted/template examples excluded; executable doctests and real event/workflow regressions run locally and in docs-sync. Four existing reusable workflow callers are pinned to a verified upstream commit without changing their inputs or rollout settings.

- **Pure-driver integration setup is explicit (#464)** — `tox -e integration` now requires a `cubrid+pycubrid://` test URL rather than the former bare `cubrid://` C-extension URL. A bounded sync/async `SELECT 1` preflight fails before pytest when the URL, driver or database is unavailable. Async and stress suites derive their endpoint from the selected URL, preserving authentication, port and query options; an explicit `CUBRID_TEST_AURL` remains supported. The formal C-extension compliance CI route is unchanged, and optional native-driver comparisons remain explicitly skipped when that driver is absent.

- **Local tooling agrees with CI (#464)** — Ruff/mypy pre-commit revisions match the dev pins; the isolated mypy hook uses interpreter-compatible SQLAlchemy pins and existing Alembic dependencies without automatic stub installation. Tox covers Python 3.10–3.14, uses integration markers, retains 95% coverage, and matches CI's type-check cells. CLI/CI/tox share the Makefile's maintained Python source paths while hooks keep all tracked Python/pyi coverage. A deterministic consistency check rejects stale pins, missing interpreter branches, source omissions and runner drift. Two helper scripts received formatting-only changes with unchanged ASTs.

- **Strict typing is enforced across SQLAlchemy 2.0 and 2.1 (#459)** — timezone constructor annotations retain their always-enabled timezone behavior; compiler overrides match upstream positional arguments with typed boundaries for unannotated framework hooks. UNIQUE-index FK collision checks now raise a clear `CompileError` when no live Alembic connection is available. `make typecheck` reports dependency versions, and two pinned CI cells must pass through the required `matrix-result` check. Runtime SQL compilation and the 95% offline coverage threshold remain unchanged.

- **Async installation includes SQLAlchemy's required bridge (#448)** — the existing `[pycubrid]` and `[dev]` extras now request `SQLAlchemy[asyncio]`, which installs `greenlet` on both SQLAlchemy 2.0 and 2.1. The `[pycubrid]` extra intentionally supports sync and async URLs; bare installation keeps the same dependency contract. Fresh wheel smokes exercise async engine creation on 2.0.53 and 2.1.1 without a database or ambient packages. This is a patch-level installation bug fix.

- **Installation guidance distinguishes the driver from the async bridge (#448)** — FAQs, connection and troubleshooting guides, and translations now consistently state that pycubrid itself needs no CUBRID native libraries, while the `[pycubrid]` extra's `greenlet` dependency may need build tools when no compatible wheel is available.

- **Last-insert-ID SQL fallback works on SQLAlchemy 2.x (#458)** — both execution contexts now obtain a regular cursor from the active DBAPI connection for `SELECT LAST_INSERT_ID()`, instead of calling SQLAlchemy's unimplemented server-side-cursor hook. Native driver IDs (including `None`) remain preferred, and the temporary cursor is closed even if execution, fetching, or integer conversion fails. This is a backward-compatible bug fix suitable for a patch release.

- **Nightly mutation testing now uses mutmut 3** — The development extra pins `mutmut>=3.8,<4` instead of 2.x (superseding #450). `setup.cfg` and the non-gating CI job use mutmut 3's `source_paths`, `only_mutate`, pytest settings, `forkserver` isolation and `export-cicd-stats` rather than removed 2.x commands. A crash, failed clean tests, zero mutants or zero kills fails the job step; surviving mutants only lower the score, and the job remains `continue-on-error`. mutmut 3 generates a different mutant set, so its score is not directly comparable to the old 288/449 baseline. CI/development tooling only; no runtime change.
- **Timezone-aware types keep `timezone=True` on the instance (#442)** — `TIMESTAMPTZ`, `TIMESTAMPLTZ`, `DATETIMETZ` and `DATETIMELTZ` inherited the default `TIMESTAMP` constructor, so their instances reported `timezone=False`; they now set `timezone=True` and discard a duplicate `timezone` keyword during reflection ([#445](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/445)) by @pratipc (first contribution 🎉).

### Documentation

- Added a README "First contribution" guide (with Korean translation) pointing newcomers to the right sibling repo for their first PR, and documented the `good first issue` → `status: in progress` label lifecycle in AGENTS.md.

- **LIMIT/OFFSET troubleshooting matches the emitted SQL (#416)** — `docs/TROUBLESHOOTING.md` (+ ko) now states that the dialect emits the comma form (`.limit(10).offset(20)` → `LIMIT 20, 10`), that CUBRID also accepts standard `LIMIT n OFFSET m` without the dialect using it, and that bare `OFFSET` is a syntax error, so `.offset(n)` alone renders a large row-count sentinel ([#419](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/419)) by @paikend.

## [1.7.1] - 2026-09-18

This maintenance release contains fixes and supporting documentation and tests. The detailed sections below identify the affected behavior and related references.

**Highlights**

- **More accurate SQL execution** — fixes multi-column primary-key reflection, numeric bind handling, `OFFSET` without `LIMIT`, and `IS DISTINCT FROM` execution.

- **Safer ORM behavior** — improves `executemany` inserts and makes unsupported multi-row `ON DUPLICATE KEY UPDATE` expressions fail with a clear error.

- **Stronger regression coverage** — adds UUID round-trip, property-based, differential, and real-application ORM tests, and makes SQLAlchemy dialect compliance checks gate CI.

- **Expanded documentation** — adds runnable examples and clarifies driver-specific numeric precision limitations.

The detailed changes below preserve the original technical context and references.

### Added

- **Runnable usage examples in public docstrings (#337)** — added short, live-verified examples to the five main entry points: the connection URL forms (`cubrid+pycubrid://`, `cubrid+cubriddb://`, async `cubrid+aiopycubrid://`) in the package docstring, the `ON DUPLICATE KEY UPDATE` construct on `insert()`, and reflection via `inspect()` in the dialect module docstring (`REPLACE` and `MERGE` already had examples). Docstrings only — no behavior change; each example was executed against a live CUBRID 11.4.

- **UUID type contract test matrix (#376)** — added `test/test_uuid_contract.py`, which pins the full round-trip contract for `sa.Uuid()` (Python `uuid.UUID` values) and `sa.Uuid(as_uuid=False)` (string values) across INSERT, SELECT, WHERE, UPDATE, and reflection, against a live CUBRID. CUBRID has no native UUID type; the dialect stores it as `CHAR(32)`, and these 8 `integration`-marked tests catch any regression in that CHAR-backed storage or the value coercion (verified: `sa.Uuid()` round-trips as `uuid.UUID`, `as_uuid=False` as `str`, WHERE/UPDATE by UUID work, and reflection reports `CHAR`). Wired into the nightly `integration-full` bug-hunt job.

- **Mutation testing for `compiler.py` (stabilization Phase 8)** — added a `[mutmut]` configuration in `setup.cfg` (pinned `mutmut>=2.5,<3` in the `dev` extra) and a non-gating nightly `mutation-testing` job in `integration-full`. Mutation testing checks whether the offline suite actually *verifies* compiler logic rather than merely executing it: it mutates `compiler.py` and asserts the tests catch each change. The initial run scored 55.9% (251/449 mutants killed) and surfaced weak substring assertions — several tests asserted only `"JSON_EXTRACT" in sql`, `"LIMIT" in sql`, or `"GROUP_CONCAT" in sql` while letting the surrounding SQL structure mutate freely. Strengthening those to exact-match assertions on the full compiled output (JSON path extraction by type, `LIMIT`/`OFFSET` operand order and the offset-without-limit sentinel form, `UPDATE ... LIMIT`, and `GROUP_CONCAT`) raised the score to 64.1% (288/449). The job is `continue-on-error` because a score dip is a signal to strengthen a test, not a reason to block a release; the run needs no database.

- **Integration tests now exercise realistic ORM application behavior** — `test/test_dogfood_orm.py` models users, orders and tags (one-to-many and many-to-many) and verifies returned data, not only compiled SQL. Its 16 live tests cover lazy, `selectinload` and `joinedload` relationships; joins, filters, aggregates, correlated subqueries, pagination and outer joins; plus commit/rollback, bulk updates, orphan cascade deletion and auto-generated primary keys after `flush()`. The 16 tests run in the historical `integration-full` `fuzz-bug-hunt` job against **CUBRID 11.4**, not across the four-version snapshot matrix, and catch failures that individual compiler tests may miss.
- **Cross-version snapshots detect undeclared CUBRID behavior differences** — `test/version_differential/snapshot.py` records live server capability probes (ENUM, Boolean casts, `<=>`, CTEs, windows, `RETURNING`, `INTERSECT`/`EXCEPT`) and `get_columns()` reflection for fixed column types. The `integration-full` matrix captures one snapshot per supported server version (10.2, 11.0, 11.2 and 11.4); `version-differential` fails when a dialect-visible difference is not declared in `KNOWN_DIFFERENCES`. This checks portability expectations rather than assuming that all underlying servers behave identically.
- **Capability probe suite and driver-differential testing (stabilization Phases 5 & 7)** — added `test/capability/test_capability_probes.py`, which runs raw SQL against a live CUBRID and asserts the server's actual behavior matches what the dialect declares (`supports_native_enum`, `supports_native_boolean`, `supports_is_distinct_from`, `supports_multivalues_insert`, `supports_alter`, `supports_comments`, `insert_returning`, plus CTE/window/LIMIT-OFFSET), so a drift between a `supports_*` flag and reality is caught immediately instead of surfacing as a confusing downstream error. Added `test/test_driver_differential.py`, which runs the same Core operations on both the pycubrid and CUBRIDdb C-extension drivers and asserts they agree on SELECT round-trips, UPDATE/DELETE rowcount, aggregates, and NULL handling (skipping cleanly if the C-extension driver is not built). Both are `integration`-marked and run in the nightly `integration-full` bug-hunt job.

- **Property-based fuzz + metamorphic testing with Hypothesis (stabilization Phases 1–4)** — added `test/test_fuzz_select.py`, `test/test_fuzz_insert.py`, `test/test_fuzz_reflection.py`, and `test/test_metamorphic.py`. The fuzzers generate SELECT/INSERT combinations and random tables the hand-written suite never enumerated (boundary values `0`, `±1`, `2^31`, `2^63-1`, empty/Unicode/reserved-word/backslash strings) and assert dialect invariants: compilation raises only `CompileError` (never an unexpected exception), the positional-placeholder count equals the bound-parameter count, single/executemany/multi-values inserts store identical data, DDL→reflection round-trips agree (columns, nullability, primary keys, unique constraints), and (metamorphic) Core vs ORM SELECT, bind vs literal, and SQL LIMIT/OFFSET vs a Python slice return identical rows. Hypothesis profiles (`dev`/`ci`/`nightly`) are registered in `conftest.py`; PR CI runs the fast profile, and the nightly `integration-full` workflow runs the 2000-examples profile against live CUBRID. This bug-hunt found and fixed #426.

### Fixed

- **Removed the dead `implicit_returning = False` dialect attribute (#396)** — this was a SQLAlchemy 1.x-era switch with a comment claiming it prevents a `ResourceClosedError` on server-default INSERTs. In SQLAlchemy 2.x the CRUD compiler decides implicit `INSERT ... RETURNING` from `insert_returning` (already `False`), not `implicit_returning`, and `DefaultDialect` no longer even defines the attribute. Verified live on CUBRID 11.4 that a server-default INSERT + ORM refresh behaves identically with the attribute removed (no `ResourceClosedError`), and added an offline regression test asserting `insert_returning`/`update_returning`/`delete_returning` are the real switches and that the dead attribute stays gone.

- **`docs/TROUBLESHOOTING.md` LIMIT/OFFSET section no longer documents SQL the dialect never emits (#416)** — the section claimed the dialect generates `LIMIT n OFFSET m` and that CUBRID rejects the comma form; both were wrong. The dialect **only ever** emits CUBRID's comma form `LIMIT offset, count` (offset first), and offset-without-limit uses a sentinel count. `select(users).limit(10).offset(20)` compiles to `LIMIT 20, 10`, not `LIMIT 10 OFFSET 20` — a reader trusting the old doc would also read the two operands in the wrong order. Corrected in both the English and Korean (`docs/ko/TROUBLESHOOTING.md`) docs.

- **`docs/llms-full.txt` regenerated and a drift-check added to CI (#383)** — the AI-facing doc bundle was stale relative to the corrected source docs (it still taught the pre-#356 `VALUES()` ODKU pattern). It is regenerated from source via `scripts/generate_llms_full.py`, and the `lint` CI job now fails if `llms-full.txt` drifts from its generating source (regenerate-and-diff), so it can no longer silently go stale.

- **Reflection now returns column comments, consistent missing-table errors, and only user views (#387)** — Fixed three cases found by SQLAlchemy's `ComponentReflectionTest`: (1) the catalog query now reads the correct `class_of.class_name`, so `get_columns()` returns actual comments instead of silently reporting `None`; (2) missing tables and views raise SQLAlchemy `NoSuchTableError` from `get_columns()` / `get_indexes()` instead of a raw driver `ProgrammingError` (-493 / 42S02); (3) `get_view_names()` filters internal system views using `is_system_class = 'NO'`. This clears 22 of the 25 known-failure cases in that group. CUBRID normalizes identifiers to lower case rather than the upper case assumed by SQLAlchemy's `NormalizedNameTest`, so `requires_name_normalize = False` correctly skips that specific requirement; case-insensitive schema matching is unchanged. The other three failures (`test_get_noncol_index` twice and `test_get_view_names[False]`) are SQLAlchemy-harness fixture limitations because their objects are not created on CUBRID, not unresolved dialect reflection bugs.

- **`get_pk_constraint()` no longer drops composite primary-key columns (#426)** — reflecting a table with `PRIMARY KEY (a, b)` returned only `constrained_columns: ['a']`, silently losing every PK column after the first (and giving no column order). Root cause: the reflection scanned `SHOW COLUMNS` for the `PRI` key flag, but CUBRID (MySQL-compatible) marks only the *first* column of a composite PK as `PRI`. The PK columns are now read, in key order, from the `_db_index` / `_db_index_key` system catalog, with a `SHOW COLUMNS` fallback if the catalog query fails. Fixes reflected multi-column-PK ORM mappings and Alembic autogenerate. Found by the new reflection round-trip fuzzer.

- **`executemany` INSERT into a column with a `bind_expression()` CAST no longer sends the wrong parameter count (#421)** — SQLAlchemy's `insertmanyvalues` row-expansion miscounts bind parameters when a target column's type wraps its bind in a `bind_expression` (e.g. a `TypeDecorator` rendering `CAST(? AS VARCHAR(50))`): it emitted 4 placeholders but only 3 parameters (`INSERT ... VALUES (?, CAST(? AS ...)), (?, CAST(? AS ...))` with `(2, 3, 2)`), so the driver raised "wrong number of parameters". The dialect now drops the `insertmanyvalues` plan (in `visit_insert`) for INSERTs targeting such a column, falling back to ordinary DBAPI executemany; single-row inserts and the normal multi-row fast path (columns without a `bind_expression`) are untouched. Fixes the compliance suite's `CastTypeDecoratorTest::test_special_type`.

- **`Identity()` columns now emit `AUTO_INCREMENT`, and DATETIME/TIME microsecond limits are declared to the test suite (#388)** — SQLAlchemy stores an `Identity()` as `column.server_default`, which made the DDL compiler skip its `AUTO_INCREMENT` branch and emit a plain `INTEGER NOT NULL` column, so inserts failed with `Missing value for attribute 'id'`. `Identity()` is now treated as CUBRID's `AUTO_INCREMENT` (its spelling of an identity/autoincrement column). Also declared `datetime_microseconds`/`time_microseconds` as unsupported in `requirements.py` (CUBRID `DATETIME` stores millisecond precision only and `TIME` has no fractional seconds — verified live on 11.4), so the SQLAlchemy compliance suite skips those tests via its own machinery instead of baselining them as xfail. Remaining `#388` triage entries (`DistinctOnTest`, `ReturningGuardsTest`, C-driver-specific `RowCountTest`) are kept as documented xfails with precise root-cause comments; the genuine `CastTypeDecoratorTest` `insertmanyvalues` parameter-count bug is split out to #421.

- **Documented that the legacy `CUBRIDdb` C-extension driver loses `NUMERIC`/`DECIMAL` fractional precision (#386)** — the C-extension driver (bare `cubrid://`) truncates the fractional part of `NUMERIC`/`DECIMAL` values *below* the DBAPI layer, returning e.g. `15` for a stored `15.7563`. Because the data is already lost before SQLAlchemy sees it, no dialect result processor can recover it — this is an upstream C-driver limitation, not a dialect bug. The pure-Python `cubrid+pycubrid://` driver returns `Decimal` correctly (verified live on 11.4) and is the recommended driver. The affected `NumericTest` nodes stay baselined in `test/known_failures.txt` with this explanation, and `docs/DRIVER_COMPAT.md` / `docs/TYPES.md` now document the fidelity difference between the two drivers.

- **`ON DUPLICATE KEY UPDATE` referencing `stmt.inserted.col` now fails clearly for inline multi-row `VALUES` instead of a confusing bind error (#371)** — CUBRID has no `VALUES(col)` / row-alias syntax, so the dialect re-emits the INSERT bind parameter to reference the inserted value. That works for a single-row `INSERT` and for executemany (each execution is logically single-row), but for an inline multi-row `insert(t).values([{...}, {...}])` there is no single value to bind per conflicting row — the previous code raised a misleading `cannot resolve INSERT bind parameter ... Ensure the column is included in the INSERT values` (the column *was* included). It now raises a clear `CompileError` naming the CUBRID limitation and pointing to executemany, single-row statements, a literal/expression update, or `MERGE`. Nested references (e.g. `func.coalesce(stmt.inserted.col, ...)`) are caught too; literal/expression updates that do not reference the inserted value keep compiling for multi-row inserts. Refusing to compile avoids the silent-corruption trap of binding one row's value for every conflicting row.

- **`OFFSET` without `LIMIT` no longer silently caps result sets at ~1.07B rows (#414)** — a bare `.offset(n)` compiled to `LIMIT n, 1073741823`, reusing CUBRID's VARCHAR-length constant (2^30-1) as the row-count sentinel. That is a string-length bound, not a legal upper bound for a `LIMIT` row count, so a query with an offset and no limit was silently truncated at 1,073,741,823 rows (wrong results, no error) on tables past that size. The sentinel is now `2^62` (`4611686018427387904`) — effectively unbounded (~4.6×10^18 rows). It is deliberately **not** the signed BIGINT maximum (2^63-1): CUBRID computes `offset + row_count` internally and overflow-checks it, so a BIGINT-max sentinel raises `ERROR -458 (Overflow occurred in addition context)` for any positive offset (caught by the SQLAlchemy compliance suite's `FetchLimitOffsetTest`). 2^62 leaves ~4.6×10^18 rows of offset headroom before the sum can overflow. Named the value `_CUBRID_OFFSET_NO_LIMIT_ROW_COUNT` in `compiler.py`, and the regression test now asserts on the constant (and that the old 2^30-1 cap is gone) instead of the bare literal.

- **Numeric bind parameters keep their scale in arithmetic, and FROM-less `SELECT ... WHERE` compiles (#386)** — CUBRID coerces a bound parameter in `NUMERIC(p,s) + ?` arithmetic to an integer, silently dropping the fractional scale (a SQL literal or an explicit CAST keeps it). Scaled `NUMERIC`/`DECIMAL` binds now render `CAST(? AS NUMERIC(p,s))` so the scale is preserved; unconstrained `Numeric()` binds are left untouched (CUBRID's bare `NUMERIC` is scale 0 — specify precision/scale for exact decimals). Also added a `default_from()` of ` FROM db_root` (CUBRID's `DUAL` equivalent) so a FROM-less `SELECT` carrying a `WHERE` clause no longer raises a syntax error.

- **`supports_is_distinct_from` / `supports_native_enum` now report their real capabilities (#381, #382)** — both flags were `False`, which made SQLAlchemy's official suite skip `IsOrIsNotDistinctFromTest` and the native-enum tests even though both features are fully implemented (IS DISTINCT FROM emulation via `<=>` from #345/#377; native `ENUM(...)` DDL). Flipped both to `True`; the previously-skipped suite tests now run and pass live on CUBRID 11.4 (5 IS DISTINCT FROM + native-enum cases, zero regressions). Also corrected the `ENUM` docstring, which wrongly claimed `native_enum=False` is "ignored" — it correctly emits `VARCHAR(n)` per the SQLAlchemy contract (verified live).

- **SQLAlchemy's dialect compliance tests now fail CI on regressions (#380)** — The suite previously never ran correctly: missing `[sqla_testing]` configuration crashed setup, and `|| true` hid the result. The new config enables the suite; CI runs it as a required Python 3.14 × CUBRID 11.4 cell on pinned SQLAlchemy 2.0.53. CUBRID has no temporary tables, so the associated requirements are excluded (removing 732 setup errors). Remaining known failures are recorded in `test/known_failures.txt` with strict xfails: new failures break CI, fixed cases must leave the manifest, and stale test names fail collection under `CUBRID_STRICT_KNOWN_FAILURES=1`. The baseline depends on SQLAlchemy's test version. Follow-up issues track view DDL (#385), Decimal (#386), reflection (#387), and other gaps (#388).

- **`IS DISTINCT FROM` live execution fixed (#377)** — live CUBRID rejects MySQL-style `NOT (a <=> b)` when the expression appears in a SELECT projection. The emulation now negates the NULL-safe `<=>` result as `(a <=> b) = 0`, which preserves the four-row SQL truth table and is valid CUBRID syntax. Added live truth-table coverage for both `IS DISTINCT FROM` and `IS NOT DISTINCT FROM` ([#379](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/379)) by @tayfuryldz (first contribution 🎉).

- **create-release.yml: dropped `--target` from `gh release create`** — with an already-pushed tag (the normal tag-push trigger) `--verify-tag` already guarantees the tag exists, and passing `target_commitish` for an existing tag makes the Releases API return `422 Validation Failed`, so the first tag-triggered run of this workflow always failed. Verified live by the v0.4.0 tag attempt in cubrid-mcp-server.

### Documentation

- **Demo GIF embedded in README** — auto-generated terminal demo showing create_engine → connect → execute → result.

- **Korean/multi-language docs governance** — every `docs/README.<lang>.md` translation now carries a sync marker, and docs-sync gained a `translation-sync` job that fails a PR when `README.md` changes without any translation changing (escape hatch: the `translations-deferred` label).

- **한국어 문서 페이지 — 배치 5 완결 (#341)** — TROUBLESHOOTING(1,325줄) 번역으로 14페이지 전체 완성.

- **한국어 문서 페이지 — 배치 4 (#341)** — FEATURE_SUPPORT(기능 비교)·DEVELOPMENT(개발 가이드) 번역 추가. TROUBLESHOOTING만 남음.

- **한국어 문서 페이지 — 배치 3 (#341)** — ALEMBIC(마이그레이션 가이드) 번역 추가. FEATURE·TROUBLE·DEV만 남음.

- **한국어 문서 페이지 — 배치 2 완결 (#341)** — ORM_COOKBOOK·DML_EXTENSIONS 번역으로 Usage 축 완성. ALEMBIC·FEATURE·TROUBLE·DEV는 후속 배치.

- **한국어 문서 페이지 — 배치 2 (Usage/Reference 1차, #341)** — TYPES·ARCHITECTURE 번역 추가. ORM_COOKBOOK·DML_EXTENSIONS·ALEMBIC·FEATURE·TROUBLE·DEV는 후속.

- **한국어 문서 페이지 — 배치 1 (Getting Started/Ref/Ops 축, #341)** — QUICKSTART·CONNECTION·DRIVER_COMPAT·ISOLATION_LEVELS·SUPPORT_MATRIX·PERFORMANCE 6페이지 번역을 `docs/ko/`에 추가. Usage 축(ORM·DML·TYPES·ALEMBIC)과 FEATURE/ARCH/TROUBLE/DEV는 후속 배치.

- **Docs site information architecture unified across the ecosystem** — nav reorganized to the shared six-tab skeleton (Home / Getting Started / Usage / Reference / Operations / Project), the five README translations (ko/de/hi/ru/zh) are now reachable via Project → Translations (previously URL-only), palette unified to blue with search-suggest, and the homepage gains an Ecosystem section linking the three sibling sites.

- **CUBRID-Python BSD basis documented, server-license line added, NOTICE created, copyright unified (#333)** — `THIRD_PARTY_LICENSES.md` now records that the optional CUBRID-Python extra's `BSD` claim rests on PyPI metadata and setup.py (the upstream repository ships no LICENSE file or headers; 2- vs 3-Clause unspecified), and carries the verified CUBRID server licensing statement (engine Apache-2.0, APIs/connectors BSD per upstream `COPYING` — GPL v2+ is outdated). Added a two-line `NOTICE` (independent implementation, no third-party code). LICENSE copyright unified to `Yeongseon Choe, Gyeongjun Paik` (2021-2026).

- **Added `THIRD_PARTY_LICENSES.md` and a Provenance section in `docs/ARCHITECTURE.md`** — the license inventory covers the default runtime tree (SQLAlchemy, greenlet, typing_extensions) and the optional `[alembic]`/`[cubrid]` extras; the provenance note states that this dialect is an independent implementation, not a port of the legacy `CUBRID-Python`-bundled dialect. Documentation only.

## [1.7.0] - 2026-09-02

This release contains multiple dialect improvements and compatibility changes. Review the detailed sections below for the affected features and upgrade considerations.

**Highlights**

- **More reliable SQL and schema handling** — adds native ENUM support, null-safe distinct comparisons, and safer handling of unsupported SQL constructs.

- **Improved reflection and migrations** — fixes schema-name handling, isolation-level round trips, and support for column alterations through Alembic.

- **More dependable connection recovery** — recognizes additional pycubrid disconnect errors so SQLAlchemy can invalidate broken pooled connections.

- **Driver and compatibility guidance** — documents the explicit `cubrid+cubriddb://` connection URL and aligns SQLAlchemy support guidance with versions 2.0–2.1.

The detailed changes below include the original issue references and CI/documentation updates.

### Added

- **Native ENUM type support (#343)** — `sqlalchemy_cubrid.ENUM` renders `ENUM('a', 'b', ...)` DDL. Plain `sa.Enum` maps to native ENUM via colspecs. Reflection parses the element list from `SHOW COLUMNS`. Verified live on CUBRID 10.2, 11.0, 11.4 (the docs previously and wrongly claimed CUBRID has no ENUM).

- **`IS [NOT] DISTINCT FROM` emulation (#344)** — CUBRID lacks the SQL-standard syntax but supports the null-safe equal `<=>`. The dialect now renders `NOT (a <=> b)` / `a <=> b` — the same approach the MySQL dialect uses.

- **New explicit `cubrid+cubriddb://` URL and `[cubriddb]` install extra for the legacy CUBRIDdb driver (#276)** — the legacy `CUBRIDdb` C-extension driver (the driver bound to the bare `cubrid://` URL) can now be selected unambiguously via the explicit `cubrid+cubriddb://` URL, backed by a matching `cubriddb = ["CUBRID-Python"]` install extra. The bare `cubrid://` URL continues to bind CUBRIDdb — no behavior change to any existing URL. For new projects the pure-Python `pycubrid` driver is the recommended choice: install `sqlalchemy-cubrid[pycubrid]` and use `cubrid+pycubrid://` (installs with pip alone, no C toolchain).

- **Native Alembic `ALTER COLUMN` type changes and column renames (#305)** — `CubridImpl.alter_column()` previously raised `NotImplementedError` for column type changes and renames, forcing every such migration through `batch_alter_table` (full table recreate). CUBRID in fact supports MySQL-compatible `ALTER TABLE ... MODIFY`, `CHANGE`, and `RENAME COLUMN`, so the dialect now emits native DDL: a type change compiles to `MODIFY`, a rename to `RENAME COLUMN ... TO ...`, and a combined rename + type change to a single `CHANGE`. Type conversions are governed by the server's `alter_table_change_type_strict` system parameter (incompatible/truncating conversions error when `yes`, may silently truncate when `no`); `batch_alter_table` remains available as a fallback for genuinely lossy conversions. Added SQL-emission tests covering all three DDL forms.

### Changed

- **Connection pools now recognize transport failures more reliably (#314)** — `is_disconnect()` checks stable error codes first, then an `OSError` in the explicitly chained, cycle-guarded `raise ... from` (`__cause__`) exceptions, using message text only as a fallback. It adds pycubrid `-4` (`ER_COMMUNICATION`, SQLSTATE `08S01`) to existing disconnect codes `-21003/-21005/-10005/-10007`, so changing driver error wording is less likely to leave a dead connection in the pool. To prevent false invalidation, implicit `__context__` is ignored and ordinary `OperationalError` / `InterfaceError` without a disconnect code, explicit `OSError` cause or recognized message is **not** a disconnect. Text fallback remains for CUBRIDdb (without `OperationalError`) and pycubrid client errors that expose only a message, such as `connection lost during receive`. Offline tests cover numeric codes, explicit vs implicit causes, non-transport errors and the fallback.

- **Ruff lint rule selection now declared explicitly (#271)** — `pyproject.toml` configured ruff but never set `[tool.ruff.lint] select`, so `ruff check` inherited ruff's implicit defaults. Ruff expanded that default set in 0.16 (59 → 413 rules against this repo's config), which is why #267 (`0.15.21 → 0.16.2`) failed lint with 151 errors in untouched code. Pinning the ruff *version* in #252 stopped unpinned installs from drifting, but could not survive the bump itself — the rule set is now pinned too, via `select = ["E4", "E7", "E9", "F"]`, which is exactly what ruff selected by default through 0.15.x (same 59 rules under both versions) ([#272](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/272)) by @paikend.

### Fixed

- **`is_disconnect()` now actually recognizes pycubrid's `"connection lost during receive"` message (#322)** — the #314 hardening documented (in both the CHANGELOG and the `is_disconnect()` docstring) that pycubrid's client-side `"connection lost during receive"` string was covered by the message fallback, but the pattern was never added to `_disconnect_messages`. pycubrid raises this on a clean-EOF receive (`connection.py` sync path) with **no** numeric error code and **no** `OSError` cause, so all three detection layers missed it and SQLAlchemy failed to invalidate the dead connection — a stale connection could be served to the next pool checkout. Added the substring `"connection lost"` to `_disconnect_messages` so the message fallback matches. Added an offline regression test asserting `is_disconnect()` returns `True` for a bare driver error carrying only that message.

- **`SELECT SCHEMA()` returning NULL no longer leaks the fake schema `"None"` (#290)** — `_get_default_schema_name()` did `str(connection.execute(text("SELECT SCHEMA()")).scalar())`, so when `SCHEMA()` returned SQL NULL the Python `None` was stringified to the literal `"None"`. Because `get_schema_names()` and `_schema_is_default()` test the value against the `None` object (not the string), that fake name leaked through as a real schema (`get_schema_names()` → `["None"]`). `_get_default_schema_name()` now returns `Optional[str]` — `None` when `SCHEMA()` is NULL, otherwise the real name — so `get_schema_names()` correctly returns `[]` with no default schema. This pins the default-schema contract used by the follow-up schema-guard fixes.

- **Inline SQL literals now preserve backslashes on default CUBRID servers (#313)** — The compiler previously doubled each `\` in `literal_binds=True` output, following MySQL rules. CUBRID defaults to `no_backslash_escapes=yes`, so a path like `C:\temp` could be stored or compared with two backslashes instead of one. The fix covers inline DML, JSON paths and table/column comments, verified against CUBRID 11.2 and its documented default. If the server explicitly uses `no_backslash_escapes=no`, set the static `CubridDialect(no_backslash_escapes=False)` option to retain the old escaping behavior (offline compilation may have no connection to probe). **Migration:** audit existing data written with inline literals for already-doubled backslashes; the fix does not repair those rows. Compiler, JSON, DDL-comment and live-roundtrip tests cover the change.

- **Object-detail reflection now raises `NoSuchTableError` for a non-default schema (#291)** — the shared `_schema_is_default()` guard was only applied to list/existence methods (`get_table_names`, `get_view_names`, `has_table`, `has_index`), so object-detail methods (`get_columns`, `get_pk_constraint`, `get_foreign_keys`, `get_indexes`, `get_unique_constraints`, `get_view_definition`, `get_table_comment`) silently ignored `schema=` and returned metadata from the default schema — masking the fact that CUBRID exposes a single effective schema per connection. Those seven methods now call a new `_raise_if_non_default_schema()` helper that raises `NoSuchTableError("<schema>.<object>")` when `schema=` is not the default, matching SQLite's behaviour and preventing a real "object not found" from being hidden behind empty metadata. List/existence methods keep returning empty/false via `_schema_is_default()`.

- **Schema-default comparison is now case-insensitive (#292)** — `_schema_is_default()` compared `schema == self.default_schema_name` with a plain, case-sensitive `==`. CUBRID reports catalog names uppercased (`DBA`) while SQLAlchemy normalizes to lower case, so `MetaData.reflect(schema="dba")` (or any case-mismatched schema argument) failed the guard and was treated as a foreign schema — yielding no reflection or a spurious `NoSuchTableError`. The guard now normalizes both sides via `self.normalize_name()` (the dialect's own identifier rules), so `"dba"`, `"DBA"`, and the reported default all compare equal. Names the user explicitly quoted (`quoted_name` with `quote=True`) are still compared case-sensitively, honouring the intent to preserve case.

- **Schema reflection is now internally consistent (#280)** — `get_schema_names()` previously returned `[]` with the docstring "CUBRID does not support schemas", directly contradicting `_get_default_schema_name()` (which returns a real schema via `SELECT SCHEMA()`), and the `schema=` argument was handled differently per method: `get_table_names` returned `[]` for a non-default schema while `get_view_names`/`has_table`/`has_index` ignored the argument entirely — so `MetaData.reflect(schema=<x>)` produced a contradictory "0 tables + all views". The dialect now operates in a consistent single-schema mode: `get_schema_names()` returns `[default_schema_name]`, and a shared `_schema_is_default()` guard makes `get_table_names`, `get_view_names`, `has_table`, and `has_index` honour `schema=` uniformly (the default schema is reflected; any other schema yields nothing). Owner-qualified cross-schema reflection is intentionally not attempted. Verified against live CUBRID 11.2.

- **Isolation-level `set` → `get` round-trip is now symmetric (#281)** — `get_isolation_level()` previously returned only the long granular spelling per code (setting `"REPEATABLE READ"` came back as `"REPEATABLE READ SCHEMA, REPEATABLE READ INSTANCES"`; `"READ COMMITTED"` / `"CURSOR STABILITY"` came back as the long form), so the short standard names a user passes in were never returned — a mismatch SQLAlchemy compares on pool return/reset. `_ISOLATION_LEVEL_REVERSE` now returns one canonical name per integer code: the short standard names for `READ COMMITTED` (4), `REPEATABLE READ` (5), and `SERIALIZABLE` (6), and the granular spelling for levels 1–3 (which have no short name). Aliases still collapse onto their canonical code, so `set` → `get` round-trips to the same level for every accepted input name. `reset_isolation_level()` and the `None`-row fallback now use the canonical `"READ COMMITTED"`. Added offline round-trip tests plus live CUBRID verification.

- **Obsolete pre-MVCC isolation levels (1–3) removed from the accepted set (#307)** — the dialect's `_ISOLATION_LEVEL_MAP` and `get_isolation_level_values()` still advertised the four legacy granular levels that CUBRID's MVCC engine (10.0+) removed. On a modern server (verified against live CUBRID 11.2.9) `SET TRANSACTION ISOLATION LEVEL 1|2|3` is rejected with *"Isolation level value in MVCC must be 'read committed', 'repeatable read' or 'serializable'"*, so any name resolving to codes 1–3 could only ever fail at the server. Those three names (`REPEATABLE READ SCHEMA, READ UNCOMMITTED INSTANCES`, `READ COMMITTED SCHEMA, READ COMMITTED INSTANCES`, `READ COMMITTED SCHEMA, READ UNCOMMITTED INSTANCES`) now raise a clear client-side `ValueError` instead. The dialect keeps the three supported MVCC levels — `READ COMMITTED` (4), `REPEATABLE READ` (5), `SERIALIZABLE` (6) — plus the still-valid aliases (`CURSOR STABILITY` and the two long spellings that map to 4/5). `_ISOLATION_LEVEL_REVERSE` drops the dead 1–3 entries while `get_isolation_level()` stays tolerant of any unexpected server value via its string fallback. `docs/ISOLATION_LEVELS.md` rewritten to document the three MVCC levels and the historical removal.

- **Lint job red on `main` (#268)** — `#257` removed the only use of `re` in `test/test_packaging.py` but left `import re` behind, so `ruff check sqlalchemy_cubrid/ test/` failed with `F401` and took `matrix-result` down with it. Removed the orphaned import ([#270](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/270)) by @paikend.

- **Code review fixes (#242–#246)** — the `visit_replace` fallback raises `NotImplementedError` instead of silently emitting `INSERT` (#243); `do_ping` is wrapped in `try`/`except` for `pool_pre_ping` safety (#244); `Merge` sets `inherit_cache` and the dead `_quote_free_identifiers` is removed (#245); the remaining broad `except` block in the dialect logs with `exc_info=True` (#246); and the `render_literal_value` backslash escaping is documented in a clarifying comment (#242) ([#247](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/247)) by @yeongseon, co-authored by Sean.

### Documentation

- **Documented that CUBRID's `LIST` collection type is a synonym for `SEQUENCE`** — CUBRID accepts `LIST(type)` in DDL but normalizes it to `SEQUENCE` at parse time, so a `LIST(INTEGER)` column is stored and reflected as `SEQUENCE OF INTEGER` (verified on live CUBRID 11.2). Clarified in `docs/TYPES.md` and via a code comment in `ischema_names` why the dialect exposes only the canonical `SEQUENCE` type and deliberately omits a `LIST` type/reflection entry (a type compiling to `LIST(...)` would produce spurious Alembic autogenerate diffs against the reflected `SEQUENCE(...)`). No behavior change.

- **Documented canonical isolation-level names on read-back (#293)** — clarified that `get_isolation_level()` returns the *canonical* name for a level, which may differ from the alias passed to `set_isolation_level()` (CUBRID accepts several aliases per numeric level). Added a note to `docs/ISOLATION_LEVELS.md` and the `get_isolation_level()` docstring. Behavior is unchanged; the reverse mapping was already correct.

- **Aligned the `Documentation` project URL with the README docs badge (#294)** — `pyproject.toml` pointed `Documentation` at the repo tree (`.../tree/main/docs`) while the README badge pointed at the published site `https://cubrid-lab.github.io/sqlalchemy-cubrid/`. Both now use the published site so PyPI metadata and the README agree.

- **Documented the `[cubrid]` install extra in the README (#295)** — the optional `cubrid = ["CUBRID-Python"]` extra (the legacy C-extension driver used by the bare `cubrid://` URL) was declared in `pyproject.toml` but undocumented. Added a README installation note explaining what it installs and clarifying that the pure-Python `[pycubrid]` driver remains the recommended driver for new projects.

- **Realigned the SQLAlchemy version-support narrative from "2.0–2.2" to "2.0–2.1" (#312)** — README (+5 locale docs), `docs/index.md`, `docs/ARCHITECTURE.md`, `docs/QUICKSTART.md`, `docs/PRD.md`, `docs/FEATURE_SUPPORT.md`, `docs/CONNECTION.md`, `docs/SA_COMPAT.md`, and `ROADMAP.md` claimed support for a non-existent SQLAlchemy 2.2 line, contradicting `docs/SUPPORT_MATRIX.md` (which correctly lists 2.1.x as the latest tested version and ≥2.2 as unsupported). SQLAlchemy's next feature line is 2.1, not 2.2 — PyPI ships only `2.1.0b1/b2/b3` pre-releases. Historical CHANGELOG entries are left intact as an accurate record.

### CI

- **Async integration tests now honor the supported pycubrid version range (#318)** — Instead of `pip install pycubrid`, the CI and full-integration workflows install `pip install -e ".[pycubrid]"`, enforcing the then-declared `pycubrid>=1.3.2,<2.0` range and avoiding an unintended future 2.x driver. They also remove a duplicate `pytest-asyncio` install already supplied by the development extra. These jobs verify released driver versions; testing pycubrid's unreleased `main` branch remains the separate upstream canary. CI only; no runtime or packaging change.
- **`sqlalchemy-22-canary` pin was unsatisfiable; retargeted to SA 2.1 and renamed (#312)** — the canary installed `--pre "sqlalchemy>=2.2.0b1,<2.3"`, but no `2.2.x` release exists on PyPI (SQLAlchemy's next line is 2.1, latest stable `2.0.52`), so the job failed at the install step on every PR and `main` and never actually ran. It now installs `--pre "SQLAlchemy>=2.1.0b1,<2.3"` and the job is renamed `sqlalchemy-21-canary`. It remains `continue-on-error: true` (non-gating). This reverts the incorrect #231 "bump" (which assumed `2.1.0b1` was no longer a pre-release) and restores the intent of #206.

- **The pycubrid canary now runs live integration tests, and Alembic tests tolerate version differences (#323)** — Earlier canary checks tested `pycubrid@main` offline only (#319); ordinary CI exercised released drivers. A new non-gating `upstream-canary-integration` job starts CUBRID 11.4, installs pycubrid from `main`, and runs synchronous and asynchronous integration tests (`continue-on-error: true`) to expose cross-project regressions earlier. Separately, the Alembic test patch target now adapts to the installed module layout: in Alembic 1.14+, `alembic.autogenerate.compare` is a module rather than the package path previously patched, which caused four local `ModuleNotFoundError` failures. PR #325 also capped Alembic at `<2.0` in both the then-declared `[alembic]` and `[dev]` extras (range `>=1.7,<2.0`), affecting dependency resolution but not dialect runtime behavior.
## [1.6.0] - 2026-07-18

This release strengthens schema reflection and SQLAlchemy compatibility. Primary-key and unique-constraint metadata are more reliable, with additional safeguards for changes to SQLAlchemy internals.

### Changed

- **FK reflection code extracted into testable helper (#120, PR #236)** — `_get_foreign_keys_from_ddl()` is now a standalone method. CUBRID system catalog views do not expose FK referenced-table/column metadata, so DDL parsing remains the sole FK reflection path. The extraction improves unit test isolation by @yeongseon.

### Fixed

- **`bind_with_type` private API insulation (#231, PR #235)** — `bind_with_type()` in `_compat.py` called `element._clone()` without a guard. If SQLAlchemy renames or removes `_clone()` in a future release (e.g. 2.2+), the dialect would crash with `AttributeError`. Added `try/except AttributeError` fallback that constructs a fresh `BindParameter` with the same key, value, type, and unique flag. This path only fires if SA changes the private API; the existing `_clone()` path remains the primary code path for SA 2.0–2.1 by @yeongseon.

- **PK constraint name reflection fixed (#120, PR #236)** — `get_pk_constraint()` queried the non-existent `db_constraint` system view (CUBRID has no such view in any version; verified against the CUBRID 10.1/11.2/11.4 official manuals), causing the PK constraint name to always be `None` in production. The query now targets `_db_index` (`is_primary_key = 1`), the authoritative system catalog for index metadata. Constraint names like `pk_users` are now correctly reflected by @yeongseon.

- **Unique constraint reflection hardened via system catalog (#120, PR #236)** — `get_unique_constraints()` now queries `_db_index` (`is_unique = 1`, excluding PK/FK auto-indexes) and resolves column names via `SHOW INDEXES` as the primary path, with the DDL regex as a fallback. This eliminates brittle regex parsing when the system catalog is available, matching the proven pattern already used by `get_indexes()` by @yeongseon.

### CI

- **SA 2.2 canary bumped (#231, PR #235)** — the `sqlalchemy-22-canary` CI job now installs `sqlalchemy>=2.2.0b1` (was `>=2.1.0b1`, which is no longer a pre-release). Added `continue-on-error: true` so canary failures warn but don't gate PRs — pre-release breakage is expected and shouldn't block development by @yeongseon.

- **CI lint now uses pinned ruff version (#252)** — the lint job used `pip install ruff` (unpinned). Now installs from `.[dev]` extras to match the pinned `ruff==0.15.21` in `pyproject.toml`.

### Tests

- **646 offline tests pass** (was 641 before Sprint 2); 97% `dialect.py` coverage; integration tests pass across CUBRID 10.2–11.4 × Python 3.10–3.14.

## [1.5.1] - 2026-07-18

This maintenance release makes unsupported SQLAlchemy operations fail explicitly instead of silently falling back to unexpected behavior.

### Upgrade notes

Applications that previously called `.returning()` without an immediate error must change those statements; the dialect does not provide server-side `RETURNING` support.

### Fixed

- **Reject unsupported `RETURNING` statements** — insert, update, and delete statements using `.returning()` now raise `CompileError` rather than silently using an unrelated primary-key retrieval path. For generated primary keys, use `result.inserted_primary_key` where applicable ([#229](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/229)) by @yeongseon.

- **Declare two-phase transactions unsupported** — the dialect explicitly disables two-phase commit support, allowing SQLAlchemy's compatibility tests to skip operations that CUBRID does not support through this dialect ([#230](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/230)) by @yeongseon.



## [1.5.0] - 2026-05-23

This release expands SQLAlchemy 2.1 compatibility and improves asynchronous test reliability. Check the dependency range and compatibility notes when upgrading.

### Added

- **SQLAlchemy 2.1 compatibility and preparation for 2.2 (#206)** — The dependency range became `sqlalchemy>=2.0,<2.3`, allowing installation with 2.1 and future 2.2 versions. The dialect uses SQLAlchemy 2.1's `update_post_criteria_clause` hook for CUBRID UPDATE `LIMIT`, handles the new `Float` type affinity so `JSON[...].as_float()` still emits `CAST(... AS DOUBLE)`, and declares `AsyncAdapt_pycubrid_connection.await_` as a class-level staticmethod after its base class removed that attribute. All 639 offline tests passed on SQLAlchemy 2.0.49 and 2.1.0b2; this is not evidence of live compatibility with unreleased 2.2 by @yeongseon.

### Performance

- **Historical native-ping benchmark (feature shipped in v1.4.2; no new ping change)** — The [paired seven-trial ORM benchmark](https://github.com/cubrid-lab/cubrid-benchmark/tree/main/experiments/orm-overhead/runs/2026-04-22_native-ping-hotpath) (bootstrap 95% CI) compared native `CHECK_CAS` against forced `SELECT 1` using the **same installed versions** and `pool_pre_ping=True` in both arms: Core checkout/SELECT-by-PK throughput +108.2% [+107.8, +109.6] and ORM session/SELECT-by-PK +42.1% [+41.8, +43.9], with lower p50/p95 latency. These results concern short-lived checkouts, not long-lived connections. The measurement used sqlalchemy-cubrid 1.4.2, pycubrid 1.3.2, SQLAlchemy 2.0.48, CUBRID 11.2.9, and CPython 3.10.12; **v1.5.0 does not change ping behavior**.

### CI

- **`sqlalchemy-22-canary` CI job promoted to gating (#206)** — previously `continue-on-error: true` against a non-existent `sqlalchemy>=2.2.0b1`. Now installs `--pre "sqlalchemy>=2.1.0b1,<2.3"` so the job actually exercises the latest available SA pre-release and fails the build on regressions by @yeongseon.

### Tests

- **Async integration stability for issue #208** — `test/test_aio_integration.py` now seeds per-test data instead of relying on module-shared CRUD state, adds live `pool_pre_ping=True` recovery coverage after an internal async transport drop, and verifies async SQLAlchemy INSERT returns `lastrowid` without adding a new `AsyncAdapt_pycubrid_connection.get_last_insert_id()` passthrough because async pycubrid already populates `cursor.lastrowid` and the dialect retains SQL fallback by @yeongseon.

## [1.4.3] - 2026-05-13

This patch improves collection-type reflection and SQLAlchemy 2.1 compatibility, while adding documentation for MERGE column resolution.

### Added

- **`visit_double` alias** — forward compatibility with SQLAlchemy 2.1 which compiles `Double` via `visit_double()` (#206) ([commit deaeb80](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/deaeb80c6277435b1e1045f8df0ddb4ce686b5d6)) by @yeongseon.

- **MERGE column resolution docs** — column resolution rules and error reference added to `DML_EXTENSIONS.md` (#207) ([commit d568e81](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/d568e81dcfd82184e8933fbf54f66048ca1a5cd8)) by @yeongseon.

- **Collection member split tests** — `_split_collection_members` unit tests with paren-depth guard (#204) ([commit 2ee1803](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2ee1803c6126d377eadd82bb12a66da954f30626)) by @yeongseon.

### Fixed

- **Paren-depth-aware collection member split** — reflection now correctly splits nested generic types like `NUMERIC(15,2)` inside `SET`/`MULTISET`/`SEQUENCE` (#204) ([commit f46c678](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f46c6785c60200b0bdb3a16c8354a5c3211f1ee8)) by @yeongseon.

- **Collection member type params preserved** — compilation and reflection retain precision/scale for parameterized member types (#194) ([commit 5342636](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5342636a112f4fa827e96c94ee20d7012175bb18)) by @yeongseon.

- **Oracle review fixes** — type args, timezone semantics, and regression test gaps addressed (#203) ([commit b49d2f5](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b49d2f5c97f348ca07320b46d4c10460d6c63d58)) by @yeongseon.

## [1.4.2] - 2026-04-21

This release improves connection-pool health checks for the synchronous and asynchronous pycubrid dialects.

### Upgrade notes

Applications using the `[pycubrid]` extra must meet the updated minimum driver version. The change affects connection health checks, not application SQL.

### Changed

- **Faster connection health checks** — `pool_pre_ping` uses the driver's native `Connection.ping()` or `AsyncConnection.ping()` rather than a SQL query. This reduces the extra round trip needed to validate a pooled connection ([#149](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/149)) ([commit 045c761](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/045c761bc22412d468f9853929b363be82052ac1)) by @yeongseon.

- **Updated pycubrid requirement** — installing the `[pycubrid]` extra now requires `pycubrid>=1.3.2,<2.0` to provide the native ping interface for both dialects ([commit 045c761](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/045c761bc22412d468f9853929b363be82052ac1)) by @yeongseon.



## [1.4.1] - 2026-04-21

This documentation-only patch clarifies supported behavior and keeps translated guides consistent. **No runtime or packaging behavior changed.**

### Documentation

- **Clarified dialect behavior** — expanded explanations of schema reflection, `postfetch_lastrowid`, SQLAlchemy internal API dependencies, type handling, and `ON DUPLICATE KEY UPDATE`.

- **Aligned development documentation** — corrected inconsistencies in the product requirements, contributor guidance, and CI descriptions.

- **Updated translations** — synchronized the Korean, German, Russian, Chinese, and Hindi READMEs with the English documentation.


## [1.4.0] - 2026-04-20

This release adds SQLAlchemy compatibility safeguards, Alembic migration guidance, and connection-pool stress coverage. It also updates the optional pycubrid dependency requirement.

### Added

- **SQLAlchemy 2.2 compatibility shim** — `sqlalchemy_cubrid/_compat.py` insulates compiler from SA private API changes (`is_literal_value`, `bind_with_type`, `for_update_arg`, `limit_clause`, `offset_clause`). `bind_with_type` now preserves `expanding`/`literal_execute`/`isoutparam` flags; `is_literal_value` handles `visitors.Visitable` instances (Oracle post-review fixes) (#142). SQLAlchemy 2.2 remains unsupported: the dependency stays pinned to `<2.2`, and the shim prepares the codebase for a future bump without lifting the pin.

- **Alembic safety checklist + advisory CLI** — `docs/ALEMBIC.md` adds Pre-Migration Checklist, Pre-Deploy Sequence, and Rollback Template; `scripts/alembic_safety_check.py` provides advisory detection for non-transactional DDL risks (#144)

- **Compiler benchmark baseline** — `scripts/bench_compile.py` per-construct timing baseline. Baselines: SELECT+LIMIT ~178µs, INSERT ~129µs, INSERT ON DUPLICATE KEY UPDATE ~234µs (1.8× simple INSERT due to `replacement_traverse` overhead), SELECT FOR UPDATE ~153µs (#145)

### Fixed

- **pycubrid dependency pin** — `pycubrid>=1.2.0,<2.0` (was missing upper bound) (#143)

### Tests

- **QueuePool concurrency stress tests** — 6 tests covering sync concurrent checkouts within `pool_size`, overflow burst absorption with barrier sync, `pool_timeout` exhaustion, `pool_recycle` aged-connection replacement, async `gather` within `pool_size`, async overflow burst

- **F401 lint regression** — removed unused `CubridDialect` import in `test/test_logging.py`

## [1.3.0] - 2026-04-19

This release improves schema reflection, SQL compilation, and Alembic migration diagnostics. It also adds stronger integration and packaging checks.

### Added

- **FK parsing with ON DELETE/ON UPDATE** — `get_foreign_keys()` regex now captures referential action clauses from `SHOW CREATE TABLE` (#135)

- **Multi-table UPDATE** — `UPDATE ... JOIN ... SET` syntax support via `CubridSQLCompiler` (#137)

- **FULL OUTER JOIN / LATERAL rejection** — raises `CompileError` for unsupported join types instead of generating invalid SQL (#138)

- **`get_check_constraints()`** — returns empty list with documentation that CUBRID parses but ignores CHECK constraints (#139)

- **Alembic `alter_column` guardrails** — `CubridImpl.alter_column()` rejects `type_`/`new_column_name` with clear error, allows `nullable`/`server_default` (#136)

- **Reflection fallback logging** — silent errors in dialect.py now logged (#127)

### Changed

- **Status: Beta** — README, classifiers, and documentation now consistently use Beta messaging; removed "stable", "production-ready", "frozen" language

- **pycubrid (sync) compatibility** — now requires `>=1.2.0` for full feature parity (documented requirement; the package metadata pin was raised to `>=1.2.0,<2.0` in 1.4.0, #143)

- **Compiler DML helper extraction** — cleaner `visit_on_duplicate_key_update`/`visit_merge` (#133)

### Fixed

- **`has_index()` bug** — now filters by `class_of.class_name` to avoid cross-table false positives

- **`reset_isolation_level()`** — uses canonical isolation level name instead of alias

- **`get_isolation_level()` fallback** — returns canonical `"READ COMMITTED"` instead of driver-specific alias (#140)

### Documentation

- **README consolidation** — authoritative support contract with async status and known limitations (#128)

- **ARCHITECTURE.md / DEVELOPMENT.md refresh** — updated to reflect current module structure (#129)

- **Reflection diagnostic guide** — troubleshooting for Alembic autogenerate issues (#131)

- **SA_COMPAT.md** — documents SQLAlchemy private API dependencies and 2.2 readiness plan (#132)

### CI

- **Distribution smoke test** — CI validates sdist/wheel build (#122)

- **Release consistency CI** — automated tag/version/changelog alignment checks (#124)

- **Async integration tests in CI** — promoted from optional to regular (#130)

### Tests

- **Entry point verification test** — importlib.metadata check for dialect registration (#123)

- **SHOW CREATE TABLE golden tests** — parsing fixture corpus for DDL reflection (#125)

- **Alembic autogenerate regression tests** — false-positive diff detection (#126)

- **CUBRID version-specific reflection snapshots** — DDL output tests across versions (#134)

## [1.2.3] - 2026-04-19

This corrective release ships the 1.2.2 changes that the PyPI 1.2.2 artifact is missing. Install 1.2.3 or later instead of 1.2.2.

### Fixed

- **Corrected 1.2.2 artifact** — the `v1.2.2` tag points to the #120 merge (`6c956da`), but the PyPI 1.2.2 artifact was built from an older commit (pre-async-dialect, pre-#120 fix), so it shipped without the #120 fix and without the `cubrid.pycubrid` and `cubrid.aiopycubrid` entry points. PyPI 1.2.2 is not yanked; install 1.2.3 or later.

- The `v1.2.3` tag (`c46833f`) is the `v1.2.2` tag commit plus the version bump only, so 1.2.3 ships exactly the fixes listed under [1.2.2] below.

## [1.2.2] - 2026-04-19

The intended source changes fix Alembic autogenerate reflection, but the published PyPI 1.2.2 artifact was built from an older commit: it lacks the #120 fix and the `cubrid.pycubrid` / `cubrid.aiopycubrid` entry points. **Install 1.2.3 instead.**

### Fixed

- **Alembic autogenerate false-positive diffs** (#120; [PR #121](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/121)) by @yeongseon:
  - `get_indexes()` now filters out the implicit indexes that CUBRID auto-creates
    for every primary-key and foreign-key constraint.  These auto-indexes
    previously caused Alembic to emit spurious `op.drop_index` /
    `op.create_index` operations on every `alembic check` / `revision --autogenerate`
    run.  The dialect now batch-queries `_db_index.is_primary_key` and
    `_db_index.is_foreign_key` (single round trip) and excludes flagged indexes
    from the reflection result.
  - `get_foreign_keys()` rewritten to parse `SHOW CREATE TABLE` output.  The
    previous implementation queried the `db_constraint` view, which is **not**
    queryable in CUBRID 11.x (despite older docs referencing it) and silently
    returned an empty list — leaving Alembic blind to every existing FK and
    causing it to schedule recreation on every run.
  - `get_unique_constraints()` rewritten to parse `SHOW CREATE TABLE` output
    for the same reason as `get_foreign_keys()`.

- **`compare_type` for unbounded VARCHAR**: `CubridImpl.compare_type()` now treats CUBRID's `VARCHAR(1073741823)` (the physical storage for `STRING`, `CLOB`, `TEXT`, and `String` without a length) as equivalent to SQLAlchemy's `Text()`, `CLOB()`, and `String()` (no length), eliminating false-positive type-change diffs in Alembic autogenerate by @yeongseon.

## [1.2.1] - 2026-04-19

This patch fixes asynchronous engine creation and JSON column inserts, and expands async integration coverage.

### Fixed

- **Async dialect**: Add missing `get_pool_class()` override returning `AsyncAdaptedQueuePool` — `create_async_engine()` now works correctly (#116) by @yeongseon

- **JSON serialization**: Initialize `_json_serializer` / `_json_deserializer` attributes in `CubridDialect.__init__()` — ORM `JSON` column inserts no longer raise `AttributeError` (#117) by @yeongseon

### Documentation

- Async usage sample (`samples/async_basic.py`) by @yeongseon

### Tests

- 16 async E2E integration tests (`test/test_aio_integration.py`) by @yeongseon

## [1.2.0] - 2026-04-18

This release adds JSON columns, JSON path expressions, and typed JSON access for CUBRID 10.2 and newer.

### Added

- **JSON type support** (CUBRID 10.2+, PR #115) by @yeongseon
  - `JSON` type class subclassing `sqltypes.JSON`
  - `JSONIndexType` and `JSONPathType` for path expression formatting
    (with embedded-quote escaping per CUBRID JSON path grammar: `"` → `""`)
  - `visit_JSON` type compiler emitting `JSON` DDL
  - JSON path expressions via `JSON_EXTRACT` (`col["key"]`, `col[("a", "b")]`, multi-level paths with indices such as `col[("a", 1, "b")]`); for example `select(Document.payload["meta", "author"].as_string())`
  - Typed access via `as_boolean`, `as_integer`, `as_numeric`, `as_float`, `as_string`
    using CASE / CAST / `JSON_UNQUOTE` as appropriate
  - JSON null → SQL NULL handling with CASE expressions for typed access
  - `colspecs` mapping: generic `sa.JSON` → dialect `JSON`
  - `ischema_names` mapping: `"JSON"` → `JSON` for reflection
  - 47 offline tests (`test/test_json.py`)

### Fixed

- Version consistency: synchronized `__version__` in `sqlalchemy_cubrid/__init__.py` with `pyproject.toml` (was 1.0.0 vs 1.1.0)

- Removed unused imports flagged by `ruff` in `aio_pycubrid_dialect.py` and `test/test_aio_pycubrid_dialect.py`

- CI: switched the version-consistency check to `ast.parse` so it no longer requires installing runtime dependencies just to read `__version__`

- `test_integration.py`: hoisted `Mapped`/`mapped_column` imports to module scope (function-local imports broke SQLAlchemy's annotation resolution under the `insertmanyvalues` test)

### Tests

- All 500 offline tests pass (47 new for JSON); all 8 integration matrix combinations pass (Python 3.10/3.12 × CUBRID 10.2/11.0/11.2/11.4); project coverage 98.61%, `types.py` 99%.

## [1.1.0] - 2026-04-18

This release introduces the asynchronous pycubrid dialect through the `cubrid+aiopycubrid://` connection URL.

### Upgrade notes

- **Requirements for the async dialect** — pycubrid >= 1.1.0 (with the `pycubrid.aio` module) and SQLAlchemy 2.0–2.1. The pycubrid version is the documented requirement; the `[pycubrid]` extra metadata at this tag still allows `pycubrid>=1.0,<2.0`.

- **Usage** — `create_async_engine("cubrid+aiopycubrid://dba:password@localhost:33000/demodb")` with `AsyncSession` for native asyncio.

### Added

- **Async dialect** via `cubrid+aiopycubrid://` URL scheme
  - `PyCubridAsyncDialect` (`is_async=True`) using SQLAlchemy's `AsyncAdapt_dbapi_*` base classes
  - `AsyncAdapt_pycubrid_dbapi` wraps `pycubrid.aio` module
  - `AsyncAdapt_pycubrid_connection` bridges autocommit via greenlet `await_only`
  - `AsyncAdapt_pycubrid_cursor` with full async cursor adaptation
  - `cubrid.aiopycubrid` entry point auto-discovered by SQLAlchemy

- 17 new async dialect offline tests (`test/test_aio_pycubrid_dialect.py`)

## [1.0.0] - 2026-04-11

This release establishes the 1.x compatibility contract and documents the supported Python, CUBRID, SQLAlchemy, and Alembic versions alongside known limitations.

### Upgrade notes

- **Compatibility Policy** — This release establishes the 1.x compatibility contract: the public API follows semantic versioning, and breaking changes will only occur in major version bumps (2.0+).

- **Supported Environments**
  - **Python**: 3.10, 3.11, 3.12, 3.13, 3.14
  - **CUBRID**: 10.2, 11.0, 11.2, 11.4
  - **SQLAlchemy**: 2.0–2.1 (`>=2.0,<2.2`)
  - **Alembic**: >=1.7

- **Known Limitations**
  - `RETURNING` clauses not supported (CUBRID limitation)
  - No `Sequence` support (CUBRID uses `AUTO_INCREMENT`)
  - Native `BOOLEAN` not available (mapped to `SMALLINT`)
  - Lateral joins and writable CTEs not supported
  - `RELEASE SAVEPOINT` is a no-op

> **Later update, not part of v1.0.0:** the 1.x compatibility policy above was revised after this release by [#1115](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1115); the current policy is in [RELEASING.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/RELEASING.md#public-api-compatibility-in-1x).

### Added

- Full type annotations across all 8 source modules (mypy errors: 280 → 0)

- Compatibility Matrix in README (Python, CUBRID, SQLAlchemy, Alembic versions)

### Changed

- Development Status classifier updated from "Beta" to "Production/Stable"

- pycubrid optional dependency updated from `>=0.6.0` to `>=1.0,<2.0`

- All documentation updated to explicitly state "SQLAlchemy 2.0–2.1" support

- Version bumped to 1.0.0

### Fixed

- `visit_join` signature: added missing `from_linter` parameter to match SQLAlchemy base class

- `sqlalchemy.sql.util.warn`: replaced with correct `sqlalchemy.util.warn` API

## [0.8.0] - 2026-04-04

This stabilization release documents the supported environments and compatibility boundaries ahead of 1.0, including the minimum optional pycubrid driver version.

### Upgrade notes

- **1.0 support boundary (summary)** — SQLAlchemy 2.0–2.1 (pinned `<2.2`), Python 3.10–3.14 and CUBRID 10.2–11.4 are supported. DDL, DML, reflection, ORM, Core, Alembic migrations, ODKU/MERGE/REPLACE, window functions and CTEs are supported. JSON type: not yet mapped. Native Enum: not supported (use VARCHAR + CHECK). RETURNING: not supported. BOOLEAN: mapped to SMALLINT. After a soak period on PyPI, the next release is planned as 1.0.

### Added

- `docs/SUPPORT_MATRIX.md`: Comprehensive support matrix documenting SQLAlchemy versions, Python versions, CUBRID versions, driver compatibility, feature support, type mappings, and known limitations — defines the 1.0 support boundary

- Documents private SQLAlchemy API usages that require the `<2.2` version pin

- Clarified public documentation to state SQLAlchemy 2.0–2.1 support explicitly

### Changed

- **pycubrid dependency (historical context)** — the optional `pycubrid>=0.6.0` minimum was already introduced in v0.7.1 ([#72](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/72), [commit c598b07](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c598b0749e84166f45e4f67ef3109d1171605d55)) and remains in force in this release. The driver integration expects `list[tuple]` results from `fetchall()`; do not attribute this return shape to a new behavior introduced by pycubrid v0.6.0.

- Version bumped to 0.8.0 (stabilization release on path to 1.0)

## [0.7.1] - 2026-03-13

This patch fixes UTC timestamp compilation and schema inspection, improves statement compilation caching, and reduces index-reflection overhead.

### Upgrade notes

- **First non-development PyPI release** — the only earlier PyPI uploads are `0.0.1.dev0` and `0.0.1.dev1` (2022). The optional `[pycubrid]` extra requires `pycubrid>=0.6.0` ([#72](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/72), [commit c598b07](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c598b0749e84166f45e4f67ef3109d1171605d55)).

### Changed

- **Package metadata** — Updated PyPI classifiers and the project Changelog link ([#75](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/75), [commit e682336](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/e682336b45)).

- **Version scheme** — Re-versioned the project to 0.x for the pre-1.0 development phase ([commit f6171f1](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f6171f1f3598f14feb804bce9b1fb2097d60436e)).

### Fixed

- **`visit_utc_timestamp_func`** — Compile `func.utc_timestamp()` to `UTC_TIMESTAMP()` instead of `UTC_TIME()`, returning a full datetime value instead of time-only (#53).

- **`get_indexes()`** — Fix PK index filtering: read `is_primary_key` from column 0 of the single-column query result instead of unreachable column 6, excluding primary-key indexes correctly (#54).

- **`has_table()`** — Recognize views as existing objects by accepting `class_type IN ('CLASS', 'VCLASS')` instead of only `'CLASS'` (#55).

### Performance

- **Statement caching** — Enable SQLAlchemy statement caching on `Insert` and `Replace` using `inherit_cache = True`, with cache-key regression coverage ([#70](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/70), [commit 688c415](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/688c415b76)).

- **Index reflection** — Avoid an N+1 primary-key catalog lookup in `get_indexes()` by using a batched query, with regression tests ([#70](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/70)).

- **Column reflection** — Precompile patterns used by `get_columns()` at module level instead of on every invocation ([#70](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/70)).

## [0.7.0] - 2026-03-12

This version adds the `cubrid+pycubrid://` SQLAlchemy dialect for the pure-Python pycubrid DB-API driver, with native last-insert ID handling and regression tests.

### Added

- **pycubrid dialect variant**: New `PyCubridDialect` class (`cubrid+pycubrid://` URL scheme)
  for using the [pycubrid](https://github.com/cubrid-lab/pycubrid) pure Python DB-API 2.0
  driver. Subclasses `CubridDialect` — inherits all SQL compilation, type mapping, and schema
  reflection. Overrides only driver-specific methods: `import_dbapi()`, `create_connect_args()`,
  `on_connect()`, `do_ping()` ([commit 1fd8a1e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1fd8a1e4ef82)) by @yeongseon.

- **`PyCubridExecutionContext`**: Execution context that uses pycubrid's native `cursor.lastrowid`
  (returns `int | None` directly) with SQL `LAST_INSERT_ID()` fallback.

- **`cubrid.pycubrid` entry point**: Registered in `pyproject.toml` so SQLAlchemy auto-discovers
  the pycubrid dialect via `create_engine("cubrid+pycubrid://...")`.

- **`pycubrid` optional dependency**: `pip install "sqlalchemy-cubrid[pycubrid]"` installs pycubrid.

### Documentation

- **Documentation**: Updated `docs/CONNECTION.md` and `README.md` with pycubrid driver information.

### Tests

- **30 new offline tests**: `test/test_pycubrid_dialect.py` covering driver basics, connect args,
  on_connect, do_ping, execution context, entry point registration, isolation levels, and
  misc methods.


## [0.6.0] - 2026-03-12

This version adds CUBRID monetary and object-reference types and strengthens Alembic autogenerate support for collection types.

### Upgrade notes

- **SQLAlchemy 2.1 compatibility (historical status)**: SQLAlchemy 2.1.0b1 existed at the time of this tag, but the tested stable release was SQLAlchemy 2.0.48. All 396 tests passed against 2.0.48; this version did not establish 2.1 compatibility.

- **Async DB-API support (historical status)**: The CUBRID Python driver used with this tag did not expose an async DB-API path, so asynchronous dialect support was not available in v0.6.0. Later releases must be evaluated independently.

### Added

- **`MONETARY` type class**: New `TypeEngine` subclass for CUBRID's monetary data type.
  Stores monetary values with currency — internally represented as DOUBLE with currency code ([commit 9ce99b0](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/9ce99b03eb55)) by @yeongseon.

- **`OBJECT` type class**: New `TypeEngine` subclass for CUBRID's OID reference type.
  Represents a reference to another CUBRID class instance.

- **Alembic autogenerate support**: `CubridImpl` now implements `render_type()` and
  `compare_type()` for CUBRID collection types (SET, MULTISET, SEQUENCE).
  Collection type comparison uses semantic equality (unordered for SET/MULTISET,
  ordered for SEQUENCE). CUBRID type imports are auto-added to migration scripts.

- **`merge()` factory function docstring**: Comprehensive docstring documenting all
  chaining methods (`.using()`, `.on()`, `.when_matched_then_update()`,
  `.when_not_matched_then_insert()`) with usage examples.

- **GitHub issue templates**: Bug report and feature request forms (`.github/ISSUE_TEMPLATE/`).

- **ORM Cookbook**: `docs/ORM_COOKBOOK.md` — practical ORM usage examples with CUBRID-specific
  patterns, collection types, DML extensions, and gotchas.

- **10 new offline tests**: MONETARY/OBJECT type tests (4), Alembic autogenerate tests (6).
  Total: 396 offline tests, 99.45% coverage.

### Changed

- `alembic_impl.py`: Expanded from 69 lines to 141 lines with full autogenerate support.

- `types.py`: Added MONETARY and OBJECT classes (319 → 349 lines).

- `__init__.py`: Exported MONETARY and OBJECT types.


## [0.5.0] - 2026-03-12

This version expands CUBRID-specific SQL support with REPLACE INTO, recursive CTEs, query tracing and additional regression tests.

### Added

- **`REPLACE INTO` statement**: New `Replace` DML construct and `replace()` factory function.
  `replace(table).values(...)` generates `REPLACE INTO table (...) VALUES (...)` syntax.
  Exported from `sqlalchemy_cubrid` top-level package ([commit 650bd49](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/650bd49cf291)) by @yeongseon.

- **ODKU with subquery values**: `on_duplicate_key_update()` now accepts subquery and
  expression values (e.g., `val=(select(func.max(t.c.val)))`).
  Note: CUBRID does not support the `VALUES()` function in ODKU — use literal/subquery values.

- **Recursive CTE support**: Verified `WITH RECURSIVE` works in CUBRID 11.x+.
  SQLAlchemy's base compiler generates correct syntax — 3 offline tests added.

- **Query trace utility**: New `trace_query(connection, statement)` function in `trace.py`.
  Uses CUBRID's `SET TRACE ON` / `SHOW TRACE` mechanism instead of standard `EXPLAIN`.
  Exported from `sqlalchemy_cubrid` top-level package.

- **Integration tests**: `REPLACE INTO`, recursive CTE, and `trace_query()` integration
  tests against live CUBRID Docker instance.

- **21 new offline tests**: `TestReplaceCompilation` (7), `TestRecursiveCTECompilation` (3),
  ODKU subquery tests (2), `test_trace.py` (7), ODKU expression test (1), ODKU literal test (1).

### Documentation

- `docs/FEATURE_SUPPORT.md`: Added recursive CTE, lateral joins, full-text search, query trace,
  and REPLACE INTO rows. Updated Known Limitations & Roadmap section.

- `docs/DML_EXTENSIONS.md`: Added REPLACE INTO, ODKU subquery values, and Query Trace sections.

- **Lateral joins (tag-time observation)**: `LATERAL` subqueries produced a syntax error on tested CUBRID 11.2; this describes the v0.5.0-era test, not a blanket claim about later server versions.

- **Full-text search (tag-time scope)**: This dialect did not support MySQL-style `MATCH … AGAINST` syntax or full-text indexes in the tested environment. Do not infer modern server support from this historical note.


## [0.4.0] - 2026-03-12

This version improves connection recovery and pool health checks while documenting the tested driver compatibility boundaries.

### Added

- **Error code mapping**: `is_disconnect()` detects dropped connections via string-based message
  matching (14 patterns) and numeric CUBRID CCI error codes (-21003, -21005, -10005, -10007) ([commit abeb09e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/abeb09e39f3e)) by @yeongseon.

- **`_extract_error_code()`**: Extracts numeric error codes from CUBRID DBAPI exceptions
  (supports both integer args and string-embedded codes like "-21003 message").

- **`do_ping()`**: Connection liveness check using CUBRID Python driver's native `ping()`
  method — enables SQLAlchemy's `pool_pre_ping` feature.

### Documentation

- **Connection pool tuning guide**: `docs/CONNECTION.md` expanded with pool configuration
  recommendations (`pool_size`, `pool_recycle`, `pool_pre_ping`), CUBRID broker timeout
  interaction, disconnect detection, and error code mapping documentation.

- **CUBRID-Python driver compatibility matrix**: `docs/DRIVER_COMPAT.md` documenting tested
  driver versions, CUBRID server compatibility, and known issues.

### CI

- **Python 3.14 and CUBRID compatibility CI**: Python 3.14 was added to the package classifiers in `pyproject.toml`, and integration CI expanded to Python {3.10, 3.12, 3.14} × CUBRID {11.4, 11.2, 11.0, 10.2}. These are tag-time CI and packaging changes, not a claim about every later driver/server combination.

### Tests

- **44 new offline tests**: Comprehensive coverage for `is_disconnect()` (14 message patterns,
  4 error codes, edge cases), `_extract_error_code()` (7 tests), `do_ping()` (2 tests),
  `postfetch_lastrowid` validation (5 tests), and disconnect message integrity (3 tests).


## [0.3.2] - 2026-03-12

This documentation-only version reorganizes connection, type, migration, DML and development guides into dedicated reference files.

### Added

- `docs/CONNECTION.md`: Connection guide — URL format, driver setup, troubleshooting ([commit 475d9d2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/475d9d27a500)) by @yeongseon.

- `docs/TYPES.md`: Type mapping reference — standard types, CUBRID-specific types, collection types, boolean handling.

- `docs/ISOLATION_LEVELS.md`: Isolation level guide — all 6 CUBRID levels, dual-granularity model, configuration.

- `docs/DML_EXTENSIONS.md`: DML extensions reference — ON DUPLICATE KEY UPDATE, MERGE, GROUP_CONCAT, TRUNCATE, FOR UPDATE, index hints.

- `docs/ALEMBIC.md`: Alembic migration guide — setup, configuration, limitations, batch workarounds.

- `docs/DEVELOPMENT.md`: Development guide — setup, testing, Docker, coverage, CI/CD pipeline.

### Documentation

- `README.md`: Rewritten as a concise landing page (~80 lines); all detailed content moved to `docs/` files.

- `docs/source/index.rst`: Added links to all new documentation files.

- `docs/FEATURE_SUPPORT.md`: Updated version reference from v0.3.0 to v0.3.2.


## [0.3.1] - 2026-03-12

This maintenance version updates documentation and samples, fixes CI references and removes packaging files superseded by pyproject.toml.

### Changed

- `samples/create_engine.py`: Modernized to SA 2.0 API (`text()`, context manager).

- `samples/cubrid_datatypes.py`: Modernized to SA 2.0 API (`metadata.create_all`, CUBRID types).

- `samples/env.sample`: Replaced hardcoded external IP with `localhost`.

### Removed

- Removed outdated packaging files superseded by `pyproject.toml`: `setup.py`, `setup.cfg`, `CHANGES.rst`, `requirements.txt`, `requirements-dev.txt`, `install_cubrid_python.sh`.

- Removed duplicate `pre-commit.yml` GitHub Actions workflow (functionality covered by `ci.yml`).

### Fixed

- README: Fixed lint badge referencing deleted `pre-commit.yml` workflow — now points to `ci.yml` ([commit 833e514](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/833e514f5fbc)) by @yeongseon.

### Documentation

- `SECURITY.md`: Under the **former 1.x numbering scheme** present at this tag, the security-policy table listed `1.1.x` and `1.2.x` as supported; these values are preserved as recorded, not converted to the later `v0.3.1` tag scheme.

- `docs/source/index.rst`: Replaced Sphinx quickstart boilerplate with proper project documentation.

- `docs/source/conf.py`: Set the Sphinx `release` value to **`1.2.1`** (former version numbering), and added `viewcode` and `intersphinx` extensions; the historical setting is not the `v0.3.1` Git tag.

- `docs/source/sqlalchemy_cubrid.rst`: Added `dml` and `alembic_impl` module autodoc sections.


## [0.3.0] - 2026-03-12

This version adds Alembic migration integration for CUBRID and expands **offline** dialect testing. The 99% coverage figure describes these tests, not proof of compatibility with every live database version.

### Added

- Alembic migration support via `CubridImpl` (`alembic.ddl` entry-point).
  Install with `pip install sqlalchemy-cubrid[alembic]` ([commit 0f223e9](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/0f223e95b)) by @yeongseon.

- `test/test_alembic.py`: 8 tests covering import, registry, entry-point, and import-error scenarios.

### Documentation

- `docs/FEATURE_SUPPORT.md`: Alembic row updated from ❌ to ✅.

### Tests

- Edge-case tests added for compiler.py, dml.py, and dialect.py — coverage raised from 97% to 99% (306 → 314 tests).


## [0.2.0] - 2026-03-12

This version adds SQLAlchemy compilation for CUBRID-specific DML and DDL, window functions and schema comments. Dialect-specific INSERT and MERGE operations use the documented `sqlalchemy_cubrid` helpers.

### Added

- `FOR UPDATE` clause support (`SELECT … FOR UPDATE [OF col1, col2]`) ([commit 1f9f59a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1f9f59aa5)) by @yeongseon.

- `INSERT … DEFAULT VALUES` and empty INSERT support.

- Window functions (`ROW_NUMBER`, `RANK`, `DENSE_RANK`, `NTILE`, `LAG`, `LEAD`, etc.) with `OVER()` clause.

- `NULLS FIRST` / `NULLS LAST` ordering in ORDER BY.

- Table and column `COMMENT` support — inline DDL, `ALTER` statements, and schema reflection.

- `IF NOT EXISTS` / `IF EXISTS` DDL support for `CREATE TABLE` and `DROP TABLE`.

- `ON DUPLICATE KEY UPDATE` via CUBRID-specific `sqlalchemy_cubrid.insert()` construct (MySQL-compatible syntax).

- `MERGE` statement via `sqlalchemy_cubrid.merge()` with full `WHEN MATCHED` / `WHEN NOT MATCHED` clause support.

- `GROUP_CONCAT` aggregate function compilation.

- `TRUNCATE TABLE` autocommit detection.

### Documentation

- Index hint documentation (`USING INDEX`, `USE INDEX`, `FORCE INDEX`, `IGNORE INDEX` via SQLAlchemy’s built-in `with_hint()` / `suffix_with()`).

- `docs/FEATURE_SUPPORT.md`: Comprehensive feature support matrix updated with all new capabilities.


## [0.1.0] - 2026-03-12

This initial SQLAlchemy 2.0 rewrite updates dialect APIs, SQL compilation, reflection, transactions and test coverage. **Before upgrading**, review the Python and SQLAlchemy minimum-version changes below.

### Upgrade notes

- **BREAKING**: Minimum Python version raised from 3.6 to 3.10 ([commit 00eccac](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/00eccac300e8)) by @yeongseon.

- **BREAKING**: Minimum SQLAlchemy version raised from 1.3 to 2.0.

### Added

- `dialect.py`: `import_dbapi()` classmethod (SA 2.0 API).

- `dialect.py`: `supports_statement_cache = True` for SA 2.0 query caching.

- `dialect.py`: `supports_comments`, `supports_is_distinct_from`, `insert_returning`, `update_returning`, `delete_returning` flags.

- `dialect.py`: `get_schema_names()`, `get_table_comment()`, `get_check_constraints()`, `has_sequence()` methods.

- `dialect.py`: `get_unique_constraints()` now queries `db_constraint` system table.

- `dialect.py`: `get_isolation_level_values()` method (SA 2.0 API).

- `dialect.py`: `do_release_savepoint()` no-op override — CUBRID does not support `RELEASE SAVEPOINT`.

- `compiler.py`: `CubridDDLCompiler.get_column_specification()` for proper `AUTO_INCREMENT` DDL emission.

- `requirements.py`: Comprehensive SA 2.0 test requirement flags (40+ properties), including binary, LOB, identifier quoting, and FOR UPDATE skip markers.

- `test/test_compiler.py`: 70 offline SQL compilation tests.

- `test/test_types.py`: 48 offline type system tests.

- `test/test_requirements.py`: 46 parametrized requirement flag tests.

- `test/test_dialect_offline.py`: 24 offline dialect tests (reflection, connection, isolation, savepoint).

- `test/test_base.py`: 15 base module tests.

- `test/test_integration.py`: 20 integration tests against live CUBRID Docker instances.

- `.github/workflows/ci.yml`: Full CI/CD pipeline with Python × CUBRID version matrix.

- `CHANGELOG.md`: This file.

- `docs/PRD.md`: Product requirements document.

- `docs/FEATURE_SUPPORT.md`: Feature-by-feature comparison with MySQL, PostgreSQL, and SQLite.

### Changed

- Complete rewrite of all dialect modules for SQLAlchemy 2.0 compatibility.

- Modernized project infrastructure (`pyproject.toml`, ruff linting, GitHub Actions CI).

### Removed

- `.pre-commit-config.yaml`: Replaced by ruff configuration in `pyproject.toml`.

### Fixed

- `compiler.py`: Fixed `visit_cast` missing space before `AS` keyword (`CAST(exprAS type)` → `CAST(expr AS type)`).

- `compiler.py`: Fixed `visit_CHAR` missing closing parenthesis.

- `compiler.py`: Fixed `visit_list` using Python 2 `basestring` — crashes on Python 3.

- `compiler.py`: Fixed `limit_clause` using `sql.literal()` without importing `sql` module.

- `compiler.py`: Fixed `limit_clause` for SA 2.0 (`_limit_clause` / `_offset_clause` are now ClauseElements).

- `types.py`: Fixed `REAL.__init__` calling `super(FLOAT, self)` instead of `super(REAL, self)`.

- `types.py`: Fixed `_StringType.__repr__` using `inspect.getargspec` removed in Python 3.11+.

- `dialect.py`: Fixed `get_pk_constraint` using string literal instead of f-string and missing `text()`.

- `dialect.py`: Fixed `get_indexes` shadowing outer `result` variable inside loop.

- `dialect.py`: Fixed `has_table` SQL injection via f-string interpolation — now uses parameterized query.

- `dialect.py`: Fixed `get_foreign_keys` empty stub — now queries `db_constraint` system table.

- `dialect.py`: Fixed `postfetch_lastrowid = False` → `True` so SA can retrieve auto-generated keys.

- `dialect.py`: Fixed CUBRID driver defaulting to `autocommit=True` — `on_connect()` now calls `conn.set_autocommit(False)`.

- `dialect.py`: Removed unused `from cmd import IDENTCHARS` import.

- `base.py`: Implemented `CubridExecutionContext.get_lastrowid()` using `conn.get_last_insert_id()` with `SELECT LAST_INSERT_ID()` fallback.

- All files: Modernized `super(ClassName, self).__init__()` to `super().__init__()`.


## [0.0.1] - 2022-01-01

### Added
- Initial release with basic CUBRID dialect for SQLAlchemy 1.3.
