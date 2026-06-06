# ThingHound — Data Model Specification

**Date:** 2026-06-04
**Companion documents:** `thinghound-functional-spec.md`, `thinghound-architecture.md`

This document is the **logical data model** — it describes domain entities, their attributes, relationships, and constraints in database-agnostic terms. Physical representation (column types, encoding, DDL constraints) is a mapper concern documented in `thinghound-architecture.md` §9. No DBMS-specific types or syntax appear here.

---

## 1. Conventions

### Identifiers

Primary key strategy depends on table role:

- **Structure and master-data tables** (registry-loaded config, stable named entities): integer `id` (DB-generated). Column is named **`id`**. Normal rowid table in SQLite.
- **Operational and transactional tables** (high-volume, user-created, event records): **UUIDv7** `uuid` (time-ordered, collision-free without coordination). Column is named **`uuid`**. `WITHOUT ROWID` in SQLite. In Python domain models, typed as `UUIDv7` from `thinghound.types`.
- **Reference / code tables**: natural primary key (`code TEXT`).

**FK column naming follows the referenced PK type:** a FK to an integer-PK table ends in `_id` (e.g., `category_id`, `vendor_id`); a FK to a uuid-PK table ends in `_uuid` (e.g., `item_uuid`, `instance_uuid`). The name signals the type.

Physical encoding is DBMS-specific; see the Type Mapping appendix in `thinghound-architecture.md`.

### Exact Numeric Values

**No floating-point anywhere.** Numeric attribute values are stored as exact **Decimal** in base units. The physical encoding on SQLite uses a dual-column representation (scaled integer + exact text); on Postgres a single NUMERIC column suffices. The logical model uses `Decimal` throughout. The mapper handles the encoding.

A `scale` property on each `attribute` specifies the number of significant decimal places used for comparison, indexing, and precision. This is a domain concept — it drives the physical precision per DBMS. Two attributes in the same dimension may have different scales for different practical ranges.

### Money

Money is a `Money` value: an exact decimal amount paired with an ISO 4217 currency code. Physical encoding is DBMS-specific. The mapper handles encoding and decoding.

### Timestamps and Ordering

The logical `Timestamp` and `Date` types are points in time / calendar dates, represented as ISO-8601 in the domain model and across the bridge. Their **physical** storage is DBMS-specific and a mapper concern: on SQLite they are stored as **epoch integers** (epoch milliseconds, UTC — see `thinghound-architecture.md` §9), never as text; the mapper encodes/decodes at the storage boundary. The `HLC` (Hybrid Logical Clock) type is a causal timestamp carried on events and measurements to ensure deterministic ordering across devices with clock skew; it is stored as text, not an epoch integer. Replay and costing order: `(effective_date, hlc, id)`.

### Code Table Pattern — No Native Enum Types

Neither SQLite nor all target DBMSs support native enum types consistently. All domain-constrained string values use the **code table pattern** for portability and extensibility:

- A reference entity named for what one row represents (e.g., `value_type`, `event_type`). Seeded by migrations; read-only at runtime.
- `code TEXT` — primary key, single character, application-defined.
- `name TEXT` — the full display name of the code value.
- `description TEXT` — explanation of the code's meaning and usage.

In referencing entities, the column is renamed to `<field>_code` (e.g., `value_type_code`) and its type is `String` referencing the corresponding code table. All code tables are listed in §3.

### Attribution

Every entity carries `created_user_uuid: UUID (optional)` and `updated_user_uuid: UUID (optional)`. Append-only event entities additionally carry `user_uuid: UUID (optional)` in place of updated attribution. Attribution columns are omitted from individual entity listings below for brevity but are present on all entities.

### Soft Delete

Most catalog and configuration entities use a `deleted_ts: Timestamp (optional)` tombstone. `NULL` = active; a timestamp = soft-deleted. Append-only event entities are never deleted.

### Natural-Key Uniqueness

Uniqueness on natural keys (SKU, MPN, manufacturer name, attribute name within category) is a business constraint enforced by the service layer.

---

## 2. Logical Type Vocabulary

| Type | Description |
|------|-------------|
| `UUID` | UUIDv7 identifier |
| `String` | Variable-length text |
| `Integer` | Exact whole number |
| `Decimal` | Exact decimal (never float) |
| `Boolean` | True / false |
| `Timestamp` | A point in time. ISO-8601 in the model and at the bridge; stored physically as an epoch integer on SQLite (mapper-encoded — see `thinghound-architecture.md` §9). |
| `Date` | A calendar date. ISO-8601 in the model and at the bridge; stored physically as an epoch integer on SQLite (mapper-encoded). |
| `HLC` | Hybrid Logical Clock value (causal timestamp); stored as text, not an epoch integer. |
| `Money` | Exact decimal amount + ISO 4217 currency code |
| `JSON` | Structured data — used only for genuinely free-form content |

