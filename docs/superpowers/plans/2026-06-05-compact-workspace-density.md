# Compact Workspace Density Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the first-pass dense demo workspace: global toolbar plus pane-local toolbars, dual light/dark themes with system-default startup and manual toggle, compact data typography across all panes, a denser Tabulator grid, and a clearer inspector selection header.

**Architecture:** Keep the current vanilla-JS UI structure, but introduce three focused seams before restyling: a tracked source stylesheet at `ui/styles.css`, a small theme controller module, and pane-scoped DOM renderers for toolbar content. Density and theme behavior stay in CSS tokens plus a narrow JS layer; data flow and bridge contracts remain unchanged.

**Tech Stack:** Vanilla JavaScript, Tabulator, esbuild, Vitest, jsdom, PyWebView bridge fixtures.

---

## File structure

### Create

- `ui/styles.css`
- `ui/src/theme.js`
- `ui/tests/theme.test.js`
- `ui/tests/grid.test.js`
- `ui/tests/layout.test.js`
- `ui/tests/inspector.test.js`

### Modify

- `package.json`
- `ui/index.html`
- `ui/src/main.js`
- `ui/src/layout.js`
- `ui/src/grid.js`
- `ui/src/tree.js`
- `ui/src/inspector.js`
- `ui/src/filterstrip.js`
- `ui/src/fixtures.js`

### Responsibilities

- `ui/styles.css`: source-of-truth tokens and dense component styling for global chrome, pane-local toolbars, grid overrides, tree, filter strip, and inspector.
- `ui/src/theme.js`: system-theme detection, persisted override, DOM attribute updates, and toolbar-toggle wiring.
- `ui/src/layout.js`: preserve sash/minimize behavior while supporting nested pane toolbars and content regions.
- `ui/src/grid.js`: blank thumbnail header, dense grid options, grid-pane toolbar rendering, and testable helper exports.
- `ui/src/tree.js`: pane-local toolbar actions, compact tree rows, and search placement.
- `ui/src/inspector.js`: pane-local toolbar actions plus larger selected-item title/subtitle header.
- `ui/src/filterstrip.js`: compact filter controls consistent with the shared data-text scale.
- `ui/tests/*.test.js`: DOM and behavior tests for theme mode, toolbar boundaries, dense grid configuration, and inspector header hierarchy.

---

### Task 1: Add UI test harness and stylesheet build path

**Files:**
- Create: `ui/tests/theme.test.js`
- Modify: `package.json`

- [ ] **Step 1: Write the failing test script expectation**

Add a Vitest-based script block to `package.json` in the plan target state:

```json
{
  "scripts": {
    "build": "esbuild ui/src/main.js --bundle --outfile=ui/dist/main.js --sourcemap && cp ui/index.html ui/dist/index.html && cp ui/styles.css ui/dist/styles.css",
    "dev": "esbuild ui/src/main.js --bundle --outfile=ui/dist/main.js --sourcemap --watch",
    "test:ui": "vitest run"
  },
  "devDependencies": {
    "esbuild": "^0.24.0",
    "jsdom": "^26.1.0",
    "vitest": "^2.1.8"
  }
}
```

And create the first failing test in `ui/tests/theme.test.js`:

```js
import { describe, expect, it, vi } from "vitest";
import { createThemeController } from "../src/theme.js";

describe("createThemeController", () => {
  it("uses the system mode until a manual override is set", () => {
    const mediaQuery = {
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
    const storage = new Map();
    const root = document.createElement("div");

    const controller = createThemeController({
      root,
      storage: {
        getItem: (key) => storage.get(key) ?? null,
        setItem: (key, value) => storage.set(key, value),
      },
      matchMedia: () => mediaQuery,
    });

    controller.apply();
    expect(root.dataset.theme).toBe("dark");

    controller.setMode("light");
    expect(root.dataset.theme).toBe("light");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
npm run test:ui -- ui/tests/theme.test.js
```

Expected: FAIL with `Missing script: "test:ui"` or `Cannot find module '../src/theme.js'`.

- [ ] **Step 3: Write minimal implementation**

Create `ui/src/theme.js` with the smallest implementation that satisfies the first test:

