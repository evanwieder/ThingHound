"""Migration runner: discovers, applies, and checksums numbered SQL migration files.

Migrations live in ``src/thinghound/db/migrations_sql/`` and are applied in
lexical order by their numeric prefix. Each applied migration is recorded in
the ``schema_migration`` LOCAL table with a SHA-256 checksum so that
post-application modifications to a file are detected and rejected.
"""

import hashlib
import sqlite3
from pathlib import Path

_MIGRATIONS_DIR = Path(__file__).parent / "migrations_sql"


def _ensure_migration_table(conn: sqlite3.Connection) -> None:
    """Create the ``schema_migration`` tracking table if it does not exist.

    The table is ``-- sync: LOCAL`` (never synced via cr-sqlite) and stores
    one row per applied migration.

    Args:
        conn: An open ``sqlite3.Connection``.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migration (
            version    TEXT PRIMARY KEY,
            name       TEXT NOT NULL DEFAULT '',
            checksum   TEXT NOT NULL DEFAULT '',
            applied_at INTEGER NOT NULL DEFAULT 0
        );
        """
    )


def _checksum(sql: str) -> str:
    """Compute a SHA-256 hex digest over the UTF-8 encoding of a SQL string.

    Args:
        sql: The migration SQL text.

    Returns:
        Lowercase hexadecimal SHA-256 digest.
    """
    return hashlib.sha256(sql.encode()).hexdigest()


def apply_all(conn: sqlite3.Connection, migrations_dir: Path = _MIGRATIONS_DIR) -> None:
    """Apply every unapplied ``*.sql`` file in ``migrations_dir`` in lexical order.

    Already-applied versions are skipped. If a previously applied migration
    file has been modified (checksum mismatch), a ``RuntimeError`` is raised
    immediately and no further migrations are applied.

    Args:
        conn: An open ``sqlite3.Connection`` (typically in-memory for tests or
            the real application database).
        migrations_dir: Directory containing numbered ``*.sql`` files. Defaults
            to the bundled ``src/thinghound/db/migrations_sql/`` directory.

    Raises:
        RuntimeError: If the on-disk checksum of a previously applied migration
            does not match the recorded checksum.
    """
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
    """Return the sorted list of version strings for all applied migrations.

    Args:
        conn: An open ``sqlite3.Connection`` with the ``schema_migration`` table
            already created (i.e., after at least one call to ``apply_all``).

    Returns:
        Sorted list of applied version strings (e.g., ``["0001", "0002"]``).
    """
    rows = conn.execute(
        "SELECT version FROM schema_migration ORDER BY version;"
    ).fetchall()
    return [r[0] for r in rows]
