# ThingHound — UI Design

**Date:** 2026-06-05
**Companion documents:** `thinghound-functional-spec.md`, `thinghound-data-model.md`, `thinghound-architecture.md`, `docs/superpowers/specs/2026-06-04-compact-workspace-density-design.md`

This document is the **frontend reference for the desktop workspace** — the three-pane shell, design tokens, theme system, component contract, and the bridge that connects the JS frontend to the Python service layer. It is the entry point for any future UI work; the design doc above is the why, this is the how.

---

## 1. Scope

In scope:

- The three-pane workspace shell (left tree, center grid + filter, right inspector)
- The global chrome (toolbar, status bar, sashes, pane collapse)
- The light/dark theme system
- The JS↔Python bridge contract
- The build pipeline that produces `ui/dist/`
- The test infrastructure for the JS layer

Out of scope (lives in other docs):

- Functional requirements and per-screen workflows → `thinghound-functional-spec.md`
- Data model for the entities the UI displays → `thinghound-data-model.md`
- Persistence, mappers, query assembly → `thinghound-architecture.md`
- Why the workspace is dense in the first place → `docs/superpowers/specs/2026-06-04-compact-workspace-density-design.md`

This is **explicitly a first pass for a demo** — the design doc is clear that this is not a long-term product visual identity. The goal is to make the current UI convincingly usable for demonstration without expanding scope into broader product redesign or data-layer changes.

---

## 2. Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Desktop shell | PyWebView (OS-native webview) | Avoids bundling Chromium. WebKitGTK on Linux is the packaging risk. |
| UI transport | PyWebView JS bridge only | No localhost TCP surface. |
| Frontend grid | Tabulator 6.3.0 (MIT) | Native grouping, virtual DOM, column reorder, inline editors. |
| Module system | ESM (esbuild bundle) | One entry (`ui/src/main.js`) bundled to `ui/dist/main.js`. |
| Styling | Hand-written CSS, tokenized via custom properties | Source of truth is `ui/styles.css`; copied verbatim into `ui/dist/` by the build. |
| Theme persistence | `localStorage` key `thinghound.theme` | `dark` / `light` / unset (system follows). |
| Fonts | System UI stack | `-apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", system-ui, sans-serif` for the app; `ui-monospace` family for monospace (reserved for future). |

No frontend framework, no JSX, no virtual DOM library beyond Tabulator. Vanilla DOM and CSS. The whole JS layer is ≈ 1,200 lines.

---

## 3. File Structure

```
ui/
├── index.html                Static shell — panes, sashes, restore bars, tab targets
├── styles.css                Source of truth for tokens and component styling (tracked)
├── src/                      ESM source, bundled to dist by esbuild
│   ├── main.js               Entry: theme init, layout init, pane initializers
│   ├── bridge-api.js         JS↔Python bridge wrapper; falls back to JS fixtures if bridge absent
│   ├── fixtures.js           JS-side fixture data mirroring src/thinghound/ui/fixtures.py
│   ├── theme.js              Theme controller (system / override / toggle)
│   ├── layout.js             Sash drag, pane collapse, restore bars
│   ├── tree.js               Tree state, renderTreeToolbar, renderTreeList
│   ├── grid.js               Tabulator wrapper, renderGridToolbar, column builders
│   ├── filterstrip.js        Compact labeled filter controls
│   └── inspector.js          Header + property-panel + tabs
└── dist/                     Build artifacts (gitignored)
    ├── index.html            Copied from ui/index.html
    ├── styles.css            Copied from ui/styles.css
    ├── main.js               Bundled by esbuild
    └── main.js.map           Source map
```

```
src/thinghound/ui/
├── app.py                    `python -m thinghound.ui.app [--mock]` — PyWebView entry
├── bridge.py                 Bridge class exposed to JS as `window.pywebview.api`
└── fixtures.py               Mock fixtures for `--mock` mode and tests
```

```
tests/ui/
└── test_bridge_contract.py   Python tests against the bridge fixture contracts
```

---

## 4. Build Pipeline

`package.json` scripts:

```json
{
  "build": "esbuild ui/src/main.js --bundle --outfile=ui/dist/main.js --sourcemap && cp ui/index.html ui/dist/index.html && cp ui/styles.css ui/dist/styles.css",
  "dev":   "esbuild ui/src/main.js --bundle --outfile=ui/dist/main.js --sourcemap --watch"
}
```

The build does three things, in order:

1. Bundle the ESM source starting at `ui/src/main.js` into `ui/dist/main.js` (with a source map for debugging).
2. Copy `ui/index.html` → `ui/dist/index.html` (the static shell is not transformed).
3. Copy `ui/styles.css` → `ui/dist/styles.css` (the source stylesheet is the design source of truth — never edit `ui/dist/`).

`ui/dist/` is gitignored. Generated output should be treated as build artifacts, not as the design source of truth.

PyWebView loads `ui/dist/index.html` as the entrypoint. The URL is resolved in `src/thinghound/ui/app.py` via `Path(__file__).resolve().parents[3] / "ui" / "dist" / "index.html"`.

To run the demo:

