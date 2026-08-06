.PHONY: help install lint format typecheck security check check-all test test-all integration docker-up docker-down changelog clean clean-all doctor release

PYTEST = python3 -m pytest
RUFF = ruff
MYPY = mypy
BANDIT = bandit
SRC = sqlalchemy_cubrid
TESTS = test

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install in development mode with all dependencies
	pip install -e ".[dev]"
	pre-commit install

lint: ## Run linter and format checks
	$(RUFF) check $(SRC)/ $(TESTS)/
	$(RUFF) format --check $(SRC)/ $(TESTS)/

format: ## Auto-fix lint issues and format code
	$(RUFF) check --fix $(SRC)/ $(TESTS)/
	$(RUFF) format $(SRC)/ $(TESTS)/

typecheck: ## Run mypy type checking
	$(MYPY) $(SRC)/ --config-file=pyproject.toml

security: ## Run security scans (bandit)
	$(BANDIT) -r $(SRC)/ -c pyproject.toml

check: lint typecheck ## Run lint + typecheck

check-all: check security ## Run lint + typecheck + security

test: ## Run offline tests with coverage (no DB required)
	$(PYTEST) $(TESTS)/ -v \
		--ignore=$(TESTS)/test_integration.py \
		--ignore=$(TESTS)/test_suite.py \
		--ignore=$(TESTS)/test_aio_integration.py \
		--cov=$(SRC) \
		--cov-report=term-missing \
		--cov-fail-under=95

test-all: ## Run tests across all Python versions via tox
	tox

integration: docker-up ## Run integration tests against CUBRID Docker
	@echo "Waiting for CUBRID to be ready..."
	@sleep 10
	CUBRID_TEST_URL="cubrid://dba@localhost:33000/testdb" \
		$(PYTEST) $(TESTS)/test_integration.py -v
	$(MAKE) docker-down

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

release: ## Bump version + promote CHANGELOG + commit + tag. Usage: make release VERSION=x.y.z
	@if [ -z "$(VERSION)" ]; then echo "Usage: make release VERSION=1.7.0"; exit 1; fi
	@git diff --quiet || { echo "ERROR: Working tree is dirty. Commit or stash first."; exit 1; }
	@[ "$$(git branch --show-current)" = "main" ] || { echo "ERROR: Must be on main branch."; exit 1; }
	@CURRENT=$$(python3 -c "from $(SRC) import __version__; print(__version__)" 2>/dev/null) || \
		{ echo "ERROR: Cannot import $(SRC). Run 'make install' first."; exit 1; }
	@if [ "$$CURRENT" = "$(VERSION)" ]; then echo "Version is already $(VERSION)"; exit 1; fi
	@echo "Bumping $$CURRENT → $(VERSION)..."
	@TODAY=$$(date +%Y-%m-%d) && \
		perl -pi -e 's/__version__ = ".*"/__version__ = "$(VERSION)"/' $(SRC)/__init__.py && \
		perl -pi -e "s/## \[Unreleased\]/## [Unreleased]\n\n## [$(VERSION)] - $$TODAY/" CHANGELOG.md
	@git add $(SRC)/__init__.py CHANGELOG.md
	@git commit -m "release: v$(VERSION)"
	@git tag "v$(VERSION)"
	@echo ""
	@echo "Done. Review the diff, then push:"
	@echo "  git push origin main v$(VERSION)"
