"""ISO-8601 ↔ epoch-millisecond helpers used by mappers at the storage boundary."""

from datetime import UTC, datetime

from thinghound.errors import TemporalParseError


def iso_to_epoch(value: str) -> int:
    """Parse a UTC ISO-8601 string to epoch milliseconds."""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TemporalParseError(f"invalid ISO-8601 timestamp: {value!r}") from exc
    if dt.tzinfo is None:
        raise TemporalParseError("timestamp must include a UTC offset")
    return int(dt.astimezone(UTC).timestamp() * 1000)


def epoch_to_iso(epoch_ms: int) -> str:
    """Format epoch milliseconds as a canonical UTC ISO-8601 string ending in Z."""
    dt = datetime.fromtimestamp(epoch_ms / 1000, tz=UTC)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")
