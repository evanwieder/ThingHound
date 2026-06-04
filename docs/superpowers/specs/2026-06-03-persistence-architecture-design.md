# Persistence Architecture — Design
# this file has been superceded but may still be used as a reference
**Date:** 2026-06-03
**Status:** Approved (pending written review)
**Supersedes:** the repository-owns-SQL / `row_to_*` shape described in the data-model and repository sections of `2026-06-03-coding-standards-design.md`; reframes several "locked" substrate decisions in project memory (see *What this supersedes*).

---

## Why this exists

The Phase-1 schema-registry repository was built as a god-object that held inline `SELECT *` queries, module-level `_row_to_*` mapping functions, and a `commit()` per write. That is the antipattern this document exists to prevent from becoming canonical.

The two principles that drive every decision below:

1. **Encapsulate logic.** Each responsibility lives behind one boundary that owns it completely. Consumers depend on the boundary, never on its internals.
2. **Eliminate inconsistent code in multiple places.** Every rule of SQL — every column list, every write path for a table — exists in exactly one authoritative location. There is no second code path that can drift or disagree.

Two further constraints shape the design:

3. **Physical-schema independence.** The database must be free to be optimized (normalize, denormalize, split hot/cold columns, add history/audit tables, partition) without changing the domain model or any consumer.
4. **Exactness and local-first.** No `REAL` anywhere; exact values only. Local-first, embedded, sync-ready.

---

## Substrate decision

- **ThingHound is a Python application.** No ORM — SQL is hand-written. No JavaScript data layer (PGlite was evaluated and rejected: it is JS/WASM-first with no production Python embedding, and runs Postgres in single-user/single-connection mode — a local niche, not a multiuser backend).
- **Storage: SQLite + cr-sqlite**, embedded single-file, with cr-sqlite providing genuine **local-first, multi-writer CRDT sync** across machines. FTS5 for search. BLOB(16) UUIDv7 ids. Exact values as scaled-integer + canonical `value_exact` text (no `REAL`).
- **Behind a dialect-neutral mapper seam.** The anti-lock-in mechanism is *the seam, not avoiding SQLite*. A Postgres (or other) backend becomes reachable later by writing new mappers — the domain layer, collections, session, and registry never change. We do not pay Postgres's operational weight, or give up local-first CRDT sync, for a multiuser-server scenario that is still speculative.

Paradigms other than relational were evaluated and rejected for this workload: key-value (LevelDB/RocksDB/LMDB) and object stores (ZODB) cannot serve ad-hoc multivariate range search without hand-built indexing and sacrifice portability; document stores (Couch/Pouch) are sync-strong but query-weak and JS-oriented; graph stores fit only the BOM/relationship facet. The dominant requirement — **parametric multivariate range search with joins, aggregation, and integrity** — is decisively relational. Flexible user-defined attributes are handled *inside* the relational model (EAV / typed attribute registry), not by going schemaless, because the schema is itself typed, validated, queryable data.

---

## The layers

Each layer states its single responsibility, what it knows, and — equally important — what it must **not** know.

### 1. Models (`models/`)

Pure data. Frozen Pydantic `BaseModel` for domain entities; frozen dataclasses for value objects where overhead matters. Responsibilities: structure, validation, serialization/deserialization, value conversion (e.g., scaled-int ↔ exact, BLOB ↔ UUID string at boundaries).

- **Knows:** its own fields and invariants.
- **Must not know:** SQL, connections, I/O, or that a database exists.

### 2. Aggregate mappers

The **single source of truth** for persisting a domain aggregate. A mapper is bound to a **persistence aggregate** — a root entity plus the rows it is saved and loaded with — **not to a table and not mechanically to a single Pydantic model**.

- A simple entity (e.g., `UnitDimension`) is one model, one table, one mapper. The 1:1 case exists; it is not the rule.
- A compound entity (e.g., an `Item` with its attribute values, markings, relationships) is one aggregate spanning **several Pydantic models and several physical tables**, persisted by **one mapper** that owns all the SQL to assemble and write the whole graph.

