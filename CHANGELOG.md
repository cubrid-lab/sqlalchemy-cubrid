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

- **SQLAlchemy 2.0.53 or later required** — the dependency floor rises from `sqlalchemy>=2.0` to `sqlalchemy>=2.0.53` (still `<2.2`), the oldest release CI tests, because some earlier 2.0 releases cannot import the dialect; projects pinned to SQLAlchemy 2.0.0–2.0.52 must upgrade ([#1428](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1428), [#1434](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1434)) by @yeongseon.

### Changed

- **Async sample connection URL** — `samples/async_basic.py` reads its database URL from `CUBRID_SAMPLE_URL` and falls back to the local quickstart lab, so another database no longer requires editing the file ([#1403](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1403), [#1409](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1409)) by @yeongseon.

### Removed

- **Unused dialect attributes** — `CubridDialect` no longer defines `supports_twophase_commit` and `supports_native_lateral`, which SQLAlchemy 2.0 and 2.1 never read; unreachable compatibility branches and repeated inherited settings were removed too, with no change to compiled SQL or driver behavior ([#1427](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1427), [#1433](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1433)) by @yeongseon.

### Fixed

- **Async sample** — `samples/async_basic.py` now disposes its async engine in a `finally`, so an error while connecting, inserting or cleaning up no longer skips `engine.dispose()` ([#1381](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1381), [#1387](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1387)) by @Dio77799 (first contribution 🎉).
- **Basic engine sample** — importing `samples/create_engine.py` no longer opens a database connection; the query runs in `main()` and `engine.dispose()` runs in a `finally` even when the query fails ([#1380](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1380), [#1388](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1388)) by @Dio77799.

### Performance

- **Reflection reuses table DDL** — one SQLAlchemy Inspector now reads `SHOW CREATE TABLE` once per table for column defaults, foreign keys and the unique-constraint fallback; `Inspector.clear_cache()` refreshes it ([#1396](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1396), [#1400](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1400)) by @imshah-id (first contribution 🎉).

### Documentation

- **Lesson screenshots** — Lesson 2 (first query) and Lesson 4 (rollback) of the Start here course each show a terminal screenshot of the real script output, in English and Korean; the text outputs are unchanged ([#1397](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1397), [#1419](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1419)) by @yeongseon.
- **Package docstring** — the `sqlalchemy_cubrid` module docstring now calls the `cubrid+cubriddb://` C-extension driver supported instead of legacy, matching docs/DRIVER_COMPAT.md ([#1383](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1383), [#1399](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1399)) by @RiccardoBifulco.
- **`trace_query` examples use the recommended driver** — the `sqlalchemy_cubrid/trace.py` docstring examples now connect with `cubrid+pycubrid://` to a disposable local lab database and ask readers to supply their own connection values ([#1377](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1377), [#1379](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1379)) by @RiccardoBifulco (first contribution 🎉).
- **Contributor setup** — CONTRIBUTING.md adds a Windows PowerShell setup path, not yet verified on Windows ([#1364](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1364), [#1376](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1376)) by @ebanatrm100 (first contribution 🎉). The manual setup in docs/DEVELOPMENT.md now installs the `[pycubrid]` extra for live tests and keeps a driver-free option for offline work ([#1384](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1384), [#1394](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1394)) by @Kareenashinde15 (first contribution 🎉).
- **Improvement ideas** — a new issue form invites improvement ideas, and CONTRIBUTING.md explains how problem reporters are credited ([#1398](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1398)) by @yeongseon.
- **Async example warning** — the `samples/async_basic.py` docstring now warns that the example drops and recreates `async_sample_users`, so it should run only against a disposable database ([#1371](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1371), [#1404](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1404)) by @Hanshal-aether (first contribution 🎉).
- **Commit type and release version** — CONTRIBUTING.md explains that `feat` asks for a MINOR release and `fix`, `perf` and `docs` for a PATCH, and that changes confined to `samples/` or contributor tooling do not use `feat` ([#1415](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1415)) by @yeongseon.
- **DML example SQL** — docs/DML_EXTENSIONS.md notes that its SQL examples show values inline for readability, while SQLAlchemy sends them as bound parameters ([#1370](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1370), [#1416](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1416)) by @Kareenashinde15.

### CI

- **Unused tooling removed** — the uncalled `scripts/prepare_release.py`, the weekly `maintenance.yml` lint and security run that repeated CI, `scripts/reflection_probe.py` and the agent-review bootstrap branch that could not run were removed, with their tests and path filters ([#1429](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1429), [#1435](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1435)) by @yeongseon.
- **Publisher workflow names** — PyPI releases are now published by `publish.yml`, job `publish-production`, in the GitHub environment `production`; the release tooling and recovery docs use the new names ([#1410](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1410), [#1412](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1412)) by @yeongseon.
- **Reflection comparison with several model bases** — `scripts/reflection_probe.py --compare` now stops with an explicit error when a module declares more than one `MetaData` registry, instead of silently comparing only the first ([#1382](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1382), [#1385](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1385)) by @bfs2021.
- **Benchmark scripts leave existing tables alone** — `scripts/profile_orm.py` and `scripts/bench_dialect_baseline.py` now stop with an error when their fixed table (`bench_users`, `bench_dialect_baseline`) already exists, and drop only a table they created, also after a failure ([#1401](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1401), [#1406](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1406), [#1402](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1402), [#1407](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1407)) by @Dio77799.

### Tests

- **Driver version report** — a new offline test checks that `scripts/report_driver_versions.py` probes both drivers with a configured database URL ([#1375](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1375), [#1393](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1393)) by @aka-khannaji (first contribution 🎉).
- **Async sample live run** — `samples/async_basic.py` now runs unmodified against the integration lab, with checks that its rows are real, its table is gone afterwards and a connection failure exits nonzero ([#1403](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1403), [#1414](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1414)) by @yeongseon.

## [1.12.4] - 2026-11-20

This release ships the changes prepared for 1.12.3, which was merged but never published because its release build failed on a new CI runner image. It revises one deprecation warning, rewords the missing-CUBRIDdb error and raises the setuptools version needed to build from source. It also fixes paged queries that could return the wrong rows, `BIGINT` results returned as strings and `Boolean` results read as `True` from the string `'0'`, with the PyPI CUBRIDdb 9.3 driver. SQL generation for other drivers, reflection and connection behavior are unchanged.

### Upgrade notes

- **Revised deprecation notice for ignored type arguments (#892)** — the `DeprecationWarning` for the ignored `SMALLINT`/`BIGINT` `display_width` argument (including positional `SMALLINT(11)`) and the string-type `values` argument now says they may be removed in a future reviewed **1.x MINOR** instead of the next major release. The arguments are still accepted in this release and generate no different DDL. Migrate `SMALLINT(11)` to `SMALLINT()`, `BIGINT(20)` to `BIGINT()` and `VARCHAR(30, values=["x"])` to `VARCHAR(30)`, or pin a narrower version range. The 1.x compatibility policy behind this change is in [RELEASING.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/RELEASING.md#public-api-compatibility-in-1x) ([#1115](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1115), [#1122](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1122)) by @yeongseon.
- **Building from source needs setuptools 77 or newer** — the build backend requirement is now `setuptools>=77` for SPDX license metadata. Installing the published wheel is unaffected; source builds without build isolation need an up-to-date setuptools ([#1113](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1113)) by @CloudCorpRecords.

### Changed

- **Missing-CUBRIDdb error** — the `Could not import CUBRIDdb` error for `cubrid://` and `cubrid+cubriddb://` URLs no longer calls the CUBRIDdb C-extension driver legacy or the PyPI `CUBRID-Python` releases untested. It lists both installation paths (`sqlalchemy-cubrid[cubriddb]` or an official CUBRID/cubrid-python source build) and the pure-Python `cubrid+pycubrid://` alternative. The message prefix and the chained original `ImportError` are unchanged ([#1150](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1150)) by @yeongseon.
- **First-connect warning for the PyPI CUBRIDdb 9.3 driver** — the `SAWarning` emitted when the loaded CUBRIDdb is older than 11.3 no longer calls this supported driver line untested or tells users to switch away. It now names the limitations the dialect cannot work around, as observed with CUBRID 11.4: `bytes` values cannot be bound, constraint violations are raised as `DatabaseError` instead of `IntegrityError`, and the server rejects string-bound parameters in recursive CTEs and `SET` values. It also points to pycubrid and the v11.3.0.51 source build as alternatives. The warning still fires once per engine, the connection is unchanged, and the documented `message="CUBRIDdb .* is older"` filter still matches ([#1142](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1142)) by @yeongseon.

### Removed

- **One-time historical release sync tools (#1182)** — the three historical Release sync and audit scripts, their tests, the audit record `HISTORICAL_RELEASE_AUDIT.md` (+ Korean) and the v1.12.2 Release body backup are removed. They served the one-time synchronization of published Release bodies, which finished when #1220 verified all 28 published bodies against `CHANGELOG.md`. Release preparation and publishing are unchanged ([#1182](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1182)) by @yeongseon.
- **Unused repository files (#1182)** — a stray `uv.lock` (nothing runs `uv sync`/`uv lock`; CI uses `uv pip install --group`), `codecov.yml` (no workflow uploads to Codecov), the unreferenced `docs/javascripts/mermaid-init.js` (diagrams render through `pymdownx.superfences`), the placeholder `test/fixtures/README.md`, the VHS script `demos/orm-demo.tape` (the published `docs/demo.gif` is rendered by `demos/render_gif.py` from `demos/orm-demo.json`) and the never-published MP4 recording kit (`demos/orm-demo-mp4.tape`, `demos/orm_alembic_video.py`, `demos/VIDEO_RECORDING.md`, `docs/assets/videos/.gitkeep`) are removed. No installed package code or supported behavior changes; refs [#1182](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1182).
- **Dated benchmark results and the benchmark artifact contract (#1290)** — the four dated result directories under `benchmarks/`, the artifact manifest tool `scripts/bench_artifact.py` with its tests, and the `--source-sha` install verification and `--server-image-digest`, `--host-label` and `--comparable-group` options of `scripts/bench_dialect_baseline.py` are removed. `docs/PERFORMANCE.md` (+ Korean) is shortened to performance guidance, known limitations and how to run the kept local scripts: `scripts/bench_compile.py`, `scripts/profile_orm.py` and `scripts/bench_dialect_baseline.py`, whose workloads are kept because cubrid-benchmark does not reproduce them yet; their result checks are unchanged, and the JSON report keeps the environment and workload identity but no longer records the install provenance fields or the image digest, host label and comparable-group labels. Reproducible performance experiments belong in [cubrid-benchmark](https://github.com/cubrid-lab/cubrid-benchmark). Dialect runtime behavior, the dialect's tests and release checks are unchanged ([#1290](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1290)) by @yeongseon.
- **`make check-all`** — the alias of `make check`, deprecated in 1.11.5 and announced for removal after the next minor release (1.12.0), is removed. Run `make check` instead; `make test-offline` remains an alias of `make test` ([#1313](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1313)) by @yeongseon.

### Fixed

- **Paged queries with the PyPI CUBRIDdb 9.3 driver** — this driver sends every bound parameter as a string, and CUBRID then applied a bound `LIMIT ?, ?` incorrectly: `.offset(1).fetch(2)` returned four rows instead of two, with no error. When the connected CUBRIDdb is older than 11.3, the plain integers of a query with an offset (`LIMIT offset, count`) are now written into the SQL at execution time; such a statement cannot run through `executemany()`. A limit without an offset, pycubrid and CUBRIDdb 11.3 or later still use bound parameters ([#1299](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1299), [#1300](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1300)) by @yeongseon.
- **`BIGINT` results with the PyPI CUBRIDdb 9.3 driver** — this driver returns `BIGINT` values, including `COUNT(*)` and `ROWNUM`, as strings (`'5'`). When the connected CUBRIDdb is older than 11.3, integer-typed and untyped (`text()`) result columns that the driver reports as `BIGINT` now return `int`. Other column types are never parsed, and pycubrid and CUBRIDdb 11.3 or later are unchanged ([#1145](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1145), [#1301](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1301)) by @yeongseon.
- **`Boolean` results without a fixed column type with the PyPI CUBRIDdb 9.3 driver** — this driver returns result columns that have no fixed type, such as `PERCENTILE_DISC(...) WITHIN GROUP (ORDER BY <condition>)`, as strings, and SQLAlchemy's `Boolean` result processor turned `'0'` into `True`. When the connected CUBRIDdb is older than 11.3, a string in a `Boolean` result column is now read as a number first, so `'0'` returns `False`; non-numeric text raises `ValueError` instead of returning `True`. Other types, pycubrid and CUBRIDdb 11.3 or later are unchanged ([#1143](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1143)) by @yeongseon.
- **INSERT with a driver that lacks `get_last_insert_id()`** — with the PyPI CUBRIDdb 9.3 driver, a single-row INSERT on a connection that had not yet inserted into an `AUTO_INCREMENT` column failed with `TypeError: int() argument must be ... not 'NoneType'`, even though the row was stored; Alembic's `alembic_version` insert was one example. A NULL `SELECT LAST_INSERT_ID()` now means no generated key ([#1302](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1302)) by @yeongseon.
- **`pool_pre_ping` with the PyPI CUBRIDdb 9.3 driver** — this driver has no `Connection.ping()`, so every ping failed and `pool_pre_ping=True` discarded and reopened a pooled connection on each checkout. Connections without `ping()` are now checked with `SELECT 1`; CUBRIDdb 11.3 and pycubrid are unchanged ([#1304](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1304)) by @yeongseon.

### Documentation

- **Release-note credit review checklist** — `docs/RELEASE_NOTES_STYLE.md` and its Korean version add a six-point checklist from the audit of all published release notes: map entries to the implementing PR, credit co-authors only for substantive human commits, never credit agents or bots, leave summaries and dependency updates uncredited, verify first contributions, and check that each change is inside the release's tag range ([#1220](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1220)) by @yeongseon.
- **`SystemError` after closing a PyPI CUBRIDdb 9.3 connection twice** — `docs/DRIVER_COMPAT.md` and its Korean version now give the cause and a driver-only reproduction, and explain why the dialect keeps closing connections explicitly: leaving the close to the driver's deallocator avoids the error but left a busy broker session for every discarded pooled connection in a test on CUBRID 11.4 ([#1320](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1320)) by @yeongseon.
- **PyPI CUBRIDdb 9.3 limitations after the dialect fixes** — `docs/DRIVER_COMPAT.md`, the support matrix and the README note (with their Korean versions) no longer say that `BIGINT` results stay strings, that paged queries can return the wrong rows or that `pool_pre_ping` reopens every connection with this driver; they now say what the dialect converts or works around and what remains a driver limitation. They record the manually dispatched `cubriddb-pypi.yml` lane run on `main` and the `SystemError` after a connection is closed twice ([#1145](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1145), [#1320](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1320), [#1328](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1328)) by @yeongseon.
- **Temporary tooling lifecycle** — the contributor guide and its Korean translation now say what a PR that adds a temporary script, probe or repair tool records (purpose, owner, removal trigger, evidence location, next review point), to prefer manual execution, and what to map before removing one. Permanent release automation and supported older-driver compatibility paths are not temporary tooling. The pull request template has an optional prompt ([#1183](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1183), [#1316](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1316)) by @yeongseon.
- **First connection and troubleshooting** — troubleshooting now shows the actual missing-pycubrid and authentication error messages, explains missing `greenlet` errors for async engines and broker readiness, and adds Windows virtual-environment setup to the first-connection lesson and Apple silicon options for the CUBRID lab. Translated READMEs guide readers to their first connection with `cubrid+pycubrid://` URLs and no longer overstate live CI coverage ([#1116](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1116), [#1118](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1118), [#1124](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1124), [#1126](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1126), [#1127](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1127), [#1131](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1131), [#1134](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1134), [#1137](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1137), [#1073](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1073), [#1074](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1074), [#1075](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1075), [#1080](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1080), [#1084](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1084), [#1087](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1087), [#1088](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1088)) by @yeongseon.
- **CUBRIDdb troubleshooting** — the entry quotes the actual `Could not import CUBRIDdb` error and lists the supported `sqlalchemy-cubrid[cubriddb]` and official source-build installation paths, keeping the heading and anchor correction first proposed in #1110 ([#1205](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1205)) by @yeongseon.
- **CUBRIDdb driver support policy** — the support matrix and driver guides now list both CUBRIDdb driver lines as supported: the PyPI `CUBRID-Python` 9.3.0 release installed by the `[cubrid]` / `[cubriddb]` extras, which are no longer called deprecated, and a build of the cubrid-python v11.3.0.51 source release. A separate verification table shows what was actually run: CI tests the v11.3.0.51 build, while the 9.3.0 line is supported but not verified on current Python versions, and its known limitations from an earlier run (`BIGINT` returned as `str`, 25 integration failures) stay documented. pycubrid remains the recommended driver for new projects ([#1298](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1298)) by @yeongseon.
- **CUBRIDdb installation advice** — the README (and its Korean translation), installation and troubleshooting guides, architecture overview, third-party license table and `llms.txt` no longer call the `[cubrid]` / `[cubriddb]` extras deprecated or the PyPI driver untested. They show both installation options, pointing to the known limitations of the PyPI 9.3.0 release ([#1147](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1147), [#1083](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1083)) by @yeongseon.
- **Translated driver guidance** — the German, Hindi, Russian and Chinese READMEs describe both CUBRIDdb installation options instead of calling the PyPI driver untested and the extras deprecated, and `scripts/check_support_claims.py` now also checks that the Korean support matrix keeps both driver lines supported and the PyPI 9.3.x line not reported as tested ([#1148](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1148)) by @yeongseon.
- **Feature support and versions** — corrected the CUBRID 10.2 feature-support guidance and separated database server versions from Python driver versions, with a version check that works without CUBRIDdb installed. The connection guide now links to that version terminology from its introduction ([#1117](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1117), [#1149](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1149), [#1140](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1140), [#1082](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1082), [#1312](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1312)) by @yeongseon.
- **Getting help** — the issue chooser and documentation now point to one support and questions path, and bug reports ask for the driver and URL scheme ([#1125](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1125), [#1129](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1129), [#1135](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1135), [#1077](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1077), [#1078](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1078), [#1079](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1079)) by @yeongseon.
- **Published pages** — fixed links from the documentation site and the PyPI README to repository files, made the PyPI demo render, and removed the unused Sphinx scaffold ([#1123](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1123), [#1132](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1132), [#1138](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1138), [#1076](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1076), [#1097](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1097)) by @yeongseon.
- **Historical release notes** — earlier `CHANGELOG.md` sections now use the standard headings, credit verified human contributors (#1214), restore merged changes and published details they had omitted, and correct factual errors such as the PyPI 1.2.2 statement; all 28 published GitHub Release pages were updated to match and re-verified ([#1153](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1153)) by @yeongseon.
- **Historical release notes: summaries and layout** — earlier releases gained short reader summaries of what changed for users (14 versions in one pass and seven lengthy releases in another), the v1.11.6 and v1.11.7 commit dumps were replaced with release summaries, the v1.7.0, v1.7.1, v1.9.0 and v1.12.1 notes were rewritten around user-visible changes, and the Markdown layout, spacing and duplicated release-please bullets were fixed in `CHANGELOG.md` and the published Release pages; the v1.7.0, v1.7.1, v1.8.0, v1.10.0 and v1.11.0 notes got a final pass to be easier to scan ([#1168](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1168), [#1170](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1170), [#1173](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1173), [#1174](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1174), [#1176](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1176), [#1177](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1177), [#1178](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1178), [#1179](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1179), [#1180](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1180), [#1194](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1194), [#1197](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1197), [#1213](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1213), [#1215](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1215), [#1216](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1216), [#1229](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1229), [#1246](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1246), [#1341](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1341), [#1342](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1342), [#1343](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1343), [#1345](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1345), [#1346](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1346), [#1347](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1347), [#1348](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1348), [#1358](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1358), [#1360](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1360)) by @yeongseon.
- **Historical release notes: one clarity pass per version** — the notes for v0.1.0 to v0.7.0 (including nine historical draft releases), v1.5.0, v1.7.0, v1.7.1, v1.8.0, v1.9.0, v1.10.0, v1.11.0, v1.11.5 and v1.12.0 were reworded one version at a time to say what a reader gets: upgrade guidance, SQL and connection behavior, historical driver limits, license and localization notes, and test and CI changes, with the details kept and internal tooling descriptions shortened ([#1231](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1231), [#1233](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1233), [#1249](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1249), [#1250](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1250), [#1258](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1258), [#1259](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1259), [#1260](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1260), [#1261](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1261), [#1262](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1262), [#1263](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1263), [#1264](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1264), [#1265](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1265), [#1266](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1266), [#1267](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1267), [#1268](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1268), [#1269](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1269), [#1270](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1270), [#1271](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1271), [#1272](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1272), [#1273](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1273), [#1274](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1274), [#1275](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1275), [#1276](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1276), [#1277](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1277), [#1278](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1278), [#1279](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1279), [#1280](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1280), [#1281](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1281)) by @yeongseon.
- **Historical release notes: standard headings and ordering** — earlier sections of `CHANGELOG.md` use the standard `###` headings, with the v1.6.0 and v1.7.0 sections put in the standard order, in the v1.2.1 to v1.10.0 notes (and the v1.0.0 compatibility policy is marked as revised), so they read the same way as new releases; the same passes credited verified human contributors ([#1152](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1152), [#1184](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1184), [#1188](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1188), [#1189](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1189), [#1190](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1190), [#1191](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1191), [#1192](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1192), [#1193](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1193), [#1195](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1195), [#1196](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1196), [#1200](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1200)) by @yeongseon.
- **Historical release notes: contributor credits** — credits for the human authors of earlier releases were restored and verified against the merged pull requests, from the v0.7.1 to v1.12.1 notes (for example v1.2.1, v1.2.2, v1.4.2, v1.4.3, v1.5.0, v1.5.1, v1.8.0, v1.9.0, v1.10.0, v1.11.0, v1.11.5, v1.11.6, v1.11.7, v1.12.0 and v1.12.1) ([#1198](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1198), [#1199](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1199), [#1201](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1201), [#1202](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1202), [#1221](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1221), [#1223](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1223), [#1224](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1224), [#1225](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1225), [#1226](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1226), [#1227](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1227), [#1228](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1228), [#1235](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1235), [#1236](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1236), [#1237](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1237), [#1238](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1238), [#1239](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1239), [#1240](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1240), [#1241](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1241), [#1244](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1244), [#1245](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1245), [#1282](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1282), [#1283](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1283), [#1330](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1330)) by @yeongseon.
- **Historical release notes: restored details and corrections** — merged changes and published details that earlier notes had omitted were restored (the v1.2.0 and v1.1.0 details, v1.6.0 pull request references and test results, the v0.8.0 support boundary, the v0.7.1 performance and package notes, and omitted test, CI and dependency entries of v1.10.0, v1.11.6, v1.12.1 and v1.12.2), duplicated v1.10.0 entries were removed, the v1.12.1 notes were corrected, and factual errors such as the PyPI 1.2.2 yank statement were fixed ([#1186](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1186), [#1187](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1187), [#1203](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1203), [#1204](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1204), [#1207](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1207), [#1208](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1208), [#1209](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1209), [#1210](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1210), [#1211](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1211), [#1232](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1232), [#1234](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1234), [#1242](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1242), [#1243](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1243), [#1338](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1338), [#1340](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1340)) by @yeongseon.
- **Historical release publication and audit** — historical releases were audited and guarded against retrospective synchronization mistakes, four verified GitHub Releases were synchronized safely, comparison links were completed without rewriting the original notes, the published release notes are verified after synchronization, and release notes merged without review approval were restored; the curated v1.12.1 and v1.12.2 notes were published and the 1.12.3 notes moved into `[Unreleased]` ([#1156](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1156), [#1158](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1158), [#1161](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1161), [#1167](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1167), [#1175](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1175), [#1185](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1185), [#1219](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1219)) by @yeongseon.
- **Contributor guidance and project policy** — the contributor guidance now keeps SQLAlchemy dialect contribution rules and issue and pull request evidence ownership in this repository, defines the issue handoff and development states, removes the contest deadline from the Korean README sync guidance and the organization roadmap and project-board references, says when a scoped `# type: ignore` is acceptable, and says release candidates are frozen only when their review starts; the 1.8.0 PRD is labelled a historical snapshot ([#1096](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1096), [#1101](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1101), [#1160](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1160), [#1166](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1166), [#1284](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1284), [#1286](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1286), [#1295](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1295), [#1326](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1326), [#1327](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1327)) by @yeongseon.
- **Dialect options and `MERGE` documentation** — the dialect options, the `merge()` builder and the string type arguments are documented ([#1292](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1292), [#1315](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1315)) by @yeongseon.
- **Help menu support links** — added direct links to Discussions, the issue chooser and SECURITY.md from the documentation site's Help menu ([#1294](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1294), [#1297](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1297)) by @aashnayadav (first contribution 🎉).

- **README demo** — The demo GIF no longer shows an invented 1.7.0 install line; it quotes the extra, states the `pycubrid>=1.8.0,<2.0` requirement and shows the `python` step. It is still rendered from a script, not a live install ([#1095](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1095), [#1362](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1362)) by @yeongseon.

### CI

- **Release-note publication gate (#1356)** — New release candidates must have a reader-focused introduction, curated change entries, and reasonable per-entry and total description lengths without exact duplicates. Release preparation reports violations without blocking candidate creation; final-head PR checks and the existing guarded publisher reject uncurated notes. Earlier released versions are not silently rewritten by this check ([#1356](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1356), [#1357](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1357)) by @yeongseon.
- **Manual CI lane for the PyPI CUBRIDdb 9.3 driver** — the new manual-only `cubriddb-pypi.yml` workflow installs the project with the `[cubriddb]` extra, as users do (pip and uv currently install the PyPI 9.3.0 source archive `9.3.0.0001` as 9.3.0.1), records the driver's distribution and compiled-in `_cubrid.__version__`, and runs `make integration` on Python 3.12 and CUBRID 11.4, listing every failing test. It is evidence, not a required check or release gate, and is expected to fail until the known driver limitations are resolved. The driver-version report in the other live lanes now also prints `_cubrid.__version__` ([#1146](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1146)) by @yeongseon.
- **Each change is listed once in release candidates** — when a curated `[Unreleased]` entry already cites a pull request or issue, the release changelog composer now drops the release-please entry generated for the same pull request or referenced issue, instead of listing the change twice. Generated entries without a matching reference, or crediting a contributor the curated entry does not credit, are kept, and released sections are unchanged ([#1100](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1100), [#1317](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1317)) by @yeongseon.

- **CUBRIDdb builds with GCC 14 and later** — CI builds the pinned cubrid-python v11.3.0.51 driver with two flags that newer compilers need, and the source-build guide shows them ([#1386](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1386), [#1389](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1389)) by @yeongseon.

### Tests

- **Pool recovery across CUBRID broker restarts** — live tests in `test/test_server_restart.py` run `cubrid broker restart` under a pycubrid `QueuePool`. They check that idle pooled connections are reused safely, that work interrupted by the restart fails as a disconnect and is neither stored nor replayed, and that concurrent write requests stay consistent with the table, where a request reported as failed may be stored only when its COMMIT reply was lost. Verified on CUBRID 10.2 and 11.4 with pycubrid 1.17.0 ([#1151](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1151)) by @yeongseon.
- **Async pool recovery and pool lifecycle** — the broker-restart tests now also cover the async `cubrid+aiopycubrid` engine and its `AsyncAdaptedQueuePool`: idle pooled connections are reused safely with and without `pool_pre_ping`, an interrupted transaction fails as an invalidating disconnect and is neither stored nor replayed, and the next checkout gets a new connection. `test/test_stress_pool.py` adds sync `QueuePool` checks that `pool_recycle` replaces only connections older than the limit, detected by the CUBRID server session rather than by timing, that a checkout fails with `sqlalchemy.exc.TimeoutError` after `pool_timeout` once `pool_size` and `max_overflow` are in use, and that uncommitted work is rolled back when a connection returns to the pool while its session is kept. Verified on CUBRID 10.2 and 11.4 with pycubrid 1.17.0 ([#1151](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1151)) by @yeongseon.
- **Bounded pooled request workload** — `test/test_pool_soak.py` runs a mix of short reads, committed and rolled-back write transactions and idle gaps on a sync pycubrid `QueuePool`, counts successful, failed and in-doubt requests, pool checkouts, checkins and invalidations, latency percentiles and the process RSS, file descriptors and sockets over time, then audits every write against the table. It runs for 3 seconds in every `make integration`; a longer run with a `cubrid broker restart` midway and a JSON report is manual, through `CUBRID_SOAK_SECONDS`, `CUBRID_SOAK_BROKER_RESTART` and `CUBRID_SOAK_REPORT` (see docs/DEVELOPMENT.md). Verified on CUBRID 11.4 with pycubrid 1.17.0 ([#1151](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1151)) by @yeongseon.
- **Broker restarts with the CUBRIDdb driver** — the idle-reuse and mid-transaction broker-restart tests in `test/test_server_restart.py` now run with both drivers instead of pycubrid only. With CUBRIDdb, idle pooled connections are reused after `cubrid broker restart` with and without `pool_pre_ping`, and work interrupted by the restart fails as an invalidating disconnect (`InterfaceError` -20004) that is neither stored nor replayed. Verified on CUBRID 11.4 with CUBRIDdb v11.3.0.51 and with the PyPI 9.3 release ([#1151](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1151)) by @yeongseon.
- **Bounded pooled workload with the CUBRIDdb driver** — `CUBRID_SOAK_DRIVER=CUBRIDdb` runs the sync workload in `test/test_pool_soak.py` with `cubrid://` instead of pycubrid, and the JSON report records the loaded CUBRIDdb version. 5-minute runs with a broker restart passed on CUBRID 11.4 with CUBRIDdb v11.3.0.51 and with the PyPI 9.3 release; with 9.3 the process memory grew by about 7 KiB per request, which `docs/DRIVER_COMPAT.md` now records ([#1151](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1151)) by @yeongseon.
- **Pooled request workload on the async engine** — `test/test_pool_soak.py` also runs the same request mix, audit and report as asyncio tasks on an async `cubrid+aiopycubrid` engine and its `AsyncAdaptedQueuePool`, with separate results; with `CUBRID_SOAK_REPORT` its JSON report gets an `-async` file-name suffix. The sync and async runs share one bookkeeping and audit helper, so the same durable-outcome checks apply to both. A 5-minute async run with a broker restart passed on CUBRID 11.4 with pycubrid 1.17.0, and the sync long run also passed on CUBRID 10.2 ([#1151](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1151)) by @yeongseon.
- **Compiler tests split by SQL area** — the offline compiler tests in `test/test_compiler.py` are moved, unchanged, into `test/test_compiler_dml.py` (INSERT, UPDATE, ON DUPLICATE KEY UPDATE, REPLACE, MERGE), `test/test_compiler_ddl.py` (CREATE/DROP TABLE and INDEX, comments, TRUNCATE) and `test/test_compiler_types.py` (type compiler output, rejected types, ENUM); SELECT-side and cross-statement tests stay in `test/test_compiler.py`, and shared helpers live in `test/_compiler_helpers.py`. The collected tests and their names are the same, and the new modules are added to the mutation-testing selection in `setup.cfg` ([#1291](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1291)) by @yeongseon.

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

This documentation-only patch removes obsolete agent- and tool-specific commit-message footer instructions. It does not change SQLAlchemy dialect behavior, package installation, or supported APIs.

### Documentation

- **Simplified the agent commit-message example** — removed the agent-specific and tool-specific footer guidance from the repository's commit example. This is a documentation-only update; it does not change the dialect or runtime behavior ([#1043](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1043), [commit b51b29f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b51b29fa793d12d4ec54d9ef65adb3c43cd2ae5f)) by @yeongseon.

## [1.11.6] - 2026-10-24

This maintenance release corrects a stale development-test reference and removes a temporary release-preparation override after v1.11.5 was published. Runtime SQLAlchemy dialect behavior is unchanged.

### Documentation

- **Corrected an outdated pytest test reference** — updated the development documentation so its example points to a current test rather than a stale pytest node. This is a documentation-only update; it does not change runtime behavior ([#1034](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1034), [#1033](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1033), [commit 003dca4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/003dca4d9bf79aeb1d67814c5fa8e92824216405)) by @WilliamK112.

### CI

- **Removed a temporary release-preparation override** — after v1.11.5 was successfully published, the repository removed the now-obsolete `last-release-sha` setting from `release-please-config.json`. This allows subsequent release preparation runs to resume normal tag-based discovery; it does not change the dialect's runtime behavior or rewrite previously published releases ([#1038](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1038)) by @yeongseon.

## [1.11.5] - 2026-10-24

This release fixes SQL compilation and pooled connections, and makes inline literal escaping follow the server setting. It includes the changes from unpublished v1.11.1–v1.11.4; upgrade directly from v1.11.0.

### Upgrade notes

- **MERGE and Alembic** — Use target columns or string keys in MERGE assignments; bound source-table keys now raise `CompileError`. Supply `existing_type` when altering column nullability or comments in Alembic ([#877](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/877), [#895](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/895)) by @yeongseon.
- **Reflected defaults** — String and date server defaults now reflect as quoted SQL literals. Review migration diffs that compare these defaults ([#878](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/878)) by @yeongseon.
- **Developer commands** — `make test` runs both offline lanes and `make test-fast` runs the fast suite. Use `make check` for comprehensive checks. `make docker-down` preserves the lab volume; use `make docker-clean` to delete it. The broker binds to loopback and `CUBRID_TEST_PORT` replaces `CUBRID_PORT` ([#1010](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1010), [#1017](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1017)) by @yeongseon.

### Deprecated

- **Type arguments and Make alias** — Passing ignored integer `display_width` or string-type `values` now warns; this release announced removal in a future major release. `make check-all` is a deprecated alias for `make check` ([#891](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/891), [#1010](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1010)) by @yeongseon.

### Fixed

- **SQL compilation** — Preserves aggregate ordering, compiles more Boolean projection and function expressions, and supports more CASE values ([#988](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/988), [#989](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/989), [#994](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/994)) by @yeongseon and ([#967](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/967), [#972](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/972)) by @paikend. `Select.fetch()` renders as `LIMIT`, CTEs work with INSERT/REPLACE FROM SELECT, and `on_duplicate_key_update()` supports statement caching ([#880](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/880), [#893](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/893), [#899](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/899)) by @yeongseon.
- **Reflection and connections** — Improved index reflection and autogenerate, pooled error classification and isolation retries, and async connection cleanup ([#885](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/885), [#894](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/894), [#938](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/938), [#947](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/947)) by @yeongseon.

- **JSON paths** — Keys use JSON string escaping, and Boolean indices are rejected ([#879](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/879), [#917](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/917)) by @yeongseon.

### Security

- **Inline literal escaping** — The first connection detects the server's backslash mode for inline strings and ENUM labels. An unexpected probe result fails the connection. Set `no_backslash_escapes` explicitly only when it matches the server setting ([#874](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/874)) by @yeongseon.

### Documentation

- **Examples and supported behavior** — Fixed the single-test command ([#1029](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1029)) by @HarshRajSinghania, reflected timezone type guidance ([#973](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/973)) by @CloudCorpRecords (first contribution 🎉), and Boolean expression guidance ([#986](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/986)) by @SuellenQwQ (first contribution 🎉).

### Tests

- **Regression coverage** — Added trace cleanup tests ([#931](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/931)) by @tnalbant (first contribution 🎉), identifier quoting and preflight tests ([#978](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/978), [#979](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/979), [#981](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/981)) by @CloudCorpRecords, and compiler and tool tests ([#1025](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1025), [#1026](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1026), [#1031](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1031)) by @WilliamK112 (first contribution 🎉).

## [1.11.0] - 2026-10-12

This release supports standard GIL builds of Python 3.15, caps the SQLAlchemy dependency below 2.2, and checks the built wheel against the cookbook before publishing.

### Upgrade notes

- **Python 3.15** — Use a standard GIL build and a pycubrid release that supports Python 3.15. On Python 3.15, pycubrid 1.10.0 and earlier reject `charset=ksc5601`; use `charset=euckr` or upgrade pycubrid. The declared pycubrid floor remains 1.8.0. The official CUBRIDdb source build with GCC 14 had the same known failure on Python 3.14 and 3.15 ([#807](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/807)) by @yeongseon.
- **SQLAlchemy support** — Package metadata now requires `sqlalchemy>=2.0,<2.2`, covering the verified 2.0 and 2.1 lines ([#777](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/777)) by @yeongseon.
- **Contributor installation** — Replace `pip install -e ".[dev]"` with `pip install -e . --group dev` (pip 25.1+) or `make install`. Runtime extras are unchanged ([#808](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/808)) by @yeongseon.

### Documentation

- **Python requirement** — Clarified the Python 3.11 minimum ([#803](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/803)) by @yeongseon and updated the Chinese README ([#825](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/825)) by @Vieta100-omo (first contribution 🎉).

### CI

- **Wheel verification** — Runs the cookbook against the built wheel before PyPI publication, including its Python 3.11 check ([#771](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/771), [#812](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/812)) by @yeongseon.

### Tests

- **Driver behavior** — Added coverage for async cancellation, connection invalidation on driver deadlines, and pycubrid 1.9.0 errors and value round-trips ([#798](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/798), [#799](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/799), [#800](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/800)) by @yeongseon.

## [1.10.0] - 2026-10-08

Python 3.11 is now the minimum. This release also updates the support and installation guides and makes pull-request validation more consistent.

### Upgrade notes

- **Python 3.11 or later** — Python 3.10 resolves to 1.9.x, the final line that supports it. That line receives no further releases. Upgrade Python, recreate the virtual environment, and test your application before upgrading the dialect ([#703](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/703)) by @yeongseon.

### Changed

- **Development tooling** — tox, Ruff and mypy now target Python 3.11 or later ([#728](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/728), [#729](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/729)) by @yeongseon. Disconnect detection drops its Python 3.10-specific timeout case ([#732](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/732)) by @UsmanGhias.

### Documentation

- **Python requirements** — Updated the README and quickstart ([#731](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/731)) by @yeongseon, the documentation index ([#740](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/740)) by @anush-933 (first contribution 🎉), and the contributor and CI guides ([#718](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/718)) by @kragent66-glitch (first contribution 🎉).
- **Korean documentation and licensing** — Updated Korean navigation and compatibility pages, added translation drift checks, and documented third-party licenses by installation option ([#711](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/711), [#712](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/712), [#715](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/715), [#755](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/755)) by @yeongseon.

### CI

- **Validation** — Pull requests run the complete offline suite. Live checks start independently when relevant, and CI jobs have bounded execution times ([#748](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/748), [#749](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/749), [#751](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/751), [#754](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/754)) by @yeongseon.

## [1.9.0] - 2026-10-04

This release raises the pycubrid minimum to 1.8.0, applies driver options from connection URLs, and improves reflection errors and pooled-connection recovery. Alembic 1.18+ uses plugin-based registration.

### Upgrade notes

- **pycubrid URLs** — Install `pycubrid>=1.8.0,<2.0`. Sync and async URLs now use options such as `connect_timeout`. Invalid, repeated or reserved settings raise `ArgumentError`, as does `charset` with pycubrid 1.8.0 ([#564](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/564), [#599](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/599)) by @yeongseon.
- **Reflection errors** — Constraint lookups propagate failed catalog queries. Column and index lookups raise `NoSuchTableError` for missing tables and surface other database errors. Review callers that assume an empty list or catch missing-table errors broadly ([#598](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/598)) by @yeongseon and ([#455](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/455)) by @UsmanGhias (first contribution 🎉), co-authored by @yeongseon.
- **Type lengths and collections** — Invalid lengths now fail at compile time, including explicit zero for `CHAR`, `NCHAR` and `BIT` ([#477](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/477), [#478](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/478)) by @HarshRajSinghania. Typed collection binding needs a newer pycubrid than 1.8.0. Use ordered values for `SEQUENCE` and bound parameters for non-NULL collections ([#623](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/623)) by @yeongseon.

- **LOB reads** — Ordinary cursors still return a locator when reading non-NULL BLOB or CLOB values. Binding binary, text, and NULL values was verified ([#636](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/636), [#678](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/678)) by @yeongseon.

### Changed

- **Alembic registration** — Alembic 1.18+ uses the plugin entry point. Earlier supported Alembic versions retain direct registration ([#616](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/616)) by @yeongseon.
- **Contributor commands** — Use `make test-offline` for both offline lanes. Integration defaults to pycubrid, uses its own Compose project, and fails when a configured server is unreachable ([#604](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/604), [#621](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/621)) by @yeongseon. Improved cleanup after failure ([#508](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/508)) by @soyeladice-svg.

### Deprecated

- **Python 3.10 and CUBRIDdb extras** — Python 3.10 remains supported in 1.9.x; upgrade before 1.10.0. The `[cubrid]` and `[cubriddb]` extras still resolve to the old PyPI driver in this release. CUBRIDdb below 11.3 warns at first connection; use pycubrid or a supported CUBRIDdb source build ([#588](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/588), [#665](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/665)) by @yeongseon.

### Fixed

- **Connection invalidation** — Replaces connections broken by server restart, a dead broker session, or malformed pycubrid replies. An interrupted query does not invalidate a healthy CUBRIDdb connection ([#571](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/571), [#577](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/577), [#681](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/681)) by @yeongseon.

- **SQL and reflection** — `replace()` emits the correct statement verb, and table and index existence checks handle string counts from the PyPI CUBRIDdb driver ([#584](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/584), [#600](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/600)) by @yeongseon.

### Documentation

- **Driver examples and compatibility** — Updated the quickstart and samples to use pycubrid ([#509](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/509), [#516](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/516)) by @soyeladice-svg (first contribution 🎉). Clarified SQLAlchemy 2.1 test coverage ([#506](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/506)) by @PandaHUN777 (first contribution 🎉) and aligned the Sphinx version with package metadata ([3f5c4f5](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3f5c4f5135bd3cc7f209905edc794419aa442e09)) by @HarshRajSinghania (first contribution 🎉).

### CI

- **Mutation testing** — Restored the advisory lane by including the integration helper in its sandbox ([#639](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/639)) by @paikend.

## [1.8.0] - 2026-09-29

Alembic upgrades are now atomic by default, non-DBA users get more complete reflection, and CUBRID-specific types and indexes generate corrected SQL.

### Upgrade notes

- **Alembic transactions** — A failed multi-revision upgrade rolls back the whole run. Set `transaction_per_migration=True` to commit per revision. Offline `--sql` output no longer includes `BEGIN;`; run it with `csql --no-auto-commit --no-single-line` ([#525](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/525)) by @yeongseon.
- **Alembic setup** — The dialect registers `CubridImpl` automatically with a standard `env.py`. The Alembic minimum is 1.7.2, and async migrations use Alembic's async template ([#511](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/511)) by @yeongseon.
- **Reflection and migration diffs** — Review your first autogenerate diff. Unique constraints are reflected once as unique indexes, views have no indexes, missing objects raise `NoSuchTableError`, and `Text` ↔ `String(n)` changes are detected ([#541](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/541), [#546](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/546), [#553](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/553), [#554](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/554)) by @yeongseon.
- **Index and type DDL** — Pass `table_name` to `op.drop_index()`. Conditional index create/drop flags raise `CompileError`. `TEXT` becomes `STRING`, binary lengths are expressed in bits, and UUID becomes `CHAR(32)` ([#538](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/538), [#539](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/539), [#551](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/551), [#552](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/552)) by @yeongseon.
- **Driver behavior** — CUBRIDdb executes each parameter set separately for accurate NULL values and row counts, which can slow large batches. Async `driver_connection` now returns the underlying pycubrid connection. Use `dbapi_connection` for the SQLAlchemy adapter ([#513](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/513), [#522](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/522)) by @yeongseon.
- **Transaction settings** — All drivers support AUTOCOMMIT. Hand-built pools must apply their own isolation level. With pycubrid, engine-level AUTOCOMMIT reconnects per statement; consider `skip_autocommit_rollback=True`. pycubrid 1.8.0 is recommended and is required for driver contract tests ([#527](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/527), [#528](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/528), [#557](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/557)) by @yeongseon.

- **Async installation** — The `[pycubrid]` extra now installs SQLAlchemy's async bridge, including `greenlet` ([#466](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/466)) by @yeongseon.

### Removed

- **SQLAlchemy 1.x hooks** — Removed obsolete autocommit and legacy `dbapi()` hooks ([#488](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/488)) by @yeongseon, after an earlier autocommit proposal by @biggdawg320 ([#468](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/468)).

### Fixed

- **Types** — Explicit zero-length strings raise `CompileError` ([#456](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/456)) by @anyingiit (first contribution 🎉). Timezone-aware types retain their flag ([#445](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/445)) by @pratipc (first contribution 🎉). Async binary binding works, Boolean predicates generate valid SQL, and JSON numeric results preserve decimal precision ([#510](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/510), [#536](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/536), [#555](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/555)) by @yeongseon.
- **Object lookup** — Table and view names are returned in stable order ([#457](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/457)) by @itsdevcode (first contribution 🎉). Mixed-case table and index checks work ([#550](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/550)) by @yeongseon.

### Documentation

- **Pagination** — Updated LIMIT/OFFSET troubleshooting to match emitted SQL ([#419](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/419)) by @paikend.

## [1.7.1] - 2026-09-18

This release adds native ENUM and null-safe distinct comparisons, fixes composite primary-key reflection, and improves numeric binding and multi-row inserts.

### Upgrade notes

- **Numeric precision** — CUBRIDdb can truncate the fractional part of `NUMERIC` and `DECIMAL` results. Use `cubrid+pycubrid://` when full decimal precision is required ([#420](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/420)) by @yeongseon.
- **Multi-row upserts** — Inline multi-row `VALUES` referencing `stmt.inserted.col` in `ON DUPLICATE KEY UPDATE` now raises a clear compile error ([#418](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/418)) by @yeongseon.

### Added

- **ENUM and distinct comparisons** — Added native `ENUM` and support for `IS [NOT] DISTINCT FROM` on CUBRID ([#345](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/345), [#390](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/390)) by @yeongseon.

### Fixed

- **Reflection** — Returns every column of a composite primary key, includes column comments, and reports missing tables consistently ([#427](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/427), [#428](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/428)) by @yeongseon.
- **SQL compilation and execution** — Preserves numeric scale in arithmetic, compiles FROM-less `SELECT ... WHERE`, removes the old implicit row cap for offset-only queries, and binds `executemany` INSERT values correctly when a type adds a cast ([#400](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/400), [#417](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/417), [#423](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/423)) by @yeongseon. Corrected distinct comparison execution in SELECT projections ([#379](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/379)) by @tayfuryldz (first contribution 🎉).
- **Identity columns** — `Identity()` now emits `AUTO_INCREMENT` ([#422](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/422)) by @yeongseon.

### Documentation

- **Examples and Korean documentation** — Added runnable API examples and organized the Korean documentation ([#339](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/339), [#342](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/342), [#436](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/436)) by @yeongseon.

### Tests

- **Compatibility** — SQLAlchemy compliance regressions now fail CI. Added UUID round-trip, driver comparison, and realistic ORM coverage ([#389](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/389), [#429](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/429), [#432](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/432), [#435](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/435)) by @yeongseon.

## [1.7.0] - 2026-09-02

This release adds native Alembic column alterations, an explicit CUBRIDdb connection URL, and more reliable schema reflection and connection recovery.

### Upgrade notes

- **Isolation levels** — Obsolete pre-MVCC isolation names now raise `ValueError`. Use READ COMMITTED, REPEATABLE READ or SERIALIZABLE ([#308](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/308)) by @yeongseon.
- **Column type conversions** — CUBRID's `alter_table_change_type_strict` setting controls whether incompatible conversions fail or may truncate data. Check it before applying type changes ([#306](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/306)) by @yeongseon.

### Added

- **CUBRIDdb URL** — Use `cubrid+cubriddb://` to select the C-extension explicitly or install the `[cubriddb]` extra. Existing `cubrid://` URLs still work with CUBRIDdb ([#302](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/302), [#304](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/304)) by @yeongseon.
- **Alembic column alterations** — Rename columns, change their types, or do both with native DDL. Batch mode remains available when a table rewrite is needed ([#306](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/306)) by @yeongseon.

### Fixed

- **Schema reflection** — A NULL default schema no longer becomes the string `"None"`. Default schema names compare case-insensitively and requests for unsupported non-default schemas raise `NoSuchTableError` ([#287](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/287), [#296](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/296), [#297](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/297), [#298](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/298)) by @yeongseon.
- **Connections and transactions** — Recognizes more pycubrid transport failures so SQLAlchemy can replace broken pooled connections. Isolation levels round-trip through set and get ([#286](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/286), [#316](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/316), [#324](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/324)) by @yeongseon.
- **SQL literals** — Inline strings preserve backslashes with the default CUBRID server setting ([#315](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/315)) by @yeongseon.

### Documentation

- **Compatibility** — Described the supported SQLAlchemy 2.0–2.1 series, canonical isolation names and `LIST` as a synonym for `SEQUENCE` ([#299](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/299), [#309](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/309), [#312](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/312)) by @yeongseon.

### CI

- **Lint** — Pinned Ruff's lint rules and corrected the lint job ([#270](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/270), [#272](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/272)) by @paikend.

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

- **Clarified dialect behavior** — expanded explanations of schema reflection, `postfetch_lastrowid`, SQLAlchemy internal API dependencies, type handling, and `ON DUPLICATE KEY UPDATE` ([commit 512702b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/512702b1a11dd53fbf28b2229081b576ee1b67ef), [commit fbd204d](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fbd204d0c5e6d4c00cd90cf58022de39f1d7e416)) by @yeongseon.

- **Aligned development documentation** — corrected inconsistencies in the product requirements, contributor guidance, and CI descriptions ([commit f7584ac](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f7584acbfe67ee283cd14eb5993e977aa0543a0b), [commit fbd204d](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fbd204d0c5e6d4c00cd90cf58022de39f1d7e416), [commit 39b4fa1](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/39b4fa1d1a1339063b68b23d1ed064af78bba6a5)) by @yeongseon.

- **Updated translations** — synchronized the Korean, German, Russian, Chinese, and Hindi READMEs with the English documentation ([commit b5add77](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b5add77868281fe7be0092c99d0c1cfbf306331f), [commit 0e70412](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/0e704127e83ca24e1b4ee19a8025d8603b8edad1)) by @yeongseon.


## [1.4.0] - 2026-04-20

This release adds SQLAlchemy compatibility safeguards, Alembic migration guidance, and connection-pool stress coverage. It also updates the optional pycubrid dependency requirement.

### Added

- **SQLAlchemy 2.2 compatibility shim** — `sqlalchemy_cubrid/_compat.py` insulates compiler from SA private API changes (`is_literal_value`, `bind_with_type`, `for_update_arg`, `limit_clause`, `offset_clause`). `bind_with_type` now preserves `expanding`/`literal_execute`/`isoutparam` flags; `is_literal_value` handles `visitors.Visitable` instances (Oracle post-review fixes) (#142). SQLAlchemy 2.2 remains unsupported: the dependency stays pinned to `<2.2`, and the shim prepares the codebase for a future bump without lifting the pin ([commit 48ae253](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/48ae2537157029ddfc2cf2a5033d95d3240af001)) by @yeongseon.

- **Alembic safety checklist + advisory CLI** — `docs/ALEMBIC.md` adds Pre-Migration Checklist, Pre-Deploy Sequence, and Rollback Template; `scripts/alembic_safety_check.py` provides advisory detection for non-transactional DDL risks (#144) ([commit 7966d02](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7966d027d11699c3498e38a5599ba82eeb0ed94c)) by @yeongseon

- **Compiler benchmark baseline** — `scripts/bench_compile.py` per-construct timing baseline. Baselines: SELECT+LIMIT ~178µs, INSERT ~129µs, INSERT ON DUPLICATE KEY UPDATE ~234µs (1.8× simple INSERT due to `replacement_traverse` overhead), SELECT FOR UPDATE ~153µs (#145) ([commit e09cb74](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/e09cb74e334c181cc7f93423f2fa25343d4aca01)) by @yeongseon

### Fixed

- **pycubrid dependency pin** — `pycubrid>=1.2.0,<2.0` (lower bound raised from `>=1.0`; the `<2.0` upper bound was already present) (#143) ([commit ed7e782](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ed7e782f01930efb27fcc48f6f0ac313a424b8e8)) by @yeongseon

### Tests

- **QueuePool concurrency stress tests** — 6 tests covering sync concurrent checkouts within `pool_size`, overflow burst absorption with barrier sync, `pool_timeout` exhaustion, `pool_recycle` aged-connection replacement, async `gather` within `pool_size`, async overflow burst ([commit 87abc6f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/87abc6f3092080447ccf2836aa4b37cc1a25cb06)) by @yeongseon

- **F401 lint regression** — removed unused `CubridDialect` import in `test/test_logging.py` ([commit 2b12ba4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2b12ba4aa231e7d105d71176c011fde4beb828a9)) by @yeongseon

## [1.3.0] - 2026-04-19

This release improves schema reflection, SQL compilation, and Alembic migration diagnostics. It also adds stronger integration and packaging checks.

### Added

- **FK parsing with ON DELETE/ON UPDATE** — `get_foreign_keys()` regex now captures referential action clauses from `SHOW CREATE TABLE` (#135) ([commit a25d895](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a25d8951a8019594e453d664264c69852f20ae91)) by @yeongseon

- **FULL OUTER JOIN / LATERAL rejection** — raises `CompileError` for unsupported join types instead of generating invalid SQL (#138) ([commit a25d895](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a25d8951a8019594e453d664264c69852f20ae91)) by @yeongseon

- **Alembic `alter_column` guardrails** — `CubridImpl.alter_column()` rejects `type_`/`new_column_name` with clear error, allows `nullable`/`server_default` (#136) ([commit a25d895](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a25d8951a8019594e453d664264c69852f20ae91)) by @yeongseon

- **Reflection fallback logging** — silent errors in dialect.py now logged (#127) ([commit 93c7564](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/93c75644d9e09cc4efda267f89033d607971e550)) by @yeongseon

- **Reflection diagnostic probe** — `scripts/reflection_probe.py` dumps the reflected metadata of one or all tables and can compare it with ORM declarations, to help diagnose Alembic autogenerate false-positive diffs (#131) ([commit 93c7564](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/93c75644d9e09cc4efda267f89033d607971e550)) by @yeongseon

### Changed

- **Status: Beta** — README, classifiers, and documentation now consistently use Beta messaging; removed "stable", "production-ready", "frozen" language ([commit a25d895](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a25d8951a8019594e453d664264c69852f20ae91)) by @yeongseon

- **pycubrid (sync) compatibility** — now requires `>=1.2.0` for full feature parity (documented requirement; the package metadata pin was raised to `>=1.2.0,<2.0` in 1.4.0, #143) ([commit 339d9af](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/339d9af89d6abc4348a6a8f3934b396980eb53be)) by @yeongseon

- **Compiler DML helper extraction** — cleaner `visit_on_duplicate_key_update`/`visit_merge` (#133)

### Fixed

- **`has_index()` bug** — now filters by `class_of.class_name` to avoid cross-table false positives ([commit a25d895](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a25d8951a8019594e453d664264c69852f20ae91)) by @yeongseon

- **`reset_isolation_level()`** — uses canonical isolation level name instead of alias ([commit a25d895](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a25d8951a8019594e453d664264c69852f20ae91)) by @yeongseon

- **`get_isolation_level()` fallback** — returns the canonical level-4 name `"REPEATABLE READ SCHEMA, READ COMMITTED INSTANCES"` instead of the `"READ COMMITTED"` alias (#140) ([commit a25d895](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a25d8951a8019594e453d664264c69852f20ae91)) by @yeongseon

### Documentation

- **README consolidation** — authoritative support contract with async status and known limitations (#128) ([commit 93c7564](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/93c75644d9e09cc4efda267f89033d607971e550)) by @yeongseon

- **ARCHITECTURE.md / DEVELOPMENT.md refresh** — updated to reflect current module structure (#129) ([commit 93c7564](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/93c75644d9e09cc4efda267f89033d607971e550)) by @yeongseon

- **SA_COMPAT.md** — documents SQLAlchemy private API dependencies and 2.2 readiness plan (#132) ([commit 93c7564](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/93c75644d9e09cc4efda267f89033d607971e550)) by @yeongseon

- **`get_check_constraints()` behavior documented** — the existing method still returns an empty list; `docs/FEATURE_SUPPORT.md` and a source comment now explain that CUBRID parses CHECK constraints but does not enforce them (#139) ([commit a25d895](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a25d8951a8019594e453d664264c69852f20ae91)) by @yeongseon

### CI

- **Distribution smoke test** — CI validates sdist/wheel build (#122) ([commit 93c7564](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/93c75644d9e09cc4efda267f89033d607971e550)) by @yeongseon

- **Release consistency CI** — automated tag/version/changelog alignment checks (#124) ([commit 93c7564](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/93c75644d9e09cc4efda267f89033d607971e550)) by @yeongseon

- **Async integration tests in CI** — promoted from optional to regular (#130) ([commit 93c7564](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/93c75644d9e09cc4efda267f89033d607971e550)) by @yeongseon

### Tests

- **Entry point verification test** — importlib.metadata check for dialect registration (#123) ([commit 93c7564](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/93c75644d9e09cc4efda267f89033d607971e550)) by @yeongseon

- **SHOW CREATE TABLE golden tests** — parsing fixture corpus for DDL reflection (#125) ([commit 93c7564](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/93c75644d9e09cc4efda267f89033d607971e550)) by @yeongseon

- **Alembic autogenerate regression tests** — false-positive diff detection (#126) ([commit 93c7564](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/93c75644d9e09cc4efda267f89033d607971e550)) by @yeongseon

- **CUBRID version-specific reflection snapshots** — DDL output tests across versions (#134)

- **Multi-table UPDATE coverage** — compiler tests and a `docs/FEATURE_SUPPORT.md` note for the existing multi-table UPDATE compilation, which renders `UPDATE t1, t2 SET ... WHERE ...` (#137) ([commit a25d895](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a25d8951a8019594e453d664264c69852f20ae91)) by @yeongseon

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

- Version consistency: synchronized `__version__` in `sqlalchemy_cubrid/__init__.py` with `pyproject.toml` (was 1.0.0 vs 1.1.0) ([PR #115](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/115)) by @yeongseon

- Removed unused imports flagged by `ruff` in `aio_pycubrid_dialect.py` and `test/test_aio_pycubrid_dialect.py` ([PR #115](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/115)) by @yeongseon

- CI: switched the version-consistency check to `ast.parse` so it no longer requires installing runtime dependencies just to read `__version__` ([PR #115](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/115)) by @yeongseon

- `test_integration.py`: hoisted `Mapped`/`mapped_column` imports to module scope (function-local imports broke SQLAlchemy's annotation resolution under the `insertmanyvalues` test) ([PR #115](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/115)) by @yeongseon

### Tests

- All 500 offline tests pass (47 new for JSON); all 8 integration matrix combinations pass (Python 3.10/3.12 × CUBRID 10.2/11.0/11.2/11.4); project coverage 98.61%, `types.py` 99% ([PR #115](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/115)) by @yeongseon.

## [1.1.0] - 2026-04-18

This release introduces the asynchronous pycubrid dialect through the `cubrid+aiopycubrid://` connection URL.

### Upgrade notes

- **Requirements for the async dialect** — pycubrid >= 1.1.0 (with the `pycubrid.aio` module) and SQLAlchemy 2.0–2.1. The pycubrid version is the documented requirement; the `[pycubrid]` extra metadata at this tag still allows `pycubrid>=1.0,<2.0`.

- **Usage** — `create_async_engine("cubrid+aiopycubrid://dba:password@localhost:33000/demodb")` with `AsyncSession` for native asyncio.

### Added

- **Async dialect** via `cubrid+aiopycubrid://` URL scheme ([PR #110](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/110)) by @yeongseon
  - `PyCubridAsyncDialect` (`is_async=True`) using SQLAlchemy's `AsyncAdapt_dbapi_*` base classes
  - `AsyncAdapt_pycubrid_dbapi` wraps `pycubrid.aio` module
  - `AsyncAdapt_pycubrid_connection` bridges autocommit via greenlet `await_only`
  - `AsyncAdapt_pycubrid_cursor` with full async cursor adaptation
  - `cubrid.aiopycubrid` entry point auto-discovered by SQLAlchemy

- 17 new async dialect offline tests (`test/test_aio_pycubrid_dialect.py`) ([PR #110](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/110)) by @yeongseon

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

- Full type annotations across all 8 source modules (mypy errors: 280 → 0) ([PR #103](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/103)) by @yeongseon

- Compatibility Matrix in README (Python, CUBRID, SQLAlchemy, Alembic versions) ([PR #103](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/103)) by @yeongseon

### Changed

- Development Status classifier updated from "Beta" to "Production/Stable" ([PR #103](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/103)) by @yeongseon

- pycubrid optional dependency updated from `>=0.6.0` to `>=1.0,<2.0` ([PR #103](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/103)) by @yeongseon

- All documentation updated to explicitly state "SQLAlchemy 2.0–2.1" support ([PR #103](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/103)) by @yeongseon

- Version bumped to 1.0.0 ([PR #103](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/103)) by @yeongseon

### Fixed

- `visit_join` signature: added missing `from_linter` parameter to match SQLAlchemy base class ([PR #103](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/103)) by @yeongseon

- `sqlalchemy.sql.util.warn`: replaced with correct `sqlalchemy.util.warn` API ([PR #103](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/103)) by @yeongseon

## [0.8.0] - 2026-04-04

This stabilization release documents the supported environments and compatibility boundaries ahead of 1.0, including the minimum optional pycubrid driver version.

### Upgrade notes

- **1.0 support boundary (summary)** — SQLAlchemy 2.0–2.1 (pinned `<2.2`), Python 3.10–3.14 and CUBRID 10.2–11.4 are supported. DDL, DML, reflection, ORM, Core, Alembic migrations, ODKU/MERGE/REPLACE, window functions and CTEs are supported. JSON type: not yet mapped. Native Enum: not supported (use VARCHAR + CHECK). RETURNING: not supported. BOOLEAN: mapped to SMALLINT. After a soak period on PyPI, the next release is planned as 1.0.

### Added

- `docs/SUPPORT_MATRIX.md`: Comprehensive support matrix documenting SQLAlchemy versions, Python versions, CUBRID versions, driver compatibility, feature support, type mappings, and known limitations — defines the 1.0 support boundary ([PR #82](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/82)) by @yeongseon

- Documents private SQLAlchemy API usages that require the `<2.2` version pin ([PR #82](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/82)) by @yeongseon

- Clarified public documentation to state SQLAlchemy 2.0–2.1 support explicitly

### Changed

- **pycubrid dependency (historical context)** — the optional `pycubrid>=0.6.0` minimum was already introduced in v0.7.1 ([#72](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/72), [commit c598b07](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c598b0749e84166f45e4f67ef3109d1171605d55)) and remains in force in this release. The driver integration expects `list[tuple]` results from `fetchall()`; do not attribute this return shape to a new behavior introduced by pycubrid v0.6.0.

- Version bumped to 0.8.0 (stabilization release on path to 1.0) ([PR #82](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/82)) by @yeongseon

## [0.7.1] - 2026-03-13

This patch fixes UTC timestamp compilation and schema inspection, improves statement compilation caching, and reduces index-reflection overhead.

### Upgrade notes

- **First non-development PyPI release** — the only earlier PyPI uploads are `0.0.1.dev0` and `0.0.1.dev1` (2022). The optional `[pycubrid]` extra requires `pycubrid>=0.6.0` ([#72](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/72), [commit c598b07](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c598b0749e84166f45e4f67ef3109d1171605d55)).

### Changed

- **Package metadata** — Updated PyPI classifiers and the project Changelog link ([#75](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/75), [commit e682336](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/e682336b45)) ([PR #77](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/77)) by @yeongseon.

- **Version scheme** — Re-versioned the project to 0.x for the pre-1.0 development phase ([commit f6171f1](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f6171f1f3598f14feb804bce9b1fb2097d60436e)) by @yeongseon.

### Fixed

- **`visit_utc_timestamp_func`** — Compile `func.utc_timestamp()` to `UTC_TIMESTAMP()` instead of `UTC_TIME()`, returning a full datetime value instead of time-only (#53) ([commit ff9bded](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ff9bdedcd6c0d5829597885bb5bf000615c4f28c)) by @yeongseon.

- **`get_indexes()`** — Fix PK index filtering: read `is_primary_key` from column 0 of the single-column query result instead of unreachable column 6, excluding primary-key indexes correctly (#54) ([commit ff9bded](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ff9bdedcd6c0d5829597885bb5bf000615c4f28c)) by @yeongseon.

- **`has_table()`** — Recognize views as existing objects by accepting `class_type IN ('CLASS', 'VCLASS')` instead of only `'CLASS'` (#55) ([commit ff9bded](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ff9bdedcd6c0d5829597885bb5bf000615c4f28c)) by @yeongseon.

### Performance

- **Statement caching** — Enable SQLAlchemy statement caching on `Insert` and `Replace` using `inherit_cache = True`, with cache-key regression coverage ([#70](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/70), [commit 688c415](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/688c415b76)) ([PR #76](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/76)) by @yeongseon.

- **Index reflection** — Avoid an N+1 primary-key catalog lookup in `get_indexes()` by using a batched query, with regression tests ([#70](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/70)) ([PR #76](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/76)) by @yeongseon.

- **Column reflection** — Precompile patterns used by `get_columns()` at module level instead of on every invocation ([#70](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/70)) ([PR #76](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/76)) by @yeongseon.

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
