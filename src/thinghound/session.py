"""Session and Unit-of-Work primitives for ThingHound foundation."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager


class Session:
    """Coordinates transaction scope and identity map without owning SQL."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Initialize a session.

        Args:
            connection: Active SQLite connection.
        """
        self._connection = connection
        self._identity_map: dict[tuple[type, object], object] = {}

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        """Execute a transaction scope.

        Yields:
            None.
        """
        try:
            self._connection.execute("BEGIN;")
            yield
            self._connection.execute("COMMIT;")
        except Exception:
            self._connection.execute("ROLLBACK;")
            raise

    def get_identity(self, typ: type, object_id: object) -> object | None:
        """Get object from identity map.

        Args:
            typ: Object type key.
            object_id: Object ID key.

        Returns:
            Cached object or None.
        """
        return self._identity_map.get((typ, object_id))

    def put_identity(self, typ: type, object_id: object, instance: object) -> None:
        """Put object into identity map.

        Args:
            typ: Object type key.
            object_id: Object ID key.
            instance: Instance to cache.
        """
        self._identity_map[(typ, object_id)] = instance
