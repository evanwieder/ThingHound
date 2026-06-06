# Coding Standards Infrastructure — Design
# this file is superceded but may still be used as a reference.
**Date:** 2026-06-03  
**Status:** Approved  
**Trigger:** Phase 1 repository implementation surfaced missing SQL and repository architecture standards; existing CLAUDE.md mixed agent instructions with coding standards, and had no SQL, data-model, repository, or testing standards at all.

---

## Goal

Establish a comprehensive, maintainable coding standards infrastructure that serves both human developers and AI agents. Standards must be authoritative, discoverable, and context-efficient — agents load only what is relevant to their current task, not a monolithic file.

---

## File Structure

```
ThingHound/
  coding_standards.md                    ← root overview; principles + domain index
  CONTRIBUTING.md                        ← developer onboarding; references root + docs/dev/
  CLAUDE.md                              ← agent-only; task-routing rules + project invariants
                                           (all coding standards removed; reference to coding_standards.md)
  docs/dev/
    standards-python.md                  ← verbose human: Python style, types, docstrings, layout
    standards-sql.md                     ← verbose human: SQL quality rules
    standards-data-models.md             ← verbose human: Pydantic domain entities, invariants (strictest)
    standards-repository.md              ← verbose human: repository pattern, SQL ownership, transactions
    standards-testing.md                 ← verbose human: TDD, test structure, coverage
    standards-error-handling.md          ← verbose human: exception strategy, boundary validation
    agent/
      standards-python.md                ← compact agent: directive rules only
      standards-sql.md                   ← compact agent: directive rules only
      standards-data-models.md           ← compact agent: directive rules only
      standards-repository.md            ← compact agent: directive rules only
      standards-testing.md               ← compact agent: directive rules only
      standards-error-handling.md        ← compact agent: directive rules only
```

---

## File Roles and Content Contract

### `coding_standards.md` (root)

The entry point for any reader — human or agent — who needs orientation. Contains:

- The project's engineering philosophy in a few sentences (why these standards exist)
- The non-negotiable invariants that apply everywhere (no REAL, BLOB UUIDs, FK-off, integer money, etc.)
- A domain index: one paragraph per domain with a link to the verbose doc and the agent compact doc
- A note that `docs/dev/agent/` files are the agent-authoritative versions of each standard

This file is human-readable prose. It is **not** exhaustive — it points to the detail files.

### `docs/dev/standards-{domain}.md` (verbose human docs)

One file per domain. These are the **source of truth**. Each file contains:

- The rationale for every rule (the "why")
- Complete examples of correct and incorrect patterns
- Anti-patterns with explanations
- Edge cases and exceptions

These files are for human developers reading, writing, and reviewing code. They are authoritative — if a rule exists, it exists here first.

### `docs/dev/agent/standards-{domain}.md` (compact agent docs)

One file per domain, paired 1:1 with the verbose file. These contain:

- Directive rules only — no rationale, no prose, no examples
- Written for minimum token cost and maximum clarity to an AI agent
- Every rule is a direct command: "Always X", "Never Y", "Require Z"
- No rule appears here that does not exist in the corresponding verbose file
- Ordered by importance (highest-impact rules first)

These files are **distillations**, not independent documents. When a rule changes in the verbose file, the agent compact file must be updated in the same commit. A rule that only exists in one file is a maintenance error.

### `CLAUDE.md` (agent-only instructions)

Refactored to remove all coding standards content (which moves to `docs/dev/`). Retains only:

- **Project invariants** (the few rules too critical to load conditionally — no REAL, BLOB UUID, FK-off, integer money): stated directly, not by reference
- **Task-routing rules**: explicit instructions for which agent compact file to read before each category of work
- **Workflow rules**: branch/PR discipline, no unprompted coding, no unprompted push

Task-routing rules follow this pattern:

```
Before writing or reviewing any SQL:
  Read docs/dev/agent/standards-sql.md

Before writing or reviewing any data model (Pydantic):
  Read docs/dev/agent/standards-data-models.md

Before writing or reviewing any repository:
  Read docs/dev/agent/standards-repository.md
  Read docs/dev/agent/standards-sql.md

Before writing or reviewing any tests:
  Read docs/dev/agent/standards-testing.md

Before writing or reviewing any Python code:
  Read docs/dev/agent/standards-python.md
```

### `CONTRIBUTING.md`

