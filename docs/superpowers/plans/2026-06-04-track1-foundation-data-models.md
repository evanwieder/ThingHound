# Track 1 — Foundation & Data Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (or superpowers:executing-plans). One careful worker; TDD throughout; commit per task **only after explicit user authorization to begin coding**. Read `coding_standards.md` and the relevant `docs/dev/agent/standards-*.md` before each task. Checkbox (`- [ ]`) steps track progress.

**Authoritative sources:** `docs/specs/thinghound-{functional-spec,architecture,data-model}.md`, `docs/dev/standards-*.md`, `docs/dev/crsqlite-spike-findings.md`, `docs/dev/crr-rules.md`. Where this plan and a doc disagree, the doc wins.

**Goal:** Produce the complete, CRR-correct, sync-ready data foundation: project scaffold, exact-numeric primitives, the unit/value encoding engine, the full Pydantic model set (all entities, all phases), the full migration schema + REF seeds, the rewritten CRR CI guard, the connection, the Session/Unit-of-Work, and the AppRegistry skeleton.

**Architecture:** No ORM. Frozen Pydantic models that own their own value conversion. Hand-written parameterized SQL — but **no aggregate mappers in this track** (those are Track 2). Track 1 ships the schema (DDL), the models, the primitives, and the session/registry seams that Track-2 mappers plug into. SQLite + cr-sqlite + FTS5; exact integers / `Decimal` / `Money` only.

**Layering reminder (program plan §1):** the **Session/Unit-of-Work owns the connection, transaction scope, and identity map only — no table SQL and no row↔model conversion.** Conversion is the aggregate mapper's job (Track 2). Models convert their own values (scaled-int ↔ exact, `Money`). Keep these boundaries intact here so Track 2 can rely on them.

**Reference (consult for algorithms only; never copy verbatim, always reconcile to current docs):** `/home/evan/Projects/thinghound-preserved-20260603/reference-old-code/` — `ids.py`, `money.py`, `units/scale.py`, `db/connection.py`, `db/migrations.py`, `scripts/check_crr_rules.py`. **Every reuse must drop the prohibited `from __future__ import annotations` (PEP 649) and take `scale` as a per-attribute parameter, never read it from a dimension.** The old `repository.py` is the antipattern being replaced — do not consult it.

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

- [ ] **Step 1: failing tests** — `new_id().version == 7`; a frozen model with `id: UUIDv7` accepts a v7 id and rejects a v4 id (raises `ValueError`).
- [ ] **Step 2: run → fail** (`No module named thinghound.types`).
- [ ] **Step 3: implement:**

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

- [ ] **Step 4: run → pass; commit** `feat: UUIDv7 type and id factory`.

---

## Task 3: `Money` value object

**Files:** `src/thinghound/money.py`, `tests/test_money.py`.

- [ ] **Step 1: failing tests** — `from_decimal(Decimal("1.50"),"USD",exponent=2).amount_minor == 150`; rejects excess precision (`Decimal("1.005")`, exp 2); `to_decimal` round-trips; `add` same-currency sums; cross-currency raises; non-int amount raises `TypeError`; bad currency (`"usd"`) raises.
- [ ] **Step 2: run → fail. Step 3: implement** a `@dataclass(frozen=True)` `Money(amount_minor: int, currency: str)` with `__post_init__` validation, `from_decimal`, `to_decimal`, `add` (port from reference `money.py`, **without** the `__future__` import; on 3.14 unquoted forward refs are fine).
- [ ] **Step 4: run → pass; ruff clean; commit** `feat: Money value object`.

---

## Task 4: Value encoding + typed errors

**Files:** `src/thinghound/errors.py`, `src/thinghound/value/encoding.py`, `tests/value/test_encoding.py`.

