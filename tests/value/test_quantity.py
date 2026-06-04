"""Tests for fixed-scale quantity helpers."""

from decimal import Decimal

import pytest

from thinghound.errors import ScaleOverflowError
from thinghound.value.quantity import QUANTITY_SCALE, decode_quantity, encode_quantity


def test_encode_decode_quantity_roundtrip() -> None:
    """Quantity helpers should preserve exact value at scale 6."""
    scaled, exact = encode_quantity(Decimal("123.456789"))
    decoded = decode_quantity(scaled)
    assert QUANTITY_SCALE == 6
    assert exact == "123.456789"
    assert decoded == Decimal("123.456789")


def test_encode_quantity_overflow_raises() -> None:
    """Overflowing scaled quantity should raise typed overflow error."""
    with pytest.raises(ScaleOverflowError):
        encode_quantity(Decimal("9223372036854.775808"))
