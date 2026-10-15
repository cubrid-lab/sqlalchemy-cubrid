# Testing and CI guide

> Moved from the root [AGENTS.md](../../AGENTS.md) (#907). Owner: sqlalchemy-cubrid maintainers.
> Every rule in the root file still applies. Scope: Test layout, test stats, how tests run, workflows and the CI tiers. [docs/CI_POLICY.md](../CI_POLICY.md) owns the exact cells.

## Test Structure

Representative core test modules (not exhaustive; list `test/` for the current set,
including repository-tooling, fuzz, differential and Alembic tests):

```
test/
├── conftest.py              # Fixtures: mock dialect, engine, connection
├── test_compiler.py         # SQL compilation (SELECT, JOIN, CAST, LIMIT, DML extensions)
├── test_types.py            # Type system (all type compilations, reflection)
├── test_dialect_offline.py  # Dialect (reflection stubs, connection, isolation)
├── test_base.py             # ExecutionContext, IdentifierPreparer
├── test_requirements.py     # SA requirement flags (parametrized)
├── test_alembic.py          # Alembic CubridImpl import/registry
├── test_dialects.py         # Edge cases
├── test_pycubrid_dialect.py # PyCubridDialect (pure Python driver variant)
├── test_integration.py      # Live DB tests (skipped offline)
└── test_suite.py            # SA test suite runner (skipped offline)
```

### Test Stats

- Large and growing offline and integration suites; exact counts shift with every PR, so see the `offline-tests` / `integration-tests` CI job output for current numbers rather than a hardcoded snapshot here
- Coverage threshold: 95% (CI-enforced, `--cov-fail-under=95` in the `offline-tests` job)
- A handful of defensive fallback branches are intentionally unreachable in normal operation (SA-version-specific compatibility shims, exhaustive-but-unreachable `else` arms); see `--cov=sqlalchemy_cubrid --cov-report=term-missing` output (or `make test`) for current line numbers instead of a pinned list

### Running Tests

Most tests are **offline** — they mock the CUBRID connection and test SQL compilation,
type mapping, and reflection logic without a database. Tests that need a live CUBRID
instance carry the `integration` marker (`test_integration.py`, `test_aio_integration.py`,
`test_suite.py` and several contract, fuzz and regression modules); the offline lanes
deselect them with `-m "not integration"`.

## CI/CD

### Workflows

| File | Trigger | Purpose |
|---|---|---|
| `.github/workflows/ci.yml` | PR, main, weekly, manual | Full offline suite on PRs and representative integration; see docs/CI_POLICY.md |
| `.github/workflows/integration-full.yml` | Manual dispatch, release workflow_call | Full supported compatibility matrix |
| `.github/workflows/release-please.yml` | Push to main, manual dispatch | Prepare the release PR; compose generated and curated notes; never publish |
| `.github/workflows/publish-pypi.yml` | Push to main; recovery dispatch (`resume` / `verify-only` / `dry-run`) | Detect a merged release, then matrix, build, tag + GitHub Release + PyPI, cookbook verification, summary |

### CI Matrix

Routine CI is tiered: pull requests run one representative cell, main and
changed-weekly runs cover the oldest/newest supported Python and CUBRID endpoints,
and the full integration matrix runs only on manual dispatch and every release
(no automatic nightly full matrix). The exact cells, change classification and
gate requirements live in [CI policy](../CI_POLICY.md); check it rather than
copying versions here.