```js
const STORAGE_KEY = "thinghound.theme";

export function createThemeController({ root, storage = window.localStorage, matchMedia = window.matchMedia } = {}) {
  if (root == null) {
    throw new Error("Theme root is required.");
  }

  const mediaQuery = matchMedia("(prefers-color-scheme: dark)");
  let mode = storage.getItem(STORAGE_KEY);

  const resolveMode = () => (mode ?? (mediaQuery.matches ? "dark" : "light"));

  return {
    apply() {
      root.dataset.theme = resolveMode();
    },
    setMode(nextMode) {
      mode = nextMode;
      storage.setItem(STORAGE_KEY, nextMode);
      root.dataset.theme = nextMode;
    },
  };
}
```

Update `package.json` exactly as shown in Step 1.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
npm install
npm run test:ui -- ui/tests/theme.test.js
```

Expected: PASS with `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add package.json package-lock.json ui/src/theme.js ui/tests/theme.test.js
git commit -m "test(ui): add theme test harness"
```

---

### Task 2: Introduce global toolbar and pane-local toolbar layout skeleton

**Files:**
- Create: `ui/tests/layout.test.js`
- Modify: `ui/index.html`
- Modify: `ui/src/layout.js`

- [ ] **Step 1: Write the failing layout test**

Create `ui/tests/layout.test.js`:

```js
import { describe, expect, it } from "vitest";
import { JSDOM } from "jsdom";
import { initializeLayout } from "../src/layout.js";

function buildDocument() {
  const dom = new JSDOM(`
    <div id="app" class="layout-root">
      <header class="toolbar">
        <div class="toolbar-brand">ThingHound</div>
        <div class="toolbar-actions"></div>
      </header>
      <main class="workspace" id="workspace">
        <aside class="pane pane-left" id="pane-left">
          <div class="pane-toolbar" data-pane-toolbar="tree"></div>
          <div class="pane-body" data-pane-body="tree"></div>
        </aside>
        <div class="sash sash-left" data-sash="left"></div>
        <section class="pane pane-center" id="pane-center">
          <div class="pane-toolbar" data-pane-toolbar="grid"></div>
          <div class="grid-region"></div>
          <div class="sash sash-bottom" data-sash="bottom"></div>
          <div class="filter-region" id="filter-region"></div>
        </section>
        <div class="sash sash-right" data-sash="right"></div>
        <aside class="pane pane-right" id="pane-right">
          <div class="pane-toolbar" data-pane-toolbar="inspector"></div>
          <div class="pane-body" data-pane-body="inspector"></div>
        </aside>
      </main>
      <footer class="status-bar">Ready</footer>
    </div>
  `, { pretendToBeVisual: true });

  global.window = dom.window;
  global.document = dom.window.document;
  return dom;
}

