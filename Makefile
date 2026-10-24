.PHONY: help install doctor check-tool-versions lint format-check format typecheck security check-docs-reason check check-all agent-eval-check verify test test-fast test-repo test-offline test-all integration integration-local docker-up docker-down docker-clean docker-fix-db-host changelog clean clean-all release-check

# Every tool runs through the same interpreter, and each can be overridden from the
# command line or the environment, e.g. `make check PYTHON=.venv/bin/python`.
PYTHON ?= python3
PYTEST ?= $(PYTHON) -m pytest
RUFF ?= $(PYTHON) -m ruff
MYPY ?= $(PYTHON) -m mypy
BANDIT ?= $(PYTHON) -m bandit
PRE_COMMIT ?= $(PYTHON) -m pre_commit
SRC = sqlalchemy_cubrid
TESTS = test
LINT_PATHS = $(SRC) _sqlalchemy_cubrid_alembic.py $(TESTS) scripts demos samples docs/source
# make integration: the driver the suite connects with (pycubrid, the recommended
# pure-Python driver, via cubrid+pycubrid://; or cubriddb, the CUBRIDdb C extension,
# via cubrid://), an optional fixed Compose project name (default: a fresh name per
# run), and how many seconds, on a signal, `docker compose up -d` gets to finish
# before SIGTERM and any step gets after SIGTERM before SIGKILL.
# scripts/run_integration.py owns the lifecycle; see docs/DEVELOPMENT.md.
INTEGRATION_DRIVER ?= pycubrid
# Where make integration writes junit.xml, summary.json, environment.json and (after a
# failure) service.log (#1020); relative to the repository root.
INTEGRATION_RESULTS ?= test-results/integration
# Host port of the CUBRID broker, published on 127.0.0.1 only, for make docker-up
# and the run-owned make integration container (#1008). CUBRID_PORT is the
# deprecated former name, still honoured when CUBRID_TEST_PORT is not set; the
# recipes that use the port then warn (other tools set CUBRID_PORT too, so a
# parse-time warning would fire on every target).
ifeq ($(origin CUBRID_TEST_PORT),undefined)
ifneq ($(CUBRID_PORT),)
CUBRID_TEST_PORT := $(CUBRID_PORT)
CUBRID_PORT_WARNING = $(warning CUBRID_PORT is deprecated; use CUBRID_TEST_PORT)
endif
endif
# make docker-up passes the port to Compose only when it was given (on the make
# command line, in the shell, or through CUBRID_PORT); otherwise Compose resolves it
# itself, from .env or its own 33000 default, exactly as a direct `docker compose up`.
DOCKER_UP_PORT_ENV := $(if $(filter undefined,$(origin CUBRID_TEST_PORT)),,CUBRID_TEST_PORT="$(CUBRID_TEST_PORT)" )
CUBRID_TEST_PORT ?= 33000
# Seconds make integration waits for the new server to answer SELECT 1 through the
# selected driver before it gives up (a fresh container needs about 20 seconds).
INTEGRATION_READY_TIMEOUT ?= 180
WAIT_FOR_CUBRID ?= $(PYTHON) -m scripts.wait_for_cubrid --timeout $(INTEGRATION_READY_TIMEOUT)
INTEGRATION_PROJECT ?=
INTEGRATION_STOP_GRACE ?= 10

##@ Setup

help: ## Show this help message, grouped by purpose
	@awk 'BEGIN {FS = ":.*?## "} \
		/^##@ / {printf "\n\033[1m%s\033[0m\n", substr($$0, 5)} \
		/^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install in development mode with the dev dependency group (pip >= 25.1)
	pip install --upgrade "pip>=25.1"
	pip install -e . --group dev
	$(PRE_COMMIT) install

# Every tool is checked before the verdict, so one run lists everything missing.
doctor: ## Check the required tooling; fails if a tool is missing, broken or not the pinned version
	@echo "Checking development environment..."
	@status=0; \
	$(PYTHON) -c 'import sys; print("Python", sys.version.split()[0]); sys.exit(sys.version_info < (3, 11))' \
		|| { echo "ERROR: '$(PYTHON)' is missing or older than Python 3.11" >&2; status=1; }; \
	for tool in "$(PYTEST)" "$(RUFF)" "$(MYPY)" "$(BANDIT)" "$(PRE_COMMIT)"; do \
		$$tool --version || { echo "ERROR: '$$tool --version' failed" >&2; status=1; }; \
	done; \
	$(PYTHON) scripts/check_tool_versions.py || status=1; \
	if [ $$status -ne 0 ]; then \
		echo "ERROR: required tooling is missing or invalid; run 'make install' in the project environment" >&2; \
		exit $$status; \
	fi; \
	echo "All checks passed!"

