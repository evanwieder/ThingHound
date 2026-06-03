# ThingHound — Data Model Specification

**Date:** 2026-06-03
**Companion documents:** `thinghound-functional-spec.md`, `thinghound-architecture.md`

This document is the **logical data model** — it describes domain entities, their attributes, relationships, and constraints in database-agnostic terms. Physical representation (column types, encoding, DDL constraints) is a mapper concern and is documented in `thinghound-architecture.md` under the Type Mapping section. No DBMS-specific types or syntax appear here.

---

## 1. Conventions

### Identifiers

All primary keys are **UUID** (UUIDv7 — time-ordered, collision-free across devices without coordination). In Python domain models, typed as `UUIDv7` from `thinghound.types`. Physical encoding is DBMS-specific; see the Type Mapping appendix in `thinghound-architecture.md`.

### Exact Numeric Values

**No floating-point anywhere.** Numeric attribute values are stored as exact **Decimal** in base units. The physical encoding on SQLite uses a dual-column representation (scaled integer + exact text); on Postgres a single NUMERIC column suffices. The logical model uses `Decimal` throughout. The mapper handles the encoding.

A `scale` property on each `attribute_definition` specifies the number of significant decimal places used for comparison, indexing, and precision. This is a domain concept — it drives the physical precision per DBMS. Two attributes in the same dimension may have different scales for different practical ranges (e.g., `Current` at scale 12 for pA resolution, `Current-High` at scale 3 for industrial range).

### Money

Money is a `Money` value: an exact decimal amount paired with an ISO 4217 currency code. Physical encoding is DBMS-specific (SQLite uses integer minor units + currency text). The logical model uses `Money` throughout; the mapper handles encoding and decoding.

### Timestamps and Ordering

Timestamps are ISO-8601 `Timestamp`. The `HLC` (Hybrid Logical Clock) type is a causal timestamp carried on events and measurements to ensure deterministic ordering across devices with clock skew. Replay and costing order: `(effective_date, hlc, id)`.

### Sync Classes

Every table is annotated with its sync class — a behavioral, not physical, property:

- **CRR** — Conflict-free Replicated Relation. Synced across devices via cr-sqlite. Column-level last-writer-wins merge by causal metadata.
- **LOG** — Append-only CRR. Insert-only; never updated or deleted after creation. Merges trivially.
- **LOCAL** — Device-only. Never synced. Rebuilt from CRR/LOG sources after every sync merge.

### Attribution

Every **CRR** entity carries `created_by_user_id: UUID (optional)` and `updated_by_user_id: UUID (optional)`. Every **LOG** entity carries `user_id: UUID (optional)`. All reference the `user` entity. Default to the seeded local user in v1 so multi-user can be enabled later without migrating historical data. Attribution columns are omitted from individual entity listings below for brevity but are present on all CRR and LOG entities.

### Soft Delete

Most catalog and configuration entities use a `deleted_at: Timestamp (optional)` tombstone. `NULL` = active; a timestamp = soft-deleted. Tombstones propagate correctly under sync. Events are never deleted (append-only).

### Natural-Key Uniqueness

Uniqueness on natural keys (SKU, MPN, manufacturer name, attribute name within category) is a business constraint enforced by the service layer at write time. Under sync, two devices may independently create records with the same natural key; collisions are detected by the post-merge integrity check and quarantined for user resolution.

---

## 2. Logical Type Vocabulary

| Type | Description |
|------|-------------|
| `UUID` | UUIDv7 identifier |
| `String` | Variable-length text |
| `Integer` | Exact whole number |
| `Decimal` | Exact decimal (never float) |
| `Boolean` | True / false |
| `Timestamp` | ISO-8601 datetime |
| `Date` | ISO-8601 date |
| `HLC` | Hybrid Logical Clock value (causal timestamp) |
| `Money` | Exact decimal amount + ISO 4217 currency code |
| `Enum(…)` | String constrained to a defined set of values |
| `JSON` | Structured data — used only for genuinely free-form content |

---

## 3. Configuration & Schema

### `attribute_category` (CRR)
A user-defined grouping of attribute definitions (Electrical, Physical, Mechanical, Thermal, etc.).

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | Primary key |
| `name` | String | Yes | Soft-unique |
| `sort_order` | Integer | Yes | UI ordering |
| `deleted_at` | Timestamp | No | Tombstone |

