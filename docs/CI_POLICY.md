# CI execution policy

Routine CI uses representative combinations instead of a Cartesian version/OS matrix.

| Trigger | Runtime validation |
| --- | --- |
| Documentation-only PR | Documentation and policy checks; no runtime suite or CUBRID provisioning |
| Ordinary code PR | One Ubuntu/Python 3.12 offline smoke lane; no full coverage claim |
| High-risk PR | Same offline smoke plus Python 3.14/CUBRID 11.4; targeted additional lanes where relevant |
| Code push to main | One Ubuntu/Python 3.12 full offline suite with the existing 95% coverage floor; oldest/newest live endpoints |
| Monday 03:00 UTC | Same representative policy, comparing changes in the previous seven days; unchanged/docs-only history does not select runtime tests |
| Explicit full dispatch or release | Existing full Python 3.10–3.14 × CUBRID 10.2/11.0/11.2/11.4 integration workflow and mandatory release lanes |

The PR smoke suite is deliberately bounded. Contributors must run the regression
checks relevant to their change locally and record commands/results in the PR.
Passing smoke is not evidence that the whole offline suite or coverage floor ran.
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
