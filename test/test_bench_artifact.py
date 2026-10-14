"""Offline tests of the benchmark artifact manifest contract (#901)."""

from __future__ import annotations

import argparse
import copy
import json
import math
import statistics
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts import bench_artifact as ba

REPO = Path(__file__).resolve().parents[1]
DIGEST = "sha256:" + "1" * 64
SHA_A = "a" * 40
SHA_B = "b" * 40


def _summary(values: list[float]) -> dict[str, Any]:
    return {"median": statistics.median(values), "trials": list(values)}


def make_report(driver: str = "pycubrid", sha: str = SHA_A, trials: int = 5) -> dict[str, Any]:
    vals = [float(10 + i) for i in range(trials)]
    stages = {s: _summary(vals) for s in ("insert", "update", "delete")}
    batch = {v: copy.deepcopy(stages) for v in ("raw", "core", "core_prepared_experiment", "orm")}
    if driver == "pycubrid":
        batch["raw_prepared"] = copy.deepcopy(stages)
    env: dict[str, Any] = {
        "python": "3.12.13",
        "implementation": "CPython",
        "platform": "Linux-5.15",
        "cpu": "Test CPU",
        "sqlalchemy": "2.1.4",
        "pycubrid": "1.12.0",
        "sqlalchemy_cubrid": "1.11.0",
        "source_sha": sha,
        "cubrid_server": "11.4.6.1963",
        "driver": driver,
        "target": "cubrid+pycubrid://dba@localhost:34114/testdb",
        "pool": "QueuePool",
        "pool_pre_ping": False,
        "autocommit": False,
        "use_insertmanyvalues": True,
        "insertmanyvalues_page_size": 1000,
        "cubrid_image_digest": DIGEST,
        "host": "devbox",
        "comparable_group": "g",
        "dialect_package_sha256": "5" * 64,
        "source_verification": "local_checkout",
        "installed_revision": sha,
        "args": {"trials": trials, "rows": 1000, "batch": 1000, "source_sha": sha},
    }
    if driver == "cubrid":
        env["cubrid_python"] = "11.3.0.51"
    return {
        "environment": env,
        "trials": [{} for _ in range(trials)],
        "summary": {
            "select_pk_us": {
                v: _summary(vals) for v in ("raw", "core_cached", "core_uncached", "orm")
            },
            "fetch_all_us": {v: _summary(vals) for v in ("raw", "core", "orm")},
            "batch_ms": batch,
        },
        "workload": {
            "script": "scripts/bench_dialect_baseline.py",
            "script_sha256": "2" * 64,
            "table": "bench_dialect_baseline",
        },
        "status": "complete",
    }


def write_artifact(tmp: Path, report: dict[str, Any], *, log: bool = True) -> Path:
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "raw").mkdir(exist_ok=True)
    (tmp / "raw" / "report.json").write_text(json.dumps(report), encoding="utf-8")
    argv = ["export", str(tmp / "raw" / "report.json"), "--output", str(tmp / "manifest.json")]
    if log:
        (tmp / "raw" / "report.txt").write_text("log\n", encoding="utf-8")
        argv += ["--log", str(tmp / "raw" / "report.txt")]
    assert ba.main(argv) == 0
    return tmp / "manifest.json"


def invalid(tmp: Path, report: dict[str, Any], match: str, **kw: Any) -> None:
    (tmp / "raw").mkdir(parents=True, exist_ok=True)
    (tmp / "raw" / "report.json").write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ba.ArtifactError, match=match):
        ba.build_manifest(tmp / "raw" / "report.json", root=tmp, logs=kw.get("logs", ()))


