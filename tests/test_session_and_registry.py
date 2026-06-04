"""Tests for Session (unit of work) and AppRegistry skeleton."""

import pytest

from thinghound.db.connection import connect
from thinghound.registry import AppRegistry, RegistryNotLoadedError
from thinghound.session import Session


def test_session_identity_map_roundtrip() -> None:
    session = Session(connect())
    marker = object()
    session.put_identity(str, "k1", marker)
    assert session.get_identity(str, "k1") is marker


def test_registry_get_raises_before_load() -> None:
    with pytest.raises(RegistryNotLoadedError):
        AppRegistry().get("x")


def test_registry_factors_for_raises_before_load() -> None:
    with pytest.raises(RegistryNotLoadedError):
        AppRegistry().factors_for("any")


def test_registry_load_then_get() -> None:
    registry = AppRegistry()
    registry.load({"x": 42})
    assert registry.is_loaded is True
    assert registry.get("x") == 42


def test_registry_factors_for_unknown_dimension_returns_empty() -> None:
    registry = AppRegistry()
    registry.load({})
    assert registry.factors_for("missing") == {}
