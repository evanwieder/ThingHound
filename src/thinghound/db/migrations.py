"""Migration discovery and application for ThingHound SQLite schema."""

import hashlib
import sqlite3
from pathlib import Path


def ensure_migration_table(connection: sqlite3.Connection) -> None:
    """Create migration metadata table if it does not already exist.

    Args:
        connection: Active SQLite connection.
    """
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS th_migration (
            version TEXT PRIMARY KEY,
            checksum TEXT NOT NULL,
            applied_at_epoch_ms INTEGER NOT NULL DEFAULT 0
        );
        """
    )


def _checksum(sql_text: str) -> str:
    """Compute deterministic checksum for migration SQL.

    Args:
        sql_text: Migration SQL text.

    Returns:
        SHA256 checksum in hexadecimal.
    """
    return hashlib.sha256(sql_text.encode("utf-8")).hexdigest()


def apply_migrations(connection: sqlite3.Connection, migrations_dir: Path) -> None:
    """Apply numbered migrations in lexical order.

    Args:
        connection: Active SQLite connection.
        migrations_dir: Directory containing `.sql` migration files.

    Raises:
        RuntimeError: If an already-applied version has a checksum mismatch.
    """
    ensure_migration_table(connection)
    migration_files = sorted(migrations_dir.glob("*.sql"))

    for migration_file in migration_files:
        version = migration_file.stem.split("_", 1)[0]
        sql_text = migration_file.read_text(encoding="utf-8")
        checksum = _checksum(sql_text)

        existing = connection.execute(
            "SELECT checksum FROM th_migration WHERE version = ?;",
            (version,),
        ).fetchone()

        if existing is not None:
            if existing[0] != checksum:
                raise RuntimeError(f"Checksum mismatch for migration {version}")
            continue

        with connection:
            connection.executescript(sql_text)
            connection.execute(
                """
                INSERT INTO th_migration(version, checksum, applied_at_epoch_ms)
                VALUES (?, ?, CAST(unixepoch('now', 'subsec') * 1000 AS INTEGER));
                """,
                (version, checksum),
            )
