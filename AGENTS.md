# AGENTS.md

Project knowledge base for AI coding agents.

## Project Overview

**sqlalchemy-cubrid** is a SQLAlchemy 2.0 dialect for the CUBRID relational database.
It provides SQL compilation, type mapping, schema reflection, DDL/DML extensions,
Alembic migration support, and PEP 561 typing.

- **Language**: Python 3.10+
- **Framework**: SQLAlchemy 2.0 – 2.1
- **License**: MIT
- **Version**: 1.4.3.dev0 (Production/Stable)

## Architecture

```mermaid
graph TD
    root["sqlalchemy_cubrid/ (Main package, 12 Python modules + py.typed)"]
    init["__init__.py - Public API exports types, insert(), merge(), replace(), trace_query(), __version__"]
    compat["_compat.py - SQLAlchemy private API compatibility helpers"]
    base["base.py - CubridExecutionContext, CubridIdentifierPreparer"]
    compiler["compiler.py - CubridSQLCompiler, CubridDDLCompiler, CubridTypeCompiler"]
    dialect["dialect.py - CubridDialect reflection, connection, isolation levels"]
    pycubrid["pycubrid_dialect.py - PyCubridDialect pure Python driver variant"]
    aio["aio_pycubrid_dialect.py - PyCubridAsyncDialect async driver variant"]
    dml["dml.py - ON DUPLICATE KEY UPDATE (Insert), MERGE statement"]
    trace["trace.py - Query tracing helper"]
    types["types.py - CUBRID type system numeric, string, LOB, collection"]
    req["requirements.py - SA 2.0 test requirement flags (40+ properties)"]
    alembic["alembic_impl.py - CubridImpl for Alembic migrations"]
    typed["py.typed - PEP 561 marker"]

    root --> init
    root --> compat
    root --> base
    root --> compiler
    root --> dialect
    root --> pycubrid
    root --> aio
    root --> dml
    root --> trace
    root --> types
    root --> req
    root --> alembic
    root --> typed
```

### Module Responsibilities

| Module | Role |
|---|---|
| `dialect.py` | Main dialect class. Handles `create_connect_args`, reflection (`get_columns`, `get_pk_constraint`, `get_foreign_keys`, `get_indexes`, `get_table_comment`, etc.), isolation levels, `import_dbapi()`. |
| `pycubrid_dialect.py` | `PyCubridDialect` — subclasses `CubridDialect` for the pycubrid pure Python driver. Overrides `import_dbapi()`, `create_connect_args()`, `on_connect()`, `do_ping()`. |
| `aio_pycubrid_dialect.py` | `PyCubridAsyncDialect` — async pycubrid variant for `create_async_engine()` / `AsyncSession`, registered as `cubrid.aiopycubrid`. |
| `compiler.py` | SQL compilation. `visit_cast`, `limit_clause`, `for_update_clause`, `update_limit_clause`, DDL (`get_column_specification`, `AUTO_INCREMENT`, `COMMENT`), type compilation for all CUBRID types. |
| `dml.py` | Custom DML constructs: `insert()` with `.on_duplicate_key_update()`, `merge()` with `.using()`, `.on()`, `.when_matched_then_update()`, `.when_not_matched_then_insert()`. |
| `types.py` | Type classes: `STRING`, `BIT`, `CLOB`, `SET`, `MULTISET`, `SEQUENCE`, `MONETARY`, `OBJECT`, plus standard type overrides. |
| `base.py` | Execution context (`get_lastrowid`), identifier preparer (lowercase folding, 254-char max, reserved words). |
| `trace.py` | `trace_query()` helper that enables CUBRID tracing around a statement and returns trace output. |
| `requirements.py` | Test requirement flags — marks what CUBRID does/doesn't support for SA's test suite. |
| `alembic_impl.py` | `CubridImpl(DefaultImpl)` with `transactional_ddl = False`. Auto-discovered via `alembic.ddl` entry point. |
| `_compat.py` | Internal compatibility helpers that wrap SQLAlchemy private APIs used by the dialect/compiler. |

### Entry Points (pyproject.toml)

