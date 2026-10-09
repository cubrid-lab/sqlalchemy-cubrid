"""Release-please lifecycle proof: publication and immutable tag, no live API."""

from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.repo_tooling
SPEC = importlib.util.spec_from_file_location(
    "reconcile_release_labels",
    Path(__file__).resolve().parents[1] / "scripts/reconcile_release_labels.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "draft,published,tag_sha,run_sha,run_conclusion,job_names,expected",
    [
        (False, "2026-10-03", "abc", "abc", "success", "complete", True),
        (True, "2026-10-03", "abc", "abc", "success", "complete", False),
        (False, None, "abc", "abc", "success", "complete", False),
        (False, "2026-10-03", "different", "abc", "success", "complete", False),
        (False, "2026-10-03", "abc", "different", "success", "complete", False),
        (False, "2026-10-03", "abc", "abc", "failure", "complete", False),
        (False, "2026-10-03", "abc", "abc", "success", "publish-only", False),
        (False, "2026-10-03", "abc", "abc", "success", "legacy", False),
    ],
)
def test_pending_transition_requires_completed_publication(
    draft, published, tag_sha, run_sha, run_conclusion, job_names, expected
):
    def api(*args):
        endpoint = args[1]
        if "/contents/" in endpoint:
            return {"content": base64.b64encode(json.dumps({".": "1.9.0"}).encode()).decode()}
        if "/releases/" in endpoint:
            return {"draft": draft, "published_at": published, "tag_name": "v1.9.0"}
        if "/git/ref/" in endpoint:
            return {"object": {"type": "tag", "sha": "annotated"}}
        if "/git/tags/" in endpoint:
            return {"object": {"type": "commit", "sha": tag_sha}}
        if "/workflows/" in endpoint:
            assert endpoint == (
                "repos/cubrid-lab/sqlalchemy-cubrid/actions/workflows/publish-pypi.yml/runs"
                "?head_sha=abc&per_page=100"
            )
            return {
                "workflow_runs": [{"head_sha": run_sha, "conclusion": run_conclusion, "id": 123}]
            }
        assert endpoint == "repos/cubrid-lab/sqlalchemy-cubrid/actions/runs/123/jobs?per_page=100"
        names = {
            "complete": ["Tag, GitHub Release and PyPI", "Require a verified release"],
            "publish-only": ["Tag, GitHub Release and PyPI"],
            # This filename was used by the old publish-only workflow too.
            "legacy": ["Publish to PyPI"],
        }[job_names]
        return {"jobs": [{"name": name, "conclusion": "success"} for name in names]}

    assert MODULE.ready("cubrid-lab/sqlalchemy-cubrid", "abc", api) is expected


def test_missing_or_invalid_release_facts_remain_pending():
    assert not MODULE.ready("cubrid-lab/sqlalchemy-cubrid", "abc", lambda *args: {})


# Blocked-preparation signal: classify pending PRs ready() could not prove.
NOW = MODULE.datetime(2026, 10, 9, 12, 0, tzinfo=MODULE.timezone.utc)
SHA = "d383be79e55a5f164b2569a0edb44eace9bb7e50"
RUN_URL = "https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/runs/37871732934"


