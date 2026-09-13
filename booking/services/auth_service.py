import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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
from booking.models.pending_registration import PendingRegistration
from booking.models.enums import UserRole
from booking.models.user import User
from booking.schemas.auth import LoginRequest, RegisterRequest, TokenPair


def _generate_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def register_user(db: AsyncSession, data: RegisterRequest) -> PendingRegistration:

    existing_email = await db.scalar(select(User).where(User.email == data.email))
    if existing_email is not None:
        raise ConflictError("Пользователь с таким email уже зарегистрирован")

    if data.phone is not None:
        existing_phone = await db.scalar(select(User).where(User.phone == data.phone))
        if existing_phone is not None:
            raise ConflictError("Пользователь с таким телефоном уже зарегистрирован")

    pending = await db.scalar(select(PendingRegistration).where(PendingRegistration.email == data.email))
    if pending is None:
        pending = PendingRegistration(email=data.email)
        db.add(pending)

    pending.phone = data.phone
    pending.full_name = data.full_name
    pending.password_hash = hash_password(data.password)
    pending.verification_code = _generate_verification_code()
    pending.verification_code_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.email_verification_code_ttl_minutes
    )

    await db.commit()
    return pending


async def verify_email(db: AsyncSession, email: str, code: str) -> User:
    pending = await db.scalar(select(PendingRegistration).where(PendingRegistration.email == email))
    if pending is None:
        raise NotFoundError("Регистрация не найдена — зарегистрируйтесь заново")

    if pending.verification_code_expires_at < datetime.now(timezone.utc):
        raise ValidationError("Код истёк — зарегистрируйтесь заново, чтобы получить новый")

    if not secrets.compare_digest(pending.verification_code, code):
        raise ValidationError("Неверный код")

    user = User(
        email=pending.email,
        phone=pending.phone,
        password_hash=pending.password_hash,
        full_name=pending.full_name,
        role=UserRole.ADMIN if settings.is_admin_email(pending.email) else UserRole.USER,
    )
    db.add(user)
    await db.delete(pending)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Пользователь с таким email или телефоном уже зарегистрирован") from exc

    await db.refresh(user, attribute_names=["created_at", "updated_at"])
    return user


async def authenticate_user(db: AsyncSession, data: LoginRequest) -> User:
    user = await db.scalar(select(User).where(User.email == data.email))
    if user is not None and verify_password(data.password, user.password_hash):
        return user

    if user is None:
        pending = await db.scalar(select(PendingRegistration).where(PendingRegistration.email == data.email))
        if pending is not None:
            raise ForbiddenError("Email не подтверждён. Введите код из письма.")

    raise UnauthorizedError("Неверные учётные данные")


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
