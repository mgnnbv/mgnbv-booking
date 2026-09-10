import { api } from "./api.js";
import { openModal, closeModal, showToast, showError, withSubmitLock } from "./ui.js";
import {
  PROPERTY_TYPE_LABELS,
  BOOKING_STATUS_LABELS,
  BOOKING_STATUS_BADGE,
  PAYMENT_STATUS_LABELS,
  PAYMENT_STATUS_BADGE,
  PAYMENT_TYPE_LABELS,
  formatDate,
  formatMoney,
  badge,
  escapeHtml,
  optionsHtml,
  todayIso,
} from "./utils.js";
import { cacheProperties, cacheTenants, propertyTitle, tenantName, state, loadTheme, setTheme } from "./state.js";

function formData(form) {
  const fd = new FormData(form);
  const obj = {};
  for (const [key, value] of fd.entries()) obj[key] = value;
  return obj;
}

function emptyToNull(obj, keys) {
  for (const k of keys) {
    if (obj[k] === "" || obj[k] === undefined) obj[k] = null;
  }
  return obj;
}

/* ============================== Дашборд ============================== */

export async function renderDashboard(root) {
  root.innerHTML = `<div class="empty-state">Загрузка...</div>`;
  let data;
  try {
    data = await api.dashboard();
  } catch (err) {
    root.innerHTML = `<div class="empty-state">Не удалось загрузить дашборд</div>`;
    showError(err);
    return;
  }

  cacheProperties(data.properties);

  const activeCount = data.properties.filter((p) => !p.is_archived).length;

  root.innerHTML = `
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-value">${activeCount}</div>
        <div class="stat-label">Активных объектов</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${formatMoney(data.monthly_income.total_paid)}</div>
        <div class="stat-label">Оплачено за ${data.monthly_income.month}.${data.monthly_income.year}</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${formatMoney(data.monthly_income.total_expected)}</div>
        <div class="stat-label">Ожидается за месяц</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${data.overdue_payments.length}</div>
        <div class="stat-label">Просроченных платежей</div>
      </div>
    </div>

    <div class="card">
      <div class="section-head"><h3>Ближайшие заезды/выезды (7 дней)</h3></div>
      ${
        data.upcoming_events.length === 0
          ? `<div class="empty-state">Нет событий на ближайшую неделю</div>`
          : `<table><thead><tr><th>Дата</th><th>Событие</th><th>Объект</th><th>Жилец</th></tr></thead><tbody>
              ${data.upcoming_events
                .map(
                  (e) => `<tr>
                    <td>${formatDate(e.event_date)}</td>
                    <td>${e.event_type === "check_in" ? badge("Заезд", "badge-green") : badge("Выезд", "badge-orange")}</td>
                    <td>${escapeHtml(e.property_title)}</td>
                    <td>${escapeHtml(e.tenant_full_name)}</td>
                  </tr>`
                )
                .join("")}
            </tbody></table>`
      }
    </div>

    <div class="card">
      <div class="section-head"><h3>Просроченные платежи</h3></div>
      ${
        data.overdue_payments.length === 0
          ? `<div class="empty-state">Просрочек нет</div>`
          : `<table><thead><tr><th>Объект</th><th>Жилец</th><th>Сумма</th><th>Срок</th></tr></thead><tbody>
              ${data.overdue_payments
                .map(
                  (p) => `<tr>
                    <td>${escapeHtml(p.property_title)}</td>
                    <td>${escapeHtml(p.tenant_full_name)}</td>
                    <td>${formatMoney(p.amount)}</td>
                    <td>${formatDate(p.due_date)}</td>
                  </tr>`
                )
                .join("")}
            </tbody></table>`
      }
    </div>
  `;
}

/* ============================== Объекты ============================== */

let activePropertyId = null;

export async function renderProperties(root, { resetDetail = true } = {}) {
  if (resetDetail) activePropertyId = null;
  if (activePropertyId) {
    await renderPropertyDetail(root, activePropertyId);
  } else {
    await renderPropertiesList(root);
  }
}

