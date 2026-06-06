# Testing Standards

**Compact agent version:** `docs/dev/agent/standards-testing.md`

---

## Test-Driven Development

Tests are written before implementation. The sequence is:

1. Write a failing test that specifies the desired behavior.
2. Write the minimum implementation to make it pass.
3. Refactor under the green test.

Starting implementation before a test exists is a process violation. If a behavior is untested, it is not considered implemented.

---

## Real Database, No Mocking

Integration tests hit a real SQLite database. The database layer is never mocked.

**Why:** mocking the database validates that mock behavior matches expected behavior, not that the actual SQL is correct. Schema migrations, SQL semantics, FTS5 behavior, foreign-key enforcement, and trigger logic cannot be verified against a mock. Past experience has shown that mock/production divergence masks real bugs silently.

```python
# Correct — real in-memory database
@pytest.fixture
def conn():
    c = connect(":memory:")
    migrate(c)
    return c

# Wrong — mocked connection
@pytest.fixture
def conn():
    return MagicMock(spec=sqlite3.Connection)
```

---

## Fixture Structure

**`conftest.py`** provides:
- `conn` — a configured in-memory connection with all migrations applied.
- `migrated_conn` (alias) — the same fixture, used in migration-specific tests where the name matters.
- Seed data fixtures (e.g., `electrical_category`, `resistance_dimension`) built on top of `conn`.

Tests do not run migrations themselves. A test that calls `migrate()` directly is testing the migration runner, not the domain. For domain tests, use the `conn` fixture.

---

## One Behavior Per Test

Each test has a single assertion focus. A test named `test_deleted_dimension_excluded_from_list` checks exactly that and nothing else. Testing multiple behaviors in one test makes failures ambiguous.

```python
# Correct — one behavior
def test_deleted_dimension_excluded_from_list(conn):
    mapper = UnitDimensionMapper()
    dim = make_dimension(deleted_ts="2026-01-01T00:00:00Z")
    mapper.add(conn, dim)
    result = mapper.list_active(conn)
    assert dim.id not in [d.id for d in result]

# Wrong — multiple unrelated behaviors
def test_dimension_crud(conn):
    # tests add, get, list, soft-delete all in one test
    ...
```

---

## Behavior-Named Tests

Test names describe the behavior being verified, not the implementation or the method being called.

```
# Correct — describes what the system does
test_deleted_dimension_excluded_from_list
test_scale_change_recomputes_value_scaled_from_value_exact
test_individuate_event_nets_to_zero
test_stock_correct_when_aggregation_never_ran

# Wrong — describes implementation
test_list_dimensions
test_mapper_get_returns_none
test_execute_query
```

---

## No Shared Mutable State

Tests must not share mutable state. Every test receives a fresh database connection from the fixture. A test that modifies data must not affect another test's expectations.

Each test function is independent. The fixture provides isolation; tests must not rely on execution order.

---

## Migration Tests

Every migration must be tested by:
1. Applying all migrations to a fresh in-memory database and verifying the final schema.
2. Verifying the migration's checksum is stable (modifying an applied migration is an error).

---

## Read-Model Correctness Tests

The read model keeps a materialized snapshot up to a watermark and folds the event tail past it on every read. Tests must verify that the read result is correct regardless of when aggregation last ran.

Key scenarios to cover:
- Stock read with events past the watermark equals a full fold from scratch (consistency oracle).
- Current value is correct when aggregation has never run (snapshot empty, all events in the tail).
- Advancing the watermark (compaction) does not change any read result.
- Measurements with equal or skewed `measured_ts` resolve to a stable current value by `(measured_ts, hlc, uuid)`.

---

## Test Coverage Expectations

Every aggregate mapper has:
- Round-trip tests (add → get → compare model equality).
- Batch-form tests (`add_batch` → `list_active` → compare).
- Soft-delete tests (deleted rows excluded from active lists).

Every business rule in `docs/specs/thinghound-functional-spec.md` §5 has at least one test that exercises it directly.

Every migration has a test confirming it applies cleanly to a fresh database.
