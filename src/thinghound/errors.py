"""Typed domain and infrastructure exceptions shared across ThingHound.

All application-specific exceptions inherit from ``ThingHoundError`` so
callers can catch the entire family with a single ``except`` clause when
needed.
"""


class ThingHoundError(Exception):
    """Base class for all ThingHound-specific exceptions."""


class ScaleOverflowError(ThingHoundError):
    """Raised when a scaled integer value would exceed signed int64 bounds.

    The dual-column storage encoding (``*_scaled INTEGER``) uses SQLite's
    signed 64-bit integer range. Values that would overflow are rejected at
    the encoding boundary rather than silently truncated.
    """


class TemporalParseError(ThingHoundError):
    """Raised when an ISO-8601 timestamp string cannot be parsed.

    Covers malformed strings and strings that lack an explicit UTC offset.
    Models carry timestamps as ISO-8601 strings; the mapper converts them to
    epoch milliseconds at the storage boundary using ``value/temporal.py``.
    """


class UnknownUnitError(ThingHoundError):
    """Raised when a unit symbol is absent from the caller-supplied factors map.

    Unit factors are not hard-coded in the value layer; they come from the
    ``AppRegistry`` which loads ``unit_multiplier`` and ``prefix`` rows at
    startup. This error surfaces when the input names a symbol that was not
    registered.
    """
