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

- Python 3.11 or later
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

# Install in development mode with the dev dependency group (pip >= 25.1)
python -m pip install --upgrade "pip>=25.1"
pip install -e . --group dev

# Install pre-commit hooks
pre-commit install
```

---

## Running Tests

### Offline Tests (No Database Required)

Most tests run without a CUBRID instance:

```bash
# Run every offline test: the fast tests and the repository-tooling tests
make test

# Run only the fast offline tests (what you want while iterating)
make test-fast

# Run only the repository-tooling tests (Makefile targets, signal handling, repo scripts)
make test-repo

# Run the complete non-test quality gate: lint, format check, strict typing,
# security and the docs-reason checks
make check

# Full verification: make check, make test, then the live make integration lane (Docker)
make verify

# Run a specific test file
pytest test/test_compiler.py -v

# Run a specific test
pytest test/test_compiler.py::TestSelectCompilation::test_select_limit -v
```

`make test` also writes `junit.xml`, `coverage.xml` and `summary.json` to the gitignored
`test-results/test/` (see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)). It selects `-m "not integration"` (`make test-offline` is an alias kept
for compatibility); `make test-fast` selects `-m "not integration and not repo"`. The `repo` marker is
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
# Start CUBRID (default version: 11.2) on 127.0.0.1:33000
make docker-up                         # or: docker compose up -d

# Test against a specific CUBRID version
CUBRID_VERSION=11.4 make docker-up

# Publish the broker on another host port (the test URL must follow it)
CUBRID_TEST_PORT=33300 make docker-up

# View logs
docker compose logs -f cubrid

# Stop and remove the container, keeping the data volumes
make docker-down                       # docker compose down

# Stop and delete the data volumes (removes all test data)
make docker-clean                      # docker compose down -v
```

