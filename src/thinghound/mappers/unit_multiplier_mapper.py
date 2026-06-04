"""Aggregate mapper for unit multipliers."""

import sqlite3
import uuid
from decimal import Decimal

from thinghound.models.schema.unit_multiplier import UnitMultiplier
from thinghound.value.temporal import epoch_to_iso, iso_to_epoch


class UnitMultiplierMapper:
    """Maps the `unit_multiplier` aggregate."""

    _LIST_ACTIVE = """
        -- unit_multiplier: list active rows
        SELECT
            um.id,
            um.dimension_id,
            um.name,
            um.alt_names,
            um.symbol,
            um.plural,
            um.alt_plurals,
            um.factor_scaled,
            um.factor_exact,
            um.is_si_generated,
            um.deleted_at
        FROM unit_multiplier AS um
        WHERE um.deleted_at IS NULL
        ORDER BY um.name ASC
    """

    _LOAD = """
        -- unit_multiplier: load by id
        SELECT
            um.id,
            um.dimension_id,
            um.name,
            um.alt_names,
            um.symbol,
            um.plural,
            um.alt_plurals,
            um.factor_scaled,
            um.factor_exact,
            um.is_si_generated,
            um.deleted_at
        FROM unit_multiplier AS um
        WHERE um.id = ?
    """

    _INSERT = """
        -- unit_multiplier: insert row
        INSERT INTO unit_multiplier (
            id,
            dimension_id,
            name,
            alt_names,
            symbol,
            plural,
            alt_plurals,
            factor_scaled,
            factor_exact,
            is_si_generated,
            deleted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    def _from_row(self, row: sqlite3.Row) -> UnitMultiplier:
        return UnitMultiplier(
            id=uuid.UUID(bytes=row["id"]),
            dimension_id=uuid.UUID(bytes=row["dimension_id"]),
            name=row["name"],
            alt_names=row["alt_names"],
            symbol=row["symbol"],
            plural=row["plural"],
            alt_plurals=row["alt_plurals"],
            factor=Decimal(row["factor_exact"]),
            is_si_generated=bool(row["is_si_generated"]),
            deleted_at=epoch_to_iso(row["deleted_at"]) if row["deleted_at"] is not None else None,
        )

    def _to_row(self, multiplier: UnitMultiplier) -> tuple:
        factor_exact = format(multiplier.factor, "f")
        return (
            multiplier.id.bytes,
            multiplier.dimension_id.bytes,
            multiplier.name,
            multiplier.alt_names,
            multiplier.symbol,
            multiplier.plural,
            multiplier.alt_plurals,
            0,
            factor_exact,
            1 if multiplier.is_si_generated else 0,
            iso_to_epoch(multiplier.deleted_at) if multiplier.deleted_at is not None else None,
        )

    def load(self, conn: sqlite3.Connection, id_value: uuid.UUID) -> UnitMultiplier | None:
        row = conn.execute(self._LOAD, (id_value.bytes,)).fetchone()
        return self._from_row(row) if row is not None else None

    def list_active(self, conn: sqlite3.Connection) -> list[UnitMultiplier]:
        return [self._from_row(row) for row in conn.execute(self._LIST_ACTIVE)]

    def add(self, conn: sqlite3.Connection, multiplier: UnitMultiplier) -> None:
        conn.execute(self._INSERT, self._to_row(multiplier))

    def add_batch(self, conn: sqlite3.Connection, multipliers: list[UnitMultiplier]) -> None:
        conn.executemany(self._INSERT, [self._to_row(multiplier) for multiplier in multipliers])
