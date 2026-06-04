"""Tests for UnitMultiplierMapper."""

from decimal import Decimal

from thinghound.db.connection import create_connection
from thinghound.mappers.unit_multiplier_mapper import UnitMultiplierMapper
from thinghound.models.schema.unit_dimension import UnitDimension
from thinghound.models.schema.unit_multiplier import UnitMultiplier
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
        CREATE TABLE IF NOT EXISTS unit_multiplier (
            id BLOB PRIMARY KEY,
            dimension_id BLOB NOT NULL DEFAULT X'',
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


def test_unit_multiplier_roundtrip() -> None:
    """Mapper should roundtrip multiplier rows exactly."""
    connection = create_connection()
    try:
        _create_schema(connection)
        dimension = UnitDimension(id=new_id(), name="Resistance", base_unit="ohm")
        connection.execute(
            "INSERT INTO unit_dimension (id, name, base_unit) VALUES (?, ?, ?)",
            (dimension.id.bytes, dimension.name, dimension.base_unit),
        )

        mapper = UnitMultiplierMapper()
        multiplier = UnitMultiplier(
            id=new_id(),
            dimension_id=dimension.id,
            name="kiloohm",
            symbol="kΩ",
            factor=Decimal("1000"),
            is_si_generated=True,
        )
        mapper.add(connection, multiplier)
        assert mapper.load(connection, multiplier.id) == multiplier
    finally:
        connection.close()
