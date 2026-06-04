"""Aggregate mapper for attribute categories."""

import sqlite3
import uuid

from thinghound.models.schema.attribute_category import AttributeCategory
from thinghound.value.temporal import epoch_to_iso, iso_to_epoch


class AttributeCategoryMapper:
    """Maps the `attribute_category` aggregate."""

    _LIST_ACTIVE = """
        -- attribute_category: list active rows
        SELECT
            ac.id,
            ac.name,
            ac.sort_order,
            ac.deleted_at
        FROM attribute_category AS ac
        WHERE ac.deleted_at IS NULL
        ORDER BY ac.sort_order ASC, ac.name ASC
    """

    _LOAD = """
        -- attribute_category: load by id
        SELECT
            ac.id,
            ac.name,
            ac.sort_order,
            ac.deleted_at
        FROM attribute_category AS ac
        WHERE ac.id = ?
    """

    _INSERT = """
        -- attribute_category: insert row
        INSERT INTO attribute_category (
            id,
            name,
            sort_order,
            deleted_at
        ) VALUES (?, ?, ?, ?)
    """

    def _from_row(self, row: sqlite3.Row) -> AttributeCategory:
        return AttributeCategory(
            id=uuid.UUID(bytes=row["id"]),
            name=row["name"],
            sort_order=row["sort_order"],
            deleted_at=epoch_to_iso(row["deleted_at"]) if row["deleted_at"] is not None else None,
        )

    def _to_row(self, category: AttributeCategory) -> tuple[bytes, str, int, int | None]:
        return (
            category.id.bytes,
            category.name,
            category.sort_order,
            iso_to_epoch(category.deleted_at) if category.deleted_at is not None else None,
        )

    def load(self, conn: sqlite3.Connection, id_value: uuid.UUID) -> AttributeCategory | None:
        row = conn.execute(self._LOAD, (id_value.bytes,)).fetchone()
        return self._from_row(row) if row is not None else None

    def list_active(self, conn: sqlite3.Connection) -> list[AttributeCategory]:
        return [self._from_row(row) for row in conn.execute(self._LIST_ACTIVE)]

    def add(self, conn: sqlite3.Connection, category: AttributeCategory) -> None:
        conn.execute(self._INSERT, self._to_row(category))

    def add_batch(self, conn: sqlite3.Connection, categories: list[AttributeCategory]) -> None:
        conn.executemany(self._INSERT, [self._to_row(category) for category in categories])
