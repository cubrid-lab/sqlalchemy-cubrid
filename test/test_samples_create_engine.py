"""Offline tests for samples/create_engine.py: import safety and cleanup."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "create_engine.py"


def _load_sample():
    spec = importlib.util.spec_from_file_location("create_engine_sample", SAMPLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Conn:
    def __init__(self, engine):
        self._engine = engine

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, statement):
        self._engine.statements.append(str(statement))
        if self._engine.fail:
            raise RuntimeError("injected failure")
        return [(2,)]


class FakeEngine:
    """Engine stand in that records connect() and dispose() calls."""

    def __init__(self, fail=False):
        self.fail = fail
        self.statements = []
        self.dispose_calls = 0

    def connect(self):
        return _Conn(self)

    def dispose(self):
        self.dispose_calls += 1


def test_import_does_not_create_an_engine(monkeypatch):
    calls = []
    monkeypatch.setattr("sqlalchemy.create_engine", lambda *a, **k: calls.append(a))
    sample = _load_sample()
    assert calls == []
    assert callable(sample.main)


def test_main_runs_query_and_disposes_once(monkeypatch, capsys):
    engine = FakeEngine()
    sample = _load_sample()
    monkeypatch.setattr(sample, "create_engine", lambda *a, **k: engine)
    sample.main()
    assert engine.statements == ["SELECT 1 + 1 AS answer"]
    assert engine.dispose_calls == 1
    assert "(2,)" in capsys.readouterr().out


def test_main_disposes_once_when_the_query_fails(monkeypatch):
    engine = FakeEngine(fail=True)
    sample = _load_sample()
    monkeypatch.setattr(sample, "create_engine", lambda *a, **k: engine)
    with pytest.raises(RuntimeError, match="injected failure"):
        sample.main()
    assert engine.dispose_calls == 1
