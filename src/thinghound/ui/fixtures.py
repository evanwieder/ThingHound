"""Mock bridge fixtures shaped for the UI contract."""


from typing import Any

DISPLAY_COLUMNS: list[dict[str, str]] = [
    {"key": "name", "title": "Name"},
    {"key": "sku", "title": "SKU"},
    {"key": "description", "title": "Description"},
    {"key": "stock", "title": "Stock"},
    {"key": "status", "title": "Status"},
    {"key": "footprint", "title": "Footprint"},
]

COLUMN_MAPPINGS: dict[str, dict[str, str | None]] = {
    "resistor": {"stock": "qty_available", "footprint": "nominal_footprint"},
    "capacitor": {"stock": "qty_available", "footprint": "nominal_footprint"},
    "connector": {"stock": "qty_available", "footprint": "nominal_footprint"},
    "mechanical": {"stock": "qty_available", "footprint": "nominal_footprint"},
}

ATTRIBUTES_BY_CATEGORY: dict[str, list[dict[str, str]]] = {
    "Resistors": [
        {"name": "Resistance", "value": "1 kΩ"},
        {"name": "Tolerance", "value": "±1%"},
        {"name": "Power Rating", "value": "1/10 W"},
        {"name": "Voltage Rating (DC)", "value": "75 V"},
    ],
    "Capacitors": [
        {"name": "Capacitance", "value": "100 nF"},
        {"name": "Voltage Rating (DC)", "value": "50 V"},
        {"name": "Dielectric", "value": "X7R"},
        {"name": "Tolerance", "value": "±10%"},
    ],
    "MOSFET": [
        {"name": "Polarity", "value": "N-Channel"},
        {"name": "Drain-Source Voltage (Vds)", "value": "60 V"},
        {"name": "Continuous Drain Current", "value": "200 mA"},
        {"name": "On Resistance (Rds on)", "value": "5 Ω"},
    ],
    "Connectors": [
        {"name": "Pitch", "value": "2.54 mm"},
        {"name": "Pin Count", "value": "2"},
        {"name": "Mounting Style", "value": "Through Hole"},
        {"name": "Orientation", "value": "Vertical"},
    ],
    "Mechanical": [
        {"name": "Thread", "value": "M3"},
        {"name": "Length", "value": "12 mm"},
        {"name": "Head Style", "value": "Pan Head"},
        {"name": "Material", "value": "Stainless A2"},
    ],
}


def _row(
    *,
    uid: str,
    sku: str,
    name: str,
    description: str,
    part_number: str,
    stock: str,
    status: str,
    footprint: str,
    stock_mode: str,
    instance_kind: str,
    markings: str,
    category: str,
    category_path: list[str],
) -> dict[str, Any]:
    return {
        "id": uid,
        "sku": sku,
        "name": name,
        "description": description,
        "part_number": part_number,
        "stock": stock,
        "status": status,
        "footprint": footprint,
        "stock_mode": stock_mode,
        "instance_kind": instance_kind,
        "markings": markings,
        "category": category,
        "category_path": category_path,
        "category_path_display": " > ".join(_NAME_BY_ID.get(cid, cid) for cid in category_path),
        "attributes": ATTRIBUTES_BY_CATEGORY.get(category, []),
    }


_NAME_BY_ID: dict[str, str] = {
    "root": "All Categories",
    "passive": "Passive",
    "active": "Active",
    "electromechanical": "Electromechanical",
    "mechanical": "Mechanical",
    "resistors": "Resistors",
    "capacitors": "Capacitors",
    "inductors": "Inductors",
    "semiconductors": "Semiconductors",
    "transistors": "Transistors",
    "mosfet": "MOSFET",
    "bjt": "BJT",
    "diodes": "Diodes",
    "ics": "Integrated Circuits",
    "connectors": "Connectors",
    "switches": "Switches",
}


