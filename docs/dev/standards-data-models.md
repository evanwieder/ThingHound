# Data Model Standards

**Compact agent version:** `docs/dev/agent/standards-data-models.md`

These standards are strict. ThingHound's data model is the foundation everything else depends on. Imprecision here propagates into every layer above it.

---

## Pydantic Domain Entities

Domain entities are `pydantic.BaseModel` subclasses with `frozen=True`. Frozen means instances are immutable after construction — values are validated once and cannot drift.

```python
import uuid
from pydantic import BaseModel, ConfigDict
from thinghound.types import UUIDv7

class UnitDimension(BaseModel):
    """A measurable domain with a defined base unit."""

    model_config = ConfigDict(frozen=True)

    id: UUIDv7
    name: str
    base_unit: str
    deleted_at: str | None = None
    created_by_user_id: UUIDv7 | None = None
    updated_by_user_id: UUIDv7 | None = None
```

Value objects (no identity, compared by value) use `@dataclass(frozen=True)` instead of Pydantic when instantiation overhead matters.

---

## The `UUIDv7` Type

All ID fields use the `UUIDv7` annotated type defined in `src/thinghound/types.py`. This is `uuid.UUID` wrapped with a version validator — it accepts only version-7 UUIDs at construction time, catching version mismatches (e.g., accidentally passing a v4 UUID) before they reach the database.

```python
# src/thinghound/types.py
from typing import Annotated
import uuid
from pydantic import AfterValidator

def _require_v7(v: uuid.UUID) -> uuid.UUID:
    if v.version != 7:
        raise ValueError(f"expected UUIDv7, got version {v.version}")
    return v

UUIDv7 = Annotated[uuid.UUID, AfterValidator(_require_v7)]
```

**Generate** new IDs with `uuid.uuid7()` (Python 3.14 stdlib). The result is a `uuid.UUID`; Pydantic validates it as `UUIDv7` at model construction.

**Boundary conversions are the mapper's job:**
- Write (domain → SQLite): `item.id.bytes` → `BLOB(16)`
- Read (SQLite → domain): `uuid.UUID(bytes=row["id"])` passed to model constructor → validated as `UUIDv7`
- Bridge outbound: `str(item.id)` → `"8-4-4-4-12"` canonical string
- Bridge inbound: `uuid.UUID("8-4-4-4-12")` passed to model constructor → validated as `UUIDv7`

---

## Precise Field Types

Every field is typed to its exact semantic meaning. Using a generic primitive when a domain type exists is an error.

| Wrong | Correct | Why |
|-------|---------|-----|
| `id: str` | `id: UUIDv7` | Strings are bridge artifacts only |
| `id: bytes` | `id: UUIDv7` | bytes is too generic and carries no UUID semantics |
| `id: uuid.UUID` | `id: UUIDv7` | uuid.UUID accepts any version; only v7 is valid here |
| `value_type: str` | `value_type: ValueType` (Literal or Enum) | Constrained vocabulary; wrong values caught at model construction |
| `amount: int` | `amount: Money` | Raw integers cannot carry currency |
| `resistance: float` | `value_scaled: int` + `value_exact: str` | No float for any measured value, ever |

---

## No REAL Anywhere

No model field, no database column, no intermediate computation uses a float for any dimensional value, quantity, or monetary amount.

`Decimal` is exact everywhere, but its physical SQLite encoding depends on role (see `thinghound-architecture.md` §9, "Decimal encoding by role"):

- **Attribute values:** dual-column `*_scaled INTEGER` + `*_exact TEXT`; `*_scaled` precision = the owning `attribute_definition.scale` (or `attribute_component.scale`).
- **Quantities** (`qty_*`, `moq`, `order_multiple`, `reorder_*`, `safety_stock`): dual-column at a **fixed quantity scale of 6** (project constant).
- **Factors and rates** (`unit_multiplier.factor`, `prefix.factor`, `fx_rate.rate`): **single `*_exact TEXT`** column, no `*_scaled` — a fixed scaled-int can't hold the SI prefix factor range in int64, and they're never range-searched.
- **Money:** `amount_minor: int` + `currency: str`.
- **Scale (attribute values):** defined per `attribute_definition`, not per `unit_dimension`.
- **Conversion path:** exact rationals (`Fraction`) → `Decimal` → `value_scaled`/`value_exact`. Pint's float default is bypassed. The mapper owns this encoding.

---

## Scale per Attribute Definition

The `scale` integer (decimal places for `value_scaled` encoding) is a property of `attribute_definition`, not `unit_dimension`. Two attributes in the same dimension may have different scales for different practical ranges (e.g., `Current` at scale 12 for pA resolution, `Current-High` at scale 3 for industrial range).

Any model or code that reads scale from a dimension is wrong and must be corrected.

---

## Validation in the Model

