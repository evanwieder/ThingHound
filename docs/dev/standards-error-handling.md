# Error Handling Standards

**Compact agent version:** `docs/dev/agent/standards-error-handling.md`

---

## Catch Specific Exceptions

Never use bare `except:` or `except Exception:`. Catch the most specific exception type that makes sense.

```python
# Correct — specific exception
try:
    conn.execute(self._INSERT, params)
except sqlite3.IntegrityError as exc:
    raise DuplicateSkuError(sku) from exc

# Wrong — catches everything including KeyboardInterrupt, SystemExit
try:
    conn.execute(self._INSERT, params)
except:
    pass

# Wrong — too broad, swallows programming errors
try:
    result = self._parse_value(raw)
except Exception:
    return None
```

---

## No Swallowing

Errors are not swallowed with a log line and a fallback return. If an error occurs and the caller cannot handle it, it propagates.

```python
# Correct — propagates
def encode_scaled(base: Fraction, scale: int) -> tuple[int, str]:
    value_scaled = round(base * 10**scale)
    if abs(value_scaled) > INT64_MAX:
        raise OverflowError(f"{base} at scale {scale} exceeds signed int64")
    ...

# Wrong — swallows a real error condition
def encode_scaled(base: Fraction, scale: int) -> tuple[int, str] | None:
    try:
        value_scaled = round(base * 10**scale)
        ...
    except Exception:
        return None   # caller can't tell what went wrong
```

---

## Validate at System Boundaries

Validation of untrusted data happens at entry points: the JS bridge, file imports (CSV, PDF, BOM), and external API responses. Internal code trusts its inputs.

Do not add defensive checks inside internal functions for conditions that cannot arise given correct callers. Trust the domain model (validated at construction) and framework guarantees.

```python
# Correct — validation at the bridge boundary
def handle_set_value(self, item_id: str, attribute_id: str, raw: str) -> dict:
    # raw is user input — validate here
    try:
        item_uuid = from_canonical(item_id)
        attr_uuid = from_canonical(attribute_id)
    except ValueError:
        return error_response("INVALID_UUID", "item_id or attribute_id is not a valid UUID")
    normalized = self._value_service.normalize(raw, attribute_id=attr_uuid)
    ...

# Wrong — defensive check inside internal function that trusts callers
def _dimension_from_row(self, row: sqlite3.Row) -> UnitDimension:
    if row is None:                  # callers should not pass None
        return None                  # this masks a programming error
    return UnitDimension(id=row["id"], ...)
```

---

## Typed Domain Errors

Domain-specific error conditions are typed exceptions, not bare `ValueError` strings. This lets callers catch specific conditions without string matching.

```python
# Define domain errors in a dedicated module
class DuplicateSkuError(Exception):
    def __init__(self, sku: str) -> None:
        super().__init__(f"SKU already exists: {sku!r}")
        self.sku = sku

class ScaleOverflowError(Exception):
    def __init__(self, value: Fraction, scale: int) -> None:
        super().__init__(f"{value} at scale {scale} exceeds signed int64")
        self.value = value
        self.scale = scale

class UnknownUnitError(Exception):
    def __init__(self, symbol: str, dimension: str) -> None:
        super().__init__(f"Unknown unit {symbol!r} for dimension {dimension!r}")
        self.symbol = symbol
        self.dimension = dimension
```

---

## Re-Raise with Context

When catching a low-level exception and raising a domain error, use `from` to preserve the original traceback.

```python
# Correct — original traceback preserved
try:
    conn.execute(self._INSERT, params)
except sqlite3.IntegrityError as exc:
    raise DuplicateSkuError(sku) from exc

# Acceptable — explicit suppression (rare; must be intentional)
try:
    uuid_bytes = from_canonical(raw_id)
except ValueError:
    raise InvalidRequestError("invalid UUID") from None

# Wrong — loses original traceback
try:
    conn.execute(self._INSERT, params)
except sqlite3.IntegrityError:
    raise DuplicateSkuError(sku)
```

---

## Error Responses at the Bridge

The JS bridge returns a typed error envelope for all failures:

```python
{"code": "DUPLICATE_SKU", "message": "SKU already exists: 'R-001'", "field": "sku"}
```

Service-layer exceptions are caught at the bridge handler and converted to error envelopes. Unhandled exceptions at the bridge log the full traceback and return a generic `INTERNAL_ERROR` envelope — they never surface raw Python tracebacks to the JavaScript layer.
