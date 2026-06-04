# Track 2 — Persistence & Service Units Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

> One fresh subagent per unit; superpowers:dispatching-parallel-agents for the Phase-1b fan-out. Each unit is sized for a basic (Haiku-class) agent and follows the **uniform unit template** (§2) against the **worked example** (§3). Starts only after **Gate A**. **Every commit is gated on explicit user authorization** — no exceptions.

> **Templated unit specs (program-plan §4 declared deviation).** §4 (U1–U6) and §5 (Phase-1b table) are condensed catalogs of aggregates / behaviours / bridge backing. Each unit is **expanded at dispatch time** into a full step-by-step plan by combining: (a) the unit row, (b) the Uniform Unit Template (§2), (c) the worked canonical example (§3), and (d) the relevant `data-model.md` section. The agent that executes a unit receives the expanded plan, not the §4/§5 row. The orchestrator must perform this expansion before dispatching.

**Authoritative sources:** `docs/specs/thinghound-{functional-spec,architecture,data-model}.md`; `docs/dev/standards-*.md` (the aggregate-mapper standards are `docs/dev/standards-repository.md` + agent version — the filename says "repository" but the content mandates **aggregate mappers, not a generic repository**). Where this plan and a doc disagree, the doc wins.

**Goal:** Build the Phase-1 persistence and service layer as independent, testable units — aggregate mappers, query/projection objects, and thin services — on the Track-1 foundation. First a vertical slice to a working grid (Gate B), then a parallel fan-out (Gate C).

---

## 1. Layering, the Conversion Boundary, and Mapper Granularity (READ BEFORE WRITING ANY CODE)

This restates program-plan §1 and `architecture.md §4`. It is the rule this plan exists to enforce.

### Who does what

- **The aggregate mapper is the ONLY layer that converts rows ↔ models.** It owns, for **one aggregate**: every column list, table name/alias, all SELECT/INSERT/UPDATE/DELETE and load SQL (single **and** batch), **and** the row↔model conversion as private methods — including id `bytes`↔`UUID`, scaled-int↔model, **timestamp epoch-int↔ISO-8601** (via `value/temporal.py`). It is the only layer that knows both the physical schema and the domain model. The dialect seam. It **never** calls `commit()`.
- **The Session / Unit of Work does NOT convert and holds NO table SQL.** Connection, transaction scope, identity map; exposes mappers and owns the transaction they run in. It never turns a row into a model or a model into a row.
- **Models convert only their own values** (`ScaledValue`, `Money`); timestamp/date fields are ISO-8601 strings in the model. Models know nothing about rows or the database.
- **Domain objects / collections** delegate persistence to the mapper via `write()` / `save()`; no SQL, no conversion.
- **Query / projection objects** compose parameterized read queries and return **read models** (projections); no writes, no write-row conversion.
- **Services** orchestrate use-cases, thread the acting user, and enforce invariants the schema cannot (under cr-sqlite): natural-key uniqueness, cross-column coupling, required-attribute completeness. **No SQL, no conversion.**

### One mapper per aggregate — never a god-object

A mapper is bound to **one aggregate**: a root entity plus the rows saved/loaded **with** it. It is not a catch-all for a subject area.

- A **simple** entity is one model, one table, one mapper (`UnitDimension` → `UnitDimensionMapper`).
- A **compound** aggregate is a root plus rows that have no independent lifecycle and are always written with it — across several tables, behind **one** mapper (an `AttributeDefinition` with its allowed prefixes, enum values, components; an `Item` with its category memberships and relationships).
- **Distinct, independently-referenced entities get distinct mappers.** A dimension, a unit multiplier, a prefix, an attribute definition, a manufacturer are separate aggregates → separate mappers. Lumping them into one `SchemaRegistryMapper` / `ItemMapper`-that-also-writes-manufacturers is the god-object antipattern and fails review.
- "Schema registry," "catalog," etc. are **layers / work units**, not aggregates. One **unit** below may therefore deliver **several** aggregate mappers — one per aggregate.
- **Single-writer-per-table** holds: each table is written by exactly one mapper; reads cross freely.
- Aggregate boundaries listed per unit are the default; confirm each at unit start against this rule (is the child row meaningless without its root and always written with it? → owned/compound; else → its own mapper).

