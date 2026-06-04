"""Tests for SQLite connection setup."""

from pathlib import Path

from thinghound.db.connection import connect


def test_connect_disables_foreign_keys() -> None:
    conn = connect()
    try:
        assert conn.execute("PRAGMA foreign_keys;").fetchone()[0] == 0
    finally:
        conn.close()


def test_connect_enables_wal_for_file_db(tmp_path: Path) -> None:
    conn = connect(tmp_path / "thinghound.db")
    try:
        assert conn.execute("PRAGMA journal_mode;").fetchone()[0].lower() == "wal"
    finally:
        conn.close()
