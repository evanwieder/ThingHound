"""AppRegistry skeleton — holds preloaded structure/config state for the session.

Track-2 U1 wires load() to the real aggregate mappers. Until then all accessors
raise RegistryNotLoadedError.
"""


class RegistryNotLoadedError(RuntimeError):
    """Raised when a registry accessor is called before load()."""


class AppRegistry:

    def __init__(self) -> None:
        self._loaded = False
        self._state: dict[str, object] = {}

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self, state: dict[str, object]) -> None:
        """Load from a pre-built state dict. Track-2 U1 passes the real data."""
        self._state = dict(state)
        self._loaded = True

    def get(self, key: str) -> object:
        if not self._loaded:
            raise RegistryNotLoadedError("AppRegistry.load() has not been called")
        return self._state[key]

    def factors_for(self, dimension_id: object) -> dict:
        if not self._loaded:
            raise RegistryNotLoadedError("AppRegistry.load() has not been called")
        return self._state.get("factors_by_dimension", {}).get(dimension_id, {})
