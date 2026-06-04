"""Aggregate mapper for unit dimensions."""

import sqlite3
import uuid

from thinghound.models.schema.unit_dimension import UnitDimension
from thinghound.value.temporal import epoch_to_iso, iso_to_epoch


class UnitDimensionMapper:
    """Maps the `unit_dimension` aggregate."""

    _LOAD = """
        -- unit_dimension: load by id
        SELECT
            ud.id,
            ud.name,
            ud.base_unit,
            ud.deleted_at,
            ud.created_by_user_id,
            ud.updated_by_user_id
        FROM unit_dimension AS ud
        WHERE ud.id = ?
    """

    _LIST_ACTIVE = """
        -- unit_dimension: list active rows
        SELECT
            ud.id,
            ud.name,
            ud.base_unit,
            ud.deleted_at,
            ud.created_by_user_id,
            ud.updated_by_user_id
        FROM unit_dimension AS ud
        WHERE ud.deleted_at IS NULL
        ORDER BY ud.name ASC
    """

    _INSERT = """
        -- unit_dimension: insert new row
        INSERT INTO unit_dimension (
            id,
            name,
            base_unit,
            deleted_at,
            created_by_user_id,
            updated_by_user_id
        ) VALUES (?, ?, ?, ?, ?, ?)
    """

    def _from_row(self, row: sqlite3.Row) -> UnitDimension:
        """Convert one database row to model."""
        return UnitDimension(
            id=uuid.UUID(bytes=row["id"]),
            name=row["name"],
            base_unit=row["base_unit"],
            deleted_at=epoch_to_iso(row["deleted_at"]) if row["deleted_at"] is not None else None,
            created_by_user_id=(
                uuid.UUID(bytes=row["created_by_user_id"])
                if row["created_by_user_id"] is not None
                else None
            ),
            updated_by_user_id=(
                uuid.UUID(bytes=row["updated_by_user_id"])
                if row["updated_by_user_id"] is not None
                else None
            ),
        )

    def _to_row(
        self,
        dimension: UnitDimension,
    ) -> tuple[bytes, str, str, int | None, bytes | None, bytes | None]:
        """Convert one model instance to row tuple."""
        return (
            dimension.id.bytes,
            dimension.name,
            dimension.base_unit,
            iso_to_epoch(dimension.deleted_at) if dimension.deleted_at is not None else None,
            (
                dimension.created_by_user_id.bytes
                if dimension.created_by_user_id is not None
                else None
            ),
            (
                dimension.updated_by_user_id.bytes
                if dimension.updated_by_user_id is not None
                else None
            ),
        )

    def load(self, conn: sqlite3.Connection, id_value: uuid.UUID) -> UnitDimension | None:
        """Load one model by id."""
        row = conn.execute(self._LOAD, (id_value.bytes,)).fetchone()
        return self._from_row(row) if row is not None else None

    def list_active(self, conn: sqlite3.Connection) -> list[UnitDimension]:
        """List non-deleted rows."""
        return [self._from_row(row) for row in conn.execute(self._LIST_ACTIVE)]

    def add(self, conn: sqlite3.Connection, dimension: UnitDimension) -> None:
        """Insert one model row."""
        conn.execute(self._INSERT, self._to_row(dimension))

    def add_batch(self, conn: sqlite3.Connection, dimensions: list[UnitDimension]) -> None:
        """Insert many model rows."""
        conn.executemany(self._INSERT, [self._to_row(dimension) for dimension in dimensions])
