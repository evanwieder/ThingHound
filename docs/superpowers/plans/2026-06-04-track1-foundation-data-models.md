# Track 1 — Foundation & Data Models Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

> One careful worker; TDD throughout; commit per task **only after explicit user authorization to begin coding**. Read `coding_standards.md` and the relevant `docs/dev/agent/standards-*.md` before each task.

**Authoritative sources:** `docs/specs/thinghound-{functional-spec,architecture,data-model}.md`, `docs/dev/standards-*.md`. Where this plan and a doc disagree, the doc wins. **`thinghound-data-model.md` is authoritative for every table, column, type, and key.**

**Goal:** Produce the complete data foundation: project scaffold, exact-numeric primitives, the unit/value encoding engine, the full Pydantic model set (all entities, all phases), the full migration schema + reference-code seeds, the connection, the Session/Unit-of-Work, and the AppRegistry skeleton.

**Architecture:** No ORM. Frozen Pydantic models that own their own value conversion. SQL is built by a model-aware query component — but **no aggregate mappers or query component in this track** (those are Track 2). Track 1 ships the schema (DDL), the models, the primitives, and the session/registry seams that Track-2 mappers plug into. libSQL/SQLite + FTS5; **foreign keys ON**; exact integers / `Decimal` / `Money` only.

**Layering reminder (program plan §1):** the **Session/Unit-of-Work owns the connection, transaction scope, and identity map only — no table SQL and no row↔model conversion.** Conversion is the aggregate mapper's job (Track 2). Models convert their own values (scaled-int ↔ exact, `Money`). Keep these boundaries intact here so Track 2 can rely on them.

**Key invariants this track must honour (from the specs/standards):**
- **PK strategy:** structure/master-data tables use a DB-generated **integer** PK (`id`, normal rowid table); operational/transactional tables use a **UUIDv7** PK (`uuid`, `BLOB(16)`, `WITHOUT ROWID`); reference/code tables use a natural `code TEXT` PK. FK columns end in `_id` (→ integer PK) or `_uuid` (→ uuid PK).
- **Foreign keys are enforced** (`PRAGMA foreign_keys = ON`); DDL uses real `REFERENCES`.
- **No column name ends with a preposition** (`created_ts`, not `created_at`; `qty_per_assembly`, not `qty_per`).
- **No `REAL`.** `Decimal`/`Money` use the role-based encodings in `architecture.md §9`.
- **Audit is per-table**, excluded from domain models by default: every table carries `created_user_uuid`/`updated_user_uuid` (append-only event tables carry `user_uuid`); most carry a `deleted_ts` tombstone. Models do not project these (surfaced via a separate `Audit` object in Track 2).

**Reference (consult for algorithms only; never copy verbatim, always reconcile to current docs):** preserved legacy code may contain useful algorithm references for `ids.py`, `money.py`, `units/scale.py`, `db/connection.py`, `db/migrations.py`. **The reference tree is not present in this repo by default.** Before any task that names it as a source, the orchestrator must either (a) vendor the specific reference files into `docs/dev/reference/`, or (b) supply the worker the current path to a local checkout. If neither is available, **derive the algorithm from the specs and standards alone**. **Every reuse must drop the prohibited `from __future__ import annotations` (PEP 649) and take `scale` as a per-attribute parameter, never read it from a dimension.** The old `repository.py` is the antipattern being replaced — do not consult it.

---

## File Structure

```
pyproject.toml                          # Python 3.14, deps, ruff, pytest config
src/thinghound/
  __init__.py                           # version
  types.py                              # UUIDv7 annotated type, new_id()
  errors.py                             # typed domain errors (shared)
  money.py                              # Money value object (frozen dataclass)
  value/
    scaled_value.py                     # ScaledValue value object (owns encode/decode use)
    encoding.py                         # encode_scaled / decode_scaled / parse_magnitude
    normalize.py                        # raw "magnitude+unit" -> ScaledValue (exact, factor-driven)
    temporal.py                         # iso_to_epoch / epoch_to_iso (epoch ms, UTC) — used by mappers
    quantity.py                         # QUANTITY_SCALE = 6; encode_quantity / decode_quantity
  db/
    connection.py                       # connect(): FK ON, WAL
    migrations.py                       # migration runner + schema_migration
    migrations_sql/                     # numbered .sql files (DDL + reference seeds); one per domain group
  models/                               # frozen Pydantic, one class per file, by domain
    schema/ category/ display/ identity/ item/ attrvalue/
    instance/ event/ vendor/ project/ invoice/ bom/ misc/ admin/ readmodel/
  session.py                            # Session (Unit of Work): connection + transaction + identity map
  registry.py                           # AppRegistry skeleton (load hook; populated by Track 2 U1)
tests/
  conftest.py                           # conn fixture (in-memory + migrations), seed fixtures
  ...                                   # mirrors src layout
```

---

## Task 1: Project scaffold

**Files:** `pyproject.toml`, `src/thinghound/__init__.py`, `tests/test_version.py`.

