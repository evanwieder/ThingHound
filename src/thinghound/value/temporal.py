"""ISO-8601 <-> epoch-millisecond conversion helpers."""

from datetime import UTC, datetime

from thinghound.errors import TemporalParseError


def iso_to_epoch(value: str) -> int:
    """Convert a UTC ISO-8601 timestamp string to epoch milliseconds.

    Args:
        value: ISO-8601 timestamp string.

    Returns:
        Epoch milliseconds in UTC.

    Raises:
        TemporalParseError: If input is malformed or not UTC.
    """
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TemporalParseError(f"Invalid ISO-8601 timestamp: {value}") from exc

    if parsed.tzinfo is None:
        raise TemporalParseError("Timestamp must include timezone offset")

    parsed_utc = parsed.astimezone(UTC)
    return int(parsed_utc.timestamp() * 1000)


def epoch_to_iso(epoch_ms: int) -> str:
    """Convert epoch milliseconds to canonical UTC ISO-8601 string.

    Args:
        epoch_ms: Epoch milliseconds in UTC.

    Returns:
        Canonical UTC ISO-8601 string with trailing `Z`.
    """
    seconds = epoch_ms / 1000
    dt = datetime.fromtimestamp(seconds, tz=UTC)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")