The mapper owns: the column lists, table names + aliases, all INSERT/UPDATE/DELETE and load-by-id SQL, single **and** batch (`executemany`) forms, and the row↔model mapping (which lives here, with the type's persistence — never as free functions in a repository). The **physical schema is an implementation detail inside the mapper**; this is what preserves physical-schema independence and database optimization freedom.

- **Knows:** the physical schema for its aggregate, and the domain model(s) it maps to/from. It is the only place that knows both.
- **Must not know:** anything about other aggregates' internals, the UI, or services.

**Invariant — single-writer-per-table:** a mapper may own many tables, but **each table is written by exactly one aggregate mapper.** Clear write-ownership without binding the mapper to a single table. Reads may cross freely (see §5).

### 3. Domain objects (operational data)

Wrap a model instance plus a session handle. Self-maintaining: `write()`, `reload()`, `delete()` delegate to the aggregate's mapper. This gives `item.write()` / `items[1].reload()` ergonomics **without** duplicating SQL onto the instance.

- **Knows:** its model and its session; how to ask its mapper to persist it.
- **Must not know:** SQL text or the physical schema.

### 4. Collections

Batch-first containers of domain objects. `items.save()` is **one batched statement in one transaction**, not a per-row loop. The collection is the normal unit of work for the grid, search results, and import; the single row is the degenerate case.

- **Knows:** its members and its session; how to ask the mapper for batched persistence.
- **Must not know:** SQL text or the physical schema.

### 5. Query / projection objects (the read side)

Dynamic parametric search and grid loading. These compose **fully parameterized** SQL (every value bound, never inlined) using mapper column metadata, joining and aggregating across whatever tables are needed, and return **purpose-built read-models** — projections shaped for the view (e.g., a grid row with combined counts and min/max instance measurements).

Read models are deliberately **not** the same as write models: you have **write models** (aggregates, persisted by mappers) and **read models** (projections, produced by query objects). A projection corresponds to no single table and to no write-aggregate. This is the concrete meaning of "the db model and the Pydantic models are not one-to-one."

- **Knows:** how to compose safe queries from mapper metadata; the read-model shapes.
- **Must not know:** how aggregates are written.

### 6. Repository / session

Owns the connection, the transaction (unit-of-work), and the session identity map / cache. Holds the mappers and exposes the collections and query entry points. Coordinates; **knows no table SQL itself.**

- **Knows:** the connection, transaction lifecycle, and the registry of mappers/queries.
- **Must not know:** the SQL of any specific table or aggregate (the mappers and query objects own that).

### 7. Registry (config / structure)

Config/structure — unit dimensions, attribute definitions, category trees, grid configurations — is loaded **once at startup** through the same mappers and held in memory; the app is unconfigured (no trees, no user, nothing) until it loads. Structure objects are effectively immutable session singletons. Rare structure edits go through the structure aggregate's mapper and refresh the registry. Structure and operational data are distinct layers; operational data depends on the registry being loaded.

---

## The mapper seam and portability

The mapper is the **only** layer that knows dialect-specific SQL and physical layout. Backend portability therefore means **per-backend mapper implementations behind a common interface** (`SqliteItemMapper`, later `PostgresItemMapper`), each with SQL hand-tuned for its engine. Hand-written, optimized SQL and portability coexist precisely because the per-backend SQL is concentrated at this one seam and nowhere else. For this phase there is exactly one backend (SQLite + cr-sqlite); the seam keeps a second reachable without rewriting the domain.

cr-sqlite and FTS5 are SQLite-only capabilities; under the seam they are treated as capabilities with per-backend implementations, not global assumptions. The exact-value encoding is likewise a mapper concern: the domain model carries exact rationals/Decimal, and each mapper encodes to its engine's best exact type (scaled-int on SQLite; native `NUMERIC` on a future Postgres) — the domain never sees `REAL`.

---

## Transactions, identity, batching

- **Unit-of-work:** transaction scope is the session's responsibility, not the mapper's. Mappers and domain objects never call `commit()`; callers compose multi-aggregate, multi-table writes into one transaction (e.g., an import, or an item plus its inventory event).
- **Identity map / cache:** lives in the session, session-scoped, so overlapping queries share instances rather than producing stale duplicates. The registry is itself a permanent identity map for structure.
- **Batching is the default** on the write side (collections) and the read side (projections), reflecting the real workload: grid loads, searches, and imports operate on sets.

---

## Open items

- **SQLGlot as a dev/test-time validator** (not a runtime generator, not an ORM): parse and column-qualify the composed dynamic SQL in CI so malformed queries fail loudly. Leaning yes; deferrable. To be confirmed when the query layer is specified.
- **Aggregate vocabulary:** this doc uses "aggregate" (root entity + owned rows / its consistency boundary). Adopt the owner's preferred term if different.

---

## What this supersedes

- **The antipattern:** repository-owned inline SQL, `SELECT *`, module-level `_row_to_*`, per-write `commit()`. Replaced by aggregate mappers + session-owned transactions.
- **Coding-standards spec:** the data-model and repository sections of `2026-06-03-coding-standards-design.md` must be rewritten to encode this layered model (models / aggregate mappers / domain objects / collections / query-projection objects / session / registry) and the single-writer-per-table invariant.
- **Project memory "locked decisions":** SQLite, cr-sqlite, FTS5, scaled-int, BLOB UUID, raw SQL / no ORM are **reconfirmed and re-validated**. The **mapper seam and the layered persistence architecture are new** and must be recorded. The earlier framing that the repository owns SQL is retired.

---

## Downstream consequences (not part of this design)

- The Phase-1 `schema_registry/repository.py` is built on the antipattern and is really the **registry/structure layer** — it should be reworked into the in-memory registry plus aggregate mappers, not a generic repository.
- Data-layer coding standards (SQL, data models, mappers, repository/session) will encode the rules implied here.

---

## Success criteria

1. No consumer outside a mapper or query object references a table name, column, or SQL text.
2. Each table has exactly one aggregate mapper that writes it.
3. Domain objects and collections persist via `write()` / `save()` that delegate to mappers; none calls `commit()`.
4. The grid and parametric search return read-model projections produced by query objects, distinct from write aggregates.
5. The physical schema of an aggregate can be changed (e.g., split a table) with edits confined to its mapper.
6. Swapping the backend would require new mapper implementations only — no changes to models, domain objects, collections, session, or registry.