### `unit_dimension` (CRR)
A measurable domain with a defined base unit.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `name` | String | Yes | e.g., Resistance, Mass |
| `base_unit` | String | Yes | e.g., ohm, gram, metre |
| `deleted_at` | Timestamp | No | |

### `prefix_set` (CRR)
A named collection of unit prefixes (SI, Binary/IEC, user-defined).

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `name` | String | Yes | e.g., SI, Binary/IEC |
| `description` | String | No | |
| `deleted_at` | Timestamp | No | |

### `prefix` (CRR)
A single prefix within a prefix set.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `prefix_set_id` | UUID | Yes | FK to `prefix_set` |
| `symbol` | String | Yes | e.g., k, M, m, µ, Ki |
| `name` | String | Yes | e.g., kilo, mega, milli |
| `factor` | Decimal | Yes | Exact multiplier relative to base unit |
| `sort_order` | Integer | Yes | |

### `unit_multiplier` (CRR)
A specific named unit within a dimension (including the base unit itself).

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `dimension_id` | UUID | Yes | FK to `unit_dimension` |
| `name` | String | Yes | Primary name: e.g., Ohm, Foot |
| `alt_names` | JSON | No | Array of alternate names: ["Amp"] for Ampere |
| `symbol` | String | Yes | e.g., Ω, ft |
| `plural` | String | No | e.g., Ohms, Feet |
| `alt_plurals` | JSON | No | Array of alternate plurals |
| `factor` | Decimal | Yes | Exact factor: how many base units per 1 of this unit |
| `is_si_generated` | Boolean | Yes | True = auto-generated from a prefix set |
| `deleted_at` | Timestamp | No | |

### `attribute_definition` (CRR)
A named, typed, measurable property within one attribute category. Two attributes with the same name in different attribute categories are entirely distinct entities.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `attribute_category_id` | UUID | Yes | FK to `attribute_category` |
| `name` | String | Yes | Soft-unique within its attribute category |
| `value_type` | Enum(numeric, string, enum, boolean, url, file, composite) | Yes | |
| `description` | String | No | |
| `unit_dimension_id` | UUID | No | FK to `unit_dimension`; set for numeric |
| `scale` | Integer | Yes | Decimal places for value precision and comparison |
| `display_unit_id` | UUID | No | FK to `unit_multiplier`; preferred entry/display unit |
| `constraints` | JSON | No | Free-form: min, max, regex |
| `display_template` | String | No | Jinja2; for composite attributes |
| `deleted_at` | Timestamp | No | |

### `attribute_allowed_prefix` (CRR)
Which prefixes are selectable for entry on a specific numeric attribute.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `attribute_definition_id` | UUID | Yes | FK to `attribute_definition` |
| `prefix_id` | UUID | Yes | FK to `prefix` |

### `attribute_enum_value` (CRR)
Ordered members of an enum-type attribute.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `attribute_id` | UUID | Yes | FK to `attribute_definition` |
| `value` | String | Yes | Internal key |
| `label` | String | No | Display label |
| `sort_order` | Integer | Yes | |
| `deleted_at` | Timestamp | No | |

### `attribute_component` (CRR)
A named component within a composite attribute.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `attribute_id` | UUID | Yes | FK to composite `attribute_definition` |
| `key` | String | Yes | e.g., length, diameter, width |
| `label` | String | No | |
| `value_type` | Enum(numeric, string, enum, boolean, url) | Yes | |
| `unit_dimension_id` | UUID | No | |
| `scale` | Integer | Yes | |
| `display_unit_id` | UUID | No | |
| `sort_order` | Integer | Yes | |
| `is_required` | Boolean | Yes | |

---

## 4. Category

### `category` (CRR)
A node in the single-parent category tree. Ancestry queries use recursive CTEs on the indexed `parent_id` relationship.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `name` | String | Yes | |
| `parent_id` | UUID | No | FK to `category`; NULL = root |
| `default_grid_config_id` | UUID | No | FK to `grid_configuration`; this category's default layout |
| `deleted_at` | Timestamp | No | |

### `category_attribute` (CRR)
Assigns an attribute definition to a category with per-assignment settings.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `category_id` | UUID | Yes | FK to `category` |
| `attribute_id` | UUID | Yes | FK to `attribute_definition` |
| `is_required` | Boolean | Yes | Whether this attribute is required for completeness |
| `sort_order` | Integer | Yes | |
| `default_value` | JSON | No | Default for the entry form |
| `is_override` | Boolean | Yes | True = overrides an inherited binding from an ancestor category |

