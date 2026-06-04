"""Session (Unit of Work): connection ownership, transaction scope, and identity map.

The Session is the only layer that calls ``BEGIN``/``COMMIT``/``ROLLBACK``. It
exposes mappers and query objects (added in Track 2) and owns the transaction
they run inside. It does not hold any table SQL and performs no row-to-model
conversion — those responsibilities belong exclusively to aggregate mappers.
"""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager


class Session:
    """Coordinates transaction scope and the session-level identity map.

    Does not own table SQL and performs no row-to-model conversion. Those
    responsibilities belong exclusively to aggregate mappers (Track 2).
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Initialise a session around an existing SQLite connection.

        Args:
            connection: An open ``sqlite3.Connection`` configured by
                ``thinghound.db.connection.connect()``.
        """
        self._connection = connection
        self._identity_map: dict[tuple[type, object], object] = {}

    @property
    def connection(self) -> sqlite3.Connection:
        """The underlying SQLite connection, exposed for mapper and query use."""
        return self._connection

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        """Context manager that wraps a single database transaction.

        Issues ``BEGIN`` on entry, ``COMMIT`` on clean exit, and ``ROLLBACK``
        if any exception escapes the body.

        Yields:
            Nothing; used purely for its side-effects on the connection.

        Raises:
            Exception: Re-raises any exception raised inside the ``with`` block
                after rolling back the transaction.
        """
        try:
            self._connection.execute("BEGIN;")
            yield
            self._connection.execute("COMMIT;")
        except Exception:
            self._connection.execute("ROLLBACK;")
            raise

    def get_identity(self, typ: type, object_id: object) -> object | None:
        """Retrieve a cached object from the identity map.

        Args:
            typ: The Python type used as the first key dimension.
            object_id: The object's identifier used as the second key dimension.

        Returns:
            The cached object, or ``None`` if no entry exists for the key.
        """
        return self._identity_map.get((typ, object_id))

    def put_identity(self, typ: type, object_id: object, instance: object) -> None:
        """Store an object in the identity map.

        Args:
            typ: The Python type used as the first key dimension.
            object_id: The object's identifier used as the second key dimension.
            instance: The object to cache.
        """
        self._identity_map[(typ, object_id)] = instance
