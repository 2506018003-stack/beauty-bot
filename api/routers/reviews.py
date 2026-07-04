from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models import Review

router = APIRouter()


@router.get("")
async def list_reviews(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Review).where(Review.is_published.is_(True)).order_by(Review.created_at.desc()).limit(50)
    )
    return [
        {
            "id": r.id, "rating": r.rating, "text": r.text,
            "master": r.master.name if r.master else None,
            "created_at": str(r.created_at)
        }
        for r in result.scalars().all()
    ]
