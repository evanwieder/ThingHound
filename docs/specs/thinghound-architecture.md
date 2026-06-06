# ThingHound — Architecture Specification

**Date:** 2026-06-06
**Companion documents:** `thinghound-functional-spec.md`, `thinghound-data-model.md`

---

## 1. Philosophy & Design Principles

- **No ORM.** SQL is built by a model-aware query component from mapper metadata, always parameterized. No SQL appears in service, domain, or UI code; no hand-written named SQL constants.
- **Exact arithmetic everywhere.** No `REAL` for any value, quantity, or money. The Python→SQLite path uses exact rationals and `Decimal`; the storage path uses scaled integers and exact decimal text.
- **The mapper is the dialect seam.** Every table's SQL lives in exactly one aggregate mapper. Swapping the database backend means writing new mappers; nothing above the mapper layer changes.
- **Derived data is computed, not synced.** Read-model tables, FTS indexes, and stock aggregates are derived from source data and maintained incrementally by DB-side triggers. They are rebuilt in full when needed.
- **Query-time display, index-time sort/filter.** Grid display values are computed at query time from well-indexed source tables. Pre-materialization is limited to stock aggregates. No application-side projector.

---

## 2. Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Desktop shell** | PyWebView (OS-native webview) | Avoids bundling Chromium. WebKitGTK on Linux is the known packaging risk; cross-engine test matrix required. |
| **UI transport** | PyWebView JS bridge only | No localhost TCP surface → smaller attack surface. A clean service layer behind the bridge allows a future authenticated loopback API for mobile sync without rework. |
| **Frontend grid** | Tabulator (MIT) | Native tree data, row grouping, virtual DOM, inline typed editors, column reorder/hide. |
| **Domain models** | Pydantic v2 (frozen) | API/bridge contracts, domain entity validation. |
| **Unit conversion** | Pint + exact rational preprocessing | All conversion through exact rationals/Decimal — Pint's float default is bypassed. Fraction-aware preprocessor normalizes input before Pint parsing. |
| **Templating** | Jinja2 | Name templates, LTspice generation. |
| **Database** | SQLite (FTS5 + JSON1, WAL mode) | Single file. FTS5 trigram for fuzzy search. |
| **Sync** | Turso / libSQL | Local embedded replica syncs to a Turso primary. Single-user, non-simultaneous. Conflict reconciliation deferred. |
| **DB driver** | `sqlite3` stdlib | Raw parameterized SQL, registered `Decimal`/`Money` type adapters. |
| **Formula engine** | simpleeval + Pint | Allowlisted operators for computed attributes and display formulas. Best-effort isolation of user-authored formulas. |
| **PDF extraction** | PyMuPDF (Phase 3) | Datasheet text and bounding-box extraction. |
| **Thumbnails** | Pillow | Generated lazily; cached in derived read-model table. |
| **Packaging** | PyInstaller (onedir) | Bundles webview dependencies. |
| **Backup** | Litestream (optional) | WAL streaming to object storage. Backup only — not sync. |
| **Analytics (Phase 4)** | DuckDB | Read-only replica over the SQLite file; periodic refresh; never transactional. |

---

## 3. Runtime Architecture

```
┌──────────────────────────────────────────────────────┐
│  PyWebView Window (OS-native web engine)              │
│   Tabulator grid · dynamic columns                    │
│   Inline typed editors · parametric filter bar        │
└────────────────────┬─────────────────────────────────┘
                     │ JS Bridge (no TCP)
┌────────────────────▼─────────────────────────────────┐
│  Python Application Core                              │
│                                                       │
│  Service Layer (use-cases, authorization hook point)  │
│   ├─ Jinja2 name rendering                            │
│   ├─ Pint unit normalization                          │
│   ├─ simpleeval formula engine                        │
│   └─ Session (connection, unit-of-work, identity map) │
│        │                                              │
│  Persistence Layer                                    │
│   ├─ AppRegistry (config/structure in memory)         │
│   ├─ Aggregate Mappers (all SQL lives here)           │
│   ├─ Domain Objects + Collections                     │
│   └─ Query / Specification Objects                    │
│        │                                              │
│  ┌─────▼──────┐  ┌──────────────┐  ┌───────────────┐ │
│  │ libSQL     │  │ Turso        │  │ Local FS      │ │
│  │ FTS5/JSON1 │  │ primary      │  │ attachments   │ │
│  └─────┬──────┘  └──────┬───────┘  └───────────────┘ │
└────────┼────────────────┼────────────────────────────┘
         │ (optional)     │ sync (single-user)
    Litestream            ▼
    backup → S3/B2    Turso cloud primary
```

