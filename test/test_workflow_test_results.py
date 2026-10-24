"""CI publishes and uploads test results on success and failure (#1021).

The offline lanes (``offline-tests`` in ci.yml and its release copy ``offline-endpoints``
in integration-full.yml) write JUnit, coverage and ``summary.json`` under
``test-results/offline/``, append the summary to the job summary and upload the
directory. The jobs that run integration tests upload the pytest logs they already
write. Every one of those steps runs with ``if: always()``. Test selection, the
coverage floor and the permissions are unchanged.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"
UPLOAD = "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9"
SHA_PIN = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")

OFFLINE = [("ci.yml", "offline-tests"), ("integration-full.yml", "offline-endpoints")]
# (workflow, job, log files the artifact carries, matrix keys its name must carry)
LOGS = [
    ("ci.yml", "make-integration", ["make-integration.log", "test-results/integration/"], []),
    (
        "ci.yml",
        "integration-tests",
        ["integration.log", "async-integration.log", "pycubrid-sync-integration.log", "regression.log"],
        ["python-version", "cubrid-version"],
    ),
    (
        "integration-full.yml",
        "integration-full",
        [
            "integration.log",
            "async-integration.log",
            "pycubrid-sync-integration.log",
            "regression.log",
            "show-create-table.log",
        ],
        ["python-version", "cubrid-version"],
    ),
    ("integration-full.yml", "make-integration", ["make-integration.log", "test-results/integration/"], ["driver", "cubrid-version"]),
]  # fmt: skip


def _steps(wf: str, job: str) -> list[dict[str, Any]]:
    data = yaml.safe_load((WORKFLOWS / wf).read_text(encoding="utf-8"))
    return list(data["jobs"][job]["steps"])


def _named(steps: list[dict[str, Any]], name: str) -> dict[str, Any]:
    return next(s for s in steps if s.get("name") == name)


def _uploads(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [s for s in steps if str(s.get("uses", "")).startswith("actions/upload-artifact@")]


@pytest.mark.parametrize(("wf", "job"), OFFLINE)
def test_offline_lane_keeps_its_selection_and_coverage_floor(wf: str, job: str) -> None:
    run = _named(_steps(wf, job), "Run offline tests with coverage")["run"]
    flat = " ".join(run.replace("\\\n", " ").split())
    assert 'pytest test/ -m "not integration and not repo" -v' in flat
    assert "--cov=sqlalchemy_cubrid" in run and "--cov-fail-under=95" in run
    assert "--junitxml=test-results/offline/junit.xml" in run
    assert "--cov-report=xml:test-results/offline/coverage.xml" in run


@pytest.mark.parametrize(("wf", "job"), OFFLINE)
def test_offline_lane_writes_publishes_and_uploads_on_every_run(wf: str, job: str) -> None:
    steps = _steps(wf, job)
    names = [s.get("name") for s in steps]
    run = names.index("Run offline tests with coverage")
    assert steps[run]["id"] == "offline"
    write = _named(steps, "Write test results summary")
    publish = _named(steps, "Publish test results summary")
    upload = _named(steps, "Upload test results")
    assert (
        run
        < names.index("Write test results summary")
        < names.index("Publish test results summary")
        < names.index("Upload test results")
    )
    for step in (write, publish, upload):
        assert step["if"] == "always()"
    assert write["env"]["PYTEST_OUTCOME"] == "${{ steps.offline.outcome }}"
    assert "--threshold 95" in write["run"]
    assert "test-results/offline/summary.json" in write["run"]
    assert publish["run"].rstrip().endswith('>> "$GITHUB_STEP_SUMMARY"')
    assert "step-summary --summary test-results/offline/summary.json" in publish["run"]
    assert upload["uses"].startswith(UPLOAD) and SHA_PIN.match(upload["uses"].split()[0])
    assert upload["with"] == {
        "name": "test-results-offline-py${{ matrix.python-version }}",
        "path": "test-results/",
        "retention-days": 7,
        "if-no-files-found": "warn",
    }


def test_release_copy_of_the_offline_lane_matches_ci() -> None:
    ci = _steps("ci.yml", "offline-tests")
    full = _steps("integration-full.yml", "offline-endpoints")
    for name in (
        "Run offline tests with coverage",
        "Write test results summary",
        "Publish test results summary",
        "Upload test results",
    ):
        assert _named(full, name) == _named(ci, name), name


@pytest.mark.parametrize(
    ("wf", "job", "files", "keys"),
    [pytest.param(*entry, id=f"{entry[0]}:{entry[1]}") for entry in LOGS],
)
def test_integration_jobs_upload_their_pytest_logs_on_every_run(
    wf: str, job: str, files: list[str], keys: list[str]
) -> None:
    steps = _steps(wf, job)
    upload = _named(steps, "Upload pytest logs")
    assert upload["uses"].startswith(UPLOAD) and SHA_PIN.match(upload["uses"].split()[0])
    assert upload["if"] == "always()"
    assert upload["with"]["path"].split() == files
    assert upload["with"]["retention-days"] == 7
    assert upload["with"]["if-no-files-found"] == "warn"
    assert upload["with"]["name"].startswith("pytest-logs-")
    for key in keys:  # one artifact per matrix entry, or entries would collide
        assert f"matrix.{key}" in upload["with"]["name"]
    # The log is written before it is uploaded: the upload comes after every step that tees it.
    producers = [
        i for i, s in enumerate(steps) if ".log" in str(s.get("run", "")) and "tee " in s["run"]
    ]
    assert producers and steps.index(upload) > max(producers)


# The workflow-level permissions as they were before #1021; the caller sets integration-full's.
PERMISSIONS = {
    "ci.yml": {"contents": "read", "pull-requests": "read"},
    "integration-full.yml": None,
}


@pytest.mark.parametrize("wf", ["ci.yml", "integration-full.yml"])
def test_every_new_upload_is_pinned_and_no_permissions_were_added(wf: str) -> None:
    data = yaml.safe_load((WORKFLOWS / wf).read_text(encoding="utf-8"))
    assert data.get("permissions") == PERMISSIONS[wf]
    for name, job in data["jobs"].items():
        assert "permissions" not in job, name
        for upload in _uploads(job.get("steps", [])):
            assert SHA_PIN.match(upload["uses"].split()[0]), (name, upload["uses"])
