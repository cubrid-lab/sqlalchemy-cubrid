# test/test_report_driver_versions.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Offline checks for the CI driver-version report (#851)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import report_driver_versions


def test_collect_reports_missing_package_and_unset_url_without_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    versions = {
        "sqlalchemy-cubrid": "1.2.3",
        "SQLAlchemy": "2.1.1",
        "cubrid_python": "11.3.0.51",
    }

    def package_version(dist: str) -> str:
        if dist == "pycubrid":
            raise report_driver_versions.PackageNotFoundError(dist)
        return versions[dist]

    def unexpected_create_engine(*args: object, **kwargs: object) -> None:
        pytest.fail(f"create_engine called with {args!r}, {kwargs!r}")

    monkeypatch.setattr(report_driver_versions, "version", package_version)
    monkeypatch.setattr(report_driver_versions, "create_engine", unexpected_create_engine)
    monkeypatch.setattr(report_driver_versions, "_cubrid_build_version", lambda: "11.3.0.0001")
    monkeypatch.delenv("CUBRID_TEST_URL", raising=False)
    monkeypatch.setenv("CUBRIDDB_SOURCE_REF", "v0.0.0-test")

    rows = report_driver_versions.collect()

    assert rows[1:] == [
        ("sqlalchemy-cubrid", "1.2.3"),
        ("SQLAlchemy", "2.1.1"),
        ("pycubrid", "not installed"),
        ("CUBRIDdb (cubrid_python)", "11.3.0.51"),
        ("CUBRIDdb _cubrid.__version__", "11.3.0.0001"),
        ("CUBRIDdb source ref", "v0.0.0-test"),
        ("CUBRID server via pycubrid", "CUBRID_TEST_URL not set"),
        ("CUBRID server via CUBRIDdb", "CUBRID_TEST_URL not set"),
    ]


def test_server_probe_failure_reports_only_exception_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    password = "never-print-this-password"

    class CredentialProbeError(RuntimeError):
        pass

    class FailingConnection:
        def __enter__(self) -> None:
            raise CredentialProbeError(f"failed for dba:{password}")

        def __exit__(self, *args: object) -> None:
            return None

    class FakeEngine:
        disposed = False

        def connect(self) -> FailingConnection:
            return FailingConnection()

        def dispose(self) -> None:
            self.disposed = True

    engine = FakeEngine()
    monkeypatch.setattr(report_driver_versions, "create_engine", lambda url: engine)

    result = report_driver_versions._server_version(
        f"cubrid+pycubrid://dba:{password}@localhost:33000/testdb", "cubrid+pycubrid"
    )

    assert result == "unavailable (CredentialProbeError)"
    assert password not in result
    assert engine.disposed is True


def test_server_probe_engine_creation_failure_reports_only_exception_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    password = "never-print-this-password"

    class CredentialSetupError(RuntimeError):
        pass

    def fail_create_engine(url: object) -> None:
        raise CredentialSetupError(f"failed for dba:{password} at {url!r}")

    monkeypatch.setattr(report_driver_versions, "create_engine", fail_create_engine)

    result = report_driver_versions._server_version(
        f"cubrid+pycubrid://dba:{password}@localhost:33000/testdb", "cubrid+pycubrid"
    )

    assert result == "unavailable (CredentialSetupError)"
    assert password not in result


def test_main_appends_readable_step_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rows = [
        ("Python", "3.12.0 (CPython)"),
        ("CUBRID server via pycubrid", "unavailable (ProbeError)"),
    ]
    summary = tmp_path / "summary.md"
    summary.write_text("Existing summary\n\n", encoding="utf-8")
    monkeypatch.setattr(report_driver_versions, "collect", lambda: rows)
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("VERSION_REPORT_TITLE", "Driver provenance")

    assert report_driver_versions.main() == 0

    assert capsys.readouterr().out == (
        "Python: 3.12.0 (CPython)\nCUBRID server via pycubrid: unavailable (ProbeError)\n"
    )
    assert summary.read_text(encoding="utf-8") == (
        "Existing summary\n\n"
        "### Driver provenance\n\n"
        "| Component | Version |\n"
        "|---|---|\n"
        "| Python | `3.12.0 (CPython)` |\n"
        "| CUBRID server via pycubrid | `unavailable (ProbeError)` |\n\n"
    )


@pytest.mark.parametrize(
    ("module", "expected"),
    [
        (type("Ext", (), {"__version__": b"9.3.0.0001"}), "9.3.0.0001"),
        (type("Ext", (), {"__version__": "11.3.0.0001"}), "11.3.0.0001"),
        (type("Ext", (), {}), "unknown"),
        (None, "not installed"),
    ],
    ids=["pypi-bytes", "source-str", "no-version", "missing"],
)
def test_cubrid_build_version_tells_the_driver_lines_apart(
    monkeypatch: pytest.MonkeyPatch, module: object, expected: str
) -> None:
    """The PyPI 9.3.0 release and a v11.3.0.51 build differ in _cubrid.__version__ (#1146)."""

    def import_module(name: str) -> object:
        assert name == "_cubrid"
        if module is None:
            raise ImportError(name)
        return module

    monkeypatch.setattr(report_driver_versions.importlib, "import_module", import_module)
    assert report_driver_versions._cubrid_build_version() == expected
