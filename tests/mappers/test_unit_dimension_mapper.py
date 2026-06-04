"""Tests for UnitDimensionMapper."""

from thinghound.db.connection import create_connection
from thinghound.mappers.unit_dimension_mapper import UnitDimensionMapper
from thinghound.models.schema.unit_dimension import UnitDimension
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


def test_unit_dimension_roundtrip() -> None:
    """Mapper should add and load a unit dimension exactly."""
    connection = create_connection()
    try:
        _create_schema(connection)
        mapper = UnitDimensionMapper()
        dimension = UnitDimension(id=new_id(), name="Resistance", base_unit="ohm")
        mapper.add(connection, dimension)
        assert mapper.load(connection, dimension.id) == dimension
    finally:
        connection.close()


def test_list_active_excludes_soft_deleted() -> None:
    """Active-list should exclude soft-deleted rows."""
    connection = create_connection()
    try:
        _create_schema(connection)
        mapper = UnitDimensionMapper()
        active = UnitDimension(id=new_id(), name="Mass", base_unit="gram")
        deleted = UnitDimension(
            id=new_id(),
            name="Legacy",
            base_unit="unit",
            deleted_at="2026-01-01T00:00:00.000Z",
        )
        mapper.add_batch(connection, [active, deleted])
        assert [row.id for row in mapper.list_active(connection)] == [active.id]
    finally:
        connection.close()
