"""Prefix model."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from thinghound.types import UUIDv7


class Prefix(BaseModel):
    """Represents one prefix within a prefix set."""

    model_config = ConfigDict(frozen=True)

    id: UUIDv7
    prefix_set_id: UUIDv7
    symbol: str
    name: str
    factor: Decimal
    sort_order: int
