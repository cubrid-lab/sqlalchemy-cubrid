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
- [PR·커밋 제목](#pull-request-and-commit-titles)
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

# dev 의존성 그룹과 함께 개발 모드로 설치 (pip >= 25.1)
python -m pip install --upgrade "pip>=25.1"
pip install -e . --group dev

# pre-commit 훅 설치
pre-commit install
```

---

<a name="running-tests"></a>

## 테스트 실행

### 오프라인 테스트 (데이터베이스 불필요)

대부분의 테스트는 CUBRID 인스턴스 없이 실행됩니다:

```bash
# 모든 오프라인 테스트 실행: 빠른 테스트와 저장소 도구 테스트
make test

# 빠른 오프라인 테스트만 실행 (반복 작업 중에 쓰는 명령)
make test-fast

# 저장소 도구 테스트만 실행 (Makefile 타깃, 시그널 처리, 저장소 스크립트)
make test-repo

# 테스트를 제외한 전체 품질 게이트 실행: 린트, 포맷 검사, strict 타입 검사,
# 보안 검사와 docs-reason 검사
make check

# 전체 검증: make check, make test, 이어서 live make integration 레인 (Docker 필요)
make verify

# 특정 테스트 파일 실행
pytest test/test_compiler.py -v

# 특정 테스트 실행
pytest test/test_compiler.py::TestSelectCompilation::test_select_limit -v
```

`make test`는 `-m "not integration"`을 선택하고(`make test-offline`은 호환성을 위해 남긴
별칭입니다), `make test-fast`는 `-m "not integration and not repo"`를 선택합니다. `repo` 마커는
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
# CUBRID 시작 (기본 버전: 11.2), 127.0.0.1:33000
make docker-up                         # 또는: docker compose up -d

# 특정 CUBRID 버전으로 테스트
CUBRID_VERSION=11.4 make docker-up

# 다른 호스트 포트로 브로커 공개 (테스트 URL도 이 포트를 따라야 함)
CUBRID_TEST_PORT=33300 make docker-up

# 로그 보기
docker compose logs -f cubrid

# 컨테이너 중지 및 제거 (데이터 볼륨 유지)
make docker-down                       # docker compose down

# 중지 및 데이터 볼륨 삭제 (테스트 데이터가 모두 삭제됨)
make docker-clean                      # docker compose down -v
```

브로커는 `127.0.0.1`에만, 호스트 포트 `CUBRID_TEST_PORT`(기본값 33000)로 공개됩니다.
예전 이름인 `CUBRID_PORT`는 `CUBRID_TEST_PORT`가 없을 때 계속 동작하지만 더 이상 권장되지
않습니다(deprecated). `make docker-down`은 테스트 데이터를 남기고, `make docker-clean`만
삭제합니다(#1008 이전에는 `make docker-down`이 삭제했습니다).

`docker-compose.yml`은 `CUBRID_DB_HOST: localhost`를 설정하므로 같은 볼륨에서 컨테이너를
다시 만들어도 데이터베이스가 계속 동작합니다. 11.3까지의 이미지는 데이터베이스를
`cubrid-data` 볼륨에, 11.4는 `cubrid-databases`에 두므로 지원하는 모든 버전에서 `down`이 데이터를 남깁니다.
다른 CUBRID 버전이 만든 데이터베이스가 열린다는 보장은 없으므로 `CUBRID_VERSION`을 바꾸기 전에
`make docker-clean`(테스트 데이터 삭제)을 실행하세요. 이 설정 전에 만든 볼륨은 다시 만든 뒤 -353으로
실패합니다. 데이터를 유지하는 `make docker-fix-db-host`로 복구하세요
([문제 해결](ko/TROUBLESHOOTING.md#컨테이너를-다시-만든-뒤-데이터베이스-서버-호스트를-찾을-수-없음)).

지원되는 CUBRID 버전: `11.4`, `11.2`, `11.0`, `10.2`.

`make integration`은 이 기본 스택을 사용하지 않습니다. 고유한 이름의 자체 Compose
프로젝트를 시작하고, 그 프로젝트에 이미 컨테이너·볼륨·네트워크가 있으면 실행을
거부하며, Ctrl-C, `SIGTERM` 또는 `SIGHUP` 뒤에도 자신이 만든 것만 제거합니다
(`docker compose -p <project> down -v`). 포트 33000이 사용 중이면
`make integration CUBRID_TEST_PORT=<port>`를 사용하세요. 선택한 드라이버를 통해 서버가
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
# 동기화된 도구 설정 확인과 유지 관리하는 모든 Python 소스 경로 린트
make lint

# 같은 공유 경로의 포맷 검사 (파일을 수정하지 않음)
make format-check

# 같은 공유 경로에 수정과 포맷 적용 (파일을 수정하는 유일한 타깃)
make format

# strict 타입 검사, 또는 테스트를 제외한 전체 품질 게이트 실행
make typecheck
make check

# 필요한 도구가 고정된 버전으로 설치되어 있는지 확인
make doctor
```

`make check-all`은 한 마이너 릴리스 동안 `make check`의 폐기 예정 별칭으로 계속
동작하며 stderr에 폐기 예정 안내를 출력합니다.

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
   make test        # 저장소 도구 테스트를 포함한 모든 오프라인 테스트
   ```

4. **공유 린트, 포맷, 타입, 보안, docs-reason 검사를 실행하세요**:
   ```bash
   make check
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
  [PR·커밋 제목](#pull-request-and-commit-titles)에 설명한 대로 작성하세요.
- 관련 이슈는 제목이 아니라 PR 본문에서 참조하세요(예: `Fixes #42`).
- 변경이 공개 API에 영향을 주면 문서를 갱신하세요.
- 변경 요약을 `CHANGELOG.md`에 기록하세요.

### 검토 절차

- 모든 PR은 사람이 작성했든 OpenCode, Codex, Claude Code, ChatGPT 등
  어떤 AI 도구를 사용했든 **동일한 검토 절차**를 따릅니다. 특정 Oracle
  사전·사후 리뷰나 Copilot 리뷰를 필수로 요구하지 않습니다.
  최종 PR 헤드에서 필수 GitHub CI를 확인하고, 로컬 검사는 권장하되
  별도의 병합 조건으로 삼지 않습니다. 실행 결과와 생략 이유를 정확히
  기록하고 메인테이너가 변경 내용과 지적 사항을 확인해 병합을 결정합니다.
- CI가 통과해야 합니다(해당 린트, 오프라인·통합 테스트 등).
- 명시적으로 승인받지 않는 한 하위 호환성을 유지하세요.
- `.github/CODEOWNERS`는 릴리스, CI, 보안 정책, 다이얼렉트, 컴파일러,
  리플렉션 및 Alembic 경로의 변경에 메인테이너 리뷰를 요청합니다.
  워크플로 권한·릴리스 등 고위험 경로의 독립 검토 요건은 유지합니다.
- `agent-review`는 기존 리뷰 기록을 요약하는 **참고용** 진단이며
  병합 필수 체크나 승인 근거가 아닙니다. Oracle/Copilot 등 AI 검토도
  선택적 참고자료입니다. 자세한 사항은
  [CONTRIBUTING.md](../CONTRIBUTING.md#agent-review-evidence-gate)에 있습니다.

기여자는 `dev` 의존성 그룹을 설치하고, 공유 검사를 실행하고, 관련 문서를 갱신한 뒤
동기, 명령·결과와 실행하지 않은 검사의 이유를 담아 PR을 엽니다.
문서를 변경하면 `python scripts/generate_llms_full.py`를 실행하세요(이 명령은
`docs/llms-full.txt`를 다시 생성하고 표준 `docs/llms.txt` 인덱스를 루트
`llms.txt`에 복사합니다. `docs/llms.txt`만 편집하세요). 그리고
`mkdocs-material`과 `pymdown-extensions`가 있는 문서 환경에서 `mkdocs build --strict`를 실행하세요.
`python scripts/check_docs_links.py`는 필수 `docs-check` CI 작업처럼 깨진 로컬 링크,
앵커, 닫히지 않은 코드 펜스와 없는 명령을 보고합니다.
메인테이너는 선택적인 AI 검토, 최종 통합, 릴리스 분류, 저장소
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

<a name="repository-local-issue-ownership"></a>

## 저장소별 이슈 소유권

각 저장소는 자신의 소스·워크플로·문서를 변경하는 작업의 이슈, 담당자,
우선순위, 검증 조건과 종료 여부를 독립적으로 관리합니다. 이슈만 읽어도 해당
저장소에서 구현할 범위와 완료 기준을 알 수 있어야 합니다. 다른 저장소의 실제
기술적 의존성은 `Refs owner/repo#N`으로만 연결하고, 그 저장소의 작업을 대신
소유하거나 종료하지 마세요. 현재 저장소 이슈의 완료만 `Closes #N`으로
연결합니다. 로컬 이슈가 없는 PR은 N/A와 사유를 적을 수 있습니다. 필수
`PR title` 검사는 강조나 링크로 감싼 경우를 포함해 PR 본문, PR 제목과 커밋
메시지에서 다른 저장소 이슈의 직접 자동 종료 참조를 차단합니다. 제목과 커밋
메시지는 squash 커밋을 구성하므로 일반 텍스트로 읽으며, 병합할 때 squash
메시지를 직접 고친 내용은 검사하지 않습니다. 본문의 펜스·들여쓰기 코드 블록과
HTML 주석 블록은 Markdown 구조를 정확히 따라갈 수 있을 때만 제외하고, 확실하지
않은 부분은 검사합니다. 목록 항목·각주·인용문 안의 코드 블록과 주석 블록은
항상 검사합니다. 추적할 수 없는 펜스(목록 항목·인용문·원시 HTML 안의 펜스,
들여쓴 줄의 펜스, 펜스처럼 보이기만 하는 줄) 뒤에는 이후의 펜스와 주석을
검사합니다. 본문 문장이나 인라인 코드라도 HTML 태그를 시작할 수 있는 내용
뒤에는 이후의 주석을 검사하고, `textarea`나 `select` 같은 원시 텍스트 요소
이름 뒤에는 아무것도 제외하지 않습니다. 인라인 코드와 인라인 주석은 항상
검사합니다. 외부 기여자에게 내부 AI 도구 설치나 중복 작업을 요구하지 않습니다.

<a name="pull-request-and-commit-titles"></a>

## PR·커밋 제목

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
([PR·커밋 제목](#pull-request-and-commit-titles) 참고). 예:
`fix(reflection): ...` 또는 `docs: ...`.

제보자는 영향과 재현 방법을 설명하며, GitHub 라벨을 붙일 권한은 필요하지
**않습니다**. 메인테이너가 유형 라벨과 `priority: <value>`, `size: <value>`를
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

## `good first issue` 참여 안내

담당자가 없는 `good first issue`는 **사람이 주도하는 기여자**에게 열려 있습니다. 사람이 AI 보조 도구를 사용하더라도 작업을 직접 지휘하고 검토한다면 포함됩니다. 메인테이너의 사전 허가, GitHub Assignees 지정 권한 또는 내부 AI 도구가 없어도 작업을 시작하고 PR을 제출할 수 있습니다.

시작 전 기존 담당자·댓글·열린 PR을 확인하세요. 참여 의사를 댓글로 알리는 것은 권장하지만 필수 승인 절차도 독점 예약도 아닙니다. 이미 맡은 사람이 있거나 PR을 준비 중인 사람이 있다면 먼저 조율하세요. 스스로 담당자를 지정할 수 없는 기여자의 요청을 포함해 담당자와 라벨 변경은 메인테이너가 관리합니다.

**메인테이너가 운영하는 자율 코딩 에이전트**는 신규 기여자에게 남겨 둔 `good first issue`에 착수하기 전에 **해당 이슈에 대한 명시적 승인**과 실제 구현자의 GitHub Assignees 지정이 필요합니다. 포괄적인 백로그 정리나 릴리스 준비 요청은 승인으로 간주하지 않습니다.

기존 테스트, 문서, PR 리뷰 및 병합 요건은 그대로 적용됩니다.

## 실행 가능한 이슈 설명 유지

코딩 전에 문제, 기대 동작, 범위, 완료 기준과 검증 방법을 합의하세요. 본문은
현재 명세로 유지하고 날짜가 있는 진행 상황은 댓글에 적습니다. 메인테이너는
관련 병합·인계 뒤에 닫힌 의존성과 완료된 체크리스트를 정리합니다. 원래 재현의
revision과 한계를 보존하세요. 오래된 증거는 현재 동작을 입증하지 않습니다.
우선순위·크기는 라벨에, 실행 순서는 backlog tracker에 둡니다. 조사(research) 이슈는 문서화한
결정으로 종료하며, 제안한 모든 선택지를 구현하겠다는 암묵적 약속으로 종료하지 않습니다.

사람이 주도하는 외부 기여자(AI 보조 도구 사용 포함)는 담당자가 없는 이슈에서 작업하거나 PR을 제출할 때 사전 승인 또는 GitHub Assignees 지정 권한이 필요하지 않습니다. 작업 전 기존 담당자·댓글·열린 PR을 확인하고 중복 작업이나 인계가 필요하면 먼저 조율하세요. 참여 의사 댓글은 권장하지만 필수 허가 절차는 아닙니다.

메인테이너가 운영하는 자율 코딩 에이전트나 내부 배정 작업은 착수 전에 실제 구현자를 Assignees에 지정해야 합니다. 자율 에이전트가 `good first issue`를 맡으려면 해당 이슈에 대한 명시적 승인도 필요합니다. 담당자 변경은 메인테이너가 관리하고 기존 기여자의 작업을 존중합니다. 검토자는 이슈 담당자일 필요가 없습니다.

## 최소 PR 검증

[CI 실행 정책](ko/CI_POLICY.md)을 따르세요. PR은 95% 커버리지 기준의 전체
오프라인 스위트를 실행하지만, PR의 라이브 통합 검사는 대표 검사이지 전체 매트릭스
증거가 아닙니다. 관련 회귀 테스트를 로컬에서 실행하고 명령·
결과를 보고하며, 호환성상 필요하면 정확한 head의 전체 검증을 요청하세요.
