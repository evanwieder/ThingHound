const MIN_LEFT = 36;
const MIN_RIGHT = 36;
const MIN_CENTER = 320;
const MIN_FILTER = 28;

function setupHorizontalSashes(workspace, leftPane, rightPane) {
  const leftSash = workspace.querySelector('[data-sash="left"]');
  const rightSash = workspace.querySelector('[data-sash="right"]');

  leftSash?.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = leftPane.getBoundingClientRect().width;

    const onMove = (moveEvent) => {
      const width = Math.max(MIN_LEFT, startWidth + (moveEvent.clientX - startX));
      workspace.style.setProperty("--left-width", `${width}px`);
    };

    const onUp = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  });

  rightSash?.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = rightPane.getBoundingClientRect().width;

    const onMove = (moveEvent) => {
      const width = Math.max(MIN_RIGHT, startWidth - (moveEvent.clientX - startX));
      workspace.style.setProperty("--right-width", `${width}px`);
    };

    const onUp = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  });
}

function setupFilterSash(centerPane) {
  const bottomSash = centerPane.querySelector('[data-sash="bottom"]');
  const filterRegion = centerPane.querySelector("#filter-region");

  bottomSash?.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    const startY = event.clientY;
    const startHeight = filterRegion.getBoundingClientRect().height;

    const onMove = (moveEvent) => {
      const height = Math.max(MIN_FILTER, startHeight - (moveEvent.clientY - startY));
      centerPane.style.setProperty("--filter-height", `${height}px`);
    };

    const onUp = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  });
}

function createRestoreBar({ parent, id, label, className, onRestore }) {
  const bar = document.createElement("button");
  bar.id = id;
  bar.type = "button";
  bar.className = `restore-bar ${className}`;
  bar.textContent = label;
  bar.addEventListener("click", onRestore);
  parent.appendChild(bar);
  return bar;
}

function setupPaneMinimize(workspace, leftPane, rightPane, centerPane) {
  const leftRestore = createRestoreBar({
    parent: workspace,
    id: "restore-left",
    label: "◀",
    className: "restore-left is-collapsed",
    onRestore: () => {
      leftPane.classList.remove("is-collapsed");
      workspace.querySelector('[data-sash="left"]')?.classList.remove("is-collapsed");
      leftRestore.classList.add("is-collapsed");
      workspace.style.setProperty("--left-width", `${Math.max(MIN_LEFT, 260)}px`);
      syncCenterBounds(workspace);
    },
  });

  const rightRestore = createRestoreBar({
    parent: workspace,
    id: "restore-right",
    label: "▶",
    className: "restore-right is-collapsed",
    onRestore: () => {
      rightPane.classList.remove("is-collapsed");
      workspace.querySelector('[data-sash="right"]')?.classList.remove("is-collapsed");
      rightRestore.classList.add("is-collapsed");
      workspace.style.setProperty("--right-width", `${Math.max(MIN_RIGHT, 320)}px`);
      syncCenterBounds(workspace);
    },
  });

  const filterRegion = centerPane.querySelector("#filter-region");
  const filterSash = centerPane.querySelector('[data-sash="bottom"]');
  const filterRestore = createRestoreBar({
    parent: centerPane,
    id: "restore-filter",
    label: "▲",
    className: "restore-filter is-collapsed",
    onRestore: () => {
      filterRegion.classList.remove("is-collapsed");
      filterSash?.classList.remove("is-collapsed");
      filterRestore.classList.add("is-collapsed");
      centerPane.style.setProperty("--filter-height", `${Math.max(MIN_FILTER, 160)}px`);
    },
  });

  leftPane.addEventListener("dblclick", () => {
    leftPane.classList.add("is-collapsed");
    workspace.querySelector('[data-sash="left"]')?.classList.add("is-collapsed");
    leftRestore.classList.remove("is-collapsed");
    workspace.style.setProperty("--left-width", `${MIN_LEFT}px`);
    syncCenterBounds(workspace);
  });

  rightPane.addEventListener("dblclick", () => {
    rightPane.classList.add("is-collapsed");
    workspace.querySelector('[data-sash="right"]')?.classList.add("is-collapsed");
    rightRestore.classList.remove("is-collapsed");
    workspace.style.setProperty("--right-width", `${MIN_RIGHT}px`);
    syncCenterBounds(workspace);
  });

  filterRegion.addEventListener("dblclick", () => {
    filterRegion.classList.add("is-collapsed");
    filterSash?.classList.add("is-collapsed");
    filterRestore.classList.remove("is-collapsed");
    centerPane.style.setProperty("--filter-height", `${MIN_FILTER}px`);
  });
}

function syncCenterBounds(workspace) {
  const totalWidth = workspace.getBoundingClientRect().width;
  const leftWidth = parseFloat(getComputedStyle(workspace).getPropertyValue("--left-width")) || MIN_LEFT;
  const rightWidth = parseFloat(getComputedStyle(workspace).getPropertyValue("--right-width")) || MIN_RIGHT;
  const available = totalWidth - leftWidth - rightWidth - 12;
  if (available < MIN_CENTER) {
    const deficit = MIN_CENTER - available;
    const reducedRight = Math.max(MIN_RIGHT, rightWidth - deficit);
    workspace.style.setProperty("--right-width", `${reducedRight}px`);
  }
}

export function initializeLayout() {
  const workspace = document.getElementById("workspace");
  const leftPane = document.getElementById("pane-left");
  const rightPane = document.getElementById("pane-right");
  const centerPane = document.getElementById("pane-center");

  if (workspace == null || leftPane == null || rightPane == null || centerPane == null) {
    throw new Error("Layout root elements not found.");
  }

  setupHorizontalSashes(workspace, leftPane, rightPane);
  setupFilterSash(centerPane);
  setupPaneMinimize(workspace, leftPane, rightPane, centerPane);
  syncCenterBounds(workspace);
}
