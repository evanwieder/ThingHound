# SQL Coding Standards

**Compact agent version:** `docs/dev/agent/standards-sql.md`

SQL in ThingHound is hand-written and lives exclusively in aggregate mappers. Standards are divided into two sections: **Global** (apply regardless of the target DBMS) and **SQLite-Specific** (apply only to the current SQLite + cr-sqlite backend). When a future Postgres mapper is written, global standards apply; SQLite-specific standards do not.

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

Index name tokens follow the same rule: `idx_item_deleted_at`, never `idx_items_deleted_at`.

This convention applies to all table identifiers in migrations, SQL constants, mappers, specs, and documentation. English prose and column names are exempt; only table identifiers are governed by this rule.

---

## Where SQL Lives

All SQL lives in **aggregate mappers**. No SQL string appears in service classes, domain objects, collections, query/specification objects, tests, or any other location. The mapper is the only place that knows both the physical schema and the domain model. Consumers see only domain models.

---

## SQL as Named Constants — Prepared Once, Executed Many Times

Every SQL statement is a named class-level or module-level constant. SQL is never constructed inline inside a method body. Constants are defined once and reused on every call — the driver compiles and caches the parameterized statement; repeated execution with different parameters avoids re-parsing overhead.

For high-frequency queries, DBMS drivers that support explicit prepared statements (e.g., psycopg3's `conn.prepare()`) should be used to prepare the statement once at mapper initialization and execute it repeatedly. SQLite's `sqlite3` module handles caching internally when a parameterized constant is reused.

```python
# Correct — constant defined once, reused on every call
class UnitDimensionMapper:
    _GET_BY_ID = """
        -- unit_dimension: fetch single row by primary key
        SELECT
            ud.id,
            ud.name,
            ud.base_unit,
            ud.deleted_at,
            ud.created_by_user_id,
            ud.updated_by_user_id
        FROM unit_dimension AS ud
        WHERE ud.id = ?
    """

    def get(self, conn: sqlite3.Connection, id: uuid.UUID) -> UnitDimension | None:
        row = conn.execute(self._GET_BY_ID, (id.bytes,)).fetchone()
        return self._from_row(row) if row else None

# Wrong — reconstructed on every call, no caching benefit, no traceability
def get(self, conn, id):
    row = conn.execute(
        "SELECT * FROM unit_dimension WHERE id = ?", (id,)
    ).fetchone()
```

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
    ud.deleted_at
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
    iav.item_id,
    iav.attribute_id,
    iav.value,
    ad.name AS attribute_name
FROM item_attribute_value AS iav
INNER JOIN attribute_definition AS ad
    ON ad.id = iav.attribute_id
LEFT OUTER JOIN unit_dimension AS ud
    ON ud.id = ad.unit_dimension_id
WHERE iav.item_id = ?

-- Wrong — abbreviated join types
FROM item_attribute_value iav
JOIN attribute_definition ad ON ad.id = iav.attribute_id
LEFT JOIN unit_dimension ud ON ud.id = ad.unit_dimension_id
```

---

## ON Clauses — One Per Line, Indented

Each `ON` condition appears on its own line, indented under its `JOIN`. When a join has multiple conditions, each condition is on its own line with `AND` at the start.

```sql
-- Correct
FROM item AS i
INNER JOIN item_attribute_value AS iav
    ON iav.item_id = i.id
INNER JOIN attribute_definition AS ad
    ON ad.id = iav.attribute_id
   AND ad.deleted_at IS NULL

-- Wrong — ON clause on same line as JOIN
FROM item i
INNER JOIN item_attribute_value iav ON iav.item_id = i.id
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
WHERE ud.deleted_at IS NULL

-- Wrong — no alias, no qualification
SELECT id, name FROM unit_dimension WHERE deleted_at IS NULL
```

Establish a consistent alias vocabulary: `ud` = `unit_dimension`, `iav` = `item_attribute_value`, `ad` = `attribute_definition`, `i` = `item`, `ic` = `item_category`, `ie` = `inventory_event`, etc.

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

Every SQL constant begins with a single-line comment naming the primary table and describing the operation.

```python
_GET_BY_ID = """
    -- unit_dimension: fetch by primary key
    SELECT ud.id, ud.name ...
"""

_LIST_ACTIVE = """
    -- unit_dimension: list non-deleted, ordered by name
    SELECT ud.id, ud.name ...
"""

_INSERT = """
    -- unit_dimension: insert new row
    INSERT INTO unit_dimension (id, name, ...) VALUES (?, ?, ...)
"""
```

---

## Formatting

SQL keywords are uppercase. Each major clause (`SELECT`, `FROM`, `INNER JOIN`, `WHERE`, `ORDER BY`, `GROUP BY`, `HAVING`, `LIMIT`) starts on its own line. Column lists and conditions are indented 4 spaces from the clause keyword. Continuation conditions (`AND`, `OR`) are indented to align with the first condition.

```sql
-- Correct
SELECT
    iav.item_id,
    iav.attribute_id,
    iav.value
FROM item_attribute_value AS iav
INNER JOIN item AS i
    ON i.id = iav.item_id
WHERE iav.attribute_id = ?
  AND iav.value IS NOT NULL
ORDER BY iav.value

-- Wrong
select item_id,attribute_id,value from item_attribute_value
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
    deleted_at,
    created_by_user_id,
    updated_by_user_id
) VALUES (?, ?, ?, ?, ?, ?)

