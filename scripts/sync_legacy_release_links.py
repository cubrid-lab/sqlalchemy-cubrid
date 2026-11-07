"""Apply only reviewed, byte-for-byte historical repository-link corrections."""
import argparse
import json
import re
import subprocess
from pathlib import Path

REPO = "cubrid-lab/sqlalchemy-cubrid"
TAGS = ["v1.3.0","v1.2.3","v1.2.1","v1.1.0","v1.0.0"]
ROOT = Path("docs/release-note-repairs")
OLD = "https://github.com/cubrid-labs/sqlalchemy-cubrid"
NEW = "https://github.com/cubrid-lab/sqlalchemy-cubrid"
ALLOWED = re.compile(re.escape(OLD) + r"(?=/(?:compare/|blob/main/CHANGELOG\.md|issues/\d+|pull/\d+))")


def corrected(original):
    return ALLOWED.sub(NEW, original)


def gh(path, payload=None):
    args = ["gh", "api"]
    if payload is not None:
        args += ["--method", "PATCH", "--input", "-"]
    args.append(path)
    proc = subprocess.run(args, input=json.dumps(payload) if payload else None, text=True, capture_output=True, check=True)
    return json.loads(proc.stdout)


def run(apply):
    for tag in TAGS:
        before = (ROOT / (tag + ".original.md")).read_text(encoding="utf-8")
        after = (ROOT / (tag + ".corrected.md")).read_text(encoding="utf-8")
        if corrected(before) != after or before == after:
            raise ValueError(f"{tag}: source differs from approved link-only correction")
        if not apply:
            print(f"{tag}: reviewed link-only source verified")
            continue
        endpoint = f"repos/{REPO}/releases/tags/{tag}"
        current = gh(endpoint)
        if current.get("tag_name") != tag or current.get("draft") is not False or not current.get("published_at"):
            raise ValueError(f"{tag}: no verified published release")
        body = current.get("body")
        if body == after:
            print(f"{tag}: already corrected")
            continue
        if body != before:
            raise ValueError(f"{tag}: published description changed; refusing to overwrite it")
        rid = current["id"]
        latest = gh(f"repos/{REPO}/releases/{rid}")
        if (latest.get("body"), latest.get("tag_name"), latest.get("draft")) != (before, tag, False):
            raise ValueError(f"{tag}: concurrent release change")
        updated = gh(f"repos/{REPO}/releases/{rid}", {"body": after})
        verified = gh(f"repos/{REPO}/releases/{rid}")
        for item in [updated, verified]:
            if item.get("body") != after or item.get("tag_name") != tag or item.get("draft") is not False:
                raise ValueError(f"{tag}: published correction verification failed")
        if latest.get("published_at") != verified.get("published_at") or latest.get("prerelease") != verified.get("prerelease"):
            raise ValueError(f"{tag}: published release metadata changed unexpectedly")
        print(f"{tag}: corrected navigational links without changing tag or artifacts")


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--apply", action="store_true")
    parsed = args.parse_args()
    run(parsed.apply)
