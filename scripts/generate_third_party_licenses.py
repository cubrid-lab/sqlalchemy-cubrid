"""Print the third-party license inventory of the current Python environment.

Run it with the interpreter of an isolated environment that has exactly the
dependency set to inventory installed (#735)::

    uv venv -p 3.12 /tmp/tpl-dev
    uv pip install -p /tmp/tpl-dev/bin/python -e ".[dev]"
    /tmp/tpl-dev/bin/python scripts/generate_third_party_licenses.py --exclude pycubrid

Only the standard library is used, so the generator itself never appears in the
inventory. A license is read from the PEP 639 ``License-Expression`` field, then
from ``License ::`` classifiers, then from a short ``License`` field; anything
else is reported as ``UNKNOWN`` rather than guessed. Any GPL-family mention, or
an unrecognised license, is categorised ``Needs review`` and must be resolved in
THIRD_PARTY_LICENSES.md from the package's own license files.

``--required-by`` adds a column naming the installed distributions whose
unconditional or platform-conditional requirements pull each row in; edges
gated on an ``extra`` are used only for a row that has no other parent.
"""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import re
import sys

# Licence expressions and classifier lists are split into parts; every part must
# be recognised for an automatic category, otherwise the row needs review.
PART_SPLIT = re.compile(r"\s+(?:AND|OR|WITH)\s+|\s*/\s*|[()]", re.IGNORECASE)
PERMISSIVE_PART = re.compile(
    r"^(?:MIT(?:-0)?(?: License)?|BSD(?:-[23]-Clause)?(?: License)?|0BSD|"
    r"Apache(?:-2\.0| Software License| License 2\.0)|ISC(?: License)?|ISCL|PSF-2\.0|"
    r"Python Software Foundation License|(?:The )?Unlicense|Public Domain)$",
    re.IGNORECASE,
)
MPL_PART = re.compile(r"^(?:MPL|Mozilla Public License)", re.IGNORECASE)
# No closing word boundary: "GPLv3", "LGPLv2+" must match too.
GPL_FAMILY = re.compile(r"\b(?:A|L)?GPL|General Public License", re.IGNORECASE)
REQUIREMENT_NAME = re.compile(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
EXTRA_MARKER = re.compile(r"\bextra\s*==")


def field(dist: metadata.Distribution, key: str) -> str:
    values = dist.metadata.get_all(key) or []
    return str(values[0]).strip() if values else ""


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def license_of(dist: metadata.Distribution) -> str:
    expression = field(dist, "License-Expression")
    if expression:
        return expression
    classifiers = [
        c.split("::")[-1].strip()
        for c in dist.metadata.get_all("Classifier") or []
        if c.startswith("License ::") and c.split("::")[-1].strip() != "OSI Approved"
    ]
    if classifiers:
        return " / ".join(sorted(set(classifiers)))
    text = field(dist, "License")
    if text and "\n" not in text and len(text) <= 60:
        return text
    return "UNKNOWN"


def category(license_text: str) -> str:
    """Classify a licence string; anything not fully recognised needs review."""
    if GPL_FAMILY.search(license_text):
        return "Needs review"
    parts = [p.strip() for p in PART_SPLIT.split(license_text) if p and p.strip()]
    if not parts:
        return "Needs review"
    mpl = False
    for part in parts:
        if MPL_PART.match(part):
            mpl = True
        elif not PERMISSIVE_PART.match(part):
            return "Needs review"
    return "Weak copyleft (MPL)" if mpl else "Permissive"


def url_of(dist: metadata.Distribution) -> str:
    for entry in dist.metadata.get_all("Project-URL") or []:
        label, _, url = str(entry).partition(",")
        if label.strip().lower() in {"homepage", "home", "source", "repository", "source code"}:
            return url.strip()
    return field(dist, "Home-page") or "-"


def required_by() -> dict[str, list[str]]:
    """Map each installed distribution to the installed ones that require it."""
    installed = {canonical(field(d, "Name")) for d in metadata.distributions()}
    plain: dict[str, set[str]] = {}
    via_extra: dict[str, set[str]] = {}
    for dist in metadata.distributions():
        parent = field(dist, "Name")
        for requirement in dist.requires or []:
            spec, _, marker = requirement.partition(";")
            match = REQUIREMENT_NAME.match(spec)
            if not match or canonical(match.group(1)) not in installed:
                continue
            edges = via_extra if EXTRA_MARKER.search(marker) else plain
            edges.setdefault(canonical(match.group(1)), set()).add(parent)
    names = set(plain) | set(via_extra)
    return {
        name: sorted(plain.get(name) or via_extra.get(name, set()), key=str.lower) for name in names
    }


def rows(exclude: set[str]) -> list[tuple[str, str, str, str, str]]:
    seen: dict[str, tuple[str, str, str, str, str]] = {}
    for dist in metadata.distributions():
        name = field(dist, "Name")
        if not name or canonical(name) in exclude:
            continue
        lic = license_of(dist)
        seen[canonical(name)] = (name, dist.version, lic, category(lic), url_of(dist))
    order = {"Permissive": 0, "Weak copyleft (MPL)": 1, "Needs review": 2}
    return sorted(seen.values(), key=lambda r: (order[r[3]], canonical(r[0])))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--exclude", action="append", default=[], help="distribution to skip")
    parser.add_argument(
        "--required-by", action="store_true", help="add a column naming each row's parents"
    )
    args = parser.parse_args(argv)
    exclude = {canonical(e) for e in args.exclude}
    parents = required_by() if args.required_by else {}
    extra_header = " Required by |" if args.required_by else ""
    print(f"| Name | Version | License | Category | URL |{extra_header}")
    print("|---|---|---|---|---|" + ("---|" if args.required_by else ""))
    for name, version, lic, cat, url in rows(exclude):
        line = f"| {name} | {version} | {lic} | {cat} | {url} |"
        if args.required_by:
            line += f" {', '.join(parents.get(canonical(name), [])) or '-'} |"
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
