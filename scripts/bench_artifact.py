#!/usr/bin/env python3
"""Versioned benchmark artifact manifests for external regression tracking (#901).

Turns one complete ``scripts/bench_dialect_baseline.py`` report into a manifest
that names its exact environment, workload identity, independent trial values
and the advisory metric set, validates such a manifest against the files it
lists, and compares a baseline with a candidate. It adds no benchmark of its own.

Contract ``sqlalchemy-cubrid-benchmark-artifact/2`` (see docs/PERFORMANCE.md,
"Benchmark artifact contract"; ``/1`` manifests are rejected):

* ``environment``: the dialect source SHA and version, the installed package's
  SHA-256 and how the SHA was verified, SQLAlchemy 2.0.x or 2.1.x, the driver and
  its version, the CUBRID server version and image digest, Python, the host
  label, the pool, ``pool_pre_ping``, autocommit and the dialect's
  insertmanyvalues settings.
* ``workload``: the script and its SHA-256, the table and every argument except
  ``source_sha``.
* ``trials``: the number of independent trials (at least 3).
* ``files``: the report (``role: raw``) and any log, with SHA-256 and relative path.
* ``metrics``: the advisory set below. Each has its unit, rows per timed call,
  SQL shape, commit policy, warm-up, the verified condition, every trial value
  and the median. The report exists only when every check of the run passed.

A comparison is valid only within one ``comparable_group`` and when everything
except the dialect source SHA and version is identical; otherwise it reports
``not comparable`` with the reasons. The result is advisory, not a gate.

Provenance (#903). The benchmark refuses to run when the installed dialect
does not match ``--source-sha``: for an install from a local checkout it compares
the installed ``sqlalchemy_cubrid/*.py`` with that commit's files, for a VCS
install it compares the recorded commit. ``export`` rejects an unverified install
(for example from PyPI). The image digest, host label and group are benchmark
arguments recorded in the report, so ``validate``, which rebuilds the manifest
from the hashed report, rejects an in-place edit of them in the manifest.
``validate --source-repo DIR`` also recomputes the package SHA-256 from that
commit in ``DIR``. Editing the report and the manifest together is not detected;
keep artifacts in git.

Usage:
    python scripts/bench_artifact.py export raw/report.json --output manifest.json \\
        [--log raw/report.txt]
    python scripts/bench_artifact.py validate manifest.json [--source-repo DIR]
    python scripts/bench_artifact.py compare baseline/manifest.json \\
        candidate/manifest.json [--source-repo DIR]

Exit codes: 0 valid / comparable, 1 invalid input, 2 usage error, 3 not comparable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "sqlalchemy-cubrid-benchmark-artifact/2"
PACKAGE = "sqlalchemy_cubrid"
VERIFIED_SOURCES = ("local_checkout", "vcs_info")
SCRIPT = "scripts/bench_dialect_baseline.py"
TABLE = "bench_dialect_baseline"
MIN_TRIALS = 3
FETCH_ROWS = 1000
SUPPORTED_SQLALCHEMY = re.compile(r"^2\.[01]\.\d+$")
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
DRIVERS = {"pycubrid": "pycubrid", "cubrid": "cubrid_python", "aiopycubrid": "pycubrid"}
# The environment fields a candidate may change; everything else must match.
CANDIDATE_FIELDS = (
    "dialect_source_sha",
    "sqlalchemy_cubrid",
    "dialect_package_sha256",
    "source_verification",
)

EXIT_INVALID = 1
EXIT_NOT_COMPARABLE = 3

_WARMUP = "one unrecorded pass of the variant before each trial's timed pass"
_SELECT = {
    "unit": "us",
    "statistic": "median latency of one statement within a trial",
    "rows_per_call": 1,
    "commit": "none (read in an open transaction)",
    "verified": "every returned row has the requested primary key",
}
_FETCH = {
    "unit": "us",
    "statistic": "median latency of one fetch within a trial",
    "rows_per_call": FETCH_ROWS,
    "commit": "none (read in an open transaction)",
    "verified": "every fetch returns all seeded rows",
}
_BATCH = {
    "unit": "ms",
    "statistic": "median time of one batch statement and its commit within a trial",
    "rows_per_call": None,  # the run's --batch
    "commit": "one commit per batch statement, inside the timed region",
    "verified": "table COUNT and SUM after each stage; statement rowcount where reported",
}
_FC20 = "cursor.executemany() of literal-rendered rows: one EXECUTE_BATCH (FC20)"
_FC21 = "cursor.executemany(prepared=True): PREPARE + EXECUTE_ARRAY (FC2 + FC21), opt-in"
_IMV = "Core insert() executemany through insertmanyvalues: multi-row INSERT ... VALUES"
_DIALECT_EM = "Core executemany through PyCubridDialect.do_executemany: literal FC20"
_PER_ROW = "through CubridDialect.do_executemany: one cursor.execute() per parameter set"
# CUBRIDdb runs its own executemany and the base dialect's per-row guard (#502).
CUBRIDDB_SHAPES = {
    **{
        f"batch.raw.{s}": "raw CUBRIDdb cursor.executemany()"
        for s in ("insert", "update", "delete")
    },
    "batch.core.update": f"Core executemany {_PER_ROW}",
    "batch.core.delete": f"Core executemany {_PER_ROW}",
    "batch.orm.update": f"ORM bulk update(Item) by primary key {_PER_ROW}",
}

# id -> (path in the report's summary, contract fields, SQL shape, drivers that run it)
METRICS: dict[str, tuple[tuple[str, ...], dict[str, Any], str, frozenset[str]]] = {}


def _metric(
    mid: str, path: tuple[str, ...], kind: dict[str, Any], shape: str, drivers: set[str]
) -> None:
    METRICS[mid] = (path, kind, shape, frozenset(drivers))


_ALL = set(DRIVERS)
_SYNC_PREPARED = {"pycubrid"}
_metric("select_pk.raw", ("select_pk_us", "raw"), _SELECT, "raw cursor execute + fetchone", _ALL)
_metric(
    "select_pk.core_cached",
    ("select_pk_us", "core_cached"),
    _SELECT,
    "Core select() with the compiled cache",
    _ALL,
)
_metric(
    "select_pk.core_uncached",
    ("select_pk_us", "core_uncached"),
    _SELECT,
    "Core select() with compiled_cache=None",
    _ALL,
)
_metric("select_pk.orm", ("select_pk_us", "orm"), _SELECT, "ORM select(Item) scalar_one", _ALL)
_metric("fetch_all.raw", ("fetch_all_us", "raw"), _FETCH, "raw cursor fetchall()", _ALL)
_metric("fetch_all.core", ("fetch_all_us", "core"), _FETCH, "Core execute().all()", _ALL)
_metric("fetch_all.orm", ("fetch_all_us", "orm"), _FETCH, "ORM scalars().all()", _ALL)
for _stage in ("insert", "update", "delete"):
    _metric(f"batch.raw.{_stage}", ("batch_ms", "raw", _stage), _BATCH, _FC20, _ALL)
    _metric(
        f"batch.raw_prepared.{_stage}",
        ("batch_ms", "raw_prepared", _stage),
        _BATCH,
        _FC21,
        _SYNC_PREPARED,
    )
_metric("batch.core.insert", ("batch_ms", "core", "insert"), _BATCH, _IMV, _ALL)
_metric("batch.core.update", ("batch_ms", "core", "update"), _BATCH, _DIALECT_EM, _ALL)
_metric("batch.core.delete", ("batch_ms", "core", "delete"), _BATCH, _DIALECT_EM, _ALL)
_metric(
    "batch.orm.insert",
    ("batch_ms", "orm", "insert"),
    _BATCH,
    "ORM bulk insert(Item) through insertmanyvalues",
    _ALL,
)
_metric(
    "batch.orm.update",
    ("batch_ms", "orm", "update"),
    _BATCH,
    "ORM bulk update(Item) by primary key through do_executemany",
    _ALL,
)
_metric(
    "batch.orm.delete",
    ("batch_ms", "orm", "delete"),
    _BATCH,
    "ORM unit-of-work DELETE of loaded objects",
    _ALL,
)


class ArtifactError(ValueError):
    """The input is missing, corrupt or violates the contract."""


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ArtifactError(f"cannot read {path}: {exc}") from None


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"cannot read JSON {path}: {exc}") from None


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ArtifactError(msg)


def tree_sha256(files: Mapping[str, bytes]) -> str:
    """SHA-256 over ``relative path NUL sha256(content) LF`` of every file, in path order."""
    h = hashlib.sha256()
    for name in sorted(files):
        h.update(name.encode() + b"\0" + hashlib.sha256(files[name]).hexdigest().encode() + b"\n")
    return h.hexdigest()


def installed_package_files(package_dir: Path) -> dict[str, bytes]:
    """The ``*.py`` files of an installed package, keyed by path inside the package."""
    return {
        p.relative_to(package_dir).as_posix(): p.read_bytes()
        for p in package_dir.rglob("*.py")
        if "__pycache__" not in p.parts
    }


def _git(repo: Path, *args: str) -> bytes:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"") or b""
        raise ArtifactError(
            f"git {' '.join(args)} failed in {repo}: {detail.decode(errors='replace').strip()}"
        ) from None


def git_package_files(repo: Path, sha: str) -> dict[str, bytes]:
    """The ``sqlalchemy_cubrid/*.py`` files of commit ``sha`` in ``repo``."""
    names = _git(repo, "ls-tree", "-r", "--name-only", sha, "--", f"{PACKAGE}/").decode()
    files = {
        name[len(PACKAGE) + 1 :]: _git(repo, "show", f"{sha}:{name}")
        for name in names.splitlines()
        if name.endswith(".py")
    }
    _require(bool(files), f"commit {sha} in {repo} has no {PACKAGE}/*.py files")
    return files


def _relative(path: str) -> str:
    pure = PurePosixPath(path)
    _require(
        bool(path) and not pure.is_absolute() and ".." not in pure.parts and "\\" not in path,
        f"file path {path!r} must be relative to the manifest, without '..'",
    )
    return str(pure)


def _trial_values(values: Any, trials: int, mid: str) -> list[float]:
    _require(isinstance(values, list), f"{mid}: trial values missing")
    _require(len(values) == trials, f"{mid}: {len(values)} trial values, expected {trials}")
    for v in values:
        _require(
            isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0,
            f"{mid}: trial value {v!r} is not a positive finite number",
        )
    return [float(v) for v in values]


def _environment(report: dict[str, Any]) -> dict[str, Any]:
    env: Any = report.get("environment")
    _require(isinstance(env, dict), "report has no environment")
    args = env.get("args")
    _require(isinstance(args, dict), "report environment has no args")
    sha = env.get("source_sha")
    _require(
        isinstance(sha, str) and SHA1.match(sha) is not None,
        f"dialect source SHA {sha!r} is not a full 40-character commit SHA",
    )
    _require(
        args.get("source_sha") == sha,
        f"mixed revision: environment source_sha {sha} but args.source_sha "
        f"{args.get('source_sha')}",
    )
    sa = env.get("sqlalchemy")
    _require(
        isinstance(sa, str) and SUPPORTED_SQLALCHEMY.match(sa) is not None,
        f"unsupported SQLAlchemy version {sa!r}: only 2.0.x and 2.1.x",
    )
    driver = env.get("driver")
    _require(driver in DRIVERS, f"unsupported driver {driver!r}")
    driver_version = env.get(DRIVERS[driver])
    digest = env.get("cubrid_image_digest")
    _require(
        isinstance(digest, str) and DIGEST.match(digest) is not None,
        f"bad or missing image digest {digest!r} (benchmark --server-image-digest)",
    )
    host = env.get("host")
    _require(isinstance(host, str) and bool(host), "host label missing (benchmark --host-label)")
    verification = env.get("source_verification")
    _require(
        verification in VERIFIED_SOURCES,
        f"installed dialect not verified against the source SHA ({verification!r}); "
        "install it from a git checkout or a VCS URL",
    )
    package_sha = env.get("dialect_package_sha256")
    _require(
        isinstance(package_sha, str) and SHA256.match(package_sha) is not None,
        "dialect_package_sha256 missing",
    )
    _require(
        env.get("installed_revision") == sha,
        f"installed revision {env.get('installed_revision')!r} is not the source SHA {sha}",
    )
    out = {
        "dialect_source_sha": sha,
        "dialect_package_sha256": package_sha,
        "source_verification": verification,
        "sqlalchemy_cubrid": env.get("sqlalchemy_cubrid"),
        "sqlalchemy": sa,
        "driver": driver,
        "driver_version": driver_version,
        "pycubrid": env.get("pycubrid"),
        "cubrid_server": env.get("cubrid_server"),
        "cubrid_image_digest": digest,
        "python": env.get("python"),
        "implementation": env.get("implementation"),
        "platform": env.get("platform"),
        "cpu": env.get("cpu"),
        "host": host,
        "target": env.get("target"),
        "pool": env.get("pool"),
        "pool_pre_ping": env.get("pool_pre_ping"),
        "autocommit": env.get("autocommit"),
        "use_insertmanyvalues": env.get("use_insertmanyvalues"),
        "insertmanyvalues_page_size": env.get("insertmanyvalues_page_size"),
    }
    missing = [k for k, v in out.items() if v is None or v == ""]
    _require(not missing, f"report environment is missing {', '.join(missing)}")
    return out


def build_manifest(report_path: Path, *, root: Path, logs: Sequence[Path] = ()) -> dict[str, Any]:
    """Build the manifest of one complete report; paths are relative to ``root``."""
    try:
        return _build_manifest(report_path, root=root, logs=logs)
    except (AttributeError, KeyError, TypeError) as exc:
        raise ArtifactError(f"{report_path}: malformed report ({exc!r})") from None


def _build_manifest(report_path: Path, *, root: Path, logs: Sequence[Path] = ()) -> dict[str, Any]:
    """Build the manifest of one complete report; paths are relative to ``root``."""
    report = _load_json(report_path)
    _require(isinstance(report, dict), f"{report_path} is not a report object")
    _require(
        report.get("status") == "complete",
        f"{report_path}: status {report.get('status')!r}, not 'complete' "
        "(an older or interrupted run is not a comparable artifact)",
    )
    env = _environment(report)
    group = report["environment"].get("comparable_group")
    _require(
        isinstance(group, str) and bool(group),
        "comparable group missing (benchmark --comparable-group)",
    )
    workload = report.get("workload")
    _require(isinstance(workload, dict), "report has no workload identity")
    _require(workload.get("script") == SCRIPT, f"workload script {workload.get('script')!r}")
    _require(workload.get("table") == TABLE, f"workload table {workload.get('table')!r}")
    script_sha = workload.get("script_sha256")
    _require(
        isinstance(script_sha, str) and SHA256.match(script_sha) is not None,
        "workload script_sha256 missing",
    )
    # source_sha is the candidate dimension, recorded in the environment.
    args = {k: v for k, v in report["environment"]["args"].items() if k != "source_sha"}
    trials: Any = args.get("trials")
    _require(
        isinstance(trials, int) and trials >= MIN_TRIALS,
        f"{trials!r} trials; at least {MIN_TRIALS} independent trials are required",
    )
    _require(
        isinstance(report.get("trials"), list) and len(report["trials"]) == trials,
        f"report holds {len(report.get('trials') or [])} trials, args say {trials}",
    )
    _require(args.get("rows") == FETCH_ROWS, f"rows {args.get('rows')!r}, expected {FETCH_ROWS}")
    batch = args.get("batch")
    _require(
        isinstance(batch, int) and not isinstance(batch, bool) and batch > 0,
        f"batch {batch!r} is not a positive integer",
    )
    summary = report.get("summary")
    _require(isinstance(summary, dict), "report has no summary")

    metrics = []
    for mid, (path, kind, shape, drivers) in METRICS.items():
        if env["driver"] not in drivers:
            continue
        node: Any = summary
        for key in path:
            _require(isinstance(node, dict) and key in node, f"{mid}: summary.{'.'.join(path)}")
            node = node[key]
        _require(isinstance(node, dict), f"{mid}: summary.{'.'.join(path)} is not an object")
        _require(
            isinstance(node.get("median"), (int, float)), f"{mid}: summary median is not a number"
        )
        values = _trial_values(node.get("trials"), trials, mid)
        median = statistics.median(values)
        _require(
            math.isclose(node.get("median", math.nan), median, rel_tol=1e-9),
            f"{mid}: summary median {node.get('median')!r} differs from the trial values",
        )
        fields = dict(kind)
        if fields["rows_per_call"] is None:
            fields["rows_per_call"] = batch
        metrics.append(
            {
                "id": mid,
                "source": "summary." + ".".join(path),
                **fields,
                "sql_shape": CUBRIDDB_SHAPES.get(mid, shape)
                if env["driver"] == "cubrid"
                else shape,
                "warmup": _WARMUP,
                "trials": values,
                "median": median,
            }
        )

    files = [{"path": _relative(report_path.relative_to(root).as_posix()), "role": "raw"}]
    files += [{"path": _relative(p.relative_to(root).as_posix()), "role": "log"} for p in logs]
    for f in files:
        f["sha256"] = _sha256(root / f["path"])
    paths = [f["path"] for f in files]
    _require(len(set(paths)) == len(paths), f"duplicate file paths {paths}")
    return {
        "schema": SCHEMA,
        "comparable_group": group,
        "environment": env,
        "workload": {
            "script": SCRIPT,
            "script_sha256": script_sha,
            "table": TABLE,
            "args": args,
        },
        "trials": trials,
        "files": files,
        "metrics": metrics,
    }


def validate(manifest_path: Path, source_repo: Path | None = None) -> dict[str, Any]:
    """Check a manifest and rebuild it from the files it lists; return it.

    With ``source_repo``, also recompute the installed package's SHA-256 from the
    manifest's dialect source SHA in that git repository.
    """
    try:
        manifest = _validate(manifest_path)
        if source_repo is not None:
            env = manifest["environment"]
            expected = tree_sha256(git_package_files(source_repo, env["dialect_source_sha"]))
            _require(
                expected == env["dialect_package_sha256"],
                f"dialect_package_sha256 {env['dialect_package_sha256']} is not the "
                f"{PACKAGE} of commit {env['dialect_source_sha']} ({expected})",
            )
        return manifest
    except (AttributeError, KeyError, TypeError) as exc:
        raise ArtifactError(f"{manifest_path}: malformed manifest ({exc!r})") from None


def _validate(manifest_path: Path) -> dict[str, Any]:
    manifest: dict[str, Any] = _load_json(manifest_path)
    _require(isinstance(manifest, dict), f"{manifest_path} is not a manifest object")
    _require(manifest.get("schema") == SCHEMA, f"schema {manifest.get('schema')!r}, not {SCHEMA}")
    root = manifest_path.parent
    files: Any = manifest.get("files")
    _require(isinstance(files, list) and bool(files), "manifest lists no files")
    _require(all(isinstance(f, dict) for f in files), "every file entry must be an object")
    paths = [_relative(str(f.get("path", ""))) for f in files]
    _require(len(set(paths)) == len(paths), f"duplicate file paths {paths}")
    for f, path in zip(files, paths):
        _require(f.get("role") in ("raw", "log"), f"{path}: role {f.get('role')!r}")
        actual = _sha256(root / path)
        _require(actual == f.get("sha256"), f"{path}: SHA-256 {actual} does not match the manifest")
    raws = [p for f, p in zip(files, paths) if f["role"] == "raw"]
    _require(len(raws) == 1, f"expected exactly one raw report, got {raws}")
    _require(isinstance(manifest.get("environment"), dict), "manifest has no environment")
    metrics: Any = manifest.get("metrics")
    _require(
        isinstance(metrics, list) and all(isinstance(m, dict) for m in metrics),
        "manifest metrics must be a list of objects",
    )
    for m in metrics:
        mid = m.get("id")
        _require(mid in METRICS, f"unknown metric {mid!r}")
        unit = METRICS[mid][1]["unit"]
        _require(m.get("unit") == unit, f"{mid}: unit {m.get('unit')!r}, expected {unit!r}")
    rebuilt = build_manifest(
        root / raws[0],
        root=root,
        logs=[root / p for f, p in zip(files, paths) if f["role"] == "log"],
    )
    for key in ("comparable_group", "environment", "workload", "trials", "files", "metrics"):
        _require(
            manifest.get(key) == rebuilt[key],
            f"manifest {key} does not match the files it lists (edited or mixed inputs)",
        )
    return manifest


def compare(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Compare two valid manifests; ``status`` is ``comparable`` or ``not comparable``."""
    reasons = []
    if baseline["comparable_group"] != candidate["comparable_group"]:
        reasons.append(
            f"comparable_group {baseline['comparable_group']!r} vs "
            f"{candidate['comparable_group']!r}"
        )
    benv, cenv = baseline["environment"], candidate["environment"]
    for key in sorted(set(benv) | set(cenv)):
        if key not in CANDIDATE_FIELDS and benv.get(key) != cenv.get(key):
            reasons.append(f"environment.{key} {benv.get(key)!r} vs {cenv.get(key)!r}")
    for key in sorted(set(baseline["workload"]) | set(candidate["workload"])):
        if baseline["workload"].get(key) != candidate["workload"].get(key):
            reasons.append(f"workload.{key} differs")
    if baseline["trials"] != candidate["trials"]:
        reasons.append(f"trials {baseline['trials']} vs {candidate['trials']}")
    bm = {m["id"]: m for m in baseline["metrics"]}
    cm = {m["id"]: m for m in candidate["metrics"]}
    if set(bm) != set(cm):
        reasons.append(f"metric sets differ: {sorted(set(bm) ^ set(cm))}")
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "not comparable" if reasons else "comparable",
        "reasons": reasons,
        "baseline": {k: benv[k] for k in CANDIDATE_FIELDS},
        "candidate": {k: cenv[k] for k in CANDIDATE_FIELDS},
        "metrics": [],
    }
    if not reasons:
        for mid, b in bm.items():
            c = cm[mid]
            result["metrics"].append(
                {
                    "id": mid,
                    "unit": b["unit"],
                    "baseline_median": b["median"],
                    "candidate_median": c["median"],
                    "ratio": c["median"] / b["median"],
                }
            )
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    ex = sub.add_parser("export", help="write the manifest of one complete report")
    ex.add_argument("report", type=Path)
    ex.add_argument("--output", type=Path, required=True)
    ex.add_argument("--log", type=Path, action="append", default=[])
    va = sub.add_parser("validate", help="check a manifest against its files")
    va.add_argument("manifest", type=Path)
    co = sub.add_parser("compare", help="compare a baseline and a candidate manifest")
    co.add_argument("baseline", type=Path)
    co.add_argument("candidate", type=Path)
    co.add_argument("--output", type=Path)
    for p in (va, co):
        p.add_argument(
            "--source-repo",
            type=Path,
            help="git repository to recompute the installed package SHA-256 from",
        )
    args = ap.parse_args(argv)

    try:
        if args.command == "export":
            root = args.output.resolve().parent
            manifest = build_manifest(
                args.report.resolve(), root=root, logs=[p.resolve() for p in args.log]
            )
            args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            print(f"wrote {args.output}: {len(manifest['metrics'])} metrics")
            return 0
        if args.command == "validate":
            manifest = validate(args.manifest, args.source_repo)
            print(f"valid: {args.manifest} ({len(manifest['metrics'])} metrics)")
            return 0
        result = compare(
            validate(args.baseline, args.source_repo), validate(args.candidate, args.source_repo)
        )
    except ArtifactError as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return EXIT_INVALID
    except ValueError as exc:  # Path.relative_to: a file outside the manifest directory
        print(f"invalid: {exc}", file=sys.stderr)
        return EXIT_INVALID
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(f"{result['status']}: {args.baseline} -> {args.candidate}")
    for reason in result["reasons"]:
        print(f"  {reason}")
    for m in result["metrics"]:
        print(
            f"  {m['id']:<28} {m['baseline_median']:12.3f} -> {m['candidate_median']:12.3f} "
            f"{m['unit']:<2}  x{m['ratio']:.3f}"
        )
    return 0 if result["status"] == "comparable" else EXIT_NOT_COMPARABLE


if __name__ == "__main__":
    raise SystemExit(main())
