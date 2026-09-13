import uuid

from fastapi import APIRouter

from booking.core.deps import AdminUser, DbSession
from booking.core.exceptions import ForbiddenError, NotFoundError
from booking.models.enums import UserRole
from booking.schemas.admin import AdminOverview
from booking.schemas.user import UserRead, UserRoleUpdate
from booking.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserRead])
async def list_users(
    db: DbSession,
    _: AdminUser,
) -> list[UserRead]:
    users = await admin_service.list_users(db)
    return [UserRead.model_validate(user) for user in users]


@router.patch("/users/{user_id}/role", response_model=UserRead)
async def update_user_role(
    user_id: uuid.UUID,
    data: UserRoleUpdate,
    db: DbSession,
    current_admin: AdminUser,
) -> UserRead:
    if user_id == current_admin.id and data.role != UserRole.ADMIN:
        raise ForbiddenError("Администратор не может снять роль admin с самого себя")

    user = await admin_service.get_user(db, user_id)
    if user is None:
        raise NotFoundError("Пользователь не найден")
    user = await admin_service.change_role(db, user, data.role)
    return UserRead.model_validate(user)


@router.get("/overview", response_model=AdminOverview)
async def get_overview(
    db: DbSession,
    _: AdminUser,
) -> AdminOverview:
    return await admin_service.build_overview(db)
