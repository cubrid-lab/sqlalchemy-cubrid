# Architecture

## Design Objectives
sqlalchemy-cubrid is designed to provide a robust, modern interface between SQLAlchemy and the CUBRID database. Its core design goals include:

*   Full SQLAlchemy 2.0–2.1 dialect implementation
*   Three driver modes (C-extension CUBRIDdb + pure Python pycubrid + async pycubrid.aio)
*   Schema reflection (tables, columns, constraints, indexes, comments)
*   Custom DML extensions (ON DUPLICATE KEY UPDATE, MERGE, REPLACE)
*   Alembic migration support
*   PEP 561 typed

## High-Level Flow

### Phase 1: Engine Creation & Connection
This phase covers how SQLAlchemy discovers the CUBRID dialect and establishes a physical connection to the CUBRID Server.

```mermaid
sequenceDiagram
    participant App
    participant SA as SQLAlchemy
    participant Registry as Dialect Registry
    participant Dialect as CubridDialect
    participant Driver as pycubrid / CUBRIDdb
    participant DB as CUBRID Server

    App->>SA: create_engine("cubrid+pycubrid://dba@host:33000/testdb")
    rect rgb(230, 245, 255)
      note over SA, Registry: Phase 1 — Dialect Discovery
      SA->>Registry: Lookup "cubrid.pycubrid" entry point
      Registry-->>SA: PyCubridDialect class
      SA->>Dialect: Instantiate dialect
      Dialect->>Driver: import_dbapi() → import pycubrid
    end
    
    App->>SA: engine.connect()
    rect rgb(230, 255, 230)
      note over SA, DB: Phase 2 — Physical Connection
      SA->>Dialect: create_connect_args(url)
      Dialect-->>SA: (host, port, database, user, password)
      SA->>Driver: pycubrid.connect(host, port, database, user, password)
      Driver->>DB: CAS handshake + OpenDatabase
      DB-->>Driver: Session established
      Driver-->>SA: Connection object
      Dialect->>Driver: on_connect() → set autocommit=False
    end
    SA-->>App: Connection
```

### Phase 2: SQL Compilation
This phase describes the transformation of SQLAlchemy Expression Language constructs into CUBRID-compatible SQL strings and their subsequent execution.

```mermaid
sequenceDiagram
    participant App
    participant SA as SQLAlchemy Core
    participant Compiler as CubridCompiler
    participant TypeCompiler as CubridTypeCompiler
    participant Driver as pycubrid
    participant CAS as CAS Process
    
    App->>SA: conn.execute(select(users).where(users.c.id == 1))
    rect rgb(255, 245, 230)
      note over SA, TypeCompiler: SQL Compilation
      SA->>Compiler: process(select_statement)
      Compiler->>Compiler: visit_select() → column clause
      Compiler->>Compiler: limit_clause() → LIMIT/OFFSET (no FETCH FIRST)
      Compiler->>Compiler: for_update_clause()
      Compiler->>TypeCompiler: process column types
      TypeCompiler-->>Compiler: CUBRID SQL type strings
      Compiler-->>SA: "SELECT users.id, ... FROM users WHERE users.id = ?"
    end
    rect rgb(230, 255, 230)
      note over SA, CAS: Execution
      SA->>Driver: cursor.execute(sql, params)
      Driver->>CAS: PrepareAndExecute packet
      CAS-->>Driver: Result rows
      Driver-->>SA: DB-API cursor with results
    end
    SA-->>App: CursorResult
```

## Schema Reflection
The reflection process allows SQLAlchemy to inspect an existing CUBRID database and reconstruct Table objects automatically.

