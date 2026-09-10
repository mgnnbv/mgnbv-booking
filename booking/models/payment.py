import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Date, Enum as SAEnum, ForeignKey, Index, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from booking.models.base import Base, uuid_pk
from booking.models.enums import PaymentMethod, PaymentStatus, PaymentType, enum_values

if TYPE_CHECKING:
    from booking.models.booking import Booking


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = uuid_pk()
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), index=True)

    payment_type: Mapped[PaymentType] = mapped_column(
        SAEnum(PaymentType, values_callable=enum_values),
        default=PaymentType.RENT,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, values_callable=enum_values),
        default=PaymentStatus.PENDING,
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)      # когда должны заплатить
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        SAEnum(PaymentMethod, values_callable=enum_values), nullable=True
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    booking: Mapped["Booking"] = relationship(back_populates="payments")

    __table_args__ = (
        Index("ix_payments_status_due", "status", "due_date"),  # для быстрой выборки "что просрочено"
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        CheckConstraint(
            "status != 'paid' OR paid_at IS NOT NULL",
            name="ck_payments_paid_requires_paid_at",
        ),
    )