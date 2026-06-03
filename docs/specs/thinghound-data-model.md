# ThingHound — Data Model Specification

**Date:** 2026-06-03
**Companion documents:** `thinghound-functional-spec.md`, `thinghound-architecture.md`

This document is the **logical data model** — it describes domain entities, their attributes, relationships, and constraints in database-agnostic terms. Physical representation (column types, encoding, DDL constraints) is a mapper concern documented in `thinghound-architecture.md` §9. No DBMS-specific types or syntax appear here.

---

## 1. Conventions

### Identifiers

All primary keys are **UUID** (UUIDv7 — time-ordered, collision-free across devices without coordination). In Python domain models, typed as `UUIDv7` from `thinghound.types`. Physical encoding is DBMS-specific; see the Type Mapping appendix in `thinghound-architecture.md`.

### Exact Numeric Values

**No floating-point anywhere.** Numeric attribute values are stored as exact **Decimal** in base units. The physical encoding on SQLite uses a dual-column representation (scaled integer + exact text); on Postgres a single NUMERIC column suffices. The logical model uses `Decimal` throughout. The mapper handles the encoding.

A `scale` property on each `attribute_definition` specifies the number of significant decimal places used for comparison, indexing, and precision. This is a domain concept — it drives the physical precision per DBMS. Two attributes in the same dimension may have different scales for different practical ranges.

### Money

Money is a `Money` value: an exact decimal amount paired with an ISO 4217 currency code. Physical encoding is DBMS-specific. The mapper handles encoding and decoding.

### Timestamps and Ordering

Timestamps are ISO-8601 `Timestamp`. The `HLC` (Hybrid Logical Clock) type is a causal timestamp carried on events and measurements to ensure deterministic ordering across devices with clock skew. Replay and costing order: `(effective_date, hlc, id)`.

### Sync Classes

Every entity is annotated with its sync class — a behavioral, not physical, property:

- **CRR** — Conflict-free Replicated Relation. Synced across devices via cr-sqlite. Column-level last-writer-wins merge by causal metadata.
- **LOG** — Append-only CRR. Insert-only; never updated or deleted after creation. Merges trivially.
- **LOCAL** — Device-only. Never synced. Rebuilt from CRR/LOG sources after every sync merge.
- **REF** — Reference data. Application-defined values seeded by migrations. Read-only at runtime. Identical on every device; does not sync.

### Code Table Pattern — No Native Enum Types

Neither SQLite nor all target DBMSs support native enum types consistently. All domain-constrained string values use the **code table pattern** for portability and extensibility:

- A reference entity named for what one row represents (e.g., `value_type`, `event_type`). Sync class: **REF**.
- `code TEXT` — primary key, single character, application-defined.
- `name TEXT` — the full display name of the code value.
- `description TEXT` — explanation of the code's meaning and usage.

In referencing entities, the column is renamed to `<field>_code` (e.g., `value_type_code`) and its type is `String` referencing the corresponding code table. All code tables are listed in §3.

### Attribution

Every **CRR** entity carries `created_by_user_id: UUID (optional)` and `updated_by_user_id: UUID (optional)`. Every **LOG** entity carries `user_id: UUID (optional)`. Attribution columns are omitted from individual entity listings below for brevity but are present on all CRR and LOG entities.

### Soft Delete

Most catalog and configuration entities use a `deleted_at: Timestamp (optional)` tombstone. `NULL` = active; a timestamp = soft-deleted. Events are never deleted (append-only).

### Natural-Key Uniqueness

Uniqueness on natural keys (SKU, MPN, manufacturer name, attribute name within category) is a business constraint enforced by the service layer. Under sync, collisions are detected by the post-merge integrity check and quarantined for user resolution.

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
| `JSON` | Structured data — used only for genuinely free-form content |

`Enum(…)` does not appear in this model. All domain-constrained string values are `String` columns referencing a code table (see §3 and the Code Table Pattern in §1).

---

## 3. Reference Data / Code Tables (REF)

Each table has `code TEXT PRIMARY KEY`, `name TEXT`, `description TEXT`. Seeded by migrations; read-only at runtime.

### `value_type`
The kind of value an attribute holds.

| code | name | description |
|------|------|-------------|
| N | Numeric | Exact decimal value with units; supports scale, display unit, and dimensional conversion |
| I | Integer | Whole-number-only value; no fractional component permitted |
| S | String | Free-text value |
| E | Enum | Value selected from a defined set of choices (`attribute_enum_value`) |
| B | Boolean | True or false |
| U | URL | Web address |
| F | File | Attachment reference |
| C | Composite | Multiple named component values; renders via display template |

