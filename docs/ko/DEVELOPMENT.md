# 개발 가이드 (한국어)

> 🌐 [DEVELOPMENT.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/DEVELOPMENT.md)의 번역입니다. 영어 원문이 표준이며, 페이지 번역은 경고 수준의 동기화 규칙을 따릅니다.

개발 환경 설정, 테스트 실행, sqlalchemy-cubrid 기여에 필요한 모든 것.

---

## 목차

- [사전 준비](#사전-준비)
- [설치](#설치)
- [프로젝트 구조](#프로젝트-구조)
- [Make 타깃](#make-타깃)
- [테스트 실행](#테스트-실행)
- [Docker 통합 테스트](#docker-통합-테스트)
- [다중 버전 테스트](#다중-버전-테스트)
- [코드 커버리지](#코드-커버리지)
- [코드 스타일](#코드-스타일)
- [Pre-Commit 훅](#pre-commit-훅)
- [CI/CD 파이프라인](#cicd-파이프라인)

---

## 사전 준비

| 요구사항 | 버전 |
|---|---|
| Python | 3.11+ |
| Git | 아무 버전 |
| Docker | 아무 버전 (통합 테스트용) |
| Docker Compose | v2+ |

---

## 설치

### 빠른 설정

```bash
git clone https://github.com/cubrid-lab/sqlalchemy-cubrid.git
cd sqlalchemy-cubrid
make install
```

`make install`이 수행하는 것:
1. `pip install -e ".[dev]"` — dev 의존성과 함께 편집 가능 설치
2. `pre-commit install` — git 훅 설정

### 수동 설정

```bash
# 가상 환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# dev 의존성과 함께 편집 가능 모드로 설치
pip install -e ".[dev]"

# pre-commit 훅 설치
pre-commit install
```

---

## 프로젝트 구조

```mermaid
graph TD
    root["sqlalchemy-cubrid/"]

    pkg["sqlalchemy_cubrid/ - Main package"]
    tests["test/ - Test suite"]
    docs["docs/ - Documentation"]
    samples["samples/ - Usage examples"]
    pyproject["pyproject.toml - Project config, dependencies"]
    tox["tox.ini - Multi-Python test config"]
    docker["docker-compose.yml - CUBRID Docker setup"]
    makefile["Makefile - Development shortcuts"]
    contributing["CONTRIBUTING.md - Contribution guidelines"]

    root --> pkg
    root --> tests
    root --> docs
    root --> samples
    root --> pyproject
    root --> tox
    root --> docker
    root --> makefile
    root --> contributing

    pkg --> init["__init__.py - Public API, version, type exports"]
    pkg --> base["base.py - ExecutionContext, IdentifierPreparer"]
    pkg --> compiler["compiler.py - SQL/DDL/Type compilers"]
    pkg --> dialect["dialect.py - CubridDialect (reflection, connection, etc.)"]
    pkg --> pycubrid_dialect["pycubrid_dialect.py - Pure Python driver dialect"]
    pkg --> aio_dialect["aio_pycubrid_dialect.py - Async pycubrid.aio dialect"]
    pkg --> dml["dml.py - ON DUPLICATE KEY UPDATE, MERGE constructs"]
    pkg --> trace["trace.py - Query tracing utility"]
    pkg --> types["types.py - CUBRID type system"]
    pkg --> req["requirements.py - SA 2.0 test requirement flags"]
    pkg --> alembic["alembic_impl.py - Alembic migration support"]
    pkg --> typed["py.typed - PEP 561 marker"]

    tests --> tcomp["test_compiler.py - SQL compilation tests"]
    tests --> ttypes["test_types.py - Type system tests"]
    tests --> tdialect["test_dialect_offline.py - Dialect tests (no DB)"]
    tests --> tbase["test_base.py - Base module tests"]
    tests --> treq["test_requirements.py - SA requirement flag tests"]
    tests --> tdml["test_dml.py - DML construct tests"]
    tests --> talembic["test_alembic.py - Alembic integration tests"]
    tests --> taio["test_aio_pycubrid_dialect.py - Async dialect tests"]
    tests --> taioint["test_aio_integration.py - Async integration tests"]
    tests --> tjson["test_json.py - JSON type and path tests"]
    tests --> tpackaging["test_packaging.py - Packaging and entry point tests"]
    tests --> tshowcreate["test_show_create_table.py - Reflection parser tests"]
    tests --> ttrace["test_trace.py - Query trace tests"]
    tests --> tintegration["test_integration.py - Live DB integration tests"]
    tests --> tsuite["test_suite.py - SA test suite runner"]
    tests --> tconftest["conftest.py - Test fixtures"]
```

---

## Make 타깃

모든 흔한 개발 작업은 `make`로 사용할 수 있습니다:

```bash
make help          # 사용 가능한 모든 타깃 표시
make install       # 모든 의존성과 함께 개발 모드 설치
make lint          # ruff 린터 + 포맷 검사 실행
make check-tool-versions # 로컬/CI 도구 핀과 타입 검사 셀 일치 확인
make typecheck     # 의존성 버전 출력 및 strict mypy 검사
make format        # 린트 문제 자동 수정 및 코드 포맷
make test          # 커버리지와 함께 빠른 오프라인 테스트 실행 (95% 임계값)
make test-repo     # 저장소 도구 테스트 실행 (Makefile, 시그널 처리, 저장소 스크립트)
make test-offline  # 모든 오프라인 테스트(빠른 테스트 + 저장소 도구 테스트)를 커버리지와 함께 실행
make test-all      # 모든 Python 버전에서 tox 실행
make integration   # 실행 전용 Docker 프로젝트 시작 → 통합 테스트 실행 (pycubrid) → 삭제
make docker-up     # CUBRID Docker 컨테이너 시작
make docker-down   # CUBRID Docker 컨테이너 중지 및 제거
make clean         # 빌드 산출물과 캐시 제거
```

---

## 테스트 실행

### 엄격한 타입 검사

개발 환경에서 `make typecheck`를 실행하세요. Python, SQLAlchemy, Alembic,
mypy 버전을 출력한 다음
`python3 -m mypy sqlalchemy_cubrid/ --config-file=pyproject.toml`를 실행합니다.
개발 의존성은 mypy `2.3.1`을 고정합니다.

CI는 Python 3.11 / SQLAlchemy 2.0.53과 Python 3.13 / SQLAlchemy 2.1.1의 두 셀에서
같은 Makefile 타깃을 실행합니다. 두 셀 모두 필수입니다. 타입 검사 잡이 실패하거나
취소되거나 건너뛰어지면 필수 `matrix-result` 검사가 실패합니다. Ruff와 95% 최소
커버리지의 기존 오프라인 테스트도 계속 필수입니다. 로컬 가상 환경 인터프리터를
지정하려면 `make typecheck PYTHON=/path/to/venv/bin/python`을 사용하세요.

### 오프라인 테스트 (데이터베이스 불필요)

동기 단위 테스트의 비동기 어댑터 픽스처는 실제 진입 코루틴을 await 브리지로
소비하고 대기 여부를 검증합니다. 필요한 경우 연결 브리지(SQLAlchemy 2.0)와
모듈 브리지(2.1)를 모두 패치하세요. 단순히 커서를 반환하는 mock은 잘못된
어댑터 상태를 숨기고 대기하지 않은 코루틴을 pytest의 가비지 수집 검사에 남깁니다.

대부분의 테스트 스위트는 라이브 CUBRID 인스턴스 없이 실행됩니다:

```bash
# 모든 오프라인 테스트 실행
pytest test/ -v --ignore=test/test_integration.py --ignore=test/test_suite.py \
  --ignore=test/test_aio_integration.py

# 커버리지 리포트와 함께 실행
pytest test/ -v --ignore=test/test_integration.py --ignore=test/test_suite.py \
  --ignore=test/test_aio_integration.py \
  --cov=sqlalchemy_cubrid --cov-report=term-missing

# 특정 테스트 파일 실행
pytest test/test_compiler.py -v

# 단일 테스트 실행
pytest test/test_compiler.py::TestCubridSQLCompiler::test_select_limit -v
```

### 속성 기반 퍼즈 테스트 (Hypothesis)

`test/test_fuzz_*.py`는 [Hypothesis](https://hypothesis.readthedocs.io/)를 사용해 손으로 작성한 스위트가 열거하지 않은 SELECT/INSERT/DDL 조합을 생성하고 dialect 불변식을 검증합니다(예상치 못한 컴파일 예외 없음, placeholder == 파라미터 개수, LIMIT/OFFSET 카디널리티, DDL/reflection 왕복). 오프라인 퍼즈 테스트는 일반 오프라인 스위트에서 실행되며, 라이브 실행 퍼즈 테스트는 `integration` 마커가 붙습니다.

```bash
# 빠른 프로파일 (기본, 테스트당 ~50 예제) — 오프라인 스위트와 함께 실행
pytest test/test_fuzz_select.py -v

# 확장 프로파일 (테스트당 2000 예제) — nightly 버그 헌트 프로파일
HYPOTHESIS_PROFILE=nightly pytest test/test_fuzz_select.py -v

# 라이브 실행 퍼징 (CUBRID 필요)
export CUBRID_TEST_URL="cubrid+pycubrid://dba@localhost:33000/testdb"
HYPOTHESIS_PROFILE=nightly pytest test/test_fuzz_select.py -m integration -v
```

프로파일(`dev`, `ci`, `nightly`)은 `test/conftest.py`에 등록되며 `HYPOTHESIS_PROFILE`로 선택합니다. PR CI는 빠른 프로파일을 사용하고, 명시적 전체 검증과 릴리스 게이트는 라이브 CUBRID에 대해 확장 프로파일을 실행합니다.

### 통합 테스트 (CUBRID 필요)

```bash
# CUBRID 컨테이너 시작
docker compose up -d

# CUBRID 준비 대기 (헬스체크: ~30초)
docker compose logs -f cubrid

# 연결 URL 설정
export CUBRID_TEST_URL="cubrid+pycubrid://dba@localhost:33000/testdb"

# 기존 순수 Python 드라이버 extra를 설치하는 일반 tox 프로파일
tox -e integration

# pycubrid가 설치된 환경에서 특정 동기 파일 실행
pytest test/test_integration.py -v

# 비동기 통합 테스트 실행
pytest test/test_aio_integration.py -v

# 컨테이너 중지
docker compose down -v
```

일반 tox 프로파일은 명시적인 `cubrid+pycubrid` URL을 요구합니다. URL 누락이나
레거시 C 확장 스킴을 거부하고 pytest 전에 제한된 시간의 `SELECT 1`로 동기·파생
비동기 연결을 모두 확인합니다. 비동기 스위트는 SQLAlchemy URL API로 인증 정보,
포트, 쿼리 옵션을 보존한 `cubrid+aiopycubrid` URL을 파생하며 `CUBRID_TEST_AURL`은
명시적 비동기 재정의로 유지합니다. 실패 메시지는 URL 인증 정보를 출력하지 않습니다.
선택적 네이티브 C 확장이 없으면 드라이버 차분 비교는 의도적으로
건너뛰며 CUBRIDdb를 검증했다고 주장하지 않습니다. 공식 CI의 네이티브 드라이버
`--dburi` 경로는 별도로 유지됩니다.

#### 건너뛸지 실패할지: `CUBRID_TEST_URL`이 스위치입니다

`integration` 마커가 붙은 테스트의 실행 여부는 `test/conftest.py`의
`pytest_runtest_setup` 게이트 한 곳에서 결정합니다(#593). 이제 어떤 테스트 모듈도
import 시점에 서버를 확인하지 않습니다.

| `CUBRID_TEST_URL` | 서버가 URL의 드라이버로 `SELECT 1`에 응답 | 통합 테스트 |
| --- | --- | --- |
| 미설정 또는 빈 값 | (확인하지 않음) | 로컬에서는 건너뜀. `CI=true`이면 테스트 실행 전에 종료 코드 1로 끝남 |
| 설정됨 | 예 | 실행 |
| 설정됨 | 아니요(서버 중지, 잘못된 포트, 드라이버 미설치, 데이터베이스가 있는 CUBRID URL이 아님) | 모두 같은 메시지로 **error** |

게이트는 `scripts/integration_urls.py`의 헬퍼(`scripts/wait_for_cubrid.py`와
공유)로 세션당 한 번, URL이 선택한 드라이버를 통해 서버를 확인합니다.
`cubrid+pycubrid://`에는 pycubrid가, `cubrid://`에는 CUBRIDdb C 확장이 필요하며,
`cubrid+aiopycubrid://`로 연결하는 `test/test_aio_integration.py`도 마찬가지입니다.
파괴적인 테스트 픽스처가 다른 데이터베이스에서 실행되지 않도록 `CUBRID_TEST_URL`은
데이터베이스를 지정한 `cubrid://`, `cubrid+cubriddb://` 또는 `cubrid+pycubrid://`
URL이어야 합니다. `CUBRID_TEST_AURL`로 비동기 경로를 재정의하면 게이트는 그
엔드포인트도 `cubrid+aiopycubrid://`로 확인합니다. 오류 메시지는 비밀번호를 가린
URL을 보여 줍니다. 예:

```text
CUBRID_TEST_URL is set, but CUBRID at cubrid+pycubrid://dba:***@127.0.0.1:33599/testdb
does not answer SELECT 1 through the driver the URL selects: OperationalError: ...
```

따라서 서버가 있다고 믿는 레인이 테스트를 건너뛰어 녹색이 되는 일은 더 이상
없습니다. #593 이전에는 연결할 수 없는 URL로 `pytest test/ -m integration`을 실행하면
`CI=true`에서도 447개 중 421개가 건너뛰어졌습니다. 이제 447개 모두 error가 되고
pytest는 종료 코드 1로 끝납니다. 의도적으로 건너뛰려면 `CUBRID_TEST_URL`을 해제하거나
`-m "not integration"`으로 제외하세요(오프라인 스위트가 이렇게 합니다). 이 게이트는
`--dburi` 컴플라이언스 실행에는 적용되지 않습니다. `--dburi`를 쓰면 SQLAlchemy
플러그인이 세션 시작 시 연결하고, 서버에 연결할 수 없으면 직접 실행을 실패시킵니다.

게이트를 통과한 뒤에도 일부 모듈은 자체 이유로 건너뜁니다. 드라이버 차분 테스트와
트랜잭션 DDL 테스트는 두 드라이버가 모두 필요하고, 서버 재시작 테스트는
`CUBRID_TEST_DOCKER_CONTAINER`가 필요합니다. 해당 CI 단계는
`CUBRID_REQUIRE_DRIVER_DIFFERENTIAL=1`, `CUBRID_REQUIRE_TRANSACTIONAL_DDL=1`,
`CUBRID_REQUIRE_SERVER_RESTART=1`로 이 건너뛰기를 실패로 바꿉니다(#486, #503, #565).

`test/test_integration.py`는 고정된 이름의 테이블과 데이터베이스 사용자(예:
`t583_fresh`, `alter_it_modify`, `u543`)를 만들므로, 같은 데이터베이스에 대한 두
실행은 서로 간섭합니다. 전용 데이터베이스에서 한 번에 하나씩 실행하세요.
`make integration`은 이를 위해 실행 전용 서버를 시작합니다.

`TestIsDisconnect`의 KILL QUERY 사례(#634)도 직렬 실행을 유지합니다. KILL은
서버 전체에 작용하며 사용자 조건 없이 숫자 트랜잭션 인덱스만 받으므로
원자적인 사용자 확인과 종료는 할 수 없습니다. 테스트는 새로운
`kq634_<16자리 16진수>` 데이터베이스 계정을 하나 만들고, 피해 연결을 먼저
열어 준비한 뒤 별도 종료 프로세스를 시작합니다(CUBRIDdb가 쿼리 중 GIL을
점유하므로 필요). 종료 프로세스가 끝나거나 중지될 때까지 피해 연결을
유지합니다. 종료 프로세스는 `SHOW TRANSACTION TABLES`에서 정확히 그
`Client_db_user`이고 `Query_start_time`이 NULL이 아닌 활성 쿼리만 고릅니다.
열이 없거나 해당 활성 쿼리가 여러 개면 KILL을 보내지 않고 실패합니다.
새로 나타난 DBA나 다른 사용자의 쿼리를 시간으로 추측하지 않습니다. 정리 시
피해 엔진을 폐기하고 확인 절차를 거쳐 이 실행이 만든 계정만 삭제합니다.
생성된 계정에는 비밀번호가 없으므로 피해 연결 URL은 DBA 비밀번호를 명시적으로
지웁니다. `CUBRID_TEST_URL`에 비어 있지 않은 DBA 비밀번호가 있어도 동일합니다.
버려도 되는 DBA 테스트 데이터베이스를 사용하세요. 다른 세션이 그 전용
계정을 공유하면 테스트는 안전하게 실패합니다.

`test/test_server_restart.py`(#565)는
`docker exec -u cubrid <container> bash -lc "cubrid server stop|start <db>"`로
`cub_server`를 중지·시작하고, 두 드라이버 모두에서 `pool_pre_ping` 사용 여부와
무관하게 풀이 망가진 연결을 무효화하고 회복하는지 확인합니다.
`CUBRID_TEST_DOCKER_CONTAINER`가 `CUBRID_TEST_URL`을 제공하는 컨테이너를 가리키지
않으면 건너뜁니다. 테스트가 데이터베이스를 내리므로 버려도 되는 컨테이너를
지정하세요:

```bash
CUBRID_TEST_URL="cubrid://dba@localhost:33000/testdb" \
CUBRID_TEST_DOCKER_CONTAINER=<container> \
  pytest test/test_server_restart.py -v -rs
```

CI는 각 통합 잡의 마지막 단계에서 `CUBRID_REQUIRE_SERVER_RESTART=1`로 실행하며,
이 변수는 모든 건너뛰기를 실패로 바꿉니다.

### 전체 SA 테스트 스위트

```bash
# 실행 중인 CUBRID 인스턴스 필요
pytest test/test_suite.py --dburi cubrid://dba@localhost:33000/testdb
pytest test/test_suite.py --dburi cubrid+pycubrid://dba@localhost:33000/testdb
```

알려진 실패는 드라이버와 SQLAlchemy 버전별로 기준선이 관리됩니다.
[SQLAlchemy 컴플라이언스 레인](#sqlalchemy-컴플라이언스-레인)을 참고하세요.

---

## Docker 통합 테스트

### docker-compose.yml

프로젝트에는 로컬 CUBRID 인스턴스를 위한 `docker-compose.yml`이 포함되어 있습니다:

```yaml
services:
  cubrid:
    image: cubrid/cubrid:${CUBRID_VERSION:-11.2}
    environment:
      CUBRID_DB: testdb
    ports:
      - "33000:33000"
    healthcheck:
      test: ["CMD", "csql", "-u", "dba", "testdb", "-c", "SELECT 1"]
      interval: 15s
      timeout: 10s
      retries: 10
      start_period: 30s
```

### 다른 CUBRID 버전에 대한 테스트

```bash
# 기본 (11.2)
docker compose up -d

# 특정 버전
CUBRID_VERSION=11.4 docker compose up -d
CUBRID_VERSION=11.0 docker compose up -d
CUBRID_VERSION=10.2 docker compose up -d
```

### 지원되는 CUBRID 버전

| 버전 | Docker 이미지 |
|---|---|
| 11.4 | `cubrid/cubrid:11.4` |
| 11.2 | `cubrid/cubrid:11.2` (기본) |
| 11.0 | `cubrid/cubrid:11.0` |
| 10.2 | `cubrid/cubrid:10.2` |

### 빠른 통합 워크플로

```bash
# 원커맨드: 시작, 테스트, 중지 (권장 드라이버 pycubrid)
make integration

# 같은 스위트를 CUBRIDdb C 확장으로 실행 (설치되어 있어야 함)
make integration INTEGRATION_DRIVER=cubriddb
```

`make integration`은 `integration` 마커가 붙은 모든 테스트를 하나의 pytest
세션에서 실행합니다. `INTEGRATION_DRIVER`는 `CUBRID_TEST_URL`의 드라이버를
선택합니다. `pycubrid`(기본값, `cubrid+pycubrid://`) 또는 `cubriddb`(`cubrid://`,
CUBRIDdb C 확장 필요. CI는 cubrid-python v11.3.0.51에서 빌드하며,
`.github/workflows/ci.yml`의 "Build and install CUBRID Python driver" 단계를
참고하세요)입니다. 다른 값을 주면 Docker 명령을 실행하기 전에 상태 2로
종료합니다. 여러 테스트 파일이 URL이 선택한 드라이버와 관계없이 두 드라이버로
연결하므로, 어느 드라이버를 쓰든 `.[dev,pycubrid]`를 설치하세요. PR CI는 기본
드라이버로 CUBRID 11.4에서 `make integration`을 실행하는 레인은 PR 이후 코드 검증에 유지합니다. 수동 전체 검증 및 릴리스 게이트
`integration-full.yml` 워크플로는 두 드라이버로 CUBRID 10.2와 11.4에서 실행합니다.

`docker compose up -d` 후에는 새 서버가 선택한 드라이버로 `SELECT 1`에 응답할
때까지(`scripts/wait_for_cubrid.py`) 최대 `INTEGRATION_READY_TIMEOUT`초(기본값
180) 기다리며, 끝내 응답하지 않으면 실패합니다. 새 컨테이너는 데이터베이스를
만들고 브로커를 시작하는 데 약 20초가 걸립니다. #575 이전의 고정 10초 대기는
스위트를 너무 일찍 시작시켜, 첫 테스트들이 CCI -20004로 실패하고 import 시점에
서버를 확인하던 라이브 테스트 파일들이 스스로 skip되었습니다. #593 이후로는 어떤
파일도 import 시점에 확인하지 않으며, 서버가 응답하지 않으면 conftest 게이트가 모든
통합 테스트를 error로 만들므로 준비되지 않은 서버는 실행을 건너뛰지 않고 실패시킵니다.

`make integration`은 기본적으로 `sqlalchemy-cubrid-it-<timestamp>-<pid>`라는
자체 Compose 프로젝트에서 실행됩니다. 따라서 컨테이너, 네트워크와 `cubrid-data`
볼륨은 다른 모든 실행, 그리고 `docker compose up -d`나 `make docker-up`으로 시작한
스택과 분리됩니다. 후자의 프로젝트 이름은 Compose가 체크아웃 디렉터리 이름(또는
`COMPOSE_PROJECT_NAME`)으로 정합니다.

시작하기 전에 해당 프로젝트에 컨테이너, 볼륨 또는 네트워크가 없고 이름이 정확히
`<project>_cubrid-data`인 볼륨도 없는지 확인합니다. 무엇이든 발견되면 실행을
거부하며 아무것도 시작하거나 삭제하지 않습니다. 확인 자체가 실패하면(예: Docker
데몬에 연결할 수 없음) `Ownership check ... failed; nothing was started`를 출력하고
중단합니다. 확인을 통과한 뒤에야 정리를 등록하므로 `docker compose -p <project> down -v`는
이번 실행이 만든 리소스만 삭제합니다.

정리는 셸이 종료될 때 실행되며, 컨테이너 시작, 준비 대기 또는 테스트가 실패한
경우와 실행이 `SIGINT`(Ctrl-C), `SIGTERM`(예: `timeout`이나 `kill`) 또는
`SIGHUP`(터미널 종료)을 받은 경우에도 실행됩니다.

- `docker compose up -d` 실행 중에 시그널을 받으면 정리는 먼저
  `INTEGRATION_STOP_GRACE`초(기본값 10)까지 `up -d`가 끝나기를 기다립니다. Docker
  데몬은 클라이언트가 종료된 뒤에도 컨테이너 생성을 끝까지 수행하므로, `up -d`를
  중간에 멈추면 `down -v`가 이미 놓친 컨테이너와 다시 생성된 볼륨이 남을 수 있습니다.
  `up -d`는 자체 프로세스 그룹에서 실행되므로 터미널의 Ctrl-C가 전달되지 않습니다.
  유예 시간이 지나도 실행 중이면 Compose 플러그인 프로세스를 포함한 그룹 전체에
  `SIGTERM`을 보내고, 정리는 그 그룹 전체가 종료될 때까지 기다립니다.
- 그 밖의 실행 중인 단계(준비 대기 또는 pytest)에는 즉시 `SIGTERM`을 보내고,
  `INTEGRATION_STOP_GRACE`초 후에도 실행 중이면 강제 종료합니다.
- 정리는 한 번만 실행되고, 명령은 128 + 시그널 번호(130, 143 또는 129)로 종료합니다.
- `docker compose down -v`가 끝날 때까지 추가 `SIGINT`, `SIGTERM`, `SIGHUP`은
  무시되며 `down -v`는 별도 세션에서 실행됩니다. Ctrl-C를 다시 누르거나 GNU
  `timeout`처럼 프로세스 그룹 전체에 시그널을 보내도 정리가 중단되거나 반복되지
  않습니다. `down -v` 자체가 멈추면 `SIGQUIT`(`Ctrl-\`)로 기다리지 않고 `make`를
  중지할 수 있습니다.
- 비대화형 셸의 백그라운드 작업에서 `SIGINT`처럼 `make`가 시작될 때 이미 무시되던
  시그널은 처리할 수 없습니다.

정리까지 실패하면 최초 실패를 유지하고, 테스트가 성공했더라도 정리가 실패하면
명령은 실패합니다. 정리 오류는 명시적으로 출력됩니다. `SIGKILL`이나 호스트 종료처럼
처리할 수 없는 종료 상황에서는 정리를 보장하지 않습니다. 이렇게 남은 프로젝트는
`docker compose ls -a`로 이름을 확인한 뒤 `docker compose -p <project> down -v`로
삭제하세요.

컨테이너는 CUBRID를 호스트 포트 33000에 게시합니다. 이 포트가 이미 사용 중이면
`make integration CUBRID_PORT=33999`처럼 다른 포트를 지정하세요. 테스트 URL도 이
포트를 따릅니다. `INTEGRATION_PROJECT=<name>`으로 프로젝트 이름을 고정할 수
있습니다. 이름은 `^[a-z0-9][a-z0-9_-]*$`와 일치해야 하며(그렇지 않으면 Docker 명령을
실행하기 전에 상태 2로 종료), 같은 사전 존재 확인이 적용됩니다. 같은 고정
`INTEGRATION_PROJECT`로 두 실행을 동시에 하는 것은 지원하지 않습니다. pytest는
터미널의 표준 입력을 유지하므로 `make integration PYTEST="python3 -m pytest --pdb"`로
디버거를 사용할 수 있습니다. 디버거에서 Ctrl-C를 누르면 실행이 끝나고 정리됩니다.

이미 실행 중인 서버에는 `CUBRID_TEST_URL`을 설정하고 `make integration-local`을
사용하세요. 이 대상은 Docker를 시작하거나 중지하지 않으며 외부 서버를 유지합니다.

---

## 다중 버전 테스트

### tox 구성

`tox.ini`는 Python 3.11–3.14의 로컬 오프라인 환경, 고정된 Ruff 린트 환경,
CI와 같은 Makefile 타깃 및 SQLAlchemy/Python 조합을 쓰는 `typecheck-sa20` /
`typecheck-sa21` 환경을 정의합니다. 기존 pycubrid/Alembic extra와 개발 테스트
의존성을 사용합니다. `py3xx` 환경의 오프라인 선택은 `-m "not integration and not repo"`이고,
`repo` 환경은 저장소 도구 테스트를 `-m repo`로 실행합니다(#594). 통합 환경은
`-m integration`과 `--ignore=test/test_suite.py`를 사용합니다. 공식 SQLAlchemy
컴플라이언스 스위트는 `--dburi`로 활성화되는 테스트 플러그인이 필요하며 기존 CI가
해당 인자와 알려진 실패 기준을 사용해 별도로 실행합니다. 일반 tox 통합 실행에는
공식 스위트가 포함되지 않습니다. 오프라인 커버리지 임계값은 95%를 유지합니다.

```ini
[tox]
envlist = lint, typecheck-sa20, typecheck-sa21, py310, py311, py312, py313, py314, repo
skip_missing_interpreters = true
```

### tox 실행

```bash
# 모든 환경 실행
tox

# 특정 Python 버전 실행
tox -e py312

# 린트 검사만 실행
tox -e lint

# 지정된 두 SQLAlchemy 타입 검사 환경 실행
tox -e typecheck-sa20,typecheck-sa21
```

### CI 매트릭스

일상 CI는 Ubuntu/Python 3.12 오프라인 단일 레인과 대표 통합 조합을 사용합니다.
PR은 스모크 검사를, main과 최근 변경이 있는 주간 실행은 전체 오프라인
검사와 95% 커버리지를 유지합니다. 고위험 PR은 최신 통합 조합을 선택하고,
main/주간 실행은 최저·최신 조합을 사용합니다. 저장소 도구 검사는 관련 경로에
따라 Linux 단일 레인에서 실행하며, 선택된 필수 잡은 성공해야 합니다.
전체 통합 검사는 명시적 수동 실행과 릴리스에서 유지합니다.
정확한 선택 조건과 검증 요건은 [CI 실행 정책](CI_POLICY.md)을 참고하세요.
과거 비용 측정은 이전 워크플로의 이력이며, 현재 잡 수나 새로운 절감액을
의미하지 않습니다.

---

## 코드 커버리지

### 요구사항

- **최소 임계값**: 라인 커버리지 95%
- CI는 `offline-tests` 작업(`.github/workflows/ci.yml`)에서 `--cov-fail-under=95`로 임계값을 강제합니다. 현재 테스트 개수와 커버리지는 여기 고정된 스냅샷 대신 `pytest test/ -m "not integration and not repo" --cov=sqlalchemy_cubrid --cov-report=term-missing`을 로컬에서 실행해 확인하세요 — 둘 다 PR마다 변합니다

### 커버리지 실행

```bash
# 커버리지 리포트와 함께
pytest test/ -v \
  --ignore=test/test_integration.py \
  --ignore=test/test_suite.py \
  --ignore=test/test_aio_integration.py \
  --cov=sqlalchemy_cubrid \
  --cov-report=term-missing \
  --cov-fail-under=95

# 또는 make로
make test
```

### 알려진 도달 불가능 라인

`compiler.py`와 `dml.py`의 일부 라인(`for_update_clause`/`limit_clause`의 빈
반환, DDL 컴파일의 기본 분기, 타입 정규화의 `else` 분기 등 방어적 폴백)은
SQLAlchemy 공개 API로는 발동할 수 없어 오프라인 스위트에서 절대 실행되지
않습니다. 정확한 라인 번호는 모듈이 바뀔 때마다 변하므로, 여기 고정된
목록 대신 `pytest test/ -m "not integration and not repo" --cov=sqlalchemy_cubrid
--cov-report=term-missing`(또는 `make test`)을 실행해 `Missing` 열에서
현재 목록을 확인하세요.

---

## 코드 스타일

### Ruff

이 프로젝트는 린팅과 포맷팅 모두에 [Ruff](https://docs.astral.sh/ruff/)를 사용합니다.

| 설정 | 값 |
|---|---|
| 행 길이 | 100자 |
| 대상 Python | 3.11+ |
| 린터 | `ruff check` |
| 포매터 | `ruff format` |

### 검사 실행

```bash
# 도구 일관성과 유지보수 대상 Python 소스 전체의 린트/포맷 검사
make lint

# 같은 공통 소스 경로에 수정과 포맷 적용
make format
```

---

## Pre-Commit 훅

Pre-commit 훅은 `git commit` 시 린트와 포맷 검사를 자동 실행합니다.

Ruff와 Mypy 버전의 기준은 `pyproject.toml`의 개발 의존성 핀입니다. Ruff와 Mypy
pre-commit 훅은 `repo: local` / `language: system` 훅으로, 같은 활성 `.[dev]`
환경에서 `python3 -m ruff`/`python3 -m mypy`를 직접 호출합니다. 따라서 맞춰야 할
별도의 훅 버전이 없습니다. mypy 훅은 활성 `.[dev,alembic]` 환경이 이미 제공하는
SQLAlchemy/Alembic으로 프로젝트의 엄격한 설정에 따라 `sqlalchemy_cubrid/`를
검사합니다. 스텁을 자동 설치하거나 누락된 임포트를 무시하지 않습니다. Ruff의 명시적
`include = ["*.py", "*.pyi"]`와 동일한 훅 타입 설정으로 CLI, CI, 훅 모두 Python
소스를 다루며 문서의 코드 스니펫을 다시 작성하지 않습니다.

Makefile의 공통 `LINT_PATHS`는 패키지, 테스트, 스크립트, 데모, 샘플,
`docs/source`의 Python 설정을 포함합니다. CI와 tox는 `make lint`를 실행하고,
훅은 계속 모든 추적된 Python/pyi 파일을 검사합니다. 일관성 검사는 유지보수 대상
디렉터리 누락이나 공통 타깃을 우회하는 실행 설정을 거부합니다.

Ruff나 Mypy를 올릴 때는 `pyproject.toml`의 dev 핀만 갱신하면 됩니다(Dependabot의
`pip` 생태계가 정확히 이 작업을 수행합니다): pre-commit 훅과
`tox -e lint`/`typecheck-sa20`/`typecheck-sa21` 환경 모두 프로젝트 자체의 `dev`
extra를 설치하므로 그 핀이 가리키는 버전을 그대로 사용합니다.
`tox -e typecheck-sa20`/`typecheck-sa21`은 CI의 타입 검사 매트릭스에 맞추기 위해
Python 버전별 정확한 SQLAlchemy 릴리스(3.11엔 2.0.53, 3.13엔 2.1.1)를 추가로
고정하며, 이 조합은 `scripts/check_tool_versions.py`가 CI에서 읽습니다. 갱신 후
`make check-tool-versions`, `pre-commit run --all-files`,
`tox -e lint,typecheck-sa20,typecheck-sa21`을 실행하세요. 일관성 검사는 CI 린트,
tox 린트, 로컬 pre-commit 훅에서 실행되므로 의존성만 갱신한 변경이 오래된 핀을
조용히 남길 수 없습니다.

### 설정

Ruff와 Mypy 훅은 `language: system`으로 실행되어, Git이 훅을 실행할 때 활성화된
환경에서 `python3 -m ruff`/`python3 -m mypy`를 직접 호출합니다. 먼저 그 같은
환경에 Ruff와 Mypy를 고정하는 프로젝트의 `dev` extra를 설치한 뒤 훅을
설치하세요:

```bash
pip install -e ".[dev]"
pre-commit install
```

커밋 시 훅이 실행되길 원한다면 그 환경(또는 이를 설치한 venv)을 항상
활성화해두세요. 그렇지 않으면 Ruff/Mypy가 없거나, 고정된 버전 대신 오래되거나
전역에 설치된 버전이 조용히 실행됩니다.

### 수동 실행

```bash
# 모든 파일에 모든 훅 실행
pre-commit run --all-files
```

---

## CI/CD 파이프라인

### GitHub Actions 워크플로

| 워크플로 | 파일 | 트리거 |
|---|---|---|
| CI | `.github/workflows/ci.yml` | PR, main, 주간, 수동 실행 |
| Integration Full | `.github/workflows/integration-full.yml` | 수동 실행, `publish-pypi.yml`에서 호출 |
| Prepare Release | `.github/workflows/release-please.yml` | main 푸시 또는 수동 실행; 검토할 릴리스 PR 생성 |
| Release | `.github/workflows/publish-pypi.yml` | main 푸시 (병합된 릴리스 PR만 릴리스), 복구용 수동 실행 |

### CI 파이프라인 단계

1. **Lint** — Ruff check + 포맷 검증
2. **오프라인 테스트** — Ubuntu/Python 3.12 단일 레인; PR 스모크, main/주간 전체 오프라인 커버리지
3. **통합 테스트** — 고위험 PR은 최신 조합; main/주간은 2개 조합(Python 3.14 × CUBRID 11.4, Python 3.11 × CUBRID 10.2), 비동기 통합 커버리지와 CUBRIDdb 및 릴리스된 pycubrid의 차단형 [SQLAlchemy 컴플라이언스 레인](#sqlalchemy-컴플라이언스-레인) 포함
4. **make integration** — 기본 드라이버 pycubrid로 CUBRID 11.4에서 `make integration` 실행: 로컬과 같이 `integration` 마커가 붙은 전체 스위트를 한 세션에서 실행 (두 드라이버 × CUBRID 10.2, 11.4는 수동 전체 검증 및 릴리스 게이트에서 `integration-full.yml`로 실행)
5. **커버리지** — main/주간 전체 오프라인 레인에서 ≥ 95% 임계값 강제; PR 스모크는 커버리지 검증을 주장하지 않음

### 드라이버 차분 레인

`test/test_driver_differential.py`는 같은 SQLAlchemy 작업을 pycubrid와
CUBRIDdb C 확장에서 실행하고 결과가 일치하는지 확인합니다. 기본 CRUD와 함께
릴리스된 드라이버에서 이미 동작하는 DB-API 계약 영역을 다룹니다. 정수·UTF-8/CJK·NULL
값을 사용하는 Core `executemany`, 정수·UTF-8/CJK 값을 사용하는 텍스트 `executemany`, 스칼라 바인드, 텍스트 SQL 결과 컬럼 이름,
커밋/롤백 가시성이 해당합니다. 또한 제약 조건 위반 예외 클래스(#480), 롤백 이후 읽은
결과(#481), 스칼라 `cursor.description`의 이름·타입 코드·`null_ok`(#482), 그리고
`SET`/`MULTISET`/`SEQUENCE` 왕복(#484, 릴리스된 pycubrid는 컬렉션을 매개변수로 바인딩하는
것을 거부하므로 컬렉션 리터럴을 SQL에 직접 작성한 뒤 각 드라이버가 돌려준 값을 `str`
원소로 정규화해 비교)도 비교합니다.
이 검사들은 pycubrid 1.8.0에 포함된 수정 동작(NOT NULL/외래 키 예외 클래스, 롤백 이후 결과,
`null_ok`)을 요구하며 조건 없이 실행됩니다. 이제 #479의 모든 계약 영역이 LOB(별도로
#485에서 다룸)을 제외하고 이 모듈에 차분 케이스를 갖습니다.

`ci.yml`과 `integration-full.yml`의 통합 잡은 두 드라이버를 모두 설치하고
`CUBRID_REQUIRE_DRIVER_DIFFERENTIAL=1`로 이 모듈을 실행합니다. 이 변수가 설정되면
`test/conftest.py`는 실행되어 통과한 차분 케이스가 하나도 없을 때 세션을 실패시키므로,
두 드라이버가 모두 연결되지 않은 레인이 성공으로 보고될 수 없습니다. 테스트 전에
`python -m scripts.report_driver_versions`가 정확한 Python, SQLAlchemy, pycubrid,
CUBRIDdb(패키지 버전과 소스 태그), CUBRID 서버 버전을 잡 로그와 GitHub 단계 요약에
기록합니다. 변수를 설정하지 않은 로컬 실행은 드라이버가 없으면 계속 깔끔하게
건너뜁니다. `CUBRID_TEST_URL`의 서버에 연결할 수 없으면 다른 모든 통합 테스트와
마찬가지로 error가 됩니다(#593).

```bash
export CUBRID_TEST_URL="cubrid://dba@localhost:33000/testdb"
CUBRID_REQUIRE_DRIVER_DIFFERENTIAL=1 pytest test/test_driver_differential.py -v -rs
```

### 전부 건너뛴 레인 가드

실행하려던 테스트를 전부 건너뛴 레인도 일반 pytest에서는 `0`으로 종료되어,
잘못 구성된 레인(오래된 `skipif`, 더 이상 연결되지 않는 드라이버, 더 이상 맞지 않는
파일 목록)이 녹색 체크 뒤에 숨어버립니다. 필수 드라이버 차분, 트랜잭션 DDL(#503),
서버 재시작(#565) 레인은 이미 `test/conftest.py`의 자체 `CUBRID_REQUIRE_*` 검사로
스스로를 보호합니다. `ci.yml`의 `integration-tests`, `make-integration` 잡과
`integration-full.yml`의 `integration-full`, `make-integration` 잡에 있는 일반
`pytest`/`make integration` 단계에서는 `scripts/check_not_all_skipped.py`가 직전
실행의 `tee` 출력을 읽어, 최소 하나의 요약 줄이 실제 실행
(`passed`/`failed`/`error`/`xpassed`/`xfailed`)을 보여주지 않으면 실패시킵니다.
`skipped`/`deselected`만 있거나 수집된 테스트가 0개면 해당 단계가 실패합니다:

```bash
set -o pipefail
python -m pytest test/test_integration.py -v --tb=short | tee integration.log
python -m scripts.check_not_all_skipped integration.log --label "Run integration tests"
```

특정 셀이 의도적으로 전부 건너뛰도록 되어 있다면 `--allow-all-skipped "<이유>"`를
전달해 실패 대신 이유를 출력하고 0으로 종료하게 합니다. `matrix-result`와
`full-matrix-result`는 변경이 필요 없습니다: 이 검사는 이미 그 잡들이 의존하는 잡
내부에서 실행되므로, 이 가드에 걸린 단계는 이미 해당 잡을 실패시킵니다.

### SQLAlchemy 컴플라이언스 레인

공식 SQLAlchemy 방언 컴플라이언스 스위트(`test/test_suite.py`, `--dburi`로 실행)는
두 드라이버 레인에서 병합을 차단합니다. 두 레인 모두 `ci.yml`의
`integration-tests` 잡의 단계로, 해당 셀의 CUBRID 서비스를 재사용하며, 실패하면
`matrix-result`도 실패합니다.

| 레인 | URL | 고정 버전 | CI 셀 |
|---|---|---|---|
| `cubrid@sa2.0` | `cubrid://` (CUBRIDdb C 확장) | cubrid-python v11.3.0.51, SQLAlchemy 2.0.53 | Python 3.14 × CUBRID 11.4 |
| `pycubrid@sa2.0` | `cubrid+pycubrid://` (권장) | pycubrid 1.8.0, SQLAlchemy 2.0.53 | Python 3.11 × CUBRID 10.2 |
| `pycubrid@sa2.1` | `cubrid+pycubrid://` (권장) | pycubrid 1.8.0, SQLAlchemy 2.1.1 | Python 3.14 × CUBRID 11.4 |

두 pycubrid 레인은 SQLAlchemy 2.0과 2.1을 두 PR 셀에 나누어 실행하므로 각 셀은
pycubrid 스위트를 한 번만 실행합니다(SQLAlchemy 2.1은 Python 3.11 이상이 필요하므로
3.14 셀에서 실행). 모든 레인 기준선은 새로 만든 CUBRID 10.2와 11.4 데이터베이스에서
수집했습니다. 각 pycubrid 단계는 먼저
`python -m scripts.report_driver_versions`를 실행해 정확한 Python, SQLAlchemy,
pycubrid, CUBRID 서버 버전을 잡 로그와 단계 요약에 기록합니다. CUBRID 10.2 셀의
CUBRIDdb 스위트는 계속 비차단입니다.

**알려진 실패는 레인별로 키가 지정됩니다.** `test/known_failures.txt`의 모든
항목은 실패하는 레인을 `<driver>@sa<major.minor>` 형식으로, 특정 CUBRID 서버
버전에서만 실패하면 `<driver>@sa<major.minor>@cubrid<major.minor>` 형식으로
명시합니다.

```text
test/test_suite.py::DistinctOnTest::test_distinct_on  cubrid@sa2.0 pycubrid@sa2.0 pycubrid@sa2.1
test/test_suite.py::NumericTest::test_float_as_decimal  cubrid@sa2.0
```

`test/conftest.py`는 `--dburi` 방언, 설치된 SQLAlchemy 버전, 연결된 서버 버전으로 현재 레인을
결정하고, 그 레인에 태그된 항목에만 strict xfail을 적용합니다. 따라서
CUBRIDdb 전용 실패가 pycubrid 회귀를 가릴 수 없고, 그 반대도 마찬가지입니다.
와일드카드 태그는 없으며, 태그가 없는 항목이나 CI가 게이트하지 않는 레인(예: `pycubrid@sa2.2`)은 로드 오류입니다.
`CUBRID_STRICT_KNOWN_FAILURES=1`(모든 게이트 단계에서 설정)이면 다음 경우에도
실행이 실패합니다.

- 등록된 테스트가 통과함(strict XPASS): 해당 레인 태그를 제거합니다.
- 레인 항목이 수집된 테스트와 하나도 일치하지 않음(오래된 기준선).
- 등록된 항목이 xfail이 아니라 건너뛰어짐: 더 이상 아무것도 증명하지 않으므로
  항목을 제거하거나 건너뛰는 원인을 고칩니다.
- 레인 항목이 전혀 없음: 새 드라이버나 SQLAlchemy 마이너 버전이 실수로 빈
  기준선으로 게이트되지 않도록 합니다.
- 설치된 SQLAlchemy가 레인을 수집한 릴리스와 다름(`test/conftest.py`의
  `_PINNED_SQLALCHEMY`).

매니페스트 파서는 같은 노드 ID가 두 번 나오거나, 서버를 지정한 태그가 CI가
게이트하는 (레인, 서버) 쌍(`_GATED_SERVER_LANES`: `cubrid@sa2.0@cubrid11.4`,
`pycubrid@sa2.0@cubrid10.2`, `pycubrid@sa2.1@cubrid11.4`)이 아니면 거부하므로,
오타가 있거나 실행되지 않는 서버 태그가 들어갈 수 없습니다.

CUBRID에 전혀 적용할 수 없는 테스트(예: 단정밀도 `FLOAT`의 7자리 소수 정밀도,
UTF-8이 아닌 데이터베이스의 비 ASCII 식별자)는 목록에 넣지 않고
`sqlalchemy_cubrid/requirements.py`에서 사유와 함께 제외합니다. 모든 requirement
속성은 **새** `exclusions.open()` / `exclusions.closed()` 객체를 반환해야 합니다.
SQLAlchemy는 중첩된 `@testing.requires` 체인의 첫 requirement 객체를 제자리에서
확장하므로, 공유 객체를 쓰면 다른 모든 requirement가 조용히 닫혀 스위트 대부분이
건너뛰어집니다(`test_stacked_requirements_do_not_leak_into_other_properties`가 이를
검사합니다).

**레인 기준선 갱신** (SQLAlchemy 버전 업, 새 고정 pycubrid, 등록된 테스트를
통과시키는 수정):

```bash
export CUBRID_TEST_URL="cubrid+pycubrid://dba@localhost:33000/testdb"
pip install "pycubrid==1.8.0" "sqlalchemy[asyncio]==2.1.1"
# 1. 수집: strict 모드가 아니면 없는 레인은 xfail을 적용하지 않을 뿐입니다.
pytest test/test_suite.py --dburi="$CUBRID_TEST_URL" --maxfail=1000 -q -r fE
# 2. 모든 실패를 분류하고(방언 버그, 드라이버 제한, 백엔드/스위트 한계)
#    이슈를 연결한 뒤 이 레인의 태그만 수정합니다.
# 3. CI와 동일하게 검증합니다.
CUBRID_STRICT_KNOWN_FAILURES=1 pytest test/test_suite.py --dburi="$CUBRID_TEST_URL" -q
```

레인을 추가할 때는 CUBRID 10.2와 11.4 모두에서 수집한 뒤, 같은 변경에서 `ci.yml`의
고정 버전, `test/known_failures.txt` 헤더, `test/test_known_failures.py`의
`_GATED_LANES`를 함께 갱신합니다.

### pycubrid 릴리스 후보 채택

`pycubrid@main`을 대상으로 하는 주간 `upstream-canary.yml` 실행은 비차단으로
유지합니다. 다가오는 회귀를 경고하지만, 릴리스되지 않은 업스트림 HEAD가 관련 없는
PR을 막아서는 안 됩니다. 다만 실패는 보고됩니다. 기본 브랜치의 예약 실행이나 수동 실행에서 canary 작업이
실패하면 워크플로가 "Upstream canary failing against pycubrid@main" 제목의 이슈(`ci` 레이블)를
열거나, 이미 열려 있으면 댓글을 달아 실패한 작업, 실행 링크, 테스트한 pycubrid 커밋을 남기고,
두 작업이 다시 통과하면 이슈를 닫습니다. 의존성 범위 `pycubrid>=1.8.0,<2.0`은 정확한 버전으로 설치한
**특정** pycubrid 릴리스 후보(또는 새 메이저 릴리스)가 다운스트림 계약 스위트, 즉 일반·비동기
통합 테스트, 위의 필수 드라이버 차분 레인, SQLAlchemy 호환성 스위트를 통과한 뒤에만
넓힙니다. 채택 PR에는 `scripts/report_driver_versions.py`가 보고한 버전을 기록하고,
같은 변경에서 `CHANGELOG.md`와 지원 문서에 새로 지원하는 범위를 반영합니다.

`CUBRID_PYCUBRID_UPSTREAM` strict xfail 게이트는 pycubrid 1.8.0이 해당 수정(pycubrid#390, #395,
#430, #431)을 포함해 릴리스되면서 제거되었습니다.

### 문서 검사

문서 예외는 코드·인용·템플릿 주석 밖의 내용이 채워진 단독 물리 소스 줄
`Docs: not needed - <reason>` 또는 기존 유지보수자 관리 라벨을 사용합니다.
`make check-docs-reason`은 doctest와 실제 이벤트 JSON/워크플로 회귀 검사를 실행하며
`make check-all`과 docs-sync 잡도 같은 검사를 실행합니다. 번역 도움 요청은 우회
권한을 부여하지 않습니다. 유지보수자가 기존 `translations-deferred` 라벨을 명시적으로
승인하고 후속 작업을 기록합니다. 한국어 필수·다른 언어 권고 검사는 유지합니다.

`docs/` 아래 영어 문서가 기준이고, `docs/ko/` 아래 한국어는 완전하게 유지하는 유일한
번역입니다. `python scripts/check_docs_translation.py`(린트 잡에서 실행)는 모든
`docs/<name>.md`를 `docs/ko/<name>.md`와 비교해, 한국어 파일이 없거나 제목(2~4단계),
펜스 코드 블록, 표 행의 개수가 다르면 실패합니다. 영어 섹션을 추가할 때는 같은
PR에서 한국어 섹션도 추가하세요. 의도적으로 영어로만 두는 문서는 그 스크립트의
`EXCEPTIONS`에 사유와 함께 넣습니다. 이 검사는 구조를 비교할 뿐 문구는 보지 않습니다.

### 릴리스 파이프라인

릴리스는 유지보수자 전용이며 [RELEASING.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/RELEASING.md)를 따릅니다:
`release-please.yml`이 릴리스 PR(버전 갱신 + 날짜가 있는 CHANGELOG 섹션, `make release-check VERSION=X.Y.Z`로 확인)을
엽니다. 검토 후 squash 병합하면 `publish-pypi.yml`이 전체 매트릭스, 한 번의 빌드, 태그, PyPI 게시, cookbook 검증을
자동으로 수행합니다. 태그 푸시나 게시를 수동으로 하지 않습니다.

---

*참고: [기여 가이드](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/CONTRIBUTING.md) · [기능 지원](FEATURE_SUPPORT.md) · [연결 가이드](CONNECTION.md)*
