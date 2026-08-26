# sqlalchemy-cubrid

**适用于 CUBRID 数据库的 SQLAlchemy 2.0–2.1 方言** — 为 SQLAlchemy 与 CUBRID 特有类型提供 Python ORM、模式反射、Alembic 迁移和类型映射。

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

> **状态：Production/Stable** — 支持 CUBRID 10.2–11.4 和 SQLAlchemy 2.0–2.1 的稳定维护方言。每个 PR 均通过实时数据库集成 CI 验证。

## 为什么选择 sqlalchemy-cubrid？

CUBRID 是一款高性能开源关系型数据库，在韩国公共部门和企业应用中被广泛采用。
此前一直没有一个积极维护、支持现代 2.0–2.1 API 的 SQLAlchemy 方言。

**sqlalchemy-cubrid** 填补了这一空白：

- 完整的 SQLAlchemy 2.0–2.1 方言，支持**语句缓存**和 **PEP 561 类型标注**
- **619 个离线测试**，**约 98.26% 代码覆盖率** —— 无需数据库即可运行
- **并发压力测试** —— 已在真实 CUBRID 上验证 `QueuePool` 同步线程和 `asyncio.gather` 工作负载
- **面向 SQLAlchemy 2.1 的兼容垫片** —— 私有 API 访问被封装在 `_compat.py` 中（在完成 SA 2.1 全面验证前仍固定为 `<2.3`）
- 在 **Python 3.10 -- 3.14** 上测试 **4 个 CUBRID 版本**（10.2、11.0、11.2、11.4）
- CUBRID 特有的 DML 构造：`ON DUPLICATE KEY UPDATE`、`MERGE`、`REPLACE INTO`
- 开箱即用的 Alembic 迁移支持
- **三种驱动选项** —— C 扩展（`cubrid://`）、纯 Python（`cubrid+pycubrid://`）或异步纯 Python（`cubrid+aiopycubrid://`）

## 架构

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

## 环境要求

