# Performance guide

> Moved from the root [AGENTS.md](../../AGENTS.md) (#907). Owner: sqlalchemy-cubrid maintainers.
> Every rule in the root file still applies. Scope: Where performance guidance, measurements and priorities live.

## Performance Context

sqlalchemy-cubrid provides ORM-level validation that pycubrid driver improvements reach
the application layer. [docs/PERFORMANCE.md](../PERFORMANCE.md) holds user-facing
performance guidance, known limitations and how to run the local measurement scripts
(`scripts/bench_compile.py`, `scripts/profile_orm.py`, `scripts/bench_dialect_baseline.py`).
Reproducible and published performance experiments belong in
[cubrid-benchmark](https://github.com/cubrid-lab/cubrid-benchmark); do not add dated
benchmark results, a result-artifact format or a performance gate to this repository (#1290).
Current priorities live in [ROADMAP.md](../../ROADMAP.md), not here.