```bash
npm run build
PYTHONPATH=src .venv/bin/python -m thinghound.ui.app --mock
```

---

## 5. Layout & Sizing

The workspace is a CSS Grid with three rows (`var(--toolbar-height)` / `1fr` / `var(--status-height)`) and three panes inside the middle row. Widths and heights are driven entirely by CSS custom properties so the layout can be re-themed or re-sized without touching JS.

### Sizing tokens

| Token | Value | Use |
|-------|-------|-----|
| `--toolbar-height` | `30px` | Global toolbar height |
| `--pane-header-height` | `22px` | Pane tab-style header height |
| `--pane-toolbar-height` | `24px` | Pane-local toolbar height |
| `--filter-height` | `96px` | Filter strip default height |
| `--status-height` | `22px` | Status bar height |
| `--left-width` | `240px` | Default tree pane width |
| `--right-width` | `320px` | Default inspector pane width |
| `--sash-size` | `4px` | Sash / divider width |
| `--row-height` | `22px` | Tabulator row height |
| `--cell-pad-x` / `--cell-pad-y` | `6px` / `2px` | Tabulator cell padding |
| `--data-font-size` | `11px` | The single shared compact data text size |
| `--data-line-height` | `1.3` | Shared line height for data text |
| `--inspector-title-size` | `16px` | Selected-item title in inspector |
| `--inspector-subtitle-size` | `12px` | Subtitle below the title |

All sizes are integer px — no rem/em magic that would scale unexpectedly when the user changes browser zoom. The compact data text size is **11px** deliberately, to make the grid dense without making it unreadable.

### Layout chrome

```
┌─────────────────────────────────────────────────────────────────┐
│ toolbar-global    30px   brand · global actions · theme toggle │
├──────┬──┬─────────────────────────────┬──┬───────────────────────┤
│ pane │  │ pane-header      22px                            │  │ pane- │  │
│ left │  │ pane-toolbar     24px                            │  │ right │  │
│ 240  │  │ ┌─────────────────────────┐ ┌──┬─────────────┐  │  │ 320   │  │
│      │  │ │ grid-region (flex 1)    │ │  │ filter-     │  │  │       │  │
│      │  │ │                         │ │  │ region      │  │  │       │  │
│      │  │ └─────────────────────────┘ └──┴─────────────┘  │  │       │  │
└──────┴──┴─────────────────────────────┴──┴───────────────────────┘
│ status-bar  22px                                              │
```

The center pane is itself a grid with five rows: `pane-header / pane-toolbar / grid / sash / filter`. Pane widths and the filter height are persisted as inline custom properties on the workspace/center-pane elements, so dragging a sash updates only the relevant custom property.

### Sash drag and pane collapse

`ui/src/layout.js` wires three interactions:

- **Left/right horizontal sashes** (`.sash-left`, `.sash-right`): pointer-drag updates `--left-width` / `--right-width` on the workspace.
- **Bottom sash** (`.sash-bottom` in the center pane): pointer-drag updates `--filter-height` on the center pane.
- **Double-click on a pane header** (or its sash): collapses the pane to zero width, then shows a tiny restore button (`.restore-bar`) at the edge of the workspace.

`notifyLayoutChanged()` dispatches both `resize` and `layout:changed` so the grid can redraw. The `grid:filter` event is dispatched on tree-row selection; `layout:changed` triggers a `bridgeApi.grid_query_items({})` re-fetch.

Constants in `layout.js`:

| Constant | Value | Purpose |
|----------|-------|---------|
| `MIN_LEFT` / `MIN_RIGHT` | `36px` | Minimum width a pane can be dragged to |
| `MIN_CENTER` | `320px` | Minimum center pane width; if violated, the right pane is shrunk |
| `MIN_FILTER` | `28px` | Minimum filter strip height (just the header) |
| `DEFAULT_LEFT_WIDTH` / `DEFAULT_RIGHT_WIDTH` / `DEFAULT_FILTER_HEIGHT` | `240` / `320` / `160` | Restore-bar target sizes |

---

## 6. Design Tokens

All colors are CSS custom properties, namespaced by role. Two themes exist as `[data-theme="dark"]` and `[data-theme="light"]` blocks in `ui/styles.css`. The dark theme is the default; the light theme is more colored (closer to the PartKeepr reference) than a typical "inverted dark" would be.

### Spacing / typography / structural

```css
:root {
  --data-font-size: 11px;
  --data-line-height: 1.3;
  --row-height: 22px;
  --cell-pad-x: 6px;
  --cell-pad-y: 2px;
  --toolbar-height: 30px;
  --pane-toolbar-height: 24px;
  --pane-header-height: 22px;
  --filter-height: 96px;
  --left-width: 240px;
  --right-width: 320px;
  --sash-size: 4px;
  --status-height: 22px;

  --inspector-title-size: 16px;
  --inspector-subtitle-size: 12px;

  --font-stack: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", system-ui, sans-serif;
  --mono-stack: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}
```

These never change between themes. The shared **data text** is the single 11px scale used in: grid cells, grid headers, tree rows, filter controls, inspector labels and values, toolbar buttons, and pane-local labels. Pane/frame headers and the inspector title/subtitle are intentionally larger (12–16px) to preserve orientation without breaking the dense rhythm.