`Enum(…)` does not appear in this model. All domain-constrained string values are `String` columns referencing a code table (see §3 and the Code Table Pattern in §1).

---

## 3. Reference Data / Code Tables

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

### `instance_display`
How individuated instances are shown in the grid.

| code | name | description |
|------|------|-------------|
| A | Aggregated | One row per item; instance measurements shown as aggregates |
| E | Expanded | Individuated members shown as child rows under their parent item |

### `sort_direction`
Direction of a column sort.

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

### `file_type`
The type of an attachment.

| code | name | description |
|------|------|-------------|
| P | Photo | Product image |
| D | Datasheet | Technical datasheet |
| O | Document | Other document (application note, errata, etc.) |
| M | Model | Simulation model file |
| X | Other | Uncategorized attachment |

---

## 4. Configuration & Schema

### `attribute_domain`
A user-defined grouping of attribute definitions (Electrical, Physical, Mechanical, Thermal, etc.).

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | Primary key |
| `name` | String | Yes | Soft-unique |
| `sort_order` | Integer | Yes | UI ordering |
| `deleted_ts` | Timestamp | No | Tombstone |

### `unit_dimension`
A measurable domain with a defined base unit.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `name` | String | Yes | e.g., Resistance, Mass |
| `base_unit` | String | Yes | e.g., ohm, gram, metre |
| `deleted_ts` | Timestamp | No | |

### `prefix_set`
A named collection of unit prefixes (SI, Binary/IEC, user-defined).

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `name` | String | Yes | e.g., SI, Binary/IEC |
| `description` | String | No | |
| `deleted_ts` | Timestamp | No | |

### `prefix`
A single prefix within a prefix set.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `prefix_set_id` | Integer | Yes | FK to `prefix_set` |
| `symbol` | String | Yes | e.g., k, M, m, µ, Ki |
| `name` | String | Yes | e.g., kilo, mega, milli |
| `factor` | Decimal | Yes | Exact multiplier relative to base unit |
| `sort_order` | Integer | Yes | |

### `unit_multiplier`
A specific named unit within a dimension (including the base unit itself).

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `unit_dimension_id` | Integer | Yes | FK to `unit_dimension` |
| `name` | String | Yes | Primary name: e.g., Ohm, Foot |
| `alt_names` | JSON | No | Array of alternate names |
| `symbol` | String | Yes | e.g., Ω, ft |
| `plural` | String | No | e.g., Ohms, Feet |
| `alt_plurals` | JSON | No | Array of alternate plurals |
| `factor` | Decimal | Yes | Exact factor: how many base units per 1 of this unit |
| `is_si_generated` | Boolean | Yes | True = auto-generated from a prefix set |
| `deleted_ts` | Timestamp | No | |

### `attribute`
A named, typed, measurable property within one attribute domain. Two attributes with the same name in different attribute domains are entirely distinct entities.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `attribute_domain_id` | Integer | Yes | FK to `attribute_domain` |
| `name` | String | Yes | Soft-unique within its attribute domain |
| `value_type_code` | String | Yes | FK to `value_type`; N/I/S/E/B/U/F/C |
| `description` | String | No | |
| `unit_dimension_id` | Integer | No | FK to `unit_dimension`; set for Numeric and Integer types |
| `scale` | Integer | Yes | Decimal places for value precision and comparison |
| `unit_multiplier_id` | Integer | No | FK to `unit_multiplier`; preferred entry/display unit |
| `constraints` | JSON | No | Free-form: min, max, regex |
| `display_template` | String | No | Jinja2; for Composite type |
| `deleted_ts` | Timestamp | No | |

### `attribute_allowed_prefix`
Which prefixes are selectable for entry on a specific numeric attribute.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `attribute_id` | Integer | Yes | FK to `attribute` |
| `prefix_id` | Integer | Yes | FK to `prefix` |

### `attribute_enum_value`
Ordered members of an Enum-type attribute.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `attribute_id` | Integer | Yes | FK to `attribute` |
| `value` | String | Yes | Internal key |
| `label` | String | No | Display label |
| `sort_order` | Integer | Yes | |
| `deleted_ts` | Timestamp | No | |

### `attribute_component`
A named component within a Composite attribute.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `attribute_id` | Integer | Yes | FK to composite `attribute` |
| `key` | String | Yes | e.g., length, diameter, width |
| `label` | String | No | |
| `value_type_code` | String | Yes | FK to `value_type`; N/I/S/E/B/U only |
| `unit_dimension_id` | Integer | No | |
| `scale` | Integer | Yes | |
| `unit_multiplier_id` | Integer | No | FK to `unit_multiplier` |
| `sort_order` | Integer | Yes | |
| `is_required` | Boolean | Yes | |

---

## 5. Category

