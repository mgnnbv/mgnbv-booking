from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.database import get_db
from booking.core.exceptions import ForbiddenError, UnauthorizedError
from booking.core.security import decode_token
from booking.models.enums import UserRole
from booking.models.user import User

oauth2_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:

    token = credentials.credentials if credentials else None
    if token is None:
        raise UnauthorizedError("Токен не предоставлен")

    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise UnauthorizedError("Неверный или истёкший токен") from exc

    if payload.get("type") != "access":
        raise UnauthorizedError("Ожидался access-токен")

    raw_user_id = payload.get("sub")
    if raw_user_id is None:
        raise UnauthorizedError("Некорректный токен")

    try:
        user_id = UUID(raw_user_id)
    except (ValueError, TypeError) as exc:
        raise UnauthorizedError("Некорректный токен") from exc

    user = await db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("Пользователь не найден")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


def require_role(*allowed_roles: UserRole):
    """Return a dependency that allows only users with one of the given roles."""

    async def check_role(current_user: CurrentUser) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenError("Недостаточно прав для выполнения этого действия")
        return current_user

    return check_role


AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]
