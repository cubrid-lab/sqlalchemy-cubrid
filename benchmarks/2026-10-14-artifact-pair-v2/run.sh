#!/bin/bash
# Commands of the 2026-10-14 pinned artifact pair, contract 2 (#903): one benchmark environment,
# only the installed dialect source varies. Baseline is the v1.11.0 tag
# (3a0c2898b2954e59eb675ef89ab237d252434713), candidate is main at
# 0dfe938ee8387ed8cea283a9c1ae89f0e91b99c4. Both runs use the same
# scripts/bench_dialect_baseline.py (SHA-256 recorded as workload.script_sha256 in
# each report), from the #903 pull request, run with -I so the installed dialect is
# the one measured. The benchmark verifies each install against its SHA
# (source_verification: local_checkout) and refuses to run on a mismatch. Set the variables, then run from this directory.
#
# Measured on the cubrid/cubrid:11.4 image
# sha256:1248b77ad39888df9e064655937188ab99fe056ed7e35b57d06155a015dc1791
# (CUBRID 11.4.6.1963), one host (label devbox), CPython 3.12.13. The recorded runs
# wrote to a scratch directory and the files were copied here unchanged, so the last
# line of each log names that path.
#
#   docker run -d --name sac903-cubrid-114 -e CUBRID_DB=testdb -p 34114:33000 \
#       cubrid/cubrid:11.4
#   git -C <repo> worktree add --detach ../sac-base v1.11.0
#   git -C <repo> worktree add --detach ../sac-cand 0dfe938ee8387ed8cea283a9c1ae89f0e91b99c4
#   uv venv -p 3.12 venv-base && VIRTUAL_ENV=venv-base uv pip install ../sac-base \
#       pycubrid==1.12.0 'sqlalchemy[asyncio]==2.1.4'
#   uv venv -p 3.12 venv-cand && VIRTUAL_ENV=venv-cand uv pip install ../sac-cand \
#       pycubrid==1.12.0 'sqlalchemy[asyncio]==2.1.4'
set -euo pipefail
REPO=${REPO:?sqlalchemy-cubrid checkout holding scripts/bench_dialect_baseline.py}
PY_BASE=${PY_BASE:?python of venv-base}
PY_CAND=${PY_CAND:?python of venv-cand}
SHA_BASE=${SHA_BASE:-3a0c2898b2954e59eb675ef89ab237d252434713}
SHA_CAND=${SHA_CAND:-0dfe938ee8387ed8cea283a9c1ae89f0e91b99c4}
DSN=${DSN:-cubrid+pycubrid://dba@localhost:34114/testdb}
DIGEST=${DIGEST:-sha256:1248b77ad39888df9e064655937188ab99fe056ed7e35b57d06155a015dc1791}
GROUP=devbox-cubrid114-py312-sa214-pycubrid1120-2026-10-14
declare -A PY=([baseline]=$PY_BASE [candidate]=$PY_CAND)
declare -A SHA=([baseline]=$SHA_BASE [candidate]=$SHA_CAND)
for role in baseline candidate; do
  mkdir -p $role/raw
  ${PY[$role]} -I "$REPO/scripts/bench_dialect_baseline.py" --dsn "$DSN" --trials 5 \
    --source-sha "${SHA[$role]}" --server-image-digest "$DIGEST" --host-label devbox \
    --comparable-group "$GROUP" --output $role/raw/bench_dialect_baseline.json \
    > $role/raw/bench_dialect_baseline.txt
  python "$REPO/scripts/bench_artifact.py" export $role/raw/bench_dialect_baseline.json \
    --log $role/raw/bench_dialect_baseline.txt --output $role/manifest.json
done
python "$REPO/scripts/bench_artifact.py" compare baseline/manifest.json candidate/manifest.json \
  --source-repo "$REPO" --output compare.json | tee compare.txt
