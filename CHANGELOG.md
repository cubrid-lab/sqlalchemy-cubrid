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

## [1.12.3] - 2026-11-13

This maintenance release revises one deprecation warning, rewords the missing-CUBRIDdb error and raises the setuptools version needed to build from source. It also fixes paged queries that could return the wrong rows, `BIGINT` results returned as strings and `Boolean` results read as `True` from the string `'0'`, with the PyPI CUBRIDdb 9.3 driver. SQL generation for other drivers, reflection and connection behavior are unchanged.

### Upgrade notes

- **Revised deprecation notice for ignored type arguments (#892)** — the `DeprecationWarning` for the ignored `SMALLINT`/`BIGINT` `display_width` argument (including positional `SMALLINT(11)`) and the string-type `values` argument now says they may be removed in a future reviewed **1.x MINOR** instead of the next major release. The arguments are still accepted in this release and generate no different DDL. Migrate `SMALLINT(11)` to `SMALLINT()`, `BIGINT(20)` to `BIGINT()` and `VARCHAR(30, values=["x"])` to `VARCHAR(30)`, or pin a narrower version range. The 1.x compatibility policy behind this change is in [RELEASING.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/RELEASING.md#public-api-compatibility-in-1x) ([#1115](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1115), [#1122](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1122)) by @yeongseon.
- **Building from source needs setuptools 77 or newer** — the build backend requirement is now `setuptools>=77` for SPDX license metadata. Installing the published wheel is unaffected; source builds without build isolation need an up-to-date setuptools ([#1113](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1113)) by @CloudCorpRecords.

### Changed

- **Missing-CUBRIDdb error** — the `Could not import CUBRIDdb` error for `cubrid://` and `cubrid+cubriddb://` URLs no longer calls the CUBRIDdb C-extension driver legacy or the PyPI `CUBRID-Python` releases untested. It lists both installation paths (`sqlalchemy-cubrid[cubriddb]` or an official CUBRID/cubrid-python source build) and the pure-Python `cubrid+pycubrid://` alternative. The message prefix and the chained original `ImportError` are unchanged ([#1150](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1150)) by @yeongseon.
- **First-connect warning for the PyPI CUBRIDdb 9.3 driver** — the `SAWarning` emitted when the loaded CUBRIDdb is older than 11.3 no longer calls this supported driver line untested or tells users to switch away. It now names the limitations the dialect cannot work around, as observed with CUBRID 11.4: `bytes` values cannot be bound, constraint violations are raised as `DatabaseError` instead of `IntegrityError`, and the server rejects string-bound parameters in recursive CTEs and `SET` values. It also points to pycubrid and the v11.3.0.51 source build as alternatives. The warning still fires once per engine, the connection is unchanged, and the documented `message="CUBRIDdb .* is older"` filter still matches ([#1142](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1142)) by @yeongseon.

* restore release notes merged without review approval ([#1185](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1185)) ([ce3d338](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ce3d338420e3bc011a692b7459c66fecb7390fd4)) by @yeongseon

### Removed

- **One-time historical release sync tools (#1182)** — the three historical Release sync and audit scripts, their tests, the audit record `HISTORICAL_RELEASE_AUDIT.md` (+ Korean) and the v1.12.2 Release body backup are removed. They served the one-time synchronization of published Release bodies, which finished when #1220 verified all 28 published bodies against `CHANGELOG.md`. Release preparation and publishing are unchanged ([#1182](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1182)) by @yeongseon.
- **Unused repository files (#1182)** — a stray `uv.lock` (nothing runs `uv sync`/`uv lock`; CI uses `uv pip install --group`), `codecov.yml` (no workflow uploads to Codecov), the unreferenced `docs/javascripts/mermaid-init.js` (diagrams render through `pymdownx.superfences`), the placeholder `test/fixtures/README.md`, the VHS script `demos/orm-demo.tape` (the published `docs/demo.gif` is rendered by `demos/render_gif.py` from `demos/orm-demo.json`) and the never-published MP4 recording kit (`demos/orm-demo-mp4.tape`, `demos/orm_alembic_video.py`, `demos/VIDEO_RECORDING.md`, `docs/assets/videos/.gitkeep`) are removed. No installed package code or supported behavior changes; refs [#1182](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1182).
- **Dated benchmark results and the benchmark artifact contract (#1290)** — the four dated result directories under `benchmarks/`, the artifact manifest tool `scripts/bench_artifact.py` with its tests, and the `--source-sha` install verification and `--server-image-digest`, `--host-label` and `--comparable-group` options of `scripts/bench_dialect_baseline.py` are removed. `docs/PERFORMANCE.md` (+ Korean) is shortened to performance guidance, known limitations and how to run the kept local scripts: `scripts/bench_compile.py`, `scripts/profile_orm.py` and `scripts/bench_dialect_baseline.py`, whose workloads are kept because cubrid-benchmark does not reproduce them yet; their result checks are unchanged, and the JSON report keeps the environment and workload identity but no longer records the install provenance fields or the image digest, host label and comparable-group labels. Reproducible performance experiments belong in [cubrid-benchmark](https://github.com/cubrid-lab/cubrid-benchmark). Dialect runtime behavior, the dialect's tests and release checks are unchanged ([#1290](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1290)) by @yeongseon.
- **`make check-all`** — the alias of `make check`, deprecated in 1.11.5 and announced for removal after the next minor release (1.12.0), is removed. Run `make check` instead; `make test-offline` remains an alias of `make test` ([#1313](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1313)) by @yeongseon.

### Fixed

- **Paged queries with the PyPI CUBRIDdb 9.3 driver** — this driver sends every bound parameter as a string, and CUBRID then applied a bound `LIMIT ?, ?` incorrectly: `.offset(1).fetch(2)` returned four rows instead of two, with no error. When the connected CUBRIDdb is older than 11.3, the plain integers of a query with an offset (`LIMIT offset, count`) are now written into the SQL at execution time; such a statement cannot run through `executemany()`. A limit without an offset, pycubrid and CUBRIDdb 11.3 or later still use bound parameters ([#1299](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1299)) by @yeongseon.
- **`BIGINT` results with the PyPI CUBRIDdb 9.3 driver** — this driver returns `BIGINT` values, including `COUNT(*)` and `ROWNUM`, as strings (`'5'`). When the connected CUBRIDdb is older than 11.3, integer-typed and untyped (`text()`) result columns that the driver reports as `BIGINT` now return `int`. Other column types are never parsed, and pycubrid and CUBRIDdb 11.3 or later are unchanged ([#1145](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1145)) by @yeongseon.
- **`Boolean` results without a fixed column type with the PyPI CUBRIDdb 9.3 driver** — this driver returns result columns that have no fixed type, such as `PERCENTILE_DISC(...) WITHIN GROUP (ORDER BY <condition>)`, as strings, and SQLAlchemy's `Boolean` result processor turned `'0'` into `True`. When the connected CUBRIDdb is older than 11.3, a string in a `Boolean` result column is now read as a number first, so `'0'` returns `False`; non-numeric text raises `ValueError` instead of returning `True`. Other types, pycubrid and CUBRIDdb 11.3 or later are unchanged ([#1143](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1143)) by @yeongseon.
- **INSERT with a driver that lacks `get_last_insert_id()`** — with the PyPI CUBRIDdb 9.3 driver, a single-row INSERT on a connection that had not yet inserted into an `AUTO_INCREMENT` column failed with `TypeError: int() argument must be ... not 'NoneType'`, even though the row was stored; Alembic's `alembic_version` insert was one example. A NULL `SELECT LAST_INSERT_ID()` now means no generated key ([#1302](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1302)) by @yeongseon.
- **`pool_pre_ping` with the PyPI CUBRIDdb 9.3 driver** — this driver has no `Connection.ping()`, so every ping failed and `pool_pre_ping=True` discarded and reopened a pooled connection on each checkout. Connections without `ping()` are now checked with `SELECT 1`; CUBRIDdb 11.3 and pycubrid are unchanged ([#1304](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1304)) by @yeongseon.

* capture driver and URL scheme in bug reports ([6c190e5](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6c190e5550be775273c54e34ffbb06c9e8b44261)), refs [#1079](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1079) by @yeongseon
* **compiler:** render LIMIT integers inline for CUBRIDdb older than 11.3 ([#1300](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1300)) ([5e3f10f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5e3f10f2bcd73859b31d4bdb68faedd4331d5bbc)) by @yeongseon
* publish curated v1.12.2 release notes with verified contributor credits ([#1158](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1158)) ([5d054c9](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5d054c970524e8a93e652d7a07468cc6cb8d3263)) by @yeongseon
* **release:** list each change once when curated and generated notes overlap ([#1317](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1317)) ([69b39fa](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/69b39fa8ba46f032d86d333e7a6d8b495a64f4f0)) by @yeongseon
* **types:** return BIGINT results as int with CUBRIDdb older than 11.3 ([#1301](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1301)) ([b22a011](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b22a011fe35d97a085ff2bacbeb96688c00937f4)) by @yeongseon
* verify published release body with a fresh GitHub API read ([a41616d](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a41616df4407d1545871969a4e2c17ce38ed8a8f)) by @yeongseon
* verify published release notes after synchronization ([#1175](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1175)) ([a41616d](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a41616df4407d1545871969a4e2c17ce38ed8a8f)) by @yeongseon

### Documentation

- **Release-note credit review checklist** — `docs/RELEASE_NOTES_STYLE.md` and its Korean version add a six-point checklist from the audit of all published release notes: map entries to the implementing PR, credit co-authors only for substantive human commits, never credit agents or bots, leave summaries and dependency updates uncredited, verify first contributions, and check that each change is inside the release's tag range ([#1220](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1220)) by @yeongseon.
- **`SystemError` after closing a PyPI CUBRIDdb 9.3 connection twice** — `docs/DRIVER_COMPAT.md` and its Korean version now give the cause and a driver-only reproduction, and explain why the dialect keeps closing connections explicitly: leaving the close to the driver's deallocator avoids the error but left a busy broker session for every discarded pooled connection in a test on CUBRID 11.4 ([#1320](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1320)) by @yeongseon.
- **PyPI CUBRIDdb 9.3 limitations after the dialect fixes** — `docs/DRIVER_COMPAT.md`, the support matrix and the README note (with their Korean versions) no longer say that `BIGINT` results stay strings, that paged queries can return the wrong rows or that `pool_pre_ping` reopens every connection with this driver; they now say what the dialect converts or works around and what remains a driver limitation. They record the manually dispatched `cubriddb-pypi.yml` lane run on `main` and the `SystemError` after a connection is closed twice ([#1145](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1145), [#1320](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1320)) by @yeongseon.
- **Temporary tooling lifecycle** — the contributor guide and its Korean translation now say what a PR that adds a temporary script, probe or repair tool records (purpose, owner, removal trigger, evidence location, next review point), to prefer manual execution, and what to map before removing one. Permanent release automation and supported older-driver compatibility paths are not temporary tooling. The pull request template has an optional prompt ([#1183](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1183)) by @yeongseon.
- **First connection and troubleshooting** — troubleshooting now shows the actual missing-pycubrid and authentication error messages, explains missing `greenlet` errors for async engines and broker readiness, and adds Windows virtual-environment setup to the first-connection lesson and Apple silicon options for the CUBRID lab. Translated READMEs guide readers to their first connection with `cubrid+pycubrid://` URLs and no longer overstate live CI coverage ([#1116](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1116), [#1118](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1118), [#1124](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1124), [#1126](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1126), [#1127](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1127), [#1131](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1131), [#1134](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1134), [#1137](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1137)) by @yeongseon.
- **CUBRIDdb troubleshooting** — the entry quotes the actual `Could not import CUBRIDdb` error and lists the supported `sqlalchemy-cubrid[cubriddb]` and official source-build installation paths, keeping the heading and anchor correction first proposed in #1110 ([#1205](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1205)) by @yeongseon.
- **Feature support and versions** — corrected the CUBRID 10.2 feature-support guidance and separated database server versions from Python driver versions, with a version check that works without CUBRIDdb installed ([#1117](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1117), [#1149](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1149)) by @yeongseon.
- **CUBRIDdb driver support policy** — the support matrix and driver guides now list both CUBRIDdb driver lines as supported: the PyPI `CUBRID-Python` 9.3.0 release installed by the `[cubrid]` / `[cubriddb]` extras, which are no longer called deprecated, and a build of the cubrid-python v11.3.0.51 source release. A separate verification table shows what was actually run: CI tests the v11.3.0.51 build, while the 9.3.0 line is supported but not verified on current Python versions, and its known limitations from an earlier run (`BIGINT` returned as `str`, 25 integration failures) stay documented. pycubrid remains the recommended driver for new projects ([#1298](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1298)) by @yeongseon.
- **CUBRIDdb installation advice** — the README (and its Korean translation), installation and troubleshooting guides, architecture overview, third-party license table and `llms.txt` no longer call the `[cubrid]` / `[cubriddb]` extras deprecated or the PyPI driver untested. They show both installation options, pointing to the known limitations of the PyPI 9.3.0 release ([#1147](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1147)) by @yeongseon.
- **Translated driver guidance** — the German, Hindi, Russian and Chinese READMEs describe both CUBRIDdb installation options instead of calling the PyPI driver untested and the extras deprecated, and `scripts/check_support_claims.py` now also checks that the Korean support matrix keeps both driver lines supported and the PyPI 9.3.x line not reported as tested ([#1148](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1148)) by @yeongseon.
- **Feature support and versions** — corrected the CUBRID 10.2 feature-support guidance and separated database server versions from Python driver versions, with a version check that works without CUBRIDdb installed The connection guide now links to that version terminology from its introduction ([#1117](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1117), [#1149](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1149), [#1140](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1140)) by @yeongseon.
- **Getting help** — the issue chooser and documentation now point to one support and questions path, and bug reports ask for the driver and URL scheme ([#1125](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1125), [#1129](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1129), [#1135](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1135)) by @yeongseon.
- **Published pages** — fixed links from the documentation site and the PyPI README to repository files, made the PyPI demo render, and removed the unused Sphinx scaffold ([#1123](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1123), [#1132](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1132), [#1138](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1138)) by @yeongseon.
- **Historical release notes** — earlier `CHANGELOG.md` sections now use the standard headings, credit verified human contributors (#1214), restore merged changes and published details they had omitted, and correct factual errors such as the PyPI 1.2.2 statement; all 28 published GitHub Release pages were updated to match and re-verified ([#1153](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1153)) by @yeongseon.
- **Help menu support links** — added direct links to Discussions, the issue chooser and SECURITY.md from the documentation site's Help menu ([#1294](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1294)) by @aashnayadav.

* add clear release summaries across 14 historical versions ([#1177](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1177)) ([7dd2e3a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7dd2e3acd0d4095577a9af51e16c571b4fb095c4)) by @yeongseon
* add concise reader summaries to 14 published historical releases ([7dd2e3a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7dd2e3acd0d4095577a9af51e16c571b4fb095c4)) by @yeongseon
* add concrete user-facing highlights to v1.7.0 and v1.7.1 ([80e4026](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/80e4026a667fc506aa64c01b292c579daa6edae4)) by @yeongseon
* add reader-focused introductions to seven oversized historical releases ([1a4087c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1a4087c738c0df87cc81d53e490649e5b1dc34b0)) by @yeongseon
* add support links to the documentation Help menu ([#1297](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1297)) ([f199380](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f1993803d700c2f2cda2ae97d61223935a6b7df3)) by @aashnayadav (first contribution 🎉)
* add the omitted v1.12.1 test contribution ([#1203](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1203)) ([2957cb7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2957cb7b633583d11679bd33d3507b86bce4af2b)) by @yeongseon
* add the omitted v1.12.2 test contributions ([#1204](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1204)) ([80b002b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/80b002b5917f84c2609593b285a6fb1148b22570)) by @yeongseon
* add troubleshooting and questions to issue chooser ([9f5ea30](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/9f5ea30de76c91762d2dd5ee65e8d2760818780d)), refs [#1077](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1077) by @yeongseon
* add Windows virtual environment setup to Lesson 1 ([cf75832](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/cf75832e1069ea60968cdfef92d16fa9fbc734d8)), refs [#1087](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1087) by @yeongseon
* apply valid Copilot review corrections to release note layout ([11a5179](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/11a51797d82d85f3c94ed9bb6aec00957c3685b7)) by @yeongseon
* attribute v1.12.0 release changes to verified PR author ([4219029](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/4219029ff27b00a10277e77d34eaac58a2d366eb)) by @yeongseon
* audit historical releases and guard retrospective synchronization ([#1156](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1156)) ([8d637ee](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/8d637ee008187af9b24e7182e17edba64c92debd)) by @yeongseon
* clarify issue handoff and work states ([35c1c8c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/35c1c8cddd10785e1d4389b630492b3d174fa4d0)) by @yeongseon
* clarify local issue and PR evidence ownership ([#1166](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1166)) ([aaf8b19](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/aaf8b1974383688d5be4da8822689110d4364a4f)) by @yeongseon
* clarify sqlalchemy-cubrid local issue and PR evidence ([aaf8b19](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/aaf8b1974383688d5be4da8822689110d4364a4f)) by @yeongseon
* clarify when scoped type ignores are acceptable ([f8f37fb](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f8f37fbe05825244fec3e0470b6e8191d09ea64e)), refs [#1101](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1101) by @yeongseon
* complete historical release comparison links without rewriting original notes ([#1167](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1167)) ([250ae53](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/250ae53129b2201342f7640d6d8deb8336859bd2)) by @yeongseon
* complete missing comparison links across published historical releases ([250ae53](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/250ae53129b2201342f7640d6d8deb8336859bd2)) by @yeongseon
* consolidate v1.12.1 release notes into reader-focused changes ([4e26ebe](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/4e26ebee313aa92d68c7119cb5b3a73b4e9e9eee)) by @yeongseon
* **contributing:** describe the lifecycle of temporary scripts and repair tools ([#1316](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1316)) ([1876263](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1876263d6efe35bc60325b13fea206fad5c3d228)) by @yeongseon
* correct CUBRID 10.2 feature support guidance ([34a4952](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/34a4952530ebfac1a638edd470f6629267baa0d1)), refs [#1082](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1082) by @yeongseon
* correct factual errors in historical release notes ([#1340](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1340)) ([fb3d28c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fb3d28c047c99081527d2e325c5460d79a7a4f7a)), refs [#1338](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1338) by @yeongseon
* correct headings and historical facts in older release notes ([#1184](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1184)) ([ccb8adf](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ccb8adf383a5d04bdd0fea65e2c2565fae277373)) by @yeongseon
* correct live CI claims in translated READMEs ([10a31cc](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/10a31cc662ca6d62d34cf38dc9a72c5da114642b)), refs [#1075](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1075) by @yeongseon
* correct release note layout flagged by Copilot ([#1180](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1180)) ([11a5179](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/11a51797d82d85f3c94ed9bb6aec00957c3685b7)) by @yeongseon
* correct the PyPI 1.2.2 yank statement in the v1.2.2 notes ([#1187](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1187)) ([4b6a867](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/4b6a8672cb1bb76b033da7421b4eae1cb979d150)) by @yeongseon
* correct the PyPI 1.2.2 yank statement in the v1.2.3 notes ([#1186](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1186)) ([f4876ad](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f4876ad51b1cee83abea3e65580f720bce01581d)) by @yeongseon
* credit human authors in the v0.7.1 to v1.4.1 release notes ([#1330](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1330)) ([51c7d47](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/51c7d478119c9c44f572be90b40cdc8aaa8e1c53)) by @yeongseon
* credit human PR author of v1.2.2 Alembic fixes ([98ce55e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/98ce55e83ce2cb2356ba9bf95c9671a1d5a29624)) by @yeongseon
* credit the v1.11.0 external contributor ([#1199](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1199)) ([578cc62](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/578cc6232899a4a219627c3c0e5f2fcba7908e2b)) by @yeongseon
* credit the v1.11.6 contributor ([#1202](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1202)) ([b88795a](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b88795a4bff77adc10dabd14ad4eab7293a93a52)) by @yeongseon
* credit v1.11.5 contributors and add omitted test changes ([#1201](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1201)) ([f6b0f39](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f6b0f397ae67e6f273fcb62078eaa7d615b3ae97)) by @yeongseon
* credit v1.8.0 contributors and add omitted merged changes ([#1198](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1198)) ([24926e3](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/24926e3c56978e73c294e337f6527090600f45be)) by @yeongseon
* credit verified human author in v1.11.7 notes ([#1224](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1224)) ([da75b8f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/da75b8f2601765047db2e9bf39b33888dbfb4c5a)) by @yeongseon
* credit verified human author of v1.11.7 documentation change ([da75b8f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/da75b8f2601765047db2e9bf39b33888dbfb4c5a)) by @yeongseon
* credit verified human author of v1.5.1 fixes ([856b6c8](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/856b6c854c20f63cc2f145368e4b412cb5b02270)) by @yeongseon
* credit verified human PR author for v1.2.1 fixes and tests ([3ec0adb](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3ec0adb05d600e217655dacecb3f5a6bd5b73cee)) by @yeongseon
* credit verified v1.12.1 human PR authors ([b115781](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b11578178805109bee2f06764d572ba6a191c113)) by @yeongseon
* credit verified v1.2.2 Alembic fixes author ([#1228](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1228)) ([98ce55e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/98ce55e83ce2cb2356ba9bf95c9671a1d5a29624)) by @yeongseon
* credit verified v1.4.3 contributions ([#1283](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1283)) ([9ab3a32](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/9ab3a32de13fde14b869f8089eb4f5385753c002)) by @yeongseon
* credit verified v1.5.0 feature and test authors ([fdf2cb4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fdf2cb40fd3929ff6db2edb075db5c6445333ea5)) by @yeongseon
* curate v1.12.1 release notes and synchronize published body ([#1168](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1168)) ([e29c85f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/e29c85faf73d0a437a5d987c9a53eaf6215b870b)) by @yeongseon
* define issue handoff and development states ([#1326](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1326)) ([35c1c8c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/35c1c8cddd10785e1d4389b630492b3d174fa4d0)) by @yeongseon
* describe what the dialect now handles for the PyPI CUBRIDdb 9.3 driver ([#1328](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1328)) ([d146583](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/d1465830f6a8cc3b53917cc377753ca4e4b5a554)) by @yeongseon
* **dialect:** document dialect options, MERGE builder and string type arguments ([#1315](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1315)) ([46da694](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/46da6943c76517f597f365eb2003df8a7a8fc792)), refs [#1292](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1292) by @yeongseon
* drop duplicated release-please bullets from the v1.12.0 notes ([#1194](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1194)) ([3837b49](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3837b49d8e3c034d6925430b77ee95ed69bb0be8)) by @yeongseon
* explain Apple silicon options for the CUBRID lab ([7c6e1e6](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7c6e1e69ba3485104ba8f372d788a92df77a3517)), refs [#1088](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1088) by @yeongseon
* explain missing greenlet errors for async engines ([bbf029e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/bbf029e9c7015830760acb280a2ede58e4776311)), refs [#1084](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1084) by @yeongseon
* fix broker readiness and quickstart troubleshooting ([5886ff7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5886ff74c8b357123f1551c3b3a056f78b1e74e1)), refs [#1080](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1080) by @yeongseon
* fix Markdown layout across published release notes ([#1229](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1229)) ([a1656bc](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a1656bc07fe2f634b6ec16094d31b7be142800ad)) by @yeongseon
* fix published site links to repository files ([136fbc8](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/136fbc816571aec01a9d394c7a6b12db5cb61187)), refs [#1076](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1076) by @yeongseon
* fold duplicated release-please bullets in the v1.11.5 notes ([#1216](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1216)) ([864fab3](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/864fab3312e39897f672ec8ed8826a3f2510d37d)) by @yeongseon
* fold duplicated release-please bullets in the v1.9.0 notes ([#1215](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1215)) ([9fbbc80](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/9fbbc80778a0f7c678fc57a0fde3899ce85f6e0d)) by @yeongseon
* give users a consistent support and questions path ([abbaca4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/abbaca4182087b64f45f083c8fda3a096f58ebf2)), refs [#1078](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1078) by @yeongseon
* guide translated users to their first CUBRID connection ([b0b06d0](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b0b06d043f5b7a863e6ec450aa3e48edc018eba5)), refs [#1074](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1074) by @yeongseon
* highlight user-visible changes in v1.7.0 and v1.7.1 ([#1178](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1178)) ([80e4026](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/80e4026a667fc506aa64c01b292c579daa6edae4)) by @yeongseon
* improve published release note spacing and reader summaries ([385d942](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/385d94267b9c5255891d0da9065f3628d5708a7a)) by @yeongseon
* introduce reader-focused summaries for seven lengthy releases ([#1173](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1173)) ([1a4087c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1a4087c738c0df87cc81d53e490649e5b1dc34b0)) by @yeongseon
* keep SQLAlchemy dialect contribution rules in this repository ([#1286](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1286)) ([ee51192](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ee511920a055b6182b4112cf5c92177e73b6d553)) by @yeongseon
* label the 1.8.0 PRD as a historical snapshot ([7dc5c9f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7dc5c9f7fa43aaa52f34ef441b8b36f3905f0a9d)), refs [#1096](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1096) by @yeongseon
* make published release notes easier to read ([#1246](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1246)) ([385d942](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/385d94267b9c5255891d0da9065f3628d5708a7a)) by @yeongseon
* make PyPI README links and demo render correctly ([97a855c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/97a855cc89a743440de3e0c13327eb5f437161b7)), refs [#1097](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1097) by @yeongseon
* make the v1.10.0 release notes easier to scan ([#1348](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1348)) ([74b60ea](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/74b60ea80a1f90329a47ba30821363f22cc392e0)), refs [#1256](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1256) by @yeongseon
* make the v1.11.0 release notes easier to scan ([#1345](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1345)) ([2a1c467](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2a1c467bbfb775452022835bd863df992351d721)), refs [#1253](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1253) by @yeongseon
* make the v1.11.5 release notes easier to scan ([#1341](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1341)) ([86f56f7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/86f56f7f9d8ff529c4adb6294b29f01b1bde430d)) by @yeongseon
* make the v1.7.0 release notes easier to scan ([#1347](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1347)) ([3468135](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3468135fe08ca820588a0abec09d9eeeaf94e920)), refs [#1255](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1255) by @yeongseon
* make the v1.7.1 release notes easier to scan ([#1346](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1346)) ([c005bb9](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c005bb914db17e3c9e129ebd873cb2536c75e6ac)), refs [#1254](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1254) by @yeongseon
* make the v1.8.0 upgrade and SQL changes easier to read ([#1342](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1342)) ([f2b931f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f2b931f8ceaf8bacd23e2ced719e027ea793d2ac)), refs [#1252](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1252) by @yeongseon
* make v1.12.1 release notes concise and user-focused ([#1174](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1174)) ([4e26ebe](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/4e26ebee313aa92d68c7119cb5b3a73b4e9e9eee)) by @yeongseon
* mark the revised compatibility policy in the v1.0.0 notes ([#1188](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1188)) ([0b16bf7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/0b16bf729f569f41b6554d26e605d0bb3fef74bb)) by @yeongseon
* merge the v1.7.1 documentation sections and credit the contributor ([#1197](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1197)) ([6307bcb](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6307bcb56ee7de898cc3dbce3e3a452a5cd0feac)) by @yeongseon
* move the curated 1.12.3 notes into Unreleased ([#1219](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1219)) ([0f4f331](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/0f4f331bc90f83e75335e546cbda126b6849a612)) by @yeongseon
* order the v1.6.0 notes sections by policy ([#1193](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1193)) ([aa440be](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/aa440be0eaca59e2aa7301a6193209260d43b51e)) by @yeongseon
* order the v1.7.0 notes sections and credit verified contributors ([#1196](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1196)) ([d79ed67](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/d79ed6712795da8f819acd7f425a76e432da8d79)) by @yeongseon
* point the connection guide to the version terminology section ([#1312](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1312)) ([0241a92](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/0241a92f5ff9573ab9f0ecd6c8bf856842eadb88)) by @yeongseon
* prepare accurate notes for nine historical draft releases ([#1231](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1231)) ([8f9d57c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/8f9d57cb3ef9ffecf678f1b1db77968152bb95e9)) by @yeongseon
* **release:** attribute six v1.9.0 additions to verified contributors ([#1244](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1244)) ([af55847](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/af55847107cb9a80703739b3d9ae34aa637b5b19)) by @yeongseon
* **release:** attribute v1.11.0 CI and test improvements ([#1241](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1241)) ([6569a42](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6569a421dc8a66b124a5c91b670a5e5fcde93984)) by @yeongseon
* **release:** clarify and credit v1.12.0 release notes ([#1233](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1233)) ([7b66526](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7b66526b4c16c212a476784df7500ce881c83b9d)) by @yeongseon
* **release:** clarify v0.1.0 draft upgrade and feature notes ([#1266](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1266)) ([fb6b0f3](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fb6b0f348c30bf1216d21ffb41b5820be360d61e)) by @yeongseon
* **release:** clarify v0.2.0 SQL features and documentation ([#1267](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1267)) ([24eed61](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/24eed61b7be2b7da242cd45adc7f14daa724d86f)) by @yeongseon
* **release:** clarify v0.3.0 Alembic and testing changes ([#1268](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1268)) ([dfb3d02](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/dfb3d027fe2693df0c2567c4bcadada22f381ae1)) by @yeongseon
* **release:** clarify v0.6.0 migration support and historical driver limits ([#1273](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1273)) ([ee941ce](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ee941cee57bf59fe388a6b1db252e9516f418fab)) by @yeongseon
* **release:** clarify v1.10.0 license inventory and compatibility notes ([#1259](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1259)) ([050b441](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/050b4412d1ae75b2479e16af3e5ba1ac5db87ccb)) by @yeongseon
* **release:** clarify v1.11.5 documentation and validation notes ([#1275](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1275)) ([fa2980c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fa2980c6242ba0513318b6a86d61af282ed26044)) by @yeongseon
* **release:** clarify v1.5.0 compatibility and benchmark notes ([#1258](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1258)) ([ef7e13b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ef7e13b194356c5c0c984b8faee43488f1884bf3)) by @yeongseon
* **release:** clarify v1.7.0 connection and literal safety notes ([#1262](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1262)) ([c4a74d9](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c4a74d9aea57ec0785c37e3f4ba672cba37b6be1)) by @yeongseon
* **release:** clarify v1.7.0 driver canaries and async setup ([#1280](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1280)) ([fc8089e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fc8089e642fecf7c869cc5bbbfd79070c51e1649)) by @yeongseon
* **release:** clarify v1.7.1 application and cross-version tests ([#1279](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1279)) ([31069e0](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/31069e009e2a7f744d29902cdfc361c3a89f5471)) by @yeongseon
* **release:** clarify v1.7.1 reflection fixes and test coverage ([#1261](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1261)) ([a9003ee](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a9003ee8362615c6b061719cf89779bb71d2707c)) by @yeongseon
* **release:** clarify v1.8.0 autocommit and reflection behavior ([#1263](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1263)) ([5dc314f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5dc314f0a1546ff9a9ddedfe0352a041663de004)) by @yeongseon
* **release:** clarify v1.8.0 compliance and mutation test notes ([#1277](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1277)) ([811a396](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/811a396f96978c051bb457a2eeb69b36298a1568)) by @yeongseon
* **release:** clarify v1.9.0 driver tests and integration setup ([#1264](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1264)) ([5dd50e8](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5dd50e8774aa52d622f5fae2d1ee7843f69d54ea)) by @yeongseon
* **release:** clarify v1.9.0 integration cleanup and failures ([#1276](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1276)) ([f9ba6e0](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f9ba6e05a933a6cec3709247e571530fbae859a9)) by @yeongseon
* **release:** complete v1.11.5 change and upgrade credits ([#1238](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1238)) ([20bacd8](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/20bacd8efe48db356c149a6994a046ed1c3bddb4)) by @yeongseon
* **release:** correct v1.12.1 release notes ([#1232](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1232)) ([ee0f96e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ee0f96ed50ea764c67034d661664b0a3bd7f630e)) by @yeongseon
* **release:** credit and link v1.9.0 added changes ([af55847](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/af55847107cb9a80703739b3d9ae34aa637b5b19)) by @yeongseon
* **release:** credit the verified v1.4.2 ping contribution ([#1282](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1282)) ([2d5c7d6](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2d5c7d6990a86955926247e3cbfc8a57e62d2f26)) by @yeongseon
* **release:** credit v1.11.0 CI and test changes ([6569a42](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6569a421dc8a66b124a5c91b670a5e5fcde93984)) by @yeongseon
* **release:** credit v1.11.0 upgrade and behavior changes ([19a07be](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/19a07beabac8b7f3d7b505c89dfed5a5dc75356a)) by @yeongseon
* **release:** credit v1.11.0 upgrade and package changes ([#1240](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1240)) ([19a07be](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/19a07beabac8b7f3d7b505c89dfed5a5dc75356a)) by @yeongseon
* **release:** credit v1.11.5 CI and tests with source PRs ([b011986](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b011986852b688512a2c63fb09697e3ad8e9299d)) by @yeongseon
* **release:** credit v1.11.5 documentation and remove duplicate entry ([50dc7ee](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/50dc7ee7796b73369ca98fcf11882ebdf4590107)) by @yeongseon
* **release:** credit verified human changes in v1.4.2 ([2d5c7d6](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2d5c7d6990a86955926247e3cbfc8a57e62d2f26)) by @yeongseon
* **release:** credit verified v1.11.5 dialect fixes ([#1235](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1235)) ([58f754b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/58f754b8a9fbad362c93cbfadca1bf659252a780)) by @yeongseon
* **release:** deduplicate v1.10.0 and credit verified changes ([eff375f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/eff375fd51ef4b5d986f316b5eda8c9d1267a6c0)) by @yeongseon
* **release:** document v0.5.0 SQL features and historical limits ([#1272](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1272)) ([7d6b234](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7d6b234b291dfa9947365ee8f5a0f4a0b7be414c)) by @yeongseon
* **release:** finish v1.11.5 change credits and historical references ([20bacd8](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/20bacd8efe48db356c149a6994a046ed1c3bddb4)) by @yeongseon
* **release:** freeze release candidates only when their review starts ([#1295](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1295)) ([ee52eb5](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ee52eb5215b8242f2380871d72f95c4099e8da41)) by @yeongseon
* **release:** improve v1.11.0 user-facing notes ([a2c7701](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a2c770103c1b38d914e12080e19ac8aa2a3cbcc5)) by @yeongseon
* **release:** keep standard sections and concise contributor credits ([#1250](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1250)) ([5fbcb4b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5fbcb4bb6c564298cf187f7eac34950a969393b9)) by @yeongseon
* **release:** make historical draft v0.2.0 reader-friendly ([24eed61](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/24eed61b7be2b7da242cd45adc7f14daa724d86f)) by @yeongseon
* **release:** make historical draft v0.3.0 reader-friendly ([dfb3d02](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/dfb3d027fe2693df0c2567c4bcadada22f381ae1)) by @yeongseon
* **release:** make historical draft v0.3.2 reader-friendly ([845d086](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/845d08655dfd7a7afe0dfa5eca347eaa5bfcde6a)) by @yeongseon
* **release:** make historical draft v0.4.0 reader-friendly ([7fc6997](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7fc6997903350938a3f351e555a832feb8571ffd)) by @yeongseon
* **release:** make historical draft v0.5.0 reader-friendly ([7d6b234](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7d6b234b291dfa9947365ee8f5a0f4a0b7be414c)) by @yeongseon
* **release:** make historical draft v0.7.0 reader-friendly ([d1ceba0](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/d1ceba0bba6716bb307b49be44cd222f4398ccc4)) by @yeongseon
* **release:** make v0.7.0 pycubrid draft concise and traceable ([#1274](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1274)) ([d1ceba0](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/d1ceba0bba6716bb307b49be44cd222f4398ccc4)) by @yeongseon
* **release:** make v1.7.1 detailed notes easier to read ([a9003ee](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a9003ee8362615c6b061719cf89779bb71d2707c)) by @yeongseon
* **release:** make v1.8.0 detailed notes easier to read ([5dc314f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5dc314f0a1546ff9a9ddedfe0352a041663de004)) by @yeongseon
* **release:** make v1.9.0 detailed notes easier to read ([5dd50e8](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5dd50e8774aa52d622f5fae2d1ee7843f69d54ea)) by @yeongseon
* **release:** organize v0.3.1 draft documentation and cleanup ([#1269](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1269)) ([94f2c89](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/94f2c89adbb5c5d2e67a461a477a133b58ad52b1)) by @yeongseon
* **release:** organize v0.3.2 draft documentation changes ([#1270](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1270)) ([845d086](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/845d08655dfd7a7afe0dfa5eca347eaa5bfcde6a)) by @yeongseon
* **release:** reconcile and credit v1.12.0 changes ([7b66526](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7b66526b4c16c212a476784df7500ce881c83b9d)) by @yeongseon
* **release:** remove duplicate v1.10.0 entries and verify credits ([#1242](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1242)) ([eff375f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/eff375fd51ef4b5d986f316b5eda8c9d1267a6c0)) by @yeongseon
* **release:** restore omitted v1.10.0 CI and dependency updates ([c0d0afa](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c0d0afa24bb323c6ebc44a7b1f54b1e6894578a4)) by @yeongseon
* **release:** restore omitted v1.11.6 CI change ([#1234](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1234)) ([e496ce2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/e496ce244ffa9ba994afb9fccf4cd78c8dca1b58)) by @yeongseon
* **release:** restore omitted v1.11.6 release automation change ([e496ce2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/e496ce244ffa9ba994afb9fccf4cd78c8dca1b58)) by @yeongseon
* **release:** restore v1.10.0 CI changes missing from the notes ([#1243](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1243)) ([c0d0afa](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c0d0afa24bb323c6ebc44a7b1f54b1e6894578a4)) by @yeongseon
* **release:** separate v0.4.0 connection changes from CI coverage ([#1271](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1271)) ([7fc6997](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7fc6997903350938a3f351e555a832feb8571ffd)) by @yeongseon
* **release:** shorten v1.11.0 tooling notes while preserving upgrade guidance ([#1260](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1260)) ([a2c7701](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a2c770103c1b38d914e12080e19ac8aa2a3cbcc5)) by @yeongseon
* **release:** shorten v1.11.5 upgrade notes and key fixes ([#1249](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1249)) ([87a2f10](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/87a2f1033d452af12daf4a549cac4306066dde5b)) by @yeongseon
* **release:** simplify v1.10.0 historical notes ([1dfbd59](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1dfbd59d2e4d82748d030ae82b0d4b03feddd33a)) by @yeongseon
* **release:** simplify v1.10.0 license and localization notes ([#1281](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1281)) ([1dfbd59](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1dfbd59d2e4d82748d030ae82b0d4b03feddd33a)) by @yeongseon
* **release:** simplify v1.11.0 support and CI notes ([#1278](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1278)) ([aad9a42](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/aad9a42f301da3bb7867f7bfcee8f312fa006c22)) by @yeongseon
* **release:** simplify v1.11.5 internal tooling notes ([#1265](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1265)) ([5b2d5d3](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/5b2d5d3a4f646b7b8f5d522ebcf03f9c737a3dca)) by @yeongseon
* **release:** verify v1.11.0 documentation attribution ([#1239](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1239)) ([ee6b6a4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ee6b6a49b9a873dcc06722843bd4c7749e1343ae)) by @yeongseon
* **release:** verify v1.11.5 CI and test contributor credits ([#1237](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1237)) ([b011986](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b011986852b688512a2c63fb09697e3ad8e9299d)) by @yeongseon
* **release:** verify v1.11.5 documentation credits and remove duplicate ([#1236](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1236)) ([50dc7ee](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/50dc7ee7796b73369ca98fcf11882ebdf4590107)) by @yeongseon
* **release:** verify v1.9.0 change and workflow author credits ([#1245](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1245)) ([2590136](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2590136967663a10c00332842f2c8f192c9b1c12)) by @yeongseon
* remove contest deadline from Korean README sync guidance ([#1160](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1160)) ([06744db](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/06744dbaf9925cd908d6afef6df9e49a49667ac6)) by @yeongseon
* remove obsolete organization roadmap and board references ([#1284](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1284)) ([ab8c6d7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ab8c6d7f4eda1ff727c026ed026ea22ee332146c)) by @yeongseon
* remove unsupported CUBRID-Python install advice ([e74b96e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/e74b96e9039216c3e7bec66edc5760f201240740)), refs [#1083](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1083) by @yeongseon
* replace v1.11.6 and v1.11.7 commit dumps with release summaries ([#1170](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1170)) ([9d5b8f0](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/9d5b8f0c3fec70101a58cf28a10667e8cd3a3bcc)) by @yeongseon
* restore published v1.2.0 details missing from the changelog ([#1209](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1209)) ([ef778d5](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ef778d511ac69fe6ea7f82147ff0a1292a208ab5)) by @yeongseon
* restore published v1.6.0 PR references and test results ([#1210](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1210)) ([e060875](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/e060875c0591eecac58f97442cf38e198f65944a)) by @yeongseon
* restore the v0.8.0 support boundary and date the pycubrid pin ([#1207](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1207)) ([bea6cef](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/bea6cef39330ffe86c9f8e5f44a5e4dd782c95b0)) by @yeongseon
* restore the v1.1.0 async dialect requirements ([#1208](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1208)) ([b176bf6](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b176bf6371ae77d5ecb446b51767085202f59b6b)) by @yeongseon
* restore v1.2.1 human contributor credits ([#1227](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1227)) ([3ec0adb](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3ec0adb05d600e217655dacecb3f5a6bd5b73cee)) by @yeongseon
* restore v1.5.0 human contributor credits ([#1226](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1226)) ([fdf2cb4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fdf2cb40fd3929ff6db2edb075db5c6445333ea5)) by @yeongseon
* restore v1.5.1 human contributor credits ([#1225](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1225)) ([856b6c8](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/856b6c854c20f63cc2f145368e4b412cb5b02270)) by @yeongseon
* restore verified human author credits in v1.12.0 notes ([#1223](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1223)) ([4219029](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/4219029ff27b00a10277e77d34eaac58a2d366eb)) by @yeongseon
* restore verified human author credits in v1.12.1 notes ([#1221](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1221)) ([b115781](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b11578178805109bee2f06764d572ba6a191c113)) by @yeongseon
* restore verified v0.7.1 performance and package notes ([#1211](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1211)) ([a0f608b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a0f608bd7bb835611d7863a1638b0a73bf0e9e10)) by @yeongseon
* rewrite three historical release notes with clear upgrade guidance ([6890392](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6890392c56db038e7fd594b07fdb726c70c537d7)) by @yeongseon
* rewrite v1.4.1, v1.4.2 and v1.5.1 release notes ([#1176](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1176)) ([6890392](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/6890392c56db038e7fd594b07fdb726c70c537d7)) by @yeongseon
* rewrite v1.7.0–v1.11.5 release notes around user-visible changes ([#1179](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1179)) ([06ce186](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/06ce1864a7f95ceb9683e71171b93662b03cfb27)) by @yeongseon
* shorten the v1.9.0 release notes without losing compatibility details ([#1343](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1343)) ([ee1a9ef](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ee1a9ef9a89ed484534ec35e93cf119ba3ab99ef)) by @yeongseon
* standardize release notes and verified contributor credits ([#1152](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1152)) ([ed3c78f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ed3c78f1a50c7b9d4f0691fe81b3a181bd89f32c)) by @yeongseon
* standardize v1.10.0 note headings and credit verified contributors ([#1195](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1195)) ([2fbc165](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/2fbc16557b0fb3d780793627986a197299a1d436)) by @yeongseon
* standardize v1.9.0 note headings and credit verified contributors ([#1200](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1200)) ([478e80c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/478e80cbb90a5b046ebbad96b37e67b400965e53)) by @yeongseon
* synchronize four verified historical GitHub Releases safely ([#1161](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1161)) ([46f91a2](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/46f91a2b1f764998863bf9e7ad6e914706c0c2e2)) by @yeongseon
* tidy the v1.11.0 notes without changing user-facing entries ([#1213](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1213)) ([3ce6c2e](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3ce6c2e75a3ee1639bc46225473c465ba96b8191)) by @yeongseon
* track issue work without project boards ([c80d6e4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c80d6e47bb0e420a72166d46927617f3adeba3c9)) by @yeongseon
* use issues and pull requests without project boards ([#1327](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1327)) ([c80d6e4](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c80d6e47bb0e420a72166d46927617f3adeba3c9)) by @yeongseon
* use pycubrid URLs in translated connection examples ([59dd870](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/59dd8708d274225a003a6d0be91d682d46c7f19a)), refs [#1073](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1073) by @yeongseon
* use standard section headings in the v1.2.1 notes ([#1189](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1189)) ([f8bac96](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/f8bac960a54955401f6f700480c8b99ed2fd5b6f)) by @yeongseon
* use standard section headings in the v1.3.0 notes ([#1190](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1190)) ([c70aa2c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c70aa2cd6de871592d7ed883f38562bcf5fb12e1)) by @yeongseon
* use standard section headings in the v1.4.0 notes ([#1191](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1191)) ([0c5fa90](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/0c5fa90f9d2e3256132e5682dcb6e586285bc0a9)) by @yeongseon
* use standard section headings in the v1.5.0 notes ([#1192](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1192)) ([280fa6c](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/280fa6c2ca43b4b8364f283de380c3b58f370737)) by @yeongseon

### CI

- **Manual CI lane for the PyPI CUBRIDdb 9.3 driver** — the new manual-only `cubriddb-pypi.yml` workflow installs the project with the `[cubriddb]` extra, as users do (pip and uv currently install the PyPI 9.3.0 source archive `9.3.0.0001` as 9.3.0.1), records the driver's distribution and compiled-in `_cubrid.__version__`, and runs `make integration` on Python 3.12 and CUBRID 11.4, listing every failing test. It is evidence, not a required check or release gate, and is expected to fail until the known driver limitations are resolved. The driver-version report in the other live lanes now also prints `_cubrid.__version__` ([#1146](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1146)) by @yeongseon.
- **Each change is listed once in release candidates** — when a curated `[Unreleased]` entry already cites a pull request or issue, the release changelog composer now drops the release-please entry generated for the same pull request or referenced issue, instead of listing the change twice. Generated entries without a matching reference, or crediting a contributor the curated entry does not credit, are kept, and released sections are unchanged ([#1100](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1100)) by @yeongseon.

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

- **MERGE assignment keys from other tables now raise `CompileError` (#847)** — A bound key in `when_matched_then_update()` or `when_not_matched_then_insert()` must be a column of the target (or its alias); a source-table column with the same name, previously resolved as the target column, now raises `CompileError` naming that table. Use the target's column (`target.c.name`) or string key `"name"`. String keys, unbound `sa.column()` keys and the column-list shorthand `when_not_matched_then_insert([source.c.id, ...])` are unchanged, as are valid SQL and bind order ([#895](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/895)) by @yeongseon.

- **Other changes that can need action** — Alembic `alter_column()` nullability and comment changes now require `existing_type` (#861). Passing `display_width` or `values` to the types listed under Deprecated emits a `DeprecationWarning` (#870). Unless `create_engine(no_backslash_escapes=...)` is passed, the first connection probes the server's backslash mode and fails on an unexpected result (#863). Reflected string and date server defaults now come back as quoted SQL literals (#865). `CUBRID_PORT` is deprecated in favor of `CUBRID_TEST_PORT` (#1008).

### Added

- **Offline tests now save results (#1019)** — `make test` writes `junit.xml`, `coverage.xml` and `summary.json` (`PASS`/`FAIL`/`INCOMPLETE`) to the gitignored `test-results/test/`, which `make clean` removes. Failed suites still exit nonzero; test selection and the 95% coverage threshold are unchanged ([#1022](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1022)) by @yeongseon.

- **Integration tests now save diagnostics (#1020)** — `make integration` writes JUnit results, a summary, redacted environment details and, on failure, `service.log` under `test-results/integration/` (or `INTEGRATION_RESULTS`). Missing or all-skipped results report `INCOMPLETE` and exit nonzero; cleanup failures and rejected runs report `FAIL`, not a stale success. Credentials are masked in recorded commands and logs ([#1032](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1032)) by @yeongseon.

### Changed

- **Development commands are clearer and interrupted integration runs clean up predictably (#1009)** — an interrupt during `docker compose up -d` in `make integration` waits one `INTEGRATION_STOP_GRACE` interval, then sends SIGTERM and allows a second interval before SIGKILL; other interrupted steps get SIGTERM, then SIGKILL after the grace period. **Ordinary stalled Compose calls do not have a timeout.** New `test-fast`, `format-check` and offline-only `verify` targets are added; `make doctor` checks Python 3.11+, missing tools and the Ruff/Mypy pins, and `make format` verifies tool versions. Tool commands remain overrideable through Make variables ([#1010](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1010)) by @yeongseon.

### Deprecated

- **`make check-all` (#1009)** — now an alias of `make check` that prints a deprecation notice on stderr; it will be removed after the next minor release. `make test-offline` remains an alias of `make test` ([#1010](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1010)) by @yeongseon.

- **`CUBRID_PORT` (#1008)** — use `CUBRID_TEST_PORT`, which wins when both are set. When it is unset, `CUBRID_PORT` is still honoured by `docker-compose.yml`, `make docker-up` and `make integration` (the last two print a deprecation warning); other targets ignore it, so a value exported for another CUBRID tool causes no warning ([#1017](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1017)) by @yeongseon.

- **Unused `display_width` and `values` type arguments (#870)** — `display_width` (`SMALLINT`, `BIGINT`) and `values` (`CHAR`, `VARCHAR`, `NCHAR`, `NVARCHAR`, `STRING`) never changed the DDL or any behavior; passing them now emits a `DeprecationWarning`. They are still accepted and ignored, and will be removed in a future major release. The unused private `CubridTypeCompiler._get` helper is removed ([#891](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/891)) by @yeongseon.

### Fixed

- **aggregate_order_by() on a filtered GROUP_CONCAT names FILTER in its error (#995)** — on SQLAlchemy 2.1, `aggregate_order_by(func.group_concat(col).filter(cond), col)` still raises `CompileError`, but now says CUBRID has no `FILTER (WHERE ...)` clause instead of claiming the call is not a `GROUP_CONCAT`. Every other form renders as before ([#996](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/996)) by @yeongseon.

- **aggregate_order_by() no longer drops its ORDER BY (#991)** — on SQLAlchemy 2.1, `func.group_concat(col).aggregate_order_by(col.desc())` silently rendered `GROUP_CONCAT(col)`, returning values in an unspecified order; it now renders `GROUP_CONCAT(col ORDER BY col DESC)`, also with `DISTINCT` and in `HAVING`, with boolean items grouped (#970). Any other function, including `aggregate_strings()`, raises `CompileError`, as no other CUBRID aggregate takes `ORDER BY` (verified for `JSON_ARRAYAGG`, `COUNT`, `MAX`, `SUM` and `MEDIAN`). `within_group()` and SQLAlchemy 2.0 are unchanged. Verified on CUBRID 11.4; not verified on 10.2, 11.0 or 11.2 ([#994](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/994)) by @yeongseon.

- **GROUP_CONCAT DISTINCT, ORDER BY and SEPARATOR no longer fail (#990, #984)** — an extra pair of argument parentheses made CUBRID reject the modifiers (-493). `func.group_concat(col.distinct())` and `literal_column("col ORDER BY col DESC SEPARATOR ';'")` now run, and `GROUP_CONCAT((x))` renders as `GROUP_CONCAT(x)`. Boolean arguments are grouped once (#970); values are unchanged. Still unsupported (see `FEATURE_SUPPORT`): a separate `SEPARATOR` argument, more than one argument, and SQLAlchemy 2.1's `aggregate_strings()` (`aggregate_order_by()` is fixed by #991). Verified on CUBRID 11.4; not verified on 10.2, 11.0 or 11.2 ([#989](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/989)) by @yeongseon.

- **EXISTS and AND/OR as a simple CASE value no longer fail (#987)** — a bare `AND`/`OR`/`NOT`/`EXISTS` `value=` operand of `case()`, such as `value=and_(...)` or `value=exists()`, is now parenthesized as CUBRID requires, like `THEN`/`ELSE` values (#982); columns, bind parameters, comparisons and every other rendering are unchanged. The documentation adds three CUBRID limits: a boolean-result `CASE` without a non-NULL `ELSE` (such as a single `WHEN`) can fail with -495 with or without grouping, so pass `else_=`; CUBRID 11.4 evaluates a `CASE` window `ORDER BY` or `PARTITION BY` item as a constant, without an error; and a boolean-valued `CASE` fails as a `GROUP BY` item (-493). Verified on CUBRID 11.4; not verified on 10.2, 11.0 or 11.2 ([#988](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/988)) by @yeongseon.

- **EXISTS and AND/OR as a CASE THEN or ELSE value no longer fail (#982)** — a bare `AND`/`OR`/`NOT`/`EXISTS` `THEN` or `ELSE` value of a searched or simple `case()`, such as `and_(...)` or `exists()`, is now parenthesized as CUBRID requires. `WHEN` conditions and other renderings are unchanged. Verified on CUBRID 11.4; not verified on 10.2, 11.0 or 11.2 ([#985](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/985)) by @yeongseon.

- **Boolean expressions now compile in CAST, function, and some window arguments (#970)** — a bare `EXISTS`, `NOT`, `AND` or `OR` used as a CAST or function argument (in SELECT, filters, joins or updates), and `EXISTS` or `NOT` in window and `WITHIN GROUP` ordering or partitioning, are now parenthesized as CUBRID requires. SQLAlchemy splits a window `and_()` or `or_()` into separate items, which can change the meaning; keep it with a list such as `over(order_by=[and_(...)])` or `.self_group()`. `WHERE`/`HAVING`/`ON` are unchanged, and CUBRID still rejects Boolean `GROUP BY` items, even function-wrapped; `docs/FEATURE_SUPPORT.md` replaces the earlier guidance (#971). Verified on CUBRID 11.4; not verified on 10.2, 11.0 or 11.2 ([#972](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/972)) by @paikend.

- **EXISTS and AND/OR inside a CAST, a function or ORDER BY no longer fail (#968)** — a bare `AND`/`OR`/`NOT`/`EXISTS` expression used as an ORDER BY item, or inside a CAST or function that is a SELECT column or ORDER BY item (also through `type_coerce()`, labels and sort modifiers), is now parenthesized instead of failing with -493; for example `select(cast(and_(...), Integer))`, `select(func.coalesce(exists(), False))`, a Boolean `TypeDecorator` with `column_expression()`, and `order_by(exists())`. `WHERE`, `HAVING`, `ON`, `GROUP BY`, `CASE` conditions and window `ORDER BY` are unchanged. CUBRID rejects a boolean `GROUP BY` item even in parentheses; group by a SELECT-list label instead (see `docs/FEATURE_SUPPORT.md`) ([#969](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/969)) by @yeongseon.

- **Boolean expressions in SELECT lists now compile (#966)** — CUBRID rejects unparenthesized `EXISTS`, `NOT`, `AND`, and `OR` expressions in SELECT results. The dialect now groups these expressions, including labeled columns, subqueries, and CTEs; `select(exists().where(...))` and `session.query(q.exists()).scalar()` work. Their use in `WHERE`, `HAVING`, join conditions, and `CASE` conditions remains unchanged ([#967](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/967)) by @paikend.

- **Repeated isolation re-apply failures no longer lose the retry marker (#937)** — after a successful commit or rollback, `do_begin()` retries a failed isolation-level re-apply. If that retry also failed, the pending marker was cleared too early, so a later **direct dialect `do_begin()`** could start work without restoring the level. The marker now stays pending until a re-apply succeeds or a new level is set. SQLAlchemy's normal `Connection` rollback had masked this gap in the observed reproduction. The preceding commit/rollback still succeeds and no work is replayed. Applies to `cubrid+pycubrid://` and `cubrid+aiopycubrid://` ([#947](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/947)) by @yeongseon.

- **Server errors no longer cause false disconnects (#916)** — With pycubrid 1.13's `error_source == "server"`, sync and async connections no longer treat unrelated server error codes (-1000 to -1200) or misleading error text as CAS connection failures. Actual CAS errors, unknown origins, and pycubrid versions before 1.13 retain previous behavior; the supported pycubrid range is unchanged ([#938](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/938)) by @yeongseon.

- **`bool` JSON path indices are rejected (#914)** — because `bool` is an `int` subclass, `json_col[True]` or `json_col[("items", False)]` rendered paths such as `$[True]`, which CUBRID 10.2 and 11.4 reject (-494) only after the statement is sent. `JSONIndexType` and `JSONPathType` now raise `TypeError` before any SQL is sent (`sqlalchemy.exc.StatementError` on execution, `sqlalchemy.exc.CompileError` with `literal_binds`). Integer (including `0`, `1` and negative) and string components render byte for byte as before on SQLAlchemy 2.0 and 2.1 ([#917](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/917)) by @yeongseon.

* **scripts:** dispose reflection probe engine on every exit path ([#977](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/977)) ([1303262](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/13032624148045302d0edcdfe245a28ce4c20f01)) by @CloudCorpRecords

- **`INSERT` / `REPLACE ... FROM SELECT` over a CTE renders the `WITH` clause after the column list (#897)** — `insert(t).from_select([...], select(cte))` and the dialect's `replace()` equivalent always failed, because CUBRID 10.2 and 11.4 reject a leading `WITH c AS (...) INSERT ...` (-493). They now render `INSERT INTO t (...) WITH c AS (...) SELECT ...`; recursive CTEs and bind order are unchanged, and live INSERT, recursive INSERT and REPLACE cases pass on CUBRID 10.2 and 11.4 ([#899](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/899)) by @yeongseon.

- **Unique-constraint reflection fails closed on a catalog mismatch (#848)** — `get_unique_constraints()` silently omitted a unique index that `db_index` lists but `SHOW INDEXES` does not, which Alembic autogenerate would read as a constraint to create. Such a mismatch now raises `InvalidRequestError` naming the unresolved and resolved indexes; a verified-empty catalog still returns `[]`. No such mismatch has been seen on a live CUBRID server; this hardens the reflection invariant ([#896](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/896)) by @yeongseon.

- **Garbage-collected async connections are terminated (#872)** — on SQLAlchemy 2.0.44+, when a checked-out `cubrid+aiopycubrid://` connection is garbage-collected, its socket is now closed and its pycubrid session retired, even after the connection's event loop has closed, instead of the pool logging "cannot be safely terminated" and the stream raising a `ResourceWarning`. An invalidated connection closes with `CLOSE_DATABASE`. Earlier SQLAlchemy 2.0 releases keep the old behavior ([#894](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/894)) by @yeongseon.

- **`on_duplicate_key_update()` is cacheable (#871)** — `INSERT ... ON DUPLICATE KEY UPDATE` no longer emits SQLAlchemy's "will not make use of SQL compilation caching" `SAWarning` or recompiles on every execution; a cached statement binds each execution's own values, on SQLAlchemy 2.0 and 2.1 ([#893](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/893)) by @yeongseon.

- **Reflection of names containing `:name`, collection type classes and join linting (#870)** — reflecting a table named like `x :y` or `w (:z)` no longer fails with "A value is required for bind parameter 'y'" (the SQL sent is unchanged); `SET(Integer)` with a type class no longer fails `create_all`; and SQLAlchemy's join linter no longer reports a joined select as a cartesian product or misses a real one ([#891](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/891)) by @yeongseon.

- **Expression, descending, filtered and prefix indexes reflect and autogenerate (#869)** — `LOWER(a)`, `b DESC`, `WHERE c > 3` and the prefix `a(5)` now reflect as `expressions`, `column_sorting` and the new `cubrid_where` / `cubrid_length` index options; before, an expression index was dropped with "Skipping index" and re-proposed by autogenerate on every run, and the others reflected as plain columns. `CREATE INDEX` now renders the two new options, previously ignored silently, and Alembic compares them after normalization, so an unchanged index is not proposed again; detecting a changed sort order, filter or prefix length needs Alembic 1.12+ ([#885](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/885)) by @yeongseon.

- **Alembic renders CUBRID collection member types with the dialect prefix (#868)** — autogenerate wrote members such as `cubrid_types.MULTISET(sa.MONETARY())`, which raised `AttributeError` when the migration file was loaded. Members from `sqlalchemy_cubrid.types` now render as `cubrid_types.MONETARY()` and so on; generic SQLAlchemy members keep `sa.` ([#884](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/884)) by @yeongseon.

- **`Select.fetch()` renders as `LIMIT` (#867)** — `select(...).fetch(2)` and `.offset(1).fetch(2)` emitted `OFFSET ... ROWS FETCH FIRST n ROWS ONLY`, which CUBRID rejects (-493); they now render as `LIMIT 2` and `LIMIT 1, 2`. `percent=True` and `with_ties=True` raise `CompileError`, since CUBRID has no `LIMIT` form for them ([#880](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/880)) by @yeongseon.

- **JSON path keys use JSON string escaping (#866)** — a key containing `"` failed with -1200 "Invalid JSON path", and one containing `\` silently returned `None`. Keys are now built with `json.dumps()`, so `"` and `\` are backslash-escaped and non-ASCII characters become `\uXXXX` escapes that do not depend on the connection charset ([#879](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/879)) by @yeongseon.

- **String and date server defaults reflect as quoted SQL literals (#865)** — `get_columns()` dropped string defaults' quotes (`'it''s'` reflected as `it''s`; `''`, the string `'NULL'`, dates and `'CURRENT_USER'` were also misreported), breaking reflected `CreateTable` SQL and Alembic's `existing_server_default`. Non-numeric defaults are now read from `SHOW CREATE TABLE` (one extra query per table that has one) and reflect as `'it''s'`, `''`, `'NULL'`, `date '01/02/2020'` or the function itself; a string column's `'5'` stays quoted, and numeric defaults of numeric columns are unchanged ([#878](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/878)) by @yeongseon.

- **Alembic `alter_column` emits CUBRID-compatible SQL for nullability, dropped defaults and comments (#861)** — `nullable=` and `server_default=None` produced syntax errors and `comment=` could not be rendered, so autogenerated nullability changes failed at `upgrade`. Nullability and comment changes now use `MODIFY` / `CHANGE` and require `existing_type` (otherwise `ValueError`); a dropped default emits `ALTER COLUMN c SET DEFAULT NULL`, or two `MODIFY` statements for a `NOT NULL` column. Because CUBRID 10.2/11.0 reset attributes that `MODIFY` omits while 11.2+ keep them, `NULL`, `DEFAULT NULL` and `COMMENT ''` are stated explicitly where needed, and an existing column without a default no longer gets `DEFAULT NULL`. In offline `--sql` mode, a UNIQUE `create_index` raises the documented "live connection" `CompileError` instead of `NoInspectionAvailable` ([#877](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/877)) by @yeongseon.

- **`literal_binds` and other compile options reach CAST operands, ON DUPLICATE KEY UPDATE values and collection members (#862)** — these positions dropped the compile options, so `literal_binds` and Alembic `--sql` output kept `?` placeholders, a functional `Index` over a `CAST` rendered a `?`, and `server_default=cast(literal(5), String(10))` failed `create_all` with "wrong number of parameters". CUBRID itself still rejects `CAST` in a function-based index on 10.2 and 11.4 ([#875](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/875)) by @yeongseon.

- **`has_table()`, `get_table_names()` and `get_view_names()` see only the current owner's classes on CUBRID 11.2 and later (#864)** — they also matched other owners' classes, although an unqualified name resolves only in the current user's schema: another user's `own_t` made `create_all()` skip `dba.own_t` (so the next `INSERT` failed), `MetaData.reflect()` abort with `NoSuchTableError`, and same-named tables appear twice. They now filter on `owner_name = CURRENT_USER`. CUBRID 10.2 and 11.0 are unchanged ([#876](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/876)) by @yeongseon.

### Security

- **Inline literals follow the server's backslash mode (#863)** — on a server with `no_backslash_escapes=no`, `literal_binds` rendered the value `\' OR 1=1 -- ` as `'\'' OR 1=1 -- '`, producing SQL that matched every row, because the dialect assumed `no_backslash_escapes=yes`. Unless `create_engine(no_backslash_escapes=...)` pins the mode (and skips the probe), the first connection now probes the server with `SELECT CHAR_LENGTH('\\')`, and literal rendering doubles backslashes when the server treats them as escapes; an unexpected probe result fails the connection. Native `ENUM` labels use the same escaping. A dialect that has not connected still assumes the server default ([#874](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/874)) by @yeongseon.

### Documentation

- **The architecture pages show the end-to-end driver communication flow (#1013)** — `docs/ARCHITECTURE.md` (English and Korean) adds a Mermaid diagram tracing the three URL variants through their drivers to the Broker, CAS and database server, and the site now renders Mermaid diagrams instead of showing code. Documentation only ([#1016](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1016)) by @yeongseon.

* **agents:** require repository-local issue authoring checks ([#1012](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1012)) ([7a15ad7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7a15ad76d2fb0e98e8026f0fae9c1324463db781)) by @yeongseon.

* **contributing:** fix single-test pytest node example ([c04a380](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c04a380f4b9a512fa8ecb892324fe6b59fde31b7)), refs [#881](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/881) ([#1029](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1029)) by @HarshRajSinghania

* **triage:** clarify PR overlap and execution precedence ([1d082cc](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/1d082ccccb2010b2ab6db474eaeca770431a6b7e)), refs [#1023](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1023) by @yeongseon.

- **Two CUBRIDdb result differences are documented (#1003)** — because CUBRIDdb binds values on the server, a `CASE` whose `THEN`/`ELSE` values are all bound parameters returns a string (`'10'`, not `10`), and bound parameters in a `GROUP_CONCAT` argument and `aggregate_order_by()` item fail with -494. The Driver Compatibility guide gives workarounds (`cast(..., Integer)`; `aggregate_order_by(literal_column("1"))`). The dialect is unchanged ([#1004](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1004)) by @yeongseon.

- **Boolean expressions that still failed on CUBRID (#968)** — the `docs/FEATURE_SUPPORT.md` note and its `case()` workaround are replaced, since the #970 fix makes those forms run. Do not use that workaround inside a window: CUBRID 11.4 evaluates a `CASE` (or `if()`) in a window `ORDER BY` or `PARTITION BY` as a constant ([#971](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/971)) by @yeongseon.

- **The first-connection course has one page per lesson (#943)** — Lessons 3 (save and read back a row), 4 (roll back a transaction) and 5 (cleanup and `docker rm -f -v`) move from the Quick Start to their own English and Korean pages, and its old anchors point to them. Every command was rerun against `cubrid/cubrid:11.4` with the published SQLAlchemy 2.1.4, sqlalchemy-cubrid 1.11.0 and pycubrid 1.13.0 ([#956](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/956)) by @yeongseon.

- **The first-connection course starts with two lesson pages (#943)** — preparing CUBRID and Python (`docs/LESSON_PREPARE.md`) and running the first query (`docs/LESSON_FIRST_QUERY.md`) are separate English and Korean pages, and the site shows previous/next links. Every command was rerun as written against `cubrid/cubrid:11.4` with the published SQLAlchemy 2.1.4, sqlalchemy-cubrid 1.11.0 and pycubrid 1.13.0 ([#955](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/955)) by @yeongseon.

- **The documentation site is organized by reader question (#943)** — the English and Korean navigation is now Start here, How-to guides, Reference, Help, and Project and internals. No page moved and no URL changed. Two accidental headings in the Connection guide and Feature Support are plain paragraphs again ([#954](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/954)) by @yeongseon.

- **Development documentation now identifies unreleased content (#946)** — the documentation site says it is built from `main` and may describe candidate or abandoned changes, and records its exact source commit. `RELEASING.md` distinguishes candidates, partial publication, abandoned versions and verified published packages, explains bot-PR CI states such as `action_required` (observed on #910), and lists the evidence to record; a `__version__` value on `main` is not proof of publication ([#951](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/951)) by @yeongseon.

- **The quickstart removes the lab's Docker volume too (#948)** — the English and Korean Quick Start now remove the lab with `docker rm -f -v sqlalchemy-cubrid-quickstart`, deleting the anonymous volume with the tutorial's `testdb` that `docker rm -f` left behind ([#949](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/949)) by @yeongseon.

- **The README async examples are complete programs (#941)** — the `Async` examples used module-level `await`, a `SyntaxError` in a script; they now run through `asyncio.run(main())`, always dispose their engine, and the insert example creates and drops its own `sqlalchemy_async_example_notes` table. Both were run against CUBRID 11.4. The Korean README carries both programs and the German, Hindi, Russian and Chinese READMEs the corrected query example; an offline test in the always-running lint job checks them ([#944](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/944)) by @yeongseon.

- **A first SQLAlchemy connection for CUBRID beginners (#940)** — the Quick Start (English and Korean) is one recommended path from installing `sqlalchemy-cubrid[pycubrid]` to a first query, a committed row, a rollback, cleanup and the real first-connection errors, run as written against CUBRID 11.4; the README and documentation home link to it. The CUBRIDdb C-extension driver built from source stays supported; only the `[cubrid]` and `[cubriddb]` extras are deprecated ([#942](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/942)) by @yeongseon.

- **CAS error -4 is described as an interrupted statement (#873)** — pycubrid 1.13.0 reports -4 (`ER_INTERRUPTED`, a `KILL QUERY`) as `Interrupted` with SQLSTATE `HY008` (earlier releases: `08S01`), and the guides now say so. The dialect still treats -4 as a non-disconnect, as since 1.9.0 (#572); the Driver Compatibility guide also explains why -671 (`ER_CSS_RECV_OR_SEND`) is not a disconnect code ([#939](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/939)) by @yeongseon.

- **A maintainer's review is the standalone-agent alternative to Copilot (#926)** — `AGENTS.md` and the contributor guides say a standalone agent PR waits for a substantive GitHub Copilot review or a maintainer's review recorded on the PR (maintainer decision, 2026-10-15); a reviewer agent run by the implementer does not count ([#927](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/927)) by @yeongseon.

- **Agent guidance split into task guides (#907)** — the root `AGENTS.md` keeps every rule and gains a task routing table, while detailed context moved unchanged to `docs/agents/`; `scripts/check_agents_docs.py` checks its links, commands and version pins, and with `--retained-from REF` that no earlier line was dropped. No code, CI or release behavior changes ([#918](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/918)) by @yeongseon.

- **Python 3.15 limitation of garbage-collected connection cleanup (#872)** — with SQLAlchemy 2.1 (2.1.0 to 2.1.4 checked) on CPython 3.15, a pooled connection reclaimed by the cycle collector is never terminated: its socket closes only through Python's stream finalizer with a `ResourceWarning`, and its pool slot stays checked out (python/cpython#136189). Every dialect is affected, sync pools included; SQLAlchemy 2.0 and Python 3.14 and earlier are not. The Connection Guide and Support Matrix describe it ([#909](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/909)) by @yeongseon.

* **contributing:** clarify good-first-issue access for human contributors ([#913](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/913)) ([7a2512f](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7a2512f4694ee5129081ad87a449cae8bb3d4a88)) by @yeongseon.

* correct the documented boolean expression positions ([#986](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/986)) ([7c7958b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7c7958be8e82fa49dd3fb56591ad5a5108e16e30)) by @SuellenQwQ (first contribution 🎉)

* **types:** correct the namespace of reflected timezone types ([#973](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/973)) ([9480036](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/9480036c1a184d6227c93562c67452ded57cfbc8)), refs [#882](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/882) by @CloudCorpRecords (first contribution 🎉)

- **The README and the documentation site show the CUBRID Lab repository icon (#886)** — the README, its translations and the site's logo and favicon use the sqlalchemy-cubrid icon from one immutable [cubrid-lab/brand](https://github.com/cubrid-lab/brand) commit ([#900](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/900)) by @yeongseon.

- **`ROADMAP.md` no longer presents shipped releases as plans (#833)** — the Python 3.10 retirement (1.10.0) and Python 3.15 support (1.11.0) moved to Completed, and version numbers are replaced by links to `CHANGELOG.md`, PyPI and `docs/SUPPORT_MATRIX.md` ([#844](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/844)) by @yeongseon.

- **`docs/PERFORMANCE.md` has a current same-CUBRID baseline (#830)** — raw pycubrid, SQLAlchemy Core and ORM timings on one CUBRID 11.4 server at `main` `a570ea4` (dialect source as in v1.11.0; pycubrid 1.12.0, SQLAlchemy 2.1.4 and 2.0.54, Python 3.12; 5 trials each) from the new `scripts/bench_dialect_baseline.py`, with raw data in `benchmarks/2026-10-12-dialect-baseline/`. No dialect hotspot or regression was found; runtime behavior is unchanged ([#843](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/843)) by @yeongseon.

- **The dialect baseline now covers CUBRID 10.2, 11.0 and 11.2, CUBRIDdb, the async driver and concurrent connections (#830 follow-up)** — a 2026-10-13 run through pycubrid, CUBRIDdb (built from cubrid-python v11.3.0.51) and the async driver on 1, 4 and 8 connections (`benchmarks/2026-10-13-dialect-baseline-followup/`). Reads differ little; pycubrid and the async driver scale with connections, while CUBRIDdb, whose C extension never releases the GIL, does not scale across threads. Runtime behavior is unchanged ([#860](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/860)) by @yeongseon.

- **The feature support table no longer marks CUBRID `BLOB` / `CLOB` as fully supported (#829)** — they now show ⚠️: DDL, type mapping, reflection, binding `bytes` / `str` and `NULL` round trips work, but an ordinary Core/ORM read of a non-NULL value returns the driver's LOB locator on `cubrid://`, `cubrid+pycubrid://` and `cubrid+aiopycubrid://` (Known Issue 6 in `docs/DRIVER_COMPAT.md`). Documentation only ([#842](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/842)) by @yeongseon.

* **agents:** correct stale entry points, integration commands and doc map in AGENTS.md ([#846](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/846)) ([340a587](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/340a587ae1cfe6f98123669f25555948f84255cd)) by @yeongseon.

* **i18n:** update the Python requirement in the German README ([#837](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/837)) ([fcdb443](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fcdb443891cef3a2109e9f419b5ba374434401b9)), refs [#698](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/698) by @yeongseon.

* **i18n:** update the Python requirement in the Hindi README ([#839](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/839)) ([3f79d2d](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3f79d2db34694417f31b46f0573f2038d6c2a0ee)), refs [#699](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/699) by @yeongseon.

* **i18n:** update the Python requirement in the Russian README ([#840](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/840)) ([793b6ef](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/793b6ef8d6a5b7a764b8589bef6d77b90da84fbf)), refs [#700](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/700) by @yeongseon.

### CI

* **release:** restart release preparation after the abandoned 1.11.4 ([#1037](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1037)) ([3184d9b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3184d9b462bae6e2dd50d187e33abf83f44e5775)), refs [#1011](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1011) by @yeongseon.

- **CI publishes the offline test summary and uploads results on success and failure (#1021)** — offline jobs write JUnit, coverage and `summary.json`, add the summary to the job summary and upload `test-results/`, and integration jobs upload their pytest logs, all with `if: always()`; the live-lane summary follows #1020. Test selection, the 95% coverage floor and permissions are unchanged ([#1027](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1027)) by @yeongseon.

- **The `make-integration` jobs also upload `test-results/integration/` (#1020)** — the live results of `make integration` join `make-integration.log` in the existing `pytest-logs-make-integration-*` artifact; nothing else in the workflows changes ([#1032](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1032)) by @yeongseon.

- **A change to `docker-compose.yml` runs the test that pins it (#997)** — the `tooling` path filter now lists `docker-compose.yml`, so a pull request changing only that file runs `test/test_make_integration.py` ([#999](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/999)) by @yeongseon.

* **release:** verify against the current cookbook and restart after the abandoned 1.11.3 ([#1007](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1007)) ([72bf7be](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/72bf7be9fa0ab27454401b21972a080edd796d13)) by @yeongseon.

* **release:** start release preparation after the abandoned 1.11.2 ([#1006](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/1006)) ([b1a2dfe](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/b1a2dfe825c983a2114025b8cbaa82ff4da6c09d)) by @yeongseon.

- **The CUBRID 11.4 local Docker test database is kept in a named volume (#1000)** — with `CUBRID_VERSION=11.4`, whose image keeps databases in `/home/cubrid/CUBRID/databases`, `docker compose down` lost the data. A second named volume, `cubrid-databases`, now holds that path, `make docker-down` deletes both, and `make integration` refuses a pre-existing `<project>_cubrid-databases`. Checked on CUBRID 10.2, 11.2 and 11.4; opening a database created by another CUBRID version is not verified, so reset before switching `CUBRID_VERSION`. Same fix as cubrid-lab/pycubrid#1004 ([#1001](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1001)) by @yeongseon.

- **The local Docker test database keeps working after its container is recreated (#997)** — the database was registered under the old container ID, so every connection failed with -353 after recreation. `docker-compose.yml` now sets `CUBRID_DB_HOST: localhost` (for 11.4 see #1000 above); for an older volume, `make docker-fix-db-host` rewrites only `testdb`'s host and keeps the data and a `databases.txt.before-fix-db-host` backup, or `make docker-down` (`docker compose down -v`) deletes it. `make integration`, CI and the dialect were not affected. Same fix as cubrid-lab/pycubrid#1001 ([#998](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/998)) by @yeongseon.

- **Repository-tooling tests run when only their inputs change (#964)** — the `tooling` path filter now lists `agent-evals/**`, ten repository-tooling test modules and `test/conftest.py`, and `test_workflow_path_impact.py` checks that every `REPO_TOOLING_MODULES` entry selects the tooling lane ([#965](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/965)) by @yeongseon.

- **Manual agent runs are recorded and summarized as distributions (#906)** — `scripts/agent_eval.py` gains `prompt`, `record` and `summarize`, which record manual runs and summarize them per task and model with a 95% Wilson interval, never a bare pass percentage. Runs are manual-only, from an isolated clone without publish credentials; nothing runs an agent in CI, and no score gates a pull request ([#963](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/963)) by @yeongseon.

- **Agent evaluation tasks for reflection and Alembic (#906)** — `agent-evals/` adds tasks from the #865 and #861 fixes. Neither has recorded live evidence; the Alembic task passes only a candidate that reports the live migration check as not run and says live behavior is not verified. No dialect source or CI lane changes ([#962](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/962)) by @yeongseon.

- **Offline agent evaluation tasks and grader (#906)** — `agent-evals/` and `scripts/agent_eval.py` grade a coding agent's patch for a frozen historical fix (the first task is the #914 fix) against hidden tests, allowed files, documentation, the CHANGELOG and its claims; a live CUBRID claim without a recorded live run, compiled or bound SQL reported as live evidence, or calling the supported CUBRIDdb driver deprecated fails. `make agent-eval-check` re-grades recorded fixtures without a model or database, in the `repo` lane; no agent score gates a pull request ([#961](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/961)) by @yeongseon.

- **The documentation check's shell scanner matches pycubrid again (#959)** — `scripts/_markdown.py` takes pycubrid's final `_substitution_end()` byte for byte (cubrid-lab/pycubrid#978), fixing `case`/`esac`, `;&`/`;;&` and comment handling inside substitutions. No other checker rule changes ([#960](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/960)) by @yeongseon.

- **The documentation check allocates site anchors as the site does (#957)** — the shared `scripts/_markdown.py` uses the slugifier configured in `mkdocs.yml` and the `toc` extension's id-collision rules; ordinary headings keep their anchors. The change matches cubrid-lab/cubrid-cookbook-python#402 and cubrid-lab/pycubrid#976 ([#958](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/958)) by @yeongseon.

- **The site build runs when the MkDocs provenance hook changes (#952)** — `scripts/docs_provenance_hook.py`, loaded by `mkdocs.yml` since #951, is now a `site` path-filter input, so a pull request changing only the hook runs `mkdocs build --strict` ([#953](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/953)) by @yeongseon.

- **Prepare release checks the `last-release-sha` baseline override (#945)** — preparation stops, asking for removal in a normal PR, when the override set after abandoning 1.11.1 is obsolete (a later release containing it passed the publication proof), malformed, unrelated or unreadable, so a stale override cannot make a recovery silently relist shipped commits. An API error is reported as unresolved, nothing is edited automatically, and `RELEASING.md` documents the rule; the current 1.11.1 override is active ([#950](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/950)) by @yeongseon.

- **The documentation check handles shell substitutions as pycubrid does (#934)** — `scripts/_markdown.py` takes pycubrid's substitution fixes (cubrid-lab/pycubrid#947): `$(...)`, `<(...)` and `>(...)` belong to their word and their bodies are checked as commands, a `#` after a substitution is not a comment, and an unclosed quote is prose. Review added fixes for `case` patterns, quoted substitutions, arithmetic expansion and newlines, which pycubrid receives next ([#935](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/935)) by @yeongseon.

- **`agent-review` no longer counts empty reply-only Copilot records as review rounds (#933)** — such records could push a PR past the two-round budget and reject valid evidence; a record that opens a thread still counts. Ported unchanged from cubrid-lab/cubrid-mcp-server#349 ([#936](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/936)) by @yeongseon.

- **Advisory review-evidence check added (#905)** — `agent-review.yml` reads GitHub's actual review records with a read-only token and the base-branch `scripts/agent_review_gate.py`, not PR checkboxes or bot summaries. It accepts a substantive Copilot review within the two-round budget, a maintainer `APPROVED` review, or a maintainer `COMMENTED` review opening an inline thread; changes to literal rendering, identifiers, dialect connections/disconnects, Alembic, workflows, release configuration or gate scripts require maintainer approval. Stale reviews, incomplete API data, missing commit identities and **unresolved or author-resolved** critical/security threads do not pass: only maintainer resolution satisfies a critical/security finding. Release-please-only and Dependabot PRs are exempt. Adapted from cubrid-lab/cubrid-mcp-server#341, it **remains advisory**: PRs can spoof its check name, so it must not be required until a trusted identity posts it (#929) ([#1015](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1015)) by @yeongseon.

- **Issue-number lines in block quotes inside list items are reported (#925)** — the `#<digit>` line check now covers quotes such as `- > #750`, which Python-Markdown renders as headings, and parses container prefixes in linear time ([#930](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/930)) by @yeongseon.

- **The documentation check takes link lines from the source and masks inline HTML (#923)** — link line numbers now come from each link's own source, and only what markdown-it actually parsed (inline HTML, autolinks, link tails) is masked before references are checked, so undefined references are no longer hidden or misplaced ([#928](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/928)) by @yeongseon.

- **The documentation check reports lines that the site renders as headings (#920)** — a `docs/` line starting with `#` and a digit is plain text on GitHub but an `<h1>` on the MkDocs site; `scripts/check_docs_links.py` now reports it and asks for `\#`, and the 11 existing cases are escaped ([#924](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/924)) by @yeongseon.

- **Documentation link checks handle more Markdown, HTML, Makefile and shell cases (#921)** — line numbers across multi-line HTML, grouped and double-colon Makefile targets, references hidden by malformed links or comments, shell continuations and redirections, and HTML `<source src>` links, matching the reviewed pycubrid parser (cubrid-lab/pycubrid#940, cubrid-lab/pycubrid#941) ([#922](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/922)) by @yeongseon.

- **Deterministic documentation defects block the merge (#908)** — a new `docs-check` job, required by `matrix-result` when Markdown, `scripts/` or the `Makefile` change, runs `scripts/check_docs_links.py` and `scripts/check_agents_docs.py` and fails with `file:line` on broken link targets or anchors, undefined references, unclosed code fences and nonexistent `make` goals or `scripts/` paths. It parses CommonMark with the pinned `markdown-it-py`, as pycubrid's gate does (cubrid-lab/pycubrid#939), and never fetches external links; the shared `doc-lint` workflow stays advisory. `<!-- docs-check: ignore -->` marks a reviewed false positive ([#919](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/919)) by @yeongseon.

- **Release preparation starts after the abandoned 1.11.1** — `release-please-config.json` sets `last-release-sha` to the 1.11.1 merge, so release-please no longer proposes 1.12.0 with every commit since 1.8.0; RELEASING.md documents setting that override and removing it after the next release is tagged ([#912](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/912)) by @yeongseon.

- **A release commit's `main` push no longer repeats the release's runtime lanes (#737)** — on a release commit, `ci.yml` skips the typecheck, offline, Alembic, packaging and integration lanes that `integration-full.yml` already runs behind the fail-closed `full-matrix-result`, and `integration-full.yml` gains the two pycubrid endpoint steps it lacked; lint, documentation and tooling checks still run. On the 1.11.0 release commit this would have saved 14.1 runner minutes for about 1.4 added; `docs/CI_POLICY.md` records runner minutes after the #760 and #797 consolidation ([#841](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/841)) by @yeongseon.

### Tests

- **The live test for garbage-collected async connections passes in `make integration` again (#872)** — after #1017 bound the Compose broker to `127.0.0.1`, hosts resolving `localhost` to `::1` first (GitHub runners) kept the test's connection alive in an asyncio reference cycle, failing every `make integration` lane and stopping the 1.11.4 release matrix. The test now reuses a pre-opened pooled connection and still requires the leaked connection to be terminated, with no ResourceWarning ([#1035](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1035)) by @yeongseon.

- **The CASE value and GROUP_CONCAT ORDER BY live tests pass with CUBRIDdb (#1003)** — the tests added for #987 and #991 asserted pycubrid's results, so the release matrix's `make integration (cubriddb, …)` lanes failed on CUBRID 10.2 and 11.4 and 1.11.2 was not published. They now pin the CUBRIDdb results above and keep the exact pycubrid assertions ([#1004](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1004)) by @yeongseon.

- **ORDER BY output matches SQLAlchemy's for plain items (#968)** — the dialect renders ORDER BY one item at a time, so a guard test compares its output with SQLAlchemy's own `order_by_clause` for ORDER BY items that need no grouping ([#969](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/969)) by @yeongseon.

- **SHOW TRACE read failures release both result handles (#854)** — a new mocked offline test checks that when reading the `SHOW TRACE` rows raises, `trace_query()` closes both results, still attempts `SET TRACE OFF` and passes the read error to the caller; it does not replace integration coverage on a real server. No production code changes: the behaviour already held, so no failure could be demonstrated ([#931](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/931)) by @tnalbant (first contribution 🎉).

- **Garbage-collection tests no longer depend on the cycle collector (#872)** — the live async terminate and closed-event-loop tests now commit before losing the connection, so the pool terminates it when the last reference goes on every supported Python, including 3.15. The reference-cycle case is a separate expected failure where the pool cannot clean it up (SQLAlchemy 2.1 on CPython 3.15). Both had failed on all four Python 3.15 cells of the full compatibility matrix ([#894](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/894)) by @yeongseon.

- **Benchmark artifacts verify the measured dialect and carry their provenance in the report (#903)** — `scripts/bench_dialect_baseline.py` stops if the installed `sqlalchemy_cubrid` does not match `--source-sha`, and records the package SHA-256, verification method, image digest, host label and comparable group. Contract `sqlalchemy-cubrid-benchmark-artifact/2` rejects an unverified install such as a PyPI wheel and in-place edits of those fields; `/1` manifests are rejected but kept unchanged, and the pair is re-recorded in `benchmarks/2026-10-14-artifact-pair-v2`. Benchmark tooling only ([#904](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/904)) by @yeongseon.

- **Benchmark results can now be archived and compared with provenance (#901)** — `scripts/bench_artifact.py` exports and validates a `sqlalchemy-cubrid-benchmark-artifact/1` manifest from a complete dialect benchmark report and compares baseline and candidate runs. It records dialect SHA, driver and SQLAlchemy versions, CUBRID image/server, Python/host, a password-redacted connection target (database user and URL query parameters are still recorded), pool settings, workload identity and every trial. Missing files, corrupt data or mixed source revisions are rejected, and differences other than the dialect make results `not comparable`. **Operator-supplied SHA, image digest and host labels are not independently verified** (#903). The pinned v1.11.0-to-main CUBRID 11.4 pair is in `benchmarks/2026-10-14-artifact-pair`; the older #830 archives are unchanged. Benchmark tooling only: no dialect change and no new CI gate ([#902](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/902)) by @yeongseon.

- **Isolated live CTE coverage (#849)** — SQLAlchemy's 14 `CTETest` compliance nodes are strict xfails because their fixture cleanup fails on CUBRID's per-row foreign-key check, so `TestIsolatedCTE849` replays their scenarios on fresh tables against CUBRID 10.2 to 11.4: SELECT, recursive, bound-parameter, UPDATE/DELETE with a CTE subquery and values-via-CTE cases pass, UPDATE/DELETE ... FROM are asserted as documented limits, and INSERT FROM SELECT over a CTE passes since #897 ([#898](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/898)) by @yeongseon.

- **Offline tests for identifier quoting, preflight engine disposal and the reflection probe report (#859, #858, #857)** — `test/test_base.py` covers escaped and reserved identifier quoting, `test/test_check_integration_connection.py` pins disposal of the preflight sync engine on success and on errors, and `test/test_reflection_probe_shape.py` pins the `reflection_probe` report shape with a fake inspector ([#978](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/978), [#979](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/979), [#981](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/981)) by @CloudCorpRecords.

- **Offline tests for select attribute accessors, compile benchmark iterations and version-report fallbacks (#855, #850, #851)** — `test/test_compiler.py` covers select attribute accessors, `scripts/bench_compile.py` validates its iteration count (`test/test_bench_compile.py`), and `test/test_report_driver_versions.py` covers the version report fallbacks ([#1025](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1025), [#1026](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1026), [#1031](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/1031)) by @WilliamK112 (first contribution 🎉).

## [1.11.0] - 2026-10-12

This release introduces Python 3.15 support and a broad set of compatibility, reliability, and test improvements. Review the upgrade notes before adopting it; detailed changes and references follow.

### Upgrade notes

- **Python 3.15 is supported (#666).** Standard GIL builds only. The pycubrid routes (`cubrid+pycubrid://`, `cubrid+aiopycubrid://`) are covered with the pycubrid release that declares Python 3.15 (cubrid-lab/pycubrid#831); the `[pycubrid]` floor stays `pycubrid>=1.8.0,<2.0`. On 3.15, pycubrid 1.10.0 and earlier reject `?charset=ksc5601` because Python 3.15 maps that codec alias to CP949; use `?charset=euckr` or the newer pycubrid. Building the official CUBRIDdb driver with GCC 14 fails on Python 3.14 and 3.15 alike (the two versions compared); see `docs/DRIVER_COMPAT.md` ([#807](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/807)) by @yeongseon.

- **`sqlalchemy-cubrid` no longer installs with SQLAlchemy 2.2 or newer (#774).** The package metadata now requires `sqlalchemy>=2.0,<2.2`, matching the supported range already documented (2.0 and 2.1). SQLAlchemy 2.2 is not released yet (PyPI latest 2.1.4), so no current install changes: 2.0.x and 2.1.x resolve exactly as before. Once 2.2 ships, `pip` keeps resolving SQLAlchemy 2.1.x for this package. SQLAlchemy 2.2 was never verified against the full compatibility matrix and is excluded until it ships and passes it; the cap is then lifted in a later release ([#777](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/777)) by @yeongseon.

- **The `dev` extra is gone; contributors install the `dev` dependency group (#765).** Use `pip install -e . --group dev` (pip 25.1 or later) or `make install` instead of `pip install -e ".[dev]"`, which now installs only the package and warns that the extra does not exist. End users are not affected: the runtime extras (`pycubrid`, `alembic`, `cubrid`, `cubriddb`) are unchanged ([#808](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/808)) by @yeongseon.

### Added

- **Python 3.15 is included in release compatibility testing (#666)** — The package adds the Python 3.15 classifier and `py315` tox environment. Manual and release runs cover Python 3.11–3.15 × CUBRID 10.2/11.0/11.2/11.4 (20 cells), including CUBRIDdb, synchronous/asynchronous pycubrid, cross-driver comparisons, transactional DDL and server restart. The minimum remains Python 3.11; free-threaded Python is not claimed. English/Korean support and developer guides document the pycubrid dependency, CUBRIDdb's GCC 14 build limitation, the compliance lanes kept on 3.14/11.4 and 3.11/10.2, and the C `_decimal` requirement for Decimal subclasses. German/Hindi/Russian/Chinese README translations remain tracked in #698–#701 ([#807](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/807)) by @yeongseon.

### Changed

- **Contributors install tools from dependency groups, not the `dev` extra (#765)** — `pyproject.toml` defines PEP 735 groups (`test`, `lint`, `typecheck`, `security`, `mutation`, `release` and `dev`, which includes all of them plus pre-commit/tox), and `scripts/check_tool_versions.py` checks the pins and group configuration; CI type-check, canary and security jobs install their declared groups. Switch from `pip install -e ".[dev]"` to the `dev` group; runtime extras are unchanged. Tox 4.22+ installs dependency groups, and the `dev` group resolves to the same 73 packages as the former extra. MkDocs tools remain under `.github/docs-requirements/requirements.txt` (#761). Packaging and contributor tooling only; **no dialect runtime change** ([#808](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/808)) by @yeongseon.

- **Package metadata caps SQLAlchemy below 2.2 (#774)** — `sqlalchemy>=2.0,<2.3` became `>=2.0,<2.2` in `dependencies` and in the `dev` and `pycubrid` extras, matching `docs/SUPPORT_MATRIX.md` (`≥ 2.2` unsupported); README, the translated READMEs, `SUPPORT_MATRIX`, `SA_COMPAT`, `ARCHITECTURE`, `PRD` (English and Korean) and `THIRD_PARTY_LICENSES.md` state the same range. The 2.2 forward-compat shims and the weekly `--pre` canary stay: the canary installs SQLAlchemy in a separate explicit step (`>=2.1.0b1,<2.3`) that the package cap does not bind, so it still forward-tests 2.2 pre-releases. Packaging metadata only (release type: patch); no dialect code changes ([#777](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/777)) by @yeongseon.

- **Release verification runs the cookbook's Python 3.11 cell too** — the `verify-cookbook` call to `cubrid-cookbook-python`'s `smoke-test.yml` in `.github/workflows/publish-pypi.yml` is pinned to `bd6749093813d3a447f993fec72ac733adbeae63`, the same commit as the other two package repositories (pycubrid, sqlalchemy-cubrid, cubrid-mcp-server). Since the previous pin the cookbook adds a Python 3.11 cell on release calls (`Smoke Tests (CUBRID 11.4, Python 3.11)`), so release verification needs all three cells (11.2/3.12, 11.4/3.12, 11.4/3.11); `RELEASING.md` lists the third job. CI only; the dialect is unchanged ([#771](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/771)) by @yeongseon.

- **Documentation site builds on pull requests (#786)** — a new `docs-build` job in `ci.yml` runs the `docs.yml` build (including `mkdocs build --strict`) whenever `docs/**`, `mkdocs.yml`, `scripts/generate_llms_full.py`, `.github/docs-requirements/**`, `docs.yml` or `ci.yml` change; the `site` path filter selects it and `matrix-result` requires it whenever selected, and it never uploads or deploys anything. A broken strict build or docs-tool pin bump previously failed only on `main`. CI only; the dialect is unchanged ([#769](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/769)) by @yeongseon.

- **Documentation tools are pinned and superseded security scans are canceled (#761, #762, #764, #747)** — `docs.yml` installs `mkdocs`, `mkdocs-material` and `pymdown-extensions` from Dependabot-maintained exact pins in `.github/docs-requirements/requirements.txt`. CodeQL and security scans cancel only superseded pull-request runs, so scheduled and `main` runs are not dropped. `test/test_workflow_hygiene.py` checks that the compliance job's pinned pycubrid matches the declared dependency floor. Full-integration fuzz and mutation job names no longer promise a nonexistent nightly schedule; fuzz still gates releases. CI only; no dialect change ([#766](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/766)) by @yeongseon.

- **Mutation testing no longer delays releases (#747)** — `publish-pypi.yml`'s `build` waits for the whole called `integration-full.yml`, so the non-gating `mutation-testing` job added its run time (historical median 9.6, maximum 18.1 minutes) to every release. It now runs only when `integration-full.yml` is dispatched manually and is skipped on the release call (`if: ${{ !inputs.sha }}`; the release call always passes `sha`). The Hypothesis fuzz pass still gates the release, and `full-matrix-result` and `publish-pypi.yml` are unchanged. CI only; the dialect is unchanged ([#805](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/805)) by @yeongseon.

- **Offline tests run on the oldest and newest supported Python outside PRs (#734)** — pull requests keep the single representative Python 3.12 cell, while main pushes, the weekly schedule and manual dispatches run the full offline suite (`-m "not integration and not repo"`, 95% coverage floor) on Python 3.11 and 3.14, each uploading its own `coverage-report-py<version>` artifact. `matrix-result` still fails when an offline cell fails, is cancelled or is unexpectedly skipped. CI only; the dialect is unchanged ([#756](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/756)) by @yeongseon.

- **Release validation replaces redundant CI runs (#737)** — the duplicate Python 3.12/CUBRID 11.4/pycubrid `live-smoke` lane was removed because `make-integration` covers it at the same commit. Advisory SQLAlchemy pre-release and oldest-cell CUBRIDdb checks moved from each main push to scheduled/manual runs, and `upstream-canary` moved to Thursday 06:00 UTC. The release's required `integration-full.yml` now runs its own Python 3.11/3.14 offline endpoints instead of relying on an unrelated main-push run. **PR checks are unchanged**; `docs/CI_POLICY.md` records before/after job counts, runner time, failure yield, and coverage ownership. CI only, no dialect behavior change ([#760](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/760)) by @yeongseon.

### Documentation

- **Docs state the Python 3.11+ requirement (#697)** — after 1.10.0 raised `requires-python` to `>=3.11`, `docs/CONNECTION.md`, `docs/DRIVER_COMPAT.md` and `docs/PRD.md` (with Korean copies) still described Python 3.10 (the driver table listed 3.10 as the minimum and 3.14 as pre-release). They now give 3.11 as the minimum and 3.11–3.14 as the tested range, as the full compatibility matrix runs them, and mark 3.10 as not supported from 1.10.0. Historical rows and measurements are unchanged. Docs only ([#803](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/803)) by @yeongseon.

- **The compliance-lane pycubrid pin is labelled as the declared floor (#479)** — `docs/SUPPORT_MATRIX.md` (+ ko) listed the pycubrid compliance lanes as "pycubrid 1.8.0 (recommended)", which read as a recommendation to install 1.8.0. The pin is the declared floor of `pycubrid>=1.8.0,<2.0`, kept on purpose; pycubrid is the recommended driver, and the integration lanes test the latest release. Docs only ([#801](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/801)) by @yeongseon.

- **Private vulnerability reporting is the preferred security channel (#738)** — GitHub private vulnerability reporting is now enabled for the repository. `SECURITY.md` names it as the preferred private route and keeps the maintainer email as the fallback; `README.md` and the translated READMEs say the same. Docs only ([#796](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/796)) by @yeongseon.

- **No more "nightly" full integration (#747)** — `integration-full.yml` has no schedule: it runs on manual dispatch and as the release gate, on Python 3.11–3.14. The PRD CI matrix (+ ko), `docs/TYPES.md` (+ ko), the `test/test_dogfood_orm.py` docstring and `test/version_differential/compare_snapshots.py` wrongly mentioned a nightly run (the PRD also listed Python 3.10); all now describe the current triggers, and the dogfood docstring names the CUBRID versions it actually runs on (10.2 and 11.4). `nightly` remains only as the Hypothesis profile name. Docs and comments only ([#792](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/792)) by @yeongseon.

- **`AGENTS.md` no longer carries stale planning context (#736)** — the "Performance Loop System" snapshot (R3 phases, issues #68/#70 as current work) is replaced by a short statement pointing to `docs/PERFORMANCE.md`, cubrid-benchmark, `ROADMAP.md` and the org project board. Volatile counts and inventories (module count, requirement-flag count, tested CUBRID versions, default Docker version, a test file list including the nonexistent `test_dml.py`) are removed or point to their canonical source. CUBRID dialect and Alembic invariants are unchanged. Docs only ([#757](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/757)) by @yeongseon.

- **Stale facts removed from PRD and DEVELOPMENT docs (#758)** — the nonexistent `test_dml.py` is no longer listed in `docs/DEVELOPMENT.md` and `docs/PRD.md` (and their Korean counterparts); DML tests live in `test/test_compiler.py` (ODKU regressions also in `test/test_regression.py`). The unguarded "12 Python modules", "40+ properties", "314 offline tests" and "3 uncovered lines" counts in `docs/PRD.md` are replaced with descriptions or pointers to the source, and `docs/llms-full.txt` is regenerated. Docs only ([#759](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/759)) by @yeongseon.

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

- **The closing guard also checks the PR title, commit messages and owners with an underscore** — the `PR title` check also reads the PR title and each commit message (with a read-only `pull-requests` token; it fails when a PR has 250 or more commits), and matches owners such as `alice_acme/repo#N` (cubrid-lab/pycubrid#845; same change in cubrid-lab/cubrid-mcp-server#276 and cubrid-lab/cubrid-cookbook-python#294) ([#818](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/818)) by @yeongseon.

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

- **Cookbook release verification is pinned to the cookbook SHA with the PyPI wait** — `verify-cookbook` is pinned to `32e80c6ea9ae78324f764d7b873ffb64b000ddcc` (cubrid-cookbook-python#274), which waits up to 10 minutes for PyPI to serve the requested version; this fixes the 1.10.0 post-publish stale-CDN failure. CI only ([#775](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/775)) by @yeongseon.

- **CHANGELOG lint and composer handle fenced code** — `scripts/lint_changelog.py` and `scripts/compose_release_changelog.py` treat lines inside fenced code as entry content, and the lint gains the duplicate-`###` rule for `[Unreleased]` and releases after 1.10.0. CI only ([#773](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/773)) by @yeongseon.

- **GitHub Release naming and standard release-note sections** — a Release title is exactly its tag (`scripts/check_release_title.py` fails closed on resume or recovery), `scripts/extract_release_notes.py` appends one Full Changelog link, and the lint requires the standard `###` sections for `[Unreleased]` and releases after 1.10.0. CI and release tooling only ([#772](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/772)) by @yeongseon.

### Tests

- **Async cancellation and driver deadlines discard the connection (#479)** — a cancelled (`asyncio.wait_for`) or timed-out (`read_timeout=0.5`) `SELECT SLEEP(5)` now has a live test (`test/test_aio_integration.py::TestAsyncCancellationAndDeadline`) showing the connection is invalidated without leaking a pool slot (cubrid-lab/pycubrid#554, cubrid-lab/pycubrid#556, cubrid-lab/pycubrid#687, cubrid-lab/pycubrid#744). Tests only ([#798](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/798)) by @yeongseon.

- **pycubrid 1.9.0 error classification through SQLAlchemy (#479)** — live sync and async tests on CUBRID 10.2 and 11.4 show a zero `DATE`/`DATETIME` raising `sqlalchemy.exc.DataError` without invalidating the connection (cubrid-lab/pycubrid#492/#512/#543), and foreign-key-restricted `DELETE`/`UPDATE` and a `TRUNCATE` of a referenced table raising `IntegrityError` (cubrid-lab/pycubrid#493; strict expected failures on the pycubrid 1.8.x floor). `docs/DRIVER_COMPAT.md` records two `CUBRIDdb` differences: a zero date escapes as a bare `SystemError`, and a -1284 `TRUNCATE` is `DatabaseError`. Tests and docs only ([#799](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/799)) by @yeongseon.

- **Release-please push guards are pinned (cubrid-lab/pycubrid#801)** — `test/test_release_workflows.py` asserts the exact, ordered guards of `release-please.yml`, and `RELEASING.md` gains the recovery row for abandoning a merged release. Test and docs only ([#789](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/789)) by @yeongseon.

- **Guard for the SQLAlchemy range (#774)** — `test/test_sqlalchemy_range.py` (a `repo` test) fails when the `sqlalchemy` upper bound in `pyproject.toml` (all extras) differs from the pin stated in the README, translated READMEs and docs, or when `SUPPORT_MATRIX` (English and Korean) does not list every minor below the cap as supported and the cap minor as unsupported ([#777](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/777)) by @yeongseon.

- **Live value round trips for pycubrid 1.9.0 fixes (#479)** — sync and async tests cover plain-notation and subclass `Decimal` values, aware datetimes in `DATETIMETZ`/`TIMESTAMPTZ` including the repeated DST hour, NULL-typed results, years 999 and 99, a `?charset=utf8` round trip and all-`NULL` collections (cubrid-lab/pycubrid#517, #518, #413, #542, #519, #86, #483); only the cases that fail on pycubrid 1.8.0, the `[pycubrid]` floor, are strict expected failures there. Known limitation: a `fold=1` datetime in the repeated hour is stored one hour off, because pycubrid binds `DATETIMETZ` without the fold (cubrid-lab/pycubrid#819). Tests only ([#800](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/800)) by @yeongseon.

## [1.10.0] - 2026-10-08

This release raises the minimum supported Python version to 3.11. Applications on Python 3.10 should remain on the compatible 1.9.x line until upgraded. Review the upgrade notes and detailed changes below.

### Upgrade notes

- **Python 3.11 or newer is required (#686).** Python 3.10 reached upstream end of life on 2026-10-01 and its retirement was announced in 1.9.0. On Python 3.10 `pip` keeps installing 1.9.x, the last line that supports it; only the latest release line receives fixes, so 1.9.x gets no further releases. Upgrade Python, recreate your virtual environment and validate your application before upgrading ([#703](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/703)) by @yeongseon.

### Changed

- **tox no longer lists Python 3.10 (#687)** — `py310` is removed from `envlist`, and `typecheck-sa20` type-checks SQLAlchemy 2.0.53 on Python 3.11 instead of 3.10. Local tooling only; CI and the dialect are unchanged ([#728](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/728)) by @yeongseon.

- **Ruff and mypy target Python 3.11 (#688)** — `target-version = "py311"` and `python_version = "3.11"` in `pyproject.toml`, matching the minimum supported version. The rule selection is unchanged and no source needed a fix ([#729](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/729)) by @yeongseon.

- **Disconnect detection drops the Python 3.10 timeout case (#689)** — `CubridDialect._has_oserror_cause` now checks `OSError` directly: from Python 3.11, `asyncio.TimeoutError` is the built-in `TimeoutError`, an `OSError` subclass, so the separate check was obsolete after #686. A `TimeoutError` cause is still treated as a disconnect ([#732](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/732)) by @UsmanGhias.

### Removed

- **Python 3.10 support (#686)** — `requires-python` is `>=3.11` and the 3.10 classifier is gone. CI no longer tests 3.10: the oldest integration cell is Python 3.11 × CUBRID 10.2 × SQLAlchemy 2.0.53, the full matrix covers Python 3.11–3.14 and the Alembic compatibility job runs on 3.11. Because Python 3.10 used to select SQLAlchemy 2.0 by itself (SQLAlchemy 2.1 needs Python 3.11), the oldest CI cell and the Python 3.11 row of the full matrix now pin `sqlalchemy>=2.0,<2.1`; otherwise no live lane would run the ordinary integration tests on the minimum supported SQLAlchemy line. No dialect behavior changes on Python 3.11 or newer ([#703](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/703)) by @yeongseon.

### Documentation

- **Third-party licenses are tracked separately for each installation option (#727)** — the generated `THIRD_PARTY_LICENSES.md` (from `scripts/generate_third_party_licenses.py`) records dependency versions, environment and license classification for runtime, `[pycubrid]`, `[alembic]`, `[cubrid]`/`[cubriddb]` and development installs, separately from packaged wheel/sdist contents. It notes that SQLAlchemy 2.1 no longer installs greenlet by default, identifies MPL-2.0 dependencies (`certifi`, `hypothesis`, `pathspec` in development) and flags GPL-family metadata (including `docutils`) for review. CUBRID-Python is classified as permissive BSD, but the **exact BSD variant is unresolved**. Repository tests check dependency ranges, classifications and review flags, and CI runs them for inventory changes. No runtime change ([#755](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/755)) by @yeongseon.
- **The README and quickstart state Python 3.11 or later (#695)** — the requirement lines, the tested and supported ranges (3.11–3.14) and the FAQ answer in `README.md` and `docs/README.ko.md`, and the prerequisites in `docs/QUICKSTART.md` and `docs/ko/QUICKSTART.md`. Both READMEs' Python 3.10 retirement notice now says the requirement is in effect from 1.10.0 ([#731](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/731)) by @yeongseon.

- **In-page links work on the documentation site (#721)** — the default heading slugifier drops non-ASCII characters, so Korean headings got ids such as `_2` and every Korean table of contents entry was dead; English links written for GitHub's slugs missed too (208 broken anchors). `mkdocs.yml` now uses the Unicode-aware slugifier from `pymdown-extensions`, eight remaining wrong anchors are fixed, and `validation.links.anchors: warn` makes the strict build fail on a new broken anchor ([#722](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/722)) by @yeongseon.

- **Korean documentation clarifies behavior and verification limits (#719)** — corrected the `cursor.lastrowid` fallback's cursor lifetime, `stmt.inserted` support and native Enum support-matrix entry. The new Korean PRD, SQLAlchemy compatibility, release validation and contribution pages were checked for meaning, including “checks not run” versus “could not run.” Their banner says CI checks documentation structure, **not sentence-level translation accuracy**. English documentation and runtime behavior are unchanged ([#720](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/720)) by @yeongseon.
- **The documentation home page states one SQLAlchemy range (#716)** — its ecosystem list said "SQLAlchemy 2.0–2.2" while its first line, the README and the support matrix say 2.0–2.1. Both languages now say 2.0–2.1; the dependency pin (`>=2.0,<2.3`) is unchanged ([#717](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/717)) by @yeongseon.

- **CI fails when a Korean document drifts from its English source (#710)** — `scripts/check_docs_translation.py` compares each `docs/<name>.md` with `docs/ko/<name>.md` and fails on a missing Korean file or a different number of headings (levels 2-4), fenced code blocks or table rows. It runs in the lint job on every event; until now only README drift was checked. Deliberately English-only documents are listed in the script with a reason. The check compares structure, not wording. Same script as cubrid-lab/pycubrid#721 ([#715](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/715)) by @yeongseon.

- **SA_COMPAT, PRD and the release-please validation record are available in Korean (#709)** — added `docs/ko/SA_COMPAT.md`, `docs/ko/PRD.md` and `docs/ko/RELEASE_PLEASE_VALIDATION.md`, and listed the three documents, which were missing from the site navigation, in both languages. Every document under `docs/` now has a Korean counterpart ([#714](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/714)) by @yeongseon.

- **Korean contribution guide (#708)** — `docs/CONTRIBUTING.ko.md` translates the current `CONTRIBUTING.md`, keeping commands, English GitHub conventions, label names and title examples unchanged. It is linked from the Korean README and the Korean navigation. English stays the authoritative version ([#713](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/713)) by @yeongseon.

- **Korean documentation home page and one Korean navigation section (#707)** — `docs/ko/index.md` is the Korean landing page, linked from the English home page and back. The Korean guides, previously three levels deep under "Project → Translations", are now one top-level "한국어" section grouped like the English navigation, and every Korean page is reachable from it ([#712](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/712)) by @yeongseon.

- **Korean support matrix, feature table and CI policy match the English documents (#706)** — `docs/ko/SUPPORT_MATRIX.md` shows the CI matrix as a table and drops a Korean-only closing section; `docs/ko/FEATURE_SUPPORT.md` drops a limitation row (`IS DISTINCT FROM`) that the English table does not list; `docs/ko/CI_POLICY.md` is now a full translation, not a summary. Both CI policy pages are in the site navigation. The English text is unchanged ([#711](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/711)) by @yeongseon.

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

This release makes pycubrid URL options take effect, makes reflection and connection-pool disconnect handling stricter and more accurate, and stops importing Alembic eagerly on Alembic 1.18+. It raises the pycubrid minimum to 1.8.0 and deprecates Python 3.10 and the `[cubrid]` / `[cubriddb]` extras; read the Upgrade notes before upgrading.

### Upgrade notes

- **pycubrid 1.8.0 is now the minimum (#559)** — the `[pycubrid]` extra requires `pycubrid>=1.8.0,<2.0` (was `>=1.3.2`); upgrade the driver together with this release.

- **Reflection errors are no longer hidden (#589, #454)** — `get_foreign_keys()` and the `SHOW CREATE TABLE` fallback of `get_unique_constraints()` no longer turn a failure into a warning and `[]`: disconnects, authorization and driver errors propagate, and a cataloged table without a `SHOW CREATE TABLE` row raises `NoSuchTableError`. `get_columns()` and `get_indexes()` raise `NoSuchTableError` only for a missing table and let other errors, such as syntax errors, propagate. Review code that relies on an empty list or catches `NoSuchTableError` broadly.

- **Invalid type lengths raise `CompileError` (#491, #476, #441)** — explicit negative lengths for character, bit and binary types, and an explicit zero for `CHAR`, `NCHAR` and `BIT`, now raise `CompileError` (an explicit zero previously compiled to a different type). Omitted lengths are unchanged.

- **pycubrid URL query options are applied and validated (#592)** — options such as `?connect_timeout=5`, previously ignored, now reach pycubrid; invalid, repeated or reserved options raise `ArgumentError` from `create_engine()`, and so does `?charset=` with pycubrid 1.8.0.

- **Collection values (#484)** — on the pycubrid drivers, a `set` or `frozenset` bound to a `SEQUENCE` column raises `TypeError`; non-`NULL` collection values cannot be rendered inline (`CompileError`). Typed collection binding itself needs a pycubrid release newer than 1.8.0.

- **Disconnect classification changed (#565, #572, #578, #608, #624, #680)** — the pool now invalidates connections after a `cub_server` stop or restart, a dead CAS or a malformed pycubrid reply, and keeps connections after an interrupted query (`KILL QUERY`, -4) or an application error whose text merely resembles a disconnect message. Review custom error handling that depended on the old behavior.

- **`cubrid://` warns for CUBRIDdb older than 11.3 (#585)** — the PyPI `CUBRID-Python` driver now triggers a `SAWarning` at first connect. Filter it to `"error"` to fail fast, or move to `cubrid+pycubrid://` or a CUBRIDdb built from cubrid-python v11.3.0.51 or later.

- **Deprecations: Python 3.10 and the `[cubrid]` / `[cubriddb]` extras** — 1.9.x still supports Python 3.10, but the following minor release (planned 1.10.0) requires Python 3.11 or later. The extras keep installing the untested PyPI `CUBRID-Python` driver; see Deprecated for the supported install paths.

- **Contributor commands (#594, #575, #567, #593)** — `make test` no longer runs the repository-tooling tests (use `make test-repo`, or `make test-offline` for both lanes). `make integration` defaults to pycubrid (`INTEGRATION_DRIVER=cubriddb` selects CUBRIDdb) and uses its own Docker Compose project, and integration tests fail instead of skipping when a configured server is unreachable or when `CI=true` is set without `CUBRID_TEST_URL`.

### Added

- **Python 3.15 preview preparation** — a manual-only offline and wheel/sdist installation lane (Ubuntu, standard GIL) at an immutable commit. Python 3.15 is not yet officially supported; promotion requires final-runtime and live CUBRID evidence. Routine PR test frequency and supported versions are unchanged ([#667](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/667), [#679](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/679)) by @yeongseon.

- **Driver comparison covers collections; CI rejects all-skipped integration runs (#486)** — `test_collection_roundtrip_agrees` compares `SET` / `MULTISET` / `SEQUENCE` and `NULL` collections between CUBRIDdb and pycubrid, written as SQL literals because released pycubrid cannot bind them (cubrid-lab/pycubrid#567 is on pycubrid main). With #480–#484 closed, this covers the remaining differential contract gap under #479 **except LOBs (#485, out of scope)**. `scripts/check_not_all_skipped.py` now fails integration jobs and `make integration` unless a test actually ran or `--allow-all-skipped "<reason>"` is given. Verified on CUBRID 11.4 with pycubrid 1.8.0 and CI-built CUBRIDdb ([#644](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/644)) by @yeongseon.

- **Recorded `SHOW CREATE TABLE` output for constraint reflection (#611)** — foreign keys are reflected only by parsing `SHOW CREATE TABLE`, fixtures record its output on CUBRID 10.2.18, 11.0.16, 11.2.9 and 11.4.6 for composite and self-referencing foreign keys, every referential action, unusual identifiers and unique constraints. Tests run the recordings through the real parsers (via the #590 adapter) and fail with a diff when a live server's output or reflected constraints differ; `python -m test.test_show_create_table_server_output <url>` records a version. No dialect change ([#627](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/627)) by @yeongseon.

- **`SET`, `MULTISET` and `SEQUENCE` values can bind through pycubrid typed collections (#484)** — on `cubrid+pycubrid://` and `cubrid+aiopycubrid://`, a `list` or `tuple` (and, for `SET` and `MULTISET`, a `set` or `frozenset`) is wrapped in the matching `pycubrid.types` class (cubrid-lab/pycubrid#567). **Those classes are on pycubrid main but not yet released:** with pycubrid 1.8.0, a collection parameter still raises `ProgrammingError`. With every pycubrid version, a `set` or `frozenset` bound to an ordered `SEQUENCE` raises `TypeError` on the pycubrid drivers instead of being sorted; non-`NULL` collection values cannot be rendered inline (`CompileError`), and values read back are not converted. CUBRIDdb is unchanged and binds every collection as a SET, losing MULTISET duplicates and SEQUENCE order (Known Issue 11 in `docs/DRIVER_COMPAT.md`). Live round trips pass on CUBRID 10.2 and 11.4 with pycubrid main and are strict xfails on released pycubrid ([#623](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/623)) by @yeongseon.

- **BLOB/CLOB value contract re-verified on pycubrid 1.8.0 and pycubrid main (#485)** — the LOB tests first verified in #490 move to `test/test_lob_value_contract.py` and were re-run with pycubrid 1.8.0, pycubrid main and CUBRIDdb on CUBRID 10.2 and 11.4. Binding `bytes`, `str` and `NULL` works. **Selecting a non-`NULL` `BLOB`/`CLOB` still returns the driver's LOB locator instead of the value** (a `dict` on sync pycubrid, a bare string on `cubrid+aiopycubrid://`, a `'file:...'` string on CUBRIDdb), because neither pycubrid 1.8.0 nor pycubrid main implements LOB fetch for ordinary cursors (cubrid-lab/pycubrid#441/#442 remain open); these cases are strict xfails. `docs/DRIVER_COMPAT.md` Known Issue 6 and `docs/TYPES.md` are corrected. Tests, CI and docs only ([#636](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/636), [#678](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/678)) by @yeongseon.

- **Ordinary scalar execution verified not to use pycubrid's `compat.native` prepared core (#483)** — pycubrid 1.8.0 includes an opt-in typed scalar-binding cursor under `pycubrid.compat.native` (pycubrid#439), but the SQLAlchemy dialects never import `pycubrid.compat`, so it does not change how they bind parameters. New Core/ORM, sync/async tests on CUBRID 10.2 and 11.4 with pycubrid 1.8.0, pycubrid main and CUBRIDdb, plus guards that fail if the dialect starts using `pycubrid.compat`, keep this verified (Known Issue 12 in `docs/DRIVER_COMPAT.md`). No dialect change ([#637](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/637)) by @yeongseon.


### Changed

- Release preparation moves to SHA-pinned release-please in PR-only mode. Generated Conventional Commit notes are composed with curated Upgrade notes; reviewed candidates still use the existing guarded publisher. Maintainers freeze candidate edits and explicitly start final-head PR CI; see RELEASING.md ([commit ccacf037](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ccacf0375f97576a90eb226155861f5bf96f9d4d)) by @yeongseon.

- **PyPI Trusted Publisher filename** — the guarded release orchestrator is renamed from `release.yml` back to `publish-pypi.yml` (environment `pypi`), the filename that published 1.8.0 and that the PyPI Trusted Publisher is bound to; under `release.yml` publication would have been refused with `invalid-publisher`, as happened in pycubrid (cubrid-lab/pycubrid#681). Release gates are unchanged, and a run of the former publish-only workflow of the same name does not count as a completed release. No dialect behavior, version, dependency or support change ([#683](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/683)) by @yeongseon.

- Omit unsupported coverage badges from badge-sync until a coverage feed exists (#645); workflow correction by @yeongseon ([commit fb683495](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/fb683495319085debedb18b0272b997530f275b2)); the pull request was squash-merged as [commit c2265867](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/c2265867f14fca5b90a2f4ac4c53d324b57b9295).

- Reduce routine PR CI to one representative offline lane and targeted live checks; move full compatibility matrices to explicit dispatch/releases and schedule representative checks weekly ([#659](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/659)) by @yeongseon.

- **KILL QUERY integration test only targets its own session (#634)** — the helper picked its victim by timing, so another server session could be killed or make the test ambiguous. The test now runs its victim under a fresh account, kills only a single exact match for that account (otherwise it fails without KILL) and removes the account afterwards; the test class stays serialized. Verified on CUBRID 10.2/11.4 with both Python drivers. No dialect runtime change ([#640](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/640)) by @yeongseon.

- **On Alembic 1.18+, `CubridImpl` registers through the `alembic.plugins` entry point, so loading the dialect no longer imports Alembic (#595)** — The first `create_engine("cubrid+pycubrid://...")` gets faster (about 18 ms instead of 80 ms in one measurement) and no longer triggers Alembic's seven `INFO` `setup plugin ...` lines (#561); `import alembic` logs one more line, `setup plugin sqlalchemy_cubrid`. Alembic 1.7.2–1.17, an already imported Alembic or unreadable package metadata keep the direct import, so a default `env.py` works on every supported Alembic, and a plugin failure warns instead of breaking `import alembic`. CI tests Alembic 1.7.2, 1.17.2, 1.18.0 and the latest release, and `docs/ALEMBIC.md` replaces the #561 statement that no lazy hook exists ([#616](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/616)) by @yeongseon.

- **pycubrid-specific disconnect rules moved into the pycubrid dialects; redundant async overrides removed (#596)** — internal refactor, no behavior change on any supported driver path: `PyCubridDialect` now matches pycubrid's `errno` (-111, -199, -224, -677 and the legacy-renumbered CAS code -1002) and client-side messages, `CubridDialect` keeps the shared code / `OSError`-cause / message layering and reads only CUBRIDdb's `int` code in `args[0]`, and `PyCubridAsyncDialect` inherits `on_connect()` and `do_ping()`. In 12,801 `is_disconnect()` probes the pycubrid dialects classify every probe identically, and `CubridDialect` differs only for pycubrid-shaped errors. Contributors add pycubrid rules in `PyCubridDialect._has_disconnect_code()` or `_disconnect_messages` ([#633](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/633)) by @yeongseon.

- **`get_unique_constraints()` skips `SHOW CREATE TABLE` when the catalog shows indexes but no unique one (#610)** — reflecting a current user's table (before CUBRID 11.2, any visible table) with a primary or foreign key and no `UNIQUE` now takes 2 requests instead of 3. The fallback, and the previous result, is kept when the catalog lists no index of the table, and on CUBRID 11.2+ for another owner's class, which still raises `NoSuchTableError` (and is left out of `get_multi_unique_constraints()`). Results were identical in 42 cases on CUBRID 10.2, 11.2 and 11.4; a failing catalog query still raises. `docs/FEATURE_SUPPORT.md` describes the condition ([#629](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/629)) by @yeongseon.

- **Repository-tooling tests run in a separate required lane (#594)** — `make test`, tox's `py3xx` environments and CI's `offline-tests` job now select `-m "not integration and not repo"`; the Makefile and repository-script tests carry the new `repo` marker. The offline run dropped from 103.4 s to 22.0 s with coverage unchanged, and the 182 repository-tooling tests stay required in the new `repo-tests` CI job. New targets: `make test-repo` and `make test-offline` (both lanes, with coverage); tox gains a `repo` environment ([#621](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/621)) by @yeongseon.

- **Ruff/Mypy pre-commit hooks and tox lint/typecheck environments use the `pyproject.toml` dev pin (#558)** — pre-commit runs Ruff and Mypy from the active `.[dev]` environment, and tox and CI's `typecheck` job install the dev extra instead of hardcoded versions, so Dependabot's Ruff/Mypy bumps no longer leave `.pre-commit-config.yaml` and `tox.ini` stale and fail the tooling consistency gate ([#570](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/570)) by @yeongseon.

- **pycubrid 1.8.0 is now the minimum (#559)** — the `[pycubrid]` extra requires `pycubrid>=1.8.0,<2.0` (was `>=1.3.2,<2.0`), because the contract tests already need the 1.8.0 fixes (NOT NULL / foreign-key `IntegrityError`, no silently truncated result after `commit()` / `rollback()`, `cursor.description` `null_ok` and collection type codes), and 1.8.0 keeps the CAS session across `commit()` / `rollback()` and in autocommit mode. README, its translations (several still said `>=1.2.0`) and the driver guides state the new range ([#564](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/564)) by @yeongseon.

- **pycubrid compliance lanes re-baselined on pycubrid 1.8.0 (#559)** — the `pycubrid@sa2.0` and `pycubrid@sa2.1` CI steps pin `pycubrid==1.8.0` (was 1.7.1). On CUBRID 10.2 and 11.4 both fail exactly the same tests as on 1.7.1, so `test/known_failures.txt` keeps every entry (pycubrid 1.8.0 still raises the -924 foreign-key restriction as `DatabaseError`; cubrid-lab/pycubrid#390 fixed -631 and -922 only) ([#564](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/564)) by @yeongseon.

- **The pycubrid isolation-level re-apply is kept, and its documentation now describes pycubrid 1.8.0 (#559)** — pycubrid 1.8.0 no longer drops the level at every `commit()` / `rollback()`, but a session reopened after the CAS goes away out of transaction (a CAS restart, a broker reset) starts at the server default. On CUBRID 11.4, the re-apply keeps SERIALIZABLE after a CAS killed right after `commit()`; without it the level falls to READ COMMITTED. If the CAS of an idle pooled connection with a configured level dies, the next statement fails as a disconnect instead of silently running at the default level; `pool_pre_ping=True` replaces such a connection at checkout. The driver, isolation-level and troubleshooting guides no longer claim that pycubrid reconnects after every commit, rollback or autocommitted statement. No code behavior change ([#564](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/564)) by @yeongseon.

- **`cubrid://` warns at first connect when CUBRIDdb is older than 11.3 (#585)** — the dialect reads the driver's compiled-in version (`CUBRIDdb._cubrid.__version__`, `b'9.3.0.0001'` for the PyPI release) and, when its major.minor is below 11.3, emits a `SAWarning` naming the version, the recommended `cubrid+pycubrid://` driver and the source-build path. It warns instead of raising `NotSupportedError` so deployments that followed the old install instructions keep connecting; filter the warning to `"error"` to fail fast. pycubrid engines and drivers whose version cannot be read are not affected. The `ImportError` for a missing CUBRIDdb no longer suggests `pip install CUBRID-Python` ([#588](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/588)) by @yeongseon.

- **`test_show_create_table.py` golden cases run through the real dialect parser (#590)** — instead of a hand-maintained copy that had drifted (it lacked `referred_schema` / `duplicates_index` and the sort-by-name order for multiple foreign keys, #531); the `mixed_pk_fk_unique` fixture is corrected to that order. Test suite only; no dialect behavior changed ([#618](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/618)) by @yeongseon.

- Earlier release workflow unification with the sibling repos: new `RELEASING.md`; `make release` replaced by the read-only `make release-check VERSION=x.y.z`; `publish-pypi.yml` was manual-dispatch only and then dispatched the cookbook smoke test after a successful publish (replacing `notify-cookbook.yml`); CI lints `CHANGELOG.md` ([#563](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/563)) by @yeongseon.

- **PyPI publish fails closed on duplicate files (#566)** — `publish-pypi.yml` no longer passes `skip-existing: true`. `scripts/pypi_duplicate_guard.py` compares each file's SHA-256 with the file PyPI already serves under that name: an identical file (from a partial upload being re-run) is skipped, and a different hash or an unreachable PyPI fails the job. `RELEASING.md` documents the recovery ([#573](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/573)) by @yeongseon.

- **CI: releases happen automatically when a reviewed release PR is merged (#601)** — `prepare-release.yml` opens the `chore: release vX.Y.Z` PR. On every push to `main`, the guarded workflow (introduced as `release.yml`; see the Trusted Publisher entry above) decides from git facts alone whether to release, then runs the full matrix, build, tag, draft GitHub Release, PyPI upload and cookbook verification pinned to the merge SHA; the release fails unless the cookbook check installs the requested version (#605). `create-release.yml` and the manual `publish-pypi.yml` were removed and the former manual publisher is not restored; a narrow recovery dispatch (`resume`, `verify-only`, `dry-run`) remains. Ported from cubrid-lab/pycubrid#540 ([#603](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/603)) by @yeongseon.

### Deprecated

- **Python 3.10 support** — advance notice for the 1.9.x release. Python 3.10 reached upstream end of life on 2026-10-01 ([PEP 619](https://peps.python.org/pep-0619/#310-lifespan)). The current 1.8.x line and 1.9.x retain Python 3.10 support; the following minor release (planned 1.10.0) will require Python >=3.11. Upgrade Python, recreate your virtual environment and validate your application before upgrading. Current package metadata, CI coverage and runtime behavior remain unchanged; see [support matrix](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/SUPPORT_MATRIX.md) and [roadmap](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/ROADMAP.md) ([#665](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/665)) by @yeongseon.

- **The `[cubrid]` and `[cubriddb]` extras (#585)** — both depend on an unbounded `CUBRID-Python`, and PyPI has no release newer than 9.3.0.2 (sdist only, 2015), so they install a driver this dialect has never tested: on CUBRID 11.4 it returns `BIGINT` as `str` (#583) and fails parts of the integration suite. A version floor would make the extras uninstallable, and removing them would change what an existing `pip install "sqlalchemy-cubrid[cubriddb]"` resolves to, so they are kept unchanged for now and marked deprecated. The supported CUBRIDdb is built from cubrid-python v11.3.0.51 or later; `cubrid+pycubrid://` remains the recommended driver. The install guides now document that path, and the `docs/DRIVER_COMPAT.md` build recipe clones with `--recurse-submodules` and checks `CUBRIDdb._cubrid.__version__` ([#588](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/588)) by @yeongseon.

### Fixed

- **Alembic autogenerate no longer pairs a reflected foreign key with a same-named model foreign key on different columns (#624)** — the default-`RESTRICT` correction from #597 matched by name alone, so a reflected `fk_x(a)` was compared with a model `fk_x(b)` and its `RESTRICT` cleared even when the model foreign key on `a` named `RESTRICT` explicitly. A name match now also needs the same columns and target; otherwise the model foreign keys on the same columns are compared ([#668](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/668)) by @yeongseon.

- **Negative character and bit lengths now fail at compile time (#491)** — VARCHAR, NVARCHAR/NCHAR VARYING, CHAR, NCHAR, BIT, BIT VARYING, BINARY and VARBINARY reject explicit negative lengths with `CompileError`, matching the existing zero-length contract; omitted and positive lengths are unchanged ([#662](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/662)) by @yeongseon, co-authored by @soyeladice-svg.

- **The nightly mutation-testing lane measures again (#628)** — since #604, `test/conftest.py` imports `scripts.integration_urls`, which mutmut did not copy into its sandbox, so every run since 2026-09-30 stopped at "failed to collect stats" (reproduced on `main` da752c4; last passing run at 56d4d90, first failing at 5f1e07e). `setup.cfg [mutmut]` now sets `also_copy = scripts`; the lane reports a score again (949 of 1340 mutants killed, 70.8%, on Python 3.12 with SQLAlchemy 2.1.1) and stays non-gating, and `test/test_mutmut_sandbox.py` catches the next missing package ([#639](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/639)) by @paikend.

- **An aiopycubrid read timeout invalidates the connection on Python 3.10 (#624)** — pycubrid's async driver retires the session and raises `OperationalError` from `asyncio.TimeoutError`, which is an `OSError` only from Python 3.11, so on 3.10 the pool kept a connection the driver had already closed. An `asyncio.TimeoutError` in the explicit cause chain now counts as a transport failure on every supported Python ([#672](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/672)) by @yeongseon.

- **A server error whose text happens to contain a disconnect phrase no longer invalidates the connection (#624)** — CUBRID error messages echo application data, so an error such as `RAISE_APPLICATION_ERROR(1001, 'connection refused by policy')` (-889) matched the message fallback of `is_disconnect()` and the pool discarded a healthy connection. The fallback is now skipped for errors that carry a server error code, except -190, -191 and -368, whose own text reports a failed server connection; other classification is unchanged. Recorded on CUBRID 11.4.6 with pycubrid ([#676](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/676)) by @yeongseon.

- **`get_unique_constraints()` no longer trusts an empty catalog result when the server version is unknown (#624)** — the owner check added in #610 applies from CUBRID 11.2, so without `server_version_info` `SHOW CREATE TABLE` now decides, as before #610. A connected engine always knows its server version, so ordinary reflection is unchanged ([#675](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/675)) by @yeongseon.

- **pycubrid's malformed-reply error invalidates the connection (#680)** — pycubrid closes the connection and raises `OperationalError("malformed response from broker")` when a broker reply cannot be parsed; `is_disconnect()` did not recognize it, so the next statement failed with "connection is closed". The message is now a disconnect pattern of the pycubrid dialects ([#681](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/681)) by @yeongseon.

- Isolate CI cancellation by event/ref; include the CI execution policy in generated documentation and use a working policy URL in both LLM indices (PR #659 follow-up) ([#660](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/660)) by @yeongseon.

- **Empty emphasized link captions no longer exempt documentation updates (#648)** — `scripts/check_docs_reason.py` is synchronized with the reviewed pycubrid#573 helper, so emphasis around an empty comment or image no longer counts as an explanation; regression tests keep the pycubrid#429 case families ([#649](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/649)) by @yeongseon.

- **Collection domains and authorized ENUM values reflect without guessing (#631)** — `get_columns()` no longer reflects a native ENUM as `NullType` and now recognizes the server's `SET OF` / `MULTISET OF` / `SEQUENCE OF` forms. CUBRID prints ENUM labels unescaped, so an authorized reader now gets the exact ordered values from `_db_domain.enumeration`; a non-DBA `-494` denial warns and returns `NullType` instead of inventing labels, and other catalog failures propagate. **Full ENUM reflection for non-DBA users remains unsupported.** Collection members come from the public `db_attr_setdomain_elm` view, and `MONETARY` members reflect as `MONETARY`. Members that cannot be resolved safely (incomplete rows, a dropped OBJECT class, an inexpressible type, an `ENUM` member on 11.2+, or a column name `SHOW COLUMNS` lists twice) warn and return `NullType` instead of failing the rest of the table; on 11.2+ another owner's OBJECT member reflects as `owner.class`, and member collations are not reflected. Tested against the #611 recordings; see `docs/TYPES.md` ([#635](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/635)) by @yeongseon.

- **Column reflection accepts whitespace in numeric type parameters (#609)** — `NUMERIC(10, 2)` / `DECIMAL(10 , 2)` reflected as `NullType` with a "Did not recognize type" warning, while `NUMERIC(10,2)` worked; whitespace around the comma is now accepted for columns and collection members. Only digit lists are stripped; other types and the unrecognized-type warning are unchanged. This is parser robustness: CUBRID 10.2, 11.0, 11.2 and 11.4 print the compact form, so no supported-server regression was observed ([#626](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/626), refs [#615](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/615)) by @yeongseon.

- **Alembic autogenerate no longer drops and re-creates an unchanged foreign key declared without `ondelete` / `onupdate` (#597)** — CUBRID's default referential action is `RESTRICT` and `SHOW CREATE TABLE` always prints it, so every `alembic revision --autogenerate` proposed `drop_constraint` + `create_foreign_key` for such a key. `CubridImpl.correct_for_autogen_foreignkeys()` now clears a reflected `RESTRICT` when the matching model foreign key has no action (matched by name first; an unnamed key only when every model key on the same columns and target has no action); reflection still reports `RESTRICT`, and changes to `CASCADE` / `SET NULL` are still detected. `NO ACTION` versus no action stays undetected, as before. Verified with a default `env.py` on CUBRID 11.4 and 10.2 ([#622](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/622)) by @yeongseon.

- **`is_disconnect()` no longer reads an error code out of message text (#608)** — a message that merely started with a number was classified by that number, so `pycubrid.DataError("-20004 rows rejected by application validation", errno=-495)` invalidated a working pooled connection. Codes are now read only from an integer `args[0]` (not `bool`) and an integer pycubrid `errno`. The code tables, the `OSError` cause check and the message-pattern fallback are unchanged, so a CAS killed mid-transaction and a stopped `cub_server` are still detected on `cubrid://`, `cubrid+pycubrid://` and `cubrid+aiopycubrid://` ([#620](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/620)) by @yeongseon.

- **Unreachable configured CUBRID servers fail integration tests instead of silently skipping (#593)** — an unreachable `CUBRID_TEST_URL` used to skip 421 of 447 integration tests, even with `CI=true`. One session-level `SELECT 1` probe with the configured URL's driver now reports errors instead. With `CI=true`, selecting integration tests without `CUBRID_TEST_URL` fails before execution; without a configured URL, local runs may still skip. An optional `CUBRID_TEST_AURL` is probed through `cubrid+aiopycubrid://`; `--dburi` compliance runs and `CUBRID_REQUIRE_*` switches (#486) are unchanged ([#604](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/604)) by @yeongseon.

- **`replace()` emits `REPLACE` as the statement verb instead of rewriting the first `INSERT INTO` in the compiled SQL (#591)** — the old substitution could hit an `INSERT INTO` inside a `prefix_with()` prefix, a comment, a string literal or a quoted identifier: the statement then stayed a plain `INSERT` (a duplicate key raised `IntegrityError` instead of replacing the row) and the stored value became `'REPLACE INTO'`. Now `replace(t).prefix_with("/* c */")` renders `REPLACE /* c */ INTO t ...`, leaving values, identifiers, comments and bind parameters untouched, including multi-row `values()`, `executemany` and `from_select()`. An unexpected compiled form raises `CompileError` instead of `NotImplementedError`. Verified on CUBRID 11.4 with SQLAlchemy 2.0 and 2.1 ([#600](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/600)) by @yeongseon.

- **`cubrid+pycubrid://` and `cubrid+aiopycubrid://` forward URL query options to pycubrid (#592)** — `?connect_timeout=5` or `?charset=euckr` used to connect without error and have no effect. Both dialects now forward `charset`, `connect_timeout`, `read_timeout`, `fetch_size`, `ssl`, `decode_collections`, `no_backslash_escapes` and `enable_timing`, converted to the types pycubrid expects. An invalid or repeated value, a field that belongs in the URL itself (`host`, `port`, `database`, `user`, `password`), `autocommit` and `json_deserializer` raise `ArgumentError` from `create_engine()`; other keys are ignored with pycubrid's `UnknownConnectionOptionWarning` (cubrid-lab/pycubrid#377). **`charset` needs a pycubrid release newer than 1.8.0** (cubrid-lab/pycubrid#510); with 1.8.0 it raises `ArgumentError` naming the installed version. `cubrid://` is unchanged (CUBRIDdb's `connect()` takes no keyword options); `docs/CONNECTION.md` documents the options ([#599](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/599)) by @yeongseon.

- **`get_foreign_keys()` and `get_unique_constraints()` no longer report a failed `SHOW CREATE TABLE` as "no constraints" (#589)** — both caught every exception from `SHOW CREATE TABLE` (for `get_unique_constraints()`, in its fallback), logged a warning and returned `[]`, so a disconnect or authorization error looked like a table without foreign keys and Alembic autogenerate emitted `add_fk` for existing keys. **Behavior change:** `Unknown class` still raises `NoSuchTableError` (#530), a missing `SHOW CREATE TABLE` row for a table the catalog listed now also raises it, and every other exception propagates unchanged (a disconnect keeps `connection_invalidated`); the `SHOW CREATE TABLE failed ...` warning is gone, and `[]` now means the query succeeded and found no constraint. No leniency is kept for non-DBA users: on CUBRID 10.2 and 11.4 they only see tables they can `SELECT`, for which `SHOW CREATE TABLE` does not fail with an authorization error. Views still return `[]` ([#598](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/598)) by @yeongseon.

- **The advisory Alembic safety checker now counts DDL calls, not attribute references (#447)** — `scripts/alembic_safety_check.py` warned about `operations = [op.create_table, op.drop_table]` although nothing was called, and missed the `create_unique_constraint`, `create_foreign_key`, `create_check_constraint` and `create_primary_key` operations. It now counts only `op.x(...)` / `batch_op.x(...)` calls, includes those operations and stays advisory ([#587](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/587)) by @yeongseon.

- **`has_table()` / `has_index()` no longer report missing objects as existing under `cubrid://` with the PyPI `CUBRID-Python` driver (#583)** — the catalog `COUNT(*)` is a `BIGINT`, which the `CUBRID-Python` 9.3.x releases on PyPI fetch as `str`, so `bool('0')` made every missing table or index look present: `create_all(checkfirst=True)` silently skipped the `CREATE` and `drop_all(checkfirst=True)` failed with `-494 Unknown class`. The count is now converted with `int(...)`. CUBRIDdb built from `cubrid-python` v11.3.0.51 (the CI driver) and pycubrid return `int` and were not affected ([#584](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/584)) by @yeongseon.

- **Follow-ups from the #577 disconnect-code audit (#578)** — -10002 (`CAS_ER_NO_MORE_MEMORY`), sent when the CAS closes the connection after a failed read-buffer allocation, is now a disconnect instead of being caught one call later through -20004. pycubrid, which does not negotiate CUBRID's renewed error-code protocol, receives it as the legacy-renumbered -1002, which is now matched too (its `errno` was previously checked only against the four server-session codes from #565). `docs/TROUBLESHOOTING.md` shows each driver's real -4 interrupted-query message. The `KILL QUERY` test helper still finds its victim by timing (CUBRID exposes no statement text to match) and documents that limit. Verified live on CUBRID 11.4 with both drivers ([#582](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/582)) by @yeongseon.

- **Integration runs now wait for a ready CUBRID server instead of sleeping (#575)** — a fixed 10-second delay after Docker startup caused false CCI -20004 failures, incorrect Enum capability results, flaky reflection fuzz tests and skipped live tests on cold containers; these were **startup timing issues, not dialect or driver limitations**. `scripts/wait_for_cubrid.py` retries `SELECT 1` until ready or `INTEGRATION_READY_TIMEOUT` (default 180 seconds). `make integration` defaults to `cubrid+pycubrid://`; `INTEGRATION_DRIVER=cubriddb` selects CUBRIDdb, and an invalid driver exits 2 **before any Docker command**. Ownership, signals and cleanup are unchanged (#567 and #568). A required PR CI job runs the pycubrid suite on CUBRID 11.4; nightly/tag jobs run both drivers on 10.2 and 11.4 ([#581](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/581)) by @yeongseon.

- **The pool invalidates connections broken by a `cub_server` stop, restart or crash (#565)** — afterwards, a connection inside a transaction fails with -111 and then -224 on every statement until the transaction ends, even after the server is back, and `pool_pre_ping` cannot catch it because the CAS still answers. The four codes for which the broker resets the CAS are now disconnects on both drivers: -111 (`ER_TM_SERVER_DOWN_UNILATERALLY_ABORTED`), -199 (`ER_NET_SERVER_CRASHED`), -224 (`ER_OBJ_NO_CONNECT`) and -677 (`ER_BO_CONNECT_FAILED`), as is pycubrid's `CAS did not answer CHECK_CAS out of transaction and reconnecting failed`. Message patterns now match the driver's own message instead of pycubrid's `str()`, so pycubrid errors -4 (an interrupted query) and -671 are no longer misread as disconnects (CUBRIDdb's -4 is tracked in #572; -671 stays out, as evaluated in #564). A new server-restart test checks with both drivers, with and without `pool_pre_ping`, that the pool recovers ([#571](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/571)) by @yeongseon.

- **An interrupted query no longer invalidates a CUBRIDdb connection, and a dead CAS now does (#572)** — an audit against CUBRID's `error_code.h`, `cas_error.h` and CCI's `cas_cci.h` removed five codes that are not disconnects for either driver: -4 (`ER_INTERRUPTED` from `KILL QUERY`, which replaced working CUBRIDdb connections), -10005 and -10007 (`CAS_ER_TRAN_TYPE`, `CAS_ER_NUM_BIND`) and the JDBC-only -21003 and -21005. The table now holds the codes CUBRIDdb raises for a dead or unusable connection: -20004 (`CCI_ER_COMMUNICATION`), -10003 (`CAS_ER_COMMUNICATION`), -20002 (`CCI_ER_CON_HANDLE`) and -20016 (`CCI_ER_CONNECT`); without -20004, a CAS that died in a transaction left its broken connection in the pool. The four server-session codes from #565 are unchanged and still the only ones matched against pycubrid's `errno`. A new integration test checks that `KILL QUERY` yields -4 and keeps the connection ([#577](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/577)) by @yeongseon.

- **`CHAR(0)` / `NCHAR(0)` no longer silently compile to bare `CHAR` / `NCHAR` (#476)** — the type compiler still checked fixed-width lengths by truthiness after #456, so an explicit `length=0` was treated as unspecified. `length=None` still emits bare `CHAR` / `NCHAR`; an explicit zero now raises `CompileError` ([#477](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/477)) by @HarshRajSinghania.

- **`BIT(length=0)` is no longer silently coerced to `BIT(1)` (#441)** — `BIT.__init__` used `length or 1`, so an explicit zero became 1 before the compiler ran. Unspecified length still defaults to `BIT(1)`; `BIT VARYING` with no length is still unlimited. An explicit zero now raises `CompileError` ([#478](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/478)) by @HarshRajSinghania.

- **Reflection no longer reports a syntax error as a missing table (#454)** — `get_columns()` and `get_indexes()` raised `NoSuchTableError` for any `SHOW COLUMNS` / `SHOW INDEXES` failure with code -493, SQLSTATE `42S02` or a `Table not found` message, but CUBRID uses -493 for every parser error (and pycubrid before 1.8.0 reports `42S02` for all of them), so a syntax error, such as CUBRID 11.4's for a table name containing `]`, was hidden. Both methods now translate only the server's `Unknown class "<owner>.<name>"` error, like the other reflection methods since #530, and let other errors propagate; missing tables still raise `NoSuchTableError` ([#455](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/455)) by @UsmanGhias (first contribution 🎉), co-authored by @yeongseon.

- **Interrupted `make integration` runs clean up their own Docker stack (#568)** — the recipe traps `SIGINT`, `SIGTERM` and `SIGHUP` (including Ctrl-C and `timeout`), not only EXIT. An in-progress `docker compose up -d` gets up to `INTEGRATION_STOP_GRACE` (default 10 seconds) to finish, so it does not leave containers and volumes behind; other steps are terminated, then killed after the same grace period if still running. Cleanup removes only this run's resources (#567), and the recipe exits with 128 plus the signal number; `SIGKILL`, host shutdown and `SIGQUIT` are outside the guarantee ([#574](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/574)) by @yeongseon.

- **`make integration` no longer removes a Compose project or volume it did not create (#567)** — since #446 the recipe ran `docker compose down -v` on the default Compose project on every exit, so a failed startup could delete the `cubrid-data` volume of an existing stack (for example from `make docker-up`). Each run now uses its own project (`sqlalchemy-cubrid-it-<timestamp>-<pid>`, overridable with a validated `INTEGRATION_PROJECT`) and refuses to start, creating and removing nothing, if that project already has resources or the ownership check fails. Concurrent runs with the same fixed `INTEGRATION_PROJECT` are not supported. `docker-compose.yml` and `make integration` accept `CUBRID_PORT` for the host port (default 33000) ([#574](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/574)) by @yeongseon.

- **Docker integration cleanup runs after failures (#446)** — `make integration` registers cleanup before starting Docker, so failed startup, readiness waiting and tests all attempt `docker compose down -v`. An original failure is preserved if cleanup also fails, and a cleanup-only failure returns a failing status ([#508](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/508)) by @soyeladice-svg.

### Documentation

- Prepare an ORM/Alembic video recording script and defer the Quick Start embed until a verified MP4 is present ([#374](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/374)) by @yeongseon.

- **Refreshed current support claims and removed stale test statistics (#461)** — hardcoded, already inconsistent test counts and coverage figures in README, AGENTS.md, ROADMAP.md, SECURITY.md and several `docs/` pages are replaced with the durable CI coverage gate (`--cov-fail-under=95`). Stale versions in AGENTS.md, ROADMAP.md and SECURITY.md are corrected, and SECURITY.md states the actual policy: a single rolling release line, with security fixes only for the latest release. The PR integration matrix is documented as the 2 combinations `ci.yml` runs (3.14×11.4, 3.10×10.2); the type tables list `TIMESTAMPTZ`/`TIMESTAMPLTZ`/`DATETIMETZ`/`DATETIMELTZ` as the distinct `timezone=True` types reflected since #181/#442; the non-functional `codecov` badge is removed ([#643](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/643)) by @yeongseon.

- **Quick Start uses the recommended pycubrid driver (#495)** — English and Korean Quick Start docs now use `sqlalchemy-cubrid[pycubrid]` / `cubrid+pycubrid://` as the primary path and point C-extension users to the supported CUBRID-Python 11.3.0.51+ source-build path ([#516](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/516)) by @soyeladice-svg.

- Contributor setup docs no longer list redundant `pip install` steps for tools included in the `[dev]` extra (#497) ([#663](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/663)) by @yeongseon.

- **`llms.txt` capabilities corrected and the two entry points single-sourced (#460)** — the root `llms.txt` wrongly said CUBRID has no JSON support, advertised six isolation levels, described only two driver backends and linked to retired cookbook paths. `docs/llms.txt` is now the only maintained index, checked against the code; `scripts/generate_llms_full.py` copies it to the root `llms.txt`, and the CI `lint` job fails when `docs/llms-full.txt` or `llms.txt` is stale ([#579](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/579)) by @yeongseon.

- **Alembic import log lines (#561)** — `docs/ALEMBIC.md` (+ Korean) explains that loading the dialect imports Alembic when it is installed (about 0.1 s), so Alembic 1.18+ logs seven `INFO` `setup plugin ...` lines under `INFO` root logging, and gives the application-side fix `logging.getLogger("alembic").setLevel(logging.WARNING)`. No supported Alembic hook defers the registration; no behavior change ([#562](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/562)) by @yeongseon.

- **SQLAlchemy 2.1 is documented as released and tested, not a pre-release (#492)** — `docs/SUPPORT_MATRIX.md` now says CI tests SQLAlchemy 2.1.1 instead of calling 2.1.x the "latest tested pre-release until GA", and `docs/SA_COMPAT.md` describes the non-blocking canary as a `--pre` install of `SQLAlchemy>=2.1.0b1,<2.3` with `continue-on-error` ([#506](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/506)) by @PandaHUN777 (first contribution 🎉).

- **Samples use the recommended pycubrid driver (#498)** — `samples/create_engine.py` and `samples/cubrid_datatypes.py` used `cubrid://`, which a plain install does not provide; they now use `cubrid+pycubrid://` and name `pip install "sqlalchemy-cubrid[pycubrid]"` in their docstrings ([#509](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/509)) by @soyeladice-svg (first contribution 🎉).

* **contributing:** keep issue specifications current and assign owners ([#650](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/650)) ([7414fdb](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7414fdbf6c513758b2f5590e55bcf7f3e361d68f)) by @yeongseon

* derive Sphinx release from package version ([#499](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/499)) ([3f5c4f5](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/3f5c4f5135bd3cc7f209905edc794419aa442e09)) by @HarshRajSinghania (first contribution 🎉)

* mention repository and full offline test lanes ([#647](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/647)) ([e4b90f0](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/e4b90f050324154a23306a8b8b88ec05f2a28423)) by @soyeladice-svg

* pin cookbook smoke-test fallback to the exact release ([#576](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/576)) ([ad47e3b](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ad47e3bac6484d5dda4c8faa5b5736c58a363f21)) by @yeongseon

* **reflection:** state when another owner's class reaches the DDL fallback ([#673](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/673)) ([7c676fa](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/7c676fafe3bafcc7e85772328d22362cfae023ea)) by @yeongseon

* **release:** document release-please review and recovery ([#657](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/657)) ([a01c338](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/a01c3385ed4d8f4327c6dae55c13b386cc07cdef)) by @yeongseon

* **types:** record the tested non-DBA ENUM reflection limitation ([#677](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues/677)) ([112fde7](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/112fde7d934b15a099ba9a044acc6429dd170e5d)) by @yeongseon

## [1.8.0] - 2026-09-29

Alembic upgrades are now atomic by default, several types and index operations emit DDL that CUBRID accepts or fail early with `CompileError`, and reflection is complete for non-DBA users. Read the upgrade notes first: some fixes change the emitted SQL, raise errors where invalid SQL was emitted before, or change reflected metadata.

### Upgrade notes

Behavior changes you may notice (details in the entries below):

- **Alembic upgrades are atomic by default (#503).** CUBRID DDL is transactional, so a failed multi-revision `alembic upgrade` now rolls back the whole run, including the `alembic_version` update. Set `transaction_per_migration=True` in `context.configure()` to keep per-revision commits (recommended for long or large-table migrations). Offline `--sql` scripts no longer contain `BEGIN;`; run them with `csql --no-auto-commit --no-single-line` so a failing statement stops the script.

- **Alembic registration (#504).** `CubridImpl` is registered when the dialect loads, so a default `env.py` works without importing `sqlalchemy_cubrid.alembic_impl`. The `[alembic]` and `[dev]` extras now require `alembic>=1.7.2`; `cubrid+aiopycubrid://` online migrations need Alembic's async template (`alembic init -t async`).

- **Reflection.** Unique constraints are no longer reported twice and reflect as unique indexes, as on MySQL, and `get_indexes()` returns `[]` for views (#529); non-DBA users get complete metadata from the public catalog views (#549); a missing table or view raises `NoSuchTableError`, and `get_view_definition()` on a table raises it instead of returning `""` (#530); `has_table()` / `has_index()` match mixed-case names (#543) and are cached per `Inspector` until `clear_cache()` (#463, #533); `get_foreign_keys()` is sorted by name (#531); `BIT(n)` / `BIT VARYING(n)` keep their length (#545); a failing catalog query raises instead of silently returning incomplete metadata (#533, #549). Autogenerate also detects `Text` ↔ `String(n)` changes (#544). Review the first Alembic autogenerate diff after upgrading.

- **DDL and types.** `UnicodeText` and `TEXT` compile to `STRING` (#534); `BINARY(n)` / `VARBINARY(n)` compile to `BIT(n*8)` / `BIT VARYING(n*8)` and `UUID` to `CHAR(32)` (#545); `Index.drop()` and `op.drop_index()` emit `DROP INDEX <name> ON <table>`, so `op.drop_index()` needs `table_name` (#533); `if_exists=True` on index drops and `if_not_exists=True` on index creates raise `CompileError` (#533, #540), as does an explicit `String(0)` (#440); Boolean `is_()` / `is_not()` against a value render with `<=>` (#465); JSON `as_numeric(p, s)` returns `Decimal` (#535).

- **Transactions.** `isolation_level="AUTOCOMMIT"` works on every driver, invalid levels raise `ArgumentError`, and `dialect.on_connect()` no longer applies `isolation_level` (a hand-built pool must apply it) (#501). On pycubrid, engine-level AUTOCOMMIT reconnects per statement at the server-default level; `skip_autocommit_rollback=True` is recommended (#501). Engine- and connection-level isolation levels survive `commit()` / `rollback()` on pycubrid, at the cost of one extra `SET TRANSACTION ISOLATION LEVEL` + `COMMIT` per commit or rollback (#505). On `cubrid://`, `executemany` runs each parameter set separately: `None` values and rowcounts are correct, large batches are slower (#502).

- **Async.** `driver_connection` on `cubrid+aiopycubrid://` is now the `pycubrid.aio` connection; use `dbapi_connection` for the SQLAlchemy adapter (#520). Async `LargeBinary` / `BLOB` binding works (#500). The `[pycubrid]` extra now installs `SQLAlchemy[asyncio]` (`greenlet`), which may need build tools when no compatible wheel is available (#448).

- **Removed** the unreachable SQLAlchemy 1.x hooks `should_autocommit_text()`, `AUTOCOMMIT_REGEXP` and the `dbapi()` classmethods (#462).

- **pycubrid 1.8.0 is recommended.** It raises `IntegrityError` for NOT NULL and foreign-key violations, raises instead of silently returning a truncated result after `commit()` / `rollback()`, reports correct `null_ok` and collection type codes in `cursor.description`, and keeps the CAS session across commits and rollbacks except when the CAS itself is restarted (`docs/DRIVER_COMPAT.md` Known Issue 10); the pycubrid contract tests require it (#480, #481, #482). The declared range stays `pycubrid>=1.3.2,<2.0` (raising it is tracked in #559), so the dialect's isolation-level re-apply workaround is kept for older pycubrid and is a harmless no-op on 1.8.0.

### Added

- **Upstream canary failures are reported as an issue (#521)** — a failing run of the non-blocking `pycubrid@main` canary on the default branch, which used to pass silently, now opens or updates one "Upstream canary failing against pycubrid@main" issue (label `ci`) with each job's outcome, the run URL and the exact commits tested, and closes it once both jobs pass. Only the report job has `issues: write` (via the `gh` CLI and `GITHUB_TOKEN`), and a failure to report turns the run red. `docs/DEVELOPMENT.md` (+ Korean) describes it ([#524](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/524)) by @yeongseon.

- **Blocking SQLAlchemy compliance lanes for released pycubrid (#463)** — the official SQLAlchemy compliance suite now gates merges for `cubrid+pycubrid://` as well as CUBRIDdb, in lane `pycubrid@sa2.1` (pycubrid 1.7.1, SQLAlchemy 2.1.1, Python 3.14, CUBRID 11.4) and lane `pycubrid@sa2.0` (pycubrid 1.7.1, SQLAlchemy 2.0.53, Python 3.10, CUBRID 10.2); the CUBRIDdb lane (`cubrid@sa2.0`, CUBRID 11.4) is unchanged. `test/known_failures.txt` is now keyed per lane, so a failure baselined for one driver cannot hide a regression on the other, and `CUBRID_STRICT_KNOWN_FAILURES=1` fails the run on a strict XPASS, a stale entry or an unreviewed baseline. `docs/DEVELOPMENT.md` and `docs/SUPPORT_MATRIX.md` (+ Korean) describe the lanes and how to update the baseline ([#526](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/526)) by @yeongseon.

- **Required driver-differential lane (#486)** — the regular and full integration jobs run `test/test_driver_differential.py` with pycubrid and CUBRIDdb and fail when no comparison actually ran (`CUBRID_REQUIRE_DRIVER_DIFFERENTIAL=1`); local runs without the variable still skip. `scripts/report_driver_versions.py` records the exact Python, SQLAlchemy, driver and server versions. New cases cover `executemany` (in textual `executemany` CUBRIDdb 11.3.0.51 reuses the previous row's value for a NULL parameter), scalar binds, column names and commit/rollback visibility; areas blocked upstream are tracked in #480–#484. `docs/DEVELOPMENT.md` now requires a pycubrid release candidate to pass the downstream contract suite before the `pycubrid>=1.3.2,<2.0` bound is widened. Tests and CI only ([#487](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/487)) by @yeongseon.

- **Live BLOB/CLOB value tests on released drivers (#485)** — Core and ORM round trips on all three URL forms for `LargeBinary`, `BLOB`, `CLOB` and `Text`, up to 256 KiB. Verified on CUBRID 10.2 and 11.4: writes store the full value and `NULL`/`Text` round-trip, but non-NULL `BLOB`/`CLOB` reads return a driver LOB locator (pycubrid `dict` handle, CUBRIDdb `'file:...'` string) instead of `bytes`/`str`, and async `LargeBinary`/`BLOB` binding failed; these are strict per-driver xfails. The types, driver and support docs record the behavior (reflection is unaffected), and the `CLOB` type row no longer lists `sqlalchemy.Text`, which compiles to `STRING`. No dialect behavior change ([#490](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/490)) by @yeongseon.

- **Live tests that results are never silently truncated across commit or rollback (#481)** — sync and async tests fetch a 500-row result, larger than pycubrid's FETCH batch, across `commit()` and `rollback()` and require every row or a DB-API error, never a partial `Result`. Verified on CUBRID 10.2 and 11.4: CUBRIDdb 11.3.0.51 returns all rows after commit and raises `InterfaceError` after rollback, pycubrid `main` raises `InterfaceError`, and released pycubrid 1.7.1 silently returns only the buffered rows on a warm connection (cubrid-lab/pycubrid#395). Those sync cases are strict pycubrid-only xfails (via `test/pycubrid_upstream.py`); async results pass because `AsyncConnection.execute()` buffers the whole result. `docs/DRIVER_COMPAT.md` documents the per-driver behavior. Tests, CI and docs only ([#514](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/514)) by @yeongseon.

- **Live `IntegrityError` contract tests for constraint violations (#480)** — Core, ORM, async and driver-differential tests check that NOT NULL, foreign-key and unique/primary-key violations raise `sqlalchemy.exc.IntegrityError` and that the same connection or `Session` works after `rollback()`. Verified on CUBRID 10.2 and 11.4: CUBRIDdb 11.3.0.51 and pycubrid `main` pass every case; released pycubrid 1.7.1 raises NOT NULL (-631) and foreign-key (-922) violations as `DatabaseError` (cubrid-lab/pycubrid#390), so those cases are strict xfails for the pycubrid drivers only. The new `test/pycubrid_upstream.py` helper applies such xfails unless `CUBRID_PYCUBRID_UPSTREAM=1`, which the weekly `pycubrid@main` canary sets; `docs/DRIVER_COMPAT.md` lists the per-driver exception classes. Tests, CI and docs only ([#512](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/512)) by @yeongseon.

- **Stronger `IntegrityError` contract tests (#480)** — the constraint-violation tests now prove that the error does not invalidate the connection (the same DBAPI connection is kept after `rollback()`, also for a bound `Session`), assert the native server code (-631 NOT NULL, -922 foreign key, -670 unique) and that `exc.orig` is the driver's `IntegrityError`; a patched `is_disconnect()` that always returns `True` now fails them. The `is_disconnect()` docstring no longer claims CUBRIDdb lacks `OperationalError`. Tests and docs only ([#517](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/517)) by @yeongseon.

- **Stronger result-completeness tests (#481)** — the sync test asserts that CUBRIDdb raises `sqlalchemy.exc.InterfaceError` after rollback and checks every fetched row before the pycubrid#395 xfail applies. A new async case drives the lazily fetching `pycubrid.aio` cursor directly; released pycubrid 1.7.1 silently returns 16 of 500 rows there (strict xfail). `docs/DRIVER_COMPAT.md` Known Issue 8 (en/ko) records the raw async cursor behavior. Tests and docs only ([#518](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/518)) by @yeongseon.

- **Live `cursor.description` contract tests (#482)** — sync and async tests check the names, type codes (including `SET`/`MULTISET`/`SEQUENCE`) and `null_ok` that SQLAlchemy exposes. Verified on CUBRID 10.2 and 11.4: CUBRIDdb 11.3.0.51 and pycubrid `main` pass (CUBRIDdb reports collections with CCI composite codes such as 40 for `SET(INTEGER)`); released pycubrid 1.7.1 reports `null_ok` inverted (cubrid-lab/pycubrid#431) and collection columns as their element type (cubrid-lab/pycubrid#430), which are strict pycubrid-only xfails. `docs/FEATURE_SUPPORT.md` documents that the dialect passes `cursor.description` through without normalization. Tests, CI and docs only ([#515](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/515)) by @yeongseon.

- **Review follow-ups for the #480/#481 contract tests** — the result-completeness checks validate every returned row, including the one consumed by `fetchone()`, and the driver-differential constraint case asserts that `exc.orig` is the driver's own `IntegrityError` (for pycubrid, behind the existing pycubrid#390 marker). Tests only ([#519](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/519)) by @yeongseon.

### Changed

- **Contract tests now require pycubrid 1.8.0 (#480, #481, #482)** — the strict xfails for the pycubrid bugs fixed in 1.8.0 are removed: cubrid-lab/pycubrid#390 (`IntegrityError` for NOT NULL / foreign-key violations), #395 (truncated result after commit/rollback), #430 (collection type codes) and #431 (inverted `null_ok`). The pycubrid lanes therefore require pycubrid 1.8.0 or later. `test/pycubrid_upstream.py` is removed, and `docs/DRIVER_COMPAT.md` Known Issues 8 and 9 mark these bugs fixed in 1.8.0. The `pycubrid>=1.3.2,<2.0` dependency bound is unchanged ([#557](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/557)) by @yeongseon.

- **Alembic upgrades are atomic by default because CUBRID DDL is transactional (#503)** — `CubridImpl.transactional_ddl` and `context.is_transactional_ddl()` are now `True`. Contrary to the previous docs, CUBRID does not implicitly commit DDL: with client autocommit off, which the dialect always sets, `ROLLBACK` undoes `CREATE TABLE`, `ALTER TABLE`, `DROP TABLE`, `TRUNCATE`, `CREATE INDEX` (including `WITH ONLINE [PARALLEL n]`), `CREATE VIEW`, `CREATE SERIAL` and `RENAME TABLE`, and DDL never commits pending DML. **Behavior change:** a failed `alembic upgrade` now rolls back every revision of that run, including the `alembic_version` update, instead of keeping the revisions that finished before the failure (each revision was already atomic on its own). Set `transaction_per_migration=True` in `context.configure()` to keep per-revision commits; it is recommended for long or large-table migrations, because uncommitted DDL holds schema locks (other sessions wait on `SCH_S_LOCK`). Offline `--sql` scripts no longer contain `BEGIN;` (CUBRID has no `BEGIN` statement) and end each transaction with `COMMIT;`; run them with `csql --no-auto-commit --no-single-line`, because csql's default single-line mode continues past a failing statement, still runs the trailing `COMMIT;` and exits 0. Required live tests (`test/test_transactional_ddl.py`) prove this on CUBRID 10.2 and 11.4 with both drivers, and the docs and `scripts/alembic_safety_check.py` no longer recommend one DDL operation per revision ([#525](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/525)) by @yeongseon.

### Removed

- **Removed the dead SQLAlchemy 1.x `should_autocommit_text()` hook, its `AUTOCOMMIT_REGEXP`, and the legacy `dbapi()` classmethods (#462)** — SQLAlchemy 2.0 and 2.1 never call `should_autocommit_text()`, and `create_engine()` uses the `import_dbapi()` that every CUBRID dialect class defines, so none of these affected a supported runtime. This also retires #439's request to add `REPLACE` to the regex, surfaced by @biggdawg320 in #468. Transactions are unchanged: DML and DDL text commits only via `conn.commit()`, `engine.begin()` or a `Session`. The docs no longer describe statement-text autocommit detection ([#488](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/488)) by @yeongseon.

### Fixed

- **Alembic autogenerate detects `Text` ↔ `String(n)` changes (#544)** — changing a model column from `Text` to `String(10)` produced no diff, so the migration that shrinks the column was never generated: `CubridImpl` matched the dialect's `STRING` type by a class name it shares with the generic `sa.String`. `String(n)` now goes through Alembic's normal length comparison, while `Text`, `UnicodeText`, `CLOB` and a `String()` without a length still match a reflected `STRING` column. Live autogenerate tests on both drivers cover both directions and the unbounded types that must not report a diff ([#553](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/553)) by @yeongseon.

- **`BINARY`, `VARBINARY` and `UUID` create columns CUBRID accepts (#545)** — these types used SQLAlchemy's generic DDL, which CUBRID 10.2 and 11.4 reject. `BINARY(n)` now compiles to `BIT(n*8)` (`BINARY()` to `BIT(8)`), `VARBINARY(n)` to `BIT VARYING(n*8)` (`VARBINARY()` to `BIT VARYING`), and `UUID` to `CHAR(32)` like `Uuid`, with SQLAlchemy's non-native UUID handling for `as_uuid=True` and `False`. Both drivers bind and return the binary values as `bytes`, and a zero length raises `CompileError`. Reflection keeps the length and `VARYING` of `BIT(n)` / `BIT VARYING(n)` columns (they reflected as `BIT(1)`), so Alembic autogenerate reports no false type change. A new compiler test fails if any generic SQLAlchemy type compiles to a type name CUBRID rejects or that is not yet checked live. `docs/TYPES.md` (+ Korean) documents the mappings and corrects the `CHAR VARYING` reflection rows (`VARCHAR`, not `NVARCHAR`) ([#552](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/552)) by @yeongseon.

- **Boolean `IS` / `IS NOT` predicates compile to SQL CUBRID accepts (#465)** — `col.is_(True)`, `is_not(False)` and similar (also with `true()`/`false()`, a bound parameter, or an expression such as `(col == 5).is_(True)`) rendered `IS 1` / `IS NOT 0`, a syntax error on CUBRID 10.2 and 11.4. `IS` against a value now uses the null-safe equal operator: `a IS b` renders `a <=> b` and `a IS NOT b` renders `(a <=> b) = 0`, with the same SQL semantics in `WHERE` clauses and SELECT lists. `IS [NOT] NULL`, `col == True`, `not_(col)`, `true()`/`false()` and `and_()`/`or_()` are unchanged; CUBRID itself rejects `AND`, `OR` and `NOT` in a SELECT list, which is documented. A live truth-table test on CUBRID 10.2 and 11.4 with both drivers covers it; `docs/TYPES.md` and `docs/FEATURE_SUPPORT.md` (+ Korean) document the rendering ([#555](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/555)) by @yeongseon.

- **Reflection works for non-DBA users (#549)** — for any user but DBA, queries on the DBA-only `_db_index`, `_db_index_key`, `_db_attribute` and `_db_class` tables fail with -494 on CUBRID 10.2, 11.0, 11.2 and 11.4, and the dialect swallowed that error, so reflection silently degraded: `get_indexes()` reported the primary-key and foreign-key auto-indexes as ordinary indexes (spurious Alembic `drop_index`/`create_index` diffs, the #120 problem), `get_pk_constraint()` lost the PK name and every column of a composite key after the first (#426), `get_columns()` returned no column comments, and `has_index()` raised. Reflection now reads the public `db_index`, `db_index_key` and `db_attribute` views, limited on CUBRID 11.2+ to the owner preferred by the #529 lookup (so another owner's same-named class no longer adds indexes or comments), and matches table names as given or lower-cased (`get_indexes("Users")` had the same problems even for DBA); `has_index()` keeps the #543 matching. **A failing catalog query now raises** instead of silently returning incomplete metadata; the `SHOW COLUMNS` / `SHOW CREATE TABLE` fallbacks still apply when the catalog has no matching row, and an `Unknown class` error from `get_unique_constraints()` maps to `NoSuchTableError`. Live tests reflect as DBA and as a new user on CUBRID 10.2 and 11.4 with both drivers ([#554](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/554)) by @yeongseon.

- **`has_table()` and `has_index()` find mixed-case names, so `checkfirst=True` no longer silently skips (#543)** — CUBRID stores identifiers in lower case, even quoted ones, but both methods compared names exactly, so `Index.drop(checkfirst=True)` for `Index("IX_Mixed543", Table("Users543", ...))` did nothing and the index stayed. Both now also match the lower-case form, and `has_index()` prefers the current user's own class (relevant on CUBRID 11.2+, where owners can share a class name). `@reflection.cache` and error propagation (#444, #538) are unchanged. Live tests cover mixed-case `checkfirst` create and drop on CUBRID 10.2 and 11.4 with both drivers ([#550](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/550)) by @yeongseon.

- **`CreateIndex(..., if_not_exists=True)` raises `CompileError` instead of emitting `CREATE INDEX IF NOT EXISTS` (#540)** — CUBRID 10.2, 11.0, 11.2 and 11.4 reject `CREATE [UNIQUE] INDEX IF NOT EXISTS` with a syntax error. `CreateIndex(..., if_not_exists=True)` and Alembic `op.create_index(..., if_not_exists=True)` now raise a `CompileError` pointing to `inspect(conn).has_index()` and `Index.create(checkfirst=True)`, mirroring `DROP INDEX IF EXISTS` (#533). A plain `CREATE INDEX` is unchanged. `docs/ALEMBIC.md` and `docs/FEATURE_SUPPORT.md` (+ Korean) document the limitation ([#551](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/551)) by @yeongseon.

- **Reflecting a missing table or view raises `NoSuchTableError` (#530)** — `get_foreign_keys()` and `get_unique_constraints()` returned `[]` (logging a WARNING traceback), `get_table_comment()` returned `{"text": None}`, and `get_pk_constraint()` and `get_view_definition()` let a raw -493 `ProgrammingError` escape, so the `get_multi_*()` variants also reported the missing object. All now raise `NoSuchTableError`. For a view, `get_foreign_keys()` / `get_unique_constraints()` return `[]` without the WARNING traceback previously logged for every reflected view, and `get_view_definition()` on a table raises `NoSuchTableError` instead of returning `""`. Only CUBRID's `Unknown class` message maps to `NoSuchTableError`: pycubrid reports syntax errors, `<name> is not a class` and some permission errors with the same -493 / SQLSTATE 42S02 (#454), so other -493 errors still propagate (or, in the `SHOW CREATE TABLE` fallbacks, keep the logged empty result). Nine compliance entries (one also needed #529) are removed for all three lanes, and `docs/FEATURE_SUPPORT.md` (+ Korean) documents the behavior ([#546](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/546)) by @yeongseon.

- **`UnicodeText` creates a CUBRID `STRING` column instead of the non-existent `TEXT` (#534)** — `CREATE TABLE` with `UnicodeText` or `sqlalchemy.TEXT` failed with "dba.TEXT is not defined" (-494) on every CUBRID version. Both now compile to `STRING`, like `Text`; CUBRID strings use the database charset, so there is no separate national text type. Alembic's `compare_type` treats `UnicodeText` like `Text`, so autogenerate reports no spurious type change. A live CJK/emoji round trip on both drivers covers it, and six `UnicodeTextTest` compliance entries are removed. `docs/TYPES.md` (+ Korean) lists `UnicodeText` as `STRING` and `Unicode(n)` as the `VARCHAR(n)` it compiles to, and notes that no column-level `CHARSET`/`COLLATE` is rendered (`collation=` is dropped) and that non-ASCII text needs a UTF-8 database ([#539](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/539)) by @yeongseon.

- **Reflection no longer duplicates unique constraints or returns table indexes for views (#529)** — CUBRID stores unique constraints and unique indexes as the same metadata. `get_unique_constraints()` now marks each one as `duplicates_index`, so SQLAlchemy reflection and Alembic autogenerate keep the unique index instead of adding a second `UniqueConstraint`. `get_indexes()` returns `[]` for views instead of the base table's indexes. The class-type lookup handles case folding, is cached per Inspector and prefers the current user's object over a same-named DBA view on CUBRID 11.2+. **Resource safety (#548):** single-row catalog and `SHOW CREATE` reads now close their query handles (`Result.first()` instead of `fetchone()`); previously reflecting ~50–60 tables on pycubrid could hit the server's 100-entry limit (-830). Live tests reflect 150 tables on CUBRID 10.2/11.4 with both drivers; 36 resolved `ComponentReflectionTest` failures are removed from the baseline ([#541](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/541)) by @yeongseon.

- **`get_foreign_keys()` returns foreign keys sorted by name (#531)** — they came back in `SHOW CREATE TABLE` order; `get_foreign_keys()` and `get_multi_foreign_keys()` now sort by constraint name, like SQLAlchemy's built-in dialects. The 8 `test_get_multi_foreign_keys[False-…]` compliance entries are removed for all three lanes ([#537](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/537)) by @yeongseon.

- **Foreign keys and unique constraints on column names containing parentheses are reflected (#532)** — the `SHOW CREATE TABLE` parser stopped at the first `)`, so for a column named `[(3)]` the foreign key reflected `referred_columns: []` and autoloading the child table raised `ArgumentError`. Column lists are now parsed as bracketed names, so names containing `(`, `)`, `,` or spaces work. Offline tests use DDL captured from CUBRID 11.4; the 6 `BizarroCharacterTest::test_fk_ref[…-(3)-…]` compliance entries are removed for all three lanes ([#542](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/542)) by @yeongseon.

- **`Index.drop()` and Alembic `op.drop_index()` emit `DROP INDEX <name> ON <table>` (#533)** — the generic `DROP INDEX <name>` was a -493 syntax error because CUBRID scopes an index to its table; the compiler now emits `DROP INDEX <quoted name> ON <quoted table>` (with the schema when set). `CompileError` is now raised for `if_exists=True` on `DropIndex` or `op.drop_index()` (CUBRID 10.2, 11.0, 11.2 and 11.4 have no `DROP INDEX IF EXISTS`; check `inspect(conn).has_index()` first, as `Index.drop(checkfirst=True)` does), for an index not bound to a table, and for `op.drop_index()` without `table_name` (instead of emitting `ON no_table`). `has_index()` is now `@reflection.cache`d, so an `Inspector` answers from its cache until `clear_cache()` (calls without an `info_cache`, such as `Index.drop(checkfirst=True)`, still query the catalog); a failing catalog query in it now raises instead of returning `False`, while a missing table or index still returns `False`. The `HasIndexTest::test_has_index[dialect|inspector]` compliance entries are removed. `docs/ALEMBIC.md` (+ Korean) documents the `ON <table>` form and the `if_exists` limitation ([#538](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/538)) by @yeongseon.

- **JSON `.as_numeric(p, s)` returns `Decimal` instead of `float` (#535)** — the SQL changes from `CAST(JSON_EXTRACT(...) AS DOUBLE)` to `CAST(JSON_EXTRACT(...) AS NUMERIC(p,s))` when the `Numeric` has both precision and scale, so `select(t.c.data["a"].as_numeric(10, 2))` returns `Decimal('15.00')` instead of a lossy `15.0`. JSON numbers (including `1e3`), plain-decimal numeric strings such as `"15.5"` and `true`/`false` cast; JSON `null` stays SQL `NULL`. **Limits:** CUBRID raises -181 for an exponent-notation string (`"1e3"`) or a non-numeric string (`"abc"`, `""`) and -427 for a value that does not fit `NUMERIC(p,s)`; use `as_float()` (`DOUBLE`) for exponent strings and out-of-range values, and filter non-numeric strings, which `as_float()` also rejects with -181. With `asdecimal=False` the result is still a `float`. `as_float()`, any `Float` and a `Numeric` without both precision and scale stay `DOUBLE`, because a bare CUBRID `NUMERIC` means `NUMERIC(15,0)` and would truncate. Verified on CUBRID 10.2 and 11.4 with both drivers on SQLAlchemy 2.0.53 and 2.1.1; 18 `JSONTest::test_index_cross_casts[...-numeric]` compliance entries are removed, and `docs/FEATURE_SUPPORT.md` (+ Korean) lists `as_numeric()` ([#536](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/536), [#547](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/547)) by @yeongseon.

- **AUTOCOMMIT now works across CUBRIDdb and sync/async pycubrid, and pooled isolation is restored (#501)** — `execution_options(isolation_level="AUTOCOMMIT")` used to fail with `ArgumentError`, and engine-level AUTOCOMMIT could raise `ValueError`. AUTOCOMMIT now sets the driver's `autocommit` flag, and SQLAlchemy's built-in isolation handling replaces the dialect's `on_connect()` hook, so an engine-level level (including an alias such as `CURSOR STABILITY` → `READ COMMITTED`) is restored when a connection with a temporary override returns to the pool. Invalid levels raise `ArgumentError` from `create_engine()` and engine/connection options; direct `dialect.set_isolation_level()` still raises `ValueError`, and a DB-API connection without an `autocommit` property raises `AttributeError`. **Custom pools:** code that calls `dialect.on_connect()` itself must now apply its own isolation setting (or use `dialect._builtin_onconnect()`), and `dialect.isolation_level` reports the canonical name. **pycubrid:** with engine-level AUTOCOMMIT each statement reconnects at the server-default isolation level (cubrid-lab/pycubrid#468); `skip_autocommit_rollback=True` is recommended and now works with driver flag detection. Live tests cover all three drivers; see `docs/ISOLATION_LEVELS.md` and `docs/TROUBLESHOOTING.md` ([#528](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/528)) by @yeongseon.

- **Engine- and connection-level `isolation_level` no longer falls back to READ COMMITTED on pycubrid after `commit()` / `rollback()` (#505)** — with `create_engine("cubrid+pycubrid://…", isolation_level="SERIALIZABLE")` the first checkout already reported READ COMMITTED, and a per-connection level was lost at the next commit, because pycubrid 1.7.1 (and `main`) opens a new broker connection after each commit or rollback (cubrid-lab/pycubrid#468; CUBRIDdb is unaffected). The sync and async pycubrid dialects now re-apply the level in `do_commit()` / `do_rollback()`. **Cost:** one `SET TRANSACTION ISOLATION LEVEL` + `COMMIT` per commit or rollback, only on connections with a configured level (nothing per statement), and such a pooled connection holds a broker CAS while idle. A failed re-apply never fails a successful commit or masks a rollback's exception; it is logged and retried in `do_begin()`. On an engine without a configured level, check-in after a per-connection override stops the re-apply. The workaround is to be removed once a pycubrid release fixing pycubrid#468 is the minimum. Live tests cover all three drivers, and `docs/DRIVER_COMPAT.md` Known Issue 10 and `docs/ISOLATION_LEVELS.md` (+ Korean) document it; resetting to the engine level after a per-connection override is tracked in #501 ([#527](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/527)) by @yeongseon.

- **`driver_connection` on `cubrid+aiopycubrid://` is now the `pycubrid.aio` connection (#520)** — `(await conn.get_raw_connection()).driver_connection` returned SQLAlchemy's `AsyncAdapt_pycubrid_connection` adapter; it now returns the wrapped `pycubrid.aio.AsyncConnection`, as SQLAlchemy's asyncpg and aiomysql dialects do, so driver-specific async APIs (`ping()`, `cursor()`, ...) are reachable. Code that relied on `driver_connection` being the adapter should use `dbapi_connection` instead. A unit test and a live async test cover it ([#522](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/522)) by @yeongseon.

- **SQLAlchemy compliance tests no longer silently skip hundreds of valid cases (#463)** — requirement properties shared mutable exclusions, so stacked `@testing.requires` decorators skipped valid tests. With pycubrid, SQLAlchemy 2.0.53 and CUBRID 11.4 the passing count rose from 334 to 631, and all three lanes were re-baselined on fresh CUBRID 10.2 and 11.4 databases. The recapture enabled `reflects_pk_names` and `implicitly_named_constraints`, requires a UTF-8 database for `unicode_ddl` (the official Docker image creates ISO-8859-1 databases), and marks `precision_generic_float_type` unsupported because CUBRID `FLOAT` is single precision. The newly exposed bugs were filed as #529–#535 (see the entries above) ([#526](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/526)) by @yeongseon.

- **`Inspector.has_table()` honors the inspector cache (#463)** — `inspect(engine).has_table()` queried the catalog on every call and reported a table created after the first call before `clear_cache()`; it is now `@reflection.cache`d like SQLAlchemy's built-in dialects. Direct `dialect.has_table()` calls without an `info_cache` and `create_all(checkfirst=True)` are unaffected. Found by SQLAlchemy 2.1's `HasTableTest::test_has_table_cache` in the new pycubrid compliance lane ([#526](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/526)) by @yeongseon.

- **`cubrid://` executemany no longer stores the previous row's value for `None` or reports a last-row rowcount (#502)** — CUBRIDdb 11.3.0.51 skips binding `None` and prepares `executemany` once, which silently corrupted `text()` and Core `UPDATE`/`DELETE` executemany and made batched ORM UPDATEs raise `StaleDataError`. On `cubrid://` the dialect now executes each parameter set and sums the rowcount, so `supports_sane_multi_rowcount` is accurate on both drivers; the per-row execution makes large batches slower. `cubrid+pycubrid://` and `cubrid+aiopycubrid://` keep the driver's prepare-once `executemany`, and a multi-row Core `insert()` using insertmanyvalues is unaffected, except that an INSERT into a table with a `bind_expression()` column falls back to executemany (#421) and so uses the per-row path on `cubrid://`. `docs/DRIVER_COMPAT.md` and `docs/SUPPORT_MATRIX.md` (+ Korean) record the driver bug, the per-row cost and when the guard will be removed ([#513](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/513)) by @yeongseon.

- **Alembic finds `CubridImpl` with a default `env.py` (#504)** — `alembic upgrade` against any CUBRID URL failed with `KeyError: 'cubrid'` unless `env.py` imported `sqlalchemy_cubrid.alembic_impl` by hand, because no Alembic release reads the package's (now removed) `alembic.ddl` entry point. The dialect now imports `alembic_impl` whenever Alembic is installed. The standard `alembic init` template works unchanged for synchronous URLs; for `cubrid+aiopycubrid://` online migrations use Alembic's async template (`alembic init -t async`), verified live on CUBRID 11.4 (the standard template fails there with `MissingGreenlet`). The dialect always loads: a missing Alembic is skipped silently, and one that fails to import (1.7.0/1.7.1 raise `NameError` on SQLAlchemy 2.x) disables the integration with one `RuntimeWarning` (or a `sqlalchemy_cubrid.dialect` log message if warnings are errors). The `[alembic]`/`[dev]` extras, the pre-commit mypy hook and the docs now require `alembic>=1.7.2,<2.0`, the oldest release that imports on SQLAlchemy 2.x. `test/test_alembic_registration.py` runs the `alembic` CLI on an unmodified `alembic init` project offline for all four URL forms and online, and the wheel smoke checks verify registration ([#511](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/511)) by @yeongseon.

- **Async `LargeBinary` / `BLOB` binding no longer raises `AttributeError` (#500)** — every `cubrid+aiopycubrid://` INSERT/UPDATE touching a binary column failed, even with `None` or an unset ORM attribute, because the async DB-API adapter did not expose `Binary`. The adapter now copies the full PEP 249 module surface from `pycubrid`, which a unit test checks; live async tests cover Core inserts into `LargeBinary`/`BLOB` and an ORM insert. The async binding xfails from #485 are removed, leaving only the strict LOB-read locator xfails (cubrid-lab/pycubrid#441), and `docs/DRIVER_COMPAT.md` and `docs/TYPES.md` (+ Korean) no longer list the async `Binary` issue ([#510](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/510)) by @yeongseon.

- **`String(0)` / `VARCHAR(0)` / `NVARCHAR(0)` no longer silently compile to the 4096 default (#440)** — an explicit `length=0` was treated as "no length" and rendered `VARCHAR(4096)` (or `NCHAR VARYING(4096)`); it now raises `CompileError`, since `VARCHAR(0)` is not a valid CUBRID length. `length=None` still gets the documented default ([#456](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/456)) by @anyingiit (first contribution 🎉).

- **Reflection now returns table and view names in deterministic order (#443)** — added `ORDER BY class_name` to `get_table_names()` and `get_view_names()` catalog queries so reflection results no longer depend on database row order ([#457](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/457)) by @itsdevcode (first contribution 🎉).

- **Contributor workflow and docs exceptions clarified** — normal contributions use shared checks and matching docs, and maintainers coordinate project-specific reviews, labels, translation deferrals and releases. A docs-not-needed reason in the PR body must be a populated standalone statement (quoted or template examples do not count); executable doctests and real event/workflow regressions run locally and in docs-sync. Four reusable-workflow callers are pinned to a verified upstream commit without changing their inputs or rollout settings ([#472](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/472)) by @yeongseon.

- **Pure-driver integration setup is explicit (#464)** — `tox -e integration` now requires a `cubrid+pycubrid://` test URL instead of the bare `cubrid://` C-extension URL, and a bounded sync/async `SELECT 1` preflight fails before pytest when the URL, driver or database is unavailable. Async and stress suites derive their endpoint from the selected URL (an explicit `CUBRID_TEST_AURL` still works). The C-extension compliance CI route is unchanged, and native-driver comparisons are explicitly skipped when that driver is absent ([#471](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/471)) by @yeongseon.

- **Local tooling agrees with CI (#464)** — pre-commit Ruff/mypy revisions match the dev pins, tox covers Python 3.10–3.14 with CI's type-check cells and the 95% coverage threshold, and a consistency check rejects stale pins, missing interpreter branches, source omissions and runner drift ([#471](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/471)) by @yeongseon.

- **Strict typing is enforced across SQLAlchemy 2.0 and 2.1 (#459)** — compiler overrides and timezone constructors are fully typed without changing behavior, and two pinned type-check cells must pass through the required `matrix-result` check. UNIQUE-index FK collision checks now raise a clear `CompileError` when no live Alembic connection is available. Runtime SQL compilation and the 95% offline coverage threshold are unchanged ([#469](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/469)) by @yeongseon.

- **Async installation includes SQLAlchemy's required bridge (#448)** — the `[pycubrid]` and `[dev]` extras now request `SQLAlchemy[asyncio]`, which installs `greenlet` on SQLAlchemy 2.0 and 2.1; the `[pycubrid]` extra covers both sync and async URLs, and a bare installation keeps the same dependency contract. Fresh wheel smoke tests create async engines on 2.0.53 and 2.1.1 without a database ([#466](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/466)) by @yeongseon.

- **Installation guidance distinguishes the driver from the async bridge (#448)** — the FAQ, connection and troubleshooting guides and their translations state that pycubrid itself needs no CUBRID native libraries, while the `[pycubrid]` extra's `greenlet` dependency may need build tools when no compatible wheel is available ([#466](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/466)) by @yeongseon.

- **Last-insert-ID SQL fallback works on SQLAlchemy 2.x (#458)** — `SELECT LAST_INSERT_ID()` now runs on a regular cursor from the active DBAPI connection instead of SQLAlchemy's unimplemented server-side-cursor hook. Native driver IDs (including `None`) remain preferred, and the temporary cursor is closed even if execution, fetching or integer conversion fails ([#466](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/466)) by @yeongseon.

- **Nightly mutation testing now uses mutmut 3** — the development extra pins `mutmut>=3.8,<4` instead of 2.x (superseding #450), and the non-gating CI job uses mutmut 3's configuration and commands. A crash, failed clean tests, zero mutants or zero kills fails the step; surviving mutants only lower the score, and the job remains `continue-on-error`. Scores are not comparable with the old 288/449 baseline. No runtime change ([#489](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/489)) by @yeongseon.

- **Timezone-aware types keep `timezone=True` on the instance (#442)** — `TIMESTAMPTZ`, `TIMESTAMPLTZ`, `DATETIMETZ` and `DATETIMELTZ` inherited the default `TIMESTAMP` constructor, so their instances reported `timezone=False`; they now set `timezone=True` and discard a duplicate `timezone` keyword during reflection ([#445](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/445)) by @pratipc (first contribution 🎉).

### Documentation

- Added a README "First contribution" guide (with Korean translation) pointing newcomers to the right sibling repo for their first PR, and documented the `good first issue` → `status: in progress` label lifecycle in AGENTS.md ([#494](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/494)) by @yeongseon.

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

- **Native ENUM type support (#343)** — `sqlalchemy_cubrid.ENUM` renders `ENUM('a', 'b', ...)` DDL. Plain `sa.Enum` maps to native ENUM via colspecs. Reflection parses the element list from `SHOW COLUMNS`. Verified live on CUBRID 10.2, 11.0, 11.4 (the docs previously and wrongly claimed CUBRID has no ENUM) ([#345](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/345)) by @yeongseon.

- **`IS [NOT] DISTINCT FROM` emulation (#344)** — CUBRID lacks the SQL-standard syntax but supports the null-safe equal `<=>`. The dialect renders `(a <=> b) = 0` for `IS DISTINCT FROM` and `a <=> b` for `IS NOT DISTINCT FROM`; the negated form replaced MySQL's `NOT (a <=> b)` before this release (see the #377 fix below) ([#345](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/345)) by @yeongseon.

- **Public docstrings now include runnable usage examples (#337)** — short, live-verified examples cover the five main entry points: the connection URL forms (`cubrid+pycubrid://`, `cubrid+cubriddb://`, async `cubrid+aiopycubrid://`) in the package docstring, the `ON DUPLICATE KEY UPDATE` construct on `insert()`, and reflection via `inspect()` in the dialect module docstring (`REPLACE` and `MERGE` already had examples). Docstrings only, no behavior change; each example was executed against a live CUBRID 11.4 ([#436](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/436)) by @yeongseon.

- **UUID round-trips are now pinned by a contract test matrix (#376)** — `test/test_uuid_contract.py` checks `sa.Uuid()` (Python `uuid.UUID` values) and `sa.Uuid(as_uuid=False)` (string values) through INSERT, SELECT, WHERE, UPDATE and reflection against a live CUBRID. CUBRID has no native UUID type; the dialect stores it as `CHAR(32)`, and these 8 `integration`-marked tests catch regressions in that CHAR-backed storage or the value coercion (verified: `sa.Uuid()` round-trips as `uuid.UUID`, `as_uuid=False` as `str`, WHERE/UPDATE by UUID work, and reflection reports `CHAR`). They run in the nightly `integration-full` bug-hunt job ([#435](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/435)) by @yeongseon.

- **Mutation testing now checks that the offline suite verifies `compiler.py` logic, not merely executes it (stabilization Phase 8)** — a `[mutmut]` configuration in `setup.cfg` (pinned `mutmut>=2.5,<3` in the `dev` extra) and a non-gating nightly `mutation-testing` job in `integration-full` mutate `compiler.py` and assert that the tests catch each change. The initial run scored 55.9% (251/449 mutants killed) and exposed weak substring assertions (e.g. only `"JSON_EXTRACT" in sql`); exact-match assertions on the full compiled output (JSON path extraction, `LIMIT`/`OFFSET` operand order and the offset-without-limit sentinel form, `UPDATE ... LIMIT`, `GROUP_CONCAT`) raised it to 64.1% (288/449). The job is `continue-on-error` because a score dip signals a test to strengthen, not a reason to block a release; it needs no database ([#433](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/433)) by @yeongseon.

- **Integration tests now exercise realistic ORM application behavior** — `test/test_dogfood_orm.py` models users, orders and tags (one-to-many and many-to-many) and verifies returned data, not only compiled SQL. Its 16 live tests cover lazy, `selectinload` and `joinedload` relationships; joins, filters, aggregates, correlated subqueries, pagination and outer joins; and commit/rollback, bulk updates, orphan cascade deletion and auto-generated primary keys after `flush()`, catching failures that individual compiler tests may miss. They run in the historical `integration-full` `fuzz-bug-hunt` job against **CUBRID 11.4**, not across the four-version snapshot matrix ([#432](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/432)) by @yeongseon.

- **Cross-version snapshots detect undeclared CUBRID behavior differences** — `test/version_differential/snapshot.py` records live server capability probes (ENUM, Boolean casts, `<=>`, CTEs, windows, `RETURNING`, `INTERSECT`/`EXCEPT`) and `get_columns()` reflection for fixed column types. The `integration-full` matrix captures one snapshot per supported server version (10.2, 11.0, 11.2 and 11.4), and `version-differential` fails when a dialect-visible difference is not declared in `KNOWN_DIFFERENCES`. This checks portability expectations rather than assuming that all underlying servers behave identically ([#431](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/431)) by @yeongseon.

- **Capability probes check declared flags against the server, and driver-differential tests compare pycubrid with CUBRIDdb (stabilization Phases 5 & 7)** — `test/capability/test_capability_probes.py` runs raw SQL against a live CUBRID and asserts the server matches what the dialect declares (`supports_native_enum`, `supports_native_boolean`, `supports_is_distinct_from`, `supports_multivalues_insert`, `supports_alter`, `supports_comments`, `insert_returning`, plus CTE/window/LIMIT-OFFSET). `test/test_driver_differential.py` runs the same Core operations on the pycubrid and CUBRIDdb C-extension drivers and asserts they agree on SELECT round-trips, UPDATE/DELETE rowcount, aggregates and NULL handling (skipping cleanly if the C-extension driver is not built). Both are `integration`-marked and run in the nightly `integration-full` bug-hunt job ([#429](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/429)) by @yeongseon.

- **Property-based fuzz and metamorphic tests (Hypothesis) probe inputs the hand-written suite never enumerated (stabilization Phases 1–4)** — `test/test_fuzz_select.py`, `test/test_fuzz_insert.py`, `test/test_fuzz_reflection.py` and `test/test_metamorphic.py` generate SELECT/INSERT combinations and random tables (boundary values `0`, `±1`, `2^31`, `2^63-1`; empty/Unicode/reserved-word/backslash strings) and assert invariants: compilation raises only `CompileError`, placeholder count equals bound-parameter count, single/executemany/multi-values inserts store identical data, DDL→reflection round-trips agree (columns, nullability, primary keys, unique constraints), and Core vs ORM SELECT, bind vs literal, and SQL LIMIT/OFFSET vs a Python slice return identical rows. Hypothesis profiles (`dev`/`ci`/`nightly`) are registered in `conftest.py`; PR CI runs the fast profile; the nightly `integration-full` workflow runs the 2000-examples profile against live CUBRID. This bug-hunt found and fixed #426 ([#425](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/425), [#427](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/427)) by @yeongseon.

### Fixed

- **Removed the dead `implicit_returning = False` dialect attribute (#396)** — a SQLAlchemy 1.x-era switch whose comment claimed it prevents a `ResourceClosedError` on server-default INSERTs. In SQLAlchemy 2.x the CRUD compiler decides implicit `INSERT ... RETURNING` from `insert_returning` (already `False`), not `implicit_returning`, and `DefaultDialect` no longer defines the attribute. Verified live on CUBRID 11.4 that a server-default INSERT + ORM refresh behaves identically without it (no `ResourceClosedError`); an offline regression test asserts that `insert_returning`/`update_returning`/`delete_returning` are the real switches and that the dead attribute stays gone ([#437](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/437)) by @yeongseon.

- **`docs/TROUBLESHOOTING.md` no longer documents LIMIT/OFFSET SQL the dialect never emits (#416)** — the section wrongly claimed the dialect generates `LIMIT n OFFSET m` and that CUBRID rejects the comma form. The dialect **only ever** emits CUBRID's comma form `LIMIT offset, count` (offset first), and offset-without-limit uses a sentinel count; `select(users).limit(10).offset(20)` compiles to `LIMIT 20, 10`, not `LIMIT 10 OFFSET 20`, so a reader trusting the old doc would also have read the two operands in the wrong order. Corrected in both the English and Korean (`docs/ko/TROUBLESHOOTING.md`) docs ([#434](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/434)) by @yeongseon.

- **`docs/llms-full.txt` is regenerated, and CI now fails if it drifts (#383)** — the AI-facing doc bundle was stale relative to the corrected source docs (it still taught the pre-#356 `VALUES()` ODKU pattern). It is regenerated via `scripts/generate_llms_full.py`, and the `lint` CI job now regenerates and diffs it so it can no longer silently go stale ([#434](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/434)) by @yeongseon.

- **Reflection now returns column comments, consistent missing-table errors, and only user views (#387)** — `get_columns()` returns actual comments instead of silently reporting `None` (the catalog query now reads the correct `class_of.class_name`); missing tables and views raise SQLAlchemy `NoSuchTableError` from `get_columns()` / `get_indexes()` instead of a raw driver `ProgrammingError` (-493 / 42S02); and `get_view_names()` filters internal system views using `is_system_class = 'NO'`. This clears 22 of the 25 known-failure cases in SQLAlchemy's `ComponentReflectionTest`. CUBRID normalizes identifiers to lower case rather than the upper case assumed by `NormalizedNameTest`, so `requires_name_normalize = False` correctly skips that requirement; case-insensitive schema matching is unchanged. The other three failures (`test_get_noncol_index` twice and `test_get_view_names[False]`) are SQLAlchemy-harness fixture limitations because their objects are not created on CUBRID, not unresolved dialect reflection bugs ([#428](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/428)) by @yeongseon.

- **`get_pk_constraint()` no longer drops composite primary-key columns (#426)** — reflecting a table with `PRIMARY KEY (a, b)` returned only `constrained_columns: ['a']`, silently losing every PK column after the first and giving no column order. CUBRID (MySQL-compatible) marks only the *first* column of a composite PK as `PRI` in `SHOW COLUMNS`, which the reflection relied on. PK columns are now read, in key order, from the `_db_index` / `_db_index_key` system catalog, with a `SHOW COLUMNS` fallback if the catalog query fails. This fixes reflected multi-column-PK ORM mappings and Alembic autogenerate, and was found by the new reflection round-trip fuzzer ([#427](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/427)) by @yeongseon.

- **`executemany` INSERT into a column with a `bind_expression()` CAST no longer sends the wrong parameter count (#421)** — SQLAlchemy's `insertmanyvalues` row expansion miscounts bind parameters when a column's type wraps its bind in a `bind_expression` (e.g. a `TypeDecorator` rendering `CAST(? AS VARCHAR(50))`): 4 placeholders but only 3 parameters, so the driver raised "wrong number of parameters". The dialect now drops the `insertmanyvalues` plan (in `visit_insert`) for INSERTs targeting such a column and falls back to ordinary DBAPI executemany; single-row inserts and the normal multi-row fast path (columns without a `bind_expression`) are untouched. Fixes the compliance suite's `CastTypeDecoratorTest::test_special_type` ([#423](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/423)) by @yeongseon.

- **`Identity()` columns now emit `AUTO_INCREMENT`, and DATETIME/TIME microsecond limits are declared to the test suite (#388)** — SQLAlchemy stores an `Identity()` as `column.server_default`, which made the DDL compiler emit a plain `INTEGER NOT NULL` column, so inserts failed with `Missing value for attribute 'id'`; `Identity()` is now treated as CUBRID's `AUTO_INCREMENT`. `requirements.py` also declares `datetime_microseconds`/`time_microseconds` as unsupported (CUBRID `DATETIME` stores millisecond precision only and `TIME` has no fractional seconds, verified live on 11.4), so the compliance suite skips those tests instead of baselining them as xfail. The remaining `#388` triage entries (`DistinctOnTest`, `ReturningGuardsTest`, C-driver-specific `RowCountTest`) stay as documented xfails; the genuine `CastTypeDecoratorTest` `insertmanyvalues` parameter-count bug is split out to #421 ([#422](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/422)) by @yeongseon.

- **Documented that the legacy `CUBRIDdb` C-extension driver loses `NUMERIC`/`DECIMAL` fractional precision (#386)** — the C-extension driver (bare `cubrid://`) truncates the fractional part of `NUMERIC`/`DECIMAL` values *below* the DBAPI layer, returning e.g. `15` for a stored `15.7563`. The data is already lost before SQLAlchemy sees it, so no dialect result processor can recover it; this is an upstream C-driver limitation, not a dialect bug. The pure-Python `cubrid+pycubrid://` driver returns `Decimal` correctly (verified live on 11.4) and is the recommended driver. The affected `NumericTest` nodes stay baselined in `test/known_failures.txt` with this explanation, and `docs/DRIVER_COMPAT.md` / `docs/TYPES.md` now document the fidelity difference between the two drivers ([#420](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/420)) by @yeongseon.

- **`ON DUPLICATE KEY UPDATE` referencing `stmt.inserted.col` now fails clearly for inline multi-row `VALUES` instead of a confusing bind error (#371)** — CUBRID has no `VALUES(col)` / row-alias syntax, so the dialect re-emits the INSERT bind parameter to reference the inserted value. That works for a single-row `INSERT` and for executemany (each execution is logically single-row), but an inline multi-row `insert(t).values([{...}, {...}])` has no single value to bind per conflicting row. It previously raised a misleading `cannot resolve INSERT bind parameter ... Ensure the column is included in the INSERT values` (the column *was* included); it now raises a clear `CompileError` naming the CUBRID limitation and pointing to executemany, single-row statements, a literal/expression update, or `MERGE`. Nested references (e.g. `func.coalesce(stmt.inserted.col, ...)`) are caught too; literal/expression updates that do not reference the inserted value keep compiling for multi-row inserts. Refusing to compile avoids silently binding one row's value for every conflicting row ([#418](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/418)) by @yeongseon.

- **`OFFSET` without `LIMIT` no longer silently caps result sets at ~1.07B rows (#414)** — a bare `.offset(n)` compiled to `LIMIT n, 1073741823`, reusing CUBRID's VARCHAR-length constant (2^30-1) as the row-count sentinel, so a query with an offset and no limit was silently truncated at 1,073,741,823 rows (wrong results, no error) on tables past that size. The sentinel is now `2^62` (`4611686018427387904`), effectively unbounded. It is deliberately **not** the signed BIGINT maximum (2^63-1): CUBRID overflow-checks `offset + row_count`, so a BIGINT-max sentinel raises `ERROR -458 (Overflow occurred in addition context)` for any positive offset (caught by the compliance suite's `FetchLimitOffsetTest`), while 2^62 leaves ~4.6×10^18 rows of offset headroom. The value is named `_CUBRID_OFFSET_NO_LIMIT_ROW_COUNT` in `compiler.py` and the regression test asserts on it and that the old 2^30-1 cap is gone ([#417](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/417)) by @yeongseon.

- **Numeric bind parameters keep their scale in arithmetic, and FROM-less `SELECT ... WHERE` compiles (#386)** — CUBRID coerces a bound parameter in `NUMERIC(p,s) + ?` arithmetic to an integer, silently dropping the fractional scale (a SQL literal or an explicit CAST keeps it). Scaled `NUMERIC`/`DECIMAL` binds now render `CAST(? AS NUMERIC(p,s))` so the scale is preserved; unconstrained `Numeric()` binds are left untouched (CUBRID's bare `NUMERIC` is scale 0, so specify precision/scale for exact decimals). A `default_from()` of ` FROM db_root` (CUBRID's `DUAL` equivalent) also means a FROM-less `SELECT` with a `WHERE` clause no longer raises a syntax error ([#400](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/400)) by @yeongseon.

- **`supports_is_distinct_from` / `supports_native_enum` now report their real capabilities (#381, #382)** — both flags were `False`, which made SQLAlchemy's official suite skip `IsOrIsNotDistinctFromTest` and the native-enum tests even though both features are fully implemented (IS DISTINCT FROM emulation via `<=>` from #345/#377; native `ENUM(...)` DDL). Both are now `True`, and the previously skipped suite tests run and pass live on CUBRID 11.4 (5 IS DISTINCT FROM + native-enum cases, zero regressions). The `ENUM` docstring is also corrected: it wrongly claimed `native_enum=False` is "ignored", but it correctly emits `VARCHAR(n)` per the SQLAlchemy contract (verified live) ([#390](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/390)) by @yeongseon.

- **SQLAlchemy's dialect compliance tests now fail CI on regressions (#380)** — the suite previously never ran correctly: missing `[sqla_testing]` configuration crashed setup, and `|| true` hid the result. The new config enables it, and CI runs it as a required Python 3.14 × CUBRID 11.4 cell on pinned SQLAlchemy 2.0.53. CUBRID has no temporary tables, so the associated requirements are excluded (removing 732 setup errors). Remaining known failures are recorded in `test/known_failures.txt` with strict xfails: new failures break CI, fixed cases must leave the manifest, and stale test names fail collection under `CUBRID_STRICT_KNOWN_FAILURES=1`. The baseline depends on SQLAlchemy's test version. Follow-up issues track view DDL (#385), Decimal (#386), reflection (#387), and other gaps (#388) ([#389](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/389)) by @yeongseon.

- **`IS DISTINCT FROM` live execution fixed (#377)** — live CUBRID rejects MySQL-style `NOT (a <=> b)` when the expression appears in a SELECT projection. The emulation now negates the NULL-safe `<=>` result as `(a <=> b) = 0`, which preserves the four-row SQL truth table and is valid CUBRID syntax. Added live truth-table coverage for both `IS DISTINCT FROM` and `IS NOT DISTINCT FROM` ([#379](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/379)) by @tayfuryldz (first contribution 🎉).

- **create-release.yml: dropped `--target` from `gh release create`** — with an already-pushed tag (the normal tag-push trigger) `--verify-tag` already guarantees the tag exists, and passing `target_commitish` for an existing tag makes the Releases API return `422 Validation Failed`, so a tag-triggered run would have failed before creating the release. The workflow had not yet run in this repository, so the change is preventive ([#336](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/336)) by @yeongseon.

### Documentation

- **Demo GIF embedded in README** — auto-generated terminal demo showing create_engine → connect → execute → result ([#347](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/347), [#348](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/348), [#349](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/349)) by @yeongseon.

- **Korean/multi-language docs governance** — every `docs/README.<lang>.md` translation now carries a sync marker, and docs-sync gained a `translation-sync` job that fails a PR when `README.md` changes without any translation changing (escape hatch: the `translations-deferred` label) ([#340](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/340)) by @yeongseon.

- **한국어 문서 페이지 — 배치 5 완결 (#341)** — TROUBLESHOOTING(1,325줄) 번역으로 14페이지 전체 완성 ([#342](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/342)) by @yeongseon.

- **한국어 문서 페이지 — 배치 4 (#341)** — FEATURE_SUPPORT(기능 비교)·DEVELOPMENT(개발 가이드) 번역 추가. TROUBLESHOOTING만 남음 ([#342](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/342)) by @yeongseon.

- **한국어 문서 페이지 — 배치 3 (#341)** — ALEMBIC(마이그레이션 가이드) 번역 추가. FEATURE·TROUBLE·DEV만 남음 ([#342](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/342)) by @yeongseon.

- **한국어 문서 페이지 — 배치 2 완결 (#341)** — ORM_COOKBOOK·DML_EXTENSIONS 번역으로 Usage 축 완성. ALEMBIC·FEATURE·TROUBLE·DEV는 후속 배치 ([#342](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/342)) by @yeongseon.

- **한국어 문서 페이지 — 배치 2 (Usage/Reference 1차, #341)** — TYPES·ARCHITECTURE 번역 추가. ORM_COOKBOOK·DML_EXTENSIONS·ALEMBIC·FEATURE·TROUBLE·DEV는 후속 ([#342](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/342)) by @yeongseon.

- **한국어 문서 페이지 — 배치 1 (Getting Started/Ref/Ops 축, #341)** — QUICKSTART·CONNECTION·DRIVER_COMPAT·ISOLATION_LEVELS·SUPPORT_MATRIX·PERFORMANCE 6페이지 번역을 `docs/ko/`에 추가. Usage 축(ORM·DML·TYPES·ALEMBIC)과 FEATURE/ARCH/TROUBLE/DEV는 후속 배치 ([#342](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/342)) by @yeongseon.

- **Docs site information architecture unified across the ecosystem** — nav reorganized to the shared six-tab skeleton (Home / Getting Started / Usage / Reference / Operations / Project), the five README translations (ko/de/hi/ru/zh) are now reachable via Project → Translations (previously URL-only), palette unified to blue with search-suggest, and the homepage gains an Ecosystem section linking the three sibling sites ([#339](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/339)) by @yeongseon.

- **CUBRID-Python BSD basis documented, server-license line added, NOTICE created, copyright unified (#333)** — `THIRD_PARTY_LICENSES.md` now records that the optional CUBRID-Python extra's `BSD` claim rests on PyPI metadata and setup.py (the upstream repository ships no LICENSE file or headers; 2- vs 3-Clause unspecified), and carries the verified CUBRID server licensing statement (engine Apache-2.0, APIs/connectors BSD per upstream `COPYING`; GPL v2+ is outdated). A two-line `NOTICE` states this is an independent implementation with no third-party code, and the LICENSE copyright is unified to `Yeongseon Choe, Gyeongjun Paik` (2021-2026) ([#334](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/334), [#335](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/335)) by @yeongseon.

- **Added `THIRD_PARTY_LICENSES.md` and a Provenance section in `docs/ARCHITECTURE.md`** — the license inventory covers the default runtime tree (SQLAlchemy, greenlet, typing_extensions) and the optional `[alembic]`/`[cubrid]` extras; the provenance note states that this dialect is an independent implementation, not a port of the legacy `CUBRID-Python`-bundled dialect. Documentation only ([#332](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/332)) by @yeongseon.

## [1.7.0] - 2026-09-02

This release contains multiple dialect improvements and compatibility changes. Review the detailed sections below for the affected features and upgrade considerations.

**Highlights**

- **More reliable SQL and schema handling** — adds safer handling of unsupported SQL constructs.

- **Improved reflection and migrations** — fixes schema-name handling, isolation-level round trips, and support for column alterations through Alembic.

- **More dependable connection recovery** — recognizes additional pycubrid disconnect errors so SQLAlchemy can invalidate broken pooled connections.

- **Driver and compatibility guidance** — documents the explicit `cubrid+cubriddb://` connection URL and aligns SQLAlchemy support guidance with versions 2.0–2.1.

The detailed changes below include the original issue references and CI/documentation updates.

### Added

- **Explicit `cubrid+cubriddb://` URL and `[cubriddb]` install extra for the legacy CUBRIDdb driver (#276)** — the legacy `CUBRIDdb` C-extension driver (the driver bound to the bare `cubrid://` URL) can now be selected unambiguously with `cubrid+cubriddb://`, backed by a matching `cubriddb = ["CUBRID-Python"]` extra. The bare `cubrid://` URL continues to bind CUBRIDdb, so no existing URL changes behavior. For new projects the pure-Python `pycubrid` driver is the recommended choice: install `sqlalchemy-cubrid[pycubrid]` and use `cubrid+pycubrid://` (installs with pip alone, no C toolchain) ([#302](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/302), [#304](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/304)) by @yeongseon.

- **Alembic can now change column types and rename columns with native DDL (#305)** — `CubridImpl.alter_column()` previously raised `NotImplementedError` for these operations, forcing every such migration through `batch_alter_table` (full table recreate). CUBRID supports MySQL-compatible `ALTER TABLE ... MODIFY`, `CHANGE` and `RENAME COLUMN`, so a type change now compiles to `MODIFY`, a rename to `RENAME COLUMN ... TO ...`, and a combined rename + type change to a single `CHANGE`. The server's `alter_table_change_type_strict` system parameter governs type conversions: incompatible or truncating conversions error when `yes` and may silently truncate when `no`. `batch_alter_table` remains available as a fallback for genuinely lossy conversions. SQL-emission tests cover all three DDL forms ([#306](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/306)) by @yeongseon.

### Changed

- **Connection pools recognize transport failures more reliably (#314)** — a changed driver error wording is now less likely to leave a dead connection in the pool. `is_disconnect()` checks stable error codes first, then an `OSError` in the explicitly chained (cycle-guarded) `raise ... from` (`__cause__`) exceptions, and uses message text only as a fallback. It adds pycubrid `-4` (`ER_COMMUNICATION`, SQLSTATE `08S01`) to the existing disconnect codes `-21003/-21005/-10005/-10007`. To prevent false invalidation, implicit `__context__` is ignored, and an ordinary `OperationalError` / `InterfaceError` without a disconnect code, explicit `OSError` cause or recognized message is **not** a disconnect. The text fallback remains for CUBRIDdb (without `OperationalError`) and for pycubrid client errors that expose only a message, such as `connection lost during receive`. Offline tests cover numeric codes, explicit vs implicit causes, non-transport errors and the fallback ([#316](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/316)) by @yeongseon.

- **Ruff lint rules are now pinned explicitly (#271)** — `pyproject.toml` never set `[tool.ruff.lint] select`, so `ruff check` inherited ruff's implicit defaults, which grew in 0.16 (59 → 413 rules against this repo's config) and made #267 (`0.15.21 → 0.16.2`) fail lint with 151 errors in untouched code. The rule set is now pinned via `select = ["E4", "E7", "E9", "F"]`, exactly what ruff selected by default through 0.15.x (the same 59 rules under both versions); pinning only the ruff *version* in #252 could not survive that bump ([#272](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/272)) by @paikend.

### Fixed

- **`is_disconnect()` now recognizes pycubrid's `"connection lost during receive"` message (#322)** — a dead connection could be served to the next pool checkout because SQLAlchemy never invalidated it. The #314 notes and the `is_disconnect()` docstring said this message was covered by the message fallback, but the pattern was never added to `_disconnect_messages`. pycubrid raises it on a clean-EOF receive (`connection.py` sync path) with **no** numeric error code and **no** `OSError` cause, so all three detection layers missed it. The substring `"connection lost"` is now matched, with an offline regression test for a bare driver error carrying only that message ([#324](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/324)) by @yeongseon.

- **`SELECT SCHEMA()` returning NULL no longer leaks the fake schema `"None"` (#290)** — `get_schema_names()` now returns `[]` with no default schema instead of `["None"]`. `_get_default_schema_name()` stringified a SQL NULL into the literal `"None"`, which `get_schema_names()` and `_schema_is_default()` (they test against the `None` object) treated as a real schema. It now returns `Optional[str]` (`None` when `SCHEMA()` is NULL), pinning the default-schema contract used by the follow-up schema-guard fixes ([#296](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/296)) by @yeongseon.

- **Inline SQL literals now preserve backslashes on default CUBRID servers (#313)** — a path like `C:\temp` could previously be stored or compared with two backslashes instead of one, because the compiler doubled each `\` in `literal_binds=True` output following MySQL rules, while CUBRID defaults to `no_backslash_escapes=yes`. The fix covers inline DML, JSON paths and table/column comments, verified against CUBRID 11.2 and its documented default. If the server explicitly uses `no_backslash_escapes=no`, set the static `CubridDialect(no_backslash_escapes=False)` option to retain the old escaping behavior (offline compilation may have no connection to probe). **Migration:** audit existing data written with inline literals for already-doubled backslashes; the fix does not repair those rows. Compiler, JSON, DDL-comment and live-roundtrip tests cover the change ([#315](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/315)) by @yeongseon.

- **Object-detail reflection now raises `NoSuchTableError` for a non-default schema (#291)** — `get_columns`, `get_pk_constraint`, `get_foreign_keys`, `get_indexes`, `get_unique_constraints`, `get_view_definition` and `get_table_comment` previously ignored `schema=` and silently returned default-schema metadata, masking the fact that CUBRID exposes a single effective schema per connection. They now call a new `_raise_if_non_default_schema()` helper that raises `NoSuchTableError("<schema>.<object>")` when `schema=` is not the default, matching SQLite's behaviour and keeping a real "object not found" from hiding behind default-schema metadata. List/existence methods (`get_table_names`, `get_view_names`, `has_table`, `has_index`) keep returning empty/false via `_schema_is_default()` ([#297](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/297)) by @yeongseon.

- **Schema-default comparison is now case-insensitive (#292)** — `MetaData.reflect(schema="dba")` (or any case-mismatched schema argument) no longer yields no reflection or a spurious `NoSuchTableError`. CUBRID reports catalog names uppercased (`DBA`) while SQLAlchemy normalizes to lower case, and `_schema_is_default()` compared them with a case-sensitive `==`. Both sides now go through `self.normalize_name()`, so `"dba"`, `"DBA"` and the reported default compare equal. Names the user explicitly quoted (`quoted_name` with `quote=True`) are still compared case-sensitively, honouring the intent to preserve case ([#298](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/298)) by @yeongseon.

- **Schema reflection is now internally consistent (#280)** — `MetaData.reflect(schema=<x>)` no longer produces a contradictory "0 tables + all views". `get_schema_names()` used to return `[]` while `_get_default_schema_name()` returned a real schema, and `schema=` was handled differently per method (`get_table_names` returned `[]` for a non-default schema; `get_view_names`/`has_table`/`has_index` ignored it). The dialect now operates in a consistent single-schema mode: `get_schema_names()` returns `[default_schema_name]`, and a shared `_schema_is_default()` guard makes `get_table_names`, `get_view_names`, `has_table` and `has_index` honour `schema=` uniformly (the default schema is reflected; any other schema yields nothing). Owner-qualified cross-schema reflection is intentionally not attempted. Verified against live CUBRID 11.2 ([#287](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/287)) by @yeongseon.

- **Isolation-level `set` → `get` round-trip is now symmetric (#281)** — the short standard names a user passes in are now returned, which matters because SQLAlchemy compares them on pool return/reset. Previously `get_isolation_level()` returned only the long granular spelling (setting `"REPEATABLE READ"` came back as `"REPEATABLE READ SCHEMA, REPEATABLE READ INSTANCES"`; `"READ COMMITTED"` / `"CURSOR STABILITY"` came back as the long form). `_ISOLATION_LEVEL_REVERSE` now returns one canonical name per integer code: the short names for `READ COMMITTED` (4), `REPEATABLE READ` (5) and `SERIALIZABLE` (6), and the granular spelling for levels 1–3 (no short name). Aliases still collapse onto their canonical code, so every accepted input name round-trips to the same level. `reset_isolation_level()` and the `None`-row fallback now use `"READ COMMITTED"`. Offline round-trip tests and live CUBRID verification cover the change ([#286](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/286)) by @yeongseon.

- **Obsolete pre-MVCC isolation levels (1–3) removed from the accepted set (#307)** — names that resolve to the removed pre-MVCC levels 1–3 now raise a clear client-side `ValueError` instead of failing at the server. CUBRID's MVCC engine (10.0+) removed the legacy granular levels, and on a modern server (verified against live CUBRID 11.2.9) `SET TRANSACTION ISOLATION LEVEL 1|2|3` is rejected with *"Isolation level value in MVCC must be 'read committed', 'repeatable read' or 'serializable'"*, yet `_ISOLATION_LEVEL_MAP` and `get_isolation_level_values()` still advertised them. The rejected names are `REPEATABLE READ SCHEMA, READ UNCOMMITTED INSTANCES`, `READ COMMITTED SCHEMA, READ COMMITTED INSTANCES` and `READ COMMITTED SCHEMA, READ UNCOMMITTED INSTANCES`. The dialect keeps the three supported MVCC levels — `READ COMMITTED` (4), `REPEATABLE READ` (5), `SERIALIZABLE` (6) — plus the still-valid aliases (`CURSOR STABILITY` and the two long spellings that map to 4/5). `_ISOLATION_LEVEL_REVERSE` drops the dead 1–3 entries, while `get_isolation_level()` stays tolerant of any unexpected server value via its string fallback. `docs/ISOLATION_LEVELS.md` is rewritten to document the three MVCC levels and the historical removal ([#308](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/308)) by @yeongseon.

- **Lint job red on `main` (#268)** — `#257` removed the only use of `re` in `test/test_packaging.py` but left `import re` behind, so `ruff check sqlalchemy_cubrid/ test/` failed with `F401` and took `matrix-result` down with it. The orphaned import is removed ([#270](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/270)) by @paikend.

- **Code review fixes (#242–#246)** — the `visit_replace` fallback raises `NotImplementedError` instead of silently emitting `INSERT` (#243); `do_ping` is wrapped in `try`/`except` for `pool_pre_ping` safety (#244); `Merge` sets `inherit_cache` and the dead `_quote_free_identifiers` is removed (#245); the remaining broad `except` block in the dialect logs with `exc_info=True` (#246); and the `render_literal_value` backslash escaping is documented in a clarifying comment (#242) ([#247](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/247)) by @yeongseon, co-authored by Sean.

### Documentation

- **`LIST` is documented as a synonym for CUBRID's `SEQUENCE` type** — CUBRID accepts `LIST(type)` in DDL but normalizes it to `SEQUENCE` at parse time, so a `LIST(INTEGER)` column is stored and reflected as `SEQUENCE OF INTEGER` (verified on live CUBRID 11.2). `docs/TYPES.md` and a code comment in `ischema_names` now explain why the dialect exposes only the canonical `SEQUENCE` type and deliberately omits a `LIST` type/reflection entry (a type compiling to `LIST(...)` would produce spurious Alembic autogenerate diffs against the reflected `SEQUENCE(...)`). No behavior change ([#309](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/309)) by @yeongseon.

- **`get_isolation_level()` canonical names documented (#293)** — it returns the *canonical* name for a level, which may differ from the alias passed to `set_isolation_level()` (CUBRID accepts several aliases per numeric level). A note in `docs/ISOLATION_LEVELS.md` and the `get_isolation_level()` docstring now say so. Behavior is unchanged; the reverse mapping was already correct ([#299](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/299)) by @yeongseon.

- **`Documentation` project URL now matches the README docs badge (#294)** — `pyproject.toml` pointed at the repo tree (`.../tree/main/docs`) while the README badge pointed at the published site `https://cubrid-lab.github.io/sqlalchemy-cubrid/`. Both now use the published site, so PyPI metadata and the README agree ([#300](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/300)) by @yeongseon.

- **`[cubrid]` install extra documented in the README (#295)** — the optional `cubrid = ["CUBRID-Python"]` extra (the legacy C-extension driver used by the bare `cubrid://` URL) was declared in `pyproject.toml` but undocumented. A README installation note now explains what it installs and that the pure-Python `[pycubrid]` driver remains the recommended driver for new projects ([#301](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/301)) by @yeongseon.

- **Docs state SQLAlchemy support as 2.0–2.1, not 2.0–2.2 (#312)** — README (+5 locale docs), `docs/index.md`, `docs/ARCHITECTURE.md`, `docs/QUICKSTART.md`, `docs/PRD.md`, `docs/FEATURE_SUPPORT.md`, `docs/CONNECTION.md`, `docs/SA_COMPAT.md` and `ROADMAP.md` claimed support for a non-existent SQLAlchemy 2.2 line, contradicting `docs/SUPPORT_MATRIX.md` (which correctly lists 2.1.x as the latest tested version and ≥2.2 as unsupported). SQLAlchemy's next feature line is 2.1, not 2.2 — PyPI ships only `2.1.0b1/b2/b3` pre-releases. Historical CHANGELOG entries are left intact as an accurate record ([#312](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/312)) by @yeongseon.

### CI

- **CI lint uses the pinned ruff version (#252)** — the lint job ran an unpinned `pip install ruff`; it now installs from `.[dev]` extras to match the pinned `ruff==0.15.22` in `pyproject.toml` ([#252](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/252)) by @yeongseon.

- **Async integration tests honor the supported pycubrid version range (#318)** — the CI and full-integration workflows now run `pip install -e ".[pycubrid]"` instead of `pip install pycubrid`, enforcing the then-declared `pycubrid>=1.3.2,<2.0` range and avoiding an unintended future 2.x driver. They also drop a duplicate `pytest-asyncio` install already supplied by the development extra. These jobs verify released driver versions; testing pycubrid's unreleased `main` branch remains the separate upstream canary. CI only; no runtime or packaging change ([#319](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/319)) by @yeongseon.
- **`sqlalchemy-22-canary` retargeted to SA 2.1 and renamed `sqlalchemy-21-canary` (#312)** — its pin `--pre "sqlalchemy>=2.2.0b1,<2.3"` was unsatisfiable (no `2.2.x` release exists on PyPI; SQLAlchemy's next line is 2.1, latest stable `2.0.52`), so the job failed at the install step on every PR and `main` and never actually ran. It now installs `--pre "SQLAlchemy>=2.1.0b1,<2.3"` and remains `continue-on-error: true` (non-gating). This reverts the incorrect #231 "bump" (which assumed `2.1.0b1` was no longer a pre-release) and restores the intent of #206 ([#312](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/312)) by @yeongseon.

- **The pycubrid canary now runs live integration tests, and Alembic tests tolerate version differences (#323)** — earlier canary checks tested `pycubrid@main` offline only (#263, #264); ordinary CI exercised released drivers. A new non-gating `upstream-canary-integration` job starts CUBRID 11.4, installs pycubrid from `main`, and runs synchronous and asynchronous integration tests (`continue-on-error: true`) to expose cross-project regressions earlier. Separately, the Alembic test patch target now adapts to the installed module layout: in Alembic 1.14+, `alembic.autogenerate.compare` is a module rather than the package path previously patched, which caused four local `ModuleNotFoundError` failures. PR #325 also capped Alembic at `<2.0` in both the then-declared `[alembic]` and `[dev]` extras (range `>=1.7,<2.0`), affecting dependency resolution but not dialect runtime behavior ([#325](https://github.com/cubrid-lab/sqlalchemy-cubrid/pull/325)) by @yeongseon.

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