All categories live in a **single unified forest** with one unnamed root. The root's direct children are the named type-roots (merchandising, location-taxonomy, financial, …). A category's "type" is its first-level ancestor — derivable from `id_path` — not a stored field. `id_path` is the slash-joined chain of integer `id` values from the root down to and including the category itself. `full_path` is the same chain using category names. Both are **rebuilt for all descendants** whenever a category is moved to a different parent. Ancestry queries use recursive CTEs on the indexed `parent_id`.

### `category`

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `name` | String | Yes | |
| `parent_id` | Integer | No | FK to `category`; NULL = unnamed root |
| `id_path` | String | Yes | Slash-joined integer ids from root to this node e.g. `1/4/12` |
| `full_path` | String | Yes | Slash-joined names from root to this node e.g. `Merchandising/Passive/Resistor` |
| `deleted_ts` | Timestamp | No | |

### `category_attribute`
Binds or suppresses an attribute at a category level. Inheritance falls through to the nearest ancestor row. A row at a child level always overrides the ancestor for that attribute.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `category_id` | Integer | Yes | FK to `category` |
| `attribute_id` | Integer | Yes | FK to `attribute` |
| `is_excluded` | Boolean | Yes | True = attribute is suppressed at this level and inherited by descendants; all other fields ignored when true |
| `is_required` | Boolean | No | Whether this attribute is required for completeness; falls through from ancestor if absent |
| `sort_order` | Integer | No | UI ordering; falls through from ancestor if absent |
| `default_value` | JSON | No | Default for the entry form; falls through from ancestor if absent |

No row at a given level means full fallthrough from the nearest ancestor. A descendant of an excluding category can reintroduce the attribute by defining a new row with `is_excluded = false`.

---

## 6. Display & Grid

### `display_column`
A global, user-defined named grid column slot shared across all categories.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `name` | String | Yes | |
| `position` | Integer | Yes | Global order |
| `default_width` | Integer | No | |
| `value_kind_hint_code` | String | No | FK to `value_kind_hint`; N/T/A |
| `item_field_key` | String | No | When set: binds to a universal item field (sku, derived_name, fixed_name, on_hand, markings, etc.) |
| `deleted_ts` | Timestamp | No | |

### `category_column_mapping`
Binds a Display Column to a mapping target for a specific category. Soft-unique on `(category_id, display_column_id)`.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `category_id` | Integer | Yes | FK to `category` |
| `display_column_id` | Integer | Yes | FK to `display_column` |
| `attribute_id` | Integer | No | FK to `attribute`; direct attribute binding |
| `attribute_component_id` | Integer | No | FK to `attribute_component`; specific composite component |
| `source_layer_code` | String | Yes | FK to `source_layer`; C/I |
| `aggregate_code` | String | No | FK to `aggregate_function`; N/X/A/C/R; set when source layer = I |
| `display_formula` | String | No | Expression; when set, overrides direct binding |

### `display_profile`
Per-category name template.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `category_id` | Integer | Yes | FK to `category`; soft-unique |
| `name_template` | String | Yes | Jinja2 expression |

### `grid_layout`
A named, savable physical grid layout. Has no association with categories or search — it defines only the visual structure of the grid.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `name` | String | Yes | |
| `instance_display_code` | String | Yes | FK to `instance_display`; A/E |
| `created_ts` | Timestamp | Yes | |
| `deleted_ts` | Timestamp | No | |

### `grid_layout_column`
Visible columns for a grid layout.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `grid_layout_id` | Integer | Yes | PK part; FK to `grid_layout` |
| `display_column_id` | Integer | Yes | PK part; FK to `display_column` |
| `position` | Integer | Yes | Left-to-right order |
| `width` | Integer | No | |
| `is_pinned` | Boolean | Yes | Frozen to left edge |

### `grid_layout_sort`
Saved multi-level sort for a grid layout. Identified by position, not by column — the same column may not appear twice.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `grid_layout_id` | Integer | Yes | PK part; FK to `grid_layout` |
| `position` | Integer | Yes | PK part; 1 = primary sort |
| `display_column_id` | Integer | Yes | FK to `display_column` |
| `sort_direction_code` | String | Yes | FK to `sort_direction`; A/D |

### `grid_layout_grouping`
Saved group-by levels for a grid layout. Identified by position — outermost group first.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `grid_layout_id` | Integer | Yes | PK part; FK to `grid_layout` |
| `position` | Integer | Yes | PK part; 1 = outermost grouping level |
| `display_column_id` | Integer | Yes | FK to `display_column` |

### `saved_search_group`
Organizes saved searches into named groups (one level deep).

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `name` | String | Yes | |
| `sort_order` | Integer | Yes | UI ordering |

### `saved_search`
A named, reusable search: a full-text query, a parametric predicate tree, or both. Either may be absent but not both.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `saved_search_group_id` | Integer | No | FK to `saved_search_group` |
| `name` | String | Yes | |
| `text_query` | String | No | Full-text search term; runs against `fts_item` |
| `predicate` | JSON | No | Parametric predicate tree (AND/OR of attribute/field criteria) |
| `tags` | JSON | No | Array of user-defined tag strings for organization |
| `created_ts` | Timestamp | Yes | |
| `updated_ts` | Timestamp | Yes | |
| `deleted_ts` | Timestamp | No | |

