import { api, ApiError, isAuthenticated, setTokens } from "./api.js";
import { showError } from "./ui.js";
import { setUser, loadUser, clearUser } from "./state.js";
import { renderDashboard, renderProperties, renderBookings, renderTenants, renderOverdue } from "./views.js";

const authScreen = document.getElementById("auth-screen");
const appShell = document.getElementById("app-shell");

/* ---------------- Auth screen: tabs + forms ---------------- */

const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const loginError = document.getElementById("login-error");
const registerError = document.getElementById("register-error");

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const isLogin = tab.dataset.tab === "login";
    loginForm.hidden = !isLogin;
    registerForm.hidden = isLogin;
    loginError.textContent = "";
    registerError.textContent = "";
  });
});

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  loginError.textContent = "";
  const btn = loginForm.querySelector('button[type="submit"]');
  const fd = new FormData(loginForm);
  const phone = fd.get("phone");
  btn.disabled = true;
  try {
    const tokens = await api.login({ phone, password: fd.get("password") });
    setTokens(tokens);
    setUser(phone);
    enterApp();
  } catch (err) {
    loginError.textContent = err instanceof ApiError ? err.message : "Не удалось войти";
  } finally {
    btn.disabled = false;
  }
});

registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  registerError.textContent = "";
  const btn = registerForm.querySelector('button[type="submit"]');
  const fd = new FormData(registerForm);
  const payload = {
    phone: fd.get("phone"),
    password: fd.get("password"),
    full_name: fd.get("full_name") || null,
    email: fd.get("email") || null,
  };
  btn.disabled = true;
  try {
    const user = await api.register(payload);
    const tokens = await api.login({ phone: payload.phone, password: payload.password });
    setTokens(tokens);
    setUser(user.full_name || user.phone);
    enterApp();
  } catch (err) {
    registerError.textContent = err instanceof ApiError ? err.message : "Не удалось зарегистрироваться";
  } finally {
    btn.disabled = false;
  }
});

/* ---------------- App shell: nav + routing ---------------- */

const viewRoot = document.getElementById("view-root");
const viewTitle = document.getElementById("view-title");
const userNameEl = document.getElementById("user-name");

const VIEWS = {
  dashboard: { title: "Дашборд", render: renderDashboard },
  properties: { title: "Объекты", render: renderProperties },
  bookings: { title: "Брони", render: renderBookings },
  tenants: { title: "Жильцы", render: renderTenants },
  overdue: { title: "Просрочки", render: renderOverdue },
};

async function navigate(viewName) {
  const view = VIEWS[viewName] || VIEWS.dashboard;
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === viewName);
  });
  viewTitle.textContent = view.title;
  location.hash = viewName;
  try {
    await view.render(viewRoot);
  } catch (err) {
    showError(err);
  }
}

window.addEventListener("auth:expired", () => {
  clearUser();
  enterAuth();
});

document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => navigate(btn.dataset.view));
});

document.getElementById("logout-btn").addEventListener("click", () => {
  setTokens(null);
  clearUser();
  enterAuth();
});

function enterApp() {
  authScreen.hidden = true;
  appShell.hidden = false;
  userNameEl.textContent = loadUser();
  const initial = location.hash.replace("#", "") || "dashboard";
  navigate(VIEWS[initial] ? initial : "dashboard");
}

function enterAuth() {
  appShell.hidden = true;
  authScreen.hidden = false;
  loginForm.reset();
  registerForm.reset();
}

if (isAuthenticated()) {
  enterApp();
} else {
  enterAuth();
}
