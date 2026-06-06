function debounce(callback, waitMs) {
  let timeoutId;
  return (value) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => callback(value), waitMs);
  };
}

function buildLabeledControl(labelText, control) {
  const wrap = document.createElement("label");
  wrap.className = "filter-control";
  const label = document.createElement("span");
  label.className = "filter-control-label";
  label.textContent = labelText;
  wrap.append(label, control);
  return wrap;
}

export function initFilterStrip(target) {
  const quickSearch = document.createElement("input");
  quickSearch.type = "search";
  quickSearch.placeholder = "Quick search (/)";

  const scope = document.createElement("select");
  ["Current Category", "All Categories", "Favorites"].forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    scope.appendChild(option);
  });

  const configuration = document.createElement("select");
  ["Default", "Electrical", "Mechanical"].forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    configuration.appendChild(option);
  });

  const addChip = document.createElement("button");
  addChip.type = "button";
  addChip.className = "filter-add-chip";
  addChip.textContent = "+ Filter";

  const chips = document.createElement("div");
  chips.className = "filter-chips";

  addChip.addEventListener("click", () => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = "attribute = value";
    chips.appendChild(chip);
  });

  const debouncedSearch = debounce((value) => {
    window.dispatchEvent(new CustomEvent("grid:filter", { detail: { quickSearch: value } }));
  }, 250);

  quickSearch.addEventListener("input", () => debouncedSearch(quickSearch.value));

  window.addEventListener("keydown", (event) => {
    if (event.key === "/") {
      const tag = event.target?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
        return;
      }
      event.preventDefault();
      quickSearch.focus();
    }
  });

  const searchControl = buildLabeledControl("Search", quickSearch);
  const scopeControl = buildLabeledControl("Scope", scope);
  const viewControl = buildLabeledControl("View", configuration);

  target.replaceChildren(searchControl, scopeControl, viewControl, addChip, chips);
}
