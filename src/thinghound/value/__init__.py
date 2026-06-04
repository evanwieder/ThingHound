"""Value-layer encoding helpers used at the mapper storage boundary.

This package provides exact, DBMS-agnostic primitives for encoding and
decoding domain values to and from their SQLite physical representations.
No layer above the aggregate mappers should import from this package directly.
"""
