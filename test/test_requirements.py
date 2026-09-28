from __future__ import annotations

import pytest

from sqlalchemy_cubrid import requirements as requirements_module
from sqlalchemy_cubrid.requirements import Requirements


def _is_open(requirement):
    return requirement.enabled_for_config(None)


@pytest.fixture
def requirements():
    return Requirements()


class TestRequirements:
    @pytest.mark.parametrize(
        "property_name",
        [
            "returning",
            "insert_returning",
            "update_returning",
            "delete_returning",
        ],
    )
    def test_returning_group_is_closed(self, requirements, property_name):
        assert not _is_open(getattr(requirements, property_name))

    @pytest.mark.parametrize(
        "property_name",
        ["nullable_booleans", "non_native_boolean_unconstrained"],
    )
    def test_boolean_group_is_open(self, requirements, property_name):
        assert _is_open(getattr(requirements, property_name))

    @pytest.mark.parametrize("property_name", ["sequences", "sequences_optional"])
    def test_sequences_group_is_closed(self, requirements, property_name):
        assert not _is_open(getattr(requirements, property_name))

    @pytest.mark.parametrize(
        "property_name, expected_open",
        [
            ("schemas", False),
            ("temp_table_names", False),
            ("temporary_tables", False),
            ("temporary_views", False),
            ("table_ddl_if_exists", True),
            ("comment_reflection", True),
            ("check_constraint_reflection", False),
        ],
    )
    def test_schema_group_states(self, requirements, property_name, expected_open):
        assert _is_open(getattr(requirements, property_name)) is expected_open

    @pytest.mark.parametrize(
        "property_name, expected_open",
        [
            ("empty_inserts", True),
            ("insert_from_select", True),
            ("ctes", True),
            ("ctes_on_dml", False),
        ],
    )
    def test_dml_group_states(self, requirements, property_name, expected_open):
        assert _is_open(getattr(requirements, property_name)) is expected_open

    @pytest.mark.parametrize(
        "property_name, expected_open",
        [
            ("window_functions", True),
            ("intersect", True),
            ("except_", True),
            ("fetch_no_order", False),
            ("order_by_col_from_union", True),
        ],
    )
    def test_select_group_states(self, requirements, property_name, expected_open):
        assert _is_open(getattr(requirements, property_name)) is expected_open

    @pytest.mark.parametrize(
        "property_name, expected_open",
        [
            ("datetime_literals", False),
            ("date", True),
            ("time", True),
            ("datetime", True),
            ("timestamp", True),
            ("precision_generic_float_type", False),
            ("text_type", True),
            ("json_type", True),
            ("array_type", False),
            ("uuid_data_type", False),
        ],
    )
    def test_type_group_states(self, requirements, property_name, expected_open):
        assert _is_open(getattr(requirements, property_name)) is expected_open

    @pytest.mark.parametrize(
        "property_name, expected_open",
        [
            ("views", True),
            ("savepoints", True),
            ("foreign_keys", True),
            ("self_referential_foreign_keys", True),
            ("unique_constraint_reflection", True),
            ("foreign_key_constraint_reflection", True),
            ("index_reflection", True),
            ("primary_key_constraint_reflection", True),
            ("on_update_cascade", True),
            ("on_delete_cascade", True),
            ("server_side_cursors", False),
            ("independent_connections", True),
        ],
    )
    def test_misc_group_states(self, requirements, property_name, expected_open):
        assert _is_open(getattr(requirements, property_name)) is expected_open

    @pytest.mark.parametrize(
        "property_name",
        [
            "binary_comparisons",
            "binary_literals",
            "unusual_column_name_characters",
            "update_nowait",
            "two_phase_transactions",
        ],
    )
    def test_unsupported_features_are_closed(self, requirements, property_name):
        assert not _is_open(getattr(requirements, property_name))

    def test_for_update_is_open(self, requirements):
        assert _is_open(requirements.for_update)


_OWN_PROPERTIES = sorted(
    name for name, value in vars(Requirements).items() if isinstance(value, property)
)


@pytest.mark.parametrize("property_name", _OWN_PROPERTIES)
def test_stacked_requirements_do_not_leak_into_other_properties(requirements, property_name):
    """Stacked @requires decorators extend the first compound in place, so each
    property must return a fresh one or other requirements change too (#463)."""

    def fn():
        pass

    before = getattr(requirements, property_name)
    assert before is not getattr(requirements, property_name)
    skips, fails = len(before.skips), len(before.fails)
    requirements.sequences(getattr(requirements, property_name)(fn))
    after = getattr(requirements, property_name)
    assert (len(after.skips), len(after.fails)) == (skips, fails)


def test_stacking_keeps_open_requirements_open(requirements):
    def fn():
        pass

    requirements.sequences(requirements.views(fn))
    assert _is_open(requirements.views)
    assert _is_open(requirements.ctes)


@pytest.mark.parametrize("charset, expected_open", [("utf8", True), ("iso88591", False)])
def test_unicode_ddl_requires_a_utf8_database(requirements, monkeypatch, charset, expected_open):
    from unittest.mock import MagicMock

    # The probe is cached per URL; isolate the cache and use a stable URL
    # (a MagicMock's default str() embeds id(), which can be reused).
    monkeypatch.setattr(requirements_module, "_UTF8_BY_URL", {})
    config = MagicMock()
    config.db.url = f"cubrid+pycubrid://dba@localhost:33000/{charset}"
    conn = config.db.connect.return_value.__enter__.return_value
    conn.exec_driver_sql.return_value.scalar.return_value = charset
    assert requirements.unicode_ddl.enabled_for_config(config) is expected_open
    # probed once per database URL
    assert requirements.unicode_ddl.enabled_for_config(config) is expected_open
    assert conn.exec_driver_sql.call_count == 1


def test_unicode_ddl_skips_when_the_charset_probe_fails(requirements, monkeypatch):
    from unittest.mock import MagicMock

    monkeypatch.setattr(requirements_module, "_UTF8_BY_URL", {})
    config = MagicMock()
    config.db.url = "cubrid+pycubrid://dba@localhost:33000/unreachable"
    config.db.connect.side_effect = RuntimeError("server unreachable")
    assert requirements.unicode_ddl.enabled_for_config(config) is False


@pytest.mark.parametrize("property_name", ["implicitly_named_constraints", "reflects_pk_names"])
def test_constraint_naming_is_open(requirements, property_name):
    assert _is_open(getattr(requirements, property_name))