- [ ] **Step 1: `errors.py`** — `ScaleOverflowError(value: Fraction, scale: int)` and `UnknownUnitError(symbol: str, dimension: str)` (used in Task 5).
- [ ] **Step 2: failing tests** — `encode_scaled(Fraction(1000), 3) == (1_000_000, "1000.000")`; exact round-trip `decode_scaled(encode_scaled(...))`; `½` entry equals `0.5` on `value_exact`; mixed/vulgar/slash parse; overflow raises `ScaleOverflowError`.
- [ ] **Step 3: run → fail. Step 4: implement** `parse_magnitude`, `encode_scaled(base: Fraction, scale: int) -> tuple[int,str]` (raises `ScaleOverflowError`), `decode_scaled` (port from reference `units/scale.py`, drop `__future__`, scale is a parameter; keep `getcontext().prec = 60` and `INT64_MAX`). **Do not** port `normalize`/`Dimension` here.
- [ ] **Step 5: run → pass; commit** `feat: exact value encoding + typed errors`.

---

## Task 5: `ScaledValue` + unit normalization

**Files:** `src/thinghound/value/scaled_value.py`, `src/thinghound/value/normalize.py`, `tests/value/test_normalize.py`.

- [ ] **Step 1: `ScaledValue`** — `@dataclass(frozen=True)` with `value_scaled: int`, `value_exact: str`, `scale: int`, `value_raw: str | None`, `display_unit: str | None`.
- [ ] **Step 2: failing tests** for `normalize(raw, *, factors: dict[str, Fraction], scale: int, dimension_name: str = "")` — `"2.2 kΩ"` with `{Ω:1, kΩ:1000}` at scale 3 → `(2_200_000, "2200.000")`; preserves `value_raw`/`display_unit`; same factors different scale → different `value_exact` precision (scale is per-call); fraction input normalizes; unknown unit raises `UnknownUnitError`.
- [ ] **Step 3: run → fail. Step 4: implement** `_split_input` (NFC, split trailing unit incl. `Ω`/`µ`) + `normalize` (look up `factors[unit]`, `base = parse_magnitude(mag) * factor`, `encode_scaled(base, scale)`). Scale is a parameter — never `Dimension.scale`.

> Production note: in production the `factors` map is derived by the AppRegistry from `unit_multiplier`/`prefix` rows; Pint may parse SI-prefixed/custom units, but **all arithmetic stays in `Fraction`/`Decimal`**. The `factors`-dict signature is the seam; Pint wiring is a Track-2 concern.

- [ ] **Step 5: run → pass; commit** `feat: ScaledValue + exact unit normalization`.
- [ ] **Step 6: temporal helpers** — `src/thinghound/value/temporal.py`: `iso_to_epoch(s: str) -> int` and `epoch_to_iso(ms: int) -> str` (epoch **milliseconds, UTC**; exact integer; raise a typed error on malformed input). Tests: round-trip `epoch_to_iso(iso_to_epoch(x)) == x` for a UTC ISO-8601 string; known value (`"1970-01-01T00:00:00Z" -> 0`). These are pure value utilities the **mappers** call at the storage boundary; models keep ISO-8601 strings. Commit `feat: ISO-8601 ↔ epoch-ms temporal conversion`.
- [ ] **Step 7: quantity helpers** — `src/thinghound/value/quantity.py`: `QUANTITY_SCALE = 6` and `encode_quantity(d: Decimal) -> tuple[int, str]` / `decode_quantity(scaled: int) -> Decimal` (dual-column at the fixed quantity scale; reuse `encode_scaled`/`decode_scaled` with `QUANTITY_SCALE`; raise `ScaleOverflowError` past int64). Tests: exact round-trip; a value finer than 10⁻⁶ raises (or is rejected) per the quantization rule chosen. Factors/rates do **not** use this — they store a single `*_exact TEXT` (architecture §9). Commit `feat: fixed-scale quantity encoding (scale 6)`.

---

## Task 6: Database connection

**Files:** `src/thinghound/db/connection.py`, `tests/db/test_connection.py`.

- [ ] **Step 1: failing tests** — `connect(":memory:")` has `PRAGMA foreign_keys == 0`; a file db is in `WAL` mode.
- [ ] **Step 2: run → fail. Step 3: implement** `connect(path, *, load_crsqlite=False)`: `sqlite3.connect`, `row_factory = sqlite3.Row`, `PRAGMA foreign_keys=OFF`, `PRAGMA journal_mode=WAL` (skip for `:memory:`). cr-sqlite loading is guarded by `enable_load_extension` availability (may be absent in this environment per spike findings; default off). No row↔model conversion here — this layer only configures the connection.
- [ ] **Step 4: run → pass; commit** `feat: configured SQLite connection (FK off, WAL)`.