### Dark theme (default)

```css
[data-theme="dark"] {
  --bg:        #0c1219;   /* window background */
  --bg-2:      #0a0e15;   /* sash / divider area */
  --panel:     #161e2a;   /* pane surface */
  --panel-2:   #1c2632;   /* secondary (toolbars, tab strips) */
  --panel-3:   #243042;   /* raised control surface */
  --line:      #2b3749;   /* primary borders */
  --line-2:    #38465c;   /* secondary borders */
  --text:      #e0e7f1;   /* primary text */
  --muted:     #8597b3;   /* secondary text */
  --accent:    #5a8ed6;   /* interactive accent */
  --accent-2:  #3d6cae;   /* hover/pressed accent */
  --accent-text: #ffffff; /* text on accent */
  --brand:     #2c4a73;   /* toolbar brand gradient start */
  --brand-2:   #1d365a;   /* toolbar brand gradient end */
  --selection: #274a78;   /* row/tab selection */
  --strip:     rgba(255, 255, 255, 0.03);  /* row striping */

  /* Tabulator-specific tokens (so we don't bleed midnight CSS) */
  --tabulator-bg:           #1a2230;
  --tabulator-header-bg:    #1f2935;
  --tabulator-row-bg:       #1a2230;
  --tabulator-row-strip-bg: #1f2935;
  --tabulator-border:       #2b3749;
  --tabulator-text:         #e0e7f1;
  --tabulator-group-bg:     transparent;
  --tabulator-group-border: #2b3749;
  --tabulator-row-hover:    #243042;
  --tabulator-selected:     #274a78;
}
```

### Light theme

```css
[data-theme="light"] {
  --bg:        #c4d2e3;   /* outer chrome — saturated blue-grey */
  --bg-2:      #aec2da;
  --panel:     #dee8f3;   /* pane surface */
  --panel-2:   #cfdcec;   /* secondary */
  --panel-3:   #ffffff;   /* content surface */
  --line:      #8aa2c2;
  --line-2:    #a4b6d2;
  --text:      #0f1e34;
  --muted:     #3f5575;
  --accent:    #2c5aa0;
  --accent-2:  #1e4485;
  --accent-text: #ffffff;
  --brand:     #2c5aa0;
  --brand-2:   #1e4485;
  --selection: #6c97cf;
  --strip:     rgba(0, 0, 0, 0.04);

  --tabulator-bg:           #ffffff;
  --tabulator-header-bg:    #d3deec;
  --tabulator-row-bg:       #ffffff;
  --tabulator-row-strip-bg: #ebf1f8;
  --tabulator-border:       #a4b6d2;
  --tabulator-text:         #0f1e34;
  --tabulator-group-bg:     transparent;
  --tabulator-group-border: #a4b6d2;
  --tabulator-row-hover:    #d8e3f1;
  --tabulator-selected:     #c0d4ee;
}
```

The light theme is **not** a desaturated grey inversion of dark — it's a saturated blue scheme intentionally closer to the PartKeepr reference. The earlier pale grey version was too washed out; this is the palette to keep.

### How tokens are used

| Token family | Use |
|--------------|-----|
| `--bg`, `--bg-2` | Outer window and sash dividers |
| `--panel`, `--panel-2`, `--panel-3` | Pane surfaces, raised controls, white content |
| `--line`, `--line-2` | Borders and dividers |
| `--text`, `--muted` | Primary and secondary text |
| `--accent`, `--accent-2`, `--accent-text` | Interactive controls (tabs, buttons, link colors) |
| `--brand`, `--brand-2` | Global toolbar gradient only |
| `--selection` | Selected row, selected tab, hovered tree row |
| `--strip` | Alternating row stripe (very low alpha) |
| `--tabulator-*` | Tabulator surface overrides — see §10 for why this set exists |

To re-skin, change the token values inside the `[data-theme="..."]` blocks. Do not override colors at component level.

---

## 7. Components

Every component class is namespaced and lives in `ui/styles.css`. New components should follow the existing conventions: a single-purpose class per element, no utility classes, no nesting deeper than one level.

### 7.1 Global toolbar — `.toolbar.toolbar-global`

The window-level chrome at the top. Always reserved for **global actions** that apply across the workspace. Holds the brand label on the left and a small set of icon-or-text buttons on the right.

- Height: `var(--toolbar-height)` (30px)
- Background: `linear-gradient(to bottom, var(--brand) 0%, var(--brand-2) 100%)`
- Color: `--accent-text` (white)
- Border-bottom: 1px solid `--brand-2`
- Brand: uppercase, letter-spaced
- Actions: `.toolbar-btn` with translucent white background

Current buttons: **Save View**, **Load View**, **Theme Toggle**. The toggle is wired in `main.js` to `createThemeController().toggle()` and its label flips between `Light Mode` and `Dark Mode` based on the active mode.

### 7.2 Status bar — `.status-bar`

The bottom row, 22px tall. Currently shows the literal text `Ready`; intended to surface async bridge status. Color: `--muted` on `--panel-2`.

