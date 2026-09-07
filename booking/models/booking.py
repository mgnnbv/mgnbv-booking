import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Date, Enum as SAEnum, ForeignKey, Index, Numeric, Text, func
from sqlalchemy.dialects.postgresql import DATERANGE, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from booking.models.base import Base, uuid_pk
from booking.models.enums import BookingStatus, RentalType

if TYPE_CHECKING:
    from booking.models.payment import Payment
    from booking.models.property import Property
    from booking.models.tenant import Tenant


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = uuid_pk()
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="RESTRICT"), index=True)

    rental_type: Mapped[RentalType] = mapped_column(
        SAEnum(RentalType, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )    
    status: Mapped[BookingStatus] = mapped_column(
        SAEnum(BookingStatus, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=BookingStatus.PENDING,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    # NULL = длительная аренда без фиксированной даты окончания ("бессрочно").
    # Для проверки пересечений в этом случае используем sentinel-дату в самом
    # запросе (см. ниже про date_range), а не храним 9999-12-31 в БД напрямую —
    # это упрощает логику "договор ещё не закрыт".
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Служебное поле-диапазон для EXCLUDE CONSTRAINT.
    # Заполняется сервисным слоем: [start_date, end_date) либо
    # [start_date, infinity) если end_date IS NULL.
    date_range = mapped_column(DATERANGE, nullable=False)

    rent_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    deposit_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Для долгосрочной аренды — день месяца регулярного платежа (например, 5-е число)
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
        # Запрет пересечения дат для одного объекта, но только среди
        # "активных" броней (pending/active) — отменённые/завершённые
        # не должны блокировать новые даты.
        ExcludeConstraint(
            ("property_id", "="),
            ("date_range", "&&"),
            name="no_overlapping_bookings",
            where="status IN ('pending', 'active')",
        ),
        Index("ix_bookings_property_dates", "property_id", "start_date", "end_date"),
    )
