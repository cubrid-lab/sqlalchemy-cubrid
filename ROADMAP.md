# Roadmap

> **Last updated**: 2026-10-02
>
> This roadmap reflects current priorities. For the ecosystem-wide view, see the
> [CUBRID Labs Ecosystem Roadmap](https://github.com/cubrid-lab/.github/blob/main/ROADMAP.md).

## Python 3.10 retirement schedule

- Upstream Python 3.10 support ended on 2026-10-01 ([PEP 619](https://peps.python.org/pep-0619/#310-lifespan)).
- 1.8.x and 1.9.x: Python >=3.10 is the installation requirement.
- 1.9.0 (published 2026-10-04): carried the advance notice in CHANGELOG Deprecated
  and the support matrix; Python 3.10 stays supported throughout the 1.9.x line.
- Done on `main` for the next minor release (planned 1.10.0): package metadata
  requires Python >=3.11, the 3.10 classifier is removed and CI matrices start at
  3.11 (#686). Tooling targets and the remaining documentation follow in the
  child issues of #685.
- Users should migrate Python and recreate/test their virtual environment before
  upgrading to the removal release. No release date or publication is claimed.

## Python 3.15 support preparation

- As of 2026-10-03, 3.15.0rc3 is a preview; final is scheduled for 2026-10-09
  ([upstream release notes](https://www.python.org/downloads/release/python-3150rc3/)).
- Add one manually dispatched Ubuntu/standard-GIL preview lane for full offline
  regressions, distribution validation and fresh wheel/sdist installations.
  Routine PRs do not gain a matrix cell or automatic preview run.
- Before official support: record successful final-runtime/dependency, packaging,
  offline and real CUBRID integration results at the candidate SHA, including sync/async pycubrid; assess native CUBRIDdb compatibility separately.
- Then align the Python 3.15 classifier, full release matrix, local tooling where
  present, release notes and English/Korean supported-version docs in a follow-up.
  This preparation changes no official support declaration or Python minimum.

## Links

- 📋 [GitHub Milestones](https://github.com/cubrid-lab/sqlalchemy-cubrid/milestones)
- 🗂️ [Org Project Board](https://github.com/orgs/cubrid-lab/projects/2)
- 🌐 [Ecosystem Roadmap](https://github.com/cubrid-lab/.github/blob/main/ROADMAP.md)

## Current Release Line — v1.8.x — Stable Maintenance & Polish

- Documentation accuracy and consistency across README / docs / AI-facing project files
- Continued SQLAlchemy 2.0–2.1 hardening while forward-testing against post-2.1 pre-releases
- Reflection/autogenerate polish and benchmark-driven performance tuning

## Next — Performance & Ecosystem

- Performance profiling and benchmark integration
- Ecosystem examples and cookbook expansion
- SQLAlchemy 2.1 is released and tested (CI pins 2.1.1); forward-compatibility investigation continues for SA 2.2+ pre-releases via the non-gating canary CI job

## Compatibility

Python 3.10+, SQLAlchemy 2.0–2.1, CUBRID 10.2–11.4

## Completed

### Async Dialect Support
- `cubrid+aiopycubrid://` URL scheme via `PyCubridAsyncDialect`
- Full `create_async_engine` / `AsyncSession` support
- Requires pycubrid >= 1.8.0,<2.0 with async module

### JSON Type Support
- Native JSON type with `JSON_EXTRACT`-based path expressions
- `col["key"]` and `col[("a", "b")]` indexing compiled to CUBRID SQL
- Full colspecs/ischema_names integration for reflection
