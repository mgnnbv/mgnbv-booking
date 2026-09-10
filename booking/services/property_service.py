import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

from booking.core.config import settings
from booking.core.exceptions import NotFoundError, ValidationError
from booking.models.property import Property, PropertyPhoto
from booking.schemas.property import PropertyCreate, PropertyUpdate

ALLOWED_PHOTO_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def _write_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _delete_file(path: Path) -> None:
    path.unlink(missing_ok=True)


def _disk_path_from_url(url: str) -> Path:
    relative = url.removeprefix(settings.photos_public_base_url).lstrip("/")
    return Path(settings.photos_storage_path) / relative


async def list_properties(
    db: AsyncSession, owner_id: uuid.UUID, include_archived: bool = False
) -> list[Property]:
    stmt = select(Property).options(selectinload(Property.photos)).where(Property.owner_id == owner_id)
    if not include_archived:
        stmt = stmt.where(Property.is_archived.is_(False))
    stmt = stmt.order_by(Property.created_at.desc())

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_owned_property(db: AsyncSession, owner_id: uuid.UUID, property_id: uuid.UUID) -> Property:
    stmt = (
        select(Property)
        .options(selectinload(Property.photos))
        .where(Property.id == property_id, Property.owner_id == owner_id)
    )
    prop = await db.scalar(stmt)
    if prop is None:
        raise NotFoundError("Объект не найден")
    return prop


async def create_property(db: AsyncSession, owner_id: uuid.UUID, data: PropertyCreate) -> Property:
    prop = Property(owner_id=owner_id, **data.model_dump())
    db.add(prop)
    await db.commit()
    await db.refresh(prop, attribute_names=["created_at", "updated_at", "photos"])
    return prop


async def update_property(db: AsyncSession, prop: Property, data: PropertyUpdate) -> Property:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(prop, field, value)
    await db.commit()
    await db.refresh(prop, attribute_names=["updated_at", "photos"])
    return prop


async def archive_property(db: AsyncSession, prop: Property) -> Property:
    prop.is_archived = True
    await db.commit()
    await db.refresh(prop, attribute_names=["updated_at", "photos"])
    return prop


async def add_photo(
    db: AsyncSession, owner_id: uuid.UUID, property_id: uuid.UUID, file: UploadFile, sort_order: int = 0
) -> PropertyPhoto:
    await get_owned_property(db, owner_id, property_id)  # заодно проверяет что объект принадлежит юзеру

    ext = ALLOWED_PHOTO_TYPES.get(file.content_type or "")
    if ext is None:
        raise ValidationError("Допустимые форматы фото: JPEG, PNG, WEBP")

    content = await file.read()
    if len(content) > settings.max_photo_size_mb * 1024 * 1024:
        raise ValidationError(f"Файл больше {settings.max_photo_size_mb} МБ")

    filename = f"{uuid.uuid4()}{ext}"
    disk_path = Path(settings.photos_storage_path) / str(property_id) / filename
    await run_in_threadpool(_write_file, disk_path, content)

    url = f"{settings.photos_public_base_url}/{property_id}/{filename}"
    photo = PropertyPhoto(property_id=property_id, url=url, sort_order=sort_order)
    db.add(photo)
    await db.commit()
    await db.refresh(photo, attribute_names=["id"])
    return photo


async def delete_photo(db: AsyncSession, owner_id: uuid.UUID, property_id: uuid.UUID, photo_id: uuid.UUID) -> None:
    await get_owned_property(db, owner_id, property_id)  # проверка владельца

    photo = await db.get(PropertyPhoto, photo_id)
    if photo is None or photo.property_id != property_id:
        raise NotFoundError("Фотография не найдена")

    disk_path = _disk_path_from_url(photo.url)
    await db.delete(photo)
    await db.commit()
    await run_in_threadpool(_delete_file, disk_path)