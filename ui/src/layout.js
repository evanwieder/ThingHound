const MIN_LEFT = 36;
const MIN_RIGHT = 36;
const MIN_CENTER = 320;
const MIN_FILTER = 28;

function setupHorizontalSashes(workspace, leftPane, rightPane) {
  const leftSash = workspace.querySelector('[data-sash="left"]');
  const rightSash = workspace.querySelector('[data-sash="right"]');

  leftSash?.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    const workspaceRect = workspace.getBoundingClientRect();

    const onMove = (moveEvent) => {
      const width = Math.max(MIN_LEFT, moveEvent.clientX - workspaceRect.left);
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
    const workspaceRect = workspace.getBoundingClientRect();

    const onMove = (moveEvent) => {
      const width = Math.max(MIN_RIGHT, workspaceRect.right - moveEvent.clientX);
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

function notifyLayoutChanged() {
  requestAnimationFrame(() => {
    window.dispatchEvent(new Event("resize"));
    window.dispatchEvent(new Event("layout:changed"));
  });
}

function setupPaneMinimize(workspace, leftPane, rightPane, centerPane) {
  const leftSash = workspace.querySelector('[data-sash="left"]');
  const rightSash = workspace.querySelector('[data-sash="right"]');
  const leftRestore = createRestoreBar({
    parent: workspace,
    id: "restore-left",
    label: "◀",
    className: "restore-left is-collapsed",
    onRestore: () => {
      leftPane.classList.remove("is-collapsed");
      leftSash?.classList.remove("is-collapsed");
      leftRestore.classList.add("is-collapsed");
      workspace.style.setProperty("--left-width", `${Math.max(MIN_LEFT, 260)}px`);
      syncCenterBounds(workspace);
      notifyLayoutChanged();
    },
  });

  const rightRestore = createRestoreBar({
    parent: workspace,
    id: "restore-right",
    label: "▶",
    className: "restore-right is-collapsed",
    onRestore: () => {
      rightPane.classList.remove("is-collapsed");
      rightSash?.classList.remove("is-collapsed");
      rightRestore.classList.add("is-collapsed");
      workspace.style.setProperty("--right-width", `${Math.max(MIN_RIGHT, 320)}px`);
      syncCenterBounds(workspace);
      notifyLayoutChanged();
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
      notifyLayoutChanged();
    },
  });

  leftPane.addEventListener("dblclick", () => {
    leftPane.classList.add("is-collapsed");
    leftSash?.classList.add("is-collapsed");
    leftRestore.classList.remove("is-collapsed");
    workspace.style.setProperty("--left-width", "0px");
    syncCenterBounds(workspace);
    notifyLayoutChanged();
  });

  rightPane.addEventListener("dblclick", () => {
    rightPane.classList.add("is-collapsed");
    rightSash?.classList.add("is-collapsed");
    rightRestore.classList.remove("is-collapsed");
    workspace.style.setProperty("--right-width", "0px");
    syncCenterBounds(workspace);
    notifyLayoutChanged();
  });

  filterRegion.addEventListener("dblclick", () => {
    filterRegion.classList.add("is-collapsed");
    filterSash?.classList.add("is-collapsed");
    filterRestore.classList.remove("is-collapsed");
    centerPane.style.setProperty("--filter-height", `${MIN_FILTER}px`);
    notifyLayoutChanged();
  });
}

function syncCenterBounds(workspace) {
  const totalWidth = workspace.getBoundingClientRect().width;
  const leftValue = parseFloat(getComputedStyle(workspace).getPropertyValue("--left-width"));
  const rightValue = parseFloat(getComputedStyle(workspace).getPropertyValue("--right-width"));
  const leftWidth = Number.isNaN(leftValue) ? MIN_LEFT : leftValue;
  const rightWidth = Number.isNaN(rightValue) ? MIN_RIGHT : rightValue;
  const available = totalWidth - leftWidth - rightWidth - 12;
  if (available < MIN_CENTER) {
    const deficit = MIN_CENTER - available;
    const reducedRight = Math.max(0, rightWidth - deficit);
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
