#!/bin/bash
# Commands of the 2026-10-13 follow-up to the dialect baseline (#830): the same
# scripts/bench_dialect_baseline.py on CUBRID 10.2, 11.0, 11.2 and 11.4, through
# cubrid+pycubrid://, cubrid:// (CUBRIDdb) and cubrid+aiopycubrid://, with the
# concurrency workload at 1, 4 and 8 connections. One server runs at a time.
# Set the two variables, then run from this directory. Results land in raw/;
# `python aggregate.py` then writes summary.json.
#
# Measured with REPO checked out at the commit recorded as source_sha in every raw
# JSON file, on these images (docker image inspect --format '{{.Id}}'):
#   cubrid/cubrid:10.2 sha256:fee7c63b57159bed0827588b5678c611beec6dac07633cf3e13729247456b02f
#   cubrid/cubrid:11.0 sha256:b875e6b3296e5735819edff426b7cc783a089035f5b897cac6220d890f4f80a2
#   cubrid/cubrid:11.2 sha256:bbf8622a60496060cfb96095f01df27e9b2236de6d254998ecbcf05fdbe8345d
#   cubrid/cubrid:11.4 sha256:1248b77ad39888df9e064655937188ab99fe056ed7e35b57d06155a015dc1791
#
# The venv (CUBRIDdb built as in docs/DRIVER_COMPAT.md "Building CUBRIDdb from Source",
# cubrid-python v11.3.0.51 = c63ab9c51353e5c80e02dd2c1a19d4640acb29f5):
#   git clone --branch v11.3.0.51 --depth 1 --recurse-submodules \
#       https://github.com/CUBRID/cubrid-python.git
#   (cd cubrid-python/cci-src && mkdir -p build_x86_64_release && cd build_x86_64_release \
#       && cmake ../ && make -j"$(nproc)")
#   printf '#!/bin/bash\nexit 0\n' > cubrid-python/build_cci.sh
#   uv build --wheel --python 3.12 --out-dir wheel cubrid-python
#   uv venv -p 3.12 venv21 && VIRTUAL_ENV=venv21 uv pip install -e <repo> \
#       pycubrid==1.12.0 'sqlalchemy[asyncio]==2.1.4' wheel/cubrid_python-*.whl
set -euo pipefail
REPO=${REPO:?sqlalchemy-cubrid checkout}
PY=${PY:?python of the venv above}
PORT=${PORT:-33851}
R=raw
SHA=$(git -C "$REPO" rev-parse HEAD)
mkdir -p $R
for v in 10.2 11.0 11.2 11.4; do
  name=clsa-bench-${v//./}
  docker rm -f -v "$name" >/dev/null 2>&1 || true
  docker run -d --name "$name" -e CUBRID_DB=testdb -p 127.0.0.1:$PORT:33000 cubrid/cubrid:$v
  (cd "$REPO" && CUBRID_TEST_URL="cubrid+pycubrid://dba@localhost:$PORT/testdb" \
    "$PY" -m scripts.wait_for_cubrid --timeout 300)
  for d in pycubrid cubriddb aiopycubrid; do
    case $d in
      pycubrid) dsn="cubrid+pycubrid://dba@localhost:$PORT/testdb" ;;
      cubriddb) dsn="cubrid://dba@localhost:$PORT/testdb" ;;
      aiopycubrid) dsn="cubrid+aiopycubrid://dba@localhost:$PORT/testdb" ;;
    esac
    "$PY" -I "$REPO/scripts/bench_dialect_baseline.py" --dsn "$dsn" --trials 5 \
      --concurrency 1,4,8 --source-sha "$SHA" \
      --output "$R/bench_dialect_baseline_cubrid${v//./}_$d.json" \
      > "$R/bench_dialect_baseline_cubrid${v//./}_$d.txt"
  done
  docker rm -f -v "$name" >/dev/null
done
