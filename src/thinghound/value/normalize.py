"""Unit normalization helpers for scaled values."""

from decimal import Decimal

from thinghound.errors import UnknownUnitError

UNIT_FACTORS: dict[str, Decimal] = {
    "": Decimal("1"),
    "ohm": Decimal("1"),
    "kohm": Decimal("1000"),
    "mohm": Decimal("1000000"),
    "v": Decimal("1"),
    "mv": Decimal("0.001"),
    "a": Decimal("1"),
    "ma": Decimal("0.001"),
    "f": Decimal("1"),
    "uf": Decimal("0.000001"),
    "nh": Decimal("0.000000001"),
}


def normalize_unit(symbol: str | None) -> str:
    """Normalize unit symbol to lowercase canonical form.

    Args:
        symbol: Unit symbol from input.

    Returns:
        Canonical lowercase symbol.

    Raises:
        UnknownUnitError: If symbol is unknown.
    """
    normalized = (symbol or "").strip().lower()
    if normalized not in UNIT_FACTORS:
        raise UnknownUnitError(f"Unknown unit: {symbol}")
    return normalized


def unit_factor(symbol: str | None) -> Decimal:
    """Get decimal factor for canonical unit symbol.

    Args:
        symbol: Unit symbol from input.

    Returns:
        Decimal factor to base unit.
    """
    return UNIT_FACTORS[normalize_unit(symbol)]
