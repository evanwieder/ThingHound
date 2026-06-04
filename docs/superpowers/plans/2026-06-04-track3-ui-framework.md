# Track 3 — UI Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development for post-gate units; superpowers:frontend-design where available. Runs **in parallel with Track 1** — it codes against the **bridge contract** (`functional-spec.md §6`), not a live database. The first deliverable is a **main-page demo on dummy data**, a **hard gate (Gate D)**: no further UI work until the user approves. Begin coding only with explicit user authorization. Checkbox (`- [ ]`) steps track progress.

**Authoritative sources:** `docs/specs/thinghound-functional-spec.md` (§4 UI, §6 bridge), `docs/specs/thinghound-architecture.md` (§2 stack, §3 runtime, §7 security). Where this plan and a doc disagree, the doc wins.

**Goal:** Stand up the PyWebView + Tabulator desktop shell and deliver a data-dense main-page demo (three-pane layout, heterogeneous grid with dynamic Display Columns, category tree, inspector, filter strip) from dummy data — the touchstone that validates direction before UI investment scales.

**Architecture:** OS-native webview (PyWebView, no bundled Chromium) over a JS bridge (no TCP). Frontend is Tabulator-driven, virtualized, compact. The bridge is the only Python↔JS seam; the demo uses a **mock bridge** returning fixtures shaped exactly like the real §6 responses, so the Gate-B swap to real services is a drop-in.

**Tech stack:** PyWebView, Tabulator (MIT), vanilla JS/TS + a light build step (esbuild or Vite), HTML/CSS. No heavy SPA framework — density and Tabulator control come first.

---

## 1. Why This Track Parallelizes Now

The UI depends on the **shape** of bridge responses, not real data. `functional-spec.md §6` defines that shape (`grid.queryItems -> {rows,total}`, `grid.getDisplayColumns`, `grid.getColumnMappings`, `schema.getResolvedSchema`, `inventory.getBalances`, …). Contract invariants the mock must honor:
- Every scaled value crosses the bridge **with its `value_exact`/display form** — the UI never does float math.
- Every UUID crosses as a canonical `8-4-4-4-12` string.
- Errors are typed envelopes `{code, message, field?, details?}` (`architecture.md §7`).

The bridge is a **transport boundary**: it converts UUID strings ↔ ids and shapes envelopes, then delegates to services (which call mappers). It does **no database row↔model conversion** itself. When Track 2 reaches Gate B, the mock is replaced by the real bridge binding with zero frontend change.

---

## 2. Task A — PyWebView Shell + Bridge Stub

**Files:** `src/thinghound/ui/app.py`, `src/thinghound/ui/bridge.py`, `tests/ui/test_bridge_contract.py`.

- [ ] **Step 1: branch** `feat/track3-ui` (parallel to Track 1).
- [ ] **Step 2: failing contract tests** — `Bridge().error("INVALID_UUID","bad","field"="item_id")` returns the typed envelope; `Bridge(mock=True).grid_query_items(...)` returns `{"rows": [...], "total": int}`.
- [ ] **Step 3: implement** `Bridge`: methods mirroring the §6 surface; each wraps results so service exceptions become typed envelopes and unhandled ones become `INTERNAL_ERROR` (no raw tracebacks to JS, `architecture.md §7`). In `mock=True` it reads from the fixtures module (Task C) instead of services. `app.py` creates `webview.create_window(...)` bound to a `Bridge`; a `--mock` flag selects mock mode.
- [ ] **Step 4: run → pass; commit** `feat(ui): PyWebView shell + typed bridge stub`.

---

## 3. Task B — Frontend Scaffold + Main Layout

**Files:** `ui/index.html`, `ui/src/{main,layout,grid,tree,inspector,filterstrip}.js`, `ui/styles/*.css`, build config.

Implements the `functional-spec.md §4.1` layout: global toolbar (top, always visible) · left pane (category tree) · centre pane (grid above, filter strip below; dominant, always visible) · right pane (inspector) · status bar (bottom, always visible).

- [ ] **Step 1: build tooling** — esbuild/Vite bundles `ui/src` → `ui/dist`; `app.py` points the webview at the built `index.html`.
- [ ] **Step 2: layout shell** — CSS-grid three panes + toolbar + status bar. **All sashes draggable**; left/right/filter-strip each **independently minimisable** to a thin restore bar at their edge (left/right/bottom); centre grid always fills remaining space, cannot minimise; sensible default percentages at startup (§4.1 pane sizing).
- [ ] **Step 3: Tabulator grid** (§4.4) — virtualized (no pagination), compact rows, thumbnail column first, dynamic columns built from `grid.getDisplayColumns()` + `grid.getColumnMappings()`, hero column pinned + bold, group-by category with collapsible in-grid section headers, row-click populates the inspector without navigation.
- [ ] **Step 4: category tree** (§4.1) — hierarchical, searchable; selecting a node filters the grid to that subtree.
- [ ] **Step 5: inspector** (§4.3) — top summary zone (name, SKU, mfr/PN, primary category, lifecycle, on-hand, thumbnail) always visible; bottom tabbed zone (Attributes, Stock & Events, Instances, Vendors, Alternates, BOM/Where-used, Simulation) populated from fixtures.
- [ ] **Step 6: filter strip** (§4.5) — quick-search bar (`/` focus), parametric filter chips (`attribute · operator · value+unit`), scope selector, configuration switcher.
- [ ] **Step 7: commit** `feat(ui): main layout shell`.

