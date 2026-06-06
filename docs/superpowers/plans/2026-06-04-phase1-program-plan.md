# ThingHound Phase 1 — Program Plan (Orchestration)

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

> This is the **master plan**. It contains no code. It defines the development tracks, their dependency gates, the parallelization model, the **persistence layering and responsibility boundaries** every unit must respect, and the per-unit Definition of Done. Execute the per-track plans it points to.

**Authoritative sources (the only sources of truth).** This plan is derived from, and must not deviate from:
- `docs/specs/thinghound-functional-spec.md` — requirements, business rules, bridge surface.
- `docs/specs/thinghound-architecture.md` — stack, **persistence layers (§4)**, type mapping (§9), sync (§6).
- `docs/specs/thinghound-data-model.md` — every entity, key, code tables.
- `docs/dev/standards-*.md` (+ `docs/dev/agent/standards-*.md`) — Python, SQL, data-models, **aggregate-mapper**, testing, error-handling standards.

Where this plan and a doc above disagree, the doc wins; fix the plan.

**Goal:** Stand up ThingHound Phase 1 (core catalog + inventory + a working heterogeneous grid) on a clean local-first data layer — built data-models-first, then by parallel basic agents in testable units with explicit review and testing, with the UI on a parallel track gated by a main-page demo.

**Architecture (one paragraph):** Local-first libSQL/SQLite + FTS5 (embedded replica, optional Turso sync — single-user, non-simultaneous). No ORM; a model-aware query component builds parameterized SQL from mapper metadata. Foreign keys enforced. Exact numeric storage — no float anywhere. Frozen Pydantic models. PyWebView + Tabulator UI over a JS bridge. Detail lives in the specs above.

**Tech stack:** Python 3.14, Pydantic v2, Pint, libSQL/Turso, FTS5, Jinja2, simpleeval, PyWebView, Tabulator, pytest, Ruff, PyInstaller.

---

## 1. Persistence Layering & Responsibility Boundaries (READ FIRST)

Every Track-2 unit and the Track-1 session/registry depend on getting this exactly right. It restates `architecture.md §4` and `docs/dev/standards-repository.md`. **There is no "repository" class. ThingHound uses aggregate mappers.**

| Layer | Owns | **Must NOT do** |
|-------|------|-----------------|
| **Models** (`models/`) | Frozen Pydantic entities / frozen-dataclass value objects: structure, field validation, and value-level conversion of their own fields (e.g. `ScaledValue` encode/decode, `Money`). | Know SQL, connections, I/O, or that a database exists. |
| **Aggregate mapper** (`mappers/`) | The **single source of truth** for persisting one aggregate: the column/relationship **metadata** the query component builds SQL from, **and all row↔model conversion** — `uuid.bytes`↔`uuid.UUID(bytes=…)` for uuid keys, integer ids passed through, scaled-int↔model, **timestamp epoch-int↔ISO-8601**, etc. — as private methods (`_attribute_from_row`). The only layer that knows **both** the physical schema and the domain model. The dialect seam. | Call `commit()`/`rollback()`. Hand-write SQL strings. Know other aggregates' internals, the UI, or services. Be bound mechanically to one table (it may own several). |
| **Query component** (`query/`) | Builds all SQL from mapper metadata. Callers express intent only; values bound; identifiers from metadata. | Convert rows to models. Accept caller-supplied SQL or identifiers. |
| **Domain objects** | A model + a session handle; `write()`/`reload()`/`delete()` **delegate to the aggregate's mapper**. | Contain SQL text or convert rows. Hold the physical schema. |
| **Collections** | Batch-first containers; `items.save()` = one batched statement in one transaction. | Per-row loops. SQL text. Conversion. |
| **Query / projection objects** | Express read intent to the query component; return purpose-built **read models** (projections), distinct from write aggregates. | Know how aggregates are written. Hand-write SQL. |
| **Session / Unit of Work** (what one might loosely call a "repository") | The connection, the transaction scope (`BEGIN`/`COMMIT`/`ROLLBACK`), and the identity map. Exposes mappers/collections/query entry points. | **Know any table SQL. Convert any row to or from any model or value object.** It coordinates; it never maps. |
| **AppRegistry** | Structure/config (dimensions, prefixes, attributes, category forest, grid layouts) loaded once at startup **through the same mappers** and held in memory. | Issue ad-hoc per-row SQL at runtime; be a general cache. |
| **Services** | Use-case orchestration, the acting-user context, and invariants the schema does not enforce (natural-key uniqueness, required-attribute completeness, cross-row business rules). Call mappers within a session transaction. | Contain SQL or row↔model conversion. |

