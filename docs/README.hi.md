# sqlalchemy-cubrid

**CUBRID डेटाबेस के लिए SQLAlchemy 2.0–2.1 dialect** — SQLAlchemy और CUBRID-विशिष्ट types के लिए Python ORM, schema reflection, Alembic migrations, और type mapping प्रदान करता है।

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

> **स्थिति: Production/Stable** — CUBRID 10.2–11.4 और SQLAlchemy 2.0–2.1 के लिए स्थिर रूप से रखरखाव किया गया dialect। प्रत्येक PR को लाइव DB इंटीग्रेशन CI द्वारा सत्यापित किया जाता है।

## sqlalchemy-cubrid क्यों?

CUBRID एक उच्च-प्रदर्शन ओपन-सोर्स रिलेशनल डेटाबेस है, जिसका उपयोग कोरियाई सार्वजनिक
क्षेत्र और एंटरप्राइज़ अनुप्रयोगों में व्यापक रूप से किया जाता है। अब तक ऐसा कोई
सक्रिय रूप से maintained SQLAlchemy dialect नहीं था जो आधुनिक 2.0–2.1 API को सपोर्ट करे।

**sqlalchemy-cubrid** इस कमी को पूरा करता है:

- **statement caching** और **PEP 561 typing** के साथ पूर्ण SQLAlchemy 2.0–2.1 dialect
- **619 ऑफ़लाइन टेस्ट** और **लगभग 98.26% code coverage** — इन्हें चलाने के लिए डेटाबेस की आवश्यकता नहीं
- **Concurrency stress tests** — `QueuePool` sync threaded + `asyncio.gather` workloads को live CUBRID पर validate किया गया है
- **SQLAlchemy 2.1-ready compat shim** — private API access को `_compat.py` में wrap किया गया है (पूर्ण SA 2.1 validation तक अभी भी `<2.3` पर pinned)
- **Python 3.10 -- 3.14** पर **4 CUBRID versions** (10.2, 11.0, 11.2, 11.4) के खिलाफ टेस्ट किया गया
- CUBRID-विशिष्ट DML constructs: `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`
- Alembic migration support box से बाहर उपलब्ध
- **तीन driver options** — C-extension (`cubrid://`), pure Python (`cubrid+pycubrid://`), या async pure Python (`cubrid+aiopycubrid://`)

## आर्किटेक्चर

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

## आवश्यकताएँ

