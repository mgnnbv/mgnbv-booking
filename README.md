# mgnbvbooking

Бэкенд сервиса учёта аренды для частных владельцев квартир/комнат:
календарь занятости, жильцы, договоры, платежи и задолженности.
Не сервис поиска арендаторов — инструмент учёта уже найденных.

Стек: FastAPI · SQLAlchemy 2.0 (async, asyncpg) · PostgreSQL 15+ (`btree_gist`) · Alembic · JWT · Redis Streams.

Состоит из двух сервисов:
- `booking/` — основной API (брони, жильцы, платежи, объекты).
- `notifications/` — микросервис уведомлений: слушает события в Redis Streams
  (`booking.created`, `payment.received`) и рассылает email владельцам.

## Локальный запуск через Docker

```bash
cp .env.example .env
cp notifications/.env.example notifications/.env
# сгенерировать ENCRYPTION_KEY и вписать в .env:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

docker compose up --build
```

API поднимется на `http://localhost:8000`, документация — `/docs`.
notifications — на `http://localhost:8001` (`/health`).
Миграции (`alembic upgrade head`) применяются автоматически при старте контейнера `api`.

## Локальный запуск без Docker

```bash
poetry install
cp .env.example .env  # укажите DATABASE_URL на локальный Postgres, задайте JWT_SECRET/ENCRYPTION_KEY

poetry run alembic upgrade head
poetry run uvicorn booking.main:app --reload
```

notifications запускается отдельно, из своей директории (свой `pyproject.toml`):

```bash
cd notifications
poetry install
cp .env.example .env  # укажите REDIS_URL и SMTP_*
poetry run uvicorn app.main:app --reload --port 8001
```

## Структура

- `booking/models/` — SQLAlchemy-модели
- `booking/schemas/` — Pydantic-схемы запросов/ответов
- `booking/services/` — бизнес-логика, работа с БД
- `booking/api/routers/` — FastAPI-роутеры (`/api/v1/...`)
- `booking/core/` — конфиг, сессия БД, security, шифрование, exception handlers, `events.py` — публикация событий в Redis
- `alembic/` — миграции (первая миграция создаёт расширение `btree_gist` и все таблицы)
- `notifications/` — отдельный микросервис (свой `pyproject.toml`/`Dockerfile`, свой пакет `app/`), слушает Redis Streams и шлёт email
