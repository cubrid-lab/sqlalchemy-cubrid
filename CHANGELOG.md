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

### Upgrade notes

- **1.x dialect-extension API policy clarified (#892)** — the dialect can
  consider individually reviewed, low-impact changes to project-specific
  convenience APIs in a later MINOR without waiting for 2.0. This is
  prospective and requires a documented user-impact assessment and migration
  instructions; it does **not** permit breaking SQLAlchemy Core/ORM behavior,
  generated SQL, data correctness, reflection or migrations. Already published
  API-specific promises still require an explicit revised notice in a
  published release before removal. In particular, the deprecated
  `SMALLINT`/`BIGINT` `display_width` and string-type `values` arguments
  **continue to work with warnings in this change**; #892's actual removal,
  including positional calls such as `SMALLINT(11)`, is a separate decision.
  **This release revises the actual `DeprecationWarning` text** from "future
  major" to "may be removed in a future 1.x MINOR". The ignored arguments
  remain accepted in this release. Migrate `SMALLINT(display_width=11)` /
  `SMALLINT(11)` to `SMALLINT()`, `BIGINT(20)` to `BIGINT()`, and
  `VARCHAR(30, values=["x"])` to `VARCHAR(30)`. Removing ignored arguments
  changes no generated CUBRID DDL. Applications using a `<2.0` dependency
  range may automatically pick up a breaking MINOR once the revised notice has been published and removal is approved;
  pin the specific version range or migrate ahead of removal.

### Changed

- The `Could not import CUBRIDdb` error raised for `cubrid://` and
  `cubrid+cubriddb://` URLs no longer calls the CUBRIDdb C-extension driver
  legacy or the PyPI `CUBRID-Python` releases untested. It now lists both
  installation paths (`sqlalchemy-cubrid[cubriddb]` or an official
  CUBRID/cubrid-python source build) and the pure-Python
  `cubrid+pycubrid://` alternative. The message prefix and the chained
  original `ImportError` are unchanged.

## [1.12.2] - 2026-11-05

This release improves documentation, examples, and contribution guidance. Runtime behavior is unchanged.

### Changed

- **Contribution guidance** — Clarified evidence-based issue triage and self-explanatory comments, including guidance for agents ([#1060](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1060), [#1103](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1103)) by @yeongseon.

### Documentation

- **Brand icons** — Updated the README, translations, documentation logo, and favicon to the transparent ORM icon at brand revision `e55990a`, with transparent gaps rather than white strokes ([#1089](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1089), [#1090](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1090)) by @yeongseon.
- **Documentation theme** — Aligned the documentation site's Python Yellow theme with shared brand tokens ([#1093](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1093)) by @yeongseon.
- **FAQ and troubleshooting** — Clarified the names used in help text and diagnostic examples ([#1105](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1105)) by @AzalHoseinian (first contribution 🎉).
- **Async sample** — Corrected the installation command and Docker guidance ([#1092](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1092)) by @bfs2021 (first contribution 🎉).

## [1.12.1] - 2026-10-27

This maintenance release improves documentation branding, contributor guidance, and test reliability. **There are no runtime behavior changes.**

### Documentation

- **Updated documentation branding** — the README, its five translations, and the documentation site's logo and favicon now use the revised Python Yellow ORM icon. The updates progressively aligned the icon with the cube-shaped organization emblem and white role markings. These are documentation asset changes only ([#1050](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1050), [#1054](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1054), [#1063](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1063), [#1066](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1066)).
- **Clarified contributor communication guidance** — added guidance encouraging clear, human-readable communication from coding agents ([#1056](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1056), [commit 74afeb3](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/74afeb36fe5cba4503b2b860dafdd0b19903af7b)).

### CI

- **Run pycubrid-dependent tests in CI** — the `repo-tests` job now installs the `[pycubrid]` extra, preventing benchmark-script tests from being skipped solely because the dependency is absent. Optional-import guards remain for minimal installations ([#1049](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1049)).

### Tests

- **Prevent resource warnings from interrupted-query tests** — the KILL QUERY test helper now closes its stdout/stderr pipes and clears leftover garbage before warning collection, preventing unrelated failures in the cubriddb compatibility lane ([#1061](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1061)).

Branding change history: [#1051](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1051) ([7159590](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/715959028dcab9915eaab7478dca2228bc0345a5)), [#1055](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1055) ([f166be7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f166be7df70599af34bd353110075f9b092ee327)), [#1064](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1064) ([c5fd64d](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c5fd64d8d64ff8d31edd4db292ebb47dd8c6f250)), and [#1067](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1067) ([e1ae6a4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/e1ae6a4d1bc1d91bbb7028b07d344499b6997179)).


## [1.12.0] - 2026-10-25

This release improves the reliability and reporting of the development verification workflow. It changes developer commands and test reporting, not the dialect's runtime API.

### Upgrade notes

- **`make verify` now runs the live integration lane (#1018, [#1045](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1045))** — it runs `make check`, the
  complete offline `make test` and then the run-owned `make integration` lane (default
  `INTEGRATION_DRIVER=pycubrid`), so it needs Docker and takes as long as the live suite. It
  fails when CUBRID never becomes ready or every live test skips, and it starts the live lane
  only after the offline suite passed, also under `make -j`. `make test` stays offline; run
  `make check test` for the former offline-only `make verify`. The deprecated `CUBRID_PORT`
  fallback is unchanged. `make install` now also installs the `[pycubrid]` extra, so the live
  lane can connect right after it. Development tooling only; the dialect API is unchanged.

### Added

- **`make verify` writes `test-results/verify/` (#1020, [#1047](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1047))** — after its phases, also after a
  failure, `make verify` writes `summary.json` with the overall `PASS`/`FAIL`/`INCOMPLETE` status
  and one entry per phase (`check`, `test`, `integration`). A phase that never started is
  `NOT_RUN`, and a missing or unreadable lane summary or an all-skipped live lane is never
  `PASS`. It also copies each lane's JUnit file to `junit/` and the live lane's redacted
  `environment.json`, with configured passwords masked, and a file it cannot copy keeps the
  summary from `PASS`. The new `scripts/run_verify.py` runs the phases and forwards a SIGINT,
  SIGTERM or SIGHUP sent to make to the running phase, so `make integration` still cleans up.
  The new `scripts/report_test_results.py aggregate` subcommand builds the summary, and
  `step-summary` renders it. `make verify` now clears `test-results/test/` and
  `test-results/integration/` before it starts; `make -n verify` writes nothing.

### CI

- **The `make integration` CI jobs publish the live results summary (#1021)** — `make-integration`
  in `ci.yml` and `integration-full.yml` append `test-results/integration/summary.json` to the job
  summary with `if: always()`, so a failing or incomplete live lane shows its status and counts
  next to the uploaded `pytest-logs-*` artifact. No permission, secret or test-selection change.
- **Every new issue starts in `status: needs triage` (#1028)** — the issue forms add the
  label, `issue-triage.yml` adds it to every opened issue instead of only to issues with
  incomplete titles or labels, and the upstream canary adds it to the issues it files. The
  unused `scripts/check_issue_metadata.py` check is removed. Priority and size are still set
  by a maintainer, who removes the label after triage.

## [1.11.7] - 2026-10-25

### Documentation

- **Simplified the agent commit-message example** — removed the agent-specific and tool-specific footer guidance from the repository's commit example. This is a documentation-only update; it does not change the dialect or runtime behavior ([#1043](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1043), [commit b51b29f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b51b29fa793d12d4ec54d9ef65adb3c43cd2ae5f)).

## [1.11.6] - 2026-10-24

### Documentation

- **Corrected an outdated pytest test reference** — updated the development documentation so its example points to a current test rather than a stale pytest node. This is a documentation-only update; it does not change runtime behavior ([#1034](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1034), [#1033](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1033), [commit 003dca4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/003dca4d9bf79aeb1d67814c5fa8e92824216405)).

## [1.11.5] - 2026-10-24

This release consolidates changes from versions 1.11.1 to 1.11.4, which were not published. Review the upgrade notes first; the detailed sections below retain the complete changes and references.

### Upgrade notes

- **Unpublished versions 1.11.1 to 1.11.4 (#838, #910, #1005, #1011)** — 1.11.1, 1.11.2, 1.11.3 and 1.11.4 were never published because their release gates failed (1.11.1 on Python 3.15, 1.11.2 in the CUBRIDdb integration lanes, #1003, 1.11.3 in the cookbook candidate verification, 1.11.4 in the `make integration` lanes, #1035), so none of them has a tag, GitHub Release or PyPI version; upgrade from 1.11.0 directly to 1.11.5, which contains every 1.11.1 to 1.11.4 change.
- **Makefile test and lint targets updated (#1009)** — `make test` now runs every offline test (the former `make test-offline`, covering fast and repository-tooling tests), while the former fast lane is `make test-fast`; `make lint` runs `ruff check` only, while `make format-check` (or `make check`) checks formatting; `make check` is now the complete non-test quality gate (lint, format-check, typecheck, security, check-docs-reason), and local scripts calling `make check-all` or `make test-offline` continue working through aliases.
- **Docker test data retention and broker binding (#1008)** — `make docker-down` now preserves local test data volumes (running `docker compose down`), while the new `make docker-clean` deletes them (running `docker compose down -v`); scripts relying on starting from an empty database must call `make docker-clean`. `docker-compose.yml` publishes the broker as `127.0.0.1:${CUBRID_TEST_PORT}:33000` so it is no longer reachable from external hosts; `CUBRID_TEST_PORT` (default 33000) overrides the host port for `make docker-up`, `docker compose up` and `make integration`, while `make integration` still creates and removes its own run-owned project.
- **Foreign table column keys in MERGE raise CompileError (#847)** — a MERGE assignment key that is a column of another table now raises `CompileError`, also when the target has a column of the same name, replacing former silent resolution to the target column; use the target's column (`target.c.name`) or the string `"name"`, while the column-list shorthand `when_not_matched_then_insert([source.c.id, ...])` remains unchanged.

### Added

- **Machine-readable offline test results (#1019)** — `make test` writes `junit.xml`, `coverage.xml` and `summary.json` under `test-results/test/` via `scripts/report_test_results.py` with exit status reflecting suite status.
- **Machine-readable integration test results (#1020)** — `make integration` writes `junit.xml`, `summary.json`, `environment.json` and on failure `service.log` under `test-results/integration/` with credential masking and status tracking.

### Changed

- **Makefile targets and integration execution (#1009)** — Makefile targets now have single responsibilities, `make integration` delegates to `scripts/run_integration.py` for driver validation, startup, readiness and cleanup, uncooperative Docker groups are terminated after `INTEGRATION_STOP_GRACE`, and new targets `test-fast`, `format-check` and `verify` are added.
- **MERGE assignment keys require target lineage (#847, [#895](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/895))** — bound column keys in `when_matched_then_update()` and `when_not_matched_then_insert()` must have lineage to the target table or its alias, raising `CompileError` for foreign table columns, while string keys, unbound `sa.column()` keys and column-list shorthands continue resolving by name.

### Deprecated

- **`make check-all` (#1009)** — deprecated alias of `make check` that prints a deprecation notice on stderr and will be removed after the next minor release, while `make test-offline` remains an alias of `make test`.
- **`CUBRID_PORT` (#1008)** — deprecated in favor of `CUBRID_TEST_PORT`; still read when `CUBRID_TEST_PORT` is unset by `make docker-up`, `make integration` (which print a deprecation warning) and `docker-compose.yml`, while `CUBRID_TEST_PORT` takes precedence when both are set.
- **Unused `display_width` and `values` type arguments (#870)** — passing `display_width` to `SMALLINT` / `BIGINT` or `values` to `CHAR` / `VARCHAR` / `NCHAR` / `NVARCHAR` / `STRING` now emits a `DeprecationWarning` and will be removed in a future major release; neither argument affected DDL or runtime behavior, and private helper `CubridTypeCompiler._get` is removed.

### Fixed

- **aggregate_order_by() error on filtered GROUP_CONCAT (#995)** — on SQLAlchemy 2.1, `aggregate_order_by()` on `func.group_concat().filter()` now explicitly raises `CompileError` stating CUBRID lacks a `FILTER (WHERE ...)` clause instead of claiming the call was not a `GROUP_CONCAT`.
- **aggregate_order_by() retains ORDER BY clause (#991, [#994](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/994))** — on SQLAlchemy 2.1, `func.group_concat(col).aggregate_order_by(...)` renders `GROUP_CONCAT(col ORDER BY ...)`, including with `DISTINCT` and in `HAVING`, while calls on unsupported aggregates raise `CompileError`.
- **GROUP_CONCAT with modifiers and boolean expressions (#990, #984)** — `GROUP_CONCAT` no longer wraps arguments in extra parentheses that CUBRID rejects (-493), allowing `DISTINCT`, `ORDER BY`, `SEPARATOR` literal columns and boolean arguments to execute correctly.
- **EXISTS and AND/OR as simple CASE value operand (#987, [#988](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/988))** — the `value=` operand of simple `case()` is grouped inside parentheses when given boolean expressions such as `and_()`, `or_()`, `not_()` or `exists()`, preventing syntax errors on CUBRID.
- **EXISTS and AND/OR as CASE THEN or ELSE results (#982, [#985](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/985))** — boolean expressions used as `THEN` or `ELSE` results in searched or simple `case()` constructs are grouped inside parentheses, preventing syntax errors on CUBRID.
- **EXISTS and AND/OR in CAST, functions and window clauses (#970, [#972](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/972))** — boolean expressions are grouped when passed as arguments to `cast()`, SQL functions in any position, or window and `WITHIN GROUP` `ORDER BY` and `PARTITION BY` clauses.
- **EXISTS and AND/OR in SELECT columns, CAST and ORDER BY (#968, [#969](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/969))** — boolean expressions and `exists()` constructs inside CAST, functions or `order_by()` are grouped to prevent syntax errors (-493) on CUBRID.
- **EXISTS and AND/OR in SELECT list (#966, [#967](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/967))** — boolean expressions and `exists()` queries selected directly as columns or labeled elements are grouped in parentheses, preventing syntax errors (-493) in queries and ORM `session.query(q.exists()).scalar()` calls.
- **Isolation level re-application persistence (#937, [#947](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/947))** — when restoring an isolation level fails at transaction begin on `cubrid+pycubrid://` and `cubrid+aiopycubrid://`, the pending mark is retained so subsequent begin calls retry and raise until restoration succeeds.
- **Disconnection classification for overlapping server error codes (#916, [#938](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/938))** — with pycubrid 1.13's `error_source == "server"`, `is_disconnect()` distinguishes server error codes (-1000 to -1200) from legacy CAS disconnect codes, preventing false connection invalidation on non-disconnect server errors.
- **Boolean JSON path indices rejected (#914, [#917](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/917))** — boolean JSON path components now raise `TypeError` (reported as `StatementError` on execution or `CompileError` under `literal_binds`) instead of rendering invalid paths like `$[True]` that CUBRID rejects (-494).
- **CTE placement in INSERT and REPLACE FROM SELECT (#897, [#899](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/899))** — the dialect now sets `cte_follows_insert` so that CTEs render after the column list (`INSERT INTO t (...) WITH ... SELECT ...`), matching CUBRID's accepted syntax instead of raising -493.
- **Unique constraint reflection fails closed on catalog mismatch (#848, [#896](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/896))** — `get_unique_constraints()` now raises `InvalidRequestError` if a unique index listed in `db_index` cannot be resolved in `SHOW INDEXES`, preventing Alembic from proposing redundant constraint creations.
- **Async connection termination on garbage collection (#872, [#894](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/894))** — `cubrid+aiopycubrid://` implements `AsyncAdapt_terminate` on SQLAlchemy 2.0.44+ to synchronously close sockets and retire sessions when pooled connections are garbage-collected.
- **Cacheable ON DUPLICATE KEY UPDATE (#871, [#893](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/893))** — `OnDuplicateClause` now implements `_traverse_internals`, enabling SQL compilation caching for `INSERT ... ON DUPLICATE KEY UPDATE` statements on SQLAlchemy 2.0 and 2.1.
- **Colons in reflected names, collection type classes and join linting (#870, [#891](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/891))** — colons in reflected table names are escaped to avoid bind parameter errors, collection member type classes like `SET(Integer)` are instantiated, and `visit_join` preserves `from_linter` to track cartesian products accurately.
- **Reflection and autogeneration of functional, descending, filtered and prefix indexes (#869, [#885](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/885))** — `get_indexes()` reflects expressions, descending sorting, `cubrid_where` filters and `cubrid_length` prefix lengths from `SHOW INDEXES` and `db_index`, and Alembic autogenerate compares normalized definitions without spurious re-creations; detecting a changed sort order, filter or prefix length needs Alembic 1.12+.
- **Alembic rendering of CUBRID collection member types (#868, [#884](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/884))** — Alembic migrations render dialect-specific collection member types with the `cubrid_types.` prefix instead of `sa.`, preventing `AttributeError` when loading migration files.
- **Select.fetch() renders as LIMIT (#867, [#880](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/880))** — `Select.fetch()` and `.offset().fetch()` render as CUBRID-compatible `LIMIT` clauses, while unsupported `percent=True` and `with_ties=True` options raise `CompileError`.
- **JSON path string escaping (#866, [#879](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/879))** — JSON path keys are encoded using `json.dumps()`, properly escaping quotes, backslashes and non-ASCII characters.
- **Quoted SQL literals for reflected server defaults (#865, [#878](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/878))** — non-numeric server defaults are inspected via `SHOW CREATE TABLE`, reflecting string and date defaults as quoted SQL literals instead of unquoted identifiers.
- **Alembic alter_column compatibility for nullability, defaults and comments (#861, [#877](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/877))** — `alter_column` operations emit CUBRID-compatible `MODIFY` / `CHANGE` and `ALTER COLUMN ... SET DEFAULT NULL` statements instead of generic syntax that CUBRID rejects.
- **Propagation of compile options to CAST, ON DUPLICATE KEY UPDATE and collections (#862, [#875](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/875))** — compiler options including `literal_binds` reach nested operands in `visit_cast`, `ON DUPLICATE KEY UPDATE` values and collection member DDL.
- **Table and view reflection scoped to current owner on CUBRID 11.2+ (#864, [#876](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/876))** — `has_table()`, `get_table_names()` and `get_view_names()` filter on `owner_name = CURRENT_USER` on CUBRID 11.2 and later, preventing duplicate names and false positives from other users' schemas.
- **Reflected timezone types use dialect namespace ([#973](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/973), refs [#882](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/882))** — corrected the namespace of reflected timezone types.

### Security

- **Inline literals follow the server's backslash mode (#863, [#874](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/874))** — the dialect assumed `no_backslash_escapes=yes` unless told otherwise, so on a server with `no_backslash_escapes=no` the value `\' OR 1=1 -- ` rendered with `literal_binds` as `'\'' OR 1=1 -- '` and the compiled SQL matched every row. When `create_engine(no_backslash_escapes=...)` is not passed, the first connection now probes the server with `SELECT CHAR_LENGTH('\\')` and literal rendering doubles backslashes when the server treats them as escapes; an unexpected probe result fails the connection. Native `ENUM` labels now use the same escaping. An explicit option still pins the mode and skips the probe; a dialect that has not connected still assumes the server default.

### Documentation

- **Python 3.15 limitation on garbage-collected connection cleanup (#872, [#909](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/909))** — with SQLAlchemy 2.1 (2.1.0 to 2.1.4 checked) on CPython 3.15, the pool never cleans up a pooled connection that Python's cycle collector reclaims, such as one lost while its autobegun transaction is still open. CPython 3.15 clears weak references later (python/cpython#136189), and SQLAlchemy 2.1's pool finalizer then returns early: the connection is not terminated, its socket closes only through Python's stream finalizer with a `ResourceWarning`, and the pool slot stays checked out. This affects every dialect, sync pools included. SQLAlchemy 2.0 and Python 3.14 and earlier are not affected, and the dialect's own terminate path is unchanged. The Connection Guide and the Support Matrix describe the limitation.
- **Documented CUBRIDdb driver behavior differences (#1003)** — documented that with CUBRIDdb, which binds parameters on the server rather than in client SQL, a `CASE` whose `THEN`/`ELSE` values are all bound parameters returns strings rather than integers, and `GROUP_CONCAT` arguments or `aggregate_order_by()` items containing bound parameters fail with -494; workarounds (`cast(..., Integer)` and positional ordering) are documented in the Driver Compatibility guide.
- **BLOB and CLOB value reads documented as partial (#829, [#842](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/842))** — `docs/FEATURE_SUPPORT.md` marks CUBRID `BLOB` and `CLOB` as partially supported, clarifying that while DDL, reflection, binding and NULL round trips work, reading non-NULL values returns the driver's LOB locator across `cubrid://`, `cubrid+pycubrid://` and `cubrid+aiopycubrid://` (Known Issue 6 in `docs/DRIVER_COMPAT.md`).
- **CAS error -4 documented as interrupted statement (#873, [#939](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/939))** — updated Driver Compatibility, Connection and Troubleshooting guides to note pycubrid 1.13.0 reports -4 (`ER_INTERRUPTED`, `KILL QUERY`) as `Interrupted` with SQLSTATE `HY008` (previously `08S01`); dialect non-disconnect behavior is unchanged since 1.9.0 (#572).
- **Architecture and brand diagrams (#1013, [#1016](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1016), #886, [#900](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/900))** — added end-to-end driver communication architecture diagrams covering URL variants, Broker, CAS and CCI interactions in `docs/ARCHITECTURE.md`, enabled SuperFences Mermaid rendering, and displayed the repository icon across READMEs and docs (loading from [cubrid-lab/brand](https://github.com/cubrid-lab/brand)).
- **Onboarding and first-connection course reorganization (#940, #941, [#942](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/942), #943, [#944](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/944), #948, [#949](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/949), [#954](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/954), [#955](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/955), [#956](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/956))** — restructured Quick Start into a 5-lesson first-connection tutorial with standalone runnable async examples, organized docs by reader question, added anonymous volume deletion (`docker rm -f -v`) to cleanup instructions, and updated boolean expression caveats (#968, [#971](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/971), [#986](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/986)).
- **Documentation provenance, runbooks and performance baselines (#946, [#951](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/951), #830, #833, [#844](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/844))** — added "About this documentation" provenance notice to identify development docs, added release runbook version state tables in `RELEASING.md`, updated `ROADMAP.md` completed history, and recorded comprehensive performance baselines across CUBRID 10.2 to 11.4 and driver variants in `docs/PERFORMANCE.md`.
- **Contributor guidance and translated documentation (#907, #926, [#927](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/927), [#1012](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1012), [#846](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/846), [#913](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/913), [#1023](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1023), [#881](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/881), [#837](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/837), [#839](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/839), [#840](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/840), refs [#698](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/698), [#699](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/699), [#700](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/700))** — split `AGENTS.md` into modular task guides with link verification (`scripts/check_agents_docs.py`), clarified standalone agent review routes and good-first-issue policies, and synchronized Python version requirements across German, Hindi and Russian README translations.

### CI

- **CI test summary and artifact uploads (#1020, #1021)** — `ci.yml` offline test jobs upload JUnit, coverage and `summary.json` reports under `test-results/offline/`, append summaries to GitHub step summaries, and upload `test-results/integration/` for `make integration` jobs.
- **Docker test database volume and host stability (#997, [#998](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/998), #1000, [#1001](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1001), cubrid-lab/pycubrid#1001, cubrid-lab/pycubrid#1004)** — `docker-compose.yml` mounts named volume `cubrid-databases` for CUBRID 11.4 database files and sets `CUBRID_DB_HOST: localhost` to ensure container re-creation preserves connections and data, with `make docker-fix-db-host` provided to migrate existing volumes.
- **Workflow path filtering and release run optimizations (#737, #952, #964, #997, #760, #797)** — updated `ci.yml` path filters so `repo-tests`, `site` builds and Docker tests trigger when their inputs, agent evals or tooling modules change, and skipped redundant runtime test lanes on release commit pushes to `main`.
- **Deterministic documentation checking (#908, #920, #921, [#922](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/922), #923, [#924](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/924), #925, [#928](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/928), [#930](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/930), #934, [#935](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/935), #957, [#958](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/958), #959, [#960](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/960), cubrid-lab/pycubrid#939, cubrid-lab/pycubrid#940, cubrid-lab/pycubrid#941, cubrid-lab/pycubrid#947, cubrid-lab/pycubrid#976, cubrid-lab/pycubrid#978, cubrid-lab/cubrid-cookbook-python#402, ex. - > #750)** — added fail-closed `docs-check` CI job validating link targets, anchors, code fences, shell syntax, heading allocations (treating &#10; as no line break) and make goals via `scripts/check_docs_links.py` and `scripts/_markdown.py`.
- **Agent review gate and evaluation benchmarks (#905, #906, #933, [#936](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/936), Refs cubrid-lab/cubrid-mcp-server#341, cubrid-lab/cubrid-mcp-server#349, #929)** — added advisory `agent-review.yml` workflow checking PR review records, ignored reply-only empty Copilot records, and introduced offline agent benchmark evaluation tasks and grader in `agent-evals/`.
- **Release automation and baseline tracking (#945, [#1006](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1006), [#1007](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1007), [#1037](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1037), refs #1011, #977)** — automated verification and retirement of `last-release-sha` baseline overrides for abandoned release candidates in release preparation workflows and disposed probe engine on exit paths.

### Tests

- **Integration tests for async garbage collection and CUBRIDdb (#872, #1003, #1017, refs #987, #991)** — fixed `TestAsyncTerminateLive872` connection reuse assertions after broker localhost binding (#1017) and updated CASE and GROUP_CONCAT integration assertions to match CUBRIDdb results.
- **Compliance and query cleanup regression coverage (#849, #854, #968)** — added `TestIsolatedCTE849` for isolated live CTE compliance verification across CUBRID 10.2 to 11.4, verified ORDER BY output against SQLAlchemy's clause compiler, and added offline tests for `SHOW TRACE` statement and trace result handle cleanup.
- **Benchmark artifact manifests and provenance verification (#901, #903)** — added versioned `sqlalchemy-cubrid-benchmark-artifact` manifests (`scripts/bench_artifact.py`) and source verification (`scripts/bench_dialect_baseline.py`) to validate dialect source SHAs, package hashes and test environment metadata.

## [1.11.0] - 2026-10-12

This release introduces Python 3.15 support and a broad set of compatibility, reliability, and test improvements. Review the upgrade notes before adopting it; detailed changes and references follow.

### Upgrade notes

- **Python 3.15 is supported (#666)** — Standard GIL builds only. The pycubrid routes (`cubrid+pycubrid://`, `cubrid+aiopycubrid://`) are covered with the pycubrid release that declares Python 3.15 (cubrid-lab/pycubrid#831); the `[pycubrid]` floor stays `pycubrid>=1.8.0,<2.0`. On 3.15, pycubrid 1.10.0 and earlier reject `?charset=ksc5601` because Python 3.15 maps that codec alias to CP949; use `?charset=euckr` or the newer pycubrid. Building the official CUBRIDdb driver with GCC 14 fails on Python 3.14 and 3.15 alike (the two versions compared); see `docs/DRIVER_COMPAT.md`.
- **SQLAlchemy 2.2+ restriction (#774)** — `sqlalchemy-cubrid` no longer installs with SQLAlchemy 2.2 or newer. The package metadata now requires `sqlalchemy>=2.0,<2.2`, matching the supported range already documented (2.0 and 2.1). SQLAlchemy 2.2 is not released yet (PyPI latest 2.1.4), so no current install changes: 2.0.x and 2.1.x resolve exactly as before. Once 2.2 ships, `pip` keeps resolving SQLAlchemy 2.1.x for this package. SQLAlchemy 2.2 was never verified against the full compatibility matrix and is excluded until it ships and passes it; the cap is then lifted in a later release.
- **Contributor dependency group migration (#765)** — The `dev` extra is gone; contributors install the `dev` dependency group. Use `pip install -e . --group dev` (pip 25.1 or later) or `make install` instead of `pip install -e ".[dev]"`, which now installs only the package and warns that the extra does not exist. End users are not affected: the runtime extras (`pycubrid`, `alembic`, `cubrid`, `cubriddb`) are unchanged.

### Added

- **Python 3.15 support (#666, [#807](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/807))** — Declared the Python 3.15 package classifier, added `py315` to tox, and expanded the full 20-cell compatibility matrix across Python 3.11 to 3.15 and CUBRID 10.2 to 11.4, keeping `requires-python` at `>=3.11` without free-threaded claims (#698, #701).

### Changed

- **PEP 735 contributor dependency groups (#765)** — Replaced the published `dev` extra with PEP 735 `[dependency-groups]` in `pyproject.toml` (`test`, `lint`, `typecheck`, `security`, `mutation`, `release`, `dev`) and updated tox and CI environments to install pinned groups without altering runtime extras.

### Fixed

- **SQLAlchemy requirement cap ([#777](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/777), refs [#774](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/774))** — Capped SQLAlchemy dependency metadata to `>=2.0,<2.2` in `pyproject.toml` and extras (`dev`, `pycubrid`) to match the documented support matrix.

### Documentation

- **Private vulnerability reporting (#738, [#796](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/796))** — Enabled GitHub private vulnerability reporting as the preferred channel for security disclosures, retaining maintainer email as fallback in `SECURITY.md`, `README.md`, and translated READMEs.
- **Compatibility and driver documentation (#479, #697, [#781](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/781), [#782](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/782), [#783](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/783), [#801](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/801), [#803](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/803), [#825](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/825))** — Updated connection, driver compatibility, type mapping, and PRD docs across English and translations to reflect Python 3.11+ requirements, pycubrid 1.9.0 collection binding, the `[pycubrid]` 1.8.0 compliance floor, and CUBRIDdb driver limits.
- **Contributor and maintenance documentation (#68, #70, #736, #747, #758, [#757](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/757), [#759](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/759), [#784](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/784), [#788](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/788), [#792](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/792), [#802](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/802), [#817](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/817), [#819](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/819))** — Replaced stale performance planning snapshots, nightly integration references, and obsolete file references with canonical pointers, while updating agent review, release-please, canary, and closing-guard documentation in `AGENTS.md`, `DEVELOPMENT.md`, and `RELEASING.md`.

### CI

- **PR title and closing guard hardening (cubrid-lab/pycubrid#845, cubrid-lab/pycubrid#849, cubrid-lab/cubrid-mcp-server#275, cubrid-lab/cubrid-mcp-server#276, cubrid-lab/cubrid-cookbook-python#293, cubrid-lab/cubrid-cookbook-python#294)** — Enhanced the PR title and body closing guard across PR titles, commit messages, link text, list continuations, raw HTML entities (`&#35;`), and underscore owners (`alice_acme/repo#N`), preventing foreign issue auto-closures.
- **Validation and matrix consolidation (#479, #666, #734, #737, #747, #761, #762, #764, #786)** — Consolidated workflow validation by moving offline endpoints to Python 3.11 and 3.15 (#666, #734), running compliance lanes and restart tests on latest pycubrid in releases (#479, #737), adding a PR docs build job (#786), pinning docs requirements (#761), grouping Dependabot minor/patch updates (#737), and tuning run concurrency (#747, #762, #764).
- **Release pipeline and verification (#704, #730, #747, #770, #821, cubrid-lab/cubrid-cookbook-python#240, cubrid-lab/cubrid-cookbook-python#274)** — Hardened release workflows by verifying built wheels with the cookbook smoke test before publishing (cubrid-lab/cubrid-cookbook-python#240, cubrid-lab/cubrid-cookbook-python#274), rewriting generated issue references to "refs" (#770, #821), adopting `hashlib.file_digest()` (#730), moving mutation testing out of release gates (#747), surfacing blocked release PRs (#704), enforcing Release title tags, and standardizing changelog linting.

### Tests

- **Integration tests for driver error handling and cancellation (#479, cubrid-lab/pycubrid#492, cubrid-lab/pycubrid#493, cubrid-lab/pycubrid#512, cubrid-lab/pycubrid#542, cubrid-lab/pycubrid#543, cubrid-lab/pycubrid#554, cubrid-lab/pycubrid#556, cubrid-lab/pycubrid#687, cubrid-lab/pycubrid#744)** — Added sync and async integration tests verifying connection invalidation under query cancellation and deadlines, along with proper `DataError` and `IntegrityError` classification without connection loss.
- **Value round trips and type handling (#86, #413, #479, #483, #517, #518, #519, #542, cubrid-lab/pycubrid#819)** — Expanded live value round-trip coverage across sync and async engines for `Decimal` scientific notation, timezone-aware datetimes, NULL collection decoding, historic dates, and UTF-8 multibyte characters.
- **Workflow and dependency range test guards (#774, cubrid-lab/pycubrid#801)** — Added repository tests verifying SQLAlchemy dependency upper bounds against documentation (#774) and pinned ordered push and branch guards for `release-please.yml` (cubrid-lab/pycubrid#801).

## [1.10.0] - 2026-10-08

This release raises the minimum supported Python version to 3.11. Applications on Python 3.10 should remain on the compatible 1.9.x line until upgraded. Review the upgrade notes and detailed changes below.

### Upgrade notes

- **Python 3.11 or newer is required (#686, #703)** — Python 3.10 reached upstream end of life on 2026-10-01 and its retirement was announced in 1.9.0. On Python 3.10 `pip` keeps installing 1.9.x, the last line that supports it; only the latest release line receives fixes, so 1.9.x gets no further releases. Upgrade Python, recreate your virtual environment and validate your application before upgrading.

### Changed

- **Development tooling updated for Python 3.11 (#687, #688)** — Removed `py310` from tox `envlist` and re-targeted `typecheck-sa20` to Python 3.11 (#687); updated Ruff `target-version` and mypy `python_version` to 3.11 in `pyproject.toml` (#688).

### Removed

- **Python 3.10 support (#686, #703)** — `requires-python` is `>=3.11` and the 3.10 classifier is gone. CI no longer tests 3.10: the oldest integration cell is Python 3.11 × CUBRID 10.2 × SQLAlchemy 2.0.53, the full matrix covers Python 3.11-3.14 and the Alembic compatibility job runs on 3.11. Python 3.10 used to select SQLAlchemy 2.0 by itself (SQLAlchemy 2.1 needs Python 3.11), so the oldest CI cell and the Python 3.11 row of the full matrix now pin `sqlalchemy>=2.0,<2.1`; without the pin no live lane would run the ordinary integration tests on the minimum supported SQLAlchemy line. No dialect behavior changes on Python 3.11 or newer.

### Documentation

- **Python 3.11 documentation updates (#685, #695, #696, #702, #718, #731, #740)** — Stated the Python 3.11+ requirement and 3.11-3.14 support range across README, quickstarts, contributor and CI guides, and the canonical index (#685, #695, #696, #702, #718, #731, #740).
- **Korean translation expansion and synchronization (#706, #707, #708, #709, #710, #711, #712, #713, #714, #719, #720)** — Added Korean homepage and navigation (#707, #712), contribution guide (#708, #713), and translations for `SA_COMPAT`, `PRD`, and `RELEASE_PLEASE_VALIDATION` (#709, #714); aligned Korean matrices and feature tables with English (#706, #711, #719, #720); and added `scripts/check_docs_translation.py` in CI to detect drift (#710).
- **Site navigation, anchors, and license inventory (#716, #717, #721, #722, #727, #733, #739, #755)** — Fixed documentation site heading anchors with Unicode-aware slugifier (#721, #722), aligned the homepage SQLAlchemy support range to 2.0-2.1 (#716, #717), added reproducible scope-based license inventory in `THIRD_PARTY_LICENSES.md` (#727, #755), and aligned contributor ownership guardrails (#733, #739).

## [1.9.0] - 2026-10-04

This release contains a substantial set of dialect and development improvements. Read the upgrade notes and compatibility guidance before upgrading; the detailed changes below preserve the full technical history.

### Added

- **Collection binding with pycubrid typed collections (#484, #623)** — Bound `SET`, `MULTISET`, and `SEQUENCE` values using `pycubrid.types.Set`, `Multiset`, or `Sequence` on `cubrid+pycubrid://` and `cubrid+aiopycubrid://` when supported by pycubrid (#567), while raising `TypeError` for sets bound to ordered `SEQUENCE` columns.

### Changed

- **pycubrid 1.8.0 is now the minimum (#559)** — The `[pycubrid]` extra requires `pycubrid>=1.8.0,<2.0` (was `>=1.3.2,<2.0`), because contract tests require 1.8.0 fixes (NOT NULL / foreign-key `IntegrityError`, no silently truncated result after `commit()` / `rollback()`, `cursor.description` `null_ok`, and collection type codes) and 1.8.0 keeps the CAS session across `commit()` / `rollback()` and in autocommit mode. README and translations, `docs/CONNECTION.md`, `docs/DRIVER_COMPAT.md`, `docs/SUPPORT_MATRIX.md`, and `docs/DEVELOPMENT.md` (+ Korean) state the new range.
- **`cubrid://` warns at first connect when CUBRIDdb is older than 11.3 (#585, #588)** — `CubridDialect.initialize()` reads the loaded driver's compiled-in version (`CUBRIDdb._cubrid.__version__`, `b'9.3.0.0001'` for the PyPI release) and emits a `SAWarning` naming the version, the recommended `cubrid+pycubrid://` driver, and the source-build path when its major.minor is below 11.3. It warns instead of raising `NotSupportedError` so that existing deployments keep connecting; filter the warning to `"error"` to fail fast, and the `ImportError` for missing CUBRIDdb no longer suggests `pip install CUBRID-Python`.
- **Lazy Alembic registration via entry point (#595, #616)** — `pyproject.toml` registers `_sqlalchemy_cubrid_alembic` under `alembic.plugins` for Alembic 1.18+, eliminating immediate Alembic imports and log noise on dialect load while preserving direct import for Alembic 1.7.2-1.17 (#561).
- **Reflection skips redundant DDL fallback (#610, #629, #673)** — `get_unique_constraints()` skips `SHOW CREATE TABLE` when catalog queries confirm no unique index exists on current-user tables, reducing inspection queries from 3 to 2.
- **Dialect driver policy isolation (#596)** — Moved pycubrid-specific disconnect classification into `PyCubridDialect` and removed redundant `on_connect()` and `do_ping()` overrides in `PyCubridAsyncDialect` without altering behavior.
- **Isolation level re-apply documentation (#559)** — Clarified that pycubrid 1.8.0 preserves isolation levels across commits and rollbacks but re-applies levels when CAS resets out-of-transaction, keeping idle pooled connections bound to configured levels.

### Deprecated

- **Python 3.10 support (#665)** — advance notice for the 1.9.x release. Python 3.10 reached upstream end of life on 2026-10-01 ([PEP 619](https://peps.python.org/pep-0619/#310-lifespan)). The current 1.8.x line and 1.9.x retain Python 3.10 support. After this notice ships in 1.9.0, the following minor release (planned 1.10.0) will require Python >=3.11. Upgrade Python, recreate your virtual environment and validate your application before upgrading. Current package metadata, CI coverage and runtime behavior remain unchanged; see [support matrix](docs/SUPPORT_MATRIX.md) and [roadmap](ROADMAP.md).
- **The `[cubrid]` and `[cubriddb]` extras (#585)** — both depend on an unbounded `CUBRID-Python`, and PyPI has no release newer than 9.3.0.2 (sdist only, 2015), so they install a driver this dialect has never tested: on CUBRID 11.4 it returns `BIGINT` as `str` (#583) and fails parts of the integration suite. A version floor would make the extras uninstallable and removing them would change what an existing `pip install "sqlalchemy-cubrid[cubriddb]"` resolves to, so they are kept unchanged for now and marked deprecated. The supported CUBRIDdb is built from cubrid-python v11.3.0.51 or later; `cubrid+pycubrid://` remains the recommended driver. README (+ Korean), `docs/CONNECTION.md`, `docs/DRIVER_COMPAT.md`, `docs/TROUBLESHOOTING.md`, `docs/SUPPORT_MATRIX.md`, `docs/QUICKSTART.md` (+ Korean) and `docs/llms.txt` now document that install path instead of `pip install CUBRID-Python`, and `docs/DRIVER_COMPAT.md`'s build recipe now clones with `--recurse-submodules` and its version check reads `CUBRIDdb._cubrid.__version__` (`CUBRIDdb.__version__` does not exist).

### Fixed

- **Alembic foreign key autogenerate matching (#624, #668)** — Autogenerate matches reflected and model foreign keys by columns and target table in addition to constraint name, preventing incorrect name-only pairings across different columns.
- **Negative and zero type lengths rejected (#441, #476, #477, #478, #491, #662)** — VARCHAR, NVARCHAR, CHAR, NCHAR, BIT, BIT VARYING, BINARY, and VARBINARY reject explicit negative lengths with `CompileError` (#456, #491, #662), `CHAR(0)` and `NCHAR(0)` no longer compile to bare types (#476, #477), and `BIT(length=0)` raises `CompileError` instead of coercing to `BIT(1)` (#441, #478).
- **Async read timeout connection invalidation (#624, #672)** — `is_disconnect()` recognizes `asyncio.TimeoutError` in the cause chain of pycubrid `OperationalError` on Python 3.10, properly retiring closed sessions.
- **Disconnect phrase filtering in server errors (#624, #676)** — Prevented healthy pooled connections from being discarded when server error messages echo user data containing disconnect substrings, while preserving disconnection handling for -190, -191, and -368.
- **Reflection DDL fallback on unknown server version (#624, #675)** — `get_unique_constraints()` retains `SHOW CREATE TABLE` fallback when `server_version_info` is unavailable, ensuring tables from other owners are not falsely reported as lacking unique constraints.
- **pycubrid malformed-reply disconnect handling (#680, #681)** — Classified pycubrid `OperationalError("malformed response from broker")` as a disconnect condition so broken connections are recycled rather than reused.
- **Collection domains and authorized ENUM reflection (#631, #635, #677)** — `get_columns()` queries `_db_domain.enumeration` for exact ordered ENUM labels, inspects `SET`/`MULTISET`/`SEQUENCE` collection member types through `db_attr_setdomain_elm`, and returns `NullType` on unauthorized access instead of fabricating labels.
- **Whitespace accepted in numeric type parameters (#609, #615, #626)** — Column reflection accepts whitespace in numeric parameter lists (such as `NUMERIC(10, 2)`), correctly extracting precision and scale instead of falling back to `NullType`.
- **Alembic autogenerate default RESTRICT preservation (#597, #622)** — `CubridImpl.correct_for_autogen_foreignkeys()` clears reflected default `RESTRICT` actions when the model specifies no action, preventing spurious drop and re-create operations.
- **Disconnect error code parsing (#608, #620)** — Stopped treating leading numbers in error message text as disconnect error codes, reading codes strictly from integer `args[0]` and pycubrid `errno`.
- **REPLACE statement compilation (#591, #600)** — `replace()` replaces only the statement verb in compiled SQL rather than replacing the first `INSERT INTO` substring, avoiding corruption in SQL prefixes, comments, or string literals.
- **URL query options forwarded to pycubrid (#592, #599)** — `cubrid+pycubrid://` and `cubrid+aiopycubrid://` forward connection parameters including `connect_timeout`, `read_timeout`, `fetch_size`, `ssl`, and `charset` (#377, #510) to pycubrid with validation.
- **Constraint reflection exception propagation (#589)** — `get_foreign_keys()` and `get_unique_constraints()` propagate unexpected exceptions from `SHOW CREATE TABLE` instead of falsely reporting tables as having no constraints (#530).
- **Catalog COUNT(*) coercion in object existence checks (#583, #584)** — `has_table()` and `has_index()` coerce catalog `COUNT(*)` results to `int`, preventing string `'0'` returned by PyPI `CUBRID-Python` from evaluating to `True`.
- **CAS memory allocation disconnect detection (#578, #582)** — Added -10002 (`CAS_ER_NO_MORE_MEMORY`) and pycubrid legacy renumbered code -1002 to disconnect tables so memory exhaustion closes the connection immediately.
- **Server crash and restart disconnect classification (#564, #565, #571)** — Added CUBRID server failure codes -111, -199, -224, and -677 as disconnects for both drivers, invalidating pooled connections when `cub_server` crashes or restarts.
- **CUBRIDdb disconnect codes audited (#572, #577)** — Corrected CUBRIDdb disconnect codes by adding -20004, -10003, -20002, and -20016 for dead CAS connections and removing -4, -10005, -10007, -21003, and -21005 so interrupted queries no longer discard working connections.
- **Reflection syntax errors propagate instead of raising NoSuchTableError (#454, #455)** — `get_columns()` and `get_indexes()` propagate native syntax errors (-493) instead of masking them behind `NoSuchTableError` by @UsmanGhias.

### Documentation

- **Driver recommendations and usage samples (#495, #498, #516)** — Updated Quick Start guides and sample scripts to use `cubrid+pycubrid://` as primary driver and documented CUBRID-Python 11.3 source builds (#495, #498, #516).
- **Support claims, version matrices, and metadata refresh (#460, #461, #492, #499, #506, #579, #643)** — Replaced stale test counts and coverage stats with durable policy references (#461, #643); documented SQLAlchemy 2.1 as tested GA (#492, #506); corrected CUBRID capabilities in single-sourced `llms.txt` (#460, #579); and derived Sphinx release dynamically (#499).
- **Alembic logging and contributor documentation (#181, #346, #374, #442, #497, #561, #562, #650, #663)** — Documented Alembic import log behavior under INFO logging (#561, #562); prepared demo recording script while deferring embed (#346, #374); updated type-mapping tables for timezone types (#181, #442); removed redundant dev install steps (#497, #663); and updated contributor issue specification guidance (#650).

### CI

- **Automated release workflow and publication guards (#540, #566, #576, #601, #605, #657)** — Unified release automation with sibling repositories using PR-only release-please (#657), automated release dispatch upon merging release PRs (#540, #601), cookbook smoke verification (#576, #605), PyPI duplicate file guard (#566), and publisher workflow renaming to `publish-pypi.yml` (pycubrid#681).
- **CI matrix optimization and concurrency (#645, #659)** — Reduced routine PR CI to one representative offline lane with scheduled weekly full matrices, isolated CI workflow cancellation by event/ref, and aligned coverage badge sync (#645, #659).
- **Tooling consistency and documentation reason checks (#429, #447, #558, #573, #587, #648, #649)** — Single-sourced Ruff/Mypy pre-commit hooks and tox environments from `pyproject.toml` dev pins (#558); synchronized docs-reason validation to reject empty captions (#429, #573, #648, #649); and updated Alembic safety checker to count actual DDL calls (#447, #587).
- **Python 3.15 preview lane** — Added manual-only offline and packaging validation lane for upcoming Python 3.15 preview.

### Tests

- **Integration runner reliability and Docker lifecycle (#446, #508, #567, #568, #574, #575, #581, #593)** — `make integration` waits for server readiness via `scripts/wait_for_cubrid.py` (#575, #581), uses isolated Compose project names to avoid removing external containers (#567), traps signals for clean container shutdown (#568, #574), guarantees cleanup on failure (#446, #508), and fails immediately with masked URLs when `CUBRID_TEST_URL` is unreachable (#593).
- **Driver differential and contract test suites (#439, #479, #480, #483, #484, #485, #486, #490)** — Added collection round-trip differential tests and skip-detection via `scripts/check_not_all_skipped.py` (#486); dedicated modules verify LOB value contracts (#485, #490) and verify scalar DB-API execution without `compat.native` (#439, #483).
- **Test suite organization, parser validation, and mutation testing (#390, #531, #559, #590, #594, #598, #604, #611, #628, #634, #647)** — Separated repository-tooling tests into an independent `-m repo` lane (#594, #647); re-baselined compliance suites on pycubrid 1.8.0 (#390, #559); recorded golden `SHOW CREATE TABLE` outputs across CUBRID 10.2-11.4 (#611); verified parser logic against real dialect methods (#531, #590, #598); isolated KILL QUERY test accounts (#634); and restored mutmut sandbox execution (#604, #628).

## [1.8.0] - 2026-09-29

This release includes substantial dialect and integration changes. Review the upgrade notes and detailed sections below to assess compatibility and migration impact.

### Upgrade notes
- **Alembic upgrades are atomic by default (#503)** — CUBRID DDL is transactional, so a failed multi-revision alembic upgrade now rolls back the whole run, including the alembic_version update. Set transaction_per_migration=True in context.configure() to keep per-revision commits (recommended for long or large-table migrations to prevent schema locks). Offline --sql scripts no longer contain BEGIN;; run them with csql --no-auto-commit --no-single-line so a failing statement stops script execution.
- **Alembic registration and async migrations (#504)** — CubridImpl registers when the dialect loads, letting default env.py configurations run without importing sqlalchemy_cubrid.alembic_impl. The [alembic] and [dev] extras now require alembic>=1.7.2. Online migrations on cubrid+aiopycubrid:// require Alembic's async template (alembic init -t async).
- **Reflection behavioral changes (#529, #530, #531, #533, #543, #544, #545, #549)** — Unique constraints reflect as unique indexes rather than duplicate constraints (#529). Non-DBA users get complete metadata from public catalog views (#549), missing tables or views raise NoSuchTableError (#530), and has_table() and has_index() match mixed-case names (#543). get_foreign_keys() sorts constraints by name (#531), BIT(n) and BIT VARYING(n) keep their lengths (#545), failing catalog queries raise instead of silently returning incomplete metadata (#533, #549), and Alembic autogenerate detects Text <-> String(n) changes (#544). Review your first Alembic autogenerate diff after upgrading.
- **DDL and type compilation (#440, #465, #533, #534, #535, #540, #545)** — UnicodeText and TEXT compile to STRING (#534). BINARY(n) and VARBINARY(n) compile to BIT(n*8) and BIT VARYING(n*8), while UUID compiles to CHAR(32) (#545). Index.drop() and op.drop_index() emit DROP INDEX <name> ON <table>, requiring table_name in op.drop_index() (#533). if_exists=True on index drops (#533) and if_not_exists=True on index creates (#540) raise CompileError, as does explicit String(0) (#440). Boolean is_() and is_not() against a value render with <=> (#465), and JSON as_numeric(p, s) returns Decimal (#535).
- **Transaction isolation and batch execution (#501, #502, #505)** — isolation_level="AUTOCOMMIT" works across all drivers, invalid levels raise ArgumentError, and dialect.on_connect() no longer applies isolation_level (hand-built pools must apply it) (#501). Engine- and connection-level isolation levels survive commit() and rollback() on pycubrid (#505). On cubrid://, executemany runs each parameter set separately: None values and rowcounts are correct, but large batches run slower (#502).
- **Async connection accessor (#500, #520)** — driver_connection on cubrid+aiopycubrid:// now returns the underlying pycubrid.aio.AsyncConnection rather than the adapter; code expecting the adapter must use dbapi_connection (#520). Async LargeBinary and BLOB parameter binding is now supported (#500).
- **Legacy SQLAlchemy 1.x hooks removed (#462)** — Removed unreachable SQLAlchemy 1.x hooks should_autocommit_text(), AUTOCOMMIT_REGEXP, and the legacy dbapi() classmethods (#462).
- **Recommended pycubrid 1.8.0 driver (#480, #481, #482, #559)** — pycubrid 1.8.0 is recommended: it raises IntegrityError for NOT NULL and foreign-key violations, prevents silent result truncation after commit() or rollback(), reports correct null_ok and collection type codes in cursor.description, and keeps CAS sessions across transactions (docs/DRIVER_COMPAT.md Known Issue 10); contract tests require it (#480, #481, #482). The declared range stays pycubrid>=1.3.2,<2.0 (#559), preserving the isolation-level re-apply workaround as a safe no-op on pycubrid 1.8.0.

### Changed
- **Transactional Alembic DDL migrations by default (#503)** — CubridImpl.transactional_ddl is now True. Because CUBRID DDL is fully transactional, ROLLBACK undoes table, view, index, serial, and rename operations without committing prior DML. A failed multi-revision alembic upgrade now rolls back all revisions in that run including the alembic_version update. Use context.configure(transaction_per_migration=True) to restore per-revision commits for long migrations. CubridImpl.emit_begin() emits nothing because CUBRID lacks a BEGIN statement, and offline --sql scripts end transactions with COMMIT;; execute them using csql --no-auto-commit --no-single-line.
- **Pycubrid 1.8.0 contract test requirements (#480, #481, #482)** — Integration and differential suites now run contract checks unconditionally against pycubrid 1.8.0 or later, removing strict upstream xfail markers for cubrid-lab/pycubrid#390 (IntegrityError on NOT NULL and foreign-key violations), #395 (no silent result truncation), #430 (collection type codes in cursor.description), and #431 (inverted null_ok). test/pycubrid_upstream.py and the CUBRID_PYCUBRID_UPSTREAM canary switch are removed, while the declared pycubrid>=1.3.2,<2.0 dependency range remains unchanged.

### Removed
- **Legacy SQLAlchemy 1.x autocommit hooks and dbapi classmethods (#439, #462, #468)** — Removed dead SQLAlchemy 1.x should_autocommit_text(), AUTOCOMMIT_REGEXP, and dialect dbapi() classmethods (#462), retiring #439's request to add REPLACE to autocommit regex surfaced by @biggdawg320 in #468. Dialects resolve drivers directly via import_dbapi(), and SQL statements commit only through explicit transaction demarcation.

### Fixed
- **Alembic autogenerate detects Text to String column changes (#544)** — CubridImpl now matches the STRING dialect type by class instead of class name, allowing autogenerate to detect when a model column alters between Text and bounded String(n) while keeping unbounded string types clean.
- **BINARY, VARBINARY, and UUID DDL compilation and reflection (#545)** — BINARY(n) compiles to BIT(n*8), VARBINARY(n) compiles to BIT VARYING(n*8) (zero length raises CompileError), and UUID compiles to CHAR(32). Reflection now preserves lengths for BIT(n) and BIT VARYING(n) columns to prevent false autogenerate diffs.
- **Boolean IS and IS NOT predicate compilation (#465)** — Comparisons against boolean values like col.is_(True) now render with the null-safe equality operator <=> (a <=> b and (a <=> b) = 0) instead of invalid IS 1 or IS 0 syntax rejected by CUBRID.
- **Reflection access for non-DBA users via public catalog views (#120, #426, #549)** — Reflection now queries public views db_index, db_index_key, and db_attribute instead of DBA-only _db_* tables, preventing authorization errors (-494) that dropped composite PK columns (#426) or misreported unique constraints and foreign keys (#120). Lookups respect owner precedence on CUBRID 11.2+, match mixed-case table names, and raise immediately on catalog failures instead of degrading.
- **Mixed-case table and index name resolution (#444, #538, #543)** — has_table() and has_index() now match identifiers in lower-case form (IN (:name, LOWER(:name))), preventing checkfirst=True operations from silently skipping on mixed-case names (#543, #444, #538).
- **CreateIndex if_not_exists validation (#540)** — Index creation with if_not_exists=True now raises CompileError pointing to inspect(conn).has_index() or Index.create(checkfirst=True) rather than emitting CREATE INDEX IF NOT EXISTS syntax rejected by CUBRID.
- **NoSuchTableError raised for missing tables and views (#454, #530)** — get_foreign_keys(), get_unique_constraints(), get_table_comment(), and get_view_definition() now verify class existence via db_class first, raising NoSuchTableError for nonexistent objects rather than returning empty lists or escaping generic -493 errors (#454, #530).
- **UnicodeText and TEXT compilation to STRING (#534)** — UnicodeText and generic sqlalchemy.TEXT now compile to CUBRID STRING instead of emitting nonexistent TEXT definitions (-494), and Alembic autogenerate compares them consistently.
- **Duplicate unique constraints, view index reflection, and query entry leak (#529, #548)** — get_unique_constraints() marks reflected unique constraints with duplicates_index so reflection keeps only the unique index (#529). get_indexes() returns an empty list for views instead of leaking base table indexes, and single-row catalog queries use Result.first() to close results and prevent -830 query entry exhaustion (#548).
- **Deterministic sorting for reflected foreign keys (#531)** — get_foreign_keys() and get_multi_foreign_keys() now return constraints sorted by constraint name, matching standard SQLAlchemy dialect behavior.
- **Foreign keys and unique constraints on column names with parentheses (#532)** — SHOW CREATE TABLE regex parsing now handles bracketed column identifiers containing parentheses like [(3)], commas, or spaces without truncating column lists.
- **Index drop DDL table qualification (#533)** — Index.drop() and op.drop_index() emit DROP INDEX <name> ON <table> (requiring table_name in op.drop_index()). Specifying if_exists=True raises CompileError because CUBRID lacks DROP INDEX IF EXISTS support, and has_index() results are now cached on the Inspector.
- **JSON as_numeric precision and Decimal return type (#535)** — JSON .as_numeric(p, s) renders CAST(... AS NUMERIC(p,s)) when precision and scale are specified, returning exact Decimal instances rather than float values. Unscaled numeric casts continue using DOUBLE via as_float().
- **AUTOCOMMIT isolation level support across all drivers (#501)** — Setting isolation_level="AUTOCOMMIT" toggles driver-level autocommit across cubrid://, cubrid+pycubrid://, and cubrid+aiopycubrid:// without raising ArgumentError or ValueError. Engine-level isolation levels are restored upon connection checkin, and invalid isolation levels raise ArgumentError consistently.
- **Transaction isolation preservation on pycubrid (#468, #505)** — PyCubridDialect and PyCubridAsyncDialect re-apply configured isolation levels in do_commit() and do_rollback(), preventing transactions from resetting to the server default level when pycubrid reconnects broker sessions (cubrid-lab/pycubrid#468).
- **Async driver_connection accessor (#520)** — Accessing driver_connection on cubrid+aiopycubrid:// returns the underlying pycubrid.aio.AsyncConnection rather than the internal adapter; applications that need the adapter should use dbapi_connection.
- **Inspector has_table caching (#463)** — CubridDialect.has_table() is now decorated with @reflection.cache, ensuring inspect(engine).has_table() respects the inspector cache until clear_cache() is invoked.
- **CUBRIDdb executemany parameter binding and rowcounts (#421, #502)** — CubridDialect.do_executemany executes each parameter set individually on cubrid:// to prevent CUBRIDdb from reusing previous row values for None and to correctly report total affected rowcounts across batched DML and bind_expression inserts (#421).
- **Automatic Alembic CubridImpl registration on dialect import (#504)** — Importing sqlalchemy_cubrid automatically registers CubridImpl with Alembic's dialect registry when Alembic is installed, eliminating the need to import sqlalchemy_cubrid.alembic_impl manually in env.py.
- **Async LargeBinary and BLOB parameter binding (#441, #485, #500)** — AsyncAdapt_pycubrid_dbapi now implements the full PEP 249 interface including Binary and type constructors, preventing AttributeError when binding binary data on async engines (#500) while LOB locator read limits remain documented (#441, #485).
- **Explicit String(0) rejection (#440)** — Specifying String(0), VARCHAR(0), or NVARCHAR(0) now raises CompileError rather than silently falling back to the 4096-character default.
- **Deterministic table and view reflection ordering (#443)** — get_table_names() and get_view_names() queries now sort results with ORDER BY class_name.
- **Async installation extra includes greenlet bridge (#448)** — The [pycubrid] and [dev] package extras now require SQLAlchemy[asyncio], installing greenlet automatically for async engine support on SQLAlchemy 2.0 and 2.1.
- **SQL fallback for last-insert-ID on SQLAlchemy 2.x (#458)** — Both execution contexts obtain a standard DBAPI cursor for SELECT LAST_INSERT_ID() queries instead of calling SQLAlchemy's unimplemented server-side cursor hook.

### Documentation
- **Installation prerequisites and driver guidance (#448)** — Documentation across connection guides, troubleshooting, and FAQs clarifies that pycubrid requires no native CUBRID libraries, while the [pycubrid] async extra requires greenlet which may need C build tools when prebuilt wheels are unavailable.
- **Contributor guides and documentation exception rules** — Added a repository contribution guide with Korean translations, documented the good first issue lifecycle in AGENTS.md, and clarified standalone format requirements for docs-not-needed PR body exemptions.

### CI
- **Upstream pycubrid canary issue reporting (#521)** — Configured scheduled and manual canary workflows against pycubrid@main to automatically open, comment on, or close a tracking issue titled "Upstream canary failing against pycubrid@main" using the GitHub CLI.
- **Tooling, typing, and mutation testing alignment (#450, #459, #464)** — Aligned Ruff and mypy pre-commit hooks with development dependencies (#464), enforced strict typing across SQLAlchemy 2.0 and 2.1 via typed boundaries and CI check cells (#459), and upgraded nightly mutation testing to mutmut 3 with score reporting and strict failure handling (#450).

### Tests
- **SQLAlchemy compliance and driver-differential testing lanes (#463, #486)** — Added merge-gating compliance lanes for cubrid+pycubrid:// on Python 3.14/CUBRID 11.4 and Python 3.10/CUBRID 10.2 using lane-keyed test/known_failures.txt manifests, unskipping ~300 tests per lane (#463, #529, #530, #531, #532, #533, #534, #535). A required driver-differential suite now includes an all-skipped safety guard and driver version logging (#486).
- **Live driver contract and constraint test suites (#464, #480, #481, #482, #484, #485)** — Added live integration tests across CUBRIDdb and pycubrid for BLOB/CLOB round trips (#485), verified that results are never silently truncated across commit or rollback boundaries (#481), asserted IntegrityError on constraint violations with connection reuse (#480, #484), checked cursor.description type codes and nullability (#482), and made pure-driver tox integration preflight checks explicit (#464).

## [1.7.1] - 2026-09-18

This maintenance release fixes multi-column primary-key reflection, numeric bind scale preservation, OFFSET without LIMIT, and IS DISTINCT FROM execution. It also improves executemany inserts with cast decorators, makes unsupported multi-row ON DUPLICATE KEY UPDATE expressions fail clearly, and expands dialect test coverage.

### Added
- **Runnable usage examples in public docstrings (#337)** — added live-verified usage examples to package and dialect docstrings for connection URL forms (cubrid+pycubrid://, cubrid+cubriddb://, async cubrid+aiopycubrid://), inspect(), and insert().on_duplicate_key_update().

### Removed
- **Dead implicit_returning dialect attribute removed (#396)** — removed the obsolete SQLAlchemy 1.x-era implicit_returning = False attribute; SQLAlchemy 2.x determines implicit RETURNING support solely from insert_returning (already False), and DefaultDialect no longer defines the attribute.

### Fixed
- **Reflection gaps and system view filtering (#387)** — fixed get_columns() to read comments from class_of.class_name, translated raw table-not-found errors to NoSuchTableError in get_columns() and get_indexes(), filtered out internal system views in get_view_names(), and set requires_name_normalize = False to skip incompatible case-normalization tests.
- **Composite primary key reflection (#426)** — updated get_pk_constraint() to query _db_index and _db_index_key in key order with a SHOW COLUMNS fallback, preventing composite primary keys from losing columns after the first.
- **Parameter count in executemany with bind expressions (#421)** — disabled insertmanyvalues row-expansion for INSERT statements targeting columns with type-decorator bind expressions (such as CAST), falling back to standard DBAPI executemany to avoid parameter-count mismatches.
- **Identity column compilation and time precision limits (#388)** — compiled Identity() columns to AUTO_INCREMENT instead of plain INTEGER NOT NULL, and declared lack of microsecond support for DATETIME (millisecond only) and TIME in compliance requirements.
- **Validation for multi-row ON DUPLICATE KEY UPDATE (#371)** — raised a clear CompileError when stmt.inserted.col is referenced in multi-row inline VALUES constructs because CUBRID lacks row-alias syntax, directing callers to executemany, single-row inserts, or MERGE.
- **Sentinel row count for OFFSET without LIMIT (#414)** — replaced the 2^30-1 string-length cap with a 2^62 sentinel constant (_CUBRID_OFFSET_NO_LIMIT_ROW_COUNT) to allow unbounded offsets without triggering addition-overflow errors at signed BIGINT max.
- **Numeric bind parameter scaling and FROM-less queries (#386)** — rendered CAST(? AS NUMERIC(p,s)) for scaled numeric binds in arithmetic to prevent scale loss from CUBRID integer coercion, and added default_from() returning FROM db_root for FROM-less SELECT queries with WHERE clauses.
- **Dialect capability flags updated (#381, #382)** — set supports_is_distinct_from and supports_native_enum to True to reflect implemented capabilities (IS DISTINCT FROM emulation via <=> from #345 and #377; native ENUM DDL), enabling compliance suite tests, and corrected ENUM docstrings regarding native_enum=False.
- **IS DISTINCT FROM expression projection (#377)** — rendered null-safe negation as (a <=> b) = 0 instead of NOT (a <=> b) to ensure valid execution in SELECT projection lists on live CUBRID servers.
- **Driver-specific numeric precision limitation documented (#386)** — documented in docs/DRIVER_COMPAT.md and docs/TYPES.md that the legacy CUBRIDdb C-extension driver truncates fractional parts of NUMERIC/DECIMAL values below the DBAPI layer, whereas pure-Python cubrid+pycubrid:// preserves Decimal scale correctly.

### Documentation
- **Troubleshooting guide LIMIT/OFFSET correction (#416)** — corrected English and Korean troubleshooting docs to document CUBRID's native comma syntax LIMIT offset, count rather than the unsupported LIMIT n OFFSET m form.
- **Documentation localization and site navigation (#341)** — completed Korean translations for 14 pages across batches 1 through 5 (including TROUBLESHOOTING, FEATURE_SUPPORT, and DEVELOPMENT), unified site navigation to a six-tab layout, and established translation synchronization tracking.
- **Third-party licenses and provenance documentation (#333)** — added THIRD_PARTY_LICENSES.md documenting runtime dependencies and CUBRID-Python extra licensing, added a project NOTICE, documented implementation provenance in docs/ARCHITECTURE.md, and unified copyright notices.

### CI
- **AI documentation bundle and drift detection (#383)** — regenerated docs/llms-full.txt from source to remove outdated VALUES() references (#356), and added a CI lint step that fails on documentation drift.
- **SQLAlchemy dialect compliance suite gating (#380)** — configured setup.cfg with [sqla_testing] and gated CI on Python 3.14 with CUBRID 11.4 and sqlalchemy==2.0.53, establishing strict-xfail baselines in test/known_failures.txt with tracking issues (#385, #386, #387, #388).
- **Release workflow tag creation fix** — dropped the redundant --target flag from gh release create in create-release.yml to avoid 422 Validation Failed errors when tags are already pushed.

### Tests
- **Comprehensive dialect test suite additions (#376)** — added integration test suites including a UUID type round-trip contract matrix (#376), real-application ORM dogfooding scenarios, CUBRID version-differential snapshots across 10.2 through 11.4, live capability probe suites, Hypothesis property-based fuzzers, and mutmut mutation testing for compiler.py.

## [1.7.0] - 2026-09-02

This release adds native ENUM support, null-safe distinct comparisons, and native Alembic column alterations. It fixes literal backslash doubling, schema reflection, isolation-level handling, and connection pool disconnect detection while adding the explicit cubrid+cubriddb:// URL.

### Added
- **Native ENUM type support (#343)** — added native ENUM DDL via sqlalchemy_cubrid.ENUM and mapped plain sa.Enum to native ENUM with element-list reflection from SHOW COLUMNS across CUBRID 10.2, 11.0, and 11.4.
- **IS [NOT] DISTINCT FROM emulation (#344)** — emulated SQL-standard distinct comparisons using CUBRID's null-safe equal operator <=> as NOT (a <=> b) and a <=> b.
- **Explicit CUBRIDdb URL and install extra (#276)** — added the explicit cubrid+cubriddb:// URL and matching cubriddb = ["CUBRID-Python"] install extra for the legacy C-extension driver, keeping bare cubrid:// unchanged while recommending cubrid+pycubrid:// for new projects.
- **Native Alembic column migrations (#305)** — implemented native ALTER TABLE MODIFY for type changes, RENAME COLUMN for renames, and CHANGE for combined operations in CubridImpl.alter_column(), avoiding batch_alter_table recreations subject to alter_table_change_type_strict.

### Changed
- **Hardened connection pool disconnect detection (#314)** — prioritized stable numeric error codes (adding pycubrid code -4 / ER_COMMUNICATION / SQLSTATE 08S01 alongside -21003, -21005, -10005, and -10007) and explicit-cause OSError inspection over substring matching in is_disconnect().

### Removed
- **Obsolete pre-MVCC isolation levels removed (#307)** — removed pre-MVCC isolation levels 1, 2, and 3 (REPEATABLE READ SCHEMA, READ UNCOMMITTED INSTANCES; READ COMMITTED SCHEMA, READ COMMITTED INSTANCES; READ COMMITTED SCHEMA, READ UNCOMMITTED INSTANCES) from _ISOLATION_LEVEL_MAP and _ISOLATION_LEVEL_REVERSE, raising ValueError on use while retaining the three supported MVCC levels (READ COMMITTED, REPEATABLE READ, SERIALIZABLE) and valid aliases.

### Fixed
- **Preserved literal backslashes by default (#313)** — stopped unconditionally doubling backslashes in literal rendering since CUBRID defaults to no_backslash_escapes=yes, preventing data corruption in DML literals, JSON path literals, and DDL comments; added CubridDialect(no_backslash_escapes=False) for servers configured with no_backslash_escapes=no. Migration note: databases written by an affected version may contain unintended doubled backslashes in literal-rendered data, so audit such rows if you relied on inline literals.
- **Connection pool cleanup for clean-EOF disconnects (#322)** — added the substring "connection lost" to _disconnect_messages so pycubrid client-side EOF errors without numeric codes or OSError causes correctly invalidate broken connections.
- **Default schema name handling (#290)** — updated _get_default_schema_name() to return None instead of the string "None" when SELECT SCHEMA() yields SQL NULL, ensuring get_schema_names() returns an empty list instead of a fake schema name.
- **Schema validation on object-detail reflection (#291)** — added _raise_if_non_default_schema() to get_columns(), get_pk_constraint(), get_foreign_keys(), get_indexes(), get_unique_constraints(), get_view_definition(), and get_table_comment() to raise NoSuchTableError for non-default schemas.
- **Case-insensitive default schema matching (#292)** — normalized schema names with self.normalize_name() in _schema_is_default(), allowing case-mismatched names like "dba" and "DBA" to match while preserving case for explicitly quoted identifiers.
- **Single-schema reflection consistency (#280)** — aligned get_schema_names() to return [default_schema_name] and enforced uniform schema filtering across get_table_names(), get_view_names(), has_table(), and has_index().
- **Symmetric isolation level round-trips (#281)** — updated _ISOLATION_LEVEL_REVERSE to return canonical short names for READ COMMITTED, REPEATABLE READ, and SERIALIZABLE, ensuring pool return and reset comparisons succeed across input aliases.

### Documentation
- **SQLAlchemy version support narrative realigned (#312)** — aligned documentation across all locales and ROADMAP.md to state support for SQLAlchemy versions 2.0 to 2.1 rather than an unreleased 2.2 line.
- **Documented legacy CUBRIDdb install extra (#295)** — added README installation notes for the optional cubrid = ["CUBRID-Python"] extra while recommending the pure-Python pycubrid driver for new projects.
- **Documentation and metadata updates (#293, #294)** — documented that CUBRID treats LIST as a synonym for SEQUENCE in docs/TYPES.md, noted canonical isolation level return names in docs/ISOLATION_LEVELS.md (#293), and pointed the pyproject.toml Documentation URL to the published site https://cubrid-lab.github.io/sqlalchemy-cubrid/ matching the README badge (#294).

### CI
- **Integration dependencies and upstream canaries (#318, #323)** — installed pycubrid using the declared [pycubrid] extra (pycubrid>=1.3.2,<2.0) in async integration jobs (#318), added live CUBRID 11.4 integration runs against pycubrid@main in upstream-canary, and hardened Alembic autogenerate test patching for alembic>=1.14 with bounds tightened to >=1.7,<2.0 (#319, #323).
- **SQLAlchemy canary retargeted to 2.1 (#312)** — retargeted and renamed the experimental canary job from 2.2 to --pre "SQLAlchemy>=2.1.0b1,<2.3" to track available pre-releases (#206, #231, #312).
- **Pinned Ruff lint rules and resolved import warnings (#271, #268)** — declared explicit ruff rule selection select = ["E4", "E7", "E9", "F"] to prevent lint failures from expanded default sets (#252, #267, #271), and removed an unused re import in test/test_packaging.py (#257, #268).

## [1.6.0] - 2026-07-18

This release strengthens schema reflection and SQLAlchemy compatibility. Primary-key and unique-constraint metadata are more reliable, with additional safeguards for changes to SQLAlchemy internals.

### Changed
- **FK reflection code extracted into testable helper (#120)** — `_get_foreign_keys_from_ddl()` is now a standalone method. CUBRID system catalog views do not expose FK referenced-table/column metadata, so DDL parsing remains the sole FK reflection path. The extraction improves unit test isolation.

### Fixed
- **`bind_with_type` private API insulation (#231)** — `bind_with_type()` in `_compat.py` called `element._clone()` without a guard. If SQLAlchemy renames or removes `_clone()` in a future release (e.g. 2.2+), the dialect would crash with `AttributeError`. Added `try/except AttributeError` fallback that constructs a fresh `BindParameter` with the same key, value, type, and unique flag. This path only fires if SA changes the private API; the existing `_clone()` path remains the primary code path for SA 2.0–2.1.
- **PK constraint name reflection fixed (#120)** — `get_pk_constraint()` queried the non-existent `db_constraint` system view (CUBRID has no such view in any version), causing the PK constraint name to always be `None` in production. The query now targets `_db_index` (`is_primary_key = 1`), the authoritative system catalog for index metadata. Constraint names like `pk_users` are now correctly reflected.
- **Unique constraint reflection hardened via system catalog (#120)** — `get_unique_constraints()` now queries `_db_index` (`is_unique = 1`, excluding PK/FK auto-indexes) and resolves column names via `SHOW INDEXES` as the primary path, with the DDL regex as a fallback. This eliminates brittle regex parsing when the system catalog is available, matching the proven pattern already used by `get_indexes()`.

### CI
- **SA 2.2 canary bumped (#231)** — the `sqlalchemy-22-canary` CI job now installs `sqlalchemy>=2.2.0b1` (was `>=2.1.0b1`, which is no longer a pre-release). Added `continue-on-error: true` so canary failures warn but don't gate PRs — pre-release breakage is expected and shouldn't block development.
- **CI lint now uses pinned ruff version (#252)** — the lint job used `pip install ruff` (unpinned). Now installs from `.[dev]` extras to match the pinned `ruff==0.15.21` in `pyproject.toml`.

## [1.5.1] - 2026-07-18

This maintenance release makes unsupported SQLAlchemy operations fail explicitly instead of silently falling back to unexpected behavior.

### Upgrade notes

Applications that previously called `.returning()` without an immediate error must change those statements; the dialect does not provide server-side `RETURNING` support.

### Fixed

- **Reject unsupported `RETURNING` statements** — insert, update, and delete statements using `.returning()` now raise `CompileError` rather than silently using an unrelated primary-key retrieval path. For generated primary keys, use `result.inserted_primary_key` where applicable ([#229](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/229)).
- **Declare two-phase transactions unsupported** — the dialect explicitly disables two-phase commit support, allowing SQLAlchemy's compatibility tests to skip operations that CUBRID does not support through this dialect ([#230](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/230)).



## [1.5.0] - 2026-05-23

This release expands SQLAlchemy 2.1 compatibility and improves asynchronous test reliability. Check the dependency range and compatibility notes when upgrading.

### Added
- **SQLAlchemy 2.1 / forward-compat shims for SA 2.2 (#206)** — dependency upper bound bumped to `<2.3` (now `sqlalchemy>=2.0,<2.3`), enabling installation on SA 2.1 and future 2.2 releases. New `CubridCompiler.update_post_criteria_clause` override routes the existing `cubrid_limit` LIMIT rendering through the SA 2.1 hook that replaced `update_limit_clause`. `_render_json_extract_from_binary` now recognises `Float` as a numeric affinity since SA 2.1 split it out of `Numeric`, restoring `CAST(... AS DOUBLE)` emission for `JSON[...].as_float()`. `AsyncAdapt_pycubrid_connection.await_` is redeclared as a class-level staticmethod because SA 2.1 dropped the inherited attribute on `AsyncAdapt_dbapi_connection`. Cross-version offline test suite (639 tests) green on both SA 2.0.49 and SA 2.1.0b2.

### Performance
- **Native pycubrid ping causally validated** — Tier 2 ORM benchmark in [cubrid-benchmark`2026-04-22_native-ping-hotpath`](https://github.com/cubrid-lab/cubrid-benchmark/tree/main/experiments/orm-overhead/runs/2026-04-22_native-ping-hotpath) (paired same-version A/B, 7 trials, bootstrap 95% CI) confirms `do_ping()` native CHECK_CAS path delivers a practical pre-ping hot-path win: SQLAlchemy Core `checkout_select_by_pk` +108.2% throughput [+107.8, +109.6], ORM `session_select_by_pk` +42.1% [+41.8, +43.9], with p50/p95 latency also reduced. Effect applies to short-lived checkout/session workloads with `pool_pre_ping=True` (typical web request pattern); steady-state long-connection workloads are unaffected.

### CI
- **`sqlalchemy-22-canary` CI job promoted to gating (#206)** — previously `continue-on-error: true` against a non-existent `sqlalchemy>=2.2.0b1`. Now installs `--pre "sqlalchemy>=2.1.0b1,<2.3"` so the job actually exercises the latest available SA pre-release and fails the build on regressions.

### Tests
- **Async integration stability for issue #208** — `test/test_aio_integration.py` now seeds per-test data instead of relying on module-shared CRUD state, adds live `pool_pre_ping=True` recovery coverage after an internal async transport drop, and verifies async SQLAlchemy INSERT returns `lastrowid` without adding a new `AsyncAdapt_pycubrid_connection.get_last_insert_id()` passthrough because async pycubrid already populates `cursor.lastrowid` and the dialect retains SQL fallback.

## [1.4.3] - 2026-05-13

This patch improves collection-type reflection and SQLAlchemy 2.1 compatibility, while adding documentation for MERGE column resolution.

### Added
- **`visit_double` alias** — forward compatibility with SQLAlchemy 2.1 which compiles `Double` via `visit_double()` (#206)
- **MERGE column resolution docs** — column resolution rules and error reference added to `DML_EXTENSIONS.md` (#207)
- **Collection member split tests** — `_split_collection_members` unit tests with paren-depth guard (#204)

### Fixed
- **Paren-depth-aware collection member split** — reflection now correctly splits nested generic types like `NUMERIC(15,2)` inside `SET`/`MULTISET`/`SEQUENCE` (#204)
- **Collection member type params preserved** — compilation and reflection retain precision/scale for parameterized member types (#194)
- **Oracle review fixes** — type args, timezone semantics, and regression test gaps addressed (#203)

## [1.4.2] - 2026-04-21

This release improves connection-pool health checks for the synchronous and asynchronous pycubrid dialects.

### Upgrade notes

Applications using the `[pycubrid]` extra must meet the updated minimum driver version. The change affects connection health checks, not application SQL.

### Changed

- **Faster connection health checks** — `pool_pre_ping` uses the driver's native `Connection.ping()` or `AsyncConnection.ping()` rather than a SQL query. This reduces the extra round trip needed to validate a pooled connection ([#149](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/149)).
- **Updated pycubrid requirement** — installing the `[pycubrid]` extra now requires `pycubrid>=1.3.2,<2.0` to provide the native ping interface for both dialects.



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
- **pycubrid (sync) compatibility** — now requires `>=1.2.0` for full feature parity
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

- **Re-release of 1.2.2** from current `main` HEAD. The PyPI 1.2.2 artifact was
  built from an older commit (pre-async-dialect, pre-#120 fix), so it shipped
  without the #120 fix and without the `cubrid.pycubrid` and `cubrid.aiopycubrid`
  entry points. PyPI 1.2.2 is not yanked; do not pin `==1.2.2`.
- No source code changes vs. `main` — same fixes as listed under [1.2.2] below,
  now actually shipped to PyPI.

## [1.2.2] - 2026-04-19

The intended source changes fix Alembic autogenerate reflection, but the published PyPI 1.2.2 artifact was built from an older commit: it lacks the #120 fix and the `cubrid.pycubrid` / `cubrid.aiopycubrid` entry points. **Install 1.2.3 instead.**

### Fixed

- **Alembic autogenerate false-positive diffs** (#120):
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
- **`compare_type` for unbounded VARCHAR**: `CubridImpl.compare_type()` now
  treats CUBRID's `VARCHAR(1073741823)` (the physical storage for `STRING`,
  `CLOB`, `TEXT`, and `String` without a length) as equivalent to SQLAlchemy's
  `Text()`, `CLOB()`, and `String()` (no length), eliminating false-positive
  type-change diffs in Alembic autogenerate.

## [1.2.1] - 2026-04-19

This patch fixes asynchronous engine creation and JSON column inserts, and expands async integration coverage.

### Fixed

- **Async dialect**: Add missing `get_pool_class()` override returning
  `AsyncAdaptedQueuePool` — `create_async_engine()` now works correctly (#116)
- **JSON serialization**: Initialize `_json_serializer` / `_json_deserializer`
  attributes in `CubridDialect.__init__()` — ORM `JSON` column inserts no
  longer raise `AttributeError` (#117)

### Documentation

- Async usage sample (`samples/async_basic.py`)

### Tests

- 16 async E2E integration tests (`test/test_aio_integration.py`)

## [1.2.0] - 2026-04-18

This release adds JSON columns, JSON path expressions, and typed JSON access for CUBRID 10.2 and newer.

### Added

- **JSON type support** (CUBRID 10.2+)
  - `JSON` type class subclassing `sqltypes.JSON`
  - `JSONIndexType` and `JSONPathType` for path expression formatting
    (with embedded-quote escaping per CUBRID JSON path grammar)
  - `visit_JSON` type compiler emitting `JSON` DDL
  - JSON path expressions via `JSON_EXTRACT` (`col["key"]`, `col[("a", "b")]`)
  - Typed access via `as_boolean`, `as_integer`, `as_numeric`, `as_float`, `as_string`
    using CASE / CAST / `JSON_UNQUOTE` as appropriate
  - JSON null → SQL NULL handling with CASE expressions for typed access
  - `colspecs` mapping: generic `sa.JSON` → dialect `JSON`
  - `ischema_names` mapping: `"JSON"` → `JSON` for reflection
  - 47 offline tests (`test/test_json.py`)

### Fixed

- Version consistency: synchronized `__version__` in `sqlalchemy_cubrid/__init__.py`
  with `pyproject.toml` (was 1.0.0 vs 1.1.0)
- Removed unused imports flagged by `ruff` in `aio_pycubrid_dialect.py` and
  `test/test_aio_pycubrid_dialect.py`

## [1.1.0] - 2026-04-18

This release introduces the asynchronous pycubrid dialect through the `cubrid+aiopycubrid://` connection URL.

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

- **Compatibility policy** — this release established the 1.x compatibility contract: the
  public API follows semantic versioning, and breaking changes were to occur only in major
  version bumps (2.0+). This policy was later revised: individually reviewed
  dialect-specific convenience APIs may change in a later 1.x MINOR; core SQLAlchemy and
  database semantics remain protected (#1115, see
  [the 1.x API policy](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/RELEASING.md#public-api-compatibility-in-1x)).
- **Supported environments** — Python 3.10, 3.11, 3.12, 3.13, 3.14; CUBRID 10.2, 11.0, 11.2,
  11.4; SQLAlchemy 2.0–2.1 (`>=2.0,<2.2`); Alembic >=1.7.
- **Known limitations** — `RETURNING` clauses not supported (CUBRID limitation); no
  `Sequence` support (CUBRID uses `AUTO_INCREMENT`); native `BOOLEAN` not available (mapped
  to `SMALLINT`); lateral joins and writable CTEs not supported; `RELEASE SAVEPOINT` is a
  no-op.

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

### Added
- `docs/SUPPORT_MATRIX.md`: Comprehensive support matrix documenting SQLAlchemy versions,
  Python versions, CUBRID versions, driver compatibility, feature support, type mappings,
  and known limitations — defines the 1.0 support boundary
- Documents private SQLAlchemy API usages that require the `<2.2` version pin
- Clarified public documentation to state SQLAlchemy 2.0–2.1 support explicitly

### Changed
- **pycubrid dependency**: Pin optional `pycubrid` dependency to `>=0.6.0` — required for
  tuple-based `fetchall()` return type introduced in pycubrid v0.6.0 (#72)
- Version bumped to 0.8.0 (stabilization release on path to 1.0)

## [0.7.1] - 2026-03-13

This patch corrects UTC timestamp compilation, primary-key index filtering, and view detection in schema inspection.

### Fixed
- **`visit_utc_timestamp_func`**: Compile `func.utc_timestamp()` to `UTC_TIMESTAMP()` instead of `UTC_TIME()`, returning a full datetime value instead of time-only (#53).
- **`get_indexes()`**: Fix PK index filtering — read `is_primary_key` from column 0 of the single-column query result instead of unreachable column 6, so primary-key indexes are properly excluded (#54).
- **`has_table()`**: Recognize views as existing objects by accepting `class_type IN ('CLASS', 'VCLASS')` instead of only `'CLASS'` (#55).

## [0.7.0] - 2026-03-12

### Added
- **pycubrid dialect variant**: New `PyCubridDialect` class (`cubrid+pycubrid://` URL scheme)
  for using the [pycubrid](https://github.com/cubrid-lab/pycubrid) pure Python DB-API 2.0
  driver. Subclasses `CubridDialect` — inherits all SQL compilation, type mapping, and schema
  reflection. Overrides only driver-specific methods: `import_dbapi()`, `create_connect_args()`,
  `on_connect()`, `do_ping()`.
- **`PyCubridExecutionContext`**: Execution context that uses pycubrid's native `cursor.lastrowid`
  (returns `int | None` directly) with SQL `LAST_INSERT_ID()` fallback.
- **`cubrid.pycubrid` entry point**: Registered in `pyproject.toml` so SQLAlchemy auto-discovers
  the pycubrid dialect via `create_engine("cubrid+pycubrid://...")`.
- **`pycubrid` optional dependency**: `pip install "sqlalchemy-cubrid[pycubrid]"` installs pycubrid.
- **30 new offline tests**: `test/test_pycubrid_dialect.py` covering driver basics, connect args,
  on_connect, do_ping, execution context, entry point registration, isolation levels, and
  misc methods.
- **Documentation**: Updated `docs/CONNECTION.md` and `README.md` with pycubrid driver information.

### Changed
- Version bumped to 0.7.0.

## [0.6.0] - 2026-03-12

### Added
- **`MONETARY` type class**: New `TypeEngine` subclass for CUBRID's monetary data type.
  Stores monetary values with currency — internally represented as DOUBLE with currency code.
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
- Version bumped to 0.6.0.

### Investigated (Blocked)
- **SQLAlchemy 2.1 compatibility**: SA 2.1 does not exist yet (latest: 2.0.48).
  All 396 tests pass with SA 2.0.48 — readiness confirmed.
- **Async DBAPI support**: CUBRID Python driver has no async support — blocked.

## [0.5.0] - 2026-03-12

### Added
- **`REPLACE INTO` statement**: New `Replace` DML construct and `replace()` factory function.
  `replace(table).values(...)` generates `REPLACE INTO table (...) VALUES (...)` syntax.
  Exported from `sqlalchemy_cubrid` top-level package.
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

### Investigated (Not Supported)
- **Lateral joins**: CUBRID does not support `LATERAL` subqueries — syntax error in 11.2.
- **Full-text search**: CUBRID has no `MATCH … AGAINST` syntax or full-text index support.

### Changed
- `docs/FEATURE_SUPPORT.md`: Added recursive CTE, lateral joins, full-text search, query trace,
  and REPLACE INTO rows. Updated Known Limitations & Roadmap section.
- `docs/DML_EXTENSIONS.md`: Added REPLACE INTO, ODKU subquery values, and Query Trace sections.
- Version bumped to 0.5.0.

## [0.4.0] - 2026-03-12

### Added
- **Error code mapping**: `is_disconnect()` detects dropped connections via string-based message
  matching (14 patterns) and numeric CUBRID CCI error codes (-21003, -21005, -10005, -10007).
- **`_extract_error_code()`**: Extracts numeric error codes from CUBRID DBAPI exceptions
  (supports both integer args and string-embedded codes like "-21003 message").
- **`do_ping()`**: Connection liveness check using CUBRID Python driver's native `ping()`
  method — enables SQLAlchemy's `pool_pre_ping` feature.
- **Connection pool tuning guide**: `docs/CONNECTION.md` expanded with pool configuration
  recommendations (`pool_size`, `pool_recycle`, `pool_pre_ping`), CUBRID broker timeout
  interaction, disconnect detection, and error code mapping documentation.
- **CUBRID-Python driver compatibility matrix**: `docs/DRIVER_COMPAT.md` documenting tested
  driver versions, CUBRID server compatibility, and known issues.
- **Python 3.14 support**: Added to CI matrix and `pyproject.toml` classifiers.
- **44 new offline tests**: Comprehensive coverage for `is_disconnect()` (14 message patterns,
  4 error codes, edge cases), `_extract_error_code()` (7 tests), `do_ping()` (2 tests),
  `postfetch_lastrowid` validation (5 tests), and disconnect message integrity (3 tests).

### Changed
- CI integration test matrix expanded: Python {3.10, 3.12, 3.14} × CUBRID {11.4, 11.2, 11.0, 10.2}.
- `pyproject.toml`: Added `Programming Language :: Python :: 3.14` classifier.

## [0.3.2] - 2026-03-12

### Added
- `docs/CONNECTION.md`: Connection guide — URL format, driver setup, troubleshooting.
- `docs/TYPES.md`: Type mapping reference — standard types, CUBRID-specific types, collection types, boolean handling.
- `docs/ISOLATION_LEVELS.md`: Isolation level guide — all 6 CUBRID levels, dual-granularity model, configuration.
- `docs/DML_EXTENSIONS.md`: DML extensions reference — ON DUPLICATE KEY UPDATE, MERGE, GROUP_CONCAT, TRUNCATE, FOR UPDATE, index hints.
- `docs/ALEMBIC.md`: Alembic migration guide — setup, configuration, limitations, batch workarounds.
- `docs/DEVELOPMENT.md`: Development guide — setup, testing, Docker, coverage, CI/CD pipeline.

### Changed
- `README.md`: Rewritten as a concise landing page (~80 lines); all detailed content moved to `docs/` files.
- `docs/source/index.rst`: Added links to all new documentation files.
- `docs/FEATURE_SUPPORT.md`: Updated version reference from v0.3.0 to v0.3.2.

## [0.3.1] - 2026-03-12

### Fixed
- README: Fixed lint badge referencing deleted `pre-commit.yml` workflow — now points to `ci.yml`.
- SECURITY.md: Added v0.2.x and v0.3.x to supported versions table.
- `docs/source/index.rst`: Replaced Sphinx quickstart boilerplate with proper project documentation.
- `docs/source/conf.py`: Updated version to 0.3.0, added `viewcode` and `intersphinx` extensions.
- `docs/source/sqlalchemy_cubrid.rst`: Added `dml` and `alembic_impl` module autodoc sections.
- `samples/create_engine.py`: Modernized to SA 2.0 API (`text()`, context manager).
- `samples/cubrid_datatypes.py`: Modernized to SA 2.0 API (`metadata.create_all`, CUBRID types).
- `samples/env.sample`: Replaced hardcoded external IP with `localhost`.

### Removed
- Removed legacy files superseded by `pyproject.toml`: `setup.py`, `setup.cfg`, `CHANGES.rst`, `requirements.txt`, `requirements-dev.txt`, `install_cubrid_python.sh`.
- Removed duplicate `pre-commit.yml` GitHub Actions workflow (functionality covered by `ci.yml`).
## [0.3.0] - 2026-03-12

### Added
- Alembic migration support via `CubridImpl` (`alembic.ddl` entry-point).
  Install with `pip install sqlalchemy-cubrid[alembic]`.
- `test/test_alembic.py`: 8 tests covering import, registry, entry-point, and import-error scenarios.

### Changed
- Edge-case tests added for compiler.py, dml.py, and dialect.py — coverage raised from 97% to 99% (306 → 314 tests).
- `docs/FEATURE_SUPPORT.md`: Alembic row updated from ❌ to ✅.

## [0.2.0] - 2026-03-12

### Added
- `FOR UPDATE` clause support (`SELECT … FOR UPDATE [OF col1, col2]`).
- `INSERT … DEFAULT VALUES` and empty INSERT support.
- Window functions (`ROW_NUMBER`, `RANK`, `DENSE_RANK`, `NTILE`, `LAG`, `LEAD`, etc.) with `OVER()` clause.
- `NULLS FIRST` / `NULLS LAST` ordering in ORDER BY.
- Table and column `COMMENT` support — inline DDL, `ALTER` statements, and schema reflection.
- `IF NOT EXISTS` / `IF EXISTS` DDL support for `CREATE TABLE` and `DROP TABLE`.
- `ON DUPLICATE KEY UPDATE` via CUBRID-specific `sqlalchemy_cubrid.insert()` construct (MySQL-compatible syntax).
- `MERGE` statement via `sqlalchemy_cubrid.merge()` with full `WHEN MATCHED` / `WHEN NOT MATCHED` clause support.
- `GROUP_CONCAT` aggregate function compilation.
- `TRUNCATE TABLE` autocommit detection.
- Index hint documentation (`USING INDEX`, `USE INDEX`, `FORCE INDEX`, `IGNORE INDEX` via SQLAlchemy’s built-in `with_hint()` / `suffix_with()`).
- `docs/FEATURE_SUPPORT.md`: Comprehensive feature support matrix updated with all new capabilities.

## [0.1.0] - 2026-03-12

### Changed
- **BREAKING**: Minimum Python version raised from 3.6 to 3.10.
- **BREAKING**: Minimum SQLAlchemy version raised from 1.3 to 2.0.
- Complete rewrite of all dialect modules for SQLAlchemy 2.0 compatibility.
- Modernized project infrastructure (`pyproject.toml`, ruff linting, GitHub Actions CI).

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

### Removed
- `.pre-commit-config.yaml`: Replaced by ruff configuration in `pyproject.toml`.

## [0.0.1] - 2022-01-01

### Added
- Initial release with basic CUBRID dialect for SQLAlchemy 1.3.
