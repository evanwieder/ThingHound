"""Tests for scaled value and encoding helpers."""

from decimal import Decimal

import pytest

from thinghound.errors import ScaleOverflowError
from thinghound.value.scaled_value import ScaledValue
from thinghound.value.encoding import decode_scaled, encode_scaled


def test_encode_decode_scaled_roundtrip() -> None:
    """Encoding then decoding should preserve the decimal value."""
    value_scaled, value_exact = encode_scaled(Decimal("123.456"), scale=3)
    decoded = decode_scaled(value_scaled=value_scaled, value_exact=value_exact, scale=3)
    assert value_scaled == 123456
    assert decoded == Decimal("123.456")


def test_encode_scaled_overflow() -> None:
    """Encoding should fail when scaled value exceeds signed int64 bounds."""
    with pytest.raises(ScaleOverflowError):
        encode_scaled(Decimal("9223372036854775808"), scale=0)


def test_scaled_value_from_decimal() -> None:
    """ScaledValue should provide a stable decimal roundtrip API."""
    value = ScaledValue.from_decimal(Decimal("1.2345"), scale=4, display_unit="ohm")
    assert value.value_scaled == 12345
    assert value.value_exact == "1.2345"
    assert value.to_decimal() == Decimal("1.2345")