### Converter naming

- A mapper that maps a **single** entity type names its converters **`_from_row` / `_to_row`** — the class already identifies the type; an entity prefix would be noise.
- A **compound** mapper that maps several types names one converter per type: **`_<entity>_from_row` / `_<entity>_to_row`** (e.g. `_definition_from_row`, `_enum_value_from_row`) to disambiguate.

If a unit puts a `_*_from_row` on anything but its aggregate's mapper, makes the session/service convert a row, lumps unrelated aggregates into one mapper, or prefixes converters on a single-entity mapper, it fails review.

---

## 2. The Uniform Unit Template

A unit delivers **one mapper per aggregate it owns** (plus any query objects and one service). Each mapper is built with this sequence:

```
- [ ] Step 1  Read the unit spec (§4/§5) + the worked example (§3) + the compact standards files
              (agent/standards-repository.md, -sql, -data-models, -testing, -error-handling).
              Identify aggregate boundaries: which root + owned rows each mapper covers.
- [ ] Step 2  Per aggregate: write the failing round-trip test (add -> load -> model equality).
- [ ] Step 3  Run -> FAIL (mapper not defined).
- [ ] Step 4  Implement the aggregate's mapper: SQL as named class constants (column-explicit,
              parameterized, traceability comment, full join syntax); row<->model conversion as
              private `_from_row`/`_to_row` (single-entity) or `_<entity>_from_row`/`_<entity>_to_row`
              (compound) ON THAT MAPPER; single- and batch-form load/write; NO commit().
- [ ] Step 5  Run -> PASS.
- [ ] Step 6  Add remaining mapper tests: batch round-trip, owned-row round-trip, soft-delete
              exclusion, load/list.
- [ ] Step 7  Write failing tests for the unit's query/projection objects and service methods.
- [ ] Step 8  Implement query objects (parameterized reads -> read models) and the service
              (orchestrates the unit's mappers within a session transaction; threads acting user;
              enforces uniqueness/coupling; raises typed errors). Service does NO SQL, NO conversion.
- [ ] Step 9  Run full suite -> green; ruff clean; CRR guard clean (if a migration changed).
- [ ] Step 10 Self-verify (paste real green output), then request code review against this spec + DoD.
- [ ] Step 11 Address review, then **request explicit user authorization** before committing.
              Only after that authorization, commit `feat(<unit>): <summary>`. **This applies
              to every unit, every time** — neither the template nor any prior approval grants
              standing authorization for subsequent commits (CLAUDE.md, program plan §8).
```

**Definition of Done** = program plan §5.

---

## 3. Worked Canonical Example — `UnitDimensionMapper` (a single-entity aggregate)

`UnitDimension` is a simple aggregate: one model, one table (`unit_dimension`), one mapper. Because it maps a single type, its converters are the unprefixed `_from_row` / `_to_row`.

**Aggregate:** `UnitDimension`. **Single writer of `unit_dimension` and no other table.**
**Model:** `models/schema/unit_dimension.py`.
**Files:** `src/thinghound/mappers/unit_dimension_mapper.py`; tests `tests/mappers/test_unit_dimension_mapper.py`.

- [ ] **Step 2 — failing round-trip test** (`tests/mappers/test_unit_dimension_mapper.py`):

```python
"""UnitDimensionMapper round-trips a unit dimension exactly."""

from thinghound.mappers.unit_dimension_mapper import UnitDimensionMapper
from thinghound.models.schema.unit_dimension import UnitDimension
from thinghound.types import new_id


def test_dimension_round_trip(conn):
    mapper = UnitDimensionMapper()
    dim = UnitDimension(id=new_id(), name="Resistance", base_unit="ohm")
    mapper.add(conn, dim)
    assert mapper.load(conn, dim.id) == dim


def test_deleted_dimension_excluded_from_active_list(conn):
    mapper = UnitDimensionMapper()
    dim = UnitDimension(id=new_id(), name="Mass", base_unit="gram",
                        deleted_at="2026-01-01T00:00:00Z")
    mapper.add(conn, dim)
    assert dim.id not in [d.id for d in mapper.list_active(conn)]
```