- Python 3.10+
- SQLAlchemy 2.0 – 2.1
- [CUBRID-Python](https://github.com/CUBRID/cubrid-python)（C 扩展）**或** [pycubrid](https://github.com/cubrid-lab/pycubrid)（纯 Python）

## 安装

```bash
pip install sqlalchemy-cubrid
```

使用纯 Python 驱动（无需 C 构建）：

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

包含 Alembic 支持：

```bash
pip install "sqlalchemy-cubrid[alembic]"
```

## 快速开始

### Core（连接级别）

```python
from sqlalchemy import create_engine, text

engine = create_engine("cubrid://dba:password@localhost:33000/demodb")

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.scalar())
```

### ORM（会话级别）

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

## 功能特性

- 为 SQLAlchemy 标准类型和 CUBRID 特有类型提供类型映射 —— 数值、字符串、日期/时间、位、LOB、集合和 JSON 类型
- SQL 编译 -- SELECT、JOIN、CAST、LIMIT/OFFSET、子查询、CTE、窗口函数
- DML 扩展 -- `ON DUPLICATE KEY UPDATE`、`MERGE`、`REPLACE INTO`、`FOR UPDATE`、`TRUNCATE`
- DDL 支持 -- `COMMENT`、`IF NOT EXISTS` / `IF EXISTS`、`AUTO_INCREMENT`
- 模式反射 -- 表、视图、列、主键、外键、索引、唯一约束、注释
- 通过 `CubridImpl` 提供 Alembic 迁移（自动发现入口点）
- 支持 CUBRID 的三种 MVCC 隔离级别 — `READ COMMITTED`（默认）、`REPEATABLE READ`、`SERIALIZABLE`
- Async 支持 —— 通过 pycubrid.aio 使用 `create_async_engine("cubrid+aiopycubrid://...")`

## 已知限制

- **不支持 `RETURNING`** —— 不支持 `INSERT/UPDATE/DELETE ... RETURNING`；请改用 `cursor.lastrowid` 或 `LAST_INSERT_ID()`
- **不支持序列** —— CUBRID 仅使用 `AUTO_INCREMENT`
- **不支持多 schema** —— 每个数据库只有单一 schema
- **DDL 会自动提交** —— 迁移不是事务性的（`transactional_ddl = False`）
- **仅支持 SQLAlchemy 2.0–2.1** —— 由于内部 API 依赖，版本固定为 `<2.3`（[详情](ARCHITECTURE.md)）
- **Async 需要 pycubrid >= 1.2.0,<2.0** —— `cubrid+aiopycubrid://` 驱动需要本项目当前支持的 async 能力 pycubrid 包线

## 文档

| 指南 | 描述 |
|---|---|
| [连接](CONNECTION.md) | 连接字符串、URL 格式、驱动设置、连接池调优 |
| [类型映射](TYPES.md) | 完整类型映射、CUBRID 特有类型、集合类型 |
| [DML 扩展](DML_EXTENSIONS.md) | ON DUPLICATE KEY UPDATE、MERGE、REPLACE INTO、查询跟踪 |
| [隔离级别](ISOLATION_LEVELS.md) | CUBRID 的三种 MVCC 隔离级别、配置 |
| [Alembic 迁移](ALEMBIC.md) | 设置、配置、限制、批量解决方案 |
| [功能支持](FEATURE_SUPPORT.md) | 与 MySQL、PostgreSQL、SQLite 的对比 |
| [ORM 指南](ORM_COOKBOOK.md) | 实用 ORM 示例、关系、查询 |
| [开发指南](DEVELOPMENT.md) | 开发设置、测试、Docker、覆盖率、CI/CD |
| [驱动兼容性](DRIVER_COMPAT.md) | CUBRID-Python 驱动版本和已知问题 |
| [故障排除](TROUBLESHOOTING.md) | 常见问题、错误解决方案、调试技巧 |
| [异步连接](CONNECTION.md#async-connection) | 使用 `cubrid+aiopycubrid://` 设置异步引擎 |

## 兼容性矩阵

| 组件 | 支持的版本 |
|---|---|
| Python | 3.10、3.11、3.12、3.13、3.14 |
| CUBRID | 10.2、11.0、11.2、11.4 |
| SQLAlchemy | 2.0–2.1 |
| Alembic | >=1.7 |
| pycubrid（sync） | >=1.2.0,<2.0 |
| pycubrid（async） | >=1.2.0,<2.0 |

## FAQ

### 如何通过 SQLAlchemy 连接到 CUBRID？

```python
from sqlalchemy import create_engine
engine = create_engine("cubrid://dba:password@localhost:33000/demodb")
```

对于纯 Python 驱动（无需 C 构建）：`create_engine("cubrid+pycubrid://dba@localhost:33000/demodb")`

### sqlalchemy-cubrid 支持 SQLAlchemy 2.0–2.1 吗？

支持。sqlalchemy-cubrid 是为 SQLAlchemy 2.0–2.1 构建的，并支持 2.0 风格 API，包括 `Session.execute()`、带类型标注的 `Mapped[]` 列以及语句缓存。

### sqlalchemy-cubrid 支持 Alembic 迁移吗？

支持。请通过 `pip install "sqlalchemy-cubrid[alembic]"` 安装。该方言会通过入口点自动注册。请注意，CUBRID 会自动提交 DDL，因此迁移不是事务性的。

### 支持哪些 Python 版本？

支持 Python 3.10、3.11、3.12、3.13 和 3.14。

### CUBRID 支持 RETURNING 子句吗？

不支持。CUBRID 不支持 `INSERT ... RETURNING` 或 `UPDATE ... RETURNING`。请改用 `cursor.lastrowid` 或 `SELECT LAST_INSERT_ID()`。

### 如何在 CUBRID 中使用 ON DUPLICATE KEY UPDATE？

```python
from sqlalchemy_cubrid import insert
stmt = insert(users).values(name="Alice").on_duplicate_key_update(name="Alice Updated")
```

### `cubrid://` 和 `cubrid+pycubrid://` 有什么区别？

`cubrid://` 使用需要编译的 C 扩展驱动（CUBRIDdb）。`cubrid+pycubrid://` 使用纯 Python 驱动，只需 pip 即可安装 —— 无需构建工具。`cubrid+aiopycubrid://` 使用纯 Python 驱动的异步变体，可与 `create_async_engine` 和 `AsyncSession` 一起使用。

### sqlalchemy-cubrid 支持 async 吗？

支持。请配合 pycubrid 异步驱动使用 `create_async_engine("cubrid+aiopycubrid://...")`。需要 `pycubrid>=1.3.2,<2.0`。两个 pycubrid 方言现在都会在 `pool_pre_ping` 中使用原生 `Connection.ping(False)` / `AsyncConnection.ping(False)`，所有 Core 和 ORM 功能都可在 `AsyncSession` 中使用。


## 相关项目

- [pycubrid](https://github.com/cubrid-lab/pycubrid) — 适用于 CUBRID 的纯 Python DB-API 2.0 驱动
- [cubrid-cookbook-python](https://github.com/cubrid-lab/cubrid-cookbook-python) — 面向 CUBRID 的生产级 Python 示例

## 路线图

项目方向和后续里程碑请参见 [`ROADMAP.md`](../ROADMAP.md)。

生态系统全貌请参见 [CUBRID Labs Ecosystem Roadmap](https://github.com/cubrid-lab/.github/blob/main/ROADMAP.md) 和 [Project Board](https://github.com/orgs/cubrid-lab/projects/2)。

## 贡献

贡献指南请参阅 [CONTRIBUTING.md](../CONTRIBUTING.md)，开发环境设置请参阅 [docs/DEVELOPMENT.md](DEVELOPMENT.md)。

## 安全

请通过电子邮件报告漏洞 -- 详见 [SECURITY.md](../SECURITY.md)。请勿就安全问题创建公开 issue。

## 许可证

MIT -- 参见 [LICENSE](../LICENSE)。
