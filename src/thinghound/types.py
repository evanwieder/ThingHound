"""UUIDv7 annotated type and id factory for all domain ID fields.

All primary keys in domain models use UUIDv7. The canonical string form
(``str(id)``) is used only at the bridge boundary; domain models always
hold a ``uuid.UUID`` instance typed as ``UUIDv7``.
"""

import uuid
from typing import Annotated

from pydantic import AfterValidator


def _require_v7(v: uuid.UUID) -> uuid.UUID:
    """Pydantic AfterValidator that rejects non-v7 UUIDs.

    Args:
        v: The UUID value to validate.

    Returns:
        The same UUID value when the version is 7.

    Raises:
        ValueError: If the UUID version is not 7.
    """
    if v.version != 7:
        raise ValueError(f"expected UUIDv7, got version {v.version}")
    return v


UUIDv7 = Annotated[uuid.UUID, AfterValidator(_require_v7)]
"""Annotated UUID type that enforces version 7 at Pydantic validation time."""


def new_id() -> uuid.UUID:
    """Generate a new time-ordered UUIDv7 using Python 3.14's stdlib ``uuid.uuid7()``.

    Returns:
        A freshly generated UUIDv7 value.
    """
    return uuid.uuid7()
