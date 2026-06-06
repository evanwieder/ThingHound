# SQL Standards — Agent Reference

Every rule here exists in `docs/dev/standards-sql.md`. Update both files in the same commit when a rule changes.

Standards are split: **Global** rules apply to all DBMS targets. **SQLite-Specific** rules apply only to the current SQLite + cr-sqlite backend and do not apply when writing a Postgres or other DBMS mapper. CRR/LOG are SQLite/cr-sqlite constructs.

---

## Global (all DBMS targets)

1. Table names are named for what a single row represents — almost always singular (`item`, `inventory_event`, `item_category`). Plural only when each row itself represents a collection, which is rare. Index name tokens follow the same rule. Applies to all table identifiers in migrations, SQL, mappers, specs, and docs.
2. All SQL lives in aggregate mappers. Never write SQL in services, domain objects, tests, or free functions.
3. Every SQL statement is a named class-level constant. Never construct SQL inline. The constant is defined once, compiled/cached by the driver, and reused on every call. For high-frequency queries on drivers that support it (e.g., psycopg3), prepare explicitly at mapper initialization.
4. Never `SELECT *`. Always list every column explicitly with its alias prefix.
5. Always use fully explicit join syntax: `INNER JOIN`, `LEFT OUTER JOIN`, `RIGHT OUTER JOIN`, `FULL OUTER JOIN`, `CROSS JOIN`. Never `JOIN`, `LEFT JOIN`, `RIGHT JOIN`, or `FULL JOIN`. No abbreviated join types, ever.
6. Each `ON` condition is on its own line, indented under its `JOIN`. Multiple conditions use `AND` at the start of each continuation line.
7. Every table reference carries an alias declared with `AS`. All column references qualify with the alias, even on single-table queries.
8. CTEs (`WITH` clauses) are permitted. Recursive CTEs are the standard for tree traversal (category and location hierarchies).
9. Every SQL constant begins with a single-line traceability comment: `-- table_name: description of operation`.
10. Keywords uppercase. Each major clause on its own line. Column lists and conditions indented 4 spaces. Continuation `AND`/`OR` indented to align with first condition.
11. Every value is a bound parameter. Never use f-strings, `%`, or `.format()` on SQL text. Dynamic WHERE assembly accumulates fragments and parameters separately.
12. Every INSERT lists target columns explicitly. Never `INSERT INTO table VALUES (...)` without a column list.
13. Every write operation has a single-row form and a batch (`executemany`) form using the same constant.
14. Mappers never call `commit()` or `rollback()`. Transaction scope belongs to the session.

---

## SQLite-Specific (does not apply to Postgres or other DBMS mappers)

15. CRR/LOG tables: every non-PK `NOT NULL` column must have a `DEFAULT` value (cr-sqlite rejects tables without defaults).
16. CRR/LOG tables: no cross-column `CHECK` constraints. Enforce cross-column invariants at the service layer.
17. CRR/LOG tables: no `AUTOINCREMENT`, no `REAL` columns.
17a. SQLite tables with a non-integer primary key must be declared `WITHOUT ROWID`.
17b. `Timestamp` / `Date` columns are `INTEGER` epoch (epoch ms, UTC), never `TEXT`; the mapper encodes ISO-8601 ↔ epoch at the storage boundary. `HLC` stays `TEXT`.
18. CRR/LOG schema changes use `crsql_begin_alter` / `crsql_commit_alter`.
19. SQLite parameter placeholder is `?`. Postgres drivers use `%s` (psycopg2) or `$1` (psycopg3).