### 7.3 Workspace and sashes — `.workspace`, `.sash`

The grid is `grid-template-columns: var(--left-width) var(--sash-size) minmax(320px, 1fr) var(--sash-size) var(--right-width)`. Sashes are 4px wide, fill their column with `--bg-2`, and turn `--accent` on hover. Cursor changes (`col-resize` / `row-resize`) signal draggability.

Restore bars (`.restore-bar`) are absolutely positioned thin buttons that appear at the edge of the workspace when a pane is collapsed. They use the `◀` `▶` `▲` characters as labels.

### 7.4 Pane header — `.pane-header`

A tab-style title bar at the top of each pane. Renders the pane name (e.g. `Categories`, `Parts List`, `Part Details`) in uppercase, bold, letter-spaced, on a vertical gradient (`--panel-2` to `--panel`). Right side (`.pane-header-actions`) is reserved for sub-view tabs (e.g. `Parts List` / `Thumbnail View`); currently unused.

This is the visual identifier for the pane — when collapsed, the restore bar replaces it.

### 7.5 Pane-local toolbar — `.pane-toolbar`

Below the pane header, 24px tall, on `--bg-2`. Compact low-noise row of action buttons and controls specific to that pane.

Three button styles live here:

| Class | Use |
|-------|-----|
| `.pane-toolbar-btn` | Text-only button (e.g. `Collapse All`, `Edit Item`) |
| `.pane-toolbar-select` | Labeled `<select>` (e.g. `View: Default`) |
| `.pane-toolbar-search` | Labeled `<input type="search">` (e.g. `Search: …`) |

**Toolbar is for pane-specific actions only.** Save/Load View, theme toggle, and other workspace-wide actions belong in the global toolbar. The split should be obvious from placement.

### 7.6 Tree pane (left) — `.tree-region`, `.tree-row`, `.tree-chevron`

The tree is rendered by `ui/src/tree.js`. State is held in a `TreeState` class with an `expanded: Set<string>` of node IDs and a `query: string` for filtering. Visible nodes are recomputed on every state change by walking the tree depth-first.

- `.tree-region` — scrollable container inside the pane body. Padding `4px 0`. Background `--panel`.
- `.tree-row` — one row per visible node. Display flex, gap 2px, padding `1px 6px 1px 0` plus `padding-left: calc(var(--tree-depth, 0) * 10px + 4px)` for indentation.
- `.tree-chevron` — small (12×14) chevron character (`▸` collapsed, `▾` open, or `·` for leaves). `stopPropagation` on the click so toggling doesn't trigger the row's filter action.
- `.tree-label` — flex-1 with ellipsis overflow.

Toolbar actions: **Collapse All**, **Expand All**, **Search**, **Edit**. The first two call into `TreeState`; search updates the filter query; Edit is a no-op stub that dispatches `tree:request-edit`.

Clicking a row body (not the chevron) emits an `onFilter` callback that `main.js` wires to a `grid:filter` event with `{ categoryId }`. The grid mock uses `category_path` membership for ancestor-aware filtering, so clicking `Semiconductors` returns all items in that subtree.

### 7.7 Grid pane (center) — `.grid-region` (Tabulator)

The grid is Tabulator. The JS in `ui/src/grid.js` wraps it with a small config object and a `renderGridToolbar` for the pane-local action bar. Tabulator's CSS (`tabulator_midnight.min.css`) is loaded from the unpkg CDN; our stylesheet overrides it with `!important` rules (see §10 for why).

Configuration notes (`buildGridOptions` in `ui/src/grid.js`):

| Option | Value | Why |
|--------|-------|-----|
| `layout` | `fitColumns` | Columns share width |
| `reactiveData` | `true` | Row data mutations propagate to the grid |
| `virtualDom` | `true` | Only renders visible rows; required for large catalogs |
| `movableColumns` | `true` | User can reorder columns |
| `rowHeight` | `22` | Matches `--row-height` |
| `columnHeaderVertAlign` | `middle` | Vertical center for tight 11px header |
| `groupBy` | `category_path_display` | Breadcrumb group headers, not leaf names |
| `groupHeader` | `(value, count) => "<span class='group-path'>…</span> <span class='group-count'>(N parts)</span>"` | Custom rendering with separate styling for the path vs the count |

**Columns are built by `buildColumns(displayColumns)`.** The first column is always a 36px-wide blank-title thumbnail (no header text per the design). The `stock` column is right-aligned and rendered with a `pcs` suffix via a custom cell formatter.

**Row click wiring is special in Tabulator 6.x.** The `rowClick` constructor option does not fire in 6.x — the Interaction module only wires it when you subscribe via `table.on("rowClick", ...)` after construction. See §10.

**Initial selection is sent in `table.on("tableBuilt", ...)`** by emitting the first row's data. This populates the inspector on page load.

**Toolbar actions**: **Columns** (dispatches `grid:request-columns`), **View** (a `Default` / `Electrical` / `Mechanical` dropdown), **Edit Views** (dispatches `grid:request-edit-views`). All three are no-op visual stubs in the first pass.

### 7.8 Filter strip — `.filter-region`, `.filter-header`, `.filter-body`

