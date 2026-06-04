export function initFilterStrip(target) {
  const quickSearch = document.createElement("input");
  quickSearch.type = "search";
  quickSearch.placeholder = "Quick search (/)...";

  const chips = document.createElement("div");
  chips.className = "filter-chips";

  const addChip = document.createElement("button");
  addChip.type = "button";
  addChip.textContent = "Add Filter";

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

  addChip.addEventListener("click", () => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = "attribute = value";
    chips.appendChild(chip);
  });

  const debouncedSearch = debounce((value) => {
    console.log("quick-search", value);
    window.dispatchEvent(new CustomEvent("grid:filter", { detail: { quickSearch: value } }));
  }, 250);

  quickSearch.addEventListener("input", () => debouncedSearch(quickSearch.value));

  window.addEventListener("keydown", (event) => {
    if (event.key === "/") {
      event.preventDefault();
      quickSearch.focus();
    }
  });

  target.replaceChildren(quickSearch, addChip, scope, configuration, chips);
}

function debounce(callback, waitMs) {
  let timeoutId;
  return (value) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => callback(value), waitMs);
  };
}
