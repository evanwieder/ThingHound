# Compact Workspace Density — Design
**Date:** 2026-06-04
**Status:** Approved in conversation (pending written review)

---

## Why this exists

The first working grid now exists, but it does not yet support the density the demo needs. Rows are too tall, repeated text is too large, padding consumes useful width, and group-header contrast is visually jarring. The whole three-pane workspace should behave more like a dense desktop inventory tool: compact, scannable, and clearly centered on the selected item.

This is explicitly a **first pass for a demo**, not a final visual system. The goal is to make the current UI convincingly usable for demonstration without expanding scope into broader product redesign or data-layer changes.

---

## Goals

1. Make the entire workspace materially denser so more information fits on screen.
2. Apply one compact data-text scale across the left tree, center grid, filter strip, and right inspector data rows.
3. Keep the center grid as the primary information surface while making the side panes visually quieter.
4. Retain grouped rows in the grid, but reduce the contrast between group headers and data rows.
5. Support both light mode and dark mode while keeping density identical in each theme.
6. Preserve the current interaction model: grid selection drives the inspector.
7. Separate global actions from pane-local actions with a clear toolbar structure.

---

## Non-goals

1. No bridge-contract or data-model changes.
2. No change to grouping logic beyond presentation.
3. No change to tree semantics or inspector information architecture beyond presentation hierarchy.
4. No attempt to finalize the long-term product visual identity in this pass.
5. No generated-file-first workflow; tracked source UI assets become the source of truth.

---

## Locked decisions

### Density and typography

- The workspace is optimized for **maximum density first**.
- Repeated data surfaces use **one shared compact font size**:
  - grid cells
  - grid headers
  - tree rows
  - filter labels and controls
  - inspector labels and values
- Grid headers use the **same size** as data text, but are **bold**.
- Pane/frame headers may remain larger than data text.
- The right-inspector **selected-item title and subtitle area** is intentionally larger and more prominent than the compact data rows below it, to clearly indicate what the center-grid selection is driving.

### Grid behavior

- Grid cells stay **single-line** with ellipsis.
- The thumbnail column remains visible, but becomes narrower.
- The thumbnail column header text is removed entirely.
- Grouping remains enabled.
- Group headers are rendered as **subtle section labels**, not heavy visual bands.
- Alternate row striping is present but **very subtle**.

### Workspace scope

- The first pass restyles the **whole three-pane workspace**, not only the center grid.
- The left tree and right inspector should share the same dense rhythm as the center area, while remaining visually secondary to the main data table.

### Theme behavior

- Both **light mode** and **dark mode** are supported in this pass.
- Initial theme follows the **system preference**.
- The UI also includes a **visible theme toggle** so the user can switch modes manually after startup.
- Light and dark themes share the same spacing, sizing, and layout rules; only tokens/palette differ.

### Toolbar model

- The main window toolbar is reserved for **global actions** that apply across the workspace.
- Each pane gets its own **small local toolbar at the top** for actions specific to that pane.
- Pane-local toolbars use the same compact visual language as the rest of the demo.
- The split between global and local actions should be obvious from placement, not only from icon or label wording.

---

## Visual direction

The target UX is similar to a dense desktop parts/inventory application:

- compact rows
- narrow columns
- restrained separators
- low-contrast section headers
- enough hierarchy to keep orientation clear without wasting space

The center grid should feel tight and information-rich. The tree and inspector should feel supportive rather than ornamental. The result should read as a practical desktop tool, not a roomy marketing-style web UI.

---

## Component design

### Main window toolbar

- Keep the top toolbar for **global actions only**.
- Add the theme toggle here.
- Global toolbar actions may include things like saving and loading grid views, workspace setups, or other app-wide state.
- Keep toolbar visuals secondary to the workspace below.
- Toolbar controls remain usable, but should not establish the primary density scale for repeated data.

### Pane-local toolbars

- Each pane gets a small toolbar at its top edge.
- These toolbars are for **pane-specific actions only**.
- They should be compact, low-noise, and visually integrated with the pane they control.
- They provide the action boundary for the three workspace regions:
  - tree pane actions stay with the tree
  - grid pane actions stay with the grid
  - inspector actions stay with the inspector

### Left tree

