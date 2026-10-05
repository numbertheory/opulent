function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Local Timezone Conversion Helpers
function parseUtcDate(isoString) {
  if (!isoString) return null;
  let str = String(isoString).trim();
  if (!str.endsWith("Z") && !/[+-]\d{2}:\d{2}$/.test(str)) {
    str += "Z";
  }
  const d = new Date(str);
  return isNaN(d.getTime()) ? null : d;
}

window.formatToLocal = function (isoString, includeSeconds = false) {
  const d = parseUtcDate(isoString);
  if (!d) return isoString || "";

  const pad = (n) => String(n).padStart(2, "0");
  const year = d.getFullYear();
  const month = pad(d.getMonth() + 1);
  const day = pad(d.getDate());

  let hours = d.getHours();
  const ampm = hours >= 12 ? "pm" : "am";
  hours = hours % 12;
  if (hours === 0) hours = 12;
  const mins = pad(d.getMinutes());

  if (includeSeconds) {
    const secs = pad(d.getSeconds());
    return `${year}-${month}-${day} ${hours}:${mins}:${secs}${ampm}`;
  }
  return `${year}-${month}-${day} ${hours}:${mins}${ampm}`;
};

window.updateLocalTimes = function () {
  document.querySelectorAll("time.local-time").forEach((el) => {
    const iso = el.getAttribute("datetime");
    if (!iso) return;
    const includeSeconds = el.getAttribute("data-seconds") === "true";
    const formatted = window.formatToLocal(iso, includeSeconds);
    if (formatted) {
      el.textContent = formatted;
      try {
        const d = parseUtcDate(iso);
        if (d) el.title = d.toLocaleString();
      } catch (e) {}
    }
  });

  document.querySelectorAll("option[data-datetime]").forEach((opt) => {
    const iso = opt.getAttribute("data-datetime");
    const ver = opt.getAttribute("data-version");
    if (iso && ver) {
      const formatted = window.formatToLocal(iso, false);
      const isCurrent = opt.getAttribute("data-current") === "true";
      opt.textContent = `v${ver} (${formatted})${isCurrent ? " (Current)" : ""}`;
    }
  });
};

// Global Drawer Controls
window.openDrawer = async function () {
  const drawer = document.getElementById("docs-drawer");
  const backdrop = document.getElementById("drawer-backdrop");
  if (drawer) drawer.classList.add("open");
  if (backdrop) backdrop.classList.add("open");
  document.body.style.overflow = "hidden";

  // Focus search input after animation
  setTimeout(() => {
    const searchInput = document.getElementById("drawer-search-input");
    if (searchInput) searchInput.focus();
  }, 150);

  // If list container has no items, dynamically fetch from /api/docs
  const listContainer = document.getElementById("drawer-doc-list");
  if (listContainer && listContainer.children.length === 0) {
    try {
      const res = await fetch("/api/docs?page=1&per_page=15");
      if (res.ok) {
        const data = await res.json();
        const countBadge = document.getElementById("drawer-total-count");
        if (countBadge) {
          countBadge.textContent = data.total;
          countBadge.style.display = "";
        }
        if (data.items && data.items.length > 0) {
          const emptyState = document.getElementById("drawer-empty-state");
          if (emptyState) emptyState.style.display = "none";
          listContainer.innerHTML = "";
          data.items.forEach((item) => {
            const card = document.createElement("div");
            card.className = "drawer-doc-card";
            card.setAttribute("data-title", (item.title || "").toLowerCase());
            card.setAttribute("data-id", (item.id || "").toLowerCase());
            card.setAttribute("data-format", (item.format || "").toLowerCase());

            const updateDateIso = item.effective_updated_at || item.updated_at || item.created_at;
            const formattedDate = updateDateIso ? window.formatToLocal(updateDateIso) : "";
            const iconSvg = item.format_icon_svg || `<svg class="format-icon format-icon-${escapeHtml(item.format)}" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`;

            card.innerHTML = `
              <div class="drawer-doc-top">
                <span class="doc-format-icon" style="display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;" title="${escapeHtml(item.display_format || item.format)}">
                  ${iconSvg}
                </span>
                <a href="${item.url}" class="drawer-doc-title">${escapeHtml(item.title || "Untitled")}</a>
              </div>
              ${item.snippet ? `<div class="doc-snippet">${escapeHtml(item.snippet)}</div>` : ""}
              <div class="drawer-doc-meta">
                <time class="local-time" datetime="${updateDateIso || ''}">${escapeHtml(formattedDate)}</time>
                ${item.version_count > 1 ? `<span class="badge badge-gold" style="font-size: 0.68rem; padding: 0.05rem 0.3rem;">v${item.version_count}</span>` : ""}
              </div>
            `;
            listContainer.appendChild(card);
          });
          window.updateLocalTimes();
        }
      }
    } catch (err) {
      console.error("Failed to load documents into drawer:", err);
    }
  }
};

