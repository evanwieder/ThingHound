# Error Handling Standards — Agent Reference

Every rule here exists in `docs/dev/standards-error-handling.md`. Update both files in the same commit when a rule changes.

---

1. Never use bare `except:` or `except Exception:`. Catch the most specific exception type.
2. Never swallow errors with a log line and a fallback return. Let them propagate.
3. Validate untrusted data at system boundaries only: the JS bridge, file imports, external API responses.
4. Internal functions trust their inputs. Do not add defensive checks for conditions that cannot arise given correct callers.
5. Domain-specific errors are typed exceptions (e.g., `DuplicateSkuError`, `ScaleOverflowError`). Never a bare `ValueError` string.
6. Re-raise with `from exc` to preserve the original traceback. Use `from None` only when explicitly suppressing.
7. Bridge handlers catch service-layer exceptions and convert them to typed error envelopes `{code, message, field?}`. Raw tracebacks never reach the JS layer.
