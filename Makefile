.PHONY: help install lint format check-tool-versions check-docs-reason typecheck security check check-all test test-all integration integration-local docker-up docker-down changelog clean clean-all doctor release-check

PYTEST = python3 -m pytest
PYTHON = python3
RUFF = ruff
MYPY = $(PYTHON) -m mypy
BANDIT = bandit
SRC = sqlalchemy_cubrid
TESTS = test
LINT_PATHS = $(SRC) $(TESTS) scripts demos samples docs/source
# make integration: host port for the run-owned CUBRID container, and an optional
# fixed Compose project name (default: a fresh name per run; see docs/DEVELOPMENT.md).
CUBRID_PORT ?= 33000
INTEGRATION_PROJECT ?=
# Run a command in its own session, ignoring INT/TERM/HUP, so that signals sent to
# the whole process group (Ctrl-C, a closed terminal, GNU timeout) cannot abort
# make integration's cleanup halfway.
RUN_DETACHED = $(PYTHON) -c 'import signal, subprocess, sys; [signal.signal(s, signal.SIG_IGN) for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)]; rc = subprocess.call(sys.argv[1:], start_new_session=True); sys.exit(128 - rc if rc < 0 else rc)'

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install in development mode with all dependencies
	pip install -e ".[dev]"
	pre-commit install

check-tool-versions: ## Detect local and CI tool-version drift
	$(PYTHON) scripts/check_tool_versions.py

lint: check-tool-versions ## Run linter and format checks
	$(RUFF) check $(LINT_PATHS)
	$(RUFF) format --check $(LINT_PATHS)

format: ## Auto-fix lint issues and format code
	$(RUFF) check --fix $(LINT_PATHS)
	$(RUFF) format $(LINT_PATHS)

typecheck: ## Run mypy type checking
	$(PYTHON) -c 'import platform; from importlib.metadata import version; print("Python:", platform.python_version()); [print(name + ":", version(name)) for name in ("SQLAlchemy", "alembic", "mypy")]'
	$(MYPY) $(SRC)/ --config-file=pyproject.toml

security: ## Run security scans (bandit)
	$(BANDIT) -r $(SRC)/ -c pyproject.toml

check: lint typecheck ## Run lint + typecheck

check-docs-reason: ## Check docs reasons and real event/workflow regressions
	$(PYTHON) -m doctest scripts/check_docs_reason.py -v
	$(PYTHON) -m unittest discover -s test -p 'test_docs_reason.py' -v

check-all: check security check-docs-reason ## Run lint + typecheck + security + docs gate tests

test: ## Run offline tests with coverage (no DB required)
	$(PYTEST) $(TESTS)/ -v \
		-m "not integration" \
		--cov=$(SRC) \
		--cov-report=term-missing \
		--cov-fail-under=95

test-all: ## Run tests across all Python versions via tox
	tox

integration: ## Run integration tests in a fresh, run-owned Docker Compose project and always clean it up
	@set -e; \
	project="$(INTEGRATION_PROJECT)"; \
	if [ -z "$$project" ]; then project="sqlalchemy-cubrid-it-$$(date +%Y%m%d%H%M%S)-$$$$"; fi; \
	label="label=com.docker.compose.project=$$project"; \
	existing_containers=$$(docker ps -aq --filter "$$label"); \
	existing_volumes=$$(docker volume ls -q --filter "$$label"); \
	existing_networks=$$(docker network ls -q --filter "$$label"); \
	if [ -n "$$existing_containers$$existing_volumes$$existing_networks" ] || \
		docker volume inspect "$${project}_cubrid-data" >/dev/null 2>&1; then \
		echo "Refusing to run: Compose project '$$project' already has containers, volumes or networks." >&2; \
		echo "make integration only starts and removes a project it creates; nothing was started or removed." >&2; \
		exit 1; \
	fi; \
	CUBRID_PORT="$(CUBRID_PORT)"; export CUBRID_PORT; \
	child=; cleaning=; \
	run() { "$$@" & child=$$!; status=0; wait "$$child" || status=$$?; child=; return "$$status"; }; \
	cleanup() { \
		original_status=$$1; \
		if [ -n "$$cleaning" ]; then return 0; fi; \
		cleaning=1; \
		trap '' INT TERM HUP; \
		trap - 0; \
		if [ -n "$$child" ]; then kill "$$child" 2>/dev/null || true; wait "$$child" 2>/dev/null || true; fi; \
		if $(RUN_DETACHED) docker compose -p "$$project" down -v; then \
			cleanup_status=0; \
		else \
			cleanup_status=$$?; \
			echo "Docker cleanup of Compose project '$$project' failed (status $$cleanup_status)" >&2; \
		fi; \
		if [ "$$original_status" -ne 0 ]; then exit "$$original_status"; fi; \
		exit "$$cleanup_status"; \
	}; \
	trap 'cleanup $$?' 0; \
	trap 'echo "Received SIGINT; cleaning up" >&2; cleanup 130' INT; \
	trap 'echo "Received SIGTERM; cleaning up" >&2; cleanup 143' TERM; \
	trap 'echo "Received SIGHUP; cleaning up" >&2; cleanup 129' HUP; \
	echo "Using run-owned Compose project '$$project' on host port $$CUBRID_PORT"; \
	run docker compose -p "$$project" up -d; \
	echo "Waiting for CUBRID to be ready..."; \
	run sleep 10; \
	CUBRID_TEST_URL="cubrid://dba@localhost:$$CUBRID_PORT/testdb"; export CUBRID_TEST_URL; \
	run $(PYTEST) $(TESTS)/ -m integration -v

integration-local: ## Run integration tests against an already-running CUBRID (set CUBRID_TEST_URL; no Docker)
	@if [ -z "$$CUBRID_TEST_URL" ]; then \
		echo "ERROR: set CUBRID_TEST_URL (e.g. cubrid://dba@localhost:33000/testdb) to point at a running CUBRID"; \
		exit 1; \
	fi
	$(PYTEST) $(TESTS)/ -m integration -v

docker-up: ## Start CUBRID Docker container
	docker compose up -d
	@echo "CUBRID container starting... Use 'docker compose logs -f' to monitor."

docker-down: ## Stop and remove CUBRID Docker container
	docker compose down -v

changelog: ## Generate changelog with git-cliff
	git-cliff --output CHANGELOG.md

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info .pytest_cache/ .coverage .ruff_cache/ __pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true

clean-all: clean ## Remove all artifacts including .mypy_cache and .tox
	rm -rf .mypy_cache/ .tox/ htmlcov/

doctor: ## Check development environment
	@echo "Checking development environment..."
	@python3 --version || echo "ERROR: python3 not found"
	@$(RUFF) --version || echo "ERROR: ruff not found"
	@$(MYPY) --version || echo "ERROR: mypy not found"
	@$(BANDIT) --version || echo "ERROR: bandit not found"
	@pre-commit --version || echo "ERROR: pre-commit not found"
	@echo "All checks passed!"

release-check: ## Read-only pre-tag release gate (no commit/tag). Usage: make release-check VERSION=x.y.z
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
