"""Unit dimension model."""

from pydantic import BaseModel, ConfigDict

from thinghound.types import UUIDv7


class UnitDimension(BaseModel):
    """Represents one measurable unit dimension."""

    model_config = ConfigDict(frozen=True)

    id: UUIDv7
    name: str
    base_unit: str
    deleted_at: str | None = None
    created_by_user_id: UUIDv7 | None = None
    updated_by_user_id: UUIDv7 | None = None
