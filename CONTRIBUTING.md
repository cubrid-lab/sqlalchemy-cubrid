# Contributing to sqlalchemy-cubrid

Thank you for your interest in contributing! This document provides guidelines
and instructions for contributing to the project.

## Table of Contents

- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Docker Integration Testing](#docker-integration-testing)
- [Code Style](#code-style)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Pull request and commit titles](#pull-request-and-commit-titles)
- [Releases](#releases)
- [Reporting Issues](#reporting-issues)

---

## Development Setup

### Prerequisites

- Python 3.10 or later
- Git
- Docker (for integration tests)

### Installation

```bash
# Clone the repository
git clone https://github.com/cubrid-lab/sqlalchemy-cubrid.git
cd sqlalchemy-cubrid

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Install test coverage tool
pip install pytest-cov

# Install pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install
```

---

## Running Tests

### Offline Tests (No Database Required)

Most tests run without a CUBRID instance:

```bash
# Run the fast offline tests (what you want while iterating)
make test

# Run the repository-tooling tests (Makefile recipes, signal handling, repo scripts)
make test-repo

# Run every offline test (both of the above)
make test-offline

# Run shared lint, strict typing and security checks
make check-all

# Run a specific test file
pytest test/test_compiler.py -v

# Run a specific test
pytest test/test_compiler.py::TestCubridSQLCompiler::test_select_limit -v
```

`make test` selects `-m "not integration and not repo"`. The `repo` marker is
applied by `test/conftest.py` to every test in the modules listed in
`REPO_TOOLING_MODULES` (`test_make_integration.py`, `test_docs_reason.py`,
`test_release_detect.py`): they run the Makefile and repository scripts through
subprocesses and took most of the offline run's time (#594). They are still
required: CI runs them in the `repo-tests` job on every pull request. Run
`make test-repo` before pushing a change to the `Makefile`, `scripts/` or those
tests. A new module that tests repository tooling rather than the dialect
belongs in `REPO_TOOLING_MODULES`.

### Integration Tests (Requires CUBRID)

```bash
# Start a CUBRID container
docker compose up -d

# Set the connection URL
export CUBRID_TEST_URL="cubrid+pycubrid://dba@localhost:33000/testdb"

# Run the regular pure-driver profile with sync/async connection preflight
tox -e integration

# Stop the container when done
docker compose down
```

`CUBRID_TEST_URL` decides whether integration tests run. Unset, they skip (and a
`CI=true` run that selects them exits 1). Set, the server behind it must answer
`SELECT 1` through the URL's driver, or every integration test errors with one
message naming the URL without its password, instead of silently skipping
(#593). Unset it, or use `-m "not integration"`, to skip them on purpose. See
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#skip-or-fail-cubrid_test_url-is-the-switch).

### Multi-Python Testing with tox

```bash
pip install tox
tox           # Run all environments
tox -e py312  # Run a specific Python version
tox -e lint   # Run lint checks only
```

### Coverage Target

We maintain **≥ 95% code coverage**. The CI pipeline enforces this threshold.

---

## Docker Integration Testing

A `docker-compose.yml` is provided for local development:

```bash
# Start CUBRID (default version: 11.2)
docker compose up -d

# Test against a specific CUBRID version
CUBRID_VERSION=11.4 docker compose up -d

# View logs
docker compose logs -f cubrid

# Stop and remove
docker compose down -v
```

Supported CUBRID versions: `11.4`, `11.2`, `11.0`, `10.2`.

`make integration` does not use this default stack. It starts its own uniquely
named Compose project, refuses to run if that project already has containers,
volumes or networks, and removes only what it created (`docker compose -p
<project> down -v`), also after Ctrl-C, `SIGTERM` or `SIGHUP`. Use `make integration CUBRID_PORT=<port>` if port 33000 is
taken. It waits until the server answers through the selected driver and then runs
the whole integration suite with pycubrid (`cubrid+pycubrid://`); use
`make integration INTEGRATION_DRIVER=cubriddb` to run it through the CUBRIDdb C
extension (`cubrid://`). See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#quick-integration-workflow).

---

## Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

### Rules

- **Line length**: 100 characters
- **Target Python**: 3.10+
- **Formatter**: `ruff format`
- **Linter**: `ruff check`

### Running Checks

```bash
# Check synchronized tooling and every maintained Python source path
make lint

# Apply fixes and formatting over the same shared paths
make format

# Check strict typing, or run lint + typing + security together
make typecheck
make check-all
```

### Pre-commit Hooks

If you installed pre-commit hooks, these checks run automatically on `git commit`.
To run all hooks manually:

```bash
pre-commit run --all-files
```

---

## Pull Request Guidelines

### Before Submitting

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/my-feature main
   ```

2. **Write tests** for any new functionality. We require ≥ 95% coverage.

3. **Run the offline test suite** and ensure all tests pass:
   ```bash
   make test
   make test-repo   # when you touched the Makefile, scripts/ or their tests
   ```

4. **Run the shared lint, type and security checks**:
   ```bash
   make check-all
   ```

5. **Run integration tests** if your change affects database interaction:
   ```bash
   docker compose up -d
   export CUBRID_TEST_URL="cubrid+pycubrid://dba@localhost:33000/testdb"
   tox -e integration
   ```

### PR Content

- Keep PRs focused — one feature or fix per PR.
- Write a clear description explaining _what_ and _why_, and title the PR as
  described in [Pull request and commit titles](#pull-request-and-commit-titles).
- Reference related issues in the PR body (e.g., `Fixes #42`), not in the title.
- Update documentation if your change affects the public API.
- Update `CHANGELOG.md` with a summary of your change.

### Review Process

- All PRs require at least one review before merge.
- CI must pass (lint, offline tests, integration tests).
- Maintain backward compatibility unless explicitly approved.

Contributors install the dev extra, run the shared checks, update affected docs
and open a PR with motivation, commands/results and reasons for checks not run.
For documentation changes, run `python scripts/generate_llms_full.py` (it regenerates
`docs/llms-full.txt` and copies the canonical `docs/llms.txt` index to the root
`llms.txt`; edit only `docs/llms.txt`) and, in a
docs environment with `mkdocs-material` and `pymdown-extensions`, `mkdocs build --strict`.
Maintainers coordinate project-specific Oracle/Codex reviews, final integration,
release classification, repository secrets and GitHub labels. No particular agent
installation, repository-secret access or named coauthor is required to contribute.
Preserve actual authorship; separate AI review notes from executed test evidence.
Use English for GitHub issues, pull requests and comments; localized documentation contributions remain welcome.

Update matching behavior documentation. If none is needed, use a populated
standalone physical source line `Docs: not needed - <reason>` rather than leaving the placeholder;
the explanation must contain visible text. Empty emphasized link captions such as
`[**<!-- empty -->**](/issue)` or `[**![](/img)**](/issue)` do not supply a reason,
while `[**tests only**](/issue)` does. The `docs-not-needed` label remains
maintainer-controlled. For translation help,
state missing languages and a reason in the PR body. That is a request, not
permission: only explicit maintainer approval via the existing
`translations-deferred` label defers the translation gate, with follow-up recorded.
Korean-required and other-language advisory checks remain unchanged.

Reusable workflow updates use reviewed upstream commit SHAs. Verify the target
file and `workflow_call` inputs at that commit, update the related callers together,
and validate through a PR. The pinned doc-lint job still downloads its configured
main-based assets; pinning the caller does not freeze those assets.

---

## Pull request and commit titles

This rule covers issue titles, pull request titles and commit subjects in every
cubrid-lab repository. Pull requests are squash-merged and the pull request
title becomes the commit title on `main`, so the pull request title is the one
that must be right. The `PR title` check enforces it.

```text
type: description
type(scope): description
type!: description
type(scope)!: description
```

- **type** (lowercase, exactly one of): `feat`, `fix`, `docs`, `test`, `perf`,
  `refactor`, `ci`, `build`, `chore`, `style`, `revert`.
- **scope** is optional: lowercase letters, digits, `-` or `_`, such as
  `compiler`, `aio`, `deps` or `release`.
- **`!`** before the colon marks a breaking change. Follow the repository's
  release policy for breaking changes as well.
- Exactly **one space** after the colon.
- **description**: English and specific (name the function, type or behavior
  that changed). Start with a lowercase letter unless the first word is an API
  name, acronym or proper noun. No trailing period.
- No bracket, status or priority prefixes (`[Bug]`, `[WIP]`, `Track:`,
  `epic:`, `P1`). Open a draft pull request for unfinished work; priority and
  size are labels.
- No issue or pull request numbers in the title. Put `Closes #123` or
  `Refs #123` in the pull request body. GitHub appends the pull request
  number, for example `(#456)`, to the squash commit by itself.

| Type | Use for |
|------|---------|
| `feat` | A new user-facing capability |
| `fix` | Corrects wrong behavior, including security fixes |
| `docs` | Documentation only |
| `test` | Tests only |
| `perf` | Faster or lighter with no behavior change |
| `refactor` | Restructuring with no behavior change |
| `ci` | CI workflows and their configuration |
| `build` | Packaging and the build system |
| `chore` | Maintenance: releases, dependency bumps, housekeeping |
| `style` | Formatting only |
| `revert` | Reverts an earlier change; name it in the description |

Examples:

```text
fix(protocol): keep the CAS session after OUT_TRAN
feat(aio): add a charset connection option
docs: document JSON as_numeric() input limits
chore(deps): bump ruff from 0.16.8 to 0.16.9
chore: release v1.9.0
refactor(compiler)!: drop legacy LIMIT rendering
```

Issue forms prefill a type prefix; keep it and write the rest of the title the
same way. A tracking issue (epic) uses the type of the work it tracks.

Maintainers merge with **squash merge only** and keep the pull request title as
the commit title. Branch commits are squashed into the commit body, so keep
their messages meaningful and keep any `Co-authored-by:` trailers intact.

---

## Releases

Contributors never release. Add user-visible changes under `## [Unreleased]` in
`CHANGELOG.md`, and do not change `__version__` or add a dated `## [X.Y.Z]`
section in an ordinary PR: a merged version change is what starts an automatic
release. Maintainers open release PRs with `prepare-release.yml`; see
[`RELEASING.md`](RELEASING.md).

---

## Reporting Issues

Search for an existing issue first, then use the closest issue form. Keep its
prefilled title prefix (`fix:`, `feat:`, or `chore:`); for a custom issue, use
the same `type(scope): description` format as pull request titles (see
[Pull request and commit titles](#pull-request-and-commit-titles)), for example
`fix(reflection): ...` or `docs: ...`.

Reporters describe impact and reproduction; they do **not** need permission
to apply GitHub labels. Maintainers assign a type label, one
`priority: <value>` and one `size: <value>` label (plus `area:` when relevant).
Topical labels such as `testing` may also be present.
Human-submitted CLI/API issues with incomplete metadata receive
`status: needs triage`. The maintainer corrects the metadata and removes
that label. Workflows creating issues with `GITHUB_TOKEN` must set the title
and labels themselves: GitHub does not start another workflow from that event.

When reporting a bug, please include:

- Python version (`python --version`)
- SQLAlchemy version (`pip show sqlalchemy`)
- CUBRID server version
- CUBRID-Python driver version
- Minimal reproduction code
- Full traceback

For feature requests, describe the use case and expected behavior.

Report urgency and approximate scope even if you cannot edit labels. Maintainers
or triagers assign the required canonical priority/size labels; contributors do
not need label-write access.

---

## Questions?

Open a [GitHub Discussion](https://github.com/cubrid-lab/sqlalchemy-cubrid/discussions)
or file an [issue](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues).

## Minimum PR validation

Follow the [CI execution policy](docs/CI_POLICY.md). PR smoke is representative,
not full-suite/coverage evidence. Run relevant regression tests locally and report
commands/results; request exact-head full validation where compatibility requires it.
