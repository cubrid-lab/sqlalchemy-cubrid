# CI execution policy

Routine CI uses representative combinations instead of a Cartesian version/OS matrix.

| Trigger | Runtime validation |
| --- | --- |
| Documentation-only PR | Documentation and policy checks; no runtime suite or CUBRID provisioning |
| Ordinary code PR | One Ubuntu/Python 3.12 full offline suite with the 95% coverage floor (#742) |
| High-risk PR | Same full offline suite plus Python 3.14/CUBRID 11.4; targeted additional lanes where relevant |
| Code push to main | Ubuntu full offline suite with the existing 95% coverage floor on the oldest and newest supported Python (3.11, 3.14) (#734); oldest/newest live endpoints |
| Monday 03:00 UTC | Same policy as a main push (including the Python 3.11/3.14 offline cells), comparing changes in the previous seven days; unchanged/docs-only history does not select runtime tests |
| Explicit full dispatch or release | Existing full Python 3.11–3.14 × CUBRID 10.2/11.0/11.2/11.4 integration workflow and mandatory release lanes |

PRs run the same full offline selection (`-m "not integration and not repo"`) and
95% coverage floor as pushes. The former three-file PR smoke ran in about 1 s
locally against about 24 s for the full suite, too small a saving to justify
letting offline regressions first fail on main (#742). Live integration on PRs
stays representative: contributors must run the regression checks relevant to
their change locally and record commands/results in the PR.
`make test` and `make integration` remain available without changing their scope.

Change selection is in `ci.yml`'s `detect-changes` job. Non-documentation paths
are code by default, so new source/configuration files do not silently become docs.
Connection/protocol/cursor/async/compatibility or dialect/compiler/reflection,
dependency, build and script changes and `ci.yml` itself select representative
pre-merge integration; other workflow changes select the tooling lane and the
offline suite instead (see
[Workflow change impact](#workflow-change-impact)). Repository tooling tests run in one Linux lane when tooling changes.
The static lint job continues on all events, including generated documentation checks.

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
and packaging uses SQLAlchemy 2.1.1. The oldest/newest live endpoint cells retain
SQLAlchemy 2.0 and 2.1 compliance coverage on main/weekly. Live smoke, make integration
and the advisory SQLAlchemy canary are deferred from PRs to non-PR code validation.

## Offline Python endpoints

The `offline-tests` matrix is chosen by `github.event_name` (#734). Pull requests,
ordinary and high-risk alike, run one representative Python 3.12 cell. Every other
`ci.yml` event (a push to `main`, the Monday schedule and a manual
`workflow_dispatch`) runs the oldest and newest supported Python, 3.11 and 3.14,
instead of 3.12. The supported range between them is covered by those endpoints
plus the 3.12 PR evidence; 3.13 has no routine offline cell. Both kinds of run use
the same selection (`-m "not integration and not repo"`), the 95% coverage floor
and the `detect-changes` `code` output: a docs-only push, or a week without code
changes, selects no offline cell at all. A `workflow_dispatch` on `main` has no
previous push to compare with, so `paths-filter` selects cells from its last commit
only: dispatching right after a docs-only merge runs no offline cell. Each cell uploads its own
`coverage-report-py<version>` artifact, so the cells do not collide on one name.

| Event | `offline-tests` cells |
| --- | --- |
| `pull_request` | Python 3.12 |
| `push` to `main`, `schedule`, `workflow_dispatch` | Python 3.11 and 3.14 |

The matrix uses `fail-fast: false`, so one failing interpreter does not cancel the
other's evidence. `matrix-result` reads the job's aggregate result: any failed or
cancelled cell makes it non-success, and a skip while `code` is selected is
unexpected; each fails the required gate. Compared with the former single 3.12
cell, a code push or weekly run adds one offline job of about the same length
(the job budget is 15 minutes); pull requests are unchanged. `integration-full.yml`
gains no offline cells: the release commit is a `main` commit whose push run
normally carries the endpoint evidence, which avoids repeating it. Nothing in
the release path enforces that run's success yet, and a later merge can cancel it
through the push concurrency group; #737 tracks closing that gap. The
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

`integration-tests`, `make-integration` and `live-smoke` depend only on
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
`test/test_workflow_timeouts.py`: the shared `doc-lint`, `live-smoke` (also used
by the fuzz bug hunt) and `codeql` workflows in `cubrid-lab/.github`, and the
cookbook smoke test. That test parses every workflow and fails when an executing
job lacks a bounded timeout, when a new external caller is not allowlisted, or
when the release gate (`full-matrix-result`) stops failing on a non-success
dependency; `matrix-result` is covered by `test/test_ci_policy.py`.

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
pre-release canary uses `--upgrade-package SQLAlchemy --prerelease=if-necessary-or-explicit`, which keeps pip's upgrade scope (only SQLAlchemy, not its dependencies) and admits a pre-release only where the specifier asks for one. The oldest cell's SQLAlchemy 2.0 pin step logs the pinned version. Plain `pip` stays where it is the
point: the packaging smoke venvs prove the built wheel and sdist install with the
end-user tool, and the external `live-smoke` reusable workflow receives its own
install command. `test/test_workflow_installs.py` enforces this.

## Python 3.15 preview preparation

`python-canary.yml` is manual-only: supply the full SHA and dispatch the branch
at that commit. One Ubuntu/standard-GIL lane selects Python 3.15 with prereleases
allowed, prints the actual interpreter/dependency versions, runs full offline
regressions and validates fresh wheel/sdist installs. Failed setup/install/tests
fail the run normally. It is separate from required PR checks and release gates;
there is no new schedule, PR matrix cell or CUBRID provisioning. This lane alone
does not establish official support, live database or free-threaded compatibility.

GitHub dispatches a manual workflow only after its file is on the default
branch, so the lane cannot run before it is merged. Its first run is made at
the merged commit and recorded on the tracking issue; ordinary PR CI is not
Python 3.15 evidence.
