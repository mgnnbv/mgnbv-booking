import uuid
from datetime import date

from fastapi import APIRouter, Query, status

from booking.core.deps import CurrentUser, DbSession
from booking.core.events import publish_event
from booking.models.property import Property
from booking.models.tenant import Tenant
from booking.schemas.booking import BookingCreate, BookingRead, BookingUpdate
from booking.services import booking_service

router = APIRouter(tags=["bookings"])


@router.get("/properties/{property_id}/bookings", response_model=list[BookingRead])
async def list_property_bookings(
    property_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
) -> list[BookingRead]:
    bookings = await booking_service.list_property_bookings(db, current_user.id, property_id, date_from, date_to)
    return [BookingRead.model_validate(b) for b in bookings]


@router.post("/bookings", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
async def create_booking(data: BookingCreate, current_user: CurrentUser, db: DbSession) -> BookingRead:
    booking = await booking_service.create_booking(db, current_user.id, data)

    property_ = await db.get(Property, data.property_id)
    tenant = await db.get(Tenant, data.tenant_id)
    await publish_event(
        "booking.created",
        {
            "booking_id": str(booking.id),
            "owner_email": current_user.email,
            "owner_name": current_user.full_name,
            "property_title": property_.title if property_ else None,
            "tenant_name": tenant.full_name if tenant else None,
            "start_date": booking.start_date.isoformat(),
            "end_date": booking.end_date.isoformat() if booking.end_date else None,
            "rent_amount": float(booking.rent_amount),
        },
    )
    return BookingRead.model_validate(booking)


@router.get("/bookings/{booking_id}", response_model=BookingRead)
async def get_booking(booking_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> BookingRead:
    booking = await booking_service.get_owned_booking(db, current_user.id, booking_id)
    return BookingRead.model_validate(booking)


@router.patch("/bookings/{booking_id}", response_model=BookingRead)
async def update_booking(
    booking_id: uuid.UUID, data: BookingUpdate, current_user: CurrentUser, db: DbSession
) -> BookingRead:
    booking = await booking_service.get_owned_booking(db, current_user.id, booking_id)
    booking = await booking_service.update_booking(db, booking, data)
    return BookingRead.model_validate(booking)


@router.delete("/bookings/{booking_id}", response_model=BookingRead)
async def cancel_booking(booking_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> BookingRead:
    booking = await booking_service.get_owned_booking(db, current_user.id, booking_id)
    booking = await booking_service.cancel_booking(db, booking)
    return BookingRead.model_validate(booking)