"""Tests for UUIDv7 typing helpers."""

import uuid

import pytest
from pydantic import BaseModel

from thinghound.types import UUIDv7, new_id


class _Model(BaseModel):
    """Simple test model for UUIDv7 validation."""

    id: UUIDv7


def test_new_id_returns_uuid_v7() -> None:
    """new_id should return a version-7 UUID."""
    value = new_id()
    assert isinstance(value, uuid.UUID)
    assert value.version == 7


def test_uuidv7_annotation_rejects_non_v7() -> None:
    """UUIDv7 annotation should reject UUID values with a different version."""
    with pytest.raises(ValueError):
        _Model(id=uuid.uuid4())
