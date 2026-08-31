import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from booking.models.base import Base, uuid_pk
from booking.models.enums import PropertyType, RentalType

if TYPE_CHECKING:
    from booking.models.booking import Booking
    from booking.models.user import User


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)          # "Квартира на Ленина 5"
    property_type: Mapped[PropertyType] = mapped_column(SAEnum(PropertyType), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Дефолтная ставка — используется как подсказка при создании новой брони,
    # не является источником истины по факту оплаты (это в Payment).
    default_rate: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    default_rental_type: Mapped[RentalType | None] = mapped_column(SAEnum(RentalType), nullable=True)

    is_archived: Mapped[bool] = mapped_column(default=False)  # объект временно не сдаётся / скрыт

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="properties")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    photos: Mapped[list["PropertyPhoto"]] = relationship(back_populates="property", cascade="all, delete-orphan")


class PropertyPhoto(Base):
    __tablename__ = "property_photos"

    id: Mapped[uuid.UUID] = uuid_pk()
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0)

    property: Mapped["Property"] = relationship(back_populates="photos")
