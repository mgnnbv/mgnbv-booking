import uuid

from fastapi import APIRouter, Query, status

from booking.core.deps import CurrentUser, DbSession
from booking.schemas.booking import BookingRead
from booking.schemas.tenant import TenantCreate, TenantDetailRead, TenantRead, TenantUpdate
from booking.services import tenant_service

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("", response_model=list[TenantRead])
async def list_tenants(
    current_user: CurrentUser, db: DbSession, search: str | None = Query(default=None)
) -> list[TenantRead]:
    tenants = await tenant_service.list_tenants(db, current_user.id, search)
    return [tenant_service.to_tenant_read(t) for t in tenants]


@router.post("", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
async def create_tenant(data: TenantCreate, current_user: CurrentUser, db: DbSession) -> TenantRead:
    tenant = await tenant_service.create_tenant(db, current_user.id, data)
    return tenant_service.to_tenant_read(tenant)


@router.get("/{tenant_id}", response_model=TenantDetailRead)
async def get_tenant(tenant_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> TenantDetailRead:
    tenant = await tenant_service.get_owned_tenant(db, current_user.id, tenant_id, with_bookings=True)
    base = tenant_service.to_tenant_read(tenant)
    return TenantDetailRead(
        **base.model_dump(),
        bookings=[BookingRead.model_validate(b) for b in tenant.bookings],
    )


@router.patch("/{tenant_id}", response_model=TenantRead)
async def update_tenant(
    tenant_id: uuid.UUID, data: TenantUpdate, current_user: CurrentUser, db: DbSession
) -> TenantRead:
    tenant = await tenant_service.get_owned_tenant(db, current_user.id, tenant_id)
    tenant = await tenant_service.update_tenant(db, tenant, data)
    return tenant_service.to_tenant_read(tenant)