- [ ] **Step 1: Branch** (after authorization) `feat/track1-foundation` from the base the user names.
- [ ] **Step 2: `pyproject.toml`** — `requires-python = ">=3.14"`; deps `pydantic>=2.7, pint>=0.24, jinja2>=3.1, simpleeval>=0.9.13, libsql-experimental` (or the agreed libSQL driver); dev `pytest>=8, ruff>=0.6`; hatchling build with `packages = ["src/thinghound"]`; ruff `line-length=100`, `target-version="py314"`, `extend-exclude=["docs/", ".venv/"]`, lint `select=["E","F","I","UP","B"]`; pytest `pythonpath=["src","."]`, `testpaths=["tests"]`.
- [ ] **Step 3: version module** — `src/thinghound/__init__.py` with `__version__ = "0.1.0"`.
- [ ] **Step 4: failing smoke test** — `tests/test_version.py` asserting `thinghound.__version__ == "0.1.0"`.
- [ ] **Step 5: venv + install** — create the venv from the project's Python 3.14 interpreter, `pip install -e ".[dev]"`.
- [ ] **Step 6: run + commit** — `pytest -q` (1 passed), `ruff check .` (clean), commit `chore: project scaffold`.

---

## Task 2: `UUIDv7` type

**Files:** `src/thinghound/types.py`, `tests/test_types.py`.

- [x] **Step 1: failing tests** — `new_id().version == 7`; a frozen model with `uuid: UUIDv7` accepts a v7 id and rejects a v4 id (raises `ValueError`).
- [x] **Step 2: run → fail** (`No module named thinghound.types`).
- [x] **Step 3: implement:**

```python
"""Domain identifier types. UUIDv7 for operational/transactional keys; canonical string only at the bridge."""

import uuid
from typing import Annotated

from pydantic import AfterValidator


def _require_v7(v: uuid.UUID) -> uuid.UUID:
    if v.version != 7:
        raise ValueError(f"expected UUIDv7, got version {v.version}")
    return v


UUIDv7 = Annotated[uuid.UUID, AfterValidator(_require_v7)]


def new_id() -> uuid.UUID:
    """Generate a fresh time-ordered UUIDv7 (Python 3.14 stdlib)."""
    return uuid.uuid7()
```

- [x] **Step 4: run → pass; commit** `feat: UUIDv7 type and id factory`.

---

## Task 3: `Money` value object

**Files:** `src/thinghound/money.py`, `tests/test_money.py`.

- [x] **Step 1: failing tests** — `from_decimal(Decimal("1.50"),"USD",exponent=2).amount_minor == 150`; rejects excess precision (`Decimal("1.005")`, exp 2); `to_decimal` round-trips; `add` same-currency sums; cross-currency raises; non-int amount raises `TypeError`; bad currency (`"usd"`) raises.
- [x] **Step 2: run → fail. Step 3: implement** a `@dataclass(frozen=True)` `Money(amount_minor: int, currency: str)` with `__post_init__` validation, `from_decimal`, `to_decimal`, `add` (port from reference `money.py`, **without** the `__future__` import).
- [x] **Step 4: run → pass; ruff clean; commit** `feat: Money value object`.

---

## Task 4: Value encoding + typed errors

**Files:** `src/thinghound/errors.py`, `src/thinghound/value/encoding.py`, `tests/value/test_encoding.py`.

- [x] **Step 1: `errors.py`** — `ScaleOverflowError(value: Fraction, scale: int)` and `UnknownUnitError(symbol: str, dimension: str)` (used in Task 5).
- [x] **Step 2: failing tests** — `encode_scaled(Fraction(1000), 3) == (1_000_000, "1000.000")`; exact round-trip `decode_scaled(encode_scaled(...))`; `½` entry equals `0.5` on `value_exact`; mixed/vulgar/slash parse; overflow raises `ScaleOverflowError`.
- [x] **Step 3: run → fail. Step 4: implement** `parse_magnitude`, `encode_scaled(base: Fraction, scale: int) -> tuple[int,str]` (raises `ScaleOverflowError`), `decode_scaled` (port from reference `units/scale.py`, drop `__future__`, scale is a parameter; keep `getcontext().prec = 60` and `INT64_MAX`). **Do not** port `normalize`/`Dimension` here.
- [x] **Step 5: run → pass; commit** `feat: exact value encoding + typed errors`.

---

## Task 5: `ScaledValue` + unit normalization

**Files:** `src/thinghound/value/scaled_value.py`, `src/thinghound/value/normalize.py`, `tests/value/test_normalize.py`.

- [x] **Step 1: `ScaledValue`** — `@dataclass(frozen=True)` with `value_scaled: int`, `value_exact: str`, `scale: int`, `value_raw: str | None`, `display_unit: str | None`.
- [x] **Step 2: failing tests** for `normalize(raw, *, factors: dict[str, Fraction], scale: int, dimension_name: str = "")` — `"2.2 kΩ"` with `{Ω:1, kΩ:1000}` at scale 3 → `(2_200_000, "2200.000")`; preserves `value_raw`/`display_unit`; same factors different scale → different `value_exact` precision (scale is per-call); fraction input normalizes; unknown unit raises `UnknownUnitError`.
- [x] **Step 3: run → fail. Step 4: implement** `_split_input` (NFC, split trailing unit incl. `Ω`/`µ`) + `normalize` (look up `factors[unit]`, `base = parse_magnitude(mag) * factor`, `encode_scaled(base, scale)`). Scale is a parameter — never `Dimension.scale`.

> Production note: in production the `factors` map is derived by the AppRegistry from `unit_multiplier`/`prefix` rows; Pint may parse SI-prefixed/custom units, but **all arithmetic stays in `Fraction`/`Decimal`**. The `factors`-dict signature is the seam; Pint wiring is a Track-2 concern.

