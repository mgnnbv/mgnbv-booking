import { api, ApiError, isAuthenticated, setTokens } from "./api.js";
import { showError } from "./ui.js";
import { setUser, loadUser, clearUser, loadTheme, applyTheme } from "./state.js";
import { renderDashboard, renderProperties, renderBookings, renderTenants, renderOverdue, renderSettings } from "./views.js";

applyTheme(loadTheme());

const authScreen = document.getElementById("auth-screen");
const appShell = document.getElementById("app-shell");

/* ---------------- Auth screen: tabs + forms ---------------- */

const tabsEl = document.querySelector(".tabs");
const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const verifyForm = document.getElementById("verify-form");
const loginError = document.getElementById("login-error");
const registerError = document.getElementById("register-error");
const verifyError = document.getElementById("verify-error");
const verifyHint = document.getElementById("verify-hint");
const verifyBackBtn = document.getElementById("verify-back-btn");

// Пароль/email временно держим в памяти между "зарегистрировался"/"код не
// подтверждён при входе" и успешным вводом кода, чтобы не просить войти дважды.
let pendingAuth = null;

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

function showVerifyScreen(email, password) {
  pendingAuth = { email, password };
  tabsEl.hidden = true;
  loginForm.hidden = true;
  registerForm.hidden = true;
  verifyForm.hidden = false;
  verifyError.textContent = "";
  verifyHint.textContent = `Мы отправили код подтверждения на ${email}. Введите его ниже.`;
  verifyForm.reset();
}

function backToLogin() {
  pendingAuth = null;
  tabsEl.hidden = false;
  verifyForm.hidden = true;
  loginForm.hidden = false;
  registerForm.hidden = true;
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === "login"));
}

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  loginError.textContent = "";
  const btn = loginForm.querySelector('button[type="submit"]');
  const fd = new FormData(loginForm);
  const email = fd.get("email");
  const password = fd.get("password");
  btn.disabled = true;
  try {
    const tokens = await api.login({ email, password });
    setTokens(tokens);
    setUser(email);
    enterApp();
  } catch (err) {
    if (err instanceof ApiError && err.status === 403) {
      showVerifyScreen(email, password);
    } else {
      loginError.textContent = err instanceof ApiError ? err.message : "Не удалось войти";
    }
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
    email: fd.get("email"),
    password: fd.get("password"),
    full_name: fd.get("full_name") || null,
    phone: fd.get("phone") || null,
  };
  btn.disabled = true;
  try {
    await api.register(payload);
    showVerifyScreen(payload.email, payload.password);
  } catch (err) {
    registerError.textContent = err instanceof ApiError ? err.message : "Не удалось зарегистрироваться";
  } finally {
    btn.disabled = false;
  }
});

verifyForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  verifyError.textContent = "";
  const btn = verifyForm.querySelector('button[type="submit"]');
  const fd = new FormData(verifyForm);
  const code = fd.get("code");
  btn.disabled = true;
  try {
    await api.verifyEmail({ email: pendingAuth.email, code });
    const tokens = await api.login({ email: pendingAuth.email, password: pendingAuth.password });
    setTokens(tokens);
    setUser(pendingAuth.email);
    pendingAuth = null;
    tabsEl.hidden = false;
    enterApp();
  } catch (err) {
    verifyError.textContent = err instanceof ApiError ? err.message : "Не удалось подтвердить код";
  } finally {
    btn.disabled = false;
  }
});

verifyBackBtn.addEventListener("click", backToLogin);

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
  settings: { title: "Настройки", render: renderSettings },
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
  backToLogin();
  loginForm.reset();
  registerForm.reset();
}

if (isAuthenticated()) {
  enterApp();
} else {
  enterAuth();
}
