import asyncio
import os
import sys
import tempfile
import uuid
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

# asyncpg на Windows нестабилен под ProactorEventLoop (закрытие соединений
# роняет event loop) — переключаемся на SelectorEventLoop, как рекомендует
# сама asyncpg для Windows.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

TEST_DB_NAME = "rental_db_test"


os.environ.setdefault(
    "DATABASE_URL", f"postgresql+asyncpg://postgres:1008@localhost:15432/{TEST_DB_NAME}"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("PROMETHEUS_URL", "http://localhost:9090")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-production")
os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault(
    "PHOTOS_STORAGE_PATH", str(Path(tempfile.gettempdir()) / "mgnbvbooking_test_uploads")
)

import asyncpg
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

REPO_ROOT = Path(__file__).resolve().parent.parent


def _admin_dsn(database_url: str) -> str:
    """asyncpg не понимает суффикс '+asyncpg' и не умеет CREATE DATABASE на
    базе, к которой подключён, — коннектимся к системной 'postgres'."""
    base, _, _ = database_url.rpartition("/")
    return base.replace("postgresql+asyncpg://", "postgresql://") + "/postgres"


async def _ensure_test_database() -> None:
    database_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(dsn=_admin_dsn(database_url))
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        await conn.close()


def pytest_configure(config) -> None:
    asyncio.run(_ensure_test_database())

    alembic_cfg = Config(str(REPO_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="session")
def event_loop():
    """SQLAlchemy engine и redis-клиент в приложении — модульные синглтоны,
    привязанные к тому event loop, в котором были впервые использованы.
    Дефолтный per-test loop pytest-asyncio их бы рвал между тестами —
    держим один loop на всю сессию, как в реальном работающем сервере."""
    loop = asyncio.new_event_loop()
    yield loop

    # publish_event() лениво открывает robust-соединение с RabbitMQ и держит
    # его в module-level синглтоне — закрываем тем же loop'ом, пока он ещё
    # жив (через отдельную async-фикстуру порядок teardown'ов не гарантирован
    # и close() уже пытался достучаться до закрытого loop'а).
    from booking.core.events import close_event_client

    loop.run_until_complete(close_event_client())
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables():
    from booking.core.database import engine

    yield
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE payments, bookings, property_photos, properties, "
                "tenants, pending_registrations, users RESTART IDENTITY CASCADE"
            )
        )


@pytest_asyncio.fixture
async def client():
    from booking.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _get_pending_code(email: str) -> str:
    from booking.core.database import engine

    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT verification_code FROM pending_registrations WHERE email = :email"),
            {"email": email},
        )
        row = result.first()
        assert row is not None, f"нет pending-регистрации для {email}"
        return row[0]


@pytest_asyncio.fixture
def register_user(client):
    async def _register(
        email: str | None = None, password: str = "password123", full_name: str = "Test User"
    ) -> dict:
        email = email or f"user-{uuid.uuid4().hex[:12]}@example.com"

        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": full_name},
        )
        resp.raise_for_status()

        code = await _get_pending_code(email)
        verify_resp = await client.post(
            "/api/v1/auth/verify-email", json={"email": email, "code": code}
        )
        verify_resp.raise_for_status()
        user = verify_resp.json()

        login_resp = await client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        login_resp.raise_for_status()
        tokens = login_resp.json()

        return {
            "user": user,
            "email": email,
            "password": password,
            "tokens": tokens,
            "headers": {"Authorization": f"Bearer {tokens['access_token']}"},
        }

    return _register


@pytest_asyncio.fixture
async def auth_client(client, register_user):
    reg = await register_user()
    client.headers.update(reg["headers"])
    return client, reg
