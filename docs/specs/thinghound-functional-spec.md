# ThingHound — Functional Specification

**Date:** 2026-06-03
**Companion documents:** `thinghound-data-model.md`, `thinghound-architecture.md`

---

## 1. Overview & Philosophy

ThingHound is a local-first, sync-ready desktop application for hobbyist and small-team component catalog management, inventory tracking, BOM/build management, and procurement. It is a dense, configurable, PartKeepr-class tool that runs as a native desktop application using an OS-native webview — not a bundled browser, not a SaaS tab.

### 1.1 Core Principles

- **Local-first, sync-ready.** A single SQLite file on disk is the source of truth. Multi-device sync is a first-class design concern, implemented via CRDTs (cr-sqlite) so two devices can edit offline and merge without a server.
- **Single-user now, multi-user-ready.** Ships single-user with no login. Every synced and logged row carries a user reference from day one so multi-user can be added later without migrating historical data. Privilege enforcement is deferred; attribution recording is not.
- **Event-based inventory.** No mutable stock quantity. Quantity on hand is derived from an immutable, append-only event log. Append-only logs merge trivially under sync.
- **Exact numeric storage — no REAL anywhere.** Money is stored as integer minor units plus currency. Dimensional values use a dual representation: `value_scaled INTEGER` (base value × 10^scale, indexed for sort and range) and `value_exact TEXT` (canonical exact decimal for display, math, and equality). Floating-point is never used for any value or quantity.
- **Hand-written, parameterized SQL.** No ORM. SQL lives in aggregate mappers; no SQL appears in service, domain, or UI code.
- **Schema is data.** Categories, attribute definitions, unit dimensions, and grid configurations live in the database and are managed through the application. No hardcoded schemas.
- **Referential integrity is relational.** Relationships are junction tables, not arrays of IDs in JSON. JSON is reserved for genuine free-form or raw capture.

### 1.2 Platform Targets

Windows, macOS, Linux. Single install; no external server required for core use.

### 1.3 Non-Goals

- Not a multi-tenant SaaS. Sync is peer/personal multi-device.
- Not an EDA tool. Imports and exports simulation models; does not draw schematics.
- RBAC enforcement is out of scope for v1; the data model accommodates it.

---

## 2. Definitions / Glossary