---

## 4. Persistence Architecture

The persistence layer is organized in discrete layers. Each layer depends only on layers below it; SQL never leaks upward past the aggregate mapper.

### 4.1 Models (`models/`)

Pure data. Frozen Pydantic `BaseModel` for domain entities; frozen dataclasses for value objects where instantiation overhead matters. Responsibilities: structure, field validation, serialization/deserialization, value conversion at domain boundaries. No SQL, no connections, no I/O. The physical encoding of domain types is the mapper's concern, not the model's.

### 4.2 Aggregate Mappers

The single source of truth for persisting a domain aggregate. An aggregate is a root entity and the rows it is saved and loaded with — not a table, not a single model.

- A simple entity maps to one table; a compound entity (e.g., an item with its attribute values) maps to several physical tables via one mapper.
- Each mapper owns: column lists, table names and aliases, and all row ↔ model mapping. SQL itself is built by the model-aware query component (§4.5) from mapper-provided metadata; the mapper does not hand-write SQL strings. `_row_to_*` free functions are an antipattern — row mapping belongs on the mapper that owns the type. A single-entity mapper names its converters `_from_row` / `_to_row`; a compound mapper that owns several entity types prefixes each pair with the entity name (`_<entity>_from_row` / `_<entity>_to_row`, e.g. `_definition_from_row`, `_enum_value_from_row`) to disambiguate.
- **The physical schema is an implementation detail inside the mapper.** The mapper can normalize, denormalize, split hot/cold columns, or partition across tables without changing any consumer.
- The mapper is the dialect seam: per-backend implementations (`SqliteItemMapper`, later `PostgresItemMapper`) sit behind a common interface. The domain layer, session, and registry never see dialect-specific SQL.

### 4.3 Domain Objects (operational data)

Wrap a model instance plus a session reference. Self-maintaining: `write()`, `reload()`, `delete()` delegate to the aggregate's mapper. This gives `item.write()` / `instances[1].reload()` ergonomics without duplicating SQL onto the instance.

### 4.4 Collections

Batch-first containers of domain objects. `items.save()` is one batched statement in one transaction — not a per-row loop. The collection is the normal unit of work for grid loads, search results, and bulk imports; the single-row path is the degenerate case.

### 4.5 Query Component (read side)

A model-aware query component builds all SQL. Callers express **intent only** — the entity, the projection they need, the predicate, the ordering — and never decide how the query is assembled. Construction and strategy live inside the component and are chosen per use case. Joins derive from the model's declared relationships. SQL is assembled from curated pieces; every value is bound (never interpolated) and identifiers come only from metadata. The component returns purpose-built read models shaped for the caller (e.g., a grid row with computed display values).

The component is in-house. SQLGlot may be used at dev/test time to validate composed SQL, but is not a runtime dependency. (Detailed generator behavior — projection/aggregate declaration, EAV filter strategy, expression surface — is in-progress and not yet final.)

### 4.6 Session / Unit of Work

Owns the connection, the transaction scope, and the session-level identity map (cache). Exposes mappers, domain objects, collections, and query entry points. **Knows no table SQL and performs no row↔model conversion** — both are exclusively the aggregate mapper's responsibility. Transaction management — `BEGIN` / `COMMIT` / `ROLLBACK` — is the session's responsibility, not the mapper's or domain object's. No `commit()` is called inside any mapper or `write()` method; callers compose multi-aggregate writes into one transaction.

### 4.7 AppRegistry (configuration / structure layer)

Config and structure (unit dimensions, prefix sets, unit multipliers, attribute domains, attributes, category forest, grid layouts) is loaded once at startup through the same mappers and held in memory for the session. These are the integer-keyed structure tables. The application is unconfigured until the registry loads. Structure objects are effectively immutable session singletons. Rare structure edits go through the structure aggregate's mapper and trigger a registry refresh. Structure and operational data are distinct layers; operational data depends on the registry.

