"""Category model for item taxonomy."""

from pydantic import BaseModel, ConfigDict

from thinghound.types import UUIDv7


class Category(BaseModel):
    """Represents a category node in the catalog hierarchy."""

    model_config = ConfigDict(frozen=True)

    id: UUIDv7
    name: str
    parent_id: UUIDv7 | None = None
