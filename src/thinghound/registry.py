"""Application registry skeleton for preloaded reference/config state."""


class RegistryNotLoadedError(RuntimeError):
    """Raised when a registry accessor is used before data is loaded."""


class AppRegistry:
    """Stores application reference/configuration state loaded at startup."""

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._loaded = False
        self._state: dict[str, object] = {}

    @property
    def is_loaded(self) -> bool:
        """Return whether registry state has been loaded."""
        return self._loaded

    def load(self, state: dict[str, object]) -> None:
        """Load immutable registry state.

        Args:
            state: Registry state values.
        """
        self._state = dict(state)
        self._loaded = True

    def get(self, key: str) -> object:
        """Get a value from loaded registry state.

        Args:
            key: State key.

        Returns:
            Stored value for key.

        Raises:
            RegistryNotLoadedError: If `load` was not called.
            KeyError: If key does not exist.
        """
        if not self._loaded:
            raise RegistryNotLoadedError("AppRegistry is not loaded")
        return self._state[key]