- Python 3.10+
- SQLAlchemy 2.0 – 2.1
- [CUBRID-Python](https://github.com/CUBRID/cubrid-python) (C-extension) **या** [pycubrid](https://github.com/cubrid-lab/pycubrid) (pure Python)

## इंस्टॉलेशन

```bash
pip install sqlalchemy-cubrid
```

Pure Python driver के साथ (C build की आवश्यकता नहीं):

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

Alembic support के साथ:

```bash
pip install "sqlalchemy-cubrid[alembic]"
```

## त्वरित शुरुआत

### Core (कनेक्शन-स्तर)

```python
from sqlalchemy import create_engine, text

engine = create_engine("cubrid://dba:password@localhost:33000/demodb")

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.scalar())
```

### ORM (सेशन-स्तर)

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

## विशेषताएँ

- SQLAlchemy standard types और CUBRID-विशिष्ट types के लिए type mapping — numeric, string, date/time, bit, LOB, collection, और JSON types
- SQL compilation -- SELECT, JOIN, CAST, LIMIT/OFFSET, subqueries, CTEs, window functions
- DML extensions -- `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`, `FOR UPDATE`, `TRUNCATE`
- DDL support -- `COMMENT`, `IF NOT EXISTS` / `IF EXISTS`, `AUTO_INCREMENT`
- Schema reflection -- tables, views, columns, PKs, FKs, indexes, unique constraints, comments
- `CubridImpl` के जरिए Alembic migrations (auto-discovered entry point)
- तीन CUBRID MVCC isolation levels — `READ COMMITTED` (डिफ़ॉल्ट), `REPEATABLE READ`, `SERIALIZABLE`
- Async support — pycubrid.aio के जरिए `create_async_engine("cubrid+aiopycubrid://...")`

## ज्ञात सीमाएँ

- **`RETURNING` नहीं** — `INSERT/UPDATE/DELETE ... RETURNING` समर्थित नहीं है; `cursor.lastrowid` या `LAST_INSERT_ID()` का उपयोग करें
- **कोई sequences नहीं** — CUBRID केवल `AUTO_INCREMENT` का उपयोग करता है
- **कोई multi-schema नहीं** — प्रति डेटाबेस एक single schema
- **DDL auto-commit करता है** — migrations transactional नहीं हैं (`transactional_ddl = False`)
- **केवल SQLAlchemy 2.0–2.1** — internal API dependencies के कारण `<2.3` पर pinned ([details](ARCHITECTURE.md))
- **Async के लिए pycubrid >= 1.2.0,<2.0 आवश्यक है** — `cubrid+aiopycubrid://` driver को वही async-capable pycubrid package line चाहिए जिसे यह परियोजना वर्तमान में सपोर्ट करती है

## दस्तावेज़ीकरण

| गाइड | विवरण |
|---|---|
| [कनेक्शन](CONNECTION.md) | कनेक्शन स्ट्रिंग, URL प्रारूप, driver setup, pool tuning |
| [टाइप मैपिंग](TYPES.md) | पूर्ण टाइप मैपिंग, CUBRID-विशिष्ट टाइप, collection types |
| [DML एक्सटेंशन](DML_EXTENSIONS.md) | ON DUPLICATE KEY UPDATE, MERGE, REPLACE INTO, query trace |
| [आइसोलेशन लेवल](ISOLATION_LEVELS.md) | तीन CUBRID MVCC isolation levels, configuration |
| [Alembic migrations](ALEMBIC.md) | setup, configuration, limitations, batch workarounds |
| [फ़ीचर सपोर्ट](FEATURE_SUPPORT.md) | MySQL, PostgreSQL, SQLite से तुलना |
| [ORM cookbook](ORM_COOKBOOK.md) | व्यावहारिक ORM उदाहरण, relationships, queries |
| [डेवलपमेंट](DEVELOPMENT.md) | dev setup, testing, Docker, coverage, CI/CD |
| [ड्राइवर अनुकूलता](DRIVER_COMPAT.md) | CUBRID-Python driver versions और ज्ञात समस्याएँ |
| [समस्या निवारण](TROUBLESHOOTING.md) | सामान्य समस्याएँ, error solutions, debugging techniques |
| [Async connection](CONNECTION.md#async-connection) | `cubrid+aiopycubrid://` के साथ async engine setup |

## अनुकूलता मैट्रिक्स

| घटक | समर्थित versions |
|---|---|
| Python | 3.10, 3.11, 3.12, 3.13, 3.14 |
| CUBRID | 10.2, 11.0, 11.2, 11.4 |
| SQLAlchemy | 2.0–2.1 |
| Alembic | >=1.7 |
| pycubrid (sync) | >=1.2.0,<2.0 |
| pycubrid (async) | >=1.2.0,<2.0 |

## FAQ

### मैं SQLAlchemy के साथ CUBRID से कैसे कनेक्ट करूँ?

```python
from sqlalchemy import create_engine
engine = create_engine("cubrid://dba:password@localhost:33000/demodb")
```

Pure Python driver के लिए (C build की आवश्यकता नहीं): `create_engine("cubrid+pycubrid://dba@localhost:33000/demodb")`

### क्या sqlalchemy-cubrid SQLAlchemy 2.0–2.1 को सपोर्ट करता है?

हाँ। sqlalchemy-cubrid, SQLAlchemy 2.0–2.1 के लिए बनाया गया है और `Session.execute()`, typed `Mapped[]` columns, और statement caching सहित 2.0-style API को सपोर्ट करता है।

### क्या sqlalchemy-cubrid Alembic migrations को सपोर्ट करता है?

हाँ। `pip install "sqlalchemy-cubrid[alembic]"` के साथ इंस्टॉल करें। Dialect entry point के जरिए auto-register होता है। ध्यान दें कि CUBRID DDL को auto-commit करता है, इसलिए migrations transactional नहीं हैं।

### कौन-से Python versions समर्थित हैं?

Python 3.10, 3.11, 3.12, 3.13, और 3.14।

### क्या CUBRID RETURNING clauses को सपोर्ट करता है?

नहीं। CUBRID `INSERT ... RETURNING` या `UPDATE ... RETURNING` को सपोर्ट नहीं करता। इसके बजाय `cursor.lastrowid` या `SELECT LAST_INSERT_ID()` का उपयोग करें।

### मैं CUBRID के साथ ON DUPLICATE KEY UPDATE कैसे उपयोग करूँ?

```python
from sqlalchemy_cubrid import insert
stmt = insert(users).values(name="Alice").on_duplicate_key_update(name="Alice Updated")
```

### `cubrid://` और `cubrid+pycubrid://` में क्या अंतर है?

`cubrid://` C-extension driver (CUBRIDdb) का उपयोग करता है जिसे compilation की आवश्यकता होती है। `cubrid+pycubrid://` pure Python driver का उपयोग करता है जो केवल pip से install हो जाता है — किसी build tool की आवश्यकता नहीं। `cubrid+aiopycubrid://` pure Python driver के async variant का उपयोग करता है, जो `create_async_engine` और `AsyncSession` के साथ काम करता है।

### क्या sqlalchemy-cubrid async को सपोर्ट करता है?

हाँ। pycubrid async driver के साथ `create_async_engine("cubrid+aiopycubrid://...")` का उपयोग करें। `pycubrid>=1.3.2,<2.0` आवश्यक है। दोनों pycubrid dialects अब `pool_pre_ping` के लिए native `Connection.ping(False)` / `AsyncConnection.ping(False)` का उपयोग करते हैं, और सभी Core व ORM features `AsyncSession` के साथ काम करते हैं।


## संबंधित परियोजनाएँ

- [pycubrid](https://github.com/cubrid-lab/pycubrid) — CUBRID के लिए शुद्ध Python DB-API 2.0 ड्राइवर
- [cubrid-cookbook-python](https://github.com/cubrid-lab/cubrid-cookbook-python) — CUBRID के लिए production-ready Python उदाहरण

## रोडमैप

इस परियोजना की दिशा और अगले milestones के लिए [`ROADMAP.md`](../ROADMAP.md) देखें।

पूरे ecosystem के दृष्टिकोण के लिए [CUBRID Labs Ecosystem Roadmap](https://github.com/cubrid-lab/.github/blob/main/ROADMAP.md) और [Project Board](https://github.com/orgs/cubrid-lab/projects/2) देखें।

## योगदान

दिशानिर्देशों के लिए [CONTRIBUTING.md](../CONTRIBUTING.md) और development setup के लिए [docs/DEVELOPMENT.md](DEVELOPMENT.md) देखें।

## सुरक्षा

कमज़ोरियों की रिपोर्ट ईमेल के माध्यम से करें -- विवरण के लिए [SECURITY.md](../SECURITY.md) देखें। सुरक्षा चिंताओं के लिए सार्वजनिक issues न खोलें।

## लाइसेंस

MIT -- [LICENSE](../LICENSE) देखें.
