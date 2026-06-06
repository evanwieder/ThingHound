# ThingHound — Coding Standards

**Date:** 2026-06-04

These standards apply to every contributor and every AI agent working in this repository. They are mandatory, not advisory.

---

## Engineering Philosophy

Code in this repository is built to last. The domain model is complex and the data must remain exact forever. Every standard below exists to protect one or more of: **correctness**, **maintainability**, and **encapsulation**. When a rule seems inconvenient, that friction is protecting you from a class of bugs or a future rewrite.

---

## Non-Negotiable Invariants

These rules apply everywhere, always. They are stated here so no agent or developer need load additional context to know them.

| Rule | Reason |
|------|--------|
| **No floating-point anywhere** | Floats cannot represent exact values. Domain values are `Decimal`; money is `Money`. Physical encoding is DBMS-specific (see `thinghound-architecture.md` §9) but is never a float. |
| **PK strategy: integer `id` for structure/master-data, `UUIDv7` `uuid` for operational/transactional** | Integer PKs for registry-loaded structure and stable master data; UUIDv7 for high-volume transactional rows. FK column names follow the referenced PK's type (`_id` for integer FK, `_uuid` for uuid FK). `UUIDv7` (from `thinghound.types`) validates version 7. Canonical `8-4-4-4-12` string only at the bridge boundary. |
| **FK enforcement ON** | Real foreign keys in DDL. Referential integrity is not application-only. |
| **No column name may end with a preposition** | Use `created_ts`, `updated_ts`, `deleted_ts`, `created_user_id`, `updated_user_id` — never `created_at`, `updated_at`, `created_by`, etc. |
| **SQL is built by the query component** | Callers express intent only; the query component decides construction and strategy per use case. No hand-written named SQL constants. No SQL in service, domain, UI, or test code. |
| **All SQL is parameterized** | Every value is a bound parameter. Identifiers come only from metadata. No string interpolation into SQL text. |
| **Scale per `attribute_definition`** | Not per `unit_dimension`. Two attributes in the same dimension may have different scales for different practical ranges. Physical encoding of scale is DBMS-specific. |
| **Logical model is DBMS-agnostic** | The data model spec uses logical types (UUID, Decimal, Money, etc.). Physical encoding belongs in mappers. See `thinghound-architecture.md` §9 for the type mapping. |

---

## Standards by Domain

Each domain has a verbose human-readable document and a compact agent-directed document.

### Python Style
- **Human:** `docs/dev/standards-python.md`
- **Agent:** `docs/dev/agent/standards-python.md`

Type annotations, union syntax, docstring format (Google-style), one-class-per-file rule, frozen models, exception handling, import conventions. `from __future__ import annotations` is prohibited — Python 3.14 evaluates annotations lazily by default (PEP 649).

### SQL
- **Human:** `docs/dev/standards-sql.md`
- **Agent:** `docs/dev/agent/standards-sql.md`

Global: column-explicit SELECT; fully explicit join syntax (`INNER JOIN`, `LEFT OUTER JOIN`, `RIGHT OUTER JOIN`, `FULL OUTER JOIN` — never abbreviated); `ON` clauses on their own lines; `AS` aliases on every table; CTEs permitted; query component builds all SQL; traceability comments; formatting; parameterization; explicit INSERT column lists; batch forms; transaction discipline. SQLite-specific: `WITHOUT ROWID` for uuid-PK tables only; `?` placeholder syntax; temporal columns as `INTEGER` epoch values.

### Data Models
- **Human:** `docs/dev/standards-data-models.md`
- **Agent:** `docs/dev/agent/standards-data-models.md`

Pydantic frozen models, precise field types, model-level validation, domain primitives (`UUIDv7`, `Money`, `Decimal`), integer/uuid PK split and naming, relationships on models, Audit object pattern, no-trailing-preposition naming rule.

### Repository / Aggregate Mapper
- **Human:** `docs/dev/standards-repository.md`
- **Agent:** `docs/dev/agent/standards-repository.md`

Aggregate mapper pattern, SQL ownership via the query component, row-to-model mapping as class methods, transaction discipline, batch-first collections.

### Testing
- **Human:** `docs/dev/standards-testing.md`
- **Agent:** `docs/dev/agent/standards-testing.md`

TDD, real database in integration tests (no mocking), behavior-named tests, fixture discipline, migration coverage.

### Error Handling
- **Human:** `docs/dev/standards-error-handling.md`
- **Agent:** `docs/dev/agent/standards-error-handling.md`

Specific exception types, boundary validation, typed domain errors, no swallowing.

---

## Maintenance Rule

The verbose `docs/dev/standards-*.md` files are the source of truth. The compact `docs/dev/agent/standards-*.md` files are distillations — every rule in an agent file must exist in the corresponding verbose file. When a standard changes, both files are updated in the same commit. A rule that exists in only one file is a maintenance error.
