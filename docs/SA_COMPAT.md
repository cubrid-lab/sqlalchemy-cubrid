# SQLAlchemy Internal API Compatibility

This document tracks every SQLAlchemy internal or semi-private API used by
`sqlalchemy-cubrid`, why it is used, the SQLAlchemy version range verified by
tests, and what would break if SQLAlchemy changes the API.

Verified against: SQLAlchemy `2.0.x` and `2.1.x` (project pin: `>=2.0,<2.3`).

## Internal API Inventory

| API | Location | Used for | Verified | Breakage if changed |
|---|---|---|---|---|
| `Select._for_update_arg` | `sqlalchemy_cubrid/_compat.py`, `sqlalchemy_cubrid/compiler.py` | Render `FOR UPDATE OF ...` columns | 2.0, 2.1 | `FOR UPDATE` clauses lose `OF` targets or fail to compile |
| `Select._limit_clause` | `sqlalchemy_cubrid/_compat.py`, `sqlalchemy_cubrid/compiler.py` | Render CUBRID `LIMIT offset, count` form | 2.0, 2.1 | LIMIT/OFFSET SQL generation breaks |
| `Select._offset_clause` | `sqlalchemy_cubrid/_compat.py`, `sqlalchemy_cubrid/compiler.py` | Render CUBRID `LIMIT offset, count` form | 2.0, 2.1 | OFFSET SQL generation breaks |
| `Select._distinct` | `sqlalchemy_cubrid/_compat.py`, `sqlalchemy_cubrid/compiler.py` | Render `DISTINCT` prefix in SELECT | 2.0, 2.1 | DISTINCT queries lose the keyword |
| `sqlalchemy.sql._typing._DMLTableArgument` | `sqlalchemy_cubrid/dml.py` | Type contract for custom `insert/merge/replace` factories | 2.0, 2.1 | Type checking and signatures drift; runtime usually unaffected |
| `sqlalchemy.sql.base._generative` | `sqlalchemy_cubrid/dml.py` | SQLAlchemy-style immutable statement chaining | 2.0, 2.1 | `on_duplicate_key_update()` / `MERGE` builders become mutable or incorrect |
| `sqlalchemy.sql.base._exclusive_against` | `sqlalchemy_cubrid/dml.py` | Guard against duplicate post-values clauses | 2.0, 2.1 | Duplicate ODKU clauses can be built without clear errors |
| `sqlalchemy.util.typing.Self` | `sqlalchemy_cubrid/dml.py` | Typing for fluent DML methods | 2.0, 2.1 | Typing regressions for fluent API; runtime usually unaffected |
| `sqlalchemy.connectors.asyncio.AsyncAdapt_dbapi_connection` | `sqlalchemy_cubrid/aio_pycubrid_dialect.py` | Async connection adapter for pycubrid.aio | 2.0, 2.1 | Async dialect cannot wrap pycubrid connections |
| `sqlalchemy.connectors.asyncio.AsyncAdapt_dbapi_cursor` | `sqlalchemy_cubrid/aio_pycubrid_dialect.py` | Async cursor adapter for pycubrid.aio | 2.0, 2.1 | Async cursor operations fail |
| `sqlalchemy.connectors.asyncio.AsyncAdapt_dbapi_module` | `sqlalchemy_cubrid/aio_pycubrid_dialect.py` | Async DBAPI module adapter | 2.0, 2.1 | Async engine creation fails |
| `sqlalchemy.util.concurrency.await_only` | `sqlalchemy_cubrid/aio_pycubrid_dialect.py` | Run coroutines from sync context in async adapter | 2.0, 2.1 | Async connection/cursor bridging fails |

## Notes On Non-Internal Imports

The project also imports SQLAlchemy modules such as `sqlalchemy.sql.compiler`,
`sqlalchemy.sql.elements`, and `sqlalchemy.sql.type_api`. These are not
underscore-prefixed internals and are part of common dialect extension
patterns, but they are still monitored in canary CI because dialects depend on
compiler internals in practice.

## Risk Summary

- Highest risk: `Select._for_update_arg`, `Select._limit_clause`,
  `Select._offset_clause`, and `Select._distinct` because they directly affect SQL compilation.
- High risk: `sqlalchemy.connectors.asyncio` adapters and `await_only` because
  the entire async dialect depends on them.
- Medium risk: `_generative` and `_exclusive_against` because they control
  custom DML builder behavior.
- Lower runtime risk: `_DMLTableArgument` and `Self` (mostly typing surface).

## Validation Plan

- Keep running full offline tests on SQLAlchemy `2.0.x` and `2.1.x`.
- Run a SQLAlchemy `2.1` pre-release canary job with `continue-on-error`.
- If canary fails, prioritize replacing direct internal usage where public
  alternatives exist, or align with upstream dialect patterns.
