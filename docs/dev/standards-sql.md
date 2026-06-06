# SQL Coding Standards

**Compact agent version:** `docs/dev/agent/standards-sql.md`

SQL in ThingHound is built by the model-aware query component from mapper-provided metadata; callers express intent only. No SQL is hand-written in service, domain, or UI code, and there are no hand-written named SQL constants. Standards are divided into two sections: **Global** (apply regardless of the target DBMS) and **SQLite-Specific** (apply only to the current libSQL/SQLite backend). When a future Postgres mapper is written, global standards apply; SQLite-specific standards do not.

---

# Global SQL Standards

These rules apply to every SQL statement written for any DBMS target.

---

## Table Naming

Table names are named for what **a single row** represents.

- A row in `item` represents one item → `item` (singular).
- A row in `inventory_event` represents one event → `inventory_event` (singular).
- A row in `item_category` represents one item-category membership → `item_category` (singular).

Almost all table names are therefore singular. A table name is plural only when each row itself represents a **collection** of objects — for example, a table where each row stores an aggregated set or a bundle as its primary content. This is rare. When uncertain: if one row = one thing, the name is singular.

Index name tokens follow the same rule: `idx_item_deleted_ts`, never `idx_items_deleted_ts`.

This convention applies to all table identifiers in migrations, SQL, mappers, specs, and documentation. English prose and column names are exempt; only table identifiers are governed by this rule.

---

## Where SQL Lives

No SQL string appears in service classes, domain objects, collections, tests, or any other location. SQL is built by the **model-aware query component** from the mapper's column and relationship metadata. The mapper is the only place that knows both the physical schema and the domain model; consumers see only domain models and express query *intent* — never SQL.

---

## SQL Is Built, Not Hand-Written

There are no hand-written named SQL constants. The caller declares what it needs (entity, projection, predicate, ordering) and the query component assembles the statement, choosing construction and strategy per use case. Joins derive from the model's declared relationships. Two rules are absolute regardless of how a statement is assembled:

- **Every value is a bound parameter.** Never interpolate a value into SQL text.
- **Identifiers come only from metadata.** Table and column names originate from the mapper's metadata, never from caller input.

The rules in the rest of this document describe the **shape of the SQL the component emits** (and the shape any SQL reviewed in tests or logs must have). The snippets below are illustrations of that emitted shape, not literal constants to author by hand.

---

## Never `SELECT *`

Every SELECT statement lists columns explicitly. `SELECT *` is prohibited.

`SELECT *` returns columns in schema-defined order and silently breaks if columns are added, reordered, or renamed. Explicit column lists make the contract visible and keep the mapper in control of exactly what it receives.

```sql
-- Correct
SELECT
    ud.id,
    ud.name,
    ud.base_unit,
    ud.deleted_ts
FROM unit_dimension AS ud
WHERE ud.id = ?

-- Wrong
SELECT * FROM unit_dimension WHERE id = ?
```

---

## Join Types — Always Fully Explicit

Every join uses its full keyword. No abbreviated forms are acceptable for any join type.

| Correct | Wrong |
|---------|-------|
| `INNER JOIN` | `JOIN` |
| `LEFT OUTER JOIN` | `LEFT JOIN` |
| `RIGHT OUTER JOIN` | `RIGHT JOIN` |
| `FULL OUTER JOIN` | `FULL JOIN` |
| `CROSS JOIN` | — |

Full syntax communicates intent unambiguously. Abbreviated forms are not permitted even when they are technically equivalent — consistency is the rule.

```sql
-- Correct
SELECT
    iav.item_uuid,
    iav.attribute_id,
    iav.value,
    ad.name AS attribute_name
FROM item_attribute_value AS iav
INNER JOIN attribute AS ad
    ON ad.id = iav.attribute_id
LEFT OUTER JOIN unit_dimension AS ud
    ON ud.id = ad.unit_dimension_id
WHERE iav.item_uuid = ?

-- Wrong — abbreviated join types
FROM item_attribute_value iav
JOIN attribute ad ON ad.id = iav.attribute_id
LEFT JOIN unit_dimension ud ON ud.id = ad.unit_dimension_id
```

