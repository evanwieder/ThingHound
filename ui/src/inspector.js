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

function buildSectionHeader(label) {
  const header = document.createElement("div");
  header.className = "inspector-section";
  header.textContent = label;
  return header;
}

function buildPropertiesTable(entries) {
  const table = document.createElement("div");
  table.className = "inspector-properties";
  for (const [label, value] of entries) {
    const row = document.createElement("div");
    row.className = "inspector-property";

    const labelCell = document.createElement("div");
    labelCell.className = "inspector-property-label";
    labelCell.textContent = label;

    const valueCell = document.createElement("div");
    valueCell.className = "inspector-property-value";
    valueCell.textContent = value == null || value === "" ? "—" : String(value);

    row.append(labelCell, valueCell);
    table.appendChild(row);
  }
  return table;
}

function buildPlaceholder(text) {
  const placeholder = document.createElement("div");
  placeholder.className = "inspector-placeholder";
  placeholder.textContent = text;
  return placeholder;
}

function buildPartDetailsPanel() {
  const panel = document.createElement("div");
  panel.className = "inspector-tab-panel";
  panel.dataset.tabPanel = "Part Details";

  const propertiesSection = buildSectionHeader("Properties");
  const propertiesTable = buildPropertiesTable([]);
  propertiesTable.setAttribute("data-section", "properties");

  const attributesSection = buildSectionHeader("Attributes");
  const attributesTable = buildPropertiesTable([]);
  attributesTable.setAttribute("data-section", "attributes");

  panel.append(propertiesSection, propertiesTable, attributesSection, attributesTable);
  return panel;
}

function renderTabs(tabContainer, contentContainer, tabs) {
  tabContainer.replaceChildren();
  contentContainer.replaceChildren();

  tabs.forEach((tab, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = tab;
    button.className = index === 0 ? "active" : "";

    const panel =
      tab === "Part Details"
        ? buildPartDetailsPanel()
        : (() => {
            const div = document.createElement("div");
            div.className = "inspector-tab-panel";
            div.dataset.tabPanel = tab;
            div.append(buildPlaceholder(`${tab} content`));
            return div;
          })();

    if (index !== 0) {
      panel.classList.add("is-collapsed");
    }

    button.addEventListener("click", () => {
      tabContainer
        .querySelectorAll("button")
        .forEach((node) => node.classList.remove("active"));
      contentContainer
        .querySelectorAll(".inspector-tab-panel")
        .forEach((node) => node.classList.add("is-collapsed"));
      button.classList.add("active");
      panel.classList.remove("is-collapsed");
    });

    tabContainer.appendChild(button);
    contentContainer.appendChild(panel);
  });
}

function updatePartDetailsPanel(panel, properties, attributes) {
  const propertyEntries = Object.entries(properties ?? {});
  const attributeEntries = (attributes ?? []).map((attr) => [attr.name, attr.value]);

  const newPropertiesTable = buildPropertiesTable(propertyEntries);
  newPropertiesTable.setAttribute("data-section", "properties");

  const newAttributesTable = buildPropertiesTable(attributeEntries);
  newAttributesTable.setAttribute("data-section", "attributes");

  const oldProperties = panel.querySelector("[data-section='properties']");
  const oldAttributes = panel.querySelector("[data-section='attributes']");
  oldProperties?.replaceWith(newPropertiesTable);
  oldAttributes?.replaceWith(newAttributesTable);
}

export function initInspector(toolbarTarget, bodyTarget, bridgeApi) {
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

  const tabContainer = document.createElement("div");
  tabContainer.className = "inspector-tabs";

  const content = document.createElement("div");
  content.className = "inspector-content";

  bodyTarget.replaceChildren(header, tabContainer, content);
  renderTabs(tabContainer, content, fallbackTabs);

  function applySummary(item) {
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
      metaParts.push(`${stock} pcs`);
    }
    if (item.status) {
      metaParts.push(item.status);
    }
    if (item.footprint) {
      metaParts.push(item.footprint);
    }
    meta.textContent = metaParts.join(" \u2022 ");
  }

  function defaultPropertiesFor(item) {
    return {
      "Internal ID": item.sku ?? "",
      Name: item.name ?? "",
      SKU: item.sku ?? "",
      "Part Number": item.part_number ?? "",
      Category: item.category ?? "",
      Description: item.description ?? "",
      Footprint: item.footprint ?? "",
      Status: item.status ?? "",
      "Stock Level": item.stock ?? "",
      "Stock Mode": item.stock_mode ?? "",
      "Instance Kind": item.instance_kind ?? "",
      Markings: item.markings || "—"
    };
  }

  function defaultAttributesFor(item) {
    return item.attributes ?? [];
  }

  function applyPropertiesAndAttributes(properties, attributes) {
    const panel = content.querySelector('[data-tab-panel="Part Details"]');
    if (panel == null) {
      return;
    }
    updatePartDetailsPanel(panel, properties, attributes);
  }

  window.addEventListener("row:selected", (event) => {
    const item = event.detail;
    if (item == null) {
      return;
    }
    applySummary(item);
    applyPropertiesAndAttributes(defaultPropertiesFor(item), defaultAttributesFor(item));

    if (bridgeApi == null) {
      return;
    }
    bridgeApi
      .get_inspector_payload({ itemId: item.id })
      .then((payload) => {
        if (payload == null || payload.error != null) {
          return;
        }
        const summary = payload.summary ?? {};
        const enriched = {
          name: summary.name ?? item.name,
          sku: summary.sku ?? item.sku,
          category: summary.category ?? item.category,
          part_number: summary.part_number ?? item.part_number,
          stock: summary.stock ?? item.stock,
          status: summary.status ?? item.status,
          footprint: summary.footprint ?? item.footprint,
          stock_mode: item.stock_mode,
          instance_kind: item.instance_kind,
          markings: item.markings,
          description: summary.description ?? item.description
        };
        applySummary(enriched);
        applyPropertiesAndAttributes(
          payload.properties ?? defaultPropertiesFor(enriched),
          payload.attributes ?? defaultAttributesFor(item)
        );
      })
      .catch((error) => {
        console.error("Failed loading inspector payload", error);
      });
  });
}
