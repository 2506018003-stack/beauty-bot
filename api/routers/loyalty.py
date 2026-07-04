from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models import User
from api.dependencies import get_current_guest
from bot.services.loyalty import get_or_create_referral_code

router = APIRouter()


@router.get("/me")
async def my_loyalty(user_id: int = Depends(get_current_guest), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    ref_code = await get_or_create_referral_code(db, user)
    await db.commit()
    return {"points": user.loyalty_points, "referral_code": ref_code}