---

## 5. Read Model & Query Strategy

### 5.1 No Pre-Materialized Grid

Grid display values are computed at query time. Pre-materialized grid rows create tight coupling between attributes (scale, display unit) and cached display strings — a scale change would require cascading updates across all affected items' cached rows. With well-designed indexes, query-time computation is fast at realistic catalog sizes and avoids this coupling entirely.

### 5.2 Indexes Drive Performance

All performance-critical queries use covering indexes:

- Parametric search: `(attribute_id, value_scaled)` on `item_attribute_value` — O(log n) range scan.
- Text search: FTS5 external-content table with trigram tokenizer.
- Sort by attribute: same `(attribute_id, value_scaled)` index.
- Category traversal: `parent_id` index on `category` and `location`; recursive CTEs.
- Event replay/costing: `(item_id, effective_date, hlc, id)` on `inventory_event`.

### 5.3 Derived Stock Aggregates

Stock quantities (`rm_item_stock`, `rm_stock_by_location`, `rm_instance_state`) are pre-aggregated from events into derived tables. These are the exception to query-time computation because event-log aggregation at query time over large event histories would be expensive. They are maintained by DB-side triggers on `inventory_event`. Each read-model keeps a materialized running value up to a watermark; a read returns the snapshot plus the fold of events past the watermark, so values are always correct. Aggregation advances the watermark and is compaction for performance, never required for correctness. Timing is configurable: on open, on close, every N minutes, or on demand.

### 5.4 Bulk Rebuild

For large imports or restores, derived tables are rebuilt in a single batch operation. Triggers are suppressed during the rebuild; all source rows are inserted first, then derived tables are rebuilt once at the end.

---

## 6. Sync Design

### 6.1 Engine

Sync uses **Turso / libSQL**. The application runs against a local embedded replica that optionally syncs to a Turso primary. Sync is **single-user and non-simultaneous** — one active machine at a time. There is no concurrent multi-writer merge; conflict reconciliation is **deferred** and out of scope for v1. The free tier is sufficient for the catalog scale targeted. This applies only to the SQLite/libSQL backend; the future Postgres backend has its own sync/deployment model.

### 6.2 What Syncs

- **Synced** — catalog, schema, configuration, items, attribute values, vendors, BOMs, inventory events, instance measurements, offer history, synced app settings.
- **Device-local, never synced** — `device_setting` and all derived read-model/cache tables. These are rebuilt locally; they are not part of the replica's synced set.
- **Reference / code tables** — seeded by migrations, read-only at runtime, identical everywhere.

### 6.3 Identity

Operational/transactional PKs are `UUIDv7` (from `thinghound.types`, validates version byte at construction) — time-ordered and collision-free without coordination. Structure/master-data PKs are DB-generated integers. UUIDs are stored as `BLOB(16)` in SQLite and cross the JS bridge as canonical `8-4-4-4-12` strings; integers cross as integers. The mapper converts at the storage boundary and the bridge handler at the transport boundary.

### 6.4 Event Ordering

Events carry an HLC timestamp. Replay and costing order is `(effective_date, hlc, uuid)` — deterministic under back-dating and ties.

### 6.5 Referential Integrity

Foreign keys are enforced at the database level (FK enforcement ON). With single-user, non-simultaneous sync there is no concurrent-merge scenario that would reject a peer's partial write, so the CRDT-era trade-offs (FK off, no cross-column CHECK, application-only integrity) no longer apply.

### 6.6 Transport

Replica ↔ primary sync is handled by libSQL/Turso. Hardening multi-device sync and a mobile companion are Phase 4 deliverables.

---

## 7. Security

- **JS bridge only** — no open TCP port. The attack surface is limited to bridge method calls from the webview.
- **Parameterized SQL everywhere** — no string interpolation of user values into SQL. This is enforced by the coding standards (no inline SQL outside mappers; all values bound).
- **Formula engine allowlist** — simpleeval with an explicit operator and function allowlist. Treated as best-effort isolation of the user's own formulas, not a sandbox guarantee.
- **Import parsers hardened** — malformed CSV/Excel/BOM files produce errors, not crashes. File size and MIME type validated on attachment upload.
- **Attachment paths** — files stored under the managed user-data directory with relative paths in the database. Absolute paths and path traversal rejected at the service layer.

