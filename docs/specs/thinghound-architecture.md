# ThingHound — Architecture Specification

**Date:** 2026-06-03
**Companion documents:** `thinghound-functional-spec.md`, `thinghound-data-model.md`

---

## 1. Philosophy & Design Principles

- **No ORM.** All SQL is hand-written, parameterized, and owned by aggregate mappers. No SQL appears in service, domain, or UI code.
- **Exact arithmetic everywhere.** No `REAL` for any value, quantity, or money. The Python→SQLite path uses exact rationals and `Decimal`; the storage path uses scaled integers and exact decimal text.
- **The mapper is the dialect seam.** Every table's SQL lives in exactly one aggregate mapper. Swapping the database backend means writing new mappers; nothing above the mapper layer changes.
- **Local-first correctness.** The schema is CRDT-ready from day one. cr-sqlite compatibility rules are enforced by a CI guard before any migration is merged.
- **Derived data is LOCAL.** Nothing computed from sources is synced. Read-model tables, FTS indexes, and stock aggregates are rebuilt from CRR/LOG sources after every sync merge and maintained incrementally by DB-side triggers for local writes.
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
| **Sync** | cr-sqlite (loadable CRDT extension) | Conflict-free multi-writer merge, tombstones, column-level LWW. Bundled per-OS binary. |
| **DB driver** | `sqlite3` stdlib | Raw parameterized SQL, registered `Decimal`/`Money` type adapters. |
| **Formula engine** | simpleeval + Pint | Allowlisted operators for computed attributes and display formulas. Best-effort isolation of user-authored formulas. |
| **PDF extraction** | PyMuPDF (Phase 3) | Datasheet text and bounding-box extraction. |
| **Thumbnails** | Pillow | Generated lazily; cached in LOCAL table. |
| **Packaging** | PyInstaller (onedir) | Bundles webview dependencies and cr-sqlite binary. |
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
│  │ SQLite     │  │ cr-sqlite    │  │ Local FS      │ │
│  │ FTS5/JSON1 │  │ (CRDT/CRR)   │  │ attachments   │ │
│  └─────┬──────┘  └──────┬───────┘  └───────────────┘ │
└────────┼────────────────┼────────────────────────────┘
         │ (optional)     │ changesets
    Litestream            ▼
    backup → S3/B2    Peer devices (sync)
