"""UUIDv7 annotated type and id factory. Canonical string form only at the bridge boundary."""

import uuid
from typing import Annotated

from pydantic import AfterValidator


def _require_v7(v: uuid.UUID) -> uuid.UUID:
    if v.version != 7:
        raise ValueError(f"expected UUIDv7, got version {v.version}")
    return v


UUIDv7 = Annotated[uuid.UUID, AfterValidator(_require_v7)]


def new_id() -> uuid.UUID:
    """New time-ordered UUIDv7 via Python 3.14 stdlib uuid.uuid7()."""
    return uuid.uuid7()
