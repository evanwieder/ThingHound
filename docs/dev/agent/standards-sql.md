# SQL Standards — Agent Reference

Every rule here exists in `docs/dev/standards-sql.md`. Update both files in the same commit when a rule changes.

Standards are split: **Global** rules apply to all DBMS targets. **SQLite-Specific** rules apply only to the current libSQL/SQLite backend and do not apply when writing a Postgres or other DBMS mapper.

---

## Global (all DBMS targets)

1. Table names are named for what a single row represents — almost always singular (`item`, `inventory_event`, `item_category`). Plural only when each row itself represents a collection, which is rare. Index name tokens follow the same rule. Applies to all table identifiers in migrations, SQL, mappers, specs, and docs.
2. SQL is built by the model-aware query component from mapper metadata. Never write SQL in services, domain objects, tests, or free functions. No hand-written named SQL constants.
3. Callers express query intent only (entity, projection, predicate, ordering); the component decides how the SQL is assembled, per use case.
4. Never `SELECT *`. Always list every column explicitly with its alias prefix.
5. Always use fully explicit join syntax: `INNER JOIN`, `LEFT OUTER JOIN`, `RIGHT OUTER JOIN`, `FULL OUTER JOIN`, `CROSS JOIN`. Never `JOIN`, `LEFT JOIN`, `RIGHT JOIN`, or `FULL JOIN`. No abbreviated join types, ever.
6. Each `ON` condition is on its own line, indented under its `JOIN`. Multiple conditions use `AND` at the start of each continuation line.
7. Every table reference carries an alias declared with `AS`. All column references qualify with the alias, even on single-table queries.
8. CTEs (`WITH` clauses) are permitted. Recursive CTEs are the standard for tree traversal (category and location hierarchies).
9. Emitted SQL begins with a single-line traceability comment: `-- table_name: description of operation`.
10. Keywords uppercase. Each major clause on its own line. Column lists and conditions indented 4 spaces. Continuation `AND`/`OR` indented to align with first condition.
11. Every value is a bound parameter. Never interpolate values into SQL text. Identifiers come only from metadata. Dynamic WHERE assembly accumulates fragments and parameters separately.
12. Every INSERT lists target columns explicitly. Never `INSERT INTO table VALUES (...)` without a column list.
13. Every write operation has a single-row form and a batch (`executemany`) form built from the same definition.
14. Mappers never call `commit()` or `rollback()`. Transaction scope belongs to the session.

---

## SQLite-Specific (does not apply to Postgres or other DBMS mappers)

15. PKs: structure/master-data tables use DB-generated `INTEGER PRIMARY KEY` (rowid table, column `id`); operational/transactional tables use a `UUID` PK as `BLOB(16)` (column `uuid`). FK columns end in `_id` or `_uuid` to match the referenced PK type.
16. Tables with a non-integer (uuid) primary key are declared `WITHOUT ROWID`. Integer-`id` tables are normal rowid tables. `AUTOINCREMENT`/sequences permitted on integer keys.
17. Foreign keys are enforced (`PRAGMA foreign_keys = ON`); DDL uses real `REFERENCES`.
18. `CHECK` constraints — single-column and cross-column — are both permitted. No `REAL` columns (no-float rule).
19. `Timestamp` / `Date` columns are `INTEGER` epoch (epoch ms, UTC), never `TEXT`; the mapper encodes ISO-8601 ↔ epoch at the storage boundary. `HLC` stays `TEXT`.
20. No column name ends with a preposition (`created_ts`, not `created_at`).
21. SQLite parameter placeholder is `?`. Postgres drivers use `%s` (psycopg2) or `$1` (psycopg3).
