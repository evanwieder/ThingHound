"""Tests for Session (unit of work) and AppRegistry skeleton."""

import pytest

from thinghound.db.connection import create_connection
from thinghound.registry import AppRegistry, RegistryNotLoadedError
from thinghound.session import Session


def test_session_identity_map_roundtrip() -> None:
    """Session should cache and retrieve objects by type and id."""
    session = Session(create_connection())
    marker = object()
    session.put_identity(str, "k1", marker)
    assert session.get_identity(str, "k1") is marker


def test_registry_get_requires_load() -> None:
    """Registry should reject reads before load() is called."""
    registry = AppRegistry()
    with pytest.raises(RegistryNotLoadedError):
        registry.get("x")


def test_registry_factors_for_requires_load() -> None:
    """Registry.factors_for should reject reads before load() is called."""
    registry = AppRegistry()
    with pytest.raises(RegistryNotLoadedError):
        registry.factors_for("any_id")


def test_registry_load_then_get() -> None:
    """Registry should return values after load()."""
    registry = AppRegistry()
    registry.load({"x": 42})
    assert registry.is_loaded is True
    assert registry.get("x") == 42


def test_registry_load_then_factors_for_missing_dimension() -> None:
    """factors_for returns an empty dict for an unknown dimension."""
    registry = AppRegistry()
    registry.load({})
    assert registry.factors_for("nonexistent") == {}
