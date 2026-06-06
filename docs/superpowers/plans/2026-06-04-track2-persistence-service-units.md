# Track 2 — Persistence & Service Units Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

> One fresh subagent per unit; superpowers:dispatching-parallel-agents for the Phase-1b fan-out. Each unit is sized for a basic (Haiku-class) agent and follows the **uniform unit template** (§2) against the **worked example** (§3). Starts only after **Gate A** and the query-component unit (**U0**). **Every commit is gated on explicit user authorization** — no exceptions.

> **Templated unit specs (program-plan §4 declared deviation).** §4 (U0–U6) and §5 (Phase-1b table) are condensed catalogs of aggregates / behaviours / bridge backing. Each unit is **expanded at dispatch time** into a full step-by-step plan by combining: (a) the unit row, (b) the Uniform Unit Template (§2), (c) the worked canonical example (§3), and (d) the relevant `data-model.md` section. The orchestrator performs this expansion before dispatching.

**Authoritative sources:** `docs/specs/thinghound-{functional-spec,architecture,data-model}.md`; `docs/dev/standards-*.md` (the aggregate-mapper standards are `docs/dev/standards-repository.md` + agent version — the filename says "repository" but the content mandates **aggregate mappers, not a generic repository**). Where this plan and a doc disagree, the doc wins. **`thinghound-data-model.md` is authoritative for every table, column, type, and key.**

**Goal:** Build the Phase-1 persistence and service layer as independent, testable units — the model-aware query component, aggregate mappers, query/projection objects, and thin services — on the Track-1 foundation. First the query component (U0) and a vertical slice to a working grid (Gate B), then a parallel fan-out (Gate C).

---

## 1. Layering & the Conversion Boundary (READ BEFORE WRITING ANY CODE)

This restates program-plan §1 and `architecture.md §4`. It is the rule this plan exists to enforce.

### Who does what

- **The model-aware query component builds all SQL.** Callers express **intent** (entity, projection, predicate, ordering); the component assembles the parameterized statement from mapper-provided metadata, choosing construction and strategy per use case. Joins derive from declared relationships. Values are always bound; identifiers come only from metadata. No hand-written named SQL constants anywhere.
- **The aggregate mapper owns metadata + conversion for ONE aggregate.** It declares the column/relationship metadata the query component needs and owns the row↔model conversion as private methods — id `bytes`↔`UUID` for uuid keys, integer ids passed through, scaled-int↔model, **timestamp epoch-int↔ISO-8601** (via `value/temporal.py`). It is the only layer that knows both the physical schema and the domain model. It **never** calls `commit()`.
- **The Session / Unit of Work does NOT convert and holds NO table SQL.** Connection, transaction scope, identity map; exposes mappers and owns the transaction they run in.
- **Models convert only their own values** (`ScaledValue`, `Money`); timestamp/date fields are ISO-8601 strings in the model. Models know nothing about rows or the database, and **carry no audit fields** (those come via a separate `Audit` object).
- **Domain objects / collections** delegate persistence to the mapper; no SQL, no conversion.
- **Query / projection objects** express read intent to the query component and return **read models** (projections); no writes.
- **Services** orchestrate use-cases, thread the acting user, and enforce invariants the schema does not: natural-key uniqueness, required-attribute completeness, cross-row business rules. **No SQL, no conversion.**

### One mapper per aggregate — never a god-object

A mapper is bound to **one aggregate**: a root entity plus the rows saved/loaded **with** it.

- A **simple** entity is one model, one table, one mapper (`UnitDimension` → `UnitDimensionMapper`).
- A **compound** aggregate is a root plus rows with no independent lifecycle, always written with it — across several tables, behind **one** mapper (an `Attribute` with its allowed prefixes, enum values, components; an `Item` with its category memberships and relationships).
- **Distinct, independently-referenced entities get distinct mappers.** A dimension, a unit multiplier, a prefix, an attribute, a manufacturer are separate aggregates → separate mappers. Lumping them into one `SchemaRegistryMapper` / `ItemMapper`-that-also-writes-manufacturers is the god-object antipattern and fails review.
- "Schema registry," "catalog," etc. are **layers / work units**, not aggregates. One **unit** below may deliver **several** aggregate mappers.
- Reads cross tables freely (the query component joins per the model). Confirm each aggregate boundary at unit start: is the child row meaningless without its root and always written with it? → owned/compound; else → its own mapper.