No `is_inherited` attribute. Inheritance is computed at runtime from the category tree.

---

## 5. Display & Grid

### `display_column` (CRR)
A global, user-defined named grid column slot shared across all categories.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `name` | String | Yes | |
| `position` | Integer | Yes | Global order |
| `default_width` | Integer | No | |
| `value_kind_hint` | Enum(NUMERIC, TEXT, ANY) | No | Editor hint |
| `is_hero` | Boolean | Yes | Pinned/prominent column |
| `item_field_key` | String | No | When set: binds to a universal item field (sku, name, on_hand, markings, etc.) |
| `deleted_at` | Timestamp | No | |

### `category_column_mapping` (CRR)
Binds a Display Column to a mapping target for a specific category. Soft-unique on `(category_id, display_column_id)`.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `category_id` | UUID | Yes | FK to `category` |
| `display_column_id` | UUID | Yes | FK to `display_column` |
| `attribute_id` | UUID | No | Direct attribute binding |
| `component_id` | UUID | No | Specific composite component |
| `source_layer` | Enum(CATALOG, INSTANCE_MEASUREMENT) | Yes | |
| `aggregate` | Enum(MIN, MAX, AVG, COUNT, RANGE) | No | For INSTANCE_MEASUREMENT source |
| `display_formula` | String | No | Expression; when set, overrides direct binding |

### `display_profile` (CRR)
Per-category name template.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `category_id` | UUID | Yes | FK to `category`; soft-unique |
| `name_template` | String | Yes | Jinja2 expression |

### `grid_configuration` (CRR)
A named, savable grid layout.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `name` | String | Yes | |
| `scope` | Enum(GLOBAL, CATEGORY) | Yes | |
| `category_id` | UUID | No | FK to `category`; set when scope = CATEGORY |
| `instance_display` | Enum(AGGREGATED, EXPANDED) | Yes | |
| `filter` | JSON | No | Saved predicate tree |
| `created_at` | Timestamp | Yes | |
| `deleted_at` | Timestamp | No | |

### `grid_configuration_column` (CRR)
Visible columns and display settings for a Grid Configuration.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `configuration_id` | UUID | Yes | PK part; FK to `grid_configuration` |
| `display_column_id` | UUID | Yes | PK part; FK to `display_column` |
| `position` | Integer | Yes | |
| `width` | Integer | No | |
| `is_pinned` | Boolean | Yes | |
| `sort_priority` | Integer | No | |
| `sort_direction` | Enum(ASC, DESC) | No | |

### `grid_configuration_grouping` (CRR)
Ordered group-by levels for a Grid Configuration.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `configuration_id` | UUID | Yes | PK part |
| `display_column_id` | UUID | Yes | PK part |
| `position` | Integer | Yes | |

---

## 6. Identity & Series

### `manufacturer` (CRR)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `name` | String | Yes | Soft-unique |
| `alt_names` | JSON | No | Array of alternate names |
| `url` | String | No | |
| `deleted_at` | Timestamp | No | |

### `product_series` (CRR)
A manufacturer product line with shared default attribute values.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `manufacturer_id` | UUID | Yes | FK to `manufacturer` |
| `name` | String | Yes | |
| `description` | String | No | |
| `category_id` | UUID | No | FK to `category` |
| `default_footprint` | String | No | |

### `series_attribute_default` (CRR)
Default attribute values for a product series, auto-populated to new items.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `series_id` | UUID | Yes | FK to `product_series` |
| `attribute_id` | UUID | Yes | FK to `attribute_definition` |
| `value` | Decimal | No | Numeric value in base units |
| `value_text` | String | No | For string/enum/boolean/url types |
| `display_unit` | String | No | Symbol of the entry unit |
| `value_raw` | JSON | No | Original entry preserved |
| `is_editable` | Boolean | Yes | Whether the user can override this default |

---

## 7. Core Item