def test_export_writes_the_advisory_metric_set(tmp_path: Path) -> None:
    manifest = ba.validate(write_artifact(tmp_path, make_report()))
    assert manifest["schema"] == "sqlalchemy-cubrid-benchmark-artifact/2"
    assert manifest["environment"]["dialect_source_sha"] == SHA_A
    assert manifest["environment"]["cubrid_image_digest"] == DIGEST
    assert manifest["environment"]["pool_pre_ping"] is False
    assert manifest["environment"]["use_insertmanyvalues"] is True
    assert manifest["trials"] == 5
    assert [f["path"] for f in manifest["files"]] == ["raw/report.json", "raw/report.txt"]
    ids = [m["id"] for m in manifest["metrics"]]
    assert ids[:7] == [
        "select_pk.raw",
        "select_pk.core_cached",
        "select_pk.core_uncached",
        "select_pk.orm",
        "fetch_all.raw",
        "fetch_all.core",
        "fetch_all.orm",
    ]
    assert "batch.raw_prepared.insert" in ids
    assert not [i for i in ids if "core_prepared_experiment" in i]
    by_id = {m["id"]: m for m in manifest["metrics"]}
    assert by_id["select_pk.core_cached"]["unit"] == "us"
    assert by_id["fetch_all.orm"]["rows_per_call"] == 1000
    assert by_id["batch.raw.insert"]["sql_shape"].endswith("EXECUTE_BATCH (FC20)")
    assert "FC21" in by_id["batch.raw_prepared.update"]["sql_shape"]
    assert "insertmanyvalues" in by_id["batch.core.insert"]["sql_shape"]
    assert "do_executemany" in by_id["batch.core.update"]["sql_shape"]
    assert by_id["batch.core.delete"]["commit"].startswith("one commit per batch")
    assert by_id["batch.orm.delete"]["trials"] == [10.0, 11.0, 12.0, 13.0, 14.0]


def test_cubriddb_artifact_has_no_prepared_metrics(tmp_path: Path) -> None:
    manifest = ba.validate(write_artifact(tmp_path, make_report(driver="cubrid")))
    assert manifest["environment"]["driver_version"] == "11.3.0.51"
    assert not [m for m in manifest["metrics"] if "prepared" in m["id"]]
    shapes = {m["id"]: m["sql_shape"] for m in manifest["metrics"]}
    assert shapes["batch.raw.insert"] == "raw CUBRIDdb cursor.executemany()"
    assert "one cursor.execute() per parameter set" in shapes["batch.core.update"]
    assert "one cursor.execute() per parameter set" in shapes["batch.orm.update"]
    assert "insertmanyvalues" in shapes["batch.core.insert"]
    assert not [s for s in shapes.values() if "FC20" in s or "PyCubridDialect" in s]


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda r: r["environment"].pop("pycubrid"), "missing driver_version, pycubrid"),
        (lambda r: r["environment"].pop("cubrid_server"), "missing cubrid_server"),
        (lambda r: r["environment"].pop("target"), "missing target"),
        (lambda r: r["environment"].update(args=None), "no args"),
        (lambda r: r.update(summary=[]), "no summary"),
        (lambda r: r["summary"]["select_pk_us"].update(orm=[1]), "is not an object"),
        (lambda r: r["summary"]["select_pk_us"]["orm"].update(median="x"), "not a number"),
        (lambda r: r["environment"]["args"].update(rows=None), "rows None"),
        (lambda r: r["environment"]["args"].update(batch=None), "batch None"),
        (lambda r: r["environment"]["args"].update(batch="1000"), "batch '1000'"),
        (lambda r: r["environment"]["args"].update(batch=-1), "batch -1"),
        (lambda r: r["environment"]["args"].update(batch=True), "batch True"),
        (lambda r: r.update(trials=None), "report holds 0 trials"),
        (lambda r: r["environment"].update(pool_pre_ping=None), "missing pool_pre_ping"),
        (lambda r: r.pop("environment"), "no environment"),
        (lambda r: r["environment"].update(source_sha="unknown"), "not a full 40-character"),
        (lambda r: r["environment"]["args"].update(source_sha=SHA_B), "mixed revision"),
        (lambda r: r["environment"].update(sqlalchemy="1.4.54"), "unsupported SQLAlchemy"),
        (lambda r: r["environment"].update(sqlalchemy="2.2.0"), "unsupported SQLAlchemy"),
        (lambda r: r["environment"].update(driver="mysqldb"), "unsupported driver"),
        (lambda r: r.pop("status"), "not 'complete'"),
        (lambda r: r.update(status="failed"), "not 'complete'"),
        (lambda r: r.pop("workload"), "no workload identity"),
        (lambda r: r["workload"].update(table="other"), "workload table"),
        (lambda r: r["workload"].update(script_sha256="x"), "script_sha256 missing"),
        (lambda r: r["environment"]["args"].update(trials=2), "at least 3"),
        (lambda r: r["trials"].pop(), "report holds 4 trials"),
        (lambda r: r["environment"]["args"].update(rows=10), "rows 10"),
        (lambda r: r["summary"]["select_pk_us"].pop("orm"), "select_pk.orm"),
        (lambda r: r["summary"]["fetch_all_us"]["raw"]["trials"].pop(), "4 trial values"),
        (lambda r: r["summary"]["batch_ms"]["raw"]["insert"].pop("trials"), "trial values"),
        (lambda r: r["summary"]["batch_ms"]["orm"]["update"]["trials"].__setitem__(0, 0), "0"),
        (
            lambda r: r["summary"]["batch_ms"]["orm"]["update"]["trials"].__setitem__(0, math.inf),
            "inf",
        ),
        (lambda r: r["summary"]["select_pk_us"]["raw"].update(median=99.0), "summary median"),
    ],
)
def test_incomplete_or_inconsistent_reports_are_rejected(
    tmp_path: Path, mutate: Any, match: str
) -> None:
    report = make_report()
    mutate(report)
    invalid(tmp_path, report, match)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("cubrid_image_digest", "1248b77ad398", "bad or missing image digest"),
        ("cubrid_image_digest", None, "bad or missing image digest"),
        ("host", "", "host label missing"),
        ("comparable_group", None, "comparable group missing"),
        ("source_verification", "unverified", "not verified against the source SHA"),
        ("source_verification", None, "not verified against the source SHA"),
        ("dialect_package_sha256", "x", "dialect_package_sha256 missing"),
        ("installed_revision", SHA_B, "installed revision"),
        ("installed_revision", None, "installed revision"),
    ],
)
def test_unverified_or_incomplete_provenance_is_rejected(
    tmp_path: Path, field: str, value: Any, match: str
) -> None:
    report = make_report()
    report["environment"][field] = value
    invalid(tmp_path, report, match)