### Converter naming

- A mapper that maps a **single** entity type names its converters **`_from_row` / `_to_row`**.
- A **compound** mapper names one converter per type: **`_<entity>_from_row` / `_<entity>_to_row`** (e.g. `_attribute_from_row`, `_enum_value_from_row`).

If a unit puts a `_*_from_row` on anything but its aggregate's mapper, makes the session/service convert a row, hand-writes SQL, lumps unrelated aggregates into one mapper, or prefixes converters on a single-entity mapper, it fails review.

---

## 2. The Uniform Unit Template

A unit delivers **one mapper per aggregate it owns** (plus any query objects and one service). Each mapper is built with this sequence:

```
- [ ] Step 1  Read the unit spec (§4/§5) + the worked example (§3) + the compact standards files
              (agent/standards-repository.md, -sql, -data-models, -testing, -error-handling).
              Identify aggregate boundaries: which root + owned rows each mapper covers.
- [ ] Step 2  Per aggregate: write the failing round-trip test (add -> load -> model equality).
- [ ] Step 3  Run -> FAIL (mapper not defined).
- [ ] Step 4  Implement the aggregate's mapper: declare its column/relationship metadata for the
              query component; implement row<->model conversion as private `_from_row`/`_to_row`
              (single-entity) or `_<entity>_from_row`/`_<entity>_to_row` (compound) ON THAT MAPPER;
              expose single- and batch-form load/write that call the query component with intent;
              NO hand-written SQL; NO commit().
- [ ] Step 5  Run -> PASS.
- [ ] Step 6  Add remaining mapper tests: batch round-trip, owned-row round-trip, soft-delete
              exclusion, load/list.
- [ ] Step 7  Write failing tests for the unit's query/projection objects and service methods.
- [ ] Step 8  Implement query objects (read intent -> read models) and the service (orchestrates the
              unit's mappers within a session transaction; threads acting user; enforces
              uniqueness/coupling; raises typed errors). Service does NO SQL, NO conversion.
- [ ] Step 9  Run full suite -> green; ruff clean; foreign keys enforced.
- [ ] Step 10 Self-verify (paste real green output), then request code review against this spec + DoD.
- [ ] Step 11 Address review, then **request explicit user authorization** before committing.
              Only after that authorization, commit `feat(<unit>): <summary>`. **This applies to
              every unit, every time** — no standing authorization (CLAUDE.md, program plan §8).
```

**Definition of Done** = program plan §5.

---

## 3. Worked Canonical Example — `UnitDimensionMapper` (a single-entity aggregate)

`UnitDimension` is a simple aggregate: one model, one table (`unit_dimension`), one mapper. It is a **structure table → integer `id` PK**. Because it maps a single type, its converters are the unprefixed `_from_row` / `_to_row`. Audit fields are not on the model.

**Aggregate:** `UnitDimension`. **Model:** `models/schema/unit_dimension.py`.
**Files:** `src/thinghound/mappers/unit_dimension_mapper.py`; tests `tests/mappers/test_unit_dimension_mapper.py`.

- [ ] **Step 2 — failing round-trip test:**

```python
"""UnitDimensionMapper round-trips a unit dimension exactly."""

from thinghound.mappers.unit_dimension_mapper import UnitDimensionMapper
from thinghound.models.schema.unit_dimension import UnitDimension


def test_dimension_round_trip(conn):
    mapper = UnitDimensionMapper(query)        # query = the model-aware query component
    new_id = mapper.add(conn, UnitDimension(id=None, name="Resistance", base_unit="ohm"))
    assert mapper.load(conn, new_id) == UnitDimension(id=new_id, name="Resistance", base_unit="ohm")


def test_deleted_dimension_excluded_from_active_list(conn):
    mapper = UnitDimensionMapper(query)
    did = mapper.add(conn, UnitDimension(id=None, name="Mass", base_unit="gram"))
    mapper.soft_delete(conn, did)
    assert did not in [d.id for d in mapper.list_active(conn)]
```

