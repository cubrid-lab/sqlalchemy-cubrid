"""Offline tests for scripts/release_detect.py against throwaway git repositories.

Each test builds a small repository with a bare ``origin`` in ``tmp_path``;
nothing reaches the network. Kept identical across pycubrid, sqlalchemy-cubrid
and cubrid-mcp-server.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "_release_detect", ROOT / "scripts" / "release_detect.py"
)
assert _spec is not None and _spec.loader is not None
detect = importlib.util.module_from_spec(_spec)
sys.modules["_release_detect"] = detect
_spec.loader.exec_module(detect)

VERSION_FILE = "pkg/__init__.py"
CHANGELOG_HEAD = "# Changelog\n\n## [Unreleased]\n\n"


def changelog(*sections: str) -> str:
    return CHANGELOG_HEAD + "".join(f"{s}\n\n### Fixed\n- something\n\n" for s in sections)


class Repo:
    def __init__(self, path: Path) -> None:
        self.origin = path / "origin.git"
        self.work = path / "work"
        subprocess.run(["git", "init", "-q", "--bare", str(self.origin)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.work)], check=True)
        self.git("remote", "add", "origin", str(self.origin))

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
            cwd=self.work,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def commit(self, version: str, log: str, message: str = "change") -> str:
        (self.work / "pkg").mkdir(exist_ok=True)
        (self.work / VERSION_FILE).write_text(f'"""pkg."""\n\n__version__ = "{version}"\n')
        (self.work / "CHANGELOG.md").write_text(log)
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)
        sha = self.git("rev-parse", "HEAD")
        self.git("push", "-q", "origin", "HEAD:refs/heads/main")
        self.git("fetch", "-q", "origin")
        return sha

    def tag(self, name: str, sha: str, annotated: bool = True) -> None:
        if annotated:
            self.git("tag", "-a", name, sha, "-m", name)
        else:
            self.git("tag", name, sha)
        self.git("push", "-q", "origin", f"refs/tags/{name}")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Repo:
    r = Repo(tmp_path)
    monkeypatch.chdir(r.work)
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    r.commit("1.0.0", changelog("## [1.0.0] - 2026-01-01"), "chore: release v1.0.0")
    return r


def run(*args: str) -> tuple[int, dict[str, str]]:
    output = Path("github_output")
    output.write_text("")
    os.environ["GITHUB_OUTPUT"] = str(output.resolve())
    try:
        code = detect.main(["--version-file", VERSION_FILE, *args])
    finally:
        del os.environ["GITHUB_OUTPUT"]
    values = dict(line.split("=", 1) for line in output.read_text().splitlines() if "=" in line)
    output.unlink()
    return code, values


def test_ordinary_merge_is_no_release(repo: Repo) -> None:
    sha = repo.commit("1.0.0", changelog("## [1.0.0] - 2026-01-01") + "x\n", "fix: something")
    code, out = run("--sha", sha)
    assert code == 0
    assert out["release"] == out["build"] == out["publish"] == out["verify"] == "false"
    assert out["reason"] == "__version__ unchanged (1.0.0) compared with the first parent"
    assert out["mode"] == "push"


def test_release_pr_merge_releases(repo: Repo) -> None:
    sha = repo.commit("1.1.0", changelog("## [1.1.0] - 2026-02-01", "## [1.0.0] - 2026-01-01"))
    code, out = run("--sha", sha)
    assert code == 0
    assert out == {
        "release": "true",
        "build": "true",
        "publish": "true",
        "verify": "true",
        "mode": "push",
        "version": "1.1.0",
        "tag": "v1.1.0",
        "sha": sha,
        "tag_state": "absent",
        "reason": "release v1.1.0",
    }


def test_title_is_irrelevant(repo: Repo) -> None:
    # A "chore: release" title without a version change never releases ...
    sha = repo.commit(
        "1.0.0", changelog("## [1.0.0] - 2026-01-01") + "y\n", "chore: release v9.9.9"
    )
    assert run("--sha", sha)[1]["release"] == "false"
    # ... and a version change releases whatever the title says.
    sha = repo.commit(
        "1.0.1", changelog("## [1.0.1] - 2026-02-01", "## [1.0.0] - 2026-01-01"), "misc"
    )
    assert run("--sha", sha)[1]["release"] == "true"


@pytest.mark.parametrize(
    "log",
    [
        changelog("## [1.0.0] - 2026-01-01"),  # no section at all
        changelog("## [1.1.0]", "## [1.0.0] - 2026-01-01"),  # undated
        changelog("## [1.1.0] - TBD", "## [1.0.0] - 2026-01-01"),
        changelog("## [1.1.0.1] - 2026-02-01", "## [1.0.0] - 2026-01-01"),  # other version
    ],
)
def test_version_change_without_dated_section_is_no_release(
    repo: Repo, log: str, capsys: pytest.CaptureFixture[str]
) -> None:
    sha = repo.commit("1.1.0", log)
    code, out = run("--sha", sha)
    assert code == 0
    assert out["release"] == "false"
    assert "has no dated '## [1.1.0] - YYYY-MM-DD' section" in out["reason"]
    assert "::warning::" in capsys.readouterr().out


def test_non_semver_version_is_no_release(repo: Repo) -> None:
    sha = repo.commit(
        "1.1.0rc1", changelog("## [1.1.0rc1] - 2026-02-01", "## [1.0.0] - 2026-01-01")
    )
    code, out = run("--sha", sha)
    assert (code, out["release"]) == (0, "false")
    assert "not MAJOR.MINOR.PATCH" in out["reason"]


@pytest.mark.parametrize("annotated", [True, False])
def test_tag_at_same_sha_resumes(repo: Repo, annotated: bool) -> None:
    sha = repo.commit("1.1.0", changelog("## [1.1.0] - 2026-02-01", "## [1.0.0] - 2026-01-01"))
    repo.tag("v1.1.0", sha, annotated)
    code, out = run("--sha", sha)
    assert code == 0
    assert (out["release"], out["publish"], out["tag_state"]) == ("true", "true", "same")
    assert out["reason"] == "resume v1.1.0 (tag already at this commit)"


def test_tag_at_other_sha_is_no_release(repo: Repo) -> None:
    first = repo.commit("1.1.0", changelog("## [1.1.0] - 2026-02-01", "## [1.0.0] - 2026-01-01"))
    repo.tag("v1.1.0", first)
    repo.commit("1.0.0", changelog("## [1.0.0] - 2026-01-01"), "revert")
    sha = repo.commit("1.1.0", changelog("## [1.1.0] - 2026-02-02", "## [1.0.0] - 2026-01-01"))
    code, out = run("--sha", sha)
    assert code == 0
    assert (out["release"], out["tag_state"]) == ("false", "different")
    assert "tags are never moved" in out["reason"]


def test_similar_tag_names_do_not_count(repo: Repo) -> None:
    sha = repo.commit("1.1.0", changelog("## [1.1.0] - 2026-02-01", "## [1.0.0] - 2026-01-01"))
    base = repo.git("rev-parse", "HEAD~1")
    repo.tag("v1.1.00", base)
    repo.tag("xv1.1.0", base)
    assert run("--sha", sha)[1]["tag_state"] == "absent"


def test_push_rejects_unknown_or_short_sha(repo: Repo) -> None:
    assert run("--sha", "0" * 40)[0] == 1
    assert run("--sha", repo.git("rev-parse", "--short", "HEAD"))[0] == 1


# Recovery dispatch -----------------------------------------------------------


def released(repo: Repo) -> str:
    sha = repo.commit("1.1.0", changelog("## [1.1.0] - 2026-02-01", "## [1.0.0] - 2026-01-01"))
    repo.tag("v1.1.0", sha)
    repo.commit(
        "1.1.0", changelog("## [1.1.0] - 2026-02-01", "## [1.0.0] - 2026-01-01") + "z", "docs"
    )
    return sha


def test_resume_uses_the_tag_commit(repo: Repo) -> None:
    sha = released(repo)
    code, out = run("--mode", "resume", "--version", "1.1.0")
    assert code == 0
    assert (out["sha"], out["mode"], out["publish"], out["build"]) == (
        sha,
        "resume",
        "true",
        "true",
    )


def test_verify_only_publishes_nothing(repo: Repo) -> None:
    sha = released(repo)
    code, out = run("--mode", "verify-only", "--version", "1.1.0")
    assert code == 0
    assert (out["sha"], out["build"], out["publish"], out["verify"]) == (
        sha,
        "false",
        "false",
        "true",
    )


@pytest.mark.parametrize("mode", ["resume", "verify-only"])
def test_recovery_never_creates_a_new_version(repo: Repo, mode: str, capsys) -> None:
    repo.commit("1.2.0", changelog("## [1.2.0] - 2026-03-01", "## [1.0.0] - 2026-01-01"))
    code, out = run("--mode", mode, "--version", "1.2.0")
    assert (code, out) == (1, {})
    assert "tag v1.2.0 does not exist" in capsys.readouterr().out


@pytest.mark.parametrize("mode", ["resume", "verify-only"])
def test_recovery_requires_the_tag_on_main(repo: Repo, mode: str, capsys) -> None:
    repo.git("switch", "-q", "-c", "side")
    sha = repo.commit("1.1.0", changelog("## [1.1.0] - 2026-02-01", "## [1.0.0] - 2026-01-01"))
    repo.git("push", "-q", "--force", "origin", f"{sha}~1:refs/heads/main")
    repo.git("fetch", "-q", "--prune", "origin")
    repo.tag("v1.1.0", sha)
    assert run("--mode", mode, "--version", "1.1.0")[0] == 1
    assert "is not contained in origin/main" in capsys.readouterr().out


def test_recovery_requires_matching_version_and_changelog(repo: Repo, capsys) -> None:
    repo.tag("v1.1.0", repo.git("rev-parse", "HEAD"))  # tag on a 1.0.0 commit
    assert run("--mode", "resume", "--version", "1.1.0")[0] == 1
    assert "has __version__ '1.0.0', not 1.1.0" in capsys.readouterr().out
    sha = repo.commit("1.2.0", changelog("## [1.0.0] - 2026-01-01"))
    repo.tag("v1.2.0", sha)
    assert run("--mode", "resume", "--version", "1.2.0")[0] == 1
    assert "no dated '## [1.2.0]' section" in capsys.readouterr().out


@pytest.mark.parametrize("version", ["", "1.1", "v1.1.0", "1.1.0; rm -rf /"])
def test_recovery_validates_the_version(repo: Repo, version: str) -> None:
    assert run("--mode", "resume", "--version", version)[0] == 1


def test_dry_run_rehearses_the_current_version(repo: Repo) -> None:
    sha = released(repo)
    head = repo.git("rev-parse", "HEAD")
    code, out = run("--mode", "dry-run", "--sha", head, "--version", "1.1.0")
    assert code == 0
    assert (out["build"], out["publish"], out["verify"]) == ("true", "false", "true")
    assert (out["sha"], out["tag_state"]) == (head, "different")
    assert sha != head


def test_dry_run_rejects_another_version(repo: Repo, capsys) -> None:
    head = repo.git("rev-parse", "HEAD")
    assert run("--mode", "dry-run", "--sha", head, "--version", "2.0.0")[0] == 1
    assert "has __version__ '1.0.0', not 2.0.0" in capsys.readouterr().out


def test_usage_errors_exit_2() -> None:
    assert detect.main(["--mode", "bogus", "--version-file", VERSION_FILE]) == 2
    assert detect.main([]) == 2


def test_parse_version_is_ast_only() -> None:
    assert detect.parse_version('__version__ = "1.2.3"\n') == "1.2.3"
    assert detect.parse_version("__version__ = get()\n") == ""
    assert detect.parse_version("def (:\n") == ""
    assert detect.parse_version(None) == ""


def test_unvalidated_version_never_reaches_github_output(repo: Repo) -> None:
    sha = repo.commit("1.1.0\\npublish=true", changelog("## [1.0.0] - 2026-01-01"))
    code, out = run("--sha", sha)
    assert code == 0
    assert (out["release"], out["publish"], out["version"]) == ("false", "false", "")
    assert out["reason"] == "__version__ is not MAJOR.MINOR.PATCH"


def test_outputs_are_single_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(path))
    detect.write_outputs({"reason": "a\npublish=true"})
    assert path.read_text() == "reason=a publish=true\n"
