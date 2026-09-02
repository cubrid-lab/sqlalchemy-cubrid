# CUBRID-Python Driver Compatibility

This document describes the tested compatibility matrix between `sqlalchemy-cubrid`,
the CUBRID Python driver (`CUBRIDdb`), and CUBRID server versions.

---

## Table of Contents

- [Driver Overview](#driver-overview)
- [Version Compatibility Matrix](#version-compatibility-matrix)
- [Exception Hierarchy](#exception-hierarchy)
- [Driver API Usage](#driver-api-usage)
- [Known Issues](#known-issues)
- [Installation Notes](#installation-notes)

---

## Driver Overview

| Property | Value |
|---|---|
| PyPI package | `CUBRID-Python` |
| Import name | `CUBRIDdb` |
| Type | C extension (CPython only) |
| DBAPI level | DB-API 2.0 (PEP 249) |
| Parameter style | `qmark` |
| Source | [github.com/CUBRID/cubrid-python](https://github.com/CUBRID/cubrid-python) |

The driver wraps the CUBRID CCI (C Client Interface) library. It is **not** a pure
Python driver and requires compilation against the CCI headers.

---

## Version Compatibility Matrix

### Tested Configurations

| sqlalchemy-cubrid | CUBRID-Python Driver | CUBRID Server | Python | Status |
|---|---|---|---|---|
| 0.4.0 | v11.3.0.51 | 11.4 | 3.10 – 3.14 | ✅ Tested in CI |
| 0.4.0 | v11.3.0.51 | 11.2 | 3.10 – 3.14 | ✅ Tested in CI |
| 0.4.0 | v11.3.0.51 | 11.0 | 3.10 – 3.14 | ✅ Tested in CI |
| 0.4.0 | v11.3.0.51 | 10.2 | 3.10 – 3.14 | ✅ Tested in CI |
| 0.3.x | v11.3.0.51 | 10.2 – 11.4 | 3.10 – 3.13 | ✅ Tested |

### CUBRID Server Version Support

| Server Version | Driver Version | Notes |
|---|---|---|
| 11.4 | v11.3.0.51 | Latest stable |
| 11.2 | v11.3.0.51 | LTS release |
| 11.0 | v11.3.0.51 | Legacy support |
| 10.2 | v11.3.0.51 | Minimum supported |
| 12.x | — | Not yet released; will be tested when available |

### Python Version Support

| Python | Status | Notes |
|---|---|---|
| 3.10 | ✅ Fully supported | Minimum version |
| 3.11 | ✅ Fully supported | |
| 3.12 | ✅ Fully supported | |
| 3.13 | ✅ Fully supported | |
| 3.14 | 🔄 CI matrix added | Pre-release; depends on driver C extension compatibility |

---

## Exception Hierarchy

CUBRIDdb exposes a **limited** exception hierarchy compared to PEP 249:

```mermaid
graph TD
    base["BaseException"] --> exc["Exception"]
    exc --> err["CUBRIDdb.Error (Base DBAPI error)"]
    err --> iface["CUBRIDdb.InterfaceError (Driver-level errors)"]
    err --> db["CUBRIDdb.DatabaseError (Server-level errors)"]
    err --> ns["CUBRIDdb.NotSupportedError (Unsupported operations)"]
```

**Missing PEP 249 exceptions** (not provided by the driver):
- `OperationalError` — subsumed by `DatabaseError`
- `ProgrammingError` — subsumed by `DatabaseError`
- `InternalError` — subsumed by `DatabaseError`
- `DataError` — subsumed by `DatabaseError`
- `IntegrityError` — subsumed by `DatabaseError`

This means all database-level errors (constraint violations, syntax errors, connection
issues) are raised as `DatabaseError`. The `sqlalchemy-cubrid` dialect uses
**string-based message matching** to distinguish disconnect errors from other failures.

---

## Driver API Usage

The dialect relies on these driver-specific APIs:

### Connection Methods

| Method | Purpose | Used by |
|---|---|---|
| `conn.ping()` | Check connection liveness | `CubridDialect.do_ping()` |
| `conn.get_last_insert_id()` | Get auto-increment value | `CubridExecutionContext.get_lastrowid()` |
| `conn.set_autocommit(bool)` | Control autocommit | `CubridDialect.on_connect()` |
| `conn.cursor()` | Create cursor | Standard DB-API |

### Error Code Extraction

```python
# Error codes are in exception.args[0]
try:
    cursor.execute("invalid sql")
except CUBRIDdb.DatabaseError as e:
    code = e.args[0]  # int or str
```

The dialect's `_extract_error_code()` handles both integer codes and string-embedded
codes (e.g., `"-21003 Cannot communicate with broker"`).

---

## Known Issues

### 1. No `OperationalError` for Disconnect Detection

Since the driver doesn't provide `OperationalError`, the dialect cannot use
`isinstance(e, dbapi.OperationalError)` like MySQL dialects do. Instead, it uses:
- String pattern matching against 15 known disconnect messages
- Numeric error code matching for CCI communication errors

### 2. CCI Library Dependency

The driver requires the CCI library to be compiled from source. In CI, this is handled by:
```bash
git clone --branch v11.3.0.51 --depth 1 https://github.com/CUBRID/cubrid-python.git
cd cubrid-python/cci-src && mkdir build_x86_64_release && cd build_x86_64_release
cmake ../ && make -j$(nproc)
```

### 3. `cursor.lastrowid` Not Available

The standard DB-API `cursor.lastrowid` attribute is not implemented. The dialect
uses `connection.get_last_insert_id()` instead, with a `SELECT LAST_INSERT_ID()`
SQL fallback.

### 4. CUBRID 12.x Compatibility

CUBRID 12 has not yet been released. When available, the driver and dialect will be
tested and the CI matrix updated. Potential concerns:
- CCI API changes may require driver recompilation
- New SQL features may need compiler updates
- New data types may need type mapping additions

---

## Installation Notes

For the pure Python pycubrid dialect variants, install `sqlalchemy-cubrid[pycubrid]` with `pycubrid>=1.3.2,<2.0`. That minimum version is required for native sync and async `ping(False)` support used by `pool_pre_ping`.

### From Source (Required for CI)

```bash
# Clone the driver
git clone --branch v11.3.0.51 --depth 1 \
  https://github.com/CUBRID/cubrid-python.git

# Build CCI library
cd cubrid-python/cci-src
mkdir -p build_x86_64_release && cd build_x86_64_release
cmake ../ && make -j$(nproc)

# Install
cd /path/to/cubrid-python
pip install .
```

### Verify Installation

```python
import CUBRIDdb
print(CUBRIDdb.__version__)  # Should print version string
```

---

*See also: [Connection Guide](CONNECTION.md) · [Development](DEVELOPMENT.md) · [Feature Support](FEATURE_SUPPORT.md)*
