.PHONY: help install lint format check-tool-versions check-docs-reason typecheck security check check-all test test-repo test-offline test-all integration integration-local docker-up docker-down changelog clean clean-all doctor release-check

PYTEST = python3 -m pytest
PYTHON = python3
RUFF = ruff
MYPY = $(PYTHON) -m mypy
BANDIT = bandit
SRC = sqlalchemy_cubrid
TESTS = test
LINT_PATHS = $(SRC) _sqlalchemy_cubrid_alembic.py $(TESTS) scripts demos samples docs/source
# make integration: the driver the suite connects with (pycubrid, the recommended
# pure-Python driver, via cubrid+pycubrid://; or cubriddb, the CUBRIDdb C extension,
# via cubrid://), host port for the run-owned CUBRID container, an optional fixed
# Compose project name (default: a fresh name per run), and how many seconds, on a
# signal, `docker compose up -d` gets to finish before SIGTERM and any step gets
# after SIGTERM before SIGKILL. See docs/DEVELOPMENT.md.
INTEGRATION_DRIVER ?= pycubrid
CUBRID_PORT ?= 33000
# Seconds make integration waits for the new server to answer SELECT 1 through the
# selected driver before it gives up (a fresh container needs about 20 seconds).
INTEGRATION_READY_TIMEOUT ?= 180
WAIT_FOR_CUBRID = $(PYTHON) -m scripts.wait_for_cubrid --timeout $(INTEGRATION_READY_TIMEOUT)
INTEGRATION_PROJECT ?=
INTEGRATION_STOP_GRACE ?= 10
# Run a command in its own session, ignoring INT/TERM/HUP, so that signals sent to
# the whole process group (Ctrl-C, a closed terminal, GNU timeout) cannot abort
# make integration's cleanup halfway.
RUN_DETACHED = $(PYTHON) -c 'import signal, subprocess, sys; [signal.signal(s, signal.SIG_IGN) for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)]; rc = subprocess.call(sys.argv[1:], start_new_session=True); sys.exit(128 - rc if rc < 0 else rc)'
# Exec a command as the leader of a new process group. `docker compose up -d` runs
# this way: a terminal Ctrl-C does not interrupt it, and stopping it also stops the
# Compose CLI plugin process it spawns. On a signal, cleanup first lets it finish,
# because the daemon completes a container create even after the client is killed,
# which would leave resources that `down -v` has already missed.
RUN_IN_NEW_GROUP = $(PYTHON) -c 'import os, sys; os.setpgid(0, 0); os.execvp(sys.argv[1], sys.argv[1:])'
# After a delay, send a signal to a process (to its whole group if it leads one).
SIGNAL_AFTER = $(PYTHON) -c 'import os, signal, sys, time; time.sleep(float(sys.argv[2])); pid = int(sys.argv[3]); os.kill(-pid if os.getpgid(pid) == pid else pid, getattr(signal, sys.argv[1]))'
# Wait until no process is left in a process group, then SIGKILL the group after a
# delay. The Compose plugin can outlive the `docker` CLI that started it, so cleanup
# must not start before the whole group is gone. Returns at once if the group does
# not exist (the step was not a group leader).
WAIT_GROUP = $(PYTHON) -c 'exec("import os, signal, sys, time\ngrace, pgid = float(sys.argv[1]), int(sys.argv[2])\ndef alive():\n    try:\n        os.killpg(pgid, 0)\n    except ProcessLookupError:\n        return False\n    return True\ndeadline = time.monotonic() + grace\nwhile alive() and time.monotonic() < deadline:\n    time.sleep(0.1)\nif alive():\n    os.killpg(pgid, signal.SIGKILL)\nwhile alive() and time.monotonic() < deadline + 5:\n    time.sleep(0.1)\n")'

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
	$(MYPY) $(SRC)/ _sqlalchemy_cubrid_alembic.py --config-file=pyproject.toml

security: ## Run security scans (bandit)
	$(BANDIT) -r $(SRC)/ _sqlalchemy_cubrid_alembic.py -c pyproject.toml

check: lint typecheck ## Run lint + typecheck

check-docs-reason: ## Check docs reasons and real event/workflow regressions
	$(PYTHON) -m doctest scripts/check_docs_reason.py -v
	$(PYTHON) -m unittest discover -s test -p 'test_docs_reason.py' -v

check-all: check security check-docs-reason ## Run lint + typecheck + security + docs gate tests

# Offline test lanes (#594). `repo` marks repository-tooling tests (Makefile
# recipes, signal handling, repo scripts; see REPO_TOOLING_MODULES in
# test/conftest.py). CI runs both lanes as required jobs.
test: ## Run the fast offline tests with coverage (no DB, no repo-tooling tests)
	$(PYTEST) $(TESTS)/ -v \
		-m "not integration and not repo" \
		--cov=$(SRC) \
		--cov-report=term-missing \
		--cov-fail-under=95

test-repo: ## Run the repository-tooling tests (Makefile, signal handling, repo scripts)
	$(PYTEST) $(TESTS)/ -v -m repo

test-offline: ## Run every offline test (fast + repo-tooling) with coverage
	$(PYTEST) $(TESTS)/ -v \
		-m "not integration" \
		--cov=$(SRC) \
		--cov-report=term-missing \
		--cov-fail-under=95