| Term | Definition |
|------|------------|
| **Acquisition Cost** | The price paid per unit, recorded on an `ADD` event. Used for costing per the user's chosen costing method (average, FIFO, etc.). |
| **Attribute Category** | A user-defined grouping of attribute definitions (e.g., Electrical, Physical, Mechanical, Thermal). Purely organizational — attributes with the same name in different attribute categories are distinct entities with independent types, units, and scales. |
| **Attribute Definition** | A named, typed, measurable property within one attribute category. Identity is `(name, attribute_category)`. |
| **Attribute Set** | The set of attribute definitions assigned to a category, with per-attribute settings (required flag, sort order, default value). Settings inherit down the category tree; values never inherit. Prepopulates the item entry UI but does not hard-constrain which attributes an item may carry. |
| **Attribute Type** | The kind of value an attribute holds. Stored as a code referencing the `value_type` code table: `N`=Numeric (exact decimal with units), `I`=Integer (whole number only), `S`=String, `E`=Enum (from a defined choice set), `B`=Boolean, `U`=URL, `F`=File, `C`=Composite (multiple named components). Integer and Numeric are distinct — some attributes only permit whole-number values. |
| **Attribution** | Every CRR row carries `created_by_user_id` and `updated_by_user_id`; every LOG row carries `user_id`. Recorded from day one so multi-user history is preserved without migration. |
| **Audit Log** | Append-only record of changes to mutable CRR rows. Off by default in single-user mode; enabled when a second user is added. |
| **Availability Status** | Current stock state of a vendor offer: `IN_STOCK`, `OUT_OF_STOCK`, `BACKORDER`, `LEAD_TIME`, `DISCONTINUED`, `UNKNOWN`. |
| **Base Unit** | The canonical unit of a Unit Dimension (e.g., `ohm`, `gram`, `metre`). All values are normalized to the base unit for storage. |
| **Base Value** | A value normalized to its dimension's base unit, stored as `value_scaled` (INTEGER = base × 10^scale, indexed) and `value_exact` (TEXT, exact decimal). No `REAL`. |
| **BOM** | Bill of Materials: a named, revisioned list of item lines defining what is needed to produce something. |
| **BOM Line** | One item requirement within a BOM revision: item, quantity, unit, optional reference designators, do-not-populate flag. |
| **BOM Revision** | An immutable-once-released version of a BOM. States: `DRAFT` → `RELEASED` → `OBSOLETE`. |
| **Build** | An act of consuming a BOM revision's quantities from stock, linked to a project, optionally producing a stockable assembly. |
| **Buildable Quantity** | The maximum number of a BOM revision producible from current stock, accounting for substitutes and lifecycle warnings. |
| **Catalog Item** | The abstract part definition — the orderable, reusable entity identified by a unique SKU. |
| **Catalog Value** | An attribute value on the item itself, representing the nominal or specified characteristic. Carries provenance. |
| **Column Mapping** | A per-category binding of a Display Column to a mapping target: a direct attribute value, composite component, instance measurement aggregate, built-in item field, or a display formula. |
| **Computed Attribute** | An attribute whose value is derived at runtime by a formula over other attributes. Stored with `provenance = COMPUTED`. A dependency graph drives recomputation when inputs change. |
| **CRR** | Conflict-free Replicated Relation — a table managed by cr-sqlite for sync. Column-level last-writer-wins merge. |
| **Costing Method** | A user-level setting governing how acquisition cost is assigned to consumption events (e.g., weighted average, FIFO). |
| **Device** | A local installation of ThingHound. Each device has its own `device_id` and local-only settings. User identity is distinct from device identity. |
| **Dimension-Wide Search** | A search targeting all attributes sharing a dimension (e.g., all tolerance attributes regardless of unit), converting the threshold to base units and applying per-attribute scaling. |
| **Display Column** | A global, user-defined, named grid column slot shared across all categories. Count and names are user-configurable. |
| **Display Formula** | An expression on a column mapping that computes a display value from item-derivable variables: attribute values, built-in fields, inventory quantities, and pricing data. Evaluated per row at render time; result is not stored. |
| **Display Profile** | Per-category Jinja2 name template that renders an item's display name from its attribute values. |
| **Display Unit** | The unit chosen for rendering a value (e.g., `kΩ`). Sort and range always operate on `value_scaled`; display uses `value_raw` / `display_unit`. |
| **Event** | An immutable inventory fact appended to the log. Types: `ADD`, `CONSUME`, `MOVE`, `INDIVIDUATE`, `ADJUST`, `WASTE`, `LOST`. |
| **Filter Predicate Tree** | The AND/OR structure of a parametric search. Leaves target attributes, built-in fields, or instance measurement aggregates. Savable as JSON in a Grid Configuration. |
| **FX Rate** | An exchange rate from a foreign currency to the home currency on a specific date. |
| **Grid Configuration** | A named, savable grid layout: selected visible columns, order, widths, grouping levels, sort, and saved filters. Scoped globally or to a specific category. |
| **HLC** | Hybrid Logical Clock. A causal timestamp on every event ensuring deterministic ordering across devices with clock skew. |
| **Home Currency** | The user's base currency into which all multi-currency roll-ups are converted. |
| **Hybrid Stock** | An item simultaneously holding an anonymous bulk pool and zero or more tracked instances. On-hand = bulk pool + Σ instance quantities. |
| **Individuate** | Promotes N units from an item's bulk pool into N tracked instances at the same location. Net zero. |
| **Instance / Lot** | A physical unit (`SERIAL`, qty 1) or batch (`LOT`, qty ≥ 1) tracked individually. |
| **Instance Display Mode** | Per grid configuration: `AGGREGATED` (one row per item, combined on-hand, instance measurements as aggregates) or `EXPANDED` (individuated members as child rows). |
| **Instance Measurement** | An attribute value recorded against a specific tracked instance. Append-only; current value is the latest by `(measured_at, hlc, id)`. |
| **Kitting** | Assembling the required parts for a build, consuming from stock atomically. |
| **Lifecycle Status** | Catalog status: `ACTIVE`, `NRND` (not recommended for new designs), `OBSOLETE`, `UNKNOWN`. Drives warnings in BOMs and procurement. |
| **LOCAL** | Device-only table, never synced. Derived and cached data. Rebuilt from CRR/LOG sources after a sync merge. |
| **Location** | A node in the physical storage hierarchy. Types: `STORAGE` (nested physical locations), `WASTE` (terminal), `LOST` (terminal). Hierarchy traversed via recursive CTEs on `parent_id`. |
| **LOG** | Append-only CRR. Immutable once written; new facts are new rows. |
| **Markings** | Free-text description of the physical identification marks on a part (printed text, resistor color bands, maker's marks). FTS-searchable for reverse lookup. |
| **Money** | Stored as integer minor units plus an ISO 4217 currency code. Never a float. |
| **Name Template** | A Jinja2 expression per category rendering an item's display name from its attribute values. |
| **Offer History** | An append-only log of point-in-time snapshots of a vendor offer's availability and representative price. |
| **Parametric Search** | A compound filter where each leaf targets an attribute or composite component with a numeric range, converted to base units and evaluated against `value_scaled`. Leaves combine as AND/OR predicates. |
| **Parent Item** | A non-stocked item that groups child variant items (bins, packages, equivalent configurations). Enables navigation and substitution across the variant family. |
| **Permission** | A named capability checked at the service layer (e.g., `item.edit`, `inventory.consume`). Vocabulary defined now; enforcement deferred to a later phase. |
| **Polyhierarchy** | An item may belong to multiple categories; exactly one is its primary category. |
| **Post-Merge Repair** | A deterministic function run after every sync merge to validate referential integrity and quarantine dangling references. Pure function of merged state; every replica computes identical repairs. |
| **Price Break** | A quantity-tiered unit price within a vendor offer. |
| **Primary Category** | The single category used to resolve an item's column mappings and render its canonical name when no specific category context is active. Stored as a single cell on the item. |
| **Project** | A named entity that consumption events are linked to. Distinct from the physical storage location hierarchy. |
| **Provenance** | The recorded source of an attribute value: `TEMPLATE`, `NOMINAL`, `USER`, `MEASURED`, `OBSERVED`, `TESTED`, `DATASHEET_EXTRACTED`, `COMPUTED`. |
| **Reference Designator** | The circuit position identifier for a BOM line (e.g., R1, C4, U12). Optional. |
| **Replacement Cost** | The lowest current unit price across active vendor offers, converted to home currency. |
| **Role** | A named permission bundle assigned to a user. Defined now; enforcement deferred. |
| **Scale** | A per-attribute-definition integer: the number of decimal places kept when encoding a base-unit value as a scaled integer. Chosen per attribute for practical resolution and range within signed int64. |
| **Shortage** | The per-line difference between required and available quantity when buildable quantity is below the target. |
| **Stock Mode** | Per-item receipt default: `BULK` (receipts go to the anonymous pool) or `INSTANCE` (receipts create tracked instances). Not a hard wall. |
| **Substitute** | An item allowed as a per-line BOM replacement. Seeded from the item's equivalence/alternate relationships but overridable per line. |
| **Tombstone** | A soft-delete marker (`deleted_at`) on CRR rows so deletions propagate correctly under sync. |
| **Unit Dimension** | A measurable domain (Resistance, Mass, Length) with a defined base unit and associated multipliers and prefix sets. |
| **Unit Multiplier** | A named conversion factor within a Unit Dimension. Carries a primary name, optional alternate names, a symbol, optional plural forms, and an exact decimal factor. No float. |
| **User** | A person who interacts with the application. v1 seeds one local user as the default for all writes. |
| **Vendor** | A distributor or supplier. Distinct from manufacturer. |
| **Vendor Offer** | A vendor's listing for a specific item: vendor SKU, URL, currency, availability, MOQ, order multiple, package type. One offer per `(item, vendor)` pairing. |
| **Where-Used** | The reverse BOM query: given an item, which BOM revisions and builds reference it. |

---

## 3. Functional Requirements

### 3.1 Category Management

- Categories form a single-parent tree. Ancestry queries use recursive CTEs on indexed `parent_id`; no closure table.
- Items link to multiple categories (polyhierarchy); exactly one is the item's primary category, stored as a single cell on the item to remain unique under sync merges.
- CRUD with drag-and-drop reparenting (parent_id update; ancestry cache in AppRegistry refreshed on change).
- Deleting a category requires confirmation and reassignment of children and items. Delete is a soft-delete tombstone.

### 3.2 Attribute Schema System

- **Attribute categories** are user-defined groupings (e.g., Electrical, Physical, Thermal). Each attribute definition belongs to exactly one attribute category. Two attributes with the same name in different attribute categories are distinct entities with independent types, units, and scales.
- **Attribute definitions** carry: name, attribute category, value type, optional unit dimension, scale (per attribute, not per dimension), preferred display unit, optional constraints, optional composite display template.
- **Value types** (codes from the `value_type` reference table): `N`=Numeric (exact decimal, supports units and scale), `I`=Integer (whole number only, supports units and scale), `S`=String, `E`=Enum (from a defined choice set via `attribute_enum_value`), `B`=Boolean, `U`=URL, `F`=File, `C`=Composite. Integer and Numeric are distinct types — an attribute typed Integer rejects fractional input.
- **Composite attributes** hold named components, each itself a typed value with its own unit dimension, scale, and display unit. Components are individually stored, indexed, sortable, and filterable.
- **Category attribute sets** define which attribute definitions are relevant for a category with per-attribute settings: required flag, sort order, default value. These settings inherit down the category tree; values never inherit.
- An item missing a required category attribute is flagged as incomplete but is not prevented from saving. Required is a UI hint and validation state, not a hard data constraint.
- A user may set any attribute definition on an item regardless of whether it appears in any of the item's categories' attribute sets. The category attribute set prepopulates the entry form; it does not limit what can be recorded.
- Inheritance is computed at runtime from the category tree (recursive CTE); no stored `is_inherited` flag.
- A child category binding for the same attribute overrides `is_required`, `sort_order`, and `default_value`.
- For a multi-category item, the resolved attribute set is the union of all linked categories' resolved sets. An attribute is required for the item iff required in the primary category's resolved set.

### 3.3 Unit & Dimension System

- **Unit dimensions** define a base unit and whether SI prefixes are enabled.
- **Prefix sets** are user-extensible. Shipped sets include SI and Binary/IEC. Each attribute definition specifies which prefixes from its dimension's set are available for entry, limiting the dropdown to the relevant range (e.g., Resistance exposes only m, none, k, M, G).
- **Unit multipliers** carry: primary name, optional alternate names (JSON array), symbol, optional plural forms, and an exact decimal factor string. No float.
- **Scale** is defined per attribute definition, not per dimension. This allows attributes measuring the same dimension to use different scales for different practical ranges (e.g., `Current` at scale 12 for pA resolution, `Current-High` at scale 3 for industrial range), while keeping values directly comparable within a single attribute via its indexed `value_scaled`.
- Input accepts: decimals, vulgar fractions (½, ¼), slash fractions (1/2), mixed numbers (1-1/16, 1 1/16), SI-prefixed and custom units.
- A preprocessor normalizes the numeric token; Pint parses and converts to base units using exact rationals — no float in the conversion path.
- Storage: `value_scaled INTEGER` (base × 10^scale, indexed for sort/filter/range) + `value_exact TEXT` (canonical exact decimal, source of truth for display and equality).
- Display: values render in their original entry form (`value_raw`, `display_unit`) by default. A per-view normalize option renders from `value_exact` in a chosen unit.
- Sort and range always use `value_scaled`. Equality and arithmetic always use `value_exact`.
- Money: integer minor units + ISO 4217 currency code. Never float.

### 3.4 Catalog Item Identity

- Every item has a mandatory, unique SKU — the stable internal key.
- **MPN** (Manufacturer Part Number): `(manufacturer_id, part_number)` — unique where both are present.
- **GPN** (Generic/House Part Number): `(NULL manufacturer, part_number)` — unique where manufacturer is absent.
- **No part number:** valid; identified by SKU alone.
- Uniqueness on natural keys (SKU, MPN, GPN) is enforced locally at write time by the service layer. Under sync, collisions are detected by the post-merge integrity check and quarantined for user resolution — UNIQUE constraints are not present on CRR tables.
- **Parent items** are non-stocked grouping constructs for variant families. Child items may vary by bin (different attribute ranges), package/footprint, or both. Equivalence relationships between families from different manufacturers (e.g., LSK170 ↔ 2SK170) are captured via item relationships at the family or specific-variant level.
- Lifecycle status: `ACTIVE`, `NRND`, `OBSOLETE`, `UNKNOWN`.
- Stock mode: `BULK` or `INSTANCE` (receipt default, not a hard wall).
- Optional: stock unit dimension (for continuous quantities like wire by metre or solder by gram), instance kind (`SERIAL` / `LOT`), reorder point, reorder quantity, safety stock, description, markings, nominal footprint, barcode.

### 3.5 Attribute Values & Provenance

Two independent value layers per item:

**Catalog layer** (`item_attribute_value`) — nominal/specified values:
- Harmonized columns: `value_scaled`, `value_exact`, `value_text` (for string/enum/boolean/url), `display_unit`, `value_raw_json`, `provenance`, `provenance_context_json`.
- Tolerance on a value is represented as a separate attribute definition in the appropriate dimension (e.g., "Resistance Tolerance" in the Resistance dimension for absolute ±Ω tolerance, or "Tolerance" in a dimensionless Ratio dimension for percentage/ppm tolerance). No dedicated tolerance fields on the value row.

**Instance measurement layer** (`instance_measurement`) — append-only measured values:
- Same harmonized columns plus `instrument`, `measured_at`, `hlc`, `notes`.
- Current measured value = latest by `(measured_at, hlc, id)` — deterministic and merge-stable.

**Composite values** are stored as one row per component in `item_attribute_component_value`, each with the same harmonized columns. The composite renders via its attribute's display template.

**Auto-populate:** when creating an item by specifying a vendor SKU or MPN that matches an existing item, attributes are offered for auto-population from that item's catalog values with `provenance = TEMPLATE`.

### 3.6 Event-Based Inventory

No mutable stock field. Stock is derived from the immutable, append-only event log.

| Event | Meaning | Qty sign |
|-------|---------|----------|
| `ADD` | Receipt of stock | > 0 |
| `CONSUME` | Use for a project or bench | < 0 |
| `WASTE` | Damaged / expired / scrapped | < 0 |
| `LOST` | Unaccounted | < 0 |
| `MOVE` | Transfer between storage locations | net 0 |
| `INDIVIDUATE` | Promote N bulk units → N tracked instances | net 0 |
| `ADJUST` | Audit correction; reason required | ± |

- `CONSUME` events carry: `qty`, `unit_cost_at_purchase` (per the costing method), `unit_replacement_cost` (current market price at event time), and `project_id`.
- `WASTE` and `LOST` remove items from the inventory count. No location tracking for wasted or lost items.
- `MOVE` requires a source and destination storage location.
- `INDIVIDUATE` emits a group of legs (one bulk −N, one +1 per instance) sharing an `individuation_group_id`, netting zero.
- `ADJUST` requires a reason. Can be positive or negative.
- All events carry `effective_date`, `hlc`, `user_id`. Replay order: `(effective_date, hlc, id)` — deterministic under back-dating, ties, and sync merges.
- Events are immutable (insert-only) — ideal for CRDT merge.
- Money fields: minor units + currency.

### 3.7 Stock Modes, Units, Instances & Lots

- **`stock_mode`** is the receipt default: `BULK` (receipts go to the anonymous pool) or `INSTANCE` (receipts create tracked units). An item may hold both simultaneously (hybrid stock).
- **`stock_unit_dimension_id`**: if NULL, quantities are dimensionless counts; if set, quantities are a continuous measure in that dimension's base unit (e.g., wire in metres).
- **`instance_kind`** (`SERIAL` / `LOT`): the kind of instance created when receiving as instance or individuating.
- **Individuation:** takes N units from the bulk pool at a location and creates N instances with labels, optional barcodes, location, and optional initial measurements. Emits a net-zero INDIVIDUATE event group. On-hand is unchanged; only the pool/instance split changes.
- **Merge-to-bulk:** the inverse — reabsorbs an instance's remaining quantity into the pool.
- **On-hand = bulk pool + Σ instance quantities.** Individuated instances remain part of their parent item's stock and nominal identity.
- Per-location balances are derived from event `from_location_id` / `to_location_id` and `instance_id`.

### 3.8 BOM & Build Management

- BOMs are named; an optional `produces_item_id` marks a BOM that builds a stockable assembly (enabling nested BOMs).
- Revisions follow `DRAFT` → `RELEASED` → `OBSOLETE`. Released revisions are immutable; changes require a new revision.
- BOM lines carry `item_id` (nullable for unresolved/imported lines), `qty_per`, `qty_unit`, optional `refdes`, `do_not_populate`, notes.
- **Substitutes:** per-line allowed substitutes (`bom_line_substitute`), default-seeded from the item's global ranked relationships and overridable per line.
- **Shortage / Buildable analysis:** for a revision and target quantity, compute per-line required vs. available (honoring substitutes and lifecycle warnings), the buildable quantity, and the shortfall.
- **Build:** records `CONSUME` events linked via `build_id` against a project atomically. Optionally emits an `ADD` for `produces_item_id`. Insufficient stock either blocks or allows back-order per user choice.
- **Where-used:** given an item, list BOM revisions and builds that use it.
- **Import:** generic CSV and KiCad/Altium BOM formats with column mapping; unresolved lines stage for matching.

### 3.9 Vendors, Offers & Pricing

- Vendors are distinct from manufacturers.
- An item may have multiple offers — one per `(item, vendor)` — each with its own vendor SKU, URL, currency, and price breaks.
- Offers carry: `currency`, `is_active`, `moq`, `order_multiple`, `package`, `availability_status`, optional `qty_available`, `lead_time_days`, `last_checked`.
- **Offer history** (`offer_history`) appends a snapshot on each availability/price check. Answers trend questions: "Is this getting harder to source or more expensive?"
- Price breaks keyed on quantity with `qty_min` / `qty_max` as scaled integers.
- **Replacement cost** = lowest `qty_min`-tier unit price across active offers, converted to home currency via FX rate.
- **Acquisition cost** = price paid, recorded on `ADD` events (minor units + currency).
- **Costing method** is a user-level setting governing how acquisition cost is assigned to consumption events (weighted average, FIFO, etc.).
- Optional shipping/tax allocation across receipt lines for true landed cost.

### 3.10 Procurement / Shopping List

- Generate a buy-list from low-stock items (below reorder point) and BOM shortages.
- Group by vendor; suggest the cheapest offer honoring MOQ, order multiple, price breaks, and current availability. Flag out-of-stock/discontinued and surface ranked alternatives.
- Show estimated cost in home currency.
- Export to CSV / vendor cart formats. A committed purchase later reconciles against invoice import.

### 3.11 Invoice & BOM Import / Reconciliation

Shared pipeline: **Ingest → Match → Reconcile → Commit**

1. **Ingest:** parse CSV/Excel into `invoice` / `invoice_line` (status `PENDING`). Saveable column-mapping templates per vendor; auto-detect template by header signature.
2. **Auto-match:** P1 exact `vendor_sku`; P2 `part_number` + `manufacturer`; P3 fuzzy FTS5 description (trigram, similarity threshold); P4 → `NEW`.
3. **Reconcile:** grid of matched/ambiguous/new/ignored lines; inline creation pre-filled from line data.
4. **Commit:** atomic creation of items/offers/price-breaks/`ADD` events linked to `invoice_line_id`. New items seed an offer with a `qty_min=1` break at the invoice unit cost. Duplicate-invoice warning on `(vendor_id, invoice_number, invoice_date)`. Shipping/tax lines `IGNORED` or optionally allocated.

### 3.12 Computed Attributes

- `attribute_formula`: target attribute, expression, applicable categories (relational `formula_category`), enabled flag.
- `formula_input` maps each expression symbol → `attribute_id` + `layer` (`CATALOG` / `INSTANCE` / `EITHER`) so symbols resolve deterministically.
- **Engine:** `simpleeval` with an allowlisted operator set (`+ - * / ** sqrt log exp abs min max`), Pint-aware unit propagation, hardened evaluator.
- Evaluate when all mapped inputs are non-NULL. Output normalized through the target dimension. Stored with `provenance = COMPUTED`.
- A dependency graph drives a topological recompute cascade that also marks rendered names and FTS rows stale. Cycles rejected at save.
- User edits to a computed value either break the formula link (`provenance → USER`) or are rejected per user choice.

### 3.13 Display Columns, Column Mappings & Grid Configurations

- **Display Columns are global and user-defined.** The user creates an ordered, named set of grid column slots shared across all categories. A column may be bound to a universal built-in item field (`item_field_key`: `sku`, `name`, `description`, `lifecycle_status`, `on_hand`, `instance_count`, `markings`, etc.) that resolves identically for every item with no per-category mapping.
- **Column Mappings are per-category.** For each category, the user maps each Display Column to:
  - A direct attribute value
  - A specific composite component value
  - An instance measurement aggregate (`MIN` / `MAX` / `AVG` / `COUNT` / `RANGE`)
  - A built-in item field
  - A **display formula** combining any item-derivable variables (attribute values, item fields, inventory quantities, pricing data; e.g., `weight_attribute × on_hand_count`)
  - Nothing (cell renders blank)
- A mapping targets either the catalog layer or an instance measurement aggregate (`source_layer`).
- **Heterogeneous rendering.** Each row resolves each Display Column through its item's primary category Column Mapping, allowing a mixed grid (resistors, capacitors, mechanical parts) to align under shared columns.
- **Sorting and filtering** on a Display Column operate on the resolved attribute's indexed `value_scaled` (or `value_text` for non-numeric). Across mixed categories a numeric sort compares raw base values that may be in different dimensions — the grid indicates mixed-dimension columns.
- **Grid Configurations** are savable named layouts: selected visible columns, column order, widths, grouping levels, sort, and saved filters (predicate tree JSON). Scoped globally or to a specific category. One per scope may be marked default via a single-cell reference on the item or in `app_setting`.
- **Instance Display Mode** is per-configuration: `AGGREGATED` (default — one row per item, combined on-hand, aggregate columns for instance measurements) or `EXPANDED` (individuated members as child tree rows under their parent item).
- **Display Profile** (per category) holds only the name template. Grid layout and defaults live in Grid Configurations.

### 3.14 Search, Filter & Tags

- **FTS5** (trigram tokenizer) over canonical names, descriptions, SKUs, part numbers, markings, reference designators, and tags. Each dimensional attribute value is indexed in both its as-defined form (`1 kΩ`) and its canonical base-unit form (`1000 ohm`) — search matches whichever the user types.
- **Range/equality filters** entered in any unit and numeric form (fraction-aware); converted to base units and queried on `value_scaled`. Non-numeric filters use `value_text`.
- **Parametric search** builds an AND/OR predicate tree whose leaves target any attribute, composite component, built-in field, or instance measurement aggregate — whether or not it is a visible column. Each numeric leaf is unit/fraction-converted and evaluated on the appropriate indexed `value_scaled`.
- **Dimension-wide search** targets all attributes sharing a dimension (e.g., all tolerance attributes), converting the user's threshold to base units and applying per-attribute `value_scaled` thresholds. Enables "tolerance < 1%" to return results regardless of whether tolerance is stored as % or ppm.
- The unit-aware quick-search bar parses `magnitude+unit` tokens and routes to `value_scaled` lookup; plain tokens hit FTS.
- **Tags** via `tag` / `item_tag`.
- Saved filter predicate trees live in Grid Configurations.

### 3.15 Asset Management

- **Polymorphic attachments** (`attachment`): `owner_type` (`ITEM` / `INSTANCE` / `VENDOR` / `MANUFACTURER`), `owner_id`, `role` (`PHOTO` / `DATASHEET` / `DOCUMENT` / `MODEL` / `OTHER`), `file_path`, `mime_type`, `sha256`, `caption`, `sort_order`, `page_count`.
- Files stored under the managed user-data directory. Relative paths in the database. Thumbnails generated lazily (Pillow) and cached in a LOCAL table.
- Barcode/QR code fields on items, instances, and locations for future label generation and scanning.

### 3.16 Datasheet Extraction (Phase 3)

- PDF datasheets are attachments with `role = DATASHEET`. Extraction candidates land in `datasheet_extraction` with page number, bounding-box columns, extracted text, dual base value, confidence, and status.
- Review UI accepts/rejects. Accepted values write to the catalog with `provenance = DATASHEET_EXTRACTED` and full `provenance_context` (PDF sha256, page, bbox).

### 3.17 LTspice Model Templating

- `ltspice_template` (MODEL / SUBCKT / SYMBOL / PARAMS) with Jinja2 body.
- Parameters mapped relationally via `ltspice_template_param(var_name → attribute_id)`.
- Custom `ltspice_unit` Jinja2 filter (µ → `u`, MΩ → `Meg`, etc.).
- Per-item template selection or `ltspice_override_text`. Cached `ltspice_generated` invalidated by the recompute cascade.

### 3.18 Settings, Preferences & Onboarding

- **`app_setting`** (synced CRR): home currency, default display units per dimension, default grid configuration, and other settings that should follow the user across devices.
- **`device_setting`** (LOCAL): window geometry, last-opened path, theme, device ID.
- **Onboarding:** first-run wizard offers seed packs (bundled unit dimensions, common electronics attribute definitions, starter category tree) and a guided first-part creation path. Schema packs are importable/exportable for community sharing. PartKeepr importer maps categories, parameters, parts, and stock.

### 3.19 Alternatives, Replacements & Lifecycle

- **Lifecycle.** Each item's `lifecycle_status` marks discontinuation. `OBSOLETE` / `NRND` raise warnings in BOMs and procurement.
- **Alternatives are a directed, ranked graph** (`item_relationship`). An item may have multiple alternatives ordered by `rank`:
  - `EXACT_REPLACEMENT` — drop-in; safe to substitute automatically.
  - `ALTERNATE` — non-exact; applicable with conditions/notes.
  - `EQUIVALENT` — interchangeable both ways (`symmetric = true`).
  - `ALTERNATE_MPN` — same physical part under a different MPN (cross-reference).
- Relationships exist at any level in the parent-child hierarchy — family-to-family or specific variant-to-variant — wherever the equivalence actually holds.
- **Discontinued workflow.** When an item is `OBSOLETE` / `NRND`, its detail view, BOM lines, and the procurement list surface its ranked replacements and steer toward the preferred `EXACT_REPLACEMENT`. BOM-line substitutes default-seed from this graph and are overridable per line.

---

## 4. UI/UX Specifications

### 4.1 Main Layout

Left category tree (search, drag-reparent) · centre dense grid (dynamic columns per active category or global view) · right context inspector · status bar (counts, selection summary, last sync time and status).

### 4.2 Add-Item Wizard

Category → Manufacturer/Series → Attributes (compound `[magnitude][unit▼]` inputs for numeric; labeled sub-form for composite attributes) → Identity (SKU, MPN/GPN, lifecycle, description, markings, tags, footprint, stock mode/unit, parent item) → Initial Stock (`ADD`; if instance/lot: serial/lot grid with quantities, vendor, price-break tier). Required-field enforcement from the primary category's resolved attribute set (incomplete flag).

### 4.3 Inspector Panel

Tabs: **Catalog** (nominal attributes by attribute category, lifecycle, markings, tags; computed attributes show a calculator icon; incomplete-flag indicator for missing required attributes) · **Stock & Events** (ledger with per-location balances split by bulk pool vs instances; Adjust, Waste, Lost, Individuate actions; invoice links; costing summary) · **Instances** (lots/serials with remaining qty, measured-value history, location, assign/waste/lost; Individuate selected bulk units) · **Vendors** (per-vendor offers with SKU/URL, MOQ/multiple/package, price-break tiers, availability, price+availability history) · **Alternates** (ranked replacements and cross-refs; preferred replacement highlighted for OBSOLETE/NRND items) · **BOM/Where-used** · **Simulation** (LTspice template, preview, override, export).

### 4.4 Grid Behaviour

Powered by Tabulator. Single layout from global Display Columns; each row resolves columns through its item's primary-category Column Mapping. The hero column is pinned/bold. Dimensional columns display converted values; sort/filter operate on `value_scaled` or `value_text`. Native tree/grouping (instance expansion, group-by category or any column), virtualisation for large datasets, inline editing with typed editors (unit spinners with per-attribute prefix range, enum dropdowns). Multi-select bulk actions (move, tag, edit, delete) with undo/redo. Instance aggregation: by default one row per item; EXPANDED mode reveals individuated members as child rows.

### 4.5 Search & Filters

Global search bar (`/`). A parametric filter bar where the user adds filter chips — each `attribute · operator · value+unit` (e.g., `Resistance 1k–1.5k Ω`, `Power ≥ ¼ W`, `Length ≤ 6 mm`) — that AND together with optional OR groups. Chips may target any attribute, built-in field, or instance aggregate. Each bound is unit/fraction-converted to base units. A configuration switcher selects among saved Grid Configurations; the current layout can be saved or updated.

### 4.6 BOM & Build Workspace

Create/import BOMs; edit lines with optional refdes and substitutes; shortage view (per-line required/available/short, buildable quantity, estimated cost); Build action with project selection and shortage handling; where-used view.

### 4.7 Procurement Workspace

Auto-assembled shopping list (low-stock + BOM shortages), grouped by vendor with cheapest-offer/MOQ-aware suggestions and availability indicators; export; later reconciled by invoice import.

### 4.8 Invoice / BOM Import

Initiate via menu or drag-drop; first-time column mapping with saveable, auto-detected templates; reconcile grid (matched/ambiguous/new/ignored) with inline creation; atomic commit summary.

### 4.9 Measurement Entry

Select instance → Add Measurement (attribute dropdown from resolved schema), shows nominal alongside input, instrument, date; writes to `instance_measurement`; out-of-tolerance indication if a tolerance attribute is present.

### 4.10 Onboarding & Empty State

First-run wizard: pick seed packs (units, attribute categories, attributes, starter categories), optional PartKeepr import, and guided first-part creation.

### 4.11 Validation, Errors, i18n, Accessibility

Consistent inline validation model (bad unit, failed import, constraint violation, incomplete-item indicator). Locale-aware number and unit parsing. Keyboard-first navigation. Accessibility commitments documented per view. Sync conflict queue UI for post-merge quarantined records.

---

## 5. Business Rules & Logic

### 5.1 Series Auto-Populate

On item creation, selecting a series copies `series_attribute_default` values into `item_attribute_value` with `provenance = TEMPLATE` (normalizing dimensional defaults to base units). User-edited fields are not overwritten; `is_editable = false` fields are locked. Disassociating a series retains values but flips `provenance → USER`.

### 5.2 Stock & Quantity Semantics

Quantities are interpreted in the item's stock unit (each vs continuous dimension). Bulk consumption deducts from the anonymous pool; instance/lot consumption references an instance and deducts from its remaining quantity. On-hand = bulk pool + Σ instance quantities. Per-location, per-bucket balances must remain non-negative; the app blocks consumption exceeding available at the source location/bucket (override via `ADJUST` with reason).

### 5.3 Individuation Workflow

Selecting N units from a bulk pool location and choosing "Individuate / Label" atomically: (a) creates N `item_instance` records with labels (`instance_ref`), optional barcodes, location (defaults to source), and optional initial measurements; (b) emits one `INDIVIDUATE` event group — a −N bulk leg plus +1 instance legs sharing an `individuation_group_id` — netting zero. On-hand is unchanged; only the pool/instance split changes. Untouched bulk units stay in the pool with no per-unit records.

### 5.4 Base-Value Write Path

1. Fraction-aware preprocessor normalizes the numeric token (vulgar fractions, slash fractions, mixed numbers, locale separators).
2. Pint parses magnitude+unit, converts to base units via exact rational arithmetic — no float in the conversion path.
3. Store `value_scaled = round(base × 10^scale)` and `value_exact = canonical_decimal(base, scale)`.
4. Preserve the original entry in `value_raw_json` and `display_unit`.

### 5.5 Costing

- Acquisition cost is immutable on `ADD` events (minor units + currency), linked to `invoice_line_id` when available.
- All roll-ups (replacement cost, average landed) computed in home currency via `fx_rate` at the event or quote date.
- Event order for costing replay: `(effective_date, hlc, id)` — deterministic under back-dating, ties, and sync merges.
- The costing method (weighted average, FIFO, etc.) is a user-level setting. It governs how `unit_cost_at_purchase` is assigned to consumption events at write time.
- Optional shipping/tax allocation distributes IGNORED invoice charges across receipt lines.

### 5.6 BOM / Build Rules

- Buildable quantity = `min` over lines of `floor(available_including_subs / qty_per)` for the target quantity. `do_not_populate` lines are excluded. `OBSOLETE` / `NRND` parts raise warnings.
- A build consumes line quantities atomically (preferring primary item, then ranked substitutes) and may emit an `ADD` for `produces_item_id`. Insufficient stock either blocks or records a back-order per user choice.
- Released revisions are immutable; edits require a new revision.

### 5.7 Computed Attribute Rules

Evaluate when all mapped inputs are non-NULL. Resolve symbols via `formula_input`. Propagate units via Pint. Normalize through the target dimension. Store with `provenance = COMPUTED`. Topological recompute cascade refreshes dependents and marks rendered names and FTS rows stale. Cycles rejected at save. User edits to a computed value either break the link (`provenance → USER`) or are rejected.

### 5.8 Polyhierarchy Rendering

The canonical name (primary category's name template) is used wherever there is no active category context (search, BOM, procurement, invoice reconcile), and the primary category's column mappings resolve which attribute fills each Display Column for that item. Within a single category view, that category's profile renders the contextual name.

### 5.9 Deletion & Tombstones

Catalog and config rows are soft-deleted (`deleted_at`) so deletions propagate to other devices under sync. Events are never deleted (append-only). Hard purge is an explicit, local maintenance action outside normal flows.

### 5.10 Incomplete Items

An item is considered incomplete if any attribute marked required by its primary category's resolved attribute set has no value in `item_attribute_value`. Incompleteness is a derived flag surfaced in the UI — it does not prevent saving or syncing.

---

## 6. API / Bridge Contract

Bridge methods are versioned, Pydantic-validated request/response objects. All `BLOB(16)` UUIDv7 identifiers cross the bridge as canonical UUID strings (`8-4-4-4-12` hex). Every scaled integer value is accompanied by its `value_exact` / display form so the UI never performs float math. Errors return a typed envelope `{ code, message, field?, details? }`.

Representative surface:

```
schema.getAttributeCategories() -> AttributeCategory[]
schema.getResolvedSchema(categoryId | itemId) -> AttributeSchema
schema.getDimensions() -> UnitDimension[]

grid.getDisplayColumns() -> DisplayColumn[]
grid.getColumnMappings(categoryId) -> ColumnMapping[]
grid.queryItems(filters, sort, page, categoryScope?) -> { rows, total }
grid.getConfigurations(scope?, categoryId?) -> GridConfiguration[]
grid.saveConfiguration(config) -> GridConfiguration
grid.setDefaultConfiguration(id, scope, categoryId?)

items.create(payload) -> Item
items.update(id, patch) -> Item
items.softDelete(id)
items.getVariants(parentId) -> Item[]

attrs.setValue(itemId, attributeId, rawInput) -> NormalizedValue
attrs.setComponentValue(itemId, attributeId, componentId, rawInput) -> NormalizedValue

inventory.addEvent(event) -> InventoryEvent
inventory.getLedger(itemId) -> InventoryEvent[]
inventory.getBalances(itemId) -> Balance[]
inventory.individuate(itemId, fromLocationId, units[{label, barcode?, toLocationId?, measurements?}]) -> Instance[]
inventory.mergeToBulk(instanceId)

instances.measure(instanceId, attributeId, rawInput, instrument) -> InstanceMeasurement

bom.import(file, mapping) -> BomImportResult
bom.getShortage(revisionId, qty) -> ShortageReport
bom.build(revisionId, qty, projectId) -> BuildResult

procurement.buildList() -> ShoppingList

invoice.import(file) -> InvoiceImportResult
invoice.reconcile(invoiceId, matches[]) -> ReconcileResult
invoice.commit(invoiceId) -> CommitResult

formula.save(def) -> AttributeFormula
formula.recompute(scope)

settings.get(scope, key) -> value
settings.set(scope, key, value)

sync.status() -> { lastMerge, pendingChanges, quarantinedCount }
sync.getQuarantine() -> ConflictRecord[]
sync.resolveConflict(id, resolution)
```

---

## 7. Implementation Roadmap

### Phase 1 — Core Catalog & Inventory
SQLite + FTS5 + cr-sqlite wired from day one; UUIDv7 IDs; migrations runner. Attribute categories; unit dimensions with prefix sets; attribute definitions with per-attribute scale. Category tree (recursive CTE). Item CRUD; parent-child variants; stock modes/units; event-based inventory with HLC; per-location balances. Vendor offers; price breaks; tags; polymorphic attachments; FTS search and parametric filter. Global Display Columns; per-category column mappings; display formulas; savable Grid Configurations. Read model via well-indexed queries + FTS5 + LOCAL stock aggregates. Onboarding and seed packs. BOM basics (revisions, lines, shortage view, simple build). Packaging (PyInstaller) bundling webview and cr-sqlite.

### Phase 2 — Procurement, Instances, Advanced BOM, Computed Attributes, LTspice
Instance/lot tracking with measurement history; locations workspace. Substitutes/lifecycle; procurement/shopping list; invoice import and reconciliation; landed-cost allocation; offer history and price trends. Advanced BOM (substitute-aware buildable qty, sub-assemblies, where-used, KiCad/PartKeepr import). Computed attributes (formula_input, recompute cascade). LTspice templating/export.

### Phase 3 — Datasheet & Measurement Depth
Datasheet extraction (PyMuPDF) with bounding-box review UI; instrument tracking; extractor plugins.

### Phase 4 — Ecosystem
DuckDB analytics; sync changeset transport (authenticated peer/mobile companion); multi-user with role-based privileges and login (additive thanks to day-one attribution); barcode/QR label generation and scanning; vendor API plugins (DigiKey/Mouser) for live pricing.

> **Day-one prerequisite:** the `user` table seeded with the local user, attribution columns on all CRR/LOG tables, and the acting user threaded through the service-call context.