### `value_kind_hint`
Editor display hint for a Display Column.

| code | name | description |
|------|------|-------------|
| N | Numeric | Column holds numeric values; show numeric editor |
| T | Text | Column holds text values; show text editor |
| A | Any | Column type is mixed or unknown |

### `source_layer`
Which value layer a column mapping reads from.

| code | name | description |
|------|------|-------------|
| C | Catalog | Read the item's nominal catalog attribute value |
| I | Instance Measurement | Read an aggregate over the item's instance measurements |

### `aggregate_function`
Aggregation applied to instance measurements for a column mapping.

| code | name | description |
|------|------|-------------|
| N | Min | Minimum measured value across instances |
| X | Max | Maximum measured value across instances |
| A | Average | Mean measured value across instances |
| C | Count | Number of instances with a measured value |
| R | Range | Difference between max and min measured values |

### `grid_scope`
Scope of a Grid Configuration.

| code | name | description |
|------|------|-------------|
| G | Global | Applies across all categories (the all-items grid) |
| C | Category | Applies when a specific category is selected |

### `instance_display`
How individuated instances are shown in the grid.

| code | name | description |
|------|------|-------------|
| A | Aggregated | One row per item; instance measurements shown as aggregates |
| E | Expanded | Individuated members shown as child rows under their parent item |

### `sort_direction`
Direction of a column sort in a Grid Configuration.

| code | name | description |
|------|------|-------------|
| A | Ascending | Lowest to highest |
| D | Descending | Highest to lowest |

### `lifecycle_status`
Catalog lifecycle state of an item.

| code | name | description |
|------|------|-------------|
| A | Active | Current production item; safe for new designs |
| N | NRND | Not recommended for new designs; still available |
| O | Obsolete | Discontinued; surface replacements in BOMs and procurement |
| U | Unknown | Lifecycle status not determined |

### `stock_mode`
Per-item receipt default — how incoming stock is handled.

| code | name | description |
|------|------|-------------|
| B | Bulk | Receipts go to the anonymous pool |
| I | Instance | Receipts create individually tracked instances |

### `instance_kind`
The kind of tracked instance created on receipt or individuation.

| code | name | description |
|------|------|-------------|
| S | Serial | Unique unit; quantity always 1 |
| L | Lot | Batch with a quantity that may be partially consumed |

### `relationship_type`
Type of directed relationship between two items.

| code | name | description |
|------|------|-------------|
| X | Exact Replacement | Drop-in replacement; safe to substitute automatically |
| A | Alternate | Non-exact; applicable with conditions |
| E | Equivalent | Interchangeable both ways |
| M | Alternate MPN | Same physical part under a different manufacturer part number |

### `provenance`
Source of an attribute value.

| code | name | description |
|------|------|-------------|
| T | Template | Copied from a product series |
| N | Nominal | User-entered specification |
| U | User | Manually set or overridden |
| M | Measured | Recorded from an instrument |
| O | Observed | Visually confirmed |
| V | Tested | Functionally verified |
| D | Datasheet Extracted | Parsed from a PDF datasheet |
| C | Computed | Derived by a formula |

### `instance_status`
Current status of a tracked instance.

| code | name | description |
|------|------|-------------|
| A | Available | Ready for use |
| S | Assigned | Allocated to a project |
| C | Consumed | Used up |
| W | Waste | Damaged or scrapped |
| L | Lost | Unaccounted for |

### `event_type`
Type of inventory event.

| code | name | description |
|------|------|-------------|
| A | Add | Receipt of stock |
| C | Consume | Use for a project or bench |
| M | Move | Transfer between storage locations |
| I | Individuate | Promote bulk units to tracked instances |
| D | Adjust | Audit correction; reason required |
| W | Waste | Damaged, expired, or scrapped |
| L | Lost | Unaccounted for |

### `project_status`
Current status of a project.

| code | name | description |
|------|------|-------------|
| A | Active | Work in progress |
| C | Completed | Work finished |
| R | Archived | Closed and archived; no further activity expected |

### `match_status`
Match state of an invoice line during import reconciliation.

| code | name | description |
|------|------|-------------|
| P | Pending | Not yet processed |
| M | Matched | Matched to an existing item or offer |
| N | New | Will create a new item on commit |
| I | Ignored | Excluded from import (e.g., shipping charge) |

### `import_kind`
Type of import template.

