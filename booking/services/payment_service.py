import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from booking.core.exceptions import NotFoundError
from booking.models.booking import Booking
from booking.models.enums import PaymentStatus
from booking.models.payment import Payment
from booking.models.property import Property
from booking.schemas.payment import OverduePaymentRead, PaymentCreate, PaymentUpdate


def to_overdue_read(payment: Payment) -> OverduePaymentRead:
    return OverduePaymentRead(
        id=payment.id,
        booking_id=payment.booking_id,
        payment_type=payment.payment_type,
        status=payment.status,
        amount=payment.amount,
        due_date=payment.due_date,
        paid_at=payment.paid_at,
        payment_method=payment.payment_method,
        comment=payment.comment,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
        property_title=payment.booking.property.title,
        tenant_full_name=payment.booking.tenant.full_name,
    )


async def _assert_owns_booking(db: AsyncSession, owner_id: uuid.UUID, booking_id: uuid.UUID) -> None:
    stmt = (
        select(Booking)
        .join(Property, Booking.property_id == Property.id)
        .where(Booking.id == booking_id, Property.owner_id == owner_id)
    )
    booking = await db.scalar(stmt)
    if booking is None:
        raise NotFoundError("Бронь не найдена")


async def list_booking_payments(db: AsyncSession, owner_id: uuid.UUID, booking_id: uuid.UUID) -> list[Payment]:
    await _assert_owns_booking(db, owner_id, booking_id)
    stmt = select(Payment).where(Payment.booking_id == booking_id).order_by(Payment.due_date)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_payment(
    db: AsyncSession, owner_id: uuid.UUID, booking_id: uuid.UUID, data: PaymentCreate
) -> Payment:
    await _assert_owns_booking(db, owner_id, booking_id)

    payment = Payment(booking_id=booking_id, **data.model_dump())
    db.add(payment)
    await db.commit()
    await db.refresh(payment, attribute_names=["created_at", "updated_at"])
    return payment


async def get_owned_payment(db: AsyncSession, owner_id: uuid.UUID, payment_id: uuid.UUID) -> Payment:
    stmt = (
        select(Payment)
        .join(Booking, Payment.booking_id == Booking.id)
        .join(Property, Booking.property_id == Property.id)
        .where(Payment.id == payment_id, Property.owner_id == owner_id)
    )
    payment = await db.scalar(stmt)
    if payment is None:
        raise NotFoundError("Платёж не найден")
    return payment


async def update_payment(db: AsyncSession, payment: Payment, data: PaymentUpdate) -> Payment:
    updates = data.model_dump(exclude_unset=True)

    if updates.get("status") == PaymentStatus.PAID and payment.paid_at is None and "paid_at" not in updates:
        updates["paid_at"] = datetime.now(timezone.utc)

    for field, value in updates.items():
        setattr(payment, field, value)

    await db.commit()
    await db.refresh(payment, attribute_names=["updated_at"])
    return payment


async def cancel_payment(db: AsyncSession, payment: Payment) -> Payment:
    payment.status = PaymentStatus.CANCELLED
    await db.commit()
    await db.refresh(payment, attribute_names=["updated_at"])
    return payment


async def list_overdue_payments(db: AsyncSession, owner_id: uuid.UUID) -> list[Payment]:
    today = date.today()
    stmt = (
        select(Payment)
        .join(Booking, Payment.booking_id == Booking.id)
        .join(Property, Booking.property_id == Property.id)
        .where(
            Property.owner_id == owner_id,
            Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.OVERDUE]),
            Payment.due_date < today,
        )
        .options(
            joinedload(Payment.booking).joinedload(Booking.property),
            joinedload(Payment.booking).joinedload(Booking.tenant),
        )
        .order_by(Payment.due_date)
    )
    result = await db.execute(stmt)
    return list(result.unique().scalars().all())
