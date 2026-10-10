# Releasing sqlalchemy-cubrid

Merging a reviewed release PR is the only normal way to release `sqlalchemy-cubrid`.
Nobody pushes tags or runs a publish workflow by hand, and ordinary PR merges
never deploy. This procedure is kept identical (except for package names and
version files) with the sibling cubrid-lab repositories.

Key invariants:

- The version is single-sourced from `sqlalchemy_cubrid/__init__.py` (`__version__`).
- `RELEASE_CHANGELOG.md` contains generated Conventional Commit entries.
  `CHANGELOG.md` combines them with reviewed Upgrade notes and remains the
  publication source; historical sections are preserved byte for byte.
- A release is decided from git facts on `main`, never from a PR title.
- The workflows never delete PyPI files, never move a tag and never create a
  version that was not merged through a release PR.
- A GitHub Release title is exactly its tag `vX.Y.Z`, drafts included. Release
  notes use the standard `###` sections. Both rules, and the handling of stale
  drafts, are in the "GitHub Release Policy" section of [`AGENTS.md`](AGENTS.md).

## Normal flow

`release-please.yml` → reviewed release PR → squash merge → `publish-pypi.yml`.

### 1. Prepare the release PR

On each push to `main`, or a manual `release-please.yml` dispatch from `main`,
the SHA-pinned upstream action prepares a Python release PR. It never creates
tags or GitHub Releases (`skip-github-release: true`). The former
`prepare-release.yml` entry point is removed; `prepare_release.py` remains only
as tested legacy transformation code, without an active workflow caller.

