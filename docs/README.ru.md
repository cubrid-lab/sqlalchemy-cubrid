# sqlalchemy-cubrid

**Диалект SQLAlchemy 2.0–2.1 для базы данных CUBRID** — Python ORM, рефлексия схемы, миграции Alembic и сопоставление типов для SQLAlchemy и специфичных для CUBRID типов.

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

> **Статус: Production/Stable** — стабильный диалект SQLAlchemy для CUBRID 10.2–11.4. Каждый PR проверяется интеграционным CI на реальной базе данных.

## Почему sqlalchemy-cubrid?

CUBRID — это высокопроизводительная реляционная база данных с открытым исходным
кодом, широко используемая в корейском государственном секторе и корпоративных
приложениях. До сих пор не было активно поддерживаемого диалекта SQLAlchemy,
который поддерживал бы современный API 2.0–2.1.

**sqlalchemy-cubrid** закрывает этот пробел:

- Полноценный диалект SQLAlchemy 2.0–2.1 с **кэшированием выражений** и **типизацией PEP 561**
- **619 офлайн-тестов** с **~98,26 % покрытия кода** — для запуска не требуется база данных
- **Стресс-тесты конкурентности** — синхронные threaded-нагрузки `QueuePool` и `asyncio.gather` валидированы на реальном CUBRID
- **Compat shim, готовый к SQLAlchemy 2.1** — доступ к приватным API обёрнут в `_compat.py` (пока остаётся ограничение `<2.3` до полной валидации SA 2.1)
- Протестирован на **4 версиях CUBRID** (10.2, 11.0, 11.2, 11.4) и **Python 3.10 -- 3.14**
- CUBRID-специфичные DML-конструкции: `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`
- Поддержка миграций Alembic из коробки
- **Три варианта драйвера** — C-расширение (`cubrid://`), чистый Python (`cubrid+pycubrid://`) или асинхронный чистый Python (`cubrid+aiopycubrid://`)

## Архитектура

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

## Требования