| code | name | description |
|------|------|-------------|
| I | Invoice | Vendor invoice column mapping |
| B | BOM | Bill of Materials column mapping |

### `availability_status`
Current stock availability of a vendor offer.

| code | name | description |
|------|------|-------------|
| I | In Stock | Available for immediate shipment |
| O | Out of Stock | Temporarily unavailable |
| B | Backorder | Available but with a delay |
| L | Lead Time | Available to order with a specified lead time |
| D | Discontinued | Vendor no longer stocks this item |
| U | Unknown | Availability not determined |

### `bom_status`
Lifecycle status of a BOM revision.

| code | name | description |
|------|------|-------------|
| D | Draft | In preparation; may be edited |
| R | Released | Approved for production; immutable |
| O | Obsolete | Superseded by a newer revision |

### `build_status`
Current status of a build.

| code | name | description |
|------|------|-------------|
| P | Planned | Scheduled but not started |
| I | In Progress | Stock consumption in progress |
| C | Completed | Build finished; production quantities recorded |
| X | Cancelled | Build abandoned |

### `formula_layer`
Which value layer a formula input reads from.

| code | name | description |
|------|------|-------------|
| C | Catalog | Use the item's nominal catalog value |
| I | Instance | Use the latest instance measurement |
| E | Either | Use instance measurement if present, otherwise catalog value |

### `ltspice_template_type`
Type of LTspice model template.

| code | name | description |
|------|------|-------------|
| M | Model | .model statement |
| S | Subckt | .subckt definition |
| Y | Symbol | Symbol file (.asy) |
| P | Params | .param statements |

### `extraction_status`
Review status of a datasheet extraction candidate.

| code | name | description |
|------|------|-------------|
| P | Pending | Awaiting user review |
| A | Accepted | Approved and written to the catalog |
| R | Rejected | Discarded |

### `attachment_owner_type`
The type of entity an attachment belongs to.

| code | name | description |
|------|------|-------------|
| I | Item | Catalog item |
| N | Instance | Tracked instance or lot |
| V | Vendor | Vendor record |
| M | Manufacturer | Manufacturer record |

### `attachment_role`
The role or purpose of an attachment.

| code | name | description |
|------|------|-------------|
| P | Photo | Product image |
| D | Datasheet | Technical datasheet |
| O | Document | Other document (application note, errata, etc.) |
| M | Model | Simulation model file |
| X | Other | Uncategorized attachment |

### `audit_action`
The type of change recorded in an audit log entry.

| code | name | description |
|------|------|-------------|
| C | Create | A new record was created |
| U | Update | An existing record was modified |
| D | Delete | A record was soft-deleted |

---

## 4. Configuration & Schema

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
| `alt_names` | JSON | No | Array of alternate names |
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
| `value_type_code` | String | Yes | FK to `value_type`; N/I/S/E/B/U/F/C |
| `description` | String | No | |
| `unit_dimension_id` | UUID | No | FK to `unit_dimension`; set for Numeric and Integer types |
| `scale` | Integer | Yes | Decimal places for value precision and comparison |
| `display_unit_id` | UUID | No | FK to `unit_multiplier`; preferred entry/display unit |
| `constraints` | JSON | No | Free-form: min, max, regex |
| `display_template` | String | No | Jinja2; for Composite type |
| `deleted_at` | Timestamp | No | |

### `attribute_allowed_prefix` (CRR)
Which prefixes are selectable for entry on a specific numeric attribute.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `attribute_definition_id` | UUID | Yes | FK to `attribute_definition` |
| `prefix_id` | UUID | Yes | FK to `prefix` |

### `attribute_enum_value` (CRR)
Ordered members of an Enum-type attribute.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `attribute_id` | UUID | Yes | FK to `attribute_definition` |
| `value` | String | Yes | Internal key |
| `label` | String | No | Display label |
| `sort_order` | Integer | Yes | |
| `deleted_at` | Timestamp | No | |

### `attribute_component` (CRR)
A named component within a Composite attribute.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `attribute_id` | UUID | Yes | FK to composite `attribute_definition` |
| `key` | String | Yes | e.g., length, diameter, width |
| `label` | String | No | |
| `value_type_code` | String | Yes | FK to `value_type`; N/I/S/E/B/U only |
| `unit_dimension_id` | UUID | No | |
| `scale` | Integer | Yes | |
| `display_unit_id` | UUID | No | |
| `sort_order` | Integer | Yes | |
| `is_required` | Boolean | Yes | |