### `grid_view`
A named, savable combination of a grid layout and a saved search. Selecting a view replaces both the current layout and current search in one action.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `name` | String | Yes | |
| `grid_layout_id` | Integer | Yes | FK to `grid_layout` |
| `saved_search_id` | Integer | Yes | FK to `saved_search` |
| `tags` | JSON | No | Array of user-defined tag strings for organization |
| `created_ts` | Timestamp | Yes | |
| `updated_ts` | Timestamp | Yes | |
| `deleted_ts` | Timestamp | No | |

---

## 7. Identity & Series

### `manufacturer`

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `name` | String | Yes | Soft-unique |
| `alt_names` | JSON | No | Array of alternate names |
| `url` | String | No | |
| `deleted_ts` | Timestamp | No | |

### `product_series`
A manufacturer product line with shared default attribute values.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `manufacturer_id` | Integer | Yes | FK to `manufacturer` |
| `name` | String | Yes | |
| `description` | String | No | |
| `category_id` | Integer | No | FK to `category` |
| `default_footprint` | String | No | |

### `series_attribute_default`
Default attribute values for a product series, auto-populated to new items.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `product_series_id` | Integer | Yes | FK to `product_series` |
| `attribute_id` | Integer | Yes | FK to `attribute` |
| `value` | Decimal | No | Numeric value in base units |
| `value_text` | String | No | For string/enum/boolean/url types |
| `display_unit` | String | No | Symbol of the entry unit |
| `value_raw` | JSON | No | Original entry preserved |
| `is_editable` | Boolean | Yes | Whether the user can override this default |

---

## 8. Core Item

### `item`
The abstract catalog item — the orderable, reusable entity. An item belongs to one or more categories via `item_category`. There is no primary category; a single **naming category** (`naming_category_id`) is the per-item fallback for name rendering and for display-column resolution when no category section is active.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `sku` | String | Yes | Soft-unique; mandatory stable internal key |
| `parent_item_uuid` | UUID | No | FK to `item`; NULL = not a variant child |
| `naming_category_id` | Integer | No | FK to `category`; must be one of the item's categories that has a name template. Renders `derived_name` and resolves display columns when no category section is active. Defaults to the first assigned category with a template; user-overridable |
| `manufacturer_id` | Integer | No | FK to `manufacturer` |
| `part_number` | String | No | MPN or GPN |
| `product_series_id` | Integer | No | FK to `product_series` |
| `lifecycle_status_code` | String | Yes | FK to `lifecycle_status`; A/N/O/U |
| `stock_mode_code` | String | Yes | FK to `stock_mode`; B/I |
| `instance_kind_code` | String | Yes | FK to `instance_kind`; S/L |
| `stock_unit_dimension_id` | Integer | No | FK to `unit_dimension`; NULL = dimensionless count |
| `reorder_point` | Decimal | No | In stock units |
| `reorder_qty` | Decimal | No | In stock units |
| `safety_stock` | Decimal | No | In stock units |
| `derived_name` | String | No | Rendered by the naming engine from the category name template + attribute values; never user-editable |
| `fixed_name` | String | No | Optional user-set name; overrides `derived_name` for display when not NULL |
| `description` | String | No | |
| `markings` | String | No | Physical identification marks; full-text searchable |
| `nominal_footprint` | String | No | |
| `barcode` | String | No | |
| `asset_folder` | String | No | Path to attachments folder |
| `ltspice_template_id` | Integer | No | FK to `ltspice_template` |
| `ltspice_override_text` | String | No | |
| `ltspice_generated` | String | No | Cached; invalidated by the recompute cascade |
| `created_ts` | Timestamp | Yes | |
| `updated_ts` | Timestamp | Yes | |
| `deleted_ts` | Timestamp | No | |

Soft-unique business constraints (enforced by the service layer):
- `sku` — unique among non-deleted items
- `(manufacturer_id, part_number)` — unique MPN where both are present
- `part_number` where `manufacturer_id` is absent — unique GPN

### `item_category`
Many-to-many membership: an item may belong to any number of categories in the unified forest. There is no primary category.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `item_uuid` | UUID | Yes | PK part; FK to `item` |
| `category_id` | Integer | Yes | PK part; FK to `category` |

### `item_relationship`
Directed, ranked alternatives and equivalence graph. Relationships exist at any level in the parent-child hierarchy.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `item_uuid` | UUID | Yes | FK to `item`; source |
| `related_item_uuid` | UUID | Yes | FK to `item`; target |
| `relationship_type_code` | String | Yes | FK to `relationship_type`; X/A/E/M |
| `symmetric` | Boolean | Yes | True = applies both ways |
| `rank` | Integer | Yes | Preference order among multiple alternatives |
| `conditions` | String | No | Conditions for non-exact alternates |
| `notes` | String | No | |