Below the grid, with its own 96px-tall region. Structure:

```
┌────────────────────────────────────────┐
│ filter-header      "Filter"            │  24px
├────────────────────────────────────────┤
│ filter-body                            │
│   [Search  input]  [Scope  select]     │
│   [View    select] [Stock  select]     │
│   [+ Filter] [Apply] [Reset]           │  72px
└────────────────────────────────────────┘
```

- `.filter-header` — uppercase header bar, same style as `.pane-header`.
- `.filter-body` — flex-wrap row of `.filter-control` items. Each control is a labeled `<label>` with a `.filter-control-label` (muted) and a `<select>` or `<input>` (compact border, `--panel-2` background).
- `.filter-actions` — right-aligned cluster of action buttons (`+ Filter`, `Apply`, `Reset`).
- `.filter-chips` — chip container, populated by the `+ Filter` button.

`/ ` keyboard shortcut focuses the Quick Search input (suppressed when another input has focus).

### 7.9 Inspector pane (right) — `.inspector-region`, `.inspector-header`, `.inspector-section`, `.inspector-properties`, `.inspector-tab-panel`

The inspector is the most structured pane. It has four horizontal regions:

```
┌────────────────────────────────────────┐
│ inspector-header                       │
│   inspector-title        16px          │  the selected item
│   inspector-subtitle     12px          │  sku · category · MPN
│   inspector-meta         11px          │  stock · status · footprint
├────────────────────────────────────────┤
│ inspector-tabs                         │  Part Details · Stock History · …
├────────────────────────────────────────┤
│ inspector-content                      │
│   inspector-tab-panel                   │
│     inspector-section  "Properties"    │  section header
│     inspector-properties (data-section="properties")
│       inspector-property
│         inspector-property-label       │  110px wide, muted
│         inspector-property-value       │  1fr, ellipsis
│     inspector-section  "Attributes"    │  section header
│     inspector-properties (data-section="attributes")
│       …                                │
└────────────────────────────────────────┘
```

- `.inspector-header` — selected-item identity. Title is the part name (16px, bold). Subtitle is `sku · category · MPN part_number` (12px, muted). Meta is `stock · status · footprint` (11px, primary).
- `.inspector-tabs` — horizontal tab strip on `--bg-2`. Active tab has bottom border in `--accent` and `--panel-2` background.
- `.inspector-content` — scrollable container, holds one `.inspector-tab-panel` per tab.
- `.inspector-tab-panel` — flex column with `overflow: auto`. The `Part Details` panel is the only one with a real layout; others get a `.inspector-placeholder` italic note.
- `.inspector-section` — uppercase section header, same visual style as `.pane-header` but smaller padding. Used to separate "Properties" from "Attributes" inside the Part Details panel.
- `.inspector-properties` — flex column of `.inspector-property` rows.
- `.inspector-property` — grid `110px 1fr`. Label cell on `--panel-2` with right border. Value cell on `--panel`. Even rows get a `--strip` background.
- `.inspector-placeholder` — italic muted text for tabs without a real layout yet.

**The "Properties" section shows non-attribute item fields** (Internal ID, Name, SKU, Part Number, Category, Description, Footprint, Status, Stock Level, Stock Mode, Instance Kind, Markings). **The "Attributes" section shows per-category attribute values** from the row's `attributes` array (Resistance/Tolerance/Power Rating for resistors, Polarity/Vds/Id/Rds for MOSFETs, etc.). This is the split requested in the design review.

Inspector selection state is held in DOM. The `row:selected` event handler in `initInspector` mutates the `title`, `subtitle`, and `meta` text directly, then `replaceWith`-swaps the two property tables in place — keeping the Part Details panel's scroll position stable across selections.

Toolbar actions: **Edit Item**, **Adjust Inventory**. Both are no-op stubs that dispatch `inspector:request-edit` / `inspector:request-adjust`.

### 7.10 Quick reference: all CSS classes

```
Layout chrome
  .layout-root, .workspace, .pane, .pane-left, .pane-center, .pane-right
  .sash, .sash-left, .sash-right, .sash-bottom
  .restore-bar, .restore-left, .restore-right, .restore-filter
  .is-collapsed
  .toolbar, .toolbar-global, .toolbar-brand, .toolbar-actions, .toolbar-btn
  .status-bar

Pane chrome
  .pane-header, .pane-header-name, .pane-header-actions
  .pane-toolbar, .pane-toolbar-btn, .pane-toolbar-select,
  .pane-toolbar-search, .pane-toolbar-label

Filter strip
  .filter-region, .filter-header, .filter-body
  .filter-control, .filter-control-label
  .filter-actions, .filter-add-chip, .filter-chips, .chip

Tree
  .tree-region, .tree-row, .tree-chevron, .tree-chevron-leaf, .tree-label

Grid (Tabulator overrides)
  .tabulator, .tabulator-row, .tabulator-row-odd, .tabulator-row-even
  .tabulator-header, .tabulator-col, .tabulator-col-content, .tabulator-col-sorter
  .tabulator-cell, .tabulator-group, .tabulator-group-label, .tabulator-arrow
  .tabulator-footer, .tabulator-editing
  .group-path, .group-count

Inspector
  .inspector-region, .inspector-header
  .inspector-title, .inspector-subtitle, .inspector-meta
  .inspector-tabs, .inspector-tab-panel, .inspector-placeholder
  .inspector-section, .inspector-properties, .inspector-property
  .inspector-property-label, .inspector-property-value
```

