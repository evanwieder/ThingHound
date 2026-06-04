"""Tests for SQLite connection setup."""

from pathlib import Path

from thinghound.db.connection import create_connection


def test_create_connection_disables_foreign_keys_for_memory_db() -> None:
    """Memory connection should always set foreign_keys pragma to OFF."""
    connection = create_connection()
    try:
        row = connection.execute("PRAGMA foreign_keys;").fetchone()
        assert row[0] == 0
    finally:
        connection.close()


def test_create_connection_enables_wal_for_file_db(tmp_path: Path) -> None:
    """File-based connection should switch to WAL journal mode."""
    connection = create_connection(tmp_path / "thinghound.db")
    try:
        row = connection.execute("PRAGMA journal_mode;").fetchone()
        assert str(row[0]).lower() == "wal"
    finally:
        connection.close()
