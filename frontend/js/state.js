export const state = {
  userDisplayName: "",
  userRole: "user",
  // Кэш id объекта/жильца -> название, чтобы не гонять лишние запросы там, где
  // бэкенд не денормализует title (например, брони жильца или объекта).
  propertyTitleCache: new Map(),
  propertiesLoaded: false,
  tenantNameCache: new Map(),
  tenantsLoaded: false,
};

export function setUser(displayName, role = "user") {
  state.userDisplayName = displayName;
  state.userRole = role;
  localStorage.setItem("mgnbv_user_display", displayName);
  localStorage.setItem("mgnbv_user_role", role);
}

export function loadUser() {
  state.userDisplayName = localStorage.getItem("mgnbv_user_display") || "";
  state.userRole = localStorage.getItem("mgnbv_user_role") || "user";
  return state.userDisplayName;
}

export function clearUser() {
  state.userDisplayName = "";
  state.userRole = "user";
  localStorage.removeItem("mgnbv_user_display");
  localStorage.removeItem("mgnbv_user_role");
}

export function isAdmin() {
  return state.userRole === "admin";
}

export function cacheProperties(properties) {
  state.propertiesLoaded = true;
  for (const p of properties) {
    state.propertyTitleCache.set(p.id, p.title);
  }
}

export function propertyTitle(id) {
  return state.propertyTitleCache.get(id) || "Объект";
}

export function cacheTenants(tenants) {
  state.tenantsLoaded = true;
  for (const t of tenants) {
    state.tenantNameCache.set(t.id, t.full_name);
  }
}

export function tenantName(id) {
  return state.tenantNameCache.get(id) || "Жилец";
}

const THEME_KEY = "mgnbv_theme";

export function loadTheme() {
  return localStorage.getItem(THEME_KEY) || "system";
}

export function applyTheme(theme) {
  const root = document.documentElement;
  if (theme === "dark" || theme === "light") {
    root.setAttribute("data-theme", theme);
  } else {
    root.removeAttribute("data-theme");
  }
}

export function setTheme(theme) {
  localStorage.setItem(THEME_KEY, theme);
  applyTheme(theme);
}
