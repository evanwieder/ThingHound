"""Tests for UI bridge contract behavior."""

from thinghound.ui.bridge import Bridge


def test_bridge_error_returns_typed_envelope() -> None:
    """Bridge should emit typed error envelopes for JS consumers."""
    bridge = Bridge(mock=True)

    assert bridge.error("INVALID_UUID", "bad", field="item_id") == {
        "code": "INVALID_UUID",
        "message": "bad",
        "field": "item_id",
    }


def test_mock_grid_query_items_returns_rows_and_total() -> None:
    """Mock bridge grid query should return rows and total shape."""
    bridge = Bridge(mock=True)

    response = bridge.grid_query_items({})

    assert set(response.keys()) == {"rows", "total"}
    assert isinstance(response["rows"], list)
    assert isinstance(response["total"], int)


def test_mock_bridge_exposes_display_schema_and_tree() -> None:
    """Mock bridge should provide display columns, mappings, and category tree."""
    bridge = Bridge(mock=True)

    columns = bridge.get_display_columns({})
    mappings = bridge.get_column_mappings({})
    tree = bridge.get_category_tree({})

    assert "columns" in columns and isinstance(columns["columns"], list)
    assert "mappings" in mappings and isinstance(mappings["mappings"], dict)
    assert "nodes" in tree and isinstance(tree["nodes"], list)


def test_mock_inspector_payload_returns_summary_and_tabs() -> None:
    """Mock bridge should return inspector payload for known item ids."""
    bridge = Bridge(mock=True)

    grid = bridge.grid_query_items({})
    first_id = grid["rows"][0]["id"]
    payload = bridge.get_inspector_payload({"itemId": first_id})

    assert "summary" in payload and isinstance(payload["summary"], dict)
    assert "tabs" in payload and isinstance(payload["tabs"], dict)


def test_mock_inspector_payload_returns_typed_not_found_error() -> None:
    """Unknown items should return typed not-found errors."""
    bridge = Bridge(mock=True)

    payload = bridge.get_inspector_payload({"itemId": "00000000-0000-0000-0000-000000000000"})

    assert payload["code"] == "NOT_FOUND"
    assert payload["field"] == "itemId"
