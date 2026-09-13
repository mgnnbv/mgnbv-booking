import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from booking.models.base import Base, uuid_pk
from booking.models.enums import UserRole, enum_values

if TYPE_CHECKING:
    from booking.models.property import Property
    from booking.models.tenant import Tenant


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole", values_callable=enum_values),
        nullable=False,
        default=UserRole.USER,
        server_default=UserRole.USER.value,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    properties: Mapped[list["Property"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    tenants: Mapped[list["Tenant"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