- [ ] **Step 4 — the aggregate mapper** (`unit_dimension_mapper.py`). Single entity → converters are `_from_row` / `_to_row`. Conversion lives here and nowhere else.

```python
"""Aggregate mapper for the UnitDimension aggregate (one entity, one table).

Single source of truth for unit_dimension SQL, physical layout, and row<->model
conversion. Single writer of unit_dimension. Never calls commit().
"""

import sqlite3
import uuid

from thinghound.models.schema.unit_dimension import UnitDimension
from thinghound.value.temporal import epoch_to_iso, iso_to_epoch


class UnitDimensionMapper:
    """Maps the UnitDimension aggregate. Conversion lives here and nowhere else;
    the session, services, and domain objects do not convert rows."""

    _LOAD = """
        -- unit_dimension: load single row by primary key
        SELECT
            ud.id,
            ud.name,
            ud.base_unit,
            ud.deleted_at,
            ud.created_by_user_id,
            ud.updated_by_user_id
        FROM unit_dimension AS ud
        WHERE ud.id = ?
    """

    _LIST_ACTIVE = """
        -- unit_dimension: list non-deleted rows ordered by name
        SELECT
            ud.id,
            ud.name,
            ud.base_unit,
            ud.deleted_at,
            ud.created_by_user_id,
            ud.updated_by_user_id
        FROM unit_dimension AS ud
        WHERE ud.deleted_at IS NULL
        ORDER BY ud.name
    """

    _INSERT = """
        -- unit_dimension: insert new row
        INSERT INTO unit_dimension (
            id, name, base_unit, deleted_at,
            created_by_user_id, updated_by_user_id
        ) VALUES (?, ?, ?, ?, ?, ?)
    """

    # --- row <-> model conversion: PRIVATE METHODS ON THE MAPPER (the only converter).
    #     Single-entity mapper, so the unprefixed _from_row / _to_row names are used. ---

    def _from_row(self, row: sqlite3.Row) -> UnitDimension:
        # Converts ids (bytes<->UUID) AND timestamps (epoch-int<->ISO-8601).
        return UnitDimension(
            id=uuid.UUID(bytes=row["id"]),
            name=row["name"],
            base_unit=row["base_unit"],
            deleted_at=epoch_to_iso(row["deleted_at"]) if row["deleted_at"] is not None else None,
            created_by_user_id=(uuid.UUID(bytes=row["created_by_user_id"])
                                if row["created_by_user_id"] else None),
            updated_by_user_id=(uuid.UUID(bytes=row["updated_by_user_id"])
                                if row["updated_by_user_id"] else None),
        )

    def _to_row(self, d: UnitDimension) -> tuple:
        return (
            d.id.bytes,
            d.name,
            d.base_unit,
            iso_to_epoch(d.deleted_at) if d.deleted_at is not None else None,
            d.created_by_user_id.bytes if d.created_by_user_id else None,
            d.updated_by_user_id.bytes if d.updated_by_user_id else None,
        )

    # --- load/write API: returns/accepts domain models only ---

    def load(self, conn: sqlite3.Connection, id: uuid.UUID) -> UnitDimension | None:
        row = conn.execute(self._LOAD, (id.bytes,)).fetchone()
        return self._from_row(row) if row else None

    def list_active(self, conn: sqlite3.Connection) -> list[UnitDimension]:
        return [self._from_row(r) for r in conn.execute(self._LIST_ACTIVE)]

    def add(self, conn: sqlite3.Connection, d: UnitDimension) -> None:
        conn.execute(self._INSERT, self._to_row(d))

    def add_batch(self, conn: sqlite3.Connection, ds: list[UnitDimension]) -> None:
        conn.executemany(self._INSERT, [self._to_row(d) for d in ds])
```

### When the aggregate is compound (the prefixed form)

