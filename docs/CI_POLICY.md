# CI execution policy

Routine CI uses representative combinations instead of a Cartesian version/OS matrix.

| Trigger | Runtime validation |
| --- | --- |
| Documentation-only PR | Documentation and policy checks; no runtime suite or CUBRID provisioning |
| Ordinary code PR | One Ubuntu/Python 3.12 full offline suite with the 95% coverage floor (#742) |
| High-risk PR | Same full offline suite plus Python 3.14/CUBRID 11.4; targeted additional lanes where relevant |
| Code push to main | Ubuntu full offline suite with the existing 95% coverage floor on the oldest and newest supported Python (3.11, 3.15) (#734); live endpoints Python 3.14/CUBRID 11.4 and Python 3.11/CUBRID 10.2. The push of a release commit runs only the static, documentation and tooling checks; its runtime lanes run in the release at the same SHA (#737) |
| Monday 03:00 UTC | Same policy as a main push (including the Python 3.11/3.15 offline cells), comparing changes in the previous seven days; unchanged/docs-only history does not select runtime tests. The advisory SQLAlchemy pre-release canary and the oldest cell's advisory CUBRIDdb compliance run here, not on pushes; the compliance step needs code changes in the previous seven days (#737) |
| Explicit full dispatch or release | Existing full Python 3.11–3.15 × CUBRID 10.2/11.0/11.2/11.4 integration workflow and mandatory release lanes, plus the Python 3.11/3.15 offline cells, type checking, `alembic-compat`, the packaging smoke test and the gating SQLAlchemy compliance lanes (#737) |

PRs run the same full offline selection (`-m "not integration and not repo"`) and
95% coverage floor as pushes. The former three-file PR smoke ran in about 1 s
locally against about 24 s for the full suite, too small a saving to justify
letting offline regressions first fail on main (#742). Live integration on PRs
stays representative: contributors must run the regression checks relevant to
their change locally and record commands/results in the PR.
`make test-fast` runs this offline selection locally, and `make integration` remains
available without changing its scope; `make test` also runs the repository-tooling
tests (#1009).

Change selection is in `ci.yml`'s `detect-changes` job. Non-documentation paths
are code by default, so new source/configuration files do not silently become docs.
Connection/protocol/cursor/async/compatibility or dialect/compiler/reflection,
dependency, build and script changes and `ci.yml` itself select representative
pre-merge integration; other workflow changes select the tooling lane and the
offline suite instead (see
[Workflow change impact](#workflow-change-impact)). Repository tooling tests run in one Linux lane when tooling changes; tooling includes
`agent-evals/**` and every repository-tooling test module, because the offline lanes
never run those modules (#964).
The static lint job continues on all events, including generated documentation checks
and the README async example test (`test/test_readme_async_examples.py`), so a
README-only change still runs it.

The aggregate required-check name stays stable and includes change detection.
Selected jobs must succeed: skipped, failed or cancelled selected checks fail the
gate. Only intentionally unselected jobs may skip. Keep branch protection on the
aggregate gate; do not require every old matrix cell name after reducing matrices.
Branch protection must be inspected before merge. No protection-setting change
is part of this PR.

Full verification has no automatic nightly schedule. `integration-full.yml`
retains manual dispatch and the release `workflow_call` with the immutable candidate
SHA. Dispatch the workflow on the exact candidate branch/commit and verify the
run's head SHA before using it as PR evidence. A moved branch needs new evidence.
The routine CI dispatch is path-sensitive; use the full workflow to request an
unconditional compatibility run. No release publisher/generator is changed.

Concurrency is isolated by event and ref, so main pushes, weekly schedules and
manual dispatches cannot cancel each other. Superseded runs for the same PR still
cancel within that PR group. Main pushes and PR merge refs are
not assumed to have identical SHAs. Weekly change selection uses the previous
seven days, not a persisted last-success cache; a failed weekly run must be
rerun or followed by manual validation rather than treated as successful evidence.

GitHub charges have not been attributed to a workflow or runner SKU. Reduced job
counts establish less repeated work; they are not a measured monetary saving.
Compare subsequent Actions jobs/runner minutes and the actual billing category
before making a cost claim.

Routine type checking uses Python 3.13/SQLAlchemy 2.1.1; Alembic checks use latest,
and packaging uses SQLAlchemy 2.1.1. The live endpoint cells (Python 3.14/CUBRID 11.4 and Python 3.11/CUBRID 10.2) retain
SQLAlchemy 2.0 and 2.1 compliance coverage on main/weekly. Make integration is deferred
from PRs to non-PR code validation and also owns the former live-smoke assertions; the
advisory SQLAlchemy canary runs on the weekly schedule and manual dispatches (#737).

## Event tiers and cost evidence

\#737 gives each expensive workflow event one purpose: pull requests stay fast and
representative, `main` pushes carry endpoint evidence; the weekly schedule also carries the canaries, and the release runs the full matrix and fails closed. Consolidation
removed only lanes whose assertions another lane on the same SHA already makes,
or advisory lanes that gate nothing.

### Measurements

Measured with the GitHub REST API (`actions/runs` and `runs/{id}/jobs`) on
2026-10-09, before this change. Runner minutes are the sum of each executed job's
`completed_at - started_at`; "rounded" rounds every job up to a whole minute, the
granularity GitHub meters at. This repository is public and uses standard
GitHub-hosted runners, so runner minutes are not billed charges. Failure yield
counts failed runs; cancelled runs are listed apart because every one in the
sample was superseded by a newer run in the same concurrency group, not a
defect. Samples are the most recent completed runs of each category; the
workflow shape changed often in early October, so windows are short.

| Category | Window (runs) | Median jobs | Median runner min | Median rounded min | Median wall min | Failed / cancelled |
| --- | --- | --- | --- | --- | --- | --- |
| Docs-only PR | 2026-10-03..09 (15) | 7 | 1.0 | 7 | 0.6 | 0 / 0 |
| Ordinary code PR | 2026-10-03..06 (16) | 9 | 1.9 | 9 | 0.8 | 0 / 0 |
| Risk PR | 2026-10-08..09 (20) | 13 | 10.2 | 19 | 6.2 | 1 (lint) / 5 |
| Main push, code | 2026-10-05..09 (20) | 17 | 19.3 | 29.5 | 6.6 | 0 / 4 |
| Weekly `ci.yml` schedule | 2026-10-05 (1) | 17 | 21.2 | 32 | 7.3 | 0 / 0 |
| Upstream pycubrid canary | 2026-08-10..10-08 (19) | 2 | 1.9 | 4 | 1.2 | 3 canary jobs (drift, reported) / 0 |
| Release (`publish-pypi.yml` with `integration-full.yml`) | 2026-10-04..09 (2) | 35 | 82.4 | 103.5 | 14.2 | 1 (cookbook verification) / 0 |
| `integration-full.yml` dispatch | 2026-09-27..10-08 (8) | 24 | 73.4 | 85.5 | 8.0 | 0 / 0 |

Over the 72 code pushes to `main` from 2026-10-01 to 2026-10-09 (a "code push" is
a `main` push run where `offline-tests` or `typecheck` ran; 84 pushes in total),
47 succeeded, 9 failed and 16 were cancelled. Each failure (all on 2026-10-03) was `offline-tests`
together with `sqlalchemy-21-canary` on the same run; `live-smoke`, `make-integration` and `integration-tests` never failed on
a push. All 9 failures of `sqlalchemy-21-canary` in every non-PR `ci.yml` run from
2026-09-25 to 2026-10-09 (all attempts), all on 2026-10-03, coincided with an
`offline-tests (3.12)` failure, so the canary added no independent signal on pushes.

Median per-job runner minutes on code pushes: `integration-tests` 5.3 per cell,
`make integration` 2.1, `repo-tests` 1.6, `live-smoke` 1.3, `offline-tests` 0.7–0.8
per cell, `sqlalchemy-21-canary` 0.6, packaging 0.5, `alembic-compat` 0.5,
typecheck 0.4, lint 0.4. The advisory CUBRIDdb compliance step of the oldest
`integration-tests` cell takes a median 34 s.

### Coverage ownership

| Coverage | Owner (workflow / job) | Event tier |
| --- | --- | --- |
| Offline suite, 95% floor | `ci.yml` `offline-tests`; `integration-full.yml` `offline-endpoints` | PR: Python 3.12. Main push, weekly, dispatch: 3.11 and 3.15. Release: 3.11 and 3.15 |
| Type checking | `ci.yml` `typecheck` (Python 3.13, SQLAlchemy 2.1.1); `integration-full.yml` `typecheck` (same cell) | Every code event; dispatch and release |
| Alembic compatibility | `ci.yml` `alembic-compat` (latest Alembic); `integration-full.yml` `alembic-compat` (same cell); offline Alembic tests in `offline-tests`; live Alembic operations in `integration-tests`, `make-integration` and `integration-full`; transactional DDL in `integration-tests` and `integration-full` | Risk PR and non-PR code; dispatch and release |
| Packaging | `ci.yml` `packaging-smoke-test`; `integration-full.yml` `packaging-smoke-test` (same steps, including the pycubrid extra and Alembic checks); `publish-pypi.yml` `build` | Risk PR and non-PR code; dispatch and release |
| Representative live smoke | `ci.yml` `make-integration` (pycubrid, CUBRID 11.4, Python 3.12), which absorbed `live-smoke` | Main push, weekly, dispatch |
| `make integration` | `ci.yml` `make-integration`; `integration-full.yml` `make-integration` (both drivers, CUBRID 10.2 and 11.4) | Non-PR code; dispatch and release |
| CUBRID/Python endpoints | `ci.yml` `integration-tests` (3.14/11.4 on risk PRs, plus 3.11/10.2 on non-PR code); `integration-full.yml` `integration-full` (5 × 4) | Risk PR, non-PR code; dispatch and release |
| SQLAlchemy dialect compliance (gating) | `ci.yml` `integration-tests`: CUBRIDdb lane on 3.14/11.4, released-pycubrid lane on both cells; `integration-full.yml` `sqlalchemy-compliance` (the same lanes on the same two cells) | Risk PR (3.14/11.4), non-PR code (both cells); dispatch and release (both cells) |
| SQLAlchemy compliance, CUBRIDdb on the oldest cell (advisory) | `ci.yml` `integration-tests` (3.11/10.2) | Weekly runs with code changes in the previous 7 days, and code dispatches |
| SQLAlchemy pre-release canary (advisory) | `ci.yml` `sqlalchemy-21-canary` | Weekly schedule and dispatch |
| pycubrid upstream canary (advisory, reported) | `upstream-canary.yml` | Thursday 06:00 UTC and dispatch |
| Driver differential | `ci.yml` `integration-tests`; `integration-full.yml` `integration-full` | Risk PR, non-PR code; dispatch and release |
| CUBRID version differential | `integration-full.yml` `version-differential` | Dispatch and release |
| Fuzz and metamorphic | `dev` profile inside `make integration`; `nightly` profile in `integration-full.yml` `fuzz-bug-hunt` | Non-PR code; dispatch and release |
| Mutation testing (non-gating) | `integration-full.yml` `mutation-testing` | Dispatch only; skipped on the release call (#747) |

### Consolidation

- `live-smoke` is removed from `ci.yml`. It ran `test/test_integration.py` and
  `test/test_regression.py` with Python 3.12, CUBRID 11.4 and
  `cubrid+pycubrid://`. Both files are `integration`-marked, so `make-integration`
  on the same SHA runs every one of those tests with the same Python, server
  version and URL, in an environment that installs a superset of the packages
  (`.[pycubrid]` plus the `dev` dependency group, which includes Alembic) and with the stricter
  `check_not_all_skipped` guard. No assertion is lost. The removed job installed
  only `.[pycubrid,alembic] pytest`, without the dev tooling, while `make-integration`
  uses `.[pycubrid]` plus the `dev` group; `packaging-smoke-test` covers importing the package in a
  minimal install but not running the smoke tests without dev-only packages. This
  trade-off is accepted. `integration-tests` is
  kept: its CUBRIDdb lanes, compliance suites, driver differential,
  transactional DDL and server-restart steps are unique.
- `sqlalchemy-21-canary` runs on the weekly schedule and manual dispatches only,
  whatever changed, and stays `continue-on-error`. It watches upstream
  SQLAlchemy pre-releases, which change independently of this repository's
  commits, and in the sample it never added a failure that `offline-tests` did
  not already report.
- The advisory CUBRIDdb compliance step of the oldest `integration-tests` cell
  (Python 3.11, CUBRID 10.2) runs inside `integration-tests`, which requires code
  changes, so only on weekly runs with code changes in the previous 7 days and on
  code dispatches.
  It is `continue-on-error`, so it never gated a push; the gating
  released-pycubrid compliance lane of the same cell still runs on every code
  push.
- `upstream-canary.yml` moves from Monday 06:00 UTC to Thursday 06:00 UTC so it no
  longer stacks on the Monday `ci.yml` schedule. Its jobs differ from the weekly
  `ci.yml` suites (they install `pycubrid@main`), so both stay.
- Pull requests are unchanged: ordinary PRs still run one Python 3.12 offline
  cell and no live lane, and #734's 3.11/3.15 cells stay off PRs.

Expected runner minutes, computed from the per-job medians above:

| Category | Jobs before → after | Runner min before → after | Rounded min before → after |
| --- | --- | --- | --- |
| Ordinary code PR | 9 → 9 | 1.9 → 1.9 | 9 → 9 |
| Risk PR | 13 → 13 | 10.2 → 10.2 | 19 → 19 |
| Main push, code | 17 → 15 | 19.3 → about 16.8 | 29.5 → about 26 |
| Weekly `ci.yml` schedule | 17 → 16 | 21.2 → about 19.8 | 32 → about 30 |
| Upstream pycubrid canary | 2 → 2 | 1.9 → 1.9 | 4 → 4 |
| Release | 35 → 37 | 82.4 → about 83.9 | 103.5 → about 105.5 |

A weekly run without code changes now spends about 0.8 runner minutes on the
SQLAlchemy canary, which previously did not run. These are expectations, not
measurements; compare the next weeks of Actions data before claiming a saving.

### Release evidence

The release commit is a `main` commit, and its `ci.yml` push run used to be the
only source of the Python 3.11/3.14 offline evidence (#734). Nothing in the
release path required that run to succeed, and a later merge could cancel it
through the push concurrency group. `integration-full.yml` now runs the same two
cells as `offline-endpoints` at the exact release SHA, and `full-matrix-result`
fails unless they succeed. This repeats about 1.5 runner minutes per release.
Requiring the push run instead would have needed a polling job (which holds a
runner for at least as long), `actions: read` on the release workflow, which is
kept identical across cubrid-lab repositories, and non-cancelling push runs,
which would have finished the 16 cancelled runs measured above.

The same reasoning now covers the rest of the `main` push evidence (#737,
option b). `integration-full.yml` also runs copies of `ci.yml` `typecheck`,
`alembic-compat` and `packaging-smoke-test` (including its pycubrid-extra and
Alembic checks), and an `sqlalchemy-compliance` job with the gating CUBRIDdb lane
on Python 3.14/CUBRID 11.4 and the gating released-pycubrid lane on both
3.14/11.4 and 3.11/10.2, each pinned to the SQLAlchemy version its
`test/known_failures.txt` baseline was captured with. They check out the release
SHA, are not selected by changed paths, and run on every `integration-full.yml`
run (manual dispatch and the release call). `full-matrix-result` lists them in
`needs` and fails unless each one succeeds, so a failed, cancelled or skipped
lane blocks `publish-pypi.yml`, whose `build` and `publish` jobs need the called
workflow. The advisory CUBRIDdb compliance lane of the oldest cell gates nothing
and is not repeated. `publish-pypi.yml` is unchanged: it is kept identical across
cubrid-lab repositories, which ruled out option (a) (`actions: read` and a
required `ci.yml` push run). The copies add three short jobs (about 1.4 runner
minutes from the medians above) and two live compliance cells per release;
`test/test_ci_policy.py` keeps their steps equal to the `ci.yml` sources.

### Release commit push

A release commit is pushed to `main` once, and two workflows start on that SHA:
`ci.yml`'s push run and `publish-pypi.yml`, whose `matrix` job calls
`integration-full.yml`. The release call already runs every runtime lane of a
`main` push: the Python 3.11/3.15 offline cells, type checking, `alembic-compat`,
the packaging smoke test, `make integration` (both drivers, CUBRID 10.2 and 11.4),
the gating compliance lanes and all 20 Python × CUBRID cells, behind the
fail-closed `full-matrix-result`. Measured on the three release commits in the
sample (1.9.0, 1.10.0, 1.11.0), the push run spent 15.0 to 19.5 runner minutes
repeating that work (14.1 runner minutes and 18 rounded minutes in 8 jobs on
1.11.0, the first release after the consolidation).

`ci.yml`'s `detect-changes` therefore runs `scripts/release_detect.py --mode push`
on push events to `main`, the same script, mode and SHA that `publish-pypi.yml`'s
`detect` job uses. When it selects a release (`build=true`), the `code`, `live` and
`extended` outputs are false, so `typecheck`, `offline-tests`, `alembic-compat`,
`packaging-smoke-test`, `integration-tests` and `make-integration` are
intentionally unselected and `matrix-result` accepts their skips. Lint,
documentation lint, the site build and repository-tooling tests still follow
their own selection. A failed detection fails `detect-changes` and with it the
required gate, so a release push is never reported green by accident.

The two `integration-tests` steps that `integration-full.yml` did not run, "Run
pycubrid sync integration tests" and "Run regression tests", now also run in its
Python 3.11/CUBRID 10.2 and Python 3.14/CUBRID 11.4 cells, with the same commands
and URLs (the 3.11 row already pins SQLAlchemy 2.0, as the oldest `ci.yml` cell
does). They took a median 42 seconds and 1 second per cell on `main` pushes, so
the release gains about 1.4 runner minutes while each release commit's push run
drops about 14 runner minutes. `test/test_ci_policy.py` keeps the copied steps
equal to the `ci.yml` source and their cells equal to its push matrix.

Release verification stays fail-closed and complete: nothing is published unless
`full-matrix-result` succeeds, and a release that fails or is never published
leaves the version unreleased. The release commit only changes the version,
`CHANGELOG.md` and release metadata, and the release PR ran the PR tier before
the merge. Ordinary pushes, the weekly schedule and manual dispatches are
unchanged.

### Measured after the consolidation

Measured with the same method on 2026-10-12 (`actions/runs` and `runs/{id}/jobs`,
all attempts, skipped jobs excluded). "Before" is 2026-10-03 to the merge of #760
(2026-10-09 03:19 UTC); for the release rows it is everything before #797
(2026-10-10 23:56 UTC). "After" runs until 2026-10-12. Samples are short, and
several other CI changes merged in the same days, noted below the table.

| Category | Before: window (runs) | Before: median runner / rounded min | After: window (runs) | After: median runner / rounded min | After: failed / cancelled |
| --- | --- | --- | --- | --- | --- |
| Docs-only PR | 2026-10-03..09 (15) | 1.0 / 7 | 2026-10-10..12 (29) | 1.0 / 8 | 1 / 2 |
| Ordinary code PR | 2026-10-03..06 (17) | 2.0 / 9 | 2026-10-09..12 (39) | 3.8 / 11 | 2 / 2 |
| Risk PR | 2026-10-03..09 (66) | 10.4 / 19 | 2026-10-09..12 (65) | 9.4 / 18 | 0 / 15 |
| Main push, code | 2026-10-03..09 (48) | 18.9 / 28.5 | 2026-10-09..12 (47) | 17.0 / 27 | 0 / 4 |
| Weekly `ci.yml` schedule | 2026-10-05 (1) | 21.2 / 32 | 2026-10-12 (1) | 18.8 / 29 | 0 / 0 |
| Upstream pycubrid canary | 2026-09-21..10-08 (13) | 2.0 / 4 | none yet (first Thursday run 2026-10-15) | not measured | not measured |
| Release (`publish-pypi.yml` push) | 2026-10-04, 10-09 (2) | 93.8 and 143.9 / 118 and 185 | 2026-10-12 (1) | 103.8 / 133 | 0 / 0 |
| Release rehearsal (`publish-pypi.yml` dry-run dispatch) | none | not measured | 2026-10-11 (5) | 92.8 / 118 | 0 / 0 |
| `integration-full.yml` dispatch | 2026-10-04..09 (8) | 73.4 / 85.5 | 2026-10-10..12 (11) | 82.1 / 102 | 0 / 1 |

- Main pushes dropped about 1.9 runner minutes at the median: `live-smoke` and the
  push-time SQLAlchemy canary are gone, and #734's second offline cell took back
  part of that. The weekly run dropped 2.4 runner minutes. Main-push failures fell
  from 9 to 0; cancelled runs are still superseded runs, as before.
- Ordinary code PRs rose because #742 (2026-10-08) runs the full offline suite on
  every PR and #786 builds the documentation site on PRs that touch it. Neither is
  part of this consolidation; both move failures from `main` to the PR.
- `integration-full.yml` rose from 24 to 35 jobs: #797 added the five release
  copies (about 5.2 runner minutes) and #807 (2026-10-11) added the Python 3.15
  row (four cells). The 10-09 release before includes re-run attempts.
- These are runner minutes on GitHub-hosted runners of a public repository, not
  billed charges. With this change, each future release commit also saves the
  push run's runtime lanes measured above (about 14 runner minutes), less about
  1.4 runner minutes added to the release.

## Offline Python endpoints

The `offline-tests` matrix is chosen by `github.event_name` (#734). Pull requests,
ordinary and high-risk alike, run one representative Python 3.12 cell. Every other
`ci.yml` event (a push to `main`, the Monday schedule and a manual
`workflow_dispatch`) runs the oldest and newest supported Python, 3.11 and 3.15,
instead of 3.12. The supported range between them is covered by those endpoints
plus the 3.12 PR evidence; 3.13 and 3.14 have no routine offline cell (3.14 is
still exercised live on every high-risk PR and in the full matrix). Both kinds of run use
the same selection (`-m "not integration and not repo"`), the 95% coverage floor
and the `detect-changes` `code` output: a docs-only push, or a week without code
changes, selects no offline cell at all. A `workflow_dispatch` on `main` has no
previous push to compare with, so `paths-filter` selects cells from its last commit
only: dispatching right after a docs-only merge runs no offline cell. Each cell uploads its own
`coverage-report-py<version>` artifact, so the cells do not collide on one name.

| Event | `offline-tests` cells |
| --- | --- |
| `pull_request` | Python 3.12 |
| `push` to `main`, `schedule`, `workflow_dispatch` | Python 3.11 and 3.15 |

The matrix uses `fail-fast: false`, so one failing interpreter does not cancel the
other's evidence. `matrix-result` reads the job's aggregate result: any failed or
cancelled cell makes it non-success, and a skip while `code` is selected is
unexpected; each fails the required gate. Compared with the former single 3.12
cell, a code push or weekly run adds one offline job of about the same length
(the job budget is 15 minutes); pull requests are unchanged. `integration-full.yml`
runs the same two cells as `offline-endpoints` at the release SHA, and
`full-matrix-result` requires them (#737; see
[Release evidence](#release-evidence)). The
repository-tooling lane stays on the representative Python 3.12 cell.
`test/test_ci_policy.py` renders the matrix for each event and runs the gate
against failed, cancelled and skipped offline results.

## Workflow change impact

Changed-path selection follows a per-workflow impact table (#746). Only `ci.yml`
selects the live PR lanes (`integration-tests`, `alembic-compat`, packaging) through
`risk`, because it defines and runs them. Every other workflow under `.github/` is a
non-documentation change, so it runs the full offline suite, and it selects the
repository-tooling lane; together they cover every test that reads a workflow file.
The live lanes of `ci.yml` do not execute another workflow's jobs, so running them
adds no detection.

| Changed workflow | PR validation |
| --- | --- |
| `ci.yml` | All lanes it defines, plus tooling and the offline suite |
| `integration-full.yml`, `upstream-canary.yml`, `python-canary.yml` | Tooling and offline suite, plus a manual `workflow_dispatch` of that workflow on the PR head, linked in the PR |
| `publish-pypi.yml`, `release-please.yml` | Tooling and offline suite (release workflow tests) |
| Other workflows | Tooling and offline suite; `pr-title.yml`, `docs-sync.yml`, `codeql.yml` and `security.yml` also run themselves on the PR |

`test/test_workflow_path_impact.py` evaluates the filters against every workflow
file and representative paths, and fails if any test module that reads a workflow
file (by literal path, split path or constant) contains an `integration` mark,
which would leave that test unrun on such a PR.

## Parallel live lanes

`integration-tests` and `make-integration` depend only on
`detect-changes` (#744), so they start alongside lint, type checking and offline
tests instead of after them. `matrix-result` still needs every job, so a lint, type
or offline failure keeps the required check red even when the live lanes pass. The
trade-off is that a PR that fails lint can still spend live-lane runner time.

## CUBRIDdb driver build cache

The CUBRIDdb lanes build cubrid-python v11.3.0.51 into a wheel and cache it (#745).
The wheel links CCI statically (`libcascci.a`) and needs only libc and libstdc++,
so the cache key is the runner OS and architecture, the runner image (`ImageOS`),
the Python ABI (`SOABI`, for example `cpython-314-x86_64-linux-gnu`) and the
resolved source commit, never just the tag. The CUBRID server version is not part
of the key, so the server cells of one Python version share a wheel. On a hit the
CCI compile and the `build-essential`/`cmake` install are skipped; on a miss the
wheel is built with `uv build` and saved when the job succeeds. The key uses the ABI
rather than the patch release because CPython keeps the ABI stable within a minor
version, while runner images ship different patch releases. A change to the build
recipe or toolchain needs a manual bump of the `cubriddb-wheel-v` prefix, and the
three copies of the recipe must stay identical. A hit is never treated as evidence: every
run installs the wheel, imports `CUBRIDdb`, and the readiness step connects to the
live server before any suite runs. `test/test_workflow_cubriddb_cache.py` enforces
the key components and that the build is skipped only on a hit.

## Job timeouts

Every executing job sets an integer `timeout-minutes` (GitHub's default is 360
minutes), so a hung container, socket, driver build or install fails within its
budget instead of holding a runner for six hours (#741). Budgets are roughly 3–5×
the observed maximum Actions duration with a floor: 5 minutes for gates and small
jobs, 10–15 for lint/type/offline/Alembic/canary jobs, 20 for `make integration`
and the upstream canary integration job, 30 for the live integration matrix
(observed maximum 7.1, including the CUBRIDdb source build and compliance suites)
and 60 for mutation testing (observed maximum 18.1). No job needs an exception
above the 180-minute cap. Aggregate gates (`matrix-result`, `full-matrix-result`)
run with `if: always()` and a short timeout; a timed-out dependency reports a
non-success result (`cancelled`/`failure`), which the gate treats as a failure.

Jobs that call a reusable workflow cannot set `timeout-minutes`. Repo-local
callees (`publish-pypi.yml` → `integration-full.yml`) are covered through their
own jobs. The externally owned callees are an explicit allowlist in
`test/test_workflow_timeouts.py`: the shared `doc-lint`, `live-smoke` (used by
the fuzz bug hunt in `integration-full.yml`) and `codeql` workflows in `cubrid-lab/.github`, and the
cookbook smoke test. That test parses every workflow and fails when an executing
job lacks a bounded timeout, when a new external caller is not allowlisted, or
when the release gate (`full-matrix-result`) stops failing on a non-success
dependency; `matrix-result` is covered by `test/test_ci_policy.py`.

## Docs tooling, scan concurrency and the pycubrid floor

- **Pinned docs tools (#761).** `docs.yml` and the `docs-build` job of `ci.yml`
  (see below) run `mkdocs build --strict`; `docs.yml` installs `mkdocs`, `mkdocs-material` and
  `pymdown-extensions` from `.github/docs-requirements/requirements.txt`, which
  pins exact versions. A dedicated Dependabot `pip` entry for
  `/.github/docs-requirements` proposes updates, so an upstream release cannot
  break the strict build without a repository change.
- **Documentation site build on pull requests (#786).** `ci.yml` builds the site
  before merge, so a docs edit or a docs-tool pin bump that breaks
  `mkdocs build --strict` fails on the pull request instead of later on `main`. The
  `docs-build` job is selected by the `site` path filter: `docs/**` (content,
  translations and assets), `mkdocs.yml`, `scripts/generate_llms_full.py`,
  the MkDocs hook `scripts/docs_provenance_hook.py`, `.github/docs-requirements/**`, `.github/workflows/docs.yml` and
  `.github/workflows/ci.yml`. Root `*.md` files are not site inputs, so they do not
  select it, and `workflow_dispatch` forces it like the other lanes. The job runs the
  `docs.yml` build steps (install from `.github/docs-requirements/requirements.txt`
  with the pinned uv, `scripts/generate_llms_full.py`, `mkdocs build --strict`) with
  read-only permissions, pinned actions, a 10-minute timeout and
  `persist-credentials: false`; it never uploads a Pages artifact or deploys. The
  `matrix-result` gate expects `docs-build` to succeed exactly when `site` is selected
  and accepts a skip otherwise. `test/test_ci_policy.py`,
  `test/test_workflow_path_impact.py` and `test/test_workflow_hygiene.py` enforce this.
- **Deterministic documentation gate (#908).** The `docs-check` job runs
  `scripts/check_docs_links.py` and `scripts/check_agents_docs.py` on every tracked
  Markdown file. It is selected by the `docs` filter (`**/*.md`, `docs/**`) or the
  `tooling` filter (`scripts/**`, `Makefile`, ...), because a removed script or make
  target strands the documents that name it. It fails, printing `file:line` and a
  suggested fix when one is close, on:
  - a relative Markdown or HTML (`<img src>`, `<a href>`, `<source src>`) link target that is missing,
    absolute or outside the repository;
  - an `#anchor` that is not a heading (its GitHub or site slug, or `{#id}`) or an
    `<a id>`/`<a name>` of the target file;
  - a reference link `[text][label]` without a definition, and an unclosed code fence;
  - a paragraph line under `docs/` that starts with `#` and a digit, such as a wrapped issue
    number, also as a list item or in a block quote: the MkDocs site renders it as a
    heading (#920), so write `\#750`;
  - a `make` goal written in inline code or a fenced block that the Makefile does not
    define, and a `scripts/` path that does not exist. Release history (`CHANGELOG.md`,
    `RELEASE_CHANGELOG.md`) keeps the commands of its time, so only its links are checked.

  Markdown is parsed as CommonMark (`markdown-it-py`, pinned in
  `.github/docs-requirements/requirements.txt`), so links in code are examples; brackets in
  a URL, a title or an HTML comment are not references; and quoted text and redirections
  are not make goals. A reviewed false positive is marked with
  `<!-- docs-check: ignore -->` on the reported line or the line before it. The job never
  opens a network connection, and the check takes about one second. The `matrix-result`
  gate expects `docs-check` to succeed exactly when either filter is selected and accepts
  a skip otherwise, so a docs-only pull request still skips the CUBRID runtime lanes.
  `scripts/check_support_claims.py` remains the authority for support wording; `docs-check`
  makes no support claim. The shared `doc-lint` workflow stays advisory
  (`fail-on-issue: false`), for these reasons on the #918 head (2026-10-15): markdownlint
  reported 2,207 style findings, 1,530 of them table style (MD060); the Mermaid scan reported
  none; and lychee exited on its `--exclude-mail` argument without checking a link. Setting
  `fail-on-issue: true` would gate the style findings and still check no link.
  `test/test_check_docs_links.py` holds the passing and failing fixtures.
- **Scan concurrency (#762).** `codeql.yml` and `security.yml` set
  `concurrency` with group `${{ github.workflow }}-${{ github.event_name == 'pull_request' && github.ref || github.run_id }}` and
  `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`: a new push
  cancels the superseded scan on a pull request, while every other event gets a
  unique per-run group (GitHub replaces a pending run within one group even
  without `cancel-in-progress`), so main pushes and the weekly schedule are
  never cancelled or dropped. Scan coverage is unchanged.
- **Declared pycubrid floor (#764).** `pyproject.toml` declares
  `pycubrid>=1.8.0,<2.0`; the gating compliance lane in `ci.yml` installs
  `pycubrid==1.8.0`, the only lane that exercises the floor (the integration
  jobs install the latest release). `test/test_workflow_hygiene.py` fails when
  the pinned version and the declared floor differ, so raising one without the
  other is caught offline without an extra CI job. The cub_server restart step
  that runs after it, last in the job, upgrades back to the latest release
  (`--upgrade-package pycubrid`; a plain reinstall keeps 1.8.0) so it tests the
  same pycubrid as the other integration steps; `test/test_ci_policy.py` pins
  this (#479).
- **Wording (#747).** `integration-full.yml` has no schedule. The
  `fuzz-bug-hunt` and `mutation-testing` job names no longer say "nightly"
  (`nightly` remains the name of the Hypothesis profile). Gating is unchanged:
  fuzz gates the release, mutation testing is non-gating. No required status
  check refers to these job names.
- **Mutation testing off the release path (#747).** `publish-pypi.yml` calls
  `integration-full.yml` and its `build` job waits for the whole called
  workflow, so the non-gating `mutation-testing` job delayed every release by
  its run time (historical median 9.6, maximum 18.1 minutes) without being able
  to block it. The job now has `if: ${{ !inputs.sha }}`: a release call always
  passes the required `sha` input and skips it, while a direct manual dispatch
  of `integration-full.yml` (no inputs) still runs it and reports the score.
  The path is chosen by that explicit input, not by `github.event_name`, which
  in a called workflow is the caller's event (`push` or `workflow_dispatch`)
  and so cannot tell a release call from a manual run. The Hypothesis fuzz
  pass keeps gating the release unchanged. `full-matrix-result` never needed
  the mutation job, so a skipped run can neither fail the gate nor count as a
  pass of a required job. `publish-pypi.yml` is unchanged (it stays identical
  to the canonical copy). `test/test_ci_policy.py` pins the condition, that no
  job waits on mutation testing, and that fuzz still runs on the release call.

## Dependency installation

`ci.yml`, `integration-full.yml` and `upstream-canary.yml` install dependencies with
uv (#743): each job that installs packages runs `astral-sh/setup-uv` pinned to a
commit SHA, with uv itself pinned (`version: "0.12.17"`), after `actions/setup-python`.
It then installs with `uv pip install --system` into that interpreter and logs the
result with `uv pip freeze --system`. setup-uv receives the same `python-version` spec
as setup-python (for example `"3.12"` or the matrix value), so its cache key carries
the job's Python minor version rather than the patch release `uv python find` would
report, which differs between runner images and would make the key miss. With the
`pyproject.toml` hash and a per-job `cache-suffix`, each job and Python version keeps
its own cache. The same input exports `UV_PYTHON`, and `uv pip install --system`
picks the first matching interpreter on `PATH`, which is setup-python's. Routine CI and the
canary always cache (`enable-cache: true`); `integration-full.yml` uses `auto`, which
disables caching only for tag pushes, `release`, `pull_request_target` and
`workflow_run` events. The release path (`publish-pypi.yml` on a `main` push, or its
recovery dispatch) therefore still restores caches. That is safe because a uv cache
holds only downloaded and built wheels: every run re-resolves from the same
constraints, so a cache can speed an install but cannot change the resolved versions.
Only the installer changes: before the switch, `.[dev]`, `.[dev,alembic]` and
`.[dev,pycubrid]` on Python 3.12 resolved to identical package sets with pip and uv
(73, 73 and 74 packages after PEP 503 name normalization). The pinned SQLAlchemy
and pycubrid compliance installs keep their exact pins, and the SQLAlchemy
pre-release canary uses `--upgrade-package SQLAlchemy --prerelease=if-necessary-or-explicit`, which requests an SQLAlchemy-only upgrade. This resolver flag does not guarantee that the newest available SQLAlchemy pre-release is selected: a compatible stable 2.1.x release may still win over a 2.2 beta. Issue #778 tracks verifying the resolved version against a real published 2.2 pre-release; the canary must not be cited as evidence of 2.2 coverage until that check succeeds. The oldest cell's SQLAlchemy 2.0 pin step logs the pinned version. Plain `pip` stays where it is the
point: the packaging smoke venvs prove the built wheel and sdist install with the
end-user tool, and the external `live-smoke` reusable workflow receives its own
install command. `test/test_workflow_installs.py` enforces this.

## Dependabot grouping

Dependabot used to open one PR per package for pip (`/`), pip
(`/.github/docs-requirements`) and GitHub Actions, and each one ran the PR tier.
`.github/dependabot.yml` now groups minor and patch version updates into one PR per
ecosystem and directory (`dev-tools`, `docs-tools`, `github-actions`), so a weekly
batch costs one CI run per group (#737). These stay in their own PRs:

- **Major updates** are excluded from every group (`update-types` is only `minor` and
  `patch`), and `dependabot-auto-merge.yml` still holds them for human review.
- **Security updates** stay separate: the groups set `applies-to: version-updates`.
- **SQLAlchemy, pycubrid, Alembic and CUBRID-Python** are excluded from `dev-tools`.
  Their compatibility risk differs from that of a tool bump, so each update stays
  independently reviewable.

Grouping does not bypass anything. A grouped PR runs the same required checks, and
auto-merge completes only after they pass. `dependabot/fetch-metadata` reports the
highest semver change of a grouped PR as its `update-type`, so a group can never carry
a major update into auto-merge. One failing package blocks the whole group: fix it in
the group PR, or, if it needs separate work, add it to the group's `exclude-patterns`
through a reviewed PR so Dependabot opens it on its own.
`test/test_workflow_hygiene.py` enforces the group settings.

The first grouped weekly run on 2026-10-10 opened one PR, #793 ("bump the
github-actions group with 2 updates"), for `actions/upload-artifact` and
`actions/download-artifact` across four workflows; on 2026-09-21 the same two actions had needed two PRs
(#451, #452). It passed the required checks before it merged. The SHA bumps of the
pinned cookbook smoke-test workflow (#794, #809) are commit updates, not minor or
patch version updates, so the group does not match them and they still open their
own PRs.

## Python 3.15 validation preparation

`python-canary.yml` is manual-only: supply the full SHA and dispatch the branch
at that commit. One Ubuntu/standard-GIL lane selects Python 3.15 (prereleases
are allowed by the selector), prints the actual interpreter/dependency versions, runs full offline
regressions and validates fresh wheel/sdist installs. Failed setup/install/tests
fail the run normally. It is separate from required PR checks and release gates;
there is no new schedule, PR matrix cell or CUBRID provisioning. This lane alone
does not establish official support, live database or free-threaded compatibility.

GitHub dispatches a manual workflow only after its file is on the default
branch, so the lane cannot run before it is merged. Its first run is made at
the merged commit and recorded on the tracking issue; ordinary PR CI is not
Python 3.15 evidence.

Python 3.15 is now supported (#666; see the [support matrix](SUPPORT_MATRIX.md)).
Its support evidence comes from the full compatibility matrix (Python 3.15 × four
CUBRID versions, with the CUBRIDdb and pycubrid lanes), the 3.15 offline endpoint
cells and this lane's fresh wheel/sdist installs; the lane is kept as a manual
packaging check. The representative live cells stay on Python 3.14/CUBRID 11.4 and
Python 3.11/CUBRID 10.2, and the SQLAlchemy compliance lanes stay on those two
cells.
