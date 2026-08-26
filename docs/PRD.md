# PRD: sqlalchemy-cubrid — CUBRID Dialect for SQLAlchemy 2.0–2.2

## 1. Overview

**Project**: sqlalchemy-cubrid
**Current Version**: 1.4.0
**Status**: Beta (actively maintained; async + JSON shipped)
**Repository**: [github.com/cubrid-lab/sqlalchemy-cubrid](https://github.com/cubrid-lab/sqlalchemy-cubrid)
**License**: MIT

### 1.1 Problem Statement (Original)

The original `sqlalchemy-cubrid` project was abandoned and broken:
- Targeted SQLAlchemy < 1.4 (current is 2.0+)
- Used deprecated APIs (`basestring`, `inspect.getargspec`, `super(ClassName, self)`)
- Had critical bugs in compiler, type system, and reflection methods
- No CI pipeline, no tests, could not install on modern environments

### 1.2 What Was Built

A complete ground-up rewrite delivering a modern CUBRID dialect for SQLAlchemy 2.0–2.2:

- **Full SQLAlchemy 2.0–2.2 dialect** with statement caching
- **Complete SQL feature coverage** — everything CUBRID supports is enabled
- **Comprehensive type system** — 20+ types including CUBRID-specific collections and JSON
- **Schema reflection** — tables, views, columns, PKs, FKs, indexes, unique constraints, comments
- **DML extensions** — ON DUPLICATE KEY UPDATE, MERGE, GROUP_CONCAT, TRUNCATE
- **DDL support** — COMMENT, IF NOT EXISTS / IF EXISTS, AUTO_INCREMENT
- **Alembic migration support** via auto-discovered entry point
- **~98.26% offline coverage** (619 offline tests, 35 sync integration tests, 16 async integration tests)
- **CI/CD** — Python 3.10–3.14 × CUBRID 10.2–11.4 matrix
- **17 English documentation files** in `docs/` covering the dialect

### 1.3 Success Criteria — Status

| Criterion | Target | Achieved |
|---|---|---|
| Installable on Python 3.10+ | ✅ | ✅ `pip install sqlalchemy-cubrid` |
| SQLAlchemy 2.0 – 2.2 compatible | ✅ | ✅ Full API compliance |
| Offline tests (no live DB) | ✅ | ✅ 619 tests, ~98.26% coverage |
| All dialect methods implemented | ✅ | ✅ Reflection, compilation, types |
| CI/CD with version matrix | ✅ | ✅ Py 3.10–3.14 × CUBRID 10.2–11.4 |
| Publishable to PyPI | ✅ | ✅ Release workflow on tag |
| Alembic support | ✅ | ✅ CubridImpl auto-discovered + autogenerate |
| ≥ 95% code coverage | ✅ | ✅ ~98.26% (CI-enforced) |
| Comprehensive documentation | ✅ | ✅ 17 English docs files + README |

---

## 2. Technical Architecture

### 2.1 Module Structure

```mermaid
graph TD
    root["sqlalchemy_cubrid/ (12 Python modules + py.typed marker)"]
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

### 2.2 Dependency Matrix

| Package | Version | Purpose |
|---|---|---|
| SQLAlchemy | ≥ 2.0, < 2.2 | Core ORM/engine framework |
| Python | ≥ 3.10 | Runtime |
| CUBRID-Python | any | DBAPI driver (optional extra) |
| Alembic | ≥ 1.7 | Migration support (optional extra) |
| pytest | ≥ 7.0 | Testing (dev) |
| ruff | ≥ 0.4 | Lint + format (dev) |

### 2.3 Entry Points

```toml
[project.entry-points."sqlalchemy.dialects"]
cubrid = "sqlalchemy_cubrid.dialect:CubridDialect"
"cubrid.cubrid" = "sqlalchemy_cubrid.dialect:CubridDialect"
"cubrid.pycubrid" = "sqlalchemy_cubrid.pycubrid_dialect:PyCubridDialect"
"cubrid.aiopycubrid" = "sqlalchemy_cubrid.aio_pycubrid_dialect:PyCubridAsyncDialect"

[project.entry-points."alembic.ddl"]
cubrid = "sqlalchemy_cubrid.alembic_impl:CubridImpl"
```

---

## 3. Implemented Features

### 3.1 Type System (`types.py` — 349 lines)

#### Standard SQL Types

| SQLAlchemy Type | CUBRID SQL Type | Notes |
|---|---|---|
| `Integer` | `INTEGER` | 32-bit signed |
| `SmallInteger` | `SMALLINT` | 16-bit signed |
| `BigInteger` | `BIGINT` | 64-bit signed |
| `Float` | `FLOAT` | 7-digit precision |
| `Double`, `REAL` | `DOUBLE` | 15-digit precision |
| `Numeric(p, s)` | `NUMERIC(p, s)` | Exact numeric, up to 38 digits |
| `String(n)` | `VARCHAR(n)` | Variable-length |
| `Text` | `STRING` | VARCHAR(1,073,741,823) |
| `Unicode(n)` | `NVARCHAR(n)` | National character set |
| `UnicodeText` | `NVARCHAR` | Max-length national |
| `LargeBinary` | `BLOB` | Binary Large Object |
| `Boolean` | `SMALLINT` | Emulated 0/1 |
| `Date` / `Time` / `DateTime` / `TIMESTAMP` | Native | Direct mapping |

#### CUBRID-Specific Types

| Type | Description |
|---|---|
| `STRING` | `VARCHAR(1,073,741,823)` — max-length variable string |
| `BIT(n)` / `BIT VARYING(n)` | Fixed/variable-length bit strings |
| `CLOB` | Character Large Object |
| `MONETARY` | Fixed-point currency type |
| `OBJECT` | OID reference type |
| `SET(type)` | Unordered collection of unique elements |
| `MULTISET(type)` | Unordered collection allowing duplicates |
| `SEQUENCE(type)` | Ordered collection allowing duplicates |

### 3.2 SQL Compiler (`compiler.py` — 507 lines)

#### SQLCompiler

| Method | Output |
|---|---|
| `visit_cast` | `CAST(expr AS type)` |
| `visit_sysdate_func` | `SYSDATE` |
| `visit_utc_timestamp_func` | `UTC_TIME()` |
| `visit_group_concat_func` | `GROUP_CONCAT(...)` |
| `render_literal_value` | Backslash escaping |
| `get_select_precolumns` | `DISTINCT` handling |
| `visit_join` | `INNER JOIN` / `LEFT OUTER JOIN` |
| `limit_clause` | `LIMIT offset, count` (MySQL-style) |
| `for_update_clause` | `FOR UPDATE [OF col, ...]` |
| `update_limit_clause` | `LIMIT n` on UPDATE |

#### DDLCompiler

| Method | Output |
|---|---|
| `get_column_specification` | Column DDL with `AUTO_INCREMENT`, `COMMENT` |
| `visit_set_table_comment` | `ALTER TABLE t COMMENT = 'text'` |
| `visit_drop_table_comment` | `ALTER TABLE t COMMENT = ''` |
| `visit_set_column_comment` | `ALTER TABLE t MODIFY col ... COMMENT 'text'` |

#### TypeCompiler

All CUBRID types compiled to DDL strings: `SMALLINT`, `INTEGER`, `BIGINT`, `NUMERIC(p,s)`,
`DECIMAL(p,s)`, `FLOAT(p)`, `REAL(p)`, `DOUBLE`, `DOUBLE PRECISION`, `CHAR(n)`, `VARCHAR(n)`,
`NCHAR(n)`, `NVARCHAR(n)`, `STRING`, `BIT(n)`, `BIT VARYING(n)`, `BLOB`, `CLOB`,
`SET(type)`, `MULTISET(type)`, `SEQUENCE(type)`, `MONETARY`, `OBJECT`, `BOOLEAN` → `SMALLINT`.

### 3.3 Dialect (`dialect.py` — 605 lines)

#### Dialect Configuration

```python
class CubridDialect(default.DefaultDialect):
    name = "cubrid"
    supports_statement_cache = True
    supports_native_boolean = False       # Emulated via SMALLINT
    supports_native_enum = False
    supports_native_decimal = True
    supports_sequences = False            # Uses AUTO_INCREMENT
    supports_default_values = True        # INSERT ... DEFAULT VALUES
    supports_empty_insert = True
    supports_multivalues_insert = True
    supports_comments = True              # Table + column comments
    supports_is_distinct_from = False
    insert_returning = False              # No RETURNING clause
    update_returning = False
    delete_returning = False
    postfetch_lastrowid = True
    requires_name_normalize = True        # Lowercase folding
    max_identifier_length = 254
    default_paramstyle = "qmark"
```

> **Async dialect**: `PyCubridAsyncDialect` subclasses the pycubrid dialect with `is_async = True` and wraps `pycubrid.aio` via `AsyncAdapt_pycubrid_dbapi`. Registered under the `cubrid.aiopycubrid` entry point for use with `create_async_engine("cubrid+aiopycubrid://...")`.

#### Reflection Methods (All Implemented)

| Method | Source |
|---|---|
| `get_table_names()` | `db_class` (`class_type = 'CLASS'`, non-system tables) |
| `get_view_names()` | `db_class` (`class_type = 'VCLASS'`) |
| `get_view_definition()` | `SHOW CREATE VIEW` |
| `get_columns()` | `SHOW COLUMNS IN` + `_db_attribute.comment` |
| `get_pk_constraint()` | `SHOW COLUMNS IN` (+ optional `db_constraint` lookup for PK name) |
| `get_foreign_keys()` | `SHOW CREATE TABLE` parsing |
| `get_indexes()` | `SHOW INDEXES IN` + `_db_index` flags |
| `get_unique_constraints()` | `SHOW CREATE TABLE` parsing |
| `get_table_comment()` | `db_class.comment` |
| `get_check_constraints()` | Returns `[]` (CUBRID ignores CHECK) |
| `get_schema_names()` | Returns `[]` (no schema objects) |
| `has_table()` | Parameterized query on `db_class` |
| `has_index()` | Query on `_db_index` |
| `has_sequence()` | Returns `False` always |

#### Connection & Isolation

- **URL translation**: `cubrid://user:pass@host:port/db` → `CUBRID:host:port:db:::`
- **3 MVCC isolation levels** — `READ COMMITTED` (default), `REPEATABLE READ`, `SERIALIZABLE`
- **Autocommit detection**: `SET`, `ALTER`, `CREATE`, `DROP`, `GRANT`, `REVOKE`, `TRUNCATE`
- **Savepoints**: Supported; `RELEASE SAVEPOINT` is a no-op

### 3.4 DML Extensions (`dml.py` — 267 lines)

#### ON DUPLICATE KEY UPDATE

```python
from sqlalchemy_cubrid import insert

stmt = insert(users).values(id=1, name="alice")
stmt = stmt.on_duplicate_key_update(name="updated_alice")
# Or reference inserted values:
stmt = stmt.on_duplicate_key_update(name=stmt.inserted.name)
```

#### MERGE Statement

```python
from sqlalchemy_cubrid.dml import merge

stmt = (
    merge(target)
    .using(source)
    .on(target.c.id == source.c.id)
    .when_matched_then_update({"name": source.c.name})
    .when_not_matched_then_insert({"id": source.c.id, "name": source.c.name})
)
```

### 3.5 Alembic Support (`alembic_impl.py` — 141 lines)

- `CubridImpl(DefaultImpl)` with `transactional_ddl = False`
- Auto-discovered via `alembic.ddl` entry point
- Autogenerate: `render_type()` for SET/MULTISET/SEQUENCE rendering in migration scripts
- Autogenerate: `compare_type()` for semantic comparison of collection types
- Limitations: no ALTER COLUMN TYPE, no RENAME COLUMN (use `batch_alter_table`)
---

## 4. Test Coverage

### 4.1 Test Matrix

| Test File | Tests | Coverage Area |
|---|---|---|
| `test_compiler.py` | 70 | SQL compilation (SELECT, JOIN, CAST, LIMIT, DML, DDL) |
| `test_types.py` | 53 | Type compilation, reflection, collection, MONETARY, OBJECT |
| `test_requirements.py` | 46 | SA 2.0 requirement flags (parametrized) |
| `test_dialect_offline.py` | 24 | Reflection stubs, connection, isolation, savepoint |
| `test_base.py` | 15 | ExecutionContext, IdentifierPreparer |
| `test_dml.py` | ~80 | ON DUPLICATE KEY UPDATE, MERGE, REPLACE compilation |
| `test_alembic.py` | 21 | Import, registry, entry-point, autogenerate |
| `test_dialects.py` | ~23 | Edge cases, dialect config |
| `test_trace.py` | 7 | Query trace utility |
| **Total** | **619 offline tests** | **~98.26% coverage** |

### 4.2 Unreachable Lines (4 entries)

| File | Line | Reason |
|---|---|---|
| `compiler.py` | 72 | `for_update_clause` returning `""` — SA always calls with valid state |
| `compiler.py` | 84 | `limit_clause` returning `""` — SA always provides limit context |
| `compiler.py` | 298-300 | DDL type compilation fallback — all types covered |
| `dml.py` | 310 | `else` branch in type normalization — all input types covered |

### 4.3 CI Matrix

| Workflow | Python versions | CUBRID versions | Source |
|---|---|---|---|
| PR/push offline tests | 3.10, 3.11, 3.12, 3.13, 3.14 | N/A (offline) | `.github/workflows/ci.yml` |
| PR/push integration tests | 3.10, 3.14 | 10.2, 11.0, 11.2, 11.4 | `.github/workflows/ci.yml` |
| Nightly / tagged / manual full integration matrix | 3.10, 3.11, 3.12, 3.13, 3.14 | 10.2, 11.0, 11.2, 11.4 | `.github/workflows/integration-full.yml` |

---

## 5. Known Limitations

Limitations imposed by CUBRID itself (not the dialect):

| Feature | Status | Reason |
|---|---|---|
| `RETURNING` clause | ❌ | CUBRID has no `INSERT/UPDATE/DELETE ... RETURNING` |
| Native `BOOLEAN` | ⚠️ | Emulated via `SMALLINT` (0/1) |
| `JSON` type | ✅ | Native JSON type/functions are supported in CUBRID 10.2+ and mapped by the dialect |
| `ARRAY` type | ❌ | Use `SET` / `MULTISET` / `SEQUENCE` collections |
| Sequences | ❌ | CUBRID uses `AUTO_INCREMENT` |
| Multi-schema | ❌ | Single-schema model |
| Temporary tables | ❌ | CUBRID has no `CREATE TEMPORARY TABLE` |
| `IS DISTINCT FROM` | ❌ | Not a CUBRID SQL operator |
| `RELEASE SAVEPOINT` | ❌ | Dialect implements as no-op |
| Check constraint reflection | ❌ | CUBRID parses but ignores CHECK |
| Async DBAPI support | ✅ | Via pycubrid.aio async driver (`cubrid+aiopycubrid://`) |
| Two-phase commit (XA) | ❌ | CUBRID has no distributed transaction support |
| Server-side cursors | ❌ | CUBRID Python driver limitation |
| Alembic ALTER COLUMN TYPE | ❌ | Use `batch_alter_table` workaround |
| Alembic RENAME COLUMN | ❌ | Use `batch_alter_table` workaround |
| FOR UPDATE NOWAIT / SKIP LOCKED | ❌ | Not supported by CUBRID |

---

## 6. Documentation

| Document | Lines | Content |
|---|---|---|
| [`README.md`](../README.md) | 80 | Concise landing page |
| [`docs/CONNECTION.md`](CONNECTION.md) | 258 | Connection strings, URL format, driver setup |
| [`docs/TYPES.md`](TYPES.md) | 313 | Full type mapping, CUBRID-specific types |
| [`docs/ISOLATION_LEVELS.md`](ISOLATION_LEVELS.md) | 206 | The three CUBRID MVCC isolation levels |
| [`docs/DML_EXTENSIONS.md`](DML_EXTENSIONS.md) | 361 | ON DUPLICATE KEY UPDATE, MERGE, GROUP_CONCAT |
| [`docs/ALEMBIC.md`](ALEMBIC.md) | 376 | Alembic migration guide, limitations |
| [`docs/FEATURE_SUPPORT.md`](FEATURE_SUPPORT.md) | 442 | Feature comparison with MySQL/PG/SQLite |
| [`docs/DEVELOPMENT.md`](DEVELOPMENT.md) | 383 | Dev setup, testing, Docker, CI/CD |
| [`CHANGELOG.md`](../CHANGELOG.md) | 119 | Release history (Keep a Changelog) |
| [`CONTRIBUTING.md`](../CONTRIBUTING.md) | 225 | Contribution guidelines |

---

## 7. Release History

| v0.1.0 | 2026-03-12 | Complete rewrite — SA 2.0, all reflection, compiler, types, CI/CD |
| v0.2.0 | 2026-03-12 | SQL feature expansion — FOR UPDATE, window functions, MERGE, ODKU, COMMENT, DDL extensions |
| v0.3.0 | 2026-03-12 | Alembic support, edge-case tests, 99% coverage |
| v0.3.1 | 2026-03-12 | Cleanup — legacy file removal, sample modernization, community files |
| v0.3.2 | 2026-03-12 | Documentation restructuring — 6 new guide files, README rewrite |
| v0.4.0 | 2026-03-12 | Driver & compatibility hardening — error codes, do_ping, connection pool tuning |
| v0.5.0 | 2026-03-12 | Query feature expansion — REPLACE INTO, recursive CTEs, ODKU subqueries, trace |
| v0.6.0 | 2026-03-12 | Type system expansion, Alembic autogenerate, SA 2.1 readiness, ORM cookbook |

---

## 8. Roadmap

### v0.4.0 — Driver & Compatibility Hardening

**Goal**: Improve real-world usability and CUBRID driver compatibility.

| Item | Description | Priority |
| Item | Description | Priority | Status |
|---|---|---|---|
| CUBRID-Python driver audit | Test against latest CUBRID-Python releases, document version compatibility matrix | High | ✅ Done |
| Connection pool tuning | Test and document SA connection pool behavior with CUBRID (pool_size, pool_recycle, pool_pre_ping) | High | ✅ Done |
| `postfetch_lastrowid` validation | Verify `get_last_insert_id()` behavior across CUBRID versions, fix if inconsistent | High | ✅ Done |
| Error code mapping | Map CUBRID error codes to SA exceptions (`IntegrityError`, `OperationalError`, etc.) for proper exception handling | Medium | ✅ Done |
| CUBRID 12.x support | Test against CUBRID 12 when released, add to CI matrix | Medium | ⏳ Blocked (not released) |
| Python 3.14 support | Add Python 3.14 to CI matrix when available | Low | ✅ Done |

### v0.5.0 — Query Feature Expansion

**Goal**: Maximize SQL feature coverage within CUBRID's capabilities.

| Item | Description | Priority | Status |
|---|---|---|---|
| `REPLACE` statement | CUBRID supports `REPLACE INTO` — add as custom DML construct | Medium | ✅ Done |
| `INSERT ... ON DUPLICATE KEY UPDATE` with subqueries | Support subquery values in ODKU clause | Medium | ✅ Done |
| Lateral joins | Investigate CUBRID's lateral join support, enable if available | Low | ❌ Not supported |
| Recursive CTEs | Test recursive `WITH RECURSIVE` support in CUBRID 11.x+ | Low | ✅ Done |
| Full-text search | CUBRID has full-text indexes — expose via custom construct if feasible | Low | ❌ Not supported |
| `EXPLAIN` output | Add `EXPLAIN` prefix support for query plan inspection | Low | ✅ Done (trace_query) |

### v0.6.0 — SQLAlchemy 2.1+ & Async

**Goal**: Full SQLAlchemy 2.1 alignment and modern async support.

| Item | Description | Priority | Status |
|---|---|---|---|
| SQLAlchemy 2.1 compatibility | Track SA 2.1 breaking changes, update dialect accordingly | High | ⏳ SA 2.1 not released |
| SQLAlchemy 2.2+ forward compat | Test and adjust for future SA releases | High | ⏳ Not released |
| Async DBAPI support | If CUBRID Python driver adds async support, implement `create_async_engine` compatibility | Medium | ✅ Done |
| Type annotation improvements | Add full `overload` signatures for `insert()`, `merge()` return types | Medium | ✅ Done |
| `RETURNING` emulation | Investigate TRIGGER-based or `LAST_INSERT_ID` workaround for single-row returning | Low | ⏳ Not started |

### Long-Term — Community & Ecosystem

**Goal**: Sustainable open-source project with active community.

| Item | Description | Priority | Status |
|---|---|---|---|
| PyPI publication | Publish to PyPI for `pip install` from registry | High | ✅ Done |
| Documentation site | Deploy docs via GitHub Pages or Read the Docs | Medium | ⏳ Not started |
| Alembic autogenerate tuning | Improve autogenerate for CUBRID-specific types (SET, MULTISET, SEQUENCE) | Medium | ✅ Done |
| SQLAlchemy test suite pass rate | Track and increase pass rate against SA's standard dialect test suite | Medium | ⏳ Not started |
| CUBRID ORM cookbook | Practical examples: relationships, eager loading, hybrid properties with CUBRID | Low | ✅ Done |
| Performance benchmarks | Benchmark dialect overhead vs raw CUBRID-Python for common operations | Low | ⏳ Not started |
| Community contributors | Issue templates, good-first-issue labels, contributor docs | Low | ✅ Done (issue templates) |

### Roadmap Priorities

```mermaid
graph LR
    v130["v0.4.0"] --> v130a["Driver compatibility hardening"]
    v130 --> v130b["Error code mapping + connection pooling"]

    v140["v0.5.0"] --> v140a["REPLACE statement"]
    v140 --> v140b["Recursive CTEs, full-text search"]

    v200["v0.6.0"] --> v200a["SQLAlchemy 2.1+ full compatibility"]
    v200 --> v200b["Async support (when driver supports it)"]

    longterm["Long-term"] --> longa["PyPI, docs site, community growth"]
    longterm --> longb["SA test suite pass rate, benchmarks"]
```

---

## 9. Architecture Decisions

### 9.1 Why Single Package (not separate repos)

Alembic support, types, and DML extensions are all in `sqlalchemy_cubrid/` — one package.
This follows the pattern of all mature SA dialects (MySQL, PostgreSQL, SQLite).
Separate repos create versioning complexity with no benefit for a dialect this size.

### 9.2 Why Offline Tests by Default

CUBRID requires a running server instance. Most dialect logic (SQL compilation,
type mapping, reflection parsing) is deterministic and testable without a database.
314 of our tests run offline, enabling fast CI and contributor onboarding.

### 9.3 Why 95% Coverage Threshold

SA dialect bugs are subtle — wrong SQL generation, missing escaping, broken reflection.
High coverage catches regressions before they reach users. The 3 uncovered lines are
verified unreachable defensive fallbacks, documented in test suite.

### 9.4 Why `batch_alter_table` for Alembic Limitations

CUBRID lacks `ALTER COLUMN TYPE` and `RENAME COLUMN`. Rather than emulating these
with complex DDL (which could silently lose data), we document the limitation and
recommend Alembic's `batch_alter_table` — a proven table-recreate strategy used
by SQLite's dialect for the same reason.

---

*Last updated: April 2026 · sqlalchemy-cubrid v1.4.0 Beta*

---

## 10. Example-first Design Philosophy

### Why Example-first

CUBRID's ecosystem is small compared to PostgreSQL or MySQL. For a small-ecosystem
project, the entry barrier must be minimized — users should be able to copy-paste
working code within 30 seconds of reading the documentation.

> Because the ecosystem is still small, the project provides extensive examples
> and cookbook-style documentation to lower the adoption barrier.

### Hello World

```bash
pip install sqlalchemy-cubrid
```

```python
from sqlalchemy import create_engine, text

engine = create_engine("cubrid://dba:password@localhost:33000/demodb")

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.scalar())  # 1
```

This code connects to a CUBRID database via SQLAlchemy, runs a query, and prints the
result. No ORM setup required — just install and connect.

### Hello World — ORM

```python
from sqlalchemy import create_engine, String
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(200), unique=True)


engine = create_engine("cubrid://dba:password@localhost:33000/demodb")
Base.metadata.create_all(engine)

with Session(engine) as session:
    user = User(name="Alice", email="alice@example.com")
    session.add(user)
    session.commit()
```

### AI Agent Discoverability

Modern developers increasingly rely on AI coding assistants — Claude Code, OpenCode,
Cursor, GitHub Copilot, Devin, and others. These agents read README files, PRDs,
documentation, and example code to decide which libraries to recommend.

**More examples in documentation = higher probability of AI recommendation.**

By embedding working code directly in the PRD, README, and docs, we ensure that
AI agents can discover, learn, and recommend sqlalchemy-cubrid accurately.

### Cookbook Integration

The [cubrid-cookbook](https://github.com/cubrid-lab/cubrid-cookbook) repository provides
runnable examples for sqlalchemy-cubrid:

| Example | Description |
|---|---|
| `python/sqlalchemy/01_connect.py` | Core engine connection |
| `python/sqlalchemy/02_orm.py` | ORM models and CRUD |
| `python/sqlalchemy/03_dml.py` | DML extensions (ODKU, MERGE, REPLACE) |
| `python/sqlalchemy/04_relationships.py` | ORM relationships |
| `python/sqlalchemy/05_reflection.py` | Schema reflection |
| `python/sqlalchemy/06_alembic.py` | Alembic migrations |

Framework integration examples:

| Example | Framework | Description |
|---|---|---|
| `python/fastapi/` | FastAPI | REST API with automatic docs |
| `python/django/` | Django | Django project via SQLAlchemy bridge |
| `python/flask/` | Flask | Flask + Flask-SQLAlchemy |
| `python/pandas/` | Pandas | Data analysis pipeline |
| `python/streamlit/` | Streamlit | Interactive data dashboard |
| `python/celery/` | Celery | Async task queue |

### Inspiration from Successful Projects

Projects that succeeded partly through example-heavy documentation:

| Project | What They Did |
|---|---|
| **FastAPI** | Every endpoint documented with runnable examples; became the fastest-growing Python web framework |
| **LangChain** | Cookbook-first approach drove explosive adoption in the AI space |
| **SQLAlchemy** | Extensive ORM cookbook and tutorial; de facto Python ORM for 15+ years |
| **Pandas** | "10 Minutes to pandas" and cookbook lowered entry barrier for data science |

sqlalchemy-cubrid follows the same philosophy: **examples are not supplementary — they are the primary documentation.**
