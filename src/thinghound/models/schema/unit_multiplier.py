"""Unit multiplier model."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from thinghound.types import UUIDv7


class UnitMultiplier(BaseModel):
    """Represents a named unit multiplier inside a dimension."""

    model_config = ConfigDict(frozen=True)

    id: UUIDv7
    dimension_id: UUIDv7
    name: str
    alt_names: str | None = None
    symbol: str
    plural: str | None = None
    alt_plurals: str | None = None
    factor: Decimal
    is_si_generated: bool
    deleted_at: str | None = None
