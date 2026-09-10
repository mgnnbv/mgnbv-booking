import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.config import settings
from booking.core.exceptions import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError, ValidationError
from booking.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from booking.models.user import User
from booking.schemas.auth import LoginRequest, RegisterRequest, TokenPair


def _generate_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
    existing_email = await db.scalar(select(User).where(User.email == data.email))
    if existing_email is not None:
        raise ConflictError("Пользователь с таким email уже зарегистрирован")

    if data.phone is not None:
        existing_phone = await db.scalar(select(User).where(User.phone == data.phone))
        if existing_phone is not None:
            raise ConflictError("Пользователь с таким телефоном уже зарегистрирован")

    user = User(
        email=data.email,
        phone=data.phone,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        email_verification_code=_generate_verification_code(),
        email_verification_code_expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=settings.email_verification_code_ttl_minutes),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user, attribute_names=["created_at", "updated_at"])
    return user


async def verify_email(db: AsyncSession, email: str, code: str) -> User:
    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        raise NotFoundError("Пользователь не найден")

    if user.email_verified:
        return user

    if (
        user.email_verification_code is None
        or user.email_verification_code_expires_at is None
        or user.email_verification_code_expires_at < datetime.now(timezone.utc)
    ):
        raise ValidationError("Код истёк или не запрашивался — запросите новый")

    if not secrets.compare_digest(user.email_verification_code, code):
        raise ValidationError("Неверный код")

    user.email_verified = True
    user.email_verification_code = None
    user.email_verification_code_expires_at = None
    await db.commit()
    await db.refresh(user, attribute_names=["updated_at"])
    return user


async def authenticate_user(db: AsyncSession, data: LoginRequest) -> User:
    user = await db.scalar(select(User).where(User.email == data.email))
    if user is None or not verify_password(data.password, user.password_hash):
        raise UnauthorizedError("Неверные учётные данные")
    if not user.email_verified:
        raise ForbiddenError("Email не подтверждён. Введите код из письма.")
    return user


def issue_token_pair(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> str:
    try:
        payload = decode_token(refresh_token)
    except ValueError as exc:
        raise UnauthorizedError("Недействительный refresh-токен") from exc

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Ожидался refresh-токен")

    raw_user_id = payload.get("sub")

    try:
        user_id = uuid.UUID(raw_user_id)
    except (ValueError, TypeError) as exc:
        raise UnauthorizedError("Некорректный токен") from exc

    user = await db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("Пользователь не найден")

    return create_access_token(user.id)