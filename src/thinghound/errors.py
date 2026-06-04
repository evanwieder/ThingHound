"""Domain and infrastructure error types for ThingHound foundation."""


class ThingHoundError(Exception):
    """Base class for ThingHound-specific exceptions."""


class ScaleOverflowError(ThingHoundError):
    """Raised when scaled integer magnitude overflows supported bounds."""


class TemporalParseError(ThingHoundError):
    """Raised when an ISO-8601 timestamp cannot be parsed."""


class UnknownUnitError(ThingHoundError):
    """Raised when a unit symbol cannot be normalized."""
