import uuid

from fastapi import APIRouter, status

from booking.core.deps import CurrentUser, DbSession
from booking.schemas.property import PropertyCreate, PropertyRead, PropertyUpdate
from booking.services import property_service

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=list[PropertyRead])
async def list_properties(
    current_user: CurrentUser, db: DbSession, include_archived: bool = False
) -> list[PropertyRead]:
    properties = await property_service.list_properties(db, current_user.id, include_archived)
    return [PropertyRead.model_validate(p) for p in properties]


@router.post("", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
async def create_property(data: PropertyCreate, current_user: CurrentUser, db: DbSession) -> PropertyRead:
    prop = await property_service.create_property(db, current_user.id, data)
    return PropertyRead.model_validate(prop)


@router.get("/{property_id}", response_model=PropertyRead)
async def get_property(property_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> PropertyRead:
    prop = await property_service.get_owned_property(db, current_user.id, property_id)
    return PropertyRead.model_validate(prop)


@router.patch("/{property_id}", response_model=PropertyRead)
async def update_property(
    property_id: uuid.UUID, data: PropertyUpdate, current_user: CurrentUser, db: DbSession
) -> PropertyRead:
    prop = await property_service.get_owned_property(db, current_user.id, property_id)
    prop = await property_service.update_property(db, prop, data)
    return PropertyRead.model_validate(prop)


@router.delete("/{property_id}", response_model=PropertyRead)
async def archive_property(property_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> PropertyRead:
    """Soft delete: помечает объект как is_archived, не удаляет из БД."""
    prop = await property_service.get_owned_property(db, current_user.id, property_id)
    prop = await property_service.archive_property(db, prop)
    return PropertyRead.model_validate(prop)
