"""Tests for temporal conversion helpers."""

import pytest

from thinghound.errors import TemporalParseError
from thinghound.value.temporal import epoch_to_iso, iso_to_epoch


def test_iso_to_epoch_known_zero_value() -> None:
    """Unix epoch start should map to zero milliseconds."""
    assert iso_to_epoch("1970-01-01T00:00:00Z") == 0


def test_temporal_roundtrip_utc_iso() -> None:
    """ISO UTC input should roundtrip via epoch milliseconds."""
    value = "2026-01-02T03:04:05.678Z"
    assert epoch_to_iso(iso_to_epoch(value)) == value


def test_iso_to_epoch_rejects_malformed_input() -> None:
    """Malformed timestamp should raise typed temporal parse error."""
    with pytest.raises(TemporalParseError):
        iso_to_epoch("not-a-timestamp")
