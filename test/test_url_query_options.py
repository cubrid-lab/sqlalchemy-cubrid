"""URL query options are forwarded to pycubrid.connect() (#592)."""

from __future__ import annotations

import asyncio
import types
import warnings
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine, exc
from sqlalchemy.engine import url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.util.concurrency import greenlet_spawn

from sqlalchemy_cubrid.aio_pycubrid_dialect import (
    AsyncAdapt_pycubrid_dbapi,
    PyCubridAsyncDialect,
)
from sqlalchemy_cubrid.dialect import CubridDialect
from sqlalchemy_cubrid.pycubrid_dialect import PyCubridDialect, _query_connect_options

INSTALLED = "sqlalchemy_cubrid.pycubrid_dialect._installed_pycubrid"


class FakeUnknownOptionWarning(UserWarning):
    pass


def _connect_with_charset(host: str = "", charset: str = "utf-8", **kwargs: Any) -> None:
    pass


def _connect_without_charset(host: str = "", **kwargs: Any) -> None:
    pass


def _fake_pycubrid(*, charset: bool, version: str = "9.9.9") -> Any:
    """A stand-in ``pycubrid`` whose ``connect()`` names ``charset`` or not."""
    module: Any = types.ModuleType("pycubrid")
    module.connect = _connect_with_charset if charset else _connect_without_charset
    module.__version__ = version
    module.UnknownConnectionOptionWarning = FakeUnknownOptionWarning
    return module


def _options(query: str, *, charset: bool = True) -> dict[str, Any]:
    with patch(INSTALLED, return_value=_fake_pycubrid(charset=charset)):
        return _query_connect_options(url.make_url(f"cubrid+pycubrid://dba@h/db?{query}").query)


class TestForwardedToDriverConnect:
    """Failing-first regressions: the option reaches the driver's connect() call."""

    def test_sync_charset_reaches_pycubrid_connect(self):
        dbapi = MagicMock()
        with patch(INSTALLED, return_value=_fake_pycubrid(charset=True)):
            engine = create_engine("cubrid+pycubrid://dba@h/db?charset=utf8", module=dbapi)
            cargs, cparams = engine.dialect.create_connect_args(engine.url)
        engine.dialect.connect(*cargs, **cparams)

        assert dbapi.connect.call_args.kwargs["charset"] == "utf8"

    def test_async_charset_reaches_pycubrid_aio_connect(self):
        fake_aio = MagicMock()
        fake_aio.connect = AsyncMock(return_value=MagicMock())
        with patch.dict("sys.modules", {"pycubrid": MagicMock()}):
            dbapi = AsyncAdapt_pycubrid_dbapi(fake_aio)
        with patch(INSTALLED, return_value=_fake_pycubrid(charset=True)):
            engine = create_async_engine("cubrid+aiopycubrid://dba@h/db?charset=utf8", module=dbapi)
            dialect = engine.sync_engine.dialect
            cargs, cparams = dialect.create_connect_args(engine.sync_engine.url)

        asyncio.run(greenlet_spawn(dialect.connect, *cargs, **cparams))

        assert fake_aio.connect.call_args.kwargs["charset"] == "utf8"

    @pytest.mark.parametrize(
        "dialect_cls, scheme",
        [(PyCubridDialect, "cubrid+pycubrid"), (PyCubridAsyncDialect, "cubrid+aiopycubrid")],
    )
    def test_connect_timeout_forwarded_by_both_dialects(self, dialect_cls: Any, scheme: str):
        with patch(INSTALLED, return_value=_fake_pycubrid(charset=False)):
            _, kwargs = dialect_cls().create_connect_args(
                url.make_url(f"{scheme}://dba:pw@h:33001/db?connect_timeout=5")
            )
        assert kwargs == {
            "host": "h",
            "port": 33001,
            "database": "db",
            "user": "dba",
            "password": "pw",
            "connect_timeout": 5.0,
        }


