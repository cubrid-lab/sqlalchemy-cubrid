# sqlalchemy-cubrid

**SQLAlchemy-2.0–2.2-Dialekt für die CUBRID-Datenbank** — Python-ORM, Schema-Reflexion, Alembic-Migrationen und Typzuordnung für SQLAlchemy und CUBRID-spezifische Typen.

[🇰🇷 한국어](README.ko.md) · [🇺🇸 English](../README.md) · [🇨🇳 中文](README.zh.md) · [🇮🇳 हिन्दी](README.hi.md) · [🇩🇪 Deutsch](README.de.md) · [🇷🇺 Русский](README.ru.md)

<!-- BADGES:START -->
[![PyPI version](https://img.shields.io/pypi/v/sqlalchemy-cubrid)](https://pypi.org/project/sqlalchemy-cubrid)
[![python version](https://img.shields.io/pypi/pyversions/sqlalchemy-cubrid)](https://www.python.org)
[![ci workflow](https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/workflows/ci.yml/badge.svg)](https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/workflows/ci.yml)
[![integration-full workflow](https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/workflows/integration-full.yml/badge.svg)](https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/workflows/integration-full.yml)
[![coverage](https://codecov.io/gh/cubrid-lab/sqlalchemy-cubrid/branch/main/graph/badge.svg)](https://codecov.io/gh/cubrid-lab/sqlalchemy-cubrid)
[![license](https://img.shields.io/github/license/cubrid-lab/sqlalchemy-cubrid)](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/cubrid-lab/sqlalchemy-cubrid)](https://github.com/cubrid-lab/sqlalchemy-cubrid)
[![docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://cubrid-lab.github.io/sqlalchemy-cubrid/)
<!-- BADGES:END -->

---

> **Status: Production/Stable** — Stabiler, gewarteter SQLAlchemy-Dialekt für CUBRID 10.2–11.4. Jeder PR wird durch Live-Datenbank-Integrations-CI validiert.

## Warum sqlalchemy-cubrid?

CUBRID ist eine leistungsstarke relationale Open-Source-Datenbank, die in
koreanischen Behörden und Unternehmensanwendungen weit verbreitet ist. Bislang
gab es keinen aktiv gepflegten SQLAlchemy-Dialekt, der die moderne 2.0–2.2-API
unterstützt.

**sqlalchemy-cubrid** schließt diese Lücke:

- Vollständiger SQLAlchemy-2.0–2.2-Dialekt mit **Statement-Caching** und **PEP-561-Typisierung**
- **619 Offline-Tests** mit **~98,26 % Codeabdeckung** — zum Ausführen ist keine Datenbank erforderlich
- **Nebenläufigkeits-Stresstests** — `QueuePool`-basierte synchrone Threads + `asyncio.gather`-Workloads gegen echtes CUBRID validiert
- **SQLAlchemy-2.2-fähiger Compat-Shim** — Zugriff auf private APIs in `_compat.py` gekapselt (bis zur vollständigen SA-2.2-Validierung weiterhin auf `<2.3` festgelegt)
- Gegen **4 CUBRID-Versionen** (10.2, 11.0, 11.2, 11.4) auf **Python 3.10 -- 3.14** getestet
- CUBRID-spezifische DML-Konstrukte: `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`
- Alembic-Migrationsunterstützung sofort einsatzbereit
- **Drei Treiberoptionen** — C-Erweiterung (`cubrid://`), reines Python (`cubrid+pycubrid://`) oder asynchrones reines Python (`cubrid+aiopycubrid://`)

## Architektur

```mermaid
flowchart TD
    app["Application"] --> sa["SQLAlchemy Core/ORM"]
    sa --> dialect["CubridDialect"]
    dialect --> pycubrid["pycubrid driver"]
    dialect --> cext["CUBRIDdb driver"]
    dialect --> aio["pycubrid.aio async driver"]
    pycubrid --> server["CUBRID Server"]
    cext --> server
    aio --> server
```

```mermaid
flowchart TD
    expr["SQL Expression"] --> compiler["CubridSQLCompiler"] --> sql["SQL String"]
```

## Anforderungen

- Python 3.10+
- SQLAlchemy 2.0 – 2.2
- [CUBRID-Python](https://github.com/CUBRID/cubrid-python) (C-Erweiterung) **oder** [pycubrid](https://github.com/cubrid-lab/pycubrid) (reines Python)

## Installation

```bash
pip install sqlalchemy-cubrid
```

Mit dem Pure-Python-Treiber (kein C-Build erforderlich):

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

Mit Alembic-Unterstützung:

```bash
pip install "sqlalchemy-cubrid[alembic]"
```

## Schnellstart

### Core (Verbindungsebene)

```python
from sqlalchemy import create_engine, text

engine = create_engine("cubrid://dba:password@localhost:33000/demodb")

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.scalar())
```

### ORM (Sitzungsebene)

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

### Async

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

engine = create_async_engine("cubrid+aiopycubrid://dba:password@localhost:33000/demodb")

async with AsyncSession(engine) as session:
    result = await session.execute(text("SELECT 1"))
    print(result.scalar())
```

## Funktionen

- Typzuordnung für SQLAlchemy-Standardtypen und CUBRID-spezifische Typen — numerische, String-, Datum/Zeit-, Bit-, LOB-, Collection- und JSON-Typen
- SQL-Kompilierung -- SELECT, JOIN, CAST, LIMIT/OFFSET, Unterabfragen, CTEs, Fensterfunktionen
- DML-Erweiterungen -- `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`, `FOR UPDATE`, `TRUNCATE`
- DDL-Unterstützung -- `COMMENT`, `IF NOT EXISTS` / `IF EXISTS`, `AUTO_INCREMENT`
- Schema-Reflexion -- Tabellen, Views, Spalten, PKs, FKs, Indizes, Unique-Constraints, Kommentare
- Alembic-Migrationen über `CubridImpl` (automatisch erkannter Entry-Point)
- Drei CUBRID-MVCC-Isolationsstufen — `READ COMMITTED` (Standard), `REPEATABLE READ`, `SERIALIZABLE`
- Async-Unterstützung — `create_async_engine("cubrid+aiopycubrid://...")` über pycubrid.aio

## Bekannte Einschränkungen

- **Kein `RETURNING`** — `INSERT/UPDATE/DELETE ... RETURNING` wird nicht unterstützt; stattdessen `cursor.lastrowid` oder `LAST_INSERT_ID()` verwenden
- **Keine Sequenzen** — CUBRID verwendet ausschließlich `AUTO_INCREMENT`
- **Kein Multi-Schema** — ein einzelnes Schema pro Datenbank
- **DDL committet automatisch** — Migrationen sind nicht transaktional (`transactional_ddl = False`)
- **Nur SQLAlchemy 2.0–2.2** — wegen interner API-Abhängigkeiten auf `<2.3` festgelegt ([Details](ARCHITECTURE.md))
- **Async erfordert pycubrid >= 1.2.0,<2.0** — der Treiber `cubrid+aiopycubrid://` benötigt die von diesem Projekt aktuell unterstützte async-fähige pycubrid-Paketlinie

## Dokumentation

| Leitfaden | Beschreibung |
|---|---|
| [Verbindung](CONNECTION.md) | Verbindungszeichenfolgen, URL-Format, Treibereinrichtung, Pool-Tuning |
| [Typzuordnung](TYPES.md) | Vollständige Typzuordnung, CUBRID-spezifische Typen, Sammlungstypen |
| [DML-Erweiterungen](DML_EXTENSIONS.md) | ON DUPLICATE KEY UPDATE, MERGE, REPLACE INTO, Query-Trace |
| [Isolationsstufen](ISOLATION_LEVELS.md) | Die drei CUBRID-MVCC-Isolationsstufen, Konfiguration |
| [Alembic-Migrationen](ALEMBIC.md) | Einrichtung, Konfiguration, Einschränkungen, Batch-Workarounds |
| [Feature-Unterstützung](FEATURE_SUPPORT.md) | Vergleich mit MySQL, PostgreSQL, SQLite |
| [ORM-Kochbuch](ORM_COOKBOOK.md) | Praktische ORM-Beispiele, Beziehungen, Abfragen |
| [Entwicklung](DEVELOPMENT.md) | Entwicklungsumgebung, Tests, Docker, Abdeckung, CI/CD |
| [Treiberkompatibilität](DRIVER_COMPAT.md) | CUBRID-Python-Treiberversionen und bekannte Probleme |
| [Fehlerbehebung](TROUBLESHOOTING.md) | Häufige Probleme, Fehlerlösungen, Debugging-Techniken |
| [Asynchrone Verbindung](CONNECTION.md#async-connection) | Einrichtung einer Async-Engine mit `cubrid+aiopycubrid://` |

## Kompatibilitätsmatrix

| Komponente | Unterstützte Versionen |
|---|---|
| Python | 3.10, 3.11, 3.12, 3.13, 3.14 |
| CUBRID | 10.2, 11.0, 11.2, 11.4 |
| SQLAlchemy | 2.0–2.2 |
| Alembic | >=1.7 |
| pycubrid (sync) | >=1.2.0,<2.0 |
| pycubrid (async) | >=1.2.0,<2.0 |

## FAQ

### Wie verbinde ich mich mit SQLAlchemy zu CUBRID?

```python
from sqlalchemy import create_engine
engine = create_engine("cubrid://dba:password@localhost:33000/demodb")
```

Für den Pure-Python-Treiber (kein C-Build erforderlich): `create_engine("cubrid+pycubrid://dba@localhost:33000/demodb")`

### Unterstützt sqlalchemy-cubrid SQLAlchemy 2.0–2.2?

Ja. sqlalchemy-cubrid wurde für SQLAlchemy 2.0–2.2 entwickelt und unterstützt die API im 2.0-Stil einschließlich `Session.execute()`, typisierter `Mapped[]`-Spalten und Statement-Caching.

### Unterstützt sqlalchemy-cubrid Alembic-Migrationen?

Ja. Installieren Sie mit `pip install "sqlalchemy-cubrid[alembic]"`. Der Dialekt registriert sich automatisch über einen Entry-Point. Beachten Sie, dass CUBRID DDL automatisch committet, daher sind Migrationen nicht transaktional.

### Welche Python-Versionen werden unterstützt?

Python 3.10, 3.11, 3.12, 3.13 und 3.14.

### Unterstützt CUBRID RETURNING-Klauseln?

Nein. CUBRID unterstützt weder `INSERT ... RETURNING` noch `UPDATE ... RETURNING`. Verwenden Sie stattdessen `cursor.lastrowid` oder `SELECT LAST_INSERT_ID()`.

### Wie verwende ich ON DUPLICATE KEY UPDATE mit CUBRID?

```python
from sqlalchemy_cubrid import insert
stmt = insert(users).values(name="Alice").on_duplicate_key_update(name="Alice Updated")
```

### Was ist der Unterschied zwischen `cubrid://` und `cubrid+pycubrid://`?

`cubrid://` verwendet den C-Erweiterungstreiber (CUBRIDdb), der eine Kompilierung erfordert. `cubrid+pycubrid://` verwendet den Pure-Python-Treiber, der allein mit pip installiert wird — ohne Build-Werkzeuge. `cubrid+aiopycubrid://` verwendet die asynchrone Variante des Pure-Python-Treibers für die Verwendung mit `create_async_engine` und `AsyncSession`.

### Unterstützt sqlalchemy-cubrid Async?

Ja. Verwenden Sie `create_async_engine("cubrid+aiopycubrid://...")` mit dem pycubrid-Async-Treiber. Erfordert `pycubrid>=1.3.2,<2.0`. Beide pycubrid-Dialekte verwenden für `pool_pre_ping` das native `Connection.ping(False)` / `AsyncConnection.ping(False)`, und alle Core- und ORM-Funktionen arbeiten mit `AsyncSession`.


## Verwandte Projekte

- [pycubrid](https://github.com/cubrid-lab/pycubrid) — Reiner Python-DB-API-2.0-Treiber für CUBRID
- [cubrid-cookbook-python](https://github.com/cubrid-lab/cubrid-cookbook-python) — Produktionsreife Python-Beispiele für CUBRID

## Roadmap

Siehe [`ROADMAP.md`](../ROADMAP.md) für die Ausrichtung des Projekts und die nächsten Meilensteine.

Für die Ökosystem-Perspektive siehe die [CUBRID Labs Ecosystem Roadmap](https://github.com/cubrid-lab/.github/blob/main/ROADMAP.md) und das [Project Board](https://github.com/orgs/cubrid-lab/projects/2).

## Mitwirken

Siehe [CONTRIBUTING.md](../CONTRIBUTING.md) für Hinweise und [docs/DEVELOPMENT.md](DEVELOPMENT.md) für die Entwicklungsumgebung.

## Sicherheit

Melden Sie Schwachstellen per E-Mail -- siehe [SECURITY.md](../SECURITY.md). Erstellen Sie keine öffentlichen Issues für Sicherheitsprobleme.

## Lizenz

MIT -- siehe [LICENSE](../LICENSE).
