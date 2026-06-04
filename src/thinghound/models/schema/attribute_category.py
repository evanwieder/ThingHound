"""Attribute category model."""

from pydantic import BaseModel, ConfigDict

from thinghound.types import UUIDv7


class AttributeCategory(BaseModel):
    """Represents a grouping bucket for attribute definitions."""

    model_config = ConfigDict(frozen=True)

    id: UUIDv7
    name: str
    sort_order: int
    deleted_at: str | None = None
