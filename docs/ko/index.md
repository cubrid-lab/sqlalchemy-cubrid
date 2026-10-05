# sqlalchemy-cubrid (한국어)

> 🌐 [index.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/index.md)의 번역입니다. 영어 원문이 표준이며, 페이지 번역은 경고 수준의 동기화 규칙을 따릅니다.

CUBRID용 SQLAlchemy 2.0–2.1 방언으로, 프로덕션 수준의 Core 및 ORM 워크로드를 위해 만들어졌습니다.

> English: [documentation home](../index.md)

## 주요 기능

- 문장 캐싱을 갖춘 네이티브 SQLAlchemy 2.0–2.1 방언 지원
- `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`를 포함한 CUBRID 전용 DML 지원
- 완전한 타입 시스템 커버리지와 스키마 리플렉션 지원
- CUBRID용 Alembic 마이그레이션 통합 내장
- 이중 드라이버 지원: C 확장(`cubrid://`)과 순수 Python(`cubrid+pycubrid://`)

## 빠른 설치

```bash
pip install sqlalchemy-cubrid
```

순수 Python 드라이버 옵션:

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

## 최소 예제

```python
from sqlalchemy import create_engine, text
engine = create_engine("cubrid://dba:password@localhost:33000/demodb")
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    row = result.fetchone()
    print(row[0])
```

## 문서 섹션

- [시작하기](CONNECTION.md)
- [사용자 가이드](TYPES.md)
- [레퍼런스](FEATURE_SUPPORT.md)

## 프로젝트 링크

- [GitHub](https://github.com/cubrid-lab/sqlalchemy-cubrid)
- [PyPI](https://pypi.org/project/sqlalchemy-cubrid/)
- [변경 이력](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/CHANGELOG.md)
- [기여하기](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/CONTRIBUTING.md)

## 생태계

cubrid-lab Python 생태계의 일부입니다:

- pycubrid — CUBRID용 순수 Python DB-API 2.0 드라이버 (동기 + 네이티브 asyncio)
- **sqlalchemy-cubrid** — SQLAlchemy 2.0–2.1 방언 + Alembic
- cubrid-cookbook-python — 실행 가능한 예제 68개와 애플리케이션 템플릿
- cubrid-mcp-server — MCP 서버 — LLM 클라이언트를 위한 자연어 접근
