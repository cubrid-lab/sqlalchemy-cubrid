# Third-Party Software Licenses

This file records the third-party open-source software that **sqlalchemy-cubrid**
depends on, by install scope, and what sqlalchemy-cubrid itself distributes. It
is an engineering inventory, not legal advice.

## Install scopes

Each scope has a different support and distribution boundary, so each has its
own table below:

| Scope | Installed by | Purpose |
|---|---|---|
| Default runtime | `pip install sqlalchemy-cubrid` | Always installed |
| `[pycubrid]` | `pip install "sqlalchemy-cubrid[pycubrid]"` | Pure-Python driver (recommended) |
| `[alembic]` | `pip install "sqlalchemy-cubrid[alembic]"` | Alembic migrations |
| `[cubrid]` / `[cubriddb]` | `pip install "sqlalchemy-cubrid[cubrid]"` | Legacy C-extension driver CUBRID-Python |
| `[dev]` | `pip install -e ".[dev]"` | Contributors' development and test toolchain |

None of the extras is installed by default.

**greenlet.** SQLAlchemy 2.1 no longer installs `greenlet` by default; it comes
with `sqlalchemy[asyncio]`, which the `[pycubrid]` and `[dev]` extras request.
The declared range `sqlalchemy>=2.0,<2.2` also admits SQLAlchemy 2.0.x, whose
default install adds `greenlet` (MIT AND PSF-2.0) on common platforms. Either
way the license is the one listed in the `[pycubrid]` table.

