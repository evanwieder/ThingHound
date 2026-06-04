"""Read-only query object for category schema resolution."""

import sqlite3
import uuid

from thinghound.models.read_model.attribute_schema import AttributeSchema


class SchemaResolutionQuery:
    """Resolves effective attributes for a category via recursive ancestry."""

    _RESOLVE = """
        -- category_attribute/attribute_definition: resolve effective schema by category ancestry
        WITH RECURSIVE lineage(category_id, parent_id, depth) AS (
            SELECT
                c.id,
                c.parent_id,
                0
            FROM category AS c
            WHERE c.id = ?
            UNION ALL
            SELECT
                p.id,
                p.parent_id,
                lineage.depth + 1
            FROM category AS p
            INNER JOIN lineage
                ON p.id = lineage.parent_id
        ),
        ranked AS (
            SELECT
                ca.category_id,
                ca.attribute_id,
                ca.is_override,
                lineage.depth,
                ROW_NUMBER() OVER (
                    PARTITION BY ca.attribute_id
                    ORDER BY lineage.depth ASC, ca.is_override DESC
                ) AS rn
            FROM category_attribute AS ca
            INNER JOIN lineage
                ON ca.category_id = lineage.category_id
        )
        SELECT
            ranked.category_id,
            ad.id AS attribute_id,
            ad.name AS attribute_name,
            ad.value_type_code,
            ad.scale,
            ranked.is_override
        FROM ranked
        INNER JOIN attribute_definition AS ad
            ON ad.id = ranked.attribute_id
        WHERE ranked.rn = 1
          AND ad.deleted_at IS NULL
        ORDER BY ad.name ASC
    """

    def resolve(self, conn: sqlite3.Connection, category_id: uuid.UUID) -> list[AttributeSchema]:
        """Resolve the effective attribute schema rows for one category."""
        rows = conn.execute(self._RESOLVE, (category_id.bytes,)).fetchall()
        return [
            AttributeSchema(
                category_id=uuid.UUID(bytes=row["category_id"]),
                attribute_id=uuid.UUID(bytes=row["attribute_id"]),
                attribute_name=row["attribute_name"],
                value_type_code=row["value_type_code"],
                scale=row["scale"],
                is_override=bool(row["is_override"]),
            )
            for row in rows
        ]