---

## 5. Category

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

## 6. Display & Grid

### `display_column` (CRR)
A global, user-defined named grid column slot shared across all categories.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `name` | String | Yes | |
| `position` | Integer | Yes | Global order |
| `default_width` | Integer | No | |
| `value_kind_hint_code` | String | No | FK to `value_kind_hint`; N/T/A |
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
| `source_layer_code` | String | Yes | FK to `source_layer`; C/I |
| `aggregate_code` | String | No | FK to `aggregate_function`; N/X/A/C/R; set when source layer = I |
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
| `scope_code` | String | Yes | FK to `grid_scope`; G/C |
| `category_id` | UUID | No | FK to `category`; set when scope = C |
| `instance_display_code` | String | Yes | FK to `instance_display`; A/E |
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
| `sort_direction_code` | String | No | FK to `sort_direction`; A/D |

### `grid_configuration_grouping` (CRR)
Ordered group-by levels for a Grid Configuration.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `configuration_id` | UUID | Yes | PK part |
| `display_column_id` | UUID | Yes | PK part |
| `position` | Integer | Yes | |

---

## 7. Identity & Series

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

## 8. Core Item

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
| `lifecycle_status_code` | String | Yes | FK to `lifecycle_status`; A/N/O/U |
| `stock_mode_code` | String | Yes | FK to `stock_mode`; B/I |
| `instance_kind_code` | String | Yes | FK to `instance_kind`; S/L |
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
| `relationship_type_code` | String | Yes | FK to `relationship_type`; X/A/E/M |
| `symmetric` | Boolean | Yes | True = applies both ways |
| `rank` | Integer | Yes | Preference order among multiple alternatives |
| `conditions` | String | No | Conditions for non-exact alternates |
| `notes` | String | No | |

---

## 9. Attribute Values

### `item_attribute_value` (CRR)
Catalog-layer attribute values on an item. One row per `(item, attribute)`.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `item_id` | UUID | Yes | PK part; FK to `item` |
| `attribute_id` | UUID | Yes | PK part; FK to `attribute_definition` |
| `value` | Decimal | No | Numeric value in base units (Numeric and Integer attributes) |
| `value_text` | String | No | For String / Enum / Boolean / URL attributes |
| `display_unit` | String | No | Symbol of the unit the value was entered in |
| `value_raw` | JSON | No | Original entry preserved for round-trip display |
| `provenance_code` | String | Yes | FK to `provenance`; T/N/U/M/O/V/D/C |
| `provenance_context` | JSON | No | Source detail (PDF sha256, page, bbox, etc.) |
| `updated_at` | Timestamp | Yes | |

Tolerance is not a field here. It is a separate attribute definition in the appropriate dimension.

### `item_attribute_component_value` (CRR)
Per-component values for Composite attributes. One row per `(item, attribute, component)`.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `item_id` | UUID | Yes | PK part |
| `attribute_id` | UUID | Yes | PK part; FK to composite `attribute_definition` |
| `component_id` | UUID | Yes | PK part; FK to `attribute_component` |
| `value` | Decimal | No | Numeric value in base units |
| `value_text` | String | No | |
| `display_unit` | String | No | |
| `value_raw` | JSON | No | |
| `provenance_code` | String | Yes | FK to `provenance`; T/N/U/M/O/V/D/C |
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
| `provenance_code` | String | Yes | FK to `provenance`; M/O/V only |
| `provenance_context` | JSON | No | |
| `instrument` | String | No | |
| `measured_at` | Timestamp | Yes | |
| `hlc` | HLC | Yes | Causal ordering; current value = latest by (measured_at, hlc, id) |
| `notes` | String | No | |

---

## 10. Instances

### `item_instance` (CRR)
A tracked physical unit or batch.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `item_id` | UUID | Yes | FK to `item` |
| `instance_ref` | String | No | Label / serial number |
| `instance_kind_code` | String | Yes | FK to `instance_kind`; S/L |
| `qty_initial` | Decimal | Yes | Initial quantity |
| `status_code` | String | Yes | FK to `instance_status`; A/S/C/W/L |
| `current_location_id` | UUID | No | FK to `location`; cached from events |
| `acquisition_event_id` | UUID | No | FK to `inventory_event` |
| `barcode` | String | No | |
| `distinguishing_traits` | String | No | Per-unit quirks not in the catalog |
| `deleted_at` | Timestamp | No | |

---

## 11. Events & Costing