`AttributeDefinition` owns rows that are meaningless without it and always written with it — `attribute_allowed_prefix`, `attribute_enum_value`, `attribute_component`. They live behind **one** `AttributeDefinitionMapper`, which maps several types, so its converters are prefixed:

```python
class AttributeDefinitionMapper:
    """Maps the AttributeDefinition aggregate: the definition root plus its owned
    allowed-prefix, enum-value, and component rows. Single writer of all four tables."""

    def _definition_from_row(self, row): ...     # attribute_definition
    def _enum_value_from_row(self, row): ...      # attribute_enum_value
    def _component_from_row(self, row): ...       # attribute_component
    def _allowed_prefix_from_row(self, row): ...  # attribute_allowed_prefix
    def load(self, conn, id): ...                 # assembles the whole aggregate
```

- [ ] **Step 8 — query object + service + registry wiring (U1 scope).**
  - `schema_resolution_query.py`: a **query object** resolving a category's attribute set with inheritance + child override via a recursive CTE, returning a read-model `AttributeSchema` (backs `schema.getResolvedSchema`). Writes nothing.
  - `schema_service.py`: exposes `schema.getDimensions()`, `getAttributeCategories()`, `getResolvedSchema(...)`; validates `*_code` against the loaded code tables; enforces `(name, attribute_category_id)` uniqueness via `AttributeDefinitionMapper` with a typed error. **No SQL, no conversion** — calls the unit's mappers inside a `session.transaction()`.
  - Wire `AppRegistry.load(session)` to populate dimensions (`UnitDimensionMapper`), multipliers (`UnitMultiplierMapper`), prefix sets/prefixes (`PrefixSetMapper`/`PrefixMapper`), attribute categories (`AttributeCategoryMapper`), attribute definitions (`AttributeDefinitionMapper`), and the `factors_for(dimension_id)` map (exact `Fraction` factors) — **via the mappers**, not ad-hoc SQL.

- [ ] **Behavioral tests U1 must include:** dimension round-trip + batch; multiplier round-trip; attribute-definition aggregate round-trip incl. owned enum values/components; soft-delete exclusion; service-enforced `(name, attribute_category_id)` uniqueness; scale-per-attribute respected (two attributes, same dimension, different scales); `factors_for` returns exact factors.

Every later unit follows this shape: identify its aggregates, one mapper each, converters named per the §1 rule.

---

## 4. Phase 1a — Vertical Slice Units (sequential; each unwraps the next)

Each is one subagent + review and delivers **one mapper per aggregate** (listed under "Aggregate mappers"; single-entity unless noted "compound"). No two mappers write the same table. Gate B is reached when U6 feeds the UI demo with real data.

### U1 — Structure / Schema Registry — the worked example (§3). Wires `AppRegistry.load`. Blocks all other units.
- **Aggregate mappers:** `UnitDimensionMapper` (`unit_dimension`) · `UnitMultiplierMapper` (`unit_multiplier`) · `PrefixSetMapper` (`prefix_set`) · `PrefixMapper` (`prefix`) · `AttributeCategoryMapper` (`attribute_category`) · `AttributeDefinitionMapper` *(compound: `attribute_definition` + `attribute_allowed_prefix` + `attribute_enum_value` + `attribute_component`)*.
- **Query/service:** `schema_resolution_query.py`, `schema_service.py`.

### U2 — Category
- **Aggregate mappers:** `CategoryMapper` *(compound: `category` + its `category_attribute` bindings)* · `DisplayProfileMapper` (`display_profile`).
- **Behaviors/tests:** CRUD + soft-delete; a **query object** for recursive-CTE ancestry/descendants; attribute-set resolution with inheritance + `is_override` (drives `schema.getResolvedSchema(categoryId)`); reparent updates `parent_id` and refreshes the registry ancestry cache.
- **Backs:** `schema.getResolvedSchema`, the left-pane tree.

