"""Fixed-scale quantity encoding helpers."""

from decimal import Decimal

from thinghound.value.encoding import decode_scaled, encode_scaled

QUANTITY_SCALE = 6


def encode_quantity(value: Decimal) -> tuple[int, str]:
    """Encode a quantity decimal to scaled integer and exact text.

    Args:
        value: Quantity decimal value.

    Returns:
        Tuple of `(scaled, exact)` at fixed scale 6.
    """
    return encode_scaled(value=value, scale=QUANTITY_SCALE)


def decode_quantity(scaled: int) -> Decimal:
    """Decode fixed-scale quantity integer to decimal.

    Args:
        scaled: Quantity integer stored at scale 6.

    Returns:
        Decoded decimal quantity.
    """
    return decode_scaled(value_scaled=scaled, value_exact=None, scale=QUANTITY_SCALE)