def test_vcs_verified_reports_export(tmp_path: Path) -> None:
    report = make_report()
    report["environment"]["source_verification"] = "vcs_info"
    manifest = ba.validate(write_artifact(tmp_path, report))
    assert manifest["environment"]["source_verification"] == "vcs_info"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cubrid_image_digest", "sha256:" + "9" * 64),
        ("host", "otherhost"),
        ("dialect_package_sha256", "6" * 64),
        ("source_verification", "vcs_info"),
        ("dialect_source_sha", SHA_B),
    ],
)
def test_validate_rejects_in_place_edits_of_provenance(
    tmp_path: Path, field: str, value: str
) -> None:
    """These fields come from the hashed report, so editing the manifest alone fails (#903)."""
    manifest_path = write_artifact(tmp_path, make_report())
    manifest = json.loads(manifest_path.read_text())
    manifest["environment"][field] = value
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ba.ArtifactError, match="environment does not match"):
        ba.validate(manifest_path)


def test_validate_rejects_an_in_place_edit_of_the_group(tmp_path: Path) -> None:
    manifest_path = write_artifact(tmp_path, make_report())
    manifest = json.loads(manifest_path.read_text())
    manifest["comparable_group"] = "other"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ba.ArtifactError, match="comparable_group does not match"):
        ba.validate(manifest_path)


def test_duplicate_paths_are_rejected(tmp_path: Path) -> None:
    raw = tmp_path / "raw" / "report.json"
    invalid(tmp_path, make_report(), "duplicate file paths", logs=[raw])