async function renderPropertiesList(root) {
  root.innerHTML = `<div class="empty-state">Загрузка...</div>`;
  const includeArchived = root.dataset.includeArchived === "1";
  let properties;
  try {
    properties = await api.listProperties(includeArchived);
  } catch (err) {
    root.innerHTML = `<div class="empty-state">Не удалось загрузить объекты</div>`;
    showError(err);
    return;
  }
  cacheProperties(properties);

  root.innerHTML = `
    <div class="toolbar">
      <button class="btn btn-primary" id="add-property-btn">+ Добавить объект</button>
      <div class="spacer"></div>
      <label class="checkbox-inline">
        <input type="checkbox" id="include-archived" ${includeArchived ? "checked" : ""} />
        Показывать архивные
      </label>
    </div>
    ${
      properties.length === 0
        ? `<div class="empty-state">Пока нет объектов — добавьте первый</div>`
        : `<div class="property-grid">
            ${properties
              .map(
                (p) => `
              <div class="property-card ${p.is_archived ? "archived" : ""}" data-id="${p.id}">
                <h4>${escapeHtml(p.title)}</h4>
                <div class="property-meta">${PROPERTY_TYPE_LABELS[p.property_type] || p.property_type}${p.address ? " · " + escapeHtml(p.address) : ""}</div>
                <div class="property-meta">${p.default_rate ? formatMoney(p.default_rate) : "ставка не указана"}</div>
                ${p.is_archived ? badge("Архив", "badge-gray") : ""}
              </div>`
              )
              .join("")}
          </div>`
    }
  `;

  root.querySelector("#add-property-btn").addEventListener("click", () => openPropertyForm(null, () => renderProperties(root, { resetDetail: false })));
  root.querySelector("#include-archived").addEventListener("change", (e) => {
    root.dataset.includeArchived = e.target.checked ? "1" : "0";
    renderPropertiesList(root);
  });
  root.querySelectorAll(".property-card").forEach((card) => {
    card.addEventListener("click", () => {
      activePropertyId = card.dataset.id;
      renderProperties(root, { resetDetail: false });
    });
  });
}

async function renderPropertyDetail(root, propertyId) {
  root.innerHTML = `<div class="empty-state">Загрузка...</div>`;
  let property, bookings;
  try {
    [property, bookings] = await Promise.all([
      api.getProperty(propertyId),
      api.listPropertyBookings(propertyId),
    ]);
  } catch (err) {
    root.innerHTML = `<div class="empty-state">Не удалось загрузить объект</div>`;
    showError(err);
    return;
  }

  if (!state.tenantsLoaded) {
    try {
      cacheTenants(await api.listTenants());
    } catch {
      /* не критично для отображения */
    }
  }

  root.innerHTML = `
    <div class="toolbar">
      <button class="btn btn-ghost" id="back-btn">&larr; К объектам</button>
      <div class="spacer"></div>
      <button class="btn btn-secondary" id="edit-property-btn">Редактировать</button>
      <button class="btn ${property.is_archived ? "btn-secondary" : "btn-danger"}" id="archive-property-btn">
        ${property.is_archived ? "Восстановить" : "Архивировать"}
      </button>
    </div>

    <div class="card">
      <h3 style="margin-top:0">${escapeHtml(property.title)} ${property.is_archived ? badge("Архив", "badge-gray") : ""}</h3>
      <p class="property-meta">${PROPERTY_TYPE_LABELS[property.property_type] || property.property_type}${property.address ? " · " + escapeHtml(property.address) : ""}</p>
      ${property.description ? `<p>${escapeHtml(property.description)}</p>` : ""}
      <p class="property-meta">Ставка по умолчанию: ${property.default_rate ? formatMoney(property.default_rate) : "—"}</p>
    </div>

    <div class="card">
      <div class="section-head">
        <h3>Брони</h3>
        <button class="btn btn-primary btn-sm" id="add-booking-btn">+ Новая бронь</button>
      </div>
      ${
        bookings.length === 0
          ? `<div class="empty-state">Броней пока нет</div>`
          : `<table><thead><tr><th>Жилец</th><th>Период</th><th>Сумма</th><th>Статус</th><th></th></tr></thead><tbody>
              ${bookings
                .map(
                  (b) => `<tr class="booking-row" data-id="${b.id}" style="cursor:pointer">
                    <td>${escapeHtml(tenantName(b.tenant_id))}</td>
                    <td>${formatDate(b.start_date)} — ${formatDate(b.end_date)}</td>
                    <td>${formatMoney(b.rent_amount)}</td>
                    <td>${badge(BOOKING_STATUS_LABELS[b.status] || b.status, BOOKING_STATUS_BADGE[b.status])}</td>
                    <td class="row-actions"><button class="btn btn-ghost btn-sm">Открыть</button></td>
                  </tr>`
                )
                .join("")}
            </tbody></table>`
      }
    </div>
  `;

  root.querySelector("#back-btn").addEventListener("click", () => {
    activePropertyId = null;
    renderProperties(root, { resetDetail: false });
  });
  root.querySelector("#edit-property-btn").addEventListener("click", () =>
    openPropertyForm(property, () => renderProperties(root, { resetDetail: false }))
  );
  root.querySelector("#archive-property-btn").addEventListener("click", async () => {
    try {
      if (property.is_archived) {
        // DELETE /properties/{id} всегда архивирует (is_archived=True) и не умеет
        // восстанавливать — для отмены архивации используем PATCH.
        await api.updateProperty(property.id, { is_archived: false });
      } else {
        await api.archiveProperty(property.id);
      }
      showToast(property.is_archived ? "Объект восстановлен" : "Объект архивирован");
      renderProperties(root, { resetDetail: false });
    } catch (err) {
      showError(err);
    }
  });
  root.querySelector("#add-booking-btn").addEventListener("click", () =>
    openBookingForm({ propertyId: property.id, onSaved: () => renderProperties(root, { resetDetail: false }) })
  );
  root.querySelectorAll(".booking-row").forEach((row) => {
    row.addEventListener("click", async () => {
      try {
        const booking = await api.getBooking(row.dataset.id);
        openBookingDetail(booking, () => renderProperties(root, { resetDetail: false }));
      } catch (err) {
        showError(err);
      }
    });
  });
}

