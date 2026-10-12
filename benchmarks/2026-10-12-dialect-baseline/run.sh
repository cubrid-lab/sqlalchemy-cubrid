#!/bin/bash
# Commands of the 2026-10-12 same-CUBRID dialect baseline (#830), run in this order.
# Set the five variables, then run from this directory. Results land in raw/;
# `python aggregate.py` then writes summary.json.
#
# Measured with REPO checked out at a570ea4d3aa7f222553a925677e0b324b8b39cde and the
# cubrid/cubrid:11.4 image sha256:1248b77ad39888df9e064655937188ab99fe056ed7e35b57d06155a015dc1791
# (CUBRID 11.4.6.1963).
#
#   docker run -d --name clsa-830-db114 -e CUBRID_DB=testdb \
#       -p 127.0.0.1:33830:33000 cubrid/cubrid:11.4
#   git clone https://github.com/cubrid-lab/cubrid-benchmark && git -C cubrid-benchmark checkout f5510d0
#   uv venv -p 3.12 venv21 && VIRTUAL_ENV=venv21 uv pip install -e <repo> pycubrid==1.12.0 sqlalchemy==2.1.4
#   uv venv -p 3.12 venv20 && VIRTUAL_ENV=venv20 uv pip install -e <repo> pycubrid==1.12.0 sqlalchemy==2.0.54
set -euo pipefail
REPO=${REPO:?sqlalchemy-cubrid checkout}
BENCH=${BENCH:?cubrid-benchmark checkout at f5510d0}
PY21=${PY21:?python of the SQLAlchemy 2.1.4 venv}
PY20=${PY20:?python of the SQLAlchemy 2.0.54 venv}
DSN=${DSN:-cubrid+pycubrid://dba@localhost:33830/testdb}
R=raw
W=$BENCH/experiments/orm-overhead/workers
SHA=$(git -C "$REPO" rev-parse HEAD)
declare -A PY=([sa21]=$PY21 [sa20]=$PY20)
mkdir -p $R
for sa in sa21 sa20; do
  ${PY[$sa]} -I "$REPO/scripts/bench_dialect_baseline.py" --dsn "$DSN" --trials 5 \
    --source-sha "$SHA" --output $R/bench_dialect_baseline_$sa.json > $R/bench_dialect_baseline_$sa.txt
  for t in 1 2 3 4 5; do
    ${PY[$sa]} -I "$REPO/scripts/bench_compile.py" -n 10000 > $R/bench_compile_${sa}_trial$t.txt
  done
done
# input.json names the DSN the workers connect to.
for t in 1 2 3 4 5; do
  $PY21 -I $W/worker_raw_pycubrid.py input.json > $R/worker_raw_pycubrid_trial$t.json
  for sa in sa21 sa20; do
    ${PY[$sa]} -I $W/worker_sqlalchemy_core.py input.json > $R/worker_sqlalchemy_core_${sa}_trial$t.json
    ${PY[$sa]} -I $W/worker_sqlalchemy_orm.py input.json > $R/worker_sqlalchemy_orm_${sa}_trial$t.json
  done
done
for sa in sa21 sa20; do
  (cd "$REPO" && ${PY[$sa]} scripts/profile_orm.py --dsn "$DSN" \
    --output "$OLDPWD/$R/profile_orm_$sa.json") > $R/profile_orm_$sa.txt
done
