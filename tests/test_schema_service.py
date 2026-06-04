"""Tests for schema resolution query and schema service wiring."""

from thinghound.db.connection import create_connection
from thinghound.mappers.attribute_category_mapper import AttributeCategoryMapper
from thinghound.mappers.attribute_definition_mapper import AttributeDefinitionMapper
from thinghound.mappers.unit_dimension_mapper import UnitDimensionMapper
from thinghound.models.schema.attribute_category import AttributeCategory
from thinghound.models.schema.attribute_definition import AttributeDefinition
from thinghound.models.schema.unit_dimension import UnitDimension
from thinghound.queries.schema_resolution_query import SchemaResolutionQuery
from thinghound.services.schema_service import DuplicateAttributeNameError, SchemaService
from thinghound.session import Session
from thinghound.types import new_id


def _create_schema(connection) -> None:
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
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS category (
            id BLOB PRIMARY KEY,
            name TEXT NOT NULL DEFAULT '',
            parent_id BLOB DEFAULT NULL
        ) WITHOUT ROWID;
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS category_attribute (
            id BLOB PRIMARY KEY,
            category_id BLOB NOT NULL DEFAULT X'00000000000000000000000000000000',
            attribute_id BLOB NOT NULL DEFAULT X'00000000000000000000000000000000',
            is_override INTEGER NOT NULL DEFAULT 0
        ) WITHOUT ROWID;
        """
    )


def test_schema_service_lists_active_dimensions_and_categories() -> None:
    """Service should expose active dimensions and attribute categories."""
    connection = create_connection()
    try:
        _create_schema(connection)
        session = Session(connection)

        dim_mapper = UnitDimensionMapper()
        cat_mapper = AttributeCategoryMapper()
        def_mapper = AttributeDefinitionMapper()
        service = SchemaService(dim_mapper, cat_mapper, def_mapper, SchemaResolutionQuery())

        dim_mapper.add(connection, UnitDimension(id=new_id(), name="Resistance", base_unit="ohm"))
        dim_mapper.add(
            connection,
            UnitDimension(
                id=new_id(),
                name="Legacy",
                base_unit="legacy",
                deleted_at="2026-01-01T00:00:00.000Z",
            ),
        )
        cat_mapper.add(connection, AttributeCategory(id=new_id(), name="Electrical", sort_order=1))

        assert [d.name for d in service.get_dimensions(session)] == ["Resistance"]
        assert [c.name for c in service.get_attribute_categories(session)] == ["Electrical"]
    finally:
        connection.close()


def test_schema_service_enforces_unique_name_within_category() -> None:
    """Service should reject duplicate attribute names in one category."""
    connection = create_connection()
    try:
        _create_schema(connection)
        session = Session(connection)

        category_id = new_id()
        definition = AttributeDefinition(
            id=new_id(),
            attribute_category_id=category_id,
            name="Tolerance",
            value_type_code="N",
            scale=2,
        )

        mapper = AttributeDefinitionMapper()
        mapper.add(connection, definition)

        service = SchemaService(
            UnitDimensionMapper(),
            AttributeCategoryMapper(),
            mapper,
            SchemaResolutionQuery(),
        )

        try:
            service.assert_unique_name_within_category(
                session=session,
                attribute_category_id=category_id,
                name="tolerance",
            )
        except DuplicateAttributeNameError:
            pass
        else:
            raise AssertionError("Expected DuplicateAttributeNameError")
    finally:
        connection.close()


def test_schema_resolution_query_prefers_child_override() -> None:
    """Resolved schema should choose the closest category override."""
    connection = create_connection()
    try:
        _create_schema(connection)
        parent_id = new_id()
        child_id = new_id()
        attribute_id = new_id()
        category_group_id = new_id()

        connection.execute(
            "INSERT INTO category (id, name, parent_id) VALUES (?, ?, ?)",
            (parent_id.bytes, "Parent", None),
        )
        connection.execute(
            "INSERT INTO category (id, name, parent_id) VALUES (?, ?, ?)",
            (child_id.bytes, "Child", parent_id.bytes),
        )

        definition_mapper = AttributeDefinitionMapper()
        definition_mapper.add(
            connection,
            AttributeDefinition(
                id=attribute_id,
                attribute_category_id=category_group_id,
                name="Tolerance",
                value_type_code="N",
                scale=3,
            ),
        )

        insert_category_attribute = (
            "INSERT INTO category_attribute "
            "(id, category_id, attribute_id, is_override) VALUES (?, ?, ?, ?)"
        )
        connection.execute(
            insert_category_attribute,
            (new_id().bytes, parent_id.bytes, attribute_id.bytes, 0),
        )
        connection.execute(
            insert_category_attribute,
            (new_id().bytes, child_id.bytes, attribute_id.bytes, 1),
        )

        resolved = SchemaResolutionQuery().resolve(connection, child_id)
        assert len(resolved) == 1
        assert resolved[0].category_id == child_id
        assert resolved[0].is_override is True
    finally:
        connection.close()
