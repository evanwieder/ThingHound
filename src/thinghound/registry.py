"""Application registry: session-scoped cache of preloaded structure and config state.

The registry is populated once at startup via ``AppRegistry.load()`` and then
treated as read-only for the duration of the session. Track-2 U1 wires
``load()`` to the real aggregate mappers; until then all accessors raise
``RegistryNotLoadedError``.
"""


class RegistryNotLoadedError(RuntimeError):
    """Raised when any ``AppRegistry`` accessor is called before ``load()``."""


class AppRegistry:
    """Session-scoped cache for unit dimensions, attribute definitions, and factors.

    Populated by Track-2 U1 via ``load()``. Before that call every accessor
    raises ``RegistryNotLoadedError`` so accidental early access fails loudly.
    """

    def __init__(self) -> None:
        """Initialise an empty, unloaded registry."""
        self._loaded = False
        self._state: dict[str, object] = {}

    @property
    def is_loaded(self) -> bool:
        """``True`` after ``load()`` has been called at least once."""
        return self._loaded

    def load(self, state: dict[str, object]) -> None:
        """Populate the registry from a pre-built state dict.

        Track-2 U1 constructs this dict by querying the aggregate mappers and
        passes it here. Until that unit exists, tests may pass a minimal dict
        directly.

        Args:
            state: Mapping of named registry keys to their values. The
                ``"factors_by_dimension"`` key, if present, must map
                dimension UUIDs to ``{multiplier_uuid: Fraction}`` dicts.
        """
        self._state = dict(state)
        self._loaded = True

    def get(self, key: str) -> object:
        """Return a value from the loaded state dict.

        Args:
            key: Registry state key.

        Returns:
            The value stored under ``key``.

        Raises:
            RegistryNotLoadedError: If ``load()`` has not been called.
            KeyError: If ``key`` is not present in the loaded state.
        """
        if not self._loaded:
            raise RegistryNotLoadedError("AppRegistry.load() has not been called")
        return self._state[key]

    def factors_for(self, dimension_id: object) -> dict:
        """Return the exact unit-factor map for a dimension.

        Args:
            dimension_id: The ``UUIDv7`` of the ``unit_dimension`` row.

        Returns:
            A ``{multiplier_id: Fraction}`` dict, or an empty dict if the
            dimension has no registered multipliers.

        Raises:
            RegistryNotLoadedError: If ``load()`` has not been called.
        """
        if not self._loaded:
            raise RegistryNotLoadedError("AppRegistry.load() has not been called")
        return self._state.get("factors_by_dimension", {}).get(dimension_id, {})
