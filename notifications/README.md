# notifications

Notifications-микросервис mgnbvbooking.

Слушает поток событий `notifications` в Redis Streams (публикует их основной
сервис `mgnbvbooking` через `app.core.events.publish_event`) и рассылает
email-уведомления владельцам объектов: новая бронь (`booking.created`),
поступила оплата (`payment.received`).

## Локальный запуск

```bash
cp .env.example .env  # укажите REDIS_URL и SMTP_*
poetry install
poetry run uvicorn app.main:app --reload --port 8001
```

Событие без `owner_email` в payload или без шаблона для своего `type`
пропускается (логируется, но не ломает обработку остальных сообщений).