GRID_ROWS: list[dict[str, Any]] = [
    _row(
        uid="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        sku="RES-1K-0603-1%",
        name="Resistor 1 kΩ 1% 0603",
        description="Thick film chip resistor, 0603, 1 kΩ, ±1%, 1/10 W",
        part_number="RC0603FR-071KL",
        stock="250",
        status="Active",
        footprint="0603",
        stock_mode="Bulk",
        instance_kind="Lot",
        markings="102",
        category="Resistors",
        category_path=["root", "passive", "resistors"],
    ),
    _row(
        uid="01ARZ3NDEKTSV4RRFFQ69G5FAW",
        sku="RES-10K-0603-1%",
        name="Resistor 10 kΩ 1% 0603",
        description="Thick film chip resistor, 0603, 10 kΩ, ±1%, 1/10 W",
        part_number="RC0603FR-0710KL",
        stock="0",
        status="Active",
        footprint="0603",
        stock_mode="Bulk",
        instance_kind="Lot",
        markings="103",
        category="Resistors",
        category_path=["root", "passive", "resistors"],
    ),
    _row(
        uid="01ARZ3NDEKTSV4RRFFQ69G5FAX",
        sku="CAP-100N-0603-50V",
        name="Capacitor 100 nF 50 V 0603 X7R",
        description="MLCC, 0603, 100 nF, 50 V, X7R, ±10%",
        part_number="CC0603KRX7R9BB104",
        stock="500",
        status="Active",
        footprint="0603",
        stock_mode="Bulk",
        instance_kind="Lot",
        markings="104",
        category="Capacitors",
        category_path=["root", "passive", "capacitors"],
    ),
    _row(
        uid="01ARZ3NDEKTSV4RRFFQ69G5FB1",
        sku="CAP-10U-0805-25V",
        name="Capacitor 10 µF 25 V 0805 X5R",
        description="MLCC, 0805, 10 µF, 25 V, X5R, ±20%",
        part_number="CL21A106KAYNNNG",
        stock="120",
        status="Active",
        footprint="0805",
        stock_mode="Bulk",
        instance_kind="Lot",
        markings="106",
        category="Capacitors",
        category_path=["root", "passive", "capacitors"],
    ),
    _row(
        uid="01ARZ3NDEKTSV4RRFFQ69G5FB2",
        sku="MOS-2N7000-TO92",
        name="MOSFET 2N7000 N-Channel",
        description="N-Channel 60 V 200 mA enhancement-mode MOSFET, TO-92",
        part_number="2N7000",
        stock="23",
        status="Active",
        footprint="TO-92",
        stock_mode="Instance",
        instance_kind="Serial",
        markings="2N7000",
        category="MOSFET",
        category_path=["root", "active", "semiconductors", "transistors", "mosfet"],
    ),
    _row(
        uid="01ARZ3NDEKTSV4RRFFQ69G5FB3",
        sku="MOS-IRFZ44N-TO220",
        name="MOSFET IRFZ44N N-Channel",
        description="N-Channel 55 V 49 A MOSFET, TO-220",
        part_number="IRFZ44N",
        stock="6",
        status="NRND",
        footprint="TO-220",
        stock_mode="Instance",
        instance_kind="Serial",
        markings="IRFZ44N",
        category="MOSFET",
        category_path=["root", "active", "semiconductors", "transistors", "mosfet"],
    ),
    _row(
        uid="01ARZ3NDEKTSV4RRFFQ69G5FB4",
        sku="CON-JST-XH-2P",
        name="Connector JST-XH 2-Pin",
        description="JST XH series, 2-pin header, 2.54 mm pitch, top entry",
        part_number="B2B-XH-A",
        stock="48",
        status="Active",
        footprint="TH-2.54",
        stock_mode="Bulk",
        instance_kind="Lot",
        markings="",
        category="Connectors",
        category_path=["root", "electromechanical", "connectors"],
    ),
    _row(
        uid="01ARZ3NDEKTSV4RRFFQ69G5FB5",
        sku="CON-JST-XH-4P",
        name="Connector JST-XH 4-Pin",
        description="JST XH series, 4-pin header, 2.54 mm pitch, top entry",
        part_number="B4B-XH-A",
        stock="36",
        status="Active",
        footprint="TH-2.54",
        stock_mode="Bulk",
        instance_kind="Lot",
        markings="",
        category="Connectors",
        category_path=["root", "electromechanical", "connectors"],
    ),
    _row(
        uid="01ARZ3NDEKTSV4RRFFQ69G5FB6",
        sku="MECH-M3-12",
        name="Screw M3 × 12 Pan Head",
        description="M3 × 12 mm pan head Phillips machine screw, stainless A2",
        part_number="M3X12-PAN-A2",
        stock="900",
        status="Active",
        footprint="M3",
        stock_mode="Bulk",
        instance_kind="Lot",
        markings="",
        category="Mechanical",
        category_path=["root", "mechanical"],
    ),
]

CATEGORY_TREE: list[dict[str, Any]] = [
    {
        "id": "root",
        "name": "All Categories",
        "children": [
            {
                "id": "passive",
                "name": "Passive",
                "children": [
                    {"id": "resistors", "name": "Resistors", "children": []},
                    {"id": "capacitors", "name": "Capacitors", "children": []},
                    {"id": "inductors", "name": "Inductors", "children": []},
                ],
            },
            {
                "id": "active",
                "name": "Active",
                "children": [
                    {
                        "id": "semiconductors",
                        "name": "Semiconductors",
                        "children": [
                            {
                                "id": "transistors",
                                "name": "Transistors",
                                "children": [
                                    {"id": "mosfet", "name": "MOSFET", "children": []},
                                    {"id": "bjt", "name": "BJT", "children": []},
                                ],
                            },
                            {"id": "diodes", "name": "Diodes", "children": []},
                            {"id": "ics", "name": "Integrated Circuits", "children": []},
                        ],
                    }
                ],
            },
            {
                "id": "electromechanical",
                "name": "Electromechanical",
                "children": [
                    {"id": "connectors", "name": "Connectors", "children": []},
                    {"id": "switches", "name": "Switches", "children": []},
                ],
            },
            {"id": "mechanical", "name": "Mechanical", "children": []},
        ],
    }
]

INSPECTOR_TABS: list[str] = [
    "Part Details",
    "Stock History",
    "Parameters",
    "Vendors",
    "Alternates",
    "BOM/Where-used",
]