##@ Quality (static checks; only format modifies files)

check-tool-versions: ## Detect local and CI tool-version drift
	$(PYTHON) scripts/check_tool_versions.py

lint: check-tool-versions ## Run the Ruff linter (never modifies files)
	$(RUFF) check $(LINT_PATHS)

format-check: check-tool-versions ## Check Ruff formatting (never modifies files)
	$(RUFF) format --check $(LINT_PATHS)

format: check-tool-versions ## Auto-fix lint issues and format code (the only mutating target)
	$(RUFF) check --fix $(LINT_PATHS)
	$(RUFF) format $(LINT_PATHS)

typecheck: ## Run mypy type checking
	$(PYTHON) -c 'import platform; from importlib.metadata import version; print("Python:", platform.python_version()); [print(name + ":", version(name)) for name in ("SQLAlchemy", "alembic", "mypy")]'
	$(MYPY) $(SRC)/ _sqlalchemy_cubrid_alembic.py --config-file=pyproject.toml

security: ## Run security scans (bandit)
	$(BANDIT) -r $(SRC)/ _sqlalchemy_cubrid_alembic.py -c pyproject.toml

check-docs-reason: ## Check docs reasons and real event/workflow regressions
	$(PYTHON) -m doctest scripts/check_docs_reason.py -v
	$(PYTHON) -m unittest discover -s test -p 'test_docs_reason.py' -v

check: lint format-check typecheck security check-docs-reason ## Complete non-test quality gate: lint, format-check, typecheck, security, check-docs-reason

# Deprecated alias of `check`, kept for one minor release (#1009).
check-all: check ## Deprecated alias of check (removed after the next minor release)
	@echo "WARNING: 'make check-all' is deprecated and will be removed after the next minor release; use 'make check'." >&2

agent-eval-check: ## Validate the agent-evals tasks and re-grade their fixtures (offline; no model, no DB)
	$(PYTHON) scripts/agent_eval.py validate
	$(PYTHON) scripts/agent_eval.py check

##@ Tests (offline; no Docker, no database)

verify: check test ## Run check, then the complete offline suite (no Docker)

# Offline test lanes (#594). `repo` marks repository-tooling tests (Makefile
# recipes, signal handling, repo scripts; see REPO_TOOLING_MODULES in
# test/conftest.py). CI runs the fast and repository-tooling lanes as required jobs.
# `make test` writes test-results/test/{junit.xml,coverage.xml,summary.json} (#1019).
# pytest's own status is kept, the helper turns the files into summary.json and the
# final console line, and the recipe fails when either one failed.
TEST_RESULTS = test-results/test
test: ## Run every offline test (fast + repository-tooling) with coverage; writes test-results/test/
	@case "$(TEST_RESULTS)" in ""|.|./|..|../|/) \
		echo "ERROR: refusing to use TEST_RESULTS='$(TEST_RESULTS)'" >&2; exit 2;; esac
	rm -rf -- "$(TEST_RESULTS)"
	mkdir -p -- "$(TEST_RESULTS)"
	@status=0; \
	$(PYTEST) $(TESTS)/ -v \
		-m "not integration" \
		--junitxml="$(TEST_RESULTS)/junit.xml" \
		--cov=$(SRC) \
		--cov-report=term-missing \
		--cov-report=xml:"$(TEST_RESULTS)/coverage.xml" \
		--cov-fail-under=95 || status=$$?; \
	$(PYTHON) -m scripts.report_test_results --lane test \
		--junit "$(TEST_RESULTS)/junit.xml" --coverage "$(TEST_RESULTS)/coverage.xml" \
		--threshold 95 --pytest-exit $$status --output "$(TEST_RESULTS)/summary.json" \
		|| { [ $$status -ne 0 ] && exit $$status || exit 1; }; \
	exit $$status

test-offline: test ## Alias of test

test-fast: ## Run the fast offline tests with coverage (no repository-tooling tests)
	$(PYTEST) $(TESTS)/ -v \
		-m "not integration and not repo" \
		--cov=$(SRC) \
		--cov-report=term-missing \
		--cov-fail-under=95

test-repo: ## Run the repository-tooling tests (Makefile, signal handling, repo scripts)
	$(PYTEST) $(TESTS)/ -v -m repo

test-all: ## Run tests across all Python versions via tox
	tox

##@ Integration (Docker)

