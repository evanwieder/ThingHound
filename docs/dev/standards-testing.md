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

**Why:** mocking the database validates that mock behavior matches expected behavior, not that the actual SQL is correct. Schema migrations, SQL semantics, FTS5 behavior, cr-sqlite constraints, and trigger logic cannot be verified against a mock. Past experience has shown that mock/production divergence masks real bugs silently.

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
    dim = make_dimension(deleted_at="2026-01-01T00:00:00Z")
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
test_two_offline_skus_quarantined_after_merge

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
3. The CRR-rules CI guard verifying no cr-sqlite compatibility violations exist in the migration SQL.

---

## Sync and Merge Tests

Sync-correctness tests create two in-memory databases, apply operations to each independently, exchange cr-sqlite changesets, and verify the merged state satisfies all invariants. These tests are the authoritative verification that CRDT conflict policies are correct.

Key scenarios to cover:
- Two devices create the same SKU offline → post-merge quarantine fires.
- Concurrent edits to the same item attribute → LWW resolves deterministically.
- Partial INDIVIDUATE group delivered in two sync rounds → integrity check tolerates, then passes once complete.
- Post-merge read-model rebuild produces results identical to trigger-maintained state.

---

## Test Coverage Expectations

Every aggregate mapper has:
- Round-trip tests (add → get → compare model equality).
- Batch-form tests (`add_batch` → `list_active` → compare).
- Soft-delete tests (deleted rows excluded from active lists).

Every business rule in `docs/specs/thinghound-functional-spec.md` §5 has at least one test that exercises it directly.

Every migration has a test confirming it applies cleanly to a fresh database.
