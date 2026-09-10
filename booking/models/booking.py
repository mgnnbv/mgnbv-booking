from decimal import Decimal
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Date, Enum as SAEnum, ForeignKey, Index, Numeric, Text, func
from sqlalchemy.dialects.postgresql import DATERANGE, ExcludeConstraint, Range
from sqlalchemy.orm import Mapped, mapped_column, relationship

from booking.models.base import Base, uuid_pk
from booking.models.enums import BookingStatus

if TYPE_CHECKING:
    from booking.models.payment import Payment
    from booking.models.property import Property
    from booking.models.tenant import Tenant


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = uuid_pk()
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="RESTRICT"), index=True)

    status: Mapped[BookingStatus] = mapped_column(
        SAEnum(BookingStatus, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=BookingStatus.PENDING,
    )
    
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_range: Mapped[Range[date]] = mapped_column(DATERANGE, nullable=False)
    
    rent_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    deposit_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    monthly_payment_day: Mapped[int | None] = mapped_column(nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    property: Mapped["Property"] = relationship(back_populates="bookings")
    tenant: Mapped["Tenant"] = relationship(back_populates="bookings")
    payments: Mapped[list["Payment"]] = relationship(back_populates="booking", cascade="all, delete-orphan")

    __table_args__ = (

        ExcludeConstraint(
            ("property_id", "="),
            ("date_range", "&&"),
            name="no_overlapping_bookings",
            where=f"status IN ('{BookingStatus.PENDING.value}', '{BookingStatus.ACTIVE.value}')",
        ),
        Index("ix_bookings_property_dates", "property_id", "start_date", "end_date"),
        CheckConstraint("rent_amount > 0", name="ck_bookings_rent_positive"),
        CheckConstraint("deposit_amount IS NULL OR deposit_amount >= 0", name="ck_bookings_deposit_nonneg"),
        CheckConstraint(
        "monthly_payment_day IS NULL OR (monthly_payment_day BETWEEN 1 AND 31)",
        name="ck_bookings_payment_day_range",),)