# scripts/run_integration.py owns driver validation, the run-owned Compose project,
# ownership checks, readiness, signal handling, cleanup and the exit status. `exec`
# makes it the recipe's only process, so make's signals reach it directly.
integration: ## Run integration tests (INTEGRATION_DRIVER=pycubrid|cubriddb) in a fresh, run-owned Docker Compose project and always clean it up
	@exec $(PYTHON) scripts/run_integration.py $(CUBRID_PORT_WARNING)\
		--driver="$(INTEGRATION_DRIVER)" \
		--port="$(CUBRID_TEST_PORT)" \
		--project="$(INTEGRATION_PROJECT)" \
		--ready-timeout="$(INTEGRATION_READY_TIMEOUT)" \
		--stop-grace="$(INTEGRATION_STOP_GRACE)" \
		--wait="$(WAIT_FOR_CUBRID)" \
		--test="$(PYTEST) $(TESTS)/ -m integration -v" \
		--results-dir="$(INTEGRATION_RESULTS)" \
		--command="make integration INTEGRATION_DRIVER=$(INTEGRATION_DRIVER)"

integration-local: ## Run integration tests against an already-running CUBRID (set CUBRID_TEST_URL; no Docker)
	@if [ -z "$$CUBRID_TEST_URL" ]; then \
		echo "ERROR: set CUBRID_TEST_URL (e.g. cubrid+pycubrid://dba@localhost:33000/testdb) to point at a running CUBRID"; \
		exit 1; \
	fi
	$(PYTEST) $(TESTS)/ -m integration -v

# The manual stack (Compose project named after the checkout directory, or
# COMPOSE_PROJECT_NAME). Only docker-clean deletes its data volumes (#1008).
docker-up: ## Start the local CUBRID test database (broker on 127.0.0.1:CUBRID_TEST_PORT, else .env, else 33000)
	$(CUBRID_PORT_WARNING)$(DOCKER_UP_PORT_ENV)docker compose up -d
	@echo "CUBRID container starting on $$(docker compose port cubrid 33000 2>/dev/null || echo 'the configured port')... Use 'docker compose logs -f' to monitor."

docker-down: ## Stop and remove the local CUBRID container and network; keeps the test data volumes
	docker compose down

docker-clean: ## Remove the local CUBRID container, network and test data volumes (deletes the test data)
	docker compose down -v

# A volume created before docker-compose.yml set CUBRID_DB_HOST registers testdb
# for the creating container's ID, which a recreated container cannot resolve
# (-353, #997). Rewrite only that host field to localhost; the data is kept.
# The file is rewritten in place to keep its owner and mode, after the first
# run saves a copy next to it.
docker-fix-db-host: ## Repair a running container's volume that registers testdb for a stale host (keeps the data)
	docker compose exec -T -u root cubrid sh -c 'set -e; \
		f="$$CUBRID_DATABASES/databases.txt"; t="$$(mktemp)"; \
		[ -e "$$f.before-fix-db-host" ] || cp -p "$$f" "$$f.before-fix-db-host"; \
		awk '"'"'BEGIN { OFS = "\t" } $$1 == "testdb" { $$3 = "localhost" } { print }'"'"' "$$f" > "$$t"; \
		cat "$$t" > "$$f"; rm -f "$$t"; \
		echo "Saved the previous file as $$f.before-fix-db-host"; \
		grep "^testdb[[:space:]]" "$$f"'

##@ Maintenance

changelog: ## Generate changelog with git-cliff
	git-cliff --output CHANGELOG.md

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info .pytest_cache/ .coverage .ruff_cache/ __pycache__/ test-results/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true

clean-all: clean ## Remove all artifacts including .mypy_cache and .tox
	rm -rf .mypy_cache/ .tox/ htmlcov/

release-check: ## Read-only release consistency gate (run by release-please.yml and publish-pypi.yml). Usage: make release-check VERSION=x.y.z
	@if [ -z "$(VERSION)" ]; then echo "Usage: make release-check VERSION=x.y.z"; exit 1; fi
	@ACTUAL=$$($(PYTHON) -c 'import ast, pathlib; tree = ast.parse(pathlib.Path("$(SRC)/__init__.py").read_text()); print(next(n.value.value for n in ast.walk(tree) if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name) and t.id == "__version__"))') || exit 1; \
		if [ "$$ACTUAL" != "$(VERSION)" ]; then echo "ERROR: $(SRC).__version__ is $$ACTUAL, expected $(VERSION)"; exit 1; fi; \
		echo "OK: $(SRC).__version__ == $(VERSION)"
	$(PYTHON) scripts/lint_changelog.py
	$(PYTHON) scripts/extract_release_notes.py v$(VERSION)
	rm -f RELEASE_NOTES.md
	rm -rf dist
	$(PYTHON) -m build
	$(PYTHON) -m twine check dist/*