window.closeDrawer = function () {
  const drawer = document.getElementById("docs-drawer");
  const backdrop = document.getElementById("drawer-backdrop");
  if (drawer) drawer.classList.remove("open");
  if (backdrop) backdrop.classList.remove("open");
  document.body.style.overflow = "";
};

window.filterDrawerDocuments = function (query) {
  const q = (query || "").trim().toLowerCase();
  const cards = document.querySelectorAll(".drawer-doc-card");
  let visibleCount = 0;

  cards.forEach((card) => {
    const title = card.getAttribute("data-title") || "";
    const id = card.getAttribute("data-id") || "";
    const format = card.getAttribute("data-format") || "";

    if (!q || title.includes(q) || id.includes(q) || format.includes(q)) {
      card.style.display = "";
      visibleCount++;
    } else {
      card.style.display = "none";
    }
  });

  // Handle empty search feedback
  let noResultsNotice = document.getElementById("drawer-no-results");
  const listContainer = document.getElementById("drawer-doc-list");
  if (!noResultsNotice && listContainer) {
    noResultsNotice = document.createElement("div");
    noResultsNotice.id = "drawer-no-results";
    noResultsNotice.style.cssText =
      "text-align: center; color: var(--text-muted); padding: 1.5rem; font-size: 0.9rem;";
    noResultsNotice.textContent = "No documents match your search.";
    listContainer.appendChild(noResultsNotice);
  }

  if (noResultsNotice) {
    noResultsNotice.style.display =
      visibleCount === 0 && cards.length > 0 ? "block" : "none";
  }
};

// Filter Documents in the Standalone Full Table View
window.filterDocumentsTable = function (query) {
  const q = (query || "").trim().toLowerCase();
  const rows = document.querySelectorAll(".docs-table tbody tr.doc-table-row");
  let visibleCount = 0;

  rows.forEach((row) => {
    const title = row.getAttribute("data-title") || "";
    const id = row.getAttribute("data-id") || "";
    const format = row.getAttribute("data-format") || "";

    if (!q || title.includes(q) || id.includes(q) || format.includes(q)) {
      row.style.display = "";
      visibleCount++;
    } else {
      row.style.display = "none";
    }
  });

  const noResultsRow = document.getElementById("table-no-results");
  if (noResultsRow) {
    noResultsRow.style.display =
      visibleCount === 0 && rows.length > 0 ? "" : "none";
  }
};

// Theme Management (Light / Dark with system default and persistence)
function getSystemTheme() {
  return window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: light)").matches
    ? "light"
    : "dark";
}

function getCurrentTheme() {
  try {
    const saved = localStorage.getItem("opulent-theme");
    if (saved === "light" || saved === "dark") {
      return saved;
    }
  } catch (e) {}
  return getSystemTheme();
}

function applyTheme(theme, persist = false) {
  document.documentElement.setAttribute("data-theme", theme);
  if (persist) {
    try {
      localStorage.setItem("opulent-theme", theme);
    } catch (e) {
      console.warn("Could not save theme to localStorage:", e);
    }
  }
  updateThemeToggleUI(theme);
}