- [ ] **Step 4 — the aggregate mapper.** The mapper declares metadata and owns conversion; the **query component** builds the SQL. The exact query-component API is defined in **U0** (`architecture.md §4.5`); the calls below are illustrative of intent, not a frozen signature.

```python
"""Aggregate mapper for the UnitDimension aggregate (one entity, one table).

Declares unit_dimension metadata for the query component and owns the row<->model
conversion. Single source of truth for that conversion. Never calls commit().
"""

import sqlite3

from thinghound.models.schema.unit_dimension import UnitDimension


class UnitDimensionMapper:
    """Maps the UnitDimension aggregate (structure table, integer id).
    Conversion lives here and nowhere else."""

    table = "unit_dimension"
    columns = ("id", "name", "base_unit")   # metadata the query component reads; audit cols handled separately
    key = "id"                               # integer PK

    def __init__(self, query):
        self.query = query                   # the model-aware query component

    # --- row <-> model conversion: PRIVATE METHODS ON THE MAPPER (the only converter) ---

    def _from_row(self, row: sqlite3.Row) -> UnitDimension:
        return UnitDimension(
            id=row["id"],                    # integer id passes through
            name=row["name"],
            base_unit=row["base_unit"],
        )

    def _to_row(self, d: UnitDimension) -> dict:
        return {"name": d.name, "base_unit": d.base_unit}   # id is DB-generated on insert

    # --- load/write API: returns/accepts domain models only; SQL built by the query component ---

    def load(self, conn: sqlite3.Connection, id: int) -> UnitDimension | None:
        row = self.query.get(conn, self, id=id)
        return self._from_row(row) if row else None

    def list_active(self, conn: sqlite3.Connection) -> list[UnitDimension]:
        return [self._from_row(r) for r in self.query.list(conn, self, active_only=True)]

    def add(self, conn: sqlite3.Connection, d: UnitDimension) -> int:
        return self.query.insert(conn, self, self._to_row(d))      # returns new integer id

    def add_batch(self, conn: sqlite3.Connection, ds: list[UnitDimension]) -> None:
        self.query.insert_many(conn, self, [self._to_row(d) for d in ds])

    def soft_delete(self, conn: sqlite3.Connection, id: int) -> None:
        self.query.soft_delete(conn, self, id=id)                  # sets deleted_ts
```

Notes that generalize to every mapper:
- **uuid aggregates** (operational/transactional, e.g. `Item`) convert ids `bytes`↔`UUID` in `_from_row`/`_to_row` and supply `uuid` on insert (UUIDv7 generated by the service); their `key` is `"uuid"` and FK columns end in `_uuid`.
- **timestamps** convert epoch-int↔ISO-8601 in the mapper via `value/temporal.py`.
- **audit fields** are written/read by the query component from the acting-user context and surfaced via the `Audit` object on demand — they are not on the domain model.

### When the aggregate is compound (the prefixed form)

`Attribute` owns rows meaningless without it and always written with it — `attribute_allowed_prefix`, `attribute_enum_value`, `attribute_component`. They live behind **one** `AttributeMapper`, which maps several types, so its converters are prefixed:

```python
class AttributeMapper:
    """Maps the Attribute aggregate: the attribute root plus its owned allowed-prefix,
    enum-value, and component rows (all integer-keyed structure tables)."""

    def _attribute_from_row(self, row): ...       # attribute
    def _enum_value_from_row(self, row): ...       # attribute_enum_value
    def _component_from_row(self, row): ...        # attribute_component
    def _allowed_prefix_from_row(self, row): ...   # attribute_allowed_prefix
    def load(self, conn, id): ...                  # assembles the whole aggregate
```

- [ ] **Step 8 — query object + service + registry wiring (U1 scope).**
  - `schema_resolution_query.py`: a **query object** resolving a category's attribute set with inheritance + child override + `is_excluded` via a recursive CTE, returning a read-model `AttributeSchema` (backs `schema.getResolvedSchema`).
  - `schema_service.py`: exposes `schema.getDimensions()`, `getAttributeDomains()`, `getResolvedSchema(...)`; validates `*_code` against the loaded code tables; enforces `(name, attribute_domain_id)` uniqueness via `AttributeMapper` with a typed error. **No SQL, no conversion.**
  - Wire `AppRegistry.load(session)` to populate dimensions, multipliers, prefix sets/prefixes, attribute domains, attributes, and the `factors_for(unit_dimension_id)` map (exact `Fraction` factors) — **via the mappers**.