```mermaid
sequenceDiagram
    participant App
    participant SA as SQLAlchemy
    participant Dialect as CubridDialect
    participant CAS as CAS Process
    
    App->>SA: metadata.reflect(engine)
    SA->>Dialect: get_table_names(connection)
    Dialect->>CAS: SELECT class_name FROM db_class
    CAS-->>Dialect: Table list
    
    loop For each table
      SA->>Dialect: get_columns(connection, table_name)
      Dialect->>CAS: SHOW COLUMNS IN "table_name"
      CAS-->>Dialect: Column definitions
      
      SA->>Dialect: get_pk_constraint(connection, table_name)
      Dialect->>CAS: SHOW COLUMNS IN "table_name" (collect PRI columns)
      Dialect->>CAS: Optional db_constraint lookup for PK name
      CAS-->>Dialect: PK columns (+ optional constraint name)
      
      SA->>Dialect: get_foreign_keys(connection, table_name)
      Dialect->>CAS: SHOW CREATE TABLE (parse FK clauses)
      CAS-->>Dialect: FK constraints
      
      SA->>Dialect: get_indexes(connection, table_name)
      Dialect->>CAS: SELECT ... FROM _db_index (batch PK/FK flags)
      Dialect->>CAS: SHOW INDEXES IN "table_name"
      CAS-->>Dialect: Non-PK/non-FK index definitions
    end
    
    SA-->>App: MetaData with reflected tables
```

## Module Boundaries
The package is organized into specialized modules, each handling a specific aspect of the dialect's functionality.

```mermaid
flowchart TD
    init["__init__.py<br/>Public API: types, insert(), merge(), replace(), trace_query()"]
    dialect["dialect.py<br/>CubridDialect: reflection, connection, isolation"]
    pycubrid_d["pycubrid_dialect.py<br/>PyCubridDialect: pure Python variant"]
    aio_pycubrid_d["aio_pycubrid_dialect.py<br/>PyCubridAsyncDialect: async variant"]
    compiler["compiler.py<br/>SQL, DDL, Type compilers"]
    base["base.py<br/>ExecutionContext, IdentifierPreparer"]
    dml["dml.py<br/>ODKU, MERGE, REPLACE constructs"]
    compat["_compat.py<br/>SQLAlchemy compatibility helpers"]
    types["types.py<br/>CUBRID type system"]
    trace_mod["trace.py<br/>Query tracing utility"]
    req["requirements.py<br/>SA test requirement flags"]
    alembic_mod["alembic_impl.py<br/>CubridImpl DDL operations"]
    
    init --> types
    init --> dml
    dialect --> base
    dialect --> compiler
    dialect --> types
    pycubrid_d --> dialect
    aio_pycubrid_d --> pycubrid_d
    compiler --> types
    compiler --> base
    compiler --> compat
    trace_mod --> dialect
    
    %% External dependencies
    sa["SQLAlchemy 2.0"]
    pycubrid_pkg["pycubrid / pycubrid.aio (driver)"]
    alembic_pkg["Alembic"]
    
    dialect -.-> sa
    pycubrid_d -.-> pycubrid_pkg
    aio_pycubrid_d -.-> pycubrid_pkg
    compiler -.-> sa
    alembic_mod -.-> alembic_pkg
    req -.-> sa
```

### Module Descriptions

#### `__init__.py`
Defines the public API boundary, exporting CUBRID-specific types and DML extensions like `insert()`, `merge()`, and `replace()`. It serves as the primary entry point for users of the dialect.

#### `dialect.py`
Contains the base `CubridDialect` class, implementing core logic for schema reflection, connection management, and transaction isolation levels. Reflection (`get_columns`, `get_indexes`, `get_foreign_keys`, `get_pk_constraint`, `get_unique_constraints`) is implemented here. It defaults to the C-extension driver `CUBRIDdb`.

#### `pycubrid_dialect.py`
Implements the `PyCubridDialect` variant, which uses the pure Python `pycubrid` driver. It overrides connection argument parsing and connection-time initialization logic.

#### `aio_pycubrid_dialect.py`
Implements `PyCubridAsyncDialect`, the async dialect variant used by `cubrid+aiopycubrid://`. It adapts `pycubrid.aio` for SQLAlchemy's async engine and `AsyncSession` APIs.

