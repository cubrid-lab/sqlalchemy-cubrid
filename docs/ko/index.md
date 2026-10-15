# sqlalchemy-cubrid (한국어)

> 🌐 [index.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/index.md)의 번역입니다. 영어 원문이 표준이며, CI가 영어 원문과의 구조 일치를 검사합니다.

CUBRID용 SQLAlchemy 2.0–2.1 방언으로, 프로덕션 수준의 Core 및 ORM 워크로드를 위해 만들어졌습니다.

> English: [documentation home](../index.md)

## 여기서 시작하세요

CUBRID나 SQLAlchemy가 처음이라면
[SQLAlchemy로 CUBRID에 처음 연결하기](QUICKSTART.md)를 따라 하세요. 무엇이 필요한지(CUBRID는
별도의 데이터베이스 서버이며, Python 패키지를 설치해도 설치되지 않습니다), Docker로 일회용 로컬
데이터베이스를 띄우는 방법을 설명하고, 권장 경로인 `sqlalchemy-cubrid[pycubrid]`로 첫 쿼리와 첫
행 저장까지 안내합니다.

## 주요 기능

- 문장 캐싱을 갖춘 네이티브 SQLAlchemy 2.0–2.1 방언 지원
- `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`를 포함한 CUBRID 전용 DML 지원
- 완전한 타입 시스템 커버리지와 스키마 리플렉션 지원
- CUBRID용 Alembic 마이그레이션 통합 내장
- 드라이버 선택: 순수 Python(`cubrid+pycubrid://`, 권장, 동기와 비동기) 또는 CUBRIDdb C 확장(`cubrid://`)

## 빠른 설치

권장 설치(순수 Python 드라이버 포함):

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

방언만 설치(예: 소스에서 빌드한 CUBRIDdb C 확장과 함께 사용, [드라이버 호환성](DRIVER_COMPAT.md) 참고):

```bash
pip install sqlalchemy-cubrid
```

## 최소 예제

[빠른 시작의 로컬 실습 환경](QUICKSTART.md#방법-b-버려도-되는-로컬-데이터베이스가-필요합니다)(데이터베이스
`testdb`, 비밀번호 없는 `dba` 사용자)을 사용합니다. 다른 데이터베이스에서는 URL에 그 값을 넣으세요.

```python
from sqlalchemy import create_engine, text

engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")
with engine.connect() as conn:
    print(conn.execute(text("SELECT 1 + 1")).scalar())  # 2
engine.dispose()
```

## 문서 섹션

- [여기서 시작: 첫 연결](QUICKSTART.md)
- [연결 가이드](CONNECTION.md)
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
