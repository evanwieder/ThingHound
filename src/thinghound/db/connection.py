"""SQLite connection configured for ThingHound (FK off, WAL, cr-sqlite guarded)."""

import sqlite3
from pathlib import Path


def connect(db_path: str | Path = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF;")
    if str(db_path) != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL;")
    return conn
