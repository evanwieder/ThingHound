"""User model for attribution and audit ownership."""

from pydantic import BaseModel, ConfigDict

from thinghound.types import UUIDv7


class User(BaseModel):
    """Represents an application user identity."""

    model_config = ConfigDict(frozen=True)

    id: UUIDv7
    username: str
    is_active: bool = True
