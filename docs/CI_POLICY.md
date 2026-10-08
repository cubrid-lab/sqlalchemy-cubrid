# CI execution policy

Routine CI uses representative combinations instead of a Cartesian version/OS matrix.

| Trigger | Runtime validation |
| --- | --- |
| Documentation-only PR | Documentation and policy checks; no runtime suite or CUBRID provisioning |
| Ordinary code PR | One Ubuntu/Python 3.12 full offline suite with the 95% coverage floor (#742) |
| High-risk PR | Same full offline suite plus Python 3.14/CUBRID 11.4; targeted additional lanes where relevant |
| Code push to main | One Ubuntu/Python 3.12 full offline suite with the existing 95% coverage floor; oldest/newest live endpoints |
| Monday 03:00 UTC | Same representative policy, comparing changes in the previous seven days; unchanged/docs-only history does not select runtime tests |
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
dependency, build, script and workflow changes select representative pre-merge
integration. Repository tooling tests run in one Linux lane when tooling changes.
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
result with `uv pip freeze --system`. Because setup-uv runs after setup-python, its
cache key carries the job's interpreter; with the `pyproject.toml` hash and a per-job
`cache-suffix`, each job and Python version keeps its own cache. Routine CI and the
canary always cache (`enable-cache: true`); the release-gate `integration-full.yml`
uses `auto`, keeping setup-uv's guard against restoring caches on release-type events.
Only the installer changes: before the switch, `.[dev]`, `.[dev,alembic]` and
`.[dev,pycubrid]` on Python 3.12 resolved to identical package sets with pip and uv
(73, 73 and 74 packages after PEP 503 name normalization). The pinned SQLAlchemy
and pycubrid compliance installs keep their exact pins, and the SQLAlchemy
pre-release canary uses uv's `--prerelease=allow`. Plain `pip` stays where it is the
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
