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
