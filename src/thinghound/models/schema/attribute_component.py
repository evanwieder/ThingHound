"""Attribute component model."""

from pydantic import BaseModel, ConfigDict

from thinghound.types import UUIDv7


class AttributeComponent(BaseModel):
    """Represents one component row owned by a composite attribute definition."""

    model_config = ConfigDict(frozen=True)

    id: UUIDv7
    attribute_id: UUIDv7
    key: str
    label: str | None = None
    value_type_code: str
    unit_dimension_id: UUIDv7 | None = None
    scale: int
    display_unit_id: UUIDv7 | None = None
    sort_order: int
    is_required: bool
