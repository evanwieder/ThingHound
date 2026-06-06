# Track 1 — Foundation & Data Models Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

> One careful worker; TDD throughout; commit per task **only after explicit user authorization to begin coding**. Read `coding_standards.md` and the relevant `docs/dev/agent/standards-*.md` before each task.

**Authoritative sources:** `docs/specs/thinghound-{functional-spec,architecture,data-model}.md`, `docs/dev/standards-*.md`, `docs/dev/crsqlite-spike-findings.md`, `docs/dev/crr-rules.md`. Where this plan and a doc disagree, the doc wins.

**Goal:** Produce the complete, CRR-correct, sync-ready data foundation: project scaffold, exact-numeric primitives, the unit/value encoding engine, the full Pydantic model set (all entities, all phases), the full migration schema + REF seeds, the rewritten CRR CI guard, the connection, the Session/Unit-of-Work, and the AppRegistry skeleton.

**Architecture:** No ORM. Frozen Pydantic models that own their own value conversion. Hand-written parameterized SQL — but **no aggregate mappers in this track** (those are Track 2). Track 1 ships the schema (DDL), the models, the primitives, and the session/registry seams that Track-2 mappers plug into. SQLite + cr-sqlite + FTS5; exact integers / `Decimal` / `Money` only.

**Layering reminder (program plan §1):** the **Session/Unit-of-Work owns the connection, transaction scope, and identity map only — no table SQL and no row↔model conversion.** Conversion is the aggregate mapper's job (Track 2). Models convert their own values (scaled-int ↔ exact, `Money`). Keep these boundaries intact here so Track 2 can rely on them.

**Reference (consult for algorithms only; never copy verbatim, always reconcile to current docs):** preserved legacy code that may contain useful algorithm references for `ids.py`, `money.py`, `units/scale.py`, `db/connection.py`, `db/migrations.py`, `scripts/check_crr_rules.py`. **The reference tree is not present in this repo by default.** Before any task that names it as a source, the orchestrator must either (a) vendor the specific reference files into `docs/dev/reference/` so any worker on any machine can find them, or (b) supply the worker the current macOS path to a local checkout. If neither is available, **derive the algorithm from the specs and standards alone** — do not invent a path or attempt to read a Linux path on macOS. **Every reuse must drop the prohibited `from __future__ import annotations` (PEP 649) and take `scale` as a per-attribute parameter, never read it from a dimension.** The old `repository.py` is the antipattern being replaced — do not consult it.

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
    quantity.py                         # QUANTITY_SCALE = 6; encode_quantity / decode_quantity (Decimal <-> scaled-int+exact)
  db/
    connection.py                       # connect(): FK off, WAL, cr-sqlite load (guarded)
    migrations.py                       # migration runner + schema_migration
    migrations_sql/                     # numbered .sql files (DDL + REF seeds); one per domain group
  models/                               # frozen Pydantic, one class per file, by domain
    schema/ category/ display/ identity/ item/ attrvalue/
    instance/ event/ vendor/ project/ invoice/ bom/ misc/ admin/ readmodel/
  session.py                            # Session (Unit of Work): connection + transaction + identity map
  registry.py                           # AppRegistry skeleton (load hook; populated by Track 2 U1)
scripts/
  check_crr_rules.py                    # CRR CI guard (all 5 rules)
tests/
  conftest.py                           # conn fixture (in-memory + migrations), seed fixtures
  ...                                   # mirrors src layout