#### `compiler.py`
Houses the SQL, DDL, and Type compilers. It translates SQLAlchemy's abstract syntax trees into CUBRID-specific SQL dialects, handling nuances like LIMIT/OFFSET and FOR UPDATE clauses.

#### `_compat.py`
Provides narrow compatibility shims around SQLAlchemy attributes and behavior that are not fully public APIs (`_for_update_arg`, `_limit_clause`, `_offset_clause`, and typed bind recreation helpers), so compiler logic can stay centralized and easier to adapt across SQLAlchemy releases.

#### `base.py`
Provides the `CubridExecutionContext` for statement execution state and the `CubridIdentifierPreparer` for handling CUBRID's lowercase identifier folding and quoting rules.

#### `dml.py`
Defines custom DML constructs for CUBRID-specific features such as `ON DUPLICATE KEY UPDATE` (ODKU), `MERGE INTO`, and `REPLACE INTO`.

#### `types.py`
Implements the CUBRID-specific type system, mapping SQLAlchemy's generic types to CUBRID's internal types like `SET`, `MULTISET`, and `BIT`.

#### `trace.py`
Provides the `trace_query()` utility for enabling CUBRID query tracing around a statement execution and returning trace output for debugging and performance analysis.

#### `requirements.py`
Defines feature flags used by the SQLAlchemy test suite to determine which behavioral tests should be executed against a CUBRID backend.

#### `alembic_impl.py`
Provides the `CubridImpl` class for Alembic, enabling DDL migration support and defining CUBRID's lack of transactional DDL capabilities.

## Dialect Discovery
SQLAlchemy uses entry points to discover and load the appropriate dialect class based on the provided connection URL.

```mermaid
flowchart TD
    url["Connection URL<br/>cubrid+pycubrid://dba@host:33000/db"]
    parse["SQLAlchemy URL Parser<br/>backend=cubrid, driver=pycubrid"]
    entry["Entry Point Lookup<br/>sqlalchemy.dialects → cubrid.pycubrid"]
    
    url --> parse
    parse --> entry
    
    entry -->|"cubrid://"| cubrid_dialect["CubridDialect<br/>(C-extension CUBRIDdb)"]
    entry -->|"cubrid.cubrid://"| cubrid_dialect
    entry -->|"cubrid+pycubrid://"| pycubrid_dialect["PyCubridDialect<br/>(Pure Python pycubrid)"]
    entry -->|"cubrid+aiopycubrid://"| aio_pycubrid_dialect["PyCubridAsyncDialect<br/>(Async pycubrid.aio)"]
    
    cubrid_dialect --> import_c["import CUBRIDdb"]
    pycubrid_dialect --> import_py["import pycubrid"]
    aio_pycubrid_dialect --> import_aio["import pycubrid.aio"]
    
    alembic_entry["Entry Point: alembic.ddl → cubrid"]
    alembic_entry --> alembic_impl["CubridImpl<br/>transactional_ddl = False"]
```

## Driver Architecture
The dialect supports the legacy C-extension driver, the modern pure Python driver, and the async pycubrid.aio variant through a hierarchical class structure.

```mermaid
flowchart TD
    sa_default["sqlalchemy.engine.default<br/>DefaultDialect"]
    cubrid_base["CubridDialect<br/>dialect.py<br/>• reflection<br/>• isolation levels<br/>• type mapping<br/>• import_dbapi() → CUBRIDdb"]
    pycubrid_variant["PyCubridDialect<br/>pycubrid_dialect.py<br/>• import_dbapi() → pycubrid<br/>• create_connect_args()<br/>• on_connect()<br/>• do_ping()"]
    aio_variant["PyCubridAsyncDialect<br/>aio_pycubrid_dialect.py<br/>• is_async = True<br/>• import_dbapi() → pycubrid.aio adapter<br/>• async connection adaptation"]
    
    sa_default --> cubrid_base
    cubrid_base --> pycubrid_variant
    pycubrid_variant --> aio_variant
    
    cubrid_base -.->|"loads"| cci["CUBRIDdb<br/>(C-extension driver)"]
    pycubrid_variant -.->|"loads"| pure["pycubrid<br/>(Pure Python driver)"]
    aio_variant -.->|"loads"| pure_async["pycubrid.aio<br/>(Async pure Python driver)"]
```