---

## Task 7: Migration runner

**Files:** `src/thinghound/db/migrations.py`, `tests/db/test_migrations.py`. Reference: `reference-old-code/.../db/migrations.py`.

- [ ] **Step 1: failing tests** — `apply_all(conn)` records version `"0001"`; second `apply_all` is a no-op (idempotent); `applied_versions` returns a sorted list.
- [ ] **Step 2: run → fail. Step 3: implement** `schema_migration(version TEXT PRIMARY KEY, name TEXT, checksum TEXT, applied_at INTEGER)` (LOCAL; `applied_at` epoch ms); discover `migrations_sql/*.sql` by numeric prefix; apply each unapplied file in a transaction; record a SHA-256 checksum; raise if an applied migration's checksum changed; forward-only. Provide a minimal `0001` stub so the runner has input (Task 9 fills it).
- [ ] **Step 4: run → pass; commit** `feat: migration runner with checksums`.

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

All 26 code tables from `data-model.md §3` (`value_type`, `value_kind_hint`, `source_layer`, `aggregate_function`, `grid_scope`, `instance_display`, `sort_direction`, `lifecycle_status`, `stock_mode`, `instance_kind`, `relationship_type`, `provenance`, `instance_status`, `event_type`, `project_status`, `match_status`, `import_kind`, `availability_status`, `bom_status`, `build_status`, `formula_layer`, `ltspice_template_type`, `extraction_status`, `attachment_owner_type`, `attachment_role`, `audit_action`). Each: `code TEXT PRIMARY KEY, name TEXT, description TEXT`, `-- sync: REF`, seeded with the exact rows from §3.

- [ ] **Step 1: failing tests** — e.g. `value_type` has 8 codes; `event_type` code `C` is `Consume`.
- [ ] **Step 2: run → fail. Step 3: write the full SQL; run → pass; CRR guard clean. Step 4: commit** `feat: migration 0001 — REF code tables + seeds`.

---

## Task 10: Migrations 0002…00NN — full CRR/LOG/LOCAL schema

**Files:** `migrations_sql/000N_*.sql` (one per domain group), `tests/db/test_schema.py`.

DDL for **every** entity in `data-model.md §4–§19`, grouped: 0002 config/schema · 0003 category/display · 0004 identity/item · 0005 attr-values · 0006 instances/events/currency/fx · 0007 vendor/pricing · 0008 project/invoice · 0009 bom/build · 0010 misc (tags/formula/ltspice/extraction) · 0011 admin (attachment/settings/user/rbac/audit) · 0012 LOCAL read-model (rm_* + FTS5) · 0013 indexes (§20).

**DDL rules (the CRR guard enforces them):**
- PK `id BLOB PRIMARY KEY` (UUIDv7 bytes); junctions use composite PK; code/natural-key tables as specified.
- Every non-PK `NOT NULL` column has a `DEFAULT`; prefer **nullable + service-enforced "required"** where a default is unnatural (spike findings).
- **No** `FOREIGN KEY`/`REFERENCES`, **no** `AUTOINCREMENT`, **no** `REAL`, **no** secondary `UNIQUE` on natural keys (SKU/MPN/manufacturer name — uniqueness is service-enforced, `architecture.md §6.5`).
- **No cross-column `CHECK`.** Single-column tombstone checks allowed.
- Attribution: `created_by_user_id BLOB DEFAULT NULL`, `updated_by_user_id BLOB DEFAULT NULL` on every CRR table; `user_id BLOB DEFAULT NULL` on every LOG table.
- Logical `Decimal` is encoded **by role** (`architecture.md §9`, "Decimal encoding by role"): **attribute values** → `*_scaled INTEGER` + `*_exact TEXT` at the owning `attribute_definition.scale`; **quantities** (`qty_*`, `moq`, `order_multiple`, `reorder_*`, `safety_stock`, read-model `qty_*`) → `*_scaled INTEGER` + `*_exact TEXT` at **fixed quantity scale 6**; **factors/rates** (`unit_multiplier.factor`, `prefix.factor`, `fx_rate.rate`) → **single `*_exact TEXT`**, no `*_scaled`. Logical `Money` → `*_minor INTEGER` + `*_currency TEXT`. `-- sync:` comment above every `CREATE`.
- `Timestamp`/`Date` columns are `INTEGER` epoch (epoch ms, UTC), never `TEXT`; the mapper (Track 2) encodes ISO-8601 ↔ epoch at the storage boundary. `HLC` columns are `TEXT`.