```toml
[project.entry-points."sqlalchemy.dialects"]
cubrid = "sqlalchemy_cubrid.dialect:CubridDialect"
"cubrid.cubrid" = "sqlalchemy_cubrid.dialect:CubridDialect"
"cubrid.pycubrid" = "sqlalchemy_cubrid.pycubrid_dialect:PyCubridDialect"
"cubrid.aiopycubrid" = "sqlalchemy_cubrid.aio_pycubrid_dialect:PyCubridAsyncDialect"
[project.entry-points."alembic.ddl"]
cubrid = "sqlalchemy_cubrid.alembic_impl:CubridImpl"
```

## Development

### Setup

```bash
git clone https://github.com/cubrid-lab/sqlalchemy-cubrid.git
cd sqlalchemy-cubrid
make install          # pip install -e ".[dev]" + pytest-cov + pre-commit + tox
```

### Key Commands

```bash
make test             # Offline tests with 95% coverage threshold
make lint             # ruff check + format
make format           # Auto-fix lint/format
make integration      # Docker → integration tests → cleanup
make test-all         # tox across Python 3.10–3.14
```

### Test Commands (manual)

```bash
# Offline (no DB needed) — this is the primary test command
pytest test/ -v --ignore=test/test_integration.py --ignore=test/test_suite.py \
  --cov=sqlalchemy_cubrid --cov-report=term-missing --cov-fail-under=95

# Integration (requires Docker)
docker compose up -d
export CUBRID_TEST_URL="cubrid://dba@localhost:33000/testdb"
pytest test/test_integration.py -v
```

### Docker

```bash
docker compose up -d                          # Default CUBRID 11.2
CUBRID_VERSION=11.4 docker compose up -d      # Specific version
docker compose down -v                        # Cleanup
```

## Code Conventions

### Style

- **Linter/Formatter**: Ruff
- **Line length**: 100 characters
- **Target Python**: 3.10+
- **Imports**: `from __future__ import annotations` in every module
- **Type hints**: Full typing; PEP 561 compliant (`py.typed`)
- **super()**: Always `super().__init__()`, never `super(ClassName, self)`

### Naming

- Classes: `CubridDialect`, `CubridSQLCompiler`, `CubridTypeCompiler`, `CubridDDLCompiler`
- Test classes: `TestCubridSQLCompiler`, `TestCubridTypes`, etc.
- Test files: `test/test_*.py`

### Patterns to Follow

- All SA dialect methods use `@cache_anon_map` / `@reflection.cache` where appropriate
- Reflection methods accept `**kw` and use `text()` for parameterized queries (no f-string SQL)
- Type compiler methods: `visit_TYPENAME(self, type_, **kw)` returning SQL string
- `supports_statement_cache = True` — required for SA 2.0

### Anti-Patterns (Never Do)

- No `as any`, `@ts-ignore` equivalents — no type suppression
- No f-string interpolation in SQL queries (SQL injection risk)
- No `super(ClassName, self)` — use `super()` only
- No Python 2 constructs (`basestring`, `getargspec`, etc.)
- No empty `except` blocks

## Development Workflow (cubrid-lab org standard)

All non-trivial work across cubrid-lab repositories MUST follow this 4-phase cycle:

1. **Oracle Design Review** — Consult Oracle before implementation to validate architecture, API surface, and approach. Raise concerns early.
2. **Implementation** — Build the feature/fix with tests. Follow existing codebase patterns.
3. **Documentation Update** — Update ALL affected docs (README, CHANGELOG, ROADMAP, API docs, SUPPORT_MATRIX, PRD, etc.) in the same PR or as an immediate follow-up. Code without doc updates is incomplete.
4. **Oracle Post-Implementation Review** — Consult Oracle to review the completed work for correctness, edge cases, and consistency before merging.

Skipping any phase requires explicit justification. Trivial changes (typos, single-line fixes) may skip phases 1 and 4.

5. **All changes to `main` MUST go through a Pull Request** with at least one review. No direct pushes.

## Test Structure

```
test/
├── conftest.py              # Fixtures: mock dialect, engine, connection
├── test_compiler.py         # SQL compilation (SELECT, JOIN, CAST, LIMIT, etc.)
├── test_types.py            # Type system (all type compilations, reflection)
├── test_dialect_offline.py  # Dialect (reflection stubs, connection, isolation)
├── test_base.py             # ExecutionContext, IdentifierPreparer
├── test_requirements.py     # SA requirement flags (parametrized)
├── test_dml.py              # ON DUPLICATE KEY UPDATE, MERGE compilation
├── test_alembic.py          # Alembic CubridImpl import/registry
├── test_dialects.py         # Edge cases
├── test_pycubrid_dialect.py # PyCubridDialect (pure Python driver variant)
├── test_integration.py      # Live DB tests (skipped offline)
└── test_suite.py            # SA test suite runner (skipped offline)
```

