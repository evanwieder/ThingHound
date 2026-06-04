"""Tests for migration application behaviour."""

from pathlib import Path

import pytest

from thinghound.db.connection import connect
from thinghound.db.migrations import apply_all, applied_versions


def _write_migration(directory: Path, name: str, sql: str) -> None:
    (directory / name).write_text(sql, encoding="utf-8")


def test_apply_all_is_idempotent(tmp_path: Path) -> None:
    mdir = tmp_path / "migrations_sql"
    mdir.mkdir()
    _write_migration(mdir, "0001_init.sql",
                     "CREATE TABLE IF NOT EXISTS demo(id INTEGER PRIMARY KEY);")
    conn = connect()
    try:
        apply_all(conn, mdir)
        apply_all(conn, mdir)
        assert applied_versions(conn) == ["0001"]
    finally:
        conn.close()


def test_apply_all_records_schema_migration_row(tmp_path: Path) -> None:
    mdir = tmp_path / "migrations_sql"
    mdir.mkdir()
    _write_migration(mdir, "0001_init.sql",
                     "CREATE TABLE IF NOT EXISTS demo(id INTEGER PRIMARY KEY);")
    conn = connect()
    try:
        apply_all(conn, mdir)
        row = conn.execute("SELECT version, name FROM schema_migration;").fetchone()
        assert row["version"] == "0001"
        assert row["name"] == "0001_init"
    finally:
        conn.close()


def test_apply_all_raises_on_checksum_mismatch(tmp_path: Path) -> None:
    mdir = tmp_path / "migrations_sql"
    mdir.mkdir()
    f = mdir / "0001_init.sql"
    f.write_text("CREATE TABLE IF NOT EXISTS demo(id INTEGER PRIMARY KEY);", encoding="utf-8")
    conn = connect()
    try:
        apply_all(conn, mdir)
        f.write_text("CREATE TABLE IF NOT EXISTS demo(id INTEGER PRIMARY KEY, x TEXT);",
                     encoding="utf-8")
        with pytest.raises(RuntimeError, match="Checksum mismatch"):
            apply_all(conn, mdir)
    finally:
        conn.close()
