# Repository / Aggregate Mapper Standards

**Compact agent version:** `docs/dev/agent/standards-repository.md`

---

## The Aggregate Mapper Pattern

ThingHound uses **aggregate mappers**, not a generic repository. The distinction matters.

A **generic repository** owns one table and provides CRUD methods. This is the antipattern: SQL leaks across multiple places, a `row_to_*` helper smeared in module scope, the repository calling `commit()`.

An **aggregate mapper** owns a *persistence aggregate* — a root entity and all the rows it is loaded and saved with. A simple entity maps to one table; a compound entity (e.g., an item with its attribute values and component values) maps to several tables via one mapper. The mapper is the single authoritative place for that aggregate's SQL, its physical layout, and its row-to-model translation.

---

## SQL Ownership

SQL is built by the model-aware query component from the mapper's column and relationship metadata. The mapper owns that metadata and the row ↔ model conversions; it does not hand-write SQL strings or store them as class constants. Callers express intent only. No SQL appears anywhere else — not in services, not in domain objects, not in tests, not in free functions. (The examples below show the emitted SQL shape, not literal constants to copy.)

```python
class UnitDimensionMapper:
    """Aggregate mapper for unit_dimension and unit_multiplier tables."""

    # emitted shape — fetch single row by primary key
    #   SELECT ud.id, ud.name, ud.base_unit
    #   FROM unit_dimension AS ud
    #   WHERE ud.id = ?
    #
    # emitted shape — list all non-deleted rows ordered by name
    #   SELECT ud.id, ud.name, ud.base_unit
    #   FROM unit_dimension AS ud
    #   WHERE ud.deleted_ts IS NULL
    #   ORDER BY ud.name
    #
    # emitted shape — insert new row
    #   INSERT INTO unit_dimension (name, base_unit) VALUES (?, ?)
```

`unit_dimension` is a structure table, so its PK is a DB-generated integer `id` and the model does not carry it through audit columns (`deleted_ts`, `created_user_uuid`, `updated_user_uuid` are excluded from the model and surfaced via a separate `Audit` object on demand; `deleted_ts` is still used in WHERE filters at the SQL level).

---

## Row-to-Model Mapping as Private Class Methods

Row mapping belongs to the mapper, not to free module-level functions. Every `_row_to_*` equivalent is a private method on the mapper class.

```python
class UnitDimensionMapper:

    def _from_row(self, row: sqlite3.Row) -> UnitDimension:
        return UnitDimension(
            id=row["id"],
            name=row["name"],
            base_unit=row["base_unit"],
        )

    def get(self, conn: sqlite3.Connection, id: int) -> UnitDimension | None:
        row = self.query.get(conn, UnitDimension, id=id)
        return self._from_row(row) if row else None
```

Free module-level `_row_to_dimension()` functions are the antipattern this replaces.

---

## Converter Naming: Single-Entity vs. Compound Mappers

The naming of the `*_from_row` / `*_to_row` converters depends on how many entity types the mapper maps:

- A mapper that maps a **single entity type** names its converters **`_from_row` / `_to_row`**. The class name already identifies the type; an entity prefix would be noise.
- A mapper that maps **several entity types** (a compound aggregate — e.g. `AttributeMapper` mapping `attribute`, `attribute_enum_value`, `attribute_component`, `attribute_allowed_prefix`) names one converter per type using the form **`_<entity>_from_row` / `_<entity>_to_row`** (e.g. `_attribute_from_row`, `_enum_value_from_row`, `_component_from_row`, `_allowed_prefix_from_row`) to disambiguate.

```python
# Single-entity mapper — unprefixed converters
class UnitDimensionMapper:
    def _from_row(self, row: sqlite3.Row) -> UnitDimension: ...
    def _to_row(self, dim: UnitDimension) -> tuple: ...

# Compound mapper — one converter per owned type, each prefixed
class AttributeMapper:
    def _attribute_from_row(self, row): ...       # attribute
    def _enum_value_from_row(self, row): ...      # attribute_enum_value
    def _component_from_row(self, row): ...       # attribute_component
    def _allowed_prefix_from_row(self, row): ...  # attribute_allowed_prefix
```

---

## No `commit()` in Mappers

Mappers never call `commit()` or `rollback()`. Transaction scope is the session's responsibility. This allows callers to compose multi-table, multi-aggregate writes into one atomic transaction.

```python
# Correct — mapper writes but does not commit
def add(self, conn: sqlite3.Connection, dim: UnitDimension) -> None:
    self.query.insert(conn, UnitDimension, self._to_row(dim))

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
def get(self, conn: sqlite3.Connection, id: int) -> UnitDimension | None: ...
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
    self.query.insert(conn, UnitDimension, self._to_row(dim))

def add_batch(self, conn: sqlite3.Connection, dims: list[UnitDimension]) -> None:
    self.query.insert_many(conn, UnitDimension, [self._to_row(d) for d in dims])
```

Collections use `items.save()` → one batched statement in one transaction, not a per-item loop.

---

## Physical Schema Independence

The physical layout of tables is an implementation detail of the mapper. Consumers (services, domain objects, collections, query objects, tests) never reference table names, column names, or SQL text. If the physical schema of an aggregate changes (e.g., a table is split, columns are reorganized), the change is confined to the mapper.

This is the test: could you change the physical schema and have it only affect the mapper? If no, the boundary is leaking.

---

## The AppRegistry

Config and structure data (unit dimensions, attribute domains, attributes, category trees) is loaded at startup into the `AppRegistry` singleton and held in memory for the session. Operational code accesses structure through the registry — it does not issue SQL queries to look up attributes or unit dimensions at runtime.

The AppRegistry is populated by the same mappers that service operational writes. It is refreshed when structure changes (rare). It is not a general-purpose cache; it is the in-memory representation of configuration that must be consistent for the whole session.
