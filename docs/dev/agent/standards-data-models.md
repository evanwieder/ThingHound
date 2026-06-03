# Data Model Standards — Agent Reference

Every rule here exists in `docs/dev/standards-data-models.md`. Update both files in the same commit when a rule changes.

---

1. Domain entities: `pydantic.BaseModel` with `model_config = ConfigDict(frozen=True)`.
2. Every field typed to its exact semantic meaning. Never use a generic primitive where a domain type exists.
3. `id` fields are `UUIDv7` (from `thinghound.types`). Never `bytes`, `str`, or plain `uuid.UUID` in a domain model. Mapper converts: `id.bytes` for storage writes; `uuid.UUID(bytes=row["id"])` passed to model constructor on reads; `str(id)` at the bridge boundary.
4. Generate IDs with `uuid.uuid7()` (Python 3.14 stdlib). Pydantic validates as `UUIDv7` at construction.
5. No `REAL` anywhere. Dimensional values: `value_scaled: int` + `value_exact: str`. Money: `amount_minor: int` + `currency: str`.
6. `scale` is a property of `attribute_definition`, not `unit_dimension`. Never read scale from a dimension.
7. Never add tolerance fields (`tol_low_scaled`, `tol_high_scaled`, etc.) to value rows. Tolerance is a separate attribute definition.
8. Validation logic belongs in the model via `@field_validator` / `@model_validator`. Never duplicate validation in callers.
9. Every nullable field (`X | None`) requires justification in a docstring.
10. Never pass raw primitives at domain boundaries. Use `UUIDv7`, `Money`, `ScaledValue` wrappers.
11. CRR entities carry `created_by_user_id: UUID` and `updated_by_user_id: UUID`. LOG entities carry `user_id: UUID`. These are domain attribution fields, not physical constraints.
12. LOG entities are insert-only. No `update()` method on LOG mappers.
13. Physical SQLite constraints for CRR/LOG tables (DEFAULT on NOT NULL, no cross-column CHECK) are in `thinghound-architecture.md` §9 and `docs/dev/standards-sql.md`. They are not logical model concerns.
14. Every `attribute_definition` belongs to exactly one `attribute_category`. Same name in different categories = different attribute.
15. One class per file.