### U3 — Item
- **Aggregate mappers:** `ItemMapper` *(compound: `item` + `item_category` + `item_relationship`)* · `ManufacturerMapper` (`manufacturer`) · `ProductSeriesMapper` *(compound: `product_series` + `series_attribute_default`)*. *(Three distinct aggregates — not one mapper.)*
- **Behaviors/tests:** item aggregate round-trip; **service-enforced** uniqueness — `sku` (`DuplicateSkuError`), `(manufacturer_id, part_number)` MPN, GPN where manufacturer absent; primary category is the single `item.primary_category_id` cell; variant navigation (`getVariants`); series auto-populate (§5.1) → attribute values with `provenance = T` (coordinates with U4).
- **Backs:** `items.create/update/softDelete/getVariants`.

### U4 — Attribute Values
- **Aggregate mappers:** `ItemAttributeValueMapper` *(compound: `item_attribute_value` + `item_attribute_component_value`)*.
- **Behaviors/tests:** the **value write path** (§5.4) in the service — fraction preprocessor → registry `factors_for` → `encode_scaled(base, scale)` where **scale comes from the `attribute_definition`** → mapper stores `value_scaled`+`value_exact`+`value_raw`+`display_unit`+`provenance`; Integer-typed attribute rejects fractional input; composite components one row each; a **parametric search query object** (range/equality on `(attribute_id, value_scaled)`, AND/OR leaves, unit-converted thresholds, dimension-wide search); service enforces `(value_scaled IS NULL) = (value_exact IS NULL)`.
- **Backs:** `attrs.setValue`, `attrs.setComponentValue`, filter-predicate evaluation.

### U5 — Inventory Events
- **Aggregate mappers:** `InventoryEventMapper` (`inventory_event`, LOG) · `ItemInstanceMapper` (`item_instance`) · `CurrencyMapper` (`currency`) · `FxRateMapper` (`fx_rate`). **LOCAL** read-model tables (`rm_item_stock`, `rm_stock_by_location`, `rm_instance_state`) are maintained by DB triggers + a full-rebuild routine owned by this unit and read via query objects — not write-aggregate mappers.
- **Behaviors/tests:** append-only insert with `(effective_date, hlc, id)` ordering (query object derives balances); on-hand = bulk pool + Σ instances; **INDIVIDUATE nets to zero**; service requires ADJUST reason and MOVE source+dest; negative-balance block at source; **trigger-maintained aggregates equal full rebuild** (consistency oracle, `architecture.md §5.3/§8`); weighted-average + FIFO costing replay stable under shuffled/back-dated/tie events.
- **Backs:** `inventory.addEvent/getLedger/getBalances/individuate/mergeToBulk`.

### U6 — Grid Query (Gate B deliverable)
- **Aggregate mappers:** `DisplayColumnMapper` (`display_column`) · `CategoryColumnMappingMapper` (`category_column_mapping`) · `GridConfigurationMapper` *(compound: `grid_configuration` + `grid_configuration_column` + `grid_configuration_grouping`)*.
- **Behaviors/tests:** the **heterogeneous grid query object** — `grid.queryItems(...)` resolves each global Display Column through each row's primary-category column mapping (direct attribute / composite component / built-in field / instance-measurement aggregate / display formula / blank), returning grid **read-model** rows with display values **plus `value_exact`** so the UI does no float math; sort/filter on resolved `value_scaled`/`value_text`; hero column; AGGREGATED instance display; grid-config CRUD + default-per-scope (single cell). Joins `rm_item_stock` for `on_hand`.
- **Backs:** `grid.getDisplayColumns/getColumnMappings/queryItems/getConfigurations/saveConfiguration/setDefaultConfiguration`.

- [ ] **Gate B:** U1–U6 green + reviewed; the UI demo's dummy bridge is swapped for real `grid.*`/`schema.*` services and a seeded item renders in the real grid.

---

## 5. Phase 1b — Parallel Fan-Out Units

After Gate B, dispatch in parallel (superpowers:dispatching-parallel-agents). No two mappers share a writer table. Each unit delivers one mapper per aggregate (single-entity unless noted "compound").

