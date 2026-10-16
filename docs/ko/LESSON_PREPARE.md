# 1강: CUBRID와 Python 준비

> 🌐 [LESSON_PREPARE.md](https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/LESSON_PREPARE.md)의 번역입니다. 영어 원문이 표준이며, CI가 영어 원문과의 구조 일치를 검사합니다.

**목표:** 접속할 수 있는 CUBRID 데이터베이스와, 방언과 드라이버가 설치된 Python 가상 환경을
준비합니다. 로컬 실습 환경이면 `CUBRID is ready`와 설치된 세 패키지 버전이 출력됩니다.

**사전 준비:** Python 3.11 이상. 로컬 실습 환경에는 Docker와 bash 같은 셸도 필요합니다.
[SQLAlchemy로 CUBRID에 처음 연결하기](QUICKSTART.md)의 첫 강의이며, SQLAlchemy, 방언,
드라이버, 서버가 어떻게 함께 동작하는지는 과정 페이지에서 설명합니다.

---

## 데이터베이스 고르기

상황에 맞는 방법을 고르세요.

### 방법 A: 이미 CUBRID 데이터베이스가 있습니다

관리자에게 묻거나 직접 구성한 환경에서 다음 다섯 값을 확인하세요.

- **host**: CUBRID가 실행되는 머신, 예: `db.example.com` 또는 `localhost`
- **port**: 연결을 받는 입구인 CUBRID 브로커 포트(기본값 `33000`)
- **database**: 데이터베이스 이름, 예: `testdb`
- **user**와 **password**: 그 데이터베이스의 계정

3강은 작은 테이블 하나를 만들고 나중에 지웁니다. 연습용 데이터베이스나 그곳에서
테이블을 만들 수 있는 계정을 사용하세요. 이 튜토리얼에 운영 데이터베이스나 그
`dba` 계정을 사용하지 마세요. 2강과 3강에서 실습 환경 URL
`cubrid+pycubrid://dba@localhost:33000/testdb`를 여러분의 값으로 채운
`cubrid+pycubrid://USER:PASSWORD@HOST:PORT/DATABASE`로 바꾼 뒤
[sqlalchemy-cubrid 설치](#가상-환경에-sqlalchemy-cubrid-설치)로 진행하세요.
실제 비밀번호는 공유하거나 커밋하는 파일에 넣지 마세요.

### 방법 B: 버려도 되는 로컬 데이터베이스가 필요합니다

Docker에서 `testdb` 데이터베이스가 있는 일회용 CUBRID 11.4 서버를 시작합니다.
[Docker](https://docs.docker.com/get-started/get-docker/)와 bash 같은 셸이 필요합니다.
명령은 x86_64(amd64) Linux에서 검증했습니다. `cubrid/cubrid:11.4` 이미지는 amd64용으로만
배포되므로 다른 아키텍처(예: Apple silicon)와 Windows는 검증하지 않았습니다.

```bash
docker run -d --name sqlalchemy-cubrid-quickstart -e CUBRID_DB=testdb \
  -p 127.0.0.1:33000:33000 cubrid/cubrid:11.4
ready=no
for i in $(seq 36); do
  if docker exec sqlalchemy-cubrid-quickstart csql -u dba testdb -c "SELECT 1" >/dev/null 2>&1; then
    ready=yes; break
  fi
  sleep 5
done
if [ "$ready" = yes ]; then echo "CUBRID is ready"
else echo "CUBRID did not answer within 3 minutes; see: docker logs sqlalchemy-cubrid-quickstart"; fi
```

`127.0.0.1:`은 이 컴퓨터에만 포트를 열어 다른 머신이 실습 환경에 연결할 수 없게 합니다.
`docker run` 다음의 반복문은 데이터베이스가 응답할 때까지 최대 3분을 기다린 뒤(보통 1분이 채 걸리지
않습니다) `CUBRID is ready`를 출력합니다. 대신 `CUBRID did not answer within 3 minutes`가
출력되면 `docker logs sqlalchemy-cubrid-quickstart`로 원인을 확인하세요. 포트 33000이
이미 사용 중인 경우처럼 `docker run` 자체가 실패했다면 먼저 그 문제를 해결하고
`docker rm -f -v sqlalchemy-cubrid-quickstart`로 컨테이너를 지운 뒤 다시 시작하세요.
실습 환경은 비밀번호가 비어 있는 `dba` 계정을 사용합니다. 이는 이 로컬 일회용
컨테이너에서만 허용됩니다. 다른 사람이 접근할 수 있는 서버에서는 절대 빈 비밀번호를
사용하지 마세요.

튜토리얼을 모두 마치면 `docker rm -f -v sqlalchemy-cubrid-quickstart`로 실습 환경을 지우세요.
이미지는 데이터베이스를 이 컨테이너에 속한 익명 Docker 볼륨에 보관합니다. `-v`가 그 볼륨도 지우므로
`testdb`가 함께 지워집니다. `-v` 없이 지우면 컨테이너만 지워지고 볼륨은 남습니다(`docker volume ls`에
보입니다).

---

## 가상 환경에 sqlalchemy-cubrid 설치

가상 환경은 이 프로젝트의 패키지를 시스템의 나머지 부분과 분리합니다. 먼저
`python3 --version`이 3.11 이상을 출력하는지 확인하세요. 더 오래된 버전이 나오면 첫 명령에서
더 새로운 인터프리터를 이름으로 지정하세요(예: `python3.12`). pip은 사용하는 Python을
지원하는 릴리스만 설치하므로, 오래된 인터프리터에는 오래된 패키지가 설치됩니다.
그런 다음 빈 폴더에서 다음 명령을 실행하세요.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "sqlalchemy-cubrid[pycubrid]"
python -c "import sqlalchemy, sqlalchemy_cubrid, pycubrid; print(sqlalchemy.__version__, sqlalchemy_cubrid.__version__, pycubrid.__version__)"
```

`[pycubrid]` 부분은 방언과 함께 권장 순수 Python 드라이버를 설치합니다. 마지막 명령은
설치된 세 버전(SQLAlchemy, sqlalchemy-cubrid, pycubrid)을 출력합니다(예: `2.1.4 1.11.0 1.13.0`).
이 가이드를 마지막으로 실행한 2026-10-15의 PyPI 공개 릴리스이며, 더 새로운 릴리스가 있으면 더 높은
번호가 출력됩니다. 다음 강의의 모든 `python` 명령은 가상 환경이 활성화된 이 터미널에서 실행하세요.

---

## 다음

[2강: 첫 쿼리 실행](LESSON_FIRST_QUERY.md).