function openPropertyForm(existing, onSaved) {
  const body = openModal(existing ? "Редактировать объект" : "Новый объект", `
    <form id="property-form" class="form-grid">
      <label class="full">Название *
        <input name="title" required maxlength="255" value="${escapeHtml(existing?.title || "")}" />
      </label>
      <label>Тип объекта *
        <select name="property_type">${optionsHtml(PROPERTY_TYPE_LABELS, existing?.property_type || "apartment")}</select>
      </label>
      <label>Адрес
        <input name="address" value="${escapeHtml(existing?.address || "")}" />
      </label>
      <label>Ставка по умолчанию
        <input name="default_rate" type="number" step="0.01" min="0" value="${existing?.default_rate ?? ""}" />
      </label>
      <label class="full">Описание
        <textarea name="description">${escapeHtml(existing?.description || "")}</textarea>
      </label>
      <div class="full modal-actions">
        <button type="button" class="btn btn-ghost" id="cancel-btn">Отмена</button>
        <button type="submit" class="btn btn-primary">Сохранить</button>
      </div>
    </form>
  `);

  const form = body.querySelector("#property-form");
  body.querySelector("#cancel-btn").addEventListener("click", closeModal);
  form.addEventListener(
    "submit",
    withSubmitLock(form, async () => {
      const data = emptyToNull(formData(form), ["address", "description", "default_rate"]);
      try {
        if (existing) {
          await api.updateProperty(existing.id, data);
          showToast("Объект обновлён");
        } else {
          await api.createProperty(data);
          showToast("Объект создан");
        }
        closeModal();
        onSaved();
      } catch (err) {
        showError(err);
      }
    })
  );
}

/* ============================== Брони ============================== */

