"""Offline tests for scripts/release_summary.py (the release run summary).

Kept identical across pycubrid, sqlalchemy-cubrid and cubrid-mcp-server.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "_release_summary", ROOT / "scripts" / "release_summary.py"
)
assert _spec is not None and _spec.loader is not None
summary = importlib.util.module_from_spec(_spec)
sys.modules["_release_summary"] = summary
_spec.loader.exec_module(summary)

SHA = "a" * 40
HASHES = {"pycubrid-1.9.0-py3-none-any.whl": "1" * 64, "pycubrid-1.9.0.tar.gz": "2" * 64}


def needs(mode: str = "push", **results: Any) -> dict[str, Any]:
    detect = {
        "release": "true",
        "build": "true" if mode != "verify-only" else "false",
        "publish": "true" if mode in ("push", "resume") else "false",
        "verify": "true",
        "mode": mode,
        "version": "1.9.0",
        "tag": "v1.9.0",
        "sha": SHA,
        "tag_state": "absent",
        "reason": "release v1.9.0",
    }
    data: dict[str, Any] = {
        "detect": {"result": "success", "outputs": detect},
        "consistency": {"result": "success", "outputs": {}},
        "matrix": {"result": "success", "outputs": {}},
        "build": {"result": "success", "outputs": {"sha256": json.dumps(HASHES)}},
        "publish": {
            "result": "success" if detect["publish"] == "true" else "skipped",
            "outputs": {},
        },
        "verify-cookbook": {
            "result": "success",
            "outputs": {
                "status": "success",
                "requested_version": "1.9.0",
                "installed_version": "1.9.0",
                "artifact": "release-verification-pycubrid-v1.9.0-1-1",
            },
        },
        "require-cookbook": {"result": "success", "outputs": {}},
    }
    for name, value in results.items():
        name = name.replace("_", "-")
        if isinstance(value, dict):
            data[name] = value
        else:
            data[name] = {"result": value, "outputs": {}}
    return data


def verify(
    status: str, result: str = "failure", requested: str = "1.9.0", installed: str = ""
) -> dict[str, Any]:
    outputs = {
        "status": status,
        "requested_version": requested,
        "installed_version": installed,
        "artifact": "release-verification-pycubrid-v1.9.0-1-1",
    }
    return {"result": result, "outputs": outputs}


def test_ordinary_merge_reports_no_release() -> None:
    data = {
        "detect": {
            "result": "success",
            "outputs": {
                "release": "false",
                "reason": "__version__ unchanged (1.8.0) compared with the first parent",
            },
        },
        **{
            name: {"result": "skipped", "outputs": {}}
            for name in (
                "consistency",
                "matrix",
                "build",
                "publish",
                "verify-cookbook",
                "require-cookbook",
            )
        },
    }
    assert (
        summary.final_state(data)
        == "no release: __version__ unchanged (1.8.0) compared with the first parent"
    )


def test_published_and_verified() -> None:
    assert summary.final_state(needs()) == "published and verified"


@pytest.mark.parametrize(
    "verify_job",
    [
        pytest.param(verify("failure"), id="report-failure"),
        pytest.param(verify("failure", installed="1.9.0"), id="status-failure"),
        pytest.param(
            verify("success", result="success", installed="1.8.0"), id="installed-differs"
        ),
        pytest.param(verify("success", result="success", installed=""), id="installed-empty"),
        pytest.param(
            verify("success", result="success", requested="1.8.0", installed="1.8.0"),
            id="requested-is-not-the-release",
        ),
        pytest.param(verify("success", result="failure", installed="1.9.0"), id="call-failed"),
        pytest.param({"result": "failure", "outputs": {}}, id="failed-without-outputs"),
        pytest.param({"result": "cancelled", "outputs": {}}, id="cancelled"),
        pytest.param({"result": "success", "outputs": {}}, id="success-without-outputs"),
    ],
)
def test_post_release_verification_is_never_silently_green(verify_job: dict[str, Any]) -> None:
    data = needs(verify_cookbook=verify_job)
    assert summary.final_state(data) == "published; post-release verification failed"
    assert summary.verification(data)[0] == "failure"


def test_failed_require_job_is_a_failed_verification() -> None:
    data = needs(require_cookbook="failure")
    assert summary.final_state(data) == "published; post-release verification failed"
    assert "require-cookbook failure" in summary.verification(data)[1]


def test_cancelled_call_reason_names_the_called_workflow() -> None:
    data = needs(verify_cookbook={"result": "cancelled", "outputs": {}})
    status, reason = summary.verification(data)
    assert status == "failure"
    assert "called workflow cancelled" in reason


@pytest.mark.parametrize("job", ["consistency", "matrix", "build"])
def test_failure_before_publish_says_nothing_was_published(job: str) -> None:
    data = needs(
        **{
            job: "failure",
            "publish": "skipped",
            "verify_cookbook": "skipped",
            "require_cookbook": "skipped",
        }
    )
    state = summary.final_state(data)
    assert (
        state
        == f"failed before publish in {job} (failure); nothing was tagged, released or uploaded"
    )


def test_publish_failure_points_to_rerun_failed() -> None:
    data = needs(publish="failure", verify_cookbook="skipped", require_cookbook="skipped")
    assert "gh run rerun <run-id> --failed" in summary.final_state(data)


def test_detect_failure() -> None:
    assert summary.final_state(needs(detect="failure")).startswith("failed in detect")


def test_dry_run_and_verify_only() -> None:
    assert (
        summary.final_state(needs("dry-run"))
        == "dry run passed; nothing published; cookbook verification success"
    )
    data = needs("dry-run", verify_cookbook=verify("failure"))
    assert (
        summary.final_state(data)
        == "dry run passed; nothing published; cookbook verification failure"
    )
    assert summary.final_state(needs("dry-run", matrix="failure")).startswith(
        "dry run failed in matrix"
    )
    data = needs("verify-only", consistency="skipped", matrix="skipped", build="skipped")
    assert summary.final_state(data) == "verification only of v1.9.0: success"
    data = needs(
        "verify-only",
        consistency="skipped",
        matrix="skipped",
        build="skipped",
        verify_cookbook={"result": "cancelled", "outputs": {}},
    )
    assert summary.final_state(data) == "verification only of v1.9.0: failure"


def test_table_lists_every_required_field() -> None:
    text = summary.render(
        needs(), {"PACKAGE": "pycubrid", "GITHUB_REPOSITORY": "cubrid-lab/pycubrid"}
    )
    assert text.startswith("## Release summary\n")
    for expected in (
        "| Final state | **published and verified** |",
        f"[`{SHA}`](https://github.com/cubrid-lab/pycubrid/commit/{SHA})",
        "| Version | 1.9.0 |",
        "| Tag | v1.9.0 (absent before this run) |",
        "| Full matrix | success |",
        f"`pycubrid-1.9.0.tar.gz` `{'2' * 64}`",
        f"`pycubrid-1.9.0-py3-none-any.whl` `{'1' * 64}`",
        "| PyPI | https://pypi.org/project/pycubrid/1.9.0/ |",
        "| GitHub Release | https://github.com/cubrid-lab/pycubrid/releases/tag/v1.9.0 |",
        "| Cookbook verification | success: installed 1.9.0 == requested 1.9.0 "
        "(report artifact `release-verification-pycubrid-v1.9.0-1-1`) |",
    ):
        assert expected in text, expected


def test_unpublished_runs_show_no_pypi_links() -> None:
    text = summary.render(needs("dry-run"), {"PACKAGE": "pycubrid", "GITHUB_REPOSITORY": "o/r"})
    assert "| PyPI | - |" in text
    assert "| GitHub Release | - |" in text


def test_table_cells_cannot_break_the_table() -> None:
    data = needs(verify_cookbook=verify("failure", installed="a | b"))
    assert "installed a / b" in summary.render(data, {})


def test_main_writes_the_step_summary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "summary.md"
    env = {"NEEDS": json.dumps(needs()), "GITHUB_STEP_SUMMARY": str(out), "PACKAGE": "pycubrid"}
    assert summary.main(env) == 0
    assert "published and verified" in out.read_text()
    assert "::notice::published and verified" in capsys.readouterr().out
    assert summary.main({"NEEDS": "not json"}) == 1
    assert summary.main({"NEEDS": "[]"}) == 1
