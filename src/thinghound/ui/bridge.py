"""UI bridge between PyWebView and ThingHound services."""


from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from thinghound.ui import fixtures


@dataclass(slots=True)
class Bridge:
    """Expose typed bridge methods for JS calls."""

    mock: bool = False

    def error(
        self,
        code: str,
        message: str,
        *,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a typed error envelope for the frontend."""
        envelope: dict[str, Any] = {"code": code, "message": message}
        if field is not None:
            envelope["field"] = field
        if details is not None:
            envelope["details"] = details
        return envelope

    def grid_query_items(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Return grid rows and total for the UI."""
        return self._call("grid_query_items", filters)

    def _call(self, method_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Route method call to mock data or future live service."""
        if self.mock:
            handler = self._mock_handlers().get(method_name)
            if handler is None:
                return self.error(
                    "INTERNAL_ERROR",
                    f"Unknown mock bridge method: {method_name}",
                )
            try:
                return handler(payload)
            except Exception as exc:  # pragma: no cover - defensive boundary
                return self.error("INTERNAL_ERROR", str(exc))

        return self.error(
            "INTERNAL_ERROR",
            "Live bridge mode is not yet configured.",
        )

    def get_display_columns(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return global display columns used by the heterogeneous grid."""
        del payload
        return self._call("get_display_columns", {})

    def get_column_mappings(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return per-type column mappings for the grid."""
        del payload
        return self._call("get_column_mappings", {})

    def get_category_tree(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return category tree for left-pane filtering."""
        del payload
        return self._call("get_category_tree", {})

    def get_inspector_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return inspector payload for selected item."""
        return self._call("get_inspector_payload", payload)

    def _mock_handlers(self) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
        """Return handlers that serve fixture-shaped contract responses."""
        return {
            "grid_query_items": self._mock_grid_query_items,
            "get_display_columns": lambda _payload: {"columns": fixtures.DISPLAY_COLUMNS},
            "get_column_mappings": lambda _payload: {"mappings": fixtures.COLUMN_MAPPINGS},
            "get_category_tree": lambda _payload: {"nodes": fixtures.CATEGORY_TREE},
            "get_inspector_payload": self._mock_get_inspector_payload,
        }

    def _mock_grid_query_items(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return filtered mock grid rows and total count."""
        category_id = str(payload.get("categoryId", "")).lower()
        quick_search = str(payload.get("quickSearch", "")).lower().strip()

        rows = fixtures.GRID_ROWS
        if category_id and category_id != "root":
            needle = category_id.rstrip("s")
            rows = [row for row in rows if str(row["category"]).lower().startswith(needle)]
        if quick_search:
            rows = [
                row
                for row in rows
                if quick_search in str(row["name"]).lower()
                or quick_search in str(row["category"]).lower()
                or quick_search in str(row["value"]).lower()
            ]

        return {"rows": rows, "total": len(rows)}

    def _mock_get_inspector_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return summary and tab payload for selected item."""
        item_id = payload.get("itemId")
        for row in fixtures.GRID_ROWS:
            if row["id"] == item_id:
                return {
                    "summary": {
                        "name": row["name"],
                        "category": row["category"],
                        "on_hand": row["on_hand"]["display"],
                        "hero": row["hero"],
                    },
                    "tabs": {
                        tab: {"content": f"{tab} fixture content for {row['name']}"}
                        for tab in fixtures.INSPECTOR_TABS
                    },
                }

        return self.error("NOT_FOUND", "Item not found", field="itemId")
