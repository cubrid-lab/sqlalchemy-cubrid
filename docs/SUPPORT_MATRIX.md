# Support Matrix

Compatibility and feature support for sqlalchemy-cubrid releases.

---

## Version Compatibility

### SQLAlchemy

| SQLAlchemy Version | Status | Notes |
|---|---|---|
| 2.0.x | ✅ Supported | Minimum required version |
| 2.1.x | ✅ Supported | CI-tested on SQLAlchemy 2.1.1 |
| ≥ 2.2 | ❌ Not supported | Excluded by the `<2.2` cap until 2.2 ships and passes the full matrix; code uses private SA internals (see below) |
| < 2.0 | ❌ Not supported | SA 1.x API removed |

**Why `<2.2`?** The dialect accesses private SQLAlchemy APIs that may change without notice:

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
| 3.11 | ✅ Supported |
| 3.12 | ✅ Supported |
| 3.13 | ✅ Supported |
| 3.14 | ✅ Supported |
| 3.15 | ✅ Supported (standard GIL builds; see the notes below) |
| 3.10 | ❌ Not supported from 1.10.0 (last supported in 1.9.x) |
| < 3.10 | ❌ Not supported |

**Python 3.10 support retirement:** Python 3.10 reached upstream end of life on
2026-10-01 ([PEP 619](https://peps.python.org/pep-0619/#310-lifespan)).
The 1.8.x and 1.9.x lines support Python 3.10; 1.9.0 carried the advance notice.
From 1.10.0 the package requires Python 3.11 or newer (`requires-python =
">=3.11"`), so `pip` on Python 3.10 keeps installing 1.9.x. Only the latest
release line receives fixes, so 1.9.x gets no further releases. Upgrade your
interpreter, recreate your virtual environment and validate your application
before upgrading.

**Python 3.15:** Supported on the final CPython
[3.15.0](https://www.python.org/downloads/release/python-3150/) release with the
standard GIL; free-threaded builds are not supported. The full compatibility
matrix runs Python 3.15 against every supported CUBRID version on manual dispatch
and every release, and 3.15 is the newest offline endpoint. The manual
`python-canary.yml` lane still checks fresh wheel/sdist installs on 3.15. The
scope of the claim:

- **pycubrid (`cubrid+pycubrid://`, `cubrid+aiopycubrid://`):** pycubrid declares
  Python 3.15 from the release after 1.10.0
  ([cubrid-lab/pycubrid#831](https://github.com/cubrid-lab/pycubrid/pull/831)).
  The `[pycubrid]` floor stays `pycubrid>=1.8.0,<2.0`; pycubrid 1.10.0 passes the
  sync and async integration suites on 3.15 but does not declare it. On 3.15,
  pycubrid 1.10.0 and earlier reject `?charset=ksc5601`, because Python 3.15 maps
  that codec alias to CP949; use `?charset=euckr`, or the pycubrid release that
  declares 3.15, which maps `ksc5601` to EUC-KR itself.
- **CUBRIDdb (`cubrid://`):** the official `cubrid-python` v11.3.0.51 source builds
  for 3.15 with the CI recipe on `ubuntu-latest`, and the full matrix runs its
  lanes on 3.15. With GCC 14 the stock build fails on Python 3.14 and 3.15
  alike (the two versions compared; 3.11–3.13 were not tried): GCC 14 makes `-Wincompatible-pointer-types` and
  `-Wint-conversion` errors. This project does not add warning-downgrade flags to
  CI; see [Driver Compatibility](DRIVER_COMPAT.md).
- **Not run on 3.15:** the SQLAlchemy compliance lanes stay on Python 3.14/CUBRID
  11.4 and Python 3.11/CUBRID 10.2.
- **Garbage-collected connections:** with SQLAlchemy 2.1, a pooled connection lost
  inside a reference cycle (such as one with its transaction still open) is neither
  terminated nor returned to the pool on 3.15. This is a SQLAlchemy 2.1/CPython 3.15
  interaction that affects every dialect, and the integration test for it is an
  expected failure there; see [Connection Guide](CONNECTION.md#async-connection).
- **Environment:** Decimal-subclass parameters through pycubrid need the C
  `_decimal` module, which a Python built without `libmpdec` lacks; pycubrid then
  raises `ProgrammingError` for them, and plain `Decimal` values are unaffected.
  The `actions/setup-python` 3.15.0 build that CI uses, the `python:3.15-rc`
  Docker image and a source build without `libmpdec-dev` were observed without it,
  so the Decimal-subclass round trip is skipped in CI's 3.15 cells. Docker Hub had no final `python:3.15` image when 3.15 was
  promoted; CI uses `actions/setup-python`.

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
| CUBRIDdb (CCI) | Build from cubrid-python v11.3.0.51+ ([how](DRIVER_COMPAT.md#building-cubriddb-from-source)); the `[cubrid]` / `[cubriddb]` extras are deprecated and install the untested PyPI 9.3.x | `cubrid://` / `cubrid+cubriddb://` | ✅ Supported C-extension driver (v11.3.0.51+ only) |
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
| Autogenerate | ✅ | Including collection types (SET, MULTISET, SEQUENCE); CUBRID-specific member types render as `cubrid_types.MONETARY()`, `cubrid_types.BIT(...)` and so on |
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
| Recursive CTE | ✅ | `WITH RECURSIVE` (verified on CUBRID 10.2, 11.0, 11.2 and 11.4) |
| Window functions | ✅ | ROW_NUMBER, RANK, LAG, LEAD, etc. |
| Index hints | ✅ | Via SA `with_hint()` / `suffix_with()` |

### Known Limitations

| Feature | Status | Notes |
|---|---|---|
| JSON type | ✅ | Since v1.2.0, requires CUBRID ≥ 10.2 |
| Native Enum | ✅ | Native `ENUM('a', 'b', ...)` — verified on 10.2–11.4 (#343) |
| Interval type | ❌ | Not supported by CUBRID |
| RETURNING clause | ❌ | `INSERT/UPDATE/DELETE ... RETURNING` not supported |
| BOOLEAN | ⚠️ | Mapped to SMALLINT (0/1) — no native boolean. `col.is_(True)` / `is_not(False)` etc. are emulated with null-safe `<=>` (`col <=> 1`, `(col <=> 1) = 0`) because CUBRID's `IS` accepts only `NULL`/`TRUE`/`FALSE` (#465); `IS [NOT] NULL`, `col == True` and `not_(col)` compile natively. CUBRID rejects `AND`/`OR`/`NOT` in a SELECT list — use them in `WHERE` or wrap them in `case()`. See [Boolean predicates](TYPES.md#boolean-predicates) |
| Sequences | ❌ | CUBRID uses AUTO_INCREMENT only |
| CHECK constraint reflection | ❌ | `get_check_constraints()` returns empty list |
| Multi-schema | ❌ | CUBRID has single-schema model |
| RELEASE SAVEPOINT | ❌ | No-op (CUBRID doesn't support it) |
| Lateral joins | ❌ | CUBRID lacks LATERAL subquery support |
| Full-text search | ❌ | No MATCH … AGAINST syntax |
| Async DBAPI | ✅ | Via pycubrid.aio async driver (`cubrid+aiopycubrid://`), requires pycubrid >= 1.8.0,<2.0 |

---

## Type Mapping

Declared/compiled types and reflected types are not identical. `REAL`, `MONETARY`,
and `OBJECT` compile correctly and can be declared in models, but they are not
present in `dialect.ischema_names`, so reflection will not auto-map them back.
The reflection column describes schema metadata mapping; the Python type column
describes the intended value shape. Neither column promises that every driver
binds and returns that value unchanged. See [Type Mapping](TYPES.md) and
[Driver Compatibility](DRIVER_COMPAT.md) for BLOB/CLOB locators, empty BIT values,
CUBRIDdb DECIMAL truncation and collection binding differences.

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
| TIMESTAMPTZ | `TIMESTAMPTZ` (`timezone=True`) | `datetime.datetime` | ✅ Distinct reflected type, not collapsed into `TIMESTAMP` |
| TIMESTAMPLTZ | `TIMESTAMPLTZ` (`timezone=True`) | `datetime.datetime` | ✅ Distinct reflected type, not collapsed into `TIMESTAMP` |
| DATETIMETZ | `DATETIMETZ` (`timezone=True`) | `datetime.datetime` | ✅ Distinct reflected type, not collapsed into `DATETIME` |
| DATETIMELTZ | `DATETIMELTZ` (`timezone=True`) | `datetime.datetime` | ✅ Distinct reflected type, not collapsed into `DATETIME` |
| BIT(n) / BIT VARYING(n) | `BIT(n)` / `BIT(n, varying=True)` | `bytes` | ✅ Length and `VARYING` preserved |
| BIT(n\*8) | `sa.BINARY(n)` (`BINARY()` → `BIT(8)`) | `bytes` | ✅ Reflects as `BIT(n*8)` |
| BIT VARYING(n\*8) | `sa.VARBINARY(n)` (`VARBINARY()` → `BIT VARYING`) | `bytes` | ✅ Reflects as `BIT VARYING(n*8)` |
| CHAR(32) | `sa.Uuid` / `sa.UUID` | `uuid.UUID`; `str` with `as_uuid=False` | ✅ Reflects as `CHAR(32)` |
| BLOB | `sa.LargeBinary` | `bytes` (documented); non-NULL reads currently return a driver LOB locator, see [Driver Compatibility, Known Issue 6](DRIVER_COMPAT.md#known-issues) | ✅ |
| CLOB | `CLOB` | `str` (documented); non-NULL reads currently return a driver LOB locator, see [Driver Compatibility, Known Issue 6](DRIVER_COMPAT.md#known-issues) | ✅ |
| SET | `SET` | Collection | ✅ |
| MULTISET | `MULTISET` | Collection | ✅ |
| SEQUENCE | `SEQUENCE` | Collection | ✅ |
| OBJECT | `OBJECT` | OID reference | ❌ Declared/compiled only |

CUBRID has no `BINARY`, `VARBINARY` or `UUID` type. `sa.BINARY(n)` / `sa.VARBINARY(n)` compile to bit strings sized in bits (`BIT(n*8)` / `BIT VARYING(n*8)`); `BINARY` pads shorter values with `\x00`. An empty `b""` is not preserved: it reads back as `None` (or as zero bytes from `BINARY(n)` on pycubrid). `sa.Uuid` and `sa.UUID` are stored as 32-character hex in `CHAR(32)`. Reflected BIT columns keep their length, so Alembic autogenerate reports no false type change for these columns. See [Standard SQL Types](TYPES.md#standard-sql-types).

---

## CI Matrix

| Validation | Routine execution | Full compatibility |
| --- | --- | --- |
| Offline | Full suite with 95% coverage: Ubuntu/Python 3.12 for PRs; Python 3.11 and 3.15 for main, changed-weekly and dispatched runs | Local full tests remain available |
| Live integration | High-risk PR Python 3.14/CUBRID 11.4; main/changed-weekly also Python 3.11/CUBRID 10.2 | Python 3.11–3.15 × CUBRID 10.2/11.0/11.2/11.4 on manual dispatch and every release |

See [CI execution policy](CI_POLICY.md). That policy selects what each run tests; it does
not define the supported versions listed above, and representative PR checks are not
evidence for every supported combination.

### SQLAlchemy compliance lanes

The official SQLAlchemy compliance suite blocks merges for both drivers. Each lane has its own reviewed known-failure baseline in `test/known_failures.txt`; see [Development Guide](DEVELOPMENT.md#sqlalchemy-compliance-lanes).

| Lane | Driver | SQLAlchemy | CUBRID (PR CI) | Known failures (11.4 / 10.2) |
|---|---|---|---|---|
| `cubrid@sa2.0` | CUBRIDdb (cubrid-python v11.3.0.51) | 2.0.53 | 11.4 | 68 / 61 |
| `pycubrid@sa2.0` | pycubrid 1.8.0 (declared floor) | 2.0.53 | 10.2 | 54 (gated on 10.2 only) |
| `pycubrid@sa2.1` | pycubrid 1.8.0 (declared floor) | 2.1.1 | 11.4 | 58 / 51 |

pycubrid is the recommended driver. Its compliance lanes pin the declared floor of `pycubrid>=1.8.0,<2.0` on purpose, so the oldest release users can install is tested. The integration lanes install the latest pycubrid release instead, and behavior that changed after 1.8.0 has its own regression tests, which are strict xfails on 1.8.0 (#479).

Most known failures are shared by both drivers: CUBRID backend rules (identifier case folding, `[ ]` identifier delimiters, no window frame clause, per-row foreign-key checks, single-precision `FLOAT`) and open dialect reflection/DDL bugs listed in `test/known_failures.txt`. Only the CUBRIDdb lane carries its NUMERIC truncation and integer-division entries.

## Test Coverage

Offline and integration test counts grow with every PR; see the `offline-tests`
/ `integration-tests` CI job output for current numbers instead of a pinned
snapshot here.

| Metric | Value |
|---|---|
| Coverage threshold | 95% (CI-enforced, `--cov-fail-under=95` in the `offline-tests` job) |

---

*See also: [Connection Guide](CONNECTION.md) · [Type System](TYPES.md) · [Feature Support](FEATURE_SUPPORT.md) · [Driver Compatibility](DRIVER_COMPAT.md) · [Changelog](../CHANGELOG.md)*
