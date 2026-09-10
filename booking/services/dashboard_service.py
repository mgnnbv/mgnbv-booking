import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from booking.models.enums import BookingStatus, PaymentStatus
from booking.models.booking import Booking
from booking.models.enums import PaymentStatus
from booking.models.payment import Payment
from booking.models.property import Property
from booking.models.tenant import Tenant
from booking.schemas.dashboard import DashboardResponse, MonthlyIncomeSummary, UpcomingBookingEvent
from booking.schemas.property import PropertyRead
from booking.services import payment_service

UPCOMING_HORIZON_DAYS = 7


async def _upcoming_events(db: AsyncSession, owner_id: uuid.UUID, today: date, horizon: date) -> list[UpcomingBookingEvent]:
    check_ins_stmt = (
        select(Booking, Property.title, Tenant.full_name)
        .join(Property, Booking.property_id == Property.id)
        .join(Tenant, Booking.tenant_id == Tenant.id)
        .where(
            Property.owner_id == owner_id,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.ACTIVE]),
            Booking.start_date >= today,
            Booking.start_date <= horizon,
        )
    )
    check_outs_stmt = (
        select(Booking, Property.title, Tenant.full_name)
        .join(Property, Booking.property_id == Property.id)
        .join(Tenant, Booking.tenant_id == Tenant.id)
        .where(
            Property.owner_id == owner_id,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.ACTIVE]),
            Booking.end_date.is_not(None),
            Booking.end_date >= today,
            Booking.end_date <= horizon,
        )
    )

    check_ins = (await db.execute(check_ins_stmt)).all()
    check_outs = (await db.execute(check_outs_stmt)).all()

    events = [
        UpcomingBookingEvent(
            booking_id=booking.id,
            property_id=booking.property_id,
            property_title=title,
            tenant_id=booking.tenant_id,
            tenant_full_name=tenant_name,
            event_type="check_in",
            event_date=booking.start_date,
        )
        for booking, title, tenant_name in check_ins
    ] + [
        UpcomingBookingEvent(
            booking_id=booking.id,
            property_id=booking.property_id,
            property_title=title,
            tenant_id=booking.tenant_id,
            tenant_full_name=tenant_name,
            event_type="check_out",
            event_date=booking.end_date,
        )
        for booking, title, tenant_name in check_outs
    ]
    events.sort(key=lambda event: event.event_date)
    return events


async def _monthly_income_summary(db: AsyncSession, owner_id: uuid.UUID, today: date) -> MonthlyIncomeSummary:
    month_start = today.replace(day=1)
    next_month_start = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)

    paid_stmt = (
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(Booking, Payment.booking_id == Booking.id)
        .join(Property, Booking.property_id == Property.id)
        .where(
            Property.owner_id == owner_id,
            Payment.status == PaymentStatus.PAID,
            Payment.paid_at.is_not(None),
            Payment.paid_at >= month_start,
            Payment.paid_at < next_month_start,
        )
    )
    expected_stmt = (
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(Booking, Payment.booking_id == Booking.id)
        .join(Property, Booking.property_id == Property.id)
        .where(
            Property.owner_id == owner_id,
            Payment.status != PaymentStatus.CANCELLED,
            Payment.due_date >= month_start,
            Payment.due_date < next_month_start,
        )
    )

    total_paid = (await db.execute(paid_stmt)).scalar_one()
    total_expected = (await db.execute(expected_stmt)).scalar_one()

    return MonthlyIncomeSummary(
        year=today.year,
        month=today.month,
        total_paid=total_paid,
        total_expected=total_expected,
    )


async def build_dashboard(db: AsyncSession, owner_id: uuid.UUID) -> DashboardResponse:
    today = date.today()
    horizon = today + timedelta(days=UPCOMING_HORIZON_DAYS)

    properties_stmt = (
        select(Property)
        .options(selectinload(Property.photos))
        .where(Property.owner_id == owner_id, Property.is_archived.is_(False))
        .order_by(Property.created_at.desc())
    )
    properties = (await db.execute(properties_stmt)).scalars().all()

    upcoming_events = await _upcoming_events(db, owner_id, today, horizon)

    overdue = await payment_service.list_overdue_payments(db, owner_id)
    overdue_payments = [payment_service.to_overdue_read(p) for p in overdue]

    monthly_income = await _monthly_income_summary(db, owner_id, today)

    return DashboardResponse(
        properties=[PropertyRead.model_validate(p) for p in properties],
        upcoming_events=upcoming_events,
        overdue_payments=overdue_payments,
        monthly_income=monthly_income,
    )
