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

from pathlib import Path

import pytest

from test.conftest import _KNOWN_FAILURES_FILE, _load_known_failures, _normalize_nodeid

# Lanes gated in .github/workflows/ci.yml; each must have a reviewed baseline.
_GATED_LANES = {"cubrid@sa2.0", "pycubrid@sa2.0", "pycubrid@sa2.1"}


def test_manifest_lanes_match_the_gated_ci_lanes():
    lanes = _load_known_failures(_KNOWN_FAILURES_FILE)
    assert set(lanes) == _GATED_LANES
    assert all(lanes.values())


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