### Test Stats

- **619 offline tests + 35 sync integration tests + 16 async integration tests**, **~98.26% offline coverage**
- Coverage threshold: 95% (CI-enforced)
- 6 unreachable lines (defensive fallbacks): `compiler.py:72`, `compiler.py:84`, `compiler.py:298-300`, `dml.py:310`

### Running Tests

Most tests are **offline** — they mock the CUBRID connection and test SQL compilation,
type mapping, and reflection logic without a database. Only `test_integration.py` and
`test_suite.py` need a live CUBRID instance.

## CUBRID-Specific Knowledge

### Key Differences from MySQL/PostgreSQL

- **No RETURNING** — `INSERT/UPDATE/DELETE ... RETURNING` not supported
- **No native BOOLEAN** — mapped to `SMALLINT` (0/1)
- **JSON support (10.2+)** — native JSON type is mapped in this dialect, including path/index helpers and reflection support
- **No ARRAY** — uses `SET`, `MULTISET`, `SEQUENCE` collection types
- **No Sequences** — uses `AUTO_INCREMENT`
- **No multi-schema** — single-schema model
- **No RELEASE SAVEPOINT** — `do_release_savepoint()` is a no-op
- **DDL auto-commits** — `transactional_ddl = False`
- **6 isolation levels** — dual-granularity (class-level + instance-level)
- **Identifier folding** — lowercase (not uppercase like SQL standard)
- **Max identifier length** — 254 characters

### Connection Format

SQLAlchemy URL: `cubrid://user:password@host:port/dbname`
CUBRID native:  `CUBRID:host:port:dbname:::`

The dialect translates automatically in `create_connect_args()`.

### CUBRID Versions Tested

10.2, 11.0, 11.2, 11.4 — via Docker images `cubrid/cubrid:{version}`.

## CI/CD

### Workflows

| File | Trigger | Purpose |
|---|---|---|
| `.github/workflows/ci.yml` | Push to main, PRs | Lint + offline tests (Py 3.10–3.14) + regular integration matrix |
| `.github/workflows/integration-full.yml` | Nightly (03:00 UTC), tag push, manual dispatch | Full Python × CUBRID compatibility matrix |
| `.github/workflows/publish-pypi.yml` | GitHub Release | Build and publish to PyPI |

### CI Matrix

- **Offline (every PR/push)**: Python 3.10, 3.11, 3.12, 3.13, 3.14
- **Integration (every PR/push)**: Python {3.10, 3.14} × CUBRID {10.2, 11.0, 11.2, 11.4} — 8 jobs
- **Integration full (nightly + tag push + dispatch)**: Python {3.10, 3.11, 3.12, 3.13, 3.14} × CUBRID {10.2, 11.0, 11.2, 11.4} — 20 jobs

## Documentation Map

| File | Content |
|---|---|
| `README.md` | Concise landing page (~80 lines) |
| `docs/CONNECTION.md` | Connection strings, URL format, driver setup |
| `docs/TYPES.md` | Full type mapping, CUBRID-specific types |
| `docs/ISOLATION_LEVELS.md` | All 6 CUBRID isolation levels |
| `docs/DML_EXTENSIONS.md` | ON DUPLICATE KEY UPDATE, MERGE, GROUP_CONCAT, TRUNCATE |
| `docs/ALEMBIC.md` | Alembic migration guide, limitations, workarounds |
| `docs/FEATURE_SUPPORT.md` | Feature comparison with MySQL, PostgreSQL, SQLite |
| `docs/DEVELOPMENT.md` | Dev setup, testing, Docker, coverage, CI/CD |
| `docs/ORM_COOKBOOK.md` | Practical ORM usage examples with CUBRID |
| `docs/PRD.md` | Product requirements document |
| `CHANGELOG.md` | Release history (Keep a Changelog format) |
| `CONTRIBUTING.md` | Contribution guidelines |
| `SECURITY.md` | Security vulnerability reporting |
| `docs/DRIVER_COMPAT.md` | CUBRID-Python driver versions and known issues |
| `docs/TROUBLESHOOTING.md` | Common issues, error solutions, debugging techniques |