- [x] **Step 5: run → pass; commit** `feat: ScaledValue + exact unit normalization`.
- [x] **Step 6: temporal helpers** — `src/thinghound/value/temporal.py`: `iso_to_epoch(s: str) -> int` and `epoch_to_iso(ms: int) -> str` (epoch **milliseconds, UTC**; exact integer; raise a typed error on malformed input). Tests: round-trip; known value (`"1970-01-01T00:00:00Z" -> 0`). These are pure value utilities the **mappers** call at the storage boundary; models keep ISO-8601 strings. Commit `feat: ISO-8601 ↔ epoch-ms temporal conversion`.
- [x] **Step 7: quantity helpers** — `src/thinghound/value/quantity.py`: `QUANTITY_SCALE = 6` and `encode_quantity(d: Decimal) -> tuple[int, str]` / `decode_quantity(scaled: int) -> Decimal` (dual-column at the fixed quantity scale; reuse `encode_scaled`/`decode_scaled` with `QUANTITY_SCALE`; raise `ScaleOverflowError` past int64). Factors/rates do **not** use this — they store a single `*_exact TEXT` (architecture §9). Commit `feat: fixed-scale quantity encoding (scale 6)`.

---

## Task 6: Database connection

**Files:** `src/thinghound/db/connection.py`, `tests/db/test_connection.py`.

- [ ] **Step 1: failing tests** — `connect(":memory:")` has `PRAGMA foreign_keys == 1`; a file db is in `WAL` mode.
- [ ] **Step 2: run → fail. Step 3: implement** `connect(path)`: open the libSQL/SQLite connection, `row_factory = sqlite3.Row` (or the driver equivalent), `PRAGMA foreign_keys=ON`, `PRAGMA journal_mode=WAL` (skip for `:memory:`). No row↔model conversion here — this layer only configures the connection. (Turso replica sync configuration is wired later; local development runs against the embedded file/`:memory:`.)
- [ ] **Step 4: run → pass; commit** `feat: configured connection (FK on, WAL)`.

---

## Task 7: Migration runner

**Files:** `src/thinghound/db/migrations.py`, `tests/db/test_migrations.py`.

- [ ] **Step 1: failing tests** — `apply_all(conn)` records version `"0001"`; second `apply_all` is a no-op (idempotent); `applied_versions` returns a sorted list.
- [ ] **Step 2: run → fail. Step 3: implement** `schema_migration(version TEXT PRIMARY KEY, name TEXT, checksum TEXT, applied_ts INTEGER)` (`applied_ts` epoch ms); discover `migrations_sql/*.sql` by numeric prefix; apply each unapplied file in a transaction; record a SHA-256 checksum; raise if an applied migration's checksum changed; forward-only. Provide a minimal `0001` stub so the runner has input (Task 9 fills it).
- [ ] **Step 4: run → pass; commit** `feat: migration runner with checksums`.

---

## Task 8: Migration 0001 — reference code tables + seeds

**Files:** `migrations_sql/0001_ref_code_tables.sql`, `tests/db/test_ref_seed.py`.

All 23 code tables from `data-model.md §3` (`value_type`, `value_kind_hint`, `source_layer`, `aggregate_function`, `instance_display`, `sort_direction`, `lifecycle_status`, `stock_mode`, `instance_kind`, `relationship_type`, `provenance`, `instance_status`, `event_type`, `project_status`, `match_status`, `import_kind`, `availability_status`, `bom_status`, `build_status`, `formula_layer`, `ltspice_template_type`, `extraction_status`, `file_type`). Each: `code TEXT PRIMARY KEY, name TEXT, description TEXT`, seeded with the exact rows from §3. (These are seeded by migrations and read-only at runtime; the count and rows are authoritative in `data-model.md §3` — if it changes, this task follows.)

- [ ] **Step 1: failing tests** — e.g. `value_type` has 8 codes; `event_type` code `C` is `Consume`; `file_type` has codes `P/D/O/M/X`.
- [ ] **Step 2: run → fail. Step 3: write the full SQL; run → pass. Step 4: commit** `feat: migration 0001 — reference code tables + seeds`.

---

## Task 9: Migrations 0002–0013 — full schema (one task per group)

**Files:** `migrations_sql/000N_<name>.sql` (one per domain group), `tests/db/test_schema_<name>.py`.

DDL for **every** entity in `data-model.md §4–§19`. Each sub-task below is **one migration file, one matching schema-shape test file, one commit**. Field lists, types, and keys come **verbatim** from `data-model.md`; do not invent columns.