- [ ] **Cross-cutting test** — `test_no_migration_violates_crr_rules`: every `*.sql` passes `check_sql`. Plus per-group "applies clean to a fresh db" and targeted shape tests (e.g. no UNIQUE on `item.sku`; `inventory_event` is LOG-shaped).
- [ ] Per group 0002→0013, write DDL test-first, green the guard + apply tests, **commit per group**. FTS5 `fts_item` is external-content + trigram; the `rm_item_stock` trigger *logic* is owned by Track-2 U5 (note the handoff — 0012 may create the table and leave trigger bodies to U5).

> Field lists come **verbatim** from `data-model.md §4–§19`. Do not invent columns. Expand `Decimal`/`Money` to their two-column physical encoding. Prefer nullable + service enforcement when NOT NULL is awkward under cr-sqlite.

---

## Task 11: Pydantic domain models (all entities)

**Files:** `src/thinghound/models/<domain>/<entity>.py` (one class per file), `tests/models/<domain>/test_<entity>.py`.

A frozen Pydantic model for **every** entity in `data-model.md §4–§19` (REF code tables share a small `CodeRow` model). Per `standards-data-models.md`: `UUIDv7` ids; `*_code` fields are `str` validated against the loaded code table **at the service layer** (never `Literal`/`Enum`); `Money` for money; dimensional values via `ScaledValue`/`Decimal`; `X | None` for nullable with each absence justified in a field comment; attribution fields per sync class.

**Models own their own value conversion** (encode/decode of `ScaledValue`, `Money`) — but they do **not** read or write the database, and they do **not** know about rows. (Row↔model assembly is the mapper's job in Track 2.) Timestamp/date fields carry **ISO-8601 strings** in the model (e.g. `deleted_at: str | None`); the mapper converts them to/from the SQLite epoch integer — models never hold the epoch int.

Worked example — `src/thinghound/models/schema/unit_dimension.py`:

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
    deleted_at: str | None = None            # NULL = active; ISO-8601 = soft-deleted
    created_by_user_id: UUIDv7 | None = None  # NULL = single-user/legacy write
    updated_by_user_id: UUIDv7 | None = None
```

Mirror `data-model.md` field lists exactly for `item` (§8), `inventory_event` (§11, LOG: `user_id`, `Money` fields, no update semantics), and the rest.

- [ ] Per entity: **failing test first** (construct with valid fields; assert each model-level invariant, e.g. non-v7 id rejected; Integer-typed value rejects a fraction; `ScaledValue.value_scaled` within int64). Implement. Add model validators only for **single-entity** invariants (cross-entity checks are service-layer). Group commits by domain package, one class per file.

> Volume note: this is mechanical transcription from `data-model.md` plus per-field nullability justification and a few model validators. The worked example is the pattern for all ~60 models.

---

## Task 12: Session / Unit of Work

**Files:** `src/thinghound/session.py`, `tests/test_session.py`.

The Session is the coordinator (`architecture.md §4.6`): connection, transaction scope, identity map. **It owns no table SQL and performs no row↔model conversion.** (When Track-2 mappers exist, the session exposes them and owns the transaction they run in — but the session itself never maps a row.)

- [ ] **Step 1: failing tests** — `with session.transaction():` commits on success and rolls back on exception (verified by row counts against a REF table); `get_identity`/`put_identity` round-trip an object in the identity map.
- [ ] **Step 2: run → fail. Step 3: implement** `Session(conn)`: `transaction()` context manager (`BEGIN`/`COMMIT`/`ROLLBACK`); a `dict[type, dict[uuid.UUID, object]]` identity map with `get_identity`/`put_identity`. No SQL constants, no `_*_from_row` — those belong to mappers.
- [ ] **Step 4: run → pass; commit** `feat: Session (unit of work: transaction + identity map)`.

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
