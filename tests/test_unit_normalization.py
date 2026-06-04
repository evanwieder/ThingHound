"""Tests for unit normalization helpers."""

from decimal import Decimal

import pytest

from thinghound.errors import UnknownUnitError
from thinghound.unit_normalization import normalize_unit, unit_factor


def test_normalize_unit_canonicalizes_case_and_space() -> None:
    """normalize_unit should produce lowercase canonical symbol."""
    assert normalize_unit("  kOhM ") == "kohm"


def test_unit_factor_returns_decimal_factor() -> None:
    """unit_factor should return correct base conversion factors."""
    assert unit_factor("mV") == Decimal("0.001")
    assert unit_factor("ohm") == Decimal("1")


def test_normalize_unit_rejects_unknown_symbol() -> None:
    """normalize_unit should raise typed errors for unknown units."""
    with pytest.raises(UnknownUnitError):
        normalize_unit("miles")
