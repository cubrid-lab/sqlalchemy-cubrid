# test/test_suite.py
# SA built-in dialect test suite — requires a live CUBRID instance.
import pytest

from sqlalchemy.testing.suite import *  # noqa: E402, F401, F403

from sqlalchemy.testing.suite import BooleanTest as _BooleanTest

pytestmark = pytest.mark.integration


class BooleanTest(_BooleanTest):
    @pytest.mark.skip(reason="CUBRID maps BOOLEAN to SMALLINT; no native bool.")
    def test_round_trip(self):
        pass
