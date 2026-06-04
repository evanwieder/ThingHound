"""Aggregate mapper for prefixes."""

import sqlite3
import uuid
from decimal import Decimal

from thinghound.models.schema.prefix import Prefix


class PrefixMapper:
    """Maps the `prefix` aggregate."""

    _LIST_BY_PREFIX_SET = """
        -- prefix: list rows by prefix_set_id
        SELECT
            p.id,
            p.prefix_set_id,
            p.symbol,
            p.name,
            p.factor_scaled,
            p.factor_exact,
            p.sort_order
        FROM prefix AS p
        WHERE p.prefix_set_id = ?
        ORDER BY p.sort_order ASC, p.name ASC
    """

    _LOAD = """
        -- prefix: load by id
        SELECT
            p.id,
            p.prefix_set_id,
            p.symbol,
            p.name,
            p.factor_scaled,
            p.factor_exact,
            p.sort_order
        FROM prefix AS p
        WHERE p.id = ?
    """

    _INSERT = """
        -- prefix: insert row
        INSERT INTO prefix (
            id,
            prefix_set_id,
            symbol,
            name,
            factor_scaled,
            factor_exact,
            sort_order
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    def _from_row(self, row: sqlite3.Row) -> Prefix:
        return Prefix(
            id=uuid.UUID(bytes=row["id"]),
            prefix_set_id=uuid.UUID(bytes=row["prefix_set_id"]),
            symbol=row["symbol"],
            name=row["name"],
            factor=Decimal(row["factor_exact"]),
            sort_order=row["sort_order"],
        )

    def _to_row(self, prefix: Prefix) -> tuple[bytes, bytes, str, str, int, str, int]:
        return (
            prefix.id.bytes,
            prefix.prefix_set_id.bytes,
            prefix.symbol,
            prefix.name,
            0,
            format(prefix.factor, "f"),
            prefix.sort_order,
        )

    def load(self, conn: sqlite3.Connection, id_value: uuid.UUID) -> Prefix | None:
        row = conn.execute(self._LOAD, (id_value.bytes,)).fetchone()
        return self._from_row(row) if row is not None else None

    def list_for_prefix_set(
        self,
        conn: sqlite3.Connection,
        prefix_set_id: uuid.UUID,
    ) -> list[Prefix]:
        rows = conn.execute(self._LIST_BY_PREFIX_SET, (prefix_set_id.bytes,)).fetchall()
        return [self._from_row(row) for row in rows]

    def add(self, conn: sqlite3.Connection, prefix: Prefix) -> None:
        conn.execute(self._INSERT, self._to_row(prefix))

    def add_batch(self, conn: sqlite3.Connection, prefixes: list[Prefix]) -> None:
        conn.executemany(self._INSERT, [self._to_row(prefix) for prefix in prefixes])
