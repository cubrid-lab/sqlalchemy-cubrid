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
gh run watch "$(gh run list --workflow publish-pypi.yml --limit 1 --json databaseId -q '.[0].databaseId')"
```

The workflow re-verifies tag == `__version__`, the dated CHANGELOG entry, that
the tag is contained in `main`, and the successful full matrix; it then builds,
smoke-tests the wheel and sdist, and publishes via Trusted Publisher (OIDC)
behind the `pypi` environment.

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
  error): re-dispatch `publish-pypi.yml -f tag=vX.Y.Z`.