## Key Design Decisions

*   **SQLAlchemy `<2.3` pin**: Uses three remaining private SA attributes (`select._limit_clause`, `select._offset_clause`, `select._for_update_arg`) via `_compat.py` helpers at compiler.py:93, 104-105 — requires version pinning until public alternatives exist.
*   **BOOLEAN → SMALLINT mapping**: CUBRID has no native BOOLEAN — dialect maps to `SMALLINT` (0/1).
*   **JSON type support (v1.2.0+)**: Full JSON type mapping including `JSON`, `JSONIndexType`, `JSONPathType`, with path access via `json_getattr` and `json_getitem_op`. Requires CUBRID ≥ 10.2.
*   **`transactional_ddl = False`**: CUBRID auto-commits DDL statements — Alembic cannot roll back failed migrations.
*   **`supports_statement_cache = True`**: Required for SA 2.0 performance — dialect is cache-safe.
*   **Lowercase identifier folding**: CUBRID folds to lowercase (not SQL-standard uppercase) — `CubridIdentifierPreparer` handles this.
*   **No RELEASE SAVEPOINT**: CUBRID doesn't support it — `do_release_savepoint()` is a no-op.

## Public API Boundary

```python
# DML Extensions
insert()    # Insert with .on_duplicate_key_update()
merge()     # MERGE INTO ... USING ... ON ... WHEN MATCHED/NOT MATCHED
replace()   # REPLACE INTO
trace_query() # Query tracing utility

# Types (CUBRID-specific)
STRING, BIT, CLOB, BLOB, SET, MULTISET, SEQUENCE, MONETARY, OBJECT
JSON, JSONIndexType, JSONPathType
NCHAR, NVARCHAR, DOUBLE_PRECISION, REAL

# Types (standard, re-exported)
SMALLINT, INTEGER, BIGINT, NUMERIC, DECIMAL, FLOAT, DOUBLE
CHAR, VARCHAR, DATE, TIME, TIMESTAMP, DATETIME

# Entry Points (registered via pyproject.toml)
cubrid://          → CubridDialect
cubrid.cubrid://   → CubridDialect  
cubrid+pycubrid:// → PyCubridDialect
cubrid+aiopycubrid:// → PyCubridAsyncDialect
cubrid (alembic)   → CubridImpl
```

## What This Package Owns / Does Not Own

### Owns
*   SQLAlchemy dialect for CUBRID
*   SQL compilation (SELECT/INSERT/UPDATE/DELETE with CUBRID syntax)
*   DDL compilation
*   Type mapping
*   Schema reflection
*   DML extensions (ODKU, MERGE, REPLACE)
*   Alembic DDL support
*   Identifier quoting

### Does Not Own
*   The CUBRID driver itself (use pycubrid or CUBRIDdb)
*   Connection pooling (SQLAlchemy handles this)
*   ORM model definitions (user code)
*   The CAS wire protocol (pycubrid handles this)
*   Query optimization (CUBRID server handles this)

## Related Documents
*   [Connection Guide](CONNECTION.md)
*   [Type System](TYPES.md)
*   [Isolation Levels](ISOLATION_LEVELS.md)
*   [DML Extensions](DML_EXTENSIONS.md)
*   [Alembic Guide](ALEMBIC.md)
*   [Feature Support](FEATURE_SUPPORT.md)
*   [Support Matrix](SUPPORT_MATRIX.md)
*   [Driver Compatibility](DRIVER_COMPAT.md)
