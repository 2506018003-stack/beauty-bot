from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models import Booking, BookingStatus, Service
from api.schemas import BookingCreate
from api.dependencies import get_current_guest
from bot.services.loyalty import points_earned_for_amount

router = APIRouter()


@router.post("")
async def create_booking(payload: BookingCreate, user_id: int = Depends(get_current_guest), db: AsyncSession = Depends(get_db)):
    service_result = await db.execute(select(Service).where(Service.id == payload.service_id))
    service = service_result.scalar_one()

    booking = Booking(
        user_id=user_id,
        master_id=payload.master_id,
        service_id=payload.service_id,
        booking_date=payload.booking_date,
        booking_time=payload.booking_time,
        comment=payload.comment,
        status=BookingStatus.PENDING,
        points_earned=points_earned_for_amount(service.price),
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return {"id": booking.id, "status": booking.status.value}


@router.get("/my")
async def my_bookings(user_id: int = Depends(get_current_guest), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Booking).where(Booking.user_id == user_id).order_by(Booking.created_at.desc()).limit(20)
    )
    bookings = result.scalars().all()
    return [
        {
            "id": b.id, "service": b.service.name, "master": b.master.name,
            "booking_date": str(b.booking_date), "booking_time": str(b.booking_time),
            "status": b.status.value, "comment": b.comment
        }
        for b in bookings
    ]