```

---

## Task 1: Project scaffold

**Files:** `pyproject.toml`, `src/thinghound/__init__.py`, `tests/test_version.py`.

- [ ] **Step 1: Branch** (after authorization) `feat/track1-foundation` from the base the user names.
- [ ] **Step 2: `pyproject.toml`** — `requires-python = ">=3.14"`; deps `pydantic>=2.7, pint>=0.24, jinja2>=3.1, simpleeval>=0.9.13`; dev `pytest>=8, ruff>=0.6`; hatchling build with `packages = ["src/thinghound"]`; ruff `line-length=100`, `target-version="py314"`, `extend-exclude=["docs/", ".venv/"]`, lint `select=["E","F","I","UP","B"]`; pytest `pythonpath=["src","."]`, `testpaths=["tests"]`.
- [ ] **Step 3: version module** — `src/thinghound/__init__.py` with `__version__ = "0.1.0"`.
- [ ] **Step 4: failing smoke test** — `tests/test_version.py` asserting `thinghound.__version__ == "0.1.0"`.
- [ ] **Step 5: venv + install** — create the venv from the project's Python 3.14 interpreter, `pip install -e ".[dev]"`.
- [ ] **Step 6: run + commit** — `pytest -q` (1 passed), `ruff check .` (clean), commit `chore: project scaffold`.

---

## Task 2: `UUIDv7` type

**Files:** `src/thinghound/types.py`, `tests/test_types.py`.

- [x] **Step 1: failing tests** — `new_id().version == 7`; a frozen model with `id: UUIDv7` accepts a v7 id and rejects a v4 id (raises `ValueError`).
- [x] **Step 2: run → fail** (`No module named thinghound.types`).
- [x] **Step 3: implement:**

```python
"""Domain identifier types. UUIDv7 for all IDs; canonical string only at the bridge."""

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
- [x] **Step 2: run → fail. Step 3: implement** a `@dataclass(frozen=True)` `Money(amount_minor: int, currency: str)` with `__post_init__` validation, `from_decimal`, `to_decimal`, `add` (port from reference `money.py`, **without** the `__future__` import; on 3.14 unquoted forward refs are fine).
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
- [x] **Step 6: temporal helpers** — `src/thinghound/value/temporal.py`: `iso_to_epoch(s: str) -> int` and `epoch_to_iso(ms: int) -> str` (epoch **milliseconds, UTC**; exact integer; raise a typed error on malformed input). Tests: round-trip `epoch_to_iso(iso_to_epoch(x)) == x` for a UTC ISO-8601 string; known value (`"1970-01-01T00:00:00Z" -> 0`). These are pure value utilities the **mappers** call at the storage boundary; models keep ISO-8601 strings. Commit `feat: ISO-8601 ↔ epoch-ms temporal conversion`.
- [x] **Step 7: quantity helpers** — `src/thinghound/value/quantity.py`: `QUANTITY_SCALE = 6` and `encode_quantity(d: Decimal) -> tuple[int, str]` / `decode_quantity(scaled: int) -> Decimal` (dual-column at the fixed quantity scale; reuse `encode_scaled`/`decode_scaled` with `QUANTITY_SCALE`; raise `ScaleOverflowError` past int64). Tests: exact round-trip; a value finer than 10⁻⁶ raises (or is rejected) per the quantization rule chosen. Factors/rates do **not** use this — they store a single `*_exact TEXT` (architecture §9). Commit `feat: fixed-scale quantity encoding (scale 6)`.

---

## Task 6: Database connection

**Files:** `src/thinghound/db/connection.py`, `tests/db/test_connection.py`.

- [x] **Step 1: failing tests** — `connect(":memory:")` has `PRAGMA foreign_keys == 0`; a file db is in `WAL` mode.
- [x] **Step 2: run → fail. Step 3: implement** `connect(path, *, load_crsqlite=False)`: `sqlite3.connect`, `row_factory = sqlite3.Row`, `PRAGMA foreign_keys=OFF`, `PRAGMA journal_mode=WAL` (skip for `:memory:`). cr-sqlite loading is guarded by `enable_load_extension` availability (may be absent in this environment per spike findings; default off). No row↔model conversion here — this layer only configures the connection.
- [x] **Step 4: run → pass; commit** `feat: configured SQLite connection (FK off, WAL)`.

---

## Task 7: Migration runner

**Files:** `src/thinghound/db/migrations.py`, `tests/db/test_migrations.py`. Reference: `reference-old-code/.../db/migrations.py`.

- [x] **Step 1: failing tests** — `apply_all(conn)` records version `"0001"`; second `apply_all` is a no-op (idempotent); `applied_versions` returns a sorted list.
- [x] **Step 2: run → fail. Step 3: implement** `schema_migration(version TEXT PRIMARY KEY, name TEXT, checksum TEXT, applied_at INTEGER)` (LOCAL; `applied_at` epoch ms); discover `migrations_sql/*.sql` by numeric prefix; apply each unapplied file in a transaction; record a SHA-256 checksum; raise if an applied migration's checksum changed; forward-only. Provide a minimal `0001` stub so the runner has input (Task 9 fills it).
- [x] **Step 4: run → pass; commit** `feat: migration runner with checksums`.

---

## Task 8: CRR CI guard (all 5 rules) + correct `crr-rules.md`

**Files:** `scripts/check_crr_rules.py`, `tests/test_crr_rules.py`. Authority: `architecture.md §6.8`, `standards-sql.md`, `crsqlite-spike-findings.md`. The old guard only checked AUTOINCREMENT/REAL/FK/missing-PK; it must also enforce the NOT-NULL-default and no-cross-column-CHECK rules.

- [ ] **Step 1: failing tests** (one per rule) against a `check_sql(sql) -> list[violation]`: flags `AUTOINCREMENT`; flags `REAL`; flags a non-PK `NOT NULL` with no `DEFAULT`; allows `NOT NULL DEFAULT ''`; flags a cross-column `CHECK` (references >1 column); allows a single-column `CHECK`; flags `FOREIGN KEY`/`REFERENCES`; exempts `-- sync: LOCAL` / `REF` tables.
- [ ] **Step 2: run → fail. Step 3: implement** `check_sql` + `main()` scanning `migrations_sql/*.sql`, classifying tables by the `-- sync:` comment (CRR/LOG enforced; LOCAL/REF exempt), detecting cross-column CHECK by counting distinct known column identifiers in each `CHECK(...)` body, and (rule 5) warning if an `ALTER TABLE` on a CRR table appears without `crsql_begin_alter`/`crsql_commit_alter`.
- [ ] **Step 4: run → pass. Step 5: correct the doc** — `docs/dev/crr-rules.md`'s "compliant example" currently shows `name TEXT NOT NULL UNIQUE`, which violates rule 1 and adds a hazardous secondary `UNIQUE`; change to `name TEXT NOT NULL DEFAULT ''` with no secondary UNIQUE, switch attribution columns to `BLOB`, and reconcile with `architecture.md §6.8`.
- [ ] **Step 6: wire into CI; commit** `feat: CRR guard (all five rules) + correct crr-rules.md`.