---

## 9. Attribute Values

### `item_attribute_value`
Catalog-layer attribute values on an item. One row per `(item, attribute)`.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `item_uuid` | UUID | Yes | PK part; FK to `item` |
| `attribute_id` | Integer | Yes | PK part; FK to `attribute` |
| `value` | Decimal | No | Numeric value in base units (Numeric and Integer attributes) |
| `value_text` | String | No | For String / Enum / Boolean / URL attributes |
| `display_unit` | String | No | Symbol of the unit the value was entered in |
| `value_raw` | JSON | No | Original entry preserved for round-trip display |
| `provenance_code` | String | Yes | FK to `provenance`; T/N/U/M/O/V/D/C |
| `provenance_context` | JSON | No | Source detail (PDF page, bbox, etc.) |
| `updated_ts` | Timestamp | Yes | |

Tolerance is not a field here. It is a separate attribute definition in the appropriate dimension.

### `item_attribute_component_value`
Per-component values for Composite attributes. One row per `(item, attribute, component)`.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `item_uuid` | UUID | Yes | PK part; FK to `item` |
| `attribute_id` | Integer | Yes | PK part; FK to composite `attribute` |
| `attribute_component_id` | Integer | Yes | PK part; FK to `attribute_component` |
| `value` | Decimal | No | Numeric value in base units |
| `value_text` | String | No | |
| `display_unit` | String | No | |
| `value_raw` | JSON | No | |
| `provenance_code` | String | Yes | FK to `provenance`; T/N/U/M/O/V/D/C |
| `provenance_context` | JSON | No | |
| `updated_ts` | Timestamp | Yes | |

### `instance_measurement`
Append-only measured values for tracked instances.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `instance_uuid` | UUID | Yes | FK to `item_instance` |
| `attribute_id` | Integer | Yes | FK to `attribute` |
| `value` | Decimal | No | |
| `value_text` | String | No | |
| `display_unit` | String | No | |
| `value_raw` | JSON | No | |
| `provenance_code` | String | Yes | FK to `provenance`; M/O/V only |
| `provenance_context` | JSON | No | |
| `instrument` | String | No | |
| `measured_ts` | Timestamp | Yes | |
| `hlc` | HLC | Yes | Causal ordering; current value = latest by (measured_ts, hlc, uuid) |
| `notes` | String | No | |

---

## 10. Instances

### `item_instance`
A tracked physical unit or batch.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `item_uuid` | UUID | Yes | FK to `item` |
| `instance_ref` | String | No | Label / serial number |
| `instance_kind_code` | String | Yes | FK to `instance_kind`; S/L |
| `qty_initial` | Decimal | Yes | Initial quantity |
| `status_code` | String | Yes | FK to `instance_status`; A/S/C/W/L |
| `current_location_id` | Integer | No | FK to `location`; cached from events |
| `acquisition_event_uuid` | UUID | No | FK to `inventory_event` |
| `barcode` | String | No | |
| `distinguishing_traits` | String | No | Per-unit quirks not in the catalog |
| `deleted_ts` | Timestamp | No | |

---

## 11. Events & Costing

### `inventory_event`
Immutable inventory fact. Insert-only.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `item_uuid` | UUID | Yes | FK to `item` |
| `instance_uuid` | UUID | No | FK to `item_instance`; NULL = bulk pool |
| `event_type_code` | String | Yes | FK to `event_type`; A/C/M/I/D/W/L |
| `qty_change` | Decimal | Yes | Signed; negative for consumption/waste/loss |
| `qty_unit` | String | No | Unit symbol if continuous stock |
| `unit_cost_at_purchase` | Money | No | Acquisition cost per unit (per costing method) |
| `unit_replacement_cost` | Money | No | Market replacement cost per unit at event time |
| `project_uuid` | UUID | No | FK to `project`; set for CONSUME |
| `vendor_offer_uuid` | UUID | No | FK to `vendor_offer` |
| `invoice_line_uuid` | UUID | No | FK to `invoice_line` |
| `build_uuid` | UUID | No | FK to `build` |
| `individuation_group_uuid` | UUID | No | Groups paired INDIVIDUATE legs |
| `from_location_id` | Integer | No | FK to `location`; source for CONSUME/MOVE/INDIVIDUATE |
| `to_location_id` | Integer | No | FK to `location`; destination for ADD/MOVE/INDIVIDUATE |
| `effective_date` | Date | Yes | |
| `hlc` | HLC | Yes | Causal clock; replay order: (effective_date, hlc, uuid) |
| `reason` | String | No | Required by the service layer for ADJUST |
| `notes` | String | No | |
| `created_ts` | Timestamp | Yes | |

Sign and location constraints are enforced by the service layer.

### `currency`

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `code` | String | Yes | ISO 4217; primary key |
| `exponent` | Integer | Yes | Minor unit divisor exponent (e.g., 2 for USD) |
| `symbol` | String | No | |

