"""Keep issue title and label triage rules executable."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_issue_metadata import main, metadata_gaps

_VALID = ("bug", "priority: high", "size: M", "area: protocol")


@pytest.mark.parametrize(
    ("title", "labels", "expected"),
    [
        ("fix: preserve cursor state", _VALID, ()),
        ("fix(protocol): preserve cursor state", _VALID, ()),
        ("[Bug]: preserve cursor state", _VALID, ("title",)),
        ("fix: ", _VALID, ("title",)),
        ("fix: preserve cursor state", ("priority: high", "size: M"), ("type",)),
        (
            "fix: fail closed when the integration service is unavailable",
            ("ci", "priority: critical", "size: M"),
            (),
        ),
        ("fix: fence prepared requests", ("enhancement", "priority: high", "size: L"), ()),
        ("fix: preserve cursor state", (*_VALID, "ci"), ()),
        ("test: add coverage", ("testing", "priority: medium", "size: S"), ()),
        ("refactor: simplify compiler", ("refactor", "priority: medium", "size: S"), ()),
        ("ci: extend coverage", ("ci", "testing", "priority: medium", "size: M"), ()),
        ("epic: compare drivers", ("enhancement", "testing", "priority: high", "size: L"), ()),
        ("perf: tune fetches", ("enhancement", "priority: medium", "size: S"), ()),
        ("perf: tune fetches", ("performance", "priority: medium", "size: S"), ()),
        ("perf: tune fetches", ("enhancement", "performance", "priority: medium", "size: S"), ()),
        ("fix: preserve cursor state", ("bug", "size: M"), ("priority",)),
        ("fix: preserve cursor state", ("bug", "priority:high", "size: M"), ("priority",)),
        (
            "fix: preserve cursor state",
            ("bug", "priority: high", "priority: low", "size: M"),
            ("priority",),
        ),
        ("fix: preserve cursor state", ("bug", "priority: high"), ("size",)),
        ("fix: preserve cursor state", ("bug", "priority: high", "size:M"), ("size",)),
    ],
)
def test_metadata_gaps(title: str, labels: tuple[str, ...], expected: tuple[str, ...]) -> None:
    assert metadata_gaps(title, labels) == expected


def test_event_path_emits_only_a_triage_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    event = tmp_path / "event.json"
    event.write_text(
        json.dumps(
            {
                "issue": {
                    "title": "fix: preserve cursor state",
                    "labels": [{"name": name} for name in _VALID],
                }
            }
        ),
        encoding="utf-8",
    )
    assert main(["check_issue_metadata.py", str(event)]) == 0
    assert capsys.readouterr().out == "needs_triage=false\n"

    event.write_text(
        json.dumps({"issue": {"title": "Missing prefix", "labels": []}}),
        encoding="utf-8",
    )
    assert main(["check_issue_metadata.py", str(event)]) == 0
    captured = capsys.readouterr()
    assert captured.out == "needs_triage=true\n"
    assert "title, type, priority, size" in captured.err
