"""Typed aliases and factories used by ThingHound domain models."""

import uuid
from typing import Annotated

from pydantic import AfterValidator


def _require_v7(value: uuid.UUID) -> uuid.UUID:
    """Validate UUID version 7 values.

    Args:
        value: UUID value to validate.

    Returns:
        The same UUID value when valid.

    Raises:
        ValueError: If UUID version is not 7.
    """
    if value.version != 7:
        raise ValueError("Expected UUID version 7")
    return value


UUIDv7 = Annotated[uuid.UUID, AfterValidator(_require_v7)]


def new_id() -> uuid.UUID:
    """Create a new UUIDv7 value.

    Returns:
        Newly generated UUIDv7.
    """
    return uuid.uuid7()
