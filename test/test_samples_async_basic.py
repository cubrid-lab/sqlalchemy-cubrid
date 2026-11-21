"""Offline tests for samples/async_basic.py: the engine is always disposed."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "async_basic.py"


def _load_sample():
    spec = importlib.util.spec_from_file_location("async_basic_sample", SAMPLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Result:
    def scalar(self):
        return 1

    def __iter__(self):
        return iter(())


class _Conn:
    def __init__(self, engine):
        self._engine = engine

    async def execute(self, statement, *args):
        sql = str(statement)
        self._engine.statements.append(sql)
        if self._engine.fail_on:
            needle, occurrence = self._engine.fail_on
            if needle in sql and sum(needle in s for s in self._engine.statements) == occurrence:
                raise RuntimeError("injected failure")
        return _Result()

    async def run_sync(self, fn):
        return None


class _Context:
    def __init__(self, engine):
        self._engine = engine

    async def __aenter__(self):
        return _Conn(self._engine)

    async def __aexit__(self, *exc):
        return False


class FakeEngine:
    """Async engine stand in that records statements and dispose() calls."""

    def __init__(self, fail_on=None):
        self.fail_on = fail_on
        self.statements = []
        self.dispose_calls = 0

    def connect(self):
        return _Context(self)

    def begin(self):
        return _Context(self)

    async def dispose(self):
        self.dispose_calls += 1


def _run(monkeypatch, engine):
    sample = _load_sample()
    monkeypatch.setattr(sample, "create_async_engine", lambda *a, **k: engine)
    asyncio.run(sample.main())


def test_engine_disposed_once_after_success(monkeypatch):
    engine = FakeEngine()
    _run(monkeypatch, engine)
    assert engine.dispose_calls == 1
    assert any("INSERT" in s for s in engine.statements)


@pytest.mark.parametrize(
    "fail_on",
    [("SELECT 1", 1), ("INSERT", 1), ("DROP TABLE", 2)],
    ids=["connect", "insert", "cleanup"],
)
def test_engine_disposed_once_when_a_step_fails(monkeypatch, fail_on):
    engine = FakeEngine(fail_on=fail_on)
    with pytest.raises(RuntimeError, match="injected failure"):
        _run(monkeypatch, engine)
    assert engine.dispose_calls == 1