---

## 4. Task C — Main-Page Demo on Dummy Data (TOUCHSTONE — Gate D)

**Files:** `ui/src/fixtures.js` (or served by `bridge.py` mock mode): a realistic heterogeneous catalog — resistors, capacitors, a connector, a mechanical part — with Display Columns and **per-category column mappings** so the grid renders a genuinely mixed grid aligned under shared columns. Values carry `value_exact`/display strings (no floats); a hero column (e.g. Resistance in a resistor view); on-hand quantities; a couple of thumbnails.

- [ ] **Step 1:** author fixtures shaped **exactly** like §6 responses. Heterogeneity is the point: a resistor fills the hero column from Resistance, a capacitor from Capacitance, a mechanical part leaves it blank — all under the same global Display Columns.
- [ ] **Step 2:** wire the demo through the **mock bridge** so the data path equals production (`window.pywebview.api.grid_query_items(...)` → mock → fixtures).
- [ ] **Step 3:** run `python -m thinghound.ui.app --mock`; confirm full layout renders, grid is dense + heterogeneous, tree filtering works, row-click fills the inspector, filter chips render, panes resize/minimise.
- [ ] **Step 4:** capture a screenshot (via the `run`/`verify` skill) and present it.

- [ ] **GATE D — STOP.** Present the demo. **Do not start any post-gate unit until the user explicitly approves the direction.** Absorb any layout/density/interaction revisions first.
- [ ] **Step 5 (after approval):** commit `feat(ui): main-page demo on dummy data (touchstone)`.

---

## 5. Post-Gate UI Units (parallel, only after Gate D approval)

Listed, not detailed, until approved — detail is written at dispatch time to reflect any Gate-D revisions. Each follows the unit template (one subagent + review).

| Unit | Spec | Notes |
|------|------|-------|
| Add-Item Wizard | §4.2, §5.1 | Category→Mfr/Series→Attributes (compound `[mag][unit▼]`, composite sub-forms)→Identity→Initial Stock; required-field enforcement |
| Inspector tabs (live) | §4.3 | wire each tab to its real bridge method as the backing Phase-1b unit lands |
| Parametric filter chips (live) | §4.5, §3.14 | unit/fraction-aware chip editor; AND/OR groups; routes to `grid.queryItems` |
| Inline grid editing | §4.4 | typed editors (unit spinners w/ per-attribute prefix range, enum dropdowns); multi-select bulk + undo/redo |
| BOM & Build workspace | §4.6 | lines, substitutes, shortage view, build action |
| Procurement workspace | §4.7 | buy-list grouped by vendor, MOQ-aware, export |
| Invoice / BOM import | §4.8 | drag-drop, column mapping, reconcile grid, commit summary |
| Measurement entry | §4.9 | instance measurement form; nominal alongside; out-of-tolerance indicator |
| Onboarding & empty state | §4.10 | seed-pack picker, PartKeepr import, guided first part |
| Validation / a11y / i18n | §4.11 | inline validation; keyboard-first; locale-aware parsing; conflict-queue UI (Phase 4) |

---

## 6. Integration with Track 2

- **Gate B:** replace the mock bridge with the real `Bridge` bound to live services; frontend unchanged because fixtures matched §6. The demo becomes the real main page.
- Each post-gate unit goes live when its backing Phase-1b unit reaches Gate C; until then it renders against mock data behind the same bridge methods.

---

## 7. Self-Review (against the spec)

- **Layout coverage:** §4.1 (three panes + toolbar + status bar + resize/minimise), §4.3 (two-zone inspector + seven tabs), §4.4 (Tabulator: thumbnail col, dynamic columns, hero pinned/bold, grouping, virtualization, row-click inspector), §4.5 (quick-search + chips + scope + config switcher).
- **Contract fidelity:** every mock response matches a §6 signature; scaled values carry `value_exact`; UUIDs are canonical strings; errors are typed envelopes → Gate-B swap is drop-in.
- **Boundary:** the bridge converts UUID strings and shapes envelopes (transport boundary) and delegates to services; it performs no database row↔model conversion. The UI displays server-provided `value_exact`/display strings and never computes on raw scaled integers.
- **Gate discipline:** Task C ends with an explicit STOP; no post-gate unit is detailed or started before user approval.
