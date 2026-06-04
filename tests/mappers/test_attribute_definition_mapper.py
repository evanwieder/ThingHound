"""Tests for AttributeDefinitionMapper."""

from thinghound.db.connection import create_connection
from thinghound.mappers.attribute_definition_mapper import AttributeDefinitionMapper
from thinghound.models.schema.attribute_allowed_prefix import AttributeAllowedPrefix
from thinghound.models.schema.attribute_component import AttributeComponent
from thinghound.models.schema.attribute_definition import AttributeDefinition
from thinghound.models.schema.attribute_enum_value import AttributeEnumValue
from thinghound.types import new_id


def _create_schema(connection) -> None:
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


def test_attribute_definition_roundtrip_with_owned_rows() -> None:
    """Mapper should round-trip the root and all owned rows exactly."""
    connection = create_connection()
    try:
        _create_schema(connection)
        mapper = AttributeDefinitionMapper()

        definition_id = new_id()
        definition = AttributeDefinition(
            id=definition_id,
            attribute_category_id=new_id(),
            name="Resistance tolerance",
            value_type_code="E",
            scale=2,
            enum_values=(
                AttributeEnumValue(
                    id=new_id(),
                    attribute_id=definition_id,
                    value="1pct",
                    label="±1%",
                    sort_order=1,
                ),
            ),
            components=(
                AttributeComponent(
                    id=new_id(),
                    attribute_id=definition_id,
                    key="min",
                    label="Minimum",
                    value_type_code="N",
                    scale=2,
                    sort_order=1,
                    is_required=True,
                ),
            ),
            allowed_prefixes=(
                AttributeAllowedPrefix(
                    id=new_id(),
                    attribute_definition_id=definition_id,
                    prefix_id=new_id(),
                ),
            ),
        )

        mapper.add(connection, definition)
        loaded = mapper.load(connection, definition.id)

        assert loaded is not None
        assert loaded.id == definition.id
        assert loaded.name == definition.name
        assert len(loaded.allowed_prefixes) == 1
        assert len(loaded.enum_values) == 1
        assert len(loaded.components) == 1
    finally:
        connection.close()
