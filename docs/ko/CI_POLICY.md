# CI 실행 정책 (한국어)

> 🌐 [CI_POLICY.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/CI_POLICY.md)의 번역입니다. 영어 원문이 표준이며, CI가 영어 원문과의 구조 일치를 검사합니다.

일상적인 CI는 버전/OS의 전체 조합 매트릭스 대신 대표 조합을 사용합니다.

| 트리거 | 런타임 검증 |
| --- | --- |
| 문서만 변경한 PR | 문서 및 정책 검사만 수행. 런타임 스위트와 CUBRID 서버 생성 없음 |
| 일반 코드 PR | 95% 커버리지 기준을 적용한 Ubuntu/Python 3.12 전체 오프라인 스위트 하나(#742) |
| 고위험 PR | 같은 전체 오프라인 스위트와 Python 3.14/CUBRID 11.4. 필요하면 대상 레인 추가 |
| main으로의 코드 푸시 | 기존 95% 커버리지 기준을 적용한 Ubuntu/Python 3.12 전체 오프라인 스위트 하나. 최저·최신 라이브 엔드포인트 |
| 월요일 03:00 UTC | 같은 대표 정책으로 최근 7일의 변경을 비교. 변경이 없거나 문서만 바뀐 이력은 런타임 테스트를 선택하지 않음 |
| 명시적 전체 실행 또는 릴리스 | 기존 전체 Python 3.11–3.14 × CUBRID 10.2/11.0/11.2/11.4 통합 워크플로와 필수 릴리스 레인 |

PR은 푸시와 같은 전체 오프라인 선택(`-m "not integration and not repo"`)과 95%
커버리지 기준을 실행합니다. 이전의 세 파일 PR 스모크는 로컬에서 약 1초, 전체
스위트는 약 24초로, 오프라인 회귀가 main에서 처음 실패하도록 둘 만큼의 절감이
아니었습니다(#742). PR의 라이브 통합 검사는 계속 대표 검사입니다. 기여자는 자신의
변경과 관련된 회귀 검사를 로컬에서 실행하고 명령과 결과를 PR에 기록해야 합니다.
`make test`와 `make integration`은 범위 변경 없이 그대로 사용할 수 있습니다.

변경 선택은 `ci.yml`의 `detect-changes` 잡에서 이루어집니다. 문서가 아닌 경로는
기본적으로 코드로 취급하므로, 새 소스/설정 파일이 조용히 문서로 분류되지
않습니다. 연결/프로토콜/커서/비동기/호환성 또는 다이얼렉트/컴파일러/리플렉션,
의존성, 빌드, 스크립트 변경과 `ci.yml` 자체의 변경은 병합 전 대표 통합 검사를 선택하며, 그
밖의 워크플로 변경은 대신 도구 레인과 오프라인 스위트를 선택합니다([워크플로 변경
영향](#워크플로-변경-영향) 참고).
저장소 도구 테스트는 도구가 바뀔 때 Linux 한 레인에서 실행합니다.
정적 린트 잡은 생성 문서 검사를 포함해 모든 이벤트에서 계속 실행됩니다.

집계 필수 검사의 이름은 그대로 유지되며 변경 감지를 포함합니다. 선택된 잡은
성공해야 합니다. 선택된 검사가 생략·실패·취소되면 게이트가 실패합니다.
의도적으로 선택하지 않은 잡만 생략될 수 있습니다. 브랜치 보호는 집계 게이트에
걸어 두고, 매트릭스를 줄인 뒤 예전 매트릭스 셀 이름을 하나하나 필수로 두지
마세요. 병합 전에 브랜치 보호 설정을 확인해야 합니다. 보호 설정 변경은 이
PR에 포함되지 않습니다.

전체 검증에는 자동 야간 일정이 없습니다. `integration-full.yml`은 수동 실행과,
변경 불가능한 후보 SHA를 넘기는 릴리스 `workflow_call`을 유지합니다. 정확한 후보
브랜치/커밋에서 워크플로를 실행하고, PR 증거로 쓰기 전에 실행의 head SHA를
확인하세요. 브랜치가 움직였다면 새 증거가 필요합니다. 일상 CI의 수동 실행은
경로에 따라 달라지므로, 조건 없는 호환성 실행이 필요하면 전체 워크플로를
사용하세요. 릴리스 게시자/생성기는 변경하지 않습니다.

동시 실행은 이벤트와 ref별로 분리되므로 main 푸시, 주간 일정, 수동 실행이 서로를
취소할 수 없습니다. 같은 PR의 대체된 실행은 그 PR 그룹 안에서 여전히 취소됩니다.
main 푸시와 PR 병합 ref의 SHA가 같다고 가정하지 않습니다. 주간 변경 선택은 저장된
마지막 성공 캐시가 아니라 최근 7일을 사용합니다. 실패한 주간 실행은 성공한
증거로 취급하지 말고 재실행하거나 수동 검증으로 이어 가야 합니다.

GitHub 요금이 어느 워크플로나 러너 SKU에서 발생하는지는 확인되지 않았습니다.
잡 수를 줄인 것은 반복 작업이 줄었다는 뜻이지, 측정된 비용 절감이 아닙니다.
비용을 주장하기 전에 이후의 Actions 잡/러너 분과 실제 과금 범주를 비교하세요.

일상적인 타입 검사는 Python 3.13/SQLAlchemy 2.1.1을 사용하고, Alembic 검사는 최신
버전을, 패키징은 SQLAlchemy 2.1.1을 사용합니다. 최저/최신 라이브 엔드포인트 셀은
main/주간 실행에서 SQLAlchemy 2.0과 2.1 컴플라이언스 커버리지를 유지합니다. 라이브
스모크, make integration, 권고 수준의 SQLAlchemy 카나리는 PR에서 PR이 아닌 코드
검증으로 미뤄집니다.

## 워크플로 변경 영향

변경 경로 선택은 워크플로별 영향 표를 따릅니다(#746). `risk`를 통해 라이브 PR
레인(`integration-tests`, `alembic-compat`, packaging)을 선택하는 것은 이를 정의하고
실행하는 `ci.yml`뿐입니다. `.github/` 아래의 다른 워크플로는 문서가 아닌 변경이므로 전체
오프라인 스위트를 실행하고 저장소 도구 레인도 선택합니다. 둘이 합쳐 워크플로 파일을 읽는
모든 테스트를 다룹니다. `ci.yml`의 라이브 레인은 다른 워크플로의 잡을 실행하지 않으므로
이를 돌려도 검출력이 늘지 않습니다.

| 변경된 워크플로 | PR 검증 |
| --- | --- |
| `ci.yml` | 정의한 모든 레인과 도구 레인, 오프라인 스위트 |
| `integration-full.yml`, `upstream-canary.yml`, `python-canary.yml` | 도구 레인과 오프라인 스위트, 그리고 PR head에서 해당 워크플로를 수동 `workflow_dispatch`로 실행하고 PR에 링크 |
| `publish-pypi.yml`, `release-please.yml` | 도구 레인과 오프라인 스위트(릴리스 워크플로 테스트) |
| 그 밖의 워크플로 | 도구 레인과 오프라인 스위트. `pr-title.yml`, `docs-sync.yml`, `codeql.yml`, `security.yml`은 PR에서 스스로도 실행됨 |

`test/test_workflow_path_impact.py`가 모든 워크플로 파일과 대표 경로에 대해 필터를
평가하고, 워크플로 파일을 (리터럴 경로, 분할 경로, 상수로) 읽는 테스트 모듈에
`integration` 표시가 있어 그런 PR에서 실행되지 않으면 실패합니다.

## 병렬 라이브 레인

`integration-tests`, `make-integration`, `live-smoke`는 `detect-changes`에만
의존하므로(#744), lint, 타입 검사, 오프라인 테스트가 끝난 뒤가 아니라 함께
시작합니다. `matrix-result`는 여전히 모든 잡을 요구하므로 라이브 레인이 통과해도
lint, 타입, 오프라인 실패가 있으면 필수 검사는 실패합니다. 대신 lint에 실패한
PR도 라이브 레인 러너 시간을 쓸 수 있습니다.

## CUBRIDdb 드라이버 빌드 캐시

CUBRIDdb 레인은 cubrid-python v11.3.0.51을 wheel로 빌드해 캐시합니다(#745). wheel은
CCI를 정적으로 링크하고(`libcascci.a`) libc와 libstdc++만 필요하므로, 캐시 키는 러너
OS와 아키텍처, 러너 이미지(`ImageOS`), Python ABI(`SOABI`, 예: `cpython-314-x86_64-linux-gnu`),
그리고 태그가 아닌 해석된 소스 커밋입니다. CUBRID 서버 버전은 키에 포함되지 않으므로 같은
Python 버전의 서버 셀들이 wheel을 공유합니다. 적중하면 CCI 컴파일과
`build-essential`/`cmake` 설치를 건너뛰고, 적중하지 않으면 `uv build`로 wheel을 빌드해
잡이 성공하면 저장합니다. CPython은 마이너 버전 안에서 ABI를 안정적으로 유지하지만 러너
이미지마다 패치 버전이 다르므로, 키에는 패치 버전 대신 ABI를 씁니다. 빌드 절차나 툴체인이
바뀌면 `cubriddb-wheel-v` 접두사를 직접 올려야 하며, 세 곳의 빌드 절차는 동일하게
유지해야 합니다. 적중을 증거로 보지 않습니다. 매 실행이 wheel을 설치하고 `CUBRIDdb`를 import하며,
준비 확인 단계가 스위트 실행 전에 실제 서버에 연결합니다.
`test/test_workflow_cubriddb_cache.py`가 키 구성 요소와 적중 시에만 빌드를 건너뛰는지를
검증합니다.

## 잡 타임아웃

실행되는 모든 잡은 정수 `timeout-minutes`를 지정합니다(GitHub 기본값은 360분).
따라서 멈춘 컨테이너, 소켓, 드라이버 빌드, 설치가 러너를 6시간 동안 붙잡지 않고
예산 안에서 실패합니다(#741). 예산은 Actions에서 관측된 최대 실행 시간의 약
3–5배이며 하한을 둡니다. 게이트와 작은 잡은 5분, lint/type/오프라인/Alembic/카나리
잡은 10–15분, `make integration`과 업스트림 카나리 통합 잡은 20분, 라이브 통합
매트릭스는 30분(CUBRIDdb 소스 빌드와 컴플라이언스 스위트를 포함한 관측 최대 7.1분),
뮤테이션 테스트는 60분(관측 최대 18.1분)입니다. 180분 상한을 넘는 예외가 필요한
잡은 없습니다. 집계 게이트(`matrix-result`, `full-matrix-result`)는 `if: always()`와
짧은 타임아웃으로 실행됩니다. 타임아웃된 의존 잡은 성공이 아닌 결과
(`cancelled`/`failure`)로 보고되며 게이트는 이를 실패로 처리합니다.

재사용 워크플로를 호출하는 잡에는 `timeout-minutes`를 지정할 수 없습니다. 저장소
내부 피호출 워크플로(`publish-pypi.yml` → `integration-full.yml`)는 그 워크플로의
잡에서 검증합니다. 외부 소유 피호출 워크플로는 `test/test_workflow_timeouts.py`의
명시적 허용 목록입니다. `cubrid-lab/.github`의 공유 `doc-lint`, `live-smoke`(fuzz
버그 탐색에서도 사용), `codeql` 워크플로와 cookbook 스모크 테스트가 여기에
해당합니다. 이 테스트는 모든 워크플로를 파싱하여 실행 잡에 제한된 타임아웃이
없거나, 새 외부 호출자가 허용 목록에 없거나, 릴리스 게이트(`full-matrix-result`)가
성공이 아닌 의존 결과에서 실패하지 않으면 실패합니다. `matrix-result`는
`test/test_ci_policy.py`에서 검증합니다.

## 의존성 설치

`ci.yml`, `integration-full.yml`, `upstream-canary.yml`은 uv로 의존성을 설치합니다
(#743). 패키지를 설치하는 각 잡은 `actions/setup-python` 다음에 커밋 SHA로 고정한
`astral-sh/setup-uv`를 실행하고 uv 자체도 고정합니다(`version: "0.12.17"`). 그다음
`uv pip install --system`으로 그 인터프리터에 설치하고, 결과를 `uv pip freeze --system`으로
기록합니다. setup-uv에는 setup-python과 같은 `python-version` 지정(예: `"3.12"` 또는
매트릭스 값)을 넘기므로, 캐시 키에는 러너 이미지마다 달라 키 불일치를 일으키는
`uv python find`의 패치 버전 대신 잡의 Python 마이너 버전이 들어갑니다.
`pyproject.toml` 해시와 잡별 `cache-suffix`를 함께 써서 잡과 Python 버전마다 별도
캐시를 유지합니다. 같은 입력이 `UV_PYTHON`을 내보내며, `uv pip install --system`은
`PATH`에서 처음 일치하는 인터프리터, 즉 setup-python의 인터프리터를 고릅니다. 일상 CI와 카나리는 항상 캐시하고(`enable-cache: true`), 릴리스
게이트인 `integration-full.yml`은 `auto`를 사용하며, 이는 태그 푸시, `release`,
`pull_request_target`, `workflow_run` 이벤트에서만 캐시를 끕니다. 따라서 릴리스 경로
(`main` 푸시에서 실행되는 `publish-pypi.yml` 또는 복구용 수동 실행)는 여전히 캐시를
복원합니다. uv 캐시에는 내려받거나 빌드한 wheel만 들어 있고 매 실행이 같은 제약에서
다시 해석하므로, 캐시는 설치를 빠르게 할 뿐 해석된 버전을 바꿀 수 없어 안전합니다. 바뀌는 것은 설치 도구뿐입니다. 전환 전에 Python
3.12에서 `.[dev]`, `.[dev,alembic]`, `.[dev,pycubrid]`를 pip와 uv로 해석한 결과는 같은
패키지 집합이었습니다(PEP 503 이름 정규화 후 각각 73, 73, 74개). 고정된 SQLAlchemy와
pycubrid 컴플라이언스 설치는 정확한 핀을 유지하고, SQLAlchemy 프리릴리스 카나리는
`--upgrade-package SQLAlchemy --prerelease=if-necessary-or-explicit`를 사용해 pip의 업그레이드 범위(SQLAlchemy만, 의존성은 제외)를 유지하고 지정자가 요구하는 경우에만 프리릴리스를 허용합니다. 가장 오래된 셀의 SQLAlchemy 2.0 고정 단계는 고정된 버전을 기록합니다. 일반 `pip`는 그것이 목적인 곳에 남습니다. 패키징
스모크 가상 환경은 빌드된 wheel과 sdist가 최종 사용자 도구로 설치되는지 증명하고, 외부
`live-smoke` 재사용 워크플로는 자체 설치 명령을 받습니다. `test/test_workflow_installs.py`가
이를 검증합니다.

## Python 3.15 프리뷰 준비

`python-canary.yml`은 수동 전용입니다. 전체 SHA를 전달하고 그 커밋의 브랜치에서
실행하세요. Ubuntu/표준 GIL 레인 하나가 프리릴리스를 허용해 Python 3.15를
선택하고, 실제 인터프리터/의존성 버전을 출력하며, 전체 오프라인 회귀 검사를
실행하고 새로 설치한 wheel/sdist를 검증합니다. 설정/설치/테스트 실패는 평소처럼
실행을 실패시킵니다. 이 레인은 필수 PR 검사나 릴리스 게이트와 분리되어 있으며,
새 일정, PR 매트릭스 셀, CUBRID 서버 생성이 없습니다. 이 레인만으로는 공식 지원,
라이브 데이터베이스 호환성, free-threaded 호환성이 성립하지 않습니다.

GitHub는 수동 워크플로의 파일이 기본 브랜치에 있어야만 실행하므로, 이 레인은
병합되기 전에는 실행할 수 없습니다. 첫 실행은 병합된 커밋에서 이루어지고 추적
이슈에 기록됩니다. 일반 PR CI는 Python 3.15의 증거가 아닙니다.
