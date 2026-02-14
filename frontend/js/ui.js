/**
 * js/ui.js — Shared UI utilities: notifications, loaders, dark mode, helpers.
 */

// ── Toast Notifications ───────────────────────────────────────
export function showToast(message, type = "info") {
  const container = document.getElementById("toast-container") || createToastContainer();
  const toast = document.createElement("div");
  const colors = {
    success: "bg-green-600",
    error: "bg-red-600",
    info: "bg-blue-600",
    warning: "bg-yellow-600",
  };
  toast.className = `${colors[type] || colors.info} text-white px-5 py-3 rounded-lg shadow-lg 
    flex items-center gap-2 text-sm font-medium transition-all duration-300 transform translate-y-0 opacity-100`;
  toast.innerHTML = `
    <span>${getToastIcon(type)}</span>
    <span>${message}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.add("opacity-0", "translate-y-2");
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function createToastContainer() {
  const el = document.createElement("div");
  el.id = "toast-container";
  el.className = "fixed bottom-6 right-6 flex flex-col gap-2 z-50";
  document.body.appendChild(el);
  return el;
}

function getToastIcon(type) {
  const icons = {
    success: "✓",
    error: "✗",
    info: "ℹ",
    warning: "⚠",
  };
  return icons[type] || "ℹ";
}

// ── Loading State ─────────────────────────────────────────────
export function setLoading(buttonEl, loading, loadingText = "Loading...") {
  if (!buttonEl) return;
  if (loading) {
    buttonEl.dataset.originalText = buttonEl.textContent;
    buttonEl.textContent = loadingText;
    buttonEl.disabled = true;
    buttonEl.classList.add("opacity-75", "cursor-not-allowed");
  } else {
    buttonEl.textContent = buttonEl.dataset.originalText || "Submit";
    buttonEl.disabled = false;
    buttonEl.classList.remove("opacity-75", "cursor-not-allowed");
  }
}

// ── Dark Mode ─────────────────────────────────────────────────
export function initDarkMode() {
  const toggle = document.getElementById("dark-mode-toggle");
  const root = document.documentElement;

  // Load saved preference or default to system
  const saved = localStorage.getItem("civiciq_dark");
  if (saved === "true" || (!saved && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
    root.classList.add("dark");
    if (toggle) toggle.checked = true;
  }

  if (toggle) {
    toggle.addEventListener("change", () => {
      root.classList.toggle("dark", toggle.checked);
      localStorage.setItem("civiciq_dark", toggle.checked);
    });
  }
}

// ── Severity Badge ────────────────────────────────────────────
export function severityBadge(severity) {
  const colors = {
    High: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
    Medium: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300",
    Low: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
  };
  return `<span class="px-2 py-0.5 rounded-full text-xs font-semibold ${colors[severity] || ""}">${severity}</span>`;
}

// ── Status Badge ──────────────────────────────────────────────
export function statusBadge(status) {
  const config = {
    pending: { cls: "bg-orange-100 text-orange-700", label: "Pending" },
    in_progress: { cls: "bg-blue-100 text-blue-700", label: "In Progress" },
    resolved: { cls: "bg-green-100 text-green-700", label: "Resolved" },
  };
  const { cls, label } = config[status] || { cls: "bg-gray-100 text-gray-700", label: status };
  return `<span class="px-2 py-0.5 rounded-full text-xs font-semibold ${cls}">${label}</span>`;
}

// ── Time Formatting ───────────────────────────────────────────
export function timeAgo(isoString) {
  const date = new Date(isoString);
  const seconds = Math.floor((Date.now() - date) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

// ── Escape HTML ───────────────────────────────────────────────
export function escHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
