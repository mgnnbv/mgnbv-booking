from typing import Any

_TEMPLATES = {
    "booking.created": (
        "Новая бронь: {property_title}",
        "Создана новая бронь.\n\n"
        "Объект: {property_title}\n"
        "Жилец: {tenant_name}\n"
        "Заезд: {start_date}\n"
        "Выезд: {end_date}\n"
        "Сумма: {rent_amount}\n",
    ),
    "payment.received": (
        "Оплата получена: {property_title}",
        "Зафиксирована оплата.\n\n"
        "Объект: {property_title}\n"
        "Жилец: {tenant_name}\n"
        "Сумма: {amount}\n"
        "Тип платежа: {payment_type}\n"
        "Дата оплаты: {paid_at}\n",
    ),
    "auth.email_verification": (
        "Код подтверждения email",
        "Ваш код подтверждения: {code}\n\n"
        "Код действителен {ttl_minutes} минут. Если вы не запрашивали регистрацию — "
        "просто проигнорируйте это письмо.\n",
    ),
}

_DEFAULTS = {"end_date": "бессрочно", "paid_at": "—"}


def render(event_type: str, payload: dict[str, Any]) -> tuple[str, str] | None:
    template = _TEMPLATES.get(event_type)
    if template is None:
        return None

    subject_tpl, body_tpl = template
    values = {**payload}
    for key, default in _DEFAULTS.items():
        if not values.get(key):
            values[key] = default
    values = {k: (v if v is not None else "—") for k, v in values.items()}

    return subject_tpl.format(**values), body_tpl.format(**values)