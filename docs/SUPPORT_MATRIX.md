# Support Matrix

Compatibility and feature support for sqlalchemy-cubrid releases.

---

## Version Compatibility

### SQLAlchemy

| SQLAlchemy Version | Status | Notes |
|---|---|---|
| 2.0.x | ✅ Supported | Minimum required version |
| 2.1.x | ✅ Supported | Latest tested pre-release until GA |
| ≥ 2.2 | ❌ Not supported | Code uses private SA internals (see below) |
| < 2.0 | ❌ Not supported | SA 1.x API removed |

**Why `<2.3`?** The dialect accesses private SQLAlchemy APIs that may change without notice:

| Private API | Location | Usage |
|---|---|---|
| `select._limit_clause` | `compiler.py:104` | LIMIT clause compilation |
| `select._offset_clause` | `compiler.py:105` | OFFSET clause compilation |
| `select._for_update_arg` | `compiler.py:93` | FOR UPDATE clause |

Literal detection and typed-bind recreation now go through local `_compat.py`
helpers, so the direct private API surface is down to these three attributes.

### Python

| Python Version | Status |
|---|---|
| 3.10 | ✅ Supported |
| 3.11 | ✅ Supported |
| 3.12 | ✅ Supported |
| 3.13 | ✅ Supported |
| 3.14 | ✅ Supported |
| < 3.10 | ❌ Not supported |

### CUBRID Server

| CUBRID Version | Status | Notes |
|---|---|---|
| 11.4 | ✅ Supported | Latest stable |
| 11.2 | ✅ Supported | |
| 11.0 | ✅ Supported | |
| 10.2 | ✅ Supported | Minimum tested version |
| < 10.2 | ❌ Not supported | |

### Drivers

| Driver | Install | URL Scheme | Status |
|---|---|---|---|
| CUBRID-Python (CCI) | `pip install "sqlalchemy-cubrid[cubrid]"` or `[cubriddb]` | `cubrid://` / `cubrid+cubriddb://` | ✅ Supported (legacy C-extension) |
| pycubrid (Pure Python) | `pip install "sqlalchemy-cubrid[pycubrid]"` | `cubrid+pycubrid://` | ✅ Supported |
| pycubrid async | `pip install "sqlalchemy-cubrid[pycubrid]"` | `cubrid+aiopycubrid://` | ✅ Supported |

---

## Feature Support

### SQLAlchemy Core

| Feature | Status | Notes |
|---|---|---|
| `create_engine()` | ✅ | `cubrid://`, `cubrid+cubrid://`, `cubrid+cubriddb://`, and `cubrid+pycubrid://` schemes |
| Async engine | ✅ | `create_async_engine("cubrid+aiopycubrid://...")` |
| SQL compilation | ✅ | SELECT, INSERT, UPDATE, DELETE, JOIN, subqueries |
| DDL compilation | ✅ | CREATE TABLE, ALTER, DROP, AUTO_INCREMENT, COMMENT |
| Type system | ✅ | All shipped CUBRID types compile; reflection coverage is listed separately below |
| Schema reflection | ✅ | Tables, columns, PKs, FKs, indexes, unique constraints, comments |
| Transaction management | ✅ | commit, rollback, savepoint (no RELEASE SAVEPOINT) |
| Connection pooling | ✅ | SA pool with `pool_pre_ping`, disconnect detection |
| Statement caching | ✅ | `supports_statement_cache = True` |
| `executemany` (`text()`, UPDATE, DELETE) | ✅ | `None` binds as NULL and `rowcount` is the total across parameter sets on every driver (`supports_sane_multi_rowcount = True`). On `cubrid://`, the dialect runs each parameter set as its own `execute()` to work around a CUBRIDdb bug. This costs one extra statement prepare per row: about 2.9× slower than the driver's own `executemany` in a 1000-row UPDATE. pycubrid keeps its prepare-once `executemany`. A multi-row Core `insert()` that uses insertmanyvalues is unaffected. An INSERT into a table with a column whose type defines `bind_expression()` falls back to executemany (#421) and uses the per-row guard on `cubrid://`. See [Driver Compatibility, Known Issue 7](DRIVER_COMPAT.md#known-issues) |

