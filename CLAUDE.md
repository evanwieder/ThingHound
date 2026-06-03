# ThingHound — Agent Instructions

These instructions apply to every agentic session in this repo and override default behavior.

## Python coding standards

### Type annotations
- Always annotate all function parameters, return types, and class attributes.
- Never use `Optional[X]` — use `X | None` instead.
- Never import `List`, `Dict`, or `Set` from `typing` — use the built-in `list`, `dict`, and `set`.
- Avoid `Any` unless there is no other option; leave a comment explaining why when you do use it.
- Use modern union syntax (`X | Y`) throughout; do not use `Union[X, Y]`.

### Docstrings
- **Google-style docstrings are required** for every module, class, function, and method that can have one.
- Module docstrings: one line summary at the top of every `.py` file.
- Class docstrings: describe the class purpose and, where non-obvious, its invariants.
- Function/method docstrings: summary line, then `Args:`, `Returns:`, `Raises:` sections as applicable. Omit a section only when it is genuinely empty (e.g., a `void` function with no notable raises).

```python
def encode_scaled(base: Fraction, scale: int) -> tuple[int, str]:
    """Encode an exact rational value as a scaled integer and canonical decimal string.

    Args:
        base: The value in base units as an exact rational.
        scale: Number of decimal places to keep (per-dimension constant).

    Returns:
        A tuple of (value_scaled, value_exact) where value_scaled is the integer
        representation and value_exact is the fixed-point decimal string.

    Raises:
        OverflowError: If value_scaled would exceed signed int64.
    """
```

### File and class layout
- **One class per file.** Exceptions require a strong justification (e.g., a small private helper dataclass that is only meaningful alongside its owning class, or a group of tightly coupled value types with no independent use). When in doubt, split.
- This applies to Pydantic models too — each domain model gets its own file.
- Name the file after the class in snake_case: `UnitDimension` → `unit_dimension.py`.

### General
- Use `from __future__ import annotations` at the top of every file to enable forward references.
- Prefer dataclasses (frozen) for value objects, Pydantic `BaseModel` (frozen config) for domain entities.
- No bare `except:` or `except Exception:` swallowing — catch specific exceptions or re-raise.
- No mutable default arguments.

## Project conventions

See `docs/dev/crr-rules.md` for CRR/sync table rules enforced by the CI guard.

Key invariants (do not re-litigate):
- No `REAL` anywhere — dimensional values use `value_scaled INTEGER` + `value_exact TEXT`.
- UUIDs stored as `BLOB(16)` (UUIDv7); serialized to canonical `8-4-4-4-12` string only at service/bridge boundaries.
- `foreign_keys=OFF` on every SQLite connection — referential integrity is application-enforced.
- Money is integer minor-units (`Money` value object) — never float.

## Workflow

- All development on branches; merge to `main` only via user-approved PR.
- Do not start coding unprompted; wait for explicit user instruction.
- Do not push to remote without explicit user approval.
