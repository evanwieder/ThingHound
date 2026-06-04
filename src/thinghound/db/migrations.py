"""Migration runner: discovers, applies, and checksums numbered SQL files."""

import hashlib
import sqlite3
from pathlib import Path

_MIGRATIONS_DIR = Path(__file__).parent / "migrations_sql"


def _ensure_migration_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migration (
            version  TEXT PRIMARY KEY,
            name     TEXT NOT NULL DEFAULT '',
            checksum TEXT NOT NULL DEFAULT '',
            applied_at INTEGER NOT NULL DEFAULT 0
        );
        """
    )


def _checksum(sql: str) -> str:
    return hashlib.sha256(sql.encode()).hexdigest()


def apply_all(conn: sqlite3.Connection, migrations_dir: Path = _MIGRATIONS_DIR) -> None:
    """Apply every unapplied migration in lexical order; raise on checksum change."""
    _ensure_migration_table(conn)
    for path in sorted(migrations_dir.glob("*.sql")):
        version = path.stem.split("_", 1)[0]
        name = path.stem
        sql = path.read_text(encoding="utf-8")
        checksum = _checksum(sql)
        row = conn.execute(
            "SELECT checksum FROM schema_migration WHERE version = ?;", (version,)
        ).fetchone()
        if row is not None:
            if row[0] != checksum:
                raise RuntimeError(f"Checksum mismatch for migration {version!r}")
            continue
        with conn:
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migration(version, name, checksum, applied_at) "
                "VALUES (?, ?, ?, CAST(unixepoch('now','subsec') * 1000 AS INTEGER));",
                (version, name, checksum),
            )


def applied_versions(conn: sqlite3.Connection) -> list[str]:
    """Return sorted list of applied migration version strings."""
    rows = conn.execute(
        "SELECT version FROM schema_migration ORDER BY version;"
    ).fetchall()
    return [r[0] for r in rows]
