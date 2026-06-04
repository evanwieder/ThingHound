"""Read model for resolved category attribute schema."""

from pydantic import BaseModel, ConfigDict

from thinghound.types import UUIDv7


class AttributeSchema(BaseModel):
    """Represents one resolved attribute visible for a category."""

    model_config = ConfigDict(frozen=True)

    category_id: UUIDv7
    attribute_id: UUIDv7
    attribute_name: str
    value_type_code: str
    scale: int
    is_override: bool = False
