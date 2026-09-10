import uuid

from fastapi import APIRouter, File, Form, UploadFile, status

from booking.core.deps import CurrentUser, DbSession
from booking.schemas.property import PropertyCreate, PropertyPhotoRead, PropertyRead, PropertyUpdate
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


@router.post(
    "/{property_id}/photos", response_model=PropertyPhotoRead, status_code=status.HTTP_201_CREATED
)
async def add_property_photo(
    property_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    sort_order: int = Form(default=0),
) -> PropertyPhotoRead:
    photo = await property_service.add_photo(db, current_user.id, property_id, file, sort_order)
    return PropertyPhotoRead.model_validate(photo)


@router.delete("/{property_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property_photo(
    property_id: uuid.UUID, photo_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> None:
    await property_service.delete_photo(db, current_user.id, property_id, photo_id)