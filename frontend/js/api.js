/**
 * js/api.js — Centralized API client for CivicIQ backend.
 * All fetch calls go through here. Handles auth headers and error normalization.
 */

const API_BASE = window.CIVICIQ_API_URL || "http://localhost:8000";

/**
 * Core fetch wrapper. Adds JWT if available, normalizes errors.
 */
async function apiFetch(path, options = {}) {
  const token = localStorage.getItem("civiciq_token");
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errMsg = `HTTP ${response.status}`;
    try {
      const errData = await response.json();
      errMsg = errData.detail || errData.message || errMsg;
    } catch (_) {}
    throw new Error(errMsg);
  }

  return response.json();
}

// ── Auth ──────────────────────────────────────────────────────
export const auth = {
  register: (data) =>
    apiFetch("/auth/register", { method: "POST", body: JSON.stringify(data) }),

  login: (email, password) =>
    apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  logout: () => {
    localStorage.removeItem("civiciq_token");
    localStorage.removeItem("civiciq_user");
    window.location.href = "/";
  },
};

// ── Complaints ────────────────────────────────────────────────
export const complaints = {
  submit: (data) =>
    apiFetch("/complaints", { method: "POST", body: JSON.stringify(data) }),

  list: (params = {}) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v != null))
    ).toString();
    return apiFetch(`/complaints${qs ? "?" + qs : ""}`);
  },

  get: (id) => apiFetch(`/complaints/${id}`),

  vote: (id) => apiFetch(`/complaints/${id}/vote`, { method: "POST" }),

  resolve: (id, resolution_note) =>
    apiFetch(`/complaints/${id}/resolve`, {
      method: "PATCH",
      body: JSON.stringify({ resolution_note }),
    }),
};

// ── Analytics ─────────────────────────────────────────────────
export const analytics = {
  get: () => apiFetch("/analytics"),
  localitySummary: () => apiFetch("/analytics/locality-summary"),
};

// ── Session helpers ───────────────────────────────────────────
export function saveSession(data) {
  localStorage.setItem("civiciq_token", data.access_token);
  localStorage.setItem(
    "civiciq_user",
    JSON.stringify({ id: data.user_id, email: data.email, role: data.role })
  );
}

export function getUser() {
  try {
    return JSON.parse(localStorage.getItem("civiciq_user"));
  } catch {
    return null;
  }
}

export function isLoggedIn() {
  return !!localStorage.getItem("civiciq_token");
}

export function isAdmin() {
  const user = getUser();
  return user?.role === "admin";
}