The broker is published on `127.0.0.1` only, on host port `CUBRID_TEST_PORT` (default
33000). `CUBRID_PORT`, its former name, still works when `CUBRID_TEST_PORT` is unset and
is deprecated. `make docker-down` keeps the test data; only `make docker-clean` deletes
it (before #1008, `make docker-down` deleted it).

`docker-compose.yml` sets `CUBRID_DB_HOST: localhost`, so the database keeps working
when the container is recreated on the same volume. Images up to 11.3 keep the database
on the `cubrid-data` volume and 11.4 on `cubrid-databases`, so `down` keeps it on every
supported version. Opening a database created by another CUBRID version is not verified,
so run `make docker-clean` (which deletes the test data) before switching `CUBRID_VERSION`. A volume created before that setting
fails with -353 after a recreate; repair it with `make docker-fix-db-host`, which keeps
the data (see
[Troubleshooting](docs/TROUBLESHOOTING.md#database-server-host-not-found-after-recreating-the-container)).

Supported CUBRID versions: `11.4`, `11.2`, `11.0`, `10.2`.

`make integration` does not use this default stack. It starts its own uniquely
named Compose project, refuses to run if that project already has containers,
volumes or networks, and removes only what it created (`docker compose -p
<project> down -v`), also after Ctrl-C, `SIGTERM` or `SIGHUP`. Use `make integration CUBRID_TEST_PORT=<port>` if port 33000 is
taken. It waits until the server answers through the selected driver and then runs
the whole integration suite with pycubrid (`cubrid+pycubrid://`); use
`make integration INTEGRATION_DRIVER=cubriddb` to run it through the CUBRIDdb C
extension (`cubrid://`). See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#quick-integration-workflow).

---

## Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

### Rules

- **Line length**: 100 characters
- **Target Python**: 3.11+
- **Formatter**: `ruff format`
- **Linter**: `ruff check`

### Running Checks

```bash
# Check synchronized tooling and lint every maintained Python source path
make lint

# Check formatting over the same shared paths (never modifies files)
make format-check

# Apply fixes and formatting over the same shared paths (the only mutating target)
make format

# Check strict typing, or run the complete non-test quality gate
make typecheck
make check

# Check that the required tools are installed at their pinned versions
make doctor
```

`make check-all` still works as a deprecated alias of `make check` for one minor
release and prints a deprecation notice on stderr.

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
   make test        # every offline test, including the repository-tooling tests
   ```

4. **Run the shared lint, format, type, security and docs-reason checks**:
   ```bash
   make check
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

- The same review and merge policy applies to human-authored and AI-assisted
  work, regardless of OpenCode, Codex, Claude Code, ChatGPT or other tools.
  Required GitHub CI results are authoritative at the final PR head;
  local checks are encouraged. Oracle, Copilot and `agent-review` are
  optional advisory reviews, not tool-specific approval gates.
  The responsible maintainer verifies changes and chooses whether to merge.
  Keep independent scrutiny for security, CI permissions, and publishing.

- CI must pass (lint, offline tests, integration tests).
- Maintain backward compatibility unless explicitly approved.
- `.github/CODEOWNERS` requests maintainer review automatically for release, CI,
  security-policy, dialect, compiler, reflection and Alembic paths. It only routes
  reviews: it is not a security boundary, and other changes do not wait on a code owner.

Contributors install the `dev` dependency group, run the shared checks, update affected docs
and open a PR with motivation, commands/results and reasons for checks not run.
For documentation changes, run `python scripts/generate_llms_full.py` (it regenerates
`docs/llms-full.txt` and copies the canonical `docs/llms.txt` index to the root
`llms.txt`; edit only `docs/llms.txt`) and, in a
docs environment with `mkdocs-material` and `pymdown-extensions`, `mkdocs build --strict`.
`python scripts/check_docs_links.py` reports broken local links, anchors, unclosed code
fences and missing commands, as the required `docs-check` CI job does.
Maintainers coordinate optional AI-assisted reviews, final integration,
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

### Agent-review evidence gate

`agent-review` is optional **diagnostic information**, not a required check,
a code approval or a condition of merging. The current script may still
summarize review records using legacy tool-specific evidence classifications;
that output is **not** the project's acceptance policy. Do not make its
check name a protected required context: a PR may impersonate GitHub Actions
check names. Reviewers assess any useful findings independently.

The tool-neutral merge policy is: required GitHub CI passes at the relevant
head, verified blocking issues are addressed, and the responsible maintainer
makes the final decision. Release, security and protected-path requirements
continue to apply, regardless of coding tool. First-time fork workflows
may require maintainer approval to run; this is an Actions security control.

## Repository-local issue ownership

Issues own implementation and acceptance in the repository whose files change.
Provide a self-contained local problem, scope, owner, tests, and closure
decision. Sibling repositories may be cited with Refs owner/repo#N when they
supply a real dependency or compatibility contract; their priorities and
completion are not inherited. Close only this repository's issues (Closes #N).
PRs with no local issue may state N/A and a reason. The existing PR title check
rejects direct cross-repository issue-closing keywords, including emphasized or
linked ones, in the PR body, the PR title and commit messages. The title and
commit messages make up the squash commit and are read as plain text; an edit to
the squash message at merge time is not checked. In the body, the check ignores
fenced and indented code blocks and HTML comment blocks only where it can follow
the Markdown exactly, so anything uncertain is checked: code and comment blocks
inside list items, footnotes and block quotes are always checked; after a fence
it cannot track (in a list item, block quote or raw HTML, on an indented line,
or as a line that only looks like a fence), later fences and comments are
checked; after anything that may start an HTML tag, even in prose or inline
code, later comments are checked; and after a raw-text element name such as
`<textarea>` or `<select>`, nothing is ignored. Inline code and inline comments
are always checked. External contributors do not need to install internal agent
tools or create duplicate work.

### Good first issues and contribution claims

An unassigned `good first issue` is open to **human-led contributors**, including people who direct and review AI-assisted work. They can start and submit a PR **without prior maintainer approval, GitHub Assignee access, or internal AI tooling**.

Before beginning, check the issue's Assignees, comments and open PRs. A brief comment expressing interest helps avoid duplicate work but is optional; it is not a permission gate or an exclusive claim. If someone already owns the issue or is preparing a PR, coordinate first. Maintainers handle issue assignments and labels, including requests from contributors who cannot self-assign.

**Maintainer-operated autonomous agents** are distinct from human-directed AI assistance. Before an autonomous agent implements a newcomer-reserved `good first issue`, a maintainer must authorize **that specific issue** and assign its implementer. Broad backlog/release instructions are insufficient.

Existing tests, docs requirements and PR review/merge policies remain unchanged.

## Pull request and commit titles

This section covers pull request titles and commit subjects. Issue titles use type-only prefixes such as `feat:` and `bug:`; see the [organization writing standard](https://github.com/cubrid-lab/.github/blob/main/docs/ISSUE_PR_COMMIT_STANDARD.md). Pull requests are squash-merged and the pull request
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
release. Maintainers prepare release PRs with `release-please.yml`; see
[`RELEASING.md`](RELEASING.md).

---

## Reporting Issues

Search for an existing issue first, then use the closest issue form. Keep its
prefilled title prefix (`bug:`, `feat:`, or `chore:`); for a custom issue, use `bug: ...`, `feat: ...`, or another type-only prefix without a module scope.

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

## Keeping issue descriptions actionable

Before coding, agree the issue's problem, expected behavior, scope, completion
criteria and validation method. Keep the body as the current specification;
record dated progress in comments. Maintainers reconcile closed dependencies
and completed checklist items after a related merge or handoff. Preserve the
original reproduction's revision and limits: older evidence is not proof of
current behavior. Priorities/sizes belong in labels, execution order in the
backlog tracker. Research closes on a documented decision, not an implied
promise to implement every proposed option.

Human-led contributors may work on an unclaimed issue and submit a PR without
prior maintainer authorization or the permission to self-assign. Check current
Assignees, comments and open PRs; coordinate before duplicating claimed work.
Maintainers manage assignment and handoffs. Autonomous agents operated by
maintainers need assignment before implementation and explicit authorization to
take each newcomer-reserved `good first issue`.
A reviewer does not need to be an issue assignee.

## Minimum PR validation

Follow the [CI execution policy](docs/CI_POLICY.md). PRs run the full offline suite
with the 95% coverage floor, but live integration on PRs is representative, not
full-matrix evidence. Run relevant regression tests locally and report
commands/results; request exact-head full validation where compatibility requires it.
