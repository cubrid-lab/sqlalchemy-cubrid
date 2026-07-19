from __future__ import annotations

import pytest

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
            ("unicode_ddl", True),
            ("datetime_literals", False),
            ("date", True),
            ("time", True),
            ("datetime", True),
            ("timestamp", True),
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
            "implicitly_named_constraints",
            "update_nowait",
            "two_phase_transactions",
        ],
    )
    def test_unsupported_features_are_closed(self, requirements, property_name):
        assert not _is_open(getattr(requirements, property_name))

    def test_for_update_is_open(self, requirements):
        assert _is_open(requirements.for_update)
