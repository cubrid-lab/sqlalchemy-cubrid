# Dialect guide

> Moved from the root [AGENTS.md](../../AGENTS.md) (#907). Owner: sqlalchemy-cubrid maintainers.
> Every rule in the root file still applies. Scope: CUBRID differences that the compiler, DDL, reflection and Alembic code must respect, the URL format and where tested versions live ([support matrix](../SUPPORT_MATRIX.md)).

## CUBRID-Specific Knowledge

### Key Differences from MySQL/PostgreSQL

- **No RETURNING** — `INSERT/UPDATE/DELETE ... RETURNING` not supported
- **No native BOOLEAN** — mapped to `SMALLINT` (0/1)
- **JSON support (10.2+)** — native JSON type is mapped in this dialect, including path/index helpers and reflection support
- **No ARRAY** — uses `SET`, `MULTISET`, `SEQUENCE` collection types
- **No Sequences** — uses `AUTO_INCREMENT`
- **No multi-schema** — single-schema model
- **No RELEASE SAVEPOINT** — `do_release_savepoint()` is a no-op
- **DDL is transactional** — `ROLLBACK` undoes DDL and DDL never commits earlier DML; only client autocommit (turned off by the dialect) commits it early. `transactional_ddl = True`, so a whole Alembic upgrade is one transaction by default; recommend `transaction_per_migration=True` for long or large-table migrations (uncommitted DDL holds schema locks)
- **3 MVCC isolation levels** — `READ COMMITTED` (default), `REPEATABLE READ`, `SERIALIZABLE`
- **Identifier folding** — lowercase (not uppercase like SQL standard)
- **Max identifier length** — 254 characters

### Connection Format

SQLAlchemy URL: `cubrid://user:password@host:port/dbname`
CUBRID native:  `CUBRID:host:port:dbname:::`

The dialect translates automatically in `create_connect_args()`.

### CUBRID Versions Tested

Supported and tested CUBRID versions are maintained in
[docs/SUPPORT_MATRIX.md](../SUPPORT_MATRIX.md); CI lanes are defined in
[docs/CI_POLICY.md](../CI_POLICY.md). Tests use Docker images `cubrid/cubrid:{version}`.
