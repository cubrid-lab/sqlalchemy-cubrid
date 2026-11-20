"""reflection_probe.py disposes its engine on every exit path (issue #883)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "reflection_probe",
    Path(__file__).resolve().parents[1] / "scripts/reflection_probe.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
main = MODULE.main


class _FakeInspector:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def get_table_names(self) -> list[str]:
        if self.fail:
            raise RuntimeError("inspector failure")
        return ["users"]

    def get_columns(self, table_name: str) -> list[dict[str, str]]:
        return [{"name": "id"}]

    def get_pk_constraint(self, table_name: str) -> dict[str, list[str]]:
        return {"constrained_columns": ["id"]}

    def get_foreign_keys(self, table_name: str) -> list[dict[str, str]]:
        return []

    def get_indexes(self, table_name: str) -> list[dict[str, str]]:
        return []

    def get_unique_constraints(self, table_name: str) -> list[dict[str, str]]:
        return []

    def get_table_comment(self, table_name: str) -> dict[str, str]:
        return {}


class _FakeEngine:
    def __init__(self) -> None:
        self.dispose_calls = 0

    def dispose(self) -> None:
        self.dispose_calls += 1


def _run_main(monkeypatch: pytest.MonkeyPatch, argv: list[str], fail_inspect: bool = False):
    engine = _FakeEngine()
    created: dict[str, _FakeEngine] = {}

    def fake_create_engine(url: str, **kwargs):
        created["engine"] = engine
        return engine

    monkeypatch.setattr(MODULE, "create_engine", fake_create_engine)
    monkeypatch.setattr(MODULE, "inspect", lambda eng: _FakeInspector(fail=fail_inspect))
    monkeypatch.setattr(sys, "argv", ["reflection_probe.py", *argv])
    return engine, created


def test_disposes_engine_on_normal_completion(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    engine, created = _run_main(monkeypatch, ["--url", "cubrid://dba@localhost:33000/testdb"])
    main()
    assert created["engine"] is engine
    assert engine.dispose_calls == 1
    assert "Probing 1 table(s)" in capsys.readouterr().out


def test_disposes_engine_on_inspector_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    engine, _ = _run_main(
        monkeypatch, ["--url", "cubrid://dba@localhost:33000/testdb"], fail_inspect=True
    )
    with pytest.raises(RuntimeError, match="inspector failure"):
        main()
    assert engine.dispose_calls == 1


def test_disposes_engine_when_compare_finds_no_metadata(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    engine, _ = _run_main(
        monkeypatch, ["--url", "cubrid://dba@localhost:33000/testdb", "--compare", "mymod"]
    )
    monkeypatch.setattr(MODULE.importlib, "import_module", lambda name: types.SimpleNamespace())
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1
    assert engine.dispose_calls == 1
    assert "No MetaData found" in capsys.readouterr().err


def test_missing_url_exits_without_creating_engine(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("CUBRID_TEST_URL", raising=False)
    create_engine_calls: list[str] = []

    def fail_create_engine(url: str, **kwargs):
        create_engine_calls.append(url)
        raise AssertionError("create_engine must not be called for a missing URL")

    monkeypatch.setattr(MODULE, "create_engine", fail_create_engine)
    monkeypatch.setattr(sys, "argv", ["reflection_probe.py"])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1
    assert create_engine_calls == []
    assert "Set CUBRID_TEST_URL" in capsys.readouterr().err


def _fake_reflect(self: object, bind: object = None, **kwargs: object) -> None:
    """Leave MetaData.tables empty so reflection never touches a database."""


def _patch_reflection(
    monkeypatch: pytest.MonkeyPatch, module_namespace: types.SimpleNamespace
) -> None:
    monkeypatch.setattr(MODULE.importlib, "import_module", lambda name: module_namespace)
    monkeypatch.setattr(MODULE.MetaData, "reflect", _fake_reflect)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "reflection_probe.py",
            "--url",
            "cubrid://dba@localhost:33000/testdb",
            "--compare",
            "mymod",
        ],
    )


def test_compare_accepts_classes_sharing_one_metadata(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from sqlalchemy import Column, Integer
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        pass

    class User(Base):
        __tablename__ = "users"

        id = Column(Integer, primary_key=True)

    class Post(Base):
        __tablename__ = "posts"

        id = Column(Integer, primary_key=True)

    engine, _ = _run_main(
        monkeypatch,
        ["--url", "cubrid://dba@localhost:33000/testdb", "--compare", "mymod"],
    )
    _patch_reflection(
        monkeypatch,
        types.SimpleNamespace(
            Base=Base,
            User=User,
            Post=Post,
            users_metadata=User.metadata,
            posts_metadata=Post.metadata,
        ),
    )

    main()

    assert engine.dispose_calls == 1
    out = capsys.readouterr().out
    assert "users: not in database" in out
    assert "posts: not in database" in out
    assert "distinct MetaData" not in capsys.readouterr().err


def test_compare_fails_actionably_on_multiple_registries(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from sqlalchemy import Column, Integer
    from sqlalchemy.orm import DeclarativeBase

    class BaseA(DeclarativeBase):
        pass

    class UserA(BaseA):
        __tablename__ = "users"

        id = Column(Integer, primary_key=True)

    class BaseB(DeclarativeBase):
        pass

    class AuditLog(BaseB):
        __tablename__ = "audit_log"

        id = Column(Integer, primary_key=True)

    engine, _ = _run_main(
        monkeypatch,
        ["--url", "cubrid://dba@localhost:33000/testdb", "--compare", "mymod"],
    )
    _patch_reflection(
        monkeypatch,
        types.SimpleNamespace(UserA=UserA, AuditLog=AuditLog),
    )

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 1
    assert engine.dispose_calls == 1
    assert "2 distinct MetaData registries" in capsys.readouterr().err