- [ ] **Behavioral tests U1 must include:** dimension round-trip + batch; multiplier round-trip; attribute aggregate round-trip incl. owned enum values/components; soft-delete exclusion; service-enforced `(name, attribute_domain_id)` uniqueness; scale-per-attribute respected; `factors_for` returns exact factors.

Every later unit follows this shape: identify its aggregates, one mapper each, converters named per the §1 rule.

---

## 4. Phase 1a — Query Component + Vertical Slice Units (sequential)

Each is one subagent + review. U0 builds the shared query component; U1–U6 deliver **one mapper per aggregate**. No two mappers write the same table. Gate B is reached when U6 feeds the UI demo with real data.

### U0 — Model-aware query component (blocks all mapper units)
- **Deliverable:** the query component (`architecture.md §4.5`) that builds parameterized SQL from mapper metadata: `get`, `list` (with `active_only`), `insert`/`insert_many` (returns integer id where applicable), `update`, `soft_delete`, and a relationship-driven join/predicate/order builder for read models. Values always bound; identifiers only from metadata.
- **Note:** detailed generator behavior (projection/aggregate declaration, EAV filter strategy, expression surface) is **in-progress** — finalize the API at the start of this unit with the user before the mapper units depend on it. Until then, U0's public surface is provisional and U1's worked example tracks it.
- **Backs:** every mapper and query object in this track.

### U1 — Structure / Schema Registry — the worked example (§3). Wires `AppRegistry.load`. Blocks all other mapper units.
- **Aggregate mappers:** `UnitDimensionMapper` (`unit_dimension`) · `UnitMultiplierMapper` (`unit_multiplier`) · `PrefixSetMapper` (`prefix_set`) · `PrefixMapper` (`prefix`) · `AttributeDomainMapper` (`attribute_domain`) · `AttributeMapper` *(compound: `attribute` + `attribute_allowed_prefix` + `attribute_enum_value` + `attribute_component`)*. All integer-keyed structure tables.
- **Query/service:** `schema_resolution_query.py`, `schema_service.py`.

### U2 — Category
- **Aggregate mappers:** `CategoryMapper` *(compound: `category` + its `category_attribute` bindings)* · `DisplayProfileMapper` (`display_profile`). Integer-keyed.
- **Behaviors/tests:** CRUD + soft-delete; recursive-CTE ancestry/descendants query; attribute-set resolution with inheritance + `is_excluded` (drives `schema.getResolvedSchema(categoryId)`); reparent updates `parent_id`, rebuilds `id_path`/`full_path` for all descendants, and refreshes the registry ancestry cache.
- **Backs:** `schema.getResolvedSchema`, the left-pane tree.

### U3 — Item
- **Aggregate mappers:** `ItemMapper` *(compound: `item` + `item_category` + `item_relationship`)* · `ManufacturerMapper` (`manufacturer`) · `ProductSeriesMapper` *(compound: `product_series` + `series_attribute_default`)*. *(Three distinct aggregates.)*
- **Behaviors/tests:** item aggregate round-trip (uuid PK; integer FKs `manufacturer_id`/`product_series_id`/`naming_category_id`; uuid FK `parent_item_uuid`); **service-enforced** uniqueness — `sku` (`DuplicateSkuError`), `(manufacturer_id, part_number)` MPN, GPN where manufacturer absent; **naming category** defaults to the first assigned category with a name template and is settable (`items.setNamingCategory`); variant navigation (`getVariants`); series auto-populate (§5.1) → attribute values with `provenance = T` (coordinates with U4).
- **Backs:** `items.create/update/softDelete/getVariants/setNamingCategory`.

