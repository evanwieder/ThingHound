function flatten(nodes, depth = 0) {
  return nodes.flatMap((node) => [
    { id: node.id, name: node.name, depth },
    ...flatten(node.children ?? [], depth + 1)
  ]);
}

export async function initTree(target, bridgeApi, onFilter) {
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

  const nodes = flatten(categoryTree);
  const search = document.createElement("input");
  search.type = "search";
  search.placeholder = "Search categories";

  const list = document.createElement("ul");
  list.className = "tree-list";

  const render = (query = "") => {
    list.replaceChildren();
    for (const node of nodes) {
      if (!node.name.toLowerCase().includes(query.toLowerCase())) {
        continue;
      }
      const item = document.createElement("li");
      item.style.paddingLeft = `${node.depth * 12}px`;
      item.textContent = node.name;
      item.addEventListener("click", () => onFilter(filterRowsForCategory(node.id)));
      list.appendChild(item);
    }
  };

  search.addEventListener("input", () => render(search.value));

  target.replaceChildren(search, list);
  render();
}
