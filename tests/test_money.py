"""Tests for Money value object."""

from decimal import Decimal

import pytest

from thinghound.money import Money


def test_money_from_decimal_roundtrip() -> None:
    """Money should convert between decimal and minor-unit encoding."""
    money = Money.from_decimal(Decimal("12.34"), "USD")
    assert money.amount_minor == 1234
    assert money.to_decimal() == Decimal("12.34")


def test_money_add_requires_matching_currency() -> None:
    """Money.add should reject mismatched currencies."""
    usd = Money(amount_minor=100, currency="USD")
    eur = Money(amount_minor=100, currency="EUR")

    with pytest.raises(ValueError):
        usd.add(eur)


def test_money_currency_validation() -> None:
    """Money should validate currency code shape."""
    with pytest.raises(ValueError):
        Money(amount_minor=1, currency="usd")