def test_validate_rejects_edited_files_and_manifests(tmp_path: Path) -> None:
    manifest_path = write_artifact(tmp_path, make_report())
    good = json.loads(manifest_path.read_text())

    def check(edit: Any, match: str) -> None:
        bad = copy.deepcopy(good)
        edit(bad)
        manifest_path.write_text(json.dumps(bad))
        with pytest.raises(ba.ArtifactError, match=match):
            ba.validate(manifest_path)

    check(lambda m: m.update(schema="other/1"), "schema")
    check(lambda m: m["metrics"][0].update(unit="ms"), "unit 'ms', expected 'us'")
    check(lambda m: m["metrics"][0].update(median=1.0), "metrics does not match")
    check(lambda m: m["environment"].update(sqlalchemy_cubrid="9.9.9"), "environment does not")
    check(lambda m: m["files"].append(dict(m["files"][0])), "duplicate file paths")
    check(lambda m: m["files"][1].update(role="raw"), "exactly one raw report")
    check(lambda m: m["files"][0].update(path="../raw/report.json"), "without '..'")
    check(lambda m: m.update(files=[]), "lists no files")
    check(lambda m: m.update(files=[1]), "every file entry must be an object")
    check(lambda m: m.update(metrics=[1]), "metrics must be a list of objects")
    check(lambda m: m.update(metrics=None), "metrics must be a list of objects")
    check(lambda m: m.update(environment=None), "no environment")
    check(lambda m: m["files"][0].update(path=3), "SHA-256|cannot read")
    manifest_path.write_text(json.dumps(good))
    (tmp_path / "raw" / "report.txt").write_text("changed\n")
    with pytest.raises(ba.ArtifactError, match="does not match the manifest"):
        ba.validate(manifest_path)
    assert ba.main(["validate", str(manifest_path)]) == ba.EXIT_INVALID


def test_compare_reports_ratios_when_only_the_dialect_varies(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = write_artifact(tmp_path / "base", make_report(sha=SHA_A))
    cand_report = make_report(sha=SHA_B)
    cand_report["environment"]["sqlalchemy_cubrid"] = "1.12.0"
    cand_report["summary"]["select_pk_us"]["raw"] = _summary([20.0, 22.0, 24.0, 26.0, 28.0])
    cand = write_artifact(tmp_path / "cand", cand_report)
    out = tmp_path / "compare.json"
    assert ba.main(["compare", str(base), str(cand), "--output", str(out)]) == 0
    result = json.loads(out.read_text())
    assert result["status"] == "comparable"
    provenance = {"dialect_package_sha256": "5" * 64, "source_verification": "local_checkout"}
    assert result["baseline"] == {
        "dialect_source_sha": SHA_A,
        "sqlalchemy_cubrid": "1.11.0",
        **provenance,
    }
    assert result["candidate"] == {
        "dialect_source_sha": SHA_B,
        "sqlalchemy_cubrid": "1.12.0",
        **provenance,
    }
    by_id = {m["id"]: m for m in result["metrics"]}
    assert by_id["select_pk.raw"]["ratio"] == pytest.approx(2.0)
    assert by_id["batch.orm.delete"]["ratio"] == pytest.approx(1.0)
    assert "comparable:" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("edit", "kw", "reason"),
    [
        (lambda r: r["environment"].update(sqlalchemy="2.0.54"), {}, "environment.sqlalchemy"),
        (lambda r: r["environment"].update(pycubrid="1.13.0"), {}, "environment.pycubrid"),
        (lambda r: r["environment"].update(cubrid_server="10.2.18"), {}, "cubrid_server"),
        (lambda r: r["environment"].update(python="3.11.9"), {}, "environment.python"),
        (lambda r: r["environment"].update(pool_pre_ping=True), {}, "pool_pre_ping"),
        (
            lambda r: r["environment"].update(
                target="cubrid+pycubrid://dba@otherhost:33000/testdb"
            ),
            {},
            "environment.target",
        ),
        (lambda r: r["workload"].update(script_sha256="3" * 64), {}, "workload.script_sha256"),
        (lambda r: r["environment"]["args"].update(batch=100), {}, "workload.args"),
        (
            lambda r: r["environment"].update(cubrid_image_digest="sha256:" + "4" * 64),
            {},
            "cubrid_image_digest",
        ),
        (lambda r: r["environment"].update(host="otherhost"), {}, "environment.host"),
        (lambda r: r["environment"].update(comparable_group="other"), {}, "comparable_group"),
    ],
)
def test_compare_rejects_any_other_difference(
    tmp_path: Path, edit: Any, kw: dict[str, Any], reason: str
) -> None:
    base = write_artifact(tmp_path / "base", make_report(sha=SHA_A))
    cand_report = make_report(sha=SHA_B)
    edit(cand_report)
    cand = write_artifact(tmp_path / "cand", cand_report)
    out = tmp_path / "compare.json"
    assert ba.main(["compare", str(base), str(cand), "--output", str(out)]) == 3
    result = json.loads(out.read_text())
    assert result["status"] == "not comparable"
    assert result["metrics"] == []
    assert any(reason in r for r in result["reasons"]), result["reasons"]


