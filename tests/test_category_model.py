"""Tests for Category model."""

import uuid

import pytest

from thinghound.models.category import Category
from thinghound.types import new_id


def test_category_accepts_uuidv7() -> None:
    """Category should accept UUIDv7 identifiers."""
    category = Category(id=new_id(), name="Resistors")
    assert category.parent_id is None


def test_category_rejects_non_v7_parent_id() -> None:
    """Category should reject non-v7 UUID parent IDs."""
    with pytest.raises(ValueError):
        Category(id=new_id(), name="Resistors", parent_id=uuid.uuid4())
