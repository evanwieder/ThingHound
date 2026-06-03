# Repository / Aggregate Mapper Standards

**Compact agent version:** `docs/dev/agent/standards-repository.md`

---

## The Aggregate Mapper Pattern

ThingHound uses **aggregate mappers**, not a generic repository. The distinction matters.

A **generic repository** owns one table and provides CRUD methods. This is the antipattern: SQL leaks across multiple places, a `row_to_*` helper smeared in module scope, the repository calling `commit()`.

An **aggregate mapper** owns a *persistence aggregate* — a root entity and all the rows it is loaded and saved with. A simple entity maps to one table; a compound entity (e.g., an item with its attribute values and component values) maps to several tables via one mapper. The mapper is the single authoritative place for that aggregate's SQL, its physical layout, and its row-to-model translation.

---

## SQL Ownership

All SQL for an aggregate lives in its mapper as named class-level constants. No SQL appears anywhere else — not in services, not in domain objects, not in tests, not in free functions.

```python
class UnitDimensionMapper:
    """Aggregate mapper for unit_dimension and unit_multiplier tables."""

    _GET_DIMENSION = """
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

    _LIST_DIMENSIONS = """
        -- unit_dimension: list all non-deleted rows ordered by name
        SELECT
            ud.id,
            ud.name,
            ud.base_unit,
            ud.deleted_at,
            ud.created_by_user_id,
            ud.updated_by_user_id
        FROM unit_dimension ud
        WHERE ud.deleted_at IS NULL
        ORDER BY ud.name
    """

    _INSERT_DIMENSION = """
        -- unit_dimension: insert new row
        INSERT INTO unit_dimension (
            id, name, base_unit, deleted_at,
            created_by_user_id, updated_by_user_id
        ) VALUES (?, ?, ?, ?, ?, ?)
    """
```

---

## Row-to-Model Mapping as Private Class Methods

Row mapping belongs to the mapper, not to free module-level functions. Every `_row_to_*` equivalent is a private method on the mapper class.

```python
class UnitDimensionMapper:

    def _dimension_from_row(self, row: sqlite3.Row) -> UnitDimension:
        return UnitDimension(
            id=row["id"],
            name=row["name"],
            base_unit=row["base_unit"],
            deleted_at=row["deleted_at"],
            created_by_user_id=row["created_by_user_id"],
            updated_by_user_id=row["updated_by_user_id"],
        )

    def get(self, conn: sqlite3.Connection, id: uuid.UUID) -> UnitDimension | None:
        row = conn.execute(self._GET_DIMENSION, (id.bytes,)).fetchone()
        return self._dimension_from_row(row) if row else None
```

Free module-level `_row_to_dimension()` functions are the antipattern this replaces.

---

## No `commit()` in Mappers

Mappers never call `commit()` or `rollback()`. Transaction scope is the session's responsibility. This allows callers to compose multi-table, multi-aggregate writes into one atomic transaction.

```python
# Correct — mapper writes but does not commit
def add(self, conn: sqlite3.Connection, dim: UnitDimension) -> None:
    conn.execute(self._INSERT_DIMENSION, self._dimension_to_row(dim))

# Correct caller usage — session owns the transaction
with session.transaction():
    mapper.add(conn, dimension)
    mapper.add_multipliers(conn, multipliers)
    # commit happens when the context manager exits cleanly
```

---

## Public API: Domain Models Only

Public mapper methods accept and return domain model instances — never raw tuples, dicts, or `sqlite3.Row` objects. The physical schema is encapsulated inside the mapper; consumers see only domain models.

```python
# Correct
def get(self, conn: sqlite3.Connection, id: uuid.UUID) -> UnitDimension | None: ...
def list_active(self, conn: sqlite3.Connection) -> list[UnitDimension]: ...
def add(self, conn: sqlite3.Connection, dim: UnitDimension) -> None: ...
def add_batch(self, conn: sqlite3.Connection, dims: list[UnitDimension]) -> None: ...

# Wrong — exposes raw database row to caller
def get(self, conn, id) -> sqlite3.Row: ...
def list_active(self, conn) -> list[dict]: ...
```

---

## Batch-First Design

Every write operation has both a single-row form and a batch (`executemany`) form. The batch form is the primary path for collections; the single-row form is the degenerate case.

```python
def add(self, conn: sqlite3.Connection, dim: UnitDimension) -> None:
    conn.execute(self._INSERT_DIMENSION, self._dimension_to_row(dim))

def add_batch(self, conn: sqlite3.Connection, dims: list[UnitDimension]) -> None:
    conn.executemany(self._INSERT_DIMENSION, [self._dimension_to_row(d) for d in dims])
```

Collections use `items.save()` → one batched statement in one transaction, not a per-item loop.

---

## Single-Writer-Per-Table Invariant

A mapper may own many tables, but each table is written by exactly one aggregate mapper. Two mappers may never write the same table. Read queries may cross table boundaries freely.

This invariant is what makes the mapper the single authoritative home for each table's write SQL. Violating it creates two code paths that can disagree about column lists, defaults, and data transformations.

---

## Physical Schema Independence

The physical layout of tables is an implementation detail of the mapper. Consumers (services, domain objects, collections, query objects, tests) never reference table names, column names, or SQL text. If the physical schema of an aggregate changes (e.g., a table is split, columns are reorganized), the change is confined to the mapper.

This is the test: could you change the physical schema and have it only affect the mapper? If no, the boundary is leaking.

---

## The AppRegistry

Config and structure data (unit dimensions, attribute categories, attribute definitions, category trees) is loaded at startup into the `AppRegistry` singleton and held in memory for the session. Operational code accesses structure through the registry — it does not issue SQL queries to look up attribute definitions or unit dimensions at runtime.

The AppRegistry is populated by the same mappers that service operational writes. It is refreshed when structure changes (rare). It is not a general-purpose cache; it is the in-memory representation of configuration that must be consistent for the whole session.