def test_compare_rejects_different_drivers_and_trial_counts(tmp_path: Path) -> None:
    base = ba.validate(write_artifact(tmp_path / "a", make_report()))
    other = ba.validate(write_artifact(tmp_path / "b", make_report(driver="cubrid", sha=SHA_B)))
    reasons = ba.compare(base, other)["reasons"]
    assert any("environment.driver" in r for r in reasons)
    assert any("metric sets differ" in r for r in reasons)
    six = ba.validate(write_artifact(tmp_path / "c", make_report(sha=SHA_B, trials=6)))
    assert any(r == "trials 5 vs 6" for r in ba.compare(base, six)["reasons"])


def test_compare_of_an_invalid_manifest_is_invalid(tmp_path: Path) -> None:
    base = write_artifact(tmp_path / "base", make_report())
    missing = tmp_path / "missing" / "manifest.json"
    assert ba.main(["compare", str(base), str(missing)]) == ba.EXIT_INVALID


def test_export_rejects_a_report_outside_the_manifest_directory(tmp_path: Path) -> None:
    (tmp_path / "report.json").write_text(json.dumps(make_report()))
    (tmp_path / "out").mkdir()
    argv = ["export", str(tmp_path / "report.json"), "--output", str(tmp_path / "out" / "m.json")]
    assert ba.main(argv) == ba.EXIT_INVALID


@pytest.mark.parametrize(
    "raw",
    [
        "benchmarks/2026-10-12-dialect-baseline/raw/bench_dialect_baseline_sa21.json",
        "benchmarks/2026-10-13-dialect-baseline-followup/raw/"
        + "bench_dialect_baseline_cubrid114_pycubrid.json",
    ],
)
def test_historical_archives_are_not_comparable_artifacts(raw: str) -> None:
    """The #830 reports predate the contract: no status, workload identity or pool fields."""
    path = REPO / raw
    before = path.read_bytes()
    with pytest.raises(ba.ArtifactError, match="not 'complete'"):
        ba.build_manifest(path, root=REPO)
    assert path.read_bytes() == before


def test_baseline_script_records_pool_and_insertmanyvalues_settings() -> None:
    pytest.importorskip("pycubrid")
    from scripts import bench_dialect_baseline as bdb

    dialect = argparse.Namespace(use_insertmanyvalues=True, insertmanyvalues_page_size=1000)
    args = argparse.Namespace(
        dsn="cubrid+pycubrid://dba:secret@localhost:34114/testdb",
        output="y",
        trials=5,
        source_sha=SHA_A,
        server_image_digest=DIGEST,
        host_label="devbox",
        comparable_group="g",
    )
    env = bdb.environment("11.4.6.1963", "pycubrid", "QueuePool", args, dialect)
    assert env["target"] == "cubrid+pycubrid://dba@localhost:34114/testdb"
    assert env["pool_pre_ping"] is False
    assert env["autocommit"] is False
    assert env["use_insertmanyvalues"] is True
    assert env["insertmanyvalues_page_size"] == 1000
    assert env["args"] == {"trials": 5, "source_sha": SHA_A}
    assert (env["cubrid_image_digest"], env["host"], env["comparable_group"]) == (
        DIGEST,
        "devbox",
        "g",
    )


def test_the_first_pinned_pair_is_kept_but_rejected_as_contract_1() -> None:
    pair = REPO / "benchmarks" / "2026-10-14-artifact-pair"
    with pytest.raises(ba.ArtifactError, match="artifact/1"):
        ba.validate(pair / "baseline" / "manifest.json")