### `inventory_event` (LOG)
Immutable inventory fact. Insert-only.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `item_id` | UUID | Yes | FK to `item` |
| `instance_id` | UUID | No | FK to `item_instance`; NULL = bulk pool |
| `event_type_code` | String | Yes | FK to `event_type`; A/C/M/I/D/W/L |
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

## 12. Projects

### `project` (CRR)
A named work context that consumption events are linked to. Distinct from the physical location hierarchy.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `name` | String | Yes | |
| `description` | String | No | |
| `status_code` | String | Yes | FK to `project_status`; A/C/R |
| `created_at` | Timestamp | Yes | |
| `deleted_at` | Timestamp | No | |

---

## 13. Invoices

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
| `match_status_code` | String | Yes | FK to `match_status`; P/M/N/I |
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
| `kind_code` | String | Yes | FK to `import_kind`; I/B |

---

## 14. Vendors & Pricing

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
| `availability_status_code` | String | Yes | FK to `availability_status`; I/O/B/L/D/U |
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
| `availability_status_code` | String | Yes | FK to `availability_status`; I/O/B/L/D/U |
| `qty_available` | Decimal | No | |
| `lead_time_days` | Integer | No | |
| `unit_price_1` | Money | No | Representative qty-1 price |

---

## 15. Locations

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

## 16. BOM & Build

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
| `status_code` | String | Yes | FK to `bom_status`; D/R/O |
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
| `status_code` | String | Yes | FK to `build_status`; P/I/C/X |
| `created_at` | Timestamp | Yes | |

---

## 17. Tags, Formulas, Templates & Extraction

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
| `layer_code` | String | Yes | FK to `formula_layer`; C/I/E |

### `formula_category` (CRR)
Applicable categories for a formula.

`formula_id` UUID (PK part), `category_id` UUID (PK part).

### `ltspice_template` (CRR)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `name` | String | Yes | |
| `category_id` | UUID | No | FK to `category` |
| `template_type_code` | String | Yes | FK to `ltspice_template_type`; M/S/Y/P |
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
| `status_code` | String | Yes | FK to `extraction_status`; P/A/R |
| `reviewed_by_user_id` | UUID | No | FK to `user` |

---

## 18. Attachments, Settings & Users

### `attachment` (CRR)

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | UUID | Yes | |
| `owner_type_code` | String | Yes | FK to `attachment_owner_type`; I/N/V/M |
| `owner_id` | UUID | Yes | FK to the owner entity |
| `role_code` | String | Yes | FK to `attachment_role`; P/D/O/M/X |
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
| `action_code` | String | Yes | FK to `audit_action`; C/U/D |
| `change_summary` | JSON | No | |

Off by default in single-user mode. Enabled when a second user is added — no migration required because attribution was recorded from day one.

---

## 19. LOCAL Derived Entities (Read Model)

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
Per-item, per-location, per-stock-mode stock.

| Attribute | Type | Notes |
|-----------|------|-------|
| `item_id` | UUID | PK part |
| `location_id` | UUID | PK part |
| `stock_mode_code` | String | PK part; FK to `stock_mode`; B=bulk pool, I=tracked instances |
| `qty` | Decimal | |

### `rm_instance_state` (LOCAL)
Current state of each tracked instance.

| Attribute | Type | Notes |
|-----------|------|-------|
| `instance_id` | UUID | Primary key |
| `current_location_id` | UUID | |
| `qty_remaining` | Decimal | |
| `status_code` | String | FK to `instance_status`; A/S/C/W/L |

### `fts_item` (LOCAL)
Full-text search index over item names, descriptions, SKUs, part numbers, markings, tags, and reference designators. Each dimensional attribute value is indexed in both its as-entered form and its canonical base-unit form. Maintained by triggers; rebuilt after sync merge.

### `rm_thumbnail` (LOCAL)
Cached thumbnail file paths and metadata for attachments.

---

## 20. Key Indexes (Logical)

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
| Code table lookup | Each `*_code` column by its value |

---

## 21. Migrations

### `schema_migration` (LOCAL)

| Attribute | Type | Notes |
|-----------|------|-------|
| `version` | String | Primary key |
| `name` | String | |
| `checksum` | String | SHA-256 of migration file |
| `applied_at` | Timestamp | |

Migrations are sequential, transactional, and idempotent. Each migration is wrapped in a transaction. Checksums detect post-application modification. Forward-only policy; destructive changes use data-migration hooks. Code table seed data is inserted in migrations. The minimum compatible schema version is embedded in the application for sync compatibility enforcement.
