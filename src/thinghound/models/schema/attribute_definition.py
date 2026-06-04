"""Attribute definition aggregate root model."""

from pydantic import BaseModel, ConfigDict

from thinghound.models.schema.attribute_allowed_prefix import AttributeAllowedPrefix
from thinghound.models.schema.attribute_component import AttributeComponent
from thinghound.models.schema.attribute_enum_value import AttributeEnumValue
from thinghound.types import UUIDv7


class AttributeDefinition(BaseModel):
    """Represents one attribute definition and its owned rows."""

    model_config = ConfigDict(frozen=True)

    id: UUIDv7
    attribute_category_id: UUIDv7
    name: str
    value_type_code: str
    description: str | None = None
    unit_dimension_id: UUIDv7 | None = None
    scale: int
    display_unit_id: UUIDv7 | None = None
    constraints: str | None = None
    display_template: str | None = None
    deleted_at: str | None = None
    allowed_prefixes: tuple[AttributeAllowedPrefix, ...] = ()
    enum_values: tuple[AttributeEnumValue, ...] = ()
    components: tuple[AttributeComponent, ...] = ()
