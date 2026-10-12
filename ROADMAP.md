# Roadmap

> **Last updated**: 2026-10-13
>
> This roadmap reflects current priorities. The released version is the newest
> dated version entry in [CHANGELOG.md](CHANGELOG.md) (below `[Unreleased]`) and the
> latest release on [PyPI](https://pypi.org/project/sqlalchemy-cubrid/); supported Python, SQLAlchemy,
> CUBRID and driver versions are kept in
> [docs/SUPPORT_MATRIX.md](docs/SUPPORT_MATRIX.md), which this page does not repeat.
> For the ecosystem-wide view, see the
> [CUBRID Labs Ecosystem Roadmap](https://github.com/cubrid-lab/.github/blob/main/ROADMAP.md).

## Links

- 📋 [GitHub Milestones](https://github.com/cubrid-lab/sqlalchemy-cubrid/milestones)
- 🗂️ [Org Project Board](https://github.com/orgs/cubrid-lab/projects/2)
- 🌐 [Ecosystem Roadmap](https://github.com/cubrid-lab/.github/blob/main/ROADMAP.md)

## Current Focus — Stable Maintenance & Polish

- Documentation accuracy and consistency across README / docs / AI-facing project files
- Continued SQLAlchemy 2.0–2.1 hardening while forward-testing against post-2.1 pre-releases
- Reflection/autogenerate polish and benchmark-driven performance tuning

## Next — Performance & Ecosystem

- Performance work driven by measurements: the same-CUBRID baseline of 2026-10-12 in
  [docs/PERFORMANCE.md](docs/PERFORMANCE.md#current-baseline-2026-10-12) is the reference
  for later comparisons (#830)
- Ecosystem examples and cookbook expansion
- SQLAlchemy 2.1 is released and tested (CI pins 2.1.1); forward-compatibility investigation continues for SA 2.2+ pre-releases via the non-gating canary CI job

## Compatibility

See [docs/SUPPORT_MATRIX.md](docs/SUPPORT_MATRIX.md) for the supported Python,
SQLAlchemy, CUBRID and driver versions and their caveats; package metadata
(`pyproject.toml`) owns the dependency bounds.

## Completed

### Python 3.15 support (1.11.0, published 2026-10-12)

- 1.11.0 declares Python 3.15 (#666): classifier, tox, full release matrix (Python
  3.11–3.15 × CUBRID 10.2–11.4), 3.15 as the newest offline endpoint and
  English/Korean supported-version docs. Standard GIL builds only; no free-threaded
  claim. `requires-python` stays `>=3.11`.
- The pycubrid routes depend on the pycubrid release that declares 3.15; the
  `[pycubrid]` floor is unchanged. The official CUBRIDdb build is assessed
  separately: it builds on `ubuntu-latest`, and GCC 14 breaks it on Python 3.14 and
  3.15 alike, the two versions compared (see `docs/DRIVER_COMPAT.md`).
- Preparation history: on 2026-10-03, 3.15.0rc3 was a preview
  ([upstream release notes](https://www.python.org/downloads/release/python-3150rc3/)).
  A manually dispatched Ubuntu/standard-GIL preview lane (`python-canary.yml`)
  checked offline regressions and fresh wheel/sdist installations; it is kept as
  a manual packaging check.

### Python 3.10 retirement (1.10.0, published 2026-10-09)

Decisions as recorded on 2026-10-02, with the outcome:

- Upstream Python 3.10 support ended on 2026-10-01 ([PEP 619](https://peps.python.org/pep-0619/#310-lifespan)).
- 1.8.x and 1.9.x: Python >=3.10 is the installation requirement.
- 1.9.0 (published 2026-10-04): carried the advance notice in CHANGELOG Deprecated
  and the support matrix; Python 3.10 stays supported throughout the 1.9.x line.
- 1.10.0 (published 2026-10-09) made the removal: package metadata requires Python
  >=3.11, the 3.10 classifier is removed and CI matrices start at 3.11 (#686).
  Tooling targets and the remaining documentation followed in the child issues of
  #685. On Python 3.10, `pip` keeps installing 1.9.x.

### Async Dialect Support
- `cubrid+aiopycubrid://` URL scheme via `PyCubridAsyncDialect`
- Full `create_async_engine` / `AsyncSession` support
- Requires pycubrid >= 1.8.0,<2.0 with async module

### JSON Type Support
- Native JSON type with `JSON_EXTRACT`-based path expressions
- `col["key"]` and `col[("a", "b")]` indexing compiled to CUBRID SQL
- Full colspecs/ischema_names integration for reflection