async function openBookingForm({ propertyId = null, onSaved }) {
  let tenants = [];
  let properties = [];
  try {
    // Загружаем свежие списки (а не кэш), чтобы жилец/объект, только что
    // созданные на соседней вкладке, сразу появились в выборе.
    cacheTenants(await api.listTenants());
    tenants = [...state.tenantNameCache.entries()];
    if (!propertyId) {
      properties = await api.listProperties(false);
      cacheProperties(properties);
    }
  } catch (err) {
    showError(err);
  }

  const missing = tenants.length === 0 || (!propertyId && properties.length === 0);

  const body = openModal("Новая бронь", `
    <form id="booking-form" class="form-grid">
      ${
        propertyId
          ? ""
          : `<label class="full">Объект *
              ${
                properties.length === 0
                  ? `<span class="form-error">Сначала добавьте объект во вкладке «Объекты»</span>`
                  : `<select name="property_id" required>${properties.map((p) => `<option value="${p.id}">${escapeHtml(p.title)}</option>`).join("")}</select>`
              }
            </label>`
      }
      <label class="full">Жилец *
        ${
          tenants.length === 0
            ? `<span class="form-error">Сначала добавьте жильца во вкладке «Жильцы»</span>`
            : `<select name="tenant_id" required>${tenants.map(([id, name]) => `<option value="${id}">${escapeHtml(name)}</option>`).join("")}</select>`
        }
      </label>
      <label>День платежа (1-31)
        <input name="monthly_payment_day" type="number" min="1" max="31" />
      </label>
      <label>Дата заезда *
        <input name="start_date" type="date" required value="${todayIso()}" />
      </label>
      <label>Дата выезда
        <input name="end_date" type="date" />
      </label>
      <label>Сумма аренды *
        <input name="rent_amount" type="number" step="0.01" min="0" required />
      </label>
      <label>Депозит
        <input name="deposit_amount" type="number" step="0.01" min="0" />
      </label>
      <label class="full">Заметки
        <textarea name="notes"></textarea>
      </label>
      <div class="full modal-actions">
        <button type="button" class="btn btn-ghost" id="cancel-btn">Отмена</button>
        <button type="submit" class="btn btn-primary" ${missing ? "disabled" : ""}>Создать</button>
      </div>
    </form>
  `);

  const form = body.querySelector("#booking-form");
  body.querySelector("#cancel-btn").addEventListener("click", closeModal);
  form.addEventListener(
    "submit",
    withSubmitLock(form, async () => {
      const data = emptyToNull(formData(form), ["end_date", "deposit_amount", "monthly_payment_day", "notes"]);
      if (propertyId) data.property_id = propertyId;
      if (data.monthly_payment_day) data.monthly_payment_day = Number(data.monthly_payment_day);
      try {
        await api.createBooking(data);
        showToast("Бронь создана");
        closeModal();
        onSaved();
      } catch (err) {
        showError(err);
      }
    })
  );
}

export async function renderBookings(root) {
  root.innerHTML = `<div class="empty-state">Загрузка...</div>`;
  let properties;
  try {
    properties = await api.listProperties(true);
  } catch (err) {
    root.innerHTML = `<div class="empty-state">Не удалось загрузить брони</div>`;
    showError(err);
    return;
  }
  cacheProperties(properties);

  if (!state.tenantsLoaded) {
    try {
      cacheTenants(await api.listTenants());
    } catch {
      /* не критично для отображения */
    }
  }

  if (properties.length === 0) {
    root.innerHTML = `
      <div class="toolbar"><button class="btn btn-primary" id="add-booking-btn" disabled>+ Новая бронь</button></div>
      <div class="card"><div class="empty-state">Сначала добавьте объект во вкладке «Объекты», чтобы создавать брони</div></div>
    `;
    return;
  }

  // Отдельного эндпоинта «все брони пользователя» в API нет — брони отдаются
  // только по конкретному объекту, поэтому собираем список параллельными
  // запросами по каждому объекту.
  const lists = await Promise.all(properties.map((p) => api.listPropertyBookings(p.id).catch(() => [])));
  const bookings = lists.flat().sort((a, b) => new Date(b.start_date) - new Date(a.start_date));

  root.innerHTML = `
    <div class="toolbar">
      <button class="btn btn-primary" id="add-booking-btn">+ Новая бронь</button>
    </div>
    <div class="card" style="padding:0">
      ${
        bookings.length === 0
          ? `<div class="empty-state">Броней пока нет</div>`
          : `<table><thead><tr><th>Объект</th><th>Жилец</th><th>Период</th><th>Сумма</th><th>Статус</th><th></th></tr></thead><tbody>
              ${bookings
                .map(
                  (b) => `<tr class="booking-row" data-id="${b.id}" style="cursor:pointer">
                    <td>${escapeHtml(propertyTitle(b.property_id))}</td>
                    <td>${escapeHtml(tenantName(b.tenant_id))}</td>
                    <td>${formatDate(b.start_date)} — ${formatDate(b.end_date)}</td>
                    <td>${formatMoney(b.rent_amount)}</td>
                    <td>${badge(BOOKING_STATUS_LABELS[b.status] || b.status, BOOKING_STATUS_BADGE[b.status])}</td>
                    <td class="row-actions"><button class="btn btn-ghost btn-sm">Открыть</button></td>
                  </tr>`
                )
                .join("")}
            </tbody></table>`
      }
    </div>
  `;

  root.querySelector("#add-booking-btn").addEventListener("click", () =>
    openBookingForm({ onSaved: () => renderBookings(root) })
  );
  root.querySelectorAll(".booking-row").forEach((row) => {
    row.addEventListener("click", async () => {
      try {
        const booking = await api.getBooking(row.dataset.id);
        openBookingDetail(booking, () => renderBookings(root));
      } catch (err) {
        showError(err);
      }
    });
  });
}

