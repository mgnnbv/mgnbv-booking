import uuid

from fastapi import APIRouter, status

from booking.core.deps import CurrentUser, DbSession
from booking.core.events import publish_event
from booking.models.booking import Booking
from booking.models.enums import PaymentStatus
from booking.models.property import Property
from booking.models.tenant import Tenant
from booking.schemas.payment import OverduePaymentRead, PaymentCreate, PaymentRead, PaymentUpdate
from booking.services import payment_service

router = APIRouter(tags=["payments"])


@router.get("/bookings/{booking_id}/payments", response_model=list[PaymentRead])
async def list_booking_payments(booking_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> list[PaymentRead]:
    payments = await payment_service.list_booking_payments(db, current_user.id, booking_id)
    return [PaymentRead.model_validate(p) for p in payments]


@router.post("/bookings/{booking_id}/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(
    booking_id: uuid.UUID, data: PaymentCreate, current_user: CurrentUser, db: DbSession
) -> PaymentRead:
    payment = await payment_service.create_payment(db, current_user.id, booking_id, data)
    return PaymentRead.model_validate(payment)


@router.get("/payments/overdue", response_model=list[OverduePaymentRead])
async def list_overdue_payments(current_user: CurrentUser, db: DbSession) -> list[OverduePaymentRead]:
    payments = await payment_service.list_overdue_payments(db, current_user.id)
    return [payment_service.to_overdue_read(p) for p in payments]


@router.get("/payments/{payment_id}", response_model=PaymentRead)
async def get_payment(payment_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> PaymentRead:
    payment = await payment_service.get_owned_payment(db, current_user.id, payment_id)
    return PaymentRead.model_validate(payment)


@router.patch("/payments/{payment_id}", response_model=PaymentRead)
async def update_payment(
    payment_id: uuid.UUID, data: PaymentUpdate, current_user: CurrentUser, db: DbSession
) -> PaymentRead:
    payment = await payment_service.get_owned_payment(db, current_user.id, payment_id)
    was_paid = payment.status == PaymentStatus.PAID
    payment = await payment_service.update_payment(db, payment, data)

    if payment.status == PaymentStatus.PAID and not was_paid:
        booking = await db.get(Booking, payment.booking_id)
        property_ = await db.get(Property, booking.property_id) if booking else None
        tenant = await db.get(Tenant, booking.tenant_id) if booking else None
        await publish_event(
            "payment.received",
            {
                "payment_id": str(payment.id),
                "booking_id": str(payment.booking_id),
                "owner_email": current_user.email,
                "owner_name": current_user.full_name,
                "property_title": property_.title if property_ else None,
                "tenant_name": tenant.full_name if tenant else None,
                "amount": float(payment.amount),
                "payment_type": payment.payment_type.value,
                "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
            },
        )
    return PaymentRead.model_validate(payment)


@router.delete("/payments/{payment_id}", response_model=PaymentRead)
async def cancel_payment(payment_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> PaymentRead:
    payment = await payment_service.get_owned_payment(db, current_user.id, payment_id)
    payment = await payment_service.cancel_payment(db, payment)
    return PaymentRead.model_validate(payment)