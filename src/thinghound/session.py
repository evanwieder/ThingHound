"""Session (Unit of Work): connection, transaction scope, identity map. No SQL, no row conversion."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager


class Session:
    """Coordinates transaction scope and the session-level identity map.

    Does not own table SQL and performs no row↔model conversion — those belong
    to aggregate mappers (Track 2).
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._identity_map: dict[tuple[type, object], object] = {}

    @property
    def connection(self) -> sqlite3.Connection:
        return self._connection

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        try:
            self._connection.execute("BEGIN;")
            yield
            self._connection.execute("COMMIT;")
        except Exception:
            self._connection.execute("ROLLBACK;")
            raise

    def get_identity(self, typ: type, object_id: object) -> object | None:
        return self._identity_map.get((typ, object_id))

    def put_identity(self, typ: type, object_id: object, instance: object) -> None:
        self._identity_map[(typ, object_id)] = instance