```

---

## 4. Persistence Architecture

The persistence layer is organized in discrete layers. Each layer depends only on layers below it; SQL never leaks upward past the aggregate mapper.

### 4.1 Models (`models/`)

Pure data. Frozen Pydantic `BaseModel` for domain entities; frozen dataclasses for value objects where instantiation overhead matters. Responsibilities: structure, field validation, serialization/deserialization, value conversion at domain boundaries. No SQL, no connections, no I/O. The physical encoding of domain types is the mapper's concern, not the model's.

### 4.2 Aggregate Mappers

The single source of truth for persisting a domain aggregate. An aggregate is a root entity and the rows it is saved and loaded with — not a table, not a single model.

- A simple entity maps to one table; a compound entity (e.g., an item with its attribute values) maps to several physical tables via one mapper.
- Each mapper owns: column lists, table names and aliases, all SELECT / INSERT / UPDATE / DELETE SQL, single and batch (`executemany`) forms, and all row ↔ model mapping. `_row_to_*` free functions are an antipattern — row mapping belongs on the mapper that owns the type.
- **The physical schema is an implementation detail inside the mapper.** The mapper can normalize, denormalize, split hot/cold columns, or partition across tables without changing any consumer.
- **Single-writer-per-table invariant:** a mapper may own many tables, but each table is written by exactly one aggregate mapper. Reads may cross freely.
- The mapper is the dialect seam: per-backend implementations (`SqliteItemMapper`, later `PostgresItemMapper`) sit behind a common interface. The domain layer, session, and registry never see dialect-specific SQL.

### 4.3 Domain Objects (operational data)

Wrap a model instance plus a session reference. Self-maintaining: `write()`, `reload()`, `delete()` delegate to the aggregate's mapper. This gives `item.write()` / `instances[1].reload()` ergonomics without duplicating SQL onto the instance.

### 4.4 Collections

Batch-first containers of domain objects. `items.save()` is one batched statement in one transaction — not a per-row loop. The collection is the normal unit of work for grid loads, search results, and bulk imports; the single-row path is the degenerate case.

### 4.5 Query / Projection Objects (read side)

Compose fully parameterized queries (every value bound, never interpolated) using mapper column metadata, joining and aggregating across whatever tables are needed. Return purpose-built read models shaped for the caller (e.g., a grid row with computed display values). This is where join SQL and dynamic `WHERE` / `ORDER BY` / `GROUP BY` assembly live.

The dynamic WHERE/sort assembly is in-house: a small bespoke parameter-binding builder. SQLGlot may be used at dev/test time to validate composed SQL, but is not a runtime dependency.

### 4.6 Session / Unit of Work

Owns the connection, the transaction scope, and the session-level identity map (cache). Exposes mappers, domain objects, collections, and query entry points. **Knows no table SQL.** Transaction management — `BEGIN` / `COMMIT` / `ROLLBACK` — is the session's responsibility, not the mapper's or domain object's. No `commit()` is called inside any mapper or `write()` method; callers compose multi-aggregate writes into one transaction.

### 4.7 AppRegistry (configuration / structure layer)

Config and structure (unit dimensions, prefix sets, unit multipliers, attribute categories, attribute definitions, category trees, grid configurations) is loaded once at startup through the same mappers and held in memory for the session. The application is unconfigured until the registry loads. Structure objects are effectively immutable session singletons. Rare structure edits go through the structure aggregate's mapper and trigger a registry refresh. Structure and operational data are distinct layers; operational data depends on the registry.

---

## 5. Read Model & Query Strategy

### 5.1 No Pre-Materialized Grid

Grid display values are computed at query time. Pre-materialized grid rows create tight coupling between attribute definitions (scale, display unit) and cached display strings — a scale change would require cascading updates across all affected items' cached rows. With well-designed indexes, query-time computation is fast at realistic catalog sizes and avoids this coupling entirely.

### 5.2 Indexes Drive Performance

All performance-critical queries use covering indexes:

- Parametric search: `(attribute_id, value_scaled)` on `item_attribute_value` — O(log n) range scan.
- Text search: FTS5 external-content table with trigram tokenizer.
- Sort by attribute: same `(attribute_id, value_scaled)` index.
- Category traversal: `parent_id` index on `category` and `location`; recursive CTEs.
- Event replay/costing: `(item_id, effective_date, hlc, id)` on `inventory_event`.

### 5.3 LOCAL Stock Aggregates

Stock quantities (`rm_item_stock`, `rm_stock_by_location`, `rm_instance_state`) are pre-aggregated from events in LOCAL tables. These are the exception to query-time computation because event-log aggregation at query time over large event histories would be expensive. They are maintained by DB-side triggers on `inventory_event` and rebuilt in full after a sync merge.

### 5.4 Sync Merge Rebuild

After every sync merge, all LOCAL derived tables are rebuilt from CRR/LOG sources in a single batch operation. Triggers are suppressed during the rebuild. For large imports, the same batch-mode path is used: insert all source rows without trigger overhead, then rebuild LOCAL tables once at the end.

---

## 6. Sync Design

### 6.1 Engine

cr-sqlite turns CRR and LOG tables into conflict-free replicated relations with column-level last-writer-wins and tracked deletes (tombstones). Each column carries causal metadata; changesets are exchanged between devices and applied independently per column.

### 6.2 Sync Classes

- **CRR** — catalog, schema, configuration, items, attribute values, vendors, BOMs, synced app settings.
- **LOG** — inventory events, instance measurements, offer history, audit log. Insert-only; no conflicts on write; merge trivially.
- **LOCAL** — device settings, all derived/cached tables. Never synced. Rebuilt after merge.

### 6.3 Identity

All PKs are `UUIDv7` (defined in `thinghound.types`, validates version byte at construction) — time-ordered and collision-free across devices without coordination. Stored as `BLOB(16)` in SQLite. Cross the JS bridge as canonical `8-4-4-4-12` strings, converted by the mapper at the storage boundary and by the bridge handler at the transport boundary.

### 6.4 Event Ordering

Events carry an HLC timestamp. Replay and costing order is `(effective_date, hlc, id)` — deterministic under back-dating, ties, and sync merges.

### 6.5 Uniqueness Under Merge

`UNIQUE` constraints are not placed on CRR tables for natural keys (SKU, MPN, manufacturer name, attribute definition names). Uniqueness is enforced by the service layer at local write time. Under sync, two devices may independently create records with the same natural key. The post-merge integrity check detects these collisions and quarantines the conflicting records for user resolution via a dedicated conflicts UI. A quarantine table holds the conflicting records with metadata describing the conflict; the user decides which is canonical and resolves accordingly.

### 6.6 Referential Integrity

Application-enforced across CRR tables (the CRDT trade-off — FK enforcement at the DB level would reject valid changesets from peers). A post-merge integrity check validates all critical references and quarantines dangling records rather than hard-failing. The check is a pure function of merged state so every replica computes identical results and converges without coordination.

### 6.7 Multi-Row Invariants Under LWW

Column-level LWW can split invariants that span multiple cells or rows. Mitigations:
- **Single-cell ownership where possible:** "exactly one primary category per item" lives in `item.primary_category_id` (one column, LWW-safe). "Default grid config per scope" lives in `category.default_grid_config_id` or an `app_setting` key.
- **Append-only groups:** INDIVIDUATE event legs are created atomically on one device and immutable. A merge that delivers legs out of order (partial sync) is tolerated; the integrity check flags a group that remains unbalanced after the full changeset applies.
- **Post-merge repair:** for any invariant not reducible to a single cell, a deterministic repair function runs after every merge. Pure function of merged state; every replica computes identical repairs.

### 6.8 cr-sqlite Compatibility Rules

All CRR and LOG table schemas must satisfy these rules (empirically verified — see `docs/dev/crsqlite-spike-findings.md`):

1. Every non-PK `NOT NULL` column must have a `DEFAULT` value. (`crsql_as_crr` rejects tables without defaults on NOT NULL columns.)
2. No cross-column `CHECK` constraints. Column changesets apply independently; a cross-column check may fire on a partial changeset and reject a valid remote update. Enforce such invariants at the application layer.
3. Single-column `CHECK` constraints are acceptable if conservative.
4. No `AUTOINCREMENT`. No `REAL`. No `REFERENCES` / `FOREIGN KEY` enforcement.
5. Schema changes to CRR/LOG tables use `crsql_begin_alter` / `crsql_commit_alter`.

A CI guard (`scripts/check_crr_rules.py`) enforces these rules on every migration file. It must cover all five rules; the guard must not pass migrations that violate any of them.

### 6.9 Transport

Changeset exchange between devices is out of scope for v1. The schema is sync-ready; the transport layer (authenticated peer channel, mobile companion) is a Phase 4 deliverable.

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
- **Repository round-trips:** every aggregate mapper: write → read → compare. Use a real in-memory SQLite connection; no mocking of the data layer.
- **Parametric search:** compound AND/OR predicates; unit-converted thresholds; composite component leaf filters; dimension-wide threshold queries.
- **Schema resolution:** attribute inheritance via recursive CTE; child overrides; multi-category union; required-field logic.
- **Inventory event semantics:** stock balance derivation; individuation net-zero; per-location and per-bucket balances.
- **Read-model correctness:** stock aggregate trigger maintenance equals full rebuild (consistency oracle).
- **Migrations:** forward apply on fixture database; checksum integrity; no CRR rule violations (CI guard).

### Sync / CRDT Tests
- **Merge scenarios:** offline edits on two replicas merge per policy; tombstones converge; post-merge integrity check runs correctly.
- **Uniqueness collision:** two replicas create the same SKU offline; post-merge quarantine fires correctly.
- **Partial individuation group:** INDIVIDUATE legs delivered across two partial syncs; integrity check tolerates mid-flight group; flags only if unbalanced after full changeset.
- **Measurement ordering:** concurrent measurements with equal or skewed `measured_at` resolve to the same current value on every replica.
- **Attribution:** every CRR/LOG write records a user; cross-device merges preserve correct attribution.

### CI
Ruff for linting. pytest suite headless. CRR-rules guard on all migration files. Python 3.14 minimum.

---

## 9. Physical Type Mapping

The logical data model (`thinghound-data-model.md`) uses database-agnostic types. This section defines how each logical type maps to a physical column type per supported DBMS. The mapper is responsible for all encoding and decoding at the storage boundary.

| Logical Type | SQLite (current) | Postgres (future) | Notes |
|---|---|---|---|
| `UUID` | `BLOB(16)` — raw bytes via `id.bytes` / `uuid.UUID(bytes=...)` | `UUID` — native | Bridge: `str(id)` / `uuid.UUID(str)` |
| `String` | `TEXT` | `TEXT` / `VARCHAR` | |
| `Integer` | `INTEGER` | `INTEGER` / `BIGINT` | |
| `Decimal` (base units) | Two columns: `*_scaled INTEGER` (base × 10^scale, indexed for sort/range) + `*_exact TEXT` (canonical decimal, source of truth for math/display) | Single `NUMERIC` column | SQLite has no exact decimal type; the dual-column encoding is a mapper implementation detail. `scale` on `attribute_definition` drives the `*_scaled` precision. |
| `Boolean` | `INTEGER` — 0 / 1 | `BOOLEAN` | |
| `Timestamp` | `TEXT` — ISO-8601 | `TIMESTAMPTZ` | |
| `Date` | `TEXT` — ISO-8601 | `DATE` | |
| `HLC` | `TEXT` | `TEXT` | Causal clock; comparable as string |
| `Money` | Two columns: `*_minor INTEGER` (amount in currency's minor units) + `*_currency TEXT(3)` (ISO 4217) | `NUMERIC` + `TEXT(3)` | SQLite has no money type; the dual-column encoding is a mapper implementation detail. |
| `Enum(…)` | `TEXT` with single-column `CHECK` | `TEXT` / `ENUM` | |
| `JSON` | `TEXT` | `JSONB` | Only for genuinely free-form content |

### SQLite-Specific Physical Constraints

When authoring SQLite DDL for CRR and LOG tables the mapper must follow cr-sqlite compatibility rules (see `docs/dev/crsqlite-spike-findings.md`). These are physical constraints of the SQLite + cr-sqlite substrate — not logical model concerns:

- Every non-PK `NOT NULL` column must have a `DEFAULT` value. (`crsql_as_crr` rejects tables without defaults on NOT NULL columns.)
- No cross-column `CHECK` constraints. Column changesets apply independently; a cross-column check may fire on a partial changeset and reject a valid remote write. Enforce such invariants at the application layer.
- Single-column `CHECK` constraints are acceptable if conservative.
- No `AUTOINCREMENT`. No `REAL` columns.
- Schema changes to CRR/LOG tables use `crsql_begin_alter` / `crsql_commit_alter`.
- The CI guard (`scripts/check_crr_rules.py`) enforces these rules on every migration file before merge.

---

## 10. Coding Standards

Coding standards are defined in `coding_standards.md` (root) with verbose detail in `docs/dev/standards-*.md` and compact agent-directed versions in `docs/dev/agent/standards-*.md`. CLAUDE.md contains task-routing rules directing agents to load the relevant compact standards file before working in each domain. Agents must read the relevant standards file before writing any code in that domain.

Key invariants (always load-bearing, not subject to debate):
- No floating-point anywhere — all domain values are `Decimal`; all money is `Money`. Physical encoding is DBMS-specific (see Type Mapping below) but is never a float.
- `UUIDv7` for all ID fields in domain models (validates version byte); canonical string only at the bridge boundary.
- `foreign_keys = OFF` on every SQLite connection (cr-sqlite requirement; referential integrity is application-enforced).
- All SQL lives in aggregate mappers. No SQL in service, domain, or UI code.
- All SQL is parameterized. No string interpolation of values.