## Documentation definition of done

Any change that affects public behavior, compatibility, installation, configuration, APIs, supported versions, error handling, or SQL/dialect behavior MUST update the matching documentation in the **same PR**. At minimum keep in sync: `CHANGELOG.md`, the relevant files under `docs/` (e.g. `FEATURE_SUPPORT.md`, `ISOLATION_LEVELS.md`, `TYPES.md`), the `SUPPORT_MATRIX.md`, and version/compatibility claims in `README*`.

If no documentation change is needed, state the reason explicitly in the PR body as `Docs: not needed - <reason>` or apply the `docs-not-needed` label. This is enforced by the `docs-sync` CI check.

Do not mark work complete until code, tests, and documentation are consistent.

## Commit Convention

### Format

```
<type>(<scope>): <imperative summary of WHAT changed>

- <bullet 1: specific change with file/function context>
- <bullet 2: ...>

Closes #<issue>

Ultraworked with [Sisyphus](https://github.com/code-yeongyu/oh-my-opencode)
Co-authored-by: Sisyphus <clio-agent@sisyphuslabs.ai>
```

### Types

| Type | When to use |
|------|-------------|
| `feat` | New user-facing capability (new DML construct, new type, new dialect flag) |
| `fix` | Bug fix — corrects wrong behavior |
| `refactor` | Internal restructuring with no behavior change |
| `test` | Add/update tests only |
| `docs` | Documentation only |
| `chore` | Tooling, deps, CI config, version bumps |
| `ci` | CI workflow changes |
| `perf` | Performance improvement with measurable impact |

### Rules (MANDATORY)

1. **Subject line describes WHAT changed, not batch/phase labels.**
   - ❌ `fix: batch 4 correctness fixes for 1.0 readiness`
   - ✅ `fix: preserve TZ reflection, STRING national kwarg, and UPDATE LIMIT 0`
2. **Be specific — name the function, type, or behavior.**
   - ❌ `feat: gap fixes, stability messaging, code quality improvements`
   - ✅ `fix: FK actions regex, Alembic guardrails, FULL JOIN/LATERAL rejection`
3. **One logical change per commit.** If subject needs "and" more than once, split.
4. **Never use internal jargon** (batch N, phase N, readiness) — commit history is public.
5. **Type must match content:**
   - `feat` = new capability that didn't exist before
   - `fix` = something was broken and is now correct
   - `refactor` = code moved/restructured but behavior unchanged
   - Don't label a fix as `feat` or a mixed bag as `feat`
6. **Body bullets reference issue numbers** (`#135`, `#136`) for traceability.
7. **Scope is optional** but use it for module-specific changes: `fix(compiler):`, `feat(types):`.
8. **Version in commit message must match actual project version.** Never reference "1.0" when project is v1.4.x.

## Release Process

1. Update version in `pyproject.toml` and `sqlalchemy_cubrid/__init__.py`
2. Add changelog entry in `CHANGELOG.md`
3. Commit, tag (`v{major}.{minor}.{patch}`), push with tags
4. Create GitHub release via `gh release create`
5. PyPI publish triggers automatically from the release

## Project Context — Performance Loop System

> This repo provides **ORM-level validation** of the Performance Loop.
> Board: [CUBRID Ecosystem Roadmap](https://github.com/orgs/cubrid-lab/projects/2)

### Role

sqlalchemy-cubrid proves that pycubrid driver optimizations propagate to the **application layer**.
Tier 2 ORM benchmarks (in cubrid-benchmark) measure this repo's overhead vs raw pycubrid.

### Related Issues

| Issue | Phase | Priority |
|-------|-------|----------|
| #70 Optimize query compilation and result mapping | R3 | Must-Have |
| #68 Configure PyPI Trusted Publisher | R0 | Nice-to-Have |

### Key Focus Areas

- Query compile path optimization (compiler.py)
- Result mapping improvement (dialect.py)
- Bulk insert optimization (executemany/insertmanyvalues)
- Quantify ORM overhead vs raw driver (% of total time)
