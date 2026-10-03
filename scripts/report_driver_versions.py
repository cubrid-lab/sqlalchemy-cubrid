"""Record the exact driver, SQLAlchemy, Python and CUBRID versions of a test lane (#486).

Prints one ``name: version`` line per component and, when ``GITHUB_STEP_SUMMARY``
is set, appends the same data as a Markdown table. The CUBRID server version is
queried through each driver from ``CUBRID_TEST_URL``; credentials are never
printed. This script only reports: the required lane's pass/fail decision stays
with the pytest guard in ``test/conftest.py``.
"""

from __future__ import annotations

import os
import platform
import sys
from importlib.metadata import PackageNotFoundError, version

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

# (label, distribution name) — CUBRIDdb is distributed as ``cubrid_python``.
_PACKAGES = (
    ("sqlalchemy-cubrid", "sqlalchemy-cubrid"),
    ("SQLAlchemy", "SQLAlchemy"),
    ("pycubrid", "pycubrid"),
    ("CUBRIDdb (cubrid_python)", "cubrid_python"),
)
_DRIVERS = (("pycubrid", "cubrid+pycubrid"), ("CUBRIDdb", "cubrid"))


def _package_version(dist: str) -> str:
    try:
        return version(dist)
    except PackageNotFoundError:
        return "not installed"


def _server_version(url: str, drivername: str) -> str:
    try:
        engine = create_engine(make_url(url).set(drivername=drivername))
    except Exception as exc:
        return f"unavailable ({type(exc).__name__})"
    try:
        with engine.connect() as conn:
            return str(conn.execute(text("SELECT VERSION()")).scalar_one())
    except Exception as exc:
        return f"unavailable ({type(exc).__name__})"
    finally:
        engine.dispose()


def collect() -> list[tuple[str, str]]:
    rows = [("Python", f"{platform.python_version()} ({platform.python_implementation()})")]
    rows += [(label, _package_version(dist)) for label, dist in _PACKAGES]
    source_ref = os.environ.get("CUBRIDDB_SOURCE_REF")
    if source_ref:  # the cubrid-python git tag CI built CUBRIDdb from
        rows.append(("CUBRIDdb source ref", source_ref))
    url = os.environ.get("CUBRID_TEST_URL")
    for label, drivername in _DRIVERS:
        server = _server_version(url, drivername) if url else "CUBRID_TEST_URL not set"
        rows.append((f"CUBRID server via {label}", server))
    return rows


def main() -> int:
    rows = collect()
    for name, value in rows:
        print(f"{name}: {value}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        title = os.environ.get("VERSION_REPORT_TITLE", "Tested versions")
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"### {title}\n\n| Component | Version |\n|---|---|\n")
            fh.writelines(f"| {name} | `{value}` |\n" for name, value in rows)
            fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
