"""Tests for PrefixSetMapper."""

from thinghound.db.connection import create_connection
from thinghound.mappers.prefix_set_mapper import PrefixSetMapper
from thinghound.models.schema.prefix_set import PrefixSet
from thinghound.types import new_id


def _create_schema(connection) -> None:
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


def test_prefix_set_roundtrip() -> None:
    """Mapper should add and load a prefix set exactly."""
    connection = create_connection()
    try:
        _create_schema(connection)
        mapper = PrefixSetMapper()
        prefix_set = PrefixSet(id=new_id(), name="SI", description="metric prefixes")
        mapper.add(connection, prefix_set)
        assert mapper.load(connection, prefix_set.id) == prefix_set
    finally:
        connection.close()
