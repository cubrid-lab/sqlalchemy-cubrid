# Contributing to sqlalchemy-cubrid

Thank you for your interest in contributing! This document provides guidelines
and instructions for contributing to the project.

## Table of Contents

- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Docker Integration Testing](#docker-integration-testing)
- [Code Style](#code-style)
- [Pull Request Guidelines](#pull-request-guidelines)
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
# Run all offline tests
pytest test/ -v --ignore=test/test_integration.py --ignore=test/test_suite.py

# Run with coverage
pytest test/ -v --ignore=test/test_integration.py --ignore=test/test_suite.py \
  --cov=sqlalchemy_cubrid --cov-report=term-missing

# Run a specific test file
pytest test/test_compiler.py -v

# Run a specific test
pytest test/test_compiler.py::TestCubridSQLCompiler::test_select_limit -v
```

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

3. **Run the full test suite** and ensure all tests pass:
   ```bash
   make test
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
- Write a clear title and description explaining _what_ and _why_.
- Reference any related issues (e.g., `Fixes #42`).
- Update documentation if your change affects the public API.
- Update `CHANGELOG.md` with a summary of your change.

### Review Process

- All PRs require at least one review before merge.
- CI must pass (lint, offline tests, integration tests).
- Maintain backward compatibility unless explicitly approved.

---

## Reporting Issues

When reporting a bug, please include:

- Python version (`python --version`)
- SQLAlchemy version (`pip show sqlalchemy`)
- CUBRID server version
- CUBRID-Python driver version
- Minimal reproduction code
- Full traceback

For feature requests, describe the use case and expected behavior.

---

## Questions?

Open a [GitHub Discussion](https://github.com/cubrid-lab/sqlalchemy-cubrid/discussions)
or file an [issue](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues).
