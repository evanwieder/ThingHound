"""Tests for session and app registry scaffolding."""

from decimal import Decimal

import pytest

from thinghound.db.connection import create_connection
from thinghound.mappers.attribute_category_mapper import AttributeCategoryMapper
from thinghound.mappers.attribute_definition_mapper import AttributeDefinitionMapper
from thinghound.mappers.prefix_mapper import PrefixMapper
from thinghound.mappers.prefix_set_mapper import PrefixSetMapper
from thinghound.mappers.unit_dimension_mapper import UnitDimensionMapper
from thinghound.mappers.unit_multiplier_mapper import UnitMultiplierMapper
from thinghound.models.schema.attribute_category import AttributeCategory
from thinghound.models.schema.attribute_definition import AttributeDefinition
from thinghound.models.schema.prefix import Prefix
from thinghound.models.schema.prefix_set import PrefixSet
from thinghound.models.schema.unit_dimension import UnitDimension
from thinghound.models.schema.unit_multiplier import UnitMultiplier
from thinghound.registry import AppRegistry, RegistryNotLoadedError
from thinghound.session import Session
from thinghound.types import new_id


def test_session_identity_map_roundtrip() -> None:
    """Session should cache/retrieve objects by type and id."""
    session = Session(create_connection())
    marker = object()
    session.put_identity(str, "k1", marker)
    assert session.get_identity(str, "k1") is marker


def test_registry_get_requires_load() -> None:
    """Registry should reject reads before load."""
    registry = AppRegistry()
    with pytest.raises(RegistryNotLoadedError):
        registry.get("x")


def _create_registry_schema(connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS unit_dimension (
            id BLOB PRIMARY KEY,
            name TEXT NOT NULL DEFAULT '',
            base_unit TEXT NOT NULL DEFAULT '',
            deleted_at INTEGER DEFAULT NULL,
            created_by_user_id BLOB DEFAULT NULL,
            updated_by_user_id BLOB DEFAULT NULL
        ) WITHOUT ROWID;
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS unit_multiplier (
            id BLOB PRIMARY KEY,
            dimension_id BLOB NOT NULL DEFAULT X'00000000000000000000000000000000',
            name TEXT NOT NULL DEFAULT '',
            alt_names TEXT DEFAULT NULL,
            symbol TEXT NOT NULL DEFAULT '',
            plural TEXT DEFAULT NULL,
            alt_plurals TEXT DEFAULT NULL,
            factor_scaled INTEGER NOT NULL DEFAULT 0,
            factor_exact TEXT NOT NULL DEFAULT '0',
            is_si_generated INTEGER NOT NULL DEFAULT 0,
            deleted_at INTEGER DEFAULT NULL
        ) WITHOUT ROWID;
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS prefix_set (
            id BLOB PRIMARY KEY,
            name TEXT NOT NULL DEFAULT '',
            description TEXT DEFAULT NULL,
            deleted_at INTEGER DEFAULT NULL
        ) WITHOUT ROWID;
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS prefix (
            id BLOB PRIMARY KEY,
            prefix_set_id BLOB NOT NULL DEFAULT X'00000000000000000000000000000000',
            symbol TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL DEFAULT '',
            factor_scaled INTEGER NOT NULL DEFAULT 0,
            factor_exact TEXT NOT NULL DEFAULT '0',
            sort_order INTEGER NOT NULL DEFAULT 0
        ) WITHOUT ROWID;
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS attribute_category (
            id BLOB PRIMARY KEY,
            name TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            deleted_at INTEGER DEFAULT NULL
        ) WITHOUT ROWID;
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS attribute_definition (
            id BLOB PRIMARY KEY,
            attribute_category_id BLOB NOT NULL DEFAULT X'00000000000000000000000000000000',
            name TEXT NOT NULL DEFAULT '',
            value_type_code TEXT NOT NULL DEFAULT '',
            description TEXT DEFAULT NULL,
            unit_dimension_id BLOB DEFAULT NULL,
            scale INTEGER NOT NULL DEFAULT 0,
            display_unit_id BLOB DEFAULT NULL,
            constraints TEXT DEFAULT NULL,
            display_template TEXT DEFAULT NULL,
            deleted_at INTEGER DEFAULT NULL
        ) WITHOUT ROWID;
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS attribute_allowed_prefix (
            id BLOB PRIMARY KEY,
            attribute_definition_id BLOB NOT NULL DEFAULT X'00000000000000000000000000000000',
            prefix_id BLOB NOT NULL DEFAULT X'00000000000000000000000000000000'
        ) WITHOUT ROWID;
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS attribute_enum_value (
            id BLOB PRIMARY KEY,
            attribute_id BLOB NOT NULL DEFAULT X'00000000000000000000000000000000',
            value TEXT NOT NULL DEFAULT '',
            label TEXT DEFAULT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            deleted_at INTEGER DEFAULT NULL
        ) WITHOUT ROWID;
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS attribute_component (
            id BLOB PRIMARY KEY,
            attribute_id BLOB NOT NULL DEFAULT X'00000000000000000000000000000000',
            key TEXT NOT NULL DEFAULT '',
            label TEXT DEFAULT NULL,
            value_type_code TEXT NOT NULL DEFAULT '',
            unit_dimension_id BLOB DEFAULT NULL,
            scale INTEGER NOT NULL DEFAULT 0,
            display_unit_id BLOB DEFAULT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_required INTEGER NOT NULL DEFAULT 0
        ) WITHOUT ROWID;
        """
    )


def test_registry_load_then_get() -> None:
    """Registry should return values after load."""
    registry = AppRegistry()
    registry.load({"x": 42})
    assert registry.is_loaded is True
    assert registry.get("x") == 42


def test_registry_loads_from_session_and_builds_factors_map() -> None:
    """Session-backed load should populate factor map with exact fractions."""
    connection = create_connection()
    try:
        _create_registry_schema(connection)
        session = Session(connection)

        dimension = UnitDimension(id=new_id(), name="Resistance", base_unit="ohm")
        UnitDimensionMapper().add(connection, dimension)

        multiplier = UnitMultiplier(
            id=new_id(),
            dimension_id=dimension.id,
            name="Kiloohm",
            symbol="kΩ",
            factor=Decimal("1000"),
            is_si_generated=True,
        )
        UnitMultiplierMapper().add(connection, multiplier)

        prefix_set = PrefixSet(id=new_id(), name="SI", description=None)
        PrefixSetMapper().add(connection, prefix_set)
        PrefixMapper().add(
            connection,
            Prefix(
                id=new_id(),
                prefix_set_id=prefix_set.id,
                symbol="k",
                name="kilo",
                factor=Decimal("1000"),
                sort_order=1,
            ),
        )

        category = AttributeCategory(id=new_id(), name="Electrical", sort_order=1)
        AttributeCategoryMapper().add(connection, category)
        AttributeDefinitionMapper().add(
            connection,
            AttributeDefinition(
                id=new_id(),
                attribute_category_id=category.id,
                name="Tolerance",
                value_type_code="N",
                scale=2,
            ),
        )

        registry = AppRegistry()
        registry.load(session)

        factors = registry.factors_for(dimension.id)
        assert factors[multiplier.id].numerator == 1000
        assert factors[multiplier.id].denominator == 1
    finally:
        connection.close()