---

## 8. Theme System

The theme controller lives in `ui/src/theme.js`. The factory `createThemeController({ root, toggleButton, storage, matchMedia })` returns `{ apply, setMode, toggle, current, bindToggleButton }`.

- `root` — required. A DOM element whose `dataset.theme` will be set to `dark` or `light`.
- `toggleButton` — optional. Its textContent flips between `Light Mode` and `Dark Mode`, and `dataset.targetMode` is set to the mode the button would switch to.
- `storage` — defaults to `window.localStorage`. Reads/writes key `thinghound.theme`.
- `matchMedia` — defaults to `window.matchMedia`. Used for the initial system query.

Mode resolution:

```
current mode = stored override  ??  (system prefers-dark ? "dark" : "light")
```

System mode is detected once at construction. After construction, only `setMode` or `toggle` changes the active mode. To re-read the system preference (e.g. when the OS theme changes while the app is open), call `setMode(null)` or call `matchMedia("(prefers-color-scheme: dark)")` manually — this is currently a known gap; see §10.

The controller is robust to a missing or unavailable `localStorage` (private mode) and to a missing `matchMedia` (it throws on construction only if you explicitly pass `null`).

Initial application in `main.js`:

```js
const theme = createThemeController({ root: appRoot, toggleButton: themeToggle });
theme.apply();
themeToggle?.addEventListener("click", () => theme.toggle());
```

The `index.html` ships with `data-theme="dark"` so the first paint matches the dark theme even before JS runs.

---

## 9. Bridge Contract

The bridge connects the JS frontend to the Python service layer (`thinghound.ui.bridge.Bridge`). The Python `Bridge` class is exposed to JS as `window.pywebview.api` by PyWebView. The JS wrapper `createBridgeApi(pywebviewApi)` in `ui/src/bridge-api.js` provides a typed surface and falls back to JS-side fixtures if the bridge is absent (standalone browser mode).

### Methods (called from JS, awaited, return dicts)

| Method | Request | Response | Used by |
|--------|---------|----------|---------|
| `get_display_columns({})` | — | `{ columns: [{ key, title }, …] }` | Grid column setup |
| `get_column_mappings({})` | — | `{ mappings: { type: { key: attrKey } } }` | Reserved for per-category attribute binding |
| `get_category_tree({})` | — | `{ nodes: [ { id, name, children: […] } ] }` | Tree pane |
| `grid_query_items({ categoryId?, quickSearch? })` | filter dict | `{ rows: […], total: number }` | Grid data load and reload |
| `get_inspector_payload({ itemId })` | selected item UUID | `{ summary, properties, attributes, tabs }` | Inspector panel update |

### Row data shape

Each row in `grid_query_items.rows` is a flat dict with at least:

```js
{
  id: "01ARZ3NDEKTSV4RRFFQ69G5FAV",  // UUIDv7 string
  sku: "RES-1K-0603-1%",
  name: "Resistor 1 kΩ 1% 0603",
  description: "Thick film chip resistor, 0603, 1 kΩ, ±1%, 1/10 W",
  part_number: "RC0603FR-071KL",
  stock: "250",                       // stringified Decimal; UI adds " pcs" suffix
  status: "Active",                   // lifecycle_status_code resolved to name
  footprint: "0603",
  stock_mode: "Bulk" | "Instance",
  instance_kind: "Lot" | "Serial",
  markings: "102",
  category: "Resistors",              // leaf category name
  category_path: ["root", "passive", "resistors"],  // ancestor chain
  category_path_display: "All Categories > Passive > Resistors",
  attributes: [
    { name: "Resistance", value: "1 kΩ" },
    { name: "Tolerance", value: "±1%" },
    …
  ]
}
```

The bridge mock (Python `src/thinghound/ui/fixtures.py` and JS `ui/src/fixtures.js`) must return the same shape — both are kept in sync.

### Inspector payload shape

```js
{
  summary: { name, sku, category, stock, status, footprint, part_number, description },
  properties: {                       // non-attribute item fields for the property panel
    "Internal ID": "...",
    "Name": "...",
    "SKU": "...",
    "Part Number": "...",
    "Category": "...",
    "Description": "...",
    "Footprint": "...",
    "Status": "...",
    "Stock Level": "...",
    "Stock Mode": "...",
    "Instance Kind": "...",
    "Markings": "..."
  },
  attributes: [ { name, value }, … ],  // per-category attribute values
  tabs: { "Part Details": { content }, … }  // reserved for future per-tab content
}
```

The mock returns a properties dict for every item and an `attributes` array that depends on the row's `category`. The fallback (no-bridge) JS path builds the same shape from the row data.

### Custom DOM events on `window`

The bridge is the only outward-facing API. Communication **inside** the JS layer uses `CustomEvent` on `window`:

