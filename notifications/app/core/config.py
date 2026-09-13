from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    events_exchange: str = "events"
    events_queue: str = "notifications"

    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    email_from: str = "noreply@mgnbvbooking.local"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
