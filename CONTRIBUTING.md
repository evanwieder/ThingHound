# Contributing to ThingHound

## Development Environment

**Requirements:** Python 3.14, `uv` (recommended) or `pip`.

```bash
git clone https://github.com/evanwieder/ThingHound
cd ThingHound
uv sync           # installs all dependencies including dev
uv run pytest     # run the test suite
uv run ruff check # lint
```

The database is libSQL/Turso (embedded local replica). No loadable database extension binary is required for core development.

---

## Branch & PR Workflow

- All development happens on branches. Never commit directly to `main`.
- Branch naming: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, `refactor/<topic>`.
- Merge to `main` only via a reviewed and approved pull request.
- One logical change per PR. Keep PRs focused.
- Do not push to remote without explicit authorization from the repository owner.

---

## Coding Standards

All contributors — human and AI — must follow the standards defined in [`coding_standards.md`](coding_standards.md) at the repository root.

The standards are organized by domain:

| Domain | Human doc | Agent doc |
|--------|-----------|-----------|
| Python style | `docs/dev/standards-python.md` | `docs/dev/agent/standards-python.md` |
| SQL | `docs/dev/standards-sql.md` | `docs/dev/agent/standards-sql.md` |
| Data models | `docs/dev/standards-data-models.md` | `docs/dev/agent/standards-data-models.md` |
| Repository / Mapper | `docs/dev/standards-repository.md` | `docs/dev/agent/standards-repository.md` |
| Testing | `docs/dev/standards-testing.md` | `docs/dev/agent/standards-testing.md` |
| Error handling | `docs/dev/standards-error-handling.md` | `docs/dev/agent/standards-error-handling.md` |

The `docs/dev/agent/` files are compact distillations for AI agents. Every rule in an agent file exists in the corresponding human doc. When updating a standard, update both files in the same commit.

---

## Architecture

See `docs/specs/` for the full specification set:
- `thinghound-functional-spec.md` — requirements, definitions, UI/UX, business rules, API, roadmap
- `thinghound-data-model.md` — all tables, columns, indexes, migrations
- `thinghound-architecture.md` — stack, persistence layers, sync design, testing strategy

---

## CI

CI runs on every push: `ruff` linting and the `pytest` suite. Both must pass before a PR can merge.
