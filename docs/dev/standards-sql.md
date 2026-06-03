# SQL Coding Standards

**Compact agent version:** `docs/dev/agent/standards-sql.md`

---

## Where SQL Lives

All SQL lives in **aggregate mappers**. No SQL string appears in service classes, domain objects, collections, query/specification objects, tests, or any other location. The mapper is the only place that knows both the physical schema and the domain model.

This rule enforces encapsulation: the physical table layout is an implementation detail of the mapper. Consumers see only domain models.

---

## SQL as Named Constants

Every SQL statement is a named class-level or module-level constant. SQL is never constructed inline inside a method body.

```python
# Correct — defined once, reused every call
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
        FROM unit_dimension ud
        WHERE ud.id = ?
    """

    def get(self, conn: sqlite3.Connection, id: uuid.UUID) -> UnitDimension | None:
        row = conn.execute(self._GET_BY_ID, (id.bytes,)).fetchone()
        return self._row_to_model(row) if row else None

# Wrong — constructed inline, no reuse, no traceability
def get(self, conn, id):
    row = conn.execute(
        "SELECT * FROM unit_dimension WHERE id = ?", (id,)
    ).fetchone()
```

---

## Never `SELECT *`

Every SELECT statement lists columns explicitly. `SELECT *` is prohibited.

**Why:** `SELECT *` returns columns in schema-defined order, which silently breaks if columns are added, reordered, or renamed. Explicit column lists make the contract visible and ensure the mapper controls exactly what it receives.

```sql
-- Correct
SELECT
    ud.id,
    ud.name,
    ud.base_unit,
    ud.deleted_at
FROM unit_dimension ud
WHERE ud.id = ?

-- Wrong
SELECT * FROM unit_dimension WHERE id = ?
```

---

## Table Aliases

Every table reference in a query carries an alias, even on single-table queries.

```sql
-- Correct — alias on single table
SELECT
    ud.id,
    ud.name
FROM unit_dimension ud
WHERE ud.deleted_at IS NULL

-- Correct — aliases on all tables in a join
SELECT
    iav.item_id,
    iav.attribute_id,
    iav.value_scaled,
    ad.name  AS attribute_name
FROM item_attribute_value iav
JOIN attribute_definition ad ON ad.id = iav.attribute_id
WHERE iav.item_id = ?

-- Wrong — no alias, will require rewrite when joined
SELECT id, name FROM unit_dimension WHERE deleted_at IS NULL
```

Aliases should be short and consistent across the codebase: `ud` for `unit_dimension`, `iav` for `item_attribute_value`, `ad` for `attribute_definition`, etc.

---

## Leading Traceability Comment

Every SQL constant begins with a single-line comment identifying the operation and the primary table. This comment appears inside the string, as the first line.

```python
_GET_BY_ID = """
    -- unit_dimension: fetch single row by primary key
    SELECT ud.id, ...
"""

_INSERT = """
    -- unit_dimension: insert new row
    INSERT INTO unit_dimension (id, name, base_unit, ...)
    VALUES (?, ?, ?, ...)
"""

_LIST_ACTIVE = """
    -- unit_dimension: list all non-deleted rows
    SELECT ud.id, ...
    FROM unit_dimension ud
    WHERE ud.deleted_at IS NULL
    ORDER BY ud.name
"""
```

---

## Formatting

SQL keywords are uppercase. Each major clause starts on its own line. Continuation lines are indented consistently (4 spaces inside the string).

```sql
-- Correct
SELECT
    iav.item_id,
    iav.attribute_id,
    iav.value_scaled,
    iav.value_exact
FROM item_attribute_value iav
WHERE iav.attribute_id = ?
  AND iav.value_scaled BETWEEN ? AND ?
ORDER BY iav.value_scaled

-- Wrong — junk in a string
"select item_id,attribute_id,value_scaled from item_attribute_value where attribute_id=? and value_scaled between ? and ?"
```

---

## Parameterization

Every value passed to a query is a bound parameter (`?`). No f-strings, `%` formatting, or `.format()` on SQL text. Dynamic `WHERE` clause assembly uses a parameter-binding builder that accumulates clauses and their bound values separately, then combines them.

```python
# Correct
conn.execute(self._GET_BY_ID, (id,))

# Wrong — injection surface, bypasses statement cache
conn.execute(f"SELECT ... WHERE id = '{id}'")
```

---

## INSERT Column Lists

Every INSERT statement lists the target columns explicitly. `INSERT INTO table VALUES (...)` without a column list is prohibited.

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

Every INSERT and UPDATE has both a single-row form and a batch form (`executemany`). The batch form uses the same SQL constant as the single-row form; only the execution method differs.

```python
_INSERT = """
    -- unit_multiplier: insert row
    INSERT INTO unit_multiplier (id, dimension_id, symbol, factor_exact, ...)
    VALUES (?, ?, ?, ?, ...)
"""

def add(self, conn, multiplier: UnitMultiplier) -> None:
    conn.execute(self._INSERT, self._to_row(multiplier))

def add_batch(self, conn, multipliers: list[UnitMultiplier]) -> None:
    conn.executemany(self._INSERT, [self._to_row(m) for m in multipliers])
```

---

## Transaction Discipline

Mappers never call `commit()` or `rollback()`. Transaction scope is the session's responsibility. This allows callers to compose multi-aggregate writes into a single atomic transaction.

```python
# Correct — mapper does not commit
def add(self, conn, dim: UnitDimension) -> None:
    conn.execute(self._INSERT, self._to_row(dim))

# Wrong — mapper commits, prevents transaction composition
def add(self, conn, dim: UnitDimension) -> None:
    conn.execute(self._INSERT, self._to_row(dim))
    conn.commit()  # ← violates caller's transaction control
```

---

## SQLite Physical Model Constraints (CRR/LOG Tables)

When authoring SQLite DDL for CRR or LOG tables, the following physical constraints apply. These are requirements of the SQLite + cr-sqlite substrate, not logical model concerns. See `thinghound-architecture.md` §9 for the full type mapping and rationale.

**Every non-PK `NOT NULL` column must declare a `DEFAULT` value.**
`crsql_as_crr` rejects tables with NOT NULL columns that have no default. cr-sqlite applies column-level changesets independently; a column arriving before others must not violate NOT NULL.

```sql
-- Correct
name TEXT NOT NULL DEFAULT '',
scale INTEGER NOT NULL DEFAULT 0

-- Wrong — cr-sqlite will reject crsql_as_crr
name TEXT NOT NULL
```

**No cross-column `CHECK` constraints.**
Column changesets apply independently; a cross-column check may evaluate when only one column has arrived, rejecting a valid partial changeset from a peer. Enforce cross-column invariants at the application layer (service or post-merge integrity check).

```sql
-- Wrong — may reject a valid remote write
CHECK ((value IS NULL) = (display_unit IS NULL))

-- Correct — enforce in service code, not DDL
```

**Single-column `CHECK` constraints are acceptable** if conservative (e.g., validating an enum value on a single column).

**No `AUTOINCREMENT`.** Device-local sequences cannot be safely merged.

**No `REAL` columns.** Floating-point values lose precision in JSON serialization during sync changeset exchange.

**Schema changes to CRR/LOG tables use cr-sqlite's alter protocol:**
```sql
SELECT crsql_begin_alter('table_name');
ALTER TABLE table_name ADD COLUMN notes TEXT DEFAULT NULL;
SELECT crsql_commit_alter('table_name');
```

The CI guard (`scripts/check_crr_rules.py`) enforces these rules on every migration file. A migration that violates any of them must not be merged.
