"""Tests for User model."""

import uuid

import pytest

from thinghound.models.user import User
from thinghound.types import new_id


def test_user_accepts_uuidv7() -> None:
    """User should accept UUIDv7 IDs."""
    user = User(id=new_id(), username="evan")
    assert user.is_active is True


def test_user_rejects_non_v7_uuid() -> None:
    """User should reject non-v7 UUID values."""
    with pytest.raises(ValueError):
        User(id=uuid.uuid4(), username="evan")
