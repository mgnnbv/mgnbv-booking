const toastEl = document.getElementById("toast");
let toastTimer = null;

export function showToast(message, type = "success") {
  toastEl.textContent = message;
  toastEl.className = `toast ${type}`;
  toastEl.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toastEl.hidden = true;
  }, 3500);
}

export function showError(err) {
  const message = err?.message || "Что-то пошло не так";
  showToast(message, "error");
}

const overlay = document.getElementById("modal-overlay");
const modalTitle = document.getElementById("modal-title");
const modalBody = document.getElementById("modal-body");
document.getElementById("modal-close").addEventListener("click", closeModal);
overlay.addEventListener("click", (e) => {
  if (e.target === overlay) closeModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !overlay.hidden) closeModal();
});

export function openModal(title, bodyHtml) {
  modalTitle.textContent = title;
  modalBody.innerHTML = bodyHtml;
  overlay.hidden = false;
  return modalBody;
}

export function closeModal() {
  overlay.hidden = true;
  modalBody.innerHTML = "";
}

/** Ставит на кнопку submit форму disabled + текст "Сохранение..." пока idle не вызван. */
export function withSubmitLock(form, fn) {
  return async (e) => {
    e.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    const original = btn ? btn.textContent : null;
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Сохранение...";
    }
    try {
      await fn(e);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = original;
      }
    }
  };
}
