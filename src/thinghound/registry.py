"""Application registry skeleton — holds preloaded reference/config state."""


class RegistryNotLoadedError(RuntimeError):
    """Raised when a registry accessor is used before data is loaded."""


class AppRegistry:
    """Stores application reference/configuration state loaded at startup.

    Track-2 U1 wires load() to the real mappers. Until then, all accessors
    raise RegistryNotLoadedError.
    """

    def __init__(self) -> None:
        self._loaded = False
        self._state: dict[str, object] = {}

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self, state: dict[str, object]) -> None:
        """Load registry state from a pre-built dict (Track-2 U1 passes real data)."""
        self._state = dict(state)
        self._loaded = True

    def get(self, key: str) -> object:
        """Return a value from loaded state.

        Raises:
            RegistryNotLoadedError: If load() has not been called.
            KeyError: If key does not exist.
        """
        if not self._loaded:
            raise RegistryNotLoadedError("AppRegistry is not loaded")
        return self._state[key]

    def factors_for(self, dimension_id: object) -> dict:
        """Return exact unit factors map for one dimension.

        Raises:
            RegistryNotLoadedError: If load() has not been called.
        """
        if not self._loaded:
            raise RegistryNotLoadedError("AppRegistry is not loaded")
        return self._state.get("factors_by_dimension", {}).get(dimension_id, {})
