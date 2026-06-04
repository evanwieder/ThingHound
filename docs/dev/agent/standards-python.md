# Python Standards — Agent Reference

Every rule here exists in `docs/dev/standards-python.md`. Update both files in the same commit when a rule changes.

---

1. Annotate every parameter, return type, and class attribute. No exceptions.
2. Use `X | None` not `Optional[X]`. Never import `Optional`.
3. Use `X | Y` not `Union[X, Y]`. Never import `Union`.
4. Use built-in `list`, `dict`, `set` not `List`, `Dict`, `Set` from `typing`.
5. Avoid `Any`. When unavoidable, add a comment explaining why.
6. Google-style docstrings on every module, class, function, and method.
7. Module docstring: one line, before imports.
8. Function docstring: summary line, then `Args:`, `Returns:`, `Raises:` (omit empty sections).
9. One class per file. Name the file `snake_case` of the class name.
10. Domain entities: `pydantic.BaseModel` with `model_config = ConfigDict(frozen=True)`.
11. Value objects: `@dataclass(frozen=True)`.
12. No bare `except:` or `except Exception:`. Catch specific exceptions.
13. No mutable default arguments.
14. Line length: 100 characters.
15. Do not use `from __future__ import annotations`. Python 3.14 evaluates annotations lazily by default (PEP 649); the import is redundant and must not appear in any file.
