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
      return { rows: gridRows, total: gridRows.length };
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
          category: row?.category ?? "",
          on_hand: row?.onHand ?? "",
          hero: row?.hero ?? "",
        },
        tabs: Object.fromEntries(
          inspectorTabs.map((tab) => [tab, { content: `${tab} fixture content for ${row?.name ?? "item"}` }]),
        ),
      };
    },
  };
}
