const fallbackTabs = [
  "Attributes",
  "Stock & Events",
  "Instances",
  "Vendors",
  "Alternates",
  "BOM/Where-used",
  "Simulation"
];

function renderTabs(tabContainer, contentContainer, tabs, activeItemName) {
  tabContainer.replaceChildren();
  contentContainer.replaceChildren();

  tabs.forEach((tab, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = tab;
    button.className = index === 0 ? "active" : "";

    const panel = document.createElement("div");
    panel.textContent = `${tab} fixture content for ${activeItemName}`;
    panel.className = index === 0 ? "active" : "is-collapsed";

    button.addEventListener("click", () => {
      tabContainer.querySelectorAll("button").forEach((node) => node.classList.remove("active"));
      contentContainer.querySelectorAll("div").forEach((node) => node.classList.add("is-collapsed"));
      button.classList.add("active");
      panel.classList.remove("is-collapsed");
    });

    tabContainer.appendChild(button);
    contentContainer.appendChild(panel);
  });
}

export function initInspector(target, bridgeApi) {
  const summary = document.createElement("div");
  summary.className = "inspector-summary";
  summary.textContent = "Select an item";

  const tabContainer = document.createElement("div");
  tabContainer.className = "inspector-tabs";

  const content = document.createElement("div");
  content.className = "inspector-content";

  renderTabs(tabContainer, content, fallbackTabs, "item");
  target.replaceChildren(summary, tabContainer, content);

  window.addEventListener("row:selected", async (event) => {
    const item = event.detail;
    summary.textContent = `${item.name} • ${item.category} • On hand ${item.on_hand?.display ?? item.onHand ?? "-"}`;

    if (bridgeApi == null) {
      renderTabs(tabContainer, content, fallbackTabs, item.name);
      return;
    }

    try {
      const payload = await bridgeApi.get_inspector_payload({ itemId: item.id });
      const tabNames = Object.keys(payload.tabs ?? {});
      renderTabs(tabContainer, content, tabNames.length > 0 ? tabNames : fallbackTabs, item.name);
    } catch (error) {
      console.error("Failed loading inspector payload", error);
      renderTabs(tabContainer, content, fallbackTabs, item.name);
    }
  });
}
