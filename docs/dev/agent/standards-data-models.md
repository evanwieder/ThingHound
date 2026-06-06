# Data Model Standards — Agent Reference

Every rule here exists in `docs/dev/standards-data-models.md`. Update both files in the same commit when a rule changes.

---

1. Domain entities: `pydantic.BaseModel` with `model_config = ConfigDict(frozen=True)`.
2. Every field typed to its exact semantic meaning. Never use a generic primitive where a domain type exists.
3. PK by table role: structure/master-data → integer `id: int`; operational/transactional → `uuid: UUIDv7` (from `thinghound.types`); reference/code → `code: str`. FK fields end in `_id` (→ integer PK) or `_uuid` (→ uuid PK). No field name ends with a preposition (`created_ts`, not `created_at`). For uuid keys never use `bytes`, `str`, or plain `uuid.UUID`; the mapper converts `uuid.bytes` for writes, `uuid.UUID(bytes=row["uuid"])` on reads, `str(uuid)` at the bridge.
4. Generate uuids with `uuid.uuid7()` (Python 3.14 stdlib). Pydantic validates as `UUIDv7` at construction.
5. No floating-point anywhere. Dimensional values are `Decimal`; money is `Money`. Physical encoding is the mapper's responsibility.
5a. `Decimal` SQLite encoding by role (architecture §9): attribute values → dual-column at `attribute.scale`; quantities (`qty_*`/`moq`/`order_multiple`/`reorder_*`/`safety_stock`) → dual-column at fixed quantity scale 6; factors/rates (`unit_multiplier.factor`, `prefix.factor`, `fx_rate.rate`) → single `*_exact TEXT`, no `*_scaled`.
6. `scale` is a property of `attribute`, not `unit_dimension`. Never read scale from a dimension.
7. Never add tolerance fields (`tol_low_scaled`, `tol_high_scaled`, etc.) to value rows. Tolerance is a separate attribute.
8. Validation logic belongs in the model via `@field_validator` / `@model_validator`. Never duplicate validation in callers.
9. Every nullable field (`X | None`) requires justification in a docstring.
10. Never pass raw primitives at domain boundaries. Use `UUIDv7`, `Money`, `Decimal` wrappers.
10a. Timestamps/dates: model carries an ISO-8601 string; the mapper encodes to an `INTEGER` epoch (epoch ms, UTC) for SQLite and decodes back — never stored as `TEXT`. `HLC` is a causal-clock string (text), not an epoch integer.
11. Audit is per-table, not a central log. Entities carry `created_user_uuid` + `updated_user_uuid`; append-only event entities carry `user_uuid`. Audit fields are excluded from domain models by default (surfaced via a separate `Audit` object); code tables carry no attribution.
12. Append-only event entities are insert-only. No `update()` method on their mappers.
13. Physical SQLite rules (FK on, integer/uuid PK split, `WITHOUT ROWID` for uuid PKs, no `REAL`, temporal epoch ints) are in `thinghound-architecture.md` §9 and `docs/dev/standards-sql.md`. They are not logical model concerns.
14. Never use native enum types (Pydantic `Literal[...]`, Python `Enum`, or database ENUM). All domain-constrained string values use the code table pattern: `*_code: String` referencing a REF entity. Valid codes are in data model spec §3.
15. Do not hardcode code values as `Literal[...]` in domain models. Validate `*_code` fields against the loaded code table, not a fixed literal set — code tables are extensible.
16. Every `attribute` belongs to exactly one `attribute_domain`. Same name in different domains = different attribute.
17. One class per file.
