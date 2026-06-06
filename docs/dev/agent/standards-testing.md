# Testing Standards — Agent Reference

Every rule here exists in `docs/dev/standards-testing.md`. Update both files in the same commit when a rule changes.

---

1. Write tests before implementation (TDD). Never implement without a failing test.
2. Integration tests use a real in-memory libSQL/SQLite database. Never mock the database layer.
3. Use the `conn` fixture from `conftest.py`. Tests do not call `migrate()` themselves.
4. One behavior per test. One assertion focus per test function.
5. Test names describe the behavior being verified, not the method. Example: `test_deleted_dimension_excluded_from_list`.
6. No shared mutable state between tests. Each test receives a fresh database connection.
7. Every aggregate mapper has: round-trip tests, batch-form tests, and soft-delete tests.
8. Every migration has a test confirming it applies cleanly to a fresh database.
9. Every business rule in the functional spec §5 has at least one direct test.
10. Read-model tests verify correctness independent of aggregation timing: snapshot + tail fold equals a full fold; current value correct when aggregation never ran; compaction does not change reads.