Before proposing another release, the preparer reconciles merged
`autorelease: pending` PRs only when their manifest version, tag commit,
published non-draft GitHub Release and a successful `publish-pypi.yml` run at the
merge SHA all agree. That run must include successful publication and cookbook
verification jobs. It then transitions pending to `autorelease: tagged`.
Partial publication remains pending and blocks the next release, and turns
**Prepare release** red; see [When preparation is blocked](#when-preparation-is-blocked).
Recovery runs at another head SHA require a maintainer to verify the same facts and perform
the label transition manually; no release is repeated to clear labels.

The root manifest starts at `1.8.0`, bootstrapped from published `v1.8.0` commit
`78bcbc7dbd70d8f2c756b25d3c271977ace42aa5`. Tags retain `vX.Y.Z`, without a
component prefix. The Python strategy updates `sqlalchemy_cubrid/__init__.py`;
`pyproject.toml` continues to read its version dynamically.

`always-update: true` ensures curated-only main changes and failed composition
retries return a candidate for composition, even if generated notes are unchanged.
The action writes Conventional Commit entries to `RELEASE_CHANGELOG.md`.
`changelog-sections` in `release-please-config.json` maps commit types to the
standard headings: `feat` → Added, `fix` → Fixed, `perf` → Performance,
`docs` → Documentation, `deps`/`revert` → Changed; `ci` → CI, `test` → Tests and
`refactor`/`chore`/`build`/`style` → Changed are hidden, as before, so they still
create no candidate on their own and appear only with a breaking change.
`compose_release_changelog.py` uses the same unchanged main SHA's curated
`[Unreleased]` entries, merges the candidate's generated notes into the same
standard `###` headings in the standard order (curated entries first,
release-please's `⚠ BREAKING CHANGES` under Upgrade notes), and creates the
canonical dated header required by the existing publisher, so the candidate
passes `scripts/lint_changelog.py`. It preserves released history and one empty
Unreleased section. An unknown generated or curated heading fails closed.
Stale main runs fail before generation and before pushing composed notes. The
candidate must pass `make release-check VERSION=X.Y.Z`.

### 2. Review, freeze and validate the release PR

- Check the proposed version, manifest, package metadata, notes and generated
  change classification. Upstream Python defaults are: `fix` patch, `feat`
  minor, breaking changes major, `docs` and `perf` patch, and hidden `chore`,
  `ci`, `test` or `refactor` alone no PR.
  A reviewed Conventional Commit footer `Release-As: X.Y.Z` overrides the next
  version; review compatibility before merging it. Do not edit the manifest
  alone or assume generation constitutes release approval.
- Before editing the release branch, apply **`autorelease: review`** to its PR.
  Wait for any running preparation workflow to finish; then edit. This freezes
  regeneration before the upstream action and before the composed-note push.
  The generated date is copied from the candidate header, so composition is
  deterministic for identical inputs. Leave the freeze label through merge.
- Curated notes added to main's Unreleased section survive subsequent
  regeneration. Edits made only on the candidate branch require the freeze
  label. Removing that label permits upstream regeneration and may overwrite
  those branch-only edits; first move essential text to main if needed.
- The workflow uses `GITHUB_TOKEN`; bot-created or updated PRs do **not**
  automatically start normal PR CI. After preparation completes, a maintainer
  closes/reopens the PR or pushes a commit, then verifies checks cover the
  final composed head. No new PAT or contributor secret is required.
- Run `make release-check VERSION=X.Y.Z` again after manual edits. Require
  all normal PR checks before squash-merging; the merged version change
  starts the existing guarded publisher, regardless of PR title.

### 3. Squash merge

Merge only the reviewed, fully validated release PR. Version selection is
release-please's proposal; maintainer approval remains the publication decision.

### 4. Automatic release (`publish-pypi.yml`)

Every push to `main` runs the cheap **detect** job
(`scripts/release_detect.py`). It is a release only when all of these hold at
the pushed commit:

1. `__version__` differs from the first parent,
2. the version is `MAJOR.MINOR.PATCH` and `CHANGELOG.md` has a dated
   `## [X.Y.Z] - YYYY-MM-DD` section,
3. tag `vX.Y.Z` does not exist, or already points at this commit (resume).

Otherwise the run ends with **"no release"** (an ordinary merge shows
`__version__ unchanged (…) compared with the first parent`). A version change
without a dated section, or with a tag at another commit, also ends as "no
release" and adds a warning annotation.

For a release, the jobs run in one workflow run, pinned to the merge commit SHA
and chained with explicit `needs:` (tags and Releases created with
`GITHUB_TOKEN` start no other workflow):

| Job | What it does |
| --- | --- |
| `consistency` | `make release-check VERSION=X.Y.Z` at the SHA: `__version__`, CHANGELOG lint and dated section, `build` + `twine check`. |
| `matrix` | The full Python × CUBRID matrix, the `make integration` lanes for both drivers, the Python 3.11/3.14 offline cells, the release-run copies of the `ci.yml` type check, `alembic-compat`, packaging smoke test and gating SQLAlchemy compliance lanes (#737), the version-differential and the Hypothesis fuzz pass (mutation testing is reported but non-gating): `integration-full.yml` called through `workflow_call` at the SHA. Its `full-matrix-result` job fails unless every required lane succeeds. |
| `build` | Builds the wheel and sdist **once**, `twine check`, wheel/sdist install smoke tests, extracts the release notes (the CHANGELOG section byte for byte plus one `**Full Changelog**` link to the previous CHANGELOG version; none for the first release or when the section already has a compare link), generates the SPDX SBOM and records SHA-256 hashes. Artifacts `release-dist` and `release-meta` are kept for 14 days. |
| `publish` | In the `pypi` environment: re-checks the hashes, creates the annotated tag `vX.Y.Z` at the SHA (or accepts one already there), creates a **draft** GitHub Release titled exactly `vX.Y.Z` with the notes and `sbom.spdx.json` (an existing Release found on resume must already carry that title, or the job fails closed; it is never renamed), uploads the same artifact to PyPI through `scripts/pypi_duplicate_guard.py` and Trusted Publishing (OIDC), then publishes the Release. |
| `verify-cookbook` | Calls the cookbook smoke test (`smoke-test.yml` of cubrid-cookbook-python) as a **reusable workflow** with `package=sqlalchemy-cubrid`, `version=X.Y.Z` and a `request_id`; its jobs run inside this release run. |
| `require-cookbook` | Fails unless the called workflow succeeded and its outputs report `status == success` with `installed_version == requested_version == X.Y.Z`. |
| `summary` | Always runs; one table with SHA, tag, version, artifact hashes, matrix result, PyPI and Release URLs, cookbook run and the final state. |

Only `publish` has write access (`contents: write` for the tag and Release,
`id-token: write` for PyPI); every other job reads.

#### Cookbook verification

`verify-cookbook` uses the release verification contract of
[cubrid-cookbook-python](https://github.com/cubrid-lab/cubrid-cookbook-python/blob/main/CONTRIBUTING.md)
("Calling the smoke test from a release workflow"):

```yaml
uses: cubrid-lab/cubrid-cookbook-python/.github/workflows/smoke-test.yml@<40-hex cookbook main commit> # main
with:
  package: sqlalchemy-cubrid
  version: X.Y.Z
  request_id: sqlalchemy-cubrid-vX.Y.Z-<run id>-<run attempt>
```

The cookbook jobs (`Cookbook release verification / Smoke Tests (CUBRID 11.2)`,
`… (CUBRID 11.4)`, `Cookbook release verification / Smoke Tests (CUBRID 11.4, Python 3.11)`
and `… / Release verification report`) run as jobs of the
release run with its own `GITHUB_TOKEN`: the calling job grants only
`contents: read`, and **no token, secret or polling** is involved. They install
exactly `sqlalchemy-cubrid==X.Y.Z` from PyPI (with a bounded retry for publication
delay, never a fallback to the latest release) and upload the report artifact
`release-verification-<request_id>` to the release run. The called workflow's
outputs `status`, `requested_version`, `installed_version` and `artifact` are
checked by `require-cookbook` and shown in the summary. A failed or cancelled
called workflow is a failed verification.

The verification now waits up to 10 minutes for PyPI to serve the exact version before installing, and reports what PyPI served if it times out.

The release verification report needs all three cells (CUBRID 11.2 / Python 3.12,
CUBRID 11.4 / Python 3.12 and CUBRID 11.4 / Python 3.11) to succeed; a missing or
failed cell fails the report and therefore the verification.

The pin is a full commit SHA of the cookbook's `main` branch. Dependabot
(`github-actions` ecosystem) updates it: the cookbook's version tags do not
contain the pinned commit, so Dependabot proposes the newest `main` commit.
To bump it by hand, replace the SHA with the current
`gh api repos/cubrid-lab/cubrid-cookbook-python/commits/main --jq .sha` and keep
the `# main` comment.

#### Final states in the summary

| Final state | Meaning |
| --- | --- |
| `no release: …` | Ordinary push; nothing ran after `detect`. |
| `failed before publish in <job> …` | `consistency`, `matrix` or `build` failed. No tag, no Release, no upload. |
| `publish failure; … may be partial` | Failed inside `publish`; see recovery below. |
| `published and verified` | Done. |
| `published; post-release verification failed` | On PyPI, but the called cookbook workflow failed or was cancelled, or its outputs do not report `status == success` with `installed_version == X.Y.Z`. |
| `dry run …` / `verification only …` | Recovery dispatch results (below). |

## Failure and recovery

| Situation | What happened | What to do |
| --- | --- | --- |
| `detect` says "no release" on a release merge | Version unchanged, CHANGELOG section not dated, or the tag exists at another commit (see the warning). | `detect` only releases the commit that changes `__version__`, so a follow-up PR that only fixes the CHANGELOG cannot release `X.Y.Z`. Fix the cause through a normal PR, then prepare `X.Y.(Z+1)` and fold the `## [X.Y.Z]` entries into its section (if the tag is at another commit, that version is taken anyway). |
| `consistency`, `matrix` or `build` failed | Nothing published; no tag, no Release. | Transient (flaky lane, runner error): `gh run rerun <run-id> --failed`. Real defect at that commit: `X.Y.Z` stays unpublished. Fix it in a normal PR (no version change, so no release), unblock preparation (see "A merged `X.Y.Z` is abandoned" below), then prepare `X.Y.(Z+1)`; in that release PR fold the unpublished `## [X.Y.Z]` entries into the new section. A skipped version number on PyPI is harmless. |
| A merged `X.Y.Z` is abandoned (it will not be published) | The merged release PR stays `autorelease: pending`, so reconciliation reports it as blocked (or release-please aborts while it is still in progress) and no newer candidate can be prepared. | Record on the release PR why `X.Y.Z` is abandoned, then remove `autorelease: pending` from it. Do **not** add `autorelease: tagged`: nothing was published. Merge the fix, then dispatch **Prepare release**. The next version is computed from the commits after the `X.Y.Z` merge (normally `X.Y.(Z+1)`; a `feat` gives `X.(Y+1).0`, and hidden types alone open no candidate). In that release PR fold the unpublished `## [X.Y.Z]` entries into the new section. |
| `publish` failed (tag/Release/PyPI error, partial upload) | The tag and a draft Release may exist; PyPI may hold some files. | `gh run rerun <run-id> --failed` of the **same** run. It reuses the verified artifact, accepts the tag at the same SHA, reuses the draft Release, and the duplicate guard drops files PyPI already serves byte for byte. |
| `publish` fails with `the title must be exactly 'vX.Y.Z'` | The existing Release for the tag (draft or published) has another title. | Fix only the title by hand, keeping notes, assets, published and prerelease state; for a draft, resend `tag_name` (`gh api -X PATCH repos/cubrid-lab/sqlalchemy-cubrid/releases/<id> -f name=vX.Y.Z -f tag_name=vX.Y.Z`). Then rerun. Never delete or recreate the Release or the tag. |
| release-please preparation fails with `unsupported generated section` | The composer met a generated heading outside the standard list, for example from a breaking commit of a type that `changelog-sections` does not map (`foo!:`). | Add the commit type to `changelog-sections` in `release-please-config.json` with a standard section (hidden if it should not create a release by itself) through a reviewed PR, then regenerate. |
| Same version rebuilt (new run instead of rerun) | The rebuild's bytes differ from files already on PyPI. | The guard fails on the hash mismatch, by design. Use `rerun --failed` within the 14-day artifact retention; otherwise treat it as a broken release. |
| `verify-cookbook` or `require-cookbook` failed | **Published**; the cookbook verification failed, was cancelled or did not start. | Fix the cause. If the cookbook call itself (`verify-cookbook`) failed or was cancelled, `gh run rerun <run-id> --failed` re-runs it with a new `request_id` (a new run attempt). If the call succeeded but `require-cookbook` rejected its outputs, `--failed` only re-runs that gate against the same outputs; in that case, or if the call never started, use the `verify-only` dispatch below, which requests a new cookbook run. Never republish. |
| Broken release on PyPI | Versions are immutable. | Yank it on PyPI (project settings → Releases → Yank) and release `X.Y.(Z+1)` through a new release PR. Never delete a version or move a tag. |

The duplicate guard (`scripts/pypi_duplicate_guard.py`) reads
`https://pypi.org/pypi/sqlalchemy-cubrid/X.Y.Z/json` and compares each file in the
verified `dist/` with the file PyPI serves under the same name: not on PyPI
(HTTP 404) → uploaded; same SHA-256 → skipped; different SHA-256, a PyPI file
the build did not produce, or PyPI unreachable → the job fails and nothing is
uploaded. Only an explicit "every file already on PyPI" skips the upload step.
If PyPI's JSON API lags right after an upload and does not list a file yet,
that file goes to the upload step, which is still safe: PyPI answers a
byte-identical re-upload of an existing filename with success and rejects
different bytes with `400 File already exists`. Before treating that rejection
as a broken release, re-query `https://pypi.org/pypi/sqlalchemy-cubrid/X.Y.Z/json` and
compare the published SHA-256 with the run's `SHA256SUMS` (artifact
`release-meta`): a match means the file is fine and `gh run rerun --failed`
completes the release; a mismatch is a broken release.

### When preparation is blocked

While a merged release PR stays `autorelease: pending`, upstream release-please
only logs "There are untagged, merged release PRs outstanding - aborting" and
opens no new release PR. To keep that from passing silently,
`reconcile_release_labels.py` (the **Reconcile completed external releases** step
of **Prepare release**, which runs before release-please) classifies every
pending PR it could not mark tagged, using the `publish-pypi.yml` runs at the
merge SHA:

| State | When | Prepare release run |
| --- | --- | --- |
| In progress | Any publisher run at that SHA is queued, waiting or in progress (including a re-run of an older run), or the merge is under 2 hours old (`PUBLISHER_START_GRACE`) and no run exists yet. | `::notice::`, stays green. Dispatch preparation again after the publisher succeeds. |
| Blocked | All runs are completed and the newest concluded with anything other than `success`; it succeeded but the publication proof is missing; no run exists 2 hours or more after the merge; or the run state cannot be read. | `::error::` and a step-summary section with the PR number, merge SHA, run URL, conclusion and recovery; the run fails, so release-please is skipped (it would abort anyway). |

The error includes the `rerun-failed-jobs` command only for `failure`,
`cancelled` and `timed_out`; other conclusions (for example `action_required`)
need a look at the run first. For "succeeded but not proven", the proof read
itself may have failed transiently: if the run summary shows a complete
publication, re-run Prepare release. Every error ends with "If recovery ran as
a dispatch at another SHA, label the PR manually per RELEASING.md."

A red Prepare release run with "Release preparation is blocked" therefore
means: a release was merged, and its publication is not proven. To recover:

1. Open the run URL from the message and find the failed job; fix the cause
   (for example a cookbook or PyPI CDN lag).
2. For a failed, cancelled or timed-out run, re-run its failed jobs with
   `gh api -X POST repos/cubrid-lab/sqlalchemy-cubrid/actions/runs/<id>/rerun-failed-jobs`
   (the same as `gh run rerun <id> --failed`), or follow the matching row in
   [Failure and recovery](#failure-and-recovery) (`verify-only` dispatch,
   or abandoning `X.Y.Z` and preparing `X.Y.(Z+1)` for a real defect).
3. When the publisher run at the merge SHA is green, dispatch **Prepare
   release** again. Reconciliation marks the PR tagged and release-please opens
   the next candidate. If you abandoned `X.Y.Z` instead, skip this step: there
   is no green run to wait for and the PR must not be tagged; follow the
   abandoned-release row (remove `autorelease: pending`, merge the fix, then
   dispatch).

If no publisher run exists, check whether the push started `publish-pypi.yml`
and what `detect` decided. If recovery ran as a dispatch at another SHA
(`resume` or `verify-only` from the current `main` head), the run at the merge
SHA stays failed and the PR stays blocked: after verifying the release summary,
exact tag SHA, artifact hashes and cookbook success, label it manually (add
`autorelease: tagged`, then remove `autorelease: pending`).
The script never relabels a blocked PR, reruns or dispatches anything;
never clear `autorelease: pending` just to turn the run green; the only
exception is a deliberately abandoned version (see the recovery table above). The 1.10.0
release (PR #704) is the reference case: its publisher run
[37871732934](https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/runs/37871732934)
failed in cookbook verification after PyPI publication on attempt 1, and
preparation stayed silently green until its failed jobs were re-run.

### Recovery dispatch (the only manual entry point)

`publish-pypi.yml` has one `workflow_dispatch` with an `action` input. It never
creates a new version, never moves a tag and never deletes anything.

| `action` | Allowed when | Runs |
| --- | --- | --- |
| `resume` | Dispatched from `main`; tag `vX.Y.Z` exists; its commit is on `main`; `__version__` and a dated CHANGELOG section at that commit equal `X.Y.Z`. | consistency → matrix → build → publish → verify at the tag commit (the Hypothesis fuzz pass runs only when the tag commit is `main`'s head, because its shared workflow checks out the dispatched commit). For an interrupted release whose run can no longer be rerun (for example the artifacts expired before anything reached PyPI). A rebuilt file that differs from one already on PyPI fails the guard. |
| `verify-only` | Same conditions as `resume`. | Only `verify-cookbook`, `require-cookbook` and `summary` for the already-published version, through the same reusable cookbook workflow. |
| `dry-run` | Any branch; `X.Y.Z` must equal `__version__` at the dispatched commit and have a dated CHANGELOG section. | consistency → matrix → build → verify-cookbook → require-cookbook, **no** tag, Release or upload. The cookbook jobs verify the already-published `X.Y.Z`. |

```bash
gh workflow run publish-pypi.yml -f action=resume -f version=X.Y.Z
gh workflow run publish-pypi.yml -f action=verify-only -f version=X.Y.Z
gh workflow run publish-pypi.yml --ref <branch> -f action=dry-run -f version=X.Y.Z
```

### Dry-run evidence

Before dispatching, audit `gh run list -R cubrid-lab/sqlalchemy-cubrid --workflow=publish-pypi.yml`
for an existing `dry-run`/`resume`/`verify-only` run at the current
`publish-pypi.yml` revision (including `scripts/release_detect.py`,
`scripts/release_summary.py` and the other scripts the jobs check out from
the workflow's own commit): a run against an older revision of those scripts
does not cover code paths changed since. An ordinary push whose `detect`
finds "no release" proves detection only, not the full dry-run path below.

Last full dry run: [run 36862681247](https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/runs/36862681247),
dispatched `-f action=dry-run -f version=1.8.0` from `main` at commit
[`ae80955`](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/ae80955999da710bb9f62e68dd2394b7daeb5383)
(workflow file and scripts unchanged since
[`d27b414`](https://github.com/cubrid-lab/sqlalchemy-cubrid/commit/d27b414755f7b7247492225524a00288824255df),
#606). An earlier full dry run,
[run 36721019106](https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/runs/36721019106),
had passed at commit `5f1e07e`, but `scripts/release_summary.py` changed in
`d27b414` (#606) after that run, so it no longer covered the summary job's
current code; this run re-exercises the full path at the current revision.

Job conclusions for 36862681247: `detect` success (mode `dry-run`, tag
`v1.8.0` reported `different` — it already exists at the published commit,
untouched by this dry run), `consistency` success, `matrix` (full
compatibility matrix) success — the nightly, non-gating "Mutation testing"
lane failed as it also did on the prior evidence run, and does not affect
the matrix's own gating result, which succeeded — `build` success, `publish`
**skipped** (no tag, Release or PyPI upload — verified: nothing changed on
PyPI or in this repository's tags/Releases), `verify-cookbook` success,
`require-cookbook` success (installed `1.8.0` == requested `1.8.0`),
`summary` success with final state `dry run passed; nothing published;
cookbook verification success`.

Build artifact SHA-256 (built fresh by this run and uploaded only as the
14-day `release-dist` run artifact, never to PyPI; recorded here as
dry-run evidence):

```
ed8fd12ef6b8b1f4d2ad833eeca2d794bb29b6cb7a3232fd1669bbcdeb1fe74c  sqlalchemy_cubrid-1.8.0-py3-none-any.whl
09c065db710ab93720e65d329b6c38efa8a7b01977b9ae25d89ce1279632c9be  sqlalchemy_cubrid-1.8.0.tar.gz
```

**Limit:** the `build` job's own smoke tests do install the freshly built
wheel and sdist into clean virtual environments and check their imports,
metadata, entry points and the `py.typed` marker, so a passing dry run
proves the fresh artifacts install cleanly. What it does not prove is that
those fresh artifacts pass the cookbook suite: `verify-cookbook` on a
`dry-run` installs the already-published `sqlalchemy-cubrid==1.8.0` from
PyPI (the cookbook's release verification contract only ever installs from
PyPI), never the wheel this dry run just built. Only `publish` followed by
its own `verify-cookbook` verifies the newly built artifact through the
cookbook.

## Repository settings this relies on

- Squash merge only; the PR title becomes the commit title.
- Settings → Actions → General: "Allow GitHub Actions to create and approve
  pull requests" (for `release-please.yml`).
- Environment `pypi`: deployment branches limited to `main`; PyPI Trusted
  Publisher for `cubrid-lab/sqlalchemy-cubrid`, workflow `publish-pypi.yml`, environment
  `pypi` (<https://pypi.org/manage/project/sqlalchemy-cubrid/settings/publishing/>).
  The workflow filename is part of the publisher identity: renaming the file
  without changing the PyPI registration makes the upload fail with
  `invalid-publisher`, after the tag and the draft Release were created.
- No secret for the cookbook verification: the smoke test runs as a reusable
  workflow inside the release run.
- No tag protection rule that blocks `github-actions[bot]` from creating
  `v*` tags.

## Routine CI selection

The [CI execution policy](docs/CI_POLICY.md) reduces routine execution frequency
and representative matrix cells. This CI-only maintenance changes no runtime API,
supported-version declaration or release publisher; it does not require a MINOR
version by itself. Candidate releases still invoke the full compatibility workflow
at their immutable SHA before publication.