### U4 — Attribute Values
- **Aggregate mappers:** `ItemAttributeValueMapper` *(compound: `item_attribute_value` + `item_attribute_component_value`)*.
- **Behaviors/tests:** the **value write path** (§5.4) in the service — fraction preprocessor → registry `factors_for` → `encode_scaled(base, scale)` where **scale comes from the `attribute`** → mapper stores `value_scaled`+`value_exact`+`value_raw`+`display_unit`+`provenance`; Integer-typed attribute rejects fractional input; composite components one row each; a **parametric search query object** (range/equality on `(attribute_id, value_scaled)`, AND/OR leaves, unit-converted thresholds, dimension-wide search).
- **Backs:** `attrs.setValue`, `attrs.setComponentValue`, filter-predicate evaluation.

### U5 — Inventory Events & derived stock
- **Aggregate mappers:** `InventoryEventMapper` (`inventory_event`, append-only) · `ItemInstanceMapper` (`item_instance`) · `CurrencyMapper` (`currency`) · `FxRateMapper` (`fx_rate`). The derived read-model tables (`rm_item_stock`, `rm_stock_by_location`, `rm_instance_state`) are maintained by this unit: DB triggers keep the materialized snapshot + watermark, and reads fold the event tail past the watermark (read via query objects) — not write-aggregate mappers.
- **Behaviors/tests:** append-only insert with `(effective_date, hlc, uuid)` ordering (query object derives balances); on-hand = bulk pool + Σ instances; **INDIVIDUATE nets to zero**; service requires ADJUST reason and MOVE source+dest; negative-balance block at source; **read = snapshot + tail fold equals a full fold** and is correct even when aggregation never ran (consistency oracle, `architecture.md §5.3`); weighted-average + FIFO costing replay stable under shuffled/back-dated/tie events.
- **Backs:** `inventory.addEvent/getLedger/getBalances/individuate/mergeToBulk`.

### U6 — Grid Query (Gate B deliverable)
- **Aggregate mappers:** `DisplayColumnMapper` (`display_column`) · `CategoryColumnMappingMapper` (`category_column_mapping`) · `GridLayoutMapper` *(compound: `grid_layout` + `grid_layout_column` + `grid_layout_sort` + `grid_layout_grouping`)* · `SavedSearchMapper` *(compound: `saved_search` + `saved_search_group`)* · `GridViewMapper` (`grid_view`). Integer-keyed.
- **Behaviors/tests:** the **heterogeneous grid query object** — `grid.queryItems(...)` resolves each global Display Column through the **viewed category section's** column mapping, or through the item's **naming-category** mapping when no section is active (direct attribute / composite component / built-in field / instance-measurement aggregate / display formula / blank), returning grid **read-model** rows with display values **plus `value_exact`** so the UI does no float math; the row name is `fixed_name` else `derived_name`; sort/filter on resolved `value_scaled`/`value_text`; pinned columns; AGGREGATED instance display; layout/search/view CRUD; default global layout via `app_setting`. Joins `rm_item_stock` for `on_hand`.
- **Backs:** `grid.getDisplayColumns/getColumnMappings/queryItems/getLayouts/saveLayout/getSavedSearches/saveSearch/getViews/saveView/setDefaultLayout`.

- [ ] **Gate B:** U0–U6 green + reviewed; the UI demo's dummy bridge is swapped for real `grid.*`/`schema.*` services and a seeded item renders in the real grid.

---

## 5. Phase 1b — Parallel Fan-Out Units

After Gate B, dispatch in parallel (superpowers:dispatching-parallel-agents). No two mappers share a writer table. Each unit delivers one mapper per aggregate (single-entity unless noted "compound").

