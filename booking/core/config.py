from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "mgnbvbooking"
    api_v1_prefix: str = "/api/v1"

    database_url: str

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Симметричный ключ для шифрования паспортных данных жильцов (Fernet,
    # см. core/encryption.py). Генерируется через Fernet.generate_key().
    encryption_key: str

    # Redis Streams — канал событий для notifications-микросервиса.
    redis_url: str = "redis://localhost:6379/0"
    notifications_stream: str = "notifications"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
