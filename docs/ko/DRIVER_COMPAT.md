# CUBRID-Python 드라이버 호환성 (한국어)

> 🌐 [DRIVER_COMPAT.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/DRIVER_COMPAT.md)의 번역입니다. 영어 원문이 표준이며, 페이지 번역은 경고 수준의 동기화 규칙을 따릅니다.

이 문서는 `sqlalchemy-cubrid`와 CUBRID Python 드라이버(`CUBRIDdb`), CUBRID 서버 버전 간의 테스트된 호환성 매트릭스를 설명합니다.

---

## 목차

- [드라이버 개요](#드라이버-개요)
- [버전 호환성 매트릭스](#버전-호환성-매트릭스)
- [예외 계층](#예외-계층)
- [드라이버 API 사용](#드라이버-api-사용)
- [알려진 문제](#알려진-문제)
- [설치 참고](#설치-참고)

---

## 드라이버 개요

| 속성 | 값 |
|---|---|
| PyPI 패키지 | `CUBRID-Python` |
| 임포트 이름 | `CUBRIDdb` |
| 타입 | C 확장 (CPython 전용) |
| DBAPI 수준 | DB-API 2.0 (PEP 249) |
| 파라미터 방식 | `qmark` |
| 소스 | [github.com/CUBRID/cubrid-python](https://github.com/CUBRID/cubrid-python) |

이 드라이버는 CUBRID CCI(C Client Interface) 라이브러리를 감쌉니다. 순수 Python 드라이버가 **아니며** CCI 헤더에 대한 컴파일이 필요합니다.

---

## 버전 호환성 매트릭스

### 테스트된 구성

| sqlalchemy-cubrid | CUBRID-Python 드라이버 | CUBRID 서버 | Python | 상태 |
|---|---|---|---|---|
| 0.4.0 | v11.3.0.51 | 11.4 | 3.10 – 3.14 | ✅ CI에서 테스트 |
| 0.4.0 | v11.3.0.51 | 11.2 | 3.10 – 3.14 | ✅ CI에서 테스트 |
| 0.4.0 | v11.3.0.51 | 11.0 | 3.10 – 3.14 | ✅ CI에서 테스트 |
| 0.4.0 | v11.3.0.51 | 10.2 | 3.10 – 3.14 | ✅ CI에서 테스트 |
| 0.3.x | v11.3.0.51 | 10.2 – 11.4 | 3.10 – 3.13 | ✅ 테스트됨 |

### CUBRID 서버 버전 지원

| 서버 버전 | 드라이버 버전 | 비고 |
|---|---|---|
| 11.4 | v11.3.0.51 | 최신 안정 |
| 11.2 | v11.3.0.51 | LTS 릴리스 |
| 11.0 | v11.3.0.51 | 레거시 지원 |
| 10.2 | v11.3.0.51 | 최소 지원 |
| 12.x | — | 미출시. 출시되면 테스트 예정 |

### Python 버전 지원

| Python | 상태 | 비고 |
|---|---|---|
| 3.10 | ✅ 완전 지원 | 최소 버전 |
| 3.11 | ✅ 완전 지원 | |
| 3.12 | ✅ 완전 지원 | |
| 3.13 | ✅ 완전 지원 | |
| 3.14 | 🔄 CI 매트릭스 추가됨 | 프리릴리스. 드라이버 C 확장 호환성에 따라 |

---

## 예외 계층

CUBRIDdb는 PEP 249 대비 **제한된** 예외 계층을 노출합니다:

```mermaid
graph TD
    base["BaseException"] --> exc["Exception"]
    exc --> err["CUBRIDdb.Error (Base DBAPI error)"]
    err --> iface["CUBRIDdb.InterfaceError (Driver-level errors)"]
    err --> db["CUBRIDdb.DatabaseError (Server-level errors)"]
    err --> ns["CUBRIDdb.NotSupportedError (Unsupported operations)"]
```

**누락된 PEP 249 예외** (드라이버가 제공하지 않음):
- `OperationalError` — `DatabaseError`에 흡수됨
- `ProgrammingError` — `DatabaseError`에 흡수됨
- `InternalError` — `DatabaseError`에 흡수됨
- `DataError` — `DatabaseError`에 흡수됨
- `IntegrityError` — `DatabaseError`에 흡수됨

즉, 모든 데이터베이스 수준 오류(제약 위반, 구문 오류, 연결 문제)가 `DatabaseError`로 발생합니다. `sqlalchemy-cubrid` 방언은 연결 해제 오류를 다른 실패와 구별하기 위해 **문자열 기반 메시지 매칭**을 사용합니다.

---

## 드라이버 API 사용

방언이 의존하는 드라이버 전용 API:

### 연결 메서드

| 메서드 | 용도 | 사용처 |
|---|---|---|
| `conn.ping()` | 연결 생존 확인 | `CubridDialect.do_ping()` |
| `conn.get_last_insert_id()` | auto-increment 값 조회 | `CubridExecutionContext.get_lastrowid()` |
| `conn.set_autocommit(bool)` | 오토커밋 제어 | `CubridDialect.on_connect()` |
| `conn.cursor()` | 커서 생성 | 표준 DB-API |

### 오류 코드 추출

```python
# 오류 코드는 exception.args[0]에 있음
try:
    cursor.execute("invalid sql")
except CUBRIDdb.DatabaseError as e:
    code = e.args[0]  # int 또는 str
```

방언의 `_extract_error_code()`는 정수 코드와 문자열에 박힌 코드(예: `"-21003 Cannot communicate with broker"`) 모두 처리합니다.

---

## 알려진 문제

### 1. 연결 해제 감지를 위한 `OperationalError` 없음

드라이버가 `OperationalError`를 제공하지 않으므로, 방언은 MySQL 방언처럼 `isinstance(e, dbapi.OperationalError)`를 쓸 수 없습니다. 대신:
- 알려진 연결 해제 메시지 15종에 대한 문자열 패턴 매칭
- CCI 통신 오류에 대한 숫자 오류 코드 매칭

### 2. CCI 라이브러리 의존성

드라이버는 CCI 라이브러리를 소스에서 컴파일해야 합니다. CI에서는 다음으로 처리:
```bash
git clone --branch v11.3.0.51 --depth 1 https://github.com/CUBRID/cubrid-python.git
cd cubrid-python/cci-src && mkdir build_x86_64_release && cd build_x86_64_release
cmake ../ && make -j$(nproc)
```

### 3. `cursor.lastrowid` 사용 불가

표준 DB-API의 `cursor.lastrowid` 속성이 구현되어 있지 않습니다. 방언은 `connection.get_last_insert_id()`를 대신 사용하며, `SELECT LAST_INSERT_ID()` SQL 폴백을 둡니다.

### 4. CUBRID 12.x 호환성

CUBRID 12는 아직 출시되지 않았습니다. 출시되면 드라이버와 방언을 테스트하고 CI 매트릭스를 갱신할 예정입니다. 잠재 우려:
- CCI API 변경 시 드라이버 재컴파일 필요 가능성
- 새 SQL 기능 시 컴파일러 갱신 필요 가능성
- 새 데이터 타입 시 타입 매핑 추가 필요 가능성

### 5. `NUMERIC` / `DECIMAL` 소수부 정밀도 손실

`CUBRIDdb` C-확장 드라이버는 `NUMERIC` / `DECIMAL` 값의 소수부를 DB-API 계층 *아래에서* 잘라냅니다: `15.7563`을 저장한 컬럼이 `15`로 돌아옵니다. 드라이버 내부에서 SQLAlchemy가 값을 받기 전에 자릿수가 버려지므로, 어떤 방언 result processor도 이를 복원할 수 없습니다. 이는 방언 버그가 아니라 상류 드라이버의 한계입니다.

정확한 `Decimal` 라운드트립이 필요하면 순수 파이썬 `cubrid+pycubrid://` 드라이버를 사용하세요 — 전체 정밀도로 `Decimal` 값을 네이티브 반환합니다(CUBRID 11.4에서 확인). 이것이 신규 프로젝트에 `pycubrid`를 권장하는 이유 중 하나입니다.

### 6. `BLOB` / `CLOB` 조회는 LOB 로케이터를 반환

CUBRID 10.2 및 11.4에서 실제로 검증했습니다(#485). 모든 릴리스된 드라이버에서 `BLOB` / `CLOB` 컬럼에 `bytes` / `str`을 바인딩하면 전체 값이 저장되고 `NULL`은 `None`으로 왕복됩니다. 그러나 NULL이 아닌 `BLOB` / `CLOB` 컬럼을 조회하면 `bytes` / `str` 대신 드라이버의 LOB 로케이터가 반환됩니다:

| 드라이버 URL | NULL이 아닌 `BLOB` / `CLOB` 조회 결과 |
|---|---|
| `cubrid://` (`CUBRIDdb` 11.3) | 서버 파일 로케이터 `str` (`'file:...'`) |
| `cubrid+pycubrid://` (pycubrid 1.3.2 ~ 1.7.1) | LOB 핸들 `dict` (`lob_type`, `lob_length`, `file_locator`, ...) |
| `cubrid+aiopycubrid://` (pycubrid 1.7.1) | LOB 핸들 `dict` (`None`을 포함한 `LargeBinary` / `BLOB` 값 바인딩은 #500부터 정상 동작) |

`LargeBinary` / `BLOB`의 경우 SQLAlchemy 결과 프로세서가 `TypeError`를 발생시킵니다. 내용을 읽으려면 서버에서 변환(`CLOB_TO_CHAR(col)`, `BLOB_TO_BIT(col)`)하거나, 대용량 텍스트는 `str`로 왕복되는 `sqlalchemy.Text`(CUBRID `STRING`)에 저장하세요. pycubrid의 공식 LOB 조회는 cubrid-lab/pycubrid#441에서 추적합니다. [타입](TYPES.md)도 참고하세요.

### 7. `executemany`가 `None`에 이전 행의 값을 재사용 (방언 가드)

`CUBRIDdb` 11.3.0.51(`cubrid://` 드라이버)의 `executemany()`에는 두 가지 버그가 있습니다:

- **잘못된 데이터.** `_bind_params`가 `None`을 건너뛰고 `executemany`는 문장을 한 번만 준비(prepare)합니다. 따라서 `None` 파라미터에는 이전 행에서 바인딩된 값이 그대로 남아, `[(1, 'a'), (2, None)]`이 `(2, 'a')`로 저장됩니다.
- **잘못된 rowcount.** `cursor.rowcount`가 마지막 행의 개수만 보고합니다.

SQLAlchemy를 통하면 `text()` 및 Core `UPDATE`/`DELETE` executemany가 잘못된 데이터를 저장했고, ORM의 일괄 UPDATE는 `StaleDataError`(`expected to update 3 row(s); 1 were matched`)를 발생시켰습니다. `bind_param(i, None)`이 `SystemError`를 발생시키므로 드라이버 외부에서 우회할 수도 없습니다.

**방언 가드(#502).** `CubridDialect.do_executemany`는 각 파라미터 세트를 `cursor.execute()`로 실행하고 `cursor.rowcount`를 합계로 설정합니다. 각 `execute()`가 문장을 다시 준비하므로 바인딩되지 않은 `None`은 NULL이 됩니다. 마지막 행 rowcount는 모든 문장에서 틀리므로, 가드는 `None`이 있는 행에만이 아니라 항상 적용됩니다. 가드 덕분에 `supports_sane_multi_rowcount`는 두 드라이버 모두에서 정확합니다. 대가는 일반 executemany에서 행마다 한 번의 문장 준비입니다. insertmanyvalues를 사용하는 여러 행의 Core `insert()`는 `do_execute`를 거치므로 가드를 사용하지 않습니다. 타입이 `bind_expression()`을 정의하는 컬럼이 있는 테이블에 대한 INSERT는 executemany로 대체되므로(#421) `cubrid://`에서는 행 단위 가드를 사용합니다. SQLAlchemy 없이 `CUBRIDdb`의 `cursor.executemany()`를 직접 호출하는 코드는 여전히 영향을 받습니다.

`cubrid+pycubrid://`와 `cubrid+aiopycubrid://`는 `None`을 올바르게 바인딩하고 rowcount를 합산하므로 드라이버의 한 번만 준비하는 `executemany`를 그대로 사용합니다.

수정된 `CUBRIDdb` 릴리스가 최소 지원 버전이 되면 가드를 제거합니다. CUBRID/cubrid-python에 대한 상류 보고는 아직 제출 전이며 #502에서 추적합니다.

---

## 설치 참고

순수 Python pycubrid 방언 변형은 `pycubrid>=1.3.2,<2.0`과 함께 `sqlalchemy-cubrid[pycubrid]`를 설치하세요. 그 최소 버전은 `pool_pre_ping`이 사용하는 네이티브 동기·비동기 `ping(False)` 지원에 필요합니다.

`[pycubrid]` extra는 동기·비동기 연결을 모두 지원하며, SQLAlchemy 2.0과 2.1에서
`greenlet`을 제공하는 `SQLAlchemy[asyncio]`를 포함합니다. `[dev]` extra도 비동기
테스트 import를 위해 이 브리지를 포함합니다. 기본 설치의 SQLAlchemy 의존성은
유지됩니다. pycubrid 드라이버 자체는 순수 Python이지만, 호환 wheel이 없으면
`greenlet` 설치에 빌드 도구가 필요할 수 있습니다.

### 소스에서 설치 (CI에 필요)

```bash
# 드라이버 클론
git clone --branch v11.3.0.51 --depth 1 \
  https://github.com/CUBRID/cubrid-python.git

# CCI 라이브러리 빌드
cd cubrid-python/cci-src
mkdir -p build_x86_64_release && cd build_x86_64_release
cmake ../ && make -j$(nproc)

# 설치
cd /path/to/cubrid-python
pip install .
```

### 설치 확인

```python
import CUBRIDdb
print(CUBRIDdb.__version__)  # 버전 문자열이 출력되어야 함
```

---

*참고: [연결 가이드](CONNECTION.md) · [개발 가이드](DEVELOPMENT.md) · [기능 지원](FEATURE_SUPPORT.md)*