| Event | `detail` | Dispatched by | Handled by |
|-------|----------|---------------|------------|
| `row:selected` | the full row data | grid (on click + on tableBuilt) | inspector |
| `grid:filter` | `{ categoryId?, quickSearch?, … }` | tree (on row click) and filter strip (on input) | grid (re-fetches rows) |
| `layout:changed` | — | layout (after sash drag / collapse) | grid (re-fetches rows) |
| `grid:request-columns` | — | grid toolbar | (no handler yet) |
| `grid:request-edit-views` | — | grid toolbar | (no handler yet) |
| `tree:request-edit` | — | tree toolbar | (no handler yet) |
| `inspector:request-edit` | — | inspector toolbar | (no handler yet) |
| `inspector:request-adjust` | — | inspector toolbar | (no handler yet) |

All `request-*` events are dispatch points for actions the toolbar buttons claim to perform; they have no handlers in the first pass. Future work should attach handlers for these rather than wiring button clicks directly.

### Standalone mode

`createBridgeApi(undefined)` returns an API with `hasPywebviewBridge: false`. Every method returns the JS fixture response — this lets the bundle open directly in a browser (`file://` to `ui/dist/index.html`) without PyWebView, which is useful for static layout and theme debugging.

`main.js` logs `PyWebView API not available; running in standalone layout mode.` in this case.

---

## 10. Tabulator Overrides and Gotchas

### The Tabulator midnight CSS is loaded as-is

`ui/index.html` loads `tabulator_midnight.min.css` from unpkg, unmodified. This CSS has its own dark palette baked in with high specificity (compound selectors, multiple classes). Our overrides in `ui/styles.css` use `!important` on every Tabulator property and use Tabulator's own class names (`.tabulator-row-odd`, `.tabulator-row-even`) to win the specificity battle.

If you find Tabulator cells showing the wrong background, it's almost always one of:

- A new Tabulator class added in a future version that we haven't overridden yet
- An overridden property missing `!important` and being beaten by midnight

The CSS structure to maintain is: every `.tabulator .tabulator-foo` rule uses `!important` and references theme variables (`var(--tabulator-bg)`, etc.), never hardcoded colors.

### `rowClick` is not a constructor option in Tabulator 6.x

This bit us. The `Interaction` module's `eventMap` includes `rowClick: "row-click"`, but **the constructor option is not auto-registered** as an external event. Passing `rowClick: fn` in the Tabulator constructor silently does nothing.

The wiring only happens when you call `table.on("rowClick", ...)` after construction. Always wire row/cell events this way:

```js
const table = new Tabulator(target, buildGridOptions({ rows, displayColumns }));
table.on("rowClick", (_event, row) => emitSelection(row.getData()));
table.on("rowDblClick", (_event, row) => emitSelection(row.getData()));
```

`ui/src/grid.js` also includes a backup click-delegation handler on the grid container that walks up to the nearest `.tabulator-row` and emits the selection manually, as defense-in-depth against future formatters that might swallow the click event.

### Group headers are full paths, not leaf names

The grid groups on `category_path_display`, not `category`. The data model has `id_path` (ids) and `full_path` (names) on each category; the row carries the resolved name string in `category_path_display`. This is why a MOSFET and a BJT both fall under the same "All Categories > Active > Semiconductors > Transistors" group, and the count says `(N parts)` rather than the leaf name.

`buildGridOptions` uses a custom `groupHeader` formatter to render the path bold and the count muted, separated into `.group-path` and `.group-count` spans for styling.

### Tabulator JS API surface to avoid

- `rowClick` / `rowDblClick` / `cellClick` etc. as constructor options — not wired in 6.x. Use `table.on(...)`.
- `tabulator_rowFormatter` / `rowFormatter` callbacks expecting a jQuery-style API — Tabulator 6.x returns native components (`Row`, `Cell`, `Column`).
- `setData` followed by `redraw` is fine, but for large catalogs prefer `replaceData` (uses internal diff).

---

## 11. Known Issues and Future Work

This is a first pass for a demo. The following are deliberate non-goals and should be picked up only when the workspace moves beyond demo:

1. **No row-level persistence.** All state lives in memory. A page reload resets the grid selection, tree expand state, and theme to whatever localStorage holds.
2. **No tests against the JS layer.** The plan TDD approach was deliberately skipped per the demo framing. A future agent should add Vitest + jsdom before adding non-trivial logic to `grid.js`, `inspector.js`, or `tree.js`. The Python `tests/ui/test_bridge_contract.py` covers the bridge contract.
3. **No reactivity to OS theme changes.** The theme reads `prefers-color-scheme: dark` once at construction. If the user changes the OS theme while the app is open, the in-app theme does not follow. Adding this requires listening to the `MediaQueryList.change` event and re-applying the system mode.
4. **No keyboard navigation in the grid.** Tabulator supports it but it's not enabled. Same for the tree.
5. **No save/load view wiring.** Save View, Load View, Columns, Edit Views, Edit Item, Adjust Inventory, and Edit (tree) are all no-op stubs that fire request events. The data model and bridge are ready for them; only the UI dispatch points exist.
6. **Search/filter is single-input.** The quick-search filters on `name`, `sku`, `category`, and `description`. The "+ Filter" button creates generic chips that don't yet drive queries. The `+ Filter` UI is a placeholder for the parametric predicate tree the data model supports.
7. **The right pane inspector is the only one with a rich property panel.** Stock History, Parameters, Vendors, Alternates, and BOM/Where-used are placeholder tabs. The shape of `tabs` in the bridge payload is reserved for these.
8. **No drag-and-drop between panes, no splitter shortcuts, no fullscreen toggles.**

