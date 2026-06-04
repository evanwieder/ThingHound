"""Attribute enum value model."""

from pydantic import BaseModel, ConfigDict

from thinghound.types import UUIDv7


class AttributeEnumValue(BaseModel):
    """Represents one enum member for an enum attribute definition."""

    model_config = ConfigDict(frozen=True)

    id: UUIDv7
    attribute_id: UUIDv7
    value: str
    label: str | None = None
    sort_order: int
    deleted_at: str | None = None
