"""ISO-8601 ↔ epoch-millisecond conversion helpers used at the mapper storage boundary.

Models carry timestamps as ISO-8601 strings (e.g., ``"2026-06-04T12:00:00.000Z"``).
Mappers call these helpers when encoding to SQLite ``INTEGER`` epoch-ms columns and
when decoding back to strings. No other layer should call these directly.
"""

from datetime import UTC, datetime

from thinghound.errors import TemporalParseError


def iso_to_epoch(value: str) -> int:
    """Parse a UTC ISO-8601 timestamp string to epoch milliseconds.

    Args:
        value: An ISO-8601 string with an explicit UTC offset (e.g.,
            ``"2026-06-04T12:00:00Z"`` or ``"2026-06-04T12:00:00+00:00"``).

    Returns:
        The corresponding number of milliseconds since the Unix epoch (UTC).

    Raises:
        TemporalParseError: If the string cannot be parsed as ISO-8601 or
            does not include an explicit timezone offset.
    """
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TemporalParseError(f"invalid ISO-8601 timestamp: {value!r}") from exc
    if dt.tzinfo is None:
        raise TemporalParseError("timestamp must include an explicit UTC offset")
    return int(dt.astimezone(UTC).timestamp() * 1000)


def epoch_to_iso(epoch_ms: int) -> str:
    """Format an epoch-millisecond integer as a canonical UTC ISO-8601 string.

    The output always ends with ``Z`` (e.g., ``"2026-06-04T12:00:00.000Z"``)
    and includes millisecond precision, making round-trips via ``iso_to_epoch``
    exact.

    Args:
        epoch_ms: Milliseconds since the Unix epoch, in UTC.

    Returns:
        Canonical UTC ISO-8601 string with millisecond precision ending in ``Z``.
    """
    dt = datetime.fromtimestamp(epoch_ms / 1000, tz=UTC)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")
