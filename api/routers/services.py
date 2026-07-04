from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models import ServiceCategory, Service, Master

router = APIRouter()


@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ServiceCategory).order_by(ServiceCategory.sort_order))
    return [{"id": c.id, "name": c.name} for c in result.scalars().all()]


@router.get("/items")
async def get_services(category_id: int | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Service).where(Service.is_active.is_(True))
    if category_id:
        query = query.where(Service.category_id == category_id)
    result = await db.execute(query)
    return [
        {
            "id": s.id, "name": s.name, "description": s.description,
            "price": float(s.price), "duration_minutes": s.duration_minutes,
            "photo_url": s.photo_url, "category_id": s.category_id
        }
        for s in result.scalars().all()
    ]


@router.get("/masters")
async def get_masters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Master).where(Master.is_active.is_(True)))
    return [
        {"id": m.id, "name": m.name, "specialty": m.specialty, "photo_url": m.photo_url, "bio": m.bio}
        for m in result.scalars().all()
    ]