### `item` (CRR)
The abstract catalog item — the orderable, reusable entity.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `sku` | String | Yes | Soft-unique; mandatory stable internal key |
| `parent_item_id` | UUID | No | FK to `item`; NULL = not a variant child |
| `manufacturer_id` | UUID | No | FK to `manufacturer` |
| `part_number` | String | No | MPN or GPN |
| `series_id` | UUID | No | FK to `product_series` |
| `primary_category_id` | UUID | No | FK to `category`; single-cell primary |
| `lifecycle_status` | Enum(ACTIVE, NRND, OBSOLETE, UNKNOWN) | Yes | |
| `stock_mode` | Enum(BULK, INSTANCE) | Yes | Receipt default |
| `instance_kind` | Enum(SERIAL, LOT) | Yes | Applied when creating instances |
| `stock_unit_dimension_id` | UUID | No | FK to `unit_dimension`; NULL = dimensionless count |
| `reorder_point` | Decimal | No | In stock units |
| `reorder_qty` | Decimal | No | In stock units |
| `safety_stock` | Decimal | No | In stock units |
| `description` | String | No | |
| `markings` | String | No | Physical identification marks; full-text searchable |
| `nominal_footprint` | String | No | |
| `barcode` | String | No | |
| `asset_folder` | String | No | Path to attachments folder |
| `ltspice_template_id` | UUID | No | FK to `ltspice_template` |
| `ltspice_override_text` | String | No | |
| `ltspice_generated` | String | No | Cached; invalidated by the recompute cascade |
| `created_at` | Timestamp | Yes | |
| `updated_at` | Timestamp | Yes | |
| `deleted_at` | Timestamp | No | |

Soft-unique business constraints (enforced by the service layer):
- `sku` — unique among non-deleted items
- `(manufacturer_id, part_number)` — unique MPN where both are present
- `part_number` where `manufacturer_id` is absent — unique GPN

### `item_category` (CRR)
Membership: an item belongs to a category.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `item_id` | UUID | Yes | PK part; FK to `item` |
| `category_id` | UUID | Yes | PK part; FK to `category` |

Primary category is `item.primary_category_id`, not stored here.

### `item_relationship` (CRR)
Directed, ranked alternatives and equivalence graph. Relationships exist at any level in the parent-child hierarchy.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `item_id` | UUID | Yes | FK to `item`; source |
| `related_item_id` | UUID | Yes | FK to `item`; target |
| `type` | Enum(EXACT_REPLACEMENT, ALTERNATE, EQUIVALENT, ALTERNATE_MPN) | Yes | |
| `symmetric` | Boolean | Yes | True = applies both ways (e.g., EQUIVALENT) |
| `rank` | Integer | Yes | Preference order among multiple alternatives |
| `conditions` | String | No | Conditions for non-exact alternates |
| `notes` | String | No | |

---

## 8. Attribute Values

### `item_attribute_value` (CRR)
Catalog-layer attribute values on an item. One row per `(item, attribute)`.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `item_id` | UUID | Yes | PK part; FK to `item` |
| `attribute_id` | UUID | Yes | PK part; FK to `attribute_definition` |
| `value` | Decimal | No | Numeric value in base units (numeric attributes) |
| `value_text` | String | No | For string / enum / boolean / url attributes |
| `display_unit` | String | No | Symbol of the unit the value was entered in |
| `value_raw` | JSON | No | Original entry preserved for round-trip display |
| `provenance` | Enum(TEMPLATE, NOMINAL, USER, MEASURED, OBSERVED, TESTED, DATASHEET_EXTRACTED, COMPUTED) | Yes | |
| `provenance_context` | JSON | No | Source detail (PDF sha256, page, bbox, etc.) |
| `updated_at` | Timestamp | Yes | |

Tolerance is not a field here. It is a separate attribute definition in the appropriate dimension.

### `item_attribute_component_value` (CRR)
Per-component values for composite attributes. One row per `(item, attribute, component)`.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `item_id` | UUID | Yes | PK part |
| `attribute_id` | UUID | Yes | PK part; FK to composite `attribute_definition` |
| `component_id` | UUID | Yes | PK part; FK to `attribute_component` |
| `value` | Decimal | No | Numeric value in base units |
| `value_text` | String | No | |
| `display_unit` | String | No | |
| `value_raw` | JSON | No | |
| `provenance` | Enum(TEMPLATE, NOMINAL, USER, MEASURED, OBSERVED, TESTED, DATASHEET_EXTRACTED, COMPUTED) | Yes | |
| `provenance_context` | JSON | No | |
| `updated_at` | Timestamp | Yes | |

