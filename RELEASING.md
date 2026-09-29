# Releasing sqlalchemy-cubrid

This is the single, maintainer-only release procedure for `sqlalchemy-cubrid`. It is kept
identical (except for package names) with the sibling cubrid-lab repositories.
Contributors never tag or publish; they ship changes through normal PRs.

Key invariants:

- The version is single-sourced from `sqlalchemy_cubrid/__init__.py` (`__version__`).
- `CHANGELOG.md` is the only source of release notes.
- The `vX.Y.Z` tag is created **on the squash-merged commit on `main`**, never
  on a local commit.
- PyPI publishing is a **manual** `workflow_dispatch` of `publish-pypi.yml`.
  Creating the GitHub Release does not publish anything.

## 1. Release PR

On a branch from up-to-date `main`:

1. Bump `__version__` in `sqlalchemy_cubrid/__init__.py` to `X.Y.Z`.
2. In `CHANGELOG.md`, move the `## [Unreleased]` entries under a new dated
   heading directly below an empty `## [Unreleased]`:

   ```markdown
   ## [Unreleased]

   ## [X.Y.Z] - YYYY-MM-DD

   ### Upgrade notes
   (optional: behavior changes users may notice)

   ### Added
   ...
   ```

3. Run the read-only local gate (it never commits or tags):

   ```bash
   make release-check VERSION=X.Y.Z
   ```

   It verifies that `__version__` (read via AST, no import) equals `X.Y.Z`,
   runs `scripts/lint_changelog.py`, checks that
   `scripts/extract_release_notes.py vX.Y.Z` finds a dated, non-empty section,
   then rebuilds `dist/` with `python -m build` and runs `twine check`.
   `build` and `twine` come from the `dev` extra (`pip install -e ".[dev]"`).

4. Open the PR (`chore: release vX.Y.Z`), get CI green, and **squash-merge** it.

## 2. Tag the merged commit

```bash
git fetch origin
MERGED_SHA=$(gh pr view <release-PR-number> --json mergeCommit -q .mergeCommit.oid)
git merge-base --is-ancestor "$MERGED_SHA" origin/main && git show --stat "$MERGED_SHA"
git tag -a vX.Y.Z "$MERGED_SHA" -m "sqlalchemy-cubrid vX.Y.Z"
git push origin refs/tags/vX.Y.Z
```

Push only the tag. Never push `main` directly and never tag a local commit.

## 3. Wait for tag-triggered workflows

The tag push starts two workflows. Both must be green before publishing:

- `integration-full.yml` runs the full Python × CUBRID compatibility matrix on
  the tagged commit. `publish-pypi.yml` refuses to publish without a successful
  tag-triggered run on that exact commit.
- `create-release.yml` verifies the tag is on `main`, extracts the CHANGELOG
  section, creates the GitHub Release `vX.Y.Z`, and attaches an SPDX SBOM.

```bash
gh run list --workflow integration-full.yml --event push --limit 3
gh run list --workflow create-release.yml --limit 3
```

## 4. Publish to PyPI (manual gate)

```bash
gh workflow run publish-pypi.yml -f tag=vX.Y.Z
# Identify the run you just dispatched (newest workflow_dispatch run, started
# by you a moment ago) and watch that exact run ID, failing on failure:
gh run list --workflow publish-pypi.yml --event workflow_dispatch --limit 5
gh run watch <run-id> --exit-status
```

The workflow re-verifies tag == `__version__`, the dated CHANGELOG entry, that
the tag is contained in `main`, the successful full matrix, and that the GitHub
Release for the tag exists with its SBOM (so `create-release.yml` must have
succeeded); it then builds,
smoke-tests the wheel and sdist, and publishes via Trusted Publisher (OIDC)
behind the `pypi` environment. The upload fails closed on duplicates: see the
partial-upload recovery under **Recovery**.

Verify the published package from a clean environment:

```bash
python -m venv /tmp/verify-sqlalchemy-cubrid && /tmp/verify-sqlalchemy-cubrid/bin/pip install "sqlalchemy-cubrid==X.Y.Z"
/tmp/verify-sqlalchemy-cubrid/bin/python -c "import sqlalchemy_cubrid; print(sqlalchemy_cubrid.__version__)"
```

## 5. Cookbook smoke test