Business constraints that apply to a single entity belong in the model, not in callers. Use `@field_validator` and `@model_validator` for invariants that must hold whenever the object exists.

```python
from pydantic import BaseModel, ConfigDict, field_validator

class ScaledValue(BaseModel):
    """An exact dimensional value in base units."""

    model_config = ConfigDict(frozen=True)

    value_scaled: int
    value_exact: str
    scale: int

    @field_validator("value_scaled")
    @classmethod
    def within_int64(cls, v: int) -> int:
        if abs(v) > 2**63 - 1:
            raise ValueError(f"value_scaled {v} exceeds signed int64")
        return v
```

Callers must not re-implement or duplicate these checks.

---

## Optional Fields Require Justification

A nullable field (`X | None`) represents a genuine absence of information, not a convenience default. Every nullable field in a domain entity must have its nullability justified in the field docstring or class docstring.

```python
from thinghound.types import UUIDv7

class Item(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUIDv7
    sku: str
    manufacturer_id: UUIDv7 | None = None   # NULL = generic/unknown manufacturer
    part_number: str | None = None           # NULL = no part number assigned
    parent_item_id: UUIDv7 | None = None     # NULL = not a variant child
```

---

## Domain Primitives at Boundaries

Raw primitives do not cross domain boundaries. Wrap them.

- IDs: `uuid.uuid7()` generates; Pydantic validates as `UUIDv7` at model construction; `id.bytes` at the storage boundary; `str(id)` at the bridge boundary
- Money: `Money(amount_minor=150, currency="USD")` — never pass a raw integer as a monetary value
- Scaled values: `ScaledValue(value_scaled=..., value_exact=..., scale=...)` — never pass a raw integer as a dimensional value without its scale and exact form
- Timestamps / dates: the model carries an ISO-8601 string (`created_at`, `updated_at`, `deleted_at`, `effective_date`, …); the **mapper** encodes it to an **epoch integer** (epoch milliseconds, UTC) for SQLite storage and decodes it back at the storage boundary — never stored as `TEXT`. `HLC` is a causal-clock string, stored as text (not an epoch integer). See `thinghound-architecture.md` §9.

---

## Sync Class Classification

Every entity in the logical model carries a sync class — a behavioral, domain-level property:

**CRR** — synced. Conflict-free replicated. Every CRR entity carries `created_by_user_id: UUID (optional)` and `updated_by_user_id: UUID (optional)`. Natural-key uniqueness is a business constraint enforced by the service layer.

**LOG** — append-only synced. Insert-only; never updated or deleted after creation. Every LOG entity carries `user_id: UUID (optional)`. Domain models for LOG entities have no `update()` method.

**LOCAL** — device-only. Never synced. Rebuilt from CRR/LOG after every sync merge. No attribution required.

**REF** — reference data. Application-defined code table values seeded by migrations. Identical on every device. Does not sync. Read-only at runtime. No attribution columns.

The physical constraints that CRR/LOG status imposes on SQLite DDL (DEFAULT on NOT NULL columns, no cross-column CHECK, etc.) are documented in `thinghound-architecture.md` §9. They are physical implementation details of the SQLite + cr-sqlite substrate, not logical model concerns.

---

## Code Tables — No Native Enum Types

Domain-constrained string values use the **code table pattern** — never a native enum type. Enum types are not consistently supported across all target DBMSs and are not used here.

Each code table is a **REF** entity with three attributes: `code TEXT` (primary key, single character), `name TEXT` (display name), `description TEXT`. Referencing entities rename the column to `<field>_code` (e.g., `value_type_code`) and type it as `String`.

In Python domain models, a `*_code` field is typed as `String` referencing the corresponding code entity. Valid code values are documented in the data model spec §3. The service layer validates `*_code` values against the code table on write.

Do not use Pydantic `Literal[...]` or Python `Enum` as the domain type for code fields. The code table is the authority; Pydantic validation should check against the loaded code table values, not a hardcoded literal set.

---

## Tolerance as a Separate Attribute

Tolerance is not a field on `item_attribute_value`. It is a separate attribute definition in the appropriate dimension:
- Relative tolerance (±5%, ±100ppm): a numeric attribute in a dimensionless Ratio dimension.
- Absolute tolerance (±2Ω): a numeric attribute in the same dimension as the measured value (e.g., Resistance).

Any model that adds `tol_low_scaled`, `tol_high_scaled`, or similar fields to a value row is incorrect.

---

## Attribute Categories

Every `attribute_definition` belongs to exactly one `attribute_category`. Two attributes with the same name in different attribute categories are entirely distinct entities with independent types, units, and scales. The `(name, attribute_category_id)` pair is the natural unique key.

---

## One Class Per File

Each domain model class has its own file. See Python coding standards (`docs/dev/standards-python.md`) for the naming convention.
