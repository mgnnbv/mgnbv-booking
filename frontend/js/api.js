import { API_BASE_URL } from "./config.js";

const TOKEN_KEY = "mgnbv_tokens";

function loadTokens() {
  try {
    return JSON.parse(localStorage.getItem(TOKEN_KEY) || "null");
  } catch {
    return null;
  }
}

let tokens = loadTokens();
let refreshPromise = null;

export function getTokens() {
  return tokens;
}

export function setTokens(next) {
  tokens = next;
  if (next) {
    localStorage.setItem(TOKEN_KEY, JSON.stringify(next));
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export function isAuthenticated() {
  return Boolean(tokens?.access_token);
}

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : "Ошибка запроса");
    this.status = status;
    this.detail = detail;
  }
}

async function doRefresh() {
  if (!tokens?.refresh_token) {
    setTokens(null);
    window.dispatchEvent(new CustomEvent("auth:expired"));
    throw new ApiError(401, "Сессия истекла");
  }
  const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: tokens.refresh_token }),
  });
  if (!res.ok) {
    setTokens(null);
    window.dispatchEvent(new CustomEvent("auth:expired"));
    throw new ApiError(res.status, "Сессия истекла, войдите заново");
  }
  const data = await res.json();
  setTokens({ ...tokens, access_token: data.access_token });
  return data.access_token;
}

/**
 * Обёртка над fetch: подставляет Authorization, при 401 один раз пробует
 * обновить access-токен через refresh-токен и повторяет запрос.
 */
export async function apiFetch(path, { method = "GET", body, auth = true, retry = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && tokens?.access_token) {
    headers.Authorization = `Bearer ${tokens.access_token}`;
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && auth && retry) {
    if (!refreshPromise) {
      refreshPromise = doRefresh().finally(() => {
        refreshPromise = null;
      });
    }
    try {
      await refreshPromise;
    } catch (err) {
      throw err;
    }
    return apiFetch(path, { method, body, auth, retry: false });
  }

  if (res.status === 204) return null;

  let payload = null;
  const text = await res.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!res.ok) {
    const detail = payload?.detail ?? payload ?? `Ошибка ${res.status}`;
    throw new ApiError(res.status, formatDetail(detail));
  }

  return payload;
}

function formatDetail(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    // Ошибки валидации pydantic: [{loc, msg, type}, ...]
    return detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
  }
  return JSON.stringify(detail);
}

export const api = {
  register: (data) => apiFetch("/auth/register", { method: "POST", body: data, auth: false }),
  login: (data) => apiFetch("/auth/login", { method: "POST", body: data, auth: false }),
  verifyEmail: (data) => apiFetch("/auth/verify-email", { method: "POST", body: data, auth: false }),

  dashboard: () => apiFetch("/dashboard"),

  listProperties: (includeArchived = false) =>
    apiFetch(`/properties?include_archived=${includeArchived}`),
  createProperty: (data) => apiFetch("/properties", { method: "POST", body: data }),
  getProperty: (id) => apiFetch(`/properties/${id}`),
  updateProperty: (id, data) => apiFetch(`/properties/${id}`, { method: "PATCH", body: data }),
  archiveProperty: (id) => apiFetch(`/properties/${id}`, { method: "DELETE" }),

  listTenants: (search) => apiFetch(`/tenants${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  createTenant: (data) => apiFetch("/tenants", { method: "POST", body: data }),
  getTenant: (id) => apiFetch(`/tenants/${id}`),
  updateTenant: (id, data) => apiFetch(`/tenants/${id}`, { method: "PATCH", body: data }),

  listPropertyBookings: (propertyId, from, to) => {
    const params = new URLSearchParams();
    if (from) params.set("from", from);
    if (to) params.set("to", to);
    const qs = params.toString();
    return apiFetch(`/properties/${propertyId}/bookings${qs ? `?${qs}` : ""}`);
  },
  createBooking: (data) => apiFetch("/bookings", { method: "POST", body: data }),
  getBooking: (id) => apiFetch(`/bookings/${id}`),
  updateBooking: (id, data) => apiFetch(`/bookings/${id}`, { method: "PATCH", body: data }),
  cancelBooking: (id) => apiFetch(`/bookings/${id}`, { method: "DELETE" }),

  listBookingPayments: (bookingId) => apiFetch(`/bookings/${bookingId}/payments`),
  createPayment: (bookingId, data) =>
    apiFetch(`/bookings/${bookingId}/payments`, { method: "POST", body: data }),
  listOverduePayments: () => apiFetch("/payments/overdue"),
  updatePayment: (id, data) => apiFetch(`/payments/${id}`, { method: "PATCH", body: data }),
};