class TestTypeCoercion:
    def test_every_option_converted_to_pycubrid_type(self):
        options = _options(
            "charset=euckr&connect_timeout=5&read_timeout=2.5&fetch_size=50&ssl=true"
            "&decode_collections=yes&no_backslash_escapes=0&enable_timing=off"
        )
        assert options == {
            "charset": "euckr",
            "connect_timeout": 5.0,
            "read_timeout": 2.5,
            "fetch_size": 50,
            "ssl": True,
            "decode_collections": True,
            "no_backslash_escapes": False,
            "enable_timing": False,
        }
        assert type(options["fetch_size"]) is int

    def test_empty_query_adds_nothing(self):
        assert _query_connect_options({}) == {}

    @pytest.mark.parametrize(
        "query",
        [
            "connect_timeout=abc",
            "connect_timeout=0",
            "read_timeout=-1",
            "connect_timeout=inf",
            "connect_timeout=nan",
            "fetch_size=1.5",
            "fetch_size=0",
            "fetch_size=-5",
            "ssl=maybe",
        ],
    )
    def test_invalid_value_raises(self, query: str):
        name, value = query.split("=")
        with pytest.raises(exc.ArgumentError, match=f"Invalid value '{value}'.*'{name}'"):
            _options(query)

    def test_repeated_key_raises(self):
        with pytest.raises(exc.ArgumentError, match="'connect_timeout' is given more than once"):
            _options("connect_timeout=5&connect_timeout=6")


class TestRejectedAndUnknownKeys:
    @pytest.mark.parametrize(
        "name", ["host", "port", "database", "user", "password", "autocommit", "json_deserializer"]
    )
    def test_option_not_settable_from_url_raises(self, name: str):
        with pytest.raises(exc.ArgumentError, match=f"URL query option '{name}' is not supported"):
            _options(f"{name}=x")

    def test_unknown_key_warns_with_pycubrid_category_and_is_dropped(self):
        with pytest.warns(FakeUnknownOptionWarning) as record:
            options = _options("conect_timeout=5&read_timeout=1")
        assert options == {"read_timeout": 1.0}
        message = str(record[0].message)
        assert "'conect_timeout' (did you mean 'connect_timeout'?)" in message
        assert "Supported URL query options: charset, connect_timeout" in message

    def test_unknown_keys_listed_together_without_suggestion(self):
        with pytest.warns(FakeUnknownOptionWarning, match="options ignored.*'bar', 'foo'\\."):
            _options("foo=1&bar=2")

    def test_unknown_key_warns_userwarning_without_pycubrid(self):
        with patch(INSTALLED, return_value=None):
            with pytest.warns(UserWarning, match="'zzz'"):
                _query_connect_options({"zzz": "1"})

    def test_unknown_key_warning_can_be_made_an_error(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", FakeUnknownOptionWarning)
            with pytest.raises(FakeUnknownOptionWarning):
                _options("typo=1")


class TestOptionUnsupportedByInstalledDriver:
    def test_charset_on_pycubrid_without_it_raises_clear_error(self):
        with patch(INSTALLED, return_value=_fake_pycubrid(charset=False, version="1.8.0")):
            with pytest.raises(
                exc.ArgumentError,
                match=r"'charset' requires a pycubrid release that supports it "
                r"\(cubrid-lab/pycubrid#510\); the installed pycubrid 1\.8\.0 does not",
            ):
                _query_connect_options({"charset": "euckr"})

    def test_floor_options_do_not_need_a_newer_driver(self):
        assert _options("connect_timeout=5", charset=False) == {"connect_timeout": 5.0}

    def test_without_pycubrid_the_driver_check_is_skipped(self):
        with patch(INSTALLED, return_value=None):
            assert _query_connect_options({"charset": "euckr"}) == {"charset": "euckr"}

    def test_installed_pycubrid_helper(self):
        from sqlalchemy_cubrid.pycubrid_dialect import _installed_pycubrid

        with patch(
            "sqlalchemy_cubrid.pycubrid_dialect.import_module", side_effect=ImportError("nope")
        ):
            assert _installed_pycubrid() is None
        sentinel = object()
        with patch("sqlalchemy_cubrid.pycubrid_dialect.import_module", return_value=sentinel):
            assert _installed_pycubrid() is sentinel


def test_cubriddb_dialect_behavior_unchanged():
    """``cubrid://`` still builds the CUBRIDdb URL and does not read the query."""
    args, kwargs = CubridDialect().create_connect_args(
        url.make_url("cubrid://dba:pw@h:33001/db?connect_timeout=5")
    )
    assert args == ("CUBRID:h:33001:db:::", "dba", "pw")
    assert kwargs == {}