describe("initializeLayout", () => {
  it("keeps pane toolbars present alongside sash controls", () => {
    buildDocument();
    initializeLayout();

    expect(document.querySelector('[data-pane-toolbar="tree"]')).not.toBeNull();
    expect(document.querySelector('[data-pane-toolbar="grid"]')).not.toBeNull();
    expect(document.querySelector('[data-pane-toolbar="inspector"]')).not.toBeNull();
    expect(document.getElementById("restore-left")).not.toBeNull();
    expect(document.getElementById("restore-right")).not.toBeNull();
    expect(document.getElementById("restore-filter")).not.toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
npm run test:ui -- ui/tests/layout.test.js
```

Expected: FAIL because the test DOM structure does not match the current assumptions in `initializeLayout()`, or because the restore controls are not compatible with the revised pane markup.

- [ ] **Step 3: Write minimal implementation**

Update `ui/index.html` so each pane has explicit toolbar/body regions:

```html
<aside class="pane pane-left" id="pane-left">
  <div class="pane-toolbar" data-pane-toolbar="tree"></div>
  <div class="pane-body tree-region" id="tree-region"></div>
</aside>

<section class="pane pane-center" id="pane-center">
  <div class="pane-toolbar" data-pane-toolbar="grid"></div>
  <div class="grid-region" id="grid-region"></div>
  <div class="sash sash-bottom" data-sash="bottom"></div>
  <div class="filter-region" id="filter-region"></div>
</section>

<aside class="pane pane-right" id="pane-right">
  <div class="pane-toolbar" data-pane-toolbar="inspector"></div>
  <div class="pane-body inspector-region" id="inspector-region"></div>
</aside>
```

Adjust `ui/src/layout.js` only enough to preserve `setupHorizontalSashes()`, `setupFilterSash()`, and `setupPaneMinimize()` against the new nested pane markup. Keep restore bars appended to the pane or workspace container rather than to the inner bodies.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
npm run test:ui -- ui/tests/layout.test.js
```

Expected: PASS with toolbar placeholders and restore controls present.

- [ ] **Step 5: Commit**

```bash
git add ui/index.html ui/src/layout.js ui/tests/layout.test.js
git commit -m "feat(ui): add pane toolbar layout skeleton"
```

---

### Task 3: Render toolbars and compact grid structure first

**Files:**
- Create: `ui/tests/grid.test.js`
- Modify: `ui/src/main.js`
- Modify: `ui/src/grid.js`
- Modify: `ui/src/tree.js`
- Modify: `ui/src/inspector.js`

- [ ] **Step 1: Write the failing grid and toolbar tests**

Create `ui/tests/grid.test.js`:

```js
import { describe, expect, it } from "vitest";
import { buildColumns, renderGridToolbar } from "../src/grid.js";

describe("buildColumns", () => {
  it("keeps the thumbnail column with a blank header and tighter width", () => {
    const columns = buildColumns([{ key: "name", title: "Name" }]);
    expect(columns[0]).toMatchObject({
      title: "",
      field: "thumbnail",
      width: 36,
    });
  });
});

describe("renderGridToolbar", () => {
  it("renders grid-local controls without global actions", () => {
    const target = document.createElement("div");
    renderGridToolbar(target);

    expect(target.textContent).toContain("Columns");
    expect(target.textContent).toContain("Grid View");
    expect(target.textContent).toContain("Edit Views");
    expect(target.textContent).not.toContain("Save Setup");
  });
});
```

Add similar expectations in `ui/tests/layout.test.js` or a new `ui/tests/inspector.test.js` for pane-local controls:

```js
expect(treeToolbar.textContent).toContain("Collapse All");
expect(treeToolbar.textContent).toContain("Expand All");
expect(inspectorToolbar.textContent).toContain("Edit Item");
expect(inspectorToolbar.textContent).toContain("Adjust Inventory");
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
npm run test:ui -- ui/tests/grid.test.js ui/tests/layout.test.js
```

Expected: FAIL because `buildColumns` still uses `title: "Thumb"` and no toolbar renderer exports exist yet.

- [ ] **Step 3: Write minimal implementation**

Change `ui/src/grid.js` to export testable helpers:

```js
export function buildColumns(displayColumns) {
  const base = [
    {
      title: "",
      field: "thumbnail",
      width: 36,
      hozAlign: "center",
      headerSort: false,
      formatter: "plaintext",
    },
  ];

  const dynamic = displayColumns.map((column) => ({
    title: column.title,
    field: column.key,
    headerSort: true,
  }));

  return [...base, ...dynamic];
}

export function renderGridToolbar(target) {
  target.replaceChildren(
    buildToolbarButton("Columns"),
    buildToolbarSelect("Grid View", ["Default", "Electrical", "Mechanical"]),
    buildToolbarButton("Edit Views"),
  );
}
```

Add analogous toolbar renderers:

```js
export function renderTreeToolbar(target) {
  target.replaceChildren(
    buildToolbarButton("Collapse All"),
    buildToolbarButton("Expand All"),
    buildToolbarSearch("Search tree"),
    buildToolbarButton("Edit"),
  );
}

export function renderInspectorToolbar(target) {
  target.replaceChildren(
    buildToolbarButton("Edit Item"),
    buildToolbarButton("Adjust Inventory"),
  );
}
```

Wire `ui/src/main.js` to pass the toolbar targets into the pane initializers instead of letting each pane overwrite the entire pane root.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
npm run test:ui -- ui/tests/grid.test.js ui/tests/layout.test.js
```

Expected: PASS with the blank thumbnail header and pane-local toolbar content verified.

- [ ] **Step 5: Commit**

```bash
git add ui/src/main.js ui/src/grid.js ui/src/tree.js ui/src/inspector.js ui/tests/grid.test.js ui/tests/layout.test.js
git commit -m "feat(ui): add pane-local toolbar renderers"
```

---

### Task 4: Add dense source stylesheet and whole-workspace compact styling

**Files:**
- Create: `ui/styles.css`
- Modify: `ui/index.html`
- Modify: `ui/src/filterstrip.js`

- [ ] **Step 1: Write the failing visual-structure test**

Extend `ui/tests/layout.test.js` with CSS hook expectations:

```js
it("exposes the compact styling hooks used by the dense stylesheet", () => {
  buildDocument();
  initializeLayout();

  expect(document.querySelector(".pane-toolbar")).not.toBeNull();
  expect(document.querySelector(".tree-region")).not.toBeNull();
  expect(document.querySelector(".grid-region")).not.toBeNull();
  expect(document.querySelector(".inspector-region")).not.toBeNull();
});
```

Add an inspector-specific test in `ui/tests/inspector.test.js`:

```js
import { describe, expect, it } from "vitest";
import { renderInspectorSummary } from "../src/inspector.js";

describe("renderInspectorSummary", () => {
  it("splits title/subtitle from dense metadata rows", () => {
    const target = document.createElement("div");
    renderInspectorSummary(target, {
      name: "2N7000",
      category: "MOSFET",
      onHand: "23",
    });

    expect(target.querySelector(".inspector-title")?.textContent).toBe("2N7000");
    expect(target.querySelector(".inspector-subtitle")?.textContent).toContain("MOSFET");
    expect(target.querySelector(".inspector-meta")).not.toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
npm run test:ui -- ui/tests/layout.test.js ui/tests/inspector.test.js
```

Expected: FAIL because the inspector still renders a single summary line and the compact CSS hooks are incomplete.

- [ ] **Step 3: Write minimal implementation**

Create `ui/styles.css` with compact tokens and theme surfaces:

```css
:root {
  --data-font-size: 11px;
  --row-height: 22px;
  --cell-pad-x: 6px;
  --cell-pad-y: 2px;
  --toolbar-height: 34px;
  --pane-toolbar-height: 26px;
}

[data-theme="dark"] {
  --bg: #11161e;
  --panel: #1b2330;
  --panel-2: #202938;
  --line: #2b3747;
  --text: #dfe6f1;
  --muted: #93a3b9;
}

[data-theme="light"] {
  --bg: #dfe7f2;
  --panel: #edf3fb;
  --panel-2: #f7fafe;
  --line: #bccada;
  --text: #23384f;
  --muted: #5f738b;
}

.pane-toolbar,
.tree-list,
.filter-region,
.tabulator,
.inspector-meta {
  font-size: var(--data-font-size);
}

.inspector-title {
  font-size: 18px;
  font-weight: 700;
}

.inspector-subtitle {
  font-size: 13px;
  color: var(--muted);
}
```

Update `ui/src/inspector.js` to render a structured summary:

```js
export function renderInspectorSummary(target, item) {
  const title = document.createElement("div");
  title.className = "inspector-title";
  title.textContent = item.name ?? "Select an item";

  const subtitle = document.createElement("div");
  subtitle.className = "inspector-subtitle";
  subtitle.textContent = item.category ?? "";

  const meta = document.createElement("div");
  meta.className = "inspector-meta";
  meta.textContent = `On hand ${item.on_hand?.display ?? item.onHand ?? "-"}`;

  target.replaceChildren(title, subtitle, meta);
}
```

Tighten `ui/src/filterstrip.js` to render labeled compact controls instead of an unstructured replaceChildren list.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
npm run test:ui -- ui/tests/layout.test.js ui/tests/inspector.test.js
npm run build
```

Expected:
- Vitest: PASS
- Build: PASS and `ui/dist/styles.css` exists.

- [ ] **Step 5: Commit**

```bash
git add ui/styles.css ui/src/filterstrip.js ui/src/inspector.js ui/tests/layout.test.js ui/tests/inspector.test.js package.json package-lock.json
git commit -m "feat(ui): add dense workspace stylesheet"
```

---

### Task 5: Apply dense Tabulator overrides and inspector/tree polish

**Files:**
- Modify: `ui/src/grid.js`
- Modify: `ui/src/tree.js`
- Modify: `ui/src/inspector.js`
- Modify: `ui/styles.css`

- [ ] **Step 1: Write the failing behavior test**

Expand `ui/tests/grid.test.js`:

```js
it("configures dense Tabulator behavior and subtle group headers", () => {
  const options = buildGridOptions({
    rows: [],
    displayColumns: [{ key: "name", title: "Name" }],
    onRowSelected: () => {},
  });

  expect(options.layout).toBe("fitColumns");
  expect(options.groupBy).toBe("category");
  expect(options.rowHeight).toBe(22);
  expect(options.columnHeaderVertAlign).toBe("middle");
});
```

Add a tree behavior test:

```js
it("keeps search in the tree toolbar instead of the pane body", () => {
  const toolbar = document.createElement("div");
  const body = document.createElement("div");
  renderTreeToolbar(toolbar, { onSearch: () => {} });
  renderTreeList(body, [{ id: "root", name: "All Categories", depth: 0 }], () => {});

  expect(toolbar.querySelector('input[type="search"]')).not.toBeNull();
  expect(body.querySelector('input[type="search"]')).toBeNull();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
npm run test:ui -- ui/tests/grid.test.js
```

Expected: FAIL because `buildGridOptions` and `renderTreeList` are not separated/exported yet.

- [ ] **Step 3: Write minimal implementation**

Refactor `ui/src/grid.js` into testable seams:

```js
export function buildGridOptions({ rows, displayColumns, onRowSelected }) {
  return {
    data: rows,
    layout: "fitColumns",
    reactiveData: true,
    movableColumns: true,
    virtualDom: true,
    rowHeight: 22,
    columnHeaderVertAlign: "middle",
    groupBy: "category",
    columns: buildColumns(displayColumns),
    rowClick: (_event, row) => onRowSelected(row.getData()),
  };
}
```

Move tree search and list rendering apart in `ui/src/tree.js`:

```js
export function renderTreeList(target, nodes, onFilter, query = "") {
  target.replaceChildren();
  for (const node of nodes) {
    if (!node.name.toLowerCase().includes(query.toLowerCase())) {
      continue;
    }
    const item = document.createElement("li");
    item.className = "tree-row";
    item.style.setProperty("--tree-depth", String(node.depth));
    item.textContent = node.name;
    item.addEventListener("click", () => onFilter(node.id));
    target.appendChild(item);
  }
}
```

Add the matching dense Tabulator overrides to `ui/styles.css`:

```css
.tabulator .tabulator-header .tabulator-col {
  min-height: var(--row-height);
  padding: 0;
}

.tabulator .tabulator-row .tabulator-cell {
  padding: var(--cell-pad-y) var(--cell-pad-x);
  line-height: 1.15;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tabulator-row:nth-child(even) {
  background: color-mix(in srgb, var(--panel-2) 88%, transparent);
}

.tabulator-group {
  font-size: var(--data-font-size);
  font-weight: 600;
  background: transparent;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
npm run test:ui -- ui/tests/grid.test.js ui/tests/inspector.test.js
npm run build
```

Expected:
- Vitest: PASS
- Build: PASS

- [ ] **Step 5: Commit**

```bash
git add ui/src/grid.js ui/src/tree.js ui/src/inspector.js ui/styles.css ui/tests/grid.test.js ui/tests/inspector.test.js
git commit -m "feat(ui): densify grid and pane content"
```

---

### Task 6: Wire real theme startup/toggle behavior and run end-to-end verification

**Files:**
- Modify: `ui/index.html`
- Modify: `ui/src/main.js`
- Modify: `ui/src/theme.js`
- Modify: `ui/src/fixtures.js`

- [ ] **Step 1: Write the failing integration test**

Extend `ui/tests/theme.test.js`:

```js
it("updates the toggle label and respects manual override after startup", () => {
  const mediaQuery = {
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  };
  const storage = new Map();
  const root = document.createElement("div");
  const button = document.createElement("button");

  const controller = createThemeController({
    root,
    toggleButton: button,
    storage: {
      getItem: (key) => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, value),
    },
    matchMedia: () => mediaQuery,
  });

  controller.apply();
  expect(root.dataset.theme).toBe("light");
  expect(button.textContent).toContain("Dark Mode");

  controller.toggle();
  expect(root.dataset.theme).toBe("dark");
  expect(button.textContent).toContain("Light Mode");
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
npm run test:ui -- ui/tests/theme.test.js
```

Expected: FAIL because the controller does not yet update a real toggle button or expose `toggle()`.

- [ ] **Step 3: Write minimal implementation**

Update `ui/index.html` main-toolbar actions:

```html
<div class="toolbar-actions">
  <button type="button" class="toolbar-btn" id="toolbar-save-view">Save View</button>
  <button type="button" class="toolbar-btn" id="toolbar-load-view">Load View</button>
  <button type="button" class="toolbar-btn" id="toolbar-theme-toggle">Dark Mode</button>
</div>
```

Extend `ui/src/theme.js`:

```js
export function createThemeController({ root, toggleButton, storage = window.localStorage, matchMedia = window.matchMedia } = {}) {
  const mediaQuery = matchMedia("(prefers-color-scheme: dark)");
  let mode = storage.getItem(STORAGE_KEY);

  const resolveMode = () => (mode ?? (mediaQuery.matches ? "dark" : "light"));
  const sync = () => {
    const activeMode = resolveMode();
    root.dataset.theme = activeMode;
    if (toggleButton != null) {
      toggleButton.textContent = activeMode === "dark" ? "Light Mode" : "Dark Mode";
    }
  };

  return {
    apply: sync,
    setMode(nextMode) {
      mode = nextMode;
      storage.setItem(STORAGE_KEY, nextMode);
      sync();
    },
    toggle() {
      this.setMode(resolveMode() === "dark" ? "light" : "dark");
    },
  };
}
```

Wire `ui/src/main.js`:

```js
const appRoot = document.getElementById("app");
const themeToggle = document.getElementById("toolbar-theme-toggle");
const theme = createThemeController({ root: appRoot, toggleButton: themeToggle });
theme.apply();
themeToggle?.addEventListener("click", () => theme.toggle());
```

Use fixture copy that exposes realistic inspector subtitles for manual demo checks:

```js
summary: {
  name: row?.name ?? "",
  category: row?.category ?? "",
  subtitle: `${row?.category ?? ""} • On hand ${row?.onHand ?? "-"}`,
}
```

- [ ] **Step 4: Run tests and manual verification**

Run:

```bash
npm run test:ui
npm run build
python -m thinghound.ui.app --mock
```

Expected:
- `npm run test:ui`: PASS
- `npm run build`: PASS and `ui/dist/index.html`, `ui/dist/main.js`, `ui/dist/styles.css` all exist
- manual app check:
  - system theme is respected on first launch
  - clicking the toolbar toggle switches theme without changing density
  - top toolbar contains only global actions
  - each pane shows its own compact local toolbar
  - grid rows and headers are visibly smaller and tighter
  - thumbnail column has no header text
  - tree, filter strip, and inspector data rows use the same compact data font size
  - inspector title/subtitle remains clearly larger than repeated metadata rows
  - pane drag/minimize still works

- [ ] **Step 5: Commit**

```bash
git add ui/index.html ui/src/main.js ui/src/theme.js ui/src/fixtures.js ui/tests/theme.test.js
git commit -m "feat(ui): add workspace theme toggle and final dense polish"
```

---

## Self-review

### Spec coverage

- Dense workspace across all panes: Tasks 2, 4, 5, 6
- Shared compact data font size: Task 4 and Task 5 CSS/token work
- Larger inspector selection header: Task 4
- Blank thumbnail header and narrower thumbnail column: Task 3 and Task 5
- Subtle group headers and row striping: Task 5
- Light/dark themes with system startup + manual toggle: Tasks 1 and 6
- Global toolbar vs pane-local toolbars: Tasks 2, 3, and 6
- Build artifacts copied from tracked source CSS: Task 1

### Placeholder scan

- No placeholder markers remain.
- Every task names concrete files and concrete commands.
- Each verification step includes an explicit expected outcome.

### Type and naming consistency

- Theme controller API is consistently `createThemeController`, `apply`, `setMode`, `toggle`.
- Grid helpers are consistently `buildColumns`, `buildGridOptions`, `renderGridToolbar`.
- Inspector summary helper is consistently `renderInspectorSummary`.
