// Global Drawer Controls
window.openDrawer = function () {
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

document.addEventListener("DOMContentLoaded", () => {
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

    // Pressing 'd' or 'D' opens drawer when not in an input
    if ((e.key === "d" || e.key === "D") && !isTyping && !e.ctrlKey && !e.metaKey) {
      const drawer = document.getElementById("docs-drawer");
      if (drawer) {
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
