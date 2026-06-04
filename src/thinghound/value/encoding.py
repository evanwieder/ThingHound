"""Exact numeric encoding/decoding helpers for scaled integer storage."""

from decimal import Decimal, InvalidOperation

from thinghound.errors import ScaleOverflowError

MAX_I64 = (1 << 63) - 1
MIN_I64 = -(1 << 63)


def encode_scaled(value: Decimal, scale: int) -> tuple[int, str]:
    """Encode a Decimal to scaled integer and exact string.

    Args:
        value: Decimal value to encode.
        scale: Number of decimal places for scaling.

    Returns:
        Tuple of `(value_scaled, value_exact)`.

    Raises:
        ScaleOverflowError: If scaled integer exceeds int64 bounds.
        ValueError: If scale is negative.
    """
    if scale < 0:
        raise ValueError("scale must be >= 0")

    scaled_decimal = value * (Decimal(10) ** scale)
    scaled_int = int(scaled_decimal.to_integral_exact())
    if scaled_int > MAX_I64 or scaled_int < MIN_I64:
        raise ScaleOverflowError("Scaled value exceeds int64 bounds")
    return scaled_int, format(value, "f")


def decode_scaled(value_scaled: int, value_exact: str | None, scale: int) -> Decimal:
    """Decode scaled representation to Decimal.

    Args:
        value_scaled: Stored scaled integer.
        value_exact: Optional exact-string payload.
        scale: Number of decimal places used for scaling.

    Returns:
        Decoded Decimal value.
    """
    if value_exact is not None:
        try:
            return Decimal(value_exact)
        except InvalidOperation:
            pass
    return Decimal(value_scaled) / (Decimal(10) ** scale)