def test_the_committed_pinned_pair_is_valid_and_comparable() -> None:
    pair = REPO / "benchmarks" / "2026-10-14-artifact-pair-v2"
    base = ba.validate(pair / "baseline" / "manifest.json")
    cand = ba.validate(pair / "candidate" / "manifest.json")
    result = ba.compare(base, cand)
    assert result["status"] == "comparable", result["reasons"]
    assert result["baseline"]["dialect_source_sha"] != result["candidate"]["dialect_source_sha"]
    assert json.loads((pair / "compare.json").read_text()) == result
    assert len(result["metrics"]) == 19


def test_malformed_inputs_report_invalid_instead_of_a_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest_path = write_artifact(tmp_path, make_report())
    bad = json.loads(manifest_path.read_text())
    bad["files"] = [1]
    manifest_path.write_text(json.dumps(bad))
    assert ba.main(["validate", str(manifest_path)]) == ba.EXIT_INVALID
    assert "invalid:" in capsys.readouterr().err
    (tmp_path / "raw" / "report.json").write_text("[1, 2]")
    argv = ["export", str(tmp_path / "raw" / "report.json"), "--output", str(manifest_path)]
    assert ba.main(argv) == ba.EXIT_INVALID
    report = make_report()
    report["environment"]["args"]["trials"] = "5"
    (tmp_path / "raw" / "report.json").write_text(json.dumps(report))
    assert ba.main(argv) == ba.EXIT_INVALID


# ----- installed-source verification (#903) ---------------------------------------------


def _git_repo(tmp: Path, files: dict[str, str]) -> tuple[Path, str]:
    repo = tmp / "repo"
    (repo / "sqlalchemy_cubrid").mkdir(parents=True)
    for name, text in files.items():
        (repo / "sqlalchemy_cubrid" / name).write_text(text)
    (repo / "sqlalchemy_cubrid" / "py.typed").write_text("")
    (repo / "README").write_text("not part of the package\n")
    env = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), *env, "commit", "-qm", "c"], check=True)
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"]).decode().strip()
    return repo, sha


FILES = {"__init__.py": "x = 1\n", "dialect.py": "y = 2\n"}


def test_git_and_installed_package_hashes_agree(tmp_path: Path) -> None:
    repo, sha = _git_repo(tmp_path, FILES)
    installed = ba.installed_package_files(repo / "sqlalchemy_cubrid")
    assert set(installed) == {"__init__.py", "dialect.py"}
    assert ba.tree_sha256(installed) == ba.tree_sha256(ba.git_package_files(repo, sha))
    assert ba.tree_sha256(installed) != ba.tree_sha256({**installed, "dialect.py": b"y = 3\n"})
    with pytest.raises(ba.ArtifactError, match="failed"):
        ba.git_package_files(repo, "f" * 40)


def test_validate_with_source_repo_recomputes_the_package_hash(tmp_path: Path) -> None:
    repo, sha = _git_repo(tmp_path, FILES)
    report = make_report(sha=sha)
    report["environment"]["dialect_package_sha256"] = ba.tree_sha256(
        ba.installed_package_files(repo / "sqlalchemy_cubrid")
    )
    manifest_path = write_artifact(tmp_path / "a", report)
    assert ba.main(["validate", str(manifest_path), "--source-repo", str(repo)]) == 0
    report["environment"]["dialect_package_sha256"] = "7" * 64
    manifest_path = write_artifact(tmp_path / "b", report)
    with pytest.raises(ba.ArtifactError, match="is not the sqlalchemy_cubrid of commit"):
        ba.validate(manifest_path, repo)
    assert ba.main(["validate", str(manifest_path), "--source-repo", str(repo)]) == 1


class _Dist:
    def __init__(self, direct_url: dict[str, Any] | None) -> None:
        self.direct_url = direct_url

    def read_text(self, name: str) -> str | None:
        assert name == "direct_url.json"
        return None if self.direct_url is None else json.dumps(self.direct_url)


