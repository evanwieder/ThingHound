import { categoryTree, columnMappings, displayColumns, gridRows, inspectorTabs } from "./fixtures.js";

export function createBridgeApi(pywebviewApi) {
  const hasPywebviewBridge = pywebviewApi != null;

  async function call(methodName, payload = {}) {
    if (!hasPywebviewBridge) {
      return null;
    }

    const method = pywebviewApi[methodName];
    if (typeof method !== "function") {
      throw new Error(`Bridge method is not available: ${methodName}`);
    }

    return method(payload);
  }

  return {
    hasPywebviewBridge,
    call,
    async get_display_columns(payload = {}) {
      const response = await call("get_display_columns", payload);
      if (response != null) {
        return response;
      }
      return { columns: displayColumns };
    },
    async get_column_mappings(payload = {}) {
      const response = await call("get_column_mappings", payload);
      if (response != null) {
        return response;
      }
      return { mappings: columnMappings };
    },
    async get_category_tree(payload = {}) {
      const response = await call("get_category_tree", payload);
      if (response != null) {
        return response;
      }
      return { nodes: categoryTree };
    },
    async grid_query_items(payload = {}) {
      const response = await call("grid_query_items", payload);
      if (response != null) {
        return response;
      }
      const categoryId = String(payload?.categoryId ?? "").toLowerCase();
      const quickSearch = String(payload?.quickSearch ?? "").toLowerCase().trim();
      let rows = gridRows;
      if (categoryId && categoryId !== "root") {
        rows = rows.filter((row) =>
          (row.category_path ?? []).map((id) => String(id).toLowerCase()).includes(categoryId)
        );
      }
      if (quickSearch) {
        rows = rows.filter(
          (row) =>
            quickSearch in String(row.name ?? "").toLowerCase() ||
            quickSearch in String(row.sku ?? "").toLowerCase() ||
            quickSearch in String(row.category ?? "").toLowerCase() ||
            quickSearch in String(row.description ?? "").toLowerCase()
        );
      }
      return { rows, total: rows.length };
    },
    async get_inspector_payload(payload = {}) {
      const response = await call("get_inspector_payload", payload);
      if (response != null) {
        return response;
      }
      const row = gridRows.find((item) => item.id === payload.itemId) ?? gridRows[0];
      return {
        summary: {
          name: row?.name ?? "",
          sku: row?.sku ?? "",
          category: row?.category ?? "",
          stock: row?.stock ?? "",
          status: row?.status ?? "",
          footprint: row?.footprint ?? "",
          part_number: row?.part_number ?? "",
          description: row?.description ?? "",
        },
        tabs: Object.fromEntries(
          inspectorTabs.map((tab) => [tab, { content: `${tab} fixture content for ${row?.name ?? "item"}` }]),
        ),
      };
    },
  };
}
