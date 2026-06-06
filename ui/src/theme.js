const STORAGE_KEY = "thinghound.theme";

const DARK_LABEL = "Light Mode";
const LIGHT_LABEL = "Dark Mode";

function detectSystemMode(matchMedia) {
  const query = matchMedia("(prefers-color-scheme: dark)");
  return query.matches ? "dark" : "light";
}

function readStoredMode(storage) {
  try {
    const value = storage.getItem(STORAGE_KEY);
    return value === "dark" || value === "light" ? value : null;
  } catch (_error) {
    return null;
  }
}

function writeStoredMode(storage, mode) {
  try {
    storage.setItem(STORAGE_KEY, mode);
  } catch (_error) {
    /* storage unavailable; manual override is best-effort only */
  }
}

function updateToggleLabel(toggleButton, mode) {
  if (toggleButton == null) {
    return;
  }
  toggleButton.textContent = mode === "dark" ? DARK_LABEL : LIGHT_LABEL;
  toggleButton.dataset.targetMode = mode === "dark" ? "light" : "dark";
}

export function createThemeController({
  root,
  toggleButton = null,
  storage = typeof window !== "undefined" ? window.localStorage : null,
  matchMedia = typeof window !== "undefined" ? window.matchMedia.bind(window) : null
} = {}) {
  if (root == null) {
    throw new Error("Theme root is required.");
  }
  if (matchMedia == null) {
    throw new Error("matchMedia implementation is required.");
  }

  let override = storage != null ? readStoredMode(storage) : null;
  const systemMode = detectSystemMode(matchMedia);

  const resolveMode = () => override ?? systemMode;
  const sync = () => {
    const mode = resolveMode();
    root.dataset.theme = mode;
    updateToggleLabel(toggleButton, mode);
    return mode;
  };

  const controller = {
    apply: sync,
    current() {
      return resolveMode();
    },
    setMode(nextMode) {
      if (nextMode !== "dark" && nextMode !== "light") {
        return resolveMode();
      }
      override = nextMode;
      if (storage != null) {
        writeStoredMode(storage, nextMode);
      }
      return sync();
    },
    toggle() {
      return controller.setMode(resolveMode() === "dark" ? "light" : "dark");
    },
    bindToggleButton(button) {
      updateToggleLabel(button ?? toggleButton, resolveMode());
    }
  };

  return controller;
}
