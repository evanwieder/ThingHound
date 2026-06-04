"""Typed domain errors shared across the ThingHound foundation."""


class ThingHoundError(Exception):
    """Base for all ThingHound-specific exceptions."""


class ScaleOverflowError(ThingHoundError):
    """Scaled integer magnitude exceeds signed int64 bounds."""


class TemporalParseError(ThingHoundError):
    """ISO-8601 timestamp is malformed or missing a UTC offset."""


class UnknownUnitError(ThingHoundError):
    """Unit symbol is not present in the caller-supplied factors map."""
