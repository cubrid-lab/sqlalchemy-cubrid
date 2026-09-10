# Third-Party Software Licenses

This file lists the third-party open-source software involved in building and testing **sqlalchemy-cubrid**.

Optional extras: `[alembic]` adds Alembic (MIT) and Mako (MIT); `[cubrid]`/`[cubriddb]` add the legacy C-extension driver CUBRID-Python (BSD; per PyPI metadata `license=BSD` and the package's setup.py declaration — the upstream cubrid/cubrid-python repository ships no LICENSE file or license headers, so 2- vs 3-Clause is unspecified). Neither extra is installed by default.

> **CUBRID server license, for the record.** The CUBRID server engine is
> distributed under Apache License 2.0 and the official APIs/connectors under
> BSD (upstream `COPYING`, http://www.cubrid.org/cubrid) — the frequently cited
> GPL v2+ no longer applies. This project is an independent wire-protocol client
> that neither includes nor links any CUBRID server code; the `cubrid/cubrid`
> Docker image is used for CI verification only.
All listed dependencies are distributed under permissive licenses (MIT, BSD-2/3-Clause, Apache-2.0, ISC, PSF, MPL-2.0). No dependency is copyleft/GPL, and none conflicts with this project's MIT license. MPL-2.0 packages appear in the development toolchain only and are not distributed with the package.

## Runtime dependencies (default install)

| Name              | Version | License         | URL                                             |
|-------------------|---------|-----------------|-------------------------------------------------|
| SQLAlchemy        | 2.0.52  | MIT             | https://www.sqlalchemy.org                      |
| greenlet          | 3.5.5   | MIT AND PSF-2.0 | https://greenlet.readthedocs.io                 |
| typing_extensions | 4.16.0  | PSF-2.0         | https://github.com/python/typing_extensions     |