### `instance_measurement` (LOG)
Append-only measured values for tracked instances.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `instance_id` | UUID | Yes | FK to `item_instance` |
| `attribute_id` | UUID | Yes | FK to `attribute_definition` |
| `value` | Decimal | No | |
| `value_text` | String | No | |
| `display_unit` | String | No | |
| `value_raw` | JSON | No | |
| `provenance` | Enum(MEASURED, OBSERVED, TESTED) | Yes | |
| `provenance_context` | JSON | No | |
| `instrument` | String | No | |
| `measured_at` | Timestamp | Yes | |
| `hlc` | HLC | Yes | Causal ordering; current value = latest by (measured_at, hlc, id) |
| `notes` | String | No | |

---

## 9. Instances

### `item_instance` (CRR)
A tracked physical unit or batch.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `item_id` | UUID | Yes | FK to `item` |
| `instance_ref` | String | No | Label / serial number |
| `instance_kind` | Enum(SERIAL, LOT) | Yes | |
| `qty_initial` | Decimal | Yes | Initial quantity |
| `status` | Enum(AVAILABLE, ASSIGNED, CONSUMED, WASTE, LOST) | Yes | |
| `current_location_id` | UUID | No | FK to `location`; cached from events |
| `acquisition_event_id` | UUID | No | FK to `inventory_event` |
| `barcode` | String | No | |
| `distinguishing_traits` | String | No | Per-unit quirks not in the catalog |
| `deleted_at` | Timestamp | No | |

---

## 10. Events & Costing

### `inventory_event` (LOG)
Immutable inventory fact. Insert-only.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `item_id` | UUID | Yes | FK to `item` |
| `instance_id` | UUID | No | FK to `item_instance`; NULL = bulk pool |
| `event_type` | Enum(ADD, CONSUME, MOVE, INDIVIDUATE, ADJUST, WASTE, LOST) | Yes | |
| `qty_change` | Decimal | Yes | Signed; negative for consumption/waste/loss |
| `qty_unit` | String | No | Unit symbol if continuous stock |
| `unit_cost_at_purchase` | Money | No | Acquisition cost per unit (per costing method) |
| `unit_replacement_cost` | Money | No | Market replacement cost per unit at event time |
| `project_id` | UUID | No | FK to `project`; set for CONSUME |
| `vendor_offer_id` | UUID | No | FK to `vendor_offer` |
| `invoice_line_id` | UUID | No | FK to `invoice_line` |
| `build_id` | UUID | No | FK to `build` |
| `individuation_group_id` | UUID | No | Groups paired INDIVIDUATE legs |
| `from_location_id` | UUID | No | FK to `location`; source for CONSUME/MOVE/INDIVIDUATE |
| `to_location_id` | UUID | No | FK to `location`; destination for ADD/MOVE/INDIVIDUATE |
| `effective_date` | Date | Yes | |
| `hlc` | HLC | Yes | Causal clock; replay order: (effective_date, hlc, id) |
| `reason` | String | No | Required by the service layer for ADJUST |
| `notes` | String | No | |
| `created_at` | Timestamp | Yes | |

Sign and location constraints are enforced by the service layer.

### `currency` (CRR)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `code` | String | Yes | ISO 4217; primary key |
| `exponent` | Integer | Yes | Minor unit divisor exponent (e.g., 2 for USD) |
| `symbol` | String | No | |

### `fx_rate` (CRR)
Exchange rate for multi-currency cost roll-ups.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `quote_code` | String | Yes | Foreign currency ISO 4217 code |
| `rate` | Decimal | Yes | Units of quote_code per 1 home currency unit; exact |
| `as_of_date` | Date | Yes | |

---

## 11. Projects

### `project` (CRR)
A named work context that consumption events are linked to. Distinct from the physical location hierarchy.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `name` | String | Yes | |
| `description` | String | No | |
| `status` | Enum(ACTIVE, COMPLETED, ARCHIVED) | Yes | |
| `created_at` | Timestamp | Yes | |
| `deleted_at` | Timestamp | No | |

---

## 12. Invoices

### `invoice` (CRR)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `vendor_id` | UUID | Yes | FK to `vendor` |
| `invoice_number` | String | No | |
| `invoice_date` | Date | No | |
| `currency` | String | Yes | ISO 4217 code |
| `import_template_id` | UUID | No | FK to `import_template` |
| `created_at` | Timestamp | Yes | |