async function openBookingDetail(booking, onChanged) {
  let payments = [];
  try {
    payments = await api.listBookingPayments(booking.id);
  } catch (err) {
    showError(err);
  }

  const body = openModal(`Бронь · ${propertyTitle(booking.property_id)}`, renderBookingDetailHtml(booking, payments));
  wireBookingDetail(body, booking, payments, onChanged);
}

function renderBookingDetailHtml(booking, payments) {
  return `
    <div class="section-head">
      <div>
        <strong>${escapeHtml(tenantName(booking.tenant_id))}</strong>
        <div class="property-meta">${formatDate(booking.start_date)} — ${formatDate(booking.end_date)} · ${formatMoney(booking.rent_amount)}</div>
      </div>
      ${badge(BOOKING_STATUS_LABELS[booking.status] || booking.status, BOOKING_STATUS_BADGE[booking.status])}
    </div>

    <form id="booking-status-form" class="form-grid" style="margin-bottom:18px">
      <label>Статус
        <select name="status">${optionsHtml(BOOKING_STATUS_LABELS, booking.status)}</select>
      </label>
      <label>Сумма аренды
        <input name="rent_amount" type="number" step="0.01" min="0" value="${booking.rent_amount}" />
      </label>
      <label>Дата выезда
        <input name="end_date" type="date" value="${booking.end_date || ""}" />
      </label>
      <label class="full">Заметки
        <textarea name="notes">${escapeHtml(booking.notes || "")}</textarea>
      </label>
      <div class="full modal-actions">
        <button type="button" class="btn btn-danger" id="cancel-booking-btn" ${booking.status === "cancelled" ? "disabled" : ""}>Отменить бронь</button>
        <button type="submit" class="btn btn-primary">Сохранить</button>
      </div>
    </form>

    <div class="section-head"><h3>Платежи</h3></div>
    ${
      payments.length === 0
        ? `<div class="empty-state">Платежей пока нет</div>`
        : `<table><thead><tr><th>Тип</th><th>Сумма</th><th>Срок</th><th>Статус</th><th></th></tr></thead><tbody>
            ${payments
              .map(
                (p) => `<tr>
                  <td>${PAYMENT_TYPE_LABELS[p.payment_type] || p.payment_type}</td>
                  <td>${formatMoney(p.amount)}</td>
                  <td>${formatDate(p.due_date)}</td>
                  <td>${badge(PAYMENT_STATUS_LABELS[p.status] || p.status, PAYMENT_STATUS_BADGE[p.status])}</td>
                  <td class="row-actions">
                    ${p.status !== "paid" ? `<button class="btn btn-ghost btn-sm mark-paid-btn" data-id="${p.id}">Отметить оплаченным</button>` : ""}
                  </td>
                </tr>`
              )
              .join("")}
          </tbody></table>`
    }

    <details style="margin-top:14px">
      <summary style="cursor:pointer;color:var(--primary);font-weight:600;font-size:13px">+ Добавить платёж</summary>
      <form id="payment-form" class="form-grid" style="margin-top:12px">
        <label>Тип
          <select name="payment_type">${optionsHtml(PAYMENT_TYPE_LABELS, "rent")}</select>
        </label>
        <label>Сумма *
          <input name="amount" type="number" step="0.01" min="0" required />
        </label>
        <label>Срок оплаты *
          <input name="due_date" type="date" required value="${todayIso()}" />
        </label>
        <label>Способ оплаты
          <input name="payment_method" maxlength="50" />
        </label>
        <label class="full">Комментарий
          <textarea name="comment"></textarea>
        </label>
        <div class="full modal-actions">
          <button type="submit" class="btn btn-primary">Добавить</button>
        </div>
      </form>
    </details>
  `;
}