-- Wrong
INSERT INTO unit_dimension VALUES (?, ?, ?, ?, ?, ?)
```

---

## Batch Forms

Every INSERT and UPDATE statement has both a single-row form and a batch form. Both use the same named constant; only the execution method differs. The batch form is the primary path for bulk operations.

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

The following rules apply **only** to the SQLite + cr-sqlite backend. They do not apply when writing a Postgres (or other DBMS) mapper. CRR and LOG table concepts are SQLite/cr-sqlite constructs; a real DBMS backend uses its own replication and transaction mechanisms instead.

---

## CRR/LOG Physical Constraints

These are requirements of cr-sqlite, not of SQL in general. See `docs/dev/crsqlite-spike-findings.md` for empirical verification and `thinghound-architecture.md` §9 for the full type mapping.

**Every non-PK `NOT NULL` column must declare a `DEFAULT` value.**
cr-sqlite applies column-level changesets independently. A column arriving before others must not violate NOT NULL on partially-applied rows.

```sql
-- Correct
name    TEXT    NOT NULL DEFAULT '',
scale   INTEGER NOT NULL DEFAULT 0

-- Wrong — cr-sqlite rejects crsql_as_crr
name TEXT NOT NULL
```

**No cross-column `CHECK` constraints.**
A cross-column check may fire on a partial changeset and reject a valid remote write. Enforce cross-column invariants at the service layer or post-merge integrity check.

```sql
-- Wrong on CRR/LOG tables
CHECK ((value IS NULL) = (display_unit IS NULL))
```

**Single-column `CHECK` constraints** are acceptable if conservative.

**No `AUTOINCREMENT`.** Device-local sequences cannot be safely merged across peers.

**No `REAL` columns.** Floating-point loses precision in the JSON changeset serialization used by cr-sqlite.

**Tables with non-integer primary keys must be declared `WITHOUT ROWID`.** In SQLite, rowid tables duplicate storage for non-integer PK lookups and can weaken key semantics for composite/text/blob primary keys; `WITHOUT ROWID` makes the declared primary key the table's native storage key and is the required form for ThingHound non-integer PK tables.

**Temporal columns are `INTEGER` epoch values, never `TEXT`.** `Timestamp` and `Date` columns store an epoch integer (epoch milliseconds, UTC — see `thinghound-architecture.md` §9); the mapper encodes the model's ISO-8601 value to the epoch integer and decodes it back at the storage boundary. `HLC` remains `TEXT` (a causal-clock string, not a wall-clock datetime).

**Schema changes to CRR/LOG tables use cr-sqlite's alter protocol:**
```sql
SELECT crsql_begin_alter('table_name');
ALTER TABLE table_name ADD COLUMN notes TEXT DEFAULT NULL;
SELECT crsql_commit_alter('table_name');
```

The CI guard (`scripts/check_crr_rules.py`) enforces these rules on every migration file. A migration that violates any of them must not be merged.

---

## Parameter Placeholder Syntax

SQLite's `sqlite3` module uses `?` for positional parameters:

```python
conn.execute("SELECT ... WHERE id = ?", (id.bytes,))
conn.execute("INSERT INTO t (a, b) VALUES (?, ?)", (a, b))
```

When a Postgres mapper is written, use `%s` (psycopg2) or `$1` (psycopg3 / asyncpg) as appropriate for that driver.
