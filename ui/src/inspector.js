const fallbackTabs = [
  "Attributes",
  "Stock & Events",
  "Instances",
  "Vendors",
  "Alternates",
  "BOM/Where-used",
  "Simulation"
];

function buildToolbarButton(label, { title } = {}) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "pane-toolbar-btn";
  button.textContent = label;
  if (title != null) {
    button.title = title;
  }
  return button;
}

export function renderInspectorToolbar(target) {
  const editButton = buildToolbarButton("Edit Item");
  const adjustButton = buildToolbarButton("Adjust Inventory");

  target.replaceChildren(editButton, adjustButton);

  editButton.addEventListener("click", () => {
    window.dispatchEvent(new CustomEvent("inspector:request-edit"));
  });
  adjustButton.addEventListener("click", () => {
    window.dispatchEvent(new CustomEvent("inspector:request-adjust"));
  });
}

function createSummary() {
  const title = document.createElement("div");
  title.className = "inspector-title";
  title.textContent = "Select an item";

  const subtitle = document.createElement("div");
  subtitle.className = "inspector-subtitle";
  subtitle.textContent = "";

  const meta = document.createElement("div");
  meta.className = "inspector-meta";
  meta.textContent = "";

  const header = document.createElement("div");
  header.className = "inspector-header";
  header.append(title, subtitle, meta);

  return { header, title, subtitle, meta };
}

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

export function renderInspectorSummary(target, item) {
  const title = document.createElement("div");
  title.className = "inspector-title";
  title.textContent = item?.name ?? "Select an item";

  const subtitle = document.createElement("div");
  subtitle.className = "inspector-subtitle";
  const subtitleParts = [];
  if (item?.category) {
    subtitleParts.push(item.category);
  }
  if (item?.hero) {
    subtitleParts.push(item.hero);
  }
  subtitle.textContent = subtitleParts.join(" \u2022 ");

  const meta = document.createElement("div");
  meta.className = "inspector-meta";
  const onHand = item?.on_hand?.display ?? item?.on_hand ?? item?.onHand ?? "-";
  meta.textContent = `On hand ${onHand}`;

  const header = document.createElement("div");
  header.className = "inspector-header";
  header.append(title, subtitle, meta);

  target.replaceChildren(header);
}

export function initInspector(toolbarTarget, bodyTarget, bridgeApi) {
  const { header, title, subtitle, meta } = createSummary();
  const tabContainer = document.createElement("div");
  tabContainer.className = "inspector-tabs";

  const content = document.createElement("div");
  content.className = "inspector-content";

  bodyTarget.replaceChildren(header, tabContainer, content);
  renderTabs(tabContainer, content, fallbackTabs, "item");

  const applyItem = (item, tabs) => {
    title.textContent = item.name ?? "Select an item";
    const parts = [];
    if (item.category) {
      parts.push(item.category);
    }
    if (item.hero) {
      parts.push(item.hero);
    }
    subtitle.textContent = parts.join(" \u2022 ");
    const onHand = item.on_hand?.display ?? item.on_hand ?? item.onHand ?? "-";
    meta.textContent = `On hand ${onHand}`;
    renderTabs(tabContainer, content, tabs, item.name ?? "item");
  };

  window.addEventListener("row:selected", async (event) => {
    const item = event.detail;
    const fallback = {
      name: item.name,
      category: item.category,
      hero: item.hero,
      on_hand: item.on_hand
    };
    applyItem(fallback, fallbackTabs);

    if (bridgeApi == null) {
      return;
    }
    try {
      const payload = await bridgeApi.get_inspector_payload({ itemId: item.id });
      const summary = payload.summary ?? {};
      const tabNames = Object.keys(payload.tabs ?? {});
      const enriched = {
        name: summary.name ?? item.name,
        category: summary.category ?? item.category,
        hero: summary.hero ?? item.hero,
        on_hand: summary.on_hand ?? item.on_hand
      };
      applyItem(enriched, tabNames.length > 0 ? tabNames : fallbackTabs);
    } catch (error) {
      console.error("Failed loading inspector payload", error);
    }
  });
}