**DDL rules:**
- **PKs by role:** structure/master-data tables → `id INTEGER PRIMARY KEY` (rowid table); operational/transactional tables → `uuid BLOB(16) PRIMARY KEY` + `WITHOUT ROWID`; junction tables → composite PK of their FK columns; code/natural-key tables as specified. See the PK classification in `data-model.md §1`.
- **Foreign keys are real and enforced:** `REFERENCES` clauses on every FK; FK columns named `_id` (→ integer PK) or `_uuid` (→ uuid PK).
- **No `AUTOINCREMENT` need** (rowid handles it); `AUTOINCREMENT` permitted only where a strict monotonic guarantee is required. **No `REAL`.** Secondary `UNIQUE` on natural keys (SKU/MPN/manufacturer name) is **not** added — uniqueness is service-enforced.
- **`CHECK` constraints** (single- or cross-column) are permitted.
- **Attribution:** `created_user_uuid BLOB DEFAULT NULL`, `updated_user_uuid BLOB DEFAULT NULL` on every table; append-only event tables (`inventory_event`, `instance_measurement`, `offer_history`) instead carry `user_uuid BLOB DEFAULT NULL`. Most catalog/config tables also carry `deleted_ts INTEGER DEFAULT NULL`.
- **`Decimal` by role (`architecture.md §9`):** attribute values → `*_scaled INTEGER` + `*_exact TEXT` at the owning `attribute.scale`; quantities (`qty_*`, `moq`, `order_multiple`, `reorder_*`, `safety_stock`, read-model `qty_*`) → `*_scaled INTEGER` + `*_exact TEXT` at **fixed quantity scale 6**; factors/rates (`unit_multiplier.factor`, `prefix.factor`, `fx_rate.rate`) → **single `*_exact TEXT`**, no `*_scaled`. `Money` → `*_minor INTEGER` + `*_currency TEXT`.
- **`Timestamp`/`Date`** columns are `INTEGER` epoch (epoch ms, UTC), never `TEXT`; the mapper (Track 2) encodes ISO-8601 ↔ epoch at the storage boundary. `HLC` columns are `TEXT`.

**Per-group rhythm (apply to every sub-task 9a–9l):**
1. Write the named failing schema-shape test (key assertions below per group; the full field list is in `data-model.md`).
2. `pytest -q tests/db/test_schema_<name>.py` → FAIL (table/column missing).
3. Write the DDL in `migrations_sql/000N_<name>.sql`.
4. `pytest -q tests/db/test_schema_<name>.py` → PASS.
5. **Commit (after authorization):** `feat(migrations): 000N <name>`.

### Task 9a — `0002_config_schema.sql` — config & schema registry
**Tables (`data-model.md §4`):** `unit_dimension`, `unit_multiplier`, `prefix_set`, `prefix`, `attribute_domain`, `attribute`, `attribute_allowed_prefix`, `attribute_enum_value`, `attribute_component`. All structure tables → integer `id` PKs.
- [ ] Failing test `test_schema_config`: `unit_dimension.id` is INTEGER PK (rowid); `attribute.scale` is INTEGER NOT NULL DEFAULT 0; `attribute.attribute_domain_id` is an INTEGER FK with a real `REFERENCES attribute_domain(id)`; `attribute_component.attribute_id` REFERENCES `attribute(id)`; every table has `created_user_uuid`/`updated_user_uuid`.
- [ ] Implement; commit `feat(migrations): 0002 config & schema registry`.

### Task 9b — `0003_category_display.sql` — category, display, layouts, searches, views
**Tables (`data-model.md §5–§6`):** `category`, `category_attribute`, `display_profile`, `display_column`, `category_column_mapping`, `grid_layout`, `grid_layout_column`, `grid_layout_sort`, `grid_layout_grouping`, `saved_search_group`, `saved_search`, `grid_view`. All structure tables → integer `id` PKs.
- [ ] Failing test `test_schema_category_display`: `category` has `parent_id INTEGER` with `REFERENCES category(id)`, plus `id_path TEXT NOT NULL` and `full_path TEXT NOT NULL`; `category_attribute` composite PK `(category_id, attribute_id)` with `is_excluded` present and no synthetic surrogate beyond `id`; `grid_layout_sort` composite PK `(grid_layout_id, position)`; `grid_view` has `grid_layout_id` + `saved_search_id` FKs.
- [ ] Implement; commit `feat(migrations): 0003 category, display & grid`.

### Task 9c — `0004_identity_item.sql` — identity & item
**Tables (`data-model.md §7–§8`):** `manufacturer` (int id), `product_series` (int id), `series_attribute_default` (int id), `item` (uuid), `item_category` (junction), `item_relationship` (uuid).
- [ ] Failing test `test_schema_identity_item`: `item.uuid` BLOB PK, table `WITHOUT ROWID`; `item.sku TEXT` with **no** secondary UNIQUE; `item.naming_category_id INTEGER REFERENCES category(id)` (no `primary_category_id`); `item.derived_name` and `item.fixed_name` present; `item_category` composite PK `(item_uuid, category_id)` with FKs to `item(uuid)` and `category(id)`; `item_relationship.relationship_type_code TEXT NOT NULL DEFAULT ''` REFERENCES `relationship_type(code)`.
- [ ] Implement; commit `feat(migrations): 0004 identity & item`.

### Task 9d — `0005_attr_values.sql` — item attribute values
**Tables (`data-model.md §9`):** `item_attribute_value`, `item_attribute_component_value`.
- [ ] Failing test `test_schema_attr_values`: `item_attribute_value` composite PK `(item_uuid, attribute_id)` with `value_scaled INTEGER`, `value_exact TEXT`, `value_raw TEXT`, `display_unit TEXT`, `provenance_code TEXT NOT NULL DEFAULT ''`; component-value table adds `attribute_component_id` to the PK.
- [ ] Implement; commit `feat(migrations): 0005 attribute values`.

