"""Aggregate mapper for prefix sets."""

import sqlite3
import uuid

from thinghound.models.schema.prefix_set import PrefixSet
from thinghound.value.temporal import epoch_to_iso, iso_to_epoch


class PrefixSetMapper:
    """Maps the `prefix_set` aggregate."""

    _LIST_ACTIVE = """
        -- prefix_set: list active rows
        SELECT
            ps.id,
            ps.name,
            ps.description,
            ps.deleted_at
        FROM prefix_set AS ps
        WHERE ps.deleted_at IS NULL
        ORDER BY ps.name ASC
    """

    _LOAD = """
        -- prefix_set: load by id
        SELECT
            ps.id,
            ps.name,
            ps.description,
            ps.deleted_at
        FROM prefix_set AS ps
        WHERE ps.id = ?
    """

    _INSERT = """
        -- prefix_set: insert row
        INSERT INTO prefix_set (
            id,
            name,
            description,
            deleted_at
        ) VALUES (?, ?, ?, ?)
    """

    def _from_row(self, row: sqlite3.Row) -> PrefixSet:
        return PrefixSet(
            id=uuid.UUID(bytes=row["id"]),
            name=row["name"],
            description=row["description"],
            deleted_at=epoch_to_iso(row["deleted_at"]) if row["deleted_at"] is not None else None,
        )

    def _to_row(self, prefix_set: PrefixSet) -> tuple[bytes, str, str | None, int | None]:
        return (
            prefix_set.id.bytes,
            prefix_set.name,
            prefix_set.description,
            iso_to_epoch(prefix_set.deleted_at) if prefix_set.deleted_at is not None else None,
        )

    def load(self, conn: sqlite3.Connection, id_value: uuid.UUID) -> PrefixSet | None:
        row = conn.execute(self._LOAD, (id_value.bytes,)).fetchone()
        return self._from_row(row) if row is not None else None

    def list_active(self, conn: sqlite3.Connection) -> list[PrefixSet]:
        return [self._from_row(row) for row in conn.execute(self._LIST_ACTIVE)]

    def add(self, conn: sqlite3.Connection, prefix_set: PrefixSet) -> None:
        conn.execute(self._INSERT, self._to_row(prefix_set))

    def add_batch(self, conn: sqlite3.Connection, prefix_sets: list[PrefixSet]) -> None:
        conn.executemany(self._INSERT, [self._to_row(prefix_set) for prefix_set in prefix_sets])
