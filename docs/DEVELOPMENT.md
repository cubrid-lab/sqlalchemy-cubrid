# Development Guide

Everything you need to set up a development environment, run tests, and
contribute to sqlalchemy-cubrid.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Make Targets](#make-targets)
- [Running Tests](#running-tests)
- [Docker Integration Testing](#docker-integration-testing)
- [Multi-Version Testing](#multi-version-testing)
- [Code Coverage](#code-coverage)
- [Code Style](#code-style)
- [Pre-Commit Hooks](#pre-commit-hooks)
- [CI/CD Pipeline](#cicd-pipeline)

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| Git | any |
| Docker | any (for integration tests) |
| Docker Compose | v2+ |

---

## Installation

### Quick Setup

```bash
git clone https://github.com/cubrid-lab/sqlalchemy-cubrid.git
cd sqlalchemy-cubrid
make install
```

`make install` performs:
1. `pip install -e ".[dev]"` — editable install with dev dependencies
2. `pre-commit install` — git hook setup

### Manual Setup

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

---

## Project Structure

```mermaid
graph TD
    root["sqlalchemy-cubrid/"]

    pkg["sqlalchemy_cubrid/ - Main package"]
    tests["test/ - Test suite"]
    docs["docs/ - Documentation"]
    samples["samples/ - Usage examples"]
    pyproject["pyproject.toml - Project config, dependencies"]
    tox["tox.ini - Multi-Python test config"]
    docker["docker-compose.yml - CUBRID Docker setup"]
    makefile["Makefile - Development shortcuts"]
    contributing["CONTRIBUTING.md - Contribution guidelines"]

    root --> pkg
    root --> tests
    root --> docs
    root --> samples
    root --> pyproject
    root --> tox
    root --> docker
    root --> makefile
    root --> contributing

    pkg --> init["__init__.py - Public API, version, type exports"]
    pkg --> base["base.py - ExecutionContext, IdentifierPreparer"]
    pkg --> compiler["compiler.py - SQL/DDL/Type compilers"]
    pkg --> dialect["dialect.py - CubridDialect (reflection, connection, etc.)"]
    pkg --> pycubrid_dialect["pycubrid_dialect.py - Pure Python driver dialect"]
    pkg --> aio_dialect["aio_pycubrid_dialect.py - Async pycubrid.aio dialect"]
    pkg --> dml["dml.py - ON DUPLICATE KEY UPDATE, MERGE constructs"]
    pkg --> trace["trace.py - Query tracing utility"]
    pkg --> types["types.py - CUBRID type system"]
    pkg --> req["requirements.py - SA 2.0 test requirement flags"]
    pkg --> alembic["alembic_impl.py - Alembic migration support"]
    pkg --> typed["py.typed - PEP 561 marker"]

    tests --> tcomp["test_compiler.py - SQL compilation and DML construct tests"]
    tests --> ttypes["test_types.py - Type system tests"]
    tests --> tdialect["test_dialect_offline.py - Dialect tests (no DB)"]
    tests --> tbase["test_base.py - Base module tests"]
    tests --> treq["test_requirements.py - SA requirement flag tests"]
    tests --> talembic["test_alembic.py - Alembic integration tests"]
    tests --> taio["test_aio_pycubrid_dialect.py - Async dialect tests"]
    tests --> taioint["test_aio_integration.py - Async integration tests"]
    tests --> tjson["test_json.py - JSON type and path tests"]
    tests --> tpackaging["test_packaging.py - Packaging and entry point tests"]
    tests --> tshowcreate["test_show_create_table.py - Reflection parser tests"]
    tests --> ttrace["test_trace.py - Query trace tests"]
    tests --> tintegration["test_integration.py - Live DB integration tests"]
    tests --> tsuite["test_suite.py - SA test suite runner"]
    tests --> tconftest["conftest.py - Test fixtures"]
```

---

## Make Targets

All common development tasks are available via `make`:

```bash
make help          # Show all available targets
make install       # Install in dev mode with all dependencies
make lint          # Run ruff linter + format checks
make check-tool-versions # Verify local/CI tool pins and type-check cells agree
make typecheck     # Report versions and run strict mypy
make format        # Auto-fix lint issues and format code
make test          # Run the fast offline tests with coverage (95% threshold)
make test-repo     # Run the repository-tooling tests (Makefile, signal handling, repo scripts)
make test-offline  # Run every offline test (fast + repository-tooling) with coverage
make test-all      # Run tox across all Python versions
make integration   # Start a run-owned Docker project → run integration tests (pycubrid) → remove it
make docker-up     # Start CUBRID Docker container
make docker-down   # Stop and remove CUBRID Docker container
make clean         # Remove build artifacts and caches
```

---

## Running Tests

### Strict Type Checking

Run `make typecheck` in the development environment. It reports Python,
SQLAlchemy, Alembic and mypy versions, then runs
`python3 -m mypy sqlalchemy_cubrid/ --config-file=pyproject.toml`.
The mypy version is pinned to `2.3.1` in the dev dependencies.

CI runs the same Makefile target in one cell, Python 3.13 / SQLAlchemy 2.1.1. It
is blocking: the required `matrix-result` check fails if the type-check job fails,
is cancelled or is skipped. CI's single cell is not the same set as the local tox
environments: `typecheck-sa21` mirrors it, while `typecheck-sa20` (Python 3.11 /
SQLAlchemy 2.0.53) is local-only. Ruff and the existing offline tests with 95%
minimum coverage also remain required. To choose a virtualenv interpreter
locally, use `make typecheck PYTHON=/path/to/venv/bin/python`.

### Offline Tests (No Database Required)

Async adapter fixtures in synchronous unit tests consume their actual coroutine
entry through the await bridge and assert that it was awaited. Patch both the
connection bridge (SQLAlchemy 2.0) and module bridge (2.1) when applicable; a
mock that simply returns a cursor can hide an invalid adapter and leak an
unawaited coroutine into pytest's garbage-collection checks.

The majority of the test suite runs without a live CUBRID instance:

```bash
# Run all offline tests
pytest test/ -v --ignore=test/test_integration.py --ignore=test/test_suite.py \
  --ignore=test/test_aio_integration.py

# Run with coverage report
pytest test/ -v --ignore=test/test_integration.py --ignore=test/test_suite.py \
  --ignore=test/test_aio_integration.py \
  --cov=sqlalchemy_cubrid --cov-report=term-missing

# Run a specific test file
pytest test/test_compiler.py -v

# Run a single test
pytest test/test_compiler.py::TestCubridSQLCompiler::test_select_limit -v
```

### Property-Based Fuzz Tests (Hypothesis)

`test/test_fuzz_*.py` use [Hypothesis](https://hypothesis.readthedocs.io/) to
generate SELECT/INSERT/DDL combinations the hand-written suite never enumerated
and assert dialect invariants (no unexpected compile exception, placeholder ==
parameter count, LIMIT/OFFSET cardinality, DDL/reflection round-trip). The
offline fuzz tests run in the normal offline suite; live-execution fuzz tests
are `integration`-marked.

```bash
# Fast profile (default, ~50 examples/test) — runs with the offline suite
pytest test/test_fuzz_select.py -v

# Extended profile (2000 examples/test) — the nightly bug-hunt profile
HYPOTHESIS_PROFILE=nightly pytest test/test_fuzz_select.py -v

# Live-execution fuzzing (requires CUBRID)
export CUBRID_TEST_URL="cubrid+pycubrid://dba@localhost:33000/testdb"
HYPOTHESIS_PROFILE=nightly pytest test/test_fuzz_select.py -m integration -v
```

Profiles (`dev`, `ci`, `nightly`) are registered in `test/conftest.py` and
selected via `HYPOTHESIS_PROFILE`. PR CI uses the fast profile; explicit full
validation and the release gate run the extended profile against live CUBRID.

### Integration Tests (Requires CUBRID)

```bash
# Start a CUBRID container
docker compose up -d

# Wait for CUBRID to be ready (healthcheck: ~30s)
docker compose logs -f cubrid

# Set the connection URL
export CUBRID_TEST_URL="cubrid+pycubrid://dba@localhost:33000/testdb"

# Run the regular tox profile (installs the existing pure-driver extra)
tox -e integration

# Run a focused sync file in an environment with pycubrid installed
pytest test/test_integration.py -v

# Run async integration tests
pytest test/test_aio_integration.py -v

# Stop the container
docker compose down -v
```

The regular tox profile requires an explicit `cubrid+pycubrid` URL. It rejects
missing URLs and legacy C-extension schemes, then probes both sync and derived
async connections with bounded `SELECT 1` requests before pytest. Async suites
derive `cubrid+aiopycubrid` with SQLAlchemy's URL API, retaining credentials,
ports and query options; `CUBRID_TEST_AURL` remains an explicit async override.
Failures do not print URL credentials. Without the optional native C-extension,
the driver-differential comparisons are intentionally skipped;
that profile does not claim to test CUBRIDdb. Formal CI's native-driver
`--dburi` route remains separate and unchanged.

#### Skip or fail: `CUBRID_TEST_URL` is the switch

Whether an `integration`-marked test runs is decided in one place, a
`pytest_runtest_setup` gate in `test/conftest.py` (#593). No test module probes
the server at import time any more.

| `CUBRID_TEST_URL` | Server answers `SELECT 1` through the URL's driver | Integration tests |
| --- | --- | --- |
| unset or empty | (not probed) | skipped locally; with `CI=true` the run exits 1 before any test runs |
| set | yes | run |
| set | no (down, wrong port, driver not installed, not a CUBRID URL with a database) | **error**, every one, with the same message |

The gate probes the server once per session through the helpers in
`scripts/integration_urls.py` (shared with `scripts/wait_for_cubrid.py`), using
the driver the URL selects: `cubrid+pycubrid://` needs pycubrid and `cubrid://`
needs the CUBRIDdb C extension, also for `test/test_aio_integration.py`, which
connects through `cubrid+aiopycubrid://`. `CUBRID_TEST_URL` must be a
`cubrid://`, `cubrid+cubriddb://` or `cubrid+pycubrid://` URL with a database, so
the destructive test fixtures can never run against another database. When
`CUBRID_TEST_AURL` overrides the async route, the gate probes that endpoint too,
through `cubrid+aiopycubrid://`. The error names the URL with its password
masked, for example:

```text
CUBRID_TEST_URL is set, but CUBRID at cubrid+pycubrid://dba:***@127.0.0.1:33599/testdb
does not answer SELECT 1 through the driver the URL selects: OperationalError: ...
```

So a lane that believes it has a server can no longer turn green by skipping.
Before #593, 421 of the 447 tests in `pytest test/ -m integration` skipped
against an unreachable URL, even with `CI=true`. Now all 447 error and pytest exits 1.
Unset `CUBRID_TEST_URL` to skip them on purpose, or deselect them with
`-m "not integration"` (the offline suite does). The gate does not apply to the
`--dburi` compliance runs: with `--dburi`, SQLAlchemy's plugin connects at
session start and fails the run itself when the server is unreachable.

After the gate passes, a few modules still skip for reasons of their own: the
driver-differential and transactional-DDL tests need both drivers, and the
server-restart tests need `CUBRID_TEST_DOCKER_CONTAINER`. Their CI steps turn
those skips into failures with `CUBRID_REQUIRE_DRIVER_DIFFERENTIAL=1`,
`CUBRID_REQUIRE_TRANSACTIONAL_DDL=1` and `CUBRID_REQUIRE_SERVER_RESTART=1`
(#486, #503, #565).

`test/test_integration.py` creates tables and database users with fixed names
(for example `t583_fresh`, `alter_it_modify`, `u543`), so two runs against the
same database interfere with each other. Run it against a dedicated database,
one run at a time. `make integration` starts a run-owned server for this.

The `TestIsDisconnect` KILL QUERY case (#634) also remains serialized: KILL is
server-wide and takes only a numeric transaction index, not an atomic user
predicate. The test creates one fresh `kq634_<16 hex>` database account, opens
and warms its victim connection before starting a separate killer process
(needed because CUBRIDdb holds the GIL during a query), and keeps that
connection open until the killer has exited or been stopped. The killer uses
`SHOW TRANSACTION TABLES` and selects only an active query with exactly that
`Client_db_user` and a non-null `Query_start_time`; a missing column or more
than one matching active query fails without issuing KILL. It never chooses a
newly appeared DBA or other user's query by timing. Cleanup disposes the
victim engine and drops only the account created by this run, through the
verified user-drop helper. The victim URL explicitly clears the DBA password
because the generated account has no password, even when `CUBRID_TEST_URL`
contains a nonempty DBA password. Use a disposable DBA test database; another
session sharing that dedicated account would make the test fail closed.

`test/test_server_restart.py` (#565) stops and starts `cub_server` with
`docker exec -u cubrid <container> bash -lc "cubrid server stop|start <db>"` and
checks that the pool invalidates broken connections and recovers, through both
drivers, with and without `pool_pre_ping`. It skips unless
`CUBRID_TEST_DOCKER_CONTAINER` names the container that serves `CUBRID_TEST_URL`;
point it at a disposable container, since the tests take the database down:

```bash
CUBRID_TEST_URL="cubrid://dba@localhost:33000/testdb" \
CUBRID_TEST_DOCKER_CONTAINER=<container> \
  pytest test/test_server_restart.py -v -rs
```

CI runs it last in each integration job with `CUBRID_REQUIRE_SERVER_RESTART=1`,
which turns every skip into a failure.

### Full SA Test Suite

```bash
# Requires a running CUBRID instance
pytest test/test_suite.py --dburi cubrid://dba@localhost:33000/testdb
pytest test/test_suite.py --dburi cubrid+pycubrid://dba@localhost:33000/testdb
```

Known failures are baselined per driver and SQLAlchemy version; see
[SQLAlchemy compliance lanes](#sqlalchemy-compliance-lanes).

---

## Docker Integration Testing

### docker-compose.yml

The project includes a `docker-compose.yml` for local CUBRID instances:

```yaml
services:
  cubrid:
    image: cubrid/cubrid:${CUBRID_VERSION:-11.2}
    environment:
      CUBRID_DB: testdb
    ports:
      - "33000:33000"
    healthcheck:
      test: ["CMD", "csql", "-u", "dba", "testdb", "-c", "SELECT 1"]
      interval: 15s
      timeout: 10s
      retries: 10
      start_period: 30s
```

### Testing Against Different CUBRID Versions

```bash
# Default (11.2)
docker compose up -d

# Specific version
CUBRID_VERSION=11.4 docker compose up -d
CUBRID_VERSION=11.0 docker compose up -d
CUBRID_VERSION=10.2 docker compose up -d
```

### Supported CUBRID Versions

| Version | Docker Image |
|---|---|
| 11.4 | `cubrid/cubrid:11.4` |
| 11.2 | `cubrid/cubrid:11.2` (default) |
| 11.0 | `cubrid/cubrid:11.0` |
| 10.2 | `cubrid/cubrid:10.2` |

### Quick Integration Workflow

```bash
# One-command: start, test, stop (pycubrid, the recommended driver)
make integration

# The same suite through the CUBRIDdb C extension (must be installed)
make integration INTEGRATION_DRIVER=cubriddb
```

`make integration` runs every `integration`-marked test in one pytest session.
`INTEGRATION_DRIVER` selects the driver of `CUBRID_TEST_URL`: `pycubrid` (the
default, `cubrid+pycubrid://`) or `cubriddb` (`cubrid://`, which needs the
CUBRIDdb C extension; CI builds it from cubrid-python v11.3.0.51, see the
"Build the CUBRID Python driver wheel" step in `.github/workflows/ci.yml`). Any other value exits with status 2 before any Docker
command. Several test files open connections through both drivers whichever one
the URL selects, so install `.[dev,pycubrid]` for either driver. Main/weekly code CI runs
`make integration` with the default driver on CUBRID 11.4; the full dispatch and release-gate
`integration-full.yml` workflow runs it with both drivers on CUBRID 10.2 and
11.4.

After `docker compose up -d`, the run waits until the new server answers
`SELECT 1` through the selected driver (`scripts/wait_for_cubrid.py`), for up to
`INTEGRATION_READY_TIMEOUT` seconds (default 180), and fails if it never does. A
fresh container needs about 20 seconds to create its database and start the
broker; a fixed 10-second sleep used before #575 let the suite start too early,
so the first tests failed with CCI -20004 and the live test files that probed the
server at import time skipped themselves. Since #593 no file probes at import
time; the conftest gate errors every integration test when the server does not
answer, so a server that is not ready fails the run instead of skipping it.

`make integration` runs in its own Compose project, named
`sqlalchemy-cubrid-it-<timestamp>-<pid>` by default. Its container, network and
`cubrid-data` volume are therefore separate from every other run and from a stack
started with `docker compose up -d` or `make docker-up`, whose project Compose
names after the checkout directory (or `COMPOSE_PROJECT_NAME`).

Before starting, it checks that the project has no containers, volumes or
networks and that no volume named exactly `<project>_cubrid-data` exists. If
anything is found, it refuses to run and neither starts nor removes anything. If
the check itself fails (for example, the Docker daemon is unreachable), it prints
`Ownership check ... failed; nothing was started` and stops. Only after the check
passes does it register cleanup, so `docker compose -p <project> down -v` only
removes resources that this run created.

Cleanup runs on shell exit, including after failed startup, readiness waiting or
tests, and when the run receives `SIGINT` (Ctrl-C), `SIGTERM` (for example from
`timeout` or `kill`) or `SIGHUP` (a closed terminal):

- If the signal arrives while `docker compose up -d` runs, cleanup first lets it
  finish, for up to `INTEGRATION_STOP_GRACE` seconds (default 10). The Docker
  daemon completes a container create even after the client is killed, so
  stopping `up -d` halfway could leave a container, and a re-created volume, that
  `down -v` had already missed. `up -d` runs in its own process group, so a
  terminal Ctrl-C does not reach it. If it is still running after the grace period,
  its group, including the Compose plugin process, is sent `SIGTERM`, and cleanup
  waits for the whole group to exit.
- Any other running step (the readiness wait or pytest) is sent `SIGTERM` at once
  and killed if it is still running `INTEGRATION_STOP_GRACE` seconds later.
- Cleanup runs once, and the command exits with 128 + the signal number (130, 143
  or 129).
- Further `SIGINT`, `SIGTERM` or `SIGHUP` signals are ignored until
  `docker compose down -v` finishes, and `down -v` runs in its own session.
  Neither a second Ctrl-C nor a signal sent to the whole process group (as GNU
  `timeout` does) interrupts or repeats it. If `down -v` itself hangs, `SIGQUIT`
  (`Ctrl-\`) stops `make` without waiting for it.
- A signal that was already ignored when `make` started, such as `SIGINT` for a
  background job of a non-interactive shell, cannot be handled.

The original failure is preserved if cleanup also fails; cleanup failure after
passing tests also makes the command fail. Cleanup errors are reported
explicitly. Cleanup is not guaranteed after an untrappable termination such as
`SIGKILL` or a host shutdown. Remove such a leftover project with
`docker compose -p <project> down -v` after checking its name with
`docker compose ls -a`.

The container publishes CUBRID on host port 33000. If that port is already in
use, pick another one with `make integration CUBRID_PORT=33999`; the test URL
follows it. `INTEGRATION_PROJECT=<name>` fixes the project name. It must match
`^[a-z0-9][a-z0-9_-]*$` (otherwise the command exits with status 2 before running
any Docker command), and the same pre-existence check applies. Two concurrent
runs with the same fixed `INTEGRATION_PROJECT` are not supported. pytest keeps the
terminal's standard input, so `make integration PYTEST="python3 -m pytest --pdb"`
can stop in the debugger; Ctrl-C there ends the run and cleans up.

For an already-running server, set `CUBRID_TEST_URL` and use `make integration-local`.
That target never starts or stops Docker and leaves the external server running.

---

## Multi-Version Testing

### tox Configuration

The `tox.ini` defines local offline environments for Python 3.11–3.14, a pinned
Ruff lint environment, and `typecheck-sa20` / `typecheck-sa21` environments that
run the same Makefile target against pinned SQLAlchemy/Python pairs. Only
`typecheck-sa21` (Python 3.13 / SQLAlchemy 2.1.1) corresponds to a CI cell, since
CI type-checks in one cell; `typecheck-sa20` is a local-only pair. Tox uses
the existing pycubrid/Alembic extras and development test dependencies. Offline
selection in the `py3xx` environments is `-m "not integration and not repo"`, and
the `repo` environment runs the repository-tooling tests with `-m repo` (#594);
the integration environment selects
`-m integration` with `--ignore=test/test_suite.py`. The formal SQLAlchemy
compliance suite requires the testing plugin enabled by `--dburi`; existing CI
runs it separately with that argument and its known-failure baseline. Regular
tox integration does not run the formal suite. The offline threshold remains 95%.

```ini
[tox]
envlist = lint, typecheck-sa20, typecheck-sa21, py311, py312, py313, py314, repo
skip_missing_interpreters = true
```

### Running tox

```bash
# Run all environments
tox

# Run a specific Python version
tox -e py312

# Run lint checks only
tox -e lint

# Check both designated SQLAlchemy typing environments
tox -e typecheck-sa20,typecheck-sa21
```

### CI Matrix

Routine CI uses representative offline and live combinations rather than the full
matrix. Every run selected for code changes runs the full offline suite with 95%
coverage: pull requests on Ubuntu/Python 3.12, and main pushes, changed weekly runs
and manual dispatches on Python 3.11 and 3.14 (#734). High-risk PRs select
newest integration, while main/weekly use oldest/newest endpoints. Repository
tooling is path-selected on one Linux lane. Full integration is explicit/manual
and release-only. See [CI execution policy](CI_POLICY.md) for exact selection and
validation requirements. Historical cost measurements below describe the earlier
workflow, not current job counts or new savings.

---

## Code Coverage

### Requirements

- **Minimum threshold**: 95% line coverage
- CI enforces the threshold via `--cov-fail-under=95` in the `offline-tests` job (`.github/workflows/ci.yml`); run `pytest test/ -m "not integration and not repo" --cov=sqlalchemy_cubrid --cov-report=term-missing` locally for current test counts and coverage rather than relying on a snapshot here, since both grow with every PR

### Running Coverage

```bash
# With coverage report
pytest test/ -v \
  --ignore=test/test_integration.py \
  --ignore=test/test_suite.py \
  --ignore=test/test_aio_integration.py \
  --cov=sqlalchemy_cubrid \
  --cov-report=term-missing \
  --cov-fail-under=95

# Or via make
make test
```

### Known Unreachable Lines

A few lines in `compiler.py` and `dml.py` are defensive fallbacks (an empty
`for_update_clause`/`limit_clause` return, a DDL compilation default branch, an
`else` arm in type normalization) that cannot trigger through SQLAlchemy's
public API and so never execute under the offline suite. Their exact line
numbers shift as the modules change; run `pytest test/ -m "not integration and
not repo" --cov=sqlalchemy_cubrid --cov-report=term-missing` (or `make test`)
and check the `Missing` column for the current set instead of a pinned list
here.

---

## Code Style

### Ruff

This project uses [Ruff](https://docs.astral.sh/ruff/) for both linting and
formatting.

| Setting | Value |
|---|---|
| Line length | 100 characters |
| Target Python | 3.11+ |
| Linter | `ruff check` |
| Formatter | `ruff format` |

### Running Checks

```bash
# Check tooling consistency and lint/format all maintained Python sources
make lint

# Apply fixes and formatting over the same shared source paths
make format
```

---

## Pre-Commit Hooks

Pre-commit hooks run lint and format checks automatically on `git commit`.

Ruff and Mypy versions are single-sourced from the dev pins in `pyproject.toml`.
The Ruff and Mypy pre-commit hooks are `repo: local` / `language: system` hooks
that invoke `python3 -m ruff`/`python3 -m mypy` against the active `.[dev]`
environment, so there is no separate hook revision to keep in sync: the pin in
`pyproject.toml` is authoritative everywhere. The mypy hook checks
`sqlalchemy_cubrid/` with the project's strict configuration using whatever
SQLAlchemy/Alembic the active `.[dev,alembic]` environment already provides. It
does not install stubs automatically or suppress missing imports. Ruff's
explicit `include = ["*.py", "*.pyi"]` and the matching hook types keep CLI, CI
and hooks on Python sources rather than rewriting documentation snippets.

The shared `LINT_PATHS` in the Makefile covers the package, tests, scripts,
demos, samples and `docs/source` Python configuration. CI and tox invoke
`make lint`; the hooks keep checking all tracked Python/pyi files. The drift
checker rejects omitted maintained directories or a runner that bypasses this
shared target.

Only `pyproject.toml`'s dev pin needs updating when bumping Ruff or Mypy
(Dependabot's `pip` ecosystem does exactly this): the pre-commit hooks and the
`tox -e lint`/`typecheck-sa20`/`typecheck-sa21` environments install the
project's own `dev` extra, so they always run whatever that pin resolves to.
`tox -e typecheck-sa20`/`typecheck-sa21` additionally pin an exact SQLAlchemy
release per Python version (2.0.53 on 3.11, 2.1.1 on 3.13). Only the 2.1.1 pair
corresponds to CI's single type-check cell; `scripts/check_tool_versions.py`
requires a matching `typecheck-sa<minor>` environment for every CI cell and
validates each environment's own pin. Run `make check-tool-versions`,
`pre-commit run --all-files` and `tox -e lint,typecheck-sa20,typecheck-sa21`
after a change. The consistency check runs through CI lint, tox lint and a
local pre-commit hook, so a dependency-only update cannot silently leave old
pins.

### Setup

The Ruff and Mypy hooks run via `language: system`, invoking `python3 -m
ruff`/`python3 -m mypy` from whatever environment is active when Git runs the
hook. Install the project's `dev` extra (which pins Ruff and Mypy) into that
same environment first, then install the hooks:

```bash
pip install -e ".[dev]"
pre-commit install
```

Activate that environment (or a venv where it's installed) whenever a commit
should run the hooks; otherwise Ruff/Mypy are missing or a stale/global
version silently runs instead of the pinned one.

### Manual Run

```bash
# Run all hooks on all files
pre-commit run --all-files
```

---

## CI/CD Pipeline

### GitHub Actions Workflows

| Workflow | File | Trigger |
|---|---|---|
| CI | `.github/workflows/ci.yml` | PRs, main, weekly, manual |
| Integration Full | `.github/workflows/integration-full.yml` | Manual dispatch, called by `publish-pypi.yml` |
| Prepare Release | `.github/workflows/release-please.yml` | Push to main or manual dispatch; prepares the reviewed release PR |
| Release | `.github/workflows/publish-pypi.yml` | Push to main (releases only a merged release PR), recovery dispatch |

### CI Pipeline Steps

1. **Lint** — Ruff check + format verification
2. **Offline Tests** — the full offline suite on Ubuntu/Python 3.12 for PRs, and on Python 3.11 and 3.14 for main, weekly and dispatched runs
3. **Integration Tests** — high-risk PR newest cell; main/weekly 2 combinations (Python 3.14 × CUBRID 11.4, Python 3.11 × CUBRID 10.2), plus async integration coverage and the blocking [SQLAlchemy compliance lanes](#sqlalchemy-compliance-lanes) for CUBRIDdb and released pycubrid
4. **make integration** — `make integration` with the default pycubrid driver on CUBRID 11.4: the whole `integration`-marked suite in one session, as run locally (both drivers on CUBRID 10.2 and 11.4 on full dispatch and in the release gate in `integration-full.yml`)
5. **Coverage** — Enforces ≥ 95% on the full offline lane on every event, PRs included

### Driver-differential lane

`test/test_driver_differential.py` runs the same SQLAlchemy operations on
pycubrid and the CUBRIDdb C-extension and asserts they agree. It covers basic
CRUD plus the DB-API contract areas that already work on the released drivers:
Core `executemany` with integer, UTF-8/CJK and NULL values, textual
`executemany` with integer and UTF-8/CJK values, scalar binds, textual-SQL
result column names, and commit/rollback visibility. It also compares
constraint-violation exception classes (#480), results read across a
rollback (#481), scalar `cursor.description` names, type codes and
`null_ok` (#482), and `SET`/`MULTISET`/`SEQUENCE` round trips (#484, writing
the collection literal directly in SQL since binding one is rejected by
released pycubrid, then comparing values normalized to `str` elements). These
checks require the fixed pycubrid behavior shipped in pycubrid 1.8.0 (NOT
NULL/foreign-key classes, post-rollback results and `null_ok`) and run
unconditionally. Every #479 contract area now has a case here except LOBs,
which are covered separately by #485.

The integration jobs in `ci.yml` and `integration-full.yml` run this module
with both drivers installed and `CUBRID_REQUIRE_DRIVER_DIFFERENTIAL=1`. With
that variable set, `test/conftest.py` fails the session when no differential
case ran and passed, so a lane where both drivers fail to connect cannot
report success. Before the tests, `python -m scripts.report_driver_versions`
writes the exact Python, SQLAlchemy, pycubrid, CUBRIDdb (package version and
source tag) and CUBRID server versions to the job log and the GitHub step
summary. Local runs without the variable keep skipping cleanly when a driver
is unavailable. An unreachable `CUBRID_TEST_URL` server errors instead, like
every integration test (#593):

```bash
export CUBRID_TEST_URL="cubrid://dba@localhost:33000/testdb"
CUBRID_REQUIRE_DRIVER_DIFFERENTIAL=1 pytest test/test_driver_differential.py -v -rs
```

### All-skipped lane guard

A lane that silently skips every test it was meant to run still exits `0` in
plain pytest, which hides a misconfigured lane (a stale `skipif`, a driver
that stopped connecting, a copy-pasted file list) behind a green check. The
required driver-differential, transactional-DDL (#503) and server-restart
(#565) lanes already guard themselves with their own `CUBRID_REQUIRE_*` checks
in `test/conftest.py`. For the plain `pytest`/`make integration` steps in
`ci.yml`'s `integration-tests` and `make-integration` jobs and
`integration-full.yml`'s `integration-full` and `make-integration` jobs,
`scripts/check_not_all_skipped.py` reads the `tee`'d output of the preceding
invocation and fails unless at least one summary line shows real execution
(`passed`/`failed`/`error`/`xpassed`/`xfailed`); `skipped`/`deselected` alone,
or zero tests collected, fails the step:

```bash
set -o pipefail
python -m pytest test/test_integration.py -v --tb=short | tee integration.log
python -m scripts.check_not_all_skipped integration.log --label "Run integration tests"
```

A cell that is deliberately all-skip passes `--allow-all-skipped "<reason>"`
to report the reason and exit 0 instead of failing. `matrix-result` and
`full-matrix-result` need no change: these checks run inside jobs they already
depend on, so a step failing this guard already fails its job.

### SQLAlchemy compliance lanes

The official SQLAlchemy dialect compliance suite (`test/test_suite.py`, run
with `--dburi`) blocks merges in two driver lanes. Both are steps of the
`integration-tests` job in `ci.yml`, reuse that cell's CUBRID service, and
therefore fail `matrix-result` when they fail:

| Lane | URL | Pinned versions | CI cell |
|---|---|---|---|
| `cubrid@sa2.0` | `cubrid://` (CUBRIDdb C-extension) | cubrid-python v11.3.0.51, SQLAlchemy 2.0.53 | Python 3.14 × CUBRID 11.4 |
| `pycubrid@sa2.0` | `cubrid+pycubrid://` (recommended) | pycubrid 1.8.0, SQLAlchemy 2.0.53 | Python 3.11 × CUBRID 10.2 |
| `pycubrid@sa2.1` | `cubrid+pycubrid://` (recommended) | pycubrid 1.8.0, SQLAlchemy 2.1.1 | Python 3.14 × CUBRID 11.4 |

The `Pinned versions` column is each lane's own pin. In the oldest regular
integration cell (Python 3.11 × CUBRID 10.2) every step installs
`sqlalchemy[asyncio]>=2.0,<2.1`, so that cell is not pinned to exactly 2.0.53:
the `pycubrid-compliance-sqlalchemy=2.0.53` matrix value pins this lane's suite
run only.

The two pycubrid lanes split SQLAlchemy 2.0 and 2.1 across the two PR cells,
so each cell runs the suite for pycubrid only once (SQLAlchemy 2.1 needs
Python 3.11+, so it runs in the 3.14 cell). Every lane baseline was captured on
fresh CUBRID 10.2 and 11.4 databases. Each pycubrid step
first runs `python -m scripts.report_driver_versions`, which records the exact
Python, SQLAlchemy, pycubrid and CUBRID server versions in the job log and step
summary. The CUBRIDdb suite in the CUBRID 10.2 cell stays non-gating.

**Known failures are keyed per lane.** Every entry in `test/known_failures.txt`
names the lanes it fails in, as `<driver>@sa<major.minor>`, or as
`<driver>@sa<major.minor>@cubrid<major.minor>` when it fails on one CUBRID
server version only:

```text
test/test_suite.py::DistinctOnTest::test_distinct_on  cubrid@sa2.0 pycubrid@sa2.0 pycubrid@sa2.1
test/test_suite.py::NumericTest::test_float_as_decimal  cubrid@sa2.0
```

`test/conftest.py` derives the current lane from the `--dburi` dialect, the
installed SQLAlchemy version and the connected server version, and applies a strict xfail only to the entries
tagged for it. A CUBRIDdb-only failure therefore cannot hide a pycubrid
regression, and vice versa. There is no wildcard tag, and an untagged entry or
a lane CI does not gate (e.g. `pycubrid@sa2.2`) is a load error. With `CUBRID_STRICT_KNOWN_FAILURES=1` (set by every gating step)
the run also fails when:

- a listed test passes (strict XPASS): remove that lane's tag;
- a listed entry for the lane matches no collected test (stale baseline);
- a listed entry is skipped instead of xfailed, so it no longer proves
  anything: drop it or fix the skip;
- the lane has no entries at all, so a new driver or SQLAlchemy minor cannot
  gate on an empty baseline by accident;
- the installed SQLAlchemy is not the release the lane was captured with
  (`_PINNED_SQLALCHEMY` in `test/conftest.py`).

The manifest parser also rejects a node id listed twice, and a server-narrowed
tag that is not one of the (lane, server) pairs CI gates
(`_GATED_SERVER_LANES`: `cubrid@sa2.0@cubrid11.4`, `pycubrid@sa2.0@cubrid10.2`,
`pycubrid@sa2.1@cubrid11.4`), so a typo'd or never-exercised server tag cannot
slip in.

Tests that cannot apply to CUBRID at all (for example seven-digit precision
from the single-precision `FLOAT`, or non-ASCII identifiers on a non-UTF-8
database) are excluded in `sqlalchemy_cubrid/requirements.py` with a reason
instead of being listed. Every requirement property must return a **new**
`exclusions.open()` / `exclusions.closed()` object: SQLAlchemy extends the
first requirement of a stacked `@testing.requires` chain in place, so a shared
object silently turns every other requirement closed and skips most of the
suite (`test_stacked_requirements_do_not_leak_into_other_properties` guards
this).

**Updating a lane baseline** (a SQLAlchemy bump, a new pinned pycubrid, or a
fix that makes a listed test pass):

```bash
export CUBRID_TEST_URL="cubrid+pycubrid://dba@localhost:33000/testdb"
pip install "pycubrid==1.8.0" "sqlalchemy[asyncio]==2.1.1"
# 1. Capture: without strict mode, a missing lane just applies no xfails.
pytest test/test_suite.py --dburi="$CUBRID_TEST_URL" --maxfail=1000 -q -r fE
# 2. Classify every failure (dialect bug, driver limitation, backend/suite
#    limit), link its issue, and edit only this lane's tags.
# 3. Verify exactly as CI does.
CUBRID_STRICT_KNOWN_FAILURES=1 pytest test/test_suite.py --dburi="$CUBRID_TEST_URL" -q
```

Run the capture against both CUBRID 10.2 and 11.4 when adding a lane, then
update the pinned versions in `ci.yml`, the header of
`test/known_failures.txt`, and the `_GATED_LANES` set in
`test/test_known_failures.py` in the same change.

### pycubrid release-candidate adoption

The weekly `upstream-canary.yml` run against `pycubrid@main` stays
non-blocking: it warns about upcoming regressions, but an unreleased upstream
HEAD must not block unrelated pull requests. Its failures are still reported:
when a canary job fails on a scheduled or manually dispatched run of the
default branch, the workflow
opens an issue titled "Upstream canary failing against pycubrid@main" (label
`ci`), or comments on it if it is already open, with the failing jobs, the run
link and the pycubrid commit tested, and closes it once both jobs pass again.
The dependency bound
`pycubrid>=1.8.0,<2.0` (the compliance lane pins the same floor, enforced by
`test/test_workflow_hygiene.py`) is widened only after a **specific** pycubrid release
candidate (or new major release), installed by exact version, passes the
downstream contract suite: the regular and async integration tests, the
required driver-differential lane above, and the SQLAlchemy compliance suite.
Record the versions reported by `scripts/report_driver_versions.py` in the
adoption pull request, and update `CHANGELOG.md` and the support documentation
with the newly supported range in the same change.

The `CUBRID_PYCUBRID_UPSTREAM` strict-xfail gating was removed once pycubrid 1.8.0
shipped the fixes it covered (pycubrid#390, #395, #430, #431).

### Documentation gates

Documentation exceptions use a populated standalone physical source line
`Docs: not needed - <reason>` outside code, quotes or template comments, or the existing maintainer-managed
label. `make check-docs-reason` runs executable doctests and real event-JSON/workflow
regressions; `make check-all` and the docs-sync job run those same checks.
Translation help requests do not authorize a bypass: maintainers explicitly
approve the existing `translations-deferred` label and record follow-up. The
Korean-required and other-language advisory translation checks are unchanged.

English under `docs/` is the source of truth and Korean under `docs/ko/` is the one
translation kept complete. `python scripts/check_docs_translation.py` (run by the
lint job) compares every `docs/<name>.md` with `docs/ko/<name>.md` and fails on a
missing Korean file or a different number of headings (levels 2-4), fenced code
blocks or table rows. Add the Korean section in the same PR as the English one.
A document that is deliberately English-only goes into `EXCEPTIONS` in that script
with its reason. The check compares structure, not wording.

### Release Pipeline

Releases are maintainer-only and follow [RELEASING.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/RELEASING.md):
`release-please.yml` opens a release PR (version bump + dated CHANGELOG section, checked
with `make release-check VERSION=X.Y.Z`); after review and squash-merge, `publish-pypi.yml`
runs the full matrix, builds once, tags, publishes to PyPI and verifies the cookbook
automatically. Nobody pushes tags or publishes by hand.

`python scripts/lint_changelog.py` requires, in `[Unreleased]` and in releases after
1.10.0, the standard `###` sections, each once and with content, in this order: Upgrade
notes, Added, Changed, Deprecated, Removed, Fixed, Security, Performance, Documentation,
CI, Tests. Use `Documentation`, not `Docs`, and file release automation under `CI` or
`Changed`. Releases up to 1.10.0 keep their historical headings. A GitHub Release is
titled exactly `vX.Y.Z`, and its body is the CHANGELOG section plus one
`**Full Changelog**` compare link; see the "GitHub Release Policy" in `AGENTS.md`.

---

*See also: [Contributing Guide](../CONTRIBUTING.md) · [Feature Support](FEATURE_SUPPORT.md) · [Connection Guide](CONNECTION.md)*