### Task 9e — `0006_instances_events_location_currency_fx.sql`
**Tables (`data-model.md §10–§11` + `§15`):** `location` (int id), `item_instance` (uuid), `instance_measurement` (uuid, append-only), `inventory_event` (uuid, append-only), `currency` (code PK), `fx_rate` (uuid).
- [ ] Failing test `test_schema_inventory`: `location.parent_id INTEGER REFERENCES location(id)`; `inventory_event.uuid` BLOB PK WITHOUT ROWID with `user_uuid` (append-only attribution, no update pair), `(effective_date INTEGER, hlc TEXT, uuid BLOB)` ordering columns, `from_location_id`/`to_location_id` INTEGER REFERENCES `location(id)`; `fx_rate.rate_exact TEXT` with **no** `rate_scaled`; `currency.code TEXT PRIMARY KEY`.
- [ ] Implement; commit `feat(migrations): 0006 instances, events, location, currency, FX`.

### Task 9f — `0007_vendor_pricing.sql`
**Tables (`data-model.md §14`):** `vendor` (int id), `vendor_offer` (uuid), `price_break` (uuid), `offer_history` (uuid, append-only).
- [ ] Failing test `test_schema_vendor`: `vendor_offer.vendor_id INTEGER REFERENCES vendor(id)`, `vendor_offer.item_uuid BLOB REFERENCES item(uuid)`, `currency TEXT NOT NULL DEFAULT ''`; `price_break.unit_price_minor INTEGER` + `unit_price_currency TEXT`, `qty_min_scaled`/`qty_min_exact` (quantity scale 6); `offer_history` has `user_uuid`.
- [ ] Implement; commit `feat(migrations): 0007 vendor & pricing`.

### Task 9g — `0008_project_invoice.sql`
**Tables (`data-model.md §12–§13`):** `project` (uuid), `invoice` (uuid), `invoice_line` (uuid), `import_template` (int id).
- [ ] Failing test `test_schema_project_invoice`: `invoice_line.qty_scaled`/`qty_exact`; `invoice_line.item_uuid BLOB REFERENCES item(uuid)`; `invoice.vendor_id INTEGER REFERENCES vendor(id)`; `import_template.mapping TEXT NOT NULL DEFAULT '{}'`.
- [ ] Implement; commit `feat(migrations): 0008 project & invoice`.

### Task 9h — `0009_bom_build.sql`
**Tables (`data-model.md §16`):** `bom`, `bom_revision`, `bom_line`, `bom_line_substitute`, `build` (all uuid).
- [ ] Failing test `test_schema_bom_build`: `bom_revision.status_code` REFERENCES `bom_status(code)`; `bom_line.qty_per_assembly_scaled`/`qty_per_assembly_exact`; `bom_line.item_uuid` nullable FK to `item(uuid)`; `bom_line_substitute` composite PK; `build.status_code` REFERENCES `build_status(code)`.
- [ ] Implement; commit `feat(migrations): 0009 BOM & build`.

### Task 9i — `0010_misc.sql` — tags, formulas, LTspice, extraction
**Tables (`data-model.md §17`):** `tag` (int id), `item_tag` (junction), `attribute_formula` (int id), `formula_input` (int id), `formula_category` (junction), `ltspice_template` (int id), `ltspice_template_param` (int id), `datasheet_extraction` (uuid).
- [ ] Failing test `test_schema_misc`: `item_tag` composite PK `(item_uuid, tag_id)`; `attribute_formula.enabled INTEGER NOT NULL DEFAULT 1`; `formula_input.layer_code` REFERENCES `formula_layer(code)`; `datasheet_extraction.uuid` BLOB PK; `tag.name TEXT NOT NULL DEFAULT ''` (no secondary UNIQUE).
- [ ] Implement; commit `feat(migrations): 0010 misc`.

### Task 9j — `0011_admin.sql` — attachments, settings, users, RBAC
**Tables (`data-model.md §18`):** `attachment` (uuid), `item_attachment` (junction), `invoice_attachment` (junction), `app_setting` (key PK), `device_setting` (key PK, device-local), `user` (uuid), `role` (uuid), `permission` (uuid), `role_permission` (junction), `user_role` (junction).
- [ ] Failing test `test_schema_admin`: `attachment.uuid` BLOB PK with `file_type_code` REFERENCES `file_type(code)` and **no owner columns**; `item_attachment` composite PK `(item_uuid, attachment_uuid)`; `invoice_attachment` composite PK `(invoice_uuid, attachment_uuid)`; `user`/`role`/`permission` are uuid-PK (`uuid BLOB PRIMARY KEY`); `role_permission` PK `(role_uuid, permission_uuid)`; `user_role` PK `(user_uuid, role_uuid)`. (No `audit_log` table — audit is per-table.)
- [ ] Implement; commit `feat(migrations): 0011 admin`.