### `fx_rate`
Exchange rate for multi-currency cost roll-ups.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `quote_code` | String | Yes | Foreign currency ISO 4217 code |
| `rate` | Decimal | Yes | Units of quote_code per 1 home currency unit; exact |
| `as_of_date` | Date | Yes | |

---

## 12. Projects

### `project`
A named work context that consumption events are linked to. Distinct from the physical location hierarchy.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `name` | String | Yes | |
| `description` | String | No | |
| `status_code` | String | Yes | FK to `project_status`; A/C/R |
| `created_ts` | Timestamp | Yes | |
| `deleted_ts` | Timestamp | No | |

---

## 13. Invoices

### `invoice`

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `vendor_id` | Integer | Yes | FK to `vendor` |
| `invoice_number` | String | No | |
| `invoice_date` | Date | No | |
| `currency` | String | Yes | ISO 4217 code |
| `import_template_id` | Integer | No | FK to `import_template` |
| `created_ts` | Timestamp | Yes | |

### `invoice_line`

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `invoice_uuid` | UUID | Yes | FK to `invoice` |
| `line_no` | Integer | Yes | |
| `vendor_sku` | String | No | |
| `part_number` | String | No | |
| `description` | String | No | |
| `qty` | Decimal | Yes | |
| `unit_price` | Money | No | |
| `match_status_code` | String | Yes | FK to `match_status`; P/M/N/I |
| `item_uuid` | UUID | No | FK to `item`; resolved match |
| `vendor_offer_uuid` | UUID | No | FK to `vendor_offer` |
| `raw_data` | JSON | No | Original row preserved |

### `import_template`
Saved column-mapping template for a vendor's invoice or BOM format.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `vendor_id` | Integer | No | FK to `vendor`; optional |
| `name` | String | Yes | |
| `header_signature` | String | Yes | Hash/key for auto-detection |
| `mapping` | JSON | Yes | Header → field map |
| `kind_code` | String | Yes | FK to `import_kind`; I/B |

---

## 14. Vendors & Pricing

### `vendor`

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `name` | String | Yes | Soft-unique |
| `url` | String | No | |
| `alt_names` | JSON | No | Array of alternate names |
| `deleted_ts` | Timestamp | No | |

### `vendor_offer`
A vendor's listing for a specific item. Soft-unique on `(item_uuid, vendor_id, vendor_sku)`.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `item_uuid` | UUID | Yes | FK to `item` |
| `vendor_id` | Integer | Yes | FK to `vendor` |
| `vendor_sku` | String | No | |
| `url` | String | No | |
| `currency` | String | Yes | ISO 4217 code |
| `moq` | Decimal | No | Minimum order quantity |
| `order_multiple` | Decimal | No | |
| `package` | String | No | Cut-tape, reel, etc. |
| `availability_status_code` | String | Yes | FK to `availability_status`; I/O/B/L/D/U |
| `qty_available` | Decimal | No | |
| `lead_time_days` | Integer | No | |
| `last_checked_ts` | Timestamp | No | |
| `is_active` | Boolean | Yes | |

### `price_break`

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `offer_uuid` | UUID | Yes | FK to `vendor_offer` |
| `qty_min` | Decimal | Yes | |
| `qty_max` | Decimal | No | NULL = no upper bound |
| `unit_price` | Money | Yes | |

### `offer_history`
Append-only point-in-time snapshots of a vendor offer's availability and representative price.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `offer_uuid` | UUID | Yes | FK to `vendor_offer` |
| `captured_ts` | Timestamp | Yes | |
| `availability_status_code` | String | Yes | FK to `availability_status`; I/O/B/L/D/U |
| `qty_available` | Decimal | No | |
| `lead_time_days` | Integer | No | |
| `unit_price_1` | Money | No | Representative qty-1 price |

---

## 15. Locations

### `location`
Physical storage locations in a nested hierarchy. WASTE and LOST are event types and instance statuses — not location types.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `name` | String | Yes | |
| `parent_id` | Integer | No | FK to `location`; NULL = top-level |
| `description` | String | No | |
| `barcode` | String | No | |
| `deleted_ts` | Timestamp | No | |

Hierarchy traversed via recursive queries on `parent_id`. No closure table.

---

## 16. BOM & Build

### `bom`

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `name` | String | Yes | |
| `description` | String | No | |
| `produces_item_uuid` | UUID | No | FK to `item`; for sub-assembly BOMs |
| `created_ts` | Timestamp | Yes | |
| `deleted_ts` | Timestamp | No | |

### `bom_revision`

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `bom_uuid` | UUID | Yes | FK to `bom` |
| `rev_label` | String | Yes | e.g., A, 1, 1.0 |
| `status_code` | String | Yes | FK to `bom_status`; D/R/O |
| `notes` | String | No | |
| `released_ts` | Timestamp | No | |
| `created_ts` | Timestamp | Yes | |

