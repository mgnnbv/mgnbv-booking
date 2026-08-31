import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.exceptions import ConflictError, NotFoundError
from booking.models.booking import Booking
from booking.models.enums import BookingStatus
from booking.models.property import Property
from booking.models.tenant import Tenant
from booking.schemas.booking import BookingCreate, BookingUpdate


def build_date_range(start_date: date, end_date: date | None) -> Range:
    # end_date is None -> долгосрочная аренда "бессрочно": верхняя граница
    # диапазона не задаётся (упорядочивается PostgreSQL как +infinity).
    return Range(lower=start_date, upper=end_date, bounds="[)")


async def _assert_owns_property(db: AsyncSession, owner_id: uuid.UUID, property_id: uuid.UUID) -> None:
    prop = await db.scalar(select(Property).where(Property.id == property_id, Property.owner_id == owner_id))
    if prop is None:
        raise NotFoundError("Объект не найден")


async def _assert_owns_tenant(db: AsyncSession, owner_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
    tenant = await db.scalar(select(Tenant).where(Tenant.id == tenant_id, Tenant.owner_id == owner_id))
    if tenant is None:
        raise NotFoundError("Жилец не найден")


async def list_property_bookings(
    db: AsyncSession,
    owner_id: uuid.UUID,
    property_id: uuid.UUID,
    date_from: date | None,
    date_to: date | None,
) -> list[Booking]:
    await _assert_owns_property(db, owner_id, property_id)

    stmt = select(Booking).where(Booking.property_id == property_id)
    if date_from is not None:
        stmt = stmt.where((Booking.end_date.is_(None)) | (Booking.end_date > date_from))
    if date_to is not None:
        stmt = stmt.where(Booking.start_date < date_to)
    stmt = stmt.order_by(Booking.start_date)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_owned_booking(db: AsyncSession, owner_id: uuid.UUID, booking_id: uuid.UUID) -> Booking:
    stmt = (
        select(Booking)
        .join(Property, Booking.property_id == Property.id)
        .where(Booking.id == booking_id, Property.owner_id == owner_id)
    )
    booking = await db.scalar(stmt)
    if booking is None:
        raise NotFoundError("Бронь не найдена")
    return booking


async def create_booking(db: AsyncSession, owner_id: uuid.UUID, data: BookingCreate) -> Booking:
    await _assert_owns_property(db, owner_id, data.property_id)
    await _assert_owns_tenant(db, owner_id, data.tenant_id)

    booking = Booking(
        property_id=data.property_id,
        tenant_id=data.tenant_id,
        rental_type=data.rental_type,
        status=data.status,
        start_date=data.start_date,
        end_date=data.end_date,
        date_range=build_date_range(data.start_date, data.end_date),
        rent_amount=data.rent_amount,
        deposit_amount=data.deposit_amount,
        monthly_payment_day=data.monthly_payment_day,
        notes=data.notes,
    )
    db.add(booking)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Объект занят на выбранные даты") from exc

    await db.refresh(booking, attribute_names=["created_at", "updated_at"])
    return booking


async def update_booking(db: AsyncSession, booking: Booking, data: BookingUpdate) -> Booking:
    updates = data.model_dump(exclude_unset=True)
    dates_changed = "start_date" in updates or "end_date" in updates

    new_start = updates.get("start_date", booking.start_date)
    new_end = updates["end_date"] if "end_date" in updates else booking.end_date

    for field, value in updates.items():
        setattr(booking, field, value)

    if dates_changed:
        booking.date_range = build_date_range(new_start, new_end)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Объект занят на выбранные даты") from exc

    await db.refresh(booking, attribute_names=["updated_at"])
    return booking


async def cancel_booking(db: AsyncSession, booking: Booking) -> Booking:
    booking.status = BookingStatus.CANCELLED
    await db.commit()
    await db.refresh(booking, attribute_names=["updated_at"])
    return booking
