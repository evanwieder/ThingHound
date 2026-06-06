const fallbackTabs = [
  "Part Details",
  "Stock History",
  "Parameters",
  "Vendors",
  "Alternates",
  "BOM/Where-used"
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
  subtitle.textContent = "No item selected";

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
  if (item?.sku) {
    subtitleParts.push(item.sku);
  }
  if (item?.category) {
    subtitleParts.push(item.category);
  }
  if (item?.part_number) {
    subtitleParts.push(`MPN ${item.part_number}`);
  }
  subtitle.textContent = subtitleParts.join(" \u2022 ");

  const meta = document.createElement("div");
  meta.className = "inspector-meta";
  const stock = item?.stock ?? item?.on_hand ?? "-";
  const status = item?.status ?? "";
  const footprint = item?.footprint ?? "";
  const metaParts = [];
  if (stock) {
    metaParts.push(`Stock ${stock}`);
  }
  if (status) {
    metaParts.push(status);
  }
  if (footprint) {
    metaParts.push(footprint);
  }
  meta.textContent = metaParts.join(" \u2022 ");

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
    const subtitleParts = [];
    if (item.sku) {
      subtitleParts.push(item.sku);
    }
    if (item.category) {
      subtitleParts.push(item.category);
    }
    if (item.part_number) {
      subtitleParts.push(`MPN ${item.part_number}`);
    }
    subtitle.textContent = subtitleParts.join(" \u2022 ");
    const metaParts = [];
    const stock = item.stock ?? item.on_hand ?? item.onHand;
    if (stock != null && stock !== "") {
      metaParts.push(`Stock ${stock}`);
    }
    if (item.status) {
      metaParts.push(item.status);
    }
    if (item.footprint) {
      metaParts.push(item.footprint);
    }
    meta.textContent = metaParts.join(" \u2022 ");
    renderTabs(tabContainer, content, tabs, item.name ?? "item");
  };

  window.addEventListener("row:selected", async (event) => {
    const item = event.detail;
    const fallback = {
      name: item.name,
      sku: item.sku,
      category: item.category,
      part_number: item.part_number,
      stock: item.stock,
      status: item.status,
      footprint: item.footprint
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
        sku: summary.sku ?? item.sku,
        category: summary.category ?? item.category,
        part_number: summary.part_number ?? item.part_number,
        stock: summary.stock ?? item.stock,
        status: summary.status ?? item.status,
        footprint: summary.footprint ?? item.footprint
      };
      applyItem(enriched, tabNames.length > 0 ? tabNames : fallbackTabs);
    } catch (error) {
      console.error("Failed loading inspector payload", error);
    }
  });
}
