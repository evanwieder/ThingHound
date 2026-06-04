"""Scaled value object for exact domain quantities."""

from dataclasses import dataclass
from decimal import Decimal

from thinghound.value_codec import decode_scaled, encode_scaled


@dataclass(frozen=True)
class ScaledValue:
    """Stores exact values in dual representation used by persistence layer.

    Args:
        value_scaled: Integer scaled by `scale`.
        value_exact: Exact decimal string representation.
        scale: Decimal precision.
        value_raw: Optional raw user-entered value.
        display_unit: Optional normalized display unit.
    """

    value_scaled: int
    value_exact: str
    scale: int
    value_raw: str | None = None
    display_unit: str | None = None

    @classmethod
    def from_decimal(
        cls,
        value: Decimal,
        scale: int,
        value_raw: str | None = None,
        display_unit: str | None = None,
    ) -> "ScaledValue":
        """Create a scaled value from Decimal.

        Args:
            value: Decimal value.
            scale: Decimal precision.
            value_raw: Optional raw string.
            display_unit: Optional display unit.

        Returns:
            ScaledValue instance.
        """
        value_scaled, value_exact = encode_scaled(value=value, scale=scale)
        return cls(
            value_scaled=value_scaled,
            value_exact=value_exact,
            scale=scale,
            value_raw=value_raw,
            display_unit=display_unit,
        )

    def to_decimal(self) -> Decimal:
        """Decode to Decimal.

        Returns:
            Decimal value.
        """
        return decode_scaled(
            value_scaled=self.value_scaled,
            value_exact=self.value_exact,
            scale=self.scale,
        )
