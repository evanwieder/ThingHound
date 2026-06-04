"""Database infrastructure: connection factory, migration runner, and SQL files.

All SQLite connections used by ThingHound must be opened through
``thinghound.db.connection.connect()`` so that the required pragma
settings (``foreign_keys = OFF``, WAL mode) are applied uniformly.
Migration SQL files live in ``migrations_sql/`` under this package.
"""