### `invoice_line` (CRR)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `invoice_id` | UUID | Yes | FK to `invoice` |
| `line_no` | Integer | Yes | |
| `vendor_sku` | String | No | |
| `part_number` | String | No | |
| `description` | String | No | |
| `qty` | Decimal | Yes | |
| `unit_price` | Money | No | |
| `match_status` | Enum(PENDING, MATCHED, NEW, IGNORED) | Yes | |
| `item_id` | UUID | No | FK to `item`; resolved match |
| `vendor_offer_id` | UUID | No | FK to `vendor_offer` |
| `raw_data` | JSON | No | Original row preserved |

### `import_template` (CRR)
Saved column-mapping template for a vendor's invoice or BOM format.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `vendor_id` | UUID | No | FK to `vendor`; optional |
| `name` | String | Yes | |
| `header_signature` | String | Yes | Hash/key for auto-detection |
| `mapping` | JSON | Yes | Header → field map |
| `kind` | Enum(INVOICE, BOM) | Yes | |

---

## 13. Vendors & Pricing

### `vendor` (CRR)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `name` | String | Yes | Soft-unique |
| `url` | String | No | |
| `alt_names` | JSON | No | Array of alternate names |
| `deleted_at` | Timestamp | No | |

### `vendor_offer` (CRR)
A vendor's listing for a specific item. Soft-unique on `(item_id, vendor_id, vendor_sku)`.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `item_id` | UUID | Yes | FK to `item` |
| `vendor_id` | UUID | Yes | FK to `vendor` |
| `vendor_sku` | String | No | |
| `url` | String | No | |
| `currency` | String | Yes | ISO 4217 code |
| `moq` | Decimal | No | Minimum order quantity |
| `order_multiple` | Decimal | No | |
| `package` | String | No | Cut-tape, reel, etc. |
| `availability_status` | Enum(IN_STOCK, OUT_OF_STOCK, BACKORDER, LEAD_TIME, DISCONTINUED, UNKNOWN) | Yes | |
| `qty_available` | Decimal | No | |
| `lead_time_days` | Integer | No | |
| `last_checked` | Timestamp | No | |
| `is_active` | Boolean | Yes | |

### `price_break` (CRR)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `offer_id` | UUID | Yes | FK to `vendor_offer` |
| `qty_min` | Decimal | Yes | |
| `qty_max` | Decimal | No | NULL = no upper bound |
| `unit_price` | Money | Yes | |

### `offer_history` (LOG)
Append-only point-in-time snapshots of a vendor offer's availability and representative price.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `offer_id` | UUID | Yes | FK to `vendor_offer` |
| `captured_at` | Timestamp | Yes | |
| `availability_status` | Enum(IN_STOCK, OUT_OF_STOCK, BACKORDER, LEAD_TIME, DISCONTINUED, UNKNOWN) | Yes | |
| `qty_available` | Decimal | No | |
| `lead_time_days` | Integer | No | |
| `unit_price_1` | Money | No | Representative qty-1 price |

---

## 14. Locations

### `location` (CRR)
Physical storage locations in a nested hierarchy. WASTE and LOST are event types and instance statuses — not location types.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `name` | String | Yes | |
| `parent_id` | UUID | No | FK to `location`; NULL = top-level |
| `description` | String | No | |
| `barcode` | String | No | |
| `deleted_at` | Timestamp | No | |

Hierarchy traversed via recursive queries on `parent_id`. No closure table.

---

## 15. BOM & Build

### `bom` (CRR)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `name` | String | Yes | |
| `description` | String | No | |
| `produces_item_id` | UUID | No | FK to `item`; for sub-assembly BOMs |
| `created_at` | Timestamp | Yes | |
| `deleted_at` | Timestamp | No | |

### `bom_revision` (CRR)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `bom_id` | UUID | Yes | FK to `bom` |
| `rev_label` | String | Yes | e.g., A, 1, 1.0 |
| `status` | Enum(DRAFT, RELEASED, OBSOLETE) | Yes | |
| `notes` | String | No | |
| `released_at` | Timestamp | No | |
| `created_at` | Timestamp | Yes | |

