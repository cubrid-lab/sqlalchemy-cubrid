"""Intentional type failure on a never-merged CI validation branch."""

from __future__ import annotations


def intentional_bad_return() -> int:
    return "this draft probe must fail strict mypy"
