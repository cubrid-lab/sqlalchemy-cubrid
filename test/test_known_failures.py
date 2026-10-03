# test/test_known_failures.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Offline checks for the lane-keyed compliance-suite manifest (#463).

The live compliance lanes only read ``test/known_failures.txt`` when a CUBRID
server is available; these checks catch a malformed or unkeyed entry in the
offline suite instead.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from test.conftest import (
    _GATED_SERVER_LANES,
    _KNOWN_FAILURES_FILE,
    _PINNED_SQLALCHEMY,
    _load_known_failures,
    _normalize_nodeid,
    _skipped_known_failure,
)

# Lanes gated in .github/workflows/ci.yml; each must have a reviewed baseline.
_GATED_LANES = {"cubrid@sa2.0", "pycubrid@sa2.0", "pycubrid@sa2.1"}
_CI = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "ci.yml"


def test_manifest_lanes_match_the_gated_ci_lanes():
    lanes = _load_known_failures(_KNOWN_FAILURES_FILE)
    assert {tag.split("@cubrid")[0] for tag in lanes} == _GATED_LANES
    assert _GATED_LANES <= set(lanes)


def test_driver_only_entries_stay_in_their_lane():
    lanes = _load_known_failures(_KNOWN_FAILURES_FILE)
    cubriddb_numeric = "test/test_suite.py::NumericTest::test_float_as_decimal"
    assert cubriddb_numeric in lanes["cubrid@sa2.0"]
    assert cubriddb_numeric not in lanes["pycubrid@sa2.0"]
    denormalize = (
        "test/test_suite.py::NameDenormalizeTest::test_cols_driver_cols[use_driver_cols-text_star]"
    )
    assert denormalize in lanes["pycubrid@sa2.1"]
    assert denormalize not in lanes["pycubrid@sa2.0"]


@pytest.mark.parametrize(
    "entry",
    [
        "test/test_suite.py::X::test_y",
        "test/test_suite.py::X::test_y  pycubrid",
        "test/test_suite.py::X::test_y  pycubrid@2.1",
        "test/test_suite.py::X::test_y  aiopycubrid@sa2.1",
    ],
)
def test_entry_without_a_valid_lane_tag_is_rejected(tmp_path: Path, entry: str):
    manifest = tmp_path / "known_failures.txt"
    manifest.write_text(f"# comment\n\n{entry}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="known_failures.txt:3"):
        _load_known_failures(manifest)


def test_node_id_with_spaces_and_server_lane(tmp_path: Path):
    manifest = tmp_path / "known_failures.txt"
    nodeid = "test/test_suite.py::X::test_y[per % cent-(3)]"
    manifest.write_text(f"{nodeid}  pycubrid@sa2.1@cubrid11.4\n", encoding="utf-8")
    assert _load_known_failures(manifest) == {"pycubrid@sa2.1@cubrid11.4": {nodeid}}


@pytest.mark.parametrize(
    "tag",
    [
        "pycubrid@sa2.1@cubrid11.3",  # typo'd / unsupported server
        "pycubrid@sa2.1@cubrid1.4",
        "pycubrid@sa2.0@cubrid11.4",  # supported server, but not a gated pair
        "cubrid@sa2.0@cubrid10.2",
    ],
)
def test_server_narrowed_tag_must_be_a_gated_pair(tmp_path: Path, tag: str):
    manifest = tmp_path / "known_failures.txt"
    manifest.write_text(f"test/test_suite.py::X::test_y  {tag}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not a gated"):
        _load_known_failures(manifest)


@pytest.mark.parametrize("tag", ["pycubrid@sa2.2", "cubrid@sa9.9", "cubrid@sa2.1@cubrid11.4"])
def test_lane_that_ci_does_not_gate_is_rejected(tmp_path: Path, tag: str):
    manifest = tmp_path / "known_failures.txt"
    manifest.write_text(f"test/test_suite.py::X::test_y  {tag}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown lane"):
        _load_known_failures(manifest)


def test_duplicate_node_id_is_rejected(tmp_path: Path):
    manifest = tmp_path / "known_failures.txt"
    manifest.write_text(
        "test/test_suite.py::X::test_y  cubrid@sa2.0\n"
        "# another group\n"
        "test/test_suite.py::X::test_y  pycubrid@sa2.1\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="known_failures.txt:3: .* already listed on line 1"):
        _load_known_failures(manifest)


def test_gated_server_lanes_and_pins_match_ci():
    """The (lane, server) pairs and SQLAlchemy pins in conftest.py are the ones ci.yml runs."""
    ci = _CI.read_text(encoding="utf-8")
    # The matrix is an inline JSON ``include`` list; pull-request runs use a
    # subset of the cells that pushes to main run.
    cells = sorted(
        set(
            re.findall(
                r'"cubrid-version":"([0-9.]+)","pycubrid-compliance-sqlalchemy":"([0-9.]+)"', ci
            )
        )
    )
    assert cells, "ci.yml integration matrix not found"
    expected = {"cubrid@sa2.0@cubrid11.4"} | {
        f"pycubrid@sa{'.'.join(sa.split('.')[:2])}@cubrid{server}" for server, sa in cells
    }
    assert expected == _GATED_SERVER_LANES
    for _, sa in cells:
        assert _PINNED_SQLALCHEMY[f"pycubrid@sa{'.'.join(sa.split('.')[:2])}"] == sa
    assert 'pip install "sqlalchemy==2.0.53"' in ci
    assert _PINNED_SQLALCHEMY["cubrid@sa2.0"] == "2.0.53"


def _report(nodeid: str, *, skipped: bool, wasxfail: bool = False) -> SimpleNamespace:
    report = SimpleNamespace(nodeid=nodeid, skipped=skipped)
    if wasxfail:
        report.wasxfail = "known failure"
    return report


def test_skipped_known_failure_is_detected():
    known = {"test/test_suite.py::X::test_y"}
    listed = "test/test_suite.py::X_cubrid+pycubrid_11_4_6_1963::test_y"
    assert _skipped_known_failure(_report(listed, skipped=True), known) == (
        "test/test_suite.py::X::test_y"
    )
    # xfailed (strict xfail reports as skipped with wasxfail), passed, or unlisted: ignored
    assert _skipped_known_failure(_report(listed, skipped=True, wasxfail=True), known) is None
    assert _skipped_known_failure(_report(listed, skipped=False), known) is None
    unlisted = "test/test_suite.py::Other::test_z"
    assert _skipped_known_failure(_report(unlisted, skipped=True), known) is None


def test_entry_is_keyed_to_each_named_lane(tmp_path: Path):
    manifest = tmp_path / "known_failures.txt"
    manifest.write_text("test/test_suite.py::X::test_y  cubrid@sa2.0 pycubrid@sa2.1\n")
    assert _load_known_failures(manifest) == {
        "cubrid@sa2.0": {"test/test_suite.py::X::test_y"},
        "pycubrid@sa2.1": {"test/test_suite.py::X::test_y"},
    }


@pytest.mark.parametrize(
    "nodeid",
    [
        "test/test_suite.py::NumericTest_cubrid+cubrid_11_4_6_1963::test_x",
        "test/test_suite.py::NumericTest_cubrid+pycubrid_10_2_1_8849::test_x",
    ],
)
def test_server_version_suffix_is_stripped_for_both_drivers(nodeid: str):
    assert _normalize_nodeid(nodeid) == "test/test_suite.py::NumericTest::test_x"
