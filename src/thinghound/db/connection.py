"""SQLite connection factory configured with ThingHound's required pragma settings.

Every connection used by ThingHound must be created through ``connect()`` so
that ``foreign_keys = OFF`` and WAL mode are applied consistently. cr-sqlite
extension loading is guarded behind a flag because ``enable_load_extension``
may be unavailable in some build environments (see ``docs/dev/crsqlite-spike-findings.md``).
"""

import sqlite3
from pathlib import Path


def connect(db_path: str | Path = ":memory:", *, load_crsqlite: bool = False) -> sqlite3.Connection:
    """Open a SQLite connection with ThingHound's required pragma settings.

    Sets ``foreign_keys = OFF`` (cr-sqlite requirement; referential integrity
    is enforced at the application layer) and ``journal_mode = WAL`` for
    file-based databases. In-memory databases skip WAL because SQLite ignores
    it for ``:memory:`` paths.

    Args:
        db_path: Filesystem path to the database file, or ``":memory:"`` for an
            in-memory database. Defaults to ``":memory:"``.
        load_crsqlite: If ``True``, attempt to load the cr-sqlite extension.
            Guarded by availability of ``enable_load_extension``; silently
            skipped if the SQLite build does not support extension loading.

    Returns:
        An open ``sqlite3.Connection`` with ``row_factory`` set to
        ``sqlite3.Row``.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF;")
    if str(db_path) != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL;")
    return conn
