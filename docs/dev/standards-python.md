# Python Coding Standards

**Compact agent version:** `docs/dev/agent/standards-python.md`

---

## Type Annotations

Every function parameter, return type, and class attribute must be annotated.

**Union types:** use modern union syntax throughout.
```python
# Correct
def get(self, conn: sqlite3.Connection, id: uuid.UUID) -> UnitDimension | None: ...

# Wrong
def get(self, conn: sqlite3.Connection, id: uuid.UUID) -> Optional[UnitDimension]: ...
```

**Built-in generics:** use built-in types, not `typing` imports.
```python
# Correct
def list_all(self) -> list[UnitDimension]: ...
params: dict[str, int] = {}

# Wrong
from typing import List, Dict
def list_all(self) -> List[UnitDimension]: ...
```

**`Any`:** avoid. When unavoidable (e.g., a dynamic dispatch point), leave a comment explaining why.

**`Optional[X]`:** never. Use `X | None`.

**`Union[X, Y]`:** never. Use `X | Y`.

---

## Docstrings

Google-style docstrings are required for every module, class, function, and method.

**Module docstring** — one-line summary at the top of every `.py` file, before imports:
```python
"""Aggregate mapper for the schema registry domain."""
```

**Class docstring** — describe the class purpose and any non-obvious invariants:
```python
class SchemaRegistryMapper:
    """Aggregate mapper for unit dimensions, multipliers, and attribute definitions.

    Owns all SQL for the schema registry tables. The physical schema is an
    implementation detail of this class; no consumer references table names.
    """
```

**Function/method docstring** — summary line, then `Args:`, `Returns:`, `Raises:` as applicable. Omit sections that are genuinely empty.
```python
def get_dimension(self, conn: sqlite3.Connection, id: uuid.UUID) -> UnitDimension | None:
    """Retrieve a UnitDimension by ID.

    Args:
        conn: Active SQLite connection.
        id: The dimension ID as a UUIDv7.

    Returns:
        The UnitDimension if found, None if the ID does not exist or is soft-deleted.
    """
```

Do not write docstrings that restate the function name or describe *what* the code does rather than *why*. If the code is clear, a one-line summary is sufficient.

---

## File and Class Layout

**One class per file.** Name the file after the class in `snake_case`:
- `UnitDimension` → `unit_dimension.py`
- `SchemaRegistryMapper` → `schema_registry_mapper.py`

Exceptions require strong justification: a small private helper dataclass meaningful only alongside its owning class, or a group of tightly coupled value objects with no independent use. When in doubt, split.

This applies to Pydantic models, dataclasses, and service classes equally.

---

## Value Objects and Domain Entities

**Value objects** (no identity, compared by value): use `@dataclass(frozen=True)`.

**Domain entities** (have identity, validated at construction): use `pydantic.BaseModel` with `model_config = ConfigDict(frozen=True)`.

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
```

---

## Exception Handling

No bare `except:` or `except Exception:` that swallows the error. Catch specific exceptions or re-raise.

```python
# Correct
try:
    conn.execute(self._INSERT, params)
except sqlite3.IntegrityError:
    raise DuplicateSkuError(sku) from None

# Wrong — swallows everything
try:
    conn.execute(self._INSERT, params)
except Exception:
    pass
```

---

## General

- No mutable default arguments.
- Prefer `pathlib.Path` over string paths.
- Import order: stdlib → third-party → local. One blank line between groups.
- Line length: 100 characters (configured in `pyproject.toml`).
- **Do not use `from __future__ import annotations`.** Python 3.14 evaluates annotations lazily by default (PEP 649); the import is redundant and must not appear in any file. Remove it if you encounter it in existing code.
- Ruff enforces style; CI blocks merges that fail linting.
