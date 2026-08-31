import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.exceptions import ConflictError, UnauthorizedError
from booking.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from booking.models.user import User
from booking.schemas.auth import LoginRequest, RegisterRequest, TokenPair


async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
    existing = await db.scalar(select(User).where(User.phone == data.phone))
    if existing is not None:
        raise ConflictError("Пользователь с таким телефоном уже зарегистрирован")

    user = User(
        phone=data.phone,
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user, attribute_names=["created_at", "updated_at"])
    return user


async def authenticate_user(db: AsyncSession, data: LoginRequest) -> User:
    user = await db.scalar(select(User).where(User.phone == data.phone))
    if user is None or not verify_password(data.password, user.password_hash):
        raise UnauthorizedError("Неверный телефон или пароль")
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
    user = await db.get(User, uuid.UUID(raw_user_id)) if raw_user_id else None
    if user is None:
        raise UnauthorizedError("Пользователь не найден")

    return create_access_token(user.id)
