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

## 이 문서에 대하여

이 사이트는 **개발 문서**입니다. 패키지 릴리스와 관계없이 `main` 브랜치가 바뀔 때마다 다시
빌드되므로, 아직 어떤 공개 릴리스에도 들어 있지 않은 변경을 설명할 수 있습니다. 소스의 버전
번호(`__version__`)도 릴리스가 아닙니다. 릴리스 후보이거나, 포기되어 공개되지 않은 버전(예:
1.11.1)일 수 있습니다.
<!-- docs-source-revision -->

- **공개 릴리스**는 [GitHub Releases](https://github.com/cubrid-lab/sqlalchemy-cubrid/releases)와
  [PyPI](https://pypi.org/project/sqlalchemy-cubrid/#history)에 있으며, `pip install
  sqlalchemy-cubrid`는 그중 가장 새로운 릴리스를 설치합니다. 릴리스는 업로드되는 즉시, 공개 후
  쿡북 검사가 실행되기 전에 두 곳에 나타납니다. 이 검사까지 통과했다는 것은 퍼블리셔의
  `published and verified` 결과만 보여 주며, 그 뒤 조정 단계가 릴리스 PR을 `autorelease: tagged`로
  표시합니다.
- **공개 릴리스의 문서**는 그 태그의 `docs/` 폴더입니다.
  [GitHub Releases](https://github.com/cubrid-lab/sqlalchemy-cubrid/releases)에서 릴리스를 열고
  태그의 파일을 살펴보세요. 예:
  [`v1.11.0`](https://github.com/cubrid-lab/sqlalchemy-cubrid/tree/v1.11.0/docs).
- **테스트한 버전**은 각 가이드가 명령 옆에 날짜와 함께, 공개 패키지를 썼는지 소스 빌드를 썼는지와
  함께 밝힙니다. [빠른 시작](QUICKSTART.md)은 PyPI의 공개 릴리스로 실행했습니다.

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

[빠른 시작의 로컬 실습 환경](LESSON_PREPARE.md#방법-b-버려도-되는-로컬-데이터베이스가-필요합니다)(데이터베이스
`testdb`, 비밀번호 없는 `dba` 사용자)을 사용합니다. 다른 데이터베이스에서는 URL에 그 값을 넣으세요.

```python
from sqlalchemy import create_engine, text

engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")
with engine.connect() as conn:
    print(conn.execute(text("SELECT 1 + 1")).scalar())  # 2
engine.dispose()
```

## 문서 섹션

- **여기서 시작:** [첫 연결](QUICKSTART.md). 빈 폴더에서 첫 행 저장까지 이어지는 동기
  `cubrid+pycubrid://` 경로 하나입니다.
- **작업 가이드:** [드라이버 연결과 설정](CONNECTION.md), [ORM 사용하기](ORM_COOKBOOK.md),
  [Alembic으로 마이그레이션 실행](ALEMBIC.md), [CUBRID 전용 DML 사용하기](DML_EXTENSIONS.md),
  [격리 수준 고르기](ISOLATION_LEVELS.md).
- **레퍼런스:** [타입 매핑](TYPES.md), [기능 지원](FEATURE_SUPPORT.md),
  [지원 매트릭스](SUPPORT_MATRIX.md), 지원 CUBRIDdb C 확장 드라이버를 포함한
  [드라이버 호환성](DRIVER_COMPAT.md).
- **도움말:** [문제 해결](TROUBLESHOOTING.md). 버그와 질문은
  [GitHub Issues](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues)에, 보안 문제는
  [SECURITY.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/SECURITY.md)에 따라 비공개로
  제보하세요.
- **프로젝트와 내부 구조:** 기여자를 위한 [아키텍처](ARCHITECTURE.md),
  [SQLAlchemy 내부 API 호환성](SA_COMPAT.md), [성능](PERFORMANCE.md), [개발](DEVELOPMENT.md),
  [CI 실행 정책](CI_POLICY.md).

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
