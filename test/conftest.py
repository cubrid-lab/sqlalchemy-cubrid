"""conftest.py — test configuration for sqlalchemy-cubrid.

The SA testing plugin (pytestplugin) is only loaded when running the full
SA test suite against a live CUBRID instance via ``--dburi``.  Offline tests
(test_dialects, test_compiler, test_types) work without it.
"""

import sys

# Only load the heavy SA testing plugin when a DB URI is provided.
# This allows offline tests to run without CUBRIDdb installed.
if "--dburi" in sys.argv or any(a.startswith("--dburi=") for a in sys.argv):
    from sqlalchemy.dialects import registry

    registry.register("cubrid", "sqlalchemy_cubrid.pycubrid_dialect", "PyCubridDialect")
    registry.register("cubrid.cubrid", "sqlalchemy_cubrid.dialect", "CubridDialect")
    registry.register("cubrid.cubriddb", "sqlalchemy_cubrid.dialect", "CubridDialect")
    registry.register("cubrid.pycubrid", "sqlalchemy_cubrid.pycubrid_dialect", "PyCubridDialect")

    import pytest

    pytest.register_assert_rewrite("sqlalchemy.testing.assertions")

    from sqlalchemy.testing.plugin.pytestplugin import *  # noqa: E402, F401, F403
