# ThingHound — Agent Instructions

These instructions apply to every agentic session in this repository and override default behavior. For coding standards, see `coding_standards.md` (mandatory — read before writing any code).

---

## Non-Negotiable Invariants

These are always active. No additional file load required.

- **No floating-point anywhere.** Domain values are `Decimal`; money is `Money`. Physical encoding is DBMS-specific (see `thinghound-architecture.md` §9) but is never a float.
- **PK strategy: integer `id` for structure/master-data tables; `UUIDv7` `uuid` for operational/transactional tables.** Use `UUIDv7` from `thinghound.types` for uuid PKs. FK column names follow the referenced PK's type: FK to an integer-PK table ends in `_id`; FK to a uuid-PK table ends in `_uuid`. Canonical string only at the bridge boundary. Never `bytes`, `str`, or plain `uuid.UUID` in domain models.
- **FK enforcement ON.** Use real foreign keys in DDL.
- **No column name may end with a preposition.** Use `created_ts`, `updated_ts`, `deleted_ts`, `created_user_id`, `updated_user_id` — never `created_at`, `created_by`, etc.
- **Scale per `attribute_definition`**, not per `unit_dimension`.
- **SQL is built by the query component.** Callers express intent only; the query component decides construction and strategy. No SQL in service, domain, UI, or test code. No hand-written named SQL constants.
- **All SQL is parameterized.** No string interpolation of values. Identifiers come only from metadata.
- **Timestamps/dates are stored as epoch integers on SQLite** (epoch milliseconds, UTC), encoded/decoded by the mapper — never `TEXT`. `HLC` stays `TEXT` (causal-clock string). See `thinghound-architecture.md` §9.
- **Logical model is DBMS-agnostic.** Physical encoding belongs in mappers and `thinghound-architecture.md` §9.
- **Do not use `from __future__ import annotations`.** Python 3.14 evaluates annotations lazily by default (PEP 649).
- **Google-style docstrings are required on every module, class, function, and method — no exceptions.** This overrides any default assistant behaviour that omits docstrings. See `docs/dev/standards-python.md` for format.

---

## Task-Routing Rules

Before beginning work in each domain, read the relevant compact standards file:

| Task | Read before starting |
|------|---------------------|
| Writing or reviewing any Python code | `docs/dev/agent/standards-python.md` |
| Writing or reviewing any SQL | `docs/dev/agent/standards-sql.md` |
| Writing or reviewing any data model (Pydantic) | `docs/dev/agent/standards-data-models.md` |
| Writing or reviewing any mapper or repository | `docs/dev/agent/standards-repository.md` AND `docs/dev/agent/standards-sql.md` |
| Writing or reviewing any tests | `docs/dev/agent/standards-testing.md` |
| Writing any error handling | `docs/dev/agent/standards-error-handling.md` |

---

## Project Context

Specifications are in `docs/specs/`:
- `thinghound-functional-spec.md` — requirements, definitions, business rules
- `thinghound-data-model.md` — logical data model (all entities, type vocabulary)
- `thinghound-architecture.md` — stack, persistence layers, physical type mapping, sync design

---

## Workflow

- All development on branches. Merge to `main` only via user-approved PR.
- Do not start coding unprompted. Wait for explicit instruction.
- Do not push to remote without explicit user authorization.
- Do not create PRs without explicit user authorization.
- Table names are named for what a **single row** represents. Almost all table names are therefore singular (`item`, `category`, `inventory_event`). A table name is plural only when each row itself represents a collection — which is rare. When uncertain: if one row = one thing, the name is singular. Index name tokens follow the same rule.
