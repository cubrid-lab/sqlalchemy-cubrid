# sqlalchemy-cubrid 기여 안내

> [CONTRIBUTING.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/CONTRIBUTING.md)의 한국어 번역입니다. 영어 원문이 표준입니다.

기여하려는 관심에 감사드립니다! 이 문서는 프로젝트에 기여하기 위한 지침과
절차를 안내합니다.

## 목차

- [개발 환경 설정](#development-setup)
- [테스트 실행](#running-tests)
- [Docker 통합 테스트](#docker-integration-testing)
- [코드 스타일](#code-style)
- [PR 지침](#pull-request-guidelines)
- [이슈·PR·커밋 제목](#pull-request-and-commit-titles)
- [릴리스](#releases)
- [이슈 보고](#reporting-issues)

---

<a name="development-setup"></a>

## 개발 환경 설정

### 사전 준비

- Python 3.11 이상
- Git
- Docker (통합 테스트용)

### 설치

```bash
# 저장소 복제
git clone https://github.com/cubrid-lab/sqlalchemy-cubrid.git
cd sqlalchemy-cubrid

# 가상 환경 생성
python3 -m venv venv
source venv/bin/activate

# dev 의존성과 함께 개발 모드로 설치
pip install -e ".[dev]"

# pre-commit 훅 설치
pre-commit install
```

---

<a name="running-tests"></a>

## 테스트 실행

### 오프라인 테스트 (데이터베이스 불필요)

대부분의 테스트는 CUBRID 인스턴스 없이 실행됩니다:

```bash
# 빠른 오프라인 테스트 실행 (반복 작업 중에 쓰는 명령)
make test

# 저장소 도구 테스트 실행 (Makefile 레시피, 시그널 처리, 저장소 스크립트)
make test-repo

# 모든 오프라인 테스트 실행 (위 두 가지 모두)
make test-offline

# 공유 린트, strict 타입 검사와 보안 검사 실행
make check-all

# 특정 테스트 파일 실행
pytest test/test_compiler.py -v

# 특정 테스트 실행
pytest test/test_compiler.py::TestCubridSQLCompiler::test_select_limit -v
```

`make test`는 `-m "not integration and not repo"`를 선택합니다. `repo` 마커는
`test/conftest.py`가 `REPO_TOOLING_MODULES`에 나열된 모듈
(`test_make_integration.py`, `test_docs_reason.py`, `test_release_detect.py`)의
모든 테스트에 적용합니다. 이 테스트들은 Makefile과 저장소 스크립트를 서브프로세스로
실행하며 오프라인 실행 시간의 대부분을 차지했습니다(#594). 그래도 여전히
필수입니다. CI는 모든 PR에서 `repo-tests` 잡으로 이를 실행합니다. `Makefile`,
`scripts/` 또는 해당 테스트의 변경을 push하기 전에 `make test-repo`를 실행하세요.
방언이 아닌 저장소 도구를 테스트하는 새 모듈은 `REPO_TOOLING_MODULES`에
넣어야 합니다.

### 통합 테스트 (CUBRID 필요)

```bash
# CUBRID 컨테이너 시작
docker compose up -d

# 연결 URL 설정
export CUBRID_TEST_URL="cubrid+pycubrid://dba@localhost:33000/testdb"

# 동기/비동기 연결 사전 점검과 함께 일반 순수 드라이버 프로파일 실행
tox -e integration

# 작업이 끝나면 컨테이너 중지
docker compose down
```

`CUBRID_TEST_URL`이 통합 테스트의 실행 여부를 결정합니다. 설정하지 않으면
스킵합니다(그리고 통합 테스트를 선택한 `CI=true` 실행은 1로 종료합니다). 설정하면
그 URL 뒤의 서버가 URL의 드라이버를 통해 `SELECT 1`에 응답해야 하며, 그렇지
않으면 모든 통합 테스트가 조용히 스킵하는 대신 비밀번호를 뺀 URL을 명시한 하나의
메시지와 함께 오류를 냅니다(#593). 의도적으로 스킵하려면 변수를 해제하거나
`-m "not integration"`을 사용하세요.
[docs/DEVELOPMENT.md](ko/DEVELOPMENT.md#건너뛸지-실패할지-cubrid_test_url이-스위치입니다)를 참고하세요.

### tox를 이용한 다중 Python 테스트

```bash
tox           # 모든 환경 실행
tox -e py312  # 특정 Python 버전 실행
tox -e lint   # 린트 검사만 실행
```

### 커버리지 목표

**95% 이상의 코드 커버리지**를 유지합니다. CI 파이프라인이 이 기준을 강제합니다.

---

<a name="docker-integration-testing"></a>

## Docker 통합 테스트

로컬 개발용 `docker-compose.yml`을 제공합니다:

```bash
# CUBRID 시작 (기본 버전: 11.2)
docker compose up -d

# 특정 CUBRID 버전으로 테스트
CUBRID_VERSION=11.4 docker compose up -d

# 로그 보기
docker compose logs -f cubrid

# 중지 및 제거
docker compose down -v
```

지원되는 CUBRID 버전: `11.4`, `11.2`, `11.0`, `10.2`.

`make integration`은 이 기본 스택을 사용하지 않습니다. 고유한 이름의 자체 Compose
프로젝트를 시작하고, 그 프로젝트에 이미 컨테이너·볼륨·네트워크가 있으면 실행을
거부하며, Ctrl-C, `SIGTERM` 또는 `SIGHUP` 뒤에도 자신이 만든 것만 제거합니다
(`docker compose -p <project> down -v`). 포트 33000이 사용 중이면
`make integration CUBRID_PORT=<port>`를 사용하세요. 선택한 드라이버를 통해 서버가
응답할 때까지 기다린 뒤 pycubrid(`cubrid+pycubrid://`)로 전체 통합 스위트를
실행합니다. CUBRIDdb C 확장(`cubrid://`)으로 실행하려면
`make integration INTEGRATION_DRIVER=cubriddb`를 사용하세요.
[docs/DEVELOPMENT.md](ko/DEVELOPMENT.md#빠른-통합-워크플로)를 참고하세요.

---

<a name="code-style"></a>

## 코드 스타일

이 프로젝트는 [Ruff](https://docs.astral.sh/ruff/)로 린트와 포맷 검사를 수행합니다.

### 규칙

- **줄 길이**: 100자
- **대상 Python**: 3.11+
- **포매터**: `ruff format`
- **린터**: `ruff check`

### 검사 실행

```bash
# 동기화된 도구 설정과 유지 관리하는 모든 Python 소스 경로 검사
make lint

# 같은 공유 경로에 수정과 포맷 적용
make format

# strict 타입 검사, 또는 린트 + 타입 검사 + 보안 검사를 함께 실행
make typecheck
make check-all
```

### Pre-commit 훅

pre-commit 훅을 설치했다면 이 검사들은 `git commit` 시 자동으로 실행됩니다.
모든 훅을 수동으로 실행하려면:

```bash
pre-commit run --all-files
```

---

<a name="pull-request-guidelines"></a>

## PR 지침

### 제출 전

1. `main`에서 **기능 브랜치를 만드세요**:
   ```bash
   git checkout -b feature/my-feature main
   ```

2. 새 기능에는 **테스트를 작성하세요**. 95% 이상의 커버리지가 필요합니다.

3. **오프라인 테스트 스위트를 실행하고** 모든 테스트가 통과하는지 확인하세요:
   ```bash
   make test
   make test-repo   # Makefile, scripts/ 또는 해당 테스트를 변경한 경우
   ```

4. **공유 린트, 타입, 보안 검사를 실행하세요**:
   ```bash
   make check-all
   ```

5. 변경이 데이터베이스 상호작용에 영향을 주면 **통합 테스트를 실행하세요**:
   ```bash
   docker compose up -d
   export CUBRID_TEST_URL="cubrid+pycubrid://dba@localhost:33000/testdb"
   tox -e integration
   ```

### PR 내용

- PR을 한 가지 목적에 집중하세요 — PR 하나에 기능 또는 수정 하나.
- _무엇을_ _왜_ 변경했는지 명확히 설명하고, PR 제목은
  [이슈·PR·커밋 제목](#pull-request-and-commit-titles)에 설명한 대로 작성하세요.
- 관련 이슈는 제목이 아니라 PR 본문에서 참조하세요(예: `Fixes #42`).
- 변경이 공개 API에 영향을 주면 문서를 갱신하세요.
- 변경 요약을 `CHANGELOG.md`에 기록하세요.

### 검토 절차

- 모든 PR은 병합 전에 최소 한 번의 검토가 필요합니다.
- CI가 통과해야 합니다(린트, 오프라인 테스트, 통합 테스트).
- 명시적으로 승인받지 않는 한 하위 호환성을 유지하세요.

기여자는 dev extra를 설치하고, 공유 검사를 실행하고, 관련 문서를 갱신한 뒤
동기, 명령·결과와 실행하지 못한 검사의 이유를 담아 PR을 엽니다.
문서를 변경하면 `python scripts/generate_llms_full.py`를 실행하세요(이 명령은
`docs/llms-full.txt`를 다시 생성하고 표준 `docs/llms.txt` 인덱스를 루트
`llms.txt`에 복사합니다. `docs/llms.txt`만 편집하세요). 그리고
`mkdocs-material`과 `pymdown-extensions`가 있는 문서 환경에서 `mkdocs build --strict`를 실행하세요.
메인테이너는 프로젝트별 Oracle/Codex 검토, 최종 통합, 릴리스 분류, 저장소
시크릿과 GitHub 라벨을 조율합니다. 기여하는 데 특정 에이전트 설치, 저장소
시크릿 접근 권한이나 지정된 공동 저자는 필요하지 않습니다.
실제 저작 정보를 보존하고, AI 검토 메모와 실제로 실행한 테스트 증거를 구분하세요.
GitHub 이슈, PR과 댓글은 영어로 작성하세요. 현지화 문서 기여는 계속 환영합니다.

동작과 관련된 문서를 함께 갱신하세요. 문서 변경이 필요 없으면 플레이스홀더를
그대로 두지 말고 내용을 채운 독립된 물리적 소스 줄 `Docs: not needed - <reason>`을
사용하세요. 설명에는 눈에 보이는 텍스트가 있어야 합니다.
`[**<!-- empty -->**](/issue)`나 `[**![](/img)**](/issue)` 같은 빈 강조 링크 캡션은
이유가 되지 않지만, `[**tests only**](/issue)`는 이유가 됩니다. `docs-not-needed`
라벨은 계속 메인테이너가 관리합니다. 번역 도움이 필요하면
PR 본문에 빠진 언어와 사유를 적으세요. 이는 요청일 뿐 허가가 아닙니다.
기존 `translations-deferred` 라벨을 통한 메인테이너의 명시적 승인만이 번역
게이트를 보류하며, 후속 작업을 기록합니다.
한국어 필수 검사와 다른 언어의 권고 검사는 변함없이 유지됩니다.

재사용 워크플로는 검토한 upstream 커밋 SHA로 갱신합니다. 그 커밋의 대상
파일과 `workflow_call` 입력을 확인하고, 관련 호출부를 함께 갱신한 뒤 PR로
검증하세요. 고정된 doc-lint 잡은 여전히 설정된 main 기반 자산을 내려받으므로,
호출부 고정이 그 자산까지 고정하지는 않습니다.

---

<a name="pull-request-and-commit-titles"></a>

## 이슈·PR·커밋 제목

모든 cubrid-lab 저장소의 이슈 제목, PR 제목과 커밋 첫 줄에 적용합니다.
PR은 squash-merge하며 PR 제목이 `main`의 커밋 제목이 되므로, PR 제목을
정확히 작성해야 합니다. `PR title` 검사가 이를 강제합니다.

```text
type: description
type(scope): description
type!: description
type(scope)!: description
```

- **type**: 소문자로 다음 중 정확히 하나를 사용합니다. `feat`, `fix`, `docs`,
  `test`, `perf`, `refactor`, `ci`, `build`, `chore`, `style`, `revert`.
- **scope**: 선택 사항이며 소문자·숫자·`-`·`_`를 사용합니다. 예: `compiler`,
  `aio`, `deps`, `release`.
- 콜론 앞의 **`!`**는 호환성을 깨는 변경입니다. 그런 변경에는 저장소 릴리스
  정책도 따르세요.
- 콜론 뒤에는 정확히 **공백 하나**를 둡니다.
- **description**: 영어로 구체적으로 적으세요. 변경한 함수·타입·동작을
  명시하고, 첫 단어가 API 이름·약어·고유명사가 아니면 소문자로 시작합니다.
  끝에 마침표를 붙이지 않습니다.
- 대괄호·상태·우선순위 접두사(`[Bug]`, `[WIP]`,
  `Track:`, `epic:`, `P1`)를 붙이지 않습니다. 미완성 작업은 draft PR로 열고,
  우선순위와 크기는 라벨로 표시합니다.
- 제목에 이슈·PR 번호를 넣지 마세요. PR 본문에 `Closes #123` 또는
  `Refs #123`을 적습니다. GitHub가 squash 커밋에 `(#456)` 같은 PR 번호를
  자동으로 붙입니다.

| 유형 | 용도 |
|------|------|
| `feat` | 사용자에게 보이는 새 기능 |
| `fix` | 보안 수정을 포함한 잘못된 동작의 수정 |
| `docs` | 문서만 변경 |
| `test` | 테스트만 변경 |
| `perf` | 동작 변화 없이 더 빠르거나 가볍게 변경 |
| `refactor` | 동작 변화 없는 구조 변경 |
| `ci` | CI 워크플로와 설정 |
| `build` | 패키징과 빌드 시스템 |
| `chore` | 릴리스·의존성 갱신·정리 등의 유지보수 |
| `style` | 포맷만 변경 |
| `revert` | 앞선 변경 되돌리기; 설명에 대상 변경을 명시 |

예시:

```text
fix(protocol): keep the CAS session after OUT_TRAN
feat(aio): add a charset connection option
docs: document JSON as_numeric() input limits
chore(deps): bump ruff from 0.16.8 to 0.16.9
chore: release v1.9.0
refactor(compiler)!: drop legacy LIMIT rendering
```

이슈 양식은 유형 접두사를 미리 채웁니다. 이를 유지하고 제목의 나머지도 같은
형식으로 쓰세요. 추적 이슈(epic)는 추적하는 작업의 유형을 사용합니다.

메인테이너는 **squash merge만** 사용하고 PR 제목을 커밋 제목으로 유지합니다.
브랜치 커밋은 커밋 본문으로 합쳐지므로 메시지를 의미 있게 쓰고
`Co-authored-by:` trailer를 그대로 보존하세요.

---

<a name="releases"></a>

## 릴리스

기여자는 릴리스하지 않습니다. 사용자에게 보이는 변경은 `CHANGELOG.md`의
`## [Unreleased]` 아래에 적고, 일반 PR에서 `__version__`을 변경하거나 날짜가
있는 `## [X.Y.Z]` 섹션을 추가하지 마세요. 버전 변경이 병합되면 자동 릴리스가
시작됩니다. 메인테이너는 `release-please.yml`로 릴리스 PR을 준비합니다.
[`RELEASING.md`](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/RELEASING.md)를 참고하세요.

---

<a name="reporting-issues"></a>

## 이슈 보고

기존 이슈를 먼저 검색한 뒤 가장 가까운 이슈 양식을 사용하세요. 미리 채운 제목
접두사(`fix:`, `feat:` 또는 `chore:`)를 유지합니다. 직접 만든 이슈는 PR 제목과
같은 `type(scope): description` 형식을 사용하세요
([이슈·PR·커밋 제목](#pull-request-and-commit-titles) 참고). 예:
`fix(reflection): ...` 또는 `docs: ...`.

제보자는 영향과 재현 방법을 설명하며, GitHub 라벨 권한이 없어도 보고할 수
있습니다. 메인테이너가 유형 라벨과 `priority: <value>`, `size: <value>`를
각각 하나씩 지정하고 필요하면 `area:`도 붙입니다. `testing` 같은 주제 라벨도
있을 수 있습니다. 사람이 CLI/API로 올린 이슈의 메타데이터가 불완전하면
`status: needs triage`가 붙습니다. 메인테이너가 메타데이터를 바로잡고 그 라벨을
제거합니다. `GITHUB_TOKEN`으로 이슈를 만드는 워크플로는 제목과 라벨을 직접
지정해야 합니다. GitHub는 그 이벤트로 다른 워크플로를 시작하지 않습니다.

버그를 보고할 때는 다음을 포함하세요:

- Python 버전 (`python --version`)
- SQLAlchemy 버전 (`pip show sqlalchemy`)
- CUBRID 서버 버전
- CUBRID-Python 드라이버 버전
- 최소 재현 코드
- 전체 traceback

기능 요청에는 사용 사례와 기대 동작을 설명하세요.

라벨을 편집할 수 없더라도 긴급성과 대략적인 범위를 알려 주세요. 메인테이너나
triager가 필수 표준 priority/size 라벨을 지정하므로 기여자에게 라벨 쓰기 권한은
필요하지 않습니다.

---

## 질문이 있나요?

[GitHub Discussion](https://github.com/cubrid-lab/sqlalchemy-cubrid/discussions)을
열거나 [이슈](https://github.com/cubrid-lab/sqlalchemy-cubrid/issues)를 등록하세요.

## 실행 가능한 이슈 설명 유지

코딩 전에 문제, 기대 동작, 범위, 완료 기준과 검증 방법을 합의하세요. 본문은
현재 명세로 유지하고 날짜가 있는 진행 상황은 댓글에 적습니다. 메인테이너는
관련 병합·인계 뒤에 닫힌 의존성과 완료된 체크리스트를 정리합니다. 원래 재현의
revision과 한계를 보존하세요. 오래된 증거는 현재 동작을 입증하지 않습니다.
우선순위·크기는 라벨에, 실행 순서는 backlog tracker에 둡니다. 연구는 문서화한
결정으로 종료하며 제안한 모든 선택지를 구현하겠다는 약속이 아닙니다.

작업 가능 여부를 확인하고 시작 전에 실제 구현자를 GitHub Assignees에 지정하세요.
스스로 지정할 수 없으면 메인테이너에게 요청합니다. 기존 작업자·열린 PR과 조율하고
인계하거나 작업을 반환할 때 담당자를 갱신하세요. 검토자는 이슈 담당자일 필요가
없습니다.

## 최소 PR 검증

[CI 실행 정책](ko/CI_POLICY.md)을 따르세요. PR 스모크는 대표 검사이지 전체
스위트·커버리지 증거가 아닙니다. 관련 회귀 테스트를 로컬에서 실행하고 명령·
결과를 기록하며, 호환성상 필요하면 정확한 head의 전체 검증을 요청하세요.