- Add a compact pane-local toolbar above the tree content.
- Expected actions include collapse-all, expand-all, search, and tree-edit actions when that editing surface exists.
- Reduce row height and indentation spacing.
- Use the shared compact data font size.
- Keep expand/collapse affordances, but tighten icon spacing.
- Selected-node styling should be clear without a loud block fill.

### Center grid

- Add a compact pane-local toolbar above the grid.
- Expected actions include configuring display columns, selecting a grid configuration from a dropdown, editing grid configurations, and other grid-specific controls.
- Add a tracked source stylesheet that intentionally overrides Tabulator defaults.
- Reduce header height, row height, cell padding, and column-header spacing aggressively.
- Keep header text equal in size to cell text, but bold.
- Maintain one-line cells with ellipsis.
- Keep grouping, but render group headers with subtle separation and low contrast.
- Keep the thumbnail column, shrink it, and remove its header text.
- Use very subtle row striping to help scanning without introducing noise.

### Filter strip

- Use the shared compact data font size.
- Tighten label/control spacing substantially.
- Avoid oversized empty padding blocks.
- Keep the filter area visually subordinate to the grid.

### Right inspector

- Add a compact pane-local toolbar above the inspector content.
- Expected actions include editing the current item, adjusting inventory, and other selection-specific inspector actions.
- Keep the selected-item title/subtitle area larger and more prominent than the repeated data rows.
- Use the shared compact data font size for labels and values below that header.
- Tighten key/value row spacing while preserving alignment.
- Internal section headers may be slightly larger than data rows, but clearly below the title/subtitle emphasis.

---

## Implementation boundaries

The first pass is presentation-focused and bounded:

- no schema changes
- no bridge API changes
- no new selection model
- no restructuring of inspector content
- no change to category-tree meaning

The implementation should focus on:

1. establishing a tracked source stylesheet at `ui/styles.css`
2. wiring the build so the source stylesheet is copied into `ui/dist/`
3. introducing a clear global-toolbar vs pane-toolbar layout
4. adding compact workspace theme tokens and dense component rules
5. overriding Tabulator spacing and group-header presentation intentionally
6. adding theme-toggle behavior without changing the current data flow

---

## Expected code impact

- `ui/styles.css` (new): source of truth for workspace theme tokens, dense sizing, Tabulator overrides, tree/filter/inspector styling
- `ui/src/layout.js`: pane sizing and collapse behavior kept compatible with the new toolbar structure
- `ui/src/grid.js`: compact column behavior, blank thumbnail header, and any Tabulator configuration required to support the dense presentation
- `ui/index.html`: main toolbar markup and pane-toolbar markup
- `ui/src/main.js`: theme initialization and toggle wiring
- `package.json`: build step updated so `ui/styles.css` is copied into `ui/dist/`

Generated output under `ui/dist/` should be treated as build artifacts, not as the design source of truth.

---

## Acceptance criteria

1. The grid is materially denser than the current version: smaller font, shorter rows, less padding, and more visible data per line.
2. Grid headers use the same text size as grid data, but remain bold.
3. Left tree rows, filter controls, and inspector data rows use the same compact data font size.
4. The right inspector title/subtitle area is visibly larger than inspector data rows and clearly tracks the current selection.
5. The thumbnail column remains visible but narrower, with no header text.
6. Group headers remain present, but their contrast is softened enough that they no longer dominate the grid.
7. Alternate row striping is visible but subtle.
8. Both light and dark themes render correctly.
9. Initial theme follows the system preference.
10. A visible UI toggle allows switching themes manually.
11. The main window toolbar contains global actions only.
12. Each pane has a compact local toolbar for pane-specific actions.
13. Pane resizing/collapse continues to work after the restyle.

---

## Risks and controls

### Risk: density changes reduce legibility

Control:
- keep the selected-item title/subtitle area larger
- keep bold headers in the grid
- use subtle striping and selection styling to preserve scanability

### Risk: theme support doubles styling work

Control:
- unify spacing and component rules across themes
- limit theme variation to palette tokens and a few surface treatments

### Risk: Tabulator defaults fight the intended dense layout

Control:
- centralize overrides in the source stylesheet
- make only the minimum supporting adjustments in `ui/src/grid.js`
