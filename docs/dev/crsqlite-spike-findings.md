# cr-sqlite Compatibility Spike Findings

Status: completed with an environment caveat.

## Pinned extension

- Version: `v0.16.3`
- Release: https://github.com/vlcn-io/cr-sqlite/releases/tag/v0.16.3
- Linux x86_64 asset: https://github.com/vlcn-io/cr-sqlite/releases/download/v0.16.3/crsqlite-linux-x86_64.zip
- Downloaded location: `.local/crsqlite/crsqlite-linux-x86_64-v0.16.3.zip`
- ZIP SHA-256: `8f6fd31a2be2ba8c3101aad067a504a2e63c8e9b51cc4ace786009c02e7ecbae`
- Extracted loadable extension: `.local/crsqlite/crsqlite.so`
- Extension binary was obtained in this environment but is intentionally left
  untracked.

## Smoke script

Run from the repo root:

```bash
python scripts/crsqlite_spike.py ./.local/crsqlite/crsqlite
```

Expected output:

```text
merged items: [('C-1',), ('R-1',)]
OK: crsql_as_crr + changeset merge succeeded
```

## Findings

- The requested Python command was run:
  `python scripts/crsqlite_spike.py ./.local/crsqlite/crsqlite`.
- This environment's Python `sqlite3` module is built without extension loading:
  `sqlite3.Connection` has no `enable_load_extension` attribute. The local
  `sqlite3` CLI is also unavailable.
- The same downloaded extension was loaded successfully through the SQLite C API
  in `libsqlite3.so`, so the compatibility checks below are based on the pinned
  binary rather than only documentation.
- The CHECK-shape and alter results came from separate manual C API diagnostics;
  the checked-in Python script remains the gated merge smoke.
- `BLOB PRIMARY KEY NOT NULL` is accepted by `crsql_as_crr`.
- Non-primary-key `NOT NULL` columns must have a `DEFAULT`. Without defaults,
  `crsql_as_crr('items')` rejected `sku TEXT NOT NULL` with:
  `Table items has a NOT NULL column without a DEFAULT VALUE.`
- `value_scaled INTEGER` and `value_exact TEXT` are accepted and merged
  correctly when there is no cross-column `CHECK` tying them together.
- A nullable `deleted_at TEXT` tombstone column is accepted.
- A single-column tombstone check, `deleted_at TEXT CHECK (deleted_at IS NULL OR
  length(deleted_at) > 0)`, is accepted.
- Cross-column `CHECK` constraints are not compatible with column-wise
  changeset application. A test check of
  `CHECK (value_scaled IS NULL OR value_exact IS NOT NULL)` allowed
  `crsql_as_crr`, but applying a remote changeset failed because the
  `value_scaled` column change can arrive before `value_exact`. This matches the
  upstream constraint guidance that CRRs may not have check constraints that
  depend on columns other than the defined column.
- The exact `crsql_changes` projection used by the pinned version is:
  `"table", pk, cid, val, col_version, db_version, site_id, cl, seq`.
- The smoke merge with defaulted `NOT NULL` columns and no cross-column checks
  produced:

```text
changes columns: ['table', 'pk', 'cid', 'val', 'col_version', 'db_version', 'site_id', 'cl', 'seq']
changes row count: 5
merged items: ['C-1', 'R-1']
alter add column: OK
```

- `crsql_begin_alter` / `crsql_commit_alter` ergonomics are straightforward for
  supported table alterations:

```sql
SELECT crsql_begin_alter('items');
ALTER TABLE item ADD COLUMN notes TEXT;
SELECT crsql_commit_alter('items');
```

  The add-column alteration succeeded against an existing CRR. Upstream docs say
  begin/commit calls may be nested and may occur in an outer transaction; if an
  alteration fails, transactions and savepoints are rolled back. Supported
  schema alterations are add columns, drop columns, rename columns, and index
  changes; table rename is still a work in progress.

## Gated manual checklist

Because this Python build cannot load extensions, rerun the checked-in script on
a Python build with SQLite extension loading enabled before wiring this into
application code:

```bash
python scripts/crsqlite_spike.py ./.local/crsqlite/crsqlite
```

Expected output:

```text
merged items: [('C-1',), ('R-1',)]
OK: crsql_as_crr + changeset merge succeeded
```

## Decision

No-go on the unmodified schema shape. Required adjustments:

- Add explicit defaults to every non-primary-key `NOT NULL` column on CRR tables,
  or make those columns nullable and enforce required values in application code.
- Do not put cross-column `CHECK` constraints on CRR tables. Enforce invariants
  such as `(value_scaled IS NULL) = (value_exact IS NULL)`, MPN/manufacturer
  coupling, and inventory event type/sign coupling in application code and/or
  post-merge integrity checks.
- Single-column `CHECK` constraints appear acceptable, but keep them conservative
  because remote column changes apply independently.

Go after the listed schema adjustments are applied; enablement remains deferred
to the sync plan.