@pytest.fixture
def bdb() -> Any:
    pytest.importorskip("pycubrid")
    from scripts import bench_dialect_baseline

    return bench_dialect_baseline


def test_provenance_of_a_matching_local_checkout(tmp_path: Path, bdb: Any, monkeypatch) -> None:
    repo, sha = _git_repo(tmp_path, FILES)
    monkeypatch.setattr(
        bdb, "distribution", lambda _: _Dist({"url": repo.as_uri(), "dir_info": {}})
    )
    out = bdb.dialect_provenance(sha, repo / "sqlalchemy_cubrid")
    assert out == {
        "dialect_package_sha256": ba.tree_sha256(ba.git_package_files(repo, sha)),
        "source_verification": "local_checkout",
        "installed_revision": sha,
    }


def test_provenance_rejects_a_changed_or_wrong_install(
    tmp_path: Path, bdb: Any, monkeypatch
) -> None:
    repo, sha = _git_repo(tmp_path, FILES)
    monkeypatch.setattr(
        bdb, "distribution", lambda _: _Dist({"url": repo.as_uri(), "dir_info": {"editable": True}})
    )
    (repo / "sqlalchemy_cubrid" / "dialect.py").write_text("y = 3\n")
    with pytest.raises(SystemExit, match="differs from commit .*: dialect.py"):
        bdb.dialect_provenance(sha, repo / "sqlalchemy_cubrid")
    with pytest.raises(SystemExit, match="cannot verify --source-sha"):
        bdb.dialect_provenance("f" * 40, repo / "sqlalchemy_cubrid")


def test_provenance_of_a_vcs_install(tmp_path: Path, bdb: Any, monkeypatch) -> None:
    repo, sha = _git_repo(tmp_path, FILES)
    vcs = {"url": "https://example.com/r.git", "vcs_info": {"vcs": "git", "commit_id": sha}}
    monkeypatch.setattr(bdb, "distribution", lambda _: _Dist(vcs))
    out = bdb.dialect_provenance(sha, repo / "sqlalchemy_cubrid")
    assert (out["source_verification"], out["installed_revision"]) == ("vcs_info", sha)
    with pytest.raises(SystemExit, match="not --source-sha"):
        bdb.dialect_provenance(SHA_B, repo / "sqlalchemy_cubrid")


@pytest.mark.parametrize(
    "direct_url", [None, {"url": "https://pypi.org/x.whl", "archive_info": {}}]
)
def test_provenance_of_an_unverifiable_install(
    tmp_path: Path, bdb: Any, monkeypatch, direct_url: Any
) -> None:
    repo, sha = _git_repo(tmp_path, FILES)
    monkeypatch.setattr(bdb, "distribution", lambda _: _Dist(direct_url))
    out = bdb.dialect_provenance(sha, repo / "sqlalchemy_cubrid")
    assert (out["source_verification"], out["installed_revision"]) == ("unverified", None)
    report = make_report(sha=sha)
    report["environment"].update(out)
    invalid(tmp_path / "art", report, "not verified against the source SHA")
    assert bdb.dialect_provenance("unknown", repo / "sqlalchemy_cubrid")["source_verification"] == (
        "unverified"
    )


def test_provenance_rejects_an_abbreviated_sha_before_git(
    tmp_path: Path, bdb: Any, monkeypatch
) -> None:
    repo, sha = _git_repo(tmp_path, FILES)
    monkeypatch.setattr(
        bdb, "distribution", lambda _: _Dist({"url": repo.as_uri(), "dir_info": {}})
    )
    for claimed in (sha[:12], sha.upper(), sha + "0"):
        with pytest.raises(SystemExit, match="not a full 40-character commit SHA"):
            bdb.dialect_provenance(claimed, repo / "sqlalchemy_cubrid")


def test_file_url_paths(bdb: Any) -> None:
    assert bdb.file_url_path("file:///srv/my%20repo") == Path("/srv/my repo")
    assert bdb.file_url_path("file://localhost/srv/repo") == Path("/srv/repo")
    assert str(bdb.file_url_path("file://server/share/repo")).startswith("//server/share")