def merged(hours_ago: float) -> str:
    return (NOW - MODULE.timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def publisher(status="completed", conclusion="failure", run_id=37871732934):
    return {
        "id": run_id,
        "head_sha": SHA,
        "status": status,
        "conclusion": conclusion,
        "html_url": f"https://github.com/cubrid-lab/sqlalchemy-cubrid/actions/runs/{run_id}",
    }


def fake_api(pulls, runs, published=False, calls=None):
    """Offline gh: ready() fails closed unless ``published``; record mutations."""
    calls = [] if calls is None else calls

    def api(*args):
        calls.append(args)
        if args[0] == "pr":
            # Return only the requested fields, like gh does, so a dropped field fails.
            fields = args[args.index("--json") + 1].split(",")
            return [{key: pull[key] for key in fields if key in pull} for pull in pulls]
        endpoint = args[1]
        if "/issues/" in endpoint:
            return None
        if "/workflows/" in endpoint:
            return {"workflow_runs": runs}
        if not published:
            raise MODULE.subprocess.CalledProcessError(1, ["gh", *args])
        if "/contents/" in endpoint:
            return {"content": base64.b64encode(json.dumps({".": "1.10.0"}).encode()).decode()}
        if "/releases/" in endpoint:
            return {"draft": False, "published_at": "2026-10-09", "tag_name": "v1.10.0"}
        if "/git/ref/" in endpoint:
            return {"object": {"type": "commit", "sha": SHA}}
        return {
            "jobs": [
                {"name": name, "conclusion": "success"}
                for name in ("Tag, GitHub Release and PyPI", "Require a verified release")
            ]
        }

    return api


def run_main(api, tmp_path):
    summary = tmp_path / "summary.md"
    env = {"GITHUB_REPOSITORY": "cubrid-lab/sqlalchemy-cubrid", "GITHUB_STEP_SUMMARY": str(summary)}
    code = MODULE.main(api=api, now=NOW, env=env)
    return code, summary.read_text() if summary.exists() else ""


def pending(hours_ago=10.0):
    return [{"number": 704, "mergeCommit": {"oid": SHA}, "mergedAt": merged(hours_ago)}]


@pytest.mark.parametrize("status", ["queued", "in_progress", "waiting"])
def test_pending_with_running_publisher_is_a_notice(status, tmp_path, capsys):
    api = fake_api(pending(hours_ago=30), [publisher(status=status, conclusion=None)])
    code, summary = run_main(api, tmp_path)
    out = capsys.readouterr().out
    assert code == 0
    assert "::notice::" in out and RUN_URL in out and "::error::" not in out
    assert summary == ""


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "timed_out"])
def test_pending_with_failed_publisher_is_blocked(conclusion, tmp_path, capsys):
    api = fake_api(pending(), [publisher(conclusion=conclusion)])
    code, summary = run_main(api, tmp_path)
    out = capsys.readouterr().out
    hint = "gh api -X POST repos/cubrid-lab/sqlalchemy-cubrid/actions/runs/37871732934/rerun-failed-jobs"
    assert code == 1
    for text in ("::error::", "#704", SHA, RUN_URL, f"concluded {conclusion}", hint):
        assert text in out
    assert "Release preparation is blocked" in summary
    for text in ("#704", SHA, RUN_URL, hint, "RELEASING.md"):
        assert text in summary
    assert out.rstrip().endswith(MANUAL)


MANUAL = "If recovery ran as a dispatch at another SHA, label the PR manually per RELEASING.md."


@pytest.mark.parametrize("conclusion", ["action_required", "skipped", "stale", "neutral"])
def test_non_rerunnable_conclusion_is_blocked_without_rerun_hint(conclusion, tmp_path, capsys):
    code, summary = run_main(fake_api(pending(), [publisher(conclusion=conclusion)]), tmp_path)
    out = capsys.readouterr().out
    assert code == 1
    assert f"concluded {conclusion}" in out and RUN_URL in out
    assert "rerun-failed-jobs" not in out and "rerun-failed-jobs" not in summary
    assert out.rstrip().endswith(MANUAL)


def test_newest_completed_publisher_run_decides(tmp_path, capsys):
    runs = [publisher(conclusion="failure", run_id=1), publisher(status="in_progress", run_id=2)]
    assert run_main(fake_api(pending(), runs), tmp_path)[0] == 0
    capsys.readouterr()
    runs = [publisher(conclusion="success", run_id=3), publisher(conclusion="cancelled", run_id=2)]
    assert run_main(fake_api(pending(), runs), tmp_path)[0] == 1
    out = capsys.readouterr().out
    assert "actions/runs/3 succeeded" in out and "concluded cancelled" not in out


def test_successful_run_without_publication_proof_is_blocked(tmp_path, capsys):
    code, _ = run_main(fake_api(pending(), [publisher(conclusion="success")]), tmp_path)
    out = capsys.readouterr().out
    assert code == 1
    assert "not proven" in out and "the proof read may have failed transiently" in out
    assert "rerun-failed-jobs" not in out and out.rstrip().endswith(MANUAL)


def test_in_progress_run_with_stale_failed_conclusion_is_in_progress(tmp_path, capsys):
    run = publisher(status="in_progress", conclusion="failure")
    assert run_main(fake_api(pending(hours_ago=30), [run]), tmp_path)[0] == 0
    assert "::notice::" in capsys.readouterr().out


def test_rerun_of_older_run_is_in_progress(tmp_path, capsys):
    # Re-running an older (lower-id) failed run keeps its id; the newer one stays failed.
    runs = [publisher(status="in_progress", run_id=1), publisher(conclusion="failure", run_id=2)]
    assert run_main(fake_api(pending(), runs), tmp_path)[0] == 0
    out = capsys.readouterr().out
    assert "::notice::" in out and "actions/runs/1 is in_progress" in out


def test_main_requests_merged_at(tmp_path, capsys):
    calls = []
    run_main(fake_api(pending(), [publisher()], calls=calls), tmp_path)
    (listing,) = [call for call in calls if call[0] == "pr"]
    assert listing[listing.index("--json") + 1] == "number,mergeCommit,mergedAt"