### `bom_line`

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `bom_revision_uuid` | UUID | Yes | FK to `bom_revision` |
| `line_no` | Integer | Yes | |
| `item_uuid` | UUID | No | FK to `item`; NULL = unresolved/imported line |
| `qty_per_assembly` | Decimal | Yes | |
| `qty_unit` | String | No | Unit symbol if continuous |
| `refdes` | String | No | Optional reference designators |
| `do_not_populate` | Boolean | Yes | |
| `notes` | String | No | |

### `bom_line_substitute`

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `bom_line_uuid` | UUID | Yes | FK to `bom_line` |
| `item_uuid` | UUID | Yes | FK to `item` |
| `rank` | Integer | Yes | |
| `notes` | String | No | |

### `build`

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `bom_revision_uuid` | UUID | Yes | FK to `bom_revision` |
| `qty_built` | Decimal | Yes | |
| `project_uuid` | UUID | Yes | FK to `project` |
| `status_code` | String | Yes | FK to `build_status`; P/I/C/X |
| `created_ts` | Timestamp | Yes | |

---

## 17. Tags, Formulas, Templates & Extraction

### `tag` / `item_tag`

`tag`: `id` Integer, `name` String (required), `deleted_ts` Timestamp (optional).
`item_tag`: `item_uuid` UUID (PK part; FK to `item`), `tag_id` Integer (PK part; FK to `tag`).

### `attribute_formula`

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `name` | String | Yes | |
| `target_attribute_id` | Integer | Yes | FK to `attribute` |
| `expression` | String | Yes | simpleeval + Pint |
| `enabled` | Boolean | Yes | |

### `formula_input`
Maps expression symbols to source attributes.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `attribute_formula_id` | Integer | Yes | FK to `attribute_formula` |
| `symbol` | String | Yes | e.g., $r for Resistance |
| `attribute_id` | Integer | Yes | FK to `attribute` |
| `layer_code` | String | Yes | FK to `formula_layer`; C/I/E |

### `formula_category`
Applicable categories for a formula.

`attribute_formula_id` Integer (PK part; FK to `attribute_formula`), `category_id` Integer (PK part; FK to `category`).

### `ltspice_template`

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `id` | Integer | Yes | |
| `name` | String | Yes | |
| `category_id` | Integer | No | FK to `category` |
| `template_type_code` | String | Yes | FK to `ltspice_template_type`; M/S/Y/P |
| `body` | String | Yes | Jinja2 |

### `ltspice_template_param`
`id` Integer, `ltspice_template_id` Integer (FK to `ltspice_template`), `var_name` String (required), `attribute_id` Integer (FK to `attribute`).

### `datasheet_extraction`

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `attachment_uuid` | UUID | Yes | FK to `attachment` |
| `item_uuid` | UUID | No | FK to `item` |
| `page_number` | Integer | No | |
| `bbox_x` | Integer | No | Bounding box coordinates |
| `bbox_y` | Integer | No | |
| `bbox_w` | Integer | No | |
| `bbox_h` | Integer | No | |
| `extracted_text` | String | No | |
| `mapped_attribute_id` | Integer | No | FK to `attribute` |
| `value` | Decimal | No | Extracted numeric value in base units |
| `confidence` | Integer | No | 0–100 |
| `status_code` | String | Yes | FK to `extraction_status`; P/A/R |
| `reviewed_user_uuid` | UUID | No | FK to `user` |

---

## 18. Attachments, Settings & Users

### `attachment`
A file record with no knowledge of its owner. Items and invoices each maintain their own collection via a junction table.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `file_type_code` | String | Yes | FK to `file_type`; P/D/O/M/X |
| `file_path` | String | Yes | Relative to user-data directory |
| `description` | String | No | |
| `created_ts` | Timestamp | Yes | |
| `updated_ts` | Timestamp | Yes | |
| `deleted_ts` | Timestamp | No | Tombstone |

### `item_attachment`
Ordered attachment collection for a catalog item.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `item_uuid` | UUID | Yes | PK part; FK to `item` |
| `attachment_uuid` | UUID | Yes | PK part; FK to `attachment` |
| `sort_order` | Integer | Yes | Order within the item's collection |

### `invoice_attachment`
Ordered attachment collection for an invoice.

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `invoice_uuid` | UUID | Yes | PK part; FK to `invoice` |
| `attachment_uuid` | UUID | Yes | PK part; FK to `attachment` |
| `sort_order` | Integer | Yes | Order within the invoice's collection |

### `app_setting`
Synced user preferences. Key examples: `home_currency`, `default_unit_{dimension_id}`, `default_grid_config`, `costing_method`.

`key` String (primary key), `value` JSON (required).

### `device_setting`
Device-local preferences. Never synced.

`key` String (primary key), `value` JSON (required).

### `user`

