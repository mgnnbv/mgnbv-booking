import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from booking.core.exceptions import NotFoundError
from booking.models.property import Property
from booking.schemas.property import PropertyCreate, PropertyUpdate


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


async def archive_property(db: AsyncSession, prop: Property) -> Property:
    prop.is_archived = True
    await db.commit()
    await db.refresh(prop, attribute_names=["updated_at"])
    return prop
