import { createBridgeApi } from "./bridge-api.js";
import { initFilterStrip } from "./filterstrip.js";
import { initGrid, renderGridToolbar } from "./grid.js";
import { initInspector, renderInspectorToolbar } from "./inspector.js";
import { initializeLayout } from "./layout.js";
import { createThemeController } from "./theme.js";
import { initTree, renderTreeToolbar } from "./tree.js";

const appRoot = document.getElementById("app");
const themeToggle = document.getElementById("toolbar-theme-toggle");
const theme = createThemeController({ root: appRoot, toggleButton: themeToggle });
theme.apply();
themeToggle?.addEventListener("click", () => theme.toggle());

const bridgeApi = createBridgeApi(window.pywebview?.api);

if (!bridgeApi.hasPywebviewBridge) {
  console.warn("PyWebView API not available; running in standalone layout mode.");
}

initializeLayout();

const treeToolbar = document.querySelector('[data-pane-toolbar="tree"]');
const treeBody = document.getElementById("tree-region");
const gridToolbar = document.querySelector('[data-pane-toolbar="grid"]');
const gridRegion = document.getElementById("grid-region");
const filterRegion = document.getElementById("filter-region");
const inspectorToolbar = document.querySelector('[data-pane-toolbar="inspector"]');
const inspectorBody = document.getElementById("inspector-region");

if (gridRegion != null && filterRegion != null) {
  if (gridToolbar != null) {
    renderGridToolbar(gridToolbar);
  }
  initGrid(gridRegion, bridgeApi);
  initFilterStrip(filterRegion);
}

if (treeBody != null && treeToolbar != null) {
  initTree(treeToolbar, treeBody, bridgeApi, (categoryId) => {
    window.dispatchEvent(new CustomEvent("grid:filter", { detail: { categoryId } }));
  });
}

if (inspectorBody != null && inspectorToolbar != null) {
  renderInspectorToolbar(inspectorToolbar);
  initInspector(inspectorToolbar, inspectorBody, bridgeApi);
}
