# notifications

Notifications-микросервис mgnbvbooking.

Слушает события через RabbitMQ (публикует их основной сервис `mgnbvbooking`
через `booking.core.events.publish_event` в topic exchange `events`, а
notifications подписывается на очередь `notifications` с routing key `#`)
и рассылает email-уведомления владельцам объектов: новая бронь
(`booking.created`), поступила оплата (`payment.received`), код
подтверждения email (`auth.email_verification`).

## Локальный запуск

```bash
cp .env.example .env
poetry install
poetry run uvicorn app.main:app --reload --port 8001
```

Событие без `owner_email` в payload или без шаблона для своего `type`
пропускается (логируется, но не ломает обработку остальных сообщений).
