# SQL Standards — Agent Reference

Every rule here exists in `docs/dev/standards-sql.md`. Update both files in the same commit when a rule changes.

---

1. All SQL lives in aggregate mappers. Never write SQL in services, domain objects, tests, or free functions.
2. Every SQL statement is a named class-level constant. Never construct SQL inline inside a method.
3. Never `SELECT *`. Always list every column explicitly.
4. Every table reference carries an alias, even on single-table queries.
5. Every SQL constant begins with a single-line traceability comment: `-- table_name: description of operation`.
6. Keywords uppercase. Each major clause on its own line. 4-space indentation inside the string.
7. Every value is a bound parameter (`?`). Never use f-strings, `%`, or `.format()` on SQL text.
8. Every INSERT lists target columns explicitly. Never `INSERT INTO table VALUES (...)` without a column list.
9. Every write operation has both a single-row form and a batch (`executemany`) form using the same SQL constant.
10. Mappers never call `commit()` or `rollback()`. Transaction scope belongs to the session.
11. SQLite CRR/LOG DDL: every non-PK `NOT NULL` column must have a `DEFAULT` value (cr-sqlite rejects tables without defaults).
12. SQLite CRR/LOG DDL: no cross-column `CHECK` constraints. Enforce cross-column invariants at the application layer.
13. SQLite CRR/LOG DDL: no `AUTOINCREMENT`, no `REAL` columns.
14. SQLite CRR/LOG schema changes use `crsql_begin_alter` / `crsql_commit_alter`.