---

## 12. How to Extend

### Add a new global toolbar action

1. Add the button to the `.toolbar-actions` div in `ui/index.html` with an `id`.
2. Wire its click in `ui/src/main.js` (or a new module) to do the thing. Prefer dispatching a `request-*` event so the handler can be attached anywhere.
3. Style: `.toolbar-btn` works as-is. For a brand color, use `.toolbar-global .toolbar-btn` selector.

### Add a new column to the grid

1. Add a row field to every fixture row in `ui/src/fixtures.js` and `src/thinghound/ui/fixtures.py`.
2. Add the column to `DISPLAY_COLUMNS` in both fixture files.
3. If the column needs a custom cell formatter (e.g. `pcs` suffix on stock), extend `buildColumns` in `ui/src/grid.js`.
4. Rebuild and verify.

### Add a new pane-local toolbar button

1. Add a `buildToolbarButton(...)` call in the corresponding `render*Toolbar(target)` function.
2. The function should accept the button label and any `title`/click handler. Standard pattern:
   ```js
   const button = buildToolbarButton("My Action");
   button.addEventListener("click", () => window.dispatchEvent(new CustomEvent("pane:request-action")));
   target.appendChild(button);
   ```
3. Style: `.pane-toolbar-btn` works as-is. For a more prominent style, add a new modifier class.

### Add a new theme token

1. Add the token to the `:root` block if it's structural (size/typography), or to both `[data-theme="..."]` blocks if it's a color.
2. Reference it from the relevant component rule in `ui/styles.css`.
3. Never hardcode colors or sizes in component rules — always reference a token.

### Add a new bridge method

1. Add the method to the Python `Bridge` class in `src/thinghound/ui/bridge.py` and to its `_mock_handlers` dict for `--mock` mode.
2. Add the JS wrapper in `ui/src/bridge-api.js`. The wrapper should always call the live bridge first and fall back to a JS fixture on `null`.
3. Update the bridge contract table in §9 of this doc.
4. If the method returns data for a specific component, also update the receiving component's `init*` function to call it and update its DOM.

### Add a new inspector tab

1. Add the tab name to `INSPECTOR_TABS` in both fixture files.
2. Add the tab to `fallbackTabs` in `ui/src/inspector.js`. If the tab needs a real layout (like Part Details), extend the `renderTabs` function to detect it and build a custom panel.
3. Style: the `.inspector-tab-panel` and `.inspector-placeholder` classes cover the simple case.

---

## 13. File-Level Cheat Sheet

| File | Purpose | Touch when… |
|------|---------|-------------|
| `ui/index.html` | Static shell, theme root, all tab targets | Adding a global toolbar button, adding a new tab region |
| `ui/styles.css` | All tokens, all component styles, Tabulator overrides | Re-theming, fixing a layout bug, adding a new component class |
| `ui/src/main.js` | App entry: theme init, layout init, pane init | Adding a new module, wiring a new global event |
| `ui/src/bridge-api.js` | JS↔Python bridge wrapper with JS fixture fallback | Adding a new bridge method |
| `ui/src/fixtures.js` | JS-side fixture data, mirror of `src/thinghound/ui/fixtures.py` | Adding/changing row data, columns, tree, or inspector content |
| `ui/src/theme.js` | Theme controller (system / override / toggle) | Changing theme storage key, adding a third theme |
| `ui/src/layout.js` | Sash drag, pane collapse, restore bars | Changing pane sizes, min widths, default restore sizes |
| `ui/src/tree.js` | Tree state, expand/collapse, search | Changing tree behavior, adding new tree actions |
| `ui/src/grid.js` | Tabulator wrapper, grid toolbar, column builders | Adding columns, changing grid config, wiring new row events |
| `ui/src/filterstrip.js` | Filter controls, search shortcut | Adding a new filter, changing the strip layout |
| `ui/src/inspector.js` | Inspector header, property panel, tabs | Changing inspector layout, adding a tab, adding a property |
| `src/thinghound/ui/app.py` | PyWebView entry, parses `--mock` flag | Changing how the app launches |
| `src/thinghound/ui/bridge.py` | Python Bridge class exposed to JS as `window.pywebview.api` | Adding a bridge method, changing mock handlers |
| `src/thinghound/ui/fixtures.py` | Mock fixture data for `--mock` mode | Adding/changing row data, columns, tree, or inspector content |
| `tests/ui/test_bridge_contract.py` | Python contract tests for the bridge | Adding a bridge method (write a test) |
| `package.json` | npm scripts: `build`, `dev` | Adding a build step |
| `docs/specs/thinghound-ui-design.md` | This document | Adding a new component, changing the contract |