- Python 3.10+
- SQLAlchemy 2.0 – 2.1
- [CUBRID-Python](https://github.com/CUBRID/cubrid-python) (C-расширение) **или** [pycubrid](https://github.com/cubrid-lab/pycubrid) (чистый Python)

## Установка

```bash
pip install sqlalchemy-cubrid
```

С драйвером на чистом Python (без C-сборки):

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

С поддержкой Alembic:

```bash
pip install "sqlalchemy-cubrid[alembic]"
```

## Быстрый старт

### Core (уровень соединения)

```python
from sqlalchemy import create_engine, text

engine = create_engine("cubrid://dba:password@localhost:33000/demodb")

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.scalar())
```

### ORM (уровень сессии)

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

## Возможности

- Сопоставление типов для стандартных SQLAlchemy-типов и CUBRID-специфичных типов — числовые, строковые, дата/время, битовые, LOB, коллекции и JSON-типы
- Компиляция SQL -- SELECT, JOIN, CAST, LIMIT/OFFSET, подзапросы, CTE, оконные функции
- DML-расширения -- `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`, `FOR UPDATE`, `TRUNCATE`
- DDL-поддержка -- `COMMENT`, `IF NOT EXISTS` / `IF EXISTS`, `AUTO_INCREMENT`
- Рефлексия схемы -- таблицы, представления, столбцы, PK, FK, индексы, уникальные ограничения, комментарии
- Миграции Alembic через `CubridImpl` (автоматически обнаруживаемая точка входа)
- Три уровня изоляции MVCC CUBRID — `READ COMMITTED` (по умолчанию), `REPEATABLE READ`, `SERIALIZABLE`
- Async-поддержка — `create_async_engine("cubrid+aiopycubrid://...")` через pycubrid.aio

## Известные ограничения

- **Нет `RETURNING`** — `INSERT/UPDATE/DELETE ... RETURNING` не поддерживается; используйте `cursor.lastrowid` или `LAST_INSERT_ID()`
- **Нет последовательностей** — CUBRID использует только `AUTO_INCREMENT`
- **Нет мультисхемности** — одна схема на базу данных
- **DDL коммитится автоматически** — миграции не являются транзакционными (`transactional_ddl = False`)
- **Только SQLAlchemy 2.0–2.1** — зафиксировано на `<2.3` из-за зависимости от внутренних API ([подробности](ARCHITECTURE.md))
- **Async требует pycubrid >= 1.2.0,<2.0** — драйвер `cubrid+aiopycubrid://` требует async-совместимую линейку pycubrid, которую сейчас поддерживает этот проект

## Документация

| Руководство | Описание |
|---|---|
| [Подключение](CONNECTION.md) | Строки подключения, формат URL, настройка драйвера, тюнинг пула |
| [Сопоставление типов](TYPES.md) | Полное сопоставление типов, CUBRID-специфичные типы, коллекции |
| [DML-расширения](DML_EXTENSIONS.md) | ON DUPLICATE KEY UPDATE, MERGE, REPLACE INTO, трассировка запросов |
| [Уровни изоляции](ISOLATION_LEVELS.md) | Три уровня изоляции MVCC CUBRID, конфигурация |
| [Миграции Alembic](ALEMBIC.md) | Настройка, конфигурация, ограничения, пакетные обходные пути |
| [Поддержка функций](FEATURE_SUPPORT.md) | Сравнение с MySQL, PostgreSQL, SQLite |
| [ORM-рецепты](ORM_COOKBOOK.md) | Практические ORM-примеры, связи, запросы |
| [Разработка](DEVELOPMENT.md) | Настройка среды, тестирование, Docker, покрытие, CI/CD |
| [Совместимость драйверов](DRIVER_COMPAT.md) | Версии драйвера CUBRID-Python и известные проблемы |
| [Устранение неполадок](TROUBLESHOOTING.md) | Частые проблемы, решения ошибок, методы отладки |
| [Асинхронное подключение](CONNECTION.md#async-connection) | Настройка async engine с `cubrid+aiopycubrid://` |

## Матрица совместимости

| Компонент | Поддерживаемые версии |
|---|---|
| Python | 3.10, 3.11, 3.12, 3.13, 3.14 |
| CUBRID | 10.2, 11.0, 11.2, 11.4 |
| SQLAlchemy | 2.0–2.1 |
| Alembic | >=1.7 |
| pycubrid (sync) | >=1.2.0,<2.0 |
| pycubrid (async) | >=1.2.0,<2.0 |

## FAQ

### Как подключиться к CUBRID через SQLAlchemy?

```python
from sqlalchemy import create_engine
engine = create_engine("cubrid://dba:password@localhost:33000/demodb")
```

Для драйвера на чистом Python (без C-сборки): `create_engine("cubrid+pycubrid://dba@localhost:33000/demodb")`

### Поддерживает ли sqlalchemy-cubrid SQLAlchemy 2.0–2.1?

Да. sqlalchemy-cubrid создан для SQLAlchemy 2.0–2.1 и поддерживает API в стиле 2.0, включая `Session.execute()`, типизированные столбцы `Mapped[]` и кэширование выражений.

### Поддерживает ли sqlalchemy-cubrid миграции Alembic?

Да. Установите пакет через `pip install "sqlalchemy-cubrid[alembic]"`. Диалект автоматически регистрируется через entry point. Учтите, что CUBRID автоматически коммитит DDL, поэтому миграции не являются транзакционными.

### Какие версии Python поддерживаются?

Python 3.10, 3.11, 3.12, 3.13 и 3.14.

### Поддерживает ли CUBRID предложения RETURNING?

Нет. CUBRID не поддерживает `INSERT ... RETURNING` или `UPDATE ... RETURNING`. Используйте `cursor.lastrowid` или `SELECT LAST_INSERT_ID()`.

### Как использовать ON DUPLICATE KEY UPDATE с CUBRID?

```python
from sqlalchemy_cubrid import insert
stmt = insert(users).values(name="Alice").on_duplicate_key_update(name="Alice Updated")
```

### В чём разница между `cubrid://` и `cubrid+pycubrid://`?

`cubrid://` использует драйвер C-расширения (CUBRIDdb), который требует компиляции. `cubrid+pycubrid://` использует драйвер на чистом Python, который устанавливается одним pip — без build tools. `cubrid+aiopycubrid://` использует асинхронный вариант драйвера на чистом Python для работы с `create_async_engine` и `AsyncSession`.

### Поддерживает ли sqlalchemy-cubrid async?

Да. Используйте `create_async_engine("cubrid+aiopycubrid://...")` с async-драйвером pycubrid. Требуется `pycubrid>=1.3.2,<2.0`. Оба pycubrid-диалекта используют нативный `Connection.ping(False)` / `AsyncConnection.ping(False)` для `pool_pre_ping`, и все возможности Core и ORM работают с `AsyncSession`.


## Связанные проекты

- [pycubrid](https://github.com/cubrid-lab/pycubrid) — чистый Python-драйвер DB-API 2.0 для CUBRID
- [cubrid-cookbook-python](https://github.com/cubrid-lab/cubrid-cookbook-python) — готовые к продакшену примеры Python для CUBRID

## Дорожная карта

См. [`ROADMAP.md`](../ROADMAP.md), чтобы узнать о направлении проекта и следующих этапах.

Для обзора по всей экосистеме см. [CUBRID Labs Ecosystem Roadmap](https://github.com/cubrid-lab/.github/blob/main/ROADMAP.md) и [Project Board](https://github.com/orgs/cubrid-lab/projects/2).

## Участие в проекте

См. [CONTRIBUTING.md](../CONTRIBUTING.md) с рекомендациями и [docs/DEVELOPMENT.md](DEVELOPMENT.md) с настройкой среды разработки.

## Безопасность

Сообщайте об уязвимостях по электронной почте -- см. [SECURITY.md](../SECURITY.md). Не создавайте публичные issues по вопросам безопасности.

## Лицензия

MIT -- см. [LICENSE](../LICENSE).