### `bom_line` (CRR)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `bom_revision_id` | UUID | Yes | FK to `bom_revision` |
| `line_no` | Integer | Yes | |
| `item_id` | UUID | No | FK to `item`; NULL = unresolved/imported line |
| `qty_per` | Decimal | Yes | |
| `qty_unit` | String | No | Unit symbol if continuous |
| `refdes` | String | No | Optional reference designators |
| `do_not_populate` | Boolean | Yes | |
| `notes` | String | No | |

### `bom_line_substitute` (CRR)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `bom_line_id` | UUID | Yes | FK to `bom_line` |
| `item_id` | UUID | Yes | FK to `item` |
| `rank` | Integer | Yes | |
| `notes` | String | No | |

### `build` (CRR)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `bom_revision_id` | UUID | Yes | FK to `bom_revision` |
| `qty_built` | Decimal | Yes | |
| `project_id` | UUID | Yes | FK to `project` |
| `status` | Enum(PLANNED, IN_PROGRESS, COMPLETED, CANCELLED) | Yes | |
| `created_at` | Timestamp | Yes | |

---

## 16. Tags, Formulas, Templates & Extraction

### `tag` (CRR) / `item_tag` (CRR)

`tag`: `id` UUID, `name` String (required), `deleted_at` Timestamp (optional).
`item_tag`: `item_id` UUID (PK part), `tag_id` UUID (PK part).

### `attribute_formula` (CRR)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `name` | String | Yes | |
| `target_attribute_id` | UUID | Yes | FK to `attribute_definition` |
| `expression` | String | Yes | simpleeval + Pint |
| `enabled` | Boolean | Yes | |

### `formula_input` (CRR)
Maps expression symbols to source attributes.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `formula_id` | UUID | Yes | FK to `attribute_formula` |
| `symbol` | String | Yes | e.g., $r for Resistance |
| `attribute_id` | UUID | Yes | FK to `attribute_definition` |
| `layer` | Enum(CATALOG, INSTANCE, EITHER) | Yes | |

### `formula_category` (CRR)
Applicable categories for a formula.

`formula_id` UUID (PK part), `category_id` UUID (PK part).

### `ltspice_template` (CRR)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `name` | String | Yes | |
| `category_id` | UUID | No | FK to `category` |
| `template_type` | Enum(MODEL, SUBCKT, SYMBOL, PARAMS) | Yes | |
| `body` | String | Yes | Jinja2 |

### `ltspice_template_param` (CRR)
`id` UUID, `template_id` UUID, `var_name` String (required), `attribute_id` UUID.

### `datasheet_extraction` (CRR)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `attachment_id` | UUID | Yes | FK to `attachment` |
| `item_id` | UUID | No | FK to `item` |
| `page_number` | Integer | No | |
| `bbox_x` | Integer | No | Bounding box coordinates |
| `bbox_y` | Integer | No | |
| `bbox_w` | Integer | No | |
| `bbox_h` | Integer | No | |
| `extracted_text` | String | No | |
| `mapped_attribute_id` | UUID | No | FK to `attribute_definition` |
| `value` | Decimal | No | Extracted numeric value in base units |
| `confidence` | Integer | No | 0–100 |
| `status` | Enum(PENDING, ACCEPTED, REJECTED) | Yes | |
| `reviewed_by_user_id` | UUID | No | FK to `user` |

---

## 17. Attachments, Settings & Users

### `attachment` (CRR)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `owner_type` | Enum(ITEM, INSTANCE, VENDOR, MANUFACTURER) | Yes | |
| `owner_id` | UUID | Yes | FK to the owner entity |
| `role` | Enum(PHOTO, DATASHEET, DOCUMENT, MODEL, OTHER) | Yes | |
| `file_path` | String | Yes | Relative to user-data directory |
| `mime_type` | String | No | |
| `sha256` | String | No | |
| `caption` | String | No | |
| `sort_order` | Integer | Yes | |
| `page_count` | Integer | No | |
| `created_at` | Timestamp | Yes | |

### `app_setting` (CRR)
Synced user preferences. Key examples: `home_currency`, `default_unit_{dimension_id}`, `default_grid_config`, `costing_method`.

`key` String (primary key), `value` JSON (required).

### `device_setting` (LOCAL)
Device-local preferences. Never synced.

`key` String (primary key), `value` JSON (required).

### `user` (CRR)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `username` | String | Yes | Soft-unique |
| `display_name` | String | Yes | |
| `is_active` | Boolean | Yes | |
| `created_at` | Timestamp | Yes | |
| `deleted_at` | Timestamp | No | |