def test_mixed_provable_and_blocked_prs_tag_and_fail(tmp_path, capsys):
    pulls = pending() + [{"number": 710, "mergeCommit": {"oid": "other"}, "mergedAt": merged(10)}]
    calls = []
    proven = fake_api(pulls, [publisher(conclusion="success")], published=True, calls=calls)

    def api(*args):
        if args[0] == "api" and "other" in args[1]:
            if "/workflows/" in args[1]:
                return {"workflow_runs": [dict(publisher(), head_sha="other", id=9)]}
            raise MODULE.subprocess.CalledProcessError(1, ["gh", *args])
        return proven(*args)

    code, summary = run_main(api, tmp_path)
    out = capsys.readouterr().out
    assert code == 1
    assert "PR #704 marked tagged after publication proof" in out
    assert [call[1] for call in calls if "/issues/" in call[1]] == [
        "repos/cubrid-lab/sqlalchemy-cubrid/issues/704/labels",
        "repos/cubrid-lab/sqlalchemy-cubrid/issues/704/labels/autorelease%3A%20pending",
    ]
    assert "#710" in summary and "#704" not in summary


def test_blocked_without_step_summary_still_fails(capsys):
    api = fake_api(pending(), [publisher()])
    code = MODULE.main(api=api, now=NOW, env={"GITHUB_REPOSITORY": "cubrid-lab/sqlalchemy-cubrid"})
    assert code == 1 and "::error::" in capsys.readouterr().out


def test_age_is_rounded_to_minutes():
    state, message = MODULE.classify(
        "cubrid-lab/sqlalchemy-cubrid", 704, SHA, merged(1.5051), NOW, fake_api([], [])
    )
    assert state == MODULE.IN_PROGRESS and "merged 1h30m ago." in message


def test_runs_for_other_shas_are_ignored(tmp_path, capsys):
    other = dict(publisher(status="in_progress"), head_sha="other")
    assert run_main(fake_api(pending(hours_ago=10), [other]), tmp_path)[0] == 1


@pytest.mark.parametrize(
    "hours_ago,expected",
    [
        (0, MODULE.IN_PROGRESS),
        (1.99, MODULE.IN_PROGRESS),
        (2, MODULE.BLOCKED),
        (30, MODULE.BLOCKED),
    ],
)
def test_missing_publisher_run_threshold(hours_ago, expected):
    assert MODULE.PUBLISHER_START_GRACE == MODULE.timedelta(hours=2)
    state, message = MODULE.classify(
        "cubrid-lab/sqlalchemy-cubrid", 704, SHA, merged(hours_ago), NOW, fake_api([], [])
    )
    assert state == expected
    assert "no publish-pypi.yml run" in message


def test_recent_merge_without_run_is_a_notice(tmp_path, capsys):
    code, summary = run_main(fake_api(pending(hours_ago=0.01), []), tmp_path)
    out = capsys.readouterr().out
    assert code == 0 and "::notice::" in out and "::error::" not in out and summary == ""


def test_old_merge_without_run_is_blocked(tmp_path, capsys):
    code, summary = run_main(fake_api(pending(hours_ago=3), []), tmp_path)
    out = capsys.readouterr().out
    assert code == 1 and "::error::" in out and "RELEASING.md" in summary


def test_unreadable_publisher_state_is_blocked():
    def api(*args):
        raise MODULE.subprocess.CalledProcessError(1, ["gh", *args])

    state, _ = MODULE.classify("cubrid-lab/sqlalchemy-cubrid", 704, SHA, merged(0), NOW, api)
    assert state == MODULE.BLOCKED


def test_successful_publication_transitions_exactly_as_before(tmp_path, capsys):
    calls = []
    api = fake_api(pending(), [publisher(conclusion="success")], published=True, calls=calls)
    code, summary = run_main(api, tmp_path)
    out = capsys.readouterr().out
    assert code == 0 and summary == "" and "::" not in out
    assert "PR #704 marked tagged after publication proof" in out
    mutations = [call for call in calls if "/issues/" in call[1]]
    assert mutations == [
        (
            "api",
            "repos/cubrid-lab/sqlalchemy-cubrid/issues/704/labels",
            "--method",
            "POST",
            "-f",
            "labels[]=autorelease: tagged",
        ),
        (
            "api",
            "repos/cubrid-lab/sqlalchemy-cubrid/issues/704/labels/autorelease%3A%20pending",
            "--method",
            "DELETE",
        ),
    ]


def test_blocked_pr_is_never_relabelled_or_rerun(tmp_path, capsys):
    calls = []
    run_main(fake_api(pending(), [publisher()], calls=calls), tmp_path)
    assert all(call[0] in ("pr", "api") for call in calls)
    assert not any("--method" in call or "/issues/" in call[1] for call in calls if len(call) > 1)


def test_no_pending_prs_is_silent(tmp_path, capsys):
    code, summary = run_main(fake_api([], []), tmp_path)
    assert code == 0 and summary == "" and capsys.readouterr().out == ""
