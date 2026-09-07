from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.database import get_db
from booking.core.exceptions import UnauthorizedError
from booking.core.security import decode_token
from booking.models.user import User

oauth2_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    
    token = credentials.credentials if credentials else None
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise UnauthorizedError("Неверный или истёкший токен") from exc

    if payload.get("type") != "access":
        raise UnauthorizedError("Ожидался access-токен")

    raw_user_id = payload.get("sub")
    if raw_user_id is None:
        raise UnauthorizedError("Некорректный токен")

    user = await db.get(User, UUID(raw_user_id))
    if user is None:
        raise UnauthorizedError("Пользователь не найден")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