### `role` (CRR) / `permission` (CRR) / `role_permission` (CRR) / `user_role` (CRR)
Defined now for future RBAC enforcement. Seeded and enforced in a later phase.

`role`: `id` UUID, `name` String, `description` String (optional).
`permission`: `id` UUID, `key` String (e.g., `item.edit`), `description` String (optional).
`role_permission`: `role_id` UUID (PK part), `permission_id` UUID (PK part).
`user_role`: `user_id` UUID (PK part), `role_id` UUID (PK part).

### `audit_log` (LOG)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `user_id` | UUID | Yes | FK to `user` |
| `at` | Timestamp | Yes | |
| `entity_table` | String | Yes | |
| `entity_id` | UUID | Yes | |
| `action` | Enum(CREATE, UPDATE, DELETE) | Yes | |
| `change_summary` | JSON | No | |

Off by default in single-user mode. Enabled when a second user is added — no migration required because attribution was recorded from day one.

---

## 18. LOCAL Derived Entities (Read Model)

These entities are never synced. They are rebuilt in full after every sync merge and maintained incrementally by database triggers for local writes.

### `rm_item_stock` (LOCAL)
Per-item stock aggregates derived from `inventory_event`.

| Attribute | Type | Notes |
|-----------|------|-------|
| `item_id` | UUID | Primary key |
| `qty_available` | Decimal | |
| `qty_assigned` | Decimal | |
| `qty_waste` | Decimal | |
| `qty_lost` | Decimal | |
| `avg_landed_cost` | Money | In home currency |
| `last_unit_cost` | Money | In home currency |

### `rm_stock_by_location` (LOCAL)
Per-item, per-location, per-bucket stock.

| Attribute | Type | Notes |
|-----------|------|-------|
| `item_id` | UUID | PK part |
| `location_id` | UUID | PK part |
| `bucket` | Enum(BULK, INSTANCE) | PK part |
| `qty` | Decimal | |

### `rm_instance_state` (LOCAL)
Current state of each tracked instance.

| Attribute | Type | Notes |
|-----------|------|-------|
| `instance_id` | UUID | Primary key |
| `current_location_id` | UUID | |
| `qty_remaining` | Decimal | |
| `status` | Enum(AVAILABLE, ASSIGNED, CONSUMED, WASTE, LOST) | |

### `fts_item` (LOCAL)
Full-text search index over item names, descriptions, SKUs, part numbers, markings, tags, and reference designators. Each dimensional attribute value is indexed in both its as-entered form and its canonical base-unit form. Maintained by triggers; rebuilt after sync merge.

### `rm_thumbnail` (LOCAL)
Cached thumbnail file paths and metadata for attachments.

---

## 19. Key Indexes (Logical)

The following access patterns drive the critical indexes. Physical index definitions live in migration files.

| Access pattern | Entities involved |
|----------------|-------------------|
| Parametric search: attribute value range | `item_attribute_value` by `(attribute_id, value)` |
| Parametric search: component value range | `item_attribute_component_value` by `(attribute_id, component_id, value)` |
| Event replay and costing | `inventory_event` by `(item_id, effective_date, hlc, id)` |
| Stock aggregation by location | `inventory_event` by `from_location_id`, `to_location_id` |
| Current instance measurement | `instance_measurement` by `(instance_id, attribute_id, measured_at, hlc, id)` |
| Category tree traversal | `category` by `parent_id` |
| Location tree traversal | `location` by `parent_id` |
| Item variant navigation | `item` by `parent_item_id` |
| Offer lookup | `vendor_offer` by `item_id`; `price_break` by `offer_id` |
| Soft-delete filtering | `deleted_at` on all tombstoned entities |
| Full-text search | `fts_item` (FTS5 with trigram tokenizer) |

---

## 20. Migrations

### `schema_migration` (LOCAL)

| Attribute | Type | Notes |
|-----------|------|-------|
| `version` | String | Primary key |
| `name` | String | |
| `checksum` | String | SHA-256 of migration file |
| `applied_at` | Timestamp | |

Migrations are sequential, transactional, and idempotent. Each migration is wrapped in a transaction. Checksums detect post-application modification. Forward-only policy; destructive changes use data-migration hooks. The minimum compatible schema version is embedded in the application for sync compatibility enforcement.
