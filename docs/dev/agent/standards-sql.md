# SQL Standards — Agent Reference

Every rule here exists in `docs/dev/standards-sql.md`. Update both files in the same commit when a rule changes.

Standards are split: **Global** rules apply to all DBMS targets. **SQLite-Specific** rules apply only to the current SQLite + cr-sqlite backend and do not apply when writing a Postgres or other DBMS mapper. CRR/LOG are SQLite/cr-sqlite constructs.

---

## Global (all DBMS targets)

1. All SQL lives in aggregate mappers. Never write SQL in services, domain objects, tests, or free functions.
2. Every SQL statement is a named class-level constant. Never construct SQL inline. The constant is defined once, compiled/cached by the driver, and reused on every call. For high-frequency queries on drivers that support it (e.g., psycopg3), prepare explicitly at mapper initialization.
3. Never `SELECT *`. Always list every column explicitly with its alias prefix.
4. Always use fully explicit join syntax: `INNER JOIN`, `LEFT OUTER JOIN`, `RIGHT OUTER JOIN`, `FULL OUTER JOIN`, `CROSS JOIN`. Never `JOIN`, `LEFT JOIN`, `RIGHT JOIN`, or `FULL JOIN`. No abbreviated join types, ever.
5. Each `ON` condition is on its own line, indented under its `JOIN`. Multiple conditions use `AND` at the start of each continuation line.
6. Every table reference carries an alias declared with `AS`. All column references qualify with the alias, even on single-table queries.
7. CTEs (`WITH` clauses) are permitted. Recursive CTEs are the standard for tree traversal (category and location hierarchies).
8. Every SQL constant begins with a single-line traceability comment: `-- table_name: description of operation`.
9. Keywords uppercase. Each major clause on its own line. Column lists and conditions indented 4 spaces. Continuation `AND`/`OR` indented to align with first condition.
10. Every value is a bound parameter. Never use f-strings, `%`, or `.format()` on SQL text. Dynamic WHERE assembly accumulates fragments and parameters separately.
11. Every INSERT lists target columns explicitly. Never `INSERT INTO table VALUES (...)` without a column list.
12. Every write operation has a single-row form and a batch (`executemany`) form using the same constant.
13. Mappers never call `commit()` or `rollback()`. Transaction scope belongs to the session.

---

## SQLite-Specific (does not apply to Postgres or other DBMS mappers)

14. CRR/LOG tables: every non-PK `NOT NULL` column must have a `DEFAULT` value (cr-sqlite rejects tables without defaults).
15. CRR/LOG tables: no cross-column `CHECK` constraints. Enforce cross-column invariants at the service layer.
16. CRR/LOG tables: no `AUTOINCREMENT`, no `REAL` columns.
17. CRR/LOG schema changes use `crsql_begin_alter` / `crsql_commit_alter`.
18. SQLite parameter placeholder is `?`. Postgres drivers use `%s` (psycopg2) or `$1` (psycopg3).
