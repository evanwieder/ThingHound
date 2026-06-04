"""Mock bridge fixtures shaped for the UI contract."""

from __future__ import annotations

from typing import Any

DISPLAY_COLUMNS: list[dict[str, str]] = [
    {"key": "hero", "title": "Hero"},
    {"key": "name", "title": "Name"},
    {"key": "category", "title": "Category"},
    {"key": "value", "title": "Value"},
    {"key": "on_hand", "title": "On Hand"},
]

COLUMN_MAPPINGS: dict[str, dict[str, str | None]] = {
    "resistor": {"hero": "resistance", "value": "resistance_display"},
    "capacitor": {"hero": "capacitance", "value": "capacitance_display"},
    "connector": {"hero": None, "value": "pitch_display"},
    "mechanical": {"hero": None, "value": "size_display"},
}

GRID_ROWS: list[dict[str, Any]] = [
    {
        "id": "018f49c4-8bca-7f4b-90f0-1ed20d53a001",
        "type": "resistor",
        "thumbnail": "",
        "name": "1k Resistor",
        "category": "Resistors",
        "hero": "1 kΩ",
        "resistance": {"value_exact": "1000", "display": "1 kΩ"},
        "value": "1 kΩ",
        "on_hand": {"value_exact": "250", "display": "250"},
    },
    {
        "id": "018f49c4-8bca-7f4b-90f0-1ed20d53a002",
        "type": "capacitor",
        "thumbnail": "",
        "name": "100nF Capacitor",
        "category": "Capacitors",
        "hero": "100 nF",
        "capacitance": {"value_exact": "100", "display": "100 nF"},
        "value": "100 nF",
        "on_hand": {"value_exact": "500", "display": "500"},
    },
    {
        "id": "018f49c4-8bca-7f4b-90f0-1ed20d53a003",
        "type": "connector",
        "thumbnail": "",
        "name": "JST-XH 2P",
        "category": "Connectors",
        "hero": "",
        "pitch": {"value_exact": "2.54", "display": "2.54 mm"},
        "value": "2.54 mm",
        "on_hand": {"value_exact": "48", "display": "48"},
    },
    {
        "id": "018f49c4-8bca-7f4b-90f0-1ed20d53a004",
        "type": "mechanical",
        "thumbnail": "",
        "name": "M3 Screw",
        "category": "Mechanical",
        "hero": "",
        "size": {"value_exact": "12", "display": "M3 x 12"},
        "value": "M3 x 12",
        "on_hand": {"value_exact": "900", "display": "900"},
    },
]

CATEGORY_TREE: list[dict[str, Any]] = [
    {
        "id": "root",
        "name": "All Categories",
        "children": [
            {"id": "resistors", "name": "Resistors", "children": []},
            {"id": "capacitors", "name": "Capacitors", "children": []},
            {"id": "connectors", "name": "Connectors", "children": []},
            {"id": "mechanical", "name": "Mechanical", "children": []},
        ],
    }
]

INSPECTOR_TABS: list[str] = [
    "Attributes",
    "Stock & Events",
    "Instances",
    "Vendors",
    "Alternates",
    "BOM/Where-used",
    "Simulation",
]
