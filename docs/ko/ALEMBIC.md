# Alembic 마이그레이션 지원 (한국어)

> 🌐 [ALEMBIC.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/ALEMBIC.md)의 번역입니다. 영어 원문이 표준이며, CI가 영어 원문과의 구조 일치를 검사합니다.

CUBRID 방언과 함께 [Alembic](https://alembic.sqlalchemy.org/) 데이터베이스 마이그레이션을 사용하는 가이드.

---

## 목차

- [설치](#설치)
- [구성](#구성)
- [마이그레이션 실행](#마이그레이션-실행)
- [CUBRID 전용 동작](#cubrid-전용-동작)
- [한계와 회피](#한계와-회피)
- [예제](#예제)
- [문제 해결](#문제-해결)

---

## 설치

`alembic` extra와 함께 sqlalchemy-cubrid를 설치하세요:

```bash
pip install sqlalchemy-cubrid[alembic]
```

이것은 의존성으로 Alembic ≥ 1.7.2를 끌어옵니다. CUBRID Alembic 구현(`CubridImpl`)은 CUBRID 방언이 로드될 때 자동 등록됩니다 — 수동 구성이 필요 없습니다.

> **참고**: Alembic을 따로 설치해도(`pip install alembic`), 같은 환경에 `sqlalchemy-cubrid`가 설치되어 있으면 CUBRID 구현이 그대로 등록됩니다.

---

## 구성

### Alembic 초기화

```bash
alembic init alembic
```

`alembic/` 디렉터리와 `alembic.ini` 구성 파일이 생성됩니다.

### 데이터베이스 URL 설정

`alembic.ini`를 편집하세요:

```ini
[alembic]
sqlalchemy.url = cubrid://dba:password@localhost:33000/demodb
```

또는 `alembic/env.py`에서 동적으로 설정:

```python
from sqlalchemy import create_engine

def run_migrations_online():
    connectable = create_engine("cubrid://dba:password@localhost:33000/demodb")

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()
```

### env.py 설정

어떤 CUBRID URL이든 방언을 로드하는 순간 `CubridImpl` 클래스가 등록되므로 `env.py`에 CUBRID 임포트가 필요 없습니다. 시작할 템플릿은 드라이버에 따라 다릅니다:

- **동기 URL** (`cubrid://`, `cubrid+cubriddb://`, `cubrid+pycubrid://`): `alembic init`이 만든 표준 `env.py`가 수정 없이 동작합니다.
- **비동기 URL** (`cubrid+aiopycubrid://`): Alembic의 async 템플릿(`alembic init -t async <dir>`)을 사용하세요. 생성된 `env.py`도 수정 없이 동작합니다. 표준 템플릿의 온라인 경로는 동기 `engine_from_config()`를 호출하므로 비동기 드라이버를 구동할 수 없고 `sqlalchemy.exc.MissingGreenlet`으로 실패합니다. 오프라인 `--sql` 모드는 두 템플릿 모두 동작합니다. CUBRID 11.4에서 Alembic 1.7.2와 1.20.0으로 수정하지 않은 async 템플릿 `env.py`를 통한 `upgrade head` / `downgrade base`를 검증했습니다(`test/test_alembic_registration.py`).

온라인 마이그레이션을 위한 최소 `env.py`:

```python
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

# 모델의 메타데이터 임포트
from myapp.models import Base

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
```

---

## 마이그레이션 실행

### 마이그레이션 생성

```bash
# 모델 변경에서 자동 생성
alembic revision --autogenerate -m "add users table"

# 빈 마이그레이션 생성
alembic revision -m "custom migration"
```

### 마이그레이션 적용

```bash
# 최신 버전으로 업그레이드
alembic upgrade head

# 특정 리비전으로 업그레이드
alembic upgrade abc123

# 한 단계 다운그레이드
alembic downgrade -1

# 현재 리비전 표시
alembic current

# 마이그레이션 이력 표시
alembic history --verbose
```

---

## CUBRID 전용 동작

### 트랜잭션 DDL

CUBRID의 DDL은 트랜잭션으로 처리됩니다. 클라이언트 자동 커밋이 꺼져 있으면(방언은 모든 연결에서 이를 끕니다) `CREATE TABLE`, `ALTER TABLE`, `DROP TABLE`, `TRUNCATE`, `CREATE INDEX`(`WITH ONLINE [PARALLEL n]` 포함), `CREATE VIEW`, `CREATE SERIAL`, `RENAME TABLE`은 현재 트랜잭션 안에서 실행됩니다. `ROLLBACK`이 이를 되돌리며, 같은 트랜잭션에서 앞서 실행한 DML을 커밋하지도 않습니다([CUBRID 매뉴얼](https://www.cubrid.org/manual/en/11.4/sql/transaction.html)에서 `ROLLBACK WORK`가 `ALTER TABLE … DROP`을 되돌리는 예를 볼 수 있습니다). CUBRID에서 자동 커밋이 일어나는 경우는 클라이언트 자동 커밋(`CCI_DEFAULT_AUTOCOMMIT` 또는 csql의 기본 자동 커밋 모드)뿐이며, 이때는 DDL이든 DML이든 문마다 커밋됩니다.

그래서 `CubridImpl`은 `transactional_ddl = True`를 설정해 Alembic에게 알립니다:

- 기본적으로 **`alembic upgrade` 전체가 하나의 트랜잭션**으로 실행됩니다. 어느 리비전이 실패하면 `alembic_version` 갱신을 포함해 그 실행의 모든 리비전이 롤백되므로, 데이터베이스는 시작 리비전에 그대로 남습니다.
- `context.configure()`에 `transaction_per_migration=True`를 주면 리비전마다 별도 트랜잭션으로 실행하고 커밋합니다. 끝난 리비전은 적용된 채 남고, 실패한 리비전은 통째로 롤백됩니다.
- `context.is_transactional_ddl()`은 `True`를 반환합니다.

**스키마 잠금.** 커밋되지 않은 DDL은 트랜잭션이 끝날 때까지 테이블의 스키마 잠금을 유지하므로, 그 테이블을 사용하는 다른 세션은 트랜잭션 전체가 끝날 때까지 기다립니다(`SCH_S_LOCK` 대기). CUBRID의 기본 `lock_timeout`은 무제한이므로 타임아웃 없이 계속 기다립니다. 오래 걸리는 마이그레이션이나 큰 테이블의 마이그레이션에는 `transaction_per_migration=True`를 설정해 리비전이 끝날 때마다 커밋하고 잠금을 해제하세요:

```python
# env.py
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    transaction_per_migration=True,
)
```

Alembic의 `autocommit_block()`은 CUBRID에서 업그레이드 일부를 먼저 커밋하는 수단이 아닙니다. 이 기능은 연결을 `AUTOCOMMIT` 격리 수준으로 바꾸는데, 방언은 #501 이전에는 이를 받아들이지 않으며, 업그레이드의 원자성도 잃게 됩니다. 리비전 사이에서 커밋하려면 `transaction_per_migration=True`를 사용하세요.

**오프라인(`--sql`) 스크립트.** CUBRID에는 `BEGIN` 문이 없습니다(csql은 `Syntax error: unexpected 'BEGIN'`으로 거부합니다). 트랜잭션은 암묵적으로 시작됩니다. 그래서 CUBRID 구현은 `BEGIN;`을 내지 않고 각 트랜잭션을 `COMMIT;`으로 끝냅니다(업그레이드당 하나, `transaction_per_migration=True`이면 리비전당 하나). 스크립트는 `--no-auto-commit`과 `--no-single-line`을 함께 주어 실행하세요:

```bash
csql -u dba demodb --no-auto-commit --no-single-line -i upgrade.sql
```

`--no-auto-commit`은 그 `COMMIT;` 줄만 커밋 지점이 되게 합니다. csql의 기본 자동 커밋 모드에서는 문마다 커밋됩니다. `--no-single-line`은 첫 번째로 실패한 문에서 csql을 멈추고 상태 1로 종료시키므로, 열린 트랜잭션이 롤백되어 업그레이드 전체(`transaction_per_migration=True`이면 실패한 리비전)의 변경이 남지 않습니다. csql의 기본 단일 행 모드에서는 오류를 보고한 뒤 **다음 문을 계속 실행하고, 마지막 `COMMIT;`까지 실행한 다음 0으로 종료**하므로, 실패한 스크립트가 부분 스키마와 올라간 `alembic_version`을 남길 수 있습니다.

!!! note "1.8.0에서 변경"
    이전 릴리스는 `transactional_ddl = False`였습니다. 그래도 온라인 모드의 Alembic은 리비전마다 트랜잭션을 감쌌기 때문에 각 리비전은 이미 원자적이었지만, 실패한 `upgrade`는 앞선 리비전을 남겼습니다. 이제는 기본적으로 업그레이드 전체가 원자적입니다. 이전의 리비전 단위 동작을 유지하려면 `transaction_per_migration=True`를 설정하세요.

### 자동 등록

Alembic은 `dialect.name`을 키로 하는 레지스트리에서 마이그레이션 구현을 고르며, `DefaultImpl` 하위 클래스는 모듈이 임포트될 때 이 레지스트리에 스스로 추가됩니다(`CubridImpl.__dialect__ = "cubrid"`). 모든 CUBRID URL(`cubrid://`, `cubrid+cubriddb://`, `cubrid+pycubrid://`, `cubrid+aiopycubrid://`)은 `dialect.name == "cubrid"`입니다. sqlalchemy-cubrid는 Alembic이 이 이름을 조회하기 전에, 설치된 Alembic에 따라 다음 두 가지 방법 중 하나로 `sqlalchemy_cubrid.alembic_impl`을 임포트합니다.

| Alembic | `alembic_impl`을 임포트하는 주체 | 시점 |
|---|---|---|
| 1.18 이상 | sqlalchemy-cubrid가 게시하는 `alembic.plugins` 엔트리 포인트(`_sqlalchemy_cubrid_alembic`)를 통해 Alembic이 | `import alembic` 중 |
| 1.7.2 – 1.17.x | `sqlalchemy_cubrid/dialect.py` | CUBRID 방언을 로드할 때(엔진 생성 시, 오프라인 `--sql` 모드에서는 URL로 방언을 만들 때) |

어느 경우든 `env.py`나 마이그레이션 파일에 임포트나 구성이 필요 없습니다. Alembic이 없으면 아무것도 등록하거나 기록하지 않습니다.

Alembic 1.18 이상에서는 CUBRID 방언을 로드해도 Alembic을 임포트하지 않으므로, 마이그레이션을 실행하지 않는 애플리케이션은 더 이상 그 임포트 비용을 치르지 않습니다(Alembic 1.20.0, SQLAlchemy 2.0.54, Python 3.10에서 새 프로세스의 첫 `create_engine("cubrid+pycubrid://...")`가 약 80 ms 대신 약 18 ms). 방언은 이를 Alembic 자체가 아니라 설치된 패키지 메타데이터로 판단합니다. Alembic이 이미 임포트되었거나, 메타데이터를 읽을 수 없거나, 메타데이터가 실제로 임포트될 `alembic` 패키지의 것이 아니면(예: `sys.path` 앞쪽의 이전 사본) 직접 임포트로 돌아가며, 이는 무해합니다.

Alembic 1.18 이상은 임포트될 때 `alembic.runtime.plugins` 로거로 `INFO` 줄(`setup plugin alembic.autogenerate.schemas`, ..., `setup plugin alembic.ext.checkconstraint_byname`)을 남기며, sqlalchemy-cubrid가 설치되어 있으면 `setup plugin sqlalchemy_cubrid`도 남깁니다. 이는 Alembic 자체의 메시지입니다. 이 버전들에서는 방언이 더 이상 Alembic을 임포트하지 않으므로, 이 줄은 Alembic을 사용하는 프로세스에서만, 그리고 애플리케이션이 `INFO` 레코드를 핸들러로 보낼 때(예: `logging.basicConfig(level=logging.INFO)`)에만 나타납니다. Alembic 1.7.2 – 1.17.x에서는 방언이 여전히 Alembic을 임포트하지만(약 0.1초), 이 릴리스들은 이런 줄을 남기지 않습니다. 로거 레벨은 애플리케이션이 정할 일이므로 방언은 `alembic` 로거를 건드리지 않습니다. 이 줄을 숨기려면 애플리케이션의 로깅 설정에서 해당 로거의 레벨을 올리세요.

```python
import logging

logging.getLogger("alembic").setLevel(logging.WARNING)
```

Alembic 1.18.0은 이 줄을 이름이 문자 그대로 `__name__`인 로거(`logging.getLogger("__name__")`, 1.18.1에서 수정)로 남기므로, 위 설정으로는 그 릴리스에서 숨겨지지 않습니다. 1.18.1 이상으로 업그레이드하거나 `logging.getLogger("__name__")`의 레벨도 `WARNING`으로 올리세요.

Alembic 1.18 – 1.20은 `alembic.plugins` 엔트리 포인트를 `for mod in entrypoint.load()`로 로드하지만, Alembic 문서는 엔트리 포인트 값을 플러그인 모듈 자체로 설명합니다. 일반 모듈은 반복할 수 없으므로 문서의 형태는 모든 `import alembic`을 `TypeError`로 실패시킵니다. `_sqlalchemy_cubrid_alembic`은 자기 자신을 내놓는 반복 가능한 모듈이라 두 방식 모두에서 동작합니다. Alembic은 엔트리 포인트 로드를 보호하지 않으므로, 플러그인은 표준 라이브러리만 임포트하는 최상위 모듈입니다. 이를 로드해도 `sqlalchemy_cubrid` 패키지는 임포트되지 않으며, 그 패키지의 임포트는 실패할 수 있습니다(예: 지원하지 않는 SQLAlchemy를 그 위에 설치한 경우). 그 `setup()`은 `sqlalchemy_cubrid.alembic_impl`을 임포트하며 어떤 실패도 예외 대신 `RuntimeWarning`(`-W error`에서는 `sqlalchemy_cubrid.alembic_plugin` 로거의 로그 레코드)으로 바꾸므로, 같은 환경의 다른 프로젝트에서 `import alembic`을 깨뜨릴 수 없습니다. 그래도 등록에 실패하면 Alembic은 `KeyError: 'cubrid'`를 보고하며, `env.py`에서 `sqlalchemy_cubrid.alembic_impl`을 임포트하면 `CubridImpl`이 직접 등록됩니다.

Alembic이 설치되어 있지만 임포트에 실패하면(예: SQLAlchemy 2.x에서 `NameError`를 내는 Alembic 1.7.0/1.7.1) 방언은 그대로 로드되고, Alembic 통합이 비활성화되었다는 `RuntimeWarning`을 원래 예외와 함께 한 번 냅니다. 경고 필터가 이 경고를 오류로 바꾸면(`-W error`) 대신 `sqlalchemy_cubrid.dialect` 로거로 기록하므로 방언은 그대로 로드됩니다. `alembic>=1.7.2,<2.0`으로 업그레이드하면 해결됩니다.

이 수정 이전 버전은 Alembic이 읽지 않는 `alembic.ddl` 엔트리 포인트를 선언했기 때문에, 기본 `env.py`는 `sqlalchemy_cubrid.alembic_impl`을 명시적으로 임포트하지 않으면 `KeyError: 'cubrid'`로 실패했습니다. 그 임포트는 남겨 두어도 무해합니다.

### 구현 상세

```python
class CubridImpl(DefaultImpl):
    __dialect__ = "cubrid"
    transactional_ddl = True

    def emit_begin(self):
        # CUBRID has no BEGIN statement; offline scripts only emit COMMIT;
        pass
```

구현은 `DefaultImpl`의 모든 표준 Alembic 연산을 상속합니다:
- `add_column`, `drop_column`
- `add_constraint`, `drop_constraint`
- `create_table`, `drop_table`
- `create_index`, `drop_index`
- `alter_column` (타입 변경, 이름 변경, nullable, default — 전부 네이티브)
- `bulk_insert`

---

## 한계와 회피

Alembic으로 UNIQUE 인덱스를 만들 때는 CUBRID의 FK 자동 인덱스 충돌을 확인하기 위해
라이브 연결이 필요합니다. 연결이 없으면 검증을 건너뛰지 않고 라이브 연결 요구사항을
설명하는 `CompileError`를 발생시킵니다. 비고유 인덱스 생성에는 영향이 없습니다.

### ✅ ALTER COLUMN TYPE (네이티브)

CUBRID는 `MODIFY`를 통해 컬럼의 데이터 타입을 제자리에서 변경하는 것을 지원합니다:

```sql
-- 이것은 동작:
ALTER TABLE users MODIFY COLUMN name BIGINT;
```

**Alembic에서**, `alter_column(type_=...)`은 네이티브 `ALTER TABLE ... MODIFY <col> <definition>`을 냅니다. CUBRID의 `MODIFY`는 컬럼 정의 *전체*를 재진술하므로, 방언은 Alembic이 제공하는 `existing_*` 메타데이터에서 전체 정의(`NOT NULL` / `DEFAULT` / `AUTO_INCREMENT` / `COMMENT`)를 재구성해 기존 속성이 조용히 삭제되지 않게 합니다:

```python
def upgrade():
    op.alter_column("users", "name", type_=sa.BigInteger())
```

!!! warning "손실 변환은 거부될 수 있음"
    호환되지 않거나 절단하는 변환은 `alter_table_change_type_strict` 시스템 파라미터에 따라 서버가 거부할 수 있습니다 (`yes`이면 호환 불가/절단 변환이 오류 발생, `no`이면 CUBRID가 조용히 절단할 수 있음). 진짜 손실 있거나 지원되지 않는 변환에는 `batch_alter_table`(테이블 재생성)으로 폴백하세요:

    ```python
    def upgrade():
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column("name", type_=sa.BigInteger())
    ```

### ✅ RENAME COLUMN (네이티브)

CUBRID는 `RENAME COLUMN`으로 컬럼 이름 변경을 지원합니다:

```sql
-- 이것은 동작:
ALTER TABLE users RENAME COLUMN old_name TO new_name;
```

**Alembic에서**, `alter_column(new_column_name=...)`은 네이티브 `ALTER TABLE ... RENAME COLUMN old TO new`를 냅니다. 이름 변경이 타입 변경과 결합되면, 방언은 단일 문장으로 `ALTER TABLE ... CHANGE old new <definition>`을 냅니다:

```python
def upgrade():
    op.alter_column("users", "old_name", new_column_name="new_name")
```

### ⚠️ 긴 마이그레이션은 스키마 잠금을 유지함

DDL은 트랜잭션으로 처리되므로([트랜잭션 DDL](#트랜잭션-ddl) 참고) 실패한 업그레이드는 깔끔하게 롤백됩니다. 대신 각 DDL 문은 트랜잭션이 커밋될 때까지 스키마 잠금을 유지합니다. 유의하세요:

- 기본적으로 업그레이드 전체가 하나의 트랜잭션이므로, 업그레이드가 건드린 모든 테이블은 마지막 리비전이 끝날 때까지 잠겨 있음
- 오래 걸리는 마이그레이션이나 큰 테이블에는 `transaction_per_migration=True` 사용
- 프로덕션 전 스테이징 데이터베이스에서 마이그레이션 테스트
- 마이그레이션 실행 전 데이터베이스 백업 유지

### autogenerate의 외래 키 참조 동작

CUBRID의 기본 `ON DELETE` / `ON UPDATE` 동작은 `RESTRICT`이며
`SHOW CREATE TABLE`은 이를 항상 출력합니다. 따라서 동작 없이 만든 외래 키는
`inspect(...).get_foreign_keys()`에서 `{"ondelete": "RESTRICT", "onupdate": "RESTRICT"}`로
보고됩니다. 리플렉션은 서버가 보고한 값을 그대로 유지합니다. autogenerate에서는
`CubridImpl`이 리플렉션된 `RESTRICT`를 `ondelete` / `onupdate`가 없는 모델
`ForeignKey`와 같은 것으로 취급하므로(#597), 모델이 동작을 생략하든 `RESTRICT`를
명시하든 변경되지 않은 외래 키에 대해 `drop_constraint` / `create_foreign_key` 쌍이
생성되지 않습니다. `ondelete="CASCADE"`나 `SET NULL`의 추가, 다시 제거, 둘 사이의
전환은 여전히 감지됩니다. `NO ACTION`은 다릅니다. CUBRID는 이를 `NO ACTION`으로
출력하지만 Alembic 자체가 `NO ACTION`과 동작 없음을 양방향으로 같은 것으로 취급하므로,
둘 사이의 전환은 감지되지 않습니다. CUBRID는 `ON UPDATE CASCADE`를 거부하므로
`onupdate`에는 `SET NULL`, `RESTRICT` 또는 `NO ACTION`을 사용하세요.

### `alter_column()` 동작

CUBRID Alembic 구현은 `alter_column()`을 네이티브 CUBRID DDL로 매핑합니다:

- `type_=` 변경 → `MODIFY` (이름 변경과 결합 시 `CHANGE`)
- `new_column_name=` 이름 변경 → `RENAME COLUMN` (타입 변경 시 `CHANGE`)
- `nullable=` / `server_default=` / 코멘트 변경은 `DefaultImpl`을 경유

타입 변경은 `existing_*` 메타데이터에서 전체 컬럼 정의를 재구성해 `NOT NULL` / `DEFAULT` / `COMMENT` 같은 속성이 보존됩니다.

> **중요 — 손으로 작성한 타입 변경 마이그레이션은 `existing_*`를 전달해야 합니다.**
> CUBRID의 `MODIFY` / `CHANGE`는 컬럼 정의 *전체*를 재진술하므로, 방언은 알려준 속성만 보존할 수 있습니다. Alembic autogenerate는 리플렉트된 컬럼에서 `existing_type`, `existing_nullable`, `existing_server_default`, `existing_comment`를 채우지만, 수동 `op.alter_column(..., type_=...)`은 그렇지 **않습니다**. 마이그레이션을 손으로 편집할 때, 타입 변경에서 살아남아야 하는 모든 속성에 대해 `existing_nullable=`, `existing_server_default=`, `existing_comment=`, `existing_autoincrement=`를 전달하세요 — 그렇지 않으면 삭제됩니다. 속성을 *의도적으로* 제거하려면 (예: 기본값) 명시적으로 전달하세요(`server_default=None`). 이것이 `existing_*` 값을 오버라이드합니다.

### 요약

| 연산 | 지원 | 회피 |
|---|:---:|---|
| `create_table` | ✅ | — |
| `drop_table` | ✅ | — |
| `add_column` | ✅ | — |
| `drop_column` | ✅ | — |
| `alter_column` (nullable) | ✅ | — |
| `alter_column` (default) | ✅ | — |
| `alter_column` (type) | ✅ | 손실 변환에는 `batch_alter_table` |
| `alter_column` (rename) | ✅ | — |
| `create_index` | ✅ | `if_not_exists=True`는 `CompileError`를 발생시킵니다(CUBRID에는 `CREATE INDEX IF NOT EXISTS`가 없음). 대신 먼저 `inspect(conn).has_index()`로 확인하세요 |
| `drop_index` | ✅ | `DROP INDEX <name> ON <table>`을 생성하므로 `table_name`이 필수입니다(없으면 `CompileError`). `if_exists=True`는 `CompileError`를 발생시킵니다(CUBRID에는 `DROP INDEX IF EXISTS`가 없음) |
| `add_constraint` | ✅ | — |
| `drop_constraint` | ✅ | — |
| `bulk_insert` | ✅ | — |
| 트랜잭션 DDL | ✅ | 긴 마이그레이션이나 큰 테이블에는 `transaction_per_migration=True` |

---

## 예제

### 테이블 생성

```python
"""create users table

Revision ID: 001
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(200), unique=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_users_email", "users", ["email"])


def downgrade():
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
```

### 컬럼 추가

```python
def upgrade():
    op.add_column("users", sa.Column("is_active", sa.SmallInteger(), server_default="1"))


def downgrade():
    op.drop_column("users", "is_active")
```

### 컬럼 타입 변경 (배치 경유)

```python
def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("name", type_=sa.String(500))


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("name", type_=sa.String(100))
```

### 컬럼 이름 변경 (배치 경유)

```python
def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("name", new_column_name="full_name")


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("full_name", new_column_name="name")
```

---

## 문제 해결

### "No implementation found for dialect 'cubrid'"

**원인**: `sqlalchemy-cubrid`가 설치되지 않았거나, `alembic` extra 없이 설치됨.

**해결**:

```bash
pip install sqlalchemy-cubrid[alembic]
```

### `setup plugin ...` `INFO` 로그 줄

Alembic 1.18+는 임포트될 때 이 줄을 남깁니다. 이 버전들에서는 CUBRID 방언을 로드해도 더 이상 Alembic을 임포트하지 않으므로, 이 줄은 Alembic을 사용하는 프로세스에서만 나타납니다. 애플리케이션에서 `logging.getLogger("alembic").setLevel(logging.WARNING)`을 설정하세요(이 줄을 `__name__` 로거로 남기는 Alembic 1.18.0에서는 업그레이드하거나 그 로거도 조용히 하세요). [자동 등록](#자동-등록)을 참고하세요.

### "Alembic is required for migration support"

**원인**: `alembic_impl` 모듈이 Alembic 설치 없이 직접 임포트됨.

**해결**:

```bash
pip install "alembic>=1.7.2,<2.0"
```

### 마이그레이션이 부분 적용됨

**원인**: CUBRID의 DDL은 트랜잭션으로 처리되므로, 실패한 온라인 업그레이드는 반쯤 적용된 리비전을 남기지 않습니다. 실패한 트랜잭션이 롤백되기 때문입니다. 기본값에서는 업그레이드 전체가, `transaction_per_migration=True`에서는 실패한 리비전이 롤백되고 그 앞의 리비전은 커밋되어 `alembic_version`에 기록된 채 남습니다. 그래도 다음 경우에는 부분 상태가 생길 수 있습니다:

- 클라이언트 자동 커밋(드라이버 수준 자동 커밋, csql의 기본 자동 커밋 모드, 또는 방언이 지원하는 경우(#501) `isolation_level="AUTOCOMMIT"`) — 문마다 커밋됩니다
- 오프라인(`--sql`) 스크립트를 `csql --no-auto-commit --no-single-line` 없이 실행한 경우(csql의 기본 단일 행 모드는 실패한 문 뒤에도 계속 실행하고 마지막 `COMMIT;`까지 실행합니다)
- 리비전이 직접 `COMMIT`을 실행한 경우(예: `op.execute`)

**해결**:
1. 데이터베이스 상태를 수동 검사
2. 남은 연산을 수동 완료하거나 완료된 것을 되돌리기
3. 올바른 상태로 리비전 스탬프: `alembic stamp <revision>`

### `alter_column` 타입 변경이 서버에서 거부됨

**원인**: `alter_table_change_type_strict` 시스템 파라미터가 `yes`일 때 손실 있거나 호환 불가한 타입 변환.

**해결**: 진짜 손실/미지원 변환에는 `batch_alter_table` 사용 — [ALTER COLUMN TYPE (네이티브)](#️-alter-column-type-네이티브) 참고.

### `alembic revision --autogenerate`가 리플렉션 오류로 실패함

**원인**: 외래 키는 `SHOW CREATE TABLE`에서 읽습니다. #589 이후 여기서 발생한 실패(끊긴
연결, 권한 오류, 드라이버 오류)는 "이 테이블에는 외래 키가 없음"으로 보고되지 않고 예외를
발생시킵니다. 이전 동작 때문에 autogenerate가 이미 존재하는 외래 키에 대해 `add_fk`를
제안했습니다.

**해결**: 원인이 된 오류를 해결한 뒤 autogenerate를 다시 실행하세요. 연결이 오래되었다면
엔진에 `pool_pre_ping=True`를 설정하세요. CUBRID 11.2부터는 소유자를 붙이지 않은 이름을
현재 사용자의 스키마에서 찾으므로 다른 소유자의 테이블은 `NoSuchTableError`가 됩니다.
autogenerate는 테이블 소유자로 실행하세요.

---

## 마이그레이션 안전 체크리스트

!!! note "DDL은 트랜잭션으로 처리됨"
    CUBRID는 DDL을 트랜잭션과 함께 롤백합니다. DDL을 먼저 커밋하는 것은 클라이언트 자동 커밋뿐입니다.
    기본적으로 실패한 `alembic upgrade`는 부분 스키마도, 버전 증가도 남기지 않습니다.
    커밋되지 않은 DDL은 스키마 잠금을 유지하므로, 긴 마이그레이션이나 큰 테이블에는 `transaction_per_migration=True`를 사용하세요.

!!! warning "손실 타입 변경은 서버가 거부할 수 있음"
    `alter_column(type_=...)`와 `alter_column(new_column_name=...)`은 네이티브 CUBRID DDL(`MODIFY` / `RENAME COLUMN` / `CHANGE`)을 냅니다. 진짜 손실 있거나 호환 불가한 타입 변환만 거부됩니다 (`alter_table_change_type_strict`가 관리). 그런 경우 테스트된 다운그레이드 단계와 함께 `op.batch_alter_table()`을 사용하세요.

!!! tip "항상 스테이징에서 업그레이드 + 다운그레이드 테스트"
    프로덕션 롤아웃 전에 전체 순방향/역방향 마이그레이션 체인을 검증하세요.

!!! tip "파괴적 연산을 위한 백업 생성"
    `drop_column`, `drop_table`, 다단계 재구성 마이그레이션 전에 데이터를 백업하세요.

### 마이그레이션 전 체크리스트

프로덕션에서 마이그레이션 실행 전:

- [ ] **잠금 시간 계획** — DDL은 커밋될 때까지 스키마 잠금을 유지하고, 기본적으로 업그레이드 전체가 하나의 트랜잭션입니다. 긴 마이그레이션이나 큰 테이블에는 `transaction_per_migration=True`를 사용하세요.
- [ ] **클라이언트 자동 커밋 금지** — 클라이언트 자동 커밋(드라이버 수준 자동 커밋, csql의 기본 자동 커밋 모드, 또는 방언이 지원하는 경우(#501) `isolation_level="AUTOCOMMIT"`)을 켠 채 마이그레이션을 실행하지 말고, 오프라인 스크립트는 `csql --no-auto-commit --no-single-line`으로 실행해 실패 시 깔끔하게 롤백되게 하세요.
- [ ] **데이터베이스 백업** — 파괴적 연산 전 `cubrid backupdb demodb`
- [ ] **업그레이드 + 다운그레이드 주기 테스트** — 스테이징에서 `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` 실행
- [ ] **각 단계 후 상태 검증** — `db_class` 시스템 테이블을 조회해 스키마가 기대와 일치하는지 확인
- [ ] **유지보수 창구** — 영향이 큰 마이그레이션은 저트래픽 시간대에 예약
- [ ] **롤백 스크립트 준비** — 각 `upgrade()`마다 `downgrade()`로 부족할 경우 테스트된 수동 롤백 SQL 준비

### 권장 사전 배포 시퀀스

1. `cubrid backupdb demodb` — 전체 백업 생성
2. 스테이징 사본에서 `alembic upgrade head`
3. 스테이징에 대해 스모크 테스트와 치명적 쿼리 실행
4. 가역성 검증을 위해 `alembic downgrade -1` 후 `alembic upgrade head`
5. 영향이 큰 스키마 변경은 유지보수 창구 중 배포
6. 배포 후 `alembic current` 모니터링으로 예상 리비전 확인

### 자문 CI 안전 검사

DDL 연산이 여러 개인 리비전을 나열하려면 다음 스크립트를 추가하세요. 자문 용도(경고만)이며 CI를 차단하지 않습니다. 그런 리비전도 실패하면 통째로 롤백되지만, 스키마 잠금을 더 오래 유지합니다. 스크립트는 `upgrade()`와 `downgrade()`마다 따로, 제약 조건 생성(`create_unique_constraint`, `create_foreign_key`, `create_check_constraint`, `create_primary_key`)을 포함한 Alembic DDL 연산의 호출 횟수를 셉니다. `op.drop_table`처럼 호출하지 않는 단순 참조는 세지 않습니다. 제어 흐름 분석이 아닌 휴리스틱입니다:

```python
#!/usr/bin/env python3
"""Check Alembic revisions for multiple DDL operations (advisory).

CUBRID DDL is transactional, so a failing revision is rolled back as a
whole. Every DDL statement holds a schema lock on its table until the
transaction commits, though, so this lists revisions with several DDL
calls: they keep tables locked longer and are candidates for running with
``transaction_per_migration=True`` or for splitting.

Only calls such as ``op.create_table(...)`` or ``batch_op.add_column(...)``
count; a bare reference like ``op.drop_table`` is not a DDL operation. This is
a heuristic AST scan, not control-flow analysis: a call in a loop or branch
counts once, as written, and DDL issued from helpers defined outside
``upgrade()``/``downgrade()`` is not seen.

Usage:
    python scripts/alembic_safety_check.py alembic/versions/
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

DDL_CALLS = {
    "create_table", "drop_table", "add_column", "drop_column",
    "create_index", "drop_index", "alter_column",
    "add_constraint", "drop_constraint",
    "create_unique_constraint", "create_foreign_key",
    "create_check_constraint", "create_primary_key",
}


def check_revision(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    warnings = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name not in ("upgrade", "downgrade"):
            continue
        ddl_count = sum(
            1 for node in ast.walk(func)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in DDL_CALLS
        )
        if ddl_count > 1:
            warnings.append(
                f"{path.name}:{func.name}() has {ddl_count} DDL operations "
                "(schema locks are held until the transaction commits)"
            )
    return warnings


def main() -> None:
    versions_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("alembic/versions")
    if not versions_dir.is_dir():
        print(f"Directory not found: {versions_dir}")
        sys.exit(1)

    all_warnings = []
    for py_file in sorted(versions_dir.glob("*.py")):
        all_warnings.extend(check_revision(py_file))

    if all_warnings:
        print("⚠️  Alembic safety warnings (advisory):")
        for w in all_warnings:
            print(f"  • {w}")
        print(f"\nTotal: {len(all_warnings)} warning(s)")
        print(
            "Tip: these revisions roll back whole on failure but hold schema locks "
            "until commit; use transaction_per_migration=True for long or "
            "large-table migrations."
        )
    else:
        print("✓ No revision has more than one DDL call per function.")


if __name__ == "__main__":
    main()
```

CI 통합 예시(`.github/workflows/ci.yml`):

```yaml
- name: Alembic safety check (advisory)
  run: python scripts/alembic_safety_check.py alembic/versions/ || true
```

### 롤백 스크립트 템플릿

치명적 마이그레이션에는 동반 롤백 SQL 파일을 만드세요:

```sql
-- rollback_001_add_users_table.sql
-- Manual rollback for revision abc123 (add users table)
-- Use if alembic downgrade fails or is insufficient.

DROP TABLE IF EXISTS users;

-- Verify: SELECT class_name FROM db_class WHERE class_name = 'users';
-- Expected: no rows
```

롤백 스크립트는 버전 디렉터리와 함께 `alembic/rollbacks/`에 보관하세요.

---

*참고: [연결 가이드](CONNECTION.md) · [타입 매핑](TYPES.md) · [기능 지원](FEATURE_SUPPORT.md)*
