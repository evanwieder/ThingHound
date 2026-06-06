export const displayColumns = [
  { key: "hero", title: "Hero" },
  { key: "name", title: "Name" },
  { key: "category", title: "Category" },
  { key: "value", title: "Value" },
  { key: "onHand", title: "On Hand" }
];

export const columnMappings = {
  resistor: { hero: "resistance", value: "resistance_display" },
  capacitor: { hero: "capacitance", value: "capacitance_display" },
  connector: { hero: null, value: "pitch_display" },
  mechanical: { hero: null, value: "size_display" }
};

export const gridRows = [
  {
    id: "018f49c4-8bca-7f4b-90f0-1ed20d53a001",
    type: "resistor",
    thumbnail: "",
    name: "1k Resistor",
    category: "Resistors",
    hero: "1 kΩ",
    value: "1000",
    resistance: "1000",
    resistance_display: "1 kΩ",
    onHand: "250"
  },
  {
    id: "018f49c4-8bca-7f4b-90f0-1ed20d53a002",
    type: "capacitor",
    thumbnail: "",
    name: "100nF Capacitor",
    category: "Capacitors",
    hero: "100 nF",
    value: "100nF",
    capacitance: "100",
    capacitance_display: "100 nF",
    onHand: "500"
  },
  {
    id: "018f49c4-8bca-7f4b-90f0-1ed20d53a003",
    type: "connector",
    thumbnail: "",
    name: "JST-XH 2P",
    category: "Connectors",
    hero: "",
    value: "2.54 mm",
    pitch_display: "2.54 mm",
    onHand: "48"
  },
  {
    id: "018f49c4-8bca-7f4b-90f0-1ed20d53a004",
    type: "mechanical",
    thumbnail: "",
    name: "M3 Screw",
    category: "Mechanical",
    hero: "",
    value: "12 mm",
    size_display: "M3 x 12",
    onHand: "900"
  }
];

export const categoryTree = [
  {
    id: "root",
    name: "All Categories",
    children: [
      { id: "resistors", name: "Resistors", children: [] },
      { id: "capacitors", name: "Capacitors", children: [] },
      { id: "connectors", name: "Connectors", children: [] },
      { id: "mechanical", name: "Mechanical", children: [] }
    ]
  }
];

export const inspectorTabs = [
  "Attributes",
  "Stock & Events",
  "Instances",
  "Vendors",
  "Alternates",
  "BOM/Where-used",
  "Simulation"
];