| Unit | Aggregate mappers (writer tables) | Key behaviors / tests | Backs |
|------|-----------------------------------|------------------------|-------|
| **Vendors & Offers** | `VendorMapper` (`vendor`, int id) · `VendorOfferMapper` *(compound: `vendor_offer` + `price_break`, uuid)* | offer per `(item,vendor)`; soft-unique `(item_uuid,vendor_id,vendor_sku)` service-enforced; breaks by `qty_min`; replacement cost = lowest active-offer tier in home currency | Vendors tab |
| **Offer History & Costing** | `OfferHistoryMapper` (`offer_history`, append-only) | append snapshot; price/availability trend query object; FX roll-up via `fx_rate` (read) | offer history; roll-ups |
| **Locations** | `LocationMapper` (`location`, int id) | recursive-CTE hierarchy query; per-location balances (reads `inventory_event`); scope selector | locations workspace |
| **Instances depth** | `InstanceMeasurementMapper` (`instance_measurement`, append-only) | append-only write via `instances.measure`; current-value = latest by `(measured_ts,hlc,uuid)` (query object); assign/waste/lost service actions | Instances tab, `instances.measure` |
| **Projects** | `ProjectMapper` (`project`, uuid) | CRUD + status; consumption linkage | project picker |
| **Tags & FTS** | `TagMapper` *(compound: `tag` (int id) + `item_tag`)*; `fts_item` via triggers/query | trigram FTS over `derived_name`/`fixed_name`/desc/SKU/MPN/markings/refdes/tags; `derived_name` re-indexed when a naming attribute or template changes; each dimensional value indexed as-entered **and** canonical; unit-aware quick-search routing | §3.14 search |
| **Attachments** | `AttachmentMapper` *(compound: `attachment` + `item_attachment` + `invoice_attachment`, uuid)*; `rm_thumbnail` | attachment carries no owner; item/invoice junctions hold the link + sort order; path-traversal rejected at service; lazy Pillow thumbnails | Assets, thumbnail column |
| **BOM & Build basics** | `BomMapper` *(compound: `bom` + `bom_revision` + `bom_line` + `bom_line_substitute`, uuid)* · `BuildMapper` (`build`, uuid) | DRAFT→RELEASED→OBSOLETE (released immutable); buildable qty = min floor(avail/qty_per_assembly); simple build emits CONSUME (+optional ADD); where-used query | BOM workspace, `bom.*` |
| **Invoices** | `InvoiceMapper` *(compound: `invoice` + `invoice_line`, uuid)* · `ImportTemplateMapper` (`import_template`, int id) | ingest→match(P1 vendor_sku, P2 MPN+mfr, P3 fuzzy FTS, P4 new)→reconcile→atomic commit; duplicate warning | invoice import |
| **Procurement** | *(no new writer tables; reads many)* | buy-list from low-stock + BOM shortage; group by vendor; cheapest honoring MOQ/multiple/breaks/availability; CSV export | procurement workspace |
| **Settings & Users** | `AppSettingMapper` (`app_setting`) · `DeviceSettingMapper` (`device_setting`) · `UserMapper` (`user`, uuid) | seed local user (day-one); home currency/default units/costing method/default grid layout | settings; acting-user context |
| **Onboarding & Seed packs** | *(no new writer tables; orchestrates other services)* | seed packs (units, attribute domains, attributes, starter categories); import/export schema packs | first-run wizard |

- [ ] **Gate C:** all Phase-1b units green + reviewed. Hand to integration + PyInstaller packaging.

---

## 6. Self-Review (against the specs)

- **Query component:** all SQL is built by the component from mapper metadata; no hand-written named SQL constants; values bound; identifiers from metadata only.
- **Aggregate boundaries:** every mapper owns exactly one aggregate (root + owned rows); no mapper spans unrelated entities; single-entity mappers use `_from_row`/`_to_row`, compound mappers use `_<entity>_from_row` per type. Re-verify per unit.
- **Bridge coverage:** `functional-spec.md §6` maps onto units — `schema.*`→U1/U2, `items.*`→U3, `attrs.*`→U4, `inventory.*`→U5, `grid.*`→U6, `instances.*`/`bom.*`/`procurement.*`/`invoice.*`/`settings.*`→Phase 1b. `formula.*`/`sync.*` are Phase 2/4.
- **Conversion boundary:** the session, services, domain objects, collections, and query objects convert nothing; `*_code` stays `str`; uuid ids cross as `bytes`↔`UUID` in the mapper and `str(uuid)` at the bridge; integer ids pass through; timestamps as epoch-int↔ISO-8601 in the mapper; scale read from the `attribute` in the U4 write path; no audit fields on models.
- **Keys:** structure/master-data aggregates are integer-keyed; operational/transactional aggregates are uuid-keyed; FK columns end in `_id`/`_uuid` to match.