---

## 8. Testing Strategy

### Unit Tests
- **Value encoding:** exact round-trip raw → base → `value_scaled` → base across all dimension scales; int64 headroom assertions per attribute; equality on `value_exact` (`½ W` = `.5 W`); indexed range queries return correct sets.
- **Fraction/unit parsing:** vulgar fractions, slash fractions, mixed numbers; SI and custom units; locale separators.
- **Money arithmetic:** integer minor-unit operations; multi-currency roll-ups; no float path.
- **Costing:** weighted average, FIFO; back-dated and tie-timestamp events produce stable results; replay order invariant under shuffling.
- **Formula engine:** symbol resolution; unit propagation via Pint; cycle rejection; cascade correctness.
- **BOM/build:** buildable quantity with substitutes; atomic consumption; shortage and back-order paths.

### Integration Tests
- **Repository round-trips:** every aggregate mapper: write → read → compare. Use a real in-memory libSQL/SQLite connection; no mocking of the data layer.
- **Parametric search:** compound AND/OR predicates; unit-converted thresholds; composite component leaf filters; dimension-wide threshold queries.
- **Schema resolution:** attribute inheritance via recursive CTE; child overrides and exclusions; multi-category union; required-field logic against the naming category.
- **Inventory event semantics:** stock balance derivation; individuation net-zero; per-location and per-bucket balances.
- **Read-model correctness:** watermark snapshot + tail fold equals a full rebuild (consistency oracle); current value correct regardless of when aggregation last ran.
- **Measurement ordering:** measurements with equal or skewed `measured_ts` resolve to a stable current value by `(measured_ts, hlc, uuid)`.
- **Attribution:** every write records a user.
- **Migrations:** forward apply on fixture database; checksum integrity.

### CI
Ruff for linting. pytest suite headless. Python 3.14 minimum.

---

## 9. Physical Type Mapping

The logical data model (`thinghound-data-model.md`) uses database-agnostic types. This section defines how each logical type maps to a physical column type per supported DBMS. The mapper is responsible for all encoding and decoding at the storage boundary.