function wireBookingDetail(body, booking, payments, onChanged) {
  const statusForm = body.querySelector("#booking-status-form");
  statusForm.addEventListener(
    "submit",
    withSubmitLock(statusForm, async () => {
      const data = emptyToNull(formData(statusForm), ["end_date", "notes"]);
      try {
        const updated = await api.updateBooking(booking.id, data);
        showToast("Бронь обновлена");
        onChanged();
        await refreshBookingDetail(updated, onChanged);
      } catch (err) {
        showError(err);
      }
    })
  );

  body.querySelector("#cancel-booking-btn").addEventListener("click", async () => {
    try {
      const updated = await api.cancelBooking(booking.id);
      showToast("Бронь отменена");
      onChanged();
      await refreshBookingDetail(updated, onChanged);
    } catch (err) {
      showError(err);
    }
  });

  body.querySelectorAll(".mark-paid-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await api.updatePayment(btn.dataset.id, { status: "paid", paid_at: new Date().toISOString() });
        showToast("Платёж отмечен оплаченным");
        onChanged();
        await refreshBookingDetail(booking, onChanged);
      } catch (err) {
        showError(err);
      }
    });
  });

  const paymentForm = body.querySelector("#payment-form");
  paymentForm.addEventListener(
    "submit",
    withSubmitLock(paymentForm, async () => {
      const data = emptyToNull(formData(paymentForm), ["payment_method", "comment"]);
      try {
        await api.createPayment(booking.id, data);
        showToast("Платёж добавлен");
        onChanged();
        await refreshBookingDetail(booking, onChanged);
      } catch (err) {
        showError(err);
      }
    })
  );
}

async function refreshBookingDetail(booking, onChanged) {
  let fresh, payments;
  try {
    [fresh, payments] = await Promise.all([api.getBooking(booking.id), api.listBookingPayments(booking.id)]);
  } catch (err) {
    showError(err);
    return;
  }
  const body = openModal(`Бронь · ${propertyTitle(fresh.property_id)}`, renderBookingDetailHtml(fresh, payments));
  wireBookingDetail(body, fresh, payments, onChanged);
}

/* ============================== Жильцы ============================== */

let activeTenantId = null;

export async function renderTenants(root, { resetDetail = true } = {}) {
  if (resetDetail) activeTenantId = null;
  if (activeTenantId) {
    await renderTenantDetail(root, activeTenantId);
  } else {
    await renderTenantsList(root);
  }
}