---

## Task 9: Migration 0001 — REF code tables + seeds

**Files:** `migrations_sql/0001_ref_code_tables.sql`, `tests/db/test_ref_seed.py`.

All 24 code tables from `data-model.md §3` (`value_type`, `value_kind_hint`, `source_layer`, `aggregate_function`, `grid_scope`, `instance_display`, `sort_direction`, `lifecycle_status`, `stock_mode`, `instance_kind`, `relationship_type`, `provenance`, `instance_status`, `event_type`, `project_status`, `match_status`, `import_kind`, `availability_status`, `bom_status`, `build_status`, `formula_layer`, `ltspice_template_type`, `extraction_status`, `file_type`). Each: `code TEXT PRIMARY KEY, name TEXT, description TEXT`, `-- sync: REF`, seeded with the exact rows from §3.

- [ ] **Step 1: failing tests** — e.g. `value_type` has 8 codes; `event_type` code `C` is `Consume`.
- [ ] **Step 2: run → fail. Step 3: write the full SQL; run → pass; CRR guard clean. Step 4: commit** `feat: migration 0001 — REF code tables + seeds`.

---

## Task 10: Migrations 0002–0013 — full CRR/LOG/LOCAL schema (one task per group)

**Files:** `migrations_sql/000N_<name>.sql` (one per domain group), `tests/db/test_schema_<name>.py`.

DDL for **every** entity in `data-model.md §4–§19`. Each sub-task below is **one migration file, one matching schema-shape test file, one commit**. Field lists come **verbatim** from `data-model.md`; do not invent columns.

**DDL rules (the CRR guard from Task 8 enforces them on every group below):**
- PK `id BLOB PRIMARY KEY` (UUIDv7 bytes); junctions use composite PK; code/natural-key tables as specified.
- Every non-PK `NOT NULL` column has a `DEFAULT`; prefer **nullable + service-enforced "required"** where a default is unnatural (spike findings).
- **No** `FOREIGN KEY`/`REFERENCES`, **no** `AUTOINCREMENT`, **no** `REAL`, **no** secondary `UNIQUE` on natural keys (SKU/MPN/manufacturer name — uniqueness is service-enforced, `architecture.md §6.5`).
- **No cross-column `CHECK`.** Single-column tombstone checks allowed.
- Attribution: `created_by_user_id BLOB DEFAULT NULL`, `updated_by_user_id BLOB DEFAULT NULL` on every CRR table; `user_id BLOB DEFAULT NULL` on every LOG table.
- Logical `Decimal` is encoded **by role** (`architecture.md §9`): **attribute values** → `*_scaled INTEGER` + `*_exact TEXT` at the owning `attribute_definition.scale`; **quantities** (`qty_*`, `moq`, `order_multiple`, `reorder_*`, `safety_stock`, read-model `qty_*`) → `*_scaled INTEGER` + `*_exact TEXT` at **fixed quantity scale 6**; **factors/rates** (`unit_multiplier.factor`, `prefix.factor`, `fx_rate.rate`) → **single `*_exact TEXT`**, no `*_scaled`. Logical `Money` → `*_minor INTEGER` + `*_currency TEXT`. `-- sync:` comment above every `CREATE`.
- `Timestamp`/`Date` columns are `INTEGER` epoch (epoch ms, UTC), never `TEXT`; the mapper (Track 2) encodes ISO-8601 ↔ epoch at the storage boundary. `HLC` columns are `TEXT`.

**Per-group rhythm (apply to every sub-task 10a–10l):**
1. Write the named failing schema-shape test (specific assertions below per group).
2. `pytest -q tests/db/test_schema_<name>.py` → FAIL (table/column missing).
3. Write the DDL in `migrations_sql/000N_<name>.sql`, one `-- sync:` comment per `CREATE`.
4. `pytest -q tests/db/test_schema_<name>.py` → PASS; `python scripts/check_crr_rules.py migrations_sql/000N_<name>.sql` → zero violations.
5. Run the cross-cutting `test_no_migration_violates_crr_rules` (all `*.sql` pass `check_sql`).
6. **Commit (after authorization):** `feat(migrations): 000N <name>`.

### Task 10a — `0002_config_schema.sql` — config & schema registry
**Tables (`data-model.md §4`):** `unit_dimension`, `unit_multiplier`, `prefix_set`, `prefix`, `attribute_category`, `attribute_definition`, `attribute_allowed_prefix`, `attribute_enum_value`, `attribute_component`.
- [ ] Failing test `test_schema_config`: `unit_dimension.id` is BLOB PK; `attribute_definition.scale` is INTEGER NOT NULL DEFAULT 0; `attribute_definition` has no secondary UNIQUE on `(name, attribute_category_id)`; `attribute_component.attribute_id BLOB DEFAULT NULL` (single FK to the owning composite `attribute_definition` — no `parent_`/`child_` split); every CRR table has `created_by_user_id BLOB DEFAULT NULL` and `updated_by_user_id BLOB DEFAULT NULL`.
- [ ] Implement; run; CRR guard clean; commit `feat(migrations): 0002 config & schema registry`.

