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


    encryption_key: str

    redis_url: str = "redis://localhost:6379/0"

    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    events_exchange: str = "events"

    photos_storage_path: str = "/app/uploads/properties"
    photos_public_base_url: str = "/uploads/properties"
    max_photo_size_mb: int = 5

    email_verification_code_ttl_minutes: int = 10

    # JSON allowlist. Accounts outside it always receive the user role.
    admin_emails: list[str] = []

    prometheus_url: str = "http://prometheus:9090"

    def is_admin_email(self, email: str) -> bool:
        allowed_emails = {value.strip().lower() for value in self.admin_emails if value.strip()}
        return email.strip().lower() in allowed_emails


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