| Logical Type | SQLite (current) | Postgres (future) | Notes |
|---|---|---|---|
| `UUID` | `BLOB(16)` — raw bytes via `uuid.bytes` / `uuid.UUID(bytes=...)`; `WITHOUT ROWID` table | `UUID` — native | Operational/transactional PKs. Bridge: `str(uuid)` / `uuid.UUID(str)` |
| `Integer` PK | `INTEGER PRIMARY KEY` — DB-generated rowid table | `INTEGER`/`BIGINT` identity | Structure/master-data PKs |
| `String` | `TEXT` | `TEXT` / `VARCHAR` | |
| `Integer` | `INTEGER` | `INTEGER` / `BIGINT` | |
| `Decimal` | Role-dependent — see **Decimal encoding by role** below | Single `NUMERIC` column | SQLite has no exact decimal type. `*_exact TEXT` is always the source of truth for math/display; `*_scaled INTEGER` (when present) backs indexing/sort/range. |
| `Boolean` | `INTEGER` — 0 / 1 | `BOOLEAN` | |
| `Timestamp` | `INTEGER` — epoch milliseconds (UTC) | `TIMESTAMPTZ` | Stored as an integer, never `TEXT`. The mapper encodes the model's ISO-8601 timestamp to epoch ms and decodes it back at the storage boundary. |
| `Date` | `INTEGER` — epoch milliseconds at UTC midnight | `DATE` | Stored as an integer, never `TEXT`. Mapper-encoded at the storage boundary. |
| `HLC` | `TEXT` | `TEXT` | Causal clock, not a wall-clock datetime; stays `TEXT`, compared as string. |
| `Money` | Two columns: `*_minor INTEGER` (amount in currency's minor units) + `*_currency TEXT(3)` (ISO 4217) | `NUMERIC` + `TEXT(3)` | SQLite has no money type; the dual-column encoding is a mapper implementation detail. |
| `Enum(…)` | `TEXT` with single-column `CHECK` | `TEXT` / `ENUM` | |
| `JSON` | `TEXT` | `JSONB` | Only for genuinely free-form content |

### Decimal encoding by role

`Decimal` is exact everywhere (never `REAL`), but its SQLite encoding depends on the value's role. There are three:

1. **Attribute values** — `item_attribute_value.value`, `item_attribute_component_value.value`, `instance_measurement.value`, `series_attribute_default.value`, `datasheet_extraction.value`. **Dual-column** `*_scaled INTEGER` + `*_exact TEXT`; `*_scaled` precision is the owning `attribute.scale` (or `attribute_component.scale`). Indexed for parametric search and sort.

2. **Quantities** — `inventory_event.qty_change`, `item_instance.qty_initial`, `bom_line.qty_per_assembly`, `build.qty_built`, `price_break.qty_min`/`qty_max`, `vendor_offer.moq`/`order_multiple`/`qty_available`, `offer_history.qty_available`, `invoice_line.qty`, `item.reorder_point`/`reorder_qty`/`safety_stock`, and the derived read-model `qty_*` columns. **Dual-column** `*_scaled INTEGER` + `*_exact TEXT` at a **fixed quantity scale of 6** (10⁻⁶ precision; max |qty| ≈ 9.2×10¹² in signed int64). The stock read-model aggregates and the costing/BOM logic operate on `*_scaled`.

3. **Factors and rates** — `unit_multiplier.factor`, `prefix.factor`, `fx_rate.rate`. **Single `*_exact TEXT`** canonical-decimal column; **no `*_scaled`.** These are resolved by key (unit symbol; currency + date), never range-searched, and a fixed scaled-int cannot hold the SI prefix factor range within signed int64 (e.g. quetta 10³⁰ vs quecto 10⁻³⁰ have no common scale that fits). The model field stays `Decimal`; the mapper parses the text to `Decimal`/`Fraction`.

> The fixed quantity scale (6) is a project constant defined in code (e.g. `value/quantity.py`), not per row.

### SQLite-Specific Physical Rules

Physical rules of the libSQL/SQLite substrate — not logical model concerns:

- **PKs:** operational/transactional tables use a `UUID` PK and are `WITHOUT ROWID`; structure/master-data tables use a DB-generated `INTEGER PRIMARY KEY` (normal rowid table). `AUTOINCREMENT`/sequences are permitted where useful.
- **Foreign keys are enforced** (`PRAGMA foreign_keys = ON`). Real `REFERENCES` clauses in DDL.
- No `REAL` columns (the no-float rule). `Decimal`/`Money` use the encodings above.
- Cross-column and single-column `CHECK` constraints are both permitted.
- Temporal columns (`Timestamp`, `Date`) are stored as `INTEGER` epoch values (epoch milliseconds, UTC — see the table above), never `TEXT`. The mapper encodes/decodes at the storage boundary. `HLC` remains `TEXT`.

---

## 10. Coding Standards

Coding standards are defined in `coding_standards.md` (root) with verbose detail in `docs/dev/standards-*.md` and compact agent-directed versions in `docs/dev/agent/standards-*.md`. CLAUDE.md contains task-routing rules directing agents to load the relevant compact standards file before working in each domain. Agents must read the relevant standards file before writing any code in that domain.

Key invariants (always load-bearing, not subject to debate):
- No floating-point anywhere — all domain values are `Decimal`; all money is `Money`. Physical encoding is DBMS-specific (see Type Mapping above) but is never a float.
- Integer `id` PKs for structure/master-data tables; `UUIDv7` `uuid` PKs for operational/transactional tables. FK column names signal the referenced PK type (`_id` / `_uuid`). Canonical UUID string only at the bridge boundary.
- Foreign keys enforced (`foreign_keys = ON`).
- No column name ends with a preposition (`created_ts`, not `created_at`).
- SQL is built by the model-aware query component. No SQL in service, domain, or UI code; no hand-written named SQL constants.
- All SQL is parameterized; identifiers come only from metadata.