test-all: ## Run tests across all Python versions via tox
	tox

integration: ## Run integration tests (INTEGRATION_DRIVER=pycubrid|cubriddb) in a fresh, run-owned Docker Compose project and always clean it up
	@set -e; \
	case "$(INTEGRATION_DRIVER)" in \
		pycubrid) url_scheme="cubrid+pycubrid" ;; \
		cubriddb) url_scheme="cubrid" ;; \
		*) \
			echo "INTEGRATION_DRIVER must be pycubrid or cubriddb (got '$(INTEGRATION_DRIVER)'); nothing was started." >&2; \
			exit 2 ;; \
	esac; \
	project="$(INTEGRATION_PROJECT)"; \
	if [ -n "$$project" ]; then \
		case "$$project" in \
			[abcdefghijklmnopqrstuvwxyz0123456789]*) project_ok=1 ;; \
			*) project_ok= ;; \
		esac; \
		case "$$project" in *[!abcdefghijklmnopqrstuvwxyz0123456789_-]*) project_ok= ;; esac; \
		if [ -z "$$project_ok" ]; then \
			echo "INTEGRATION_PROJECT must match ^[a-z0-9][a-z0-9_-]*\$$ (got '$$project'); nothing was started." >&2; \
			exit 2; \
		fi; \
	else \
		project="sqlalchemy-cubrid-it-$$(date +%Y%m%d%H%M%S)-$$$$"; \
	fi; \
	probe_failed() { \
		status=$$?; \
		echo "Ownership check of Compose project '$$project' failed (status $$status); nothing was started." >&2; \
		exit "$$status"; \
	}; \
	label="label=com.docker.compose.project=$$project"; \
	existing_containers=$$(docker ps -aq --filter "$$label") || probe_failed; \
	existing_volumes=$$(docker volume ls -q --filter "$$label") || probe_failed; \
	existing_networks=$$(docker network ls -q --filter "$$label") || probe_failed; \
	all_volumes=$$(docker volume ls -q) || probe_failed; \
	existing_data_volume=$$(printf '%s\n' "$$all_volumes" | grep -Fx "$${project}_cubrid-data" || true); \
	if [ -n "$$existing_containers$$existing_volumes$$existing_networks$$existing_data_volume" ]; then \
		echo "Refusing to run: Compose project '$$project' already has containers, volumes or networks." >&2; \
		echo "make integration only starts and removes a project it creates; nothing was started or removed." >&2; \
		exit 1; \
	fi; \
	CUBRID_PORT="$(CUBRID_PORT)"; export CUBRID_PORT; \
	exec 3<&0; \
	child=; starting=; cleaning=; \
	run() { "$$@" <&3 & child=$$!; status=0; wait "$$child" || status=$$?; child=; return "$$status"; }; \
	stop_children() { \
		if [ -n "$$child" ]; then \
			if [ -n "$$starting" ]; then \
				echo "Letting docker compose up finish (up to $(INTEGRATION_STOP_GRACE)s) so that cleanup sees everything it created" >&2; \
				$(SIGNAL_AFTER) SIGTERM "$(INTEGRATION_STOP_GRACE)" "$$child" 2>/dev/null & timer=$$!; \
			else \
				kill -TERM "-$$child" 2>/dev/null || kill -TERM "$$child" 2>/dev/null || true; \
				$(SIGNAL_AFTER) SIGKILL "$(INTEGRATION_STOP_GRACE)" "$$child" 2>/dev/null & timer=$$!; \
			fi; \
			wait "$$child" 2>/dev/null || true; \
			kill -KILL "$$timer" 2>/dev/null || true; \
			wait "$$timer" 2>/dev/null || true; \
			$(WAIT_GROUP) "$(INTEGRATION_STOP_GRACE)" "$$child"; \
		fi; \
		for pid in $$(jobs -p); do \
			kill -TERM "-$$pid" 2>/dev/null || kill -TERM "$$pid" 2>/dev/null || true; \
		done; \
	}; \
	cleanup() { \
		original_status=$$1; \
		if [ -n "$$cleaning" ]; then return 0; fi; \
		cleaning=1; \
		trap '' INT TERM HUP; \
		trap - 0; \
		stop_children; \
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
	echo "Using run-owned Compose project '$$project' on host port $$CUBRID_PORT (driver: $(INTEGRATION_DRIVER))"; \
	starting=1; \
	run $(RUN_IN_NEW_GROUP) docker compose -p "$$project" up -d; \
	starting=; \
	CUBRID_TEST_URL="$$url_scheme://dba@localhost:$$CUBRID_PORT/testdb"; export CUBRID_TEST_URL; \
	echo "Waiting for CUBRID to be ready (up to $(INTEGRATION_READY_TIMEOUT)s)..."; \
	run $(WAIT_FOR_CUBRID); \
	run $(PYTEST) $(TESTS)/ -m integration -v

integration-local: ## Run integration tests against an already-running CUBRID (set CUBRID_TEST_URL; no Docker)
	@if [ -z "$$CUBRID_TEST_URL" ]; then \
		echo "ERROR: set CUBRID_TEST_URL (e.g. cubrid+pycubrid://dba@localhost:33000/testdb) to point at a running CUBRID"; \
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

release-check: ## Read-only release consistency gate (run by prepare-release.yml and release.yml). Usage: make release-check VERSION=x.y.z
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