| Attribute | Type | Required | Notes |
|-----------|------|----------|-------|
| `uuid` | UUID | Yes | |
| `username` | String | Yes | Soft-unique |
| `display_name` | String | Yes | |
| `is_active` | Boolean | Yes | |
| `created_ts` | Timestamp | Yes | |
| `deleted_ts` | Timestamp | No | |

### `role` / `permission` / `role_permission` / `user_role`
Defined now for future RBAC enforcement. Seeded and enforced in a later phase.

`role`: `uuid` UUID, `name` String, `description` String (optional).
`permission`: `uuid` UUID, `key` String (e.g., `item.edit`), `description` String (optional).
`role_permission`: `role_uuid` UUID (PK part), `permission_uuid` UUID (PK part).
`user_role`: `user_uuid` UUID (PK part), `role_uuid` UUID (PK part).

---

## 19. Derived Entities (Read Model)

Each read-model aggregate keeps a **materialized running value up to a watermark**. A read always returns the materialized snapshot plus the fold of events past the watermark (the uncompacted tail), so values are **always correct** regardless of when aggregation last ran. Aggregation advances the watermark by folding the tail into the snapshot — it is compaction for performance, never required for correctness. Timing is configurable per read-model: on open, on close, every N minutes, on demand, or any combination.

Triggers maintain incremental updates for local writes. A full rebuild is available for migrations or restores.

### `rm_item_stock`
Per-item stock aggregates derived from `inventory_event`.

| Attribute | Type | Notes |
|-----------|------|-------|
| `item_uuid` | UUID | Primary key |
| `watermark_uuid` | UUID | UUID of the last `inventory_event` folded into the snapshot; NULL = no events yet aggregated |
| `qty_available` | Decimal | |
| `qty_assigned` | Decimal | |
| `qty_waste` | Decimal | |
| `qty_lost` | Decimal | |
| `avg_landed_cost` | Money | In home currency |
| `last_unit_cost` | Money | In home currency |

### `rm_stock_by_location`
Per-item, per-location, per-stock-mode stock.

| Attribute | Type | Notes |
|-----------|------|-------|
| `item_uuid` | UUID | PK part |
| `location_id` | Integer | PK part |
| `stock_mode_code` | String | PK part; FK to `stock_mode`; B=bulk pool, I=tracked instances |
| `watermark_uuid` | UUID | UUID of the last event folded in; NULL = not yet aggregated |
| `qty` | Decimal | |

### `rm_instance_state`
Current state of each tracked instance.

| Attribute | Type | Notes |
|-----------|------|-------|
| `instance_uuid` | UUID | Primary key |
| `watermark_uuid` | UUID | UUID of the last event folded in; NULL = not yet aggregated |
| `current_location_id` | Integer | |
| `qty_remaining` | Decimal | |
| `status_code` | String | FK to `instance_status`; A/S/C/W/L |

### `fts_item`
Full-text search index over `derived_name`, `fixed_name`, descriptions, SKUs, part numbers, markings, tags, and reference designators. Each dimensional attribute value is indexed in both its as-entered form and its canonical base-unit form. Maintained by triggers; `derived_name` entries are updated whenever a relevant attribute value or name template changes.

### `rm_thumbnail`
Cached thumbnail file paths and metadata for attachments.

---

## 20. Key Indexes (Logical)

The following access patterns drive the critical indexes. Physical index definitions live in migration files.

| Access pattern | Entities involved |
|----------------|-------------------|
| Parametric search: attribute value range | `item_attribute_value` by `(attribute_id, value)` |
| Parametric search: component value range | `item_attribute_component_value` by `(attribute_id, component_id, value)` |
| Event replay and costing | `inventory_event` by `(item_uuid, effective_date, hlc, uuid)` |
| Stock aggregation by location | `inventory_event` by `from_location_id`, `to_location_id` |
| Current instance measurement | `instance_measurement` by `(instance_uuid, attribute_id, measured_ts, hlc, uuid)` |
| Category tree traversal | `category` by `parent_id` |
| Category subtree lookup | `category` by `id_path` (prefix search) |
| Location tree traversal | `location` by `parent_id` |
| Item variant navigation | `item` by `parent_item_uuid` |
| Offer lookup | `vendor_offer` by `item_uuid`; `price_break` by `offer_uuid` |
| Soft-delete filtering | `deleted_ts` on all tombstoned entities |
| Full-text search | `fts_item` (FTS5 with trigram tokenizer) |
| Code table lookup | Each `*_code` column by its value |

---

## 21. Migrations

### `schema_migration`

| Attribute | Type | Notes |
|-----------|------|-------|
| `version` | String | Primary key |
| `name` | String | |
| `checksum` | String | SHA-256 of migration file |
| `applied_ts` | Timestamp | |

Migrations are sequential, transactional, and idempotent. Each migration is wrapped in a transaction. Checksums detect post-application modification. Forward-only policy; destructive changes use data-migration hooks. Code table seed data is inserted in migrations. The minimum compatible schema version is embedded in the application for sync compatibility enforcement.
