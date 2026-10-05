# SQLAlchemy 내부 API 호환성 (한국어)

> 🌐 [SA_COMPAT.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/SA_COMPAT.md)의 번역입니다. 영어 원문이 표준이며, 페이지 번역은 경고 수준의 동기화 규칙을 따릅니다.

이 문서는 `sqlalchemy-cubrid`가 사용하는 모든 SQLAlchemy 내부 또는 준비공개(semi-private)
API와 그 사용 이유, 테스트로 검증된 SQLAlchemy 버전 범위, 그리고 SQLAlchemy가 해당 API를
변경하면 무엇이 깨지는지를 추적합니다.

검증 대상: SQLAlchemy `2.0.x` 및 `2.1.x` (프로젝트 핀: `>=2.0,<2.3`).

## 내부 API 목록

| API | 위치 | 용도 | 검증됨 | 변경 시 깨지는 것 |
|---|---|---|---|---|
| `Select._for_update_arg` | `sqlalchemy_cubrid/_compat.py`, `sqlalchemy_cubrid/compiler.py` | `FOR UPDATE OF ...` 컬럼 렌더링 | 2.0, 2.1 | `FOR UPDATE` 절이 `OF` 대상을 잃거나 컴파일에 실패함 |
| `Select._limit_clause` | `sqlalchemy_cubrid/_compat.py`, `sqlalchemy_cubrid/compiler.py` | CUBRID `LIMIT offset, count` 형식 렌더링 | 2.0, 2.1 | LIMIT/OFFSET SQL 생성이 깨짐 |
| `Select._offset_clause` | `sqlalchemy_cubrid/_compat.py`, `sqlalchemy_cubrid/compiler.py` | CUBRID `LIMIT offset, count` 형식 렌더링 | 2.0, 2.1 | OFFSET SQL 생성이 깨짐 |
| `Select._distinct` | `sqlalchemy_cubrid/_compat.py`, `sqlalchemy_cubrid/compiler.py` | SELECT의 `DISTINCT` 접두사 렌더링 | 2.0, 2.1 | DISTINCT 쿼리에서 키워드가 빠짐 |
| `sqlalchemy.sql._typing._DMLTableArgument` | `sqlalchemy_cubrid/dml.py` | 사용자 정의 `insert/merge/replace` 팩토리의 타입 계약 | 2.0, 2.1 | 타입 검사와 시그니처가 어긋남. 런타임은 대개 영향 없음 |
| `sqlalchemy.sql.base._generative` | `sqlalchemy_cubrid/dml.py` | SQLAlchemy 방식의 불변 문장 체이닝 | 2.0, 2.1 | `on_duplicate_key_update()` / `MERGE` 빌더가 가변이 되거나 올바르지 않게 됨 |
| `sqlalchemy.sql.base._exclusive_against` | `sqlalchemy_cubrid/dml.py` | values 뒤에 오는 절의 중복 방지 | 2.0, 2.1 | 명확한 오류 없이 중복 ODKU 절이 만들어질 수 있음 |
| `sqlalchemy.util.typing.Self` | `sqlalchemy_cubrid/dml.py` | 플루언트 DML 메서드의 타이핑 | 2.0, 2.1 | 플루언트 API의 타이핑 회귀. 런타임은 대개 영향 없음 |
| `sqlalchemy.connectors.asyncio.AsyncAdapt_dbapi_connection` | `sqlalchemy_cubrid/aio_pycubrid_dialect.py` | pycubrid.aio용 비동기 연결 어댑터 | 2.0, 2.1 | 비동기 방언이 pycubrid 연결을 감쌀 수 없음 |
| `sqlalchemy.connectors.asyncio.AsyncAdapt_dbapi_cursor` | `sqlalchemy_cubrid/aio_pycubrid_dialect.py` | pycubrid.aio용 비동기 커서 어댑터 | 2.0, 2.1 | 비동기 커서 연산이 실패함 |
| `sqlalchemy.connectors.asyncio.AsyncAdapt_dbapi_module` | `sqlalchemy_cubrid/aio_pycubrid_dialect.py` | 비동기 DBAPI 모듈 어댑터 | 2.0, 2.1 | 비동기 엔진 생성이 실패함 |
| `sqlalchemy.util.concurrency.await_only` | `sqlalchemy_cubrid/aio_pycubrid_dialect.py` | 비동기 어댑터에서 동기 컨텍스트로부터 코루틴 실행 | 2.0, 2.1 | 비동기 연결/커서 브리징이 실패함 |

## 내부가 아닌 임포트에 대한 참고

이 프로젝트는 `sqlalchemy.sql.compiler`, `sqlalchemy.sql.elements`,
`sqlalchemy.sql.type_api` 같은 SQLAlchemy 모듈도 임포트합니다. 이들은 밑줄 접두사가
붙은 내부 API가 아니며 일반적인 방언 확장 패턴의 일부이지만, 방언이 실제로는 컴파일러
내부에 의존하기 때문에 카나리 CI에서 계속 모니터링합니다.

## 위험 요약

- 최고 위험: `Select._for_update_arg`, `Select._limit_clause`,
  `Select._offset_clause`, `Select._distinct`. SQL 컴파일에 직접 영향을 주기 때문입니다.
- 높은 위험: `sqlalchemy.connectors.asyncio` 어댑터와 `await_only`. 비동기 방언 전체가
  이들에 의존하기 때문입니다.
- 중간 위험: `_generative`와 `_exclusive_against`. 사용자 정의 DML 빌더의 동작을
  제어하기 때문입니다.
- 낮은 런타임 위험: `_DMLTableArgument`와 `Self` (대부분 타이핑 표면).

## 검증 계획

- SQLAlchemy `2.0.x`와 `2.1.x`에서 전체 오프라인 테스트를 계속 실행합니다.
- `SQLAlchemy>=2.1.0b1,<2.3`에 대해 `--pre`로 업스트림 SQLAlchemy 사전 릴리스 카나리를 실행합니다. 앞으로 나올 사전 릴리스가 일반 CI를 막지 않도록 `continue-on-error`로 유지합니다.
- 카나리가 실패하면, 공개 대안이 있는 곳에서는 직접적인 내부 API 사용을 대체하는 것을
  우선하거나 업스트림 방언 패턴에 맞춥니다.
