"""Prefix set model."""

from pydantic import BaseModel, ConfigDict

from thinghound.types import UUIDv7


class PrefixSet(BaseModel):
    """Represents a named collection of prefixes."""

    model_config = ConfigDict(frozen=True)

    id: UUIDv7
    name: str
    description: str | None = None
    deleted_at: str | None = None