After a successful publish, the `notify-cookbook` job in `publish-pypi.yml`
sends an `upstream-released` repository dispatch to
`cubrid-lab/cubrid-cookbook-python`. If the `COOKBOOK_DISPATCH_TOKEN` secret is
not configured, the job emits a warning and skips; trigger the smoke test
manually instead:

```bash
gh workflow run smoke-test.yml -R cubrid-lab/cubrid-cookbook-python
```

## Recovery

- **Failure before PyPI publish** (integration-full, create-release, or the
  publish verify job failed): nothing is on PyPI yet, so the version can be
  reused. Delete the Release and the tag, fix the problem through a PR, and
  redo the release with the same version:

  ```bash
  gh release delete vX.Y.Z --yes
  git push origin :refs/tags/vX.Y.Z
  git tag -d vX.Y.Z
  ```

- **Broken release after PyPI publish**: PyPI versions are immutable. Yank the
  broken version on PyPI (project settings → Releases → Yank) and ship a new
  patch release `X.Y.(Z+1)` through this same procedure. Never re-tag or
  delete a published version.

- **`create-release.yml` failed transiently, or the Release body must be
  refreshed from CHANGELOG**: re-run it via dispatch. Without
  `update_existing` the run fails if the existing body differs, so pass
  `-f update_existing=true` to refresh it:

  ```bash
  gh workflow run create-release.yml -f tag=vX.Y.Z                           # create a missing Release
  gh workflow run create-release.yml -f tag=vX.Y.Z -f update_existing=true   # refresh a differing body
  ```

- **Publish job failed after the checks passed** (for example a transient PyPI
  error, or an upload that stopped after the wheel but before the sdist): rerun
  only the failed jobs of the **same** run. The rerun reuses that run's
  verified build artifact and workflow commit instead of rebuilding:

  ```bash
  gh run list --workflow publish-pypi.yml --limit 5
  gh run rerun <run-id> --failed
  ```

  The publish step does not use `skip-existing`. Before it,
  `scripts/pypi_duplicate_guard.py` reads
  `https://pypi.org/pypi/<project>/X.Y.Z/json` and compares the SHA-256 of each
  file in the verified `dist/` with the file PyPI serves under the same name:

  - not on PyPI (or no such release yet, HTTP 404): uploaded;
  - on PyPI with the same SHA-256 (the earlier attempt uploaded it): removed
    from the upload set and logged. When every file is already on PyPI the
    upload step is skipped, and `notify-cookbook` still dispatches the smoke
    test, because PyPI provably serves this run's verified build;
  - on PyPI with a different SHA-256, PyPI serves a file for this version that
    the verified build did not produce, or PyPI cannot be queried (network
    error, an HTTP status other than 404, an unexpected response): the job
    fails and nothing is uploaded.

  The build is not bit-for-bit reproducible, so never dispatch a new
  `publish-pypi.yml` run (or rerun all jobs) to finish a partial upload: the
  rebuilt files differ from the ones already on PyPI and the guard fails on the
  hash mismatch, by design. The verified artifact is kept for one day; once it
  has expired, or if the guard reports a mismatch, the version cannot be
  completed. Handle it as a broken release (above): yank it on PyPI if needed
  and ship `X.Y.(Z+1)`. Transient PyPI errors during the check (HTTP 5xx,
  connection errors, timeouts) are retried a few times before the guard fails;
  only a real HTTP 404 counts as "not published". If PyPI's JSON API lags right
  after an upload and does not list a file yet, that file goes to the upload
  step, which is still safe: PyPI accepts a byte-identical re-upload of an
  existing filename and rejects different bytes (`400 File already exists`).
  So when the upload step fails after the guard passed, it is a real error,
  not lag: a `File already exists` rejection means PyPI holds different bytes
  for that filename (handle it as a broken release); for any other error, read
  the log before rerunning `--failed`.

- **`notify-cookbook` job failed** (for example `COOKBOOK_DISPATCH_TOKEN` is
  missing or the dispatch errored): the package is already on PyPI, so never
  re-dispatch `publish-pypi.yml`. Run the manual cookbook smoke test dispatch
  from step 5 instead:

  ```bash
  gh workflow run smoke-test.yml -R cubrid-lab/cubrid-cookbook-python
  ```
