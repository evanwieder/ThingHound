import { initFilterStrip } from "./filterstrip.js";
import { initGrid } from "./grid.js";
import { initInspector } from "./inspector.js";
import { initializeLayout } from "./layout.js";
import { initTree } from "./tree.js";

const bridgeApi = window.pywebview?.api;

if (bridgeApi == null) {
  console.warn("PyWebView API not available; running in standalone layout mode.");
}

initializeLayout();

const leftPane = document.getElementById("pane-left");
const gridRegion = document.querySelector(".grid-region");
const filterRegion = document.getElementById("filter-region");
const rightPane = document.getElementById("pane-right");

if (leftPane != null && gridRegion != null && filterRegion != null && rightPane != null) {
  initGrid(gridRegion, bridgeApi);
  initFilterStrip(filterRegion);
  initInspector(rightPane, bridgeApi);
  initTree(leftPane, bridgeApi, (categoryId) => {
    window.dispatchEvent(new CustomEvent("grid:filter", { detail: { categoryId } }));
  });
}