> **CUBRID server license, for the record.** The CUBRID server engine is
> distributed under Apache License 2.0 and the official APIs/connectors under
> BSD (upstream `COPYING`, http://www.cubrid.org/cubrid) — the frequently cited
> GPL v2+ no longer applies. This project is an independent wire-protocol client
> that neither includes nor links any CUBRID server code; the `cubrid/cubrid`
> Docker image is used for CI verification only.

## What sqlalchemy-cubrid distributes

- **Wheel**: only the `sqlalchemy_cubrid` package, the `_sqlalchemy_cubrid_alembic`
  plugin module and their metadata, plus `LICENSE`, `NOTICE` and `AUTHORS`. No
  source file carries a third-party copyright notice, and no third-party source
  code or asset is vendored.
- **Source distribution**: the same files, project metadata (`README.md`,
  `pyproject.toml`, `setup.cfg`) and the `test/test_*.py` modules.
- **Dependencies** in every scope are installed by users or contributors from
  PyPI. sqlalchemy-cubrid declares them; it does not bundle or redistribute
  them. In particular, the `[cubrid]` extra only lets this dialect *run on top
  of* the separately installed CUBRID-Python driver, as `docs/ARCHITECTURE.md`
  (Provenance) and `NOTICE` state.

## License categories

- **Permissive**: MIT, MIT-0, BSD-2-Clause, BSD-3-Clause, Apache-2.0 and the
  Python Software Foundation License, as declared by each package. The generator
  also accepts ISC, 0BSD, Unlicense, Public Domain and a generic "BSD" or "BSD
  License" declaration as permissive. Most packages fall here.
- **Weak (file-level) copyleft: MPL**: `certifi`, `hypothesis`, `pathspec`, all
  MPL-2.0 and all in the `[dev]` scope only. MPL-2.0 is not a permissive
  license. Its obligations attach to the MPL-covered files themselves: anyone
  distributing those files, modified or not, must make their source available
  under MPL-2.0 and keep their notices. Because MPL-2.0 is file-level, it never
  extends to this project's own files (MPL §3.3, "Larger Work"). Separately,
  sqlalchemy-cubrid does not distribute these packages, so their distribution
  obligations do not arise for this project.
- **Needs review**: any package whose metadata mentions a GPL-family license, or
  a license the generator cannot fully classify. Multiple license classifiers do
  not say whether they combine as "or" or "and", so these are never treated as
  permissive automatically. Each one is resolved below.

No strong-copyleft license (GPL, LGPL or AGPL) applies to any installed file in
these inventories.

### Reviewed entries

- **docutils** (0.23, `[dev]` only, pulled in by `twine` through
  `readme_renderer`). Its metadata carries Public Domain, BSD and GPL
  classifiers. Its `COPYING.rst` places most files in the public domain, with
  BSD-2-Clause exceptions including `docutils/utils/math/latex2mathml.py`,
  `docutils/__main__.py` and `docutils/utils/math/math2html.py` (relicensed from
  GPL-3.0+ to BSD-2-Clause for Docutils). `docutils/utils/smartquotes.py` also
  carries the original SmartyPants BSD-3-Clause notice, and
  `docutils/utils/_roman_numerals.py` is public domain or 0BSD (per its file
  header). The one GPL-3.0+ file it lists, `tools/editors/emacs/rst.el`, is not
  part of the installed package. As installed, docutils is therefore public
  domain plus permissive BSD terms (BSD-2-Clause, BSD-3-Clause and 0BSD).
- **CUBRID-Python** (`[cubrid]` / `[cubriddb]` only). Its installed metadata
  declares `License: BSD`, with no license classifier and no license file; in
  the 9.3.0.1 sdist that value comes from `license = "BSD"` in `setup_2.py` and
  `setup_3.py`. The upstream `CUBRID/cubrid-python` repository ships no LICENSE
  file, and the wrapper's own files carry no license headers. The sdist also
  bundles the CCI client library (`cci-src/`), which the driver links into its
  binary (statically on Linux and Windows). CCI's own `cci-src/COPYING`
  (Copyright (C) 2008-2014 Search Solution Corporation) states "CUBRID APIs and
  Connectors under BSD 3-Clause License". CUBRID-Python is such a connector from
  the same copyright holder, so the evidence points to BSD-3-Clause, but that is
  an inference: no notice in the wrapper's own files or metadata states the
  variant. Whether this means
  BSD-2-Clause or BSD-3-Clause is **unresolved**: this document records it as
  "BSD, variant unspecified" and does not infer one. The generator's
  "Permissive" category for this row reflects only that every BSD variant is
  permissive.

## How the inventories were generated

The tables are a snapshot of concrete versions observed in fresh environments.
The allowed version ranges are the ones declared in `pyproject.toml`, which
remains authoritative.

- Dependency declarations: commit `e66ca4b179fe1c0cfc35a955835644595760ce61`
- Environment: CPython 3.12.13 on Linux x86_64 (glibc 2.35), uv 0.11.7,
  generated 2026-10-09
- Commands (one fresh environment per scope; `--exclude sqlalchemy-cubrid` drops
  the project itself):

```bash
uv venv -p 3.12 /tmp/tpl-runtime
uv pip install -p /tmp/tpl-runtime/bin/python .
/tmp/tpl-runtime/bin/python scripts/generate_third_party_licenses.py --exclude sqlalchemy-cubrid

# Repeat with a fresh environment for each extra:
#   .[pycubrid]  .[alembic]  .[cubrid]  .[dev]
uv venv -p 3.12 /tmp/tpl-dev
uv pip install -p /tmp/tpl-dev/bin/python ".[dev]"
/tmp/tpl-dev/bin/python scripts/generate_third_party_licenses.py --exclude sqlalchemy-cubrid
```

`scripts/generate_third_party_licenses.py` uses only the standard library and
is shared with pycubrid. It reads the PEP 639 `License-Expression` field, then
`License ::` classifiers, then a short `License` field, and never guesses a
license. `test/test_third_party_licenses.py` fails when a dependency declared
in `pyproject.toml` is missing from its scope's table, when a recorded version
falls outside a declared version range, when a row's category disagrees with
what the generator would assign to its license, or when a reviewed entry loses
its row or its review. Exact `==` pins are checked for presence only: they are
authoritative in `pyproject.toml`, so a routine pin bump does not require
regenerating this snapshot. Transitive rows are kept accurate by regenerating
the tables, not by the test.

## Default runtime (2 packages)

| Name | Version | License | Category | URL |
|---|---|---|---|---|
| SQLAlchemy | 2.1.4 | MIT | Permissive | https://www.sqlalchemy.org |
| typing_extensions | 4.16.0 | PSF-2.0 | Permissive | https://github.com/python/typing_extensions |

## `[pycubrid]` extra (4 packages)

| Name | Version | License | Category | URL |
|---|---|---|---|---|
| greenlet | 3.5.6 | MIT AND PSF-2.0 | Permissive | https://greenlet.readthedocs.io |
| pycubrid | 1.9.0 | MIT | Permissive | https://github.com/cubrid-lab/pycubrid |
| SQLAlchemy | 2.1.4 | MIT | Permissive | https://www.sqlalchemy.org |
| typing_extensions | 4.16.0 | PSF-2.0 | Permissive | https://github.com/python/typing_extensions |

## `[alembic]` extra (5 packages)

| Name | Version | License | Category | URL |
|---|---|---|---|---|
| alembic | 1.20.0 | MIT | Permissive | https://alembic.sqlalchemy.org |
| Mako | 1.4.3 | MIT | Permissive | https://www.makotemplates.org/ |
| MarkupSafe | 3.0.4 | BSD-3-Clause | Permissive | https://github.com/pallets/markupsafe/ |
| SQLAlchemy | 2.1.4 | MIT | Permissive | https://www.sqlalchemy.org |
| typing_extensions | 4.16.0 | PSF-2.0 | Permissive | https://github.com/python/typing_extensions |

## `[cubrid]` / `[cubriddb]` extra (3 packages)

| Name | Version | License | Category | URL |
|---|---|---|---|---|
| CUBRID-Python | 9.3.0.1 | BSD | Permissive | http://svn.cubrid.org/cubridapis/python/ |
| SQLAlchemy | 2.1.4 | MIT | Permissive | https://www.sqlalchemy.org |
| typing_extensions | 4.16.0 | PSF-2.0 | Permissive | https://github.com/python/typing_extensions |

## Development / test dependencies: `[dev]` (73 packages, not distributed)

| Name | Version | License | Category | URL |
|---|---|---|---|---|
| alembic | 1.20.0 | MIT | Permissive | https://alembic.sqlalchemy.org |
| ast_serialize | 0.12.1 | MIT | Permissive | https://github.com/mypyc/ast_serialize |
| bandit | 1.9.4 | Apache-2.0 | Permissive | https://github.com/PyCQA/bandit |
| build | 1.6.1 | MIT | Permissive | https://build.pypa.io |
| cachetools | 7.2.1 | MIT | Permissive | https://github.com/tkem/cachetools/ |
| cffi | 2.1.1 | MIT-0 | Permissive | https://github.com/python-cffi/cffi |
| cfgv | 3.5.0 | MIT | Permissive | https://github.com/asottile/cfgv |
| charset-normalizer | 3.5.2 | MIT | Permissive | - |
| click | 8.5.0 | BSD-3-Clause | Permissive | https://github.com/pallets/click/ |
| colorama | 0.4.6 | BSD License | Permissive | https://github.com/tartley/colorama |
| coverage | 7.16.2 | Apache-2.0 | Permissive | https://github.com/coveragepy/coveragepy |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | Permissive | https://github.com/pyca/cryptography |
| distlib | 0.4.3 | Python Software Foundation License | Permissive | https://github.com/pypa/distlib |
| filelock | 4.0.12 | MIT | Permissive | https://github.com/tox-dev/py-filelock |
| greenlet | 3.5.6 | MIT AND PSF-2.0 | Permissive | https://greenlet.readthedocs.io |
| id | 1.6.1 | Apache Software License | Permissive | https://pypi.org/project/id/ |
| identify | 2.6.20 | MIT | Permissive | https://github.com/pre-commit/identify |
| idna | 3.20 | BSD-3-Clause | Permissive | https://github.com/kjd/idna |
| iniconfig | 2.3.1 | MIT | Permissive | https://github.com/pytest-dev/iniconfig |
| jaraco.classes | 3.4.0 | MIT License | Permissive | https://github.com/jaraco/jaraco.classes |
| jaraco.context | 6.1.2 | MIT | Permissive | https://github.com/jaraco/jaraco.context |
| jaraco.functools | 4.6.0 | MIT | Permissive | https://github.com/jaraco/jaraco.functools |
| jeepney | 0.9.0 | MIT | Permissive | https://gitlab.com/takluyver/jeepney |
| keyring | 25.7.0 | MIT | Permissive | https://github.com/jaraco/keyring |
| libcst | 1.9.0 | MIT License | Permissive | - |
| librt | 0.16.0 | MIT | Permissive | https://github.com/mypyc/librt |
| linkify-it-py | 2.2.0 | MIT License | Permissive | https://github.com/tsutsu3/linkify-it-py |
| Mako | 1.4.3 | MIT | Permissive | https://www.makotemplates.org/ |
| markdown-it-py | 4.2.0 | MIT License | Permissive | https://github.com/executablebooks/markdown-it-py |
| MarkupSafe | 3.0.4 | BSD-3-Clause | Permissive | https://github.com/pallets/markupsafe/ |
| mdit-py-plugins | 0.6.1 | MIT License | Permissive | https://github.com/executablebooks/mdit-py-plugins |
| mdurl | 0.1.2 | MIT License | Permissive | https://github.com/executablebooks/mdurl |
| more-itertools | 11.1.0 | MIT | Permissive | https://github.com/more-itertools/more-itertools |
| mutmut | 3.8.0 | BSD-3-Clause | Permissive | https://github.com/boxed/mutmut |
| mypy | 2.4.0 | MIT | Permissive | https://www.mypy-lang.org/ |
| mypy_extensions | 1.1.0 | MIT | Permissive | https://github.com/python/mypy_extensions |
| nh3 | 0.3.7 | MIT | Permissive | https://github.com/messense/nh3 |
| nodeenv | 1.11.0 | BSD License | Permissive | https://github.com/ekalinin/nodeenv |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | Permissive | https://github.com/pypa/packaging |
| platformdirs | 4.12.4 | MIT | Permissive | https://github.com/tox-dev/platformdirs |
| pluggy | 1.6.0 | MIT License | Permissive | - |
| pre_commit | 4.6.2 | MIT | Permissive | https://github.com/pre-commit/pre-commit |
| pycparser | 3.1 | BSD-3-Clause | Permissive | https://github.com/eliben/pycparser |
| Pygments | 2.21.0 | BSD-2-Clause | Permissive | https://pygments.org |
| pyproject-api | 1.11.4 | MIT | Permissive | https://pyproject-api.readthedocs.io |
| pyproject_hooks | 1.3.3 | MIT | Permissive | https://github.com/pypa/pyproject-hooks |
| pytest | 9.1.1 | MIT | Permissive | https://docs.pytest.org/en/latest/ |
| pytest-asyncio | 1.4.0 | Apache-2.0 | Permissive | https://github.com/pytest-dev/pytest-asyncio |
| pytest-cov | 7.1.0 | MIT | Permissive | - |
| python-discovery | 1.6.1 | MIT License | Permissive | https://github.com/tox-dev/python-discovery |
| PyYAML | 6.0.3 | MIT License | Permissive | https://github.com/yaml/pyyaml |
| readme_renderer | 46.0 | Apache-2.0 | Permissive | https://github.com/pypa/readme_renderer |
| requests | 2.34.2 | Apache Software License | Permissive | https://github.com/psf/requests |
| requests-toolbelt | 1.0.0 | Apache Software License | Permissive | https://github.com/requests/toolbelt |
| rfc3986 | 2.0.0 | Apache Software License | Permissive | http://rfc3986.readthedocs.io |
| rich | 15.0.0 | MIT License | Permissive | https://github.com/Textualize/rich |
| ruff | 0.16.10 | MIT | Permissive | https://github.com/astral-sh/ruff |
| SecretStorage | 3.5.0 | BSD-3-Clause | Permissive | https://github.com/mitya57/secretstorage |
| setproctitle | 1.3.8 | BSD-3-Clause | Permissive | https://github.com/dvarrazzo/py-setproctitle |
| sortedcontainers | 2.4.0 | Apache Software License | Permissive | http://www.grantjenks.com/docs/sortedcontainers/ |
| SQLAlchemy | 2.1.4 | MIT | Permissive | https://www.sqlalchemy.org |
| stevedore | 5.9.1 | Apache-2.0 | Permissive | https://docs.openstack.org/stevedore |
| textual | 8.2.8 | MIT License | Permissive | https://github.com/Textualize/textual |
| tomli_w | 1.2.0 | MIT License | Permissive | https://github.com/hukkin/tomli-w |
| tox | 4.64.10 | MIT | Permissive | https://tox.wiki |
| twine | 7.0.0 | Apache-2.0 | Permissive | https://twine.readthedocs.io/ |
| typing_extensions | 4.16.0 | PSF-2.0 | Permissive | https://github.com/python/typing_extensions |
| urllib3 | 2.8.0 | MIT | Permissive | - |
| virtualenv | 21.14.6 | MIT | Permissive | https://github.com/pypa/virtualenv |
| certifi | 2026.7.22 | Mozilla Public License 2.0 (MPL 2.0) | Weak copyleft (MPL) | https://github.com/certifi/python-certifi |
| hypothesis | 6.168.5 | MPL-2.0 | Weak copyleft (MPL) | https://hypothesis.works |
| pathspec | 1.1.1 | Mozilla Public License 2.0 (MPL 2.0) | Weak copyleft (MPL) | https://github.com/cpburnz/python-pathspec |
| docutils | 0.23 | BSD License / GNU General Public License (GPL) / Public Domain | Needs review | https://docutils.sourceforge.io |