async function renderTenantsList(root) {
  root.innerHTML = `<div class="empty-state">Загрузка...</div>`;
  const search = root.dataset.search || "";
  let tenants;
  try {
    tenants = await api.listTenants(search || undefined);
  } catch (err) {
    root.innerHTML = `<div class="empty-state">Не удалось загрузить жильцов</div>`;
    showError(err);
    return;
  }
  cacheTenants(tenants);

  root.innerHTML = `
    <div class="toolbar">
      <button class="btn btn-primary" id="add-tenant-btn">+ Добавить жильца</button>
      <input type="search" id="tenant-search" placeholder="Поиск по имени..." value="${escapeHtml(search)}" />
    </div>
    <div class="card" style="padding:0">
      ${
        tenants.length === 0
          ? `<div class="empty-state">Жильцов пока нет</div>`
          : `<table><thead><tr><th>Имя</th><th>Телефон</th><th>Паспортные данные</th></tr></thead><tbody>
              ${tenants
                .map(
                  (t) => `<tr class="tenant-row" data-id="${t.id}" style="cursor:pointer">
                    <td>${escapeHtml(t.full_name)}</td>
                    <td>${escapeHtml(t.phone || "—")}</td>
                    <td>${t.has_passport_data ? badge("Сохранены", "badge-green") : badge("Нет", "badge-gray")}</td>
                  </tr>`
                )
                .join("")}
            </tbody></table>`
      }
    </div>
  `;

  root.querySelector("#add-tenant-btn").addEventListener("click", () => openTenantForm(null, () => renderTenants(root, { resetDetail: false })));
  const searchInput = root.querySelector("#tenant-search");
  let searchTimer = null;
  searchInput.addEventListener("input", (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      root.dataset.search = e.target.value;
      renderTenantsList(root);
    }, 300);
  });
  root.querySelectorAll(".tenant-row").forEach((row) => {
    row.addEventListener("click", () => {
      activeTenantId = row.dataset.id;
      renderTenants(root, { resetDetail: false });
    });
  });
}

async function renderTenantDetail(root, tenantId) {
  root.innerHTML = `<div class="empty-state">Загрузка...</div>`;
  let tenant;
  try {
    tenant = await api.getTenant(tenantId);
  } catch (err) {
    root.innerHTML = `<div class="empty-state">Не удалось загрузить жильца</div>`;
    showError(err);
    return;
  }

  if (!state.propertiesLoaded) {
    try {
      cacheProperties(await api.listProperties(true));
    } catch {
      /* не критично */
    }
  }

  root.innerHTML = `
    <div class="toolbar">
      <button class="btn btn-ghost" id="back-btn">&larr; К жильцам</button>
      <div class="spacer"></div>
      <button class="btn btn-secondary" id="edit-tenant-btn">Редактировать</button>
    </div>

    <div class="card">
      <h3 style="margin-top:0">${escapeHtml(tenant.full_name)}</h3>
      <p class="property-meta">${escapeHtml(tenant.phone || "телефон не указан")}</p>
      ${tenant.notes ? `<p>${escapeHtml(tenant.notes)}</p>` : ""}
      <p class="property-meta">Паспортные данные: ${tenant.has_passport_data ? badge("Сохранены", "badge-green") : badge("Не сохранены", "badge-gray")}</p>
    </div>

    <div class="card">
      <div class="section-head"><h3>Брони жильца</h3></div>
      ${
        tenant.bookings.length === 0
          ? `<div class="empty-state">Броней пока нет</div>`
          : `<table><thead><tr><th>Объект</th><th>Период</th><th>Сумма</th><th>Статус</th></tr></thead><tbody>
              ${tenant.bookings
                .map(
                  (b) => `<tr>
                    <td>${escapeHtml(propertyTitle(b.property_id))}</td>
                    <td>${formatDate(b.start_date)} — ${formatDate(b.end_date)}</td>
                    <td>${formatMoney(b.rent_amount)}</td>
                    <td>${badge(BOOKING_STATUS_LABELS[b.status] || b.status, BOOKING_STATUS_BADGE[b.status])}</td>
                  </tr>`
                )
                .join("")}
            </tbody></table>`
      }
    </div>
  `;

  root.querySelector("#back-btn").addEventListener("click", () => {
    activeTenantId = null;
    renderTenants(root, { resetDetail: false });
  });
  root.querySelector("#edit-tenant-btn").addEventListener("click", () =>
    openTenantForm(tenant, () => renderTenants(root, { resetDetail: false }))
  );
}

