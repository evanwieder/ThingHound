"""Tests for session and app registry scaffolding."""

import pytest

from thinghound.db_connection import create_connection
from thinghound.registry import AppRegistry, RegistryNotLoadedError
from thinghound.session import Session


def test_session_identity_map_roundtrip() -> None:
    """Session should cache/retrieve objects by type and id."""
    session = Session(create_connection())
    marker = object()
    session.put_identity(str, "k1", marker)
    assert session.get_identity(str, "k1") is marker


def test_registry_get_requires_load() -> None:
    """Registry should reject reads before load."""
    registry = AppRegistry()
    with pytest.raises(RegistryNotLoadedError):
        registry.get("x")


def test_registry_load_then_get() -> None:
    """Registry should return values after load."""
    registry = AppRegistry()
    registry.load({"x": 42})
    assert registry.is_loaded is True
    assert registry.get("x") == 42
