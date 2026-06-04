"""Aggregate mapper for attribute definitions and owned rows."""

import sqlite3
import uuid

from thinghound.models.schema.attribute_allowed_prefix import AttributeAllowedPrefix
from thinghound.models.schema.attribute_component import AttributeComponent
from thinghound.models.schema.attribute_definition import AttributeDefinition
from thinghound.models.schema.attribute_enum_value import AttributeEnumValue
from thinghound.value.temporal import epoch_to_iso, iso_to_epoch


class AttributeDefinitionMapper:
    """Maps the `AttributeDefinition` compound aggregate."""

    _LIST_ACTIVE_FOR_CATEGORY = """
        -- attribute_definition: list active roots by category id
        SELECT
            ad.id
        FROM attribute_definition AS ad
        WHERE ad.attribute_category_id = ?
          AND ad.deleted_at IS NULL
        ORDER BY ad.name ASC
    """

    _LOAD_DEFINITION = """
        -- attribute_definition: load root by id
        SELECT
            ad.id,
            ad.attribute_category_id,
            ad.name,
            ad.value_type_code,
            ad.description,
            ad.unit_dimension_id,
            ad.scale,
            ad.display_unit_id,
            ad.constraints,
            ad.display_template,
            ad.deleted_at
        FROM attribute_definition AS ad
        WHERE ad.id = ?
    """

    _LOAD_ALLOWED_PREFIXES = """
        -- attribute_allowed_prefix: load owned rows by definition id
        SELECT
            aap.id,
            aap.attribute_definition_id,
            aap.prefix_id
        FROM attribute_allowed_prefix AS aap
        WHERE aap.attribute_definition_id = ?
        ORDER BY aap.id
    """

    _LOAD_ENUM_VALUES = """
        -- attribute_enum_value: load owned rows by definition id
        SELECT
            aev.id,
            aev.attribute_id,
            aev.value,
            aev.label,
            aev.sort_order,
            aev.deleted_at
        FROM attribute_enum_value AS aev
        WHERE aev.attribute_id = ?
        ORDER BY aev.sort_order, aev.id
    """

    _LOAD_COMPONENTS = """
        -- attribute_component: load owned rows by definition id
        SELECT
            ac.id,
            ac.attribute_id,
            ac.key,
            ac.label,
            ac.value_type_code,
            ac.unit_dimension_id,
            ac.scale,
            ac.display_unit_id,
            ac.sort_order,
            ac.is_required
        FROM attribute_component AS ac
        WHERE ac.attribute_id = ?
        ORDER BY ac.sort_order, ac.id
    """

    _INSERT_DEFINITION = """
        -- attribute_definition: insert root row
        INSERT INTO attribute_definition (
            id,
            attribute_category_id,
            name,
            value_type_code,
            description,
            unit_dimension_id,
            scale,
            display_unit_id,
            constraints,
            display_template,
            deleted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    _INSERT_ALLOWED_PREFIX = """
        -- attribute_allowed_prefix: insert owned row
        INSERT INTO attribute_allowed_prefix (
            id,
            attribute_definition_id,
            prefix_id
        ) VALUES (?, ?, ?)
    """

    _INSERT_ENUM_VALUE = """
        -- attribute_enum_value: insert owned row
        INSERT INTO attribute_enum_value (
            id,
            attribute_id,
            value,
            label,
            sort_order,
            deleted_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    """

    _INSERT_COMPONENT = """
        -- attribute_component: insert owned row
        INSERT INTO attribute_component (
            id,
            attribute_id,
            key,
            label,
            value_type_code,
            unit_dimension_id,
            scale,
            display_unit_id,
            sort_order,
            is_required
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    def _definition_from_row(self, row: sqlite3.Row) -> AttributeDefinition:
        return AttributeDefinition(
            id=uuid.UUID(bytes=row["id"]),
            attribute_category_id=uuid.UUID(bytes=row["attribute_category_id"]),
            name=row["name"],
            value_type_code=row["value_type_code"],
            description=row["description"],
            unit_dimension_id=(
                uuid.UUID(bytes=row["unit_dimension_id"])
                if row["unit_dimension_id"] is not None
                else None
            ),
            scale=row["scale"],
            display_unit_id=(
                uuid.UUID(bytes=row["display_unit_id"])
                if row["display_unit_id"] is not None
                else None
            ),
            constraints=row["constraints"],
            display_template=row["display_template"],
            deleted_at=epoch_to_iso(row["deleted_at"]) if row["deleted_at"] is not None else None,
        )

    def _allowed_prefix_from_row(self, row: sqlite3.Row) -> AttributeAllowedPrefix:
        return AttributeAllowedPrefix(
            id=uuid.UUID(bytes=row["id"]),
            attribute_definition_id=uuid.UUID(bytes=row["attribute_definition_id"]),
            prefix_id=uuid.UUID(bytes=row["prefix_id"]),
        )

    def _enum_value_from_row(self, row: sqlite3.Row) -> AttributeEnumValue:
        return AttributeEnumValue(
            id=uuid.UUID(bytes=row["id"]),
            attribute_id=uuid.UUID(bytes=row["attribute_id"]),
            value=row["value"],
            label=row["label"],
            sort_order=row["sort_order"],
            deleted_at=epoch_to_iso(row["deleted_at"]) if row["deleted_at"] is not None else None,
        )

    def _component_from_row(self, row: sqlite3.Row) -> AttributeComponent:
        return AttributeComponent(
            id=uuid.UUID(bytes=row["id"]),
            attribute_id=uuid.UUID(bytes=row["attribute_id"]),
            key=row["key"],
            label=row["label"],
            value_type_code=row["value_type_code"],
            unit_dimension_id=(
                uuid.UUID(bytes=row["unit_dimension_id"])
                if row["unit_dimension_id"] is not None
                else None
            ),
            scale=row["scale"],
            display_unit_id=(
                uuid.UUID(bytes=row["display_unit_id"])
                if row["display_unit_id"] is not None
                else None
            ),
            sort_order=row["sort_order"],
            is_required=bool(row["is_required"]),
        )

    def _definition_to_row(self, definition: AttributeDefinition) -> tuple:
        return (
            definition.id.bytes,
            definition.attribute_category_id.bytes,
            definition.name,
            definition.value_type_code,
            definition.description,
            (
                definition.unit_dimension_id.bytes
                if definition.unit_dimension_id is not None
                else None
            ),
            definition.scale,
            (
                definition.display_unit_id.bytes
                if definition.display_unit_id is not None
                else None
            ),
            definition.constraints,
            definition.display_template,
            iso_to_epoch(definition.deleted_at) if definition.deleted_at is not None else None,
        )

    def _allowed_prefix_to_row(
        self,
        allowed_prefix: AttributeAllowedPrefix,
    ) -> tuple[bytes, bytes, bytes]:
        return (
            allowed_prefix.id.bytes,
            allowed_prefix.attribute_definition_id.bytes,
            allowed_prefix.prefix_id.bytes,
        )

    def _enum_value_to_row(self, enum_value: AttributeEnumValue) -> tuple:
        return (
            enum_value.id.bytes,
            enum_value.attribute_id.bytes,
            enum_value.value,
            enum_value.label,
            enum_value.sort_order,
            iso_to_epoch(enum_value.deleted_at) if enum_value.deleted_at is not None else None,
        )

    def _component_to_row(self, component: AttributeComponent) -> tuple:
        return (
            component.id.bytes,
            component.attribute_id.bytes,
            component.key,
            component.label,
            component.value_type_code,
            component.unit_dimension_id.bytes if component.unit_dimension_id is not None else None,
            component.scale,
            component.display_unit_id.bytes if component.display_unit_id is not None else None,
            component.sort_order,
            1 if component.is_required else 0,
        )

    def load(self, conn: sqlite3.Connection, id_value: uuid.UUID) -> AttributeDefinition | None:
        definition_row = conn.execute(self._LOAD_DEFINITION, (id_value.bytes,)).fetchone()
        if definition_row is None:
            return None

        root = self._definition_from_row(definition_row)
        allowed_prefix_rows = conn.execute(
            self._LOAD_ALLOWED_PREFIXES,
            (id_value.bytes,),
        ).fetchall()
        enum_value_rows = conn.execute(self._LOAD_ENUM_VALUES, (id_value.bytes,)).fetchall()
        component_rows = conn.execute(self._LOAD_COMPONENTS, (id_value.bytes,)).fetchall()

        return root.model_copy(
            update={
                "allowed_prefixes": tuple(
                    self._allowed_prefix_from_row(row) for row in allowed_prefix_rows
                ),
                "enum_values": tuple(self._enum_value_from_row(row) for row in enum_value_rows),
                "components": tuple(self._component_from_row(row) for row in component_rows),
            }
        )

    def list_active_for_category(
        self,
        conn: sqlite3.Connection,
        attribute_category_id: uuid.UUID,
    ) -> list[AttributeDefinition]:
        rows = conn.execute(
            self._LIST_ACTIVE_FOR_CATEGORY,
            (attribute_category_id.bytes,),
        ).fetchall()
        return [
            loaded
            for row in rows
            if (loaded := self.load(conn, uuid.UUID(bytes=row["id"]))) is not None
        ]

    def add(self, conn: sqlite3.Connection, definition: AttributeDefinition) -> None:
        conn.execute(self._INSERT_DEFINITION, self._definition_to_row(definition))
        conn.executemany(
            self._INSERT_ALLOWED_PREFIX,
            [self._allowed_prefix_to_row(row) for row in definition.allowed_prefixes],
        )
        conn.executemany(
            self._INSERT_ENUM_VALUE,
            [self._enum_value_to_row(row) for row in definition.enum_values],
        )
        conn.executemany(
            self._INSERT_COMPONENT,
            [self._component_to_row(row) for row in definition.components],
        )
