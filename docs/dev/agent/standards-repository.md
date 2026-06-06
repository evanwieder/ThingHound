# Repository / Mapper Standards — Agent Reference

Every rule here exists in `docs/dev/standards-repository.md`. Update both files in the same commit when a rule changes.

---

1. Use aggregate mappers, not generic repositories. A mapper owns a persistence aggregate (root + all owned rows), not just one table.
2. All SQL lives in the mapper as named class-level constants. Never inline SQL in a method body.
3. Row-to-model mapping is a private class method on the mapper, never a free module-level function. Single-entity mappers name converters `_from_row` / `_to_row`; compound mappers use `_<entity>_from_row` / `_<entity>_to_row` (e.g. `_definition_from_row`, `_enum_value_from_row`) to disambiguate the types they own.
4. Public methods accept and return domain model instances. Never raw tuples, dicts, or `sqlite3.Row`.
5. Never call `commit()` or `rollback()` inside a mapper. Transaction scope belongs to the session.
6. Every write operation has a single-row form and a batch (`executemany`) form. Batch is the primary path for collections.
7. Single-writer-per-table: each table is written by exactly one aggregate mapper. Two mappers never write the same table.
8. The physical schema is encapsulated in the mapper. No consumer references table names, column names, or SQL text.
9. Config/structure data (dimensions, attribute definitions, categories) is accessed through the AppRegistry, not by issuing SQL at runtime.
10. The AppRegistry is populated by mappers at startup and refreshed on structure changes.
