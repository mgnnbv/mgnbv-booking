export const PROPERTY_TYPE_LABELS = {
  apartment: "Квартира",
  room: "Комната",
  number: "Номер",
  house: "Дом",
};

export const RENTAL_TYPE_LABELS = {
  short_term: "Посуточно",
  long_term: "Долгосрочно",
};

export const BOOKING_STATUS_LABELS = {
  pending: "Забронировано",
  active: "Проживает",
  completed: "Завершена",
  cancelled: "Отменена",
};

export const BOOKING_STATUS_BADGE = {
  pending: "badge-blue",
  active: "badge-green",
  completed: "badge-gray",
  cancelled: "badge-red",
};

export const PAYMENT_STATUS_LABELS = {
  pending: "Ожидается",
  paid: "Оплачено",
  overdue: "Просрочено",
  cancelled: "Отменено",
};

export const PAYMENT_STATUS_BADGE = {
  pending: "badge-blue",
  paid: "badge-green",
  overdue: "badge-red",
  cancelled: "badge-gray",
};

export const PAYMENT_TYPE_LABELS = {
  rent: "Аренда",
  deposit: "Депозит",
  utility: "Коммунальные",
  other: "Другое",
};

export function formatDate(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("ru-RU");
}

export function formatDateTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
}

export function formatMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return String(value);
  return num.toLocaleString("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 2 }) + " ₽";
}

export function badge(text, cls) {
  return `<span class="badge ${cls || "badge-gray"}">${escapeHtml(text)}</span>`;
}

export function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function optionsHtml(labelsMap, selected) {
  return Object.entries(labelsMap)
    .map(([value, label]) => `<option value="${value}" ${value === selected ? "selected" : ""}>${label}</option>`)
    .join("");
}

/** Сегодняшняя дата в формате YYYY-MM-DD для input[type=date]. */
export function todayIso() {
  return new Date().toISOString().slice(0, 10);
}