---

## ON Clauses — One Per Line, Indented

Each `ON` condition appears on its own line, indented under its `JOIN`. When a join has multiple conditions, each condition is on its own line with `AND` at the start.

```sql
-- Correct
FROM item AS i
INNER JOIN item_attribute_value AS iav
    ON iav.item_uuid = i.uuid
INNER JOIN attribute AS ad
    ON ad.id = iav.attribute_id
   AND ad.deleted_ts IS NULL

-- Wrong — ON clause on same line as JOIN
FROM item i
INNER JOIN item_attribute_value iav ON iav.item_uuid = i.uuid
```

---

## Table Aliases — Required on Every Reference

Every table reference in a query carries an alias using `AS`, even on single-table queries. All column references qualify with the alias. Aliases are short, consistent, and stable across the codebase.

```sql
-- Correct — alias on single table
SELECT
    ud.id,
    ud.name
FROM unit_dimension AS ud
WHERE ud.deleted_ts IS NULL

-- Wrong — no alias, no qualification
SELECT id, name FROM unit_dimension WHERE deleted_ts IS NULL
```

Establish a consistent alias vocabulary: `ud` = `unit_dimension`, `iav` = `item_attribute_value`, `ad` = `attribute`, `i` = `item`, `ic` = `item_category`, `ie` = `inventory_event`, etc.

---

## Common Table Expressions (CTEs)

CTEs (`WITH` clauses) are permitted and encouraged for complex queries where they improve clarity. Recursive CTEs are the standard mechanism for tree traversal (category hierarchy, location hierarchy) — no closure tables.

```sql
-- Correct — recursive CTE for category ancestry
WITH RECURSIVE ancestors(id, depth) AS (
    SELECT c.id, 0
    FROM category AS c
    WHERE c.id = ?
    UNION ALL
    SELECT c.id, a.depth + 1
    FROM category AS c
    INNER JOIN ancestors AS a
        ON c.id = a.parent_id
)
SELECT a.id
FROM ancestors AS a
```

---

## Leading Traceability Comment

Every emitted statement begins with a single-line comment naming the primary table and describing the operation.

```sql
-- unit_dimension: fetch by primary key
SELECT ud.id, ud.name ...

-- unit_dimension: list non-deleted, ordered by name
SELECT ud.id, ud.name ...

-- unit_dimension: insert new row
INSERT INTO unit_dimension (id, name, ...) VALUES (?, ?, ...)
```

---

## Formatting

SQL keywords are uppercase. Each major clause (`SELECT`, `FROM`, `INNER JOIN`, `WHERE`, `ORDER BY`, `GROUP BY`, `HAVING`, `LIMIT`) starts on its own line. Column lists and conditions are indented 4 spaces from the clause keyword. Continuation conditions (`AND`, `OR`) are indented to align with the first condition.

```sql
-- Correct
SELECT
    iav.item_uuid,
    iav.attribute_id,
    iav.value
FROM item_attribute_value AS iav
INNER JOIN item AS i
    ON i.uuid = iav.item_uuid
WHERE iav.attribute_id = ?
  AND iav.value IS NOT NULL
ORDER BY iav.value

-- Wrong
select item_uuid,attribute_id,value from item_attribute_value
where attribute_id=? and value is not null order by value
```

---

## Parameterization — All Values Bound

Every value passed to a query is a bound parameter. No f-strings, `%` formatting, `.format()`, or string concatenation on SQL text. Dynamic `WHERE` clause assembly uses a parameter-binding builder that accumulates clause fragments and their bound values separately, then combines them at execution time.

