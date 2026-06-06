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

function buildToolbarSearch(label) {
  const wrap = document.createElement("label");
  wrap.className = "pane-toolbar-search";

  const text = document.createElement("span");
  text.className = "pane-toolbar-label";
  text.textContent = label;
  wrap.appendChild(text);

  const input = document.createElement("input");
  input.type = "search";
  input.placeholder = "Type to filter";
  wrap.appendChild(input);
  return { wrap, input };
}

export class TreeState {
  constructor(nodes) {
    this.nodes = nodes;
    this.expanded = new Set();
    this.query = "";
    if (nodes.length > 0) {
      this.expanded.add(nodes[0].id);
    }
  }

  isExpanded(id) {
    return this.expanded.has(id);
  }

  toggle(id) {
    if (this.expanded.has(id)) {
      this.expanded.delete(id);
    } else {
      this.expanded.add(id);
    }
  }

  expandAll() {
    walkAll(this.nodes, (node) => {
      this.expanded.add(node.id);
    });
  }

  collapseAll() {
    this.expanded.clear();
    if (this.nodes.length > 0) {
      this.expanded.add(this.nodes[0].id);
    }
  }

  setQuery(value) {
    this.query = value ?? "";
  }

  visible() {
    const result = [];
    const lowerQuery = this.query.toLowerCase();
    const filterActive = lowerQuery.length > 0;
    const matchesQuery = (node) =>
      !filterActive || node.name.toLowerCase().includes(lowerQuery);

    const recurse = (node, depth, ancestorExpanded) => {
      if (!ancestorExpanded) {
        return;
      }
      const isExpanded = filterActive || this.expanded.has(node.id);
      if (matchesQuery(node)) {
        result.push({
          id: node.id,
          name: node.name,
          depth,
          hasChildren: (node.children ?? []).length > 0,
          isOpen: isExpanded
        });
      }
      if (isExpanded) {
        for (const child of node.children ?? []) {
          recurse(child, depth + 1, ancestorExpanded);
        }
      }
    };

    for (const node of this.nodes) {
      recurse(node, 0, true);
    }
    return result;
  }
}

function walkAll(nodes, callback) {
  for (const node of nodes) {
    callback(node);
    if (node.children != null && node.children.length > 0) {
      walkAll(node.children, callback);
    }
  }
}

export function renderTreeToolbar(target, { onCollapseAll, onExpandAll, onSearch, onEdit } = {}) {
  const collapseButton = buildToolbarButton("Collapse All");
  const expandButton = buildToolbarButton("Expand All");
  const search = buildToolbarSearch("Search");
  const editButton = buildToolbarButton("Edit");

  target.replaceChildren(collapseButton, expandButton, search.wrap, editButton);

  collapseButton.addEventListener("click", () => onCollapseAll?.());
  expandButton.addEventListener("click", () => onExpandAll?.());
  search.input.addEventListener("input", () => onSearch?.(search.input.value));
  editButton.addEventListener("click", () => onEdit?.());
}

function makeTreeRow(visible, onFilter) {
  const item = document.createElement("li");
  item.className = "tree-row";
  item.style.setProperty("--tree-depth", String(visible.depth));
  item.dataset.nodeId = visible.id;

  const chevron = document.createElement("span");
  chevron.className = "tree-chevron";
  if (visible.hasChildren) {
    chevron.textContent = visible.isOpen ? "\u25BE" : "\u25B8";
    chevron.setAttribute("role", "button");
    chevron.setAttribute("aria-expanded", visible.isOpen ? "true" : "false");
    chevron.tabIndex = 0;
  } else {
    chevron.classList.add("tree-chevron-leaf");
    chevron.textContent = "\u00B7";
  }
  item.appendChild(chevron);

  const label = document.createElement("span");
  label.className = "tree-label";
  label.textContent = visible.name;
  item.appendChild(label);

  return { item, chevron };
}

export function renderTreeList(target, state, onFilter) {
  target.replaceChildren();
  for (const node of state.visible()) {
    const { item, chevron } = makeTreeRow(node, onFilter);
    if (node.hasChildren) {
      chevron.addEventListener("click", (event) => {
        event.stopPropagation();
        state.toggle(node.id);
        renderTreeList(target, state, onFilter);
      });
    }
    item.addEventListener("click", () => onFilter(node.id));
    target.appendChild(item);
  }
}

export async function initTree(toolbarTarget, bodyTarget, bridgeApi, onFilter) {
  let categoryTree = [];
  if (bridgeApi != null) {
    try {
      const response = await bridgeApi.get_category_tree({});
      categoryTree = response.nodes ?? [];
    } catch (error) {
      console.error("Failed loading category tree", error);
    }
  }

  if (categoryTree.length === 0) {
    categoryTree = [{ id: "root", name: "All Categories", children: [] }];
  }

  const state = new TreeState(categoryTree);

  const renderCurrent = () => renderTreeList(bodyTarget, state, onFilter);

  renderTreeToolbar(toolbarTarget, {
    onCollapseAll: () => {
      state.collapseAll();
      renderCurrent();
    },
    onExpandAll: () => {
      state.expandAll();
      renderCurrent();
    },
    onSearch: (value) => {
      state.setQuery(value);
      renderCurrent();
    },
    onEdit: () => {
      window.dispatchEvent(new CustomEvent("tree:request-edit"));
    }
  });

  renderCurrent();
}
