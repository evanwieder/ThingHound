# CRR Rules for Synced Tables

Synced tables (shared across devices) must follow CRR (Conflict-free Replicated Rows) rules to ensure safe multi-device synchronization.

## Requirements

All synced tables **must**:

1. **Have a PRIMARY KEY** — preferably `BLOB(16)` for UUIDs or `TEXT` for natural keys. Required for merge correctness.

2. **Use BLOB for ID columns** — avoids integer collision across devices.

3. **Disable foreign key enforcement** — cr-sqlite does not enforce `REFERENCES` constraints in the sync layer. Either use a comment column or drop the constraint entirely.

4. **Prohibit AUTOINCREMENT** — auto-incrementing IDs are device-local and cannot be safely merged.

5. **Prohibit REAL columns** — floating-point values lose precision in JSON serialization during sync. Use `TEXT` (for formatted numbers) or `INTEGER` (for scaled integers) instead.

## Soft Deletes & Attribution

Recommended patterns:

- **Soft deletes**: Add `deleted_at TEXT` column (NULL = not deleted, ISO 8601 timestamp = deleted).
- **Attribution**: Add columns like `created_by TEXT`, `updated_by TEXT`, `updated_at TEXT` to track change history.

## Exempting Device-Local Tables

Tables that are **not synced** (e.g., cache, temporary views, derived data) can be exempted by adding a `-- sync: LOCAL` comment immediately before the `CREATE TABLE` statement:

```sql
-- sync: LOCAL
CREATE TABLE rm_item_grid (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id BLOB REFERENCES item(id),
  v REAL
);
```

Device-local tables are not subject to CRR rules.

## Example: Compliant Synced Table

```sql
CREATE TABLE unit_dimension (
  id BLOB(16) PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  scale INTEGER NOT NULL,
  created_at TEXT,
  updated_at TEXT,
  deleted_at TEXT
);
```

## Verification

The `scripts/check_crr_rules.py` static checker scans all migration files and fails the build if any synced table violates these rules.
