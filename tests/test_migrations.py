"""Tests for migration application behavior."""

from pathlib import Path

import pytest

from thinghound.db_connection import create_connection
from thinghound.migrations import apply_migrations


def test_apply_migrations_applies_once(tmp_path: Path) -> None:
    """Applying migrations twice should be idempotent."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "0001_init.sql").write_text(
        "CREATE TABLE IF NOT EXISTS demo(id INTEGER PRIMARY KEY, name TEXT NOT NULL DEFAULT '');",
        encoding="utf-8",
    )

    connection = create_connection()
    try:
        apply_migrations(connection, migrations_dir)
        apply_migrations(connection, migrations_dir)
        row = connection.execute("SELECT COUNT(*) FROM th_migration;").fetchone()
        assert row[0] == 1
    finally:
        connection.close()


def test_apply_migrations_detects_checksum_mismatch(tmp_path: Path) -> None:
    """Changing migration SQL after apply should raise checksum mismatch."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    migration_file = migrations_dir / "0001_init.sql"
    migration_file.write_text(
        "CREATE TABLE IF NOT EXISTS demo(id INTEGER PRIMARY KEY, name TEXT NOT NULL DEFAULT '');",
        encoding="utf-8",
    )

    connection = create_connection()
    try:
        apply_migrations(connection, migrations_dir)
        migration_file.write_text(
            (
                "CREATE TABLE IF NOT EXISTS demo(" 
                "id INTEGER PRIMARY KEY, value TEXT NOT NULL DEFAULT ''" 
                ");"
            ),
            encoding="utf-8",
        )
        with pytest.raises(RuntimeError, match="Checksum mismatch"):
            apply_migrations(connection, migrations_dir)
    finally:
        connection.close()
