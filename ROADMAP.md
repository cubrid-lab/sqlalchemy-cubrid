# Roadmap

> **Last updated**: 2026-10-02
>
> This roadmap reflects current priorities. For the ecosystem-wide view, see the
> [CUBRID Labs Ecosystem Roadmap](https://github.com/cubrid-lab/.github/blob/main/ROADMAP.md).

## Python 3.10 retirement schedule

- Upstream Python 3.10 support ended on 2026-10-01 ([PEP 619](https://peps.python.org/pep-0619/#310-lifespan)).
- Current 1.8.x: Python >=3.10 remains the installation requirement.
- Upcoming 1.9.0: publish advance notice in CHANGELOG Deprecated and the support
  matrix; keep Python 3.10 supported throughout the 1.9.x line.
- Following minor release (planned 1.10.0): require Python >=3.11 only after the
  advance-notice minor has shipped. Align package metadata, classifiers, tooling,
  CI matrices and English/Korean support documentation in a separate change.
- Users should migrate Python and recreate/test their virtual environment before
  upgrading to the removal release. No release date or publication is claimed.

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