function updateThemeToggleUI(theme) {
  const btn = document.getElementById("theme-toggle-btn");
  const label = document.getElementById("theme-toggle-text");
  if (btn) {
    const isDark = theme === "dark";
    btn.setAttribute(
      "title",
      isDark ? "Switch to light theme" : "Switch to dark theme"
    );
    btn.setAttribute(
      "aria-label",
      isDark ? "Switch to light theme" : "Switch to dark theme"
    );
    btn.classList.toggle("theme-dark", isDark);
    btn.classList.toggle("theme-light", !isDark);
    if (label) {
      label.textContent = isDark ? "Dark" : "Light";
    }
  }
}

window.toggleTheme = function () {
  const current =
    document.documentElement.getAttribute("data-theme") || getCurrentTheme();
  const next = current === "dark" ? "light" : "dark";
  applyTheme(next, true);
};

// Automatically react to OS preference changes if no manual preference is set
if (window.matchMedia) {
  window
    .matchMedia("(prefers-color-scheme: dark)")
    .addEventListener("change", (e) => {
      try {
        if (!localStorage.getItem("opulent-theme")) {
          applyTheme(e.matches ? "dark" : "light", false);
        }
      } catch (err) {}
    });
}

document.addEventListener("DOMContentLoaded", () => {
  // Convert all UTC ISO timestamps to the browser's local timezone
  window.updateLocalTimes();

  // Sync toggle button UI on DOMContentLoaded
  const initialTheme =
    document.documentElement.getAttribute("data-theme") || getCurrentTheme();
  updateThemeToggleUI(initialTheme);

  // Toast helper
  const toast = document.getElementById("toast");
  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("show");
    setTimeout(() => {
      toast.classList.remove("show");
    }, 2500);
  }

  // Clipboard copy
  window.copyText = function (text, message = "Copied to clipboard!") {
    navigator.clipboard
      .writeText(text)
      .then(() => showToast(message))
      .catch((err) => {
        console.error("Clipboard copy failed:", err);
        // Fallback
        const textarea = document.createElement("textarea");
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
        showToast(message);
      });
  };

  // Keyboard navigation & shortcuts
  document.addEventListener("keydown", (e) => {
    const activeTag = document.activeElement
      ? document.activeElement.tagName.toLowerCase()
      : "";
    const isTyping =
      activeTag === "input" ||
      activeTag === "textarea" ||
      activeTag === "select";

    // Escape closes the drawer
    if (e.key === "Escape") {
      const drawer = document.getElementById("docs-drawer");
      if (drawer && drawer.classList.contains("open")) {
        closeDrawer();
      }
    }

    // Pressing 'd' or 'D' opens drawer when not in an input, if drawer tab is available
    if ((e.key === "d" || e.key === "D") && !isTyping && !e.ctrlKey && !e.metaKey) {
      const dockedTab = document.getElementById("docked-drawer-tab");
      const drawer = document.getElementById("docs-drawer");
      if (dockedTab && drawer) {
        if (drawer.classList.contains("open")) {
          closeDrawer();
        } else {
          openDrawer();
        }
      }
    }
  });

  // Textarea live stats and tab handling
  const editor = document.getElementById("doc-content-input");
  const statsLines = document.getElementById("stat-lines");
  const statsWords = document.getElementById("stat-words");
  const statsChars = document.getElementById("stat-chars");
  const editorForm = document.getElementById("editor-form");

  if (editor) {
    function updateStats() {
      const val = editor.value;
      const lines = val ? val.split("\n").length : 0;
      const words = val.trim() ? val.trim().split(/\s+/).length : 0;
      const chars = val.length;

      if (statsLines) statsLines.textContent = `${lines} lines`;
      if (statsWords) statsWords.textContent = `${words} words`;
      if (statsChars) statsChars.textContent = `${chars} chars`;
    }

    editor.addEventListener("input", updateStats);
    updateStats();

    // Enable tab indentation and Ctrl/Cmd+Enter submission
    editor.addEventListener("keydown", (e) => {
      if (e.key === "Tab") {
        e.preventDefault();
        const start = editor.selectionStart;
        const end = editor.selectionEnd;
        editor.value =
          editor.value.substring(0, start) + "    " + editor.value.substring(end);
        editor.selectionStart = editor.selectionEnd = start + 4;
        updateStats();
      } else if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        if (editorForm) {
          editorForm.submit();
        }
      }
    });
  }
});