### Task 9k — `0012_read_models.sql` — derived read-model tables + FTS5
**Tables (`data-model.md §19`):** `rm_item_stock`, `rm_stock_by_location`, `rm_instance_state`, `rm_thumbnail`, `fts_item` (FTS5 external-content + trigram tokenizer). These are derived/device-local, rebuilt locally — not synced.
- [ ] Failing test `test_schema_read_models`: each `rm_*` aggregate carries a `watermark_uuid BLOB` column; `rm_item_stock` has `item_uuid` PK plus `qty_available_scaled/exact`, `qty_assigned_scaled/exact`, `qty_waste_scaled/exact`, `qty_lost_scaled/exact` (quantity scale 6), `avg_landed_cost_minor`/`_currency`, `last_unit_cost_minor`/`_currency`; `fts_item` created with `tokenize='trigram'` and `content='item'`, indexing `derived_name`/`fixed_name` among other fields. **Trigger/aggregation logic (watermark snapshot + tail fold) is owned by Track-2 U5** — this migration creates the tables and leaves trigger bodies to U5 (document the handoff in the SQL file's leading comment).
- [ ] Implement; commit `feat(migrations): 0012 read-models + FTS5`.

### Task 9l — `0013_indexes.sql` — performance indexes (`data-model.md §20`)
- [ ] Failing test `test_schema_indexes`: every named index from §20 exists in `sqlite_master`, including the `category.id_path` prefix-lookup index and the event-replay index `(item_uuid, effective_date, hlc, uuid)`.
- [ ] Implement; commit `feat(migrations): 0013 indexes`.

### Task 9-final — cross-cutting verification
- [ ] **Cross-cutting test** `test_migrations_apply_cleanly`: `apply_all(connect(":memory:"))` succeeds with `foreign_keys=ON`; `applied_versions` returns `["0001","0002",…,"0013"]`; a second `apply_all` is a no-op.
- [ ] **Cross-cutting test** `test_foreign_keys_enforced`: inserting a child row with a dangling FK raises an integrity error (proves `REFERENCES` are live).
- [ ] **Commit (after authorization):** `test(migrations): cross-cutting apply-clean + FK-enforcement coverage`.

---

## Task 10: Pydantic domain models (one task per domain subpackage)

**Files:** `src/thinghound/models/<domain>/<entity>.py` (one class per file), `tests/models/<domain>/test_<entity>.py`.

A frozen Pydantic model for **every** entity in `data-model.md §4–§19` (reference code tables share a small `CodeRow` model). Per `standards-data-models.md`: integer `id: int` for structure/master-data, `uuid: UUIDv7` for operational/transactional, `code: str` for code tables; FK fields end in `_id`/`_uuid`; `*_code` fields are `str` validated against the loaded code table **at the service layer** (never `Literal`/`Enum`); `Money` for money; dimensional values via `ScaledValue`/`Decimal`; `X | None` for nullable with each absence justified in a field comment. **Audit fields (`created_user_uuid`, `updated_user_uuid`, `deleted_ts`) are excluded from the model** — surfaced via a separate `Audit` object in Track 2.

**Models own their own value conversion** (encode/decode of `ScaledValue`, `Money`) — but they do **not** read or write the database, and they do **not** know about rows. Timestamp/date fields, where modeled, carry **ISO-8601 strings**; the mapper converts to/from the epoch integer.

**Per-entity rhythm:**
1. Write the failing model test: construct with valid fields; assert one model-level invariant (e.g. non-v7 uuid rejected; `frozen=True` rejects mutation; `*_code` accepts `str`).
2. `pytest -q` → FAIL.
3. Implement one class per file, mirroring `data-model.md` field list **verbatim**. Justify each `X | None`.
4. `pytest -q` → PASS.
5. Model validators only for **single-entity** invariants (cross-entity checks are service-layer).

**Per-sub-task commit (after authorization):** one commit per domain subpackage — `feat(models): <domain> entities`.

---

### Worked example A — structure entity (integer PK)

`src/thinghound/models/schema/unit_dimension.py`:

```python
"""Domain model for a unit dimension (a measurable domain with a base unit)."""

from pydantic import BaseModel, ConfigDict


class UnitDimension(BaseModel):
    """A measurable domain (Resistance, Mass, Length) with a defined base unit."""

    model_config = ConfigDict(frozen=True)

    id: int                # structure table → DB-generated integer PK
    name: str
    base_unit: str
    # audit fields (created_user_uuid / updated_user_uuid / deleted_ts) are excluded;
    # surfaced via a separate Audit object on demand.
```

### Worked example B — operational root entity (uuid PK, mixed FKs) — `item`, §8

```python
"""Domain model for a catalog item — root of the item aggregate."""

from pydantic import BaseModel, ConfigDict

from thinghound.types import UUIDv7


class Item(BaseModel):
    """A catalog item (a part, not a physical instance). Identity is the UUIDv7;
    SKU/MPN/GPN are optional natural keys whose uniqueness is service-enforced."""

    model_config = ConfigDict(frozen=True)

    uuid: UUIDv7
    sku: str | None = None                    # NULL = no internal SKU assigned yet
    parent_item_uuid: UUIDv7 | None = None    # NULL = not a variant child
    naming_category_id: int | None = None     # FK→category(id); renders derived_name / no-context columns
    manufacturer_id: int | None = None        # NULL = generic/unbranded
    part_number: str | None = None            # MPN or GPN
    product_series_id: int | None = None      # NULL = not part of a series
    lifecycle_status_code: str = ""           # validated against lifecycle_status at the service
    derived_name: str | None = None           # rendered by the naming engine; never user-set
    fixed_name: str | None = None             # optional user override; display priority over derived_name
    description: str | None = None
```

### Worked example C — append-only event entity with `Money` (`inventory_event`, §11)

Append-only: insert-only, no update attribution; single `user_uuid`.

```python
"""Domain model for an inventory event (append-only, insert-only)."""

from pydantic import BaseModel, ConfigDict

from thinghound.money import Money
from thinghound.types import UUIDv7


class InventoryEvent(BaseModel):
    """A single append-only inventory event. Ordered by (effective_date, hlc, uuid)."""

    model_config = ConfigDict(frozen=True)

    uuid: UUIDv7
    item_uuid: UUIDv7
    instance_uuid: UUIDv7 | None = None        # NULL = bulk pool
    event_type_code: str                       # ADD/CONSUME/ADJUST/MOVE/INDIVIDUATE/WASTE/LOST
    qty_change_scaled: int                      # fixed quantity scale 6
    qty_change_exact: str
    unit_cost_at_purchase: Money | None = None  # NULL when the event has no cost
    effective_date: str                         # ISO-8601 (UTC); mapper encodes epoch
    hlc: str                                     # hybrid logical clock token
    reason: str | None = None                    # required by SERVICE for ADJUST
    from_location_id: int | None = None          # FK→location(id)
    to_location_id: int | None = None            # FK→location(id)
    user_uuid: UUIDv7 | None = None              # append-only attribution (single field)
```

### Worked example D — value-bearing aggregated child (`item_attribute_value`, §9)

```python
"""Domain model for a per-item attribute value (child of the Item aggregate)."""

from pydantic import BaseModel, ConfigDict

from thinghound.types import UUIDv7
from thinghound.value.scaled_value import ScaledValue


class ItemAttributeValue(BaseModel):
    """One attribute value on one item. The scaled-int/exact-text pair is encoded
    at the attribute.scale by the service write path; the model stores the
    already-encoded ScaledValue."""

    model_config = ConfigDict(frozen=True)

    item_uuid: UUIDv7
    attribute_id: int
    value: ScaledValue | None = None      # NULL when attribute is text/enum (use value_text)
    value_text: str | None = None         # NULL when attribute is numeric (use value)
    provenance_code: str = ""             # validated against provenance at the service
```

The four worked examples cover the shapes across the ~60 entities: structure (integer PK), operational root (uuid PK), append-only event with `Money`, value-bearing child with `ScaledValue`. Each sub-task picks the matching shape.

---

### Sub-tasks (one per domain subpackage)

Entity lists come **verbatim** from `data-model.md`. If a section adds/removes entities, **data-model.md wins** — update the sub-task and re-run the affected tests.

- [ ] **Task 10a — `models/schema/`** (`§4`): `UnitDimension`, `UnitMultiplier`, `PrefixSet`, `Prefix`, `AttributeDomain`, `Attribute`, `AttributeAllowedPrefix`, `AttributeEnumValue`, `AttributeComponent`. Shape: structure (integer PK). Commit `feat(models): schema entities`.
- [ ] **Task 10b — `models/category/`** (`§5`): `Category` (integer PK; `parent_id: int | None`, `id_path: str`, `full_path: str`), `CategoryAttribute` (composite key `(category_id, attribute_id)`, `is_excluded: bool`). Commit `feat(models): category entities`.
- [ ] **Task 10c — `models/display/`** (`§6`): `DisplayColumn`, `CategoryColumnMapping`, `DisplayProfile`, `GridLayout`, `GridLayoutColumn`, `GridLayoutSort`, `GridLayoutGrouping`, `SavedSearchGroup`, `SavedSearch`, `GridView`. Shape: structure (integer PK). Commit `feat(models): display, layout & search entities`.
- [ ] **Task 10d — `models/identity/`** (`§7`): `Manufacturer`, `ProductSeries`, `SeriesAttributeDefault` (integer PK; `value: ScaledValue | None`). Commit `feat(models): identity entities`.
- [ ] **Task 10e — `models/item/`** (`§8`): `Item` (worked example B), `ItemCategory` (junction `item_uuid`+`category_id`), `ItemRelationship`. Commit `feat(models): item entities`.
- [ ] **Task 10f — `models/attrvalue/`** (`§9`): `ItemAttributeValue` (worked example D), `ItemAttributeComponentValue` (adds `attribute_component_id`). Test `ScaledValue.value_scaled` int64 fit and frozen-mutation rejection. Commit `feat(models): attribute-value entities`.
- [ ] **Task 10g — `models/instance/`** (`§10`): `ItemInstance` (uuid; `current_location_id: int | None`), `InstanceMeasurement` (uuid, append-only; measurement value is `ScaledValue`; `user_uuid`). Commit `feat(models): instance entities`.
- [ ] **Task 10h — `models/event/`** (`§11`): `InventoryEvent` (worked example C), `Currency` (code PK), `FxRate` (uuid; `rate: Decimal` — mapper stores `rate_exact TEXT`). Commit `feat(models): event, currency, FX entities`.
- [ ] **Task 10i — `models/vendor/`** (`§14`): `Vendor` (integer PK), `VendorOffer` (uuid; `currency: str`), `PriceBreak` (uuid; `qty_min: ScaledValue` scale 6; `unit_price: Money`), `OfferHistory` (uuid, append-only; `user_uuid`). Commit `feat(models): vendor & pricing entities`.
- [ ] **Task 10j — `models/project/`** (`§12`): `Project` (uuid). Commit `feat(models): project entity`.
- [ ] **Task 10k — `models/invoice/`** (`§13`): `Invoice` (uuid), `InvoiceLine` (uuid; `qty: ScaledValue` scale 6; `unit_price: Money | None`), `ImportTemplate` (integer PK; `mapping: str`). Commit `feat(models): invoice entities`.
- [ ] **Task 10l — `models/bom/`** (`§16`): `Bom`, `BomRevision`, `BomLine` (`qty_per_assembly: ScaledValue` scale 6), `BomLineSubstitute`, `Build` (all uuid). Commit `feat(models): BOM & build entities`.
- [ ] **Task 10m — `models/misc/`** (`§17`): `Tag` (integer PK), `ItemTag` (junction `item_uuid`+`tag_id`), `AttributeFormula` (integer PK), `FormulaInput` (`layer_code: str`), `FormulaCategory` (junction), `LtspiceTemplate`, `LtspiceTemplateParam`, `DatasheetExtraction` (uuid). Commit `feat(models): misc entities`.
- [ ] **Task 10n — `models/admin/`** (`§15 + §18`): `Location` (`§15` — integer PK; `parent_id: int | None`), `Attachment` (`§18` — uuid; no owner fields), `ItemAttachment` (junction), `InvoiceAttachment` (junction), `AppSetting`, `DeviceSetting`, `User` (uuid PK), `Role` (uuid PK), `Permission` (uuid PK), `RolePermission` (junction), `UserRole` (junction). Commit `feat(models): location, admin & RBAC entities`.
- [ ] **Task 10o — `models/readmodel/`** (`§19` — derived read-model projections): `RmItemStock`, `RmStockByLocation`, `RmInstanceState`, `RmThumbnail`. Projection read models; carry a `watermark_uuid`; no attribution, no soft-delete. Quantities use `ScaledValue` at scale 6. Commit `feat(models): read-model projections`.

- [x] **Task 10-final — `CodeRow`** (`src/thinghound/models/code_row.py`): a tiny shared model `CodeRow(code: str, name: str, description: str | None = None)` used by every reference code table. One failing test, implement, commit `feat(models): shared CodeRow`.

> Verification at end of Task 10: `pytest -q tests/models/` is fully green; every entity in `data-model.md §3–§19` has exactly one model file and one test file; no model imports the DB driver (`grep -rn "import sqlite3\|import libsql" src/thinghound/models/` returns nothing); no model declares `created_user_uuid`/`updated_user_uuid`/`deleted_ts` (audit excluded).

---

## Task 11: Session / Unit of Work

**Files:** `src/thinghound/session.py`, `tests/test_session.py`.

The Session is the coordinator (`architecture.md §4.6`): connection, transaction scope, identity map. **It owns no table SQL and performs no row↔model conversion.** (When Track-2 mappers exist, the session exposes them and owns the transaction they run in — but the session itself never maps a row.)

- [x] **Step 1: failing tests** — `with session.transaction():` commits on success and rolls back on exception (verified by row counts against a code table); `get_identity`/`put_identity` round-trip an object in the identity map.
- [x] **Step 2: run → fail. Step 3: implement** `Session(conn)`: `transaction()` context manager (`BEGIN`/`COMMIT`/`ROLLBACK`); an identity map keyed by `(type, key)` where `key` is the integer `id` or the `uuid`. No SQL, no `_*_from_row` — those belong to mappers/the query component.
- [x] **Step 4: run → pass; commit** `feat: Session (unit of work: transaction + identity map)`.

---

## Task 12: AppRegistry skeleton

**Files:** `src/thinghound/registry.py`, `tests/test_registry.py`.

- [ ] **Step 1: failing test** — accessors raise `RegistryNotLoadedError` before `load`.
- [ ] **Step 2: run → fail. Step 3: implement** `AppRegistry` skeleton: a `load(session)` hook (sets `_loaded`; the **real** mapper-driven population of dimensions/multipliers/prefixes/attribute domains+attributes/category forest/grid layouts is Track-2 U1) and accessors (`unit_dimensions()`, `attributes()`, `category_forest()`, `factors_for(unit_dimension_id)`) that raise until loaded. The registry calls **mappers** to load (Track 2); it never issues row↔model conversion itself.
- [ ] **Step 4: run → pass; commit** `feat: AppRegistry skeleton (structure load hook)`.

---

## Task 13: conftest + Gate A verification

**Files:** `tests/conftest.py`.

- [ ] **Step 1:** `conftest.py` providing `conn` (in-memory + `apply_all`, `foreign_keys=ON`), `migrated_conn` alias, and seed fixtures (`resistance_dimension`, `electrical_domain`) on top of `conn` (`standards-testing.md`). Domain tests use `conn`; only migration-runner tests call `apply_all` directly.
- [ ] **Step 2: Gate A check** (paste real output): `pytest -q` all green; `ruff check .` clean; foreign keys enforced across all migrations.
- [ ] **Step 3: commit** `test: conftest fixtures; Gate A green`. Foundation complete; Track 2 may begin.

---

## Self-Review (run after execution, against the specs)

- **Coverage:** every entity in `data-model.md §3–§19` has a migration (T8–T9) and a model (T10); every invariant in `coding_standards.md` is enforced by a test; the value engine covers `functional-spec.md §3.3 / §5.4`.
- **Deferred to Track 2 (by design, not gaps):** all aggregate mappers, the query component, services, FTS/trigger and watermark-aggregation logic, registry population, Pint wiring, the `Audit` object.
- **Layering:** the Session and AppRegistry contain **no** row↔model conversion and **no** table SQL; models convert only their own values; there is no "repository" class anywhere.
- **Key/type consistency:** structure/master-data PKs are integer `id`; operational/transactional PKs are `uuid: UUIDv7`; FK fields end in `_id`/`_uuid` to match; `*_code` is `str`; money is `Money`; dimensional values are scaled-int + exact-text; `encode_scaled(base, scale)` takes scale as a parameter at every call site; no audit fields on models; foreign keys are enforced.
