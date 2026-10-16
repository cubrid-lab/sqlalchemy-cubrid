# 5강: 정리

> 🌐 [LESSON_FINISH.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/LESSON_FINISH.md)의 번역입니다. 영어 원문이 표준이며, CI가 영어 원문과의 구조 일치를 검사합니다.

**목표:** 과정에서 만든 것만 지웁니다. 튜토리얼 테이블과, 사용했다면 로컬 실습 환경입니다.

**사전 준비:** 앞선 강의 전체 또는 일부. 정리는 언제 실행해도 안전합니다.

---

## 튜토리얼 테이블 지우기

`cleanup_quickstart.py`는 튜토리얼 테이블을 지우는데, 여러분의 사용자가 소유한 그 이름의 테이블에
튜토리얼 주석이 있을 때만 지웁니다. 여러분이 직접 만든 같은 이름의 테이블이나 다른 사용자의 테이블은
그대로 둡니다.

```python
from sqlalchemy import create_engine, text

MARK = "created by the sqlalchemy-cubrid quickstart"
engine = create_engine("cubrid+pycubrid://dba@localhost:33000/testdb")

with engine.begin() as conn:
    comment = conn.execute(
        text(
            "SELECT comment FROM db_class"
            " WHERE class_name = :name AND owner_name = CURRENT_USER"
        ),
        {"name": "sqlalchemy_quickstart_notes"},
    ).first()
    if comment is None:
        print("Nothing to clean up: sqlalchemy_quickstart_notes does not exist.")
    elif comment[0] != MARK:
        print("Not dropped: sqlalchemy_quickstart_notes was not created by this quickstart.")
    else:
        conn.execute(text("DROP TABLE sqlalchemy_quickstart_notes"))
        print("Dropped sqlalchemy_quickstart_notes.")

engine.dispose()
```

```bash
python cleanup_quickstart.py
```

`Dropped sqlalchemy_quickstart_notes.`를 출력하거나, 두 번째 실행처럼 지울 것이 없으면
`Nothing to clean up: sqlalchemy_quickstart_notes does not exist.`를 출력합니다. 3강이 중단되어
테이블이 남았더라도 이 스크립트가 똑같이 지웁니다.

---

## 로컬 실습 환경 지우기

1강의 Docker 실습 환경을 사용했다면 `docker rm -f -v sqlalchemy-cubrid-quickstart`로 지우세요.
이미지는 데이터베이스를 이 컨테이너에 속한 익명 Docker 볼륨에 보관합니다. `-v`가 그 볼륨도 지우므로
`testdb`가 함께 지워집니다. `-v` 없이 지우면 컨테이너만 지워지고 볼륨은 남습니다(`docker volume ls`에
보입니다).

---

## 다음

과정을 마쳤습니다. [다음 단계](QUICKSTART.md#다음-단계)에서 ORM, 연결 옵션, 다른 드라이버, 비동기
코드, Alembic으로 이어지는 길을 안내합니다.
