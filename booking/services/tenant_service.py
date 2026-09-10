import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from booking.core.encryption import encrypt_text
from booking.core.exceptions import NotFoundError
from booking.models.tenant import Tenant
from booking.schemas.tenant import TenantCreate, TenantUpdate


async def list_tenants(db: AsyncSession, owner_id: uuid.UUID, search: str | None = None) -> list[Tenant]:
    stmt = select(Tenant).where(Tenant.owner_id == owner_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(Tenant.full_name.ilike(pattern), Tenant.phone.ilike(pattern)))
    stmt = stmt.order_by(Tenant.full_name)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_owned_tenant(
    db: AsyncSession, owner_id: uuid.UUID, tenant_id: uuid.UUID, *, with_bookings: bool = False
) -> Tenant:
    stmt = select(Tenant).where(Tenant.id == tenant_id, Tenant.owner_id == owner_id)
    if with_bookings:
        stmt = stmt.options(selectinload(Tenant.bookings))

    tenant = await db.scalar(stmt)
    if tenant is None:
        raise NotFoundError("Жилец не найден")
    return tenant


async def create_tenant(db: AsyncSession, owner_id: uuid.UUID, data: TenantCreate) -> Tenant:
    tenant = Tenant(
        owner_id=owner_id,
        full_name=data.full_name,
        phone=data.phone,
        notes=data.notes,
        passport_data_encrypted=encrypt_text(data.passport_data) if data.passport_data else None,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant, attribute_names=["created_at", "updated_at"])
    return tenant


async def update_tenant(db: AsyncSession, tenant: Tenant, data: TenantUpdate) -> Tenant:
    updates = data.model_dump(exclude_unset=True, exclude={"passport_data"})
    for field, value in updates.items():
        setattr(tenant, field, value)

    if "passport_data" in data.model_fields_set:
        tenant.passport_data_encrypted = encrypt_text(data.passport_data) if data.passport_data else None

    await db.commit()
    await db.refresh(tenant, attribute_names=["updated_at"])
    return tenant