### SQLAlchemy ORM

| Feature | Status | Notes |
|---|---|---|
| Declarative models | ✅ | |
| Relationships | ✅ | |
| Session / Unit of Work | ✅ | |
| Batched UPDATE / DELETE row checks | ✅ | Batched flushes check the matched-row count on every driver. On `cubrid://` this relies on the per-row `executemany` guard, see [Driver Compatibility, Known Issue 7](DRIVER_COMPAT.md#known-issues) |
| Query API | ✅ | |
| Hybrid properties | ✅ | |

### Alembic

| Feature | Status | Notes |
|---|---|---|
| Auto-registration | ✅ | Registered when the dialect loads (no `env.py` import) |
| Schema migrations | ✅ | CREATE, ALTER, DROP |
| Autogenerate | ✅ | Including collection types (SET, MULTISET, SEQUENCE) |
| Transactional DDL | ✅ | DDL rolls back with the transaction; the whole upgrade is atomic by default (`transaction_per_migration=True` for per-revision commits) |

### DML Extensions

| Feature | Status | Notes |
|---|---|---|
| `ON DUPLICATE KEY UPDATE` | ✅ | Via `sqlalchemy_cubrid.insert()` |
| `MERGE` statement | ✅ | Via `sqlalchemy_cubrid.merge()` |
| `REPLACE INTO` | ✅ | Via `sqlalchemy_cubrid.replace()` |
| `GROUP_CONCAT` | ✅ | |
| `TRUNCATE TABLE` | ✅ | Committed with the enclosing transaction |
| `FOR UPDATE` | ✅ | Including `OF` clause |
| Recursive CTE | ✅ | `WITH RECURSIVE` (CUBRID 11.x+) |
| Window functions | ✅ | ROW_NUMBER, RANK, LAG, LEAD, etc. |
| Index hints | ✅ | Via SA `with_hint()` / `suffix_with()` |

### Known Limitations

| Feature | Status | Notes |
|---|---|---|
| JSON type | ✅ | Since v1.2.0, requires CUBRID ≥ 10.2 |
| Native Enum | ✅ | Native `ENUM('a', 'b', ...)` — verified on 10.2–11.4 (#343) |
| Interval type | ❌ | Not supported by CUBRID |
| RETURNING clause | ❌ | `INSERT/UPDATE/DELETE ... RETURNING` not supported |
| BOOLEAN | ⚠️ | Mapped to SMALLINT (0/1) — no native boolean |
| Sequences | ❌ | CUBRID uses AUTO_INCREMENT only |
| CHECK constraint reflection | ❌ | `get_check_constraints()` returns empty list |
| Multi-schema | ❌ | CUBRID has single-schema model |
| RELEASE SAVEPOINT | ❌ | No-op (CUBRID doesn't support it) |
| Lateral joins | ❌ | CUBRID lacks LATERAL subquery support |
| Full-text search | ❌ | No MATCH … AGAINST syntax |
| Async DBAPI | ✅ | Via pycubrid.aio async driver (`cubrid+aiopycubrid://`), requires pycubrid >= 1.2.0,<2.0 |

---

## Type Mapping

Declared/compiled types and reflected types are not identical. `REAL`, `MONETARY`,
and `OBJECT` compile correctly and can be declared in models, but they are not
present in `dialect.ischema_names`, so reflection will not auto-map them back.

| CUBRID Type | SQLAlchemy Type | Python Type | Reflection |
|---|---|---|---|
| INTEGER | `sa.Integer` | `int` | ✅ |
| BIGINT | `sa.BigInteger` | `int` | ✅ |
| SMALLINT | `sa.SmallInteger` | `int` | ✅ |
| FLOAT | `sa.Float` | `float` | ✅ |
| REAL | `REAL` | `float` | ❌ Declared/compiled only |
| DOUBLE | `sa.Float` | `float` | ✅ |
| NUMERIC / DECIMAL | `sa.Numeric` | `decimal.Decimal` | ✅ |
| MONETARY | `MONETARY` | `float` | ❌ Declared/compiled only |
| CHAR | `sa.CHAR` | `str` | ✅ |
| VARCHAR | `sa.String` | `str` | ✅ |
| NCHAR | `NCHAR` | `str` | ✅ |
| NVARCHAR | `NVARCHAR` | `str` | ✅ |
| STRING | `STRING` | `str` | ✅ |
| DATE | `sa.Date` | `datetime.date` | ✅ |
| TIME | `sa.Time` | `datetime.time` | ✅ |
| DATETIME | `sa.DateTime` | `datetime.datetime` | ✅ |
| TIMESTAMP | `sa.TIMESTAMP` | `datetime.datetime` | ✅ |
| BIT | `BIT` | `bytes` | ✅ |
| BLOB | `sa.LargeBinary` | `bytes` (documented); non-NULL reads currently return a driver LOB locator, see [Driver Compatibility, Known Issue 6](DRIVER_COMPAT.md#known-issues) | ✅ |
| CLOB | `CLOB` | `str` (documented); non-NULL reads currently return a driver LOB locator, see [Driver Compatibility, Known Issue 6](DRIVER_COMPAT.md#known-issues) | ✅ |
| SET | `SET` | Collection | ✅ |
| MULTISET | `MULTISET` | Collection | ✅ |
| SEQUENCE | `SEQUENCE` | Collection | ✅ |
| OBJECT | `OBJECT` | OID reference | ❌ Declared/compiled only |

---

## CI Matrix

| Dimension | PR / push | Nightly + tag + dispatch |
|---|---|---|
| Offline tests | Python 3.10, 3.11, 3.12, 3.13, 3.14 | Same |
| Integration tests | Python {3.10, 3.14} × CUBRID {10.2, 11.0, 11.2, 11.4} = 8 jobs | Python {3.10, 3.11, 3.12, 3.13, 3.14} × CUBRID {10.2, 11.0, 11.2, 11.4} = 20 jobs |

The 5 × 4 full integration matrix is run by `.github/workflows/integration-full.yml` on a nightly schedule, on tagged releases, and on demand via `workflow_dispatch`.

### SQLAlchemy compliance lanes

The official SQLAlchemy compliance suite blocks merges for both drivers. Each lane has its own reviewed known-failure baseline in `test/known_failures.txt`; see [Development Guide](DEVELOPMENT.md#sqlalchemy-compliance-lanes).

| Lane | Driver | SQLAlchemy | CUBRID (PR CI) | Known failures (11.4 / 10.2) |
|---|---|---|---|---|
| `cubrid@sa2.0` | CUBRIDdb (cubrid-python v11.3.0.51) | 2.0.53 | 11.4 | 119 / 112 |
| `pycubrid@sa2.0` | pycubrid 1.7.1 (recommended) | 2.0.53 | 10.2 | 105 (gated on 10.2 only) |
| `pycubrid@sa2.1` | pycubrid 1.7.1 (recommended) | 2.1.1 | 11.4 | 109 / 102 |

Most known failures are shared by both drivers: CUBRID backend rules (identifier case folding, `[ ]` identifier delimiters, no window frame clause, per-row foreign-key checks, single-precision `FLOAT`) and open dialect reflection/DDL bugs listed in `test/known_failures.txt`. Only the CUBRIDdb lane carries its NUMERIC truncation and integer-division entries.

## Test Coverage

| Metric | Value |
|---|---|
| Offline tests | 619 |
| Integration tests | 35 sync + 16 async |
| Line coverage | ~98.26% offline |
| Coverage threshold | 95% (CI-enforced) |

---

*See also: [Connection Guide](CONNECTION.md) · [Type System](TYPES.md) · [Feature Support](FEATURE_SUPPORT.md) · [Driver Compatibility](DRIVER_COMPAT.md) · [Changelog](../CHANGELOG.md)*
