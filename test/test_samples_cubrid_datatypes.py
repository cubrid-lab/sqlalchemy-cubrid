"""Offline tests for samples/cubrid_datatypes.py: import safety and cleanup."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import MetaData

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "cubrid_datatypes.py"


def _load_sample():
    spec = importlib.util.spec_from_file_location("cubrid_datatypes_sample", SAMPLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeEngine:
    """Engine stand-in that records dispose() calls."""

    def __init__(self):
        self.dispose_calls = 0

    def dispose(self):
        self.dispose_calls += 1


def test_import_does_not_create_engine_or_tables(monkeypatch):
    engine_calls = []
    ddl_calls = []

    monkeypatch.setattr(
        "sqlalchemy.create_engine",
        lambda *a, **k: engine_calls.append(a),
    )
    monkeypatch.setattr(
        MetaData,
        "create_all",
        lambda *a, **k: ddl_calls.append(a),
    )

    sample = _load_sample()

    assert engine_calls == []
    assert ddl_calls == []
    assert callable(sample.main)
    assert sample.users.name == "users"
    assert sample.products.name == "products"


def test_main_creates_tables_and_disposes_engine(monkeypatch):
    engine = FakeEngine()
    create_all_calls = []

    sample = _load_sample()
    monkeypatch.setattr(
        sample,
        "create_engine",
        lambda *a, **k: engine,
    )
    monkeypatch.setattr(
        sample.metadata,
        "create_all",
        lambda passed_engine: create_all_calls.append(passed_engine),
    )

    sample.main()

    assert create_all_calls == [engine]
    assert engine.dispose_calls == 1


def test_main_disposes_engine_when_table_creation_fails(monkeypatch):
    engine = FakeEngine()
    sample = _load_sample()

    monkeypatch.setattr(
        sample,
        "create_engine",
        lambda *a, **k: engine,
    )

    def fail_create_all(passed_engine):
        raise RuntimeError("injected failure")

    monkeypatch.setattr(sample.metadata, "create_all", fail_create_all)

    with pytest.raises(RuntimeError, match="injected failure"):
        sample.main()

    assert engine.dispose_calls == 1