| Unit | Aggregate mappers (writer tables) | Key behaviors / tests | Backs |
|------|-----------------------------------|------------------------|-------|
| **Vendors & Offers** | `VendorMapper` (`vendor`) · `VendorOfferMapper` *(compound: `vendor_offer` + `price_break`)* | offer per `(item,vendor)`; soft-unique `(item,vendor,vendor_sku)` service-enforced; breaks by `qty_min`; replacement cost = lowest active-offer tier in home currency | Vendors tab |
| **Offer History & Costing** | `OfferHistoryMapper` (`offer_history`, LOG) | append snapshot; price/availability trend query object; FX roll-up via `fx_rate` (read) | offer history; roll-ups |
| **Locations** | `LocationMapper` (`location`) | recursive-CTE hierarchy query; per-location balances (reads `inventory_event`); scope selector | locations workspace |
| **Instances depth** | *(no new writer tables; reads U5 aggregates)* | measurement current-value = latest `(measured_at,hlc,id)`; assign/waste/lost | Instances tab, `instances.measure` |
| **Projects** | `ProjectMapper` (`project`) | CRUD + status; consumption linkage | project picker |
| **Tags & FTS** | `TagMapper` *(compound: `tag` + `item_tag`)*; **LOCAL** `fts_item` via triggers/query | trigram FTS over names/desc/SKU/MPN/markings/refdes/tags; each dimensional value indexed as-entered **and** canonical; unit-aware quick-search routing | §3.14 search |
| **Attachments** | `AttachmentMapper` (`attachment`); **LOCAL** `rm_thumbnail` | polymorphic owner; path-traversal rejected at service; lazy Pillow thumbnails | Assets, thumbnail column |
| **BOM & Build basics** | `BomMapper` *(compound: `bom` + `bom_revision` + `bom_line` + `bom_line_substitute`)* · `BuildMapper` (`build`) | DRAFT→RELEASED→OBSOLETE (released immutable); buildable qty = min floor(avail/qty_per); simple build emits CONSUME (+optional ADD); where-used query | BOM workspace, `bom.*` |
| **Invoices** | `InvoiceMapper` *(compound: `invoice` + `invoice_line`)* · `ImportTemplateMapper` (`import_template`) | ingest→match(P1 vendor_sku, P2 MPN+mfr, P3 fuzzy FTS, P4 new)→reconcile→atomic commit; duplicate warning | invoice import |
| **Procurement** | *(no new writer tables; reads many)* | buy-list from low-stock + BOM shortage; group by vendor; cheapest honoring MOQ/multiple/breaks/availability; CSV export | procurement workspace |
| **Settings & Users** | `AppSettingMapper` (`app_setting`) · `DeviceSettingMapper` (`device_setting`, LOCAL) · `UserMapper` (`user`) | seed local user (day-one); home currency/default units/costing method | settings; acting-user context |
| **Onboarding & Seed packs** | *(no new writer tables; orchestrates other services)* | seed packs (units, attribute categories, attributes, starter categories); import/export schema packs | first-run wizard |

- [ ] **Gate C:** all Phase-1b units green + reviewed. Hand to integration + PyInstaller packaging.

---

## 6. Self-Review (against the specs)

- **Aggregate boundaries:** every mapper owns exactly one aggregate (root + owned rows); no mapper spans unrelated entities; single-entity mappers use `_from_row`/`_to_row`, compound mappers use `_<entity>_from_row` per type. Re-verify per unit.
- **Bridge coverage:** `functional-spec.md §6` maps onto units — `schema.*`→U1/U2, `items.*`→U3, `attrs.*`→U4, `inventory.*`→U5, `grid.*`→U6, `instances.*`/`bom.*`/`procurement.*`/`invoice.*`/`settings.*`→Phase 1b. `formula.*`/`sync.*` are Phase 2/4.
- **Single-writer integrity:** the "Aggregate mappers" column is authoritative; no table is written by two mappers.
- **Conversion boundary:** the session, services, domain objects, collections, and query objects convert nothing; `*_code` stays `str`; ids cross as `bytes`↔`UUID` in the mapper and `str(id)` at the bridge; timestamps as epoch-int↔ISO-8601 in the mapper; scale read from the `attribute_definition` in the U4 write path.
