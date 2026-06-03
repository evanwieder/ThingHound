# ThingHound — Coding Standards

**Date:** 2026-06-03

These standards apply to every contributor and every AI agent working in this repository. They are mandatory, not advisory.

---

## Engineering Philosophy

Code in this repository is built to last. The domain model is complex, the sync substrate is unforgiving, and the data must remain exact forever. Every standard below exists to protect one or more of: **correctness**, **maintainability**, and **encapsulation**. When a rule seems inconvenient, that friction is protecting you from a class of bugs or a future rewrite.

---

## Non-Negotiable Invariants

These rules apply everywhere, always. They are stated here so no agent or developer need load additional context to know them.

| Rule | Reason |
|------|--------|
| **No floating-point anywhere** | Floats cannot represent exact values and lose precision in JSON serialization during sync. Domain values are `Decimal`; money is `Money`. Physical encoding is DBMS-specific (see `thinghound-architecture.md` §9) but is never a float. |
| **`UUIDv7` for all ID fields in domain models** | `UUIDv7` (from `thinghound.types`) is `Annotated[uuid.UUID, ...]` validating version 7. Never `bytes`, `str`, or plain `uuid.UUID` in domain models. Canonical `8-4-4-4-12` string only at the bridge boundary. |
| **`foreign_keys = OFF` on every SQLite connection** | cr-sqlite applies column-level changesets independently; FK enforcement rejects valid remote writes. Referential integrity is application-enforced. |
| **All SQL lives in aggregate mappers** | No SQL in service, domain, UI, or test code. The mapper is the only place that knows both the physical schema and the domain model. |
| **All SQL is parameterized** | Every value is a bound parameter. No string interpolation of user data or computed values into SQL text. |
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

Column-explicit SELECT, named SQL constants, query formatting, table aliases, leading traceability comments, parameterization, INSERT column lists, batch forms, transaction discipline, and SQLite physical model constraints for CRR/LOG tables.

### Data Models
- **Human:** `docs/dev/standards-data-models.md`
- **Agent:** `docs/dev/agent/standards-data-models.md`

Pydantic frozen models, precise field types, model-level validation, domain primitives (`UUIDv7`, `Money`, `Decimal`), CRR/LOG/LOCAL behavioral classification.

### Repository / Aggregate Mapper
- **Human:** `docs/dev/standards-repository.md`
- **Agent:** `docs/dev/agent/standards-repository.md`

Aggregate mapper pattern, SQL ownership, row-to-model mapping as class methods, transaction discipline, single-writer-per-table invariant, batch-first collections.

### Testing
- **Human:** `docs/dev/standards-testing.md`
- **Agent:** `docs/dev/agent/standards-testing.md`

TDD, real database in integration tests (no mocking), behavior-named tests, fixture discipline, migration coverage, sync scenario tests.

### Error Handling
- **Human:** `docs/dev/standards-error-handling.md`
- **Agent:** `docs/dev/agent/standards-error-handling.md`

Specific exception types, boundary validation, typed domain errors, no swallowing.

---

## Maintenance Rule

The verbose `docs/dev/standards-*.md` files are the source of truth. The compact `docs/dev/agent/standards-*.md` files are distillations — every rule in an agent file must exist in the corresponding verbose file. When a standard changes, both files are updated in the same commit. A rule that exists in only one file is a maintenance error.
