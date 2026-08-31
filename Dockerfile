FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN pip install --no-cache-dir "poetry>=2.0.0,<3.0.0"

COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-interaction --no-ansi --no-root --only main

COPY . .
RUN poetry install --no-interaction --no-ansi --only main

EXPOSE 8000

CMD ["uvicorn", "booking.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