### Task 10b — `0003_category_display.sql` — category & display profile
**Tables (`data-model.md §5–§6`):** `category`, `category_attribute`, `display_profile`, `display_column`, `category_column_mapping`, `grid_configuration`, `grid_configuration_column`, `grid_configuration_grouping`.
- [ ] Failing test `test_schema_category_display`: `category.parent_id` BLOB DEFAULT NULL (self-referencing without FK); `category_attribute` composite PK `(category_id, attribute_id)` (field is `attribute_id`, not `attribute_definition_id`); `display_column.id` is BLOB PK; `grid_configuration_column` has `position INTEGER NOT NULL DEFAULT 0`.
- [ ] Implement; commit `feat(migrations): 0003 category & display`.

### Task 10c — `0004_identity_item.sql` — identity & item
**Tables (`data-model.md §7–§8`):** `manufacturer`, `product_series`, `series_attribute_default`, `item`, `item_category`, `item_relationship`.
- [ ] Failing test `test_schema_identity_item`: `item` has `sku TEXT DEFAULT NULL` with **no secondary UNIQUE** (uniqueness is service-enforced); `manufacturer_name` likewise; `item.primary_category_id BLOB DEFAULT NULL`; `item_category` composite PK `(item_id, category_id)`; `item_relationship.relationship_type_code TEXT NOT NULL DEFAULT ''`.
- [ ] Implement; commit `feat(migrations): 0004 identity & item`.

### Task 10d — `0005_attr_values.sql` — item attribute values
**Tables (`data-model.md §9`):** `item_attribute_value`, `item_attribute_component_value`.
- [ ] Failing test `test_schema_attr_values`: `item_attribute_value` has `value_scaled INTEGER DEFAULT NULL`, `value_exact TEXT DEFAULT NULL`, `value_raw TEXT DEFAULT NULL`, `display_unit TEXT DEFAULT NULL`, `provenance_code TEXT NOT NULL DEFAULT ''`; **no cross-column CHECK** between `value_scaled` and `value_exact` (that invariant is service-enforced); composite component value table mirrors structure.
- [ ] Implement; commit `feat(migrations): 0005 attribute values`.

### Task 10e — `0006_instances_events_location_currency_fx.sql`
**Tables (`data-model.md §10–§11` + `§15`):** `location`, `item_instance`, `instance_measurement`, `inventory_event` (**LOG**), `currency`, `fx_rate`. (`location` is included here because it is referenced by `inventory_event.from_location_id`/`to_location_id` and `item_instance.current_location_id`; since FK enforcement is OFF, ordering is not mandatory, but colocation keeps the operational schema coherent.)
- [ ] Failing test `test_schema_inventory`: `location.parent_id BLOB DEFAULT NULL` (self-referencing, no FK); `inventory_event` is LOG-shaped — `-- sync: LOG` comment present, `user_id BLOB DEFAULT NULL` (LOG attribution form), `(effective_date INTEGER, hlc TEXT, id BLOB)` columns all present, no UPDATE-style attribution; `fx_rate.rate_exact TEXT DEFAULT NULL` with **no** `rate_scaled` (factors/rates role — architecture §9); `currency.code TEXT PRIMARY KEY` (ISO-4217 code is the natural PK).
- [ ] Implement; commit `feat(migrations): 0006 instances, events, location, currency, FX`.

