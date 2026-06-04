"""Attribute allowed prefix model."""

from pydantic import BaseModel, ConfigDict

from thinghound.types import UUIDv7


class AttributeAllowedPrefix(BaseModel):
    """Represents one prefix allowed for numeric entry on an attribute."""

    model_config = ConfigDict(frozen=True)

    id: UUIDv7
    attribute_definition_id: UUIDv7
    prefix_id: UUIDv7
