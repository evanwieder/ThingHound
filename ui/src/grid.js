import { TabulatorFull as Tabulator } from "tabulator-tables";

function buildColumns(displayColumns) {
  const base = [
    { title: "Thumb", field: "thumbnail", width: 64, hozAlign: "center", formatter: "plaintext" }
  ];
  const dynamic = displayColumns.map((column) => ({
    title: column.title,
    field: column.key,
    headerSort: true
  }));
  return [...base, ...dynamic];
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
      { key: "hero", title: "Hero" },
      { key: "name", title: "Name" },
      { key: "category", title: "Category" },
      { key: "value", title: "Value" },
      { key: "on_hand", title: "On Hand" }
    ];
  }

  const table = new Tabulator(target, {
    data: rows,
    layout: "fitColumns",
    reactiveData: true,
    movableColumns: true,
    virtualDom: true,
    groupBy: "category",
    columns: buildColumns(displayColumns),
    rowClick: (_event, row) => emitSelection(row.getData())
  });

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
