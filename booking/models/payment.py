import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Date, Enum as SAEnum, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from booking.models.base import Base, uuid_pk
from booking.models.enums import PaymentStatus, PaymentType

if TYPE_CHECKING:
    from booking.models.booking import Booking


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = uuid_pk()
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), index=True)

    payment_type: Mapped[PaymentType] = mapped_column(
        SAEnum(PaymentType, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=PaymentType.RENT,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=PaymentStatus.PENDING,
    )

    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)      # когда должны заплатить
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)  # cash / card / transfer
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    booking: Mapped["Booking"] = relationship(back_populates="payments")

    __table_args__ = (
        Index("ix_payments_status_due", "status", "due_date"),  # для быстрой выборки "что просрочено"
    )
