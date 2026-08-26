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

### SQLAlchemy ORM

| Feature | Status | Notes |
|---|---|---|
| Declarative models | ✅ | |
| Relationships | ✅ | |
| Session / Unit of Work | ✅ | |
| Query API | ✅ | |
| Hybrid properties | ✅ | |

### Alembic

| Feature | Status | Notes |
|---|---|---|
| Auto-discovery | ✅ | `alembic.ddl` entry point |
| Schema migrations | ✅ | CREATE, ALTER, DROP |
| Autogenerate | ✅ | Including collection types (SET, MULTISET, SEQUENCE) |
| Transactional DDL | ❌ | CUBRID auto-commits DDL |

### DML Extensions

| Feature | Status | Notes |
|---|---|---|
| `ON DUPLICATE KEY UPDATE` | ✅ | Via `sqlalchemy_cubrid.insert()` |
| `MERGE` statement | ✅ | Via `sqlalchemy_cubrid.merge()` |
| `REPLACE INTO` | ✅ | Via `sqlalchemy_cubrid.replace()` |
| `GROUP_CONCAT` | ✅ | |
| `TRUNCATE TABLE` | ✅ | Autocommit detected |
| `FOR UPDATE` | ✅ | Including `OF` clause |
| Recursive CTE | ✅ | `WITH RECURSIVE` (CUBRID 11.x+) |
| Window functions | ✅ | ROW_NUMBER, RANK, LAG, LEAD, etc. |
| Index hints | ✅ | Via SA `with_hint()` / `suffix_with()` |

### Known Limitations

| Feature | Status | Notes |
|---|---|---|
| JSON type | ✅ | Since v1.2.0, requires CUBRID ≥ 10.2 |
| Native Enum | ❌ | CUBRID lacks ENUM — use VARCHAR + CHECK constraint |
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
| BLOB | `sa.LargeBinary` | `bytes` | ✅ |
| CLOB | `CLOB` | `str` | ✅ |
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

## Test Coverage

| Metric | Value |
|---|---|
| Offline tests | 619 |
| Integration tests | 35 sync + 16 async |
| Line coverage | ~98.26% offline |
| Coverage threshold | 95% (CI-enforced) |

---

*See also: [Connection Guide](CONNECTION.md) · [Type System](TYPES.md) · [Feature Support](FEATURE_SUPPORT.md) · [Driver Compatibility](DRIVER_COMPAT.md) · [Changelog](../CHANGELOG.md)*
