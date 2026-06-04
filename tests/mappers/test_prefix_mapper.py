"""Tests for PrefixMapper."""

from decimal import Decimal

from thinghound.db.connection import create_connection
from thinghound.mappers.prefix_mapper import PrefixMapper
from thinghound.models.schema.prefix import Prefix
from thinghound.types import new_id


def _create_schema(connection) -> None:
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


def test_prefix_roundtrip() -> None:
    """Mapper should add and load a prefix exactly."""
    connection = create_connection()
    try:
        _create_schema(connection)
        mapper = PrefixMapper()
        prefix = Prefix(
            id=new_id(),
            prefix_set_id=new_id(),
            symbol="k",
            name="kilo",
            factor=Decimal("1000"),
            sort_order=10,
        )
        mapper.add(connection, prefix)
        assert mapper.load(connection, prefix.id) == prefix
    finally:
        connection.close()
