import { TabulatorFull as Tabulator } from "tabulator-tables";

const THUMBNAIL_WIDTH = 36;

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

function buildToolbarSelect(label, options) {
  const wrap = document.createElement("label");
  wrap.className = "pane-toolbar-select";

  const text = document.createElement("span");
  text.className = "pane-toolbar-label";
  text.textContent = label;
  wrap.appendChild(text);

  const select = document.createElement("select");
  for (const value of options) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  }
  wrap.appendChild(select);
  return wrap;
}

export function buildColumns(displayColumns) {
  const base = [
    {
      title: "",
      field: "thumbnail",
      width: THUMBNAIL_WIDTH,
      hozAlign: "center",
      headerSort: false,
      resizable: false,
      formatter: "plaintext"
    }
  ];
  const dynamic = displayColumns.map((column) => ({
    title: column.title,
    field: column.key,
    headerSort: true
  }));
  return [...base, ...dynamic];
}

export function buildGridOptions({ rows, displayColumns, onRowSelected }) {
  return {
    data: rows,
    layout: "fitColumns",
    reactiveData: true,
    movableColumns: true,
    virtualDom: true,
    rowHeight: 22,
    columnHeaderVertAlign: "middle",
    groupBy: "category_path_display",
    groupHeader: (value, count) => `<span class="group-path">${value}</span> <span class="group-count">(${count} part${count === 1 ? "" : "s"})</span>`,
    columns: buildColumns(displayColumns),
    rowClick: (_event, row) => onRowSelected(row.getData())
  };
}

export function renderGridToolbar(target) {
  const viewSelect = buildToolbarSelect("View", ["Default", "Electrical", "Mechanical"]);
  const columnsButton = buildToolbarButton("Columns");
  const editViewsButton = buildToolbarButton("Edit Views");

  target.replaceChildren(columnsButton, viewSelect, editViewsButton);

  columnsButton.addEventListener("click", () => {
    window.dispatchEvent(new CustomEvent("grid:request-columns"));
  });
  editViewsButton.addEventListener("click", () => {
    window.dispatchEvent(new CustomEvent("grid:request-edit-views"));
  });
}

function emitSelection(rowData) {
  window.dispatchEvent(new CustomEvent("row:selected", { detail: rowData }));
}

export async function initGrid(target, bridgeApi) {
  let displayColumns = [];
  let rows = [];

  if (bridgeApi != null) {
    try {
      const [columnsResponse, queryResponse] = await Promise.all([
        bridgeApi.get_display_columns({}),
        bridgeApi.grid_query_items({})
      ]);
      displayColumns = columnsResponse.columns ?? [];
      rows = queryResponse.rows ?? [];
    } catch (error) {
      console.error("Failed loading grid data from bridge", error);
    }
  }

  if (displayColumns.length === 0) {
    displayColumns = [
      { key: "name", title: "Name" },
      { key: "sku", title: "SKU" },
      { key: "description", title: "Description" },
      { key: "stock", title: "Stock" },
      { key: "status", title: "Status" },
      { key: "footprint", title: "Footprint" }
    ];
  }

  const table = new Tabulator(target, buildGridOptions({
    rows,
    displayColumns,
    onRowSelected: emitSelection
  }));

  const reloadRows = async (filters = {}) => {
    if (bridgeApi == null) {
      table.redraw(true);
      return;
    }
    const response = await bridgeApi.grid_query_items(filters);
    await table.replaceData(response.rows ?? []);
    table.redraw(true);
  };

  window.addEventListener("grid:filter", async (event) => {
    await reloadRows(event.detail ?? {});
  });

  window.addEventListener("layout:changed", async () => {
    await reloadRows({});
  });

  table.on("tableBuilt", () => {
    const first = table.getRows()[0];
    if (first != null) {
      emitSelection(first.getData());
    }
  });
}
