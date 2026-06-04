"""Tests for AttributeCategoryMapper."""

from thinghound.db.connection import create_connection
from thinghound.mappers.attribute_category_mapper import AttributeCategoryMapper
from thinghound.models.schema.attribute_category import AttributeCategory
from thinghound.types import new_id


def _create_schema(connection) -> None:
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


def test_attribute_category_roundtrip() -> None:
    """Mapper should add and load an attribute category exactly."""
    connection = create_connection()
    try:
        _create_schema(connection)
        mapper = AttributeCategoryMapper()
        category = AttributeCategory(id=new_id(), name="Electrical", sort_order=1)
        mapper.add(connection, category)
        assert mapper.load(connection, category.id) == category
    finally:
        connection.close()
