import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from booking.models.booking import Booking
from booking.models.enums import PaymentStatus, UserRole
from booking.models.payment import Payment
from booking.models.property import Property
from booking.models.user import User
from booking.schemas.admin import AdminOverview


async def list_users(db: AsyncSession) -> list[User]:
    statement = select(User).order_by(User.created_at.desc())
    return list((await db.execute(statement)).scalars())


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def change_role(db: AsyncSession, user: User, role: UserRole) -> User:
    user.role = role
    await db.commit()
    await db.refresh(user)
    return user


async def build_overview(db: AsyncSession) -> AdminOverview:
    users_count = await db.scalar(select(func.count()).select_from(User))
    properties_count = await db.scalar(select(func.count()).select_from(Property))
    bookings_count = await db.scalar(select(func.count()).select_from(Booking))
    payments_count = await db.scalar(select(func.count()).select_from(Payment))
    paid_amount_total = await db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.status == PaymentStatus.PAID)
    )
    return AdminOverview(
        users_count=users_count or 0,
        properties_count=properties_count or 0,
        bookings_count=bookings_count or 0,
        payments_count=payments_count or 0,
        paid_amount_total=paid_amount_total or 0,
    )