function openTenantForm(existing, onSaved) {
  const body = openModal(existing ? "Редактировать жильца" : "Новый жилец", `
    <form id="tenant-form" class="form-grid">
      <label class="full">ФИО *
        <input name="full_name" required maxlength="255" value="${escapeHtml(existing?.full_name || "")}" />
      </label>
      <label>Телефон
        <input name="phone" maxlength="20" value="${escapeHtml(existing?.phone || "")}" />
      </label>
      <label class="full">Паспортные данные ${existing?.has_passport_data ? "(будут заменены при заполнении)" : ""}
        <input name="passport_data" placeholder="${existing?.has_passport_data ? "оставьте пустым, чтобы не менять" : ""}" />
      </label>
      <label class="full">Заметки
        <textarea name="notes">${escapeHtml(existing?.notes || "")}</textarea>
      </label>
      <div class="full modal-actions">
        <button type="button" class="btn btn-ghost" id="cancel-btn">Отмена</button>
        <button type="submit" class="btn btn-primary">Сохранить</button>
      </div>
    </form>
  `);

  const form = body.querySelector("#tenant-form");
  body.querySelector("#cancel-btn").addEventListener("click", closeModal);
  form.addEventListener(
    "submit",
    withSubmitLock(form, async () => {
      const data = formData(form);
      if (data.passport_data === "") delete data.passport_data;
      emptyToNull(data, ["phone", "notes"]);
      try {
        if (existing) {
          await api.updateTenant(existing.id, data);
          showToast("Жилец обновлён");
        } else {
          await api.createTenant(data);
          showToast("Жилец добавлен");
        }
        closeModal();
        onSaved();
      } catch (err) {
        showError(err);
      }
    })
  );
}

/* ============================== Просрочки ============================== */

export async function renderOverdue(root) {
  root.innerHTML = `<div class="empty-state">Загрузка...</div>`;
  let payments;
  try {
    payments = await api.listOverduePayments();
  } catch (err) {
    root.innerHTML = `<div class="empty-state">Не удалось загрузить просрочки</div>`;
    showError(err);
    return;
  }

  root.innerHTML = `
    <div class="card" style="padding:0">
      ${
        payments.length === 0
          ? `<div class="empty-state">Просроченных платежей нет 🎉</div>`
          : `<table><thead><tr><th>Объект</th><th>Жилец</th><th>Тип</th><th>Сумма</th><th>Срок</th><th></th></tr></thead><tbody>
              ${payments
                .map(
                  (p) => `<tr>
                    <td>${escapeHtml(p.property_title)}</td>
                    <td>${escapeHtml(p.tenant_full_name)}</td>
                    <td>${PAYMENT_TYPE_LABELS[p.payment_type] || p.payment_type}</td>
                    <td>${formatMoney(p.amount)}</td>
                    <td>${formatDate(p.due_date)}</td>
                    <td class="row-actions"><button class="btn btn-ghost btn-sm mark-paid-btn" data-id="${p.id}">Отметить оплаченным</button></td>
                  </tr>`
                )
                .join("")}
            </tbody></table>`
      }
    </div>
  `;

  root.querySelectorAll(".mark-paid-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await api.updatePayment(btn.dataset.id, { status: "paid", paid_at: new Date().toISOString() });
        showToast("Платёж отмечен оплаченным");
        renderOverdue(root);
      } catch (err) {
        showError(err);
      }
    });
  });
}

/* ============================== Настройки ============================== */

const THEME_LABELS = {
  system: "Как в системе",
  light: "Светлая",
  dark: "Тёмная",
};

export async function renderSettings(root) {
  const currentTheme = loadTheme();

  root.innerHTML = `
    <div class="card">
      <div class="section-head"><h3>Аккаунт</h3></div>
      <p class="property-meta">Вы вошли как ${escapeHtml(state.userDisplayName || "—")}</p>
    </div>

    <div class="card">
      <div class="section-head"><h3>Оформление</h3></div>
      <div class="toolbar" id="theme-toggle">
        ${Object.entries(THEME_LABELS)
          .map(
            ([value, label]) =>
              `<button type="button" class="btn ${value === currentTheme ? "btn-primary" : "btn-ghost"}" data-theme-value="${value}">${label}</button>`
          )
          .join("")}
      </div>
    </div>
  `;

  root.querySelectorAll("[data-theme-value]").forEach((btn) => {
    btn.addEventListener("click", () => {
      setTheme(btn.dataset.themeValue);
      renderSettings(root);
    });
  });
}
