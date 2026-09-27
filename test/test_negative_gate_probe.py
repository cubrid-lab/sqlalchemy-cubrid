"""Intentional runtime failure on a never-merged CI validation branch."""

from __future__ import annotations


def test_intentional_required_gate_failure() -> None:
    raise AssertionError("this temporary negative-validation PR must never merge")