Developer onboarding document. Contains:

- How to set up the development environment
- Branch and PR workflow (mirrors CLAUDE.md workflow rules)
- A "Standards" section that describes the standards infrastructure and links to `coding_standards.md` and each `docs/dev/standards-{domain}.md` file
- A note that `docs/dev/agent/` files exist for agent use and must be kept in sync with their verbose counterparts

---

## Domains and Scope

### Python (`standards-python.md`)
Everything currently in CLAUDE.md under "Python coding standards": type annotations, union syntax, docstring format (Google-style), one-class-per-file, frozen dataclasses/Pydantic models, no bare except. `from __future__ import annotations` is explicitly prohibited — Python 3.14 evaluates annotations lazily by default (PEP 649).

### SQL (`standards-sql.md`)
The gap that triggered this work. Key rules to codify:
- Never `SELECT *` — explicit column list required in every SELECT
- Every query string is a named class or module-level constant, not an inline literal
- Every SQL statement begins with a single-line comment identifying the operation and table
- Table aliases are required on every table reference, even single-table queries
- Formatting: keywords uppercase, one clause per line, consistent indentation
- Statements are parameterized — no string interpolation of values
- INSERT statements list columns explicitly

### Data Models (`standards-data-models.md`)
The strictest section. Evan is a principal data modeler — these rules reflect that weight:
- Pydantic `BaseModel` with `model_config = ConfigDict(frozen=True)` for all domain entities
- Every field typed precisely — no `str` for a field that is actually an enum, no `int` for a UUID
- Validation logic belongs in the model, not in callers
- Invariants that span multiple fields are enforced via `@model_validator`
- No optional field without explicit business justification in a docstring
- Nullable columns map to `X | None` fields; the distinction between "not provided" and "null" must be explicit
- Every entity model has a module docstring stating its invariants
- No raw primitive types at domain boundaries — wrap them (Money, UUIDv7, ScaledValue, etc.)

### Repository (`standards-repository.md`)
- Repository is a class, not a collection of functions
- All SQL strings are class-level or module-level named constants — never constructed inline inside a method
- Row-to-model mapping is a private class method, not a module-level function
- Repository methods do not call `commit()` — transaction management is the caller's responsibility
- Every public method accepts and returns domain models (Pydantic), never raw tuples or dicts
- Batch write methods must be supported alongside single-row methods
- Repository owns all SQL for its domain — no SQL leaks into service or test code

### Testing (`standards-testing.md`)
- TDD: tests written before implementation
- Integration tests hit a real in-memory SQLite database — no mocking of the database layer
- Each test has a single assertion focus (one behavior per test)
- Test names describe behavior, not implementation: `test_deleted_dimension_excluded_from_list`, not `test_list_dimensions`
- Fixtures provide a migrated connection; tests do not run migrations themselves
- No shared mutable state between tests

### Error Handling (`standards-error-handling.md`)
- No bare `except:` or `except Exception:` — catch specific exceptions
- Validation at system boundaries only (user input, external APIs, JS bridge) — trust internal code
- Domain errors are typed exceptions, not generic `ValueError` strings
- Errors propagate; they are not swallowed with a log line

---

## Maintenance Discipline

The dual-file pattern (verbose + agent compact per domain) is maintained by one rule: **the verbose file is the source of truth; the agent compact file is a derived artifact**. They must be updated in the same commit. The CI guard (already in place for CRR rules) will be extended in a later task to verify that every file in `docs/dev/agent/` has a corresponding file in `docs/dev/` with a matching domain name.

---

## What This Does Not Cover

- The content of each standards file — that is the implementation work
- Migrating existing CLAUDE.md content — covered in the implementation plan
- Rewriting `repository.py` to conform to the new standards — a separate task after standards are in place

---

## Success Criteria

1. `coding_standards.md` exists at the repo root and a new developer can find every standard from it
2. `CONTRIBUTING.md` exists and links to the standards infrastructure
3. `CLAUDE.md` contains no coding standards content; it contains task-routing rules pointing to `docs/dev/agent/`
4. All six verbose standards files exist in `docs/dev/` with complete content
5. All six agent compact files exist in `docs/dev/agent/` with directive-only content
6. Every rule in every agent compact file exists in the corresponding verbose file
7. The existing CLAUDE.md Python standards content is fully migrated (no duplication)
