# CI 실행 정책 (한국어)

> 🌐 [CI_POLICY.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/CI_POLICY.md)의 번역입니다. 영어 원문이 표준이며, CI가 영어 원문과의 구조 일치를 검사합니다.

일상적인 CI는 버전/OS의 전체 조합 매트릭스 대신 대표 조합을 사용합니다.

| 트리거 | 런타임 검증 |
| --- | --- |
| 문서만 변경한 PR | 문서 및 정책 검사만 수행. 런타임 스위트와 CUBRID 서버 생성 없음 |
| 일반 코드 PR | 95% 커버리지 기준을 적용한 Ubuntu/Python 3.12 전체 오프라인 스위트 하나(#742) |
| 고위험 PR | 같은 전체 오프라인 스위트와 Python 3.14/CUBRID 11.4. 필요하면 대상 레인 추가 |
| main으로의 코드 푸시 | 기존 95% 커버리지 기준을 적용한 Ubuntu 전체 오프라인 스위트를 지원하는 가장 오래된·최신 Python(3.11, 3.14)에서 실행(#734). 최저·최신 라이브 엔드포인트 |
| 월요일 03:00 UTC | main 푸시와 같은 정책(Python 3.11/3.14 오프라인 셀 포함)으로 최근 7일의 변경을 비교. 변경이 없거나 문서만 바뀐 이력은 런타임 테스트를 선택하지 않음. 권고용 SQLAlchemy 프리릴리스 카나리와 가장 오래된 셀의 권고용 CUBRIDdb 컴플라이언스는 푸시가 아니라 여기서 실행하며, 컴플라이언스 단계는 최근 7일에 코드 변경이 있어야 실행(#737) |
| 명시적 전체 실행 또는 릴리스 | 기존 전체 Python 3.11–3.14 × CUBRID 10.2/11.0/11.2/11.4 통합 워크플로와 필수 릴리스 레인, 그리고 Python 3.11/3.14 오프라인 셀, 타입 검사, `alembic-compat`, 패키징 스모크 테스트, 차단 SQLAlchemy 컴플라이언스 레인(#737) |

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
main/주간 실행에서 SQLAlchemy 2.0과 2.1 컴플라이언스 커버리지를 유지합니다. make
integration은 PR에서 PR이 아닌 코드 검증으로 미뤄지며 예전 라이브 스모크의 단언도
담당합니다. 권고 수준의 SQLAlchemy 카나리는 주간 일정과 수동 실행에서 실행됩니다(#737).

## 이벤트 계층과 비용 근거

#737은 비용이 큰 워크플로 이벤트마다 목적을 하나씩 둡니다. PR은 빠르고 대표적인
검사를 유지하고, `main` 푸시는 엔드포인트 증거를 담당하고 주간 일정은 카나리도 담당하며,
릴리스는 전체 매트릭스를 실행하고 실패 시 닫힌 상태로 실패합니다(fail closed).
통합 정리에서는 같은 SHA의 다른 레인이 이미 같은 단언을 하는 레인, 또는 아무것도
차단하지 않는 권고 레인만 제거했습니다.

### 측정

이 변경 전인 2026-10-09에 GitHub REST API(`actions/runs`, `runs/{id}/jobs`)로
측정했습니다. 러너 분은 실행된 각 잡의 `completed_at - started_at` 합계이며,
"올림"은 GitHub의 계량 단위대로 잡마다 분 단위로 올린 값입니다. 이 저장소는 공개
저장소이고 표준 GitHub 호스트 러너를 쓰므로 러너 분은 청구 금액이 아닙니다. 실패
수율은 실패한 실행을 셉니다. 취소된 실행은 따로 적었는데, 표본의 취소는 모두 같은
동시성 그룹의 더 새로운 실행에 의해 대체된 것이지 결함이 아니었기 때문입니다.
표본은 범주별로 가장 최근에 완료된 실행이며, 10월 초에 워크플로 구조가 자주 바뀌어
기간이 짧습니다.

| 범주 | 기간(실행 수) | 잡 수 중앙값 | 러너 분 중앙값 | 올림 분 중앙값 | 경과 분 중앙값 | 실패 / 취소 |
| --- | --- | --- | --- | --- | --- | --- |
| 문서만 변경한 PR | 2026-10-03..09 (15) | 7 | 1.0 | 7 | 0.6 | 0 / 0 |
| 일반 코드 PR | 2026-10-03..06 (16) | 9 | 1.9 | 9 | 0.8 | 0 / 0 |
| 고위험 PR | 2026-10-08..09 (20) | 13 | 10.2 | 19 | 6.2 | 1 (lint) / 5 |
| main 코드 푸시 | 2026-10-05..09 (20) | 17 | 19.3 | 29.5 | 6.6 | 0 / 4 |
| 주간 `ci.yml` 일정 | 2026-10-05 (1) | 17 | 21.2 | 32 | 7.3 | 0 / 0 |
| 업스트림 pycubrid 카나리 | 2026-08-10..10-08 (19) | 2 | 1.9 | 4 | 1.2 | 카나리 잡 3개(드리프트, 보고됨) / 0 |
| 릴리스(`publish-pypi.yml`과 `integration-full.yml`) | 2026-10-04..09 (2) | 35 | 82.4 | 103.5 | 14.2 | 1 (cookbook 검증) / 0 |
| `integration-full.yml` 수동 실행 | 2026-09-27..10-08 (8) | 24 | 73.4 | 85.5 | 8.0 | 0 / 0 |

2026-10-01부터 2026-10-09까지 `main`으로의 코드 푸시 72건("코드 푸시"는 `offline-tests` 또는
`typecheck`가 실행된 `main` 푸시 실행이며, 전체 푸시는 84건) 중 47건이 성공하고 9건이
실패하고 16건이 취소되었습니다. 실패(모두 2026-10-03)는 모두 같은 실행에서 `offline-tests`와
`sqlalchemy-21-canary`가 함께 실패한 것이며, `live-smoke`, `make-integration`,
`integration-tests`는 푸시에서 한 번도 실패하지 않았습니다. 2026-09-25부터 2026-10-09까지 PR이 아닌 모든 `ci.yml` 실행(모든 시도)에서
`sqlalchemy-21-canary`의 실패 9건(모두 2026-10-03)은 모두 `offline-tests (3.12)` 실패와 겹쳤으므로, 이
카나리는 푸시에서 독립적인 신호를 더하지 않았습니다.

코드 푸시에서의 잡별 러너 분 중앙값: `integration-tests` 셀당 5.3, `make integration`
2.1, `repo-tests` 1.6, `live-smoke` 1.3, `offline-tests` 셀당 0.7–0.8,
`sqlalchemy-21-canary` 0.6, 패키징 0.5, `alembic-compat` 0.5, 타입 검사 0.4, lint 0.4.
가장 오래된 `integration-tests` 셀의 권고용 CUBRIDdb 컴플라이언스 단계는 중앙값 34초가
걸립니다.

### 커버리지 소유

| 커버리지 | 소유(워크플로 / 잡) | 이벤트 계층 |
| --- | --- | --- |
| 오프라인 스위트, 95% 기준 | `ci.yml` `offline-tests`, `integration-full.yml` `offline-endpoints` | PR: Python 3.12. main 푸시, 주간, 수동 실행: 3.11과 3.14. 릴리스: 3.11과 3.14 |
| 타입 검사 | `ci.yml` `typecheck`(Python 3.13, SQLAlchemy 2.1.1), `integration-full.yml` `typecheck`(같은 셀) | 모든 코드 이벤트, 수동 실행과 릴리스 |
| Alembic 호환성 | `ci.yml` `alembic-compat`(최신 Alembic), `integration-full.yml` `alembic-compat`(같은 셀), `offline-tests`의 오프라인 Alembic 테스트, `integration-tests`·`make-integration`·`integration-full`의 라이브 Alembic 연산, `integration-tests`와 `integration-full`의 트랜잭션 DDL | 고위험 PR과 PR이 아닌 코드 이벤트, 수동 실행과 릴리스 |
| 패키징 | `ci.yml` `packaging-smoke-test`, `integration-full.yml` `packaging-smoke-test`(pycubrid extra와 Alembic 검사를 포함한 같은 단계), `publish-pypi.yml` `build` | 고위험 PR과 PR이 아닌 코드 이벤트, 수동 실행과 릴리스 |
| 대표 라이브 스모크 | `live-smoke`를 흡수한 `ci.yml` `make-integration`(pycubrid, CUBRID 11.4, Python 3.12) | main 푸시, 주간, 수동 실행 |
| `make integration` | `ci.yml` `make-integration`, `integration-full.yml` `make-integration`(두 드라이버, CUBRID 10.2와 11.4) | PR이 아닌 코드 이벤트, 수동 실행과 릴리스 |
| CUBRID/Python 엔드포인트 | `ci.yml` `integration-tests`(고위험 PR은 3.14/11.4, PR이 아닌 코드 이벤트는 3.11/10.2 추가), `integration-full.yml` `integration-full`(4 × 4) | 고위험 PR, PR이 아닌 코드 이벤트, 수동 실행과 릴리스 |
| SQLAlchemy 다이얼렉트 컴플라이언스(차단) | `ci.yml` `integration-tests`: 3.14/11.4의 CUBRIDdb 레인, 두 셀의 릴리스된 pycubrid 레인, `integration-full.yml` `sqlalchemy-compliance`(같은 두 셀의 같은 레인) | 고위험 PR(3.14/11.4), PR이 아닌 코드 이벤트(두 셀), 수동 실행과 릴리스(두 셀) |
| 가장 오래된 셀의 CUBRIDdb SQLAlchemy 컴플라이언스(권고) | `ci.yml` `integration-tests`(3.11/10.2) | 최근 7일에 코드 변경이 있는 주간 실행, 코드 수동 실행 |
| SQLAlchemy 프리릴리스 카나리(권고) | `ci.yml` `sqlalchemy-21-canary` | 주간 일정과 수동 실행 |
| pycubrid 업스트림 카나리(권고, 보고) | `upstream-canary.yml` | 목요일 06:00 UTC와 수동 실행 |
| 드라이버 차등 비교 | `ci.yml` `integration-tests`, `integration-full.yml` `integration-full` | 고위험 PR, PR이 아닌 코드 이벤트, 수동 실행과 릴리스 |
| CUBRID 버전 차등 비교 | `integration-full.yml` `version-differential` | 수동 실행과 릴리스 |
| 퍼즈와 메타모픽 | `make integration` 안의 `dev` 프로필, `integration-full.yml` `fuzz-bug-hunt`의 `nightly` 프로필 | PR이 아닌 코드 이벤트, 수동 실행과 릴리스 |
| 뮤테이션 테스트(비차단) | `integration-full.yml` `mutation-testing` | 수동 실행과 릴리스(#747) |

### 통합 정리

- `ci.yml`에서 `live-smoke`를 제거했습니다. 이 레인은 Python 3.12, CUBRID 11.4,
  `cubrid+pycubrid://`로 `test/test_integration.py`와 `test/test_regression.py`를
  실행했습니다. 두 파일 모두 `integration` 표시가 있으므로, 같은 SHA의
  `make-integration`이 같은 Python, 서버 버전, URL로 그 테스트를 모두 실행합니다. 그
  환경은 패키지의 상위 집합(Alembic을 포함하는 `.[dev,pycubrid]`)을 설치하고 더 엄격한
  `check_not_all_skipped` 가드를 씁니다. 잃는 단언은 없습니다. 제거된 잡은 dev extra 없이 `.[pycubrid,alembic] pytest`만
  설치했고 `make-integration`은 `.[dev,pycubrid]`를 쓰지만, `packaging-smoke-test`가
  최소 설치에서 패키지 임포트를 확인할 뿐 dev 전용 패키지 없이 스모크 테스트를
  실행하는 것은 검증하지 않습니다. 이 절충은 수용합니다. `integration-tests`는
  유지합니다. CUBRIDdb 레인, 컴플라이언스 스위트, 드라이버 차등 비교, 트랜잭션 DDL,
  서버 재시작 단계는 이 잡에만 있습니다.
- `sqlalchemy-21-canary`는 변경 내용과 관계없이 주간 일정과 수동 실행에서만 실행되며
  `continue-on-error`를 유지합니다. 이 카나리는 이 저장소의 커밋과 무관하게 바뀌는
  업스트림 SQLAlchemy 프리릴리스를 감시하며, 표본에서 `offline-tests`가 이미 보고하지
  않은 실패를 더한 적이 없습니다.
- 가장 오래된 `integration-tests` 셀(Python 3.11, CUBRID 10.2)의 권고용 CUBRIDdb
  컴플라이언스 단계는 코드 변경이 필요한 `integration-tests` 안에서 실행되므로, 최근 7일에 코드 변경이 있는 주간 실행과 코드 수동 실행에서만 실행됩니다. `continue-on-error`이므로
  푸시를 차단한 적이 없고, 같은 셀의 차단용 릴리스된 pycubrid 컴플라이언스 레인은
  여전히 모든 코드 푸시에서 실행됩니다.
- `upstream-canary.yml`은 월요일 `ci.yml` 일정과 겹치지 않도록 월요일 06:00 UTC에서
  목요일 06:00 UTC로 옮겼습니다. 이 잡은 `pycubrid@main`을 설치하므로 주간 `ci.yml`
  스위트와 다르며, 둘 다 유지합니다.
- PR은 바뀌지 않습니다. 일반 PR은 여전히 Python 3.12 오프라인 셀 하나만 실행하고 라이브
  레인은 없으며, #734의 3.11/3.14 셀은 PR에서 실행되지 않습니다.

위의 잡별 중앙값으로 계산한 예상 러너 분:

| 범주 | 잡 수 전 → 후 | 러너 분 전 → 후 | 올림 분 전 → 후 |
| --- | --- | --- | --- |
| 일반 코드 PR | 9 → 9 | 1.9 → 1.9 | 9 → 9 |
| 고위험 PR | 13 → 13 | 10.2 → 10.2 | 19 → 19 |
| main 코드 푸시 | 17 → 15 | 19.3 → 약 16.8 | 29.5 → 약 26 |
| 주간 `ci.yml` 일정 | 17 → 16 | 21.2 → 약 19.8 | 32 → 약 30 |
| 업스트림 pycubrid 카나리 | 2 → 2 | 1.9 → 1.9 | 4 → 4 |
| 릴리스 | 35 → 37 | 82.4 → 약 83.9 | 103.5 → 약 105.5 |

코드 변경이 없는 주간 실행도 이제 이전에는 실행하지 않던 SQLAlchemy 카나리에 약 0.8
러너 분을 씁니다. 이 값은 측정이 아닌 예상치이므로, 절감을 주장하기 전에 이후 몇 주의
Actions 데이터와 비교하세요.

### 릴리스 증거

릴리스 커밋은 `main` 커밋이며, 그 `ci.yml` 푸시 실행이 Python 3.11/3.14 오프라인
증거(#734)의 유일한 출처였습니다. 릴리스 경로는 그 실행의 성공을 요구하지 않았고,
이후 병합이 푸시 동시성 그룹을 통해 그 실행을 취소할 수 있었습니다. 이제
`integration-full.yml`이 정확한 릴리스 SHA에서 같은 두 셀을 `offline-endpoints`로
실행하고, `full-matrix-result`는 그 셀이 성공하지 않으면 실패합니다. 릴리스마다 약 1.5
러너 분이 반복됩니다. 대신 푸시 실행을 요구하려면 (적어도 그만큼 러너를 붙잡는) 폴링
잡, cubrid-lab 저장소 사이에서 동일하게 유지하는 릴리스 워크플로의 `actions: read`
권한, 그리고 취소되지 않는 푸시 실행이 필요했고, 마지막 것은 위에서 측정한 대체된
취소된 실행 16건을 끝까지 실행하게 했을 것입니다.

같은 이유가 이제 나머지 `main` 푸시 증거에도 적용됩니다(#737, 옵션 b).
`integration-full.yml`은 `ci.yml` `typecheck`, `alembic-compat`,
`packaging-smoke-test`(pycubrid extra 및 Alembic 검사 포함)의 사본과
`sqlalchemy-compliance` 잡도 실행합니다. 이 잡은 Python 3.14/CUBRID 11.4에서 차단
CUBRIDdb 레인을, 3.14/11.4와 3.11/10.2 두 셀에서 차단 릴리스된 pycubrid 레인을
실행하며, 각 레인은 `test/known_failures.txt` 기준선을 캡처한 SQLAlchemy 버전에
고정됩니다. 이 잡들은 릴리스 SHA를 체크아웃하고, 변경 경로로 선택되지 않으며, 모든
`integration-full.yml` 실행(수동 실행과 릴리스 호출)에서 실행됩니다.
`full-matrix-result`는 이들을 `needs`에 두고 각각이 성공하지 않으면 실패하므로,
실패·취소·건너뜀 레인은 호출된 워크플로를 필요로 하는 `publish-pypi.yml`의 `build`와
`publish` 잡을 막습니다. 가장 오래된 셀의 권고용 CUBRIDdb 컴플라이언스 레인은 아무것도
차단하지 않으므로 반복하지 않습니다. `publish-pypi.yml`은 바뀌지 않습니다. 이 워크플로는
cubrid-lab 저장소 사이에서 동일하게 유지되며, 이 때문에 옵션 (a)(`actions: read`와
필수 `ci.yml` 푸시 실행)를 채택하지 않았습니다. 사본은 릴리스마다 짧은 잡 세 개(위의
중앙값으로 약 1.4 러너 분)와 라이브 컴플라이언스 셀 두 개를 추가하며,
`test/test_ci_policy.py`가 그 단계를 `ci.yml` 원본과 같게 유지합니다.

## 오프라인 Python 엔드포인트

`offline-tests` 매트릭스는 `github.event_name`으로 선택됩니다(#734). PR은 일반이든
고위험이든 대표 Python 3.12 셀 하나를 실행합니다. 그 밖의 모든 `ci.yml` 이벤트
(`main` 푸시, 월요일 일정, 수동 `workflow_dispatch`)는 3.12 대신 지원하는 가장
오래된 Python과 최신 Python인 3.11과 3.14를 실행합니다. 그 사이의 지원 범위는 이
엔드포인트와 PR의 3.12 증거로 다루며, 3.13에는 일상 오프라인 셀이 없습니다. 두 종류의
실행 모두 같은 선택(`-m "not integration and not repo"`), 95% 커버리지 기준,
`detect-changes`의 `code` 출력을 사용합니다. 문서만 바뀐 푸시나 코드 변경이 없는 주에는
오프라인 셀을 하나도 선택하지 않습니다. `main`에서의 `workflow_dispatch`는 비교할 이전
푸시가 없어 `paths-filter`가 마지막 커밋만으로 셀을 고르므로, 문서만 바뀐 병합 직후에
수동 실행하면 오프라인 셀이 실행되지 않습니다. 각 셀은 자체 `coverage-report-py<version>`
아티팩트를 올리므로 셀끼리 이름이 충돌하지 않습니다.

| 이벤트 | `offline-tests` 셀 |
| --- | --- |
| `pull_request` | Python 3.12 |
| `main` `push`, `schedule`, `workflow_dispatch` | Python 3.11과 3.14 |

매트릭스는 `fail-fast: false`를 사용하므로 한 인터프리터가 실패해도 다른 쪽의 증거가
취소되지 않습니다. `matrix-result`는 잡의 집계 결과를 읽습니다. 실패하거나 취소된 셀이
있으면 결과가 성공이 아니게 되고, `code`가 선택됐는데 생략되면 예상치 못한 결과이므로
어느 경우든 필수 게이트가 실패합니다. 예전의 3.12 단일 셀과 비교하면 코드 푸시나 주간
실행마다 비슷한 길이의 오프라인 잡이 하나 늘고(잡 예산은 15분), PR은 바뀌지 않습니다.
`integration-full.yml`은 릴리스 SHA에서 같은 두 셀을 `offline-endpoints`로 실행하고,
`full-matrix-result`가 이를 요구합니다(#737, [릴리스 증거](#릴리스-증거) 참고). 저장소 도구 레인은
대표 Python 3.12 셀에 그대로 둡니다. `test/test_ci_policy.py`는 이벤트별로 매트릭스를
계산하고, 실패·취소·생략된 오프라인 결과로 게이트를 실행해 봅니다.

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

`integration-tests`와 `make-integration`은 `detect-changes`에만
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
명시적 허용 목록입니다. `cubrid-lab/.github`의 공유 `doc-lint`, `live-smoke`(`integration-full.yml`의 fuzz
버그 탐색에서 사용), `codeql` 워크플로와 cookbook 스모크 테스트가 여기에
해당합니다. 이 테스트는 모든 워크플로를 파싱하여 실행 잡에 제한된 타임아웃이
없거나, 새 외부 호출자가 허용 목록에 없거나, 릴리스 게이트(`full-matrix-result`)가
성공이 아닌 의존 결과에서 실패하지 않으면 실패합니다. `matrix-result`는
`test/test_ci_policy.py`에서 검증합니다.

## 문서 도구, 스캔 동시성, pycubrid 하한

- **문서 도구 고정 (#761).** `docs.yml`과 `ci.yml`의 `docs-build` 작업(아래 참고)이
  `mkdocs build --strict`를 실행하며, `docs.yml`은 `mkdocs`, `mkdocs-material`, `pymdown-extensions`를 정확한 버전이 고정된
  `.github/docs-requirements/requirements.txt`에서 설치합니다. `/.github/docs-requirements`용
  Dependabot `pip` 항목이 업데이트를 제안하므로, 업스트림 릴리스가 저장소 변경 없이
  엄격 빌드를 깨뜨릴 수 없습니다.
- **풀 리퀘스트의 문서 사이트 빌드 (#786).** `ci.yml`이 병합 전에 사이트를 빌드하므로,
  `mkdocs build --strict`를 깨뜨리는 문서 수정이나 문서 도구 버전 갱신은 나중에 `main`이
  아니라 풀 리퀘스트에서 실패합니다. `docs-build` 작업은 `site` 경로 필터로 선택됩니다:
  `docs/**`(콘텐츠, 번역, 자산), `mkdocs.yml`, `scripts/generate_llms_full.py`,
  `.github/docs-requirements/**`, `.github/workflows/docs.yml`,
  `.github/workflows/ci.yml`. 루트 `*.md` 파일은 사이트 입력이 아니므로 이 작업을
  선택하지 않으며, `workflow_dispatch`는 다른 레인처럼 이 작업을 강제로 선택합니다.
  이 작업은 `docs.yml`의 빌드 단계(고정된 uv로 `.github/docs-requirements/requirements.txt`
  설치, `scripts/generate_llms_full.py`, `mkdocs build --strict`)를 읽기 전용 권한, 고정된
  액션, 10분 타임아웃, `persist-credentials: false`로 실행하며 Pages 아티팩트를 올리거나
  배포하지 않습니다. `matrix-result` 게이트는 `site`가 선택된 경우에만 `docs-build`의
  성공을 요구하고 그 외에는 건너뜀을 허용합니다. `test/test_ci_policy.py`,
  `test/test_workflow_path_impact.py`, `test/test_workflow_hygiene.py`가 이를 검증합니다.
- **스캔 동시성 (#762).** `codeql.yml`과 `security.yml`은 그룹
  `${{ github.workflow }}-${{ github.event_name == 'pull_request' && github.ref || github.run_id }}`,
  `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`로 `concurrency`를
  설정합니다. 풀 리퀘스트에서는 새 푸시가 이전 스캔을 취소하지만, 그 외 이벤트는 실행마다 고유한 그룹을 받습니다(같은 그룹에서는
  `cancel-in-progress`가 없어도 대기 중인 실행이 대체됨). 따라서 main 푸시와 주간
  예약 실행은 취소되거나 누락되지 않습니다. 스캔 범위는 바뀌지 않습니다.
- **선언된 pycubrid 하한 (#764).** `pyproject.toml`은 `pycubrid>=1.8.0,<2.0`을 선언하고,
  `ci.yml`의 게이트 컴플라이언스 레인은 `pycubrid==1.8.0`을 설치합니다(통합 잡은 최신
  릴리스를 설치하므로 하한을 검증하는 유일한 레인). `test/test_workflow_hygiene.py`는 고정
  버전과 선언된 하한이 다르면 실패하므로, 추가 CI 잡 없이 한쪽만 올리는 변경을 오프라인에서
  잡아냅니다.
- **표현 (#747).** `integration-full.yml`에는 일정이 없습니다. `fuzz-bug-hunt`와
  `mutation-testing` 잡 이름에서 "nightly"를 뺐습니다(`nightly`는 Hypothesis 프로파일
  이름으로 유지). 게이트 동작은 그대로입니다. 퍼즈는 릴리스를 게이트하고 뮤테이션
  테스트는 비차단입니다. 필수 상태 검사는 이 잡 이름을 참조하지 않습니다.

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
`--upgrade-package SQLAlchemy --prerelease=if-necessary-or-explicit`로 SQLAlchemy만 업그레이드하도록 요청합니다. 이 옵션은 최신 SQLAlchemy 프리릴리스 설치를 보장하지 않으며, 안정 버전 2.1.x가 2.2 베타보다 우선 선택될 수 있습니다. #778에서 실제 공개된 2.2 프리릴리스를 대상으로 설치 버전을 검증할 예정이며, 검증 전까지 카나리 성공을 2.2 호환성 증거로 해석하지 않습니다. 가장 오래된 셀의 SQLAlchemy 2.0 고정 단계는 고정된 버전을 기록합니다. 일반 `pip`는 그것이 목적인 곳에 남습니다. 패키징
스모크 가상 환경은 빌드된 wheel과 sdist가 최종 사용자 도구로 설치되는지 증명하고, 외부
`live-smoke` 재사용 워크플로는 자체 설치 명령을 받습니다. `test/test_workflow_installs.py`가
이를 검증합니다.

## Dependabot 그룹

이전에는 Dependabot이 pip(`/`), pip(`/.github/docs-requirements`), GitHub Actions의
패키지마다 PR을 하나씩 열었고, PR마다 PR 계층 검사가 실행되었습니다. 이제
`.github/dependabot.yml`은 minor와 patch 버전 업데이트를 생태계와 디렉터리별로 PR 하나에
묶으므로(`dev-tools`, `docs-tools`, `github-actions`), 주간 업데이트 묶음은 그룹당 CI 실행
한 번으로 끝납니다(#737). 다음은 여전히 별도 PR로 열립니다.

- **Major 업데이트**는 모든 그룹에서 제외되며(`update-types`는 `minor`와 `patch`뿐),
  `dependabot-auto-merge.yml`은 여전히 사람의 리뷰를 위해 보류합니다.
- **보안 업데이트**는 그룹이 `applies-to: version-updates`로 설정되어 있어 분리됩니다.
- **SQLAlchemy, pycubrid, Alembic, CUBRID-Python**은 `dev-tools`에서 제외됩니다. 이들은
  도구 업데이트와 호환성 위험이 다르므로 업데이트마다 따로 리뷰할 수 있어야 합니다.

그룹은 아무것도 우회하지 않습니다. 그룹 PR도 같은 필수 체크를 거치며, 체크가 통과해야
자동 병합이 완료됩니다. `dependabot/fetch-metadata`는 그룹 PR의 `update-type`으로 가장
높은 semver 변경을 보고하므로, 그룹이 major 업데이트를 자동 병합으로 가져갈 수 없습니다.
패키지 하나가 실패하면 그룹 전체가 막힙니다. 그룹 PR에서 고치거나, 별도 작업이 필요하면
리뷰된 PR로 해당 패키지를 그룹의 `exclude-patterns`에 추가해 Dependabot이 단독 PR로 열게
하세요. `test/test_workflow_hygiene.py`가 그룹 설정을 검증합니다.

## Python 3.15 검증 준비

`python-canary.yml`은 수동 전용입니다. 전체 SHA를 전달하고 그 커밋의 브랜치에서
실행하세요. Ubuntu/표준 GIL 레인 하나가 Python 3.15를 선택하며 (선택기는 프리릴리스도 허용),
실제 인터프리터/의존성 버전을 출력하며, 전체 오프라인 회귀 검사를
실행하고 새로 설치한 wheel/sdist를 검증합니다. 설정/설치/테스트 실패는 평소처럼
실행을 실패시킵니다. 이 레인은 필수 PR 검사나 릴리스 게이트와 분리되어 있으며,
새 일정, PR 매트릭스 셀, CUBRID 서버 생성이 없습니다. 이 레인만으로는 공식 지원,
라이브 데이터베이스 호환성, free-threaded 호환성이 성립하지 않습니다.

GitHub는 수동 워크플로의 파일이 기본 브랜치에 있어야만 실행하므로, 이 레인은
병합되기 전에는 실행할 수 없습니다. 첫 실행은 병합된 커밋에서 이루어지고 추적
이슈에 기록됩니다. 일반 PR CI는 Python 3.15의 증거가 아닙니다.
