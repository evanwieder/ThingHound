"""SQLite connection factory configured for ThingHound constraints."""

import sqlite3
from pathlib import Path


def create_connection(db_path: str | Path = ":memory:") -> sqlite3.Connection:
    """Create a sqlite3 connection with ThingHound-required pragmas.

    Args:
        db_path: Database file path or `":memory:"`.

    Returns:
        Configured sqlite3 connection.
    """
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = OFF;")
    if str(db_path) != ":memory:":
        connection.execute("PRAGMA journal_mode = WAL;")
    return connection
