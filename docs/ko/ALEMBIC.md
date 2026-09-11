# Alembic 마이그레이션 지원 (한국어)

> 🌐 [ALEMBIC.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/ALEMBIC.md)의 번역입니다. 영어 원문이 표준이며, 페이지 번역은 경고 수준의 동기화 규칙을 따릅니다.

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

이것은 의존성으로 Alembic ≥ 1.7을 끌어옵니다. CUBRID Alembic 구현(`CubridImpl`)은 `alembic.ddl` 엔트리 포인트를 통해 자동 등록됩니다 — 수동 구성이 필요 없습니다.

> **참고**: Alembic을 따로 설치해도(`pip install alembic`), 같은 환경에 `sqlalchemy-cubrid`가 설치되어 있으면 CUBRID 구현을 자동 발견합니다.

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

표준 Alembic `env.py`는 수정 없이 동작합니다. 연결 URL이 `cubrid://` 스킴을 사용하면 `CubridImpl` 클래스가 자동 발견됩니다.

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

### DDL 자동 커밋

CUBRID는 모든 DDL 문을 암시적으로 커밋합니다. `CubridImpl`은 `transactional_ddl = False`를 설정해 Alembic에게 알립니다:

- DDL 문 주변에 **트랜잭션 래핑 없음**
- 각 `CREATE TABLE`, `ALTER TABLE`, `DROP TABLE`는 즉시 커밋
- 실패한 마이그레이션은 데이터베이스를 부분 마이그레이션 상태로 남길 수 있음

**시사점**: 여러 DDL 연산을 가진 마이그레이션이 중간에 실패하면 단순 롤백이 불가능합니다 — 이전 연산은 이미 커밋되었습니다. 작고 원자적인 단계로 마이그레이션을 작성하세요.

### 자동 발견

방언은 `pyproject.toml`의 `alembic.ddl` 엔트리 포인트로 `CubridImpl`을 등록합니다:

```toml
[project.entry-points."alembic.ddl"]
cubrid = "sqlalchemy_cubrid.alembic_impl:CubridImpl"
```

Alembic이 `cubrid://` 연결 URL을 감지하면 자동으로 `CubridImpl`을 로드합니다. 마이그레이션 파일에 임포트나 구성이 필요 없습니다.

### 구현 상세

```python
class CubridImpl(DefaultImpl):
    __dialect__ = "cubrid"
    transactional_ddl = False
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

### ⚠️ DDL 자동 커밋

위에 언급했듯이 DDL은 자동 커밋됩니다. 유의하세요:

- 마이그레이션을 작게 유지 (마이그레이션당 하나의 논리적 변경)
- 프로덕션 전 스테이징 데이터베이스에서 마이그레이션 테스트
- 마이그레이션 실행 전 데이터베이스 백업 유지

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
| `create_index` | ✅ | — |
| `drop_index` | ✅ | — |
| `add_constraint` | ✅ | — |
| `drop_constraint` | ✅ | — |
| `bulk_insert` | ✅ | — |
| 트랜잭션 DDL | ❌ | 작은 원자적 마이그레이션 |

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

### "Alembic is required for migration support"

**원인**: `alembic_impl` 모듈이 Alembic 설치 없이 직접 임포트됨.

**해결**:

```bash
pip install "alembic>=1.7,<2.0"
```

### 마이그레이션이 부분 적용됨

**원인**: 여러 DDL 문을 가진 마이그레이션이 중간에 실패. CUBRID는 DDL을 자동 커밋하므로 일부 문은 이미 효력 발생.

**해결**:
1. 데이터베이스 상태를 수동 검사
2. 남은 연산을 수동 완료하거나 완료된 것을 되돌리기
3. 올바른 상태로 리비전 스탬프: `alembic stamp <revision>`

### `alter_column` 타입 변경이 서버에서 거부됨

**원인**: `alter_table_change_type_strict` 시스템 파라미터가 `yes`일 때 손실 있거나 호환 불가한 타입 변환.

**해결**: 진짜 손실/미지원 변환에는 `batch_alter_table` 사용 — [ALTER COLUMN TYPE (네이티브)](#️-alter-column-type-네이티브) 참고.

---

## 마이그레이션 안전 체크리스트

!!! warning "DDL은 트랜잭션이 아님"
    CUBRID는 DDL을 자동 커밋합니다. 실패한 마이그레이션은 부분 스키마 변경이 적용된 상태로 남길 수 있습니다.
    논리적 스키마 변경 하나씩의 작은 리비전을 선호하세요.

!!! warning "손실 타입 변경은 서버가 거부할 수 있음"
    `alter_column(type_=...)`와 `alter_column(new_column_name=...)`은 네이티브 CUBRID DDL(`MODIFY` / `RENAME COLUMN` / `CHANGE`)을 냅니다. 진짜 손실 있거나 호환 불가한 타입 변환만 거부됩니다 (`alter_table_change_type_strict`가 관리). 그런 경우 테스트된 다운그레이드 단계와 함께 `op.batch_alter_table()`을 사용하세요.

!!! tip "항상 스테이징에서 업그레이드 + 다운그레이드 테스트"
    프로덕션 롤아웃 전에 전체 순방향/역방향 마이그레이션 체인을 검증하세요.

!!! tip "파괴적 연산을 위한 백업 생성"
    `drop_column`, `drop_table`, 다단계 재구성 마이그레이션 전에 데이터를 백업하세요.

### 마이그레이션 전 체크리스트

프로덕션에서 마이그레이션 실행 전:

- [ ] **리비전당 DDL 연산 하나** — 각 DDL이 자동 커밋되므로, 리비전 중간 실패는 부분 상태를 남깁니다. 다중 DDL 리비전을 분할하세요.
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

다중 DDL 리비전을 조기에 잡으려면 다음 스크립트를 추가하세요. 자문 용도(경고만)이며 CI를 차단하지 않습니다:

```python
#!/usr/bin/env python3
"""Check Alembic revisions for multiple DDL operations (advisory).

Warns when a single revision contains multiple DDL calls, which is risky
with CUBRID's non-transactional DDL.

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
}


def check_revision(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    warnings = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name not in ("upgrade", "downgrade"):
            continue
        ddl_count = sum(
            1 for node in ast.walk(func)
            if isinstance(node, ast.Attribute) and node.attr in DDL_CALLS
        )
        if ddl_count > 1:
            warnings.append(
                f"{path.name}:{func.name}() has {ddl_count} DDL operations "
                f"(recommended: 1 per revision for CUBRID)"
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
        print("Tip: Split multi-DDL revisions to avoid partial migration state.")
    else:
        print("✓ All revisions have single DDL operations per function.")


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