**The conversion rule, stated plainly:** row↔model and value↔column conversion happen in **exactly one place — the aggregate mapper** (using the model's own value-conversion methods). The query component, session/unit-of-work, domain objects, collections, query objects, and services **never** convert a row to or from a Pydantic model or value-object dataclass. (`standards-repository.md`: *"Row mapping belongs to the mapper… a private method on the mapper class."* `architecture.md §4.6`: the session *"knows no table SQL."*)

---

## 2. The Two Locked Decisions

1. **Foundation breadth = full logical schema.** Track 1 produces Pydantic models + migrations + REF code-table seeds for **all** entities in `data-model.md` (Phases 1–4), so the schema is sync-ready from day one. Mappers, services, and UI are built for **Phase 1 functionality only** (`functional-spec.md §7.1`).
2. **Build sequencing = vertical slice to demo, then fan out.** After the foundation lands, build the minimum mapper→service→query chain that drives a real grid (schema registry → item → attribute values → inventory events → grid query), prove it against the UI demo, **then** dispatch remaining Phase-1 units in parallel.

---

## 3. Tracks & Dependency Graph

```
TRACK 1 — Foundation & Data Models  (sequential prerequisite; one careful worker)
  scaffold · types · units/value engine · ALL Pydantic models
  · migrations (full schema + reference seeds) · connection (FK on) · Session (UoW) · AppRegistry skeleton
        │  GATE A: foundation green (all tests pass, migrations apply clean, FK enforced)
        ▼
TRACK 2 — Persistence & Service Units
  Phase 1a (vertical slice; each unwraps the next):
     U1 schema-registry → U2 category → U3 item → U4 attribute-values → U5 inventory-events → U6 grid-query
        │  GATE B: vertical slice green + wired into the UI demo (cross-track)
        ▼
  Phase 1b (parallel fan-out — many basic agents at once):
     vendors/offers/pricing · fx/currency/costing · locations · instances/individuation · projects
     · tags/FTS · attachments · manufacturer/series · BOM/build basics · invoices · procurement · settings · onboarding
        │  GATE C: Phase 1 feature-complete, all units reviewed + green
        ▼
      Phase 1 integration / packaging (PyInstaller)

TRACK 3 — UI Framework  (parallel from day one; depends only on the bridge CONTRACT, not real data)
  scaffold PyWebView shell + bridge stub · frontend scaffold (Tabulator, 3-pane layout)
  · MAIN-PAGE DEMO with dummy data   ◄── TOUCHSTONE DELIVERABLE
        │  GATE D (touchstone): user reviews demo → approves or revises before ANY further UI work
        ▼
  Post-gate UI units · integrates with Track 2 at GATE B (swap dummy bridge for real grid.queryItems)
```

Track 1 blocks Track 2. Track 3 runs alongside Track 1 (it codes against the `functional-spec.md §6` bridge contract, not a live database). Tracks 2 and 3 meet at **Gate B**.

| Track | Plan document |
|-------|---------------|
| 1 — Foundation & Data Models | `2026-06-04-track1-foundation-data-models.md` |
| 2 — Persistence & Service Units | `2026-06-04-track2-persistence-service-units.md` |
| 3 — UI Framework | `2026-06-04-track3-ui-framework.md` |

---

## 4. The Parallelization & Agent Model

**One fresh subagent per unit.** Each Track-2 unit (and post-gate Track-3 unit) is sized for a basic (Haiku-class) agent working against: the unit's spec (tables it writes, models, behaviors, tests, bridge methods), the **worked canonical example** (Track 2 §3), and the compact standards files (`docs/dev/agent/standards-*.md`, loaded per CLAUDE.md task-routing).

Why basic agents suffice: the foundation locks every hard decision (types, encoding, schema, keys, layering) and U0 locks the query-component API. Each unit is then a pattern-following application of the aggregate-mapper standard; only the table/field specifics change, and those come verbatim from `data-model.md`.

Use **superpowers:dispatching-parallel-agents** for the Phase-1b fan-out. The orchestration rule that **no two units write the same table** guarantees parallel units never collide; reads may cross freely.

**Declared deviation — templated unit specs (user-approved).** Track 2 §4 (U1–U6) and §5 (Phase-1b table) describe each unit in a condensed form (aggregate mappers + behaviours + bridge backing) rather than expanding every step inline as Track 1 does. Each unit is expanded into a full step-by-step plan **at dispatch time** by the orchestrator, combining: (a) the unit's row in §4/§5, (b) the **Uniform Unit Template** (Track 2 §2, 11 steps), (c) the **worked canonical example** (Track 2 §3, full mapper code), and (d) the relevant `data-model.md` section. This is a conscious trade — it keeps the catalog readable and lets the orchestrator inject the most current `data-model.md` field lists when dispatching, rather than freezing them in the plan. The basic agent that executes a unit receives the expanded plan, not the §4/§5 row directly. This deviation is safe because: (i) `standards-repository.md` plus the §3 worked example define the mapper shape unambiguously; (ii) Phase 1a is sequential and each unit is reviewed before the next dispatches; (iii) Phase 1b parallel units are isolated by the no-two-units-write-the-same-table rule.

---

## 5. Definition of Done (every unit, every track)

- [ ] **TDD followed** — failing test first for every behavior (`standards-testing.md`). Untested = not implemented.
- [ ] **Real database in integration tests** — in-memory libSQL/SQLite + migrations (FK on); no mocked connections.
- [ ] **Layering respected** — SQL is built by the query component; row↔model conversion lives **only** in the aggregate mapper; the session/UoW, services, domain objects, collections, and query objects perform **no conversion** (see §1).
- [ ] **All SQL parameterized**, column-explicit, fully-qualified joins, traceability comments; identifiers from metadata only (`standards-sql.md`).
- [ ] **No floating-point** anywhere; `Decimal`/`Money`/scaled-int only.
- [ ] **Keys correct** — integer `id` for structure/master-data, `UUIDv7` `uuid` for operational/transactional; FK columns end in `_id`/`_uuid`; canonical UUID string only at the bridge.
- [ ] **Frozen Pydantic** models, one class per file, precise field types, no audit fields on models (`standards-data-models.md`).
- [ ] **Foreign keys enforced**; Ruff clean; full pytest suite green.
- [ ] **Two-stage code review passed** (§6).

---

## 6. Review & Test Discipline

Each unit passes a **two-stage review** before acceptance:
1. **Self-verification** (superpowers:verification-before-completion) — run the suite + Ruff; paste real green output. No "should pass."
2. **Independent code review** (superpowers:requesting-code-review) against the unit spec and the Definition of Done; findings handled via superpowers:receiving-code-review (verify before implementing; push back on wrong feedback).

The orchestrator reviews **between** units. A unit failing review is bounced to a fresh agent with the findings; it does not merge.

---

## 7. The Touchstone Gate (Gate D)

Track 3's first deliverable is the **main-page rendered from dummy data** — the full three-pane layout, a heterogeneous Tabulator grid with dynamic Display Columns and pinned columns, the category tree, the inspector, and the filter strip (`functional-spec.md §4.1–4.5`), using fixtures, not the database. **No further UI units begin until the user reviews and approves it.**

---

## 8. Sequencing Summary (gates)

- [ ] **Gate A** — Track 1 complete: full schema migrates clean, foreign keys enforced, models + engine + session tested. *Unblocks Track 2.*
- [ ] **Gate D** — Track 3 main-page demo approved by user. *Unblocks remaining UI units.* (Independent of Gate A.)
- [ ] **Gate B** — Track 2 vertical slice (U1–U6) green and wired into the demo (dummy data → real `grid.*`). *Unblocks Phase-1b fan-out.*
- [ ] **Gate C** — All Phase-1b units reviewed + green. *Unblocks integration + packaging.*

Tracks 1 and 3 start together; Track 2 starts at Gate A; first end-to-end milestone is Gate B.

> All work on branches; merge to `main` only via user-approved PR. **Do not start coding, commit, push, or open PRs without explicit user authorization** (CLAUDE.md; project memory).