The placeholder syntax varies by DBMS driver (`?` for SQLite's `sqlite3`, `%s` or `$1` for psycopg). The mapper chooses the correct syntax for its target; the principle — no value ever interpolated into SQL text — is universal.

```python
# Correct
conn.execute(self._GET_BY_ID, (id.bytes,))

# Wrong — injection surface, prevents caching
conn.execute(f"SELECT ... WHERE id = '{id}'")
```

---

## INSERT Column Lists — Always Explicit

Every INSERT statement names its target columns. `INSERT INTO table VALUES (...)` without a column list is prohibited — it binds to column position, which breaks silently when the schema changes.

```sql
-- Correct
INSERT INTO unit_dimension (
    id,
    name,
    base_unit,
    deleted_ts,
    created_user_uuid,
    updated_user_uuid
) VALUES (?, ?, ?, ?, ?, ?)

-- Wrong
INSERT INTO unit_dimension VALUES (?, ?, ?, ?, ?, ?)
```

---

## Batch Forms

Every INSERT and UPDATE has both a single-row form and a batch form built from the same definition; only the execution method differs (`execute` vs `executemany`). The batch form is the primary path for bulk operations. (The examples below show the emitted SQL shape; the query component assembles it — it is not hand-written as a class constant.)

```python
_INSERT = """
    -- unit_multiplier: insert row
    INSERT INTO unit_multiplier (id, dimension_id, symbol, factor, ...)
    VALUES (?, ?, ?, ?, ...)
"""

def add(self, conn, mul: UnitMultiplier) -> None:
    conn.execute(self._INSERT, self._to_row(mul))

def add_batch(self, conn, muls: list[UnitMultiplier]) -> None:
    conn.executemany(self._INSERT, [self._to_row(m) for m in muls])
```

---

## Transaction Discipline

Mappers never call `commit()` or `rollback()`. Transaction scope is the session's responsibility. This allows callers to compose multi-aggregate writes into a single atomic transaction regardless of the DBMS.

```python
# Correct — mapper writes, does not commit
def add(self, conn, dim: UnitDimension) -> None:
    conn.execute(self._INSERT, self._to_row(dim))

# Wrong — mapper commits, prevents transaction composition
def add(self, conn, dim: UnitDimension) -> None:
    conn.execute(self._INSERT, self._to_row(dim))
    conn.commit()
```

---

# SQLite-Specific Standards

The following rules apply **only** to the libSQL/SQLite backend. They do not apply when writing a Postgres (or other DBMS) mapper, which uses its own type system and conventions. See `thinghound-architecture.md` §9 for the full type mapping.

---

## Physical Rules

**Primary keys signal their type.** Structure/master-data tables use a DB-generated `INTEGER PRIMARY KEY` (normal rowid table); operational/transactional tables use a `UUID` PK stored as `BLOB(16)`. The PK column is named `id` (integer) or `uuid` (uuid). FK columns end in `_id` or `_uuid` to match the referenced PK's type.

**Tables with a non-integer (uuid) primary key are declared `WITHOUT ROWID`.** This makes the declared primary key the table's native storage key. Integer-`id` tables are normal rowid tables. `AUTOINCREMENT`/sequences are permitted on integer keys where useful.

**Foreign keys are enforced** (`PRAGMA foreign_keys = ON`). DDL uses real `REFERENCES` clauses.

**`CHECK` constraints — single-column and cross-column — are both permitted.**

**No `REAL` columns** (the no-float rule). `Decimal` and `Money` use the encodings in `thinghound-architecture.md` §9.

**Temporal columns are `INTEGER` epoch values, never `TEXT`.** `Timestamp` and `Date` columns store an epoch integer (epoch milliseconds, UTC — see `thinghound-architecture.md` §9); the mapper encodes the model's ISO-8601 value to the epoch integer and decodes it back at the storage boundary. `HLC` remains `TEXT` (a causal-clock string, not a wall-clock datetime).

**No column name ends with a preposition** — `created_ts`, not `created_at`; `qty_per_assembly`, not `qty_per`.

---

## Parameter Placeholder Syntax

SQLite's `sqlite3` module uses `?` for positional parameters:

```python
conn.execute("SELECT ... WHERE id = ?", (id.bytes,))
conn.execute("INSERT INTO t (a, b) VALUES (?, ?)", (a, b))
```

When a Postgres mapper is written, use `%s` (psycopg2) or `$1` (psycopg3 / asyncpg) as appropriate for that driver.