### Task 10f — `0007_vendor_pricing.sql`
**Tables (`data-model.md §14`):** `vendor`, `vendor_offer`, `price_break`, `offer_history` (**LOG**).
- [ ] Failing test `test_schema_vendor`: `vendor_offer.currency TEXT NOT NULL DEFAULT ''` (the offer's ISO-4217 currency code — `vendor_offer` carries no unit price; price lives on `price_break`); `price_break.unit_price_minor INTEGER NOT NULL DEFAULT 0` + `unit_price_currency TEXT NOT NULL DEFAULT ''`; `price_break.qty_min_scaled INTEGER DEFAULT NULL` + `qty_min_exact TEXT DEFAULT NULL` (quantity role, scale 6); `offer_history` is LOG-shaped (`user_id BLOB DEFAULT NULL`).
- [ ] Implement; commit `feat(migrations): 0007 vendor & pricing`.

### Task 10g — `0008_project_invoice.sql`
**Tables (`data-model.md §12–§13`):** `project`, `invoice`, `invoice_line`, `import_template`.
- [ ] Failing test `test_schema_project_invoice`: `invoice_line.qty_scaled INTEGER DEFAULT NULL` + `qty_exact TEXT DEFAULT NULL`; `invoice_line.item_id BLOB DEFAULT NULL` (the resolved item match — field is `item_id`, not `matched_item_id`); `import_template.mapping TEXT NOT NULL DEFAULT '{}'` (JSON column; field is `mapping`, not `template_json`).
- [ ] Implement; commit `feat(migrations): 0008 project & invoice`.

### Task 10h — `0009_bom_build.sql`
**Tables (`data-model.md §16`):** `bom`, `bom_revision`, `bom_line`, `bom_line_substitute`, `build`.
- [ ] Failing test `test_schema_bom_build`: `bom_revision.status_code TEXT NOT NULL DEFAULT ''` (DRAFT/RELEASED/OBSOLETE in REF table 0001); `bom_line.qty_per_scaled INTEGER DEFAULT NULL` + `qty_per_exact TEXT DEFAULT NULL`; `bom_line_substitute` composite PK `(bom_line_id, substitute_item_id)`; `build.status_code TEXT NOT NULL DEFAULT ''`.
- [ ] Implement; commit `feat(migrations): 0009 BOM & build`.

### Task 10i — `0010_misc.sql` — tags, formulas, LTspice, extraction
**Tables (`data-model.md §17`):** `tag`, `item_tag`, `attribute_formula`, `formula_input`, `formula_category`, `ltspice_template`, `ltspice_template_param`, `datasheet_extraction`.
- [ ] Failing test `test_schema_misc`: `item_tag` composite PK `(item_id, tag_id)`; `attribute_formula.enabled INTEGER NOT NULL DEFAULT 1` (Boolean as INTEGER); `formula_input.layer_code TEXT NOT NULL DEFAULT ''` (the `formula_layer` REF code lives on `formula_input`, not on `attribute_formula`); `datasheet_extraction.status_code TEXT NOT NULL DEFAULT ''`; `tag.name TEXT NOT NULL DEFAULT ''` (no secondary UNIQUE — service-enforced).
- [ ] Implement; commit `feat(migrations): 0010 misc`.

### Task 10j — `0011_admin.sql` — attachments, settings, users, RBAC
**Tables (`data-model.md §18`):** `attachment`, `app_setting`, `device_setting` (LOCAL), `user`, `role`, `permission`, `role_permission`, `user_role`.
- [ ] Failing test `test_schema_admin`: `attachment.file_type_code TEXT NOT NULL DEFAULT ''`; `item_attachment` composite PK `(item_id, attachment_id)`; `invoice_attachment` composite PK `(invoice_id, attachment_id)`; `device_setting` is `-- sync: LOCAL`; `permission.key TEXT NOT NULL DEFAULT ''`; `role_permission` composite PK `(role_id, permission_id)`; `user_role` composite PK `(user_id, role_id)`.
- [ ] Implement; commit `feat(migrations): 0011 admin`.

### Task 10k — `0012_local_read_models.sql` — LOCAL read-model tables + FTS5
**Tables:** `rm_item_stock`, `rm_stock_by_location`, `rm_instance_state`, `rm_thumbnail`, `fts_item` (FTS5 external-content + trigram tokenizer).
- [ ] Failing test `test_schema_read_models`: every `rm_*` table is `-- sync: LOCAL`; `rm_item_stock` has `qty_available_scaled INTEGER NOT NULL DEFAULT 0` + `qty_available_exact TEXT NOT NULL DEFAULT '0'`, and likewise `qty_assigned_scaled/exact`, `qty_waste_scaled/exact`, `qty_lost_scaled/exact` (all quantity role, scale 6), plus `avg_landed_cost_minor INTEGER NOT NULL DEFAULT 0` + `avg_landed_cost_currency TEXT NOT NULL DEFAULT ''` and `last_unit_cost_minor`/`last_unit_cost_currency`; `fts_item` is created with `tokenize='trigram'` and `content='item'` (external-content). **Trigger bodies for `rm_item_stock` maintenance are owned by Track-2 U5** — this migration may create the table and leave triggers to U5, or create stub triggers that U5 replaces. Document the handoff in the SQL file's leading comment.
- [ ] Implement; commit `feat(migrations): 0012 LOCAL read-models + FTS5`.

### Task 10l — `0013_indexes.sql` — performance indexes (`data-model.md §20`)
- [ ] Failing test `test_schema_indexes`: every named index from §20 exists in `sqlite_master`; no index is on a column that violates DDL rules (e.g. no index on a `REAL` column — there are none).
- [ ] Implement; commit `feat(migrations): 0013 indexes`.

### Task 10-final — cross-cutting verification
- [ ] **Cross-cutting test** `test_no_migration_violates_crr_rules`: every `migrations_sql/*.sql` file passes `check_sql` with zero violations (LOCAL/REF tables exempt per their `-- sync:` comments).
- [ ] **Cross-cutting test** `test_migrations_apply_cleanly`: `apply_all(connect(":memory:"))` succeeds; `applied_versions` returns `["0001","0002",…,"0013"]`; a second `apply_all` is a no-op.
- [ ] **Commit (after authorization):** `test(migrations): cross-cutting CRR + apply-clean coverage`.

---

## Task 11: Pydantic domain models (one task per domain subpackage)

**Files:** `src/thinghound/models/<domain>/<entity>.py` (one class per file), `tests/models/<domain>/test_<entity>.py`.

A frozen Pydantic model for **every** entity in `data-model.md §4–§19` (REF code tables share a small `CodeRow` model). Per `standards-data-models.md`: `UUIDv7` ids; `*_code` fields are `str` validated against the loaded code table **at the service layer** (never `Literal`/`Enum`); `Money` for money; dimensional values via `ScaledValue`/`Decimal`; `X | None` for nullable with each absence justified in a field comment; attribution fields per sync class.

**Models own their own value conversion** (encode/decode of `ScaledValue`, `Money`) — but they do **not** read or write the database, and they do **not** know about rows. (Row↔model assembly is the mapper's job in Track 2.) Timestamp/date fields carry **ISO-8601 strings** in the model (e.g. `deleted_at: str | None`); the mapper converts them to/from the SQLite epoch integer — models never hold the epoch int.

**Per-entity rhythm (apply to every entity in every sub-task below):**
1. Write the failing model test: construct with valid fields; assert one model-level invariant (e.g. non-v7 id rejected; `frozen=True` rejects mutation; `*_code` field accepts `str`).
2. `pytest -q tests/models/<domain>/test_<entity>.py` → FAIL.
3. Implement `src/thinghound/models/<domain>/<entity>.py` (one class per file), mirroring `data-model.md` field list **verbatim**. Justify each `X | None` in a field comment.
4. `pytest -q tests/models/<domain>/test_<entity>.py` → PASS.
5. Add model validators only for **single-entity** invariants (cross-entity checks are service-layer).

**Per-sub-task commit (after authorization):** one commit per domain subpackage — `feat(models): <domain> entities`.

---

### Worked example A — simple entity (single value, no `ScaledValue`/`Money`)

`src/thinghound/models/schema/unit_dimension.py`:

```python
"""Domain model for a unit dimension (a measurable domain with a base unit)."""

from pydantic import BaseModel, ConfigDict

from thinghound.types import UUIDv7


class UnitDimension(BaseModel):
    """A measurable domain (Resistance, Mass, Length) with a defined base unit."""

    model_config = ConfigDict(frozen=True)

    id: UUIDv7
    name: str
    base_unit: str
    deleted_at: str | None = None             # NULL = active; ISO-8601 = soft-deleted
    created_by_user_id: UUIDv7 | None = None  # NULL = single-user/legacy write
    updated_by_user_id: UUIDv7 | None = None
```

### Worked example B — compound natural-key entity (`item`, §8)

`item` has multiple optional natural-key fields (`sku`, `manufacturer_part_number`, `gpn`) whose uniqueness is **service-enforced**, not model-enforced. The model just types them.

```python
"""Domain model for a catalog item — root of the item aggregate."""

from pydantic import BaseModel, ConfigDict

from thinghound.types import UUIDv7


class Item(BaseModel):
    """A catalog item (a part, not a physical instance). Identity is the UUIDv7;
    SKU/MPN/GPN are optional natural keys whose uniqueness is enforced by the
    service layer (cr-sqlite forbids secondary UNIQUE on CRR tables)."""

    model_config = ConfigDict(frozen=True)

    id: UUIDv7
    sku: str | None = None                       # NULL = no internal SKU assigned yet
    manufacturer_id: UUIDv7 | None = None        # NULL = generic/unbranded
    manufacturer_part_number: str | None = None  # NULL when manufacturer_id is NULL
    gpn: str | None = None                       # generic part number; alternative to MPN
    product_series_id: UUIDv7 | None = None      # NULL = not part of a series
    primary_category_id: UUIDv7 | None = None    # NULL until categorised; required at service write
    lifecycle_status_code: str = ""              # validated against REF lifecycle_status at service
    description: str | None = None
    deleted_at: str | None = None
    created_by_user_id: UUIDv7 | None = None
    updated_by_user_id: UUIDv7 | None = None
```

### Worked example C — LOG entity with `Money` (`inventory_event`, §11)

LOG semantics: **insert-only**, no UPDATE attribution. Attribution is a single `user_id`, not the `created_by/updated_by` pair. The event carries a unit cost as `Money`.

```python
"""Domain model for an inventory event (LOG: append-only, single-writer)."""

from pydantic import BaseModel, ConfigDict

from thinghound.money import Money
from thinghound.types import UUIDv7


class InventoryEvent(BaseModel):
    """A single append-only inventory event. Ordered by (effective_date, hlc, id).
    Carries optional unit cost as Money (price_minor + currency); never a float."""

    model_config = ConfigDict(frozen=True)

    id: UUIDv7
    item_id: UUIDv7
    location_id: UUIDv7 | None = None         # NULL = unscoped / bulk
    event_type_code: str                       # ADD/CONSUME/ADJUST/MOVE/INDIVIDUATE — REF
    qty_scaled: int                            # scale 6 (fixed quantity scale)
    qty_exact: str                             # exact decimal string at scale 6
    unit_cost: Money | None = None             # NULL when event has no cost (CONSUME/MOVE)
    effective_date: str                        # ISO-8601 (UTC); mapper encodes epoch
    hlc: str                                   # hybrid logical clock token
    reason: str | None = None                  # required by SERVICE for ADJUST
    source_location_id: UUIDv7 | None = None   # required by SERVICE for MOVE
    dest_location_id: UUIDv7 | None = None     # required by SERVICE for MOVE
    user_id: UUIDv7 | None = None              # LOG attribution (single field)
```

### Worked example D — value-bearing aggregated child (`item_attribute_value`, §9)

Carries a `ScaledValue` round-trip + a `provenance_code`. Scale is **per-attribute**, read from the owning `attribute_definition` at write time (not stored on the model).

```python
"""Domain model for a per-item attribute value (child of the Item aggregate)."""

from pydantic import BaseModel, ConfigDict

from thinghound.types import UUIDv7
from thinghound.value.scaled_value import ScaledValue


class ItemAttributeValue(BaseModel):
    """One attribute value on one item. The scaled-int/exact-text pair is encoded
    at the attribute_definition.scale by the service write path; the model
    stores the already-encoded ScaledValue."""

    model_config = ConfigDict(frozen=True)

    id: UUIDv7
    item_id: UUIDv7
    attribute_definition_id: UUIDv7
    value: ScaledValue | None = None      # NULL when attribute is text/enum (use value_text)
    value_text: str | None = None         # NULL when attribute is numeric (use value)
    provenance_code: str = ""             # M/D/T/I — manual/derived/template/imported (REF)
    created_by_user_id: UUIDv7 | None = None
    updated_by_user_id: UUIDv7 | None = None
```

The four worked examples above cover the four shapes that appear across the ~60 entities: simple, compound natural-key, LOG with `Money`, value-bearing with `ScaledValue`. Every sub-task below picks the matching shape.

---

### Sub-tasks (one per domain subpackage)

Entity lists come **verbatim** from `data-model.md`. If a section adds/removes entities, the **data-model.md wins** — update the sub-task here and re-run the affected tests.

- [ ] **Task 11a — `models/schema/`** (`data-model.md §4`): `UnitDimension`, `UnitMultiplier`, `PrefixSet`, `Prefix`, `AttributeCategory`, `AttributeDefinition`, `AttributeAllowedPrefix`, `AttributeEnumValue`, `AttributeComponent`. Shape: simple. Commit `feat(models): schema entities`.
- [ ] **Task 11b — `models/category/`** (§5): `Category`, `CategoryAttribute`. Shape: simple + composite-PK junction (`CategoryAttribute(category_id, attribute_id)` — field is `attribute_id` per data-model §5; model has both IDs, no synthetic `id`). Commit `feat(models): category entities`.
- [ ] **Task 11c — `models/display/`** (§6): `DisplayProfile`, `DisplayColumn`, `CategoryColumnMapping`, `GridConfiguration`, `GridConfigurationColumn`, `GridConfigurationGrouping`. Shape: simple. Commit `feat(models): display & grid-config entities`.
- [ ] **Task 11d — `models/identity/`** (§7): `Manufacturer`, `ProductSeries`, `SeriesAttributeDefault`. Shape: simple; `SeriesAttributeDefault.value` is `ScaledValue | None`. Commit `feat(models): identity entities`.
- [ ] **Task 11e — `models/item/`** (§8): `Item` (use worked example B), `ItemCategory` (junction), `ItemRelationship`. Commit `feat(models): item entities`.
- [ ] **Task 11f — `models/attrvalue/`** (§9): `ItemAttributeValue` (use worked example D), `ItemAttributeComponentValue` (same shape, component-keyed). Test specifically that `ScaledValue.value_scaled` fits in int64 and that mutating a constructed model raises. Commit `feat(models): attribute-value entities`.
- [ ] **Task 11g — `models/instance/`** (§10): `ItemInstance`, `InstanceMeasurement` (measurement value is `ScaledValue`). Commit `feat(models): instance entities`.
- [ ] **Task 11h — `models/event/`** (§11): `InventoryEvent` (use worked example C), `Currency`, `FxRate`. `FxRate.rate` is `Decimal` in the domain model — the mapper stores it as `rate_exact TEXT` (factors/rates role, architecture §9); the model never holds the raw text. Commit `feat(models): event, currency, FX entities`.
- [ ] **Task 11i — `models/vendor/`** (§14): `Vendor`, `VendorOffer` (`currency: str` — the offer's ISO-4217 currency code; `vendor_offer` carries no unit price), `PriceBreak` (`qty_min: ScaledValue` at quantity scale 6; `unit_price: Money`), `OfferHistory` (LOG; `user_id`). Commit `feat(models): vendor & pricing entities`.
- [ ] **Task 11j — `models/project/`** (§12): `Project`. Commit `feat(models): project entity`.
- [ ] **Task 11k — `models/invoice/`** (§13): `Invoice`, `InvoiceLine` (`qty: ScaledValue` at scale 6; `unit_price: Money | None`), `ImportTemplate` (`mapping: str` — JSON column stored as TEXT; field is `mapping`, not `template_json`). Commit `feat(models): invoice entities`.
- [ ] **Task 11l — `models/bom/`** (§16): `Bom`, `BomRevision`, `BomLine` (`qty_per: ScaledValue` at scale 6), `BomLineSubstitute` (junction), `Build`. Commit `feat(models): BOM & build entities`.
- [ ] **Task 11m — `models/misc/`** (§17): `Tag`, `ItemTag` (junction), `AttributeFormula`, `FormulaInput` (`layer_code: str`), `FormulaCategory` (junction: `formula_id` + `category_id`), `LtspiceTemplate`, `LtspiceTemplateParam`, `DatasheetExtraction`. Commit `feat(models): misc entities`.
- [ ] **Task 11n — `models/admin/`** (§15 + §18): `Location` (§15 — self-referencing `parent_id: UUIDv7 | None`), `Attachment` (§18 — no owner fields), `ItemAttachment` (junction), `InvoiceAttachment` (junction), `AppSetting`, `DeviceSetting`, `User`, `Role`, `Permission`, `RolePermission` (junction), `UserRole` (junction). Commit `feat(models): location, admin & RBAC entities`.
- [ ] **Task 11o — `models/readmodel/`** (LOCAL read-model projections — distinct from write aggregates): `RmItemStock`, `RmStockByLocation`, `RmInstanceState`, `RmThumbnail`. These are **projection read models** (`architecture.md §4.4`), not write aggregates; they have no attribution columns and no soft-delete. Quantities use `ScaledValue` at scale 6. Commit `feat(models): LOCAL read-model projections`.

- [x] **Task 11-final — `CodeRow`** (`src/thinghound/models/code_row.py`): a tiny shared model `CodeRow(code: str, name: str, description: str | None = None)` used by every REF code table the registry loads. One failing test, implement, commit `feat(models): shared CodeRow`.

> Verification at end of Task 11: `pytest -q tests/models/` is fully green; every entity in `data-model.md §3–§19` has exactly one model file and one test file; no model imports `sqlite3` (a quick `grep -rn "import sqlite3" src/thinghound/models/` returns nothing — models never know about rows).

---

## Task 12: Session / Unit of Work

**Files:** `src/thinghound/session.py`, `tests/test_session.py`.

The Session is the coordinator (`architecture.md §4.6`): connection, transaction scope, identity map. **It owns no table SQL and performs no row↔model conversion.** (When Track-2 mappers exist, the session exposes them and owns the transaction they run in — but the session itself never maps a row.)

- [x] **Step 1: failing tests** — `with session.transaction():` commits on success and rolls back on exception (verified by row counts against a REF table); `get_identity`/`put_identity` round-trip an object in the identity map.
- [x] **Step 2: run → fail. Step 3: implement** `Session(conn)`: `transaction()` context manager (`BEGIN`/`COMMIT`/`ROLLBACK`); a `dict[type, dict[uuid.UUID, object]]` identity map with `get_identity`/`put_identity`. No SQL constants, no `_*_from_row` — those belong to mappers.
- [x] **Step 4: run → pass; commit** `feat: Session (unit of work: transaction + identity map)`.

---

## Task 13: AppRegistry skeleton

**Files:** `src/thinghound/registry.py`, `tests/test_registry.py`.

- [ ] **Step 1: failing test** — accessors raise `RegistryNotLoadedError` before `load`.
- [ ] **Step 2: run → fail. Step 3: implement** `AppRegistry` skeleton: a `load(session)` hook (sets `_loaded`; the **real** mapper-driven population of dimensions/multipliers/prefixes/attribute categories+definitions/category tree/grid configs is Track-2 U1) and accessors (`unit_dimensions()`, `attribute_definitions()`, `category_tree()`, `factors_for(dimension_id)`) that raise until loaded. The registry calls **mappers** to load (in Track 2); it never issues raw row↔model conversion itself.
- [ ] **Step 4: run → pass; commit** `feat: AppRegistry skeleton (structure load hook)`.

---

## Task 14: conftest + Gate A verification

**Files:** `tests/conftest.py`.

- [ ] **Step 1:** `conftest.py` providing `conn` (in-memory + `apply_all`), `migrated_conn` alias, and seed fixtures (`resistance_dimension`, `electrical_category`) on top of `conn` (`standards-testing.md`). Domain tests use `conn`; only migration-runner tests call `apply_all` directly.
- [ ] **Step 2: Gate A check** (paste real output): `pytest -q` all green; `ruff check .` clean; `python scripts/check_crr_rules.py` zero violations across all migrations.
- [ ] **Step 3: commit** `test: conftest fixtures; Gate A green`. Foundation complete; Track 2 may begin.

---

## Self-Review (run after execution, against the specs)

- **Coverage:** every entity in `data-model.md §3–§19` has a migration (T9–T10) and a model (T11); every invariant in `coding_standards.md` is enforced by a test or the guard; the value engine covers `functional-spec.md §3.3 / §5.4`.
- **Deferred to Track 2 (by design, not gaps):** all aggregate mappers, query objects, services, FTS/trigger logic, registry population, Pint wiring.
- **Layering:** the Session and AppRegistry contain **no** row↔model conversion and **no** table SQL; models convert only their own values; there is no "repository" class anywhere.
- **Type consistency:** `*_code` is `str` everywhere; ids are `UUIDv7`; money is `Money`; dimensional values are scaled-int + exact-text; `encode_scaled(base, scale)` takes scale as a parameter at every call site.